import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { assets } from "@web/core/assets";
import { contains, mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { WorkflowAction } from "@workflow_core/action/workflow_action";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

describe.current.tags("workflow_core");
defineMailModels();

const canvas = {
    id: 1, title: "Bridge test", revision: 0, state: "draft", can_edit: false,
    graph: { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } },
};

test("OWL mounts, updates and destroys the canvas once", async () => {
    onRpc("workflow.version", "get_canvas", () => canvas);
    const calls = [];
    patchWithCleanup(assets, { loadBundle: async () => {} });
    patchWithCleanup(globalThis, { WorkflowCanvas: {
        mount(element, props) {
            calls.push(["mount", element, props.canvas.id]);
            return { update: () => calls.push(["update"]), destroy: () => calls.push(["destroy"]) };
        },
    } });
    const host = await mountWithCleanup(WorkflowAction, { props: { action: { params: { version_id: 1 } } } });
    expect(".o_workflow_action .o_control_panel .o_last_breadcrumb_item").toHaveText("Bridge test");
    expect(".wf-toolbar").toHaveCount(0);
    expect(calls.filter(([name]) => name === "mount").length).toBe(1);
    await host.refreshClick(); await animationFrame();
    expect(calls.filter(([name]) => name === "mount").length).toBe(1);
    expect(calls.filter(([name]) => name === "update").length > 0).toBe(true);
    host.__owl__.app.destroy();
    expect(calls.filter(([name]) => name === "destroy").length).toBe(1);
});

test("native control panel keeps workflow status and protects unsaved navigation", async () => {
    onRpc("workflow.version", "get_canvas", () => ({ ...canvas, definition_id: 7 }));
    patchWithCleanup(assets, { loadBundle: async () => {} });
    patchWithCleanup(globalThis, { WorkflowCanvas: { mount() {
        return { update() {}, destroy() {} };
    } } });
    const host = await mountWithCleanup(WorkflowAction, { props: { action: { params: { version_id: 1 } } } });
    expect(".o_control_panel .wf-heading").toHaveText("草稿");
    host.state.dirty = true;
    await animationFrame();
    expect(".o_control_panel .wf-heading").toHaveText(/未保存\s+草稿/);
    const pending = host.confirmDiscard();
    await animationFrame();
    expect(".modal").toHaveText(/画布有未保存的修改/);
    await contains(".modal-footer .btn-secondary").click();
    expect(await pending).toBe(false);
    expect(host.state.dirty).toBe(true);
});

test("load failure is visible and retry can mount the canvas", async () => {
    onRpc("workflow.version", "get_canvas", () => canvas);
    let fail = true, mounts = 0;
    patchWithCleanup(assets, { loadBundle: async () => { if (fail) throw new Error("Canvas unavailable"); } });
    patchWithCleanup(globalThis, { WorkflowCanvas: { mount() { mounts++; return { update() {}, destroy() {} }; } } });
    const host = await mountWithCleanup(WorkflowAction, { props: { action: { params: { version_id: 1 } } } });
    expect("[role=alert]").toHaveText("Canvas unavailable");
    expect(mounts).toBe(0);
    fail = false;
    await host.refreshClick(); await animationFrame();
    expect("[role=alert]").toHaveCount(0);
    expect(mounts).toBe(1);
});

test("destroying during an async reload prevents late RPC and mounting", async () => {
    let reads = 0, release;
    onRpc("workflow.version", "get_canvas", () => { reads++; return canvas; });
    patchWithCleanup(assets, { loadBundle: async () => {} });
    let mounts = 0, destroys = 0;
    patchWithCleanup(globalThis, { WorkflowCanvas: { mount() {
        mounts++; return { update() {}, destroy() { destroys++; } };
    } } });
    const host = await mountWithCleanup(WorkflowAction, { props: { action: { params: { version_id: 1 } } } });
    patchWithCleanup(assets, { loadBundle: () => new Promise(resolve => { release = resolve; }) });
    const pending = host.refreshClick();
    await animationFrame();
    host.__owl__.app.destroy();
    release(); await pending;
    expect(reads).toBe(1);
    expect(mounts).toBe(1);
    expect(destroys).toBe(1);
});
