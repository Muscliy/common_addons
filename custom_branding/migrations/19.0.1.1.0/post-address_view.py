from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Attach the China address form to base.cn on existing installations.

    The country data record is flagged noupdate, so the declarative
    data/country_address_view.xml only applies on fresh installs.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    china = env.ref('base.cn', raise_if_not_found=False)
    address_view = env.ref(
        'custom_branding.view_partner_address_form_cn_global',
        raise_if_not_found=False,
    )
    if china and address_view and china.address_view_id != address_view:
        china.address_view_id = address_view
