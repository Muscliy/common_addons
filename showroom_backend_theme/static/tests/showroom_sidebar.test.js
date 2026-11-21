import { expect, test, waitFor } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    mockService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

import { firstOverflowIndex, getShowroomAppIconUrl, menuTopForTrigger, ShowroomSidebar } from "@showroom_backend_theme/webclient/showroom_sidebar";

defineMailModels();

test("moves the first whole section that exceeds the viewport into column two", () => {
    expect(firstOverflowIndex([120, 180, 140], 320, 12)).toBe(2);
    expect(firstOverflowIndex([120, 180], 320, 12)).toBe(2);
    expect(firstOverflowIndex([120, 188], 320, 12)).toBe(2);
    expect(firstOverflowIndex([350, 120], 320, 12)).toBe(1);
});

test("centers a submenu on its trigger and keeps it inside the viewport", () => {
    expect(menuTopForTrigger(500, 300, 900)).toBe(350);
    expect(menuTopForTrigger(50, 300, 900)).toBe(8);
    expect(menuTopForTrigger(850, 300, 900)).toBe(592);
});

test("positions a single-column submenu on the first layout pass", () => {
    const sidebar = document.createElement("aside");
    sidebar.innerHTML = `
        <div class="o_showroom_app_row is-open"><button class="o_showroom_app_more"></button></div>
        <div class="o_showroom_app_submenu" style="padding: 16px; border: 1px solid">
            <div class="o_showroom_menu_column" style="row-gap: 12px">
                <section class="o_showroom_menu_card"></section>
            </div>
        </div>`;
    document.body.append(sidebar);
    const panel = sidebar.querySelector(".o_showroom_app_submenu");
    const trigger = sidebar.querySelector(".o_showroom_app_more");
    const card = sidebar.querySelector(".o_showroom_menu_card");
    sidebar.getBoundingClientRect = () => ({ top: 0 });
    panel.getBoundingClientRect = () => ({ height: 120 });
    trigger.getBoundingClientRect = () => ({ top: browser.innerHeight - 160, height: 30 });
    card.getBoundingClientRect = () => ({ height: 80 });
    const state = { splitIndex: null, menuTop: 8, menuReady: false };
    try {
        ShowroomSidebar.prototype.reflowMenu.call({ sidebarRef: { el: sidebar }, state });
        expect(state.splitIndex).toBe(1);
        expect(state.menuReady).toBe(false);
        ShowroomSidebar.prototype.reflowMenu.call({ sidebarRef: { el: sidebar }, state });
        expect(state.menuTop).toBe(browser.innerHeight - 205);
        expect(state.menuReady).toBe(false);
        ShowroomSidebar.prototype.reflowMenu.call({ sidebarRef: { el: sidebar }, state });
        expect(state.menuReady).toBe(true);
    } finally {
        sidebar.remove();
    }
});

test("waits for a section animation before remeasuring the panel", async () => {
    let layouts = 0;
    const state = { collapsedSectionIds: [10] };
    const sidebar = { state, reflowMenu: () => layouts++ };
    ShowroomSidebar.prototype.onSectionToggle.call(
        sidebar,
        { id: 10 },
        { currentTarget: { open: true } }
    );
    expect(layouts).toBe(0);
    expect(state.collapsedSectionIds).toHaveLength(0);
    await advanceTime(220);
    expect(layouts).toBe(1);
});

test("application icon URLs bypass old caches and remain stable on the same page", () => {
    const src = "/account/static/description/icon.png?existing=1";
    const refreshed = getShowroomAppIconUrl(src);
    expect(refreshed === src).toBe(false);
    expect(refreshed.includes("existing=1")).toBe(true);
    expect(/showroom_icon=\d+/.test(refreshed)).toBe(true);
    expect(getShowroomAppIconUrl(src)).toBe(refreshed);
    expect(getShowroomAppIconUrl(refreshed)).toBe(refreshed);
    expect(getShowroomAppIconUrl("data:image/png;base64,custom")).toBe("data:image/png;base64,custom");
    expect(getShowroomAppIconUrl("/web/static/img/default_icon_app.png")).toBe("/web/static/img/default_icon_app.png");
});

test("prefers the application icon over an outdated menu attachment", () => {
    expect(ShowroomSidebar.prototype.getAppIcon({
        webIcon: "account,static/description/icon.png",
        webIconData: "data:image/png;base64,old-icon",
    })).toBe(getShowroomAppIconUrl("/account/static/description/icon.png"));
});

