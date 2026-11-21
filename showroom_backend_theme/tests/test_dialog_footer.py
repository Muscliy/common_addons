import ast
import unittest
from pathlib import Path

import sass


class TestDialogFooter(unittest.TestCase):
    def test_dialog_actions_align_right_in_backend_and_frontend(self):
        module_path = Path(__file__).resolve().parents[1]
        asset_path = 'showroom_backend_theme/static/src/scss/showroom_dialog.scss'
        manifest = ast.literal_eval(
            (module_path / '__manifest__.py').read_text(encoding='utf-8'),
        )
        css = sass.compile(filename=str(module_path / 'static/src/scss/showroom_dialog.scss'))

        for bundle in ('web.assets_backend', 'web.assets_frontend'):
            with self.subTest(bundle=bundle):
                self.assertIn(asset_path, manifest['assets'][bundle])

        self.assertRegex(
            css,
            r'\.modal-footer\s*\{[^}]*justify-content:\s*flex-end\s*!important;',
        )
        self.assertRegex(
            css,
            r'\.modal\.o_technical_modal \.modal-footer footer,\s*'
            r'\.modal\.o_technical_modal \.modal-footer \.o_form_buttons_edit,\s*'
            r'\.modal\.o_technical_modal \.modal-footer \.o_form_buttons_view\s*'
            r'\{[^}]*justify-content:\s*flex-end;',
        )
