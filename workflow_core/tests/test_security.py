from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged

from .common import WorkflowCase, sequential


@tagged("post_install", "-at_install")
class TestSecurity(WorkflowCase):
    def test_start_context_defaults_cannot_inject_tokens_or_terminal_state(self):
        definition = self.published()
        target = definition.published_version_id.node_ids.filtered(
            lambda n: n.kind == "end",
        )
        instance = self.instance(
            definition.with_context(
                default_state="done",
                default_token_ids=[
                    Command.create(
                        {"key": "injected", "node_id": target.id, "state": "done"},
                    ),
                ],
                default_comment="forged history",
            ),
        )
        self.assertEqual(instance.state, "running")
        self.assertEqual(instance.token_ids.mapped("key"), ["root"])
        self.assertFalse(instance.log_ids.filtered("comment"))
        instance.task_ids.action_complete()
        self.assertEqual(instance.state, "done")

    def test_design_publish_execute_roles_are_separate(self):
        definition = self.definition()
        version = definition.version_ids
        version.with_user(self.designer).save_graph(sequential(self.worker.id), 0)
        with self.assertRaises(AccessError):
            version.with_user(self.designer).action_publish(1)
        with self.assertRaises(AccessError):
            version.with_user(self.publisher).save_graph(sequential(), 1)
        version.with_user(self.publisher).action_publish(1)
        with self.assertRaises(AccessError):
            definition.with_user(self.viewer).action_start()

    def test_non_assignee_cannot_complete_or_inject_runtime_changes(self):
        instance = self.instance(self.published())
        task = instance.task_ids
        for user in (self.other, self.viewer, self.manager):
            with self.assertRaises(AccessError):
                task.with_user(user).action_complete()
        for record, values in (
            (task, {"state": "done"}),
            (instance, {"state": "done"}),
            (instance.node_instance_ids[:1], {"state": "done"}),
            (instance.log_ids[:1], {"comment": "tamper"}),
        ):
            with self.assertRaises(AccessError):
                record.with_context(workflow_engine=True, sudo=True).write(values)
            with self.assertRaises(AccessError):
                record.unlink()
        with self.assertRaises(AccessError):
            self.env["workflow.instance"].with_user(self.worker).create({})

    def test_only_participants_or_viewers_can_read_instances(self):
        instance = self.instance(self.published())
        with self.assertRaises(AccessError):
            instance.with_user(self.other).get_monitor()
        self.assertEqual(
            instance.with_user(self.viewer).get_monitor()["instance_id"],
            instance.id,
        )
        self.assertFalse(
            self.env["workflow.task"]
            .with_user(self.other)
            .search([("instance_id", "=", instance.id)]),
        )

    def test_company_rules_also_limit_managers_and_monitors(self):
        second = self.env["res.company"].create({"name": "Workflow second company"})
        manager = new_test_user(
            self.env(context={**self.env.context, "no_reset_password": True}),
            login="workflow_second_manager",
            groups="workflow_core.group_manager",
            company_id=second.id,
            company_ids=[Command.set([second.id])],
        )
        definition = (
            self.env["workflow.definition"]
            .with_user(manager)
            .with_company(second)
            .create({"name": "Other company"})
        )
        version = definition.version_ids
        version.save_graph(sequential(), 0)
        version.action_publish(1)
        instance = self.instance(definition, user=manager)
        for record, method in ((version, "get_canvas"), (instance, "get_monitor")):
            with self.assertRaises(AccessError):
                getattr(record.with_user(self.manager), method)()
        with self.assertRaises(AccessError):
            instance.token_ids.with_user(self.manager).read(["state"])
        with self.assertRaises(AccessError):
            definition.with_user(self.manager).action_start()

    def test_business_access_rechecked_on_monitor_and_completion(self):
        definition = self.published(model=True)
        partner = self.env["res.partner"].create({"name": "Restricted business"})
        instance = self.instance(definition, res_id=partner.id)
        self.env["ir.rule"].create(
            {
                "name": "WF hide business",
                "model_id": self.env.ref("base.model_res_partner").id,
                "domain_force": f"[('id', '!=', {partner.id})]",
            },
        )
        for operation in (
            instance.get_monitor,
            instance.action_business_record,
            instance.task_ids.action_complete,
        ):
            with self.assertRaises(AccessError):
                operation()
        self.assertEqual(instance.task_ids.state, "pending")

    def test_invalid_assignee_and_unregistered_model_are_rejected(self):
        version = self.definition().version_ids
        with self.assertRaises(UserError):
            version.save_graph(sequential(self.viewer.id), 0)
        with self.assertRaises(ValidationError) as error:
            self.definition().write(
                {"model_id": self.env.ref("base.model_res_users").id},
            )
        self.assertIn("未注册", str(error.exception))

    def test_forged_version_and_node_crud_are_rejected(self):
        version = self.definition().version_ids
        with self.assertRaises(AccessError):
            version.with_user(self.designer).write({"state": "published"})
        with self.assertRaises(AccessError):
            self.env["workflow.node"].with_user(self.designer).create(
                {"version_id": version.id},
            )

    def test_context_defaults_cannot_select_a_foreign_published_version(self):
        published = self.published().published_version_id
        definition = (
            self.env["workflow.definition"]
            .with_user(self.designer)
            .with_context(default_published_version_id=published.id)
            .create({"name": "Forged default"})
        )
        self.assertFalse(definition.published_version_id)

    def test_template_can_restrict_who_starts_it(self):
        definition = self.published()
        definition.starter_group_ids = self.env.ref("workflow_core.group_manager")
        with self.assertRaises(AccessError):
            self.instance(definition)
        self.assertEqual(self.instance(definition, user=self.manager).state, "running")
