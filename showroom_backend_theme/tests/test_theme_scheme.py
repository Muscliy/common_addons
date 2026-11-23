from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.showroom_backend_theme.models import ir_http


class TestThemeScheme(TransactionCase):
    def test_browser_preference_selects_only_supported_bundles(self):
        for preference, expected in (
            ('light', 'light'), ('dark', 'dark'), (None, 'light'),
            ('invalid', 'light'), ('../../assets', 'light'),
        ):
            with self.subTest(preference=preference):
                request = SimpleNamespace(
                    httprequest=SimpleNamespace(cookies={'color_scheme': preference}),
                )
                with patch.object(ir_http, 'request', request):
                    self.assertEqual(self.env['ir.http'].color_scheme(), expected)
