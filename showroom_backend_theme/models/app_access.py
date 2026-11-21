from odoo import api, models
from odoo.http import request

from ..app_access import apps_enabled, check_apps_access, is_app_model


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug)
        if apps_enabled():
            return visible
        root = self.env.ref("base.menu_management", raise_if_not_found=False)
        if not root:
            return visible
        hidden = self.sudo().with_context(**{"ir.ui.menu.full_list": True}).search([
            ("id", "child_of", root.id),
        ])
        return visible - set(hidden.ids)


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    def _get_action_dict(self):
        # Core serializes actions with sudo and then limits output to an explicit
        # safe-field allowlist. Preserve that contract for ordinary internal
        # users while checking only the target model under sudo.
        if is_app_model(self.sudo().res_model or ""):
            check_apps_access()
        return super()._get_action_dict()


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def button_install(self):
        # Preserve controlled CLI installation during deployment and initialization.
        if request:
            check_apps_access()
        return super().button_install()

    def _button_immediate_function(self, function):
        if request:
            check_apps_access()
        return super()._button_immediate_function(function)

    def _import_zipfile(self, *args, **kwargs):
        # Optional base_import_module upload endpoint bypasses dataset RPC.
        if request:
            check_apps_access()
        return super()._import_zipfile(*args, **kwargs)

    def write(self, vals):
        # Also reject direct RPC state changes, including sudo/server actions.
        if request and vals.get("state") in ("to install", "to upgrade", "to remove"):
            check_apps_access()
        return super().write(vals)
