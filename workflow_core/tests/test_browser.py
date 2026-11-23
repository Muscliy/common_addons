from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestWorkflowBrowser(HttpCase):
    def test_owl_bridge(self):
        self.browser_js(
            "/web/tests?headless&loglevel=2&tag=workflow_core",
            "",
            "",
            login="admin",
            timeout=120,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=lambda message: "[HOOT]" not in message,
        )

    def test_design_publish_execute_monitor(self):
        user = new_test_user(
            self.env(context={**self.env.context, "no_reset_password": True}),
            login="workflow_ui",
            groups="workflow_core.group_manager",
        )
        definition = (
            self.env["workflow.definition"]
            .with_user(user)
            .create({"name": "Browser workflow"})
        )
        action = self.env["ir.actions.client"].create(
            {
                "name": "Workflow test",
                "tag": "workflow_core.canvas",
                "params": {"version_id": definition.version_ids.id},
            },
        )
        self.browser_js(
            f"/web?action={action.id}",
            r"""
            (async () => {
                const wait = async (condition, label) => {
                    const until = Date.now() + 20000;
                    while (Date.now() < until) {
                        if (condition()) return;
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                    throw new Error(`Timed out: ${label}; ${document.querySelector('[role=alert]')?.textContent}`);
                };
                const button = (label) => [...document.querySelectorAll('.o_workflow_action button')]
                    .find(el => el.textContent.trim() === label);
                const click = async (label) => {
                    await wait(() => button(label) && !button(label).disabled, label);
                    button(label).click();
                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    await wait(() => !document.querySelector('.wf-loading'), `${label} finished`);
                };
                await click('插入示例');
                await wait(() => document.querySelectorAll('.react-flow__node').length === 3, 'nodes');
                const handle = document.querySelector('[data-id="start"] .react-flow__handle.source');
                const bounds = handle.getBoundingClientRect();
                const hit = document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y - bounds.height / 4);
                if (getComputedStyle(handle).width !== '14px' || hit !== handle) {
                    throw new Error('The connection handle must accept input outside the visible dot');
                }
                document.querySelector('[data-id="task"]').click();
                await wait(() => document.querySelector('#wf-node-name'), 'properties');
                const name = document.querySelector('#wf-node-name');
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(name, '浏览器确认任务');
                name.dispatchEvent(new Event('input', { bubbles: true }));
                await click('保存');
                await wait(() => !button('保存').disabled && !document.querySelector('[role=alert]'), 'save');
                await click('校验');
                await wait(() => !button('发布').disabled, 'validation');
                await click('发布');
                await wait(() => button('启动流程'), 'publish');
                if (button('保存')) throw new Error('Published canvas remained editable');
                await click('启动流程');
                await wait(() => button('完成任务'), 'task created');
                await click('完成任务');
                await wait(() => document.querySelector('.wf-heading').textContent.includes('已完成'), 'completion');
                if (button('完成任务')) throw new Error('Completed task remained actionable');
                if (document.querySelectorAll('.wf-state-done').length !== 3) throw new Error('Monitor states incorrect');
                console.log('test successful');
            })();
        """,
            login=user.login,
            timeout=120,
        )
        instance = self.env["workflow.instance"].search(
            [("definition_id", "=", definition.id)],
        )
        self.assertEqual(instance.state, "done")
        self.assertEqual(instance.task_ids.name, "浏览器确认任务")
