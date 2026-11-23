from odoo import fields
from odoo.exceptions import UserError


def root_token(instance, node):
    return (
        instance.env["workflow.token"]
        .sudo()
        .create(
            {"instance_id": instance.id, "key": "root", "node_id": node.id},
        )
    )


def activation_token(instance, activation):
    token = activation.token_id
    if not token:
        # Pre-token published versions and in-flight tasks remain untouched until resumed.
        token = root_token(instance, activation.node_id)
        activation.write({"token_id": token.id})
    token.write({"state": "active"})
    return token


def split(instance, activation, token, edges, actor_id: int) -> list:
    token.write({"state": "waiting"})
    jobs = []
    for edge in edges:
        child = (
            instance.env["workflow.token"]
            .sudo()
            .create(
                {
                    "instance_id": instance.id,
                    "key": f"{activation.id}:{edge.id}",
                    "node_id": edge.target_id.id,
                    "parent_id": token.id,
                    "fork_activation_id": activation.id,
                    "branch_edge_id": edge.id,
                },
            )
        )
        jobs.append((edge.target_id, child))
    instance._log("parallel_split", actor_id, activation.node_id)
    return jobs


def arrive(instance, node, token, actor_id: int):
    fork, parent = token.fork_activation_id, token.parent_id
    if not fork or not parent or fork.node_id.config.get("join") != node.key:
        raise UserError(instance.env._("汇合令牌不属于配对的并行分支。"))
    token.write({"node_id": node.id, "state": "joined"})
    activations = instance.env["workflow.node.instance"].sudo()
    activation = activations.search(
        [("instance_id", "=", instance.id), ("node_id", "=", node.id)],
    )
    if not activation:
        activation = activations.create(
            {
                "instance_id": instance.id,
                "node_id": node.id,
                "token_id": parent.id,
                "state": "waiting",
            },
        )
    siblings = (
        instance.env["workflow.token"]
        .sudo()
        .search(
            [
                ("parent_id", "=", parent.id),
                ("fork_activation_id", "=", fork.id),
            ],
        )
    )
    expected = instance.version_id.edge_ids.filtered(
        lambda e: e.source_id == fork.node_id,
    )
    if set(siblings.branch_edge_id.ids) != set(expected.ids):
        raise UserError(instance.env._("并行分支令牌不完整，汇合已回滚。"))
    if any(s.state != "joined" for s in siblings):
        instance._log("join_waiting", actor_id, node)
        return None
    if activation.state != "waiting" or parent.state != "waiting":
        raise UserError(instance.env._("并行汇合已处理。"))
    activation.write({"state": "done", "finished_at": fields.Datetime.now()})
    parent.write({"state": "active", "node_id": node.id})
    instance._log("parallel_joined", actor_id, node)
    return parent
