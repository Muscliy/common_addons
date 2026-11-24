from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from .common import WorkflowCase, sequential


@tagged("post_install", "-at_install")
class TestDefinitionManagement(WorkflowCase):
    def ordinary_manager(self, login="designated_internal"):
        return new_test_user(
            self.env(context={**self.env.context, "no_reset_password": True}),
            login=login, groups="base.group_user",
        )

    def test_designation_grants_only_own_workflow_maintenance(self):
        user = self.ordinary_manager()
        template = self.definition()
        other = self.definition()
        template.manager_id = user
        self.assertTrue(user.has_group("workflow_core.group_user"))
        self.assertFalse(user.has_group("workflow_core.group_designer"))
        self.assertFalse(user.has_group("workflow_core.group_publisher"))
        owned = template.with_user(user)
        owned.write({"description": "指定管理员维护"})
        owned.version_ids.save_graph(sequential(), 0)
        self.assertTrue(owned.version_ids.get_canvas()["can_edit"])
        self.assertFalse(owned.version_ids.get_canvas()["can_publish"])
        owned.version_ids.get_assignees()
        with self.assertRaises(AccessError):
            other.with_user(user).write({"manager_id": user.id})
        with self.assertRaises(AccessError):
            other.version_ids.with_user(user).save_graph(sequential(), 0)
        with self.assertRaises(AccessError):
            other.version_ids.with_user(user).get_assignees()
        with self.assertRaises(AccessError):
            owned.version_ids.action_publish(1)
        with self.assertRaises(AccessError):
            owned.create({"name": "不能新建"})
        with self.assertRaises(AccessError):
            owned.unlink()
        owned.version_ids.with_user(self.publisher).action_publish(1)
        self.assertTrue(owned.action_new_version()["params"]["version_id"])

    def test_transfer_revokes_previous_admin_and_global_designers_cannot_bypass(self):
        previous = self.ordinary_manager()
        replacement = self.ordinary_manager("replacement_internal")
        template = self.definition()
        template.manager_id = previous
        with self.assertRaises(AccessError):
            template.version_ids.with_user(self.designer).save_graph(sequential(), 0)
        template.with_user(previous).manager_id = replacement
        with self.assertRaises(AccessError):
            template.with_user(previous).write({"name": "失效管理员"})
        with self.assertRaises(AccessError):
            template.version_ids.with_user(previous).save_graph(sequential(), 0)
        template.version_ids.with_user(replacement).save_graph(sequential(), 0)
        self.assertFalse(template.version_ids.with_user(previous).get_canvas()["can_edit"])

    def test_manager_rejects_portal_inactive_and_foreign_company_users(self):
        template = self.definition()
        portal = new_test_user(self.env, login="not_internal", groups="base.group_portal")
        inactive = self.ordinary_manager()
        inactive.active = False
        company = self.env["res.company"].create({"name": "Separate admin company"})
        foreign = new_test_user(self.env, login="foreign_admin", groups="base.group_user",
                                company_id=company.id, company_ids=[(6, 0, [company.id])])
        for user in (portal, inactive, foreign):
            with self.subTest(user=user.login), self.assertRaises(ValidationError):
                template.manager_id = user

    def test_category_belongs_to_module_and_module_switch_clears_selection(self):
        module, another = self.env["ir.ui.menu"].create([
            {"name": "费用模块测试"}, {"name": "财务模块测试"},
        ])
        category = self.env["workflow.category"].with_user(self.designer).create({
            "name": "报销", "application_menu_id": module.id,
        })
        template = self.definition()
        template.write({"application_menu_id": module.id, "category_id": category.id})
        with self.assertRaises(ValidationError):
            template.application_menu_id = another
        with self.assertRaises(ValidationError):
            category.application_menu_id = another
        draft = self.env["workflow.definition"].new({
            "application_menu_id": another.id, "category_id": category.id,
        })
        draft._onchange_application()
        self.assertFalse(draft.category_id)
