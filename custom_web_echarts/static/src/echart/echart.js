import { Component, onMounted, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export const ECHARTS_BUNDLE = "custom_web_echarts.echarts_lib";

/** Render an ECharts option object. The vendor library loads only when mounted. */
export class EChart extends Component {
    static template = "custom_web_echarts.EChart";
    static props = {
        onClick: { type: Function, optional: true },
        option: { type: [Object, { value: null }] },
        height: { type: Number, optional: true },
        theme: { type: String, optional: true },
        ariaLabel: { type: String, optional: true },
    };
    static defaultProps = {
        height: 300,
        theme: "",
        ariaLabel: _t("图表"),
    };

    setup() {
        this.container = useRef("chart");
        this.state = useState({ loadError: false });
        this.chart = null;
        this.chartTheme = null;
        this.resizeObserver = null;

        onWillStart(async () => {
            try {
                await loadBundle(ECHARTS_BUNDLE);
                if (!globalThis.echarts?.init) {
                    throw new Error("ECharts did not register its browser global");
                }
            } catch (error) {
                console.error("Unable to load Apache ECharts", error);
                this.state.loadError = true;
            }
        });

        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => this.chart?.resize());
            this.resizeObserver.observe(this.container.el);
        });

        useEffect(() => {
            if (this.state.loadError || !this.container.el) {
                return;
            }
            if (!this.props.option) {
                this.chart?.clear();
                return;
            }
            const theme = this.props.theme || (
                getComputedStyle(this.container.el).colorScheme === "dark" ? "dark" : ""
            );
            if (!this.chart || this.chartTheme !== theme) {
                this.chart?.dispose();
                this.chart = globalThis.echarts.init(this.container.el, theme || undefined);
                this.chartTheme = theme;
                this.chart.on("click", (event) => this.props.onClick?.(event));
            }
            this.chart.setOption({ backgroundColor: "transparent", ...this.props.option }, { notMerge: true });
            this.chart.resize();
        }, () => [this.state.loadError, this.props.option, this.props.theme]);

        onWillUnmount(() => {
            this.resizeObserver?.disconnect();
            this.chart?.dispose();
        });
    }

    get chartStyle() {
        return `height: ${this.props.height}px`;
    }
}
