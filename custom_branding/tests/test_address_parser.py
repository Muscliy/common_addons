from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAddressParser(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.cn")
        cls.parser = cls.env["abt.address.parser"]

    def test_shared_parser_recognizes_provinces_cities_and_districts(self):
        cases = [
            ("浙江省宁波市鄞州区首南街道88号", "浙江省", "宁波市", "鄞州区", "鄞州区首南街道88号"),
            ("宁波市鄞州区首南街道88号", "浙江省", "宁波市", "鄞州区", "鄞州区首南街道88号"),
            ("浙江宁波鄞州区首南街道88号", "浙江省", "宁波市", "鄞州区", "鄞州区首南街道88号"),
            ("上海市闵行区测试路1号", "上海市", "上海市", "闵行区", "闵行区测试路1号"),
            ("中国，广东省 深圳市，南山区 科技路8号", "广东省", "深圳市", "南山区", "南山区科技路8号"),
            ("新疆维吾尔自治区乌鲁木齐市天山区测试路1号", "新疆维吾尔自治区", "乌鲁木齐市", "天山区", "天山区测试路1号"),
        ]
        for text, province, city, district, street in cases:
            with self.subTest(text=text):
                result = self.parser.parse(text)
                self.assertEqual(result["province"], province)
                self.assertEqual(result["city"], city)
                self.assertEqual(result["district"], district)
                self.assertEqual(result["street"], street)
                self.assertEqual(result["original"], text)

    def test_ambiguous_unknown_and_road_names_are_not_guessed(self):
        for text in ("朝阳区测试路88号", "宁波路88号", "河南路88号", "某某园区8号", "12 Example Road"):
            with self.subTest(text=text):
                result = self.parser.parse(text)
                self.assertEqual(result["status"], "unrecognized")
                self.assertEqual(result["street"], text)
                self.assertFalse(result["province"])
        result = self.parser.parse("浙江省宁波市新设区测试路8号")
        self.assertEqual(result["city"], "宁波市")
        self.assertEqual(result["street"], "新设区测试路8号")
        self.assertFalse(result["district"])

    def test_full_address_create_write_clear_and_reports(self):
        text = "浙江省宁波市鄞州区测试路88号3幢201室"
        for company in (True, False):
            partner = self.env["res.partner"].create({
                "name": "完整地址验证", "is_company": company, "abt_full_address": text,
            })
            self.assertEqual(partner.state_id, self.env.ref("base.state_cn_ZJ"))
            self.assertEqual(partner.city, "宁波市")
            self.assertEqual(partner.abt_address_district, "鄞州区")
            self.assertEqual(partner.street, "鄞州区测试路88号3幢201室")
            self.assertEqual(partner.abt_address_original, text)
            self.assertIn("鄞州区测试路88号", partner._display_address())
            partner.write({"abt_full_address": "上海市闵行区测试路1号"})
            self.assertEqual(partner.abt_full_address, "上海市闵行区测试路1号")
            self.assertEqual(partner.state_id, self.env.ref("base.state_cn_SH"))
            partner.write({"abt_full_address": "某某园区8号"})
            self.assertEqual(partner.street, "某某园区8号")
            self.assertFalse(partner.state_id)
            self.assertFalse(partner.city)
            partner.write({"abt_full_address": False})
            self.assertFalse(partner.abt_full_address)
            self.assertFalse(partner.street)
            self.assertFalse(partner.abt_address_original)

    def test_legacy_fields_and_manual_edits_update_full_address(self):
        partner = self.env["res.partner"].create({
            "name": "原生地址验证", "country_id": self.env.ref("base.cn").id,
            "state_id": self.env.ref("base.state_cn_ZJ").id, "city": "宁波市",
            "street": "鄞州区测试路88号", "street2": "3幢201室", "zip": "315000",
        })
        self.assertEqual(partner.abt_full_address, "浙江省宁波市鄞州区测试路88号3幢201室 315000")
        self.assertFalse(partner.abt_address_original)
        partner.street = "鄞州区新路9号"
        self.assertIn("新路9号", partner.abt_full_address)
        self.assertFalse(partner.abt_address_original)
        partner.street = "海曙区新路9号"
        self.assertEqual(partner.abt_address_district, "海曙区")

    def test_form_onchange_and_delivery_child_use_the_same_service(self):
        with Form(self.env["res.partner"]) as form:
            form.name = "表单地址验证"
            form.abt_full_address = "浙江省宁波市鄞州区测试路88号"
            self.assertEqual(form.city, "宁波市")
            with form.child_ids.new() as child:
                child.type = "delivery"
                child.abt_full_address = "上海市闵行区测试路1号"
                self.assertEqual(child.city, "上海市")
        partner = form.record
        delivery = partner.child_ids.filtered(lambda record: record.type == "delivery")
        self.assertEqual(delivery.street, "闵行区测试路1号")
        self.assertEqual(delivery.abt_address_original, "上海市闵行区测试路1号")
        self.assertEqual(partner.city, "宁波市")
        self.assertEqual(partner.address_get(["delivery"])["delivery"], delivery.id)

    def test_employee_contact_inherits_but_delivery_keeps_its_address(self):
        company = self.env["res.partner"].create({
            "name": "公司地址继承验证", "is_company": True,
            "abt_full_address": "浙江省宁波市鄞州区测试路88号",
        })
        child = self.env["res.partner"].create({"name": "公司联系人", "parent_id": company.id})
        delivery = self.env["res.partner"].create({
            "name": "独立收货地址", "type": "delivery", "parent_id": company.id,
            "abt_full_address": "上海市闵行区测试路1号",
        })
        company.abt_full_address = "广东省深圳市南山区科技路8号"
        self.assertEqual(child.abt_full_address, company.abt_full_address)
        self.assertEqual(child.abt_address_district, "南山区")
        self.assertEqual(delivery.abt_full_address, "上海市闵行区测试路1号")

    def test_foreign_country_is_preserved_for_unrecognized_input(self):
        partner = self.env["res.partner"].create({
            "name": "国外地址验证", "country_id": self.env.ref("base.us").id,
            "abt_full_address": "12 Example Road",
        })
        self.assertEqual(partner.country_id, self.env.ref("base.us"))
        self.assertEqual(partner.street, "12 Example Road")
        self.assertEqual(partner.abt_full_address, "12 Example Road")

    def test_form_retains_original_after_normalizing_the_visible_address(self):
        original = "中国，宁波市 鄞州区 测试路88号"
        with Form(self.env["res.partner"]) as form:
            form.name = "地址原文验证"
            form.abt_full_address = original
        self.assertEqual(form.record.abt_address_original, original)
        self.assertEqual(form.record.city, "宁波市")

    def test_expanded_native_fields_can_be_corrected_without_reparsing(self):
        partner = self.env["res.partner"].create({
            "name": "手工修正地址验证", "abt_full_address": "浙江省宁波市鄞州区测试路88号",
        })
        with Form(partner) as form:
            form.street = "海曙区新路9号"
            form.zip = "315000"
        self.assertEqual(partner.zip, "315000")
        self.assertEqual(partner.street, "海曙区新路9号")
        self.assertEqual(partner.city, "宁波市")
        self.assertEqual(partner.abt_address_district, "海曙区")
