import math
import re
from collections import deque

from odoo.exceptions import ValidationError

from .rules import validate_rule

NODE_TYPES = [
    ("start", "开始"),
    ("end", "结束"),
    ("task", "人工任务"),
    ("condition", "条件分支"),
]
KEY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_payload(graph: dict, node_types=None) -> None:
    """草稿允许不完整的图, 但不允许恶意结构、未知类型或悬空引用。"""
    if not isinstance(graph, dict) or set(graph) != {"nodes", "edges", "viewport"}:
        message = "画布数据格式不正确。"
        raise ValidationError(message)
    nodes, edges = graph["nodes"], graph["edges"]
    if (
        not isinstance(nodes, list)
        or not isinstance(edges, list)
        or len(nodes) > 200
        or len(edges) > 500
    ):
        message = "流程最多支持200个节点和500条连线。"
        raise ValidationError(message)
    keys = set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {
            "id",
            "type",
            "position",
            "data",
        }:
            message = "节点格式不正确。"
            raise ValidationError(message)
        _key(node["id"], keys)
        if not isinstance(node["type"], str) or node["type"] not in dict(
            node_types or NODE_TYPES,
        ):
            message = "当前版本不支持此节点类型。"
            raise ValidationError(message)
        _coordinates(node["position"], {"x", "y"})
        data = node["data"]
        if (
            not isinstance(data, dict)
            or not {"label", "assignee_id"} <= data.keys()
            or set(data) - {"label", "assignee_id", "config"}
            or not isinstance(data.get("config", {}), dict)
        ):
            message = "节点属性不正确。"
            raise ValidationError(message)
        if (
            not isinstance(data["label"], str)
            or not 1 <= len(data["label"].strip()) <= 120
        ):
            message = "节点名称需为1至120个字符。"
            raise ValidationError(message)
        if type(data["assignee_id"]) is not int or data["assignee_id"] < 0:
            message = "负责人格式不正确。"
            raise ValidationError(message)
    edge_keys = set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {
            "id",
            "source",
            "target",
            "data",
        }:
            message = "连线格式不正确。"
            raise ValidationError(message)
        _key(edge["id"], edge_keys)
        if not isinstance(edge["source"], str) or not isinstance(edge["target"], str):
            message = "连线节点格式不正确。"
            raise ValidationError(message)
        if (
            edge["source"] not in keys
            or edge["target"] not in keys
            or edge["source"] == edge["target"]
        ):
            message = "连线必须连接两个不同的现有节点。"
            raise ValidationError(message)
        data = edge["data"]
        if (
            not isinstance(data, dict)
            or set(data) != {"default", "rule"}
            or type(data["default"]) is not bool
        ):
            message = "连线属性不正确。"
            raise ValidationError(message)
        if not isinstance(data["rule"], dict):
            message = "条件必须采用结构化规则。"
            raise ValidationError(message)
    _coordinates(graph["viewport"], {"x", "y", "zoom"})
    if not 0.1 <= graph["viewport"]["zoom"] <= 4:
        message = "画布缩放范围不正确。"
        raise ValidationError(message)


def _key(key: str, keys: set) -> None:
    if not isinstance(key, str) or not KEY.fullmatch(key) or key in keys:
        message = "节点或连线标识无效或重复。"
        raise ValidationError(message)
    keys.add(key)


def _coordinates(value: dict, names: set) -> None:
    if not isinstance(value, dict) or set(value) != names:
        message = "画布坐标格式不正确。"
        raise ValidationError(message)
    if any(
        type(v) not in (int, float) or abs(v) > 100000 or not math.isfinite(v)
        for v in value.values()
    ):
        message = "画布坐标超出范围。"
        raise ValidationError(message)


def validate_graph(graph: dict, fields: dict, node_types=None) -> None:
    validate_payload(graph, node_types)
    nodes = {node["id"]: node for node in graph["nodes"]}
    starts = [key for key, node in nodes.items() if node["type"] == "start"]
    if len(starts) != 1 or not any(n["type"] == "end" for n in nodes.values()):
        message = "流程需要一个开始节点和至少一个结束节点。"
        raise ValidationError(message)
    outgoing, incoming = {key: [] for key in nodes}, dict.fromkeys(nodes, 0)
    for edge in graph["edges"]:
        outgoing[edge["source"]].append(edge)
        incoming[edge["target"]] += 1
    if incoming[starts[0]]:
        message = "开始节点不能有入线。"
        raise ValidationError(message)
    for key, node in nodes.items():
        exits = outgoing[key]
        if node["type"] == "condition":
            if len(exits) < 2 or sum(e["data"]["default"] for e in exits) != 1:
                message = "条件分支至少需要两个出口, 并指定一个默认出口。"
                raise ValidationError(message)
            for edge in exits:
                if edge["data"]["default"]:
                    if edge["data"]["rule"]:
                        message = "默认出口不能配置条件。"
                        raise ValidationError(message)
                else:
                    validate_rule(edge["data"]["rule"], fields)
        else:
            expected = 0 if node["type"] == "end" else 1
            if len(exits) != expected or any(
                e["data"]["rule"] or e["data"]["default"] for e in exits
            ):
                message = "开始和任务节点需一个普通出口, 结束节点不能有出口。"
                raise ValidationError(message)
    # Kahn 排序同时验证不可达节点与环。首版不接受循环或并行。
    queue, visited = deque([starts[0]]), set()
    while queue:
        key = queue.popleft()
        visited.add(key)
        for edge in outgoing[key]:
            target = edge["target"]
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if len(visited) != len(nodes):
        message = "流程存在循环或不可达节点。"
        raise ValidationError(message)
