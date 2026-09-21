"""Activity timings independently transcribed from Timetable Setup B23:C26."""

import tempfile
import shutil
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from bcutils.app import DEFAULT_ROOT, Workspace
from bcutils.models import Activity, CalendarError, DayOverride
from bcutils.schedule import build_preview
from bcutils.storage import digest, load_semester
from bcutils.semesters import create_semester


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", self.root / "semesters")
        self.workspace = Workspace(self.root)
        self.ctx = self.workspace.use_semester("2026-27-s1")
        self.settings = dict(mode="week", anchor="2026-09-14", schedule_mode="weekdays")

    def tearDown(self):
        self.temp.cleanup()

    def select_clubs(self):
        self.ctx.save_activities([Activity("club-tue", "Chess", True, "Library"), Activity("club-wed", "Robotics", True)], digest(self.ctx.activities_path))

    def test_optional_activities_times_titles_late_and_off_defaults(self):
        self.select_clubs()
        self.assertEqual([e.title for e in self.ctx.preview(self.settings).events], ["Chess", "Robotics"])
        result = self.ctx.preview(self.settings | dict(cas=True, clubs=True))
        self.assertEqual([(e.title, e.start.strftime("%a %H:%M"), e.end.strftime("%H:%M")) for e in result.events],
                         [("CAS", "Mon 15:05", "16:05"), ("Chess", "Tue 15:45", "16:35"), ("Robotics", "Wed 15:50", "16:40")])
        late = self.ctx.preview(self.settings | dict(cas=True, clubs=True, late=True))
        self.assertEqual([e.start.strftime("%H:%M") for e in late.events], ["15:25", "16:05", "16:10"])
        self.assertEqual([e.uid for e in late.events], [e.uid for e in result.events])
        self.assertTrue(all(not e.description for e in result.events))
        self.assertEqual(result.events[1].location, "Library")

    def test_makeup_days_move_activity_slots_and_respect_closures(self):
        self.select_clubs()
        self.ctx.save_exceptions([DayOverride(date(2026, 9, 18), "use", "tuesday"), DayOverride(date(2026, 9, 14), "off")], digest(self.ctx.exceptions_path))
        result = self.ctx.preview(self.settings | dict(cas=True, clubs=True, schedule_mode="exceptions"))
        self.assertEqual([e.title for e in result.events], ["Chess", "Robotics", "Chess"])
        self.assertEqual(result.events[-1].start.strftime("%a %H:%M"), "Fri 15:45")

    def test_activity_validation_conflicts_and_copy(self):
        with self.assertRaisesRegex(CalendarError, "--activities --set"):
            self.ctx.preview(self.settings | dict(clubs=True, require_clubs=True))
        for item in [Activity("cas", "Wrong", True), Activity("club-tue", "", True), Activity("unknown", "Name", True)]:
            with self.assertRaises(CalendarError):
                self.ctx.save_activities([item], digest(self.ctx.activities_path))
        self.select_clubs()
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            self.ctx.save_activities([], "stale")
        folder = create_semester(self.workspace, "next", copy_from="2026-27-s1")
        self.assertEqual(len(load_semester(folder).activity_sessions), 3)
        self.assertFalse((self.workspace.local / "profiles/me/next/activities.csv").exists())

    def test_invalid_activity_definition_is_rejected(self):
        path = self.ctx.folder / "activities.csv"
        source = path.read_text()
        for changed in [source.replace("club-tue,club", "cas,club"), source.replace("mon-cas", "mon-b"), source.replace("15:05,16:05", "16:05,15:05")]:
            path.write_text(changed)
            with self.assertRaises(CalendarError):
                load_semester(self.ctx.folder)
        path.write_text(source)
