from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import ApprovalCase, approval_graph


@tagged("post_install", "-at_install")
class TestProtection(ApprovalCase):
    def test_review_and_definition_crud_cannot_be_forged(self):
        _, approval = self.begin()
        review = approval.review_ids[:1].with_user(self.first)
        definition = review.definition_id
        for values in (
            {"status": "approved"},
            {"comment": "fake"},
            {"model": "res.partner"},
            {"res_id": 1},
            {"reviewer_ids": [Command.set(self.first.ids)]},
            {"workflow_approval_id": False},
        ):
            with self.assertRaises(AccessError):
                review.with_context(
                    skip_validation_check=True,
                    workflow_engine=True,
                    sudo=True,
                ).write(values)
        for operation in (
            review.unlink,
            review.copy,
            lambda: definition.with_user(self.manager).write({"active": False}),
            lambda: definition.with_user(self.manager).unlink(),
            approval.with_user(self.manager).restart_validation,
            approval.with_user(self.manager).request_validation,
        ):
            with self.assertRaises(AccessError):
                operation()
        with self.assertRaises(AccessError):
            self.env["tier.review"].with_user(self.first).with_context(
                default_model="workflow.approval",
                default_res_id=approval.id,
                default_definition_id=definition.id,
                default_workflow_approval_id=approval.id,
            ).create({})
        with self.assertRaises(AccessError):
            self.env["tier.definition"].with_user(self.manager).with_context(
                default_model_id=self.env["ir.model"]._get_id("workflow.approval"),
            ).create({"name": "fake"})

    def test_comment_wizard_cannot_bypass_flow_or_order(self):
        _, approval = self.begin()
        second = approval.review_ids.filtered(lambda r: r.sequence == 2)
        for model in ("workflow.approval", "res.partner"):
            wizard = (
                self.env["comment.wizard"]
                .with_user(self.second)
                .create(
                    {
                        "res_model": model,
                        "res_id": approval.id,
                        "review_ids": [Command.set(second.ids)],
                        "validate_reject": "validate",
                        "comment": "forged",
                    },
                )
            )
            with self.assertRaises(AccessError):
                wizard.add_comment()
        self.assertEqual(second.status, "waiting")
        self.assertFalse(second.comment)

    def test_business_access_is_inherited_for_decisions_and_raw_reads(self):
        partner = self.env["res.partner"].create({"name": "Restricted approval"})
        instance, approval = self.begin(model=True, res_id=partner.id)
        self.env["ir.rule"].create(
            {
                "name": "Hide approval business",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": f"[('id', '!=', {partner.id})]",
            },
        )
        for operation in (
            lambda: self.decide(approval, self.first),
            lambda: approval.with_user(self.first).read(["name"]),
            lambda: approval.review_ids.with_user(self.first).read(["comment"]),
            lambda: approval.with_user(self.first).export_data(["name"]),
            lambda: approval.review_ids.with_user(self.first).export_data(["comment"]),
        ):
            with self.assertRaises(AccessError):
                operation()
        self.assertEqual(instance.state, "running")

    def test_candidate_without_business_access_rolls_back_start(self):
        before = self.env["workflow.approval"].search([])
        partner = self.env["res.partner"].create({"name": "Candidate restriction"})
        self.env["ir.rule"].create(
            {
                "name": "Hide from candidate",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": f"[(1, '=', 1)] if user.id != {self.first.id} else [('id', '!=', {partner.id})]",
            },
        )
        with self.assertRaises(AccessError):
            self.begin(model=True, res_id=partner.id)
        self.assertEqual(self.env["workflow.approval"].search([]), before)

    def test_non_participant_cannot_read_approval_or_tier_records(self):
        _, approval = self.begin()
        for record in (
            approval,
            approval.review_ids[:1],
            approval.review_ids[:1].definition_id,
        ):
            with self.assertRaises(AccessError):
                record.with_user(self.other).read(["name"])

    def test_other_company_cannot_read_or_approve_even_as_manager(self):
        company = self.env["res.company"].create({"name": "Other approval company"})
        foreign = new_test_user(
            self.env(context={**self.env.context, "no_reset_password": True}),
            login="foreign_approval",
            groups="workflow_core.group_manager",
            company_id=company.id,
            company_ids=[Command.set(company.ids)],
        )
        definition = (
            self.env["workflow.definition"]
            .with_user(foreign)
            .with_company(company)
            .create({"name": "Foreign approval"})
        )
        version = definition.version_ids
        version.save_graph(approval_graph([{"kind": "user", "ref": foreign.id}]), 0)
        version.action_publish(1)
        instance = self.instance(definition, user=foreign)
        approval = self.env["workflow.approval"].search(
            [("instance_id", "=", instance.id)],
        )
        for record in (
            approval,
            approval.review_ids,
            approval.review_ids.definition_id,
        ):
            with self.assertRaises(AccessError):
                record.with_user(self.manager).read(["name"])
