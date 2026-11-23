from odoo import Command
from odoo.exceptions import UserError

from .configuration import resolve_levels
from .scope import approval_scope


def begin_approval(instance, activation, record, actor_id: int) -> None:
    node = activation.node_id
    levels = resolve_levels(node, record)
    participants = sorted({user.id for users in levels for user in users})
    instance.write({"participant_ids": [Command.link(uid) for uid in participants]})
    with approval_scope(activation):
        approval = (
            instance.env["workflow.approval"]
            .sudo()
            .create(
                {
                    "name": node.name,
                    "node_instance_id": activation.id,
                    "requested_by": actor_id,
                },
            )
        )
        model = instance.env["ir.model"]._get_id("workflow.approval")
        definitions = []
        for index, users in enumerate(levels, 1):
            definitions.append(
                {
                    "name": f"{node.name} / {index}",
                    "model_id": model,
                    "workflow_approval_id": approval.id,
                    "workflow_candidate_ids": [Command.set(users.ids)],
                    "review_type": "individual",
                    "reviewer_id": users[0].id,
                    "company_id": instance.company_id.id,
                    "approve_sequence": True,
                    "sequence": 1000 - index,
                    "definition_domain": repr([("id", "=", approval.id)]),
                },
            )
        instance.env["tier.definition"].sudo().create(definitions)
        reviews = approval._request_reviews()
        if len(reviews) != len(levels):
            raise UserError(instance.env._("审批级次创建不完整，流程已回滚。"))
        instance._log("approval_requested", actor_id, node)
