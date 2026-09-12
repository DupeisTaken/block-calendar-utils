import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.cli import main
from shbs_calendar.models import Course
from shbs_calendar.storage import digest


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shbs with spaces ")
        self.root = Path(self.temp.name)
        shutil.copytree(DEFAULT_ROOT / "semesters", self.root / "semesters")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, input=""):
        return subprocess.run([sys.executable, "-m", "shbs_calendar", "--root", str(self.root), *args], input=input, capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=DEFAULT_ROOT, env=__import__("os").environ | {"PYTHONIOENCODING": "utf-8"})

    def init(self):
        result = self.run_cli("init", "--profile", "student")
        self.assertEqual(result.returncode, 0, result.stderr)
        ctx = Workspace(self.root).context("student", "2026-27-s1")
        ctx.save_courses([Course("A", "Example Math", enabled=True), Course("T", "Study period", enabled=True, timing_option="study_hall")], digest(ctx.courses_path))
        return ctx

    def test_init_preview_export_and_overwrite(self):
        self.init()
        preview = self.run_cli("preview", "--week", "2026-09-14")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("5 events", preview.stdout)
        output = self.root / "calendar.ics"
        result = self.run_cli("export", "--start", "2026-09-17", "--end", "2026-09-18", "-o", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes().count(b"BEGIN:VEVENT"), 2)
        denied = self.run_cli("export", "--week", "2026-09-14", "-o", str(output))
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(output.read_bytes().count(b"BEGIN:VEVENT"), 2)
        allowed = self.run_cli("export", "--week", "2026-09-14", "-o", str(output), "--overwrite")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_three_weeks_and_late(self):
        self.init()
        result = self.run_cli("preview", "--week", "2026-09-14", "--weeks", "3", "--late")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("15 events", result.stdout)
        self.assertIn("16:05–16:45", result.stdout)

    def test_bad_flags_missing_profile_and_csv_fail_cleanly(self):
        self.assertEqual(self.run_cli("export").returncode, 2)
        ctx = self.init()
        for args in [("preview", "--start", "2026-09-14"), ("preview", "--end", "2026-09-15"), ("preview", "--week", "no-date"), ("preview", "--start", "2026-09-14", "--end", "2026-09-16", "--weeks", "2")]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
        ctx.courses_path.write_text("block,course\nT,Study\n", encoding="utf-8")
        self.assertEqual(self.run_cli("validate").returncode, 2)

    def test_first_run_and_repeat_menu(self):
        # A through El; T has a numbered timing question. All data is synthetic.
        answers = iter(["Math", "", "", "", "", "", "", "", "Study period", "1", "", "0"])
        with patch("builtins.input", side_effect=lambda _: next(answers)), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root)]), 0)
        ctx = Workspace(self.root).context("me", "2026-27-s1")
        self.assertEqual(ctx.courses()[0].course, "Math")
        with patch("builtins.input", return_value="0") as prompt, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root)]), 0)
            self.assertEqual(prompt.call_count, 1)

    def test_eof_cancels_without_hanging(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 130)
        self.assertIn("Cancelled", result.stdout)

    def test_cli_does_not_load_tk(self):
        with patch.dict(sys.modules, {"tkinter": None}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--root", str(self.root), "init"]), 0)


if __name__ == "__main__":
    unittest.main()
