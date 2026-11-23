from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.workflow_project.services.activation import begin_project_task
from odoo.addons.workflow_project.services.configuration import validate_config


def prevent_uninstall(records):
    if records:
        raise UserError(records.env._("存在项目任务节点或历史，迁移后才能卸载适配器。"))


class WorkflowNode(models.Model):
    _inherit = "workflow.node"

    kind = fields.Selection(
        selection_add=[("project_task", "项目任务")],
        ondelete={"project_task": prevent_uninstall},
    )

    def _validate_config(self, kind: str, config: dict, version) -> None:
        if kind == "project_task":
            validate_config(config, version)
        else:
            super()._validate_config(kind, config, version)

    def _waits_for_input(self) -> bool:
        return self.kind == "project_task" or super()._waits_for_input()

    def _activate_input(self, instance, activation, record, actor_id: int) -> None:
        if self.kind == "project_task":
            begin_project_task(instance, activation, record, actor_id)
        else:
            super()._activate_input(instance, activation, record, actor_id)
