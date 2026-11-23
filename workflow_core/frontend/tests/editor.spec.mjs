import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const graph = {
    nodes: [
        { id: 'start', type: 'start', position: { x: 50, y: 100 }, data: { label: '开始', assignee_id: 0 } },
        { id: 'task', type: 'task', position: { x: 320, y: 100 }, data: { label: '确认需求', assignee_id: 0 } },
        { id: 'end', type: 'end', position: { x: 600, y: 100 }, data: { label: '结束', assignee_id: 0 } },
    ], edges: [], viewport: { x: 0, y: 0, zoom: 1 },
};

async function mount(page, editable = true, initial = graph, extras = {}) {
    await page.route('https://workflow.test/**', route => route.fulfill({
        contentType: 'text/html', body: '<div class="o_workflow_action" style="height:800px"><div id="root" style="height:100%"></div></div>',
    }));
    await page.goto('https://workflow.test/');
    await page.addStyleTag({ content: readFileSync(resolve(root, 'static/lib/workflow_canvas.css'), 'utf8') });
    await page.addStyleTag({ content: `
        .wf-editor {display:grid;grid-template-columns:160px minmax(0,1fr) 280px;height:100%}
        .wf-node{background:white;padding:16px;width:164px;border:1px solid gray}
        .wf-library,.wf-properties{padding:12px}.wf-mobile-tabs{display:none}
        .wf-canvas{min-width:0}.wf-palette-node{display:block;margin:12px}
    ` });
    await page.addScriptTag({ content: readFileSync(resolve(root, 'static/lib/workflow_canvas.js'), 'utf8') });
    await page.evaluate(({ editable, graph, extras }) => {
        window.dirty = 0;
        window.props = { canvas: { id: 1, revision: 0, graph, node_types: [['start', '开始'], ['task', '人工任务'], ['condition', '条件分支'], ['end', '结束']],
            can_edit: editable, fields: { color: { string: '颜色', type: 'integer' } }, ...extras },
            assignees: [{ id: 4, name: '负责人' }], onReady: get => window.getGraph = get,
            onChange: () => window.dirty++, onComplete: () => {}, onDecision: (...args) => window.decisions = args };
        window.bridge = WorkflowCanvas.mount(document.querySelector('#root'), window.props);
    }, { editable, graph: initial, extras });
    await expect(page.locator('.react-flow__node')).toHaveCount(initial.nodes.length);
    await page.waitForFunction(() => typeof window.getGraph === 'function');
}

test('drag, properties, connection, save and remount retain the actual graph', async ({ page }) => {
    await mount(page);
    const task = page.locator('[data-id="task"]');
    const box = await task.boundingBox();
    await page.mouse.move(box.x + 80, box.y + 35);
    await page.mouse.down(); await page.mouse.move(box.x + 140, box.y + 115, { steps: 12 }); await page.mouse.up();
    await task.click();
    await page.getByLabel('节点名称').fill('修改后的任务');
    await page.getByLabel('负责人', { exact: true }).selectOption('4');
    const source = page.locator('[data-id="start"] .source');
    const target = page.locator('[data-id="task"] .target');
    const a = await source.boundingBox(), b = await target.boundingBox();
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
    await page.mouse.down(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 15 }); await page.mouse.up();
    await expect(page.locator('.react-flow__edge')).toHaveCount(1);
    const saved = await page.evaluate(() => window.getGraph());
    expect(saved.nodes[1].position.x).not.toBe(graph.nodes[1].position.x);
    expect(saved.nodes[1].data).toEqual({ label: '修改后的任务', assignee_id: 4 });
    expect(saved.edges[0].source).toBe('start');
    await page.evaluate(saved => {
        window.bridge.destroy();
        window.bridge = WorkflowCanvas.mount(document.querySelector('#root'), { ...window.props,
            canvas: { ...window.props.canvas, graph: saved }, onReady: get => window.getGraph = get });
    }, saved);
    await expect(page.locator('[data-id="task"]')).toContainText('修改后的任务');
    expect(await page.evaluate(() => window.getGraph())).toEqual(saved);
});

test('readonly mode prevents dragging, adding, editing and deletion', async ({ page }) => {
    await mount(page, false);
    await page.locator('[data-id="task"]').click();
    await expect(page.getByLabel('节点名称')).toBeDisabled();
    await expect(page.getByRole('button', { name: '人工任务', exact: true })).toBeDisabled();
    await page.keyboard.press('Delete');
    await expect(page.locator('.react-flow__node')).toHaveCount(3);
    expect(await page.evaluate(() => window.getGraph())).toEqual(graph);
    await page.evaluate(() => window.bridge.destroy());
    await expect(page.locator('.react-flow')).toHaveCount(0);
});