const APPS = [
    { id: 1, name: "制造", xmlid: "mrp.menu_mrp_root", actionID: 11 },
    { id: 2, name: "销售", xmlid: "sale.sale_menu_root", actionID: 12 },
    { id: 3, name: "设置", xmlid: "base.menu_administration", actionID: 13 },
    { id: 4, name: "应用", xmlid: "base.menu_management", actionID: 14 },
    { id: 5, name: "讨论", xmlid: "mail.menu_root_discuss", actionID: 15 },
    {
        id: 6, name: "员工", xmlid: "hr.menu_hr_root", actionID: 16,
        webIconData: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    },
    {
        id: 7, name: "出勤", xmlid: "hr_attendance.menu_hr_attendance_root", actionID: 17,
        webIconData: "/hr_attendance/static/description/icon.png",
    },
    {
        id: 8, name: "休假", xmlid: "hr_holidays.menu_hr_holidays_root", actionID: 18,
        webIconData: "/hr_holidays/static/description/icon.png",
    },
];

function mockMenuService(onSelectMenu = () => {}) {
    mockService("menu", {
        getApps: () => APPS,
        getCurrentApp: () => APPS[1],
        getMenuAsTree: (id) => ({ ...APPS.find((app) => app.id === id), childrenTree: [] }),
        selectMenu: onSelectMenu,
    });
}

test("renders business apps and Discuss but keeps settings in the top bar", async () => {
    mockMenuService();
    await mountWithCleanup(ShowroomSidebar);

    expect(".o_showroom_app_item").toHaveCount(6);
    expect('[data-menu-xmlid="mail.menu_root_discuss"] .o_showroom_app_name').toHaveText("讨论");
    expect(".o_showroom_app_name:first").toHaveText("制造");
    expect(".o_showroom_app_row.is-active .o_showroom_app_name").toHaveText("销售");
});

test("uses Odoo menu images including custom icons and the default fallback", async () => {
    mockMenuService();
    await mountWithCleanup(ShowroomSidebar);

    expect('[data-menu-xmlid="hr.menu_hr_root"] img').toHaveAttribute("data-src", APPS[5].webIconData);
    expect('[data-menu-xmlid="hr_attendance.menu_hr_attendance_root"] img').toHaveAttribute(
        "data-src", getShowroomAppIconUrl(APPS[6].webIconData)
    );
    expect('[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"] img').toHaveAttribute(
        "data-src", getShowroomAppIconUrl(APPS[7].webIconData)
    );
    expect('[data-menu-xmlid="mrp.menu_mrp_root"] img').toHaveAttribute(
        "data-src", "/web/static/img/default_icon_app.png"
    );
});

test("selects Discuss from the sidebar", async () => {
    const selected = [];
    mockMenuService((app) => selected.push(app));
    await mountWithCleanup(ShowroomSidebar);

    await contains('[data-menu-xmlid="mail.menu_root_discuss"] .o_showroom_app_item').click();
    expect(selected).toHaveLength(1);
    expect(selected[0].xmlid).toBe("mail.menu_root_discuss");
});

test("uses module icons when menu attachments are missing", async () => {
    mockService("menu", {
        getApps: () => [
            {
                ...APPS[5],
                webIcon: "hr,static/description/icon.png",
                webIconData: "/web/static/img/default_icon_app.png",
            },
            {
                ...APPS[4],
                webIcon: "mail,static/description/icon.png",
                webIconData: false,
            },
        ],
        getCurrentApp: () => null,
        getMenuAsTree: () => ({ childrenTree: [] }),
    });
    await mountWithCleanup(ShowroomSidebar);

    expect('[data-menu-xmlid="hr.menu_hr_root"] img').toHaveAttribute(
        "data-src", getShowroomAppIconUrl("/hr/static/description/icon.png")
    );
    expect('[data-menu-xmlid="mail.menu_root_discuss"] img').toHaveAttribute(
        "data-src", getShowroomAppIconUrl("/mail/static/description/icon.png")
    );
});

test("collapses and expands the sidebar", async () => {
    browser.localStorage.removeItem("tyj.sidebar.collapsed");
    mockMenuService();
    await mountWithCleanup(ShowroomSidebar);

    expect(".o_showroom_sidebar").not.toHaveClass("is-collapsed");
    expect(".o_showroom_sidebar_toggle").toHaveAttribute("aria-expanded", "true");

    await contains(".o_showroom_sidebar_toggle").click();
    expect(".o_showroom_sidebar").toHaveClass("is-collapsed");
    expect(".o_showroom_sidebar_toggle").toHaveAttribute("aria-expanded", "false");

    await contains(".o_showroom_sidebar_toggle").click();
    expect(".o_showroom_sidebar").not.toHaveClass("is-collapsed");
    browser.localStorage.removeItem("tyj.sidebar.collapsed");
});

