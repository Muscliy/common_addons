import { Component, useEffect, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { drawPreview } from "./draw_preview";

class CanvasPreviewDrawing extends Component {
    static template = "workflow_core.CanvasPreviewDrawing";
    static props = { graph: Object, large: { type: Boolean, optional: true } };

    setup() {
        this.canvas = useRef("preview");
        useEffect(
            (canvas, graph) => {
                if (!canvas) {
                    return;
                }
                const draw = () => drawPreview(canvas, graph);
                draw();
                const resize = new ResizeObserver(draw);
                resize.observe(canvas);
                return () => resize.disconnect();
            },
            () => [this.canvas.el, this.props.graph],
        );
    }
}

class CanvasPreviewDialog extends Component {
    static template = "workflow_core.CanvasPreviewDialog";
    static components = { Dialog, CanvasPreviewDrawing };
    static props = { graph: Object, close: Function };
}

export class WorkflowCanvasPreview extends Component {
    static template = "workflow_core.CanvasPreview";
    static components = { CanvasPreviewDrawing };
    static props = standardFieldProps;

    setup() {
        this.dialog = useService("dialog");
    }

    get graph() {
        return this.props.record.data[this.props.name];
    }

    showPreview() {
        this.dialog.add(CanvasPreviewDialog, { graph: this.graph });
    }
}

registry.category("fields").add("workflow_canvas_preview", {
    component: WorkflowCanvasPreview,
    supportedTypes: ["json"],
});
