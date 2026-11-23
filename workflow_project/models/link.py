from odoo import fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_project.services.synchronization import decide


class WorkflowProjectLink(models.Model):
    _name = "workflow.project.link"
    _inherit = "workflow.runtime.record"
    _description = "流程项目任务关联"
    _table = "abt_workflow_project_link"
    _order = "id desc"

    name = fields.Char(required=True)
    node_instance_id = fields.Many2one(
        "workflow.node.instance",
        required=True,
        ondelete="restrict",
        index=True,
    )
    instance_id = fields.Many2one(
        related="node_instance_id.instance_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="instance_id.company_id",
        store=True,
        index=True,
    )
    project_task_id = fields.Many2one(
        "project.task",
        required=True,
        ondelete="restrict",
        index=True,
    )
    assignee_ids = fields.Many2many(
        "res.users",
        "abt_workflow_project_user_rel",
        "link_id",
        "user_id",
        readonly=True,
    )
    state = fields.Selection(
        [("pending", "待办理"), ("done", "已完成"), ("cancelled", "已取消")],
        required=True,
        default="pending",
    )
    completed_by = fields.Many2one("res.users", readonly=True)
    finished_at = fields.Datetime(readonly=True)
    comment = fields.Text(readonly=True)
    _activation_unique = models.Constraint(
        "UNIQUE(node_instance_id)",
        "本次激活已有项目任务。",
    )
    _task_unique = models.Constraint(
        "UNIQUE(project_task_id)",
        "项目任务已有流程关联。",
    )

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if result or operation != "read" or self.env.su:
            return result
        for link in self.sudo():
            try:
                instance = link.instance_id.with_env(self.env)
                instance.check_access("read")
                instance._business_record()
                link.project_task_id.with_env(self.env).check_access("read")
            except (AccessError, UserError):
                return self, lambda: AccessError(
                    self.env._("不能访问关联的流程或项目任务。"),
                )
        return None

    def _read_format(self, fnames, load="_classic_read"):
        self.check_access("read")
        return super()._read_format(fnames, load)

    def export_data(self, fields_to_export):
        self.check_access("read")
        return super().export_data(fields_to_export)

    def action_decide(self, decision: str, comment: str = "") -> bool:
        self.ensure_one()
        return decide(self, decision, comment)

    def action_open(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "res_id": self.project_task_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return self.instance_id.action_monitor()
