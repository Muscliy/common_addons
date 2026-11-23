const stepStatuses = {
    approved: "已通过",
    done: "已完成",
    pending: "待审批",
    waiting: "等待办理",
    running: "进行中",
    rejected: "已拒绝",
    cancel: "已取消",
    cancelled: "已取消",
    upcoming: "未到达",
};

export function runtimeProgress(canvas) {
    const nodes = new Map(canvas.graph.nodes.map((node) => [node.id, node]));
    const approvals = new Map((canvas.approvals || []).map((item) => [item.activation_id, item]));
    const tasks = new Map(canvas.tasks.map((item) => [item.activation_id, item]));
    const projects = new Map((canvas.project_tasks || []).map((item) => [item.activation_id, item]));
    const progress = [];
    for (const execution of canvas.executions) {
        const node = nodes.get(execution.node);
        if (!node || ["condition", "fork", "join"].includes(node.type)) {
            continue;
        }
        const approval = approvals.get(execution.id);
        if (approval) {
            for (const review of approval.reviews) {
                const label = approval.reviews.length > 1
                    ? [node.data.label, "第" + review.sequence + "级"].join(" · ") : node.data.label;
                progress.push({
                    key: "review-" + review.id,
                    node: node.id,
                    label,
                    person: review.actor || review.reviewers.join("、"),
                    state: review.state,
                    status: review.state === "waiting" ? "等待前级" : stepStatuses[review.state],
                });
            }
            continue;
        }
        const task = tasks.get(execution.id);
        const project = projects.get(execution.id);
        const person = node.type === "start"
            ? canvas.instance_starter
            : task?.actor || task?.assignee || project?.assignees.join("、");
        progress.push({
            key: "activation-" + execution.id,
            node: node.id,
            label: node.data.label,
            person,
            state: execution.state,
            status: stepStatuses[execution.state],
        });
    }
    if (canvas.instance_state === "running" && !canvas.executions.some((execution) => nodes.get(execution.node)?.type === "end")) {
        progress.push({ key: "end", label: "完成", state: "upcoming", status: stepStatuses.upcoming });
    }
    return progress;
}

export function runtimeApprovalHistory(approvals) {
    return (approvals || []).flatMap((approval) => approval.reviews
        .filter((review) => ["approved", "rejected"].includes(review.state))
        .map((review) => ({ ...review, name: approval.name, multiLevel: approval.reviews.length > 1 })))
        .sort((a, b) => (b.reviewed_at || "").localeCompare(a.reviewed_at || "") || b.id - a.id);
}
