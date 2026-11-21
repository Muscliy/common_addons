import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
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
import { listPreferenceScope } from "@custom_web_components/list_view/preference_scope";

describe.current.tags("cwc", "cwc_global");

class Line extends models.Model {
    _name = "cwc.global.line";
    name = fields.Char();
    note = fields.Char();
    _records = [{ id: 1, name: "Alpha", note: "Detail" }];
}
class Parent extends models.Model {
    _name = "cwc.global.parent";
    name = fields.Char();
    line_ids = fields.One2many({ relation: Line._name });
    other_ids = fields.One2many({ relation: Line._name });
    _records = [{ id: 1, name: "Parent", line_ids: [1], other_ids: [1] }];
}
defineModels([Line, Parent, webModels.ResUsers, webModels.ResPartner, webModels.ResCompany]);

test("nested paths stay within their root view and ad-hoc renderers cannot overwrite list preferences", () => {
    const renderer = {
        env: {
            config: { viewId: 91, viewType: "form" },
            componentListPath: { viewId: 91, path: "line_ids" },
        },
        props: {
            list: { resModel: Line._name },
            nestedKeyOptionalFieldsData: { field: "other_ids" },
        },
    };
    expect(listPreferenceScope(renderer)).toEqual({
        type: "list_nested",
        model: Line._name,
        viewId: 91,
        key: "x2many:line_ids.other_ids",
    });
    renderer.env.config.viewId = 92;
    expect(listPreferenceScope(renderer).key).toBe("x2many:other_ids");
    delete renderer.props.nestedKeyOptionalFieldsData;
    expect(listPreferenceScope(renderer)).toBe(null);
    renderer.env.config.viewType = "list";
    expect(listPreferenceScope(renderer)).toEqual({ type: "list", model: Line._name, viewId: 92 });
    renderer.env.config.viewId = false;
    expect(listPreferenceScope(renderer)).toBe(null);
});

test("specialized native lists offer settings without optional fields and preserve overrides", async () => {
    class SpecializedController extends ListController {
        get className() {
            return `${super.className} cwc_specialized_controller`;
        }
    }
    class SpecializedRenderer extends ListRenderer {
        get getEmptyRowIds() {
            return [];
        }
    }
    registry.category("views").add("cwc_specialized", {
        ...listView,
        Controller: SpecializedController,
        Renderer: SpecializedRenderer,
    });
    let saved;
    mockService("component_preference", {
        load: async () => ({
            note: { sequence: 0, width: 240 },
            name: { sequence: 1 },
        }),
        save: async (scope, config) => {
            saved = { scope, config };
        },
    });
    await mountView({
        type: "list",
        resModel: Line._name,
        viewId: 91,
        arch: `<list js_class="cwc_specialized"><field name="name"/><field name="note"/></list>`,
    });
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "note");
    expect(".o_data_row:first td[name='note']").toHaveText("Detail");
    expect("tbody .o_data_row").toHaveCount(1);
    expect(".cwc_specialized_controller").toHaveCount(1);
    expect("tbody tr").toHaveCount(1);
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_settings_row").toHaveCount(2);
    document.querySelector(".cwc_settings_row[data-name='name'] .cwc_column_grip").dispatchEvent(
        new KeyboardEvent("keydown", {
            bubbles: true,
            key: "ArrowUp",
            altKey: true,
        }),
    );
    await animationFrame();
    await contains(".cwc_save_layout").click();
    expect(saved.scope).toEqual({ type: "list", model: Line._name, viewId: 91 });
    expect(saved.config.note.width).toBe(240);
    expect("thead th[data-name]:first").toHaveAttribute("data-name", "name");
});

