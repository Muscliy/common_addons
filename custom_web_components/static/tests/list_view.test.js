import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    webModels,
} from "@web/../tests/web_test_helpers";
import "@custom_web_components/list_view/list_view";

describe.current.tags("cwc");

class Order extends models.Model {
    _name = "cwc.test.order";
    name = fields.Char();
    note = fields.Char();
    amount = fields.Float();
    sequence = fields.Integer();
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["done", "Done"],
        ],
    });
    partner_id = fields.Many2one({ relation: "cwc.test.partner" });
    _records = [
        { id: 1, name: "Alpha", note: "First", state: "draft", partner_id: 1 },
        { id: 2, name: "Beta", note: "Second", state: "done", partner_id: 2 },
        { id: 3, name: "Gamma", note: "Third", state: "draft", partner_id: 1 },
    ];
}
class Partner extends models.Model {
    _name = "cwc.test.partner";
    name = fields.Char();
    _records = [
        { id: 1, name: "Customer A" },
        { id: 2, name: "Customer B" },
    ];
}
defineModels([Order, Partner, webModels.ResUsers, webModels.ResPartner, webModels.ResCompany]);
const arch = `<list editable="bottom" limit="2"><field name="name" width="160px"/>
    <field name="partner_id" width="220px"/><field name="state" width="120px"/>
    <field name="note" optional="show" width="300px"/></list>`;

test("optional fields, sorting, pagination and inline editing survive a saved column order", async () => {
    mockService("component_preference", {
        load: async () => ({
            name: { sequence: 2 },
            state: { sequence: 0 },
            partner_id: { sequence: 1 },
            note: { sequence: 3 },
        }),
    });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "state");
    expect("thead .cwc_column_grip, thead .cwc_freeze_column").toHaveCount(0);
    expect(".o_data_row:first-child td[name='partner_id']").toHaveText("Customer A");
    await contains(".o_optional_columns_dropdown button").click();
    await contains(".cwc_settings_row[data-name='note'] input").click();
    expect("th[data-name='note']").toHaveCount(0);
    await contains(".cwc_settings_row[data-name='note'] input").click();
    expect("th[data-name='note']").toHaveCount(1);
    await contains(".o_optional_columns_dropdown button").click();
    await contains("th[data-name='name']").click();
    expect(".o_data_row:first-child td[name='name']").toHaveText("Alpha");
    await contains(".o_pager_next").click();
    expect(".o_data_row:first-child td[name='name']").toHaveText("Gamma");
    await contains(".o_data_row:first-child td[name='note']").click();
    expect(".cwc_column_grip:not(:disabled)").toHaveCount(0);
    await contains(".o_data_row .o_field_widget[name='note'] input").edit("Edited note");
    await contains(".o_list_button_save").click();
    await animationFrame();
    expect(".o_data_row:first-child td[name='note']").toHaveText("Edited note");
});

test("grouped list and aggregate column slots keep native rendering", async () => {
    mockService("component_preference", {
        load: async () => ({ name: { sequence: 2 }, state: { sequence: 0 } }),
    });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch,
        groupBy: ["state"],
    });
    expect(".o_group_header").toHaveCount(2);
    await contains(".o_group_header:first").click();
    expect(".o_data_row:first td[name='partner_id']").toHaveText("Customer A");
    expect("thead th[data-name='state']").toHaveCount(1);
});

test("save failures leave the layout dirty and allow a retry", async () => {
    let fail = true;
    mockService("component_preference", {
        load: async () => ({}),
        save: async () => {
            if (fail) {
                throw new Error("Simulated network failure");
            }
        },
    });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    await contains(".o_optional_columns_dropdown button").click();
    const grip = document.querySelector(".cwc_settings_row[data-name='state'] .cwc_column_grip");
    grip.dispatchEvent(
        new KeyboardEvent("keydown", { bubbles: true, key: "ArrowUp", altKey: true }),
    );
    await animationFrame();
    await contains(".cwc_save_layout").click();
    expect(".cwc_save_layout").not.toHaveAttribute("disabled");
    expect(".o_notification").toHaveCount(1);
    fail = false;
    await contains(".cwc_save_layout").click();
    expect(".cwc_save_layout").toHaveAttribute("disabled");
});

