import re
import unittest
from pathlib import Path

import sass
from lxml import etree


class TestSidebarTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        module_path = Path(__file__).resolve().parents[1]
        cls.css = sass.compile(string='\n'.join(
            (module_path / 'static/src/webclient' / name).read_text()
            for name in ('showroom_theme.scss', 'sidebar_entries.scss')
        ))
        cls.sidebar_template = etree.parse(str(
            module_path / 'static/src/webclient/showroom_sidebar.xml',
        ))

    def test_dark_shell_compiles_with_readable_navigation_and_preserved_brand(self):
        module_path = Path(__file__).resolve().parents[1]
        css = sass.compile(string=(
            (module_path / 'static/src/scss/dark_variables.scss').read_text()
            + (module_path / 'static/src/webclient/showroom_theme.scss').read_text()
            + (module_path / 'static/src/webclient/sidebar_entries.scss').read_text()
        ))
        for selector in ('.o_main_navbar', '.o_showroom_sidebar'):
            rule = re.search(r'(?m)^' + re.escape(selector) + r'\s*\{([^{}]*)\}', css)
            self.assertIn('background: #212832;', rule[1])
            self.assertIn('color: #dce2ea;', rule[1])
        self.assertIn('--btn-bg: #1677ff;', css)
        self.assertIn('background: #293d48;', css)
        self.assertNotIn('showroom-color(', css)
        self.assertNotIn('showroom-color(', self.css)
        self.assertIn('--ListRenderer-thead-bg-color: #233b5c;', css)

    def test_navigation_uses_white_surfaces_and_dark_text(self):
        navbar = re.search(r'(?m)^\.o_main_navbar\s*\{([^{}]*)\}', self.css)
        sidebar = re.search(r'(?m)^\.o_showroom_sidebar\s*\{([^{}]*)\}', self.css)
        self.assertIsNotNone(navbar)
        self.assertIsNotNone(sidebar)
        for rule in (navbar[1], sidebar[1]):
            self.assertIn('background: #ffffff;', rule)
            self.assertIn('color: #35445c;', rule)
        self.assertIn('--NavBar-entry-color--active: #078da3;', self.css)
        self.assertIn('background: #edf4f6;', self.css)

    def test_submenu_uses_distinct_toggle_and_menu_tree(self):
        template = self.sidebar_template
        self.assertEqual(len(template.xpath("//aside[@t-ref='sidebar']")), 1)
        self.assertEqual(len(template.xpath("//*[@class='o_showroom_app_more']")), 1)
        self.assertEqual(len(template.xpath("//div[contains(@t-att-class, 'o_showroom_app_submenu')]")), 1)
        self.assertEqual(len(template.xpath("//div[contains(@t-att-class, 'o_showroom_app_submenu')][contains(@t-att-style, 'state.menuTop')]")), 1)
        self.assertEqual(len(template.xpath("//t[@t-name='showroom_backend_theme.SidebarMenuNode']")), 1)
        self.assertEqual(len(template.xpath("//details[@t-att-open]/summary")), 1)
        self.assertEqual(len(template.xpath("//div[contains(@t-att-class, 'state.menuReady')]")), 1)
        self.assertIn('.o_showroom_app_submenu {', self.css)

    def test_submenu_waits_for_layout_and_animates_section_content(self):
        self.assertIn('.o_showroom_app_submenu.is-ready {', self.css)
        self.assertIn('visibility: hidden;', self.css)
        hidden_panel = re.search(r'(?m)^  \.o_showroom_sidebar \.o_showroom_app_submenu\s*\{([^{}]*)\}', self.css)
        self.assertNotIn('top 180ms ease', hidden_panel[1])
        self.assertIn('transition: opacity 160ms ease, transform 160ms ease, top 180ms ease;', self.css)
        self.assertIn('.o_showroom_menu_card details::details-content {', self.css)
        self.assertIn('block-size: 0;', self.css)
        self.assertIn('.o_showroom_menu_card details[open]::details-content {', self.css)
        self.assertIn('block-size: auto;', self.css)

    def test_submenu_uses_screen_height_and_second_column(self):
        panel = re.search(r'(?m)^  \.o_showroom_sidebar \.o_showroom_app_submenu\s*\{([^{}]*)\}', self.css)
        grid = re.search(r'(?m)^  \.o_showroom_sidebar \.o_showroom_app_submenu_grid\s*\{([^{}]*)\}', self.css)
        self.assertIsNotNone(panel)
        self.assertIsNotNone(grid)
        self.assertIn('width: 234px;', panel[1])
        self.assertNotIn('overflow-y:', panel[1])
        self.assertIn('max-height: calc(100vh - 64px - 24px);', panel[1])
        self.assertIn('grid-template-columns: minmax(0, 1fr);', grid[1])
        self.assertIn('width: 446px;', self.css)
        self.assertIn('width: 200px;', self.css)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', self.css)

    def test_sidebar_tabs_and_entries_keep_keyboard_and_collapsed_navigation(self):
        self.assertIn('.o_showroom_sidebar_tabs button:focus-visible', self.css)
        self.assertIn('.o_showroom_entry_more:focus-visible', self.css)
        self.assertIn('.o_showroom_sidebar.is-collapsed .o_showroom_sidebar_tabs', self.css)
        self.assertIn('min-height: 36px;', self.css)
        self.assertEqual(len(self.sidebar_template.xpath("//*[@role='tablist']")), 1)
        self.assertEqual(len(self.sidebar_template.xpath("//DropdownItem[contains(@class, 'o_showroom_entry_delete')]")), 1)

    def test_mobile_grid_overrides_collapsed_desktop_columns(self):
        mobile_css = self.css.split('@media (max-width: 767.98px)')[1].split('@media print')[0]
        self.assertIn('.o_web_client:has(> .o_showroom_sidebar.is-collapsed)', mobile_css)
        self.assertIn('grid-template-columns: minmax(0, 1fr);', mobile_css)
