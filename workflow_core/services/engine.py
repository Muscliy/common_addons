from odoo import Command, fields
from odoo.exceptions import UserError

from .rules import evaluate_rule


def start_instance(definition, record, request_key: str):
    env = definition.env
    instances = env["workflow.instance"].sudo()
    existing = instances.search(
        [
            ("definition_id", "=", definition.id),
            ("starter_id", "=", env.uid),
            ("request_key", "=", request_key),
        ],
        limit=1,
    )
    res_id = record.id if record is not None else 0
    if existing:
        if existing.res_id != res_id:
            raise UserError(env._("同一请求标识不能用于不同业务记录。"))
        return existing
    version = definition.published_version_id
    instance = instances.create(
        {
            "name": f"{definition.name} / V{version.number}",
            "version_id": version.id,
            "starter_id": env.uid,
            "res_id": res_id,
            "request_key": request_key,
            "participant_ids": [Command.link(env.uid)],
        },
    )
    instance._log("started", env.uid)
    first = version.node_ids.filtered(lambda n: n.kind == "start")
    activate(instance, first, record, env.uid)
    return instance


def advance(instance, node, record, actor_id: int) -> None:
    edges = instance.version_id.edge_ids.filtered(lambda e: e.source_id == node).sorted(
        "sequence",
    )
    if node.kind == "condition":
        selected = edges.filtered(
            lambda e: not e.is_default and evaluate_rule(e.rule, record),
        )[:1]
        edges = selected or edges.filtered("is_default")
    if len(edges) != 1:
        raise UserError(instance.env._("流程出口配置无效, 未推进任务。"))
    activate(instance, edges.target_id, record, actor_id)


def activate(instance, node, record, actor_id: int) -> None:
    """MVP 无环且一次仅一条执行路径, 受发布校验和唯一约束共同保护。"""
    # 迭代自动节点, 避免长顺序图造成 Python 递归栈溢出。
    for _step in range(201):
        node.ensure_one()
        waiting = node._waits_for_input()
        activation = (
            instance.env["workflow.node.instance"]
            .sudo()
            .create(
                {
                    "instance_id": instance.id,
                    "node_id": node.id,
                    "state": "waiting" if waiting else "done",
                    "finished_at": False if waiting else fields.Datetime.now(),
                },
            )
        )
        instance._log("waiting" if waiting else "node_completed", actor_id, node)
        if waiting:
            node._activate_input(instance, activation, record, actor_id)
            return
        if node.kind == "end":
            instance.write({"state": "done", "finished_at": fields.Datetime.now()})
            instance._log("completed", actor_id, node)
            return
        edges = instance.version_id.edge_ids.filtered(
            lambda e: e.source_id == node,
        ).sorted("sequence")
        if node.kind == "condition":
            selected = edges.filtered(
                lambda e: not e.is_default and evaluate_rule(e.rule, record),
            )[:1]
            edges = selected or edges.filtered("is_default")
        if len(edges) != 1:
            raise UserError(instance.env._("节点出口无效, 执行已回滚。"))
        node = edges.target_id
    raise UserError(instance.env._("流程超过自动推进步数限制。"))


def create_task(instance, activation, record) -> None:
    assignee = activation.node_id.assignee_id or instance.starter_id
    company = instance.company_id
    if not assignee.active or assignee.share or company not in assignee.company_ids:
        raise UserError(instance.env._("任务负责人已停用或无所属公司权限。"))
    if not assignee.with_user(assignee).has_group("workflow_core.group_executor"):
        raise UserError(instance.env._("任务负责人不具备工作流执行权限。"))
    if record is not None:
        record.with_user(assignee).check_access("read")
    instance.write({"participant_ids": [Command.link(assignee.id)]})
    instance.env["workflow.task"].sudo().create(
        {
            "name": activation.node_id.name,
            "node_instance_id": activation.id,
            "assignee_id": assignee.id,
        },
    )
