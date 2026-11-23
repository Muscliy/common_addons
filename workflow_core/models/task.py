from odoo import fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.workflow_core.services.access import lock_record, require_group
from odoo.addons.workflow_core.services.engine import advance


class WorkflowTask(models.Model):
    _name = "workflow.task"
    _inherit = "workflow.runtime.record"
    _description = "工作流待办"
    _table = "abt_workflow_task"
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
    assignee_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        index=True,
    )
    state = fields.Selection(
        [("pending", "待办理"), ("done", "已办理"), ("cancelled", "已取消")],
        default="pending",
        required=True,
        index=True,
    )
    comment = fields.Text(readonly=True)
    completed_by = fields.Many2one("res.users", readonly=True)
    completed_at = fields.Datetime(readonly=True)
    _task_unique = models.Constraint("UNIQUE(node_instance_id)", "节点任务已创建。")

    def action_complete(self, comment: str = "") -> bool:
        self.ensure_one()
        self.check_access("read")
        require_group(self, "group_executor")
        if not isinstance(comment, str) or len(comment) > 4000:
            raise ValidationError(self.env._("办理意见不能超过4000个字符。"))
        if self.assignee_id != self.env.user:
            raise AccessError(self.env._("只有任务负责人可以办理。"))
        record = self.instance_id._business_record()
        with self.env.cr.savepoint():
            lock_record(self.instance_id)
            lock_record(self)
            if self.state == "done":
                return True
            if self.state != "pending" or self.instance_id.state != "running":
                raise UserError(self.env._("任务已取消或流程已结束。"))
            self.sudo().write(
                {
                    "state": "done",
                    "comment": comment,
                    "completed_by": self.env.uid,
                    "completed_at": fields.Datetime.now(),
                },
            )
            activation = self.node_instance_id.sudo()
            activation.write({"state": "done", "finished_at": fields.Datetime.now()})
            instance = self.instance_id.sudo()
            instance._log("task_completed", self.env.uid, activation.node_id, comment)
            advance(instance, activation.node_id, record, self.env.uid)
        return True

    def action_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return self.instance_id.action_monitor()
