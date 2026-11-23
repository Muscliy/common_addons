import { Component, onMounted, onWillStart, onWillDestroy, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { useSetupAction } from "@web/search/action_hook";

export class WorkflowAction extends Component {
    static template = "workflow_core.Action";
    static props = ["*"];
    static path = "workflow-designer";
    static recordParam = "version_id";

    static extractProps(action) {
        return { resId: action.params?.[this.recordParam] };
    }

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.container = useRef("canvas");
        this.state = useState({ canvas: null, error: "", busy: false, dirty: false });
        this.alive = true;
        this.assignees = [];
        this.requestKey = crypto.randomUUID();
        const params = this.props.action.params || {};
        const recordParam = this.constructor.recordParam;
        this.params = {
            [recordParam]: params[recordParam] || this.props.resId || params.resId,
        };
        useSetupAction({
            beforeLeave: () => this.confirmDiscard(),
            beforeUnload: (event) => {
                if (this.state.dirty) { event.preventDefault(); event.returnValue = ""; }
            },
        });
        onWillStart(async () => {
            await this.perform(async () => {
                await loadBundle("workflow_core.canvas");
                await this.load();
            });
        });
        onMounted(() => this.renderCanvas());
        onWillDestroy(() => { this.alive = false; this.bridge?.destroy(); this.bridge = null; });
    }

    async load() {
        if (!this.alive) return;
        const instance = this.params.instance_id;
        const recordId = instance || this.params.version_id;
        if (!Number.isSafeInteger(recordId) || recordId <= 0) {
            throw new Error(_t("链接缺少有效的流程记录编号，请从工作流菜单重新打开。"));
        }
        const canvas = await this.orm.call(instance ? "workflow.instance" : "workflow.version",
            instance ? "get_monitor" : "get_canvas", [[recordId]]);
        let assignees = canvas.assignees || [];
        if (canvas.can_edit) assignees = await this.orm.call("workflow.version", "get_assignees", [[canvas.id]]);
        if (!this.alive) return;
        this.assignees = assignees;
        this.state.canvas = canvas;
        this.state.dirty = false;
    }

    renderCanvas() {
        if (!this.alive || !this.state.canvas || !this.container.el || !globalThis.WorkflowCanvas) return;
        const props = {
            canvas: { ...this.state.canvas, can_edit: this.state.canvas.can_edit && !this.state.busy },
            assignees: this.assignees, busy: this.state.busy,
            onChange: () => { if (this.alive && this.state.canvas.can_edit) this.state.dirty = true; },
            onReady: (serialise) => { this.serialise = serialise; },
            onComplete: (id, comment) => this.complete(id, comment),
            onDecision: (id, reviewId, decision, comment) => this.decide(id, reviewId, decision, comment),
            onProjectDecision: (id, decision, comment) => this.projectDecision(id, decision, comment),
            onProjectOpen: (id) => this.projectOpen(id),
        };
        if (this.bridge) this.bridge.update(props);
        else this.bridge = globalThis.WorkflowCanvas.mount(this.container.el, props);
    }

    async perform(callback) {
        if (this.state.busy) return;
        this.state.busy = true; this.state.error = ""; this.renderCanvas();
        try {
            await callback();
        } catch (error) {
            if (this.alive) this.state.error = error.data?.message || error.message || _t("操作失败，请重试。");
        } finally {
            if (this.alive) { this.state.busy = false; this.renderCanvas(); }
        }
    }

    async save() {
        if (!this.serialise || !this.state.canvas.can_edit) return;
        const canvas = await this.orm.call("workflow.version", "save_graph", [
            [this.state.canvas.id], this.serialise(), this.state.canvas.revision,
        ]);
        if (!this.alive) return;
        this.state.canvas = canvas; this.state.dirty = false;
    }

    saveClick() { return this.perform(async () => { await this.save(); this.notification.add(_t("已保存"), { type: "success" }); }); }

    validateClick() {
        return this.perform(async () => {
            if (this.state.dirty) await this.save();
            await this.orm.call("workflow.version", "action_validate", [[this.state.canvas.id]]);
            this.notification.add(_t("流程校验通过"), { type: "success" });
        });
    }

    publishClick() {
        return this.perform(async () => {
            if (this.state.dirty) await this.save();
            const canvas = await this.orm.call("workflow.version", "action_publish", [
                [this.state.canvas.id], this.state.canvas.revision,
            ]);
            if (this.alive) { this.state.canvas = canvas; this.state.dirty = false; }
        });
    }

    async start(resId = 0) {
        await this.perform(async () => {
            const result = await this.orm.call("workflow.definition", "action_start", [
                [this.state.canvas.definition_id], resId, this.requestKey, this.state.canvas.id,
            ]);
            if (this.alive) await this.action.doAction(result);
        });
    }

    startClick() {
        if (!this.state.canvas.business_model) return this.start();
        this.dialog.add(SelectCreateDialog, {
            title: _t("选择业务记录"), resModel: this.state.canvas.business_model,
            noCreate: true, multiSelect: false, onSelected: (ids) => this.start(ids[0]),
        });
    }

    complete(id, comment) {
        return this.perform(async () => {
            await this.orm.call("workflow.task", "action_complete", [[id], comment]);
            await this.load();
        });
    }

    businessClick() {
        return this.perform(async () => {
            const result = await this.orm.call("workflow.instance", "action_business_record", [[this.params.instance_id]]);
            if (this.alive) await this.action.doAction(result);
        });
    }

    decide(id, reviewId, decision, comment) {
        return this.perform(async () => {
            await this.orm.call("workflow.instance", "action_review", [[this.params.instance_id], id, reviewId, decision, comment]);
            await this.load();
        });
    }

    async projectDecision(id, decision, comment) {
        if (decision === "cancel") {
            const confirmed = await new Promise(resolve => this.dialog.add(ConfirmationDialog, {
                body: _t("取消项目任务将取消整个流程，并关闭其他未完成工作。"),
                confirm: () => resolve(true), cancel: () => resolve(false),
            }));
            if (!confirmed || !this.alive) return;
        }
        return this.perform(async () => {
            await this.orm.call("workflow.project.link", "action_decide", [[id], decision, comment]);
            await this.load();
        });
    }

    projectOpen(id) {
        return this.perform(async () => {
            const action = await this.orm.call("workflow.project.link", "action_open", [[id]]);
            if (this.alive) await this.action.doAction(action);
        });
    }

    openParent() {
        if (this.constructor.recordParam === "instance_id") {
            return this.action.doAction("workflow_core.instances", { clearBreadcrumbs: true });
        }
        const definitionId = this.state.canvas?.definition_id;
        const options = { clearBreadcrumbs: true };
        if (definitionId) Object.assign(options, { viewType: "form", props: { resId: definitionId } });
        return this.action.doAction("workflow_core.definitions", options);
    }

    confirmDiscard() {
        if (!this.state.dirty) return Promise.resolve(true);
        return new Promise((resolve) => this.dialog.add(ConfirmationDialog, {
            body: _t("画布有未保存的修改，是否放弃？"),
            confirmLabel: _t("放弃修改"), confirm: () => resolve(true), cancel: () => resolve(false),
        }));
    }

    async refreshClick() {
        if (await this.confirmDiscard()) await this.perform(async () => {
            await loadBundle("workflow_core.canvas"); await this.load();
        });
    }
}

registry.category("actions").add("workflow_core.canvas", WorkflowAction);

export class WorkflowMonitorAction extends WorkflowAction {
    static path = "workflow-monitor";
    static recordParam = "instance_id";
}

registry.category("actions").add("workflow_core.monitor", WorkflowMonitorAction);
