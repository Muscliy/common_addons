from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import ChromeBrowser


@tagged("post_install", "-at_install")
class TestAddressBrowser(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.cn")
        cls.partner = cls.env["res.partner"].create({
            "name": "地址输入试用公司", "is_company": True,
        })

    def _run_address_browser(self, code):
        original = ChromeBrowser._wait_code_ok

        def capture(browser, *args, **kwargs):
            result = original(browser, *args, **kwargs)
            browser.take_screenshot("address_success_").result(timeout=10)
            return result

        with patch.object(ChromeBrowser, "_wait_code_ok", capture):
            self.browser_js(
                f"/odoo/action-base.action_partner_form/{self.partner.id}", code,
                ready="Boolean(document.querySelector('[name=abt_full_address] input'))",
                login="admin", timeout=60,
            )

    def test_company_address_input_and_save(self):
        self._run_address_browser("""
            (async () => {
                const wait = async (predicate) => {
                    for (let i = 0; i < 100; i++) {
                        if (predicate()) return;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('Address UI did not reach the expected state');
                };
                const block = document.querySelector('.o_address_format');
                if (block.querySelector('details').open) throw new Error('Details must start collapsed');
                const input = block.querySelector('[name=abt_full_address] input');
                const vat = document.querySelector('[name=vat]').getBoundingClientRect();
                const website = document.querySelector('[name=website]').getBoundingClientRect();
                const language = document.querySelector('[name=lang]').getBoundingClientRect();
                const tags = document.querySelector('[name=category_id]').getBoundingClientRect();
                const address = input.getBoundingClientRect();
                if (vat.left >= website.left || Math.abs(vat.top - website.top) > 15) {
                    throw new Error('Identity fields must form two columns on desktop');
                }
                if (address.top < Math.max(language.bottom, tags.bottom) || address.width < vat.width * 1.5) {
                    throw new Error('Address must occupy a full row below the identity fields');
                }
                input.value = '浙江省宁波市鄞州区测试路88号3幢201室';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new FocusEvent('blur', { bubbles: true }));
                await wait(() => block.querySelector('[name=city] input')?.value === '宁波市');
                if (block.textContent.includes('已识别：')) throw new Error('Recognition hint must be hidden');
                if (block.querySelector('[name=street] input').checkVisibility({ contentVisibilityAuto: true })) {
                    throw new Error('Street must stay hidden until details are opened');
                }
                document.querySelector('.o_form_button_save').click();
                await wait(() => !document.querySelector('.o_form_status_indicator_buttons:not(.invisible)'));
                console.log('test successful');
            })().catch(error => console.error(error));
        """)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.city, "宁波市")
        self.assertEqual(self.partner.street, "鄞州区测试路88号3幢201室")

    def test_delivery_dialog_uses_full_address(self):
        self._run_address_browser("""
            (async () => {
                const wait = async (predicate) => {
                    for (let i = 0; i < 100; i++) {
                        if (predicate()) return;
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                    throw new Error('Delivery dialog did not reach the expected state');
                };
                document.querySelector('[name=child_ids] .o-kanban-button-new').click();
                await wait(() => document.querySelector('.modal [name=type]'));
                const delivery = document.querySelector('.modal [name=type] input[data-value=delivery]')
                    || document.querySelector('.modal [name=type] input[value=delivery]');
                if (!delivery) throw new Error('Delivery address type not found');
                delivery.click();
                await wait(() => document.querySelector('.modal [name=abt_full_address] input'));
                const input = document.querySelector('.modal [name=abt_full_address] input');
                input.value = '上海市闵行区测试路1号';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new FocusEvent('blur', { bubbles: true }));
                await wait(() => document.querySelector('.modal [name=city] input')?.value === '上海市');
                if (document.querySelector('.modal').textContent.includes('已识别：')) {
                    throw new Error('Delivery recognition hint must be hidden');
                }
                document.querySelector('.modal .o_form_button_save').click();
                await wait(() => !document.querySelector('.modal'));
                document.querySelector('.o_form_button_save').click();
                await wait(() => !document.querySelector('.o_form_status_indicator_buttons:not(.invisible)'));
                console.log('test successful');
            })().catch(error => console.error(error));
        """)

        self.partner.invalidate_recordset()
        delivery = self.partner.child_ids.filtered(lambda record: record.type == "delivery")
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.city, "上海市")
        self.assertEqual(delivery.street, "闵行区测试路1号")

    def test_personal_address_at_mobile_width(self):
        self.browser_size = "390x844"
        self.partner.write({"is_company": False})
        self._run_address_browser("""
            const block = document.querySelector('.o_address_format');
            const input = block.querySelector('[name=abt_full_address] input');
            const bounds = input.getBoundingClientRect();
            if (bounds.width < 100 || bounds.right > window.innerWidth) {
                throw new Error('Full address input does not fit the mobile viewport');
            }
            if (block.querySelector('details').open) throw new Error('Details must start collapsed');
            console.log('test successful');
        """)
