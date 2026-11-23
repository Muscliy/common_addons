import { Component, useState } from "@odoo/owl";

const nodeStates = {
    done: "已完成",
    waiting: "等待办理",
    running: "进行中",
    cancelled: "已取消",
    rejected: "已拒绝",
};
const reviewStates = {
    pending: "待审批",
    waiting: "等待前级",
    approved: "已通过",
    rejected: "已拒绝",
    cancel: "已取消",
    cancelled: "已取消",
};
const events = {
    started: "流程启动",
    node_completed: "节点完成",
    waiting: "等待办理",
    task_completed: "任务完成",
    completed: "流程完成",
    cancelled: "流程取消",
    approval_requested: "发起审批",
    approval_approved: "审批通过",
    approval_rejected: "审批拒绝",
    parallel_split: "并行分支启动",
    join_waiting: "等待分支汇合",
    parallel_joined: "分支已汇合",
    project_task_linked: "关联项目任务",
    project_task_completed: "项目任务完成",
    project_task_cancelled: "项目任务取消",
};

export class WorkflowRuntime extends Component {
    static template = "workflow_core.Runtime";
    static props = {
        canvas: Object,
        busy: Boolean,
        complete: Function,
        decide: Function,
        projectDecision: Function,
        projectOpen: Function,
    };

    setup() {
        this.comments = useState({});
        this.reviewStates = reviewStates;
        this.events = events;
        this.nodeStates = nodeStates;
    }

    get approvals() {
        return (this.props.canvas.approvals || []).filter((approval) => approval.state === "pending");
    }

    get approvalHistory() {
        return (this.props.canvas.approvals || []).filter((approval) => approval.state !== "pending");
    }

    get pendingTasks() {
        return (this.props.canvas.tasks || []).filter((task) => task.state === "pending");
    }

    get projectTasks() {
        return (this.props.canvas.project_tasks || []).filter((task) => task.state === "pending");
    }

    get progress() {
        const nodes = new Map(this.props.canvas.graph.nodes.map((node) => [node.id, node]));
        return this.props.canvas.executions.flatMap((execution) => {
            const node = nodes.get(execution.node);
            if (!node) {
                return [];
            }
            return [{
                ...execution,
                label: node.data.label,
                status: node.type === "join" && execution.state === "waiting"
                    ? "等待分支" : nodeStates[execution.state] || execution.state,
            }];
        });
    }

    get history() {
        return (this.props.canvas.logs || []).slice().reverse();
    }

    approvalKey(approval) {
        return `approval-${approval.id}-${approval.review_id}`;
    }

    handleDecision(approval, decision) {
        return this.props.decide(
            approval.id, approval.review_id, decision, this.comments[this.approvalKey(approval)] || "",
        );
    }
}
