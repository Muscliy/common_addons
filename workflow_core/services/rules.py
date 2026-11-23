import math
import operator

from odoo.exceptions import ValidationError

OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
}
SCALAR_TYPES = {"char", "text", "selection", "integer", "float", "monetary", "boolean"}


def scalar_fields(record) -> dict:
    if record is None:
        return {}
    # fields_get respects field-level groups; never inspect restricted values as sudo.
    return {
        name: info
        for name, info in record.fields_get().items()
        if info["type"] in SCALAR_TYPES and not name.startswith("_")
    }


def validate_rule(rule: dict, fields: dict, depth: int = 0) -> None:
    if not isinstance(rule, dict) or depth > 8:
        message = "条件格式不正确或嵌套过深。"
        raise ValidationError(message)
    if "all" in rule or "any" in rule:
        if len(rule) != 1:
            message = "条件组合只能选择 AND 或 OR。"
            raise ValidationError(message)
        children = rule.get("all", rule.get("any"))
        if not isinstance(children, list) or not 1 <= len(children) <= 20:
            message = "条件组合需要1至20个子条件。"
            raise ValidationError(message)
        for child in children:
            validate_rule(child, fields, depth + 1)
        return
    if set(rule) != {"field", "op", "value"} or not isinstance(rule["field"], str):
        message = "条件必须包含字段、运算符和值。"
        raise ValidationError(message)
    info = fields.get(rule["field"])
    if not info or not isinstance(rule["op"], str) or rule["op"] not in OPERATORS:
        message = "条件字段不可访问或运算符不支持。"
        raise ValidationError(message)
    value, kind = rule["value"], info["type"]
    if kind == "boolean":
        valid = type(value) is bool and rule["op"] in ("eq", "ne")
    elif kind in ("integer", "float", "monetary"):
        valid = type(value) in (int, float) and (
            type(value) is int or math.isfinite(value)
        )
    else:
        valid = (
            isinstance(value, str) and len(value) <= 1000 and rule["op"] in ("eq", "ne")
        )
    if not valid:
        message = "条件值或运算符与字段类型不匹配。"
        raise ValidationError(message)


def evaluate_rule(rule: dict, record) -> bool:
    validate_rule(rule, scalar_fields(record))
    if "all" in rule:
        return all(evaluate_rule(child, record) for child in rule["all"])
    if "any" in rule:
        return any(evaluate_rule(child, record) for child in rule["any"])
    value = record[rule["field"]]
    if value is False and isinstance(rule["value"], str):
        value = ""
    return OPERATORS[rule["op"]](value, rule["value"])
