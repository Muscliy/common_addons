from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ApprovalCase
from odoo.addons.workflow_core.tests.common import parallel_graph


@tagged("post_install", "-at_install")
class TestParallelApproval(ApprovalCase):
    def begin_parallel(self, both=True):
        graph = parallel_graph(self.worker.id)
        for key, user in (("left", self.first), ("right", self.second)):
            if key == "right" and not both:
                continue
            node = next(n for n in graph["nodes"] if n["id"] == key)
            node["type"] = "approval"
            node["data"].update(
                assignee_id=0,
                config={"levels": [{"kind": "user", "ref": user.id}]},
            )
        definition = self.published(graph)
        instance = self.instance(definition)
        approvals = self.env["workflow.approval"].search(
            [("instance_id", "=", instance.id)],
        )
        return (
            instance,
            approvals.filtered(lambda a: a.name == "left"),
            approvals.filtered(lambda a: a.name == "right"),
        )

    def test_parallel_approvals_wait_for_both_before_creating_successor(self):
        instance, left, right = self.begin_parallel()
        self.decide(left, self.first)
        self.assertFalse(instance.task_ids)
        self.assertEqual(right.state, "pending")
        self.decide(right, self.second)
        self.assertEqual(instance.task_ids.name, "after")
        self.decide(right, self.second)
        self.assertEqual(len(instance.task_ids), 1)
        instance.task_ids.action_complete()
        self.assertEqual(instance.state, "done")

    def test_rejection_cancels_sibling_approval_and_all_open_tokens(self):
        instance, left, right = self.begin_parallel()
        self.decide(left, self.first, decision="reject", comment="资料不符")
        self.assertEqual(instance.state, "rejected")
        self.assertEqual(left.state, "rejected")
        self.assertEqual(right.state, "cancelled")
        self.assertEqual(right.review_ids.status, "cancel")
        self.assertFalse(
            instance.token_ids.filtered(lambda t: t.state in ("active", "waiting")),
        )
        self.assertFalse(
            instance.node_instance_ids.filtered(lambda a: a.state == "waiting"),
        )
        self.assertEqual(left.review_ids.comment, "资料不符")
        with self.assertRaises(UserError):
            self.decide(right, self.second)
        self.assertFalse(instance.task_ids)

    def test_rejection_keeps_finished_sibling_and_cancels_waiting_join(self):
        instance, left, _ = self.begin_parallel(both=False)
        task = instance.task_ids
        task.action_complete("先完成")
        self.decide(left, self.first, decision="reject", comment="需补资料")
        self.assertEqual(task.state, "done")
        join = instance.node_instance_ids.filtered(lambda a: a.node_id.kind == "join")
        self.assertEqual(join.state, "cancelled")
        self.assertEqual(len(instance.task_ids), 1)

    def test_rejection_cancels_pending_human_sibling(self):
        instance, left, _ = self.begin_parallel(both=False)
        task = instance.task_ids
        self.decide(left, self.first, decision="reject", comment="拒绝")
        self.assertEqual(task.state, "cancelled")
        with self.assertRaises(UserError):
            task.action_complete()

    def test_cancel_closes_both_approvals_and_preserves_reviews(self):
        instance, left, right = self.begin_parallel()
        reviews = (left | right).review_ids
        instance.action_cancel()
        self.assertEqual(set((left | right).mapped("state")), {"cancelled"})
        self.assertEqual(set(reviews.mapped("status")), {"cancel"})
        self.assertEqual((left | right).review_ids, reviews)
        self.assertFalse(
            instance.token_ids.filtered(lambda t: t.state in ("active", "waiting")),
        )
