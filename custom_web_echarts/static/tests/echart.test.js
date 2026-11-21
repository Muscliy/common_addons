import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { assets } from "@web/core/assets";
import { defineModels, fields, models, mountView, mountWithCleanup, patchWithCleanup, preventResizeObserverError } from "@web/../tests/web_test_helpers";
import { EChart, ECHARTS_BUNDLE } from "@custom_web_echarts/echart/echart";
import { parseEChartOption } from "@custom_web_echarts/echart/echart_field";

describe.current.tags("custom_web_echarts");
preventResizeObserverError();

class ChartRecord extends models.Model {
    _name = "test.echart.record";
    chart_option = fields.Char();
}

defineModels([ChartRecord]);

const firstOption = {
    xAxis: { type: "category", data: ["一月", "二月"] },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: [3, 7] }],
};

test("loads the vendor bundle on mount and updates the same chart instance", async () => {
    const requestedBundles = [];
    const originalLoadBundle = assets.loadBundle;
    patchWithCleanup(assets, {
        loadBundle(name) {
            requestedBundles.push(name);
            return originalLoadBundle.call(this, name);
        },
    });

    class ChartHost extends Component {
        static components = { EChart };
        static template = xml`<EChart option="state.option" height="240" ariaLabel="'测试图表'"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ option: firstOption });
        }
    }

    const host = await mountWithCleanup(ChartHost);
    const canvas = document.querySelector(".o_custom_echart_canvas");
    const chart = globalThis.echarts.getInstanceByDom(canvas);
    expect(requestedBundles).toEqual([ECHARTS_BUNDLE]);
    expect(chart.getOption().series[0].data).toEqual([3, 7]);
    expect(document.querySelector(".o_custom_echart").style.height).toBe("240px");

    host.state.option = {
        xAxis: { type: "category", data: ["三月"] },
        yAxis: { type: "value" },
        series: [{ type: "line", data: [11] }],
    };
    await animationFrame();
    expect(globalThis.echarts.getInstanceByDom(canvas)).toBe(chart);
    expect(chart.getOption().series[0].type).toBe("line");
    expect(chart.getOption().series[0].data).toEqual([11]);
});

test("accepts JSON objects and strings and reports invalid field data", async () => {
    expect(parseEChartOption(firstOption).option).toBe(firstOption);
    expect(parseEChartOption(JSON.stringify(firstOption)).option.series[0].type).toBe("bar");
    expect(parseEChartOption(false).option).toBe(null);
    expect(parseEChartOption("[1,2]").error).not.toBe(null);
    expect(parseEChartOption("{invalid").error).not.toBe(null);

    ChartRecord._records = [{ id: 1, chart_option: "{invalid" }];
    await mountView({
        type: "form",
        resModel: "test.echart.record",
        resId: 1,
        arch: '<form><field name="chart_option" widget="custom_echarts"/></form>',
    });
    expect("[role='alert']").toHaveText("图表配置必须是有效的 JSON 对象。");
    expect(".o_custom_echart").toHaveCount(0);
});

test("chart clicks use the latest callback without registering duplicate handlers", async () => {
    const selected = [];
    class ClickHost extends Component {
        static components = { EChart };
        static template = xml`<EChart option="state.option" onClick="(event) => this.selected.push(event.data.id)"/>`;
        static props = ["*"];
        setup() { this.state = useState({ option: firstOption }); this.selected = selected; }
    }
    const host = await mountWithCleanup(ClickHost);
    const chart = globalThis.echarts.getInstanceByDom(document.querySelector(".o_custom_echart_canvas"));
    chart.trigger("click", { data: { id: "department:1" } });
    host.state.option = { ...firstOption, animation: false };
    await animationFrame();
    chart.trigger("click", { data: { id: "department:2" } });
    expect(selected).toEqual(["department:1", "department:2"]);
});
