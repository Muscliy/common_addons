from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WorkflowCategory(models.Model):
    _name = "workflow.category"
    _description = "流程类别"
    _table = "abt_workflow_category"
    _order = "sequence, name, id"

    name = fields.Char(string="类别名称", required=True)
    application_menu_id = fields.Many2one(
        "ir.ui.menu", string="所属模块", required=True,
        domain=[("parent_id", "=", False)], ondelete="restrict", index=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    _name_unique = models.Constraint(
        "UNIQUE(application_menu_id, name)", "同一模块下的流程类别名称不能重复。",
    )

    @api.constrains("application_menu_id")
    def _check_application(self):
        if any(category.application_menu_id.parent_id for category in self):
            raise ValidationError(self.env._("流程类别必须关联 Odoo 应用根菜单。"))
        for category in self:
            if self.env["workflow.definition"].sudo().with_context(active_test=False).search_count([
                ("category_id", "=", category.id),
                ("application_menu_id", "!=", category.application_menu_id.id),
            ]):
                raise ValidationError(self.env._("已有流程使用此类别，不能移动到其他模块。"))
