import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

const HISTORY_LIMIT = 50;

export function sidebarStorageKey(db, uid) {
    return `tyj.sidebar.entries:${db}:${uid}`;
}

export function validSidebarEntry(entry) {
    return entry && typeof entry.name === "string" && entry.name.length > 0
        && typeof entry.url === "string" && /^\/(?:app|odoo|web)(?:\/|\?|$)/.test(entry.url)
        && !entry.url.includes("\\");
}

export function createSidebarEntries(env, { action, notification }, storageKey) {
    const state = reactive({ bookmarks: [], history: [] });
    try {
        const saved = JSON.parse(browser.localStorage.getItem(storageKey) || "{}");
        for (const kind of ["bookmarks", "history"]) {
            state[kind] = Array.isArray(saved?.[kind]) ? saved[kind].filter(validSidebarEntry) : [];
        }
        state.history = state.history.slice(0, HISTORY_LIMIT);
    } catch (error) {
        notification.add(_t("无法读取侧栏书签和记录，将使用空列表。"), { type: "warning" });
    }
    function save() {
        try {
            browser.localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (error) {
            notification.add(_t("浏览器无法保存书签和记录，刷新后可能丢失。"), { type: "warning" });
        }
    }
    function currentEntry() {
        const controller = action.currentController;
        const currentAction = controller?.action;
        if (!currentAction || currentAction.target === "new" || !router.current.action
            || router.current.resId === "new") {
            return null;
        }
        const route = { ...router.current };
        delete route.debug;
        const entry = {
            name: controller.displayName || currentAction.name,
            url: router.stateToUrl(route),
        };
        return validSidebarEntry(entry) ? entry : null;
    }
    let timer;
    env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => {
        browser.clearTimeout(timer);
        // The action service commits the route on the next browser tick.
        timer = browser.setTimeout(() => {
            const entry = currentEntry();
            if (entry) {
                state.history = [entry, ...state.history.filter((item) => item.url !== entry.url)]
                    .slice(0, HISTORY_LIMIT);
                save();
            }
        });
    });
    return {
        state,
        currentEntry,
        addBookmark() {
            const entry = currentEntry();
            if (!entry) {
                notification.add(_t("请先打开一个已保存的页面。"), { type: "warning" });
                return;
            }
            state.bookmarks = [entry, ...state.bookmarks.filter((item) => item.url !== entry.url)];
            save();
            notification.add(_t("已添加到书签"), { type: "success" });
        },
        remove(kind, url) {
            if (!["bookmarks", "history"].includes(kind)) {
                return;
            }
            state[kind] = state[kind].filter((item) => item.url !== url);
            save();
        },
    };
}

registry.category("services").add("showroom_sidebar_entries", {
    dependencies: ["action", "notification"],
    start(env, services) {
        return createSidebarEntries(env, services, sidebarStorageKey(session.db, user.userId));
    },
});
