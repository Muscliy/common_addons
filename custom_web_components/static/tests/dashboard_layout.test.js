import { Component, xml } from "@odoo/owl";
import { expect, test } from "@odoo/hoot";
import { contains, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { DashboardControlPanel, organizationSearch } from "@custom_web_components/dashboard/dashboard_layout";

class OrganizationDashboard extends Component {
    static components = { DashboardControlPanel };
    static props = ["onSearch"];
    static template = xml`
        <DashboardControlPanel title="'管理看板'" model="'hr.employee'" search="search" onSearch="props.onSearch">
            <span class="test-dashboard-body">正文</span>
        </DashboardControlPanel>`;
    search = organizationSearch({
        companies: [{ id: 1, name: "雅博 & 分公司" }, { id: 2, name: "第二公司" }],
    }, { company_id: 1, department_id: 15 });
}

test("native organization facets preserve the default department and clear it when switching company", async () => {
    let current;
    mockService("orm", {
        call(model, method, args, kwargs) {
            expect(model).toBe("hr.department");
            if (method === "read") return [{ id: 15, display_name: "生产部" }];
            expect(method).toBe("name_search");
            expect(kwargs.domain).toEqual([["company_id", "in", [2]]]);
            return [[16, "质管部"]];
        },
    });
    await mountWithCleanup(OrganizationDashboard, { props: { onSearch: (context) => { current = context; } } });
    expect(".o_control_panel").toHaveText(/管理看板/);
    expect(".o_searchview_facet:contains(雅博)").toHaveCount(1);
    expect(".o_searchview_facet:contains(生产部)").toHaveCount(1);
    expect(current.dashboard_company_id).toEqual([1]);
    expect(current.dashboard_department_id).toEqual([15]);
    await contains(".o_searchview_dropdown_toggler").click();
    await contains(".o_filter_menu .o_menu_item:contains(第二公司)").click();
    expect(".o_searchview_facet:contains(生产部)").toHaveCount(0);
    expect(current.dashboard_company_id).toEqual([2]);
    expect(current.dashboard_department_id).toBe(undefined);
    await contains(".o_searchview_input").edit("质管", { confirm: false });
    await contains(".o_searchview_autocomplete .dropdown-item:contains(主职部门) .o_expand").click();
    await contains(".o_searchview_autocomplete .dropdown-item:contains(质管部)").click();
    expect(current.dashboard_department_id).toEqual([16]);
    expect(".test-dashboard-body").toHaveText("正文");
});
