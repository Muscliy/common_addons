from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import WorkflowCase


@tagged("post_install", "-at_install")
class TestWorkflowStartWizard(WorkflowCase):
    def _start_form(self, definition):
        forms = self.env["workflow.start.wizard"].with_user(self.manager)
        action = forms.action_open(definition.id, definition.published_version_id.id)
        return forms.browse(action["res_id"])

    def _upload(self, form):
        return (
            self.env["ir.attachment"]
            .with_user(self.manager)
            .create(
                {
                    "name": "receipt.txt",
                    "raw": b"receipt for test",
                    "res_model": form._name,
                    "res_id": form.id,
                },
            )
        )

    def test_menu_opens_an_unassigned_start_form(self):
        launcher = self.env.ref("workflow_core.open_start_wizard")
        action = launcher.with_user(self.worker).run()
        forms = self.env["workflow.start.wizard"].with_user(self.worker)
        wizard = forms.browse(action["res_id"])
        self.assertFalse(wizard.definition_id)
        self.assertEqual(action["target"], "new")

    def test_attachment_promotes_once_and_rechecks_business_record_access(self):
        definition = self.published(model=True)
        partner = self.env["res.partner"].create({"name": "Receipt business record"})
        wizard = self._start_form(definition)
        uploaded = self._upload(wizard)
        wizard.business_id = partner.id
        wizard.attachment_ids = [Command.link(uploaded.id)]
        action = wizard.action_submit()
        instance = self.env["workflow.instance"].browse(action["params"]["instance_id"])
        self.assertEqual(wizard.action_submit(), action)
        self.assertEqual(instance.with_user(self.worker).attachment_ids, uploaded)
        self.assertEqual(uploaded.with_user(self.worker).raw, b"receipt for test")
        with self.assertRaises(AccessError):
            uploaded.with_user(self.other).read(["raw"])
        self.env["ir.rule"].create(
            {
                "name": "Hide the attached workflow's business record",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": f"[('id', '!=', {partner.id})]",
            },
        )
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            uploaded.with_user(self.worker).read(["raw"])
        self.assertFalse(instance.with_user(self.worker).attachment_ids)

    def test_attaching_files_from_another_form_is_rejected(self):
        definition = self.published()
        first = self._start_form(definition)
        second = self._start_form(definition)
        uploaded = self._upload(first)
        second.attachment_ids = [Command.link(uploaded.id)]
        with self.assertRaises(AccessError):
            second.action_submit()
        self.assertEqual(uploaded.res_id, first.id)
        domain = [("definition_id", "=", definition.id)]
        self.assertFalse(self.env["workflow.instance"].search_count(domain))
