from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import ApprovalCase, approval_graph
from odoo.addons.workflow_core.tests.common import edge, node


@tagged("post_install", "-at_install")
class TestApproval(ApprovalCase):
    def test_multiple_approval_nodes_have_independent_snapshots(self):
        graph = approval_graph([{"kind": "user", "ref": self.first.id}], self.worker.id)
        second = node("second", "approval")
        second["data"]["config"] = {"levels": [{"kind": "user", "ref": self.second.id}]}
        graph["nodes"].insert(2, second)
        graph["edges"] = [
            edge("start", "approval"),
            edge("approval", "second"),
            edge("second", "work"),
            edge("work", "end"),
        ]
        instance = self.instance(self.published(graph))
        first = self.env["workflow.approval"].search(
            [("instance_id", "=", instance.id)],
        )
        self.decide(first, self.first)
        second = self.env["workflow.approval"].search(
            [
                ("instance_id", "=", instance.id),
                ("id", "!=", first.id),
            ],
        )
        self.assertEqual(first.state, "approved")
        self.assertEqual(second.state, "pending")
        self.assertFalse(instance.task_ids)
        self.assertNotEqual(
            first.review_ids.definition_id,
            second.review_ids.definition_id,
        )
        with self.assertRaises(AccessError):
            second.with_user(self.second).action_decide(
                "approve",
                "",
                first.review_ids.id,
            )
        with self.assertRaises(AccessError):
            instance.with_user(self.second).action_review(
                first.id,
                second.review_ids.id,
                "approve",
            )
        self.decide(second, self.second)
        self.assertEqual(len(instance.task_ids), 1)

    def test_sequential_approval_and_explicit_review_retry(self):
        instance, approval = self.begin()
        canvas = instance.version_id.with_user(self.viewer).get_canvas()
        self.assertNotIn("approval", canvas["node_options"])
        label_map = canvas["approval_labels"]["user"]
        self.assertEqual(
            label_map,
            {self.first.id: self.first.name, self.second.id: self.second.name},
        )
        self.assertEqual(
            approval.review_ids.sorted("sequence").mapped("status"),
            ["pending", "waiting"],
        )
        self.assertFalse(instance.task_ids)
        self.decide(approval, self.first)
        self.assertEqual(approval.state, "pending")
        before = len(instance.log_ids)
        self.decide(approval, self.first, comment="重试不能覆盖意见")
        self.assertEqual(len(instance.log_ids), before)
        self.assertEqual(
            approval.review_ids.filtered(lambda r: r.sequence == 1).comment,
            "已核实",
        )
        self.decide(approval, self.second, sequence=2)
        self.assertEqual(approval.validation_status, "validated")
        self.assertEqual(approval.state, "approved")
        self.assertEqual(instance.task_ids.name, "work")
        instance.task_ids.action_complete()
        self.assertEqual(instance.state, "done")

    def test_rejection_closes_flow_and_keeps_all_history(self):
        instance, approval = self.begin()
        self.decide(approval, self.first, decision="reject", comment="资料不完整")
        self.assertEqual(instance.state, "rejected")
        self.assertEqual(approval.state, "rejected")
        self.assertEqual(approval.node_instance_id.state, "rejected")
        self.assertEqual(
            approval.review_ids.sorted("sequence").mapped("status"),
            ["rejected", "cancel"],
        )
        self.assertFalse(instance.task_ids)
        self.assertEqual(len(approval.review_ids), 2)
        self.assertEqual(instance.log_ids[-1].comment, "资料不完整")

    def test_wrong_level_non_reviewer_and_missing_comment(self):
        _, approval = self.begin()
        for user, sequence in ((self.second, 2), (self.manager, 1), (self.worker, 1)):
            with self.assertRaises(AccessError):
                self.decide(approval, user, sequence)
        with self.assertRaises(ValidationError):
            self.decide(approval, self.first, decision="reject", comment="")
        with self.assertRaises(ValidationError):
            approval.with_user(self.first).validate_tier()
        self.assertEqual(
            approval.review_ids.sorted("sequence").mapped("status"),
            ["pending", "waiting"],
        )

    def test_same_person_consecutive_levels_require_separate_review_ids(self):
        instance, approval = self.begin([{"kind": "user", "ref": self.first.id}] * 2)
        self.decide(approval, self.first)
        self.decide(approval, self.first)
        self.assertFalse(instance.task_ids)
        self.assertEqual(
            approval.review_ids.filtered(lambda r: r.sequence == 2).status,
            "pending",
        )
        self.decide(approval, self.first, sequence=2)
        self.assertEqual(len(instance.task_ids), 1)

    def test_group_candidates_are_frozen_and_any_member_can_approve(self):
        group = self.env["res.groups"].create(
            {
                "name": "Workflow review group",
                "user_ids": [Command.set((self.first | self.second).ids)],
            },
        )
        instance, approval = self.begin([{"kind": "group", "ref": group.id}])
        frozen = set(approval.review_ids.reviewer_ids.ids)
        group.user_ids = self.manager
        self.assertEqual(set(approval.review_ids.reviewer_ids.ids), frozen)
        self.decide(approval, self.second)
        self.assertEqual(approval.state, "approved")
        with self.assertRaises(UserError):
            self.decide(approval, self.first)
        self.assertEqual(len(instance.task_ids), 1)

    def test_dynamic_user_field_is_snapshotted(self):
        partner = self.env["res.partner"].create(
            {"name": "Approval business", "user_id": self.first.id},
        )
        _, approval = self.begin(
            [{"kind": "field", "ref": "user_id"}],
            model=True,
            res_id=partner.id,
        )
        partner.user_id = self.second
        self.assertEqual(approval.review_ids.reviewer_ids, self.first)
        self.decide(approval, self.first)
        self.assertEqual(approval.state, "approved")

    def test_last_approval_and_downstream_task_roll_back_together(self):
        instance, approval = self.begin()
        self.decide(approval, self.first)
        self.worker.active = False
        before = len(instance.log_ids)
        with self.assertRaises(UserError):
            self.decide(approval, self.second, sequence=2)
        self.assertEqual(approval.state, "pending")
        self.assertEqual(
            approval.review_ids.filtered(lambda r: r.sequence == 2).status,
            "pending",
        )
        self.assertEqual(len(instance.log_ids), before)
        self.assertFalse(instance.task_ids)
        self.worker.active = True
        self.decide(approval, self.second, sequence=2)
        self.assertEqual(len(instance.task_ids), 1)

    def test_cancel_preserves_reviews_and_prevents_decision(self):
        instance, approval = self.begin()
        instance.action_cancel()
        self.assertEqual(approval.state, "cancelled")
        self.assertEqual(set(approval.review_ids.mapped("status")), {"cancel"})
        with self.assertRaises(UserError):
            self.decide(approval, self.first)

    def test_invalid_configuration_and_empty_dynamic_field(self):
        for levels in (
            [],
            [{"kind": "field", "ref": "__class__"}],
            [{"kind": "user", "ref": self.worker.id}],
        ):
            version = self.definition().version_ids
            with self.assertRaises(UserError):
                version.save_graph(approval_graph(levels), 0)
            self.assertFalse(version.node_ids)
        partner = self.env["res.partner"].create({"name": "No reviewer"})
        definition = self.published(
            approval_graph([{"kind": "field", "ref": "user_id"}]),
            model=True,
        )
        with self.assertRaises(UserError):
            self.instance(definition, res_id=partner.id)
        self.assertFalse(
            self.env["workflow.instance"].search(
                [("definition_id", "=", definition.id)],
            ),
        )
