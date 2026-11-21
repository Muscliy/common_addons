from odoo import api, fields, models


STANDARD_ATTENDANCE_NAMES = {
    ("Monday Morning", "0", "morning"): "周一上午",
    ("Monday Lunch", "0", "lunch"): "周一午休",
    ("Monday Afternoon", "0", "afternoon"): "周一下午",
    ("Tuesday Morning", "1", "morning"): "周二上午",
    ("Tuesday Lunch", "1", "lunch"): "周二午休",
    ("Tuesday Afternoon", "1", "afternoon"): "周二下午",
    ("Wednesday Morning", "2", "morning"): "周三上午",
    ("Wednesday Lunch", "2", "lunch"): "周三午休",
    ("Wednesday Afternoon", "2", "afternoon"): "周三下午",
    ("Thursday Morning", "3", "morning"): "周四上午",
    ("Thursday Lunch", "3", "lunch"): "周四午休",
    ("Thursday Afternoon", "3", "afternoon"): "周四下午",
    ("Friday Morning", "4", "morning"): "周五上午",
    ("Friday Lunch", "4", "lunch"): "周五午休",
    ("Friday Afternoon", "4", "afternoon"): "周五下午",
}

STANDARD_SECTION_NAMES = {
    "First week": "第一周",
    "Second week": "第二周",
}


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    flexible_hours = fields.Boolean(string="弹性工时")
    full_time_required_hours = fields.Float(string="全职标准工时")


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    @api.model
    def _localize_standard_attendance_names(self):
        english_names = [name for name, _day, _period in STANDARD_ATTENDANCE_NAMES]
        english_names.extend(STANDARD_SECTION_NAMES)
        attendances = self.search([("name", "in", english_names)])

        for attendance in attendances:
            if attendance.display_type == "line_section":
                localized_name = STANDARD_SECTION_NAMES.get(attendance.name)
            else:
                key = (
                    attendance.name,
                    attendance.dayofweek,
                    attendance.day_period,
                )
                localized_name = STANDARD_ATTENDANCE_NAMES.get(key)
            if localized_name:
                attendance.name = localized_name
