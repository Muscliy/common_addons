from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug: bool) -> dict:
        menus = super().load_web_menus(debug)
        presentation = {
            "workflow_core.menu_root": (
                self.env._("流程管理"),
                "workflow_core,static/description/icon.svg",
            ),
            "ai_agent_core.menu_workspace_root": (
                self.env._("知识库"),
                "showroom_backend_theme,static/description/knowledge.svg",
            ),
        }
        for menu in menus.values():
            branding = presentation.get(menu.get("xmlid"))
            if branding:
                name, icon = branding
                module, path = icon.split(",")
                menu.update(
                    name=name, webIcon=icon, webIconData=f"/{module}/{path}",
                    webIconDataMimetype="image/svg+xml",
                )
        return menus
