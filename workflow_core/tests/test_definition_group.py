from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import WorkflowCase


@tagged("post_install", "-at_install")
class TestDefinitionGroup(WorkflowCase):
    def test_configured_groups_are_independent_of_dynamic_application_menus(self):
        first, second = self.env["ir.ui.menu"].create([
            {"name": "动态应用甲"}, {"name": "动态应用乙"},
        ])
        group = self.env["workflow.group"].with_user(self.designer).create({"name": "自定义跨模块分组"})
        template = self.definition()
        template.write({"group_id": group.id, "application_menu_id": first.id})
        template.application_menu_id = second
        self.assertEqual(template.group_id, group)
        result = self.env["workflow.definition"]._read_group(
            [("id", "=", template.id)], ["group_id"], ["__count"],
        )
        self.assertEqual(result, [(group, 1)])
        self.assertEqual(self.env.ref("workflow_core.menu_groups").parent_id,
                         self.env.ref("workflow_core.menu_configuration"))

    def test_group_configuration_and_template_maintenance_keep_existing_permissions(self):
        group = self.env["workflow.group"].with_user(self.designer).create({"name": "审批组"})
        self.assertEqual(group.with_user(self.worker).name, "审批组")
        with self.assertRaises(AccessError):
            group.with_user(self.worker).write({"name": "越权修改"})
        with self.assertRaises(AccessError):
            self.env["workflow.group"].with_user(self.worker).create({"name": "越权新增"})
        template = self.definition()
        template.with_user(self.designer).group_id = group
        with self.assertRaises(AccessError):
            template.with_user(self.worker).group_id = False
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            group.unlink()
        group.active = False
        self.assertEqual(template.group_id, group)
