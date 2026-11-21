from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    abt_full_address = fields.Char(
        string="完整地址", compute="_compute_full_address", inverse="_inverse_full_address",
        help="填写完整地址后自动识别省市；无法识别的部分保留为详细地址。",
    )
    abt_address_original = fields.Char(string="地址输入原文", copy=False)
    abt_address_district = fields.Char(string="区县", compute="_compute_address_hint")
    abt_address_hint = fields.Char(compute="_compute_address_hint")

    @api.depends("street", "street2", "city", "state_id", "country_id", "zip")
    def _compute_full_address(self):
        for partner in self:
            partner.abt_full_address = partner._format_native_address() or False

    def _format_native_address(self):
        self.ensure_one()
        if not any((self.street, self.street2, self.city, self.state_id, self.zip)):
            return ""
        if self.country_id and self.country_id.code != "CN":
            return " ".join(filter(None, [self.street, self.street2, self.city, self.state_id.name, self.zip]))
        province = self.state_id.with_context(lang=False).name or ""
        city = self.city or ""
        parts = [province, city if city != province else "", self.street or "", self.street2 or ""]
        return "".join(parts) + (f" {self.zip}" if self.zip else "")

    def _inverse_full_address(self):
        parser = self.env["abt.address.parser"]
        for partner in self:
            # Native-field corrections also recompute this field; do not parse them again.
            if (partner.abt_full_address or "") != partner._format_native_address():
                partner.update(parser.partner_values(partner.abt_full_address))

    @api.onchange("abt_full_address")
    def _onchange_full_address(self):
        self._inverse_full_address()

    @api.depends("abt_full_address", "country_id")
    def _compute_address_hint(self):
        parser = self.env["abt.address.parser"]
        for partner in self:
            if not partner.abt_full_address:
                partner.abt_address_hint = False
                partner.abt_address_district = False
                continue
            result = parser.parse(partner.abt_full_address)
            partner.abt_address_district = result["district"] or False
            if result["status"] == "recognized":
                parts = list(dict.fromkeys(filter(None, [result["province"], result["city"], result["district"]])))
                partner.abt_address_hint = self.env._("已识别：%s", " / ".join(parts))
            else:
                partner.abt_address_hint = self.env._("地址已保留，省市未完整识别，可展开核对。")
