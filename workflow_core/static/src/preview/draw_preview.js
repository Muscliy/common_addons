const nodeWidth = 164;
const inset = 12;

function scaleNodes(nodes, width, height) {
    const boxes = nodes.map((node) => ({
        ...node,
        ...node.position,
        width: nodeWidth,
        height: node.type === "condition" ? 96 : 64,
    }));
    const left = Math.min(...boxes.map((node) => node.x));
    const top = Math.min(...boxes.map((node) => node.y));
    const contentWidth = Math.max(...boxes.map((node) => node.x + node.width)) - left;
    const contentHeight = Math.max(...boxes.map((node) => node.y + node.height)) - top;
    const scale = Math.min(0.78, (width - 2 * inset) / contentWidth, (height - 2 * inset) / contentHeight);
    const offsetX = (width - scale * contentWidth) / 2;
    const offsetY = (height - scale * contentHeight) / 2;
    return new Map(
        boxes.map((node) => [
            node.id,
            {
                ...node,
                x: offsetX + (node.x - left) * scale,
                y: offsetY + (node.y - top) * scale,
                width: node.width * scale,
                height: node.height * scale,
            },
        ]),
    );
}

const anchors = {
    left: [0, 0.5, -1, 0],
    right: [1, 0.5, 1, 0],
    top: [0.5, 0, 0, -1],
    bottom: [0.5, 1, 0, 1],
};

function connector(ctx, source, target, edge) {
    const [sx, sy, sdx, sdy] = anchors[edge.sourceHandle];
    const [tx, ty, tdx, tdy] = anchors[edge.targetHandle];
    const x1 = source.x + sx * source.width;
    const y1 = source.y + sy * source.height;
    const x2 = target.x + tx * target.width;
    const y2 = target.y + ty * target.height;
    const bend = Math.min(34, Math.max(4, Math.hypot(x2 - x1, y2 - y1) / 2));
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(x1 + sdx * bend, y1 + sdy * bend, x2 + tdx * bend, y2 + tdy * bend, x2, y2);
    ctx.stroke();
}

function drawNode(ctx, node, colors) {
    const { x, y, width, height } = node;
    ctx.beginPath();
    if (node.type === "condition") {
        ctx.moveTo(x + width / 2, y);
        ctx.lineTo(x + width, y + height / 2);
        ctx.lineTo(x + width / 2, y + height);
        ctx.lineTo(x, y + height / 2);
        ctx.closePath();
    } else {
        const radius = node.type === "start" || node.type === "end" ? height / 2 : Math.min(4, height / 2);
        ctx.roundRect(x, y, width, height, radius);
    }
    ctx.fillStyle = colors.surface;
    ctx.fill();
    const tint = colors[node.color];
    if (tint) {
        ctx.globalAlpha = 0.18;
        ctx.fillStyle = tint;
        ctx.fill();
        ctx.globalAlpha = 1;
    }
    ctx.strokeStyle = colors.blue;
    ctx.stroke();
    const labelWidth = (node.type === "condition" ? width * 0.58 : width) - 6;
    if (labelWidth >= 20 && height >= 13) {
        let label = node.label;
        if (ctx.measureText(label).width > labelWidth) {
            label = "";
            for (const character of node.label) {
                if (ctx.measureText(label + character + "…").width > labelWidth) {
                    break;
                }
                label += character;
            }
            label += "…";
        }
        ctx.fillStyle = colors.text;
        ctx.fillText(label, x + width / 2, y + height / 2);
    }
}

export function drawPreview(canvas, graph) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (width <= 2 * inset || height <= 2 * inset || !graph?.nodes?.length) {
        return;
    }
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    const style = getComputedStyle(canvas);
    const colors = Object.fromEntries(
        ["surface", "text", "muted", "blue", "green", "amber", "gray"].map((name) => [
            name,
            style.getPropertyValue("--wf-preview-" + name).trim(),
        ]),
    );
    const nodes = scaleNodes(graph.nodes, width, height);
    ctx.strokeStyle = colors.muted;
    for (const edge of graph.edges) {
        const source = nodes.get(edge.source);
        const target = nodes.get(edge.target);
        if (source && target) {
            connector(ctx, source, target, edge);
        }
    }
    ctx.font = "10px " + style.fontFamily;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const node of nodes.values()) {
        drawNode(ctx, node, colors);
    }
}
