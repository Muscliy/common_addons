import os

from odoo import api, models
from odoo.exceptions import AccessError


def playground_enabled() -> bool:
    return (os.environ.get('TYH_RUNTIME') == 'local'
            and os.environ.get('TYH_DATABASE_MODE') == 'local'
            and os.environ.get('TYH_ENV') in ('local', 'test'))


def check_playground_access(env) -> None:
    if not playground_enabled() or not env.user.has_group('base.group_user'):
        raise AccessError(env._('Component Playground is available only in local development.'))


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug)
        if playground_enabled():
            return visible
        root = self.env.ref('custom_web_components.menu_developer_tools', raise_if_not_found=False)
        if not root:
            return visible
        hidden = self.sudo().with_context(**{'ir.ui.menu.full_list': True}).search([('id', 'child_of', root.id)])
        # Filter outside the core cached method: never cache a development result for a server process.
        return visible - set(hidden.ids)


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        if (self.sudo().res_model or '').startswith('web.component.playground.'):
            check_playground_access(self.env)
        return super()._get_action_dict()


class IrActionsClient(models.Model):
    _inherit = 'ir.actions.client'

    def _get_action_dict(self):
        if self.sudo().tag in {
            'custom_web_components.component_catalog',
            'custom_web_components.theme_palette',
        }:
            check_playground_access(self.env)
        return super()._get_action_dict()
