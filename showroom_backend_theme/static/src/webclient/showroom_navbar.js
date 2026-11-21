import { url } from "@web/core/utils/urls";
import { useBus } from "@web/core/utils/hooks";
import { user, userBus } from "@web/core/user";
import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";

const SETTINGS_MENU_XMLID = "base.menu_administration";
const APPS_MENU_XMLID = "base.menu_management";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        useBus(userBus, "ACTIVE_COMPANIES_CHANGED", () => this.render());
    },

    get showroomCompanyName() {
        return user.activeCompany?.name || "";
    },

    get showroomCompanyLogoUrl() {
        return url("/web/image", {
            model: "res.company",
            id: user.activeCompany?.id,
            field: "logo",
        });
    },

    get showroomSettingsApp() {
        return this.menuService
            .getApps()
            .find((app) => app.xmlid === SETTINGS_MENU_XMLID && app.actionID);
    },

    get showroomAppsApp() {
        return this.menuService
            .getApps()
            .find((app) => app.xmlid === APPS_MENU_XMLID && app.actionID);
    },

    openShowroomSettings() {
        if (this.showroomSettingsApp) {
            return this.menuService.selectMenu(this.showroomSettingsApp);
        }
    },

    openShowroomApps() {
        if (this.showroomAppsApp) {
            return this.menuService.selectMenu(this.showroomAppsApp);
        }
    },
});
