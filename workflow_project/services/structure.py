from odoo.exceptions import AccessError


def guard_task_targets(model, values) -> None:
    """Protect inverse links too: writing an ordinary task must not restructure a bound one."""
    ids = set()
    if values.get("parent_id"):
        ids.add(values["parent_id"])
    for name in ("child_ids", "depend_on_ids", "dependent_ids"):
        for command in values.get(name) or []:
            if type(command) is int:
                ids.add(command)
            elif command[0] == 6:
                ids.update(command[2])
            elif command[1]:
                ids.add(command[1])
    if ids and model.env["workflow.project.link"].sudo().search_count(
        [("project_task_id", "in", list(ids))],
    ):
        raise AccessError(model.env._("不能把已关联工作流的任务加入父子或依赖结构。"))
