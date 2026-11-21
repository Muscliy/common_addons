import os
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.custom_web_components.dev.playground.access import playground_enabled

LOCAL_ENV = {'YABO_RUNTIME': 'local', 'YABO_DATABASE_MODE': 'local', 'YABO_ENV': 'test'}


@tagged('post_install', '-at_install')
class TestPlayground(TransactionCase):
    def test_environment_matrix_is_fail_closed(self):
        for runtime in ('', 'local', 'server'):
            for database in ('', 'local', 'remote'):
                for environment in ('', 'local', 'test', 'development', 'staging', 'production'):
                    with patch.dict(os.environ, YABO_RUNTIME=runtime, YABO_DATABASE_MODE=database, YABO_ENV=environment):
                        self.assertEqual(playground_enabled(), runtime == database == 'local' and environment in ('local', 'test'))

    def test_production_denies_menu_action_and_all_demo_data_paths(self):
        model = self.env['web.component.playground.order']
        root = self.env.ref('custom_web_components.menu_developer_tools')
        with patch.dict(os.environ, LOCAL_ENV):
            record = model.create({'name': 'LOCAL-TEST'})
            self.assertIn(root.id, self.env['ir.ui.menu']._visible_menu_ids())
        for settings in [{'YABO_RUNTIME': 'server'}, {'YABO_ENV': 'production'}, {'YABO_DATABASE_MODE': 'remote'}]:
            with patch.dict(os.environ, {**LOCAL_ENV, **settings}):
                for debug in (False, True):
                    self.assertNotIn(root.id, self.env['ir.ui.menu']._visible_menu_ids(debug))
                for index, operation in enumerate([model.open_playground, lambda: model.search_read([]), lambda: model.search_count([]),
                                  lambda: model.read_group([], ['amount:sum'], ['state']),
                                  lambda: record.read(['name']), lambda: record.export_data(['name']),
                                  lambda: record.write({'name': 'DENIED'}), record.unlink,
                                  lambda: model.create({'name': 'DENIED'}),
                                  lambda: model.get_views([(False, 'list')]),
                                  lambda: model.get_view(view_type='list'),
                                  self.env.ref('custom_web_components.action_playground_list')._get_action_dict,
                                  self.env.ref('custom_web_components.action_component_catalog')._get_action_dict,
                                  self.env.ref('custom_web_components.action_theme_palette')._get_action_dict]):
                    with self.subTest(operation_index=index), \
                            self.assertRaises(AccessError), self.cr.savepoint():
                        operation()
                with self.assertRaises(AccessError), self.cr.savepoint():
                    self.env.ref('custom_web_components.action_open_playground').run()

    def test_local_environment_exposes_developer_catalog_actions(self):
        root = self.env.ref('custom_web_components.menu_developer_tools')
        component_menu = self.env.ref('custom_web_components.menu_component_catalog')
        theme_menu = self.env.ref('custom_web_components.menu_theme_palette')
        with patch.dict(os.environ, LOCAL_ENV):
            self.assertIn(root.id, self.env['ir.ui.menu']._visible_menu_ids())
            self.assertIn(component_menu.id, self.env['ir.ui.menu']._visible_menu_ids())
            self.assertIn(theme_menu.id, self.env['ir.ui.menu']._visible_menu_ids())
            component_action = self.env.ref('custom_web_components.action_component_catalog')._get_action_dict()
            theme_action = self.env.ref('custom_web_components.action_theme_palette')._get_action_dict()
        self.assertEqual(component_action['tag'], 'custom_web_components.component_catalog')
        self.assertEqual(theme_action['tag'], 'custom_web_components.theme_palette')

    def test_seed_only_on_open_and_demo_rows_are_user_owned(self):
        alice = new_test_user(self.env, login='playground_alice', groups='base.group_user', context={'no_reset_password': True})
        bob = new_test_user(self.env, login='playground_bob', groups='base.group_user', context={'no_reset_password': True})
        model = self.env['web.component.playground.order']
        with patch.dict(os.environ, LOCAL_ENV):
            self.assertEqual(model.search_count([]), 0)
            model.with_user(alice).open_playground()
            model.with_user(alice).open_playground()
            self.assertEqual(model.with_user(alice).search_count([]), 40)
            self.assertEqual(model.with_user(bob).search_count([]), 0)
            model.with_user(bob).open_playground()
            self.assertEqual(model.search_count([]), 80)
