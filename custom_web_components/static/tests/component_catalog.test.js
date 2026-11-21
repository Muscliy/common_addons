import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    COMPONENT_COUNT,
    COMPONENT_GROUPS,
    ComponentCatalog,
} from "@custom_web_components/component_catalog/component_catalog";

describe.current.tags("cwc");

function mockCatalogServices({ onDialog = () => {}, onNotification = () => {} } = {}) {
    mockService("dialog", { add: onDialog });
    mockService("notification", { add: onNotification });
}

test("catalog covers all component families with unique entries", () => {
    const components = COMPONENT_GROUPS.flatMap((group) => group.components);
    const ids = new Set(components.map((component) => component.id));

    expect(COMPONENT_GROUPS.map((group) => group.id)).toEqual([
        "foundation",
        "layout",
        "navigation",
        "data-entry",
        "data-display",
        "feedback",
    ]);
    expect(COMPONENT_COUNT).toBe(39);
    expect(ids).toHaveLength(components.length);
    expect(ids).toInclude("button");
    expect(ids).toInclude("table");
    expect(ids).toInclude("indicator-progress");
    expect(ids).toInclude("alert");
    for (const component of components) {
        expect(component.name.length).toBeGreaterThan(0);
        expect(component.description.length).toBeGreaterThan(0);
        expect(component.snippet.length).toBeGreaterThan(0);
    }
});

test("catalog renders every component and filters by Chinese or English terms", async () => {
    mockCatalogServices();
    await mountWithCleanup(ComponentCatalog);

    expect(".o_cwc_catalog_group").toHaveCount(COMPONENT_GROUPS.length);
    expect(".o_cwc_component_entry").toHaveCount(COMPONENT_COUNT);
    expect("[data-component='indicator-progress'] .o_indicator_progress").toHaveCount(3);
    expect("[data-component='indicator-progress'] .o_indicator_progress.text-success").toHaveCount(1);
    expect("[data-component='indicator-progress'] .o_indicator_progress.text-warning").toHaveCount(1);
    expect("[data-component='indicator-progress'] .o_indicator_progress.text-danger").toHaveCount(1);

    await contains(".o_cwc_catalog_search input").edit("警告提示");
    expect(".o_cwc_catalog_group").toHaveCount(1);
    expect(".o_cwc_component_entry").toHaveCount(1);
    expect(".o_cwc_component_entry").toHaveAttribute("data-component", "alert");

    await contains(".o_cwc_catalog_search button").click();
    expect(".o_cwc_component_entry").toHaveCount(COMPONENT_COUNT);

    await contains(".o_cwc_catalog_search input").edit("not-a-component");
    expect(".o_cwc_component_entry").toHaveCount(0);
    expect(".o_cwc_catalog_no_results").toHaveCount(1);
});

test("interactive examples update and call standard feedback services", async () => {
    const notifications = [];
    const dialogs = [];
    mockCatalogServices({
        onDialog: (Dialog, props) => dialogs.push({ Dialog, props }),
        onNotification: (message, options) => notifications.push({ message, options }),
    });
    await mountWithCleanup(ComponentCatalog);

    expect(".o_cwc_switch").toHaveAttribute("aria-checked", "true");
    await contains(".o_cwc_switch").click();
    expect(".o_cwc_switch").toHaveAttribute("aria-checked", "false");

    await contains("[data-tab='settings']").click();
    expect("[data-tab='settings']").toHaveClass("active");
    expect(".o_cwc_tab_panel").toHaveText("当前内容：设置");

    await contains("[data-component='notification'] .btn-success").click();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].options.type).toBe("success");

    await contains("[data-component='dialog'] .btn-primary").click();
    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].props.title).toBe("确认提交");

    await contains("[data-component='progress'] .btn-group .btn:last-child").click();
    await animationFrame();
    expect("[data-component='progress'] strong").toHaveText("78%");
});
