"""Public dash-based vocabulary layered over the existing command handlers.

    Grammar and presentation share these names. Existing bare-command syntax is
    kept by the CLI as a compatibility path, but is not part of public help.
"""

import argparse
import textwrap


ROOT_COMMANDS = {
    "--activities": ("activities", "-a"), "--courses": ("courses", "-c"),
    "--preview": ("preview", "-p"), "--validate": ("validate", "-v"),
    "--semesters": ("semester", "-s"), "--exceptions": ("exceptions", None),
    "--export": ("export", "-e"), "--gui": ("gui", "-g"), "--init": ("init", "-i"),
}
COMMON = {"--root": "-r", "--profile": None, "--semester": None, "--help": "-h", "--docs": None}
# Prefer initials; a colliding secondary option stays long-only. Never
# invent capital or unrelated shortcuts that users would need to memorize.
EXPORT_OPTIONS = {
    "--day": "-d", "--week": "-w", "--weeks": None, "--this-week": "-t",
    "--next-week": "-n", "--first-date": "-f", "--last-date": None,
    "--schedule": "-s", "--exception": "-e", "--only": None,
    "--exclude": None, "--cas": "-c", "--clubs": None, "--late": None,
    "--normal": None, "--output": "-o", "--overwrite": None,
    "--width": None, "--layout": None,
    "--noclub": None, "--nocas": None,
    "--last-inspect": "-l",
}
GROUP_ACTIONS = {
    "semester": {"list": "-l", "show": "-s", "use": "-u", "new": "-n"},
    "courses": {"list": "-l", "path": "-p", "edit": "-e", "set": "-s", "clear": "-c", "enable": None, "disable": "-d", "import": "-i"},
    "activities": {"list": "-l", "edit": "-e", "set": "-s", "clear": "-c", "enable": None, "disable": "-d"},
    "exceptions": {"list": "-l", "set": "-s", "remove": None},
}
DETAIL_OPTIONS = {
    ("semester", "new"): {"--blocks": "-b", "--copy": "-c", "--name": "-n", "--timetable": "-t", "--weekdays": "-w", "--utc-offset": "-u", "--noon-cutoff": None},
    ("courses", "set"): {"--room": None, "--teacher": "-t", "--timing": None},
    ("activities", "set"): {"--room": None},
    ("exceptions", "set"): {"--off": "-o", "--follow": "-f", "--late": "-l", "--normal": "-n", "--no-morning": None, "--no-afternoon": None, "--shift": "-s", "--half-day": None, "--note": None, "--blank-hours": "-b", "--morning-cutoff": "-m", "--afternoon-cutoff": "-a", "--overlap": None},
}


def path_of(parser):
    """Use canonical tree metadata, never version-dependent help text."""
    return parser.command_path


def public_path(path, mode=None):
    """Name the public intent, even when handlers retain their internal names."""
    if not path:
        return ""
    target, *operations = path
    if target == "preview":
        return "--inspect"
    if target == "validate":
        return "--inspect --validate"
    if target in {"export", "gui"}:
        return "--" + target
    if mode is None:
        mode = "inspect" if operations and operations[0] in {"list", "path", "show"} or not operations and target in {"semester", "exceptions"} else "write"
    if operations == ["list"] and mode == "inspect":
        operations = []
    return " ".join(["--" + mode, "--semesters" if target == "semester" else "--" + target] + ["--" + item for item in operations])


def option_map(path):
    if path and path[0] in {"export", "preview", "validate"}:
        options = dict(EXPORT_OPTIONS)
        # -l selects the reviewed preview in exports; inspection retains -l
        # for lateness. The compatibility parser keeps its historical aliases.
        if path[0] != "export":
            options.pop("--last-inspect")
            options["--late"] = "-l"
        return COMMON | options
    return COMMON | DETAIL_OPTIONS.get(tuple(path), {})


def children(parser):
    return next((a.choices for a in parser._actions if isinstance(a, argparse._SubParsersAction)), {})


