import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";

export class ThemeSwitcher extends Component {
    static template = "showroom_backend_theme.ThemeSwitcher";
    static components = { Dropdown, DropdownItem };
    static props = {};

    get scheme() {
        return cookie.get("color_scheme") === "dark" ? "dark" : "light";
    }

    selectScheme(scheme) {
        if (!["light", "dark"].includes(scheme) || scheme === this.scheme) {
            return;
        }
        cookie.set("color_scheme", scheme);
        browser.location.reload();
    }
}

registry.category("systray").add("showroom_backend_theme.ThemeSwitcher", {
    Component: ThemeSwitcher,
}, { sequence: 1 });
