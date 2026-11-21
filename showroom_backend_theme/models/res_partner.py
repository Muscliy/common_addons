from markupsafe import Markup

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _apply_tyj_branding(self):
        """Apply white-label values to existing databases during module upgrades."""
        assistant = self.env.ref("base.partner_root", raise_if_not_found=False)
        if not assistant:
            return

        assistant.sudo().write({
            "name": "TYJ 助手",
            "email": "assistant@tyj.local",
        })

        root_user = self.env.ref("base.user_root", raise_if_not_found=False)
        if root_user:
            root_user.sudo().write({
                "email": "assistant@tyj.local",
                "signature": Markup("<div>TYJ 助手</div>"),
            })

        replacements = (
            ("OdooBot", "TYJ 助手"),
            ("Odoobot", "TYJ 助手"),
            ("Odoo Bot", "TYJ 助手"),
            ("Odoo's", "TYJ's"),
            ("Odoo 的", "TYJ 平台的"),
            ("Odoo", "TYJ"),
        )
        messages = self.env["mail.message"].sudo().search([
            ("author_id", "=", assistant.id),
            "|",
            ("body", "ilike", "odoo"),
            ("subject", "ilike", "odoo"),
        ])
        for message in messages:
            values = {}
            for field_name in ("body", "subject"):
                value = message[field_name]
                if not value:
                    continue
                branded_value = str(value)
                for source, target in replacements:
                    branded_value = branded_value.replace(source, target)
                if branded_value != str(value):
                    values[field_name] = branded_value
            if values:
                message.write(values)

        # Clean official, XML-defined email templates without touching templates
        # created by customers or administrators. SQL avoids mail.template's
        # rendering check while the registry is still loading other modules.
        template_data = self.env["ir.model.data"].sudo().search([
            ("model", "=", "mail.template"),
        ])
        templates = self.env["mail.template"].sudo().browse(template_data.mapped("res_id")).exists()
        if templates:
            self.env.cr.execute("""
                UPDATE mail_template
                   SET name = replace(replace(replace(name::text, 'OdooBot', 'TYJ 助手'), 'Odoobot', 'TYJ 助手'), 'Odoo', 'TYJ')::jsonb,
                       subject = replace(replace(replace(subject::text, 'OdooBot', 'TYJ 助手'), 'Odoobot', 'TYJ 助手'), 'Odoo', 'TYJ')::jsonb,
                       body_html = replace(
                           replace(
                               replace(
                                   replace(
                                       replace(
                                           replace(body_html::text, 'https://www.odoo.com', '#'),
                                           'http://www.odoo.com', '#'
                                       ),
                                       'http://yourcompany.odoo.com', 'https://erp.example.com'
                                   ),
                                   'OdooBot', 'TYJ 助手'
                               ),
                               'Odoobot', 'TYJ 助手'
                           ),
                           'Odoo', 'TYJ'
                       )::jsonb
                 WHERE id = ANY(%s)
                   AND concat(name::text, subject::text, body_html::text) ILIKE '%%odoo%%'
            """, [templates.ids])
            templates.invalidate_recordset(["name", "subject", "body_html"])
