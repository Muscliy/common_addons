import json
import os
from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

from .test_playground import LOCAL_ENV


@tagged('post_install', '-at_install')
class TestComponentBrowser(HttpCase):
    def test_server_rpc_denies_playground_but_allows_component_preferences(self):
        self.authenticate('admin', 'admin')
        with patch.dict(os.environ, {**LOCAL_ENV, 'TYH_RUNTIME': 'server'}):
            for method, args in [('open_playground', []), ('search_read', [[]]),
                                 ('create', [{'name': 'DENIED'}]), ('get_view', [])]:
                response = self.url_open('/web/dataset/call_kw', data=json.dumps({
                    'jsonrpc': '2.0', 'method': 'call', 'id': 1,
                    'params': {'model': 'web.component.playground.order', 'method': method,
                               'args': args, 'kwargs': {}},
                }), headers={'Content-Type': 'application/json'}).json()
                self.assertEqual(response['error']['data']['name'], 'odoo.exceptions.AccessError')
            response = self.url_open('/web/dataset/call_kw', data=json.dumps({
                'jsonrpc': '2.0', 'method': 'call', 'id': 2,
                'params': {'model': 'web.component.preference', 'method': 'get_preference',
                           'args': ['dialog', 'res.partner'], 'kwargs': {}},
            }), headers={'Content-Type': 'application/json'}).json()
            self.assertEqual(response['result'], {})

    def test_layout_survives_new_browser_session_and_reset(self):
        new_test_user(self.env, login='cwc_browser', groups='base.group_user', context={'no_reset_password': True})
        with patch.dict(os.environ, LOCAL_ENV):
            user = self.env['res.users'].search([('login', '=', 'cwc_browser')])
            self.env['web.component.playground.order'].with_user(user).open_playground()
            action = self.env.ref('custom_web_components.action_playground_list')
            url = f'/odoo/action-{action.id}'
            helpers = r'''
                const wait = async (predicate) => {
                    for (let i = 0; i < 200; i++) {
                        if (predicate()) { return; }
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                    throw new Error('Timed out waiting for list layout');
                };
                const header = name => document.querySelector(`th[data-name="${name}"]`);
                const firstName = () => document.querySelector('thead th[data-name]')?.dataset.name;
                const check = (value, message) => { if (!value) { throw new Error(message); } };
                const settingsRow = name => document.querySelector(`.cwc_settings_row[data-name="${name}"]`);
                const settle = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                const openSettings = async () => {
                    await settle();
                    await wait(() => document.querySelector('.o_optional_columns_dropdown button'));
                    if (!document.querySelector('.cwc_column_settings')) {
                        document.querySelector('.o_optional_columns_dropdown button').click();
                    }
                    await wait(() => document.querySelector('.cwc_reset_layout'));
                    await settle();
                };
                await wait(() => header('name'));
                await openSettings();
            '''
            self.browser_js(url, '(async () => {' + helpers + r'''
                check(firstName() === 'name', 'XML column order');
                check(Math.abs(header('name').getBoundingClientRect().width - 160) < 2, 'XML name width');
                const grip = settingsRow('state').querySelector('.cwc_column_grip');
                const transfer = new DataTransfer();
                grip.dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer: transfer }));
                settingsRow('name').dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: transfer }));
                await wait(() => firstName() === 'state');
                settingsRow('state').querySelector('.cwc_freeze_column').click();
                await wait(() => header('state').classList.contains('cwc_frozen_cell'));
                settingsRow('note').querySelector('input').click();
                await wait(() => !header('note'));
                settingsRow('create_date').querySelector('input').click();
                await wait(() => header('create_date'));
                document.querySelector('.o_optional_columns_dropdown button').click();
                const handle = header('name').querySelector('.o_resize');
                handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: 300, button: 0 }));
                window.dispatchEvent(new PointerEvent('pointermove', { clientX: 370 }));
                window.dispatchEvent(new PointerEvent('pointerup', { clientX: 370 }));
                await openSettings();
                await wait(() => !document.querySelector('.cwc_save_layout').disabled);
                check(Math.abs(header('name').getBoundingClientRect().width - 230) < 2, 'Resized width');
                document.querySelector('.cwc_save_layout').click();
                await wait(() => document.querySelector('.cwc_save_layout')?.disabled && document.querySelector('.cwc_reset_layout')?.disabled === false);
                console.log('test successful');
            })()''', login='cwc_browser', timeout=120)
            self.browser_js(url, '(async () => {' + helpers + r'''
                check(firstName() === 'state', 'Saved column order restored');
                check(header('state').classList.contains('cwc_frozen_cell'), 'Saved frozen column restored');
                check(!header('note') && header('create_date'), 'Saved visibility restored');
                check(!document.querySelector('thead .cwc_column_grip'), 'No header drag controls');
                const scroll = document.querySelector('.o_list_renderer');
                const before = header('state').getBoundingClientRect().left;
                scroll.scrollLeft = 300;
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                check(Math.abs(header('state').getBoundingClientRect().left - before) < 2, 'Frozen header stays during scrolling');
                scroll.scrollLeft = 0;
                await openSettings();
                check(Math.abs(header('name').getBoundingClientRect().width - 230) < 2, 'Saved width restored');
                document.querySelector('.cwc_reset_layout').click();
                await wait(() => firstName() === 'name' && !document.querySelector('.cwc_reset_layout').disabled);
                check(Math.abs(header('name').getBoundingClientRect().width - 160) < 2, 'Reset XML width');
                check(header('note') && !header('create_date'), 'Reset XML visibility');
                check(!document.querySelector('.cwc_frozen_cell'), 'Reset frozen columns');
                console.log('test successful');
            })()''', login='cwc_browser', timeout=120)
            self.browser_js(url, '(async () => {' + helpers + r'''
                check(firstName() === 'name', 'Reset persisted across browser sessions');
                check(header('note') && !header('create_date'), 'Reset visibility persisted');
                check(!document.querySelector('.cwc_frozen_cell'), 'Reset frozen state persisted');
                check(Math.abs(header('name').getBoundingClientRect().width - 160) < 2, 'Reset width persisted');
                console.log('test successful');
            })()''', login='cwc_browser', timeout=120)

    def test_hoot_components(self):
        with patch.dict(os.environ, LOCAL_ENV):
            self.browser_js('/web/tests?headless&loglevel=2&preset=desktop&tag=cwc', '', '',
                            login='admin', timeout=180, success_signal='[HOOT] Test suite succeeded')
