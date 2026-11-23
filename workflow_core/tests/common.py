from odoo.tests import TransactionCase, new_test_user


def node(key, kind="task", assignee=0):
    return {
        "id": key,
        "type": kind,
        "position": {"x": 120, "y": 80},
        "data": {"label": key, "assignee_id": assignee},
    }


def edge(source, target, rule=None, default=False):
    return {
        "id": f"{source}_{target}",
        "source": source,
        "target": target,
        "data": {"default": default, "rule": rule or {}},
    }


def sequential(assignee=0):
    return {
        "nodes": [
            node("start", "start"),
            node("first", assignee=assignee),
            node("end", "end"),
        ],
        "edges": [edge("start", "first"), edge("first", "end")],
        "viewport": {"x": 10, "y": 20, "zoom": 0.8},
    }


class WorkflowCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_manager",
            groups="workflow_core.group_manager",
        )
        cls.worker = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_worker",
            groups="workflow_core.group_executor",
        )
        cls.other = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_other",
            groups="workflow_core.group_executor",
        )
        cls.designer = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_designer",
            groups="workflow_core.group_designer",
        )
        cls.publisher = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_publisher",
            groups="workflow_core.group_publisher",
        )
        cls.viewer = new_test_user(
            cls.env(context={**cls.env.context, "no_reset_password": True}),
            login="workflow_viewer",
            groups="workflow_core.group_viewer",
        )

    def definition(self, model=False):
        return (
            self.env["workflow.definition"]
            .with_user(self.manager)
            .create(
                {
                    "name": "Test workflow",
                    "model_id": self.env.ref("base.model_res_partner").id
                    if model
                    else False,
                },
            )
        )

    def published(self, graph=None, model=False):
        definition = self.definition(model)
        version = definition.version_ids
        version.save_graph(graph or sequential(self.worker.id), 0)
        version.with_user(self.publisher).action_publish(1)
        return definition

    def instance(self, definition, user=None, key="first-request", res_id=0):
        action = definition.with_user(user or self.worker).action_start(res_id, key)
        return (
            self.env["workflow.instance"]
            .browse(action["params"]["instance_id"])
            .with_user(user or self.worker)
        )
