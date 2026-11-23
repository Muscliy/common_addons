from odoo import Command, api
from odoo.exceptions import UserError
from odoo.tools import clean_context

from .configuration import check_task, check_users
from odoo.addons.workflow_core.services.access import lock_record


def begin_project_task(instance, activation, record, actor_id: int) -> None:
    original = api.Environment(
        instance.env.cr,
        actor_id,
        clean_context(instance.env.context),
        su=False,
    )
    node = activation.node_id
    config = node.config
    if config["mode"] == "business":
        if record is None or record._name != "project.task":
            raise UserError(instance.env._("当前业务记录不是项目任务。"))
        task = record.with_env(original)
    else:
        project = original["project.project"].browse(config["project_id"]).exists()
        project.check_access("read")
        if (
            not project
            or not project.active
            or project.company_id != instance.company_id
            or project.is_template
        ):
            raise UserError(instance.env._("目标项目已停用或公司不匹配。"))
        task = original["project.task"].create(
            {
                "name": node.name,
                "project_id": project.id,
                "user_ids": [Command.set(config["user_ids"])],
                "state": "01_in_progress",
            },
        )
    lock_record(task)
    check_task(task, instance.company_id)
    links = original["workflow.project.link"].sudo()
    if links.search_count([("project_task_id", "=", task.id)]):
        raise UserError(instance.env._("此项目任务已有工作流关联，不能重复绑定。"))
    users = task.user_ids.sudo()
    check_users(users, instance.company_id, task, record)
    instance.write({"participant_ids": [Command.link(uid) for uid in users.ids]})
    links.create(
        {
            "name": node.name,
            "node_instance_id": activation.id,
            "project_task_id": task.id,
            "assignee_ids": [Command.set(users.ids)],
        },
    )
    task.invalidate_recordset(["workflow_can_open", "workflow_status"])
    instance._log("project_task_linked", actor_id, node)
