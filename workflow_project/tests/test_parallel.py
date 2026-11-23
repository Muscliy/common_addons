from odoo.tests import tagged

from .common import ProjectCase
from odoo.addons.workflow_core.tests.common import parallel_graph


@tagged("post_install", "-at_install")
class TestProjectParallel(ProjectCase):
    def begin_parallel(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"][2]["type"] = "project_task"
        graph["nodes"][2]["data"].update(
            assignee_id=0,
            config={
                "mode": "create",
                "project_id": self.project.id,
                "user_ids": [self.worker.id, self.other.id],
            },
        )
        return self.begin(graph=graph)

    def test_project_and_human_branches_join_once(self):
        instance, link = self.begin_parallel()
        right = instance.task_ids
        right.action_complete()
        self.assertEqual(
            instance.node_instance_ids.filtered(
                lambda a: a.node_id.kind == "join",
            ).state,
            "waiting",
        )
        link.with_user(self.other).action_decide("complete")
        self.assertEqual(
            instance.task_ids.filtered(lambda t: t.state == "pending").name,
            "after",
        )
        self.assertEqual(
            len(instance.log_ids.filtered(lambda log: log.event == "parallel_joined")),
            1,
        )

    def test_project_cancel_closes_other_pending_branch(self):
        instance, link = self.begin_parallel()
        right = instance.task_ids
        link.with_user(self.other).action_decide("cancel", "无需继续")
        self.assertEqual(instance.state, "cancelled")
        self.assertEqual(right.state, "cancelled")
        self.assertEqual(link.project_task_id.state, "1_canceled")
