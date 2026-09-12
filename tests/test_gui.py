"""Opt-in native Tk controller tests, using just one hidden window at a time."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.ical import calendar_bytes
from shbs_calendar.models import CalendarError


@unittest.skipUnless(os.environ.get("SHBS_GUI_TESTS") == "1", "Set SHBS_GUI_TESTS=1 for native Tk tests")
class GUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        from shbs_calendar.gui import CalendarApp
        self.temp = tempfile.TemporaryDirectory()
        root_path = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", root_path / "semesters")
        self.workspace = Workspace(root_path)
        self.app = CalendarApp(self.root, self.workspace)
        self.app.mode_var.set("Choose a week")
        self.app.anchor_var.set("2026-09-14")
        self.app.update_date_fields()

    def tearDown(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.temp.cleanup()

    def fields(self, block):
        return dict(self.app.course_vars)[block]

    def test_save_preview_and_export_match_shared_engine(self):
        self.fields("A")["course"].set("Advanced mathematics, 示例")
        self.fields("T")["course"].set("Study period")
        self.fields("T")["timing_option"].set("Study hall")
        preview = self.app.preview()
        self.assertEqual(len(preview.events), 5)
        self.assertEqual(self.app.ctx.courses()[8].timing_option, "study_hall")
        path = self.workspace.root / "export.ics"
        with patch("shbs_calendar.gui.filedialog.asksaveasfilename", return_value=str(path)):
            self.app.export()
        self.assertEqual(path.read_bytes().count(b"BEGIN:VEVENT"), 5)
        shared = self.app.ctx.preview(self.app.range_settings())
        self.assertEqual(preview.events, shared.events)
        self.assertEqual(calendar_bytes(preview.events), calendar_bytes(shared.events))

    def test_both_t_choices_late(self):
        self.fields("T")["course"].set("Course name")
        self.fields("T")["timing_option"].set("TOEFL lesson")
        self.app.late_var.set(True)
        result = self.app.preview()
        self.assertEqual(result.events[-1].end.strftime("%H:%M"), "17:25")
        self.fields("T")["timing_option"].set("Study hall")
        self.assertEqual(self.app.preview().events[-1].end.strftime("%H:%M"), "16:45")

    def test_external_edit_conflict_and_reload(self):
        self.fields("A")["course"].set("Unsaved edit")
        self.app.ctx.courses_path.write_text("block,course\nA,External\n", encoding="utf-8")
        with self.assertRaisesRegex(CalendarError, "changed on disk"):
            self.app.save()
        with patch("shbs_calendar.gui.messagebox.askyesno", return_value=True):
            self.app.reload()
        self.assertEqual(self.fields("A")["course"].get(), "External")

    def test_exception_save_remove_and_makeup_preview(self):
        self.fields("A")["course"].set("Math")
        self.app.exc_date.set("2026-09-18")
        self.app.exc_pattern.set("monday")
        self.app.save_exception()
        result = self.app.preview()
        friday = result.events[-1]
        self.assertEqual(friday.start.strftime("%H:%M"), "09:40")
        self.app.remove_exception()
        self.assertEqual(self.app.preview().events[-1].start.strftime("%H:%M"), "10:30")

    def test_invalid_dates_and_save_cancellation(self):
        self.app.anchor_var.set("invalid")
        with self.assertRaises(CalendarError):
            self.app.preview()
        self.app.anchor_var.set("2026-09-14")
        with patch("shbs_calendar.gui.filedialog.asksaveasfilename", return_value=""):
            self.app.export()
        self.assertFalse((self.workspace.root / "exports").exists())
        self.fields("A")["course"].set("Unsaved")
        with patch("shbs_calendar.gui.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.keep_edits())

    def test_export_error_is_reported(self):
        self.fields("A")["course"].set("Math")
        with patch("shbs_calendar.gui.filedialog.asksaveasfilename", return_value=str(self.workspace.root / "test.ics")), patch.object(self.app.ctx, "export", side_effect=CalendarError("disk full")), patch("shbs_calendar.gui.messagebox.showerror") as error:
            self.app.run(self.app.export)
            self.assertIn("disk full", error.call_args.args[1])

    def test_profile_switch_failure_and_pending_selection(self):
        self.app.profile_var.set("../invalid")
        with self.assertRaises(CalendarError):
            self.app.switch()
        self.assertEqual(self.app.profile_var.get(), "me")
        self.app.profile_var.set("another")
        with self.assertRaisesRegex(CalendarError, "Switch"):
            self.app.preview()
        self.app.switch()
        self.assertEqual(self.app.ctx.profile, "another")
        self.assertFalse(any(c.enabled for c in self.app.ctx.courses()))


if __name__ == "__main__":
    unittest.main()
