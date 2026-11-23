from odoo.exceptions import ValidationError


def validate_parallel(graph: dict, ordered: list[str]) -> None:
    """Carry a lexical fork/branch stack through the DAG; only a paired join may pop it."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    outgoing = {key: [] for key in nodes}
    for edge in graph["edges"]:
        outgoing[edge["source"]].append(edge)
    owners = {}
    for key, node in nodes.items():
        if node["type"] != "fork":
            continue
        join = node["data"].get("config", {}).get("join")
        if join not in nodes or nodes[join]["type"] != "join" or join in owners:
            message = "每个并行分支必须指定独立的并行汇合节点。"
            raise ValidationError(message)
        owners[join] = key
    contexts = {key: set() for key in nodes}
    contexts[ordered[0]].add(())
    for key in ordered:
        node, stacks = nodes[key], contexts[key]
        if node["type"] == "join":
            stacks = _join_context(key, stacks, owners, outgoing)
        if len(stacks) != 1:
            message = "并行分支只能在配对的汇合节点合并，不能跨分支连线。"
            raise ValidationError(message)
        stack = next(iter(stacks))
        if node["type"] == "end" and stack:
            message = "并行分支必须先汇合，不能提前结束流程。"
            raise ValidationError(message)
        targets = [e["target"] for e in outgoing[key]]
        if len(targets) != len(set(targets)):
            message = "同一节点不能重复连接同一出口。"
            raise ValidationError(message)
        for edge in outgoing[key]:
            context = (*stack, (key, edge["id"])) if node["type"] == "fork" else stack
            contexts[edge["target"]].add(context)


def _join_context(key: str, stacks: set, owners: dict, outgoing: dict) -> set:
    owner = owners.get(key)
    if not owner or not stacks or any(not s or s[-1][0] != owner for s in stacks):
        message = "并行汇合只能接收其配对分支，且必须正确嵌套。"
        raise ValidationError(message)
    expected = {e["id"] for e in outgoing[owner]}
    if {s[-1][1] for s in stacks} != expected:
        message = "并行汇合必须等待配对分支的全部出口。"
        raise ValidationError(message)
    return {s[:-1] for s in stacks}
