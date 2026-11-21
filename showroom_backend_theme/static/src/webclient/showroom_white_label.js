import "@web/webclient/user_menu/user_menu_items";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ImageUrlField } from "@web/views/fields/image_url/image_url_field";
import { getShowroomAppIconUrl } from "./showroom_sidebar";

patch(ImageUrlField.prototype, {
    get showroomImageUrl() {
        return this.props.record.resModel === "ir.module.module" && this.props.name === "icon"
            ? getShowroomAppIconUrl(this.state.src)
            : this.state.src;
    },
});

const userMenuItems = registry.category("user_menuitems");
for (const item of ["odoo_account", "support"]) {
    if (userMenuItems.contains(item)) {
        userMenuItems.remove(item);
    }
}