def normalize(argv, root):
    """Normalize only syntax positions. Consume option values before scanning.

    Names, file paths and exception rules never become commands even when they
    look like an alias. Values attached with '=' and short forms are preserved.
    """
    result, path, current, index = [], (), root, 0
    root_lookup = {token: name for flag, (name, short) in ROOT_COMMANDS.items() for token in (flag, short) if token}
    while index < len(argv):
        token = argv[index]
        head, equals, attached = token.partition("=")
        if token == "--":
            result.extend(argv[index:])
            break
        lookup = {short: long for long, short in option_map(path).items() if short}
        if not path and not equals and len(head) > 2 and not head.startswith("--") and head[:2] in lookup:
            head, attached, equals = head[:2], head[2:], "="
        # Common options may precede the command. -s / -p are actions here;
        # profile and explicit semester selection remain long-only.
        if not path and head in root_lookup:
            if equals:
                raise ValueError(f"{head} is an action. Put its arguments after a space.")
            command = root_lookup[head]
            path, current = (command,), children(root)[command]
            result.append(command)
            index += 1
            continue
        if len(path) == 1 and path[0] in GROUP_ACTIONS:
            actions = {token: name for name, short in GROUP_ACTIONS[path[0]].items() for token in ("--" + name, short) if token}
            if head in actions:
                if equals:
                    raise ValueError(f"{head} is an action. Put its arguments after a space.")
                action = actions[head]
                path, current = (*path, action), children(current)[action]
                result.append(action)
                index += 1
                continue
            if head in children(current):
                # Compatibility for mixed forms such as --activities set.
                child = children(current)[head]
                action = path_of(child)[-1]
                path, current = (*path, action), child
                result.append(action)
                index += 1
                continue
        if not path and head not in COMMON and head not in lookup:
            # Any export option starts the implicit export context.
            path, current = ("export",), children(root)["export"]
            result.append("export")
            lookup = {short: long for long, short in option_map(path).items() if short}
        canonical = lookup.get(head, head)
        if not equals and len(head) > 2 and not head.startswith("--") and head[:2] in lookup:
            canonical, attached, equals = lookup[head[:2]], head[2:], "="
        action = current._option_string_actions.get(canonical)
        # Never let the underlying compatibility aliases reinterpret a new
        # interface token that has no meaning in the selected public context.
        if canonical.startswith("-") and not canonical.startswith("--") and not (len(canonical) == 2 and canonical[1].isupper() and action):
            raise ValueError(f"Unknown option {head!r}. Use {public_path(path)} --help for available options.")
        result.append(canonical + ("=" + attached if equals else ""))
        index += 1
        if action and not equals:
            count = 0 if action.nargs == 0 else action.nargs if isinstance(action.nargs, int) else 1
            for _ in range(count):
                if index >= len(argv) or argv[index].startswith("--") or (argv[index].startswith("-") and not argv[index][1:2].isdigit()):
                    break
                result.append(argv[index])
                index += 1
    return result


def rows(items, width=84):
    """One aligned, wrapping layout for every help section."""
    lines = []
    for label, description in items:
        if description and len(label) <= 22:
            lines.extend(textwrap.wrap(description, width=width, initial_indent=f"  {label:<22}  ", subsequent_indent=" " * 26, break_long_words=False, break_on_hyphens=False))
        else:
            lines.append(f"  {label}")
            if description:
                lines.extend(textwrap.wrap(description, width=width, initial_indent="    ", subsequent_indent="    ", break_long_words=False, break_on_hyphens=False))
    return lines + [""]


def argument_label(action):
    """Expose arity and choices from argparse, including required positionals."""
    value = action.metavar or ("{" + ",".join(map(str, action.choices)) + "}" if action.choices else action.dest.upper())
    if isinstance(value, tuple):
        return " ".join(value)
    if action.nargs == "*":
        return f"[{value} ...]"
    if action.nargs == "+":
        return f"{value} [{value} ...]"
    if action.nargs == "?":
        return f"[{value}]"
    return value


def positional_labels(parser):
    return [argument_label(a) for a in parser._actions if not a.option_strings and not isinstance(a, argparse._SubParsersAction)]


def usage_arguments(parser):
    # Required choices must remain visible even in compact help. Derive these
    # from the parser so future operations cannot silently lose their arguments.
    labels = positional_labels(parser)
    for group in parser._mutually_exclusive_groups:
        if group.required:
            labels.append("(" + " | ".join(next(s for s in a.option_strings if s.startswith("--")) + (" " + argument_label(a) if a.nargs != 0 else "") for a in group._group_actions) + ")")
    return " ".join(labels + ["[options]"])


