from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.workflow_tier_validation.services.configuration import validate_config
from odoo.addons.workflow_tier_validation.services.snapshot import begin_approval


def prevent_uninstall(records):
    if records:
        raise UserError(
            records.env._(
                "仍有审批节点或审批历史，需先完成数据迁移才能卸载审批适配器。",
            ),
        )


class WorkflowNode(models.Model):
    _inherit = "workflow.node"

    kind = fields.Selection(
        selection_add=[("approval", "审批")],
        ondelete={"approval": prevent_uninstall},
    )

    def _validate_config(self, kind: str, config: dict, version) -> None:
        if kind == "approval":
            validate_config(config, version)
        else:
            super()._validate_config(kind, config, version)

    def _waits_for_input(self) -> bool:
        return self.kind == "approval" or super()._waits_for_input()

    def _activate_input(self, instance, activation, record, actor_id: int) -> None:
        if self.kind == "approval":
            begin_approval(instance, activation, record, actor_id)
        else:
            super()._activate_input(instance, activation, record, actor_id)


class WorkflowNodeInstance(models.Model):
    _inherit = "workflow.node.instance"

    state = fields.Selection(
        selection_add=[("rejected", "已拒绝")],
        ondelete={"rejected": prevent_uninstall},
    )
