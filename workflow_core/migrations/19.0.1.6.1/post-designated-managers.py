from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["workflow.definition"].with_context(active_test=False).search([])._ensure_manager_access()
