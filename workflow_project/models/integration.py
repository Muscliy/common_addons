from odoo import api, models

from odoo.addons.workflow_project.services.configuration import eligible
from odoo.addons.workflow_project.services.synchronization import close_links


class WorkflowDefinition(models.Model):
    _inherit = "workflow.definition"

    def _allowed_business_models(self) -> set[str]:
        return super()._allowed_business_models() | {"project.task"}


class WorkflowVersion(models.Model):
    _inherit = "workflow.version"

    def _node_options(self) -> dict:
        result = super()._node_options()
        if not self.definition_id._can_manage():
            return result
        projects = (
            self.env["project.project"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("is_template", "=", False),
                ],
                limit=500,
                order="name,id",
            )
            if self.env["project.project"].has_access("read")
            else self.env["project.project"]
        )
        users = (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("active", "=", True),
                    ("share", "=", False),
                    ("company_ids", "in", self.company_id.id),
                ],
                limit=500,
                order="name,id",
            )
            .filtered(lambda u: eligible(u, self.company_id))
        )
        result["project_task"] = {
            "projects": [{"id": p.id, "name": p.name} for p in projects],
            "users": [{"id": u.id, "name": u.name} for u in users],
            "can_link_business": self.definition_id.model_id.sudo().model
            == "project.task",
        }
        return result


class WorkflowInstance(models.Model):
    _inherit = "workflow.instance"

    def write(self, vals):
        result = super().write(vals)
        if "state" in vals:
            links = (
                self.env["workflow.project.link"]
                .sudo()
                .search([("instance_id", "in", self.ids)])
            )
            links.project_task_id.invalidate_recordset(
                ["workflow_status", "workflow_can_open"],
            )
        return result

    def get_monitor(self) -> dict:
        canvas = super().get_monitor()
        links = self.env["workflow.project.link"].search(
            [("instance_id", "=", self.id)],
        )
        canvas["project_tasks"] = []
        for link in links.filtered(lambda link: link.has_access("read")):
            task = link.project_task_id
            canvas["project_tasks"].append(
                {
                    "id": link.id,
                    "activation_id": link.node_instance_id.id,
                    "name": link.name,
                    "state": link.state,
                    "task_name": task.name,
                    "task_state": dict(
                        task._fields["state"]._description_selection(self.env),
                    )[task.state],
                    "assignees": link.assignee_ids.mapped("name"),
                    "comment": link.comment or "",
                    "can_complete": link.state == "pending"
                    and self.state == "running"
                    and self.env.user in link.assignee_ids
                    and eligible(self.env.user, self.company_id)
                    and task.has_access("write"),
                },
            )
        return canvas

    @api.model
    def action_todo_approvals(self) -> dict:
        action_name = "workflow_tier_validation.my_approvals"
        action = self.env.ref(action_name, raise_if_not_found=False)
        approver_group = "workflow_tier_validation.group_approver"
        if action and self.env.user.has_group(approver_group):
            return self.env["ir.actions.actions"]._for_xml_id(action_name)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "message": self.env._("当前没有可查看的流程审批。"),
            },
        }

    def _close_open_work(self) -> None:
        super()._close_open_work()
        close_links(self)
