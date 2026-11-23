from odoo import api, fields, models
from odoo.exceptions import AccessError

from odoo.addons.workflow_tier_validation.services.scope import require_scope


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    workflow_approval_id = fields.Many2one(
        "workflow.approval",
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    workflow_candidate_ids = fields.Many2many(
        "res.users",
        "abt_workflow_tier_candidate_rel",
        "definition_id",
        "user_id",
        readonly=True,
    )

    def _get_tier_validation_model_names(self):
        return super()._get_tier_validation_model_names() + ["workflow.approval"]

    def _guard_values(self, vals) -> None:
        approval_id = vals.get("workflow_approval_id")
        model_id = vals.get("model_id")
        is_workflow = (
            model_id
            and self.env["ir.model"].sudo().browse(model_id).model
            == "workflow.approval"
        )
        if approval_id or is_workflow:
            if not approval_id:
                raise AccessError(self.env._("流程审批定义必须关联其审批单。"))
            require_scope(self.env["workflow.approval"].browse(approval_id))
        elif "workflow_candidate_ids" in vals:
            raise AccessError(self.env._("不能向普通审批定义写入流程快照。"))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["model_id", "workflow_approval_id"])
        for vals in vals_list:
            self._guard_values({**defaults, **vals})
        return super().create(vals_list)

    def write(self, vals):
        protected = self.sudo().filtered(
            lambda d: d.workflow_approval_id or d.model == "workflow.approval",
        )
        if protected:
            require_scope(protected.workflow_approval_id)
            raise AccessError(self.env._("流程审批定义快照不可修改。"))
        self._guard_values(vals)
        return super().write(vals)

    def unlink(self):
        if self.sudo().filtered(
            lambda d: d.workflow_approval_id or d.model == "workflow.approval",
        ):
            raise AccessError(self.env._("流程审批定义快照不可删除。"))
        return super().unlink()

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if not result and operation == "read" and not self.env.su:
            for approval in self.sudo().workflow_approval_id.with_env(self.env):
                if not approval.has_access("read"):
                    return self, lambda: AccessError(self.env._("不能访问此审批快照。"))
        return result

    def _read_format(self, fnames, load="_classic_read"):
        self.check_access("read")
        return super()._read_format(fnames, load)

    def export_data(self, fields_to_export):
        self.check_access("read")
        return super().export_data(fields_to_export)
