from odoo.tests import HttpCase, tagged

from .common import WorkflowCase, parallel_graph


@tagged("post_install", "-at_install")
class TestParallelBrowser(WorkflowCase, HttpCase):
    def test_two_assignees_finish_branches_and_see_join_state(self):
        graph = parallel_graph(self.worker.id)
        graph["nodes"][3]["data"]["assignee_id"] = self.other.id
        instance = self.instance(self.published(graph))
        action = self.env["ir.actions.client"].create(
            {
                "name": "Parallel browser test",
                "tag": "workflow_core.canvas",
                "params": {"instance_id": instance.id},
            },
        )
        for user, target, expected in (
            (self.worker, "join", "等待分支"),
            (self.other, "join", "已完成"),
            (self.worker, "end", "已完成"),
        ):
            self.browser_js(
                f"/web?action={action.id}",
                f"""
                (async () => {{
                    const wait = async predicate => {{
                        const end = Date.now() + 20000;
                        while (!predicate()) {{
                            if (Date.now() > end) throw new Error('Parallel UI timeout: ' + document.body.innerText);
                            await new Promise(resolve => setTimeout(resolve, 50));
                        }}
                    }};
                    const button = () => [...document.querySelectorAll('.wf-task button')]
                        .find(el => el.textContent === '完成任务' && !el.disabled);
                    await wait(() => button());
                    button().click();
                    await wait(() => !document.querySelector('.wf-loading') &&
                        document.querySelector('[data-id="{target}"]')?.textContent.includes('{expected}'));
                    if (document.querySelector('.o_workflow_action [role=alert]')) throw new Error('Parallel operation failed');
                    console.log('test successful');
                }})();
            """,
                login=user.login,
                timeout=90,
            )
        self.env.invalidate_all()
        self.assertEqual(instance.state, "done")
        self.assertEqual(len(instance.task_ids), 3)
        self.assertEqual(
            len(instance.log_ids.filtered(lambda log: log.event == "parallel_joined")),
            1,
        )
