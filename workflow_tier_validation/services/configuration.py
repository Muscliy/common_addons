from odoo.exceptions import UserError, ValidationError


def reviewer_fields(version) -> dict:
    model = version.definition_id.model_id.sudo().model
    if not model:
        return {}
    return {
        name: info
        for name, info in version.env[model].fields_get().items()
        if info["type"] in ("many2one", "many2many")
        and info.get("relation") in ("res.users", "res.groups")
    }


def validate_config(config: dict, version) -> None:
    levels = config.get("levels")
    if (
        set(config) != {"levels"}
        or not isinstance(levels, list)
        or not 1 <= len(levels) <= 20
    ):
        raise ValidationError(version.env._("审批节点需配置1至20级审批。"))
    for level in levels:
        if not isinstance(level, dict) or set(level) != {"kind", "ref"}:
            raise ValidationError(version.env._("审批级次格式不正确。"))
        kind, ref = level["kind"], level["ref"]
        if kind == "field":
            if not isinstance(ref, str) or ref not in reviewer_fields(version):
                raise ValidationError(
                    version.env._("动态审批字段必须是可访问的用户或用户组字段。"),
                )
        elif kind in ("user", "group") and type(ref) is int and ref > 0:
            model = "res.users" if kind == "user" else "res.groups"
            selected = version.env[model].sudo().browse(ref).exists()
            if not selected:
                raise ValidationError(version.env._("审批人或用户组不存在。"))
            if kind == "user":
                check_candidates(selected, version.company_id)
            elif not selected.user_ids.filtered(
                lambda u: eligible(u, version.company_id),
            ):
                raise ValidationError(version.env._("所选组没有本公司的有效审批人员。"))
        else:
            raise ValidationError(version.env._("审批类型或引用不正确。"))


def eligible(user, company) -> bool:
    return bool(
        user.active
        and not user.share
        and company in user.company_ids
        and user.has_group("workflow_tier_validation.group_approver"),
    )


def check_candidates(users, company, record=None) -> None:
    if not users or any(not eligible(user, company) for user in users):
        raise UserError(users.env._("每级审批必须有本公司的有效审批人员。"))
    if record is not None:
        for user in users:
            record.with_user(user).check_access("read")


def resolve_levels(node, record) -> list:
    result = []
    for level in node.config["levels"]:
        kind, ref = level["kind"], level["ref"]
        if kind == "user":
            users = node.env["res.users"].sudo().browse(ref).exists()
        elif kind == "group":
            users = (
                node.env["res.groups"]
                .sudo()
                .browse(ref)
                .user_ids.filtered(lambda user: eligible(user, node.company_id))
            )
        else:
            if record is None or ref not in reviewer_fields(
                node.version_id.with_env(record.env),
            ):
                raise UserError(node.env._("动态审批字段当前不可访问。"))
            value = record[ref]
            users = value if value._name == "res.users" else value.user_ids
        check_candidates(users, node.company_id, record)
        result.append(users)
    return result
