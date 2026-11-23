from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def color_scheme(self):
        # Only the two supported bundles can be selected by the browser cookie.
        scheme = request.httprequest.cookies.get('color_scheme')
        if scheme in ('light', 'dark'):
            return scheme
        return super().color_scheme()
