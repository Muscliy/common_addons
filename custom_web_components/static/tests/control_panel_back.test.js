import { describe, expect, test } from "@odoo/hoot";
import { reactive } from "@odoo/owl";
import { animationFrame } from "@odoo/hoot-mock";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { contains, defineModels, models, mountWithSearch } from "@web/../tests/web_test_helpers";

describe.current.tags("cwc", "cwc_back");

class BackTarget extends models.Model {}
defineModels([BackTarget]);

test("root pages have no back button", async () => {
    await mountWithSearch(ControlPanel, { resModel: "back.target" }, {
        breadcrumbs: [{ jsId: "root", name: "总览" }],
    });
    expect(".cwc_back_button").toHaveCount(0);
});

test("drilldowns return one level and hide the button when back at root", async () => {
    const breadcrumbs = reactive([
        { jsId: "root", name: "总览", onSelected: () => expect.step("root") },
        { jsId: "list", name: "列表", onSelected: () => expect.step("list") },
        { jsId: "form", name: "详情" },
    ]);
    await mountWithSearch(ControlPanel, { resModel: "back.target" }, { breadcrumbs });
    expect(".o_control_panel_breadcrumbs > .cwc_back_button").toHaveCount(1);
    expect(".cwc_back_button").toHaveAttribute("aria-label", "返回上一层");
    expect("button.o_back_button").toHaveCount(0);
    await contains(".cwc_back_button").click();
    expect.verifySteps(["list"]);
    breadcrumbs.pop();
    await animationFrame();
    await contains(".cwc_back_button").click();
    expect.verifySteps(["root"]);
    breadcrumbs.pop();
    await animationFrame();
    expect(".cwc_back_button").toHaveCount(0);
});
