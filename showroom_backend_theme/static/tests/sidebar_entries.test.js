import { EventBus } from "@odoo/owl";
import { expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    createSidebarEntries, sidebarStorageKey,
} from "@showroom_backend_theme/webclient/sidebar_entries";

function setupEntries(saved) {
    const key = sidebarStorageKey("test-sidebar", 12);
    browser.localStorage.removeItem(key);
    if (saved) {
        browser.localStorage.setItem(key, saved);
    }
    const bus = new EventBus();
    const notices = [];
    const action = { currentController: { action: { name: "审批流程" }, displayName: "审批流程" } };
    patchWithCleanup(router, {
        current: { action: 123 },
        stateToUrl: (route) => `/app/action-${route.action}`,
    });
    const entries = createSidebarEntries({ bus }, {
        action, notification: { add: (message) => notices.push(message) },
    }, key);
    return { entries, action, bus, key, notices };
}

test("bookmarks persist, deduplicate and delete independently from history", async () => {
    const { entries, bus, key } = setupEntries();
    entries.addBookmark();
    entries.addBookmark();
    bus.trigger("ACTION_MANAGER:UI-UPDATED");
    await advanceTime(1);
    expect(entries.state.bookmarks).toHaveLength(1);
    expect(entries.state.history).toHaveLength(1);
    expect(JSON.parse(browser.localStorage.getItem(key)).bookmarks[0].name).toBe("审批流程");
    entries.remove("bookmarks", "/app/action-123");
    expect(entries.state.bookmarks).toHaveLength(0);
    expect(entries.state.history).toHaveLength(1);
    entries.remove("history", "/app/action-123");
    expect(JSON.parse(browser.localStorage.getItem(key)).history).toHaveLength(0);
    expect(sidebarStorageKey("db", 1)).not.toBe(sidebarStorageKey("db", 2));
    expect(sidebarStorageKey("db", 1)).not.toBe(sidebarStorageKey("other", 1));
});

test("recent pages move to the front and are limited to fifty entries", async () => {
    const { entries, bus } = setupEntries();
    for (let id = 1; id <= 55; id++) {
        patchWithCleanup(router, { current: { action: id } });
        bus.trigger("ACTION_MANAGER:UI-UPDATED");
        await advanceTime(1);
    }
    expect(entries.state.history).toHaveLength(50);
    expect(entries.state.history[0].url).toBe("/app/action-55");
    patchWithCleanup(router, { current: { action: 20 } });
    bus.trigger("ACTION_MANAGER:UI-UPDATED");
    await advanceTime(1);
    expect(entries.state.history[0].url).toBe("/app/action-20");
    expect(entries.state.history).toHaveLength(50);
});

test("corrupt storage and unsafe links do not break navigation", () => {
    expect(setupEntries("invalid-json").notices).toHaveLength(1);
    const { entries } = setupEntries(JSON.stringify({ bookmarks: [
        { name: "外部地址", url: "https://example.com" },
        { name: "协议地址", url: "//example.com" },
        { name: "审批流程", url: "/app/action-123" },
    ] }));
    expect(entries.state.bookmarks).toHaveLength(1);
});

test("dialogs and unsaved records cannot be bookmarked or enter history", async () => {
    const { entries, action, bus } = setupEntries();
    action.currentController.action.target = "new";
    entries.addBookmark();
    bus.trigger("ACTION_MANAGER:UI-UPDATED");
    await advanceTime(1);
    expect(entries.state.history).toHaveLength(0);
    action.currentController.action.target = "current";
    patchWithCleanup(router, { current: { action: 123, resId: "new" } });
    entries.addBookmark();
    expect(entries.state.bookmarks).toHaveLength(0);
});
