from odoo import fields, models


class WorkflowGroup(models.Model):
    _name = "workflow.group"
    _description = "流程分组"
    _table = "abt_workflow_group"
    _order = "sequence, name, id"

    name = fields.Char(string="分组名称", required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
