from odoo import api, fields, models
from odoo.exceptions import AccessError

from odoo.addons.workflow_tier_validation.services.scope import require_scope


class TierReview(models.Model):
    _inherit = "tier.review"

    workflow_approval_id = fields.Many2one(
        "workflow.approval",
        readonly=True,
        ondelete="restrict",
        index=True,
    )

    def _guard_values(self, vals) -> None:
        definition = (
            self.env["tier.definition"]
            .sudo()
            .browse(vals.get("definition_id"))
            .exists()
        )
        approval_id = vals.get("workflow_approval_id")
        protected = (
            vals.get("model") == "workflow.approval"
            or approval_id
            or definition.workflow_approval_id
        )
        if not protected:
            return
        approval = self.env["workflow.approval"].sudo().browse(approval_id).exists()
        if (
            not approval
            or vals.get("model") != "workflow.approval"
            or vals.get("res_id") != approval.id
            or definition.workflow_approval_id != approval
        ):
            raise AccessError(self.env._("审批记录与快照、流程审批单不匹配。"))
        require_scope(approval)

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(
            ["model", "res_id", "definition_id", "workflow_approval_id"],
        )
        for vals in vals_list:
            self._guard_values({**defaults, **vals})
        return super().create(vals_list)

    def write(self, vals):
        protected = self.sudo().filtered(
            lambda r: r.workflow_approval_id or r.model == "workflow.approval",
        )
        if protected:
            require_scope(protected.workflow_approval_id)
            if {
                "workflow_approval_id",
                "model",
                "res_id",
                "definition_id",
                "sequence",
                "reviewer_ids",
            } & vals.keys():
                raise AccessError(self.env._("审批快照的关联和候选人不可修改。"))
        if {"workflow_approval_id", "model", "res_id", "definition_id"} & vals.keys():
            for review in self.sudo():
                self._guard_values(
                    {
                        "model": review.model,
                        "res_id": review.res_id,
                        "definition_id": review.definition_id.id,
                        "workflow_approval_id": review.workflow_approval_id.id,
                        **vals,
                    },
                )
        return super().write(vals)

    def unlink(self):
        if self.sudo().filtered(
            lambda r: r.workflow_approval_id or r.model == "workflow.approval",
        ):
            raise AccessError(self.env._("流程审批记录不可删除。"))
        return super().unlink()

    def _get_reviewers(self):
        if self.sudo().workflow_approval_id:
            return self.definition_id.workflow_candidate_ids
        return super()._get_reviewers()

    def _check_access(self, operation):
        result = super()._check_access(operation)
        if not result and operation == "read" and not self.env.su:
            for approval in self.sudo().workflow_approval_id.with_env(self.env):
                if not approval.has_access("read"):
                    return self, lambda: AccessError(
                        self.env._("不能访问此流程审批记录。"),
                    )
        return result

    def _update_review_status(self):
        protected = self.filtered("workflow_approval_id")
        # 原生用户计数器会在读取时提升 pending。流程审批的状态推进仅在授权事务内进行。
        ordinary = self - protected
        if ordinary:
            super(TierReview, ordinary)._update_review_status()
        if protected:
            try:
                require_scope(protected.workflow_approval_id)
            except AccessError:
                return
            super(TierReview, protected)._update_review_status()

    def _read_format(self, fnames, load="_classic_read"):
        self.check_access("read")
        return super()._read_format(fnames, load)

    def export_data(self, fields_to_export):
        self.check_access("read")
        return super().export_data(fields_to_export)
