import base64
from io import BytesIO

from PIL import Image

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import WorkflowCase


@tagged("post_install", "-at_install")
class TestDefinitionPresentation(WorkflowCase):
    def test_icon_upload_resize_clear_and_write_permissions(self):
        template = self.definition()
        image = BytesIO()
        Image.new("RGBA", (512, 512), (68, 166, 174, 255)).save(image, format="PNG")
        template.write({"icon": base64.b64encode(image.getvalue())})
        stored = Image.open(BytesIO(base64.b64decode(template.icon)))
        self.assertEqual(stored.size, (256, 256))
        with self.assertRaises(AccessError):
            template.with_user(self.worker).write({"icon": False})
        template.write({"icon": False})
        self.assertFalse(template.icon)

    def test_templates_group_by_existing_application_and_unlink_clears_category(self):
        menu = self.env["ir.ui.menu"].create({"name": "费用分类测试"})
        template = self.definition()
        template.write({"application_menu_id": menu.id})
        groups = self.env["workflow.definition"]._read_group(
            [("id", "=", template.id)], ["application_menu_id"], ["__count"],
        )
        self.assertEqual(groups, [(menu, 1)])
        menu.unlink()
        template.invalidate_recordset(["application_menu_id"])
        self.assertFalse(template.application_menu_id)
