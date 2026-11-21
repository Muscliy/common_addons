import { describe, expect, test } from "@odoo/hoot";
import {
    configuredWidth,
    frozenFirst,
    moveColumn,
    orderedColumns,
} from "@custom_web_components/utils/list_layout";

describe.current.tags("cwc");

const fields = ["name", "partner_id", "amount", "note"].map((name) => ({
    name,
    type: "field",
    id: name,
}));
test("hidden optional columns retain positions and stale fields do not enter the view", () => {
    const moved = moveColumn(
        fields,
        { removed: { sequence: 0 }, note: { width: 300 } },
        "note",
        "name",
    );
    expect(orderedColumns(fields, moved).map((column) => column.name)).toEqual([
        "note",
        "name",
        "partner_id",
        "amount",
    ]);
    expect(moved.note.width).toBe(300);
    expect(orderedColumns(fields, {}).map((column) => column.name)).toEqual([
        "name",
        "partner_id",
        "amount",
        "note",
    ]);
});
test("row handles, buttons and duplicate field instances remain anchored", () => {
    const columns = [
        { id: "handle", name: "sequence", type: "field", widget: "handle" },
        fields[0],
        { id: "button", type: "button_group" },
        fields[2],
        { id: "duplicate1", name: "note", type: "field" },
        { id: "duplicate2", name: "note", type: "field" },
    ];
    const moved = moveColumn(columns, {}, "amount", "name");
    expect(orderedColumns(columns, moved).map((column) => column.id)).toEqual([
        "handle",
        "amount",
        "button",
        "name",
        "duplicate1",
        "duplicate2",
    ]);
    expect(moveColumn(columns, moved, "sequence", "name")).toBe(moved);
});
test("saved width precedes XML and absence delegates to native sizing", () => {
    const column = { name: "name", attrs: { width: "160px" } };
    expect(configuredWidth(column, { name: { width: 240 } })).toBe(240);
    expect(configuredWidth(column, {})).toBe(160);
    expect(configuredWidth({ name: "name" }, {})).toBe(null);
    expect(configuredWidth({ name: "name", attrs: { width: "50%" } }, {})).toBe(null);
});

test("frozen partition preserves structural slots and ignores flags on duplicate fields", () => {
    const columns = [
        { id: "handle", name: "sequence", type: "field", widget: "handle" },
        fields[0],
        { id: "button", type: "button_group" },
        fields[2],
        { id: "duplicate1", name: "note", type: "field" },
        { id: "duplicate2", name: "note", type: "field" },
    ];
    const config = { amount: { frozen: true }, note: { frozen: true } };
    expect(frozenFirst(columns, config).map((column) => column.id)).toEqual([
        "handle",
        "amount",
        "button",
        "name",
        "duplicate1",
        "duplicate2",
    ]);
});

test("explicit drop edges insert before or after the target in both directions", () => {
    const order = (source, target, placement) =>
        orderedColumns(fields, moveColumn(fields, {}, source, target, placement)).map(
            (column) => column.name,
        );
    expect(order("name", "amount", "before")).toEqual(["partner_id", "name", "amount", "note"]);
    expect(order("name", "amount", "after")).toEqual(["partner_id", "amount", "name", "note"]);
    expect(order("note", "partner_id", "after")).toEqual(["name", "partner_id", "note", "amount"]);
    expect(order("note", "name", "before")).toEqual(["note", "name", "partner_id", "amount"]);
    expect(order("name", "note", "after")).toEqual(["partner_id", "amount", "note", "name"]);
});
