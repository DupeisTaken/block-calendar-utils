"""Check published command examples against the actual parser without saving data."""

from contextlib import redirect_stdout
import io
import re
import shlex
import unittest
from urllib.parse import unquote

from shbs_calendar.app import DEFAULT_ROOT
from shbs_calendar.cli import arguments, parser
from shbs_calendar.cli_interface import COMMON, DETAIL_OPTIONS, EXPORT_OPTIONS, GROUP_ACTIONS, normalize
from shbs_calendar.cli_workflow import ALLOWED, STAGES, TARGETS, starts_workflow, split_stages, translate


class DocumentationTests(unittest.TestCase):
    def test_complete_shell_examples_use_supported_public_syntax(self):
        count = 0
        for relative in ("README.md", "docs/setup.md", "docs/commands.md", "docs/command-catalogue.md", "docs/gui.md", "docs/configuration.md"):
            document = (DEFAULT_ROOT / relative).read_text(encoding="utf-8")
            # Only executable examples count; prose placeholders and historic
            # verification logs intentionally do not form a runnable tutorial.
            for block in re.findall(r"```sh\n(.*?)```", document, re.S):
                for line in block.splitlines():
                    prefix = "python -m shbs-calendar "
                    if not line.startswith(prefix):
                        continue
                    count += 1
                    argv = shlex.split(line[len(prefix):])
                    self.assertTrue(argv[0].startswith("-"), line)
                    with self.subTest(file=relative, command=line), redirect_stdout(io.StringIO()):
                        cli = parser()
                        try:
                            if starts_workflow(argv):
                                stages, context = split_stages(argv, cli)
                                for mode, tokens in stages:
                                    if not tokens or all(t in {"--docs", "--help", "-h"} for t in tokens) and mode != "export":
                                        continue
                                    args = cli.parse_args(normalize(context + translate(mode, tokens), cli))
                                    self.assertIn(args.command, ALLOWED[mode])
                                    self.assertIn(getattr(args, "action", None), ALLOWED[mode][args.command])
                            else:
                                cli.parse_args(arguments(argv, cli))
                        except SystemExit as exc:
                            self.assertEqual(exc.code, 0)
        self.assertGreaterEqual(count, 35)

    def test_documentation_links_anchors_and_fences_resolve(self):
        # Resolve links relative to each source file so the README remains a
        # useful entry point when guides move or headings are renamed.
        documents = [DEFAULT_ROOT / "README.md", *sorted((DEFAULT_ROOT / "docs").glob("*.md"))]
        for source in documents:
            text = source.read_text(encoding="utf-8")
            with self.subTest(source=source.name):
                self.assertEqual(sum(line.startswith("```") for line in text.splitlines()) % 2, 0)
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("mailto:"):
                    continue
                name, _, anchor = unquote(target).partition("#")
                destination = source.parent / name if name else source
                with self.subTest(source=source.name, target=target):
                    self.assertTrue(destination.is_file(), f"Broken link: {target}")
                    if anchor:
                        headings = re.findall(r"^#+\s+(.+)$", destination.read_text(encoding="utf-8"), re.M)
                        slugs = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}
                        self.assertIn(anchor, slugs)

    def test_catalogue_covers_all_public_long_options(self):
        # Check reference coverage against the actual vocabulary rather than
        # maintaining a second hand-written checklist of supported options.
        expected = set(COMMON) | set(EXPORT_OPTIONS) | set(STAGES) | set(TARGETS)
        expected |= {"--" + name for actions in GROUP_ACTIONS.values() for name in actions}
        expected |= {flag for options in DETAIL_OPTIONS.values() for flag in options}
        expected |= {"--gui", "--day-range", "--dayrange"}
        expected = {flag for flag in expected if flag.startswith("--")}
        catalogue = (DEFAULT_ROOT / "docs/command-catalogue.md").read_text(encoding="utf-8")
        documented = set(re.findall(r"(?<![\w-])--[a-z][a-z-]*", catalogue))
        self.assertFalse(expected - documented, f"Missing catalogue options: {sorted(expected - documented)}")
