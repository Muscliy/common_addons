from copy import deepcopy
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import WorkflowCase, edge, node, sequential
from odoo.addons.workflow_core.services.rules import evaluate_rule


@tagged("post_install", "-at_install")
class TestGraph(WorkflowCase):
    def test_save_reload_revision_and_atomic_failure(self):
        version = self.definition().version_ids
        graph = sequential()
        version.save_graph(graph, 0)
        self.env.invalidate_all()
        self.assertEqual(version.get_canvas()["graph"], graph)
        with self.assertRaises(UserError):
            version.save_graph(graph, 0)
        self.assertEqual(version.revision, 1)
        with patch.object(
            type(self.env["workflow.node"]),
            "create",
            side_effect=ValidationError("injected failure"),
        ):
            with self.assertRaises(ValidationError):
                version.save_graph(graph, 1)
        self.assertEqual(version.get_canvas()["graph"], graph)
        self.assertEqual(version.revision, 1)

    def test_invalid_payloads_never_replace_existing_graph(self):
        version = self.definition().version_ids
        graph = sequential()
        version.save_graph(graph, 0)
        for mutate in (
            lambda g: g["nodes"].append(deepcopy(g["nodes"][0])),
            lambda g: g["nodes"][0].update(type="python"),
            lambda g: g["nodes"][0].update(type=[]),
            lambda g: g["nodes"][0].update(position={"x": float("nan"), "y": 0}),
            lambda g: g["edges"][0].update(target="missing"),
            lambda g: g.update(viewport={"x": 0, "y": 0, "zoom": 50}),
        ):
            invalid = deepcopy(graph)
            mutate(invalid)
            with self.assertRaises(ValidationError):
                version.save_graph(invalid, 1)
            self.assertEqual(version.get_canvas()["graph"], graph)

    def test_incomplete_cycle_and_disconnected_graph_cannot_publish(self):
        for graph in (
            {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}},
            {**sequential(), "edges": [edge("start", "first"), edge("first", "start")]},
            {**sequential(), "nodes": [*sequential()["nodes"], node("orphan", "end")]},
        ):
            version = self.definition().version_ids
            version.save_graph(graph, 0)
            with self.assertRaises(ValidationError):
                version.action_publish(1)
            self.assertEqual(version.state, "draft")
            self.assertFalse(version.definition_id.published_version_id)

    def test_published_graph_and_version_are_frozen(self):
        definition = self.published()
        version = definition.version_ids
        for operation in (
            lambda: version.save_graph(sequential(), 1),
            lambda: version.sudo().write({"viewport": {}}),
            lambda: version.sudo().node_ids[:1].write({"name": "tamper"}),
            version.sudo().edge_ids[:1].unlink,
            version.sudo().unlink,
        ):
            with self.assertRaises(UserError):
                operation()
        with self.assertRaises(AccessError):
            definition.write({"published_version_id": False})

    def test_new_version_keeps_prior_instance_snapshot(self):
        definition = self.published()
        instance = self.instance(definition)
        old = definition.published_version_id
        action = definition.action_new_version()
        draft = (
            self.env["workflow.version"]
            .browse(action["params"]["version_id"])
            .with_user(self.manager)
        )
        graph = draft.get_canvas()["graph"]
        graph["nodes"][1]["data"]["label"] = "New task"
        draft.save_graph(graph, draft.revision)
        draft.action_publish(draft.revision)
        self.assertEqual(instance.version_id, old)
        self.assertEqual(instance.task_ids.name, "first")
        self.assertEqual(self.instance(definition, key="new").task_ids.name, "New task")

    def test_safe_typed_and_or_rules(self):
        partner = self.env["res.partner"].create(
            {"name": "Example", "color": 8, "is_company": True},
        )
        rule = {
            "all": [
                {"field": "color", "op": "ge", "value": 5},
                {
                    "any": [
                        {"field": "name", "op": "eq", "value": "Example"},
                        {"field": "is_company", "op": "eq", "value": False},
                    ],
                },
            ],
        }
        self.assertTrue(evaluate_rule(rule, partner))
        for invalid in (
            {"field": "__class__", "op": "eq", "value": ""},
            {"field": "color", "op": "ge", "value": "5"},
            {"field": "color", "op": [], "value": 5},
            {"python": "record.unlink()"},
            {"all": []},
        ):
            with self.assertRaises(ValidationError):
                evaluate_rule(invalid, partner)
