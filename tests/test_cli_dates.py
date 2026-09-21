"""Terminal syntax contracts independent of the wall clock and scheduling data."""

import argparse
import unittest
from datetime import date

from shbs_calendar.cli import command_settings, parser
from shbs_calendar.cli_dates import parse_cli_date, parse_cli_range
from shbs_calendar.models import CalendarError
from shbs_calendar.storage import parse_date


TODAY = date(2026, 9, 18)


class CLIDateTests(unittest.TestCase):
    def test_explicit_and_yearless_date_spellings(self):
        for text in ("2026-09-18", "2026.9.18", "2026/09/18", "20260918", "9-18", "9.18", "09/18", "0918", " 9.18 "):
            with self.subTest(text=text):
                self.assertEqual(parse_cli_date(text, today=TODAY), TODAY)
                self.assertEqual(parse_cli_range(text, today=TODAY), (TODAY, TODAY))
        self.assertEqual(parse_cli_date("1.2", today=TODAY), date(2026, 1, 2))

    def test_equivalent_range_shapes_and_mixed_endpoint_formats(self):
        for text in ("2026-09-14-2026-09-18", "2026.9.14:2026/9/18", "20260914-20260918", "9.14-9.18", "9-14-9-18", "0914:0918", "0914..0918", "9/14 to 9/18", "9.14 TO 9.18", "9.14 – 9.18", " 9.14 : 0918 ", "20260914:9.18"):
            with self.subTest(text=text):
                self.assertEqual(parse_cli_range(text, today=TODAY), (date(2026, 9, 14), TODAY))

    def test_current_year_is_literal_without_rollover_or_inheritance(self):
        self.assertEqual(parse_cli_date("1.2", today=date(2026, 12, 31)), date(2026, 1, 2))
        self.assertEqual(parse_cli_date("12.31", today=date(2027, 1, 1)), date(2027, 12, 31))
        self.assertEqual(parse_cli_range("2025.12.31:1.2", today=TODAY), (date(2025, 12, 31), date(2026, 1, 2)))
        with self.assertRaisesRegex(CalendarError, "New Year"):
            parse_cli_range("12.31:1.2", today=TODAY)
        self.assertEqual(parse_cli_range("2026.12.31:2027.1.2", today=TODAY), (date(2026, 12, 31), date(2027, 1, 2)))

    def test_leap_year_and_calendar_boundaries(self):
        self.assertEqual(parse_cli_date("0229", today=date(2028, 1, 1)), date(2028, 2, 29))
        for text in ("2.29", "2026-2-29", "20260229"):
            with self.subTest(text=text), self.assertRaisesRegex(CalendarError, "Invalid date"):
                parse_cli_range(text, today=TODAY)
        self.assertEqual(parse_cli_date("00010101"), date.min)
        self.assertEqual(parse_cli_date("9999.12.31"), date.max)

    def test_invalid_and_ambiguous_input_has_examples(self):
        for text in ("", "917", "260918", "18.9", "09.18.26", "2026.09/18", "2026-13-01", "00000101", "9.18:", ":9.18", "9.14:9.16:9.18", "9.14-18", "2026091420260918", "2026-02-30", "9.14:2026-02-30"):
            with self.subTest(text=text), self.assertRaisesRegex(CalendarError, "YYYY-MM-DD"):
                parse_cli_range(text, today=TODAY)
        with self.assertRaisesRegex(CalendarError, "before start"):
            parse_cli_range("9.18:9.14", today=TODAY)

    def test_short_and_long_flags_normalize_to_existing_settings(self):
        cli = parser()
        for flag in ("-d", "--day", "--day-range", "--dayrange"):
            for text, mode, last in [("0914", "day", "2026-09-14"), ("9.14-9.18", "custom", "2026-09-18")]:
                with self.subTest(flag=flag, text=text):
                    settings = command_settings(cli.parse_args(["preview", flag, text, "-e", "9.14", "Mon"]), today=TODAY)
                    self.assertEqual((settings["mode"], settings["anchor"], settings["end"]), (mode, "2026-09-14", last))
                    self.assertEqual(settings["inline_exceptions"], [("2026-09-14", "Mon")])
        settings = command_settings(cli.parse_args(["preview", "-w", "0914", "-n", "3"]), today=TODAY)
        self.assertEqual((settings["mode"], settings["anchor"], settings["weeks"]), ("week", "2026-09-14", 3))

    def test_persisted_date_parser_remains_strict(self):
        self.assertEqual(parse_date("2026-09-18"), TODAY)
        for text in ("9.18", "20260918", "2026/09/18", "2026-9-18", "0918"):
            with self.subTest(text=text), self.assertRaises(CalendarError):
                parse_date(text)

    def test_public_shortcuts_use_initials_and_collisions_stay_long(self):
        from shbs_calendar.cli_interface import COMMON, EXPORT_OPTIONS, ROOT_COMMANDS, GROUP_ACTIONS, DETAIL_OPTIONS
        mappings = [COMMON, EXPORT_OPTIONS, *DETAIL_OPTIONS.values()]
        mappings += [{"--" + name: short for name, short in group.items()} for group in GROUP_ACTIONS.values()]
        mappings.append({flag: short for flag, (_, short) in ROOT_COMMANDS.items()})
        for mapping in mappings:
            used = set()
            for long, short in mapping.items():
                if short is not None:
                    self.assertEqual(short, "-" + long[2])
                    self.assertNotIn(short, used)
                    used.add(short)
        for flag in ("--weeks", "--clubs", "--exclude", "--normal", "--only", "--late"):
            self.assertIsNone(EXPORT_OPTIONS[flag])
        self.assertEqual(EXPORT_OPTIONS["--last-inspect"], "-l")
        self.assertIsNone(COMMON["--profile"])

    def test_public_shortcut_scopes_resolve_to_the_same_handlers(self):
        from shbs_calendar.cli_interface import normalize
        cli = parser()
        # Exercise overlapping initials across action scopes, and options whose
        # public initial differs from the old parser's private compatibility alias.
        cases = [
            (["--semesters", "--new", "spring", "--blocks", "X,Y", "--name", "Spring", "--weekdays", "mon=red", "--utc-offset", "+08:00"],
             ["-s", "-n", "spring", "-b", "X,Y", "-n", "Spring", "-w", "mon=red", "-u", "+08:00"]),
            (["--preview", "--next-week", "--weeks", "2", "--schedule", "exceptions", "--exception", "0918", "Mon", "--cas"],
             ["-p", "-n", "--weeks", "2", "-s", "exceptions", "-e", "0918", "Mon", "-c"]),
            (["--exceptions", "--set", "0918", "--follow", "monday", "--shift", "-20", "--note", "Late"],
             ["--exceptions", "-s", "0918", "-f", "monday", "-s", "-20", "--note", "Late"]),
            (["--exceptions", "--set", "0918", "--normal"], ["--exceptions", "-s", "0918", "-n"]),
            (["--courses", "--disable", "A"], ["-c", "-d", "A"]),
            (["--activities", "--edit", "club-tue"], ["-a", "-e", "club-tue"]),
        ]
        for long, short in cases:
            with self.subTest(short=short):
                self.assertEqual(vars(cli.parse_args(normalize(short, cli))), vars(cli.parse_args(normalize(long, cli))))
