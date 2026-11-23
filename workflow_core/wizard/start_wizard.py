from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_core.services.access import lock_record, require_group


class WorkflowStartWizard(models.TransientModel):
    _name = "workflow.start.wizard"
    _description = "发起工作流"
    _table = "abt_workflow_start_wizard"

    definition_id = fields.Many2one(
        "workflow.definition",
        string="流程模板",
        domain="[('active', '=', True), ('published_version_id', '!=', False)]",
    )
    expected_version_id = fields.Integer(readonly=True)
    business_model = fields.Char(related="definition_id.model_id.model")
    business_id = fields.Many2oneReference(
        string="业务单据",
        model_field="business_model",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "abt_workflow_start_wizard_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="附件",
    )

    @api.constrains("definition_id")
    def _check_definition_access(self):
        self.definition_id.check_access("read")

    @api.onchange("definition_id")
    def _onchange_definition_id(self):
        self.business_id = False

    @api.model
    def action_open(self, definition_id=0, expected_version_id=0):
        require_group(self, "group_executor")
        wizard = self.create(
            {
                "definition_id": definition_id or False,
                "expected_version_id": expected_version_id,
            },
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("发起流程"),
            "res_model": self._name,
            "res_id": wizard.id,
            "target": "new",
            "views": [(self.env.ref("workflow_core.start_wizard_form").id, "form")],
        }

    def action_submit(self):
        self.ensure_one()
        self.check_access("write")
        require_group(self, "group_executor")
        with self.env.cr.savepoint():
            lock_record(self)
            definition = self.definition_id
            if not definition:
                raise UserError(self.env._("请选择要发起的流程模板。"))
            request_key = f"workflow-start-wizard:{self.id}"
            existing = (
                self.env["workflow.instance"]
                .sudo()
                .search(
                    [
                        ("starter_id", "=", self.env.uid),
                        ("request_key", "=", request_key),
                    ],
                    limit=1,
                )
            )
            if existing and existing.definition_id.id != definition.id:
                raise UserError(self.env._("本次流程已发起。请从菜单重新打开表单。"))
            files = self.env["ir.attachment"]
            if not existing:
                files = self.sudo().attachment_ids.exists()
                if any(
                    file.create_uid.id != self.env.uid
                    or file.res_model != self._name
                    or file.res_id != self.id
                    or file.type != "binary"
                    or file.res_field
                    for file in files
                ):
                    message = self.env._("请重新上传附件，只能提交本次上传的文件。")
                    raise AccessError(message)
            action = definition.action_start(
                self.business_id or 0,
                request_key,
                self.expected_version_id,
            )
            instance_id = action["params"]["instance_id"]
            if files:
                files.write(
                    {
                        "res_model": "workflow.instance",
                        "res_id": instance_id,
                        "company_id": definition.company_id.id,
                        "public": False,
                        "access_token": False,
                    },
                )
            return action
