import { Component, useEffect, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { drawPreview } from "./draw_preview";

export class WorkflowCanvasPreview extends Component {
    static template = "workflow_core.CanvasPreview";
    static props = standardFieldProps;

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
            () => [this.canvas.el, this.graph],
        );
    }

    get graph() {
        return this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("workflow_canvas_preview", {
    component: WorkflowCanvasPreview,
    supportedTypes: ["json"],
});
