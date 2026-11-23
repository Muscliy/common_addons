from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_tier_validation.services.scope import (
    require_activation,
    require_scope,
)


class WorkflowApproval(models.Model):
    _name = "workflow.approval"
    _inherit = ["tier.validation", "workflow.runtime.record"]
    _description = "流程审批单"
    _table = "abt_workflow_approval"
    _order = "id desc"
    _state_from = ["pending"]
    _state_to = ["approved"]
    _cancel_state = "cancelled"

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
    requested_by = fields.Many2one("res.users", required=True, ondelete="restrict")
    state = fields.Selection(
        [
            ("pending", "待审批"),
            ("approved", "已通过"),
            ("rejected", "已拒绝"),
            ("cancelled", "已取消"),
        ],
        default="pending",
        required=True,
    )
    finished_at = fields.Datetime(readonly=True)
    _activation_unique = models.Constraint(
        "UNIQUE(node_instance_id)",
        "本次节点激活已有审批单。",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            require_activation(
                self.env["workflow.node.instance"].browse(vals.get("node_instance_id")),
            )
        return super().create(vals_list)

    def write(self, vals):
        require_scope(self)
        return super().write(vals)

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if result or operation != "read" or self.env.su:
            return result
        for instance in self.sudo().instance_id.with_env(self.env):
            try:
                instance.check_access("read")
                instance._business_record()
            except (AccessError, UserError):
                return self, lambda: AccessError(
                    self.env._("不能访问审批关联的流程或业务单据。"),
                )
        return None

    def evaluate_tier(self, tier):
        self.ensure_one()
        self.check_access("read")
        return tier.sudo().workflow_approval_id == self.sudo()

    def _request_reviews(self):
        require_scope(self)
        return super().request_validation()

    def request_validation(self):
        raise AccessError(self.env._("审批只能由流程节点启动。"))

    def restart_validation(self):
        raise AccessError(self.env._("流程审批历史不可重置或删除。"))

    def validate_tier(self):
        return self.action_decide("approve", "")

    def reject_tier(self):
        return self.action_decide("reject", "")

    def _validate_tier(self, tiers=False):
        require_scope(self)
        return super()._validate_tier(tiers)

    def _rejected_tier(self, tiers=False):
        require_scope(self)
        return super()._rejected_tier(tiers)

    def _tier_validation_check_write_allowed(self, vals):
        require_scope(self)

    def _allow_to_remove_reviews(self, values):
        return False

    def action_monitor(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return self.instance_id.action_monitor()

    def _read_format(self, fnames, load="_classic_read"):
        self.check_access("read")
        return super()._read_format(fnames, load)

    def export_data(self, fields_to_export):
        self.check_access("read")
        return super().export_data(fields_to_export)
