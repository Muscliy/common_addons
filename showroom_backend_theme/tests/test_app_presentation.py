from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAppPresentation(TransactionCase):
    def test_visible_apps_share_names_and_icons_without_writing_source_menus(self):
        for xmlid, expected in (
            ("workflow_core.menu_root", "流程管理"),
            ("ai_agent_core.menu_workspace_root", "知识库"),
        ):
            with self.subTest(xmlid=xmlid):
                menu = self.env.ref(xmlid, raise_if_not_found=False)
                if not menu:
                    action = self.env["ir.actions.act_window"].create({
                        "name": "Presentation fixture", "res_model": "res.partner",
                    })
                    menu = self.env["ir.ui.menu"].create({
                        "name": "Original application", "action": f"ir.actions.act_window,{action.id}",
                    })
                    module, name = xmlid.split(".")
                    self.env["ir.model.data"].create({
                        "module": module, "name": name, "model": "ir.ui.menu", "res_id": menu.id,
                    })
                original = menu.name
                result = self.env["ir.ui.menu"].load_web_menus(False)[menu.id]
                self.assertEqual(result["name"], expected)
                self.assertTrue(result["webIconData"].endswith(".svg"))
                self.assertEqual(result["webIconDataMimetype"], "image/svg+xml")
                self.assertEqual(menu.name, original)
