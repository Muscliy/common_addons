import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Component, xml } from "@odoo/owl";

describe.current.tags("cwc");

class UnitLabelRow extends Component {
    static props = {};
    static template = xml`
        <div class="o_form_view o_form_editable" style="min-width: 600px">
            <div class="o_row o_goal_unit_row" style="width: 600px">
                <div class="o_field_widget o_field_float">
                    <input class="o_input" type="text" value="91.80"/>
                </div>
                <span class="o_goal_label_unit">（<div
                    class="o_field_widget o_readonly_modifier o_field_many2one"
                ><div class="o_many2one"><a
                    class="o_form_uri text-truncate d-inline-block w-100"
                    href="#"
                >%</a></div></div>）</span>
            </div>
        </div>`;
}

test("keeps the field unit on the value line instead of wrapping", async () => {
    await mountWithCleanup(UnitLabelRow);
    const row = queryOne(".o_goal_unit_row");
    const field = row.querySelector(":scope > .o_field_widget");
    const unit = queryOne(".o_goal_label_unit");
    const many2one = queryOne(".o_goal_label_unit .o_many2one");

    expect(getComputedStyle(unit).whiteSpace).toBe("nowrap");
    expect(getComputedStyle(many2one).display).toBe("inline");

    const fieldRect = field.getBoundingClientRect();
    const unitRect = unit.getBoundingClientRect();
    expect(row.getBoundingClientRect().width).toBeGreaterThan(599);
    // Three stacked lines (opening parenthesis, unit, closing parenthesis) are
    // ~58px high; a single line stays below two lines of 13px text.
    expect(unitRect.height).toBeLessThan(30);
    // The input keeps a readable fixed width so the unit follows the value
    // instead of drifting to the far edge of the row.
    expect(fieldRect.width).toBeLessThan(row.getBoundingClientRect().width / 2);
    expect(unitRect.left - fieldRect.right).toBeLessThan(12);
});
