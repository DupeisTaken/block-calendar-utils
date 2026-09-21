"""Independent timetable fixtures and failure cases; all student data is synthetic."""

import shutil
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from bcutils.app import DEFAULT_ROOT, Workspace
from bcutils.ical import calendar_bytes
from bcutils.models import CalendarError, Course, DayOverride, Session
from bcutils.schedule import build_preview, date_range
from bcutils.storage import (atomic_write, digest, load_courses, load_semester,
                                   parse_time, safe_child, save_courses)

MON = date(2026, 9, 14)
ID = "472b895a-d1ac-4e5b-8203-02e2aa01d607"
# Each expected row was transcribed from the workbook, not generated from CSV.
EXPECTED = [
    [("B", "08:10", "09:30"), ("A", "09:40", "10:20"), ("C", "10:30", "11:50"), ("F", "12:45", "14:05"), ("D", "14:15", "14:55")],
    [("A", "08:10", "09:30"), ("E", "09:40", "10:20"), ("S", "10:30", "11:50"), ("D", "12:45", "14:05"), ("G", "14:15", "15:35")],
    [("E", "08:10", "09:30"), ("G", "09:40", "10:20"), ("C", "10:30", "11:50"), ("F", "12:45", "13:25"), ("El", "13:35", "14:55"), ("T", "15:05", "15:45")],
    [("F", "08:10", "09:30"), ("B", "09:40", "10:20"), ("S", "10:30", "11:50"), ("G", "12:45", "14:05"), ("E", "14:15", "15:35"), ("T", "15:45", "16:25")],
    [("D", "08:10", "09:30"), ("C", "09:40", "10:20"), ("A", "10:30", "11:50"), ("B", "12:45", "14:05")],
]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.sem = load_semester(DEFAULT_ROOT / "semesters/2026-27-s1")
        self.courses = [Course(b, f"Example {b}", enabled=True, timing_option="study_hall" if b == "T" else "") for b in self.sem.blocks]

    def preview(self, **kwargs):
        args = dict(semester=self.sem, courses=self.courses, profile_id=ID, first=MON, last=date(2026, 9, 20))
        args.update(kwargs)
        return build_preview(**args)

    def test_entire_week_and_200_minute_academic_blocks(self):
        preview = self.preview()
        self.assertEqual(len(preview.events), 26)
        for weekday, expected in enumerate(EXPECTED):
            actual = [(e.block, e.start.strftime("%H:%M"), e.end.strftime("%H:%M")) for e in preview.events if e.start.weekday() == weekday]
            self.assertEqual(actual, expected)
        minutes = Counter()
        for e in preview.events:
            minutes[e.block] += (e.end - e.start).total_seconds() / 60
        self.assertEqual({b: minutes[b] for b in "ABCDEFG"}, {b: 200 for b in "ABCDEFG"})

    def test_t_options_normal_late_and_rename(self):
        for option, normal, late in [("study_hall", "16:25", "16:45"), ("toefl", "17:05", "17:25")]:
            courses = [replace(c, course="Name does not control timing", timing_option=option) if c.block == "T" else c for c in self.courses]
            for shift, end in [(0, normal), (20, late)]:
                events = self.preview(courses=courses, shift=shift).events
                thu = next(e for e in events if e.block == "T" and e.start.weekday() == 3)
                self.assertEqual(thu.end.strftime("%H:%M"), end)
                self.assertEqual(thu.start.strftime("%H:%M"), "16:05" if shift else "15:45")

    def test_friday_follows_monday_preserves_actual_date_and_other_days(self):
        friday = date(2026, 9, 18)
        normal = self.preview()
        changed = self.preview(personal=[DayOverride(friday, "use", "monday")])
        self.assertEqual([e for e in normal.events if e.start.date() != friday], [e for e in changed.events if e.start.date() != friday])
        events = [e for e in changed.events if e.start.date() == friday]
        self.assertEqual([(e.block, e.start.strftime("%H:%M"), e.end.strftime("%H:%M")) for e in events], EXPECTED[0])

    def test_closure_weekend_and_shift_replacement(self):
        items = [DayOverride(MON, "off"), DayOverride(date(2026, 9, 19), "use", "thursday", 0)]
        events = self.preview(shift=20, personal=items).events
        self.assertFalse(any(e.start.date() == MON for e in events))
        t = next(e for e in events if e.block == "T" and e.start.weekday() == 5)
        self.assertEqual(t.end.strftime("%H:%M"), "16:25")
        self.assertTrue(any(e.start.strftime("%H:%M") == "08:30" for e in events))

    def test_personal_replaces_school_row_in_full(self):
        result = self.preview(school=[DayOverride(MON, "off")], personal=[DayOverride(MON, "adjust", time_shift_minutes=0)])
        self.assertEqual(len(result.events), 26)
        self.assertIn("replaces school", result.notes[0])

    def test_duplicate_unknown_and_inapplicable_overrides(self):
        for items in [[DayOverride(MON, "off")] * 2, [DayOverride(MON, "use", "typo")], [DayOverride(date(2026, 9, 19), "adjust", time_shift_minutes=20)]]:
            with self.subTest(items=items), self.assertRaises(CalendarError):
                self.preview(personal=items)

    def test_custom_half_day_and_second_semester(self):
        custom = Session("half", "half-a", "A", parse_time("09:00"), parse_time("09:30"))
        sem = replace(self.sem, id="new-semester", sessions=(custom,), weekdays={0: "half"}, timing_options={})
        result = self.preview(semester=sem, courses=[Course("A", "Math", enabled=True)])
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].start.strftime("%H:%M"), "09:00")

    def test_selection_and_invalid_t(self):
        self.assertEqual(self.preview(courses=[]).events, [])
        for option in ["", "typo"]:
            with self.assertRaises(CalendarError):
                self.preview(courses=[Course("T", "Study", enabled=True, timing_option=option)])
        with self.assertRaises(CalendarError):
            self.preview(courses=[Course("A", "", enabled=True)])
        with self.assertRaisesRegex(CalendarError, "control characters"):
            self.preview(courses=[Course("A", "Title\x00", enabled=True)])

    def test_overlap_and_cross_midnight(self):
        duplicate = replace(self.sem.sessions[0], session_id="extra")
        with self.assertRaisesRegex(CalendarError, "overlaps"):
            self.preview(semester=replace(self.sem, sessions=(*self.sem.sessions, duplicate)))
        with self.assertRaisesRegex(CalendarError, "midnight"):
            self.preview(shift=720)

    def test_range_presets_boundaries(self):
        self.assertEqual(date_range("week", "2026-09-16", 3), (MON, date(2026, 10, 4)))
        self.assertEqual(date_range("custom", "2026-09-16", end="2026-09-18"), (date(2026, 9, 16), date(2026, 9, 18)))
        self.assertEqual(date_range("next", today=date(2026, 12, 31)), (date(2027, 1, 4), date(2027, 1, 10)))
        self.assertEqual(date_range("custom", "2028-02-29", end="2028-02-29"), (date(2028, 2, 29),) * 2)
        for args in [("custom", "2026-09-18", 1, "2026-09-16"), ("week", "2026-02-30"), ("this", "", 0), ("custom", "2026-2-3", 1, "2026-02-04")]:
            with self.assertRaises(CalendarError):
                date_range(*args)

    def test_single_day_boundaries_and_invalid_input(self):
        # The day mode must neither round to Monday nor use a stale saved end.
        for day in (date(2026, 9, 17), date(2026, 9, 19), date(2028, 2, 29), date.min, date.max):
            with self.subTest(day=day):
                self.assertEqual(date_range("day", day.isoformat(), end="stale"), (day, day))
        for text in ("", "2026-02-29", "2026-9-17", "2026-09-17:2026-09-18"):
            with self.subTest(text=text), self.assertRaises(CalendarError):
                date_range("day", text)

    def test_uids_stable_across_ranges_titles_and_t_duration(self):
        base = self.preview()
        renamed = [replace(c, course="New title", timing_option="toefl" if c.block == "T" else "") for c in self.courses]
        partial = self.preview(courses=renamed, first=date(2026, 9, 17))
        self.assertEqual([e.uid for e in base.events if e.start.date() >= date(2026, 9, 17)], [e.uid for e in partial.events])
        other = self.preview(profile_id="75963db0-a2d6-431e-b30c-2191d63671b5")
        self.assertFalse({e.uid for e in base.events} & {e.uid for e in other.events})

    def test_ical_utc_escaping_folding_and_empty(self):
        event = replace(self.preview().events[0], title="中文,;\\\n" * 40, location="Room, 2; east", description="Line 1\r\nLine 2")
        data = calendar_bytes([event], now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        lines = data.split(b"\r\n")
        self.assertTrue(all(len(line) <= 75 for line in lines))
        for line in lines:
            line.decode("utf-8")
        unfolded = data.replace(b"\r\n ", b"").decode()
        self.assertIn("DTSTART:20260914T001000Z", unfolded)
        self.assertIn("\\,\\;\\\\\\n", unfolded)
        self.assertIn("DESCRIPTION:Line 1\\nLine 2", unfolded)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertNotIn(b"BEGIN:VEVENT", calendar_bytes([]))

    def test_exported_events_have_no_generated_annotations(self):
        courses = [replace(c, teacher="Example Teacher", location="Room 12") for c in self.courses]
        for overrides in ([], [DayOverride(date(2026, 9, 18), "use", "monday", note="Makeup day")]):
            with self.subTest(overrides=overrides):
                preview = self.preview(courses=courses, personal=overrides)
                baseline = self.preview(personal=overrides)
                self.assertTrue(preview.events)
                self.assertTrue(all(e.description == "" for e in preview.events))
                self.assertEqual([(e.uid, e.title, e.start, e.end) for e in preview.events],
                                 [(e.uid, e.title, e.start, e.end) for e in baseline.events])
                self.assertTrue(all(e.location == "Room 12" for e in preview.events))
                self.assertNotIn(b"DESCRIPTION:", calendar_bytes(preview.events))
                if overrides:
                    self.assertIn("Makeup day", preview.notes[0])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", self.root / "semesters")
        self.workspace = Workspace(self.root)
        self.ctx = self.workspace.context("student", "2026-27-s1", create=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_roundtrip_bom_optional_fields_and_backup(self):
        course = Course("A", 'Chemistry, "advanced"\n化学', "Room 2", "Teacher", True)
        self.ctx.save_courses([course], digest(self.ctx.courses_path))
        actual = self.ctx.courses()[0]
        self.assertEqual(actual, course)
        self.assertTrue(self.ctx.courses_path.with_suffix(".csv.bak").exists())
        self.assertEqual(len(self.ctx.courses()), 10)

    def test_stale_edit_prevents_lost_update(self):
        expected = digest(self.ctx.courses_path)
        self.ctx.courses_path.write_text("block,course\nA,External edit\n", encoding="utf-8")
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            self.ctx.save_courses([Course("A", "Internal", enabled=True)], expected)
        self.assertEqual(self.ctx.courses()[0].course, "External edit")

    def test_bad_csv(self):
        for content in ["name,course\nA,X", "block,course\nA,X\nA,Y", "block,course,enabled\nA,X,maybe", "block,course\nA,X,extra", "block,course,typo\nA,X,Y"]:
            self.ctx.courses_path.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(CalendarError):
                self.ctx.courses()

    def test_safe_paths(self):
        for name in ["../outside", "CON", "a/b", "a\\b", "", "..", "NUL", "file."]:
            with self.assertRaises(CalendarError):
                safe_child(self.root, name)

    def test_failed_atomic_save_preserves_original_and_cleans_temp(self):
        path = self.root / "data.csv"
        path.write_bytes(b"original")
        with patch("bcutils.storage.os.replace", side_effect=OSError("simulated disk error")):
            with self.assertRaises(CalendarError):
                atomic_write(path, b"new")
        self.assertEqual(path.read_bytes(), b"original")
        self.assertEqual(list(self.root.glob(".bcutils-*")), [])

    def test_exclusive_write_and_identity_persistence(self):
        output = self.root / "export.ics"
        atomic_write(output, b"first", overwrite=False)
        with self.assertRaises(CalendarError):
            atomic_write(output, b"second", overwrite=False)
        self.assertEqual(output.read_bytes(), b"first")
        self.assertEqual(self.ctx.identity, self.workspace.context("student", "2026-27-s1", create=True).identity)

    def test_destination_conflict_during_staging_keeps_file_and_cleans_temp(self):
        from bcutils.models import DestinationExistsError
        output = self.root / "raced.ics"
        def concurrent_create(source, destination):
            destination.write_bytes(b"another writer")
            raise FileExistsError("destination was created during staging")
        with patch("bcutils.storage.os.link", side_effect=concurrent_create):
            with self.assertRaises(DestinationExistsError):
                atomic_write(output, b"our export", overwrite=False)
        self.assertEqual(output.read_bytes(), b"another writer")
        self.assertEqual(list(self.root.glob(".bcutils-*")), [])

    def test_invalid_semester_configuration(self):
        folder = self.root / "semesters/2026-27-s1"
        path = folder / "semester.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        for changes in [{"id": "wrong-id"}, {"blocks": ["A", "A"]}, {"utc_offset_minutes": True}, {"weekdays": {"0": "missing"}}, {"timing_options": {"T": {"study_hall": {"missing-session": {"end": "16:25"}}}}}]:
            path.write_text(json.dumps(config | changes), encoding="utf-8")
            with self.subTest(changes=changes), self.assertRaises(CalendarError):
                load_semester(folder)

    def test_cli_service_reads_manual_exception_changes(self):
        self.ctx.save_courses([Course("A", "Math", enabled=True)], digest(self.ctx.courses_path))
        settings = dict(self.workspace.settings(), mode="week", anchor="2026-09-14", schedule_mode="saved")
        self.assertEqual(len(self.ctx.preview(settings).events), 3)
        self.ctx.exceptions_path.write_text("date,action\n2026-09-14,off\n", encoding="utf-8")
        self.assertEqual(len(self.ctx.preview(settings).events), 2)


if __name__ == "__main__":
    unittest.main()
