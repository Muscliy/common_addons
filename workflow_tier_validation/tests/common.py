from odoo.tests import new_test_user

from odoo.addons.workflow_core.tests.common import WorkflowCase, edge, node


def approval_graph(levels: list, assignee: int = 0) -> dict:
    approval = node("approval", "approval")
    approval["data"]["config"] = {"levels": levels}
    return {
        "nodes": [
            node("start", "start"),
            approval,
            node("work", assignee=assignee),
            node("end", "end"),
        ],
        "edges": [
            edge("start", "approval"),
            edge("approval", "work"),
            edge("work", "end"),
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


class ApprovalCase(WorkflowCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        safe = cls.env(context={**cls.env.context, "no_reset_password": True})
        cls.first = new_test_user(
            safe,
            login="flow_approver_one",
            groups="workflow_tier_validation.group_approver",
        )
        cls.second = new_test_user(
            safe,
            login="flow_approver_two",
            groups="workflow_tier_validation.group_approver",
        )

    def levels(self):
        return [
            {"kind": "user", "ref": self.first.id},
            {"kind": "user", "ref": self.second.id},
        ]

    def begin(self, levels=None, model=False, res_id=0):
        definition = self.published(
            approval_graph(levels or self.levels(), self.worker.id),
            model=model,
        )
        instance = self.instance(definition, res_id=res_id)
        approval = self.env["workflow.approval"].search(
            [("instance_id", "=", instance.id)],
        )
        return instance, approval

    def decide(self, approval, user, sequence=1, decision="approve", comment="已核实"):
        review = approval.review_ids.filtered(lambda r: r.sequence == sequence)
        return approval.with_user(user).action_decide(decision, comment, review.id)
