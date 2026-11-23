from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class WorkflowInstance(models.Model):
    _inherit = "workflow.instance"

    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="发起附件",
        compute="_compute_flow_attachments",
    )

    def _can_read_workflow_attachments(self) -> bool:
        try:
            self.check_access("read")
            self._business_record()
        except (AccessError, UserError):
            return False
        return True

    @api.depends_context("uid", "company")
    def _compute_flow_attachments(self):
        attachments = self.env["ir.attachment"]
        allowed = self.filtered(
            lambda instance: instance._can_read_workflow_attachments(),
        )
        by_instance = attachments.search(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", allowed.ids),
            ],
        ).grouped("res_id")
        for instance in self:
            instance.attachment_ids = by_instance.get(instance.id, attachments)

    def get_monitor(self) -> dict:
        canvas = super().get_monitor()
        canvas["attachments"] = [
            {"id": file.id, "name": file.name} for file in self.attachment_ids
        ]
        return canvas


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _inaccessible_comodel_records(self, model_and_ids, operation):
        yield from super()._inaccessible_comodel_records(model_and_ids, operation)
        if self.env.su or operation != "read":
            return
        ids = model_and_ids.get("workflow.instance", ())
        for instance in self.env["workflow.instance"].browse(ids).exists():
            if not instance._can_read_workflow_attachments():
                yield "workflow.instance", instance.id
