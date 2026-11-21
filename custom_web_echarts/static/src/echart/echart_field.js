import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { EChart } from "./echart";

/** Accept a JSON field value or a JSON string; reject non-option values. */
export function parseEChartOption(value) {
    if (value === false || value === null || value === undefined || value === "") {
        return { option: null, error: null };
    }
    try {
        const option = typeof value === "string" ? JSON.parse(value) : value;
        if (!option || typeof option !== "object" || Array.isArray(option)) {
            throw new Error("The chart option must be an object");
        }
        return { option, error: null };
    } catch {
        return { option: null, error: _t("图表配置必须是有效的 JSON 对象。") };
    }
}

export class EChartField extends Component {
    static template = "custom_web_echarts.EChartField";
    static components = { EChart };
    static props = {
        ...standardFieldProps,
        height: { type: Number, optional: true },
        theme: { type: String, optional: true },
        ariaLabel: { type: String, optional: true },
    };
    static defaultProps = { height: 300, theme: "" };

    get parsed() {
        return parseEChartOption(this.props.record.data[this.props.name]);
    }

    get ariaLabel() {
        return this.props.ariaLabel || this.props.record.fields[this.props.name].string;
    }
}

registry.category("fields").add("custom_echarts", {
    component: EChartField,
    displayName: _t("ECharts 图表"),
    supportedTypes: ["char", "text", "json"],
    extractProps: ({ options }) => ({
        height: Number(options.height) > 0 ? Number(options.height) : 300,
        theme: options.theme || "",
        ariaLabel: options.aria_label,
    }),
});
