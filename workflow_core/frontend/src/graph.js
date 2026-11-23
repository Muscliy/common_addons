export const labels = { start: '开始', end: '结束', task: '人工任务', condition: '条件分支', fork: '并行分支', join: '并行汇合', approval: '审批', project_task: '项目任务' };
export const states = { waiting: '等待办理', done: '已完成', cancelled: '已取消', running: '进行中', rejected: '已拒绝' };

export const backgrounds = { '': '默认', blue: '浅蓝', green: '浅绿', amber: '浅橙', gray: '浅灰' };
export const defaultHandles = { sourceHandle: 'right', targetHandle: 'left' };

export function connectedSides(edges) {
    const sides = new Map();
    const mark = (node, side) => {
        if (!sides.has(node)) sides.set(node, new Set());
        sides.get(node).add(side);
    };
    for (const edge of edges) {
        mark(edge.source, edge.sourceHandle);
        mark(edge.target, edge.targetHandle);
    }
    return sides;
}

export function serialise(nodes, edges, viewport) {
    return {
        nodes: nodes.map(({ id, type, position, data }) => ({
            id, type, position, data: { label: data.label, assignee_id: data.assignee_id || 0,
                ...(data.background_color ? { background_color: data.background_color } : {}),
                ...(data.config && Object.keys(data.config).length ? { config: data.config } : {}) },
        })),
        edges: edges.map(({ id, source, target, sourceHandle, targetHandle, data }) => ({
            id, source, target,
            ...(sourceHandle && sourceHandle !== defaultHandles.sourceHandle ? { sourceHandle } : {}),
            ...(targetHandle && targetHandle !== defaultHandles.targetHandle ? { targetHandle } : {}),
            data: { default: !!data?.default, rule: data?.rule || {} },
        })),
        viewport,
    };
}

export function exampleGraph() {
    return {
        nodes: [
            { id: 'start', type: 'start', position: { x: 80, y: 140 }, data: { label: '开始', assignee_id: 0 } },
            { id: 'task', type: 'task', position: { x: 340, y: 140 }, data: { label: '需求确认', assignee_id: 0 } },
            { id: 'end', type: 'end', position: { x: 600, y: 140 }, data: { label: '结束', assignee_id: 0 } },
        ],
        edges: [
            { id: 'start_task', source: 'start', target: 'task', data: { default: false, rule: {} } },
            { id: 'task_end', source: 'task', target: 'end', data: { default: false, rule: {} } },
        ],
        viewport: { x: 0, y: 0, zoom: 1 },
    };
}
