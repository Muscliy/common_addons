from odoo import models
from odoo.exceptions import AccessError


class CommentWizard(models.TransientModel):
    _inherit = "comment.wizard"

    def add_comment(self):
        self.ensure_one()
        if self.res_model == "workflow.approval" or self.review_ids.sudo().filtered(
            lambda r: r.workflow_approval_id or r.model == "workflow.approval",
        ):
            raise AccessError(
                self.env._("流程审批请从流程监控办理，不能使用通用评论向导。"),
            )
        return super().add_comment()