test("column settings includes mandatory and hidden fields, excludes invisible fields, and resets all settings", async () => {
    let saved;
    let resets = 0;
    mockService("component_preference", {
        load: async () => ({}),
        save: async (scope, config) => {
            saved = config;
        },
        reset: async () => {
            resets++;
        },
    });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch: `<list><field name="name" width="160px"/><field name="partner_id" width="220px"/>
            <field name="note" optional="hide" width="300px"/>
            <field name="state" column_invisible="True"/></list>`,
    });
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_settings_row").toHaveCount(3);
    expect(".cwc_settings_row[data-name='name'] input").toHaveAttribute("disabled");
    expect(".cwc_settings_row[data-name='note'] .cwc_freeze_column").toHaveAttribute("disabled");
    await contains(".cwc_settings_row[data-name='note'] input").click();
    expect("th[data-name='note']").toHaveCount(1);
    await contains(".cwc_settings_row[data-name='partner_id'] .cwc_freeze_column").click();
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "partner_id");
    expect(".cwc_settings_row:first").toHaveAttribute("data-name", "partner_id");
    expect("th[data-name='partner_id']").toHaveClass("cwc_frozen_cell");
    expect(".o_data_row:first td[name='partner_id']").toHaveClass("cwc_frozen_cell");
    expect(getComputedStyle(document.querySelector("th[data-name='partner_id']")).position).toBe(
        "sticky",
    );
    const grip = document.querySelector(".cwc_settings_row[data-name='note'] .cwc_column_grip");
    const transfer = new DataTransfer();
    grip.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: transfer }));
    document
        .querySelector(".cwc_settings_row[data-name='name']")
        .dispatchEvent(new DragEvent("drop", { bubbles: true, dataTransfer: transfer }));
    await animationFrame();
    expect(document.querySelectorAll("thead th[data-name]")[1]).toHaveAttribute(
        "data-name",
        "note",
    );
    await contains(".cwc_save_layout").click();
    expect(saved.partner_id.frozen).toBe(true);
    expect(saved.note.visible).toBe(true);
    expect(saved.note.sequence < saved.name.sequence).toBe(true);
    await contains(".cwc_settings_row[data-name='partner_id'] .cwc_freeze_column").click();
    expect(".cwc_frozen_cell").toHaveCount(0);
    await contains(".cwc_reset_layout").click();
    expect(resets).toBe(1);
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "name");
    expect("th[data-name='note']").toHaveCount(0);
    expect(".cwc_frozen_cell").toHaveCount(0);
});

test("saved visibility overrides XML defaults for ordinary and optional columns", async () => {
    mockService("component_preference", {
        load: async () => ({ name: { visible: false }, note: { visible: false, frozen: true } }),
    });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    expect("th[data-name='name']").toHaveCount(0);
    expect("th[data-name='note']").toHaveCount(0);
    expect(".cwc_frozen_cell").toHaveCount(0);
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_settings_row[data-name='note'] input").not.toBeChecked();
    await contains(".cwc_settings_row[data-name='note'] input").click();
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "note");
});

test("settings works without optional fields and is disabled while editing", async () => {
    mockService("component_preference", { load: async () => ({}) });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch: `<list editable="bottom"><field name="name"/><field name="state"/></list>`,
    });
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_settings_row").toHaveCount(2);
    await contains(".o_optional_columns_dropdown button").click();
    await contains(".o_data_row:first td[name='name']").click();
    await contains(".o_optional_columns_dropdown button").click();
    expect(
        ".cwc_column_grip:not(:disabled), .cwc_freeze_column:not(:disabled), .cwc_column_visible:not(:disabled)",
    ).toHaveCount(0);
    expect(".cwc_reset_layout").toHaveAttribute("disabled");
});

test("frozen groups forbid cross-group movement and release sticky behavior in a narrow viewport", async () => {
    mockService("component_preference", {
        load: async () => ({ name: { frozen: true }, state: { frozen: true } }),
    });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    await contains(".o_optional_columns_dropdown button").click();
    const move = async (name, key) => {
        document
            .querySelector(`.cwc_settings_row[data-name='${name}'] .cwc_column_grip`)
            .dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, altKey: true, key }));
        await animationFrame();
    };
    await move("state", "ArrowUp");
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "state");
    await move("partner_id", "ArrowUp");
    expect(".o_notification").toHaveCount(1);
    expect(document.querySelectorAll("thead th[data-name]")[2]).toHaveAttribute(
        "data-name",
        "partner_id",
    );
    const renderer = document.querySelector(".o_list_renderer");
    renderer.style.maxWidth = "200px";
    window.dispatchEvent(new Event("resize"));
    await animationFrame();
    expect(".cwc_frozen_cell").toHaveCount(0);
    expect(".cwc_column_settings [role='status']").toHaveCount(1);
    renderer.style.maxWidth = "";
    window.dispatchEvent(new Event("resize"));
    await animationFrame();
    expect("th[data-name='name']").toHaveClass("cwc_frozen_cell");
});

