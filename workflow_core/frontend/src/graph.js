export const labels = { start: '开始', end: '结束', task: '人工任务', condition: '条件分支', approval: '审批' };
export const states = { waiting: '等待办理', done: '已完成', cancelled: '已取消', running: '进行中', rejected: '已拒绝' };

export function serialise(nodes, edges, viewport) {
    return {
        nodes: nodes.map(({ id, type, position, data }) => ({
            id, type, position, data: { label: data.label, assignee_id: data.assignee_id || 0,
                ...(data.config && Object.keys(data.config).length ? { config: data.config } : {}) },
        })),
        edges: edges.map(({ id, source, target, data }) => ({
            id, source, target, data: { default: !!data?.default, rule: data?.rule || {} },
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