test("opens the selected app's grouped submenu and selects a leaf", async () => {
    const selected = [];
    const customer = { id: 21, name: "客户", xmlid: "sale.menu_customers", actionID: 31, childrenTree: [] };
    const reports = { id: 22, name: "报表", childrenTree: [
        { id: 23, name: "销售分析", xmlid: "sale.menu_report", actionID: 32, childrenTree: [] },
    ] };
    mockService("menu", {
        getApps: () => APPS,
        getCurrentApp: () => APPS[1],
        getMenuAsTree: (id) => ({ ...APPS.find((app) => app.id === id), childrenTree: id === 2 ? [customer, reports] : [] }),
        selectMenu: (menu) => selected.push(menu),
    });
    await mountWithCleanup(ShowroomSidebar);

    expect('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').toHaveAttribute("aria-expanded", "false");
    expect('[data-menu-xmlid="mrp.menu_mrp_root"] .o_showroom_app_more').toHaveCount(0);
    await contains('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').click();
    await waitFor(".o_showroom_app_submenu.is-ready");
    expect('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').toHaveAttribute("aria-expanded", "true");
    expect(".o_showroom_menu_card").toHaveCount(2);
    expect(".o_showroom_menu_card details summary").toHaveText("报表");
    expect('[data-menu-xmlid="sale.menu_report"]').toHaveText("销售分析");
    await contains(".o_showroom_menu_card details summary").click();
    expect(".o_showroom_menu_card details").not.toHaveAttribute("open");
    await contains(".o_showroom_menu_card details summary").click();
    expect(document.querySelector(".o_showroom_menu_card details").open).toBe(true);

    await contains('[data-menu-xmlid="sale.menu_report"]').click();
    expect(selected).toHaveLength(1);
    expect(selected[0]).toBe(reports.childrenTree[0]);
    expect(".o_showroom_app_submenu").toHaveCount(0);
});

test("the app submenu closes on Escape and when the sidebar collapses", async () => {
    browser.localStorage.removeItem("tyj.sidebar.collapsed");
    mockService("menu", {
        getApps: () => APPS,
        getCurrentApp: () => APPS[1],
        getMenuAsTree: (id) => ({ ...APPS.find((app) => app.id === id), childrenTree: id === 2 ? [
            { id: 20, name: "客户", xmlid: "sale.menu_customers", actionID: 31, childrenTree: [] },
        ] : [] }),
        selectMenu: () => {},
    });
    await mountWithCleanup(ShowroomSidebar);

    await contains('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').click();
    expect(".o_showroom_app_submenu").toHaveCount(1);
    await contains('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').press("Escape");
    expect(".o_showroom_app_submenu").toHaveCount(0);

    await contains('[data-menu-xmlid="sale.sale_menu_root"] .o_showroom_app_more').click();
    await contains(".o_showroom_sidebar_toggle").click();
    expect(".o_showroom_app_submenu").toHaveCount(0);
    expect(".o_showroom_app_more").toHaveCount(1);
    browser.localStorage.removeItem("tyj.sidebar.collapsed");
});

test("switches navigation tabs and deletes bookmarks and history separately", async () => {
    mockMenuService();
    const state = {
        bookmarks: [{ name: "审批流程", url: "/app/action-123" }],
        history: [{ name: "公司印章", url: "/app/action-456" }],
    };
    mockService("showroom_sidebar_entries", {
        state,
        remove: (kind, url) => { state[kind] = state[kind].filter((entry) => entry.url !== url); },
    });
    await mountWithCleanup(ShowroomSidebar);
    await contains("#showroom-tab-bookmarks").click();
    expect("#showroom-tab-bookmarks").toHaveAttribute("aria-selected", "true");
    expect(".o_showroom_entry_link").toHaveText("审批流程");
    expect(".o_showroom_entry_link").toHaveAttribute("href", "/app/action-123");
    await contains(".o_showroom_entry_more").click();
    await contains(".o_showroom_entry_delete").click();
    expect(state.bookmarks).toHaveLength(0);
    expect(state.history).toHaveLength(1);
    await contains("#showroom-tab-history").click();
    expect(".o_showroom_entry_link").toHaveText("公司印章");
    await contains(".o_showroom_entry_more").click();
    await contains(".o_showroom_entry_delete").click();
    expect(state.history).toHaveLength(0);
    await contains("#showroom-tab-apps").click();
    expect(".o_showroom_app_item").toHaveCount(6);
});

test("shows empty bookmark and history states", async () => {
    mockMenuService();
    mockService("showroom_sidebar_entries", { state: { bookmarks: [], history: [] } });
    await mountWithCleanup(ShowroomSidebar);
    await contains("#showroom-tab-bookmarks").click();
    expect(".o_showroom_entries_empty").toHaveText("暂无书签");
    await contains("#showroom-tab-history").click();
    expect(".o_showroom_entries_empty").toHaveText("暂无记录");
});
