from odoo.tests.common import TransactionCase


class TestAddressDefaults(TransactionCase):
    def test_contacts_default_to_simplified_chinese_in_english_ui(self):
        partner = self.env["res.partner"].with_context(lang="en_US")
        self.assertEqual(partner.default_get(["lang"])["lang"], "zh_CN")
        for is_company in (True, False):
            record = partner.create({"name": "默认语言验证", "is_company": is_company})
            self.assertEqual(record.lang, "zh_CN")
        explicit = partner.create({"name": "明确语言验证", "lang": "en_US"})
        self.assertEqual(explicit.lang, "en_US")
        explicit.name = "保留已有语言验证"
        self.assertEqual(explicit.lang, "en_US")

    def test_explicit_language_context_and_parent_language_are_preserved(self):
        partner = self.env["res.partner"]
        self.assertEqual(partner.with_context(default_lang="en_US").default_get(["lang"])["lang"], "en_US")
        company = partner.create({"name": "英文公司语言验证", "is_company": True, "lang": "en_US"})
        child = partner.create({"name": "继承公司语言验证", "parent_id": company.id})
        self.assertEqual(child.lang, "en_US")

    def test_address_models_default_to_china(self):
        china = self.env.ref("base.cn")

        partner_defaults = self.env["res.partner"].default_get(["country_id"])
        employee_defaults = self.env["hr.employee"].default_get(
            ["private_country_id"],
        )
        bank_defaults = self.env["res.bank"].default_get(["country"])

        self.assertEqual(partner_defaults["country_id"], china.id)
        self.assertEqual(employee_defaults["private_country_id"], china.id)
        self.assertEqual(bank_defaults["country"], china.id)

    def test_explicit_country_default_is_preserved(self):
        united_states = self.env.ref("base.us")

        partner_defaults = self.env["res.partner"].with_context(
            default_country_id=united_states.id,
        ).default_get(["country_id"])
        employee_defaults = self.env["hr.employee"].with_context(
            default_private_country_id=united_states.id,
        ).default_get(["private_country_id"])
        bank_defaults = self.env["res.bank"].with_context(
            default_country=united_states.id,
        ).default_get(["country"])

        self.assertEqual(partner_defaults["country_id"], united_states.id)
        self.assertEqual(
            employee_defaults["private_country_id"],
            united_states.id,
        )
        self.assertEqual(bank_defaults["country"], united_states.id)
