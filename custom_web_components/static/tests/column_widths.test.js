import { Component, useRef, xml } from "@odoo/owl";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { usePreferenceWidths } from "@custom_web_components/list_view/column_widths";

describe.current.tags("cwc");

// ResumeListRenderer renders a timeline instead of one cell per model field.
class TimelineList extends Component {
    static props = [];
    static template = xml`
        <div><table t-ref="table" style="width: 100%;">
            <thead><tr><th style="width: 32px;"/><th class="w-100"/></tr></thead>
            <tbody><tr><td/><td>Resume entry</td></tr></tbody>
        </table></div>`;

    setup() {
        this.tableRef = useRef("table");
        this.columns = ["name", "date_start", "date_end", "description"].map((name) => ({
            id: name,
            name,
            type: "field",
            fieldType: "char",
        }));
        this.layout = { config: { name: { width: 240 } } };
        this.columnWidths = { onStartResize() {} };
        this.preferenceWidths = usePreferenceWidths(this);
    }
}

class HeaderlessList extends TimelineList {
    static template = xml`
        <div><table t-ref="table" style="width: 100%;">
            <tbody><tr><td>Resume entry</td></tr></tbody>
        </table></div>`;
}

class MergedList extends TimelineList {
    static template = xml`
        <div><table t-ref="table" style="width: 100%;">
            <thead><tr><th style="width: 32px;"/><th/><th/><th/></tr></thead>
            <tbody><tr><td colspan="4">Resume entry</td></tr></tbody>
        </table></div>`;
}

for (const Renderer of [TimelineList, HeaderlessList, MergedList]) {
    test(`${Renderer.name} retains its widths on mount and resize`, async () => {
        const renderer = await mountWithCleanup(Renderer);
        renderer.preferenceWidths.reset();
        window.dispatchEvent(new Event("resize"));
        await animationFrame();
        expect("tbody td:last").toHaveText("Resume entry");
        expect(document.querySelector("table").style.width).toBe("100%");
        expect(document.querySelector("table").style.tableLayout).toBe("");
        if (document.querySelector("th")) {
            expect(document.querySelector("th").style.width).toBe("32px");
            expect(document.querySelector("th:last-child").style.width).toBe("");
        }
        expect(".o_list_computing_widths").toHaveCount(0);
    });
}
