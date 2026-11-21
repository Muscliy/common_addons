from odoo import api, models


def _set_china_default(recordset, values, fields_list, field_name):
    context_key = f"default_{field_name}"
    if (
        field_name in fields_list
        and not values.get(field_name)
        and context_key not in recordset.env.context
    ):
        values[field_name] = recordset.env.ref("base.cn").id
    return values


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "lang" in fields_list and "default_lang" not in self.env.context:
            values["lang"] = "zh_CN"
        return _set_china_default(self, values, fields_list, "country_id")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        return _set_china_default(
            self,
            values,
            fields_list,
            "private_country_id",
        )


class ResBank(models.Model):
    _inherit = "res.bank"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        return _set_china_default(self, values, fields_list, "country")
