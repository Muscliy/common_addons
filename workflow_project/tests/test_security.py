from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import ProjectCase, project_graph


@tagged("post_install", "-at_install")
class TestProjectSecurity(ProjectCase):
    def test_inverse_dependencies_and_context_parent_cannot_restructure_linked_task(
        self,
    ):
        _, link = self.begin()
        ordinary = (
            self.env["project.task"]
            .with_user(self.worker)
            .create({"name": "Ordinary dependency", "project_id": self.project.id})
        )
        with self.assertRaises(AccessError):
            ordinary.write({"depend_on_ids": [Command.link(link.project_task_id.id)]})
        with self.assertRaises(AccessError):
            self.env["project.task"].with_user(self.worker).with_context(
                default_parent_id=link.project_task_id.id,
            ).create({"name": "Forged child"})
        self.assertFalse(link.project_task_id.dependent_ids)

    def test_other_company_manager_cannot_read_link(self):
        second = self.env["res.company"].create({"name": "Other project company"})
        manager = new_test_user(
            self.env(context={"no_reset_password": True}),
            login="project_flow_other_company",
            groups="workflow_core.group_manager,project.group_project_manager",
            company_id=second.id,
            company_ids=[Command.set([second.id])],
        )
        project = (
            self.env["project.project"]
            .with_user(manager)
            .with_company(second)
            .create({"name": "Other company project", "company_id": second.id})
        )
        definition = (
            self.env["workflow.definition"]
            .with_user(manager)
            .with_company(second)
            .create({"name": "Other company flow"})
        )
        version = definition.version_ids
        version.save_graph(project_graph(project.id, [manager.id]), 0)
        version.action_publish(1)
        action = definition.action_start()
        link = self.env["workflow.project.link"].search(
            [("instance_id", "=", action["params"]["instance_id"])],
        )
        with self.assertRaises(AccessError):
            link.with_user(self.manager).read(["name"])

    def test_non_assignee_and_context_flags_cannot_complete(self):
        _, link = self.begin()
        for operation in (
            lambda: link.with_user(self.manager).action_decide("complete"),
            lambda: (
                link.project_task_id.with_user(self.manager)
                .with_context(workflow_project_sync=True, sudo=True)
                .write({"state": "1_done"})
            ),
            lambda: link.write({"state": "done"}),
            link.unlink,
            link.copy,
        ):
            with self.assertRaises(AccessError):
                operation()
        self.assertEqual(link.state, "pending")

    def test_assignment_structure_and_deletion_are_protected(self):
        _, link = self.begin()
        task = link.project_task_id
        for vals in (
            {"user_ids": [Command.set([self.manager.id])]},
            {"project_id": False},
            {"active": False},
            {"recurring_task": True},
        ):
            with self.assertRaises(AccessError):
                task.write(vals)
        with self.assertRaises(AccessError):
            task.unlink()
        copied = task.copy()
        self.assertFalse(copied._workflow_links())
        copied.unlink()

    def test_lost_project_read_blocks_link_reads_exports_and_completion(self):
        _, link = self.begin()
        task = link.project_task_id
        self.env["ir.rule"].create(
            {
                "name": "Hide project task",
                "model_id": self.env.ref("project.model_project_task").id,
                "domain_force": f"[('id', '!=', {task.id})]",
            },
        )
        for operation in (
            lambda: link.read(["name"]),
            lambda: link.export_data(["name"]),
            lambda: link.action_decide("complete"),
            link.action_open,
        ):
            with self.assertRaises(AccessError):
                operation()

    def test_non_participant_cannot_read_or_open_link(self):
        _, link = self.begin(users=self.worker)
        with self.assertRaises(AccessError):
            link.with_user(self.other).read(["name"])
        with self.assertRaises(AccessError):
            link.with_user(self.other).action_monitor()
        self.assertFalse(link.project_task_id.with_user(self.other).workflow_can_open)

    def test_invalid_configuration_and_closed_business_task_are_rejected(self):
        for config in (
            {"mode": "business"},
            {"mode": "create", "project_id": self.project.id, "user_ids": []},
            {
                "mode": "create",
                "project_id": self.project.id,
                "user_ids": [self.viewer.id],
            },
        ):
            graph = project_graph()
            graph["nodes"][1]["data"]["config"] = config
            with self.assertRaises(UserError):
                self.definition().version_ids.save_graph(graph, 0)
        task = self.env["project.task"].create(
            {
                "name": "Closed",
                "project_id": self.project.id,
                "user_ids": [Command.set([self.worker.id])],
                "state": "1_done",
            },
        )
        with self.assertRaises(UserError):
            self.begin(task=task)
