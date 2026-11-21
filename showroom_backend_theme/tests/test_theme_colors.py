import ast
import re
from pathlib import Path

import sass

from odoo.tests.common import TransactionCase, tagged


@tagged('standard', 'post_install')
class TestThemeColors(TransactionCase):
    """Compile the actual Odoo Bootstrap stack without a database."""

    test_module = 'showroom_backend_theme'
    test_class = 'TestThemeColors'
    test_sequence = 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module_path = Path(__file__).resolve().parents[1]
        cls.root = cls.module_path.parents[1]
        cls.web_assets = ast.literal_eval(
            (cls.root / 'addons/web/__manifest__.py').read_text(encoding='utf-8'),
        )['assets']
        cls.theme_assets = ast.literal_eval(
            (cls.module_path / '__manifest__.py').read_text(encoding='utf-8'),
        )['assets']
        cls.styles = {context: cls.compile_theme(context) for context in ('backend', 'frontend')}

    @classmethod
    def bundle_files(cls, bundle: str) -> list[str]:
        assets = list(cls.web_assets[bundle])
        if bundle == 'web._assets_primary_variables':
            # html_editor is an auto-installed dependency of this deployment.
            # OCB 19's frontend Bootstrap review calls increase-contrast(),
            # which html_editor defines in this primary-variable asset.
            assets.insert(
                assets.index('web/static/src/scss/primary_variables.scss') + 1,
                'html_editor/static/src/scss/html_editor.variables.scss',
            )
        for directive, target, path in cls.theme_assets.get(bundle, []):
            index = assets.index(target) + (directive == 'after')
            assets.insert(index, path)
        paths = []
        for asset in assets:
            if isinstance(asset, tuple):
                if asset[0] == 'include':
                    paths.extend(cls.bundle_files(asset[1]))
                elif asset[0] == 'after':
                    paths.insert(paths.index(asset[1]) + 1, asset[2])
                elif asset[0] == 'remove' and asset[1] in paths:
                    paths.remove(asset[1])
            elif asset.endswith('.scss'):
                base = 'common_addons' if asset.startswith('showroom_backend_theme/') else 'addons'
                paths.extend(str(path.relative_to(cls.root / base)) for path in sorted(
                    (cls.root / base).glob(asset),
                ))
        return list(dict.fromkeys(paths))

    @classmethod
    def compile_theme(cls, context: str, overrides: str = '') -> str:
        paths = []
        for asset in cls.web_assets[f'web.assets_{context}']:
            if isinstance(asset, tuple) and asset[0] == 'include':
                paths.extend(cls.bundle_files(asset[1]))
                if asset[1] == f'web._assets_bootstrap_{context}':
                    break
            elif isinstance(asset, str) and asset.endswith('.scss'):
                paths.append(asset)
        return cls.compile_paths(paths, overrides)

    @classmethod
    def compile_paths(cls, paths: list[str], overrides: str = '') -> str:
        imports = '\n'.join(f'@import "{path}";' for path in paths)
        return sass.compile(
            string=overrides + imports,
            include_paths=[
                str(cls.root / 'addons/web/static/lib/bootstrap/scss'),
                str(cls.root / 'addons'),
                str(cls.root / 'custom_addons'),
                str(cls.root / 'common_addons'),
            ],
            precision=8,
        )

    def rule(self, css: str, selector: str) -> str:
        matches = list(re.finditer(
            rf'(?<![\w-]){re.escape(selector)}(?=\s*[,{{])[^{{}}]*\{{([^{{}}]*)\}}', css,
        ))
        self.assertTrue(matches, f'Missing CSS rule: {selector}')
        return matches[-1][1]

    def test_exceed_color_and_readable_badges(self):
        for context, css in self.styles.items():
            with self.subTest(context=context):
                prefix = '' if context == 'backend' else 'bs-'
                self.assertIn(f'--{prefix}exceed: #5F4B8B;', css)
                self.assertIn(f'--{prefix}exceed-rgb: 95, 75, 139;', css)
                badge = self.rule(css, '.text-bg-exceed')
                self.assertRegex(badge, r'(?i)color: #(?:fff|ffffff) !important;')
                self.assertIn(f'var(--{prefix}exceed-rgb)', badge)
                text = self.rule(css, '.text-exceed')
                self.assertIn('RGBA(95, 75, 139' if context == 'backend' else '#5F4B8B', text)
                self.assertIn(f'--{prefix}exceed-bg-subtle: #dfdbe8;', css)

    def test_all_semantic_variants_are_generated(self):
        classes = (
            'text-exceed', 'bg-exceed', 'border-exceed', 'link-exceed',
            'link-underline-exceed', 'focus-ring-exceed', 'text-bg-exceed',
            'text-exceed-emphasis', 'bg-exceed-subtle', 'border-exceed-subtle',
            'btn-exceed', 'btn-fill-exceed', 'btn-outline-exceed', 'alert-exceed',
            'list-group-item-exceed', 'table-exceed',
        )
        for context, css in self.styles.items():
            with self.subTest(context=context):
                for name in classes:
                    self.rule(css, f'.{name}')
                prefix = '' if context == 'backend' else 'bs-'
                for suffix in ('text-emphasis', 'bg-subtle', 'border-subtle'):
                    self.assertRegex(css, rf'--{prefix}exceed-{suffix}: #[0-9a-fA-F]{{6}};')
                self.assertIn(
                    f'var(--{prefix}exceed-bg-subtle)', self.rule(css, '.alert-exceed'),
                )
                button = self.rule(css, '.btn-exceed')
                self.assertIn(f'--{prefix}btn-bg: #5F4B8B;', button)
                for state in ('hover', 'active', 'disabled'):
                    self.assertIn(f'--{prefix}btn-{state}-bg:', button)

    def test_standard_statuses_remain_available(self):
        for context, css in self.styles.items():
            with self.subTest(context=context):
                for status in ('success', 'warning', 'danger', 'info'):
                    for variant in ('text', 'bg', 'border', 'btn', 'alert', 'table'):
                        self.rule(css, f'.{variant}-{status}')
                success = '#28a745' if context == 'backend' else '#198754'
                prefix = '' if context == 'backend' else 'bs-'
                self.assertIn(f'--{prefix}success: {success};', css)

    def test_color_can_be_overridden_before_primary_variables(self):
        css = self.compile_theme('backend', '$o-exceed: #123456;')
        self.assertIn('--exceed: #123456;', css)
        self.assertIn('--exceed-rgb: 18, 52, 86;', css)
        self.assertIn('RGBA(18, 52, 86', self.rule(css, '.text-exceed'))

    def test_bootstrap_dark_mode_has_complete_semantic_variables(self):
        css = self.compile_theme('frontend', '$enable-dark-mode: true;')
        dark = self.rule(css, '[data-bs-theme="dark"]')
        for suffix in ('text-emphasis', 'bg-subtle', 'border-subtle'):
            self.assertRegex(dark, rf'--bs-exceed-{suffix}: #[0-9a-fA-F]{{6}};')

    def test_report_assets_compile_with_pdf_compatible_colors(self):
        css = self.compile_paths(self.bundle_files('web.report_assets_common'))
        self.assertIn('--exceed: #5F4B8B;', css)
        self.assertIn('RGB(95, 75, 139)', self.rule(css, '.bg-exceed'))
        self.assertIn('#5F4B8B', self.rule(css, '.text-exceed'))
