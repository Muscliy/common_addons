from odoo import fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.workflow_core.services.access import lock_record
from odoo.addons.workflow_core.services.engine import advance
from odoo.addons.workflow_tier_validation.services.configuration import eligible
from odoo.addons.workflow_tier_validation.services.scope import approval_scope


class WorkflowApproval(models.Model):
    _inherit = "workflow.approval"

    def _prepare_tier_review_vals(self, definition, sequence):
        return {
            **super()._prepare_tier_review_vals(definition, sequence),
            "workflow_approval_id": self.id,
        }

    def action_decide(
        self,
        decision: str,
        comment: str = "",
        review_id: int = 0,
    ) -> bool:
        self.ensure_one()
        self.check_access("read")
        if not self.env.user.has_group("workflow_tier_validation.group_approver"):
            raise AccessError(self.env._("没有流程审批权限。"))
        if (
            decision not in ("approve", "reject")
            or not isinstance(comment, str)
            or len(comment) > 4000
            or type(review_id) is not int
        ):
            raise ValidationError(self.env._("审批操作、意见或级次标识不正确。"))
        if decision == "reject" and not comment.strip():
            raise ValidationError(self.env._("请填写拒绝意见。"))
        instance = self.instance_id
        record = instance._business_record()
        if not eligible(self.env.user, self.company_id):
            raise AccessError(self.env._("当前用户已失去审批资格。"))
        with self.env.cr.savepoint():
            lock_record(instance)
            lock_record(self)
            review = self._review_for_decision(review_id, decision)
            if review.status in ("approved", "rejected"):
                return True
            if instance.state != "running" or self.state != "pending":
                raise UserError(self.env._("流程或审批已结束。"))
            with approval_scope(self.node_instance_id):
                approval, tier = self.sudo(), review.sudo()
                tier.write({"comment": comment})
                if decision == "approve":
                    approval._validate_tier(tier)
                else:
                    approval._rejected_tier(tier)
                approval.review_ids._update_review_status()
                approval._update_counter({"review_deleted": True})
                instance.sudo()._log(
                    "approval_approved"
                    if decision == "approve"
                    else "approval_rejected",
                    self.env.uid,
                    self.node_instance_id.node_id,
                    comment,
                )
                approval._sync_result(record, self.env.uid)
        return True

    def _review_for_decision(self, review_id: int, decision: str):
        reviews = self.review_ids
        if review_id:
            review = reviews.filtered(lambda r: r.id == review_id)
        else:
            # UI always sends an immutable review id, so a retry cannot approve the next level.
            raise ValidationError(self.env._("请指定当前审批级次。"))
        if not review or self.env.user not in review.reviewer_ids:
            raise AccessError(self.env._("你不是此级次的审批人员。"))
        expected = "approved" if decision == "approve" else "rejected"
        if review.status in ("approved", "rejected"):
            if review.done_by == self.env.user and review.status == expected:
                return review
            raise UserError(self.env._("此级次已由其他操作处理。"))
        current = reviews.filtered(lambda r: r.status in ("waiting", "pending")).sorted(
            "sequence",
        )[:1]
        if review != current or review.status != "pending":
            raise AccessError(self.env._("尚未轮到此级次审批。"))
        return review

    def _sync_result(self, record, actor_id: int) -> None:
        if self.state != "pending":
            return
        status = self.validation_status
        if status not in ("validated", "rejected"):
            return
        rejected = status == "rejected"
        self.write(
            {
                "state": "rejected" if rejected else "approved",
                "finished_at": fields.Datetime.now(),
            },
        )
        activation, instance = self.node_instance_id.sudo(), self.instance_id.sudo()
        activation.write(
            {
                "state": "rejected" if rejected else "done",
                "finished_at": fields.Datetime.now(),
            },
        )
        if rejected:
            instance._close_open_work()
            instance.write({"state": "rejected", "finished_at": fields.Datetime.now()})
        else:
            advance(instance, activation.node_id, record, actor_id)
