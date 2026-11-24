import os
from pathlib import Path
from unittest.mock import patch

from lxml import etree
from werkzeug.exceptions import NotFound

from odoo.exceptions import AccessError
from odoo.modules.module import get_module_path
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.showroom_backend_theme.app_access import apps_enabled
from odoo.addons.showroom_backend_theme.controllers.app_access import (
    AppAccessDataSet,
    AppAccessHome,
)
from odoo.addons.showroom_backend_theme.models import app_access as model_policy
from odoo.addons.web.controllers.dataset import DataSet
from odoo.addons.web.controllers.home import Home


@tagged('post_install', '-at_install')
class TestAppAccess(TransactionCase):
    def test_list_tables_fill_available_renderer_width(self):
        stylesheet = (Path(get_module_path('showroom_backend_theme')) / 'static' / 'src'
                      / 'webclient' / 'showroom_theme.scss').read_text(encoding='utf-8')
        self.assertIn(
            "> .o_list_table {\n        min-width: 100%;\n    }",
            stylesheet,
        )

    def test_brand_promotion_keeps_standard_extension_point(self):
        view = self.env.ref('showroom_backend_theme.showroom_brand_promotion')
        self.assertIn('web.brand_promotion_message', view.arch_db)

    def test_login_uses_clean_web_layout(self):
        login_branding = self.env.ref('showroom_backend_theme.showroom_login_branding')
        self.assertFalse(login_branding.active)
        combined = etree.fromstring(self.env.ref('web.login_layout').get_combined_arch().encode())
        self.assertTrue(combined.xpath(".//t[@t-set='no_header'][@t-value='True']"))
        self.assertTrue(combined.xpath(".//t[@t-set='no_footer'][@t-value='True']"))
        self.assertNotIn('oe_website_login_container', etree.tostring(combined, encoding='unicode'))

    def test_runtime_defaults_closed_and_does_not_follow_environment(self):
        for value in (None, "", "server", "test", "production", "LOCAL"):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                os.environ['TYH_ENV'] = 'local'
                if value is not None:
                    os.environ["TYH_RUNTIME"] = value
                self.assertFalse(apps_enabled())
        for environment in ('local', 'test', 'production'):
            for database in ('local', 'remote'):
                with self.subTest(environment=environment, database=database), patch.dict(
                    os.environ, TYH_RUNTIME='local', TYH_ENV=environment, TYH_DATABASE_MODE=database,
                ):
                    self.assertTrue(apps_enabled())

    def test_menus_and_action(self):
        menus = self.env["ir.ui.menu"]
        root = self.env.ref("base.menu_management")
        action = self.env.ref("base.open_module_tree")
        for mode in ("server", "local"):
            with self.subTest(mode=mode), patch.dict(os.environ, TYH_RUNTIME=mode):
                self.env.registry.clear_cache()
                for debug in (False, True):
                    visible = menus._visible_menu_ids(debug)
                    self.assertEqual(root.id in visible, mode == "local")
                if mode == "local":
                    self.assertEqual(action._get_action_dict()["res_model"], "ir.module.module")
                else:
                    with self.assertRaises(AccessError):
                        action._get_action_dict()
        self.env.registry.clear_cache()

    def test_local_runtime_preserves_native_user_permissions(self):
        user = new_test_user(self.env, login='app_access_internal', groups='base.group_user')
        with patch.dict(os.environ, TYH_RUNTIME='local'):
            menus = self.env['ir.ui.menu'].with_user(user)
            self.assertNotIn(self.env.ref('base.menu_management').id, menus._visible_menu_ids())
            self.assertFalse(self.env['ir.module.module'].with_user(user).has_access('write'))

    def test_internal_user_can_load_non_app_action(self):
        user = new_test_user(self.env, login='regular_action_internal', groups='base.group_user')
        action = self.env['ir.actions.act_window'].create({
            'name': 'Regular partner action',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
        })
        result = action.with_user(user)._get_action_dict()
        self.assertEqual(result['res_model'], 'res.partner')

    def test_routes_and_rpc(self):
        with patch.dict(os.environ, TYH_RUNTIME="server", TYH_ENV="local"):
            for path in ("apps", "apps/1", "action-1/apps"):
                with self.assertRaises(NotFound):
                    AppAccessHome.web_client.__wrapped__(AppAccessHome(), subpath=path)
            for method in ("call_kw", "call_button"):
                for model in ("ir.module.module", "base.module.upgrade", "base.import.module"):
                    with self.assertRaises(AccessError):
                        getattr(AppAccessDataSet, method).__wrapped__(AppAccessDataSet(), model, "button_install", [], {})
            with patch.object(DataSet, "call_kw", return_value="allowed"):
                self.assertEqual(AppAccessDataSet.call_kw.__wrapped__(AppAccessDataSet(), "res.partner", "search_read", [], {}), "allowed")
        with patch.dict(os.environ, TYH_RUNTIME="local", TYH_ENV="production"):
            with patch.object(Home, "web_client", return_value="allowed"):
                self.assertEqual(AppAccessHome.web_client.__wrapped__(AppAccessHome(), subpath="apps"), "allowed")
            with patch.object(DataSet, "call_button", return_value="allowed"):
                self.assertEqual(AppAccessDataSet.call_button.__wrapped__(AppAccessDataSet(), "ir.module.module", "button_install", [], {}), "allowed")

    def test_installation_cannot_bypass_via_settings_or_state_write(self):
        module = self.env["ir.module.module"].search([("name", "=", "base")])
        with patch.dict(os.environ, TYH_RUNTIME="server", TYH_ENV="local"), patch.object(model_policy, "request", True):
            with self.assertRaises(AccessError):
                module.button_install()
            with self.assertRaises(AccessError):
                module._button_immediate_function(lambda records: None)
            with self.assertRaises(AccessError):
                module._import_zipfile(None)
            for state in ("to install", "to upgrade", "to remove"):
                with self.assertRaises(AccessError):
                    module.sudo().write({"state": state})
