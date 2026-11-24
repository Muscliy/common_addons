from odoo.tests import HttpCase, new_test_user, tagged

from .common import sequential


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
        preview = definition.copy({"name": "Saved canvas preview"})
        graph = sequential()
        graph["nodes"][0]["position"] = {"x": 0, "y": 0}
        graph["nodes"][1]["position"] = {"x": 230, "y": 0}
        graph["nodes"][1]["type"] = "condition"
        graph["nodes"][2]["position"] = {"x": 230, "y": 140}
        graph["edges"][1].update(sourceHandle="bottom", targetHandle="top")
        graph["edges"][1]["data"]["rule"] = {
            "all": [{"field": "total_amount", "op": "ge", "value": 3000}],
        }
        preview.version_ids.save_graph(graph, 0)
        action = self.env.ref("workflow_core.definitions")
        self.browser_js(
            f"/web?action={action.id}",
            r"""
            (async () => {
                const wait = async (condition, label) => {
                    const until = Date.now() + 20000;
                    while (Date.now() < until) {
                        const value = condition();
                        if (value) return value;
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
                const templateCard = () => [...document.querySelectorAll('.o_kanban_view .o_kanban_record')]
                    .find(record => record.textContent.includes('Browser workflow'));
                await wait(() => document.querySelector('.o_kanban_group'), 'template groups');
                document.querySelectorAll('.o_kanban_group.o_column_folded .o_kanban_header')
                    .forEach(header => header.click());
                await wait(templateCard, 'default template kanban');
                if (templateCard().querySelector('.o_workflow_preview, .badge, footer')) {
                    throw new Error('Template cards must show only icon, name, description and manager');
                }
                const icon = templateCard().querySelector('img[name="icon"]');
                if (!icon || !icon.src.endsWith('/workflow_core/static/description/icon.svg')) {
                    throw new Error('Templates without uploaded icons must show the default icon');
                }
                const manager = templateCard().querySelector('[name="manager_id"]');
                if (!manager?.textContent.includes('workflow_ui')) {
                    throw new Error('Template cards must display the manager name');
                }
                document.querySelector('.o_switch_view.o_list').click();
                await wait(() => document.querySelector('.o_list_view'), 'list view switch');
                const row = [...document.querySelectorAll('.o_data_row')]
                    .find(record => record.textContent.includes('Browser workflow'));
                if (!row?.querySelector('img[name="icon"]') || row.getBoundingClientRect().height < 64) {
                    throw new Error('Template rows must show an icon with comfortable spacing');
                }
                document.querySelector('.o_switch_view.o_kanban').click();
                await wait(templateCard, 'return to kanban');
                templateCard().click();
                await wait(() => document.querySelector('.o_form_view'), 'template detail');
                document.querySelector('.o_form_view button[name="action_designer"]').click();
                await click('插入示例');
                if (!/\/workflow-designer\/[0-9]+$/.test(location.pathname)) {
                    throw new Error('Designer URL is missing the version ID');
                }
                await wait(() => document.querySelectorAll('.react-flow__node').length === 3, 'nodes');
                const handle = document.querySelector('[data-id="start"] [data-handleid="right"]');
                const bounds = handle.getBoundingClientRect();
                const hit = document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y - bounds.height / 4);
                const freePort = document.querySelector('[data-id="start"] [data-handleid="top"]');
                if (!handle.classList.contains('wf-handle-connected') ||
                    freePort.classList.contains('wf-handle-connected') || getComputedStyle(handle).opacity !== '1') {
                    throw new Error('Connected ports must be marked and visible without hover');
                }
                if (getComputedStyle(handle).width !== '14px' || hit !== handle) {
                    throw new Error('The connection handle must accept input outside the visible dot');
                }
                const task = document.querySelector('[data-id="task"]');
                const card = () => document.querySelector('[data-id="task"] .wf-node');
                const defaultBackground = getComputedStyle(card()).backgroundColor;
                task.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
                await wait(() => document.querySelector('.wf-node-actions'), 'node actions');
                document.querySelector('.wf-node-swatches button[aria-label="浅绿"]').click();
                await wait(() => card().classList.contains('wf-color-green'), 'node color selection');
                if (getComputedStyle(card()).backgroundColor === defaultBackground) {
                    throw new Error('Selected node background color did not render');
                }
                await click('编辑属性');
                await wait(() => document.querySelector('#wf-node-name'), 'properties');
                const name = document.querySelector('#wf-node-name');
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(name, '浏览器确认任务');
                name.dispatchEvent(new Event('input', { bubbles: true }));
                [...document.querySelectorAll('.o_breadcrumb .breadcrumb-item')]
                    .find(item => item.textContent.trim() === '流程模板').click();
                await wait(() => document.querySelector('.modal button[data-hotkey="x"]'), 'unsaved changes prompt');
                document.querySelector('.modal button[data-hotkey="x"]').click();
                await wait(() => !document.querySelector('.modal') && button('保存'), 'stay on canvas');
                await click('保存');
                await wait(() => !button('保存').disabled && !document.querySelector('[role=alert]'), 'save');
                await click('校验');
                await wait(() => !button('发布').disabled, 'validation');
                await click('发布');
                await wait(() => button('启动流程'), 'publish');
                if (button('保存')) throw new Error('Published canvas remained editable');
                await wait(() => document.querySelector('.wf-color-green'), 'published node background');
                await click('启动流程');
                const fileInput = await wait(() => document.querySelector(
                    '.modal .o_field_widget[name="attachment_ids"] input[type="file"]'
                ), 'native attachment uploader');
                const transfer = new DataTransfer();
                transfer.items.add(new File(['receipt for test'], 'receipt.txt', { type: 'text/plain' }));
                fileInput.files = transfer.files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                await wait(() => document.querySelector('.modal .o_attachment_many2many')?.textContent.includes('receipt.txt'),
                    'uploaded receipt');
                (await wait(() => document.querySelector('.modal button[name="action_submit"]'), 'submit workflow')).click();
                await wait(() => button('完成任务'), 'task created');
                const attachment = await wait(() => document.querySelector('.wf-runtime [aria-label="发起附件"] a'), 'runtime attachment');
                if (!attachment.textContent.includes('receipt.txt') || await (await fetch(attachment.href)).text() !== 'receipt for test') {
                    throw new Error('Submitted attachment was not available in the workflow');
                }
                await click('流程详情');
                await wait(() => document.querySelector('.o_form_view .o_attachment_many2many')?.textContent.includes('receipt.txt'),
                    'attachment in native workflow details');
                (await wait(() => document.querySelector('.o_form_view button[name="action_monitor"]'), 'open runtime from details')).click();
                await wait(() => button('完成任务'), 'return to workflow');
                if (document.querySelector('.react-flow')) throw new Error('Runtime should open without the canvas');
                if (!document.querySelector('.wf-runtime')) throw new Error('Runtime page missing');
                if (!/\/workflow-monitor\/[0-9]+$/.test(location.pathname)) {
                    throw new Error('Monitor URL is missing the instance ID');
                }
                await click('完成任务');
                await wait(() => document.querySelector('.wf-heading').textContent.includes('已完成'), 'completion');
                if (button('完成任务')) throw new Error('Completed task remained actionable');
                if (document.querySelectorAll('.wf-progress-done').length !== 3) throw new Error('Runtime states incorrect');
                await click('查看流程图');
                await wait(() => document.querySelectorAll('.wf-state-done').length === 3, 'read-only graph');
                await click('返回办理');
                await wait(() => document.querySelector('.wf-runtime') && !document.querySelector('.react-flow'), 'return to runtime');
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
        self.assertEqual(
            instance.version_id.node_ids.filtered(
                lambda node: node.key == "task",
            ).background_color,
            "green",
        )
        self.browser_js(
            f"/odoo/workflow-designer/{preview.version_ids.id}",
            "console.log('test successful');",
            """[...document.querySelectorAll('.react-flow__edge-text')]
                .some(label => label.textContent === '≥ 3,000')""",
            login=user.login,
            timeout=60,
        )
        for path, label, view in (
            (
                f"/odoo/workflow-designer/{instance.version_id.id}",
                "流程模板",
                ".o_form_view",
            ),
            (f"/odoo/workflow-monitor/{instance.id}", "流程实例", ".o_list_view"),
        ):
            self.browser_js(
                path,
                f"""
                (async () => {{
                    const parent = [...document.querySelectorAll('.o_breadcrumb .breadcrumb-item')]
                        .find(button => button.textContent.trim() === '{label}');
                    parent.click();
                    for (let i = 0; i < 400; i++) {{
                        if (document.querySelector('{view}') && !document.querySelector('.o_workflow_action')) {{
                            console.log('test successful');
                            return;
                        }}
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }}
                    throw new Error('Could not return from the workflow breadcrumb');
                }})();
                """,
                "!!document.querySelector('.wf-runtime') || document.querySelectorAll('.react-flow__node').length === 3",
                login=user.login,
                timeout=60,
            )
