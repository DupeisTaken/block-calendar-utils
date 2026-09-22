"""Timetable edits use temporary roots; exercise persistence through both UIs."""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bcutils.app import Workspace
from bcutils.cli import main
from bcutils.models import CalendarError
from bcutils.semester_editor import SemesterDraft
from bcutils.semesters import create_semester
from bcutils.storage import load_semester, read_json
from tests.fixtures import install_example


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bcutils-editor-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root)

    def cli(self, *args, answers=None, code=0):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), patch("builtins.input", side_effect=answers if answers is not None else AssertionError("Unexpected prompt")):
            try:
                actual = main(["--root", str(self.root), *args])
            except SystemExit as exc:
                actual = exc.code
        self.assertEqual(actual, code, out.getvalue() + err.getvalue())
        return out.getvalue() + err.getvalue()

    def files(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def new(self):
        self.cli("-w", "--semesters", "--new", "mine", "--blocks", "X,Y", "--weekdays", "mon=red")

    def complete(self):
        self.new()
        self.cli("-w", "--semesters", "--edit", "mine", "--session", "red-x", "red", "X", "09:00", "09:40", "--session", "red-y", "red", "Y", "09:50", "10:30")

    def test_empty_startup_and_opt_in_template(self):
        text = self.cli("-i", "--semesters")
        self.assertIn("No semester definitions", text)
        self.assertNotIn("2026-27-s1", text)
        self.assertIn("shbs-example", self.cli("-i", "--semesters", "--templates"))
        self.assertEqual(self.files(), {})
        self.cli("-w", "--semesters", "--new", "example", "--template", "shbs-example")
        self.assertTrue(load_semester(self.root / "semesters/example").sessions)
        self.assertFalse(self.workspace.local.exists())

    def test_complete_blank_workflow_and_export_utc(self):
        self.complete()
        self.cli("-w", "--semesters", "--edit", "mine", "--activity", "red-club", "red", "club-one", "club", "10:40", "11:20", "--timing-option", "X", "long", "red-x", "-", "09:45", "--utc-offset", "+08:00", "--noon-cutoff", "12:00")
        self.cli("-w", "--semesters", "--use", "mine", "-w", "--courses", "--set", "X", "化学", "--timing", "long", "-w", "--activities", "--set", "club-one", "Chess")
        self.cli("-i", "--day", "2026-09-21", "-e", "--last-inspect")
        data = next((self.root / "exports").glob("*.ics")).read_text(encoding="utf-8")
        self.assertIn("SUMMARY:化学", data)
        self.assertIn("DTEND:20260921T014500Z", data)
        self.assertIn("SUMMARY:Chess", data)

    def test_sessions_activities_settings_and_choice_removal(self):
        self.complete()
        self.cli("-w", "--semesters", "--edit", "mine", "-n", "New 名称", "-b", "X,Y,Z", "-s", "red-z", "red", "Z", "11:00", "11:40", "-a", "red-cas", "red", "cas", "cas", "12:00", "13:00", "-t", "Z", "normal", "-", "-", "-")
        semester = load_semester(self.root / "semesters/mine")
        self.assertEqual(semester.name, "New 名称")
        self.assertEqual(semester.timing_options["Z"], {"normal": {}})
        self.cli("-w", "--semesters", "--edit", "mine", "--remove-session", "red-z", "--remove-activity", "red-cas", "--remove-timing", "Z", "normal", "--blocks", "X,Y")
        semester = load_semester(self.root / "semesters/mine")
        self.assertEqual(semester.blocks, ("X", "Y"))
        self.assertFalse(semester.activities)

    def test_invalid_batch_leaves_every_file_unchanged(self):
        self.complete()
        before = self.files()
        for flags in (("--session", "bad", "red", "unknown", "10:00", "11:00"),
                      ("--weekdays", "mon=missing"), ("--remove-session", "red-x"),
                      ("--activity", "red-x", "red", "club", "club", "12:00", "13:00"),
                      ("--session", "x", "red", "X", "25:00", "26:00"),
                      ("--session", "red-x", "red", "X", "10:00", "11:00", "--remove-session", "red-x")):
            with self.subTest(flags=flags):
                self.cli("-w", "--semesters", "--edit", "mine", *flags, code=2)
                self.assertEqual(self.files(), before)

    def test_help_and_malformed_later_action_do_not_write(self):
        self.complete()
        before = self.files()
        self.cli("-w", "--semesters", "--edit", "mine", "--name", "Changed", "-e", "--help")
        self.assertEqual(self.files(), before)
        self.cli("-w", "--semesters", "--edit", "mine", "--name", "Changed", "-w", "--semesters", "--edit", "mine", "--session", "red-x", "red", "X", "12:00", "11:00", code=2)
        self.assertEqual(self.files(), before)
        self.cli("-i", "--semesters", "--edit", "mine", code=2)
        self.assertEqual(self.files(), before)

    def test_interactive_create_modify_remove_and_save(self):
        self.new()
        self.cli("-w", "--semesters", "--edit", "mine", answers=[
            "class", "red-x", "red", "X", "09:00", "09:40",
            "class", "red-y", "red", "Y", "09:50", "10:30",
            "activity", "red-club", "red", "club", "club", "11:00", "12:00",
            "timing", "X", "normal", "-", "-", "-",
            "settings", "My timetable", "", "", "", "",
            "class", "red-x", "", "", "09:05", "09:45",
            "remove-timing", "X", "normal", "remove-activity", "red-club", "save"])
        sem = load_semester(self.root / "semesters/mine")
        self.assertEqual(sem.name, "My timetable")
        self.assertEqual(sem.sessions[0].start.strftime("%H:%M"), "09:05")
        self.assertFalse(sem.activities)

    def test_interactive_cancel_eof_and_stale_save(self):
        self.complete()
        before = self.files()
        for ending in ("cancel", EOFError(), KeyboardInterrupt()):
            self.cli("-w", "--semesters", "--edit", "mine", answers=["settings", "Changed", "", "", "", "", ending], code=130)
            self.assertEqual(self.files(), before)
        draft = SemesterDraft(self.workspace, "mine")
        path = draft.folder / "timetable.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            draft.save()

    def test_existing_profile_protected_and_names_unchanged(self):
        self.complete()
        self.cli("-w", "--semesters", "--use", "mine", "-w", "--courses", "--set", "X", "Physics")
        original = {p: data for p, data in self.files().items() if p.startswith("local")}
        self.cli("-w", "--semesters", "--edit", "mine", "--session", "red-x", "red", "X", "09:05", "09:45")
        self.assertEqual(original, {p: data for p, data in self.files().items() if p.startswith("local")})
        before = self.files()
        result = self.cli("-w", "--semesters", "--edit", "mine", "--blocks", "X", "--remove-session", "red-y", code=2)
        self.assertIn("invalidate profile", result)
        self.assertEqual(before, self.files())
        self.cli("-w", "--semesters", "--edit", "mine", "--timing-option", "X", "long", "red-x", "-", "09:50", code=2)
        self.assertEqual(before, self.files())

    def test_school_exceptions_without_profile_and_personal_precedence(self):
        self.complete()
        self.cli("--semester", "mine", "-w", "--exceptions", "--set", "2026-09-21", "--school", "--off")
        self.assertFalse(self.workspace.local.exists())
        self.cli("-w", "--semesters", "--use", "mine", "-w", "--courses", "--set", "X", "Math")
        self.assertIn("0 events", self.cli("-i", "--day", "2026-09-21", "--schedule", "exceptions"))
        self.cli("-w", "--exceptions", "--set", "2026-09-21", "--follow", "red")
        self.assertIn("Math", self.cli("-i", "--day", "2026-09-21", "--schedule", "exceptions"))
        self.cli("-w", "--exceptions", "--remove", "2026-09-21", "--school")
        self.assertEqual(len(self.workspace.context("me", "mine").exceptions()), 1)

    @unittest.skipUnless(os.name == "nt", "Windows CMD integration")
    def test_real_cmd_batch_and_redirected_interactive_entry(self):
        # Use the documented CMD continuation syntax with a synthetic data root.
        from bcutils.app import DEFAULT_ROOT
        command = f'"{sys.executable}" -B -m bcutils --root "{self.root}"'
        batch = self.root / "workflow.cmd"
        batch.write_text(
            "@echo off\n" + command + " -w --semesters --new mine --blocks X,Y --weekdays mon=red\n"
            "if errorlevel 1 exit /b 1\n" + command + " -w --semesters --edit mine ^\n"
            "  --session red-x red X 09:00 09:40 ^\n"
            "  --session red-y red Y 09:50 10:30 ^\n"
            "  --activity red-club red club-one club 10:40 11:20\n"
            "if errorlevel 1 exit /b 1\n" + command + " -i --semesters --show mine\n",
            encoding="utf-8")
        result = subprocess.run(["cmd.exe", "/d", "/c", str(batch)], cwd=DEFAULT_ROOT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20,
                                env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("09:00", result.stdout)
        result = subprocess.run([sys.executable, "-B", "-m", "bcalendar-utils", "--root", str(self.root), "-w", "--semesters", "--edit", "mine"], cwd=DEFAULT_ROOT,
                                input="settings\n学校\n\n\n\n\nsave\n", capture_output=True, text=True, encoding="utf-8", timeout=20,
                                env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b", result.stdout)
        self.assertEqual(load_semester(self.root / "semesters/mine").name, "学校")
        self.assertIn("red-x", result.stdout)

    def test_implicit_ids_are_preserved_when_reordered(self):
        self.new()
        table = self.root / "semesters/mine/timetable.csv"
        table.write_text("pattern,block,start,end\nred,X,09:00,09:40\nred,X,10:00,10:40\nred,Y,11:00,11:40\n", encoding="utf-8")
        original = load_semester(table.parent)
        draft = SemesterDraft(self.workspace, "mine")
        draft.sessions.reverse()
        draft.save()
        updated = load_semester(table.parent)
        self.assertEqual({s.start: s.session_id for s in original.sessions}, {s.start: s.session_id for s in updated.sessions})

    def test_failed_second_file_save_rolls_back_original(self):
        self.complete()
        draft = SemesterDraft(self.workspace, "mine")
        old_config = (draft.folder / "semester.json").read_bytes()
        old_table = (draft.folder / "timetable.csv").read_bytes()
        draft.update_settings(name="Changed")
        draft.put_session(("red-x", "red", "X", "09:05", "09:45"))
        from bcutils.storage import atomic_write
        def fail(path, data, **kwargs):
            if path == draft.folder / "timetable.csv":
                raise CalendarError("Simulated disk failure")
            return atomic_write(path, data, **kwargs)
        with patch("bcutils.semester_editor.atomic_write", side_effect=fail), self.assertRaisesRegex(CalendarError, "disk failure"):
            draft.save()
        self.assertEqual((draft.folder / "semester.json").read_bytes(), old_config)
        self.assertEqual((draft.folder / "timetable.csv").read_bytes(), old_table)


@unittest.skipUnless(os.environ.get("BCUTILS_GUI_TESTS", os.environ.get("SHBS_GUI_TESTS")) == "1", "Enable native Tk tests")
class EditorGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.window = tk.Tk()
        cls.window.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.window.destroy()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self):
        for child in self.window.winfo_children():
            child.destroy()
        self.temp.cleanup()

    def editor(self, sid=None, **kwargs):
        from bcutils.semester_gui import SemesterEditor
        return SemesterEditor(self.window, self.workspace, sid, **kwargs)

    def fill(self, editor, key, values):
        for variable, value in zip(editor.tables[key]["variables"].values(), values):
            variable.set(value)
        editor.apply_row(key)

    def test_create_complete_and_edit_without_raw_files(self):
        editor = self.editor()
        editor.id_var.set("mine")
        editor.settings_vars["name"].set("My timetable")
        editor.settings_vars["blocks"].set("X")
        editor.settings_vars["weekdays"].set("mon=red")
        editor.save()
        editor = self.window.editor
        self.fill(editor, "classes", ("red-x", "red", "X", "09:00", "09:40"))
        self.fill(editor, "activities", ("red-club", "red", "club", "club", "10:00", "11:00"))
        self.fill(editor, "timing", ("X", "long", "red-x", "", "09:50"))
        editor.save()
        sem = load_semester(self.root / "semesters/mine")
        self.assertEqual(sem.timing_options["X"]["long"]["red-x"], {"end": "09:50"})
        self.assertEqual(sem.activities, {"club": "club"})
        self.assertFalse(self.workspace.local.exists())

    def test_template_is_explicit_and_does_not_activate(self):
        editor = self.editor()
        self.assertEqual(editor.template_var.get(), "Start blank")
        editor.id_var.set("sample")
        editor.template_var.set("shbs-example")
        editor.choose_template()
        editor.save()
        self.assertTrue(load_semester(self.root / "semesters/sample").sessions)
        self.assertFalse(self.workspace.local.exists())

    def test_unapplied_invalid_stale_and_cancelled_edits(self):
        install_example(self.root)
        editor = self.editor("2026-27-s1")
        table = editor.tables["classes"]
        table["variables"]["start"].set("09:00")
        with self.assertRaisesRegex(CalendarError, "Apply each"):
            editor.save()
        with patch("bcutils.semester_gui.messagebox.askyesno", return_value=True):
            editor.new_row("classes")
        self.fill(editor, "classes", ("bad", "monday", "unknown", "09:00", "09:40"))
        before = (editor.draft.folder / "timetable.csv").read_bytes()
        with self.assertRaises(CalendarError):
            editor.save()
        self.assertEqual(before, (editor.draft.folder / "timetable.csv").read_bytes())
        with patch("bcutils.semester_gui.messagebox.askyesno", return_value=True):
            editor.reload()
        path = editor.draft.folder / "timetable.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            editor.save()
        with patch("bcutils.semester_gui.messagebox.askyesno", return_value=True):
            editor.reload()
        editor.save()

    def test_main_app_refresh_and_school_exception_source(self):
        from bcutils.gui import CalendarApp
        install_example(self.root)
        self.workspace.use_semester("2026-27-s1")
        app = CalendarApp(self.window, self.workspace)
        app.exc_date.set("2026-09-21")
        app.exc_action.set("off")
        app.exc_source.set("School")
        app.save_exception()
        self.assertEqual(len(app.school_exception_items), 1)
        self.assertEqual(app.ctx.exceptions(), [])
        app.remove_exception()
        self.assertEqual(app.school_exception_items, [])
        # Capture the callback without opening a second native window.
        with patch("bcutils.semester_gui.open_editor") as opened:
            app.edit_timetable()
        callback = opened.call_args.args[3]
        draft = SemesterDraft(self.workspace, "2026-27-s1")
        draft.put_session(("mon-a", "monday", "A", "09:45", "10:25"))
        draft.save()
        callback("2026-27-s1")
        self.assertEqual(next(s for s in app.ctx.semester.sessions if s.session_id == "mon-a").start.strftime("%H:%M"), "09:45")
