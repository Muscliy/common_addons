from odoo.tests import HttpCase, tagged

from .common import ApprovalCase


@tagged("post_install", "-at_install")
class TestApprovalBrowser(ApprovalCase, HttpCase):
    def _monitor_action(self, instance):
        return self.env["ir.actions.client"].create(
            {
                "name": "Approval browser test",
                "tag": "workflow_core.monitor",
                "params": {"instance_id": instance.id},
            },
        )

    def test_two_users_approve_sequentially_in_monitor(self):
        instance, approval = self.begin()
        action = self.env.ref(
            "workflow_project.todo_approvals",
            raise_if_not_found=False,
        ) or self.env.ref("workflow_tier_validation.my_approvals")
        code = r"""
            (async () => {
                const wait = async condition => {
                    const until = Date.now() + 20000;
                    while (!condition()) {
                        if (Date.now() > until) throw new Error('Approval UI timeout: ' + document.body.innerText);
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                };
                await wait(() => document.querySelector('.o_list_view .o_data_row'));
                document.querySelector('.o_list_view .o_data_row .o_data_cell').click();
                const button = () => [...document.querySelectorAll('.wf-runtime button')].find(el => el.textContent === '通过');
                await wait(() => button() && !button().disabled);
                if (document.querySelector('.react-flow')) throw new Error('Approval opened the graph');
                if (document.querySelectorAll('.wf-timeline .wf-progress-person').length !== 3) {
                    throw new Error('The timeline must show the starter and both approval people');
                }
                button().click();
                await wait(() => !document.querySelector('.wf-loading') && !button());
                await wait(() => document.querySelector('[aria-label="审批记录"] tbody tr'));
                if (!document.querySelector('[aria-label="审批记录"] tbody tr').textContent.includes('已通过')) {
                    throw new Error('The decision must appear in the approval history');
                }
                if (document.querySelector('.o_workflow_action [role=alert]')) throw new Error('Approval failed');
                console.log('test successful');
            })();
        """
        self.browser_js(
            f"/web?action={action.id}",
            code,
            login=self.first.login,
            timeout=90,
        )
        self.env.invalidate_all()
        self.assertEqual(approval.state, "pending")
        self.assertFalse(instance.task_ids)
        self.browser_js(
            f"/web?action={action.id}",
            code,
            login=self.second.login,
            timeout=90,
        )
        self.env.invalidate_all()
        self.assertEqual(approval.state, "approved")
        self.assertEqual(len(instance.task_ids), 1)

    def test_rpc_write_and_forged_comment_wizard_are_denied(self):
        instance, approval = self.begin()
        review = approval.review_ids[:1]
        action = self._monitor_action(instance)
        self.browser_js(
            f"/web?action={action.id}",
            f"""
            (async () => {{
                const rpc = async (model, method, args, context = {{}}) => {{
                    const response = await fetch(`/web/dataset/call_kw/${{model}}/${{method}}`, {{
                        method: 'POST', headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{jsonrpc: '2.0', method: 'call', params: {{model, method, args, kwargs: {{context}}}}}}),
                    }});
                    return response.json();
                }};
                const write = await rpc('tier.review', 'write', [[{review.id}], {{status: 'approved'}}], {{sudo: true, skip_validation_check: true}});
                if (write.error?.data?.name !== 'odoo.exceptions.AccessError') throw new Error('RPC status write allowed');
                const wizard = await rpc('comment.wizard', 'create', [{{res_model: 'workflow.approval', res_id: {approval.id},
                    review_ids: [[6, 0, [{review.id}]]], validate_reject: 'validate', comment: 'forged'}}]);
                if (wizard.error) throw new Error('Wizard fixture could not be created');
                const decision = await rpc('comment.wizard', 'add_comment', [[wizard.result]]);
                if (decision.error?.data?.name !== 'odoo.exceptions.AccessError') throw new Error('Wizard bypass allowed');
                console.log('test successful');
            }})();
        """,
            login=self.first.login,
            timeout=90,
        )
        self.env.invalidate_all()
        self.assertEqual(review.status, "pending")
        self.assertFalse(review.comment)
