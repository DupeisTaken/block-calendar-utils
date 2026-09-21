"""Help stays readable in terminals, narrow windows and redirected output."""

from contextlib import nullcontext, redirect_stdout
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bcutils.cli import main, parser, help_parser
from bcutils.help_style import SpacedHelpFormatter, style_help, windows_vt, write_help, emit, ask, error_message


class TerminalStream(io.StringIO):
    def isatty(self):
        return True

    def fileno(self):
        return 1


class HelpStyleTests(unittest.TestCase):
    def test_last_inspection_help_scopes_the_l_shortcut(self):
        from bcutils.cli_interface import render_help
        cli = parser()
        export = render_help(help_parser(cli, ["export"]), detailed=True)
        preview = render_help(help_parser(cli, ["preview"]), detailed=True)
        self.assertIn("--last-inspect / -l", export)
        self.assertNotIn("--late / -l", export)
        self.assertIn("--late / -l", preview)
        self.assertNotIn("--last-inspect", preview)

    def test_exception_entry_help_exposes_time_filters_without_writes(self):
        # Both entry routes must explain how to save filters without requiring
        # a selected semester, opening prompts or creating a profile.
        with tempfile.TemporaryDirectory() as folder:
            for route in (["-w", "--exceptions"], ["-w", "--exceptions", "--help"],
                          ["-i", "--exceptions", "--help"], ["-w", "--exceptions", "--docs"]):
                output = io.StringIO()
                with self.subTest(route=route), redirect_stdout(output), patch("builtins.input", side_effect=AssertionError("Help must not prompt")):
                    try:
                        self.assertEqual(main(["--root", folder, *route]), 0)
                    except SystemExit as exc:
                        self.assertEqual(exc.code, 0)
                    text = output.getvalue()
                    for flag in ("--blank-hours", "--morning-cutoff", "--afternoon-cutoff", "--overlap", "--schedule exceptions"):
                        self.assertIn(flag, text)
                    self.assertNotIn("\x1b", text)
                    self.assertEqual(list(Path(folder).iterdir()), [])

    def test_help_exposes_required_arguments_choices_and_replacement(self):
        from bcutils.cli_interface import render_help
        cli = parser()
        for path, expected in [
            (["courses", "set"], "--courses --set BLOCK NAME [options]"),
            (["courses", "import"], "--courses --import FILE [options]"),
            (["activities", "edit"], "--activities --edit [IDS ...] [options]"),
            (["semester", "show"], "--semesters --show ID [options]"),
            (["exceptions", "remove"], "--exceptions --remove DATE [options]"),
        ]:
            with self.subTest(path=path):
                self.assertIn(expected, " ".join(help_parser(cli, path).format_help().split()))
        # A longer executable name may wrap the usage line; the complete choice
        # must remain visible regardless of the terminal's line breaks.
        new_semester = " ".join(help_parser(cli, ["semester", "new"]).format_help().split())
        self.assertIn("--blocks BLOCKS | --copy ID", new_semester)
        saved = " ".join(help_parser(cli, ["exceptions", "set"]).format_help().split())
        self.assertIn("--blank-hours HH:MM-HH:MM", saved)
        self.assertIn("--overlap {trim,remove}", saved)
        self.assertIn("--half-day {no-morning,no-afternoon}", saved)
        preview = render_help(help_parser(cli, ["preview"]), detailed=True)
        self.assertIn("--layout {columns,list}", preview)
        self.assertIn("--schedule {weekdays,exceptions} / -s", preview)
        self.assertNotIn("--overwrite", preview)
        for detailed in (False, True):
            export = render_help(help_parser(cli, ["export"]), detailed=detailed)
            self.assertIn("--overwrite", export)
            self.assertIn("same export command", " ".join(export.split()))
            self.assertIn("Export a reviewed preview: --last-inspect / -l.", export)
            self.assertIn("Or supply dates:", export)
            self.assertNotIn("--layout", export)
        root_docs = render_help(cli, detailed=True)
        self.assertIn("Open the desktop interface", root_docs)
        self.assertNotIn("Open gui options", root_docs)

    def test_help_is_compact_and_docs_expand_without_bare_commands(self):
        from bcutils.cli_interface import render_help
        cli = parser()
        for topics in (["activities"], ["courses", "set"], ["export"], ["exceptions", "set"]):
            with self.subTest(topics=topics):
                target = help_parser(cli, topics)
                compact, detailed = target.format_help(), render_help(target, detailed=True)
                self.assertIn("\n\n", compact)
                self.assertIn("--docs", compact)
                self.assertIn("--root", detailed)
                self.assertNotIn("\x1b", compact)
                self.assertNotRegex(compact, r"python -m bcalendar-utils [a-z]")
                self.assertGreater(len(detailed), len(compact))
        activities = help_parser(cli, ["activities"]).format_help()
        self.assertIn('--activities --set club-tue "Chess Club"', activities)
        self.assertLess(len(activities.splitlines()), 20)

    def test_styling_preserves_text_alignment_and_has_one_accent(self):
        for topics in ([], ["activities"], ["preview"], ["courses", "set"]):
            plain = help_parser(parser(), topics).format_help()
            styled = style_help(plain)
            self.assertEqual(re.sub(r"\x1b\[[0-9;]*m", "", styled), plain)
            self.assertIn("\x1b[36m", styled)
            self.assertLessEqual(set(re.findall(r"\x1b\[([0-9;]*)m", styled)), {"0", "1", "36"})
        self.assertIn("bcalendar-utils", style_help("python -m bcalendar-utils -d 2026-09-18\n"))
        self.assertIn("2026-09-18", style_help("python -m bcalendar-utils -d 2026-09-18\n"))
        self.assertNotIn("\x1b[1m", style_help("Use -d 9.14:9.18 for a range.\n"))

    def test_redirected_or_opted_out_output_is_plain(self):
        for stream, env in [(io.StringIO(), {}), (TerminalStream(), {"NO_COLOR": ""}), (TerminalStream(), {"TERM": "dumb"})]:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with patch("bcutils.help_style.windows_vt", side_effect=AssertionError("Console must not be touched")):
                    write_help("options:\n  -h, --help\n", stream)
                self.assertNotIn("\x1b", stream.getvalue())

    def test_help_routes_color_only_at_output_boundary(self):
        for argv in (["-h"], ["-a", "-h"], ["help", "a", "set"], ["help"]):
            with self.subTest(argv=argv), patch.dict(os.environ, {}, clear=True), patch("bcutils.help_style.windows_vt", side_effect=lambda _: nullcontext(True)):
                output = TerminalStream()
                with redirect_stdout(output):
                    try:
                        self.assertEqual(main(argv), 0)
                    except SystemExit as exc:
                        self.assertEqual(exc.code, 0)
                self.assertIn("\x1b[1m", output.getvalue())
                self.assertIn("\x1b[36m", output.getvalue())

    def test_wrapping_preserves_paragraphs_in_narrow_help(self):
        formatter = SpacedHelpFormatter("test", width=45)
        text = formatter._fill_text("Date formats:\nUse a complete date or a month and day in the current year.\n\nExamples:\n  -d 9.14:9.18", 40, "")
        self.assertIn("\n\nExamples:\n  -d", text)
        self.assertTrue(all(len(line) <= 40 for line in text.splitlines()))

    def test_shared_emphasis_for_prompts_previews_results_and_errors(self):
        samples = ["Activities\n  club-tue · tuesday 15:45–16:35\n", "  Club name [unused]: ",
                   "2026-09-18 Friday\n  08:10–09:30 Mathematics\n",
                   "Saved club names:\n  activities.csv\n  Include with --clubs\n"]
        for env in ({}, {"NO_COLOR": ""}):
            output = TerminalStream()
            with patch.dict(os.environ, env, clear=True), patch("bcutils.help_style.windows_vt", side_effect=lambda _: nullcontext(True)), redirect_stdout(output):
                for sample in samples:
                    emit(sample, end="")
                with patch("builtins.input", return_value="Chess") as read:
                    self.assertEqual(ask("  15:45 · Club name: "), "Chess")
                error_message("Missing date.\nTry --day 9.18.", "--preview --docs", output)
            text = output.getvalue()
            plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
            self.assertTrue(plain.startswith("".join(samples)))
            self.assertIn("Error: Missing date.\n\n  Try --day 9.18.\n\n  More: --preview --docs", plain)
            if env:
                self.assertNotIn("\x1b", text + read.call_args.args[0])
            else:
                for value in ("--clubs", "2026-09-18", "15:45", "--day"):
                    self.assertIn(f"\x1b[36m{value}\x1b[0m", text)
                self.assertIn("\x1b[36m15:45\x1b[0m", read.call_args.args[0])
                self.assertLessEqual(set(re.findall(r"\x1b\[([0-9;]*)m", text)), {"0", "1", "36"})

    @unittest.skipUnless(os.name == "nt", "Windows console API")
    def test_windows_mode_is_restored_and_failures_fall_back(self):
        with patch("ctypes.WinDLL") as library, patch("msvcrt.get_osfhandle", return_value=123):
            kernel = library.return_value
            def read_mode(handle, pointer):
                pointer._obj.value = 3
                return True
            kernel.GetConsoleMode.side_effect = read_mode
            kernel.SetConsoleMode.return_value = True
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                with windows_vt(TerminalStream()) as enabled:
                    self.assertTrue(enabled)
                    raise RuntimeError("write failed")
            self.assertEqual([call.args for call in kernel.SetConsoleMode.call_args_list], [(123, 7), (123, 3)])
            kernel.SetConsoleMode.reset_mock()
            kernel.SetConsoleMode.return_value = False
            with windows_vt(TerminalStream()) as enabled:
                self.assertFalse(enabled)
            kernel.SetConsoleMode.assert_called_once_with(123, 7)
