{
    "name": "泰缘极主题",
    "version": '19.0.1.6.1',
    "category": "Themes/Backend",
    "summary": "泰缘极后台主题",
    "author": "leehudev",
    "license": "LGPL-3",
    "depends": ["web", "mail"],
    "data": [
        "data/branding_data.xml",
        "views/branding_templates.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "showroom_backend_theme/static/src/scss/primary_variables.scss",
            ),
        ],
        "web._assets_bootstrap": [
            (
                "before",
                "web/static/src/scss/import_bootstrap.scss",
                "showroom_backend_theme/static/src/scss/theme_colors.scss",
            ),
        ],
        "web._assets_bootstrap_backend": [
            (
                "after",
                "web/static/src/scss/bootstrap_review_backend.scss",
                "showroom_backend_theme/static/src/scss/theme_colors_backend.scss",
            ),
        ],
        "web.assets_backend": [
            "showroom_backend_theme/static/src/webclient/theme_switcher.js",
            "showroom_backend_theme/static/src/webclient/theme_switcher.xml",
            "showroom_backend_theme/static/src/webclient/sidebar_entries.js",
            "showroom_backend_theme/static/src/webclient/sidebar_bookmark_menu.js",
            "showroom_backend_theme/static/src/webclient/sidebar_bookmark_menu.xml",
            "showroom_backend_theme/static/src/webclient/showroom_sidebar.js",
            "showroom_backend_theme/static/src/webclient/showroom_sidebar.xml",
            "showroom_backend_theme/static/src/webclient/showroom_navbar.js",
            "showroom_backend_theme/static/src/webclient/showroom_navbar.xml",
            "showroom_backend_theme/static/src/webclient/showroom_white_label.js",
            "showroom_backend_theme/static/src/webclient/showroom_white_label.xml",
            "showroom_backend_theme/static/src/webclient/showroom_brand_guard.js",
            "showroom_backend_theme/static/src/scss/showroom_branding.scss",
            "showroom_backend_theme/static/src/webclient/showroom_theme.scss",
            "showroom_backend_theme/static/src/webclient/sidebar_entries.scss",
            "showroom_backend_theme/static/src/scss/showroom_dialog.scss",
        ],
        "web.assets_frontend": [
            "showroom_backend_theme/static/src/scss/showroom_branding.scss",
            "showroom_backend_theme/static/src/scss/showroom_dialog.scss",
            "showroom_backend_theme/static/src/webclient/showroom_brand_guard.js",
        ],
        "web.assets_unit_tests": [
            "showroom_backend_theme/static/tests/theme_switcher.test.js",
            "showroom_backend_theme/static/tests/sidebar_entries.test.js",
            "showroom_backend_theme/static/tests/showroom_sidebar.test.js",
        ],
        "web.assets_web_dark": [
            ("prepend", "showroom_backend_theme/static/src/scss/dark_variables.scss"),
            "showroom_backend_theme/static/src/scss/dark.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
