from odoo import api, models
from odoo.osv import expression


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        result = super().name_search(name, args, operator, limit)
        if name:
            return result

        china = self.env.ref("base.cn")
        china_domain = expression.AND([args or [], [("id", "=", china.id)]])
        if not self.search(china_domain, limit=1):
            return result

        remaining = [item for item in result if item[0] != china.id]
        china_option = (china.id, china.display_name)
        if not limit:
            return [china_option, *remaining]
        return [china_option, *remaining[: limit - 1]]