test('palette supports keyboard addition and node deletion removes incident edges', async ({ page }) => {
    await mount(page);
    await page.getByRole('button', { name: '人工任务', exact: true }).focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.react-flow__node')).toHaveCount(4);
    await page.getByRole('button', { name: '删除节点', exact: true }).click();
    await expect(page.locator('.react-flow__node')).toHaveCount(3);
});

test('approval levels retain typed references and order after serialization', async ({ page }) => {
    const initial = structuredClone(graph);
    initial.nodes[1].type = 'approval';
    initial.nodes[1].data.config = { levels: [{ kind: 'user', ref: 4 }] };
    await mount(page, true, initial, {
        node_types: [['start', '开始'], ['approval', '审批'], ['end', '结束']],
        node_options: { approval: { users: [{ id: 4, name: '审批人员' }],
            groups: [{ id: 7, name: '财务审批' }], fields: { user_id: { string: '负责人' } } } },
    });
    await page.locator('[data-id="task"]').click();
    await page.getByLabel('第1级审批方式').selectOption('group');
    await page.getByLabel('第1级审批人', { exact: true }).selectOption('7');
    await page.getByRole('button', { name: '添加级次' }).click();
    await page.getByLabel('第2级审批方式').selectOption('field');
    await page.getByLabel('第2级审批人', { exact: true }).selectOption('user_id');
    await page.getByRole('button', { name: '上移第2级' }).click();
    const saved = await page.evaluate(() => window.getGraph());
    expect(saved.nodes[1].data.config.levels).toEqual([
        { kind: 'field', ref: 'user_id' }, { kind: 'group', ref: 7 },
    ]);
});

test('monitor decisions carry fixed review ids and rejection requires a comment', async ({ page }) => {
    await mount(page, false, graph, { instance_id: 9, approvals: [{ id: 12, name: '财务审批',
        can_review: true, review_id: 31, reviews: [{ id: 31, sequence: 1, state: 'pending', reviewers: ['审批人员'] }] }] });
    await expect(page.getByRole('button', { name: '拒绝', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: '通过', exact: true }).click();
    expect(await page.evaluate(() => window.decisions)).toEqual([12, 31, 'approve', '']);
    await page.getByLabel('审批意见').fill('金额需要修订');
    await page.getByRole('button', { name: '拒绝', exact: true }).click();
    expect(await page.evaluate(() => window.decisions)).toEqual([12, 31, 'reject', '金额需要修订']);
    await page.evaluate(() => window.bridge.update({ ...window.props,
        canvas: { ...window.props.canvas, approvals: window.props.canvas.approvals.map(a => ({ ...a, can_review: false })) } }));
    await expect(page.getByRole('button', { name: '通过', exact: true })).toHaveCount(0);
});

test('parallel pairing is editable, serialized and frozen in monitor mode', async ({ page }) => {
    const initial = structuredClone(graph);
    initial.nodes[1].type = 'fork';
    initial.nodes[1].data.config = { join: 'join' };
    initial.nodes.push({ id: 'join', type: 'join', position: { x: 500, y: 300 }, data: { label: '全部完成', assignee_id: 0 } });
    initial.nodes.push({ id: 'other_join', type: 'join', position: { x: 800, y: 300 }, data: { label: '第二汇合', assignee_id: 0 } });
    const types = [['start', '开始'], ['fork', '并行分支'], ['join', '并行汇合'], ['end', '结束']];
    await mount(page, true, initial, { node_types: types });
    await page.locator('[data-id="task"]').click();
    await page.getByLabel('汇合节点', { exact: true }).selectOption('other_join');
    const saved = await page.evaluate(() => window.getGraph());
    expect(saved.nodes[1].data.config).toEqual({ join: 'other_join' });
    await page.evaluate(saved => window.bridge.update({ ...window.props,
        canvas: { ...window.props.canvas, id: 2, graph: saved, can_edit: false,
            instance_id: 9, executions: [{ node: 'join', state: 'waiting' }] } }), saved);
    await page.locator('[data-id="task"]').click();
    await expect(page.getByLabel('汇合节点', { exact: true })).toBeDisabled();
    await expect(page.locator('[data-id="join"]')).toContainText('等待分支');
});
