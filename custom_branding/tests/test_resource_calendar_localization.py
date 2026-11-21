from lxml import etree

from odoo.tests.common import TransactionCase


class TestResourceCalendarLocalization(TransactionCase):
    def test_calendar_fields_have_chinese_labels(self):
        fields_data = self.env["resource.calendar"].fields_get(
            ["flexible_hours", "full_time_required_hours"],
            ["string", "selection"],
        )

        self.assertEqual(fields_data["flexible_hours"]["string"], "弹性工时")
        self.assertEqual(
            fields_data["full_time_required_hours"]["string"],
            "全职标准工时",
        )

    def test_calendar_form_has_chinese_duration_label(self):
        arch = etree.fromstring(
            self.env.ref("resource.resource_calendar_form").get_combined_arch()
        )

        labels = arch.xpath("//span[text()=' 小时/周']")
        self.assertEqual(len(labels), 1)

    def test_only_standard_attendance_names_are_localized(self):
        calendar = self.env["resource.calendar"].create({"name": "测试工作时间表"})
        standard_attendance = self.env["resource.calendar.attendance"].create(
            {
                "name": "Monday Morning",
                "calendar_id": calendar.id,
                "dayofweek": "0",
                "day_period": "morning",
                "hour_from": 8,
                "hour_to": 12,
            }
        )
        custom_attendance = self.env["resource.calendar.attendance"].create(
            {
                "name": "Monday Morning",
                "calendar_id": calendar.id,
                "dayofweek": "1",
                "day_period": "morning",
                "hour_from": 13,
                "hour_to": 17,
            }
        )

        self.env[
            "resource.calendar.attendance"
        ]._localize_standard_attendance_names()

        self.assertEqual(standard_attendance.name, "周一上午")
        self.assertEqual(custom_attendance.name, "Monday Morning")

        self.env[
            "resource.calendar.attendance"
        ]._localize_standard_attendance_names()
        self.assertEqual(standard_attendance.name, "周一上午")
