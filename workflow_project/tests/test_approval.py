from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import ProjectCase
from odoo.addons.workflow_core.tests.common import parallel_graph


@tagged("post_install", "-at_install")
class TestProjectApproval(ProjectCase):
    def begin_approval(self, reviewer):
        group = self.env.ref(
            "workflow_tier_validation.group_approver",
            raise_if_not_found=False,
        )
        if not group:
            self.skipTest("Optional tier adapter is not installed")
        reviewer.group_ids = [Command.link(group.id)]
        graph = parallel_graph(self.worker.id)
        graph["nodes"][2]["type"] = "project_task"
        graph["nodes"][2]["data"].update(
            assignee_id=0,
            config={
                "mode": "create",
                "project_id": self.project.id,
                "user_ids": [self.worker.id],
            },
        )
        graph["nodes"][3]["type"] = "approval"
        graph["nodes"][3]["data"].update(
            assignee_id=0,
            config={"levels": [{"kind": "user", "ref": reviewer.id}]},
        )
        instance, link = self.begin(graph=graph)
        approval = self.env["workflow.approval"].search(
            [("instance_id", "=", instance.id)],
        )
        return instance, link, approval.with_user(reviewer)

    def test_approval_rejection_cancels_project_task(self):
        instance, link, approval = self.begin_approval(self.worker)
        approval.action_decide("reject", "终止采购", approval.review_ids.id)
        self.assertEqual(instance.state, "rejected")
        self.assertEqual(link.state, "cancelled")
        self.assertEqual(link.project_task_id.state, "1_canceled")

    def test_rejection_without_project_write_permission_rolls_back(self):
        instance, link, approval = self.begin_approval(self.viewer)
        with self.assertRaises(AccessError):
            approval.action_decide(
                "reject",
                "没有取消项目任务权限",
                approval.review_ids.id,
            )
        self.assertEqual(instance.state, "running")
        self.assertEqual(approval.state, "pending")
        self.assertEqual(approval.review_ids.status, "pending")
        self.assertFalse(approval.review_ids.comment)
        self.assertEqual(link.project_task_id.state, "01_in_progress")
