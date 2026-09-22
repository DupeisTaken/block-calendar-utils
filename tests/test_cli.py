"""Public-command scenarios with synthetic data; normal commands must not prompt."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.fixtures import install_example
from bcutils.app import DEFAULT_ROOT, Workspace
from bcutils.cli import main
from bcutils.cli_dates import parse_cli_date
from bcutils.storage import load_semester


class CLITests(unittest.TestCase):
    def test_blank_date_ranges_and_saved_time_filters(self):
        ctx = self.init()
        before = ctx.exceptions_path.read_bytes()
        result = self.ok("-i", "--day", "2026-09-14:2026-09-18", "--exception", "2026-09-14:2026-09-18", "off")
        self.assertIn("0 events", result.stdout)
        self.assertEqual(ctx.exceptions_path.read_bytes(), before)
        self.ok("-w", "--exceptions", "--set", "2026-09-14:2026-09-16", "--blank-hours", "10:00-11:00", "--morning-cutoff", "09:00", "--afternoon-cutoff", "16:00", "--overlap", "remove")
        self.assertEqual(len(ctx.exceptions()), 3)
        self.assertTrue(all(i.blank_hours == "10:00-11:00" and i.overlap == "remove" for i in ctx.exceptions()))
        self.assertIn("morning cutoff 09:00", self.ok("-i", "--exceptions").stdout)
        self.ok("-w", "--exceptions", "--remove", "2026-09-14:2026-09-16")
        self.assertEqual(ctx.exceptions(), [])
        for dates in ("2026-09-16:2026-09-14", "2026-09-31", "2020-01-01:2040-01-01"):
            self.assertEqual(self.run_cli("-w", "--exceptions", "--set", dates, "--off").returncode, 2)

    def test_time_window_export_utc_and_activity_flags_per_stage(self):
        ctx = self.init()
        self.ok("-w", "--activities", "--set", "club-tue", "Chess")
        original = ctx.activities_path.read_bytes()
        self.assertIn("Chess", self.ok("-i", "--day", "2026-09-15").stdout)
        result = self.ok("-i", "--day", "2026-09-15", "--noclub", "--nocas")
        self.assertNotIn("Chess", result.stdout)
        for flags in (("--cas", "--nocas"), ("--clubs", "--noclub")):
            self.assertEqual(self.run_cli("-i", "--day", "2026-09-15", *flags).returncode, 2)
        result = self.ok("-i", "--day", "2026-09-15", "--noclub", "-i", "--day", "2026-09-15")
        self.assertEqual(result.stdout.count("Chess"), 1)
        output = self.root / "trimmed.ics"
        self.ok("-e", "--day", "2026-09-15", "--only", "C", "--exception", "2026-09-15", "blank=16:00-16:10", "--output", str(output))
        data = output.read_text()
        self.assertEqual(data.count("SUMMARY:Chess"), 2)
        self.assertIn("DTEND:20260915T080000Z", data)
        self.assertIn("DTSTART:20260915T081000Z", data)
        self.assertEqual(ctx.activities_path.read_bytes(), original)

    def test_new_exception_help_never_executes_earlier_write(self):
        ctx = self.init()
        before = ctx.exceptions_path.read_bytes()
        result = self.ok("-w", "--exceptions", "--set", "2026-09-14:2026-09-16", "--off", "-e", "--help")
        self.assertIn("--noclub", result.stdout)
        self.assertIn("--nocas", result.stdout)
        self.assertEqual(ctx.exceptions_path.read_bytes(), before)
        # A malformed later time rule must not leave earlier writes behind.
        original_courses = ctx.courses_path.read_bytes()
        for options in (("--blank-hours", "11:00-10:00"), ("--overlap", "trim"), ()):
            result = self.run_cli("-w", "--courses", "--set", "A", "Changed", "-w", "--exceptions", "--set", "2026-09-14", *options)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(ctx.courses_path.read_bytes(), original_courses)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bcutils with spaces ")
        self.root = Path(self.temp.name)
        install_example(self.root)
        self.workspace = Workspace(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, answers=None):
        out, err = io.StringIO(), io.StringIO()
        # Yearless examples stay deterministic after the calendar year changes.
        with redirect_stdout(out), redirect_stderr(err), patch("builtins.input", side_effect=answers if answers is not None else AssertionError("Unexpected input prompt")), patch("bcutils.cli.date") as clock, patch("bcutils.cli.parse_cli_date", side_effect=lambda value, **kw: parse_cli_date(value, today=kw.get("today", date(2026, 9, 18)))):
            clock.today.return_value = date(2026, 9, 18)
            try:
                code = main(["--root", str(self.root), *args])
            except SystemExit as exc:
                code = exc.code
        return SimpleNamespace(returncode=code, stdout=out.getvalue(), stderr=err.getvalue())

    def ok(self, *args, **kwargs):
        result = self.run_cli(*args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def init(self):
        self.ok("semester", "use", "2026-27-s1", "--profile", "student")
        self.ok("courses", "set", "A", "Example Math")
        self.ok("courses", "set", "T", "Study period", "--timing", "study-hall")
        return self.workspace.context("student", "2026-27-s1")

    def test_sequential_navigation_writes_inspects_and_exports(self):
        output = self.root / "stacked.ics"
        result = self.ok("--profile", "stacked", "-w", "--semesters", "--use", "2026-27-s1",
                         "-w", "--courses", "--set", "A", "数学", "-w", "--activities", "--set", "club-tue", "Chess",
                         "-i", "--day", "0920-0924", "--clubs", "-e", "--day", "0920-0924", "--clubs", "--output", str(output))
        self.assertIn("Exported", result.stdout)
        self.assertIn("数学", result.stdout)
        ctx = self.workspace.context("stacked", "2026-27-s1")
        self.assertEqual(ctx.courses()[0].course, "数学")
        self.assertIn("Chess", output.read_text(encoding="utf-8"))
        self.assertEqual(self.workspace.settings()["profile"], "stacked")

    def test_workflow_preflights_later_syntax_dates_and_context_before_saving(self):
        start = ("-w", "--semesters", "--use", "2026-27-s1")
        for tail in [("-e", "--day", "0920-0924", "--typo"), ("-e", "--day", "0230"),
                     ("-e", "--day", "0924-0920"), ("-e", "--day", "0920", "--weeks", "2"),
                     ("--profile", "one", "-e", "--day", "0920", "--profile", "two"),
                     ("--semester", "different-semester", "-e", "--day", "0920"),
                     ("-i", "--courses", "--set", "A", "Must not save")]:
            with self.subTest(tail=tail):
                result = self.run_cli(*start, *tail)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.workspace.local.exists())

    def test_workflow_help_anywhere_never_runs_earlier_write(self):
        for suffix in [("-e", "--docs"), ("-i", "--help"), ("-w", "--courses", "--set", "--docs")]:
            with self.subTest(suffix=suffix):
                self.ok("-w", "--semesters", "--use", "2026-27-s1", *suffix)
                self.assertFalse(self.workspace.local.exists())

    def test_workflow_cancellation_discards_batch_and_stops_export(self):
        ctx = self.init()
        before = ctx.courses_path.read_bytes()
        for abort in (EOFError(), KeyboardInterrupt()):
            result = self.run_cli("-w", "--courses", "-e", "--day", "0918", answers=["Unsaved", abort])
            self.assertEqual(result.returncode, 130)
            self.assertEqual(ctx.courses_path.read_bytes(), before)
            self.assertFalse((self.root / "exports").exists())
            self.assertIn("Later actions did not run", result.stderr)

    def test_workflow_runtime_failure_preserves_completed_writes_and_stops_later_ones(self):
        ctx = self.init()
        output = self.root / "existing.ics"
        output.write_bytes(b"keep this calendar")
        result = self.run_cli("-w", "--courses", "--set", "A", "Saved before failure",
                              "-e", "--day", "0918", "--output", str(output),
                              "-w", "--courses", "--set", "B", "Must not run")
        self.assertEqual(result.returncode, 2)
        courses = {c.block: c for c in ctx.courses()}
        self.assertEqual(courses["A"].course, "Saved before failure")
        self.assertEqual(courses["B"].course, "")
        self.assertEqual(output.read_bytes(), b"keep this calendar")
        self.assertIn("rerun the export action with --overwrite", result.stderr)
        self.ok("-e", "--day", "0918", "--output", str(output), "--overwrite")
        self.assertIn(b"Saved before failure", output.read_bytes())

    def test_workflow_inspection_only_remembers_preview_and_options_do_not_leak(self):
        self.init()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.ok("-i", "--courses", "-i", "--activities", "-i", "--semesters", "-i", "--exceptions",
                "-i", "--day", "0918", "--late", "-i", "--validate", "--day", "0918")
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and self.workspace.local / "inspections" not in p.parents}
        self.assertEqual(before, after)
        output = self.root / "normal.ics"
        self.ok("-i", "--day", "0918", "--late", "-e", "--day", "0918", "--output", str(output))
        self.assertIn(b"DTSTART:20260918T023000Z", output.read_bytes())

    def test_export_last_inspection_separate_commands_keeps_reviewed_events(self):
        from bcutils.inspection import inspection_path, load_inspection
        ctx = self.init()
        self.ok("-w", "--courses", "--set", "A", "数学课程")
        settings = self.workspace.settings_path.read_bytes()
        self.ok("-i", "--day", "2026-09-18", "--exception", "2026-09-18", "blank=11:00-11:10", "--late", "--noclub")
        saved, _ = load_inspection(ctx)
        self.assertEqual(len(saved.events), 2)
        original = inspection_path(ctx).read_bytes()
        self.ok("-w", "--courses", "--set", "A", "Changed after inspection")
        output = self.root / "last.ics"
        result = self.ok("-e", "--last-inspect", "--output", str(output))
        self.assertIn("Last inspection: student / 2026-27-s1", result.stdout)
        data = output.read_text(encoding="utf-8")
        self.assertEqual(data.count("SUMMARY:数学课程"), 2)
        self.assertNotIn("Changed after inspection", data)
        self.assertIn("DTSTART:20260918T025000Z", data)
        self.assertIn("DTEND:20260918T041000Z", data)
        self.assertTrue(all(e.uid in data for e in saved.events))
        self.assertEqual(inspection_path(ctx).read_bytes(), original)
        self.assertEqual(self.workspace.settings_path.read_bytes(), settings)
        self.assertEqual(self.run_cli("-e", "-l", "--output", str(output)).returncode, 2)
        self.ok("-e", "-l", "--output", str(output), "--overwrite")

    def test_export_last_inspection_combined_and_late_shortcuts(self):
        self.init()
        output = self.root / "stacked-last.ics"
        self.ok("-i", "--day", "2026-09-18", "-l", "-e", "-l", "--output", str(output))
        self.assertIn("DTSTART:20260918T025000Z", output.read_text())
        # An explicit-date export still builds events independently of inspection.
        self.ok("-e", "--day", "2026-09-18", "--output", str(output), "--overwrite")
        self.assertIn("DTSTART:20260918T023000Z", output.read_text())
        self.ok("-e", "--day", "2026-09-18", "--late", "--output", str(output), "--overwrite")
        self.assertIn("DTSTART:20260918T025000Z", output.read_text())

    def test_last_inspection_preserves_activities_and_never_resolves_relative_dates_again(self):
        from bcutils.inspection import load_inspection
        ctx = self.init()
        self.ok("-w", "--activities", "--set", "club-tue", "Chess")
        self.ok("-i", "--next-week", "--cas", "--only", "C")
        preview, _ = load_inspection(ctx)
        self.assertEqual([event.title for event in preview.events], ["CAS", "Chess"])
        self.ok("-w", "--activities", "--disable", "club-tue")
        output = self.root / "fixed-week.ics"
        with patch("bcutils.app.Context.preview", side_effect=AssertionError("Must export the reviewed snapshot")):
            self.ok("-e", "--last-inspect", "--output", str(output))
        data = output.read_text()
        self.assertIn("SUMMARY:Chess", data)
        self.assertIn("SUMMARY:CAS", data)
        self.assertTrue(all(event.uid in data for event in preview.events))

    def test_last_inspection_snapshot_save_failure_is_reported(self):
        from bcutils.inspection import inspection_path
        from bcutils.models import CalendarError
        ctx = self.init()
        self.ok("-i", "--day", "2026-09-18")
        original = inspection_path(ctx).read_bytes()
        with patch("bcutils.inspection.write_json", side_effect=CalendarError("Cannot remember inspection")):
            result = self.run_cli("-i", "--day", "2026-09-17", "-e", "--last-inspect")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Cannot remember inspection", result.stderr)
        self.assertEqual(inspection_path(ctx).read_bytes(), original)
        self.assertFalse((self.root / "exports").exists())

    def test_only_successful_dated_inspection_replaces_snapshot(self):
        from bcutils.inspection import inspection_path
        ctx = self.init()
        self.assertEqual(self.run_cli("-e", "--last-inspect").returncode, 2)
        self.ok("-i", "--day", "2026-09-18")
        path = inspection_path(ctx)
        original = path.read_bytes()
        self.ok("-i", "--courses", "-i", "--activities", "-i", "--exceptions", "-i", "--validate", "--day", "2026-09-17")
        self.ok("-i", "--day", "2026-09-17", "-e", "--last-inspect", "--help")
        self.assertEqual(self.run_cli("-i", "--day", "2026-09-17", "--width", "1").returncode, 2)
        self.assertEqual(path.read_bytes(), original)
        self.ok("-i", "--day", "2026-09-19")
        result = self.run_cli("-e", "--last-inspect")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no events", result.stderr)
        self.assertFalse((self.root / "exports").exists())

    def test_last_inspection_rejects_filters_before_earlier_writes(self):
        ctx = self.init()
        original = ctx.courses_path.read_bytes()
        for flags in (("--day", "0918"), ("--week", "0918"), ("--next-week",), ("--last-date", "0918"),
                      ("--weeks", "2"), ("--late",), ("--normal",), ("--cas",), ("--nocas",),
                      ("--clubs",), ("--noclub",), ("--only", "A"), ("--exclude", "T"),
                      ("--schedule", "weekdays"), ("--exception", "0918", "off")):
            with self.subTest(flags=flags):
                result = self.run_cli("-w", "--courses", "--set", "A", "Must not save", "-e", "--last-inspect", *flags)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(ctx.courses_path.read_bytes(), original)

    def test_last_inspection_is_scoped_by_profile_semester_and_identity(self):
        from bcutils.inspection import inspection_path
        ctx = self.init()
        self.ok("-i", "--day", "2026-09-18")
        self.ok("--profile", "other", "-w", "--init")
        self.assertEqual(self.run_cli("--profile", "other", "-e", "--last-inspect").returncode, 2)
        self.ok("-w", "--semesters", "--new", "next", "--copy", "2026-27-s1")
        self.ok("--semester", "next", "-w", "--init")
        self.assertEqual(self.run_cli("--semester", "next", "-e", "--last-inspect").returncode, 2)
        record = json.loads(inspection_path(ctx).read_text())
        record["identity"] = "different-profile-id"
        inspection_path(ctx).write_text(json.dumps(record))
        result = self.run_cli("-e", "--last-inspect")
        self.assertEqual(result.returncode, 2)
        self.assertIn("different profile", result.stderr)

    def test_last_inspection_corruption_is_actionable_and_never_exports(self):
        from bcutils.inspection import inspection_path, load_inspection
        ctx = self.init()
        self.ok("-i", "--day", "2026-09-18")
        path = inspection_path(ctx)
        record = json.loads(path.read_text())
        # The displayed source time is UTC even if an aware saved timestamp
        # uses another offset.
        path.write_text(json.dumps(record | {"inspected_at": "2026-09-21T08:15:00+08:00"}))
        self.assertEqual(load_inspection(ctx)[1].isoformat(), "2026-09-21T00:15:00+00:00")
        broken_event = dict(record["preview"]["events"][0], start="2026-09-18T10:30:00")
        for text in ("broken", "{}", json.dumps(record | {"version": 42}),
                     json.dumps(record | {"preview": record["preview"] | {"events": [broken_event]}})):
            with self.subTest(text=text):
                path.write_text(text)
                result = self.run_cli("-e", "--last-inspect")
                self.assertEqual(result.returncode, 2)
                self.assertIn("Run --inspect", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.root / "exports").exists())

    def test_last_inspection_survives_real_process_boundary(self):
        self.init()
        base = [sys.executable, "-m", "bcalendar-utils", "--root", str(self.root)]
        result = subprocess.run(base + ["-i", "--day", "2026-09-18", "--late"], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "other-process.ics"
        result = subprocess.run(base + ["-e", "-l", "--output", str(output)], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DTSTART:20260918T025000Z", output.read_text())

    def test_workflow_literal_values_and_shared_context_are_not_actions(self):
        self.init()
        self.ok("-w", "--courses", "--set", "A", "export", "--room=--write",
                "-i", "--courses", "--profile=student")
        ctx = self.workspace.context("student", "2026-27-s1")
        self.assertEqual(ctx.courses()[0].location, "--write")
        self.ok("-w", "--courses", "--set", "--", "A", "--export")
        self.assertEqual(ctx.courses()[0].course, "--export")
        result = self.run_cli("-w", "--courses", "--set", "A", "Name", "--room", "-e", "--day", "0918")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(ctx.courses()[0].course, "--export")

    def test_workflow_hyphen_ranges_and_week_long_form(self):
        self.init()
        expected = self.ok("-i", "--day", "2026-09-20:2026-09-24").stdout
        for dates in ("0920-0924", "9.20-9.24", "9/20-9/24", "20260920-20260924"):
            with self.subTest(dates=dates):
                self.assertEqual(self.ok("-i", "--day", dates).stdout, expected)
        self.ok("-i", "--week", "0920", "--weeks", "2")
        self.assertEqual(self.run_cli("-e", "-w", "0920").returncode, 2)

    def test_workflow_overwrite_permission_is_local_to_each_export(self):
        self.init()
        output = self.root / "repeated.ics"
        output.write_bytes(b"old")
        result = self.run_cli("-e", "--day", "0918", "--output", str(output), "--overwrite",
                              "-e", "--day", "0918", "--output", str(output))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Stopped at action 2", result.stderr)
        self.assertIn(b"BEGIN:VCALENDAR", output.read_bytes())

    def test_workflow_module_process_with_unicode_entry(self):
        self.init()
        output = self.root / "process.ics"
        result = subprocess.run([sys.executable, "-m", "bcalendar-utils", "--root", str(self.root),
                                 "-w", "--courses", "--edit", "A", "-e", "--day", "0920-0924", "--output", str(output)],
                                input="数学\n", capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b", result.stdout)
        self.assertIn("数学", output.read_text(encoding="utf-8"))

    def test_no_arguments_is_help_without_files_or_questions(self):
        result = self.ok()
        self.assertIn("First time using? run python -m bcalendar-utils --docs", result.stdout)
        self.assertLessEqual(len(result.stdout.splitlines()), 12)
        self.assertEqual(result.stdout, self.ok("-h").stdout)
        self.assertEqual(result.stdout, self.ok("--help").stdout)
        self.assertFalse(self.workspace.local.exists())

    def test_overwrite_correction_preserves_file_and_both_suggested_retries_work(self):
        self.init()
        command = ("-d", "0920:0924", "-e", "0920", "Thu", "-e", "0924", "Fri")
        self.ok(*command)
        output = self.root / "exports/student-2026-27-s1-2026-09-20-2026-09-24.ics"
        original = output.read_bytes()
        self.ok("--courses", "--set", "A", "Revised 数学")
        conflict = self.run_cli(*command)
        self.assertEqual(conflict.returncode, 2)
        self.assertIn("export action with --overwrite added", conflict.stderr)
        self.assertIn('--output "exports/another-name.ics"', conflict.stderr)
        self.assertNotIn("allow overwrite", conflict.stderr)
        self.assertNotIn("\x1b", conflict.stderr)
        self.assertEqual(output.read_bytes(), original)
        alternative = self.root / "exports/another name.ics"
        self.ok(*command, "--output", str(alternative))
        self.assertEqual(output.read_bytes(), original)
        self.assertIn("Revised 数学", alternative.read_text(encoding="utf-8"))
        # A custom path must receive the same usable guidance as the default.
        custom_conflict = self.run_cli(*command, "--output", str(alternative))
        self.assertEqual(custom_conflict.returncode, 2)
        self.assertIn("--overwrite", custom_conflict.stderr)
        self.ok(*command, "--overwrite")
        self.assertIn("Revised 数学", output.read_text(encoding="utf-8"))
        self.assertFalse(output.with_suffix(".ics.bak").exists())

    def test_help_for_every_public_operation_never_requires_setup_or_writes(self):
        from bcutils.cli_interface import ROOT_COMMANDS, GROUP_ACTIONS
        paths = [[]]
        for flag, (name, _) in ROOT_COMMANDS.items():
            paths.append([flag])
            paths.extend([flag, "--" + action] for action in GROUP_ACTIONS.get(name, {}))
        for path in paths:
            for help_flag in ("--help", "--docs"):
                with self.subTest(path=path, help_flag=help_flag):
                    self.ok(*path, help_flag)
                    self.assertFalse(self.workspace.local.exists())
                    self.assertFalse((self.root / "exports").exists())

    def test_first_use_and_command_help_are_separate_and_read_only(self):
        guide = self.ok("help").stdout
        self.assertIn("--semesters --use mine", guide)
        self.assertIn("--courses", guide)
        self.assertEqual(guide, self.ok("h").stdout)
        for topic in ("semester", "courses", "exceptions"):
            self.assertEqual(self.ok(topic).stdout, self.ok(topic, "-h").stdout)
        for prefix in ("-a", "--activities", "a", "activities"):
            help_text = self.ok(prefix, "-h").stdout
            self.assertIn("club names", help_text)
            self.assertIn("--activities --set club-tue", help_text)
            self.assertNotIn("--noon-cutoff", help_text)
        self.assertEqual(self.ok("help", "a", "s").stdout, self.ok("-a", "set", "-h").stdout)
        self.assertIn("Unknown help topic", self.run_cli("help", "missing").stderr)
        self.assertFalse(self.workspace.local.exists())

    def test_bare_activities_prompts_save_names_at_predefined_times(self):
        ctx = self.init()
        school = (ctx.folder / "activities.csv").read_bytes()
        courses = ctx.courses_path.read_bytes()
        settings = self.workspace.settings_path.read_bytes()
        for prefix in ("-a", "a", "--activities", "activities"):
            prompts = []
            answers = iter(["Chess", "机器人俱乐部"])
            def answer(prompt):
                prompts.append(prompt)
                return next(answers)
            result = self.ok(prefix, answers=answer)
            self.assertEqual(len(prompts), 2)
            self.assertIn("tuesday 15:45–16:35", result.stdout)
            self.assertIn("wednesday 15:50–16:40", result.stdout)
            self.assertEqual([a.name for a in ctx.activities() if a.enabled], ["Chess", "机器人俱乐部"])
        output = self.root / "clubs.ics"
        self.ok("-d", "20260915:20260916", "-C", "-X", "A,T", "-o", str(output))
        data = output.read_bytes()
        self.assertEqual(data.count(b"BEGIN:VEVENT"), 2)
        self.assertIn(b"DTSTART:20260915T074500Z", data)
        self.assertIn(b"DTEND:20260916T084000Z", data)
        self.assertIn("机器人俱乐部".encode(), data)
        self.assertEqual((ctx.folder / "activities.csv").read_bytes(), school)
        self.assertEqual(ctx.courses_path.read_bytes(), courses)
        self.assertEqual(self.workspace.settings_path.read_bytes(), settings)

    def test_activity_edit_keep_clear_subset_and_metadata(self):
        ctx = self.init()
        self.ok("a", "s", "club-tue", "Chess", "-R", "Library")
        self.ok("a", "s", "club-wed", "Robotics")
        self.ok("a", "off", "club-tue")
        self.ok("-a", answers=["", "-"])
        items = {a.activity: a for a in ctx.activities()}
        self.assertEqual((items["club-tue"].name, items["club-tue"].location, items["club-tue"].enabled), ("Chess", "Library", False))
        self.assertEqual((items["club-wed"].name, items["club-wed"].enabled), ("", False))
        self.ok("-a", "e", "club-tue", answers=["Debate"])
        items = {a.activity: a for a in ctx.activities()}
        self.assertEqual((items["club-tue"].name, items["club-tue"].location, items["club-tue"].enabled), ("Debate", "Library", True))
        self.assertFalse(items["club-wed"].enabled)

    def test_activity_edit_cancellation_and_invalid_slots_do_not_save(self):
        ctx = self.init()
        for abort in (EOFError(), KeyboardInterrupt()):
            self.assertEqual(self.run_cli("-a", answers=["Unsaved", abort]).returncode, 130)
            self.assertFalse(ctx.activities_path.exists())
        self.ok("-a", answers=["Chess", "Robotics"])
        original = ctx.activities_path.read_bytes()
        self.assertEqual(self.run_cli("-a", answers=["Unsaved", KeyboardInterrupt()]).returncode, 130)
        for ids in [("cas",), ("unknown",), ("club-tue", "club-tue")]:
            self.assertEqual(self.run_cli("-a", "edit", *ids).returncode, 2)
        self.assertEqual(ctx.activities_path.read_bytes(), original)

    def test_activity_edit_detects_external_changes(self):
        ctx = self.init()
        self.ok("-a", answers=["Chess", "Robotics"])
        external = ctx.activities_path.read_bytes().replace(b"Chess", b"External")
        def answer(prompt):
            ctx.activities_path.write_bytes(external)
            return "Unsaved"
        result = self.run_cli("-a", "edit", "club-tue", answers=answer)
        self.assertEqual(result.returncode, 2)
        self.assertIn("changed on disk", result.stderr)
        self.assertEqual(ctx.activities_path.read_bytes(), external)

    def test_activity_entry_shortcut_is_scoped_and_works_in_real_processes(self):
        ctx = self.init()
        self.ok("-pstudent", "--activities", "set", "club-tue", "Chess", "-r", str(self.root))
        self.ok("e", "s", "0918", "-a")
        self.assertEqual(ctx.exceptions()[0].half_day, "no-afternoon")
        self.assertEqual(self.run_cli("p", "-d", "0918", "-a").returncode, 2)
        for module, flag in [("bcalendar-utils", "-a"), ("bcutils", "--activities")]:
            result = subprocess.run([sys.executable, "-m", module, "-r", str(self.root), flag], input="Chess\nRobotics\n", capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("tuesday 15:45–16:35", result.stdout)
            self.assertIn("Saved club names", result.stdout)

    def test_setup_required_and_legacy_settings_do_not_silently_activate(self):
        self.workspace.save_settings({"semester": "2026-27-s1"})
        for args in [("--this-week",), ("courses", "edit"), ("init",)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--semesters --use", result.stderr)
        self.assertFalse((self.workspace.local / "profiles").exists())

    def test_init_preview_export_and_overwrite(self):
        self.init()
        self.assertIn("5 events", self.ok("preview", "--week", "2026-09-14").stdout)
        output = self.root / "calendar.ics"
        self.ok("--dayrange", "2026-09-17:2026-09-18", "-o", str(output))
        original = output.read_bytes()
        self.assertEqual(original.count(b"BEGIN:VEVENT"), 2)
        self.assertEqual(self.run_cli("export", "--week", "2026-09-14", "-o", str(output)).returncode, 2)
        self.assertEqual(output.read_bytes(), original)
        self.ok("export", "--week", "2026-09-14", "-o", str(output), "--overwrite")
        self.assertEqual(output.read_bytes().count(b"BEGIN:VEVENT"), 5)

    def test_three_weeks_late_and_date_aliases(self):
        self.init()
        result = self.ok("preview", "--week", "2026-09-14", "--weeks", "3", "--late")
        self.assertIn("15 events", result.stdout)
        self.assertIn("16:05–16:45", result.stdout)
        for first, last in [("--start", "--end"), ("--first-date", "--last-date")]:
            result = self.ok("preview", first, "2026-09-17", last, "2026-09-18")
            self.assertIn("2 events", result.stdout)
        self.assertIn("1 events", self.ok("preview", "--dayrange", "2026-09-17").stdout)

    def test_single_day_export_preview_validate_and_legacy_parity(self):
        ctx = self.init()
        settings = self.workspace.settings_path.read_bytes()
        courses = ctx.courses_path.read_bytes()
        for command in ("preview", "validate"):
            result = self.ok(command, "--day", "2026-09-17")
            self.assertIn("1 events", result.stdout)
            self.assertEqual(result.stdout, self.ok(command, "--day-range", "2026-09-17").stdout)
        output = self.root / "single.ics"
        self.ok("--day", "2026-09-17", "-o", str(output))
        data = output.read_bytes()
        self.assertEqual(data.count(b"BEGIN:VEVENT"), 1)
        self.assertIn(b"DTSTART:20260917T074500Z", data)
        self.assertIn(b"DTEND:20260917T082500Z", data)
        self.assertEqual(self.run_cli("export", "--day", "2026-09-17", "-o", str(output)).returncode, 2)
        self.assertEqual(output.read_bytes(), data)
        self.assertEqual(self.workspace.settings_path.read_bytes(), settings)
        self.assertEqual(ctx.courses_path.read_bytes(), courses)

    def test_single_day_exceptions_filters_activities_and_empty_export(self):
        self.init()
        self.ok("activities", "set", "club-tue", "Chess")
        result = self.ok("preview", "--day", "2026-09-19", "--exception", "2026-09-19", "Tue", "--clubs", "--late", "--exclude", "A,T")
        self.assertIn("1 events", result.stdout)
        self.assertIn("Chess", result.stdout)
        self.assertIn("16:05–16:55", result.stdout)
        self.ok("exceptions", "set", "2026-09-17", "--off")
        self.assertIn("1 events", self.ok("preview", "--day", "2026-09-17").stdout)
        self.assertIn("0 events", self.ok("preview", "--day", "2026-09-17", "--schedule", "exceptions").stdout)
        for day, extra in [("2026-09-19", ()), ("2026-09-17", ("--schedule", "exceptions"))]:
            output = self.root / "empty.ics"
            result = self.run_cli("--day", day, *extra, "-o", str(output))
            self.assertEqual(result.returncode, 2)
            self.assertIn("No events", result.stderr)
            self.assertFalse(output.exists())

    def test_single_day_rejects_invalid_dates_and_conflicting_selectors(self):
        self.init()
        invalid = [("--day",), ("--day", ""), ("--day", "2026-02-29")]
        for extra in [("--weeks", "1"), ("--next-week",), ("--this-week",),
                      ("--week", "2026-09-14"), ("--day-range", "2026-09-17"),
                      ("--first-date", "2026-09-17"), ("--last-date", "2026-09-18"),
                      ("--exception", "2026-09-18", "off")]:
            invalid.append(("--day", "2026-09-17", *extra))
        for flags in invalid:
            with self.subTest(flags=flags):
                result = self.run_cli("preview", *flags)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_friendly_date_and_range_flags_export_identical_events(self):
        self.init()
        expected = self.ok("preview", "--day-range", "2026-09-17:2026-09-18").stdout
        for flag, value in [("-d", "9.17:9.18"), ("--day", "0917-0918"),
                            ("--dayrange", "2026.9.17..2026/9/18"), ("--day-range", "9-17-9-18")]:
            with self.subTest(flag=flag, value=value):
                self.assertEqual(self.ok("p", flag, value).stdout, expected)
        self.assertEqual(self.ok("p", "-f", "9/17", "-u", "0918").stdout, expected)
        output = self.root / "friendly.ics"
        self.ok("x", "-d", "0917:0918", "-o", str(output))
        data = output.read_bytes()
        self.assertEqual(data.count(b"BEGIN:VEVENT"), 2)
        self.assertIn(b"DTSTART:20260917T074500Z", data)
        self.assertIn(b"DTSTART:20260918T023000Z", data)
        self.ok("-d", "9.17:9.18", "-o", str(output), "-O")

    def test_short_command_workflow_and_all_subcommands(self):
        self.assertIn("2026-27-s1", self.ok("s", "ls").stdout)
        self.assertIn("09:40", self.ok("s", "sh", "2026-27-s1").stdout)
        self.ok("s", "u", "2026-27-s1", "-p", "student")
        self.ok("i")
        self.ok("c", "s", "A", "Math", "-R", "Lab", "-t", "Teacher")
        self.ok("c", "s", "T", "Study", "-T", "study-hall")
        self.ok("c", "e", "A", answers=["Math"])
        self.assertIn("Math", self.ok("c", "ls").stdout)
        self.assertIn("courses.csv", self.ok("c", "p").stdout)
        self.ok("c", "off", "A")
        self.ok("c", "on", "A")
        self.ok("c", "c", "T")
        source = self.root / "choices.csv"
        source.write_text("block,course\nA,Math\n", encoding="utf-8")
        self.ok("c", "i", str(source))
        self.ok("a", "ls")
        self.ok("a", "s", "club-tue", "Chess", "-R", "Library")
        self.ok("a", "off", "club-tue")
        self.ok("a", "on", "club-tue")
        self.ok("a", "c", "club-tue")
        self.ok("e", "s", "9.18", "-f", "monday", "-S", "20", "-H", "no-afternoon", "-n", "Makeup")
        self.assertIn("2026-09-18", self.ok("e", "ls").stdout)
        self.assertIn("10:00–10:40", self.ok("p", "-d", "0918", "-S", "exceptions", "-L", "list", "-W", "100").stdout)
        self.ok("e", "rm", "0918")
        self.assertIn("1 events", self.ok("v", "-d", "9.18", "-e", "9.18", "Mon", "-i", "A", "-X", "T", "-l").stdout)
        self.ok("s", "n", "copy", "-c", "2026-27-s1", "-N", "Copy")
        self.ok("s", "n", "draft", "-b", "X", "-W", "mon=red", "-z", "+08:00", "-C", "12:00")
        with patch("bcutils.gui.launch") as launch:
            self.ok("g", "-s", "2026-27-s1", "-p", "student")
            launch.assert_called_once_with(self.root, semester_id="2026-27-s1", profile="student")

    def test_short_context_flags_and_week_aliases(self):
        self.init()
        self.assertEqual(self.ok("p", "-w", "0914", "-n", "2", "-N").stdout,
                         self.ok("preview", "--week", "2026-09-14", "--weeks", "2", "--normal").stdout)
        for short, long in [("-t", "--this-week"), ("-x", "--next-week")]:
            self.assertEqual(self.ok("p", short).stdout, self.ok("preview", long).stdout)
        for context in [("-p", "student", "-s", "2026-27-s1"),
                        ("-pstudent", "-s2026-27-s1"), ("-p=student", "-s=2026-27-s1")]:
            output = self.root / "short.ics"
            self.ok(*context, "-d", "0918", "-o", str(output), "-O", "-r", str(self.root))
            self.assertEqual(output.read_bytes().count(b"BEGIN:VEVENT"), 1)

    def test_friendly_errors_give_corrections_without_writes_or_prompts(self):
        for args, hint in [(("-d", "2.30"), "Invalid date"),
                           (("-d", "917"), "MMDD"),
                           (("p", "-d"), "-d 9.18"),
                           (("p", "-d", "0918", "-e", "0918"), "DATE and a RULE"),
                           (("p", "--wek", "0918"), "Did you mean --week?"),
                           (("p", "-d", "9.18:9.14"), "earlier date first"),
                           (("e", "s", "2026.2.30", "-O"), "Invalid date"),
                           (("-d", "0918", "--dayrange", "0919"), "one date selector")]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn(hint, " ".join(result.stderr.split()))
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.workspace.local.exists())

    def test_short_aliases_work_in_actual_module_processes(self):
        self.init()
        for module in ("bcalendar-utils", "bcutils"):
            result = subprocess.run([sys.executable, "-m", module, "-r", str(self.root), "p", "-d", "20260917-20260918", "-e", "2026.9.18", "Mon"], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("2 events", result.stdout)
            self.assertIn("09:40–10:20", result.stdout)

    def test_public_dash_workflow_and_mnemonic_short_forms(self):
        self.ok("-s", "-u", "2026-27-s1")
        self.ok("-c", "-s", "A", "Math", "--room", "Lab")
        self.ok("--courses", "--set", "T", "Study", "--timing", "study-hall")
        self.ok("-a", answers=["Chess", "Robotics"])
        expected = self.ok("preview", "--day", "9.14:9.18", "--clubs", "--cas").stdout
        self.assertEqual(self.ok("-p", "-d", "9.14:9.18", "--clubs", "-c").stdout, expected)
        self.assertEqual(self.ok("--preview", "-w", "0914", "--weeks", "2").stdout,
                         self.ok("preview", "--week", "0914", "--weeks", "2").stdout)
        self.ok("--exceptions", "--set", "0918", "--no-afternoon")
        self.assertIn("2026-09-18", self.ok("--exceptions", "--list").stdout)
        self.ok("--exceptions", "--remove", "0918")
        output = self.root / "public.ics"
        self.ok("--export", "-d", "0918", "-o", str(output))
        self.assertEqual(output.read_bytes().count(b"BEGIN:VEVENT"), 1)
        self.assertNotIn(b"\x1b", output.read_bytes())
        self.assertIn("1 events", self.ok("-v", "-d0918").stdout)

    def test_dash_courses_default_entry_and_values_not_rewritten(self):
        self.ok("--semesters", "--use", "2026-27-s1")
        self.ok("--courses", answers=["Math", *([""] * 9)])
        self.assertIn("A: Math", self.ok("--courses", "--list").stdout)
        self.ok("--courses", "--set", "A", "activities")
        self.assertIn("A: activities", self.ok("--courses", "--list").stdout)
        self.ok("--courses", "--set", "A", "--", "--preview")
        self.assertIn("A: --preview", self.ok("--courses", "--list").stdout)
        self.ok("--profile", "preview", "--courses", "--set", "A", "New profile")
        self.assertIn("A: New profile", self.ok("--courses", "--list", "--profile=preview").stdout)
        self.assertIn("--preview", self.ok("--courses", "--list", "-r" + str(self.root)).stdout)

    def test_all_public_docs_and_help_work_without_setup(self):
        cases = [[], ["--activities"], ["--activities", "--edit"], ["--activities", "--set"],
                 ["--courses"], ["--courses", "--set"], ["--semesters"], ["--semesters", "--new"],
                 ["--exceptions"], ["--exceptions", "--set"], ["--preview"], ["--export"], ["--gui"]]
        for path in cases:
            with self.subTest(path=path):
                compact, detailed = self.ok(*path, "--help"), self.ok(*path, "--docs")
                self.assertIn("Block Calendar Utils", compact.stdout)
                self.assertIn("Block Calendar Utils", detailed.stdout)
                self.assertNotRegex(detailed.stdout, r"python -m bcalendar-utils (?:courses|activities|semester|preview)\b")
                self.assertNotIn("(-P)", detailed.stdout)
                self.assertFalse(self.workspace.local.exists())

    def test_public_collisions_and_conflicting_actions_fail_before_writes(self):
        for flags in [("--preview", "--activities"), ("--courses", "--preview"),
                      ("--activities", "--edit=club-tue"), ("--courses", "--set=A"),
                      ("--day", "0918", "-x"), ("--activities", "-E"),
                      ("--preview", "-d", "0918", "--day", "0919")]:
            with self.subTest(flags=flags):
                result = self.run_cli(*flags)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.workspace.local.exists())

    def test_public_entry_in_actual_module_process(self):
        self.init()
        result = subprocess.run([sys.executable, "-m", "bcalendar-utils", "-r" + str(self.root), "-p", "-d", "20260917:20260918", "-e", "2026.9.18", "Mon"], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 events", result.stdout)
        self.assertNotIn("\x1b", result.stdout)

    def test_dates_are_required_and_invalid_flags_fail_cleanly(self):
        self.init()
        invalid = [(), ("--start", "2026-09-14"), ("--end", "2026-09-15"), ("--week", "no-date"),
            ("--dayrange", "2026-09-14:"), ("--dayrange", "2026-09-15:2026-09-14"),
            ("--dayrange", "2026-09-14:2026-09-15:2026-09-16"),
            ("--dayrange", "2026-09-14", "--weeks", "2"), ("--weeks", "2"),
            ("--week", "2026-09-14", "--weeks", "0"), ("--late", "--normal", "--this-week"),
            ("--dayrange", "2026-09-14", "--end", "2026-09-15")]
        for flags in invalid:
            with self.subTest(flags=flags):
                result = self.run_cli("preview", *flags)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertNotIn("Traceback", result.stderr)

    def test_export_defaults_ignore_saved_gui_choices_without_changing_them(self):
        self.init()
        self.ok("exceptions", "set", "2026-09-17", "--off")
        settings = self.workspace.settings() | dict(late=True, mode="custom", anchor="2020-01-01", end="2020-01-01", schedule_mode="exceptions")
        self.workspace.save_settings(settings)
        before = self.workspace.settings_path.read_bytes()
        result = self.ok("preview", "--dayrange", "2026-09-17:2026-09-18")
        self.assertIn("2 events", result.stdout)
        self.assertIn("15:45–16:25", result.stdout)
        self.assertEqual(self.workspace.settings_path.read_bytes(), before)
        self.assertIn("1 events", self.ok("preview", "--dayrange", "2026-09-17:2026-09-18", "--schedule", "exceptions").stdout)

    def test_exceptions_commands_makeup_late_off_remove_and_validate(self):
        ctx = self.init()
        self.ok("exceptions", "set", "2026-09-18", "--follow", "monday", "--shift", "20", "--note", "Makeup")
        result = self.ok("preview", "--dayrange", "2026-09-18", "--schedule", "exceptions")
        self.assertIn("10:00–10:40", result.stdout)
        self.assertIn("Makeup", self.ok("exceptions", "list").stdout)
        self.ok("exceptions", "set", "2026-09-18", "--late")
        self.assertEqual(ctx.exceptions()[0].time_shift_minutes, 20)
        self.ok("exceptions", "set", "2026-09-18", "--normal")
        self.assertEqual(ctx.exceptions()[0].time_shift_minutes, 0)
        self.ok("exceptions", "set", "2026-09-18", "--off")
        self.assertIn("0 events", self.ok("preview", "--dayrange", "2026-09-18", "--schedule", "exceptions").stdout)
        before = ctx.exceptions_path.read_bytes()
        for flags in [("--follow", "unknown"), ("--off", "--shift", "20"), ("--follow", "monday", "--shift", "999")]:
            self.assertEqual(self.run_cli("exceptions", "set", "2026-09-18", *flags).returncode, 2)
            self.assertEqual(ctx.exceptions_path.read_bytes(), before)
        self.ok("exceptions", "remove", "2026-09-18")
        result = self.run_cli("preview", "--dayrange", "2026-09-18", "--schedule", "exceptions")
        self.assertIn("remove --schedule exceptions", result.stderr)

    def test_course_commands_timing_metadata_and_csv_import(self):
        ctx = self.init()
        self.ok("courses", "set", "A", "数学, advanced", "--room", "Lab 1", "--teacher", "Example")
        self.ok("courses", "set", "A", "Renamed")
        self.assertEqual(ctx.courses()[0].location, "Lab 1")
        self.ok("courses", "disable", "A", "T")
        self.assertFalse(ctx.courses()[0].enabled)
        self.ok("courses", "enable", "A")
        self.ok("courses", "clear", "T")
        before = ctx.courses_path.read_bytes()
        self.assertEqual(self.run_cli("courses", "set", "T", "Study").returncode, 2)
        self.assertEqual(self.run_cli("courses", "set", "unknown", "Math").returncode, 2)
        self.assertEqual(ctx.courses_path.read_bytes(), before)
        self.ok("courses", "set", "T", "Exam prep", "--timing", "toefl")
        self.assertIn("toefl", self.ok("courses", "list").stdout)
        self.assertIn(str(ctx.courses_path), self.ok("courses", "path").stdout)
        source = self.root / "choices.csv"
        source.write_text("block,course\nB,Study Hall\n", encoding="utf-8")
        ctx.courses_path.write_text("mistyped-header\nbad-data\n", encoding="utf-8")
        self.ok("courses", "import", str(source))
        self.assertEqual([c.block for c in ctx.courses() if c.enabled], ["B"])
        self.assertTrue(ctx.courses_path.with_suffix(".csv.bak").exists())

    def test_explicit_course_input_only_and_cancellation_is_atomic(self):
        ctx = self.init()
        self.ok("courses", "edit", "A", "T", answers=["New Math", "Study", "invalid", "study-hall"])
        self.assertEqual(ctx.courses()[0].course, "New Math")
        before = ctx.courses_path.read_bytes()
        result = self.run_cli("courses", "edit", "A", "T", answers=["Unsaved", EOFError()])
        self.assertEqual(result.returncode, 130)
        self.assertEqual(ctx.courses_path.read_bytes(), before)
        self.ok("courses", "edit", "A", answers=["-"])
        self.assertFalse(ctx.courses()[0].enabled)

    def test_empty_export_fails_with_actionable_message(self):
        self.ok("semester", "use", "2026-27-s1")
        result = self.run_cli("--dayrange", "2026-09-14:2026-09-18")
        self.assertEqual(result.returncode, 2)
        self.assertIn("No events", result.stderr)
        self.assertFalse((self.root / "exports").exists())

    def test_inline_exceptions_and_hyphenated_day_range(self):
        ctx = self.init()
        old = ctx.exceptions_path.read_bytes()
        for dayrange in ("2026-09-17:2026-09-18", "2026-09-17-2026-09-18"):
            path = self.root / "inline.ics"
            self.ok("export", "--day-range", dayrange, "--exception", "2026-09-18", "Mon", "--exception", "2026-09-18", "no-afternoon", "-o", str(path), "--overwrite")
            data = path.read_text()
            self.assertEqual(data.count("BEGIN:VEVENT"), 2)
            self.assertIn("DTSTART:20260918T014000Z", data)
        self.assertEqual(ctx.exceptions_path.read_bytes(), old)
        self.assertEqual(self.run_cli("preview", "--day-range", "2026-09-18", "--schedule", "weekdays", "--exception", "2026-09-18", "Mon").returncode, 2)
        self.assertEqual(self.run_cli("preview", "--day-range", "2026-09-18", "--exception", "2026-09-18").returncode, 2)
        self.ok("exceptions", "set", "2026-09-18", "--follow", "monday", "--half-day", "no-afternoon")
        self.assertIn("no-afternoon", self.ok("exceptions", "list").stdout)
        self.ok("exceptions", "set", "2026-09-18", "--no-morning")
        self.assertEqual(ctx.exceptions()[0].half_day, "no-morning")

    def test_named_clubs_default_on_and_cas_opt_in(self):
        self.init()
        self.ok("activities", "set", "club-tue", "Chess", "--room", "Library")
        self.ok("activities", "set", "club-wed", "Robotics")
        self.assertIn("club-tue: Chess", self.ok("activities", "list").stdout)
        self.assertIn("7 events", self.ok("preview", "--week", "2026-09-14").stdout)
        self.assertIn("8 events", self.ok("preview", "--week", "2026-09-14", "--cas", "--clubs").stdout)
        self.ok("activities", "disable", "club-wed")
        self.assertIn("7 events", self.ok("preview", "--week", "2026-09-14", "--cas", "--clubs").stdout)
        self.assertEqual(self.run_cli("activities", "set", "cas", "Custom title").returncode, 2)
        path = self.root / "activities.ics"
        self.ok("--week", "2026-09-14", "--only", "C", "--cas", "--clubs", "-o", str(path))
        data = path.read_text()
        self.assertIn("SUMMARY:CAS", data)
        self.assertIn("SUMMARY:Chess", data)
        self.assertNotIn("DESCRIPTION:", data)

    def test_temporary_block_filters_do_not_edit_courses_or_enable_blank_blocks(self):
        ctx = self.init()
        self.ok("courses", "set", "B", "Biology")
        original = ctx.courses_path.read_bytes()
        for flags, count in [(["--only", "b"], 3), (["--exclude", "a"], 5),
                             (["--only", "A,B", "--exclude", "B"], 3),
                             (["--only", "A", "--only", "T"], 5), (["--only", "C"], 0)]:
            result = self.ok("preview", "--week", "2026-09-14", *flags)
            self.assertIn(f"{count} events", result.stdout)
        output = self.root / "only-b.ics"
        self.ok("export", "--week", "2026-09-14", "--only", "B", "-o", str(output))
        data = output.read_text(encoding="utf-8")
        self.assertEqual(data.count("SUMMARY:Biology"), 3)
        self.assertNotIn("SUMMARY:Example Math", data)
        self.assertEqual(ctx.courses_path.read_bytes(), original)
        for flags in [("--only", "unknown"), ("--exclude", "A,")]:
            self.assertEqual(self.run_cli("preview", "--this-week", *flags).returncode, 2)

    def test_context_options_before_after_and_named_like_commands(self):
        self.ok("--profile", "export", "semester", "use", "2026-27-s1")
        self.ok("--profile", "export", "courses", "set", "A", "Math")
        self.assertIn("3 events", self.ok("--profile=export", "preview", "--week", "2026-09-14", "--root", str(self.root)).stdout)
        self.ok("courses", "--profile", "second", "set", "B", "Science", "--semester", "2026-27-s1")
        self.assertEqual(self.workspace.settings()["profile"], "export")

    def test_no_tk_import_for_terminal_and_real_module_entries(self):
        with patch.dict(sys.modules, {"tkinter": None}):
            self.init()
            self.ok("courses", "set", "A", "数学课程")
            self.ok("preview", "--dayrange", "2026-09-14")
        for entry in ("bcalendar-utils", "bcutils"):
            # Force a restrictive inherited stream encoding to model redirected
            # Windows terminals. The application must correct it itself.
            result = subprocess.run([sys.executable, "-m", entry, "--root", str(self.root), "--dayrange", "2026-09-14", "-o", str(self.root / (entry + ".ics"))], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT, env=os.environ | {"PYTHONIOENCODING": "ascii"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 events", result.stdout)
        preview = subprocess.run([sys.executable, "-m", "bcalendar-utils", "--root", str(self.root), "preview", "--dayrange", "2026-09-14"], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT, env=os.environ | {"PYTHONIOENCODING": "ascii"})
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("数学课程", preview.stdout)

    def test_empty_workspace_can_define_draft_but_not_use_it(self):
        root = self.root / "empty"
        self.ok("semester", "list", "--root", str(root))
        self.ok("semester", "new", "spring", "--blocks", "X,Y,Z", "--root", str(root))
        result = self.run_cli("semester", "use", "spring", "--root", str(root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("timetable is empty", result.stderr)
        self.assertFalse((root / "local").exists())
        self.assertIn("draft", self.ok("semester", "list", "--root", str(root)).stdout)

    def new_custom(self):
        source = self.root / "new-timetable.csv"
        source.write_text("pattern,block,start,end\nred,X,09:00,09:40\nred,Y,09:50,10:30\nblue,Y,13:00,13:40\nblue,Z,13:50,14:30\n", encoding="utf-8")
        self.ok("semester", "new", "spring", "--blocks", "X,Y,Z", "--weekdays", "mon=red,tue=blue,fri=red", "--timetable", str(source))
        return source

    def test_arbitrary_semester_blocks_patterns_and_no_copied_selections(self):
        old = self.init()
        old_bytes = old.courses_path.read_bytes()
        self.new_custom()
        self.assertEqual(self.workspace.settings()["active_semester"], "2026-27-s1")
        self.assertIn("Friday: red", self.ok("semester", "show", "spring").stdout)
        self.ok("semester", "use", "spring")
        ctx = self.workspace.context("student", "spring")
        self.assertEqual([c.block for c in ctx.courses()], ["X", "Y", "Z"])
        self.assertFalse(any(c.enabled for c in ctx.courses()))
        self.ok("courses", "set", "X", "Astronomy")
        self.ok("courses", "set", "Y", "Study Hall")
        preview = self.ok("preview", "--dayrange", "2026-09-14:2026-09-18")
        self.assertIn("5 events", preview.stdout)
        self.ok("exceptions", "set", "2026-09-19", "--follow", "blue")
        self.assertIn("13:00–13:40", self.ok("preview", "--dayrange", "2026-09-19", "--schedule", "exceptions").stdout)
        self.assertEqual(old.courses_path.read_bytes(), old_bytes)

    def test_invalid_definition_import_leaves_no_destination_and_ids_are_stable(self):
        source = self.new_custom()
        folder = self.root / "semesters/spring"
        initial = load_semester(folder)
        table = folder / "timetable.csv"
        table.write_text(table.read_text(encoding="utf-8").replace("09:00", "09:05"), encoding="utf-8")
        self.assertEqual(initial.sessions[0].session_id, load_semester(folder).sessions[0].session_id)
        for blocks in ("X,Y,Z,Missing", "X,Y,Y", "X"):
            result = self.run_cli("semester", "new", "bad", "--blocks", blocks, "--weekdays", "mon=red", "--timetable", str(source))
            self.assertEqual(result.returncode, 2)
            self.assertFalse((self.root / "semesters/bad").exists())
        for mapping in ("mon=red,mon=blue", "bad=red", "mon=missing"):
            self.assertEqual(self.run_cli("semester", "new", "bad", "--blocks", "X,Y,Z", "--weekdays", mapping, "--timetable", str(source)).returncode, 2)
        self.assertFalse(list((self.root / "semesters").glob(".semester-*")))

    def test_copy_is_explicit_and_does_not_copy_exceptions_or_change_active(self):
        self.init()
        source = self.root / "semesters/2026-27-s1/exceptions.csv"
        source.write_text("date,action\n2026-09-18,off\n", encoding="utf-8")
        self.ok("semester", "new", "next", "--copy", "2026-27-s1")
        self.assertEqual(load_semester(self.root / "semesters/next").blocks, tuple("ABCDEFGST") + ("El",))
        self.assertNotIn("2026-09-18", (self.root / "semesters/next/exceptions.csv").read_text())
        self.assertEqual(self.workspace.settings()["active_semester"], "2026-27-s1")
        self.assertEqual(self.run_cli("semester", "new", "next", "--blocks", "X").returncode, 2)
        self.assertEqual(self.run_cli("semester", "new", "invalid", "--copy", "next", "--weekdays", "mon=monday").returncode, 2)

    def test_changed_active_timetable_is_revalidated_before_each_command(self):
        self.init()
        path = self.root / "semesters/2026-27-s1/semester.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["blocks"].append("Missing")
        path.write_text(json.dumps(config), encoding="utf-8")
        result = self.run_cli("--dayrange", "2026-09-14")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing", result.stderr)

    def test_explicit_semester_works_without_activation_and_read_commands_do_not_create_profiles(self):
        result = self.run_cli("courses", "list", "--semester", "2026-27-s1")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.workspace.local.exists())
        self.ok("init", "--semester", "2026-27-s1")
        self.ok("courses", "set", "A", "Math", "--semester", "2026-27-s1")
        self.ok("preview", "--semester", "2026-27-s1", "--dayrange", "2026-09-14")
        self.assertEqual(self.workspace.settings()["active_semester"], "")

    def test_bad_school_exceptions_do_not_create_a_profile_on_activation(self):
        path = self.root / "semesters/2026-27-s1/exceptions.csv"
        path.write_text("date,action\ninvalid,off\n", encoding="utf-8")
        self.assertEqual(self.run_cli("semester", "use", "2026-27-s1").returncode, 2)
        self.assertFalse(self.workspace.local.exists())


if __name__ == "__main__":
    unittest.main()
