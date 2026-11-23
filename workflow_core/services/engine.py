from collections import deque

from odoo import Command, fields
from odoo.exceptions import UserError

from .parallel import activation_token, arrive, root_token, split
from .rules import evaluate_rule


def start_instance(definition, record, request_key: str, expected_version_id: int = 0):
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
    if expected_version_id and version.id != expected_version_id:
        raise UserError(env._("当前发布版本已切换，请重新打开流程模板后启动。"))
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
    activation = instance.node_instance_ids.filtered(lambda a: a.node_id == node)
    token = activation_token(instance, activation)
    _drive(
        instance,
        [(edge.target_id, token) for edge in _exits(instance, node, record)],
        record,
        actor_id,
    )


def activate(instance, node, record, actor_id: int) -> None:
    _drive(instance, [(node, root_token(instance, node))], record, actor_id)


def _exits(instance, node, record):
    edges = instance.version_id.edge_ids.filtered(lambda e: e.source_id == node).sorted(
        "sequence",
    )
    if node.kind == "condition":
        selected = edges.filtered(
            lambda e: not e.is_default and evaluate_rule(e.rule, record),
        )[:1]
        edges = selected or edges.filtered("is_default")
    if (node.kind == "fork" and len(edges) < 2) or (
        node.kind != "fork" and len(edges) != 1
    ):
        raise UserError(instance.env._("流程出口配置无效，执行已回滚。"))
    return edges


def _drive(instance, initial: list, record, actor_id: int) -> None:
    """Instance lock and the caller's savepoint cover all tokens and side effects."""
    jobs = deque(initial)
    for _step in range(1001):
        if not jobs:
            return
        node, token = jobs.popleft()
        token.write({"node_id": node.id})
        if node.kind == "join":
            parent = arrive(instance, node, token, actor_id)
            if parent:
                jobs.extend(
                    (e.target_id, parent) for e in _exits(instance, node, record)
                )
            continue
        activation = _activate_node(instance, node, token, record, actor_id)
        if node._waits_for_input():
            continue
        if node.kind == "end":
            _finish(instance, token, node, actor_id)
            continue
        edges = _exits(instance, node, record)
        if node.kind == "fork":
            jobs.extend(split(instance, activation, token, edges, actor_id))
        else:
            jobs.extend((e.target_id, token) for e in edges)
    raise UserError(instance.env._("流程超过自动推进步数限制。"))


def _activate_node(instance, node, token, record, actor_id: int):
    waiting = node._waits_for_input()
    activation = (
        instance.env["workflow.node.instance"]
        .sudo()
        .create(
            {
                "instance_id": instance.id,
                "node_id": node.id,
                "token_id": token.id,
                "state": "waiting" if waiting else "done",
                "finished_at": False if waiting else fields.Datetime.now(),
            },
        )
    )
    instance._log("waiting" if waiting else "node_completed", actor_id, node)
    if waiting:
        token.write({"state": "waiting"})
        node._activate_input(instance, activation, record, actor_id)
    return activation


def _finish(instance, token, node, actor_id: int) -> None:
    if token.parent_id:
        raise UserError(instance.env._("并行分支尚未汇合，不能结束流程。"))
    token.write({"state": "done"})
    if instance.token_ids.filtered(lambda t: t.state in ("active", "waiting")):
        raise UserError(instance.env._("仍有未完成的执行令牌，不能结束流程。"))
    instance.write({"state": "done", "finished_at": fields.Datetime.now()})
    instance._log("completed", actor_id, node)


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
