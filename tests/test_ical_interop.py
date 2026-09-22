"""Optional independent parser tests; `icalendar` is a dev-only dependency."""

import importlib.util
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone

from tests.fixtures import example_semester
from bcutils.app import DEFAULT_ROOT
from bcutils.ical import calendar_bytes
from bcutils.models import Course, DayOverride
from bcutils.schedule import build_preview
from bcutils.storage import load_semester


@unittest.skipUnless(importlib.util.find_spec("icalendar"), "Install requirements-dev.txt for independent parser tests")
class InteropTests(unittest.TestCase):
    def test_roundtrip_unicode_escaping_dates_and_exceptions(self):
        from icalendar import Calendar
        semester = example_semester()
        title = '高级数学, seminar; "A" \\ section\n' * 12
        courses = [Course(b, title if b == "A" else "Study " + b, "Room, 12; east", "Example Teacher", True, "toefl" if b == "T" else "") for b in semester.blocks]
        preview = build_preview(semester, courses, "472b895a-d1ac-4e5b-8203-02e2aa01d607", date(2026, 9, 14), date(2026, 10, 4), 20,
                                personal=[DayOverride(date(2026, 9, 18), "use", "monday"), DayOverride(date(2026, 9, 21), "off")])
        data = calendar_bytes(preview.events)
        parsed = Calendar.from_ical(data)
        events = parsed.walk("VEVENT")
        self.assertEqual(len(events), 74)
        self.assertEqual(len({str(e["UID"]) for e in events}), 74)
        for actual, expected in zip(events, preview.events):
            self.assertEqual(str(actual["SUMMARY"]), expected.title)
            self.assertEqual(str(actual["LOCATION"]), expected.location)
            self.assertNotIn("DESCRIPTION", actual)
            self.assertEqual(actual.decoded("DTSTART"), expected.start.astimezone(timezone.utc))
            self.assertEqual(actual.decoded("DTEND"), expected.end.astimezone(timezone.utc))
            self.assertEqual(actual.errors, [])

    def test_empty_valid_calendar(self):
        from icalendar import Calendar
        parsed = Calendar.from_ical(calendar_bytes([]))
        self.assertEqual(str(parsed["VERSION"]), "2.0")
        self.assertEqual(parsed.walk("VEVENT"), [])
