const connectionGap = 52;
const axes = [
    { key: 'x', size: 'width', cross: 'y', crossSize: 'height', near: 'left', far: 'right' },
    { key: 'y', size: 'height', cross: 'x', crossSize: 'width', near: 'top', far: 'bottom' },
];

export function monitorPositions(nodes, edges) {
    const byId = new Map(nodes.map(node => [node.id, node]));
    const positions = new Map(nodes.map(node => [node.id, { ...node.position }]));
    for (const { key, size, cross, crossSize, near, far } of axes) {
        const neighbors = new Map();
        for (const edge of edges) {
            const forward = edge.sourceHandle === far && edge.targetHandle === near;
            const backward = edge.sourceHandle === near && edge.targetHandle === far;
            if (!forward && !backward) continue;
            const before = byId.get(forward ? edge.source : edge.target);
            const after = byId.get(forward ? edge.target : edge.source);
            if (!before?.measured?.[size] || !after?.measured?.[crossSize]
                || before.position[key] >= after.position[key]) continue;
            const overlap = Math.min(
                before.position[cross] + before.measured[crossSize],
                after.position[cross] + after.measured[crossSize],
            ) - Math.max(before.position[cross], after.position[cross]);
            if (overlap <= 0) continue;
            if (!neighbors.has(after.id)) neighbors.set(after.id, []);
            neighbors.get(after.id).push(before);
        }
        // In saved coordinate order, each preceding card has already been placed.
        const ordered = [...nodes].sort((a, b) => a.position[key] - b.position[key]);
        for (const node of ordered) {
            const position = positions.get(node.id);
            for (const before of neighbors.get(node.id) || []) {
                position[key] = Math.max(
                    position[key],
                    positions.get(before.id)[key] + before.measured[size] + connectionGap,
                );
            }
        }
    }
    return positions;
}
