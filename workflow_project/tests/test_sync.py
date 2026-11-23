from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import ProjectCase, project_graph


@tagged("post_install", "-at_install")
class TestProjectSync(ProjectCase):
    def test_create_multi_assignee_and_complete_from_workflow(self):
        instance, link = self.begin()
        task = link.project_task_id
        self.assertEqual(set(task.user_ids.ids), {self.worker.id, self.other.id})
        self.assertEqual(task.project_id, self.project)
        self.assertEqual(task.workflow_status, "进行中")
        self.assertFalse(instance.task_ids)
        link.with_user(self.other).action_decide("complete", "已办")
        self.assertEqual(task.state, "1_done")
        self.assertEqual(link.state, "done")
        self.assertEqual(len(instance.task_ids), 1)
        link.with_user(self.other).action_decide("complete", "重试")
        self.assertEqual(link.comment, "已办")
        self.assertEqual(len(instance.task_ids), 1)
        instance.task_ids.action_complete()
        self.assertEqual(instance.state, "done")
        self.assertEqual(task.workflow_status, "已完成")

    def test_native_task_completion_advances_once(self):
        instance, link = self.begin()
        task = link.project_task_id.with_user(self.other)
        task.write({"state": "03_approved"})
        self.assertFalse(instance.task_ids)
        task.write({"state": "1_done"})
        task.write({"state": "1_done"})
        self.assertEqual(link.state, "done")
        self.assertEqual(len(instance.task_ids), 1)
        self.assertEqual(
            len(
                instance.log_ids.filtered(
                    lambda log: log.event == "project_task_completed",
                ),
            ),
            1,
        )
        self.assertEqual(
            task.action_workflow_monitor()["params"]["instance_id"],
            instance.id,
        )
        self.assertTrue(task.workflow_can_open)
        with self.assertRaises(UserError):
            task.write({"state": "01_in_progress"})

    def test_link_current_business_task_without_creating_duplicate(self):
        task = self.env["project.task"].create(
            {
                "name": "Existing project task",
                "project_id": self.project.id,
                "user_ids": [Command.set((self.worker | self.other).ids)],
            },
        )
        self.assertFalse(task.workflow_can_open)
        instance, link = self.begin(task=task)
        self.assertTrue(task.with_user(self.worker).workflow_can_open)
        self.assertEqual(link.project_task_id, task)
        task.with_user(self.worker).write({"state": "1_done"})
        self.assertEqual(instance.task_ids.name, "after")
        with self.assertRaises(UserError):
            instance.definition_id.with_user(self.worker).action_start(
                task.id,
                "another",
            )
        self.assertEqual(
            self.env["workflow.project.link"].search_count(
                [("project_task_id", "=", task.id)],
            ),
            1,
        )

    def test_project_cancel_cancels_flow_and_keeps_audit(self):
        instance, link = self.begin()
        link.project_task_id.with_user(self.other).write({"state": "1_canceled"})
        self.assertEqual(instance.state, "cancelled")
        self.assertEqual(link.state, "cancelled")
        self.assertFalse(
            instance.token_ids.filtered(
                lambda token: token.state in ("active", "waiting"),
            ),
        )
        self.assertFalse(instance.task_ids)

    def test_flow_cancel_uses_native_project_write(self):
        instance, link = self.begin()
        instance.action_cancel()
        self.assertEqual(link.state, "cancelled")
        self.assertEqual(link.project_task_id.state, "1_canceled")
        self.assertTrue(link.project_task_id.exists())
        instance.action_cancel()

    def test_successor_failure_rolls_back_both_sides(self):
        instance, link = self.begin()
        self.worker.active = False
        with self.assertRaises(UserError):
            link.project_task_id.with_user(self.other).write({"state": "1_done"})
        self.assertEqual(link.state, "pending")
        self.assertEqual(link.project_task_id.state, "01_in_progress")
        self.assertFalse(instance.task_ids)
        self.assertFalse(
            instance.log_ids.filtered(
                lambda log: log.event == "project_task_completed",
            ),
        )
        self.worker.active = True
        link.with_user(self.other).action_decide("complete")
        self.assertEqual(link.state, "done")

    def test_original_project_permissions_are_required(self):
        graph = project_graph(self.project.id, [self.worker.id])
        definition = self.published(graph)
        self.worker.group_ids = [
            Command.unlink(self.env.ref("project.group_project_user").id),
        ]
        with self.assertRaises(AccessError):
            self.instance(definition)
        self.assertFalse(
            self.env["workflow.instance"].search(
                [("definition_id", "=", definition.id)],
            ),
        )

    def test_unrelated_native_tasks_keep_normal_behavior(self):
        task = (
            self.env["project.task"]
            .with_user(self.worker)
            .create({"name": "Ordinary", "project_id": self.project.id})
        )
        task.write({"user_ids": [Command.set([self.other.id])], "state": "1_done"})
        task.write({"state": "01_in_progress"})
        copy = task.copy()
        self.assertFalse(copy._workflow_links())
        copy.unlink()
        task.unlink()