def render_help(parser, detailed=False):
    path = path_of(parser)
    mode = getattr(parser, "navigation_mode", None)
    command = public_path(path, mode)
    heading = "Block Calendar Utils" + (" / " + " / ".join(p.lstrip("-").title() for p in command.split()) if path else "")
    if not path:
        lines = [heading, "", "  --inspect / -i        View saved data or preview dates", "  --write / -w          Save course names, clubs or date rules", "  --export / -e         Write an .ics calendar", "", "  python -m bcalendar-utils -i --day 0920-0924", "  python -m bcalendar-utils -w --courses -e --day 0920-0924", "", "  First time using? run python -m bcalendar-utils --docs"]
        if detailed:
            lines = [heading, "", "Start here", "", "  python -m bcalendar-utils -i --semesters --show 2026-27-s1", "  python -m bcalendar-utils -w --semesters --use 2026-27-s1", "  python -m bcalendar-utils -w --courses", "  python -m bcalendar-utils -w --activities", "  python -m bcalendar-utils -i --day 0920-0924", "  python -m bcalendar-utils -e --last-inspect", "", "Actions", ""]
            lines += rows([("--inspect / -i", "View timetables, saved CSV entries or dated events"), ("--write / -w", "Save names, selections or date rules to local files"), ("--export / -e", "Write an .ics snapshot for selected dates")])
            lines += ["Sequential actions", "", "  python -m bcalendar-utils -w --courses -i --day 0920-0924", "  python -m bcalendar-utils -w --courses -e --day 0920-0924", "", "  Actions run left to right. Syntax is checked before any write or prompt.", "  Each write saves before the next action. Failure or cancellation stops later", "  actions; completed saves stay saved. Help anywhere runs no actions.", "  --root PATH, --profile NAME and --semester ID apply to the whole workflow.", ""]
            lines += ["  File exists? Add --overwrite to the same export command to replace it.", '  To keep it, use --output "exports/another-name.ics" with an unused name.', ""]
            lines += ["Shortcuts", "", "  -i, -w and -e always start an action in a workflow.", "  Use --week, --exception, --edit and --import in full.", "  Other shorts use initials: --day → -d, --activities → -a.", "  Inspect details: --inspect --docs · Write details: --write --docs", "  Export details: --export --docs · Open the desktop interface: --gui", "  Python 3.11+. On macOS use python3. No runtime packages needed."]
        else:
            lines += ["  More: --docs · Short flags use the first letter, e.g. --day → -d."]
        return "\n".join(lines) + "\n"
    lines = [heading, ""] + textwrap.wrap("python -m bcalendar-utils " + command + " " + usage_arguments(parser), width=84, initial_indent="  ", subsequent_indent="    ") + [""]
    subcommands = children(parser)
    if subcommands:
        from .cli_workflow import ALLOWED
        mode = mode or ("inspect" if path[0] in {"semester", "exceptions"} else "write")
        descriptions = {"list": "View saved entries", "edit": "Enter names; save once", "set": "Save or replace one entry", "clear": "Clear name and disable selection", "enable": "Enable an existing named selection", "disable": "Keep a name but exclude it", "path": "Show the CSV location", "import": "Replace all courses from a CSV; back up old file", "show": "Review a timetable", "use": "Select timetable; create missing profile files", "new": "Create a timetable; requires --blocks or --copy", "remove": "Remove your saved date rule; school rule may remain"}
        descriptions["list"] = {"semester": "List definitions, including drafts", "courses": "Show block keys, names and enabled state", "activities": "Show slot IDs, names and times", "exceptions": "Show school and personal rules with their source"}[path[0]]
        names = {name: short for name, short in GROUP_ACTIONS.get(path[0], {}).items() if name in ALLOWED[mode].get(path[0], {})}
        lines += rows([(" ".join(["--" + name] + positional_labels(subcommands[name])), descriptions[name]) for name in names])
        if path[0] == "activities":
            lines += ["  Run --write --activities to enter club names at the predefined times.", '  One club: --write --activities --set club-tue "Chess Club"', "  Named enabled clubs are included by default; exclude with --noclub.", ""]
        elif path[0] == "courses":
            lines += ["  Run --write --courses to enter names for your selected timetable.", '  One course: --write --courses --set A "Mathematics"', ""]
    else:
        essentials = {"--day", "--week", "--next-week", "--last-inspect", "--exception", "--noclub", "--cas", "--nocas", "--late", "--output", "--overwrite"}
        items = []
        for action in parser._actions:
            if action.dest in {"help", "docs"}:
                continue
            long = next((s for s in action.option_strings if s.startswith("--")), None)
            if not detailed and long and (long in COMMON or (path[0] in {"export", "preview", "validate"} and long not in essentials)):
                continue
            label = long or argument_label(action)
            if long and action.nargs != 0:
                label += " " + argument_label(action)
            if detailed and long and (short := option_map(path).get(long)) and short not in {"-i", "-w", "-e"}:
                label += " / " + short
            description = action.help if action.help and action.help != argparse.SUPPRESS else ""
            if not detailed:
                description = {"--day": "A day or inclusive range", "--week": "The week containing this date", "--next-week": "Next Monday–Sunday", "--exception": "Blank dates/hours or change weekday/timing", "--cas": "Include CAS", "--clubs": "Include your named clubs", "--late": "Shift times by +20 minutes", "--output": "Destination .ics path; default: ROOT/exports/"}.get(long, description)
            items.append((label, description))
        lines += rows(items)
    if path[0] == "exceptions" and (subcommands or path[-1] == "list"):
        # Surface time filters at the Exceptions entry, where users choose
        # what to change, while leaving their grammar on the set operation.
        lines += ["  Time filters with --write --exceptions --set DATE[:DATE]", ""]
        lines += rows([
            ("--blank-hours HH:MM-HH:MM", "Blank hours; repeat for more windows"),
            ("--morning-cutoff HH:MM", "Blank times before this boundary"),
            ("--afternoon-cutoff HH:MM", "Blank times from this boundary onward"),
            ("--overlap trim|remove", "Trim/split (default), or remove overlapping sessions"),
        ])
        lines += ["  Apply saved rules with --schedule exceptions on preview/export.", ""]
    if path[0] == "export":
        lines += ["  Export a reviewed preview: --last-inspect / -l.", "  Or supply dates: --day DATE[:DATE], --week DATE, --this-week,", "  --next-week, or both --first-date DATE and --last-date DATE.", ""]
    elif path[0] in {"preview", "validate"}:
        lines += ["  Supply dates: --day DATE[:DATE], --week DATE, --this-week,", "  --next-week, or both --first-date DATE and --last-date DATE.", ""]
    if detailed:
        if subcommands:
            lines += ["  Add --docs after an operation to see its arguments.", "  Example: " + command + " --" + next(iter(names)) + " --docs", ""]
        elif parser.epilog:
            # Keep examples and paragraphs distinct while fitting terminal
            # width; ANSI is applied only after this plain-text layout.
            for paragraph in parser.epilog.splitlines():
                indent = "  " if paragraph.startswith("  ") else ""
                lines += textwrap.wrap(paragraph.strip(), width=84, initial_indent=indent, subsequent_indent=indent) if paragraph else [""]
            lines += [""]
        if path[0] in {"courses", "activities"}:
            lines += ["  Name entry: Enter keeps; - clears; Ctrl+C or EOF cancels the unsaved batch.", "  Inspect entries to find block/slot IDs. Quote names containing spaces.", ""]
        if path[0] == "exceptions":
            lines += ["  Saved rules apply only with --schedule exceptions on preview/export.", "  --set replaces your entire rule for that date; it does not merge fields.", ""]
        if path[0] in {"export", "preview", "validate"}:
            lines += ["  Normal times/weekdays and named clubs are defaults; CAS is off.", "  --noclub excludes clubs; --cas includes CAS; --nocas excludes CAS.", "  Saved rules require --schedule exceptions. Inline --exception rules replace", "  the saved row for their date; they never save to a file.", ""]
        if path[0] == "export":
            lines += ["  --last-inspect exports the last successful dated inspection for the current", "  profile and semester, including its dates, names, timing and exceptions.", "  It works across separate commands and in -i --day DATE -e -l.", "  Only --output and --overwrite can modify that export. Inspect again to", "  change events. Use --late for export timing; -l means --last-inspect here.", ""]
            lines += ["  Replace an existing export by adding --overwrite to that export action:", "    python -m bcalendar-utils --export --day 0920-0924 --overwrite", "  To keep the old file, choose an unused --output path ending in .ics.", "  --overwrite takes no value, does not prompt, and applies only to this export.", "  After a stacked write succeeds, retry only the failed export action.", ""]
        if subcommands:
            lines += textwrap.wrap("Operations: " + " · ".join("--" + name + " / " + short for name, short in names.items() if short and short not in {"-i", "-w", "-e"}), width=84, initial_indent="  ", subsequent_indent="    ")
        lines += ["  Common: --root PATH / -r · --profile NAME · --semester ID", "  --root selects the data folder; --profile selects a student (default: active).", "  --semester selects a timetable for this command without activating it.", "  Short forms use initials; colliding secondary options stay long-only."]
    else:
        lines += ["  More: " + command + " --docs"]
    return "\n".join(lines) + "\n"
