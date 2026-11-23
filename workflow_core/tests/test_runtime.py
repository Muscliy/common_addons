from odoo.exceptions import UserError
from odoo.modules.module import get_manifest
from odoo.tests import tagged

from .common import WorkflowCase, edge, node, sequential


@tagged("post_install", "-at_install")
class TestRuntime(WorkflowCase):
    def test_sequential_completion_and_duplicate_requests(self):
        definition = self.published()
        instance = self.instance(definition)
        self.assertEqual(self.instance(definition), instance)
        self.assertEqual(len(instance.task_ids), 1)
        task = instance.task_ids
        self.assertTrue(task.action_complete("确认完成"))
        self.assertEqual(instance.state, "done")
        self.assertEqual(task.completed_by, self.worker)
        self.assertEqual(task.comment, "确认完成")
        before = len(instance.log_ids)
        self.assertTrue(task.action_complete("重复请求"))
        self.assertEqual(len(instance.log_ids), before)
        self.assertEqual(task.comment, "确认完成")
        self.assertEqual(len(instance.node_instance_ids), 3)
        self.assertTrue(
            all(row["finished_at"] for row in instance.get_monitor()["executions"]),
        )

    def test_completion_and_next_task_creation_rollback_together(self):
        graph = sequential(self.worker.id)
        graph["nodes"].insert(2, node("second", assignee=self.other.id))
        graph["edges"] = [
            edge("start", "first"),
            edge("first", "second"),
            edge("second", "end"),
        ]
        instance = self.instance(self.published(graph))
        task = instance.task_ids
        before = len(instance.log_ids)
        self.other.active = False
        with self.assertRaises(UserError):
            task.action_complete("must roll back")
        self.assertEqual(task.state, "pending")
        self.assertFalse(task.completed_at)
        self.assertEqual(len(instance.log_ids), before)
        self.assertEqual(len(instance.node_instance_ids), 2)
        self.other.active = True
        task.action_complete()
        instance = instance.with_user(self.other)
        second = instance.task_ids.filtered(lambda t: t.state == "pending")
        self.assertEqual(second.assignee_id, self.other)
        second.action_complete()
        self.assertEqual(instance.state, "done")

    def test_condition_selects_one_path_and_default(self):
        graph = {
            "nodes": [
                node("start", "start"),
                node("branch", "condition"),
                node("large", assignee=self.worker.id),
                node("small", assignee=self.worker.id),
                node("end", "end"),
            ],
            "edges": [
                edge("start", "branch"),
                edge("branch", "large", {"field": "color", "op": "ge", "value": 5}),
                edge("branch", "small", default=True),
                edge("large", "end"),
                edge("small", "end"),
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        definition = self.published(graph, model=True)
        for color, expected in ((8, "large"), (1, "small")):
            partner = self.env["res.partner"].create(
                {"name": "WF business", "color": color},
            )
            instance = self.instance(definition, key=str(color), res_id=partner.id)
            self.assertEqual(instance.task_ids.name, expected)
            instance.task_ids.action_complete()
            self.assertEqual(instance.state, "done")
            self.assertEqual(len(instance.node_instance_ids), 4)

    def test_cancel_closes_pending_work_without_erasing_history(self):
        instance = self.instance(self.published())
        instance.action_cancel()
        self.assertEqual(instance.state, "cancelled")
        self.assertEqual(instance.task_ids.state, "cancelled")
        before = len(instance.log_ids)
        instance.action_cancel()
        self.assertEqual(len(instance.log_ids), before)
        with self.assertRaises(UserError):
            instance.task_ids.action_complete()

    def test_archived_template_and_missing_business_record_cannot_start(self):
        definition = self.published()
        definition.active = False
        with self.assertRaises(UserError):
            self.instance(definition)
        definition = self.published(model=True)
        with self.assertRaises(UserError):
            self.instance(definition)
        self.assertFalse(
            self.env["workflow.instance"].search(
                [("definition_id", "=", definition.id)],
            ),
        )

    def test_request_key_cannot_be_reused_for_different_business_record(self):
        definition = self.published(model=True)
        a, b = self.env["res.partner"].create([{"name": "A"}, {"name": "B"}])
        self.instance(definition, res_id=a.id)
        self.assertEqual(
            self.instance(definition, res_id=a.id).action_business_record()["res_id"],
            a.id,
        )
        with self.assertRaises(UserError):
            self.instance(definition, res_id=b.id)

    def test_core_has_standard_dependencies_and_namespaced_tables(self):
        dependencies = get_manifest("workflow_core")["depends"]
        self.assertEqual(set(dependencies), {"web", "mail", "hr"})
        for name in (
            "definition",
            "version",
            "node",
            "edge",
            "instance",
            "node.instance",
            "task",
            "execution.log",
            "token",
        ):
            self.assertTrue(
                self.env[f"workflow.{name}"]._table.startswith("abt_workflow_"),
            )
