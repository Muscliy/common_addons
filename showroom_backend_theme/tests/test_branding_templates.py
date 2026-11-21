"""Static checks for OCB-compatible branding view declarations."""

from pathlib import Path
import unittest
from xml.etree import ElementTree


class BrandingTemplateDeclarationTests(unittest.TestCase):
    def test_view_updates_without_architecture_reference_defined_template(self):
        xml_path = (
            Path(__file__).resolve().parents[1]
            / "views"
            / "branding_templates.xml"
        )
        root = ElementTree.parse(xml_path).getroot()
        template_ids = {template.get("id") for template in root.findall("template")}

        for record in root.findall("record[@model='ir.ui.view']"):
            if record.find("field[@name='arch']") is None:
                self.assertIn(record.get("id"), template_ids)
