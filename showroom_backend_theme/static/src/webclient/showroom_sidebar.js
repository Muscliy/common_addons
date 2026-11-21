import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, onPatched, onWillUnmount, useExternalListener, useRef, useState } from "@odoo/owl";

const SETTINGS_MENU_XMLID = "base.menu_administration";
const APPS_MENU_XMLID = "base.menu_management";
const SIDEBAR_COLLAPSED_KEY = "tyj.sidebar.collapsed";
const DEFAULT_APP_ICON = "/web/static/img/default_icon_app.png";
const APP_ICON_CACHE_KEY = Date.now().toString();

export function firstOverflowIndex(heights, maxHeight, gap) {
    let usedHeight = 0;
    for (const [index, height] of heights.entries()) {
        const nextHeight = usedHeight + (index ? gap : 0) + height;
        if (index && nextHeight > maxHeight) {
            return index;
        }
        usedHeight = nextHeight;
    }
    return heights.length;
}

export function menuTopForTrigger(triggerCenter, panelHeight, sidebarHeight) {
    const maxTop = Math.max(8, sidebarHeight - panelHeight - 8);
    return Math.round(Math.max(8, Math.min(triggerCenter - panelHeight / 2, maxTop)));
}

export function getShowroomAppIconUrl(src) {
    if (!/^\/[\w-]+\/static\/description\/icon\.(?:png|svg)(?:[?#]|$)/.test(src || "")) {
        return src;
    }
    // Share one fresh URL per page load across the sidebar and Apps cards.
    const url = new URL(src, browser.location.origin);
    url.searchParams.set("showroom_icon", APP_ICON_CACHE_KEY);
    return `${url.pathname}${url.search}${url.hash}`;
}

export class ShowroomSidebar extends Component {
    static template = "showroom_backend_theme.ShowroomSidebar";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.menuService = useService("menu");
        this.entries = useService("showroom_sidebar_entries");
        this.entryState = useState(this.entries.state);
        this.tabs = [
            { id: "apps", name: "应用", icon: "fa-th-large" },
            { id: "bookmarks", name: "书签", icon: "fa-bookmark-o" },
            { id: "history", name: "记录", icon: "fa-history" },
        ];
        this.sidebarRef = useRef("sidebar");
        this.state = useState({
            activeTab: "apps",
            isCollapsed: browser.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1",
            openAppId: null,
            splitIndex: null,
            menuTop: 8,
            menuReady: false,
            collapsedSectionIds: [],
        });
        const renderAfterMenuChange = () => {
            this.closeAppMenu();
            this.render();
        };
        this.env.bus.addEventListener("MENUS:APP-CHANGED", renderAfterMenuChange);
        useExternalListener(document, "pointerdown", (event) => {
            if (this.state.openAppId && !this.sidebarRef.el?.contains(event.target)) {
                this.closeAppMenu();
            }
        });
        useExternalListener(document, "keydown", (event) => {
            if (event.key === "Escape" && this.state.openAppId) {
                this.closeAppMenu();
            }
        });
        useExternalListener(window, "resize", () => this.reflowMenu());
        onPatched(() => this.reflowMenu());
        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", renderAfterMenuChange);
            browser.clearTimeout(this.sectionReflowTimer);
        });
    }

    get apps() {
        return this.menuService
            .getApps()
            .filter(
                (app) =>
                    ![SETTINGS_MENU_XMLID, APPS_MENU_XMLID].includes(app.xmlid) && app.actionID
            );
    }

    selectTab(tab) {
        this.closeAppMenu();
        this.state.activeTab = tab;
    }

    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    get openApp() {
        return this.apps.find((app) => app.id === this.state.openAppId);
    }

    get openSections() {
        return this.openApp ? this.menuService.getMenuAsTree(this.openApp.id).childrenTree : [];
    }

    get menuColumns() {
        const sections = this.openSections;
        const splitIndex = this.state.splitIndex;
        return splitIndex !== null && splitIndex < sections.length
            ? [sections.slice(0, splitIndex), sections.slice(splitIndex)]
            : [sections];
    }

    hasSections(app) {
        return Boolean(this.menuService.getMenuAsTree(app.id).childrenTree.length);
    }

    getAppHref(app) {
        return `/app/${app.actionPath || `action-${app.actionID}`}`;
    }

    getAppIcon(app) {
        // Use the application file so replaced icons do not retain old menu attachments.
        const parts = (app.webIcon || "").split(",");
        if (parts.length === 2 && parts[0] && parts[1].startsWith("static/")) {
            return getShowroomAppIconUrl(`/${parts[0]}/${parts[1]}`);
        }
        return getShowroomAppIconUrl(app.webIconData || DEFAULT_APP_ICON);
    }

    selectApp(app) {
        this.closeAppMenu();
        return this.menuService.selectMenu(app);
    }

    selectMenu(menu) {
        this.closeAppMenu();
        return this.menuService.selectMenu(menu);
    }

    closeAppMenu() {
        browser.clearTimeout(this.sectionReflowTimer);
        this.sectionReflowPending = false;
        this.state.openAppId = null;
        this.state.menuReady = false;
    }

    onSectionToggle(section, event) {
        const collapsed = new Set(this.state.collapsedSectionIds);
        if (event.currentTarget.open) {
            collapsed.delete(section.id);
        } else {
            collapsed.add(section.id);
        }
        if (collapsed.size === this.state.collapsedSectionIds.length) {
            return;
        }
        this.state.collapsedSectionIds = [...collapsed];
        // Measure after the content transition, so an intermediate height cannot move a card
        // between columns or pull the whole panel away from its trigger.
        browser.clearTimeout(this.sectionReflowTimer);
        this.sectionReflowPending = true;
        this.sectionReflowTimer = browser.setTimeout(() => {
            this.sectionReflowPending = false;
            this.reflowMenu();
        }, 200);
    }

    reflowMenu() {
        const sidebar = this.sidebarRef.el;
        const panel = sidebar?.querySelector(".o_showroom_app_submenu");
        if (!panel || this.sectionReflowPending) {
            return;
        }
        const column = panel.querySelector(".o_showroom_menu_column");
        const sidebarRect = sidebar.getBoundingClientRect();
        const style = getComputedStyle(panel);
        const verticalInset = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
            + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        const sidebarHeight = browser.innerHeight - sidebarRect.top;
        const availableHeight = sidebarHeight - verticalInset - 16;
        const gap = parseFloat(getComputedStyle(column).rowGap) || 0;
        const heights = [...panel.querySelectorAll(".o_showroom_menu_card")]
            .map((card) => card.getBoundingClientRect().height);
        const splitIndex = firstOverflowIndex(heights, availableHeight, gap);
        if (this.state.splitIndex !== splitIndex) {
            this.state.splitIndex = splitIndex;
            return;
        }
        const trigger = sidebar.querySelector(".o_showroom_app_row.is-open .o_showroom_app_more");
        if (trigger) {
            const triggerRect = trigger.getBoundingClientRect();
            const triggerCenter = triggerRect.top + triggerRect.height / 2 - sidebarRect.top;
            const menuTop = menuTopForTrigger(
                triggerCenter, panel.getBoundingClientRect().height, sidebarHeight
            );
            if (this.state.menuTop !== menuTop) {
                this.state.menuTop = menuTop;
                return;
            }
        }
        if (!this.state.menuReady) {
            this.state.menuReady = true;
        }
    }

    toggleAppMenu(app) {
        if (this.state.openAppId === app.id) {
            this.closeAppMenu();
            return;
        }
        this.state.splitIndex = null;
        this.state.menuTop = 8;
        this.state.menuReady = false;
        this.state.collapsedSectionIds = [];
        this.state.openAppId = app.id;
    }

    toggleSidebar() {
        this.closeAppMenu();
        this.state.isCollapsed = !this.state.isCollapsed;
        browser.localStorage.setItem(
            SIDEBAR_COLLAPSED_KEY,
            this.state.isCollapsed ? "1" : "0"
        );
        browser.setTimeout(() => browser.dispatchEvent(new Event("resize")), 200);
    }
}

patch(WebClient, {
    components: {
        ...WebClient.components,
        ShowroomSidebar,
    },
});