test("two native form detail lists have separate persistent scopes and preserve row editing", async () => {
    const scopes = [];
    let saved;
    mockService("component_preference", {
        load: async (scope) => {
            scopes.push(scope);
            return scope.key === "x2many:line_ids"
                ? { note: { sequence: 0 }, name: { sequence: 1 } }
                : {};
        },
        save: async (scope) => {
            saved = scope;
        },
    });
    const detail = `<list editable="bottom"><field name="name"/><field name="note"/></list>`;
    await mountView({
        type: "form",
        resModel: Parent._name,
        viewId: 92,
        resId: 1,
        arch: `<form><field name="name"/><field name="line_ids">${detail}</field><field name="other_ids">${detail}</field></form>`,
    });
    expect(scopes).toEqual([
        {
            type: "list_nested",
            model: Line._name,
            viewId: 92,
            key: "x2many:line_ids",
        },
        {
            type: "list_nested",
            model: Line._name,
            viewId: 92,
            key: "x2many:other_ids",
        },
    ]);
    expect(".o_field_widget[name='line_ids'] th[data-name]:first").toHaveAttribute(
        "data-name",
        "note",
    );
    expect(".o_field_widget[name='other_ids'] th[data-name]:first").toHaveAttribute(
        "data-name",
        "name",
    );
    await contains(".o_field_widget[name='line_ids'] .o_optional_columns_dropdown button").click();
    await contains(".cwc_settings_row[data-name='note'] .cwc_freeze_column").click();
    await contains(".cwc_save_layout").click();
    expect(saved.key).toBe("x2many:line_ids");
    await contains(".o_field_widget[name='line_ids'] .o_optional_columns_dropdown button").click();
    await contains(".o_field_widget[name='line_ids'] .o_data_row td[name='name']").click();
    expect(".o_field_widget[name='line_ids'] .o_data_row input").toHaveCount(2);
});

test("ordinary fields can be hidden and saved, while at least two fields stay visible", async () => {
    let saved;
    mockService("component_preference", {
        load: async () => ({}),
        save: async (scope, config) => {
            saved = config;
        },
    });
    await mountView({
        type: "list",
        resModel: Line._name,
        viewId: 91,
        arch: `<list><field name="name"/><field name="note"/><field name="id"/></list>`,
    });
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_column_visible:enabled").toHaveCount(3);
    await contains(".cwc_settings_row[data-name='name'] input").click();
    expect("th[data-name='name']").toHaveCount(0);
    expect("thead th[data-name]").toHaveCount(2);
    expect(".cwc_settings_row[data-name='note'] input").toHaveAttribute("disabled");
    expect(".cwc_settings_row[data-name='id'] input").toHaveAttribute("disabled");
    expect(".cwc_settings_row[data-name='name'] input").not.toHaveAttribute("disabled");
    document
        .querySelector(".cwc_settings_row[data-name='note'] input")
        .dispatchEvent(new Event("change", { bubbles: true }));
    await animationFrame();
    expect("thead th[data-name]").toHaveCount(2);
    await contains(".cwc_save_layout").click();
    expect(saved.name.visible).toBe(false);
    await contains(".cwc_settings_row[data-name='name'] input").click();
    expect("thead th[data-name]").toHaveCount(3);
    expect(".cwc_column_visible:enabled").toHaveCount(3);
});

test("a stale personal layout restores two allowed fields without exposing system-hidden fields", async () => {
    mockService("component_preference", {
        load: async () => ({
            name: { visible: false },
            note: { visible: false },
            id: { visible: true },
        }),
    });
    await mountView({
        type: "list",
        resModel: Line._name,
        viewId: 91,
        arch: `<list><field name="name"/><field name="note" optional="hide"/><field name="id" column_invisible="True"/></list>`,
    });
    expect("thead th[data-name]").toHaveCount(2);
    expect("th[data-name='id']").toHaveCount(0);
    await contains(".o_optional_columns_dropdown button").click();
    expect(".cwc_column_visible:checked").toHaveCount(2);
    expect(".cwc_column_visible:enabled").toHaveCount(0);
    expect(".cwc_settings_row[data-name='id']").toHaveCount(0);
});
