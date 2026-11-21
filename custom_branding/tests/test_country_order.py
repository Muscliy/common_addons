from odoo.tests.common import TransactionCase


class TestCountryOrder(TransactionCase):
    def test_china_is_first_in_empty_country_dropdown(self):
        china = self.env.ref("base.cn")

        countries = self.env["res.country"].name_search(limit=10)

        self.assertTrue(countries)
        self.assertEqual(countries[0][0], china.id)

    def test_china_respects_dropdown_limit(self):
        china = self.env.ref("base.cn")

        countries = self.env["res.country"].name_search(limit=1)

        self.assertEqual(countries, [(china.id, china.display_name)])

    def test_china_is_not_added_when_domain_excludes_it(self):
        china = self.env.ref("base.cn")

        countries = self.env["res.country"].name_search(
            args=[("id", "!=", china.id)],
            limit=10,
        )

        self.assertNotIn(china.id, [country_id for country_id, _name in countries])

    def test_typed_search_is_not_reordered(self):
        china = self.env.ref("base.cn")

        countries = self.env["res.country"].name_search(name="United", limit=10)

        self.assertNotIn(china.id, [country_id for country_id, _name in countries])