const frozenArch = arch.replace(
    "</list>",
    '<field name="amount" width="150px" sum="Total"/></list>',
);
const header = (name) => document.querySelector(`th[data-name="${name}"]`);
const waitLayout = async () => {
    await animationFrame();
    await animationFrame();
};

test("sticky end keeps the last button column beside Odoo's utility column", async () => {
    mockService("component_preference", { load: async () => ({}) });
    const buttonArch = `<list class="cwc_sticky_end"><field name="name" width="280px"/>
        <field name="note" optional="show" width="300px"/>
        <button name="noop" type="object" string="Generate" width="70px"/></list>`;
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch: buttonArch });
    await waitLayout();
    const header = document.querySelector("thead th.o_list_button");
    const cell = document.querySelector(".o_data_row td.o_list_button");
    expect(header).toHaveClass("cwc_sticky_end_cell");
    expect(cell).toHaveClass("cwc_sticky_end_cell");
    expect(document.querySelector("thead .o_list_actions_header")).toHaveClass(
        "cwc_sticky_end_cell",
    );
    expect(getComputedStyle(cell).position).toBe("sticky");
    expect(
        Number.parseFloat(header.style.getPropertyValue("--cwc-sticky-end-offset")),
    ).toBeGreaterThan(0);
    const renderer = document.querySelector(".o_list_renderer");
    renderer.style.maxWidth = "400px";
    window.dispatchEvent(new Event("resize"));
    await waitLayout();
    const buttonRight = header.getBoundingClientRect().right;
    const firstColumnLeft = document
        .querySelector("thead th[data-name='name']")
        .getBoundingClientRect().left;
    renderer.scrollLeft = 160;
    await waitLayout();
    expect(Math.abs(header.getBoundingClientRect().right - buttonRight)).toBeLessThan(2);
    expect(
        document.querySelector("thead th[data-name='name']").getBoundingClientRect().left,
    ).toBeLessThan(firstColumnLeft - 100);
    renderer.style.maxWidth = "80px";
    window.dispatchEvent(new Event("resize"));
    await waitLayout();
    expect("thead th.o_list_button.cwc_sticky_end_cell").toHaveCount(0);
    renderer.style.maxWidth = "";
    window.dispatchEvent(new Event("resize"));
    await waitLayout();
    expect("thead th.o_list_button.cwc_sticky_end_cell").toHaveCount(1);
});

test("sticky end follows the last visible field after saved column ordering", async () => {
    mockService("component_preference", {
        load: async () => ({ note: { sequence: 0 }, name: { sequence: 1 } }),
    });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch: `<list class="cwc_sticky_end"><field name="name" width="180px"/>
            <field name="note" width="220px"/></list>`,
    });
    await waitLayout();
    expect("thead th[data-name='name'].cwc_sticky_end_cell").toHaveCount(1);
    expect(".o_data_row td[name='name'].cwc_sticky_end_cell").toHaveCount(3);
    expect("thead th[data-name='note'].cwc_sticky_end_cell").toHaveCount(0);
});

test("row handles and selectors stay before frozen fields", async () => {
    mockService("component_preference", {
        load: async () => ({ amount: { frozen: true }, name: { frozen: true } }),
    });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch: frozenArch.replace(
            '<field name="name"',
            '<field name="sequence" widget="handle"/><field name="name"',
        ),
    });
    await waitLayout();
    expect("th[data-name]:first").toHaveAttribute("data-name", "sequence");
    expect("th[data-name='sequence'].cwc_frozen_cell").toHaveCount(1);
    expect("thead .o_list_record_selector.cwc_frozen_cell").toHaveCount(1);
});

test("grouped frozen aggregates remain aligned", async () => {
    mockService("component_preference", {
        load: async () => ({ amount: { frozen: true }, name: { frozen: true } }),
    });
    await mountView({
        type: "list",
        resModel: "cwc.test.order",
        viewId: 1,
        arch: frozenArch,
        groupBy: ["state"],
    });
    await contains(".o_group_header:first").click();
    await waitLayout();
    expect(".o_group_header:first td.cwc_frozen_cell").toHaveCount(1);
    const aggregate = document.querySelector(".o_group_header td.cwc_frozen_cell");
    expect(
        Math.abs(
            aggregate.getBoundingClientRect().left - header("amount").getBoundingClientRect().left,
        ),
    ).toBeLessThan(2);
});

