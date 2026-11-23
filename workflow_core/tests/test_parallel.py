from copy import deepcopy

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import WorkflowCase, edge, node, parallel_graph, sequential


@tagged("post_install", "-at_install")
class TestParallel(WorkflowCase):
    def test_condition_inside_branch_does_not_wait_for_unselected_path(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"] += [
            node("choice", "condition"),
            node("alternate", assignee=self.worker.id),
        ]
        graph["edges"] = [e for e in graph["edges"] if e["id"] != "fork_left"] + [
            edge("fork", "choice"),
            edge("choice", "left", default=True),
            edge(
                "choice",
                "alternate",
                {"all": [{"field": "active", "op": "eq", "value": False}]},
            ),
            edge("alternate", "join"),
        ]
        definition = self.published(graph, model=True)
        partner = self.env["res.partner"].create({"name": "Branch condition"})
        instance = self.instance(definition, res_id=partner.id)
        self.assertFalse(self.task(instance, "alternate"))
        self.task(instance, "left").action_complete()
        self.task(instance, "right").action_complete()
        self.assertEqual(self.task(instance, "after").state, "pending")

    def test_empty_branch_arrives_and_waits_for_human_branch(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "left"]
        graph["edges"] = [
            e for e in graph["edges"] if e["source"] != "left" and e["target"] != "left"
        ] + [edge("fork", "join")]
        instance = self.begin_parallel(graph)
        self.assertEqual(instance.task_ids.name, "right")
        self.task(instance, "right").action_complete()
        self.assertEqual(self.task(instance, "after").state, "pending")

    def test_consecutive_forks_do_not_reuse_previous_scope_children(self):
        graph = parallel_graph(self.worker.id)
        second = parallel_graph(self.worker.id)
        renamed = {n["id"]: f"second_{n['id']}" for n in second["nodes"]}
        for n in second["nodes"]:
            n["id"] = renamed[n["id"]]
            if n["type"] == "fork":
                n["data"]["config"]["join"] = "second_join"
        graph["nodes"] = [
            n for n in graph["nodes"] if n["id"] not in ("after", "end")
        ] + [n for n in second["nodes"] if n["id"] != "second_start"]
        graph["edges"] = [
            e for e in graph["edges"] if e["source"] not in ("join", "after")
        ] + [edge("join", "second_fork")]
        graph["edges"] += [
            edge(renamed[e["source"]], renamed[e["target"]])
            for e in second["edges"]
            if e["source"] != "start"
        ]
        instance = self.begin_parallel(graph)
        for key in ("left", "right", "second_left", "second_right", "second_after"):
            self.task(instance, key).action_complete()
        self.assertEqual(instance.state, "done")
        self.assertEqual(len(instance.token_ids), 5)

    def begin_parallel(self, graph=None):
        return self.instance(self.published(graph or parallel_graph(self.worker.id)))

    def task(self, instance, key):
        return instance.task_ids.filtered(
            lambda t: t.node_instance_id.node_id.key == key,
        )

    def test_waits_for_all_branches_and_advances_exactly_once(self):
        instance = self.begin_parallel()
        self.assertEqual(set(instance.task_ids.mapped("name")), {"left", "right"})
        self.assertEqual(len(instance.token_ids), 3)
        self.task(instance, "right").action_complete("right done")
        join = instance.node_instance_ids.filtered(lambda a: a.node_id.key == "join")
        self.assertEqual(join.state, "waiting")
        self.assertFalse(self.task(instance, "after"))
        self.task(instance, "left").action_complete("left done")
        self.task(instance, "left").action_complete("duplicate")
        self.assertEqual(join.state, "done")
        self.assertEqual(len(self.task(instance, "after")), 1)
        self.assertEqual(
            len(instance.log_ids.filtered(lambda log: log.event == "parallel_joined")),
            1,
        )
        self.task(instance, "after").action_complete()
        self.assertEqual(instance.state, "done")
        self.assertEqual(
            sorted(instance.token_ids.mapped("state")),
            ["done", "joined", "joined"],
        )

    def test_nested_forks_have_independent_join_scopes(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"] += [
            node("inner", "fork"),
            node("inner_join", "join"),
            node("a", assignee=self.worker.id),
            node("b", assignee=self.worker.id),
        ]
        graph["nodes"][-4]["data"]["config"] = {"join": "inner_join"}
        graph["edges"] = [e for e in graph["edges"] if e["id"] != "fork_left"] + [
            edge("fork", "inner"),
            edge("inner", "a"),
            edge("inner", "b"),
            edge("a", "inner_join"),
            edge("b", "inner_join"),
            edge("inner_join", "left"),
        ]
        instance = self.begin_parallel(graph)
        self.task(instance, "right").action_complete()
        self.task(instance, "a").action_complete()
        self.assertFalse(self.task(instance, "left"))
        self.task(instance, "b").action_complete()
        self.assertTrue(self.task(instance, "left"))
        self.assertFalse(self.task(instance, "after"))
        self.task(instance, "left").action_complete()
        self.task(instance, "after").action_complete()
        self.assertEqual(instance.state, "done")
        self.assertEqual(len(instance.token_ids), 5)
        self.assertEqual(
            len(instance.log_ids.filtered(lambda log: log.event == "parallel_joined")),
            2,
        )

    def test_split_failure_rolls_back_all_sibling_work(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"][3]["data"]["assignee_id"] = self.other.id
        definition = self.published(graph)
        self.other.active = False
        with self.assertRaises(UserError):
            self.instance(definition)
        self.assertFalse(
            self.env["workflow.instance"].search(
                [("definition_id", "=", definition.id)],
            ),
        )
        self.assertFalse(
            self.env["workflow.token"].search(
                [("instance_id.definition_id", "=", definition.id)],
            ),
        )

    def test_join_and_last_completion_roll_back_if_successor_fails(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"][-2]["data"]["assignee_id"] = self.other.id
        instance = self.begin_parallel(graph)
        self.task(instance, "left").action_complete()
        self.other.active = False
        before = len(instance.log_ids)
        with self.assertRaises(UserError):
            self.task(instance, "right").action_complete("must roll back")
        self.assertEqual(self.task(instance, "right").state, "pending")
        self.assertFalse(self.task(instance, "right").comment)
        self.assertEqual(len(instance.log_ids), before)
        self.assertEqual(
            sorted(instance.token_ids.mapped("state")),
            ["joined", "waiting", "waiting"],
        )
        self.other.active = True
        self.task(instance, "right").action_complete()
        self.assertEqual(len(self.task(instance, "after")), 1)

    def test_cancel_closes_branches_tokens_and_waiting_join(self):
        instance = self.begin_parallel()
        self.task(instance, "left").action_complete()
        instance.action_cancel()
        self.assertEqual(self.task(instance, "left").state, "done")
        self.assertEqual(self.task(instance, "right").state, "cancelled")
        self.assertFalse(
            instance.token_ids.filtered(lambda t: t.state in ("active", "waiting")),
        )
        self.assertEqual(
            instance.node_instance_ids.filtered(
                lambda a: a.node_id.key == "join",
            ).state,
            "cancelled",
        )
        with self.assertRaises(UserError):
            self.task(instance, "right").action_complete()

    def test_tokens_are_readonly_and_scoped_to_participants(self):
        instance = self.begin_parallel()
        token = instance.token_ids[:1]
        for operation in (
            lambda: token.write({"state": "done"}),
            token.unlink,
            token.copy,
            lambda: (
                self.env["workflow.token"]
                .with_user(self.worker)
                .create({"instance_id": instance.id, "key": "forged"})
            ),
            lambda: token.with_user(self.other).read(["state"]),
        ):
            with self.assertRaises(AccessError):
                operation()
        self.assertEqual(
            token.with_user(self.viewer).read(["state"])[0]["state"],
            "waiting",
        )

    def test_existing_pending_task_without_token_can_resume(self):
        instance = self.instance(self.published(sequential(self.worker.id)))
        # Reproduce the stored shape of a pre-token instance without rewriting its version/tasks.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE abt_workflow_node_instance SET token_id = NULL WHERE instance_id = %s",
            [instance.id],
        )
        self.env.cr.execute(
            "DELETE FROM abt_workflow_token WHERE instance_id = %s",
            [instance.id],
        )
        self.env.invalidate_all()
        task, version = instance.task_ids, instance.version_id
        task.action_complete()
        self.assertEqual(instance.state, "done")
        self.assertEqual(instance.version_id, version)
        self.assertEqual(instance.task_ids, task)
        self.assertEqual(instance.token_ids.state, "done")

    def test_invalid_parallel_shapes_are_rejected_on_publish(self):
        base = parallel_graph(self.worker.id)
        mutations = [
            lambda g: g["nodes"][1]["data"]["config"].update(join="left"),
            lambda g: g["edges"].append(edge("left", "right")),
            lambda g: g["edges"].__setitem__(3, edge("left", "end")),
            lambda g: g["edges"].__setitem__(1, edge("fork", "right")),
            lambda g: g["edges"].__setitem__(3, edge("left", "right")),
            lambda g: g["nodes"].append(node("orphan", "join")),
        ]
        for mutate in mutations:
            graph = deepcopy(base)
            mutate(graph)
            version = self.definition().version_ids
            with self.assertRaises(ValidationError):
                version.save_graph(graph, 0)
                version.action_publish(1)
