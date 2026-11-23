from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_project.services.scope import is_syncing
from odoo.addons.workflow_project.services.structure import guard_task_targets
from odoo.addons.workflow_project.services.synchronization import (
    authorize,
    finish,
    lock_links,
)

STRUCTURE = {
    "user_ids",
    "project_id",
    "company_id",
    "parent_id",
    "child_ids",
    "depend_on_ids",
    "dependent_ids",
    "recurring_task",
    "recurrence_id",
    "is_template",
}


class ProjectTask(models.Model):
    _inherit = "project.task"

    workflow_can_open = fields.Boolean(compute="_compute_workflow_can_open")
    workflow_status = fields.Char(compute="_compute_workflow_can_open")

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(
            ["parent_id", "child_ids", "depend_on_ids", "dependent_ids"],
        )
        for vals in vals_list:
            guard_task_targets(self, {**defaults, **vals})
        return super().create(vals_list)

    def _workflow_links(self):
        return (
            self.env["workflow.project.link"]
            .sudo()
            .search([("project_task_id", "in", self.ids)])
        )

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_workflow_can_open(self):
        visible = (
            self._workflow_links()
            .with_env(self.env)
            .filtered(lambda link: link.has_access("read"))
        )
        for task in self:
            task.workflow_can_open = task in visible.project_task_id
            link = visible.filtered(lambda item: item.project_task_id == task)
            task.workflow_status = (
                dict(
                    link.instance_id._fields["state"]._description_selection(self.env),
                ).get(link.instance_id.state, "")
                if link
                else ""
            )

    def action_workflow_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        link = self._workflow_links().with_env(self.env)
        if not link:
            raise UserError(self.env._("此任务没有关联工作流。"))
        return link.action_monitor()

    def write(self, vals):
        guard_task_targets(self, vals)
        links = self._workflow_links()
        if not links:
            return super().write(vals)
        if STRUCTURE & vals.keys() or (
            vals.get("active") is False
            and links.filtered(lambda link: link.state == "pending")
        ):
            raise AccessError(
                self.env._("已关联工作流的项目、负责人和任务结构不能修改。"),
            )
        normal = links.filtered(lambda link: not is_syncing(link))
        if "state" not in vals or not normal:
            return super().write(vals)
        with self.env.cr.savepoint():
            lock_links(normal)
            changed = normal.filtered(
                lambda link: link.project_task_id.state != vals["state"],
            )
            for link in changed.with_user(self.env.uid):
                authorize(link)
            result = super().write(vals)
            for link in changed.with_user(self.env.uid):
                finish(link, vals["state"])
            return result

    def unlink(self):
        if self._workflow_links():
            raise AccessError(self.env._("关联项目任务保留流程历史，不能删除。"))
        return super().unlink()
