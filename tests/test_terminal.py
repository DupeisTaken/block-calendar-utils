import unittest
from dataclasses import replace
from datetime import date

from bcutils.app import DEFAULT_ROOT
from bcutils.models import Course
from bcutils.schedule import build_preview, preview_text
from bcutils.storage import load_semester
from bcutils.terminal import display_width, wrap_line


class TerminalTests(unittest.TestCase):
    def setUp(self):
        semester = load_semester(DEFAULT_ROOT / "semesters/2026-27-s1")
        courses = [Course(b, "Example " + b, enabled=True, timing_option="study_hall" if b == "T" else "") for b in semester.blocks]
        self.preview = build_preview(semester, courses, "472b895a-d1ac-4e5b-8203-02e2aa01d607", date(2026, 9, 14), date(2026, 9, 25))

    def test_days_share_lines_and_week_boundaries_are_preserved(self):
        text = preview_text(self.preview, width=100)
        self.assertTrue(any("Monday, 14" in line and "Tuesday, 15" in line for line in text.splitlines()))
        self.assertTrue(any("Monday, 21" in line and "Tuesday, 22" in line for line in text.splitlines()))
        self.assertFalse(any("Friday, 18" in line and "Monday, 21" in line for line in text.splitlines()))
        self.assertTrue(all(display_width(line) <= 100 for line in text.splitlines()))

    def test_narrow_and_unicode_previews_wrap_without_losing_text(self):
        self.preview.events = [replace(self.preview.events[0], title="非常长的课程名称" * 10, location="实验室")]
        for width in (20, 40, 80, 120, 300):
            text = preview_text(self.preview, width=width)
            self.assertTrue(all(display_width(line) <= width for line in text.splitlines()))
            self.assertIn("非常长的课程名称" * 10, "".join(text.split()))
        self.assertEqual("".join(wrap_line("e\u0301" * 50, 20)), "e\u0301" * 50)

    def test_list_and_empty_previews(self):
        text = preview_text(self.preview)
        self.assertIn("Monday, 14 September 2026\n", text)
        self.preview.events = []
        self.assertIn("No events", preview_text(self.preview, width=80))
