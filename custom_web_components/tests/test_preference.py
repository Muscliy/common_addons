from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestComponentPreference(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice = new_test_user(cls.env, login='cwc_alice', groups='base.group_user', context={'no_reset_password': True})
        cls.bob = new_test_user(cls.env, login='cwc_bob', groups='base.group_user', context={'no_reset_password': True})
        cls.view = cls.env.ref('custom_web_components.view_playground_order_list')
        cls.scope = ('list', cls.view.model, cls.view.id)
        cls.preferences = cls.env['web.component.preference'].with_user(cls.alice)

    def test_save_read_reset_and_user_isolation(self):
        config = {'name': {'sequence': 2, 'width': 180, 'visible': False, 'frozen': True}}
        self.preferences.save_preference(*self.scope, config=config)
        self.assertEqual(self.preferences.get_preference(*self.scope), config)
        bob_preferences = self.preferences.with_user(self.bob)
        self.assertEqual(bob_preferences.get_preference(*self.scope), {})
        bob_preferences.save_preference(*self.scope, config={'amount': {'width': 240}})
        self.preferences.reset_preference(*self.scope)
        self.assertEqual(self.preferences.get_preference(*self.scope), {})
        self.assertEqual(bob_preferences.get_preference(*self.scope), {'amount': {'width': 240}})

    def test_view_key_and_component_isolation(self):
        second = self.view.copy({'name': 'Second preference test view'})
        for view_id, width in [(self.view.id, 100), (second.id, 200)]:
            self.preferences.save_preference('list', self.view.model, view_id, config={'name': {'width': width}})
        self.preferences.save_preference(*self.scope, key='other', config={'name': {'width': 300}})
        self.preferences.save_preference('dialog', 'res.partner', config={'size': 'large'})
        self.assertEqual(self.preferences.get_preference(*self.scope)['name']['width'], 100)
        self.assertEqual(self.preferences.get_preference('list', self.view.model, second.id)['name']['width'], 200)
        self.assertEqual(self.preferences.get_preference(*self.scope, key='other')['name']['width'], 300)
        self.assertEqual(self.preferences.get_preference('dialog', 'res.partner'), {'size': 'large'})

    def test_direct_crud_cannot_access_or_transfer_another_users_config(self):
        self.preferences.save_preference(*self.scope, config={'name': {'width': 120}})
        record = self.preferences.search([])
        other = record.with_user(self.bob)
        for operation in [lambda: other.read(['config']), lambda: other.write({'config': {}}),
                          other.unlink, lambda: record.write({'user_id': self.bob.id}),
                          lambda: self.preferences.create({'user_id': self.bob.id, 'component_type': 'dialog',
                                                           'model': 'res.partner', 'config': {'size': 'large'}})]:
            with self.assertRaises(AccessError), self.cr.savepoint():
                operation()
        self.assertFalse(self.preferences.with_user(self.bob).search([]))

    def test_validation_and_portal_denial(self):
        for config in [[], {'name': {'width': -1}}, {'name': {'width': True}},
                       {'name': {'sequence': 10001}}, {'name': {'visible': 1}}, {'name': {'frozen': 'true'}},
                       {'name': {'unexpected': 1}}, {'name': {'width': 4001}}]:
            with self.subTest(config=config), self.assertRaises(ValidationError), self.cr.savepoint():
                self.preferences.save_preference(*self.scope, config=config)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.preferences.save_preference('list', 'res.partner', self.view.id, config={'name': {'width': 100}})
        portal = new_test_user(self.env, login='cwc_portal', groups='base.group_portal', context={'no_reset_password': True})
        with self.assertRaises(AccessError):
            self.preferences.with_user(portal).get_preference(*self.scope)

    def test_save_updates_existing_row_and_empty_config(self):
        for width in (120, 180, 240):
            self.preferences.save_preference(*self.scope, config={'name': {'width': width}})
        self.assertEqual(self.preferences.search_count([]), 1)
        self.preferences.save_preference(*self.scope, config={})
        self.assertEqual(self.preferences.get_preference(*self.scope), {})

    def test_scope_injection_and_oversized_payload_are_rejected(self):
        values = {'component_type': 'dialog', 'model': 'res.partner', 'config': {'size': 'large'}}
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.preferences.create({**values, 'scope': 'forged'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.preferences.with_context(default_scope='forged').create(values)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.preferences.save_preference('dialog', 'res.partner', config={'text': 'x' * 65536})

    def test_nested_lists_are_isolated_by_parent_view_path_and_user(self):
        view = self.env['ir.ui.view'].create({
            'name': 'Nested preference test', 'model': 'res.partner', 'type': 'form',
            'arch': '<form><field name="child_ids"/></form>',
        })
        first = ('list_nested', 'res.partner', view.id, 'x2many:child_ids')
        second = ('list_nested', 'res.partner', view.id, 'x2many:child_ids.child_ids')
        self.preferences.save_preference(*first, config={'name': {'width': 180}})
        self.preferences.save_preference(*second, config={'name': {'width': 240}})
        self.assertEqual(self.preferences.get_preference(*first), {'name': {'width': 180}})
        self.assertEqual(self.preferences.get_preference(*second), {'name': {'width': 240}})
        self.assertEqual(self.preferences.with_user(self.bob).get_preference(*first), {})
        self.preferences.reset_preference(*first)
        self.assertEqual(self.preferences.get_preference(*first), {})
        self.assertEqual(self.preferences.get_preference(*second), {'name': {'width': 240}})

    def test_nested_scope_and_column_options_are_validated(self):
        view = self.env['ir.ui.view'].create({
            'name': 'Nested validation test', 'model': 'res.partner', 'type': 'form',
            'arch': '<form><field name="child_ids"/></form>',
        })
        for model, view_id, key, config in [
            ('res.partner', False, 'x2many:child_ids', {}),
            ('res.partner', view.id, 'default', {}),
            ('res.partner', view.id, 'x2many:name', {}),
            ('res.partner', view.id, 'x2many:unknown', {}),
            ('res.users', view.id, 'x2many:child_ids', {}),
            ('res.partner', view.id, 'x2many:child_ids', {'name': {'width': -1}}),
            ('res.partner', view.id, 'x2many:child_ids', {'name': {'unexpected': 1}}),
        ]:
            with self.subTest(model=model, key=key, config=config):
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    self.preferences.save_preference('list_nested', model, view_id, key, config)
