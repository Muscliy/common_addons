from odoo import Command

from odoo.addons.workflow_core.tests.common import WorkflowCase, edge, node


def project_graph(project_id=0, users=None, business=False):
    task = node("project", "project_task")
    task["data"]["config"] = (
        {"mode": "business"}
        if business
        else {"mode": "create", "project_id": project_id, "user_ids": users or []}
    )
    return {
        "nodes": [node("start", "start"), task, node("after"), node("end", "end")],
        "edges": [
            edge("start", "project"),
            edge("project", "after"),
            edge("after", "end"),
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


class ProjectCase(WorkflowCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for user in (cls.manager, cls.publisher, cls.worker, cls.other):
            user.group_ids = [
                Command.link(cls.env.ref("project.group_project_user").id),
            ]
        cls.project = cls.env["project.project"].create(
            {
                "name": "Workflow integration project",
                "company_id": cls.env.company.id,
                "privacy_visibility": "employees",
            },
        )

    def begin(self, users=None, task=None, graph=None):
        if task:
            definition = (
                self.env["workflow.definition"]
                .with_user(self.manager)
                .create(
                    {
                        "name": "Linked task workflow",
                        "model_id": self.env.ref("project.model_project_task").id,
                    },
                )
            )
            version = definition.version_ids
            version.save_graph(project_graph(business=True), 0)
            version.with_user(self.publisher).action_publish(1)
        else:
            definition = self.published(
                graph
                or project_graph(
                    self.project.id,
                    (users or (self.worker | self.other)).ids,
                ),
            )
        instance = self.instance(definition, res_id=task.id if task else 0)
        link = self.env["workflow.project.link"].search(
            [("instance_id", "=", instance.id)],
        )
        return instance, link.with_user(self.worker)
