import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SidebarBookmarkMenu extends Component {
    static template = "showroom_backend_theme.SidebarBookmarkMenu";
    static components = { DropdownItem };
    static props = {};
    setup() {
        this.entries = useService("showroom_sidebar_entries");
    }
}

registry.category("cogMenu").add("showroom-sidebar-bookmark", {
    Component: SidebarBookmarkMenu,
    groupNumber: 90,
    isDisplayed: (env) => !env.inDialog,
});
