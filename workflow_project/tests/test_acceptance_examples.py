from odoo import Command
from odoo.tests import tagged

from .common import ProjectCase
from odoo.addons.workflow_core.tests.common import edge, node


def graph(nodes, edges):
    for index, item in enumerate(nodes):
        item["position"] = {"x": index * 220, "y": 100}
    return {"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 1}}


@tagged("post_install", "-at_install")
class TestAcceptanceExamples(ProjectCase):
    def setUp(self):
        super().setUp()
        group = self.env.ref(
            "workflow_tier_validation.group_approver",
            raise_if_not_found=False,
        )
        if not group:
            self.skipTest("需要可选审批适配器")
        (self.worker | self.other).group_ids = [Command.link(group.id)]

    def approval_node(self, key, reviewer):
        item = node(key, "approval")
        item["data"]["config"] = {"levels": [{"kind": "user", "ref": reviewer.id}]}
        return item

    def approve(self, instance, key, reviewer):
        approval = self.env["workflow.approval"].search(
            [
                ("instance_id", "=", instance.id),
                ("node_instance_id.node_id.key", "=", key),
            ],
        )
        self.assertEqual(len(approval), 1)
        approval.with_user(reviewer).action_decide(
            "approve",
            "",
            approval.review_ids.id,
        )

    def test_purchase_example_routes_both_sides_of_threshold(self):
        # 联系人 color 仅作为测试用整数输入, 模拟采购金额边界。
        purchase = graph(
            [
                node("start", "start"),
                self.approval_node("department", self.worker),
                node("amount", "condition"),
                self.approval_node("finance", self.other),
                node("end", "end"),
            ],
            [
                edge("start", "department"),
                edge("department", "amount"),
                edge(
                    "amount",
                    "finance",
                    {"field": "color", "op": "ge", "value": 5000},
                ),
                edge("amount", "end", default=True),
                edge("finance", "end"),
            ],
        )
        definition = self.published(purchase, model=True)
        for amount in (4999, 5000):
            record = self.env["res.partner"].create(
                {"name": f"采购测试 {amount}", "color": amount},
            )
            instance = self.instance(definition, key=str(amount), res_id=record.id)
            self.approve(instance, "department", self.worker)
            if amount >= 5000:
                self.assertEqual(instance.state, "running")
                self.approve(instance, "finance", self.other)
            self.assertEqual(instance.state, "done")
            self.assertEqual(
                len(
                    instance.node_instance_ids.filtered(
                        lambda item: item.node_id.key == "finance",
                    ),
                ),
                int(amount >= 5000),
            )

    def test_mold_example_runs_project_and_workshop_in_parallel(self):
        fork = node("parallel", "fork")
        fork["data"]["config"] = {"join": "join"}
        procurement = node("procurement", "project_task")
        procurement["data"]["config"] = {
            "mode": "create",
            "project_id": self.project.id,
            "user_ids": [self.other.id],
        }
        mold = graph(
            [
                node("start", "start"),
                node("design"),
                self.approval_node("technical", self.worker),
                fork,
                procurement,
                node("machining"),
                node("join", "join"),
                node("trial"),
                self.approval_node("quality", self.other),
                node("end", "end"),
            ],
            [
                edge("start", "design"),
                edge("design", "technical"),
                edge("technical", "parallel"),
                edge("parallel", "procurement"),
                edge("parallel", "machining"),
                edge("procurement", "join"),
                edge("machining", "join"),
                edge("join", "trial"),
                edge("trial", "quality"),
                edge("quality", "end"),
            ],
        )
        instance = self.instance(self.published(mold))
        instance.task_ids.action_complete()
        self.approve(instance, "technical", self.worker)
        link = self.env["workflow.project.link"].search(
            [("instance_id", "=", instance.id)],
        )
        link.project_task_id.with_user(self.other).write({"state": "1_done"})
        self.assertNotIn("trial", instance.task_ids.mapped("name"))
        instance.task_ids.filtered(
            lambda task: task.name == "machining",
        ).action_complete()
        instance.task_ids.filtered(lambda task: task.name == "trial").action_complete()
        self.approve(instance, "quality", self.other)
        self.assertEqual(instance.state, "done")
        self.assertEqual(
            len(instance.log_ids.filtered(lambda log: log.event == "parallel_joined")),
            1,
        )
