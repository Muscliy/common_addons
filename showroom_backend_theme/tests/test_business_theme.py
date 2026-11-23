"""Compile the custom business UI against both real Odoo theme stacks."""
import ast
import importlib.util
import unittest
from pathlib import Path


class TestBusinessTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = Path(__file__).resolve().parents[1]
        cls.root = cls.module.parents[1]
        spec = importlib.util.spec_from_file_location(
            'business_theme_compiler', cls.module / 'tests/test_theme_colors.py',
        )
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        compiler = helper.TestThemeColors
        compiler.module_path = cls.module
        compiler.root = cls.root
        compiler.web_assets = ast.literal_eval(
            (cls.root / 'addons/web/__manifest__.py').read_text(),
        )['assets']
        compiler.theme_assets = ast.literal_eval(
            (cls.module / '__manifest__.py').read_text(),
        )['assets']
        paths = []
        for asset in compiler.web_assets['web.assets_backend']:
            if isinstance(asset, tuple) and asset[0] == 'include':
                paths.extend(compiler.bundle_files(asset[1]))
                if asset[1] == 'web._assets_bootstrap_backend':
                    break
            elif isinstance(asset, str) and asset.endswith('.scss'):
                paths.append(asset)
        cls.business_paths = []
        for directory in ('custom_addons', 'common_addons'):
            for path in sorted((cls.root / directory).glob('*/static/src/**/*.scss')):
                if path.parts[-1].endswith('variables.scss') or 'showroom_backend_theme' in path.parts:
                    continue
                cls.business_paths.append(str(path.relative_to(cls.root / directory)))
        cls.light = compiler.compile_paths(paths + cls.business_paths)
        cls.dark = compiler.compile_paths(
            paths + cls.business_paths + ['showroom_backend_theme/static/src/scss/dark.scss'],
            (cls.module / 'static/src/scss/dark_variables.scss').read_text(),
        )

    def test_all_business_styles_compile_in_both_schemes(self):
        self.assertGreater(len(self.business_paths), 20)
        for css in (self.light, self.dark):
            self.assertIn('.o_indicator_cockpit', css)
            self.assertIn('.o_employee_indicator_dashboard', css)
            self.assertIn('.o_hr_workbench', css)
            self.assertNotIn('showroom-color(', css)

    def test_custom_card_surfaces_have_dark_tokens_and_light_fallbacks(self):
        for name in (
            'custom_hr_indicator/static/src/cockpit/cockpit_dashboard.scss',
            'custom_hr_indicator/static/src/department_indicator/employee_indicator_dashboard.scss',
            'custom_hr_talent/static/src/talent_dashboard/talent_dashboard.scss',
            'yabo_strategy/static/src/strategy_cockpit/strategy_cockpit.scss',
            'ai_assistant/static/src/chat.scss',
        ):
            with self.subTest(stylesheet=name):
                source = (self.root / 'custom_addons' / name).read_text()
                self.assertIn('var(--o-theme-surface, #fff)', source)
                self.assertNotRegex(source, r'background:\s*#fff\s*;')
        self.assertIn('--o-theme-surface: #212832;', self.dark)
        self.assertNotIn('--o-theme-surface:', self.light)

    def test_semantic_colors_keep_distinct_surfaces_and_readable_text(self):
        for token in ('success', 'warning', 'danger', 'purple', 'pink'):
            self.assertIn(f'--o-theme-{token}-bg:', self.dark)
            self.assertIn(f'--o-theme-{token}-text:', self.dark)
