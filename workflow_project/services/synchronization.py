from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError

from .configuration import eligible
from .scope import syncing
from odoo.addons.workflow_core.services.access import lock_record
from odoo.addons.workflow_core.services.engine import advance

TERMINAL = {"complete": "1_done", "cancel": "1_canceled"}


def lock_links(links) -> None:
    for instance in links.sudo().instance_id.sorted("id"):
        lock_record(instance)
    for link in links.sudo().sorted("id"):
        lock_record(link)
    for task in links.sudo().project_task_id.sorted("id"):
        lock_record(task)


def authorize(link) -> None:
    link.check_access("read")
    task = link.project_task_id
    task.check_access("read")
    task.check_access("write")
    if link.env.user not in link.assignee_ids or not eligible(
        link.env.user,
        link.company_id,
    ):
        raise AccessError(link.env._("只有有效的项目任务负责人可以办理。"))
    if link.state != "pending" or link.instance_id.state != "running":
        raise UserError(link.env._("关联任务或流程已结束。"))
    link.instance_id._business_record()


def decide(link, decision: str, comment: str) -> bool:
    link.check_access("read")
    if (
        decision not in ("complete", "cancel")
        or not isinstance(comment, str)
        or len(comment) > 4000
    ):
        raise ValidationError(link.env._("项目任务操作或意见不正确。"))
    with link.env.cr.savepoint():
        lock_links(link)
        expected = "done" if decision == "complete" else "cancelled"
        if link.state == expected and link.completed_by == link.env.user:
            link.project_task_id.check_access("write")
            return True
        authorize(link)
        with syncing(link):
            link.project_task_id.write({"state": TERMINAL[decision]})
        finish(link, TERMINAL[decision], comment)
    return True


def finish(link, state: str, comment: str = "") -> None:
    if state not in TERMINAL.values():
        return
    instance, activation = link.instance_id.sudo(), link.node_instance_id.sudo()
    record = link.instance_id._business_record()
    cancelled = state == "1_canceled"
    link.sudo().write(
        {
            "state": "cancelled" if cancelled else "done",
            "completed_by": link.env.uid,
            "finished_at": fields.Datetime.now(),
            "comment": comment,
        },
    )
    activation.write(
        {
            "state": "cancelled" if cancelled else "done",
            "finished_at": fields.Datetime.now(),
        },
    )
    instance._log(
        "project_task_cancelled" if cancelled else "project_task_completed",
        link.env.uid,
        activation.node_id,
        comment,
    )
    if cancelled:
        instance._close_open_work()
        instance.write({"state": "cancelled", "finished_at": fields.Datetime.now()})
        instance._log("cancelled", link.env.uid)
    else:
        advance(instance, activation.node_id, record, link.env.uid)


def close_links(instance) -> None:
    links = (
        instance.env["workflow.project.link"]
        .sudo()
        .search(
            [
                ("instance_id", "in", instance.ids),
                ("state", "=", "pending"),
            ],
        )
    )
    lock_links(links)
    for link in links:
        original = link.with_user(instance.env.uid)
        original.check_access("read")
        with syncing(link):
            original.project_task_id.write({"state": "1_canceled"})
        link.write({"state": "cancelled", "finished_at": fields.Datetime.now()})
