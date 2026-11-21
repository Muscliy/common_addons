import { describe, expect, test } from "@odoo/hoot";
import { columnVisibility } from "@custom_web_components/list_view/column_visibility";

describe.current.tags("cwc");

const fields = ["name", "note", "amount"].map((name) => ({ type: "field", name }));

test("initial layout uses XML defaults and personal choices apply to ordinary fields", () => {
    const columns = [...fields, { type: "field", name: "extra", optional: "hide" }];
    expect([...columnVisibility(columns, {}).visible]).toEqual(["name", "note", "amount"]);
    expect([...columnVisibility(columns, { name: { visible: false } }).visible]).toEqual([
        "note",
        "amount",
    ]);
});

test("stale preferences restore two available fields and ignore structural columns and unknown names", () => {
    const columns = [
        { type: "field", name: "sequence", widget: "handle" },
        ...fields,
        { type: "button_group", name: "actions" },
        { type: "field", name: "properties", relatedPropertyField: true },
    ];
    const state = columnVisibility(columns, {
        name: { visible: false },
        note: { visible: false },
        amount: { visible: false },
        removed: { visible: true },
    });
    expect([...state.visible]).toEqual(["name", "note"]);
    expect([...state.available]).toEqual(["name", "note", "amount"]);
    expect(state.minimum).toBe(2);
});

test("one-field lists stay usable and duplicate field instances count as one field", () => {
    const state = columnVisibility([fields[0], fields[0]], { name: { visible: false } });
    expect([...state.visible]).toEqual(["name"]);
    expect(state.minimum).toBe(1);
    expect(columnVisibility([], {}).minimum).toBe(0);
});