test("preference load failure retains native optional fields without offering an unsafe save", async () => {
    mockService("component_preference", {
        load: async () => {
            throw new Error("Offline");
        },
    });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_column_settings").toHaveCount(0);
    await contains(".o-dropdown-item:contains('Note')").click();
    expect("th[data-name='note']").toHaveCount(0);
    expect(".o_notification").toHaveCount(1);
});

test("drag insertion line previews the precise gap and cleans up after drop and cancellation", async () => {
    mockService("component_preference", { load: async () => ({}) });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_column_settings").not.toHaveText(/列设置|拖动调整顺序，勾选显示|普通列/);
    const row = (name) => document.querySelector(`.cwc_settings_row[data-name='${name}']`);
    const transfer = new DataTransfer();
    const start = async (name) => {
        row(name)
            .querySelector(".cwc_column_grip")
            .dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: transfer }));
        await animationFrame();
    };
    const over = async (name, edge, type = "dragover") => {
        const rect = row(name).getBoundingClientRect();
        row(name).dispatchEvent(
            new DragEvent(type, {
                bubbles: true,
                cancelable: true,
                dataTransfer: transfer,
                clientY: edge === "before" ? rect.top + 2 : rect.bottom - 2,
            }),
        );
        await animationFrame();
    };
    const order = () =>
        [...document.querySelectorAll("thead th[data-name]")].map((el) => el.dataset.name);
    await start("name");
    await over("state", "before");
    expect(".cwc_drop_before").toHaveAttribute("data-name", "state");
    expect(".cwc_drop_after").toHaveCount(0);
    expect(order()).toEqual(["name", "partner_id", "state", "note"]);
    expect(getComputedStyle(row("state"), "::after").height).toBe("3px");
    await over("state", "after");
    expect(".cwc_drop_before").toHaveCount(0);
    expect(".cwc_drop_after").toHaveAttribute("data-name", "state");
    await over("state", "after", "drop");
    expect(order()).toEqual(["partner_id", "state", "name", "note"]);
    expect(".cwc_drop_before, .cwc_drop_after, .cwc_drag_source").toHaveCount(0);
    await start("note");
    await over("partner_id", "before");
    await over("partner_id", "before", "drop");
    expect(order()).toEqual(["note", "partner_id", "state", "name"]);
    await start("note");
    await over("name", "after");
    await over("name", "after", "drop");
    expect(order()).toEqual(["partner_id", "state", "name", "note"]);
    await start("note");
    await over("partner_id", "before");
    row("partner_id").dispatchEvent(
        new DragEvent("dragleave", { bubbles: true, relatedTarget: document.body }),
    );
    await animationFrame();
    expect(".cwc_drop_before, .cwc_drop_after").toHaveCount(0);
    await over("partner_id", "after");
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await animationFrame();
    expect(".cwc_drop_before, .cwc_drop_after, .cwc_drag_source").toHaveCount(0);
    expect(order()).toEqual(["partner_id", "state", "name", "note"]);
    await contains(".o_optional_columns_dropdown button").click();
    await start("note");
    await over("partner_id", "before");
    window.dispatchEvent(new DragEvent("dragend"));
    await animationFrame();
    expect(".cwc_drop_before, .cwc_drop_after, .cwc_drag_source").toHaveCount(0);
});

test("external drags and cross-group drops never show an insertion line or change order", async () => {
    mockService("component_preference", { load: async () => ({ name: { frozen: true } }) });
    await mountView({ type: "list", resModel: "cwc.test.order", viewId: 1, arch });
    await contains(".o_optional_columns_dropdown button").click();
    const target = document.querySelector(".cwc_settings_row[data-name='name']");
    const transfer = new DataTransfer();
    transfer.setData("text/plain", "state");
    target.dispatchEvent(new DragEvent("dragover", { bubbles: true, dataTransfer: transfer }));
    await animationFrame();
    expect(".cwc_drop_before, .cwc_drop_after").toHaveCount(0);
    document
        .querySelector(".cwc_settings_row[data-name='state'] .cwc_column_grip")
        .dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: transfer }));
    target.dispatchEvent(new DragEvent("dragover", { bubbles: true, dataTransfer: transfer }));
    await animationFrame();
    expect(".cwc_drop_before, .cwc_drop_after").toHaveCount(0);
    target.dispatchEvent(new DragEvent("drop", { bubbles: true, dataTransfer: transfer }));
    await animationFrame();
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "name");
    expect(".cwc_save_layout").toHaveAttribute("disabled");
});
