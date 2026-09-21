"""Inline exception grammar, composition, precedence and noon boundaries."""

import tempfile
import shutil
import unittest
from dataclasses import replace
from datetime import date, time
from pathlib import Path

from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.exceptions import inline_overrides
from shbs_calendar.models import Activity, CalendarError, Course, DayOverride, Session
from shbs_calendar.schedule import build_preview
from shbs_calendar.storage import digest, load_overrides, load_semester
from shbs_calendar.semesters import create_semester

MON, FRI = date(2026, 9, 14), date(2026, 9, 18)


class ExceptionTests(unittest.TestCase):
    def window_preview(self, rules, *, shift=0):
        # A single long session makes boundary and split behavior unambiguous.
        semester = replace(self.ctx.semester, sessions=(Session("edge", "long", "A", time(9), time(12)),),
                           weekdays={0: "edge"}, activities={}, activity_sessions=(), timing_options={})
        items = inline_overrides([(str(MON), rule) for rule in rules], semester, MON, MON)
        return build_preview(semester, [Course("A", "数学", "Room 1", enabled=True)], self.ctx.identity,
                             MON, MON, shift, personal=items)

    def test_blank_windows_split_trim_remove_and_stable_ids(self):
        def times(result):
            return [(e.start.time(), e.end.time()) for e in result.events]
        whole = self.window_preview([])
        split = self.window_preview(["blank=10:00-11:00"])
        self.assertEqual(times(split), [(time(9), time(10)), (time(11), time(12))])
        self.assertEqual(split.events[0].uid, whole.events[0].uid)
        self.assertNotEqual(split.events[0].uid, split.events[1].uid)
        self.assertEqual([e.uid for e in split.events], [e.uid for e in self.window_preview(["blank=10:00-11:00"]).events])
        self.assertTrue(all(e.title == "数学" and e.location == "Room 1" for e in split.events))
        self.assertFalse(self.window_preview(["blank=10:00-11:00", "overlap=remove"]).events)
        self.assertFalse(self.window_preview(["blank=00:00-24:00"]).events)
        self.assertEqual(times(self.window_preview(["blank=08:00-09:00", "blank=12:00-13:00", "overlap=remove"])), times(whole))
        self.assertEqual(times(self.window_preview(["blank=09:30-10:30", "blank=10:00-11:00"])), [(time(9), time(9, 30)), (time(11), time(12))])

    def test_custom_cutoffs_apply_after_shift_and_can_combine(self):
        result = self.window_preview(["no-morning=09:30", "no-afternoon=11:30"], shift=20)
        self.assertEqual([(e.start.time(), e.end.time()) for e in result.events], [(time(9, 30), time(11, 30))])
        self.assertFalse(self.window_preview(["no-morning=09:30", "overlap=remove"]).events)
        # A matching custom cutoff replaces the old start-only half-day filter.
        self.assertTrue(self.window_preview(["no-morning", "no-morning=09:30"]).events)

    def test_blank_windows_validation_and_csv_roundtrip(self):
        for rule in ("blank=", "blank=11:00-10:00", "blank=10:00-10:00", "blank=25:00-26:00", "blank=9-10", "blank=10:00-11:00,", "overlap=other", "no-morning=", "no-afternoon=25:00"):
            with self.subTest(rule=rule), self.assertRaises(CalendarError):
                self.window_preview([rule])
        for rules in (["no-morning=12:00", "no-afternoon=10:00"], ["overlap=remove"], ["off", "blank=10:00-11:00"]):
            with self.subTest(rules=rules), self.assertRaises(CalendarError):
                self.window_preview(rules)
        item = DayOverride(MON, "partial", blank_hours="10:00-11:00,14:00-15:00", morning_cutoff="09:00", afternoon_cutoff="17:00", overlap="remove")
        self.ctx.save_exceptions([item], digest(self.ctx.exceptions_path))
        self.assertEqual(self.ctx.exceptions(), [item])
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            self.ctx.save_exceptions([], "stale")
        self.ctx.exceptions_path.write_text("date,action\n2026-09-14,off\n")
        self.assertEqual(self.ctx.exceptions(), [DayOverride(MON, "off")])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", self.root / "semesters")
        self.workspace = Workspace(self.root)
        self.ctx = self.workspace.use_semester("2026-27-s1")
        self.ctx.save_courses([Course(b, "Class " + b, enabled=True, timing_option="study_hall" if b == "T" else "") for b in self.ctx.semester.blocks], digest(self.ctx.courses_path))
        self.settings = dict(mode="custom", anchor=str(FRI), end=str(FRI), schedule_mode="inline")

    def tearDown(self):
        self.temp.cleanup()

    def test_weekday_and_half_day_combine_in_either_order(self):
        pairs = [[str(FRI), "Mon"], [str(FRI), "no-afternoon"]]
        for rules in (pairs, list(reversed(pairs)), pairs + pairs):
            preview = self.ctx.preview(self.settings | dict(inline_exceptions=rules, cas=True))
            self.assertEqual([e.block for e in preview.events], ["B", "A", "C"])
            self.assertTrue(all(e.start.date() == FRI for e in preview.events))
            self.assertIn("cutoff 12:30", preview.notes[0])
        preview = self.ctx.preview(self.settings | dict(inline_exceptions=[[str(FRI), "Mon"], [str(FRI), "no-morning"]], cas=True))
        self.assertEqual([e.block for e in preview.events], ["F", "D", "cas"])

    def test_cutoff_uses_effective_start_keeps_whole_lessons_and_can_change(self):
        sessions = (Session("edge", "before", "A", time(12, 29), time(12, 50)), Session("edge", "at", "B", time(12, 30), time(12, 55)))
        semester = replace(self.ctx.semester, sessions=sessions, weekdays={0: "edge"}, activities={}, activity_sessions=(), timing_options={})
        courses = [Course("A", "Crosses noon", enabled=True), Course("B", "At noon", enabled=True)]
        def preview(rule, shift=0, sem=semester):
            overrides = inline_overrides([[str(MON), rule]], sem, MON, MON)
            return build_preview(sem, courses, self.ctx.identity, MON, MON, shift, personal=overrides)
        morning = preview("no-afternoon")
        self.assertEqual([e.block for e in morning.events], ["A"])
        self.assertEqual(morning.events[0].end.time(), time(12, 50))
        self.assertEqual([e.block for e in preview("no-morning").events], ["B"])
        self.assertFalse(preview("no-afternoon", shift=20).events)
        self.assertFalse(preview("no-morning", sem=replace(semester, noon_cutoff=time(13))).events)

    def test_inline_defaults_ignore_saved_rows_and_can_explicitly_include_them(self):
        self.ctx.save_exceptions([DayOverride(MON, "off"), DayOverride(FRI, "off")], digest(self.ctx.exceptions_path))
        original = self.ctx.exceptions_path.read_bytes()
        settings = self.settings | dict(anchor=str(MON), inline_exceptions=[[str(FRI), "Mon"]])
        preview = self.ctx.preview(settings)
        self.assertEqual(len(preview.events), 27)
        saved = self.ctx.preview(settings | dict(schedule_mode="exceptions"))
        self.assertEqual(len(saved.events), 22)
        self.assertEqual(self.ctx.exceptions_path.read_bytes(), original)
        self.ctx.exceptions_path.write_text("broken CSV")
        self.assertEqual(len(self.ctx.preview(settings).events), 27)

    def test_invalid_rules_conflicts_and_outside_dates_fail(self):
        for pairs in [
            [["2026-09-19", "Mon"]], [[str(FRI), "unknown"]],
            [[str(FRI), "Mon"], [str(FRI), "Tue"]],
            [[str(FRI), "no-morning"], [str(FRI), "no-afternoon"]],
            [[str(FRI), "off"], [str(FRI), "Mon"]],
            [[str(FRI), "late"], [str(FRI), "normal"]], [[str(FRI), "Sun"]]]:
            with self.subTest(pairs=pairs), self.assertRaises(CalendarError):
                self.ctx.preview(self.settings | dict(inline_exceptions=pairs))

    def test_custom_weekday_mapping_and_late_composition(self):
        semester = replace(self.ctx.semester, weekdays={0: "friday"})
        items = inline_overrides([[str(FRI), "Mon"], [str(FRI), "late"]], semester, FRI, FRI)
        self.assertEqual(items[0].pattern, "friday")
        self.assertEqual(items[0].time_shift_minutes, 20)
        by_pattern = inline_overrides([[str(FRI), "tuesday"]], self.ctx.semester, FRI, FRI)
        self.assertEqual(by_pattern[0].pattern, "tuesday")

    def test_saved_half_day_roundtrip_and_weekend_noop(self):
        self.ctx.save_exceptions([DayOverride(FRI, "use", "monday", half_day="no-afternoon")], digest(self.ctx.exceptions_path))
        actual = load_overrides(self.ctx.exceptions_path, self.ctx.semester)[0]
        self.assertEqual(actual.half_day, "no-afternoon")
        self.assertEqual(len(self.ctx.preview(self.settings | dict(schedule_mode="exceptions")).events), 3)
        weekend = self.settings | dict(anchor="2026-09-19", end="2026-09-19", inline_exceptions=[["2026-09-19", "no-afternoon"]])
        self.assertFalse(self.ctx.preview(weekend).events)

    def test_half_day_removes_clubs_after_replacement_pattern(self):
        self.ctx.save_activities([Activity("club-tue", "Chess", True)], digest(self.ctx.activities_path))
        settings = self.settings | dict(clubs=True, inline_exceptions=[[str(FRI), "Tue"], [str(FRI), "no-afternoon"]])
        self.assertEqual([e.block for e in self.ctx.preview(settings).events], ["A", "E", "S"])

    def test_custom_cutoff_is_loaded_from_semester_definition(self):
        source = self.root / "source.csv"
        source.write_text("pattern,block,start,end\nred,X,12:40,13:20\n")
        folder = create_semester(self.workspace, "custom", blocks="X", weekdays="mon=red", timetable=source, noon_cutoff="13:00")
        self.assertEqual(load_semester(folder).noon_cutoff, time(13))
        with self.assertRaises(CalendarError):
            create_semester(self.workspace, "invalid", blocks="X", noon_cutoff="bad")
