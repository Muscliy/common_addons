from odoo.exceptions import UserError, ValidationError


def eligible(user, company) -> bool:
    return bool(
        user.active
        and not user.share
        and company in user.company_ids
        and user.has_group("workflow_core.group_executor")
        and user.has_group("project.group_project_user"),
    )


def validate_config(config: dict, version) -> None:
    if config == {"mode": "business"}:
        if version.definition_id.model_id.sudo().model != "project.task":
            raise ValidationError(
                version.env._("关联当前业务任务要求流程业务模型为项目任务。"),
            )
        return
    if (
        set(config) != {"mode", "project_id", "user_ids"}
        or config.get("mode") != "create"
        or type(config.get("project_id")) is not int
        or not isinstance(config.get("user_ids"), list)
        or not 1 <= len(config["user_ids"]) <= 50
        or any(type(uid) is not int or uid <= 0 for uid in config["user_ids"])
        or len(set(config["user_ids"])) != len(config["user_ids"])
    ):
        raise ValidationError(version.env._("请配置项目和1至50名不同的负责人。"))
    project = version.env["project.project"].browse(config["project_id"]).exists()
    project.check_access("read")
    if (
        not project
        or not project.active
        or project.company_id != version.company_id
        or project.is_template
    ):
        raise ValidationError(version.env._("项目必须有效、属于流程公司且不是模板。"))
    users = version.env["res.users"].sudo().browse(config["user_ids"]).exists()
    check_users(users, version.company_id)
    if len(users) != len(config["user_ids"]):
        raise ValidationError(version.env._("项目负责人不存在。"))


def check_users(users, company, task=None, record=None) -> None:
    if not users or any(not eligible(user, company) for user in users):
        raise UserError(users.env._("负责人必须是本公司的有效流程执行及项目用户。"))
    for user in users:
        if task is not None:
            task.with_user(user).check_access("read")
            task.with_user(user).check_access("write")
        if record is not None:
            record.with_user(user).check_access("read")


def check_task(task, company) -> None:
    task.check_access("read")
    task.check_access("write")
    if (
        not task
        or not task.active
        or not task.project_id
        or task.company_id != company
        or task.state in ("1_done", "1_canceled")
        or task.is_template
        or task.parent_id
        or task.child_ids
        or task.depend_on_ids
        or task.dependent_ids
        or task.recurring_task
    ):
        raise UserError(
            task.env._(
                "只能关联本公司未结束的独立项目任务；暂不支持模板、子任务、依赖或循环任务。",
            ),
        )
