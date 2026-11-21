import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import "./list_renderer";

// Existing explicit js_class references stay valid; the standard registry is untouched.
export { ListController as ComponentListController };
export const componentListView = { ...listView };
registry.category("views").add("custom_web_list", componentListView);
