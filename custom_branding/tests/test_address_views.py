from lxml import etree

from odoo.tests.common import TransactionCase

CHINA_ADDRESS_ORDER = [
    "abt_full_address", "abt_address_original", "abt_address_hint", "state_id", "city",
    "abt_address_district", "street", "street2", "zip", "country_id",
]


class TestAddressViewOrder(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.country_id = self.env.ref("base.cn")
        self.env.registry.clear_cache("templates")

    def _fields(self, node):
        return [field.get("name") for field in node.xpath(".//field")]

    def _address_divs(self, arch):
        root = etree.fromstring(arch)
        return root.xpath(
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' o_address_format ')]",
        )

    def _partner_form_arch(self):
        view_id = self.env.ref("base.view_partner_form").id
        views = self.env["res.partner"].get_views([(view_id, "form")], {})
        return views["views"]["form"]["arch"]

    def test_china_uses_module_address_view(self):
        self.assertEqual(
            self.env.ref("base.cn").address_view_id,
            self.env.ref("custom_branding.view_partner_address_form_cn_global"),
        )

    def test_address_view_uses_china_order(self):
        view = self.env.ref("custom_branding.view_partner_address_form_cn_global")
        arch = self.env["ir.ui.view"].get_view(view.id, "form")["arch"]
        divs = self._address_divs(arch)

        self.assertEqual(len(divs), 1)
        self.assertEqual(self._fields(divs[0]), CHINA_ADDRESS_ORDER)
        self.assertEqual(divs[0].xpath("./field[@name='abt_address_hint']")[0].get("invisible"), "1")
        details = divs[0].xpath("./details")
        self.assertEqual(len(details), 1)
        self.assertIsNone(details[0].get("open"))
        self.assertEqual(self._fields(details[0]), CHINA_ADDRESS_ORDER[3:])

    def test_partner_form_uses_china_address_block(self):
        divs = self._address_divs(self._partner_form_arch())

        self.assertTrue(divs)
        self.assertEqual(self._fields(divs[0]), CHINA_ADDRESS_ORDER)

    def test_partner_form_keeps_contact_readonly_rule(self):
        address = self._address_divs(self._partner_form_arch())[0]
        state = address.xpath(".//field[@name='abt_full_address']")[0]

        self.assertEqual(state.get("readonly"), "type == 'contact' and parent_id")

    def test_delivery_subform_uses_the_same_address_input(self):
        divs = self._address_divs(self._partner_form_arch())
        self.assertGreaterEqual(len(divs), 2)
        for address in divs:
            self.assertEqual(self._fields(address), CHINA_ADDRESS_ORDER)

    def test_identity_fields_are_two_columns_above_the_full_width_address(self):
        root = etree.fromstring(self._partner_form_arch())
        identity = root.xpath("//group[@name='abt_partner_identity']")[0]
        address = root.xpath("//group[@name='abt_partner_address_row']")[0]
        self.assertEqual(identity.get("col"), "2")
        self.assertEqual(identity.get("colspan"), "2")
        self.assertEqual(self._fields(identity.xpath("./group[@name='abt_partner_identity_left']")[0]), ["vat", "lang"])
        self.assertEqual(self._fields(identity.xpath("./group[@name='abt_partner_identity_right']")[0]), ["website", "category_id"])
        self.assertEqual(address.get("colspan"), "2")
        self.assertEqual(identity.getparent(), address.getparent())
        self.assertLess(identity.getparent().index(identity), address.getparent().index(address))
