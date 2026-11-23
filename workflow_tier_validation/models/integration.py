from odoo import fields, models
from odoo.exceptions import AccessError

from odoo.addons.workflow_tier_validation.models.node import prevent_uninstall
from odoo.addons.workflow_tier_validation.services.configuration import (
    configured_reviewer_names,
    reviewer_fields,
)
from odoo.addons.workflow_tier_validation.services.scope import approval_scope


class WorkflowVersion(models.Model):
    _inherit = "workflow.version"

    def get_canvas(self) -> dict:
        canvas = super().get_canvas()
        canvas["approval_labels"] = configured_reviewer_names(self)
        return canvas

    def _node_options(self) -> dict:
        result = super()._node_options()
        if not self.env.user.has_group("workflow_core.group_designer"):
            return result
        group = self.env.ref("workflow_tier_validation.group_approver")
        users = (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("active", "=", True),
                    ("share", "=", False),
                    ("company_ids", "in", self.company_id.id),
                    ("all_group_ids", "in", group.id),
                ],
                order="name,id",
                limit=500,
            )
        )
        groups = self.env["res.groups"].sudo().search([], order="name,id", limit=500)
        result["approval"] = {
            "users": [{"id": u.id, "name": u.name} for u in users],
            "groups": [{"id": g.id, "name": g.name} for g in groups],
            "fields": reviewer_fields(self),
        }
        return result


class WorkflowInstance(models.Model):
    _inherit = "workflow.instance"

    state = fields.Selection(
        selection_add=[("rejected", "已拒绝")],
        ondelete={"rejected": prevent_uninstall},
    )

    def get_monitor(self) -> dict:
        canvas = super().get_monitor()
        approvals = self.env["workflow.approval"].search(
            [("instance_id", "=", self.id)],
        )
        canvas["approvals"] = []
        for approval in approvals:
            reviews = approval.review_ids.sorted("sequence")
            current = reviews.filtered(lambda r: r.status in ("pending", "waiting"))[:1]
            canvas["approvals"].append(
                {
                    "id": approval.id,
                    "name": approval.name,
                    "node": approval.node_instance_id.node_id.key,
                    "state": approval.state,
                    "reviews": [
                        {
                            "id": r.id,
                            "sequence": r.sequence,
                            "state": r.status,
                            "reviewers": r.reviewer_ids.mapped("name"),
                            "actor": r.done_by.name or "",
                            "comment": r.comment or "",
                        }
                        for r in reviews
                    ],
                    "review_id": current.id or 0,
                    "can_review": bool(
                        approval.state == "pending"
                        and self.state == "running"
                        and current.status == "pending"
                        and self.env.user in current.reviewer_ids
                        and self.env.user.has_group(
                            "workflow_tier_validation.group_approver",
                        ),
                    ),
                },
            )
        return canvas

    def action_review(
        self,
        approval_id: int,
        review_id: int,
        decision: str,
        comment: str = "",
    ) -> bool:
        self.ensure_one()
        self.check_access("read")
        if type(approval_id) is not int:
            raise AccessError(self.env._("审批单标识不正确。"))
        approval = self.env["workflow.approval"].browse(approval_id).exists()
        if not approval or approval.instance_id != self:
            raise AccessError(self.env._("审批单不属于当前流程。"))
        return approval.action_decide(decision, comment, review_id)

    def _close_open_work(self) -> None:
        super()._close_open_work()
        approvals = (
            self.env["workflow.approval"]
            .sudo()
            .search(
                [
                    ("instance_id", "in", self.ids),
                    ("state", "=", "pending"),
                ],
            )
        )
        for approval in approvals:
            with approval_scope(approval.node_instance_id):
                approval.review_ids.filtered(
                    lambda r: r.status in ("pending", "waiting"),
                ).write({"status": "cancel"})
                approval.write(
                    {"state": "cancelled", "finished_at": fields.Datetime.now()},
                )
                approval._update_counter({"review_deleted": True})
