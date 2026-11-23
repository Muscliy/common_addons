from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.workflow_core.tests.common import edge, node
from odoo.addons.workflow_tier_validation.tests.common import ApprovalCase


@tagged("post_install", "-at_install")
class TestExpenseRouting(ApprovalCase):
    def test_real_expense_amount_routes_at_threshold(self):
        if "hr.expense" not in self.env:
            self.skipTest("Odoo Expenses is optional")
        expense_manager = self.env.ref("hr_expense.group_hr_expense_manager")
        self.manager.sudo().write({"group_ids": [Command.link(expense_manager.id)]})
        employee = self.env["hr.employee"].create(
            {"name": "Workflow employee", "user_id": self.manager.id},
        )
        definition = self.definition()
        definition.model_id = self.env.ref("hr_expense.model_hr_expense")
        version = definition.version_ids
        model_domain = definition.fields_get(["model_id"])["model_id"]["domain"]
        self.assertIn("hr.expense", model_domain[0][2])
        amount_field = version.get_canvas()["fields"]["total_amount"]
        self.assertEqual(amount_field["type"], "monetary")

        approvals = [node("supervisor", "approval"), node("finance", "approval")]
        for approval in approvals:
            approval["data"]["config"] = {
                "levels": [{"kind": "user", "ref": self.manager.id}],
            }
        version.save_graph(
            {
                "nodes": [
                    node("start", "start"),
                    *approvals,
                    node("amount", "condition"),
                    node("end", "end"),
                ],
                "edges": [
                    edge("start", "supervisor"),
                    edge("supervisor", "amount"),
                    edge(
                        "amount",
                        "finance",
                        {"field": "total_amount", "op": "ge", "value": 3000},
                    ),
                    edge("amount", "end", default=True),
                    edge("finance", "end"),
                ],
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            },
            0,
        )
        version.action_publish(1)
        product = self.env.ref("hr_expense.expense_product_travel_accommodation")
        for amount, finance_required in ((2999, False), (3000, True)):
            with self.subTest(amount=amount):
                expense = (
                    self.env["hr.expense"]
                    .with_user(self.manager)
                    .create(
                        {
                            "name": f"Workflow expense {amount}",
                            "employee_id": employee.id,
                            "product_id": product.id,
                            "total_amount_currency": amount,
                            "tax_ids": [Command.clear()],
                        },
                    )
                )
                self.assertEqual(expense.total_amount, amount)
                with self.assertRaises(AccessError):
                    self.instance(
                        definition,
                        user=self.other,
                        key=f"denied-{amount}",
                        res_id=expense.id,
                    )
                instance = self.instance(
                    definition,
                    user=self.manager,
                    key=str(amount),
                    res_id=expense.id,
                )
                domain = [("instance_id", "=", instance.id), ("state", "=", "pending")]
                supervisor = self.env["workflow.approval"].search(domain)
                self.assertEqual(supervisor.node_instance_id.node_id.key, "supervisor")
                self.decide(supervisor, self.manager)
                finance = self.env["workflow.approval"].search(domain)
                if finance_required:
                    self.assertEqual(finance.node_instance_id.node_id.key, "finance")
                    self.assertEqual(instance.state, "running")
                    self.decide(finance, self.manager)
                else:
                    self.assertFalse(finance)
                self.assertEqual(instance.state, "done")
