from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_core.services.access import (
    business_record,
    lock_record,
    require_group,
    require_internal_write,
)


class WorkflowRuntimeRecord(models.AbstractModel):
    _name = "workflow.runtime.record"
    _description = "流程运行数据写保护"

    @api.model_create_multi
    def create(self, vals_list):
        require_internal_write(self)
        return super().create(vals_list)

    def write(self, vals):
        require_internal_write(self)
        return super().write(vals)

    def unlink(self):
        # 即使管理员也通过取消保留审计。不提供运行数据清除入口。
        raise AccessError(self.env._("运行记录和执行历史不可删除。"))


class WorkflowInstance(models.Model):
    _name = "workflow.instance"
    _inherit = "workflow.runtime.record"
    _description = "流程实例"
    _table = "abt_workflow_instance"
    _order = "id desc"

    name = fields.Char(required=True)
    version_id = fields.Many2one(
        "workflow.version",
        required=True,
        ondelete="restrict",
        index=True,
    )
    definition_id = fields.Many2one(
        related="version_id.definition_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="version_id.company_id",
        store=True,
        index=True,
    )
    starter_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        index=True,
    )
    participant_ids = fields.Many2many(
        "res.users",
        "abt_workflow_instance_user_rel",
        "instance_id",
        "user_id",
    )
    res_id = fields.Integer(string="业务记录ID")
    request_key = fields.Char(required=True)
    state = fields.Selection(
        [("running", "进行中"), ("done", "已完成"), ("cancelled", "已取消")],
        default="running",
        required=True,
        index=True,
    )
    finished_at = fields.Datetime(readonly=True)
    node_instance_ids = fields.One2many("workflow.node.instance", "instance_id")
    task_ids = fields.One2many("workflow.task", "instance_id")
    log_ids = fields.One2many("workflow.execution.log", "instance_id")
    token_ids = fields.One2many("workflow.token", "instance_id")
    _request_unique = models.Constraint(
        "UNIQUE(definition_id, starter_id, request_key)",
        "请求已处理。",
    )

    def _business_record(self):
        return business_record(self.version_id.definition_id, self.res_id)

    def action_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        self._business_record()
        return {
            "type": "ir.actions.client",
            "tag": "workflow_core.monitor",
            "name": self.name,
            "params": {"instance_id": self.id},
        }

    def action_business_record(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        record = self._business_record()
        if record is None:
            raise UserError(self.env._("此流程没有关联业务单据。"))
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def get_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        self._business_record()
        canvas = self.version_id.get_canvas()
        canvas.update(
            {
                "title": self.name,
                "can_edit": False,
                "can_publish": False,
                "can_start": False,
                "instance_id": self.id,
                "instance_state": self.state,
                "instance_starter": self.starter_id.name,
                "executions": [
                    {
                        "id": n.id,
                        "node": n.node_id.key,
                        "state": n.state,
                        "started_at": fields.Datetime.to_string(n.started_at),
                        "finished_at": fields.Datetime.to_string(n.finished_at),
                    }
                    for n in self.node_instance_ids
                ],
                "tokens": [
                    {
                        "id": t.id,
                        "node": t.node_id.key,
                        "state": t.state,
                        "parent_id": t.parent_id.id or 0,
                    }
                    for t in self.token_ids
                ],
                "tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "state": t.state,
                        "assignee": t.assignee_id.name,
                        "activation_id": t.node_instance_id.id,
                        "actor": t.completed_by.name or "",
                        "can_complete": t.state == "pending"
                        and t.assignee_id == self.env.user,
                    }
                    for t in self.task_ids
                ],
                "logs": [
                    {
                        "id": log.id,
                        "node": log.node_id.name or "",
                        "event": log.event,
                        "actor": log.actor_id.name,
                        "at": fields.Datetime.to_string(log.create_date),
                        "comment": log.comment or "",
                    }
                    for log in self.log_ids
                ],
            },
        )
        return canvas

    def action_cancel(self) -> bool:
        self.ensure_one()
        self.check_access("read")
        require_group(self, "group_executor")
        if self.starter_id != self.env.user and not self.env.user.has_group(
            "workflow_core.group_manager",
        ):
            raise AccessError(self.env._("只有发起人或工作流管理员可以取消流程。"))
        self._business_record()
        with self.env.cr.savepoint():
            lock_record(self)
            if self.state == "cancelled":
                return True
            if self.state != "running":
                raise UserError(self.env._("已结束的流程不能取消。"))
            elevated = self.sudo()
            elevated._close_open_work()
            elevated.write({"state": "cancelled", "finished_at": fields.Datetime.now()})
            elevated._log("cancelled", self.env.uid)
        return True

    def _close_open_work(self) -> None:
        require_internal_write(self)
        self.task_ids.filtered(lambda t: t.state == "pending").write(
            {"state": "cancelled"},
        )
        self.node_instance_ids.filtered(lambda n: n.state == "waiting").write(
            {
                "state": "cancelled",
                "finished_at": fields.Datetime.now(),
            },
        )
        self.token_ids.filtered(lambda t: t.state in ("active", "waiting")).write(
            {"state": "cancelled"},
        )

    def _log(self, event: str, actor_id: int, node=None, comment: str = "") -> None:
        self.env["workflow.execution.log"].sudo().create(
            {
                "instance_id": self.id,
                "node_id": node.id if node else False,
                "event": event,
                "actor_id": actor_id,
                "comment": comment,
            },
        )


class WorkflowNodeInstance(models.Model):
    _name = "workflow.node.instance"
    _inherit = "workflow.runtime.record"
    _description = "节点执行记录"
    _table = "abt_workflow_node_instance"

    instance_id = fields.Many2one(
        "workflow.instance",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="instance_id.company_id",
        store=True,
        index=True,
    )
    node_id = fields.Many2one("workflow.node", required=True, ondelete="restrict")
    token_id = fields.Many2one("workflow.token", ondelete="restrict", index=True)
    state = fields.Selection(
        [("waiting", "等待办理"), ("done", "已完成"), ("cancelled", "已取消")],
        required=True,
    )
    started_at = fields.Datetime(default=fields.Datetime.now)
    finished_at = fields.Datetime()
    _activation_unique = models.Constraint(
        "UNIQUE(instance_id, node_id)",
        "节点已激活。",
    )


class WorkflowExecutionLog(models.Model):
    _name = "workflow.execution.log"
    _inherit = "workflow.runtime.record"
    _description = "流程执行日志"
    _table = "abt_workflow_execution_log"
    _order = "id"

    instance_id = fields.Many2one(
        "workflow.instance",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="instance_id.company_id",
        store=True,
        index=True,
    )
    node_id = fields.Many2one("workflow.node", ondelete="restrict")
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    event = fields.Char(required=True)
    comment = fields.Text()

    def write(self, vals):
        raise AccessError(self.env._("执行日志只能追加。"))
