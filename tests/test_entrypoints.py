"""Exercise public launchers and a moved checkout using only synthetic profiles."""

from datetime import date
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bcutils.app import DEFAULT_ROOT
from bcutils.ical import calendar_bytes
from bcutils.models import Course
from bcutils.schedule import build_preview
from bcutils.storage import load_semester


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bcutils relocation ")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.checkout = self.parent / "original checkout"
        # Copy executable source and school definitions, never real local data.
        shutil.copytree(DEFAULT_ROOT / "bcutils", self.checkout / "bcutils",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(DEFAULT_ROOT / "semesters", self.checkout / "semesters")
        for name in ("bcalendar-utils.py", "bcutils-gui.pyw"):
            shutil.copy2(DEFAULT_ROOT / name, self.checkout / name)

    def run_module(self, module, *args):
        result = subprocess.run(
            [sys.executable, "-B", "-m", module, *args], cwd=self.checkout,
            input="", capture_output=True, text=True, encoding="utf-8", timeout=15,
            env=os.environ | {"PYTHONIOENCODING": "utf-8", "NO_COLOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout

    def profile_snapshot(self):
        return {p.relative_to(self.checkout): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.checkout / "local").rglob("*") if p.is_file()}

    def test_both_names_show_help_without_writes_or_prompts(self):
        for flag in ("--help", "--docs"):
            with self.subTest(flag=flag):
                long = self.run_module("bcalendar-utils", flag)
                short = self.run_module("bcutils", flag)
                self.assertEqual(long, short)
                self.assertIn("Block Calendar Utils", long)
                self.assertIn("python -m bcalendar-utils", long)
                self.assertNotIn("\x1b", long)
        self.assertFalse((self.checkout / "local").exists())
        self.assertFalse((self.checkout / "exports").exists())

    def test_moving_checkout_preserves_profiles_and_export_identity(self):
        self.run_module("bcalendar-utils", "-w", "--semesters", "--use", "2026-27-s1",
                        "-w", "--courses", "--set", "A", "数学 seminar")
        self.run_module("bcalendar-utils", "-e", "--day", "2026-09-14")
        original_export = next((self.checkout / "exports").glob("*.ics")).read_bytes()
        profiles = self.profile_snapshot()
        self.assertTrue(profiles)
        moved = self.parent / "block-calendar-utils"
        self.checkout.rename(moved)
        self.checkout = moved
        self.assertIn("数学 seminar", self.run_module("bcutils", "-i", "--courses"))
        output = self.checkout / "exports/after-move.ics"
        self.run_module("bcutils", "-e", "--day", "2026-09-14", "--output", str(output))
        # DTSTAMP is the export time; all other serialized fields must survive
        # both the directory move and a switch between the public module names.
        stable_lines = lambda data: [line for line in data.splitlines()
                                     if not line.startswith(b"DTSTAMP:")]
        self.assertEqual(stable_lines(original_export), stable_lines(output.read_bytes()))
        self.assertEqual(profiles, self.profile_snapshot())
        self.assertFalse((self.parent / "local").exists())

    def test_script_uses_its_checkout_from_another_working_directory(self):
        result = subprocess.run(
            [sys.executable, "-B", str(self.checkout / "bcalendar-utils.py"),
             "-i", "--semesters"], cwd=self.parent, input="", capture_output=True,
            text=True, encoding="utf-8", timeout=15,
            env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2026-27-s1", result.stdout)
        self.assertFalse((self.checkout / "local").exists())
        self.assertFalse((self.parent / "local").exists())

    def test_desktop_launcher_delegates_to_shared_gui(self):
        with patch("bcutils.gui.launch") as launch:
            runpy.run_path(str(self.checkout / "bcutils-gui.pyw"), run_name="__main__")
        launch.assert_called_once_with()

    def test_rename_preserves_preexisting_uid_and_updates_calendar_branding(self):
        semester = load_semester(self.checkout / "semesters/2026-27-s1")
        preview = build_preview(
            semester, [Course("A", "Math", enabled=True)],
            "472b895a-d1ac-4e5b-8203-02e2aa01d607",
            date(2026, 9, 14), date(2026, 9, 14),
        )
        # Recorded from the old application before renaming its package.
        self.assertEqual([event.uid for event in preview.events],
                         ["161e79c4-8c03-59bf-9319-c52b61c7220d@shbs-calendar.local"])
        data = calendar_bytes(preview.events)
        self.assertIn(b"PRODID:-//Block Calendar Utils//", data)
        self.assertIn(b"X-WR-CALNAME:Block calendar", data)
