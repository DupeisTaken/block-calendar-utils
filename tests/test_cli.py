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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.cli import main
from shbs_calendar.storage import load_semester


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shbs with spaces ")
        self.root = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", self.root / "semesters")
        self.workspace = Workspace(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, answers=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), patch("builtins.input", side_effect=answers if answers is not None else AssertionError("Unexpected input prompt")):
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

    def test_no_arguments_is_help_without_files_or_questions(self):
        result = self.ok()
        self.assertIn("--dayrange", result.stdout)
        self.assertFalse(self.workspace.local.exists())

    def test_setup_required_and_legacy_settings_do_not_silently_activate(self):
        self.workspace.save_settings({"semester": "2026-27-s1"})
        for args in [("--this-week",), ("courses", "edit"), ("init",)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertIn("semester use", result.stderr)
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
        self.assertIn("at least one exception", result.stderr)

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
        self.assertIn("No classes", result.stderr)
        self.assertFalse((self.root / "exports").exists())

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
        for entry in ("shbs-calendar", "shbs_calendar"):
            # Force a restrictive inherited stream encoding to model redirected
            # Windows terminals. The application must correct it itself.
            result = subprocess.run([sys.executable, "-m", entry, "--root", str(self.root), "--dayrange", "2026-09-14", "-o", str(self.root / (entry + ".ics"))], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT, env=os.environ | {"PYTHONIOENCODING": "ascii"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1 events", result.stdout)
        preview = subprocess.run([sys.executable, "-m", "shbs-calendar", "--root", str(self.root), "preview", "--dayrange", "2026-09-14"], capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT, env=os.environ | {"PYTHONIOENCODING": "ascii"})
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
