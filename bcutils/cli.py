"""Argument-driven commands with explicit course and club name entry prompts."""

import argparse
import re
import shutil
import sys
from dataclasses import replace
from datetime import date
from difflib import get_close_matches
from pathlib import Path

from .app import DEFAULT_ROOT, Workspace
from .cli_dates import DATE_HELP, RANGE_HELP, parse_cli_date, parse_cli_range
from .help_style import SpacedHelpFormatter, write_help, emit, ask, error_message
from .cli_interface import normalize, render_help, public_path, path_of
from .models import CalendarError, DestinationExistsError, DayOverride
from .schedule import preview_text
from .semesters import create_semester, describe_semester
from .storage import digest, load_courses, safe_child

# Aliases are scoped to their parent command and always resolve to canonical
# names. For example, `s` means semester at the top level and set under courses.
COMMAND_ALIASES = {
    "gui": "g", "init": "i", "semester": "s", "courses": "c",
    "activities": "a", "exceptions": "e", "export": "x", "preview": "p",
    "validate": "v", "list": "ls", "show": "sh", "use": "u", "new": "n",
    "edit": "e", "set": "s", "clear": "c", "enable": "on",
    "disable": "off", "import": "i", "path": "p", "remove": "rm", "help": "h",
}


def add_command(subs, name, **kwargs):
    child = subs.add_parser(name, aliases=[COMMAND_ALIASES[name]], **kwargs)
    child.set_defaults(**{subs.dest: name})
    return child


def help_parser(root, topics):
    """Resolve help through the real command tree, including its short names."""
    current = root
    for topic in topics:
        children = next((a.choices for a in current._actions if isinstance(a, argparse._SubParsersAction)), {})
        if topic not in children:
            raise CalendarError(f"Unknown help topic {topic!r}. Run python -m bcalendar-utils {public_path(path_of(current))} --help for available commands.")
        current = children[topic]
    return current


class FriendlyParser(argparse.ArgumentParser):
    """Keep errors script-safe while adding a correction and local help route."""

    def __init__(self, *args, **kwargs):
        # Only documented aliases are accepted; a typo must not pick an action.
        kwargs.setdefault("allow_abbrev", False)
        kwargs.setdefault("formatter_class", SpacedHelpFormatter)
        # Python 3.14 adds its own palette; use the same restrained styling on
        # every supported Python version and honor our output-stream detection.
        if sys.version_info >= (3, 14):
            kwargs["color"] = False
        super().__init__(*args, **kwargs)

    def format_help(self):
        return render_help(self)

    def print_help(self, file=None):
        write_help(self.format_help(), file if file is not None else sys.stdout)

    def option_names(self):
        # argparse reports leftover unknown flags at the root parser. Include
        # child options there so a typo such as --wek can still suggest --week.
        names = set(self._option_string_actions)
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    names.update(child.option_names())
        return names

    def error(self, message):
        # Argparse's diagnostics include every legacy alias. Show the public
        # long spelling so corrections follow the same vocabulary as help.
        message = re.sub(r"(--[\w-]+)(?:/--?[\w-]+)+", r"\1", message)
        hints = []
        if "unrecognized arguments:" in message:
            for token in message.split("unrecognized arguments:", 1)[1].split():
                if token.startswith("-"):
                    matches = get_close_matches(token.split("=", 1)[0], sorted(self.option_names()), n=1, cutoff=0.65)
                    if matches:
                        hints.append(f"Did you mean {matches[0]}?")
        if "expected" in message and ("--exception" in message or "-e:" in message):
            hints.append("An exception takes a DATE and a RULE, e.g. --exception 9.18 Mon or --exception 9.18 off.")
        if "expected" in message and "--day" in message:
            hints.append("Try -d 9.18 or -d 9.14:9.18.")
        error_message(message + ("\n" + "\n".join(hints) if hints else ""), public_path(path_of(self), getattr(self, "navigation_mode", None)) + " --docs")
        self.exit(2)


class DocumentationAction(argparse.Action):
    """Expanded help exits before validation, prompts or any workspace writes."""

    def __call__(self, parser, namespace, values, option_string=None):
        write_help(render_help(parser, detailed=True), sys.stdout)
        parser.exit()


class DateSelector(argparse.Action):
    """Aliases share a value, but supplying two selectors must not hide one."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            raise argparse.ArgumentError(self, "Choose one date selector. Put the whole range in one flag, e.g. -d 9.14:9.18.")
        setattr(namespace, self.dest, values)


def parser():
    # Suppression lets context flags work before OR after an action without
    # child-parser defaults erasing the values already read by its parent.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", "-r", type=Path, metavar="PATH", default=argparse.SUPPRESS, help="Project/data folder")
    common.add_argument("--profile", "-p", metavar="NAME", default=argparse.SUPPRESS, help="Student profile (default: active profile or me)")
    common.add_argument("--semester", "-s", metavar="ID", default=argparse.SUPPRESS, help="Use this defined semester for this command")
    common.add_argument("--docs", action=DocumentationAction, nargs=0, default=argparse.SUPPRESS, help="Read complete documentation for this action")
    result = FriendlyParser(prog="python -m bcalendar-utils", parents=[common],
        description="Define a timetable, name your courses, export selected dates.",
        usage="%(prog)s [COMMAND] [OPTIONS]")
    subs = result.add_subparsers(dest="command")
    guide = add_command(subs, "help", parents=[common], help="First-use guide or help for a command")
    guide.add_argument("topics", nargs="*", metavar="COMMAND", help="Optional command and subcommand, e.g. --activities --set")
    add_command(subs, "gui", parents=[common], help="Open the desktop interface")
    add_command(subs, "init", parents=[common], help="Create blank course CSVs for a selected semester")
    semester = add_command(subs, "semester", parents=[common], help="Define, inspect and select a semester")
    actions = semester.add_subparsers(dest="action")
    add_command(actions, "list", parents=[common], help="List definitions and incomplete drafts")
    for action in ("show", "use"):
        sub = add_command(actions, action, parents=[common], help="Display the timetable" if action == "show" else "Validate and select a timetable; create blank courses")
        sub.add_argument("id", help="Semester ID from --inspect --semesters")
    new = add_command(actions, "new", parents=[common], help="Create a definition; without a CSV it starts as a draft")
    new.add_argument("id", help="New semester folder name; must not already exist")
    source = new.add_mutually_exclusive_group(required=True)
    source.add_argument("--blocks", "-b", help="Comma-separated block names, e.g. X,Y,Z")
    source.add_argument("--copy", "-c", dest="copy_from", metavar="ID", help="Copy a semester definition; only --name may override a field")
    new.add_argument("--name", "-N", help="Display name")
    new.add_argument("--timetable", "-t", type=Path, metavar="FILE", help="CSV with pattern,block,start,end columns")
    new.add_argument("--weekdays", "-W", help="e.g. mon=red,tue=blue; omitted days off. Default: Monday–Friday patterns")
    new.add_argument("--utc-offset", "-z", metavar="OFFSET", help="Fixed school clock, default +08:00; negative example: --utc-offset=-05:00")
    new.add_argument("--noon-cutoff", "-C", metavar="HH:MM", help="Half-day dividing time, default 12:30")

    courses = add_command(subs, "courses", parents=[common], help="Name classes or study periods for this semester")
    actions = courses.add_subparsers(dest="action")
    for action in ("list", "path"):
        add_command(actions, action, parents=[common])
    edit = add_command(actions, "edit", parents=[common], help="Prompt for course names, then save once")
    edit.add_argument("blocks", nargs="*", help="Only ask about these blocks (default: all)")
    sub = add_command(actions, "set", parents=[common], help="Set one course; saves immediately")
    sub.add_argument("block", help="Block key from --inspect --courses")
    sub.add_argument("name", help="Course name, or Study Hall")
    sub.add_argument("--room", "-R", help="Room or location")
    sub.add_argument("--teacher", "-t", help="Teacher name (local reference only)")
    sub.add_argument("--timing", "-T", help="Semester-defined choice, e.g. study-hall or toefl")
    for action in ("clear", "enable", "disable"):
        sub = add_command(actions, action, parents=[common])
        sub.add_argument("blocks", nargs="+", help="One or more block keys from --inspect --courses")
    sub = add_command(actions, "import", parents=[common], help="Validate and replace selections from a CSV (old file backed up)")
    sub.add_argument("file", type=Path, help="Course CSV to validate and import; replaces all course selections")

    activities = add_command(subs, "activities", parents=[common], help="List CAS/club slots and save club names",
        description="Run -a to enter club names for the predefined times. No timetable editing needed.",
        epilog='Examples:\n  --write --activities\n  --inspect --activities\n  --write --activities --set club-tue "Chess Club"\n\nNamed enabled clubs are included by default; use --noclub to exclude.\nCAS has a fixed name; use --cas.')
    actions = activities.add_subparsers(dest="action")
    add_command(actions, "list", parents=[common], help="Show activity IDs, names and times")
    edit = add_command(actions, "edit", parents=[common], help="Prompt for club names, then save once (default)")
    edit.add_argument("ids", nargs="*", help="Only these club slots (default: all clubs)")
    sub = add_command(actions, "set", parents=[common], help="Save a club name for a slot",
        epilog='Example: python -m bcalendar-utils --write --activities --set club-tue "Chess Club" --room Library')
    sub.add_argument("id", help="Club slot ID from --inspect --activities")
    sub.add_argument("name", help="Club name")
    sub.add_argument("--room", "-R", help="Room or location")
    for action in ("clear", "enable", "disable"):
        sub = add_command(actions, action, parents=[common], help={"clear": "Clear a club name", "enable": "Include a named club", "disable": "Keep a club name but exclude it"}[action])
        sub.add_argument("id", help="Club slot ID from --inspect --activities")

    exceptions = add_command(subs, "exceptions", parents=[common], help="Save unusual days; apply with --schedule exceptions")
    actions = exceptions.add_subparsers(dest="action")
    add_command(actions, "list", parents=[common])
    sub = add_command(actions, "remove", parents=[common], help="Remove your exception; school rules may still apply")
    sub.add_argument("date", help="Date or inclusive range; school rules remain")
    sub = add_command(actions, "set", parents=[common], help="Save or replace unusual dates")
    sub.add_argument("date", help="Date or inclusive range; replaces your entire rule for each date")
    choice = sub.add_mutually_exclusive_group()
    choice.add_argument("--off", "-O", action="store_true", help="No events, including CAS and clubs")
    choice.add_argument("--follow", "-f", metavar="PATTERN", help="Timetable pattern, e.g. monday; see --inspect --semesters --show ID")
    choice.add_argument("--late", "-l", action="store_true", help="Usual pattern, 20 minutes later")
    choice.add_argument("--normal", "-N", action="store_true", help="Usual pattern, normal times")
    choice.add_argument("--no-morning", "-m", action="store_true", help="Usual pattern, remove morning sessions")
    choice.add_argument("--no-afternoon", "-a", action="store_true", help="Usual pattern, remove afternoon sessions")
    sub.add_argument("--shift", "-S", type=int, metavar="MINUTES", help="With --follow only: replace export timing by -720 to 720 minutes; must stay within the day")
    sub.add_argument("--half-day", "-H", choices=["no-morning", "no-afternoon"], help="Also filter a saved weekday/timing override")
    sub.add_argument("--blank-hours", action="append", default=[], metavar="HH:MM-HH:MM", help="Blank a time window; repeat for more windows")
    sub.add_argument("--morning-cutoff", metavar="HH:MM", help="Blank times before this boundary")
    sub.add_argument("--afternoon-cutoff", metavar="HH:MM", help="Blank times from this boundary onward")
    sub.add_argument("--overlap", choices=["trim", "remove"], help="Trim around blank hours (default), or remove overlapping sessions")
    sub.add_argument("--note", "-n", default="", metavar="TEXT", help="Explanation shown in previews")

    for command in ("export", "preview", "validate"):
        sub = add_command(subs, command, parents=[common], help={"export": "Write a calendar file", "preview": "Show dates and classes", "validate": "Check courses, timetable and selected dates"}[command], epilog="Date formats:\n" + DATE_HELP + "\n\nExamples:\n" + RANGE_HELP)
        dates = sub.add_mutually_exclusive_group()
        dates.add_argument("--day", "-d", "--day-range", "--dayrange", dest="day", action=DateSelector, metavar="DATE[:DATE]", help="One day or inclusive range, e.g. 9.18 or 9.14:9.18; --day-range and --dayrange also work")
        dates.add_argument("--first-date", "--start", "-f", dest="start", metavar="DATE", help="First inclusive date; also supply --last-date")
        dates.add_argument("--week", "-w", metavar="DATE", help="Any date in the first Monday–Sunday week, e.g. 9.14")
        dates.add_argument("--this-week", "-t", action="store_true", help="Current Monday–Sunday")
        dates.add_argument("--next-week", "-x", action="store_true", help="Next Monday–Sunday")
        if command == "export":
            dates.add_argument("--last-inspect", action="store_true", help="Export the exact last dated inspection for this profile and semester")
        sub.add_argument("--last-date", "--end", "-u", dest="end", metavar="DATE", help="Last inclusive date; also supply --first-date")
        sub.add_argument("--weeks", "-n", type=int, metavar="COUNT", help="1–520 consecutive weeks; only with --week, --this-week or --next-week")
        sub.add_argument("--schedule", "-S", choices=["weekdays", "exceptions"], help="weekdays ignores exceptions; exceptions applies saved files as well as inline rules")
        sub.add_argument("--exception", "-e", nargs=2, action="append", default=[], metavar=("DATE[:DATE]", "RULE"), help="Repeat: off, Mon–Sun, blank=HH:MM-HH:MM, no-morning[=HH:MM], no-afternoon[=HH:MM], overlap=trim/remove, late or normal")
        sub.add_argument("--only", "-i", action="append", default=[], metavar="BLOCKS", help="Only these saved selections, e.g. B or B,T; repeatable")
        sub.add_argument("--exclude", "-X", action="append", default=[], metavar="BLOCKS", help="Omit these blocks for this export, e.g. A or A,T; repeatable")
        cas = sub.add_mutually_exclusive_group()
        cas.add_argument("--cas", "-c", action="store_true", default=None, help="Include CAS with its fixed title (default: off)")
        cas.add_argument("--nocas", dest="cas", action="store_false", help="Exclude CAS (default)")
        clubs = sub.add_mutually_exclusive_group()
        clubs.add_argument("--clubs", "-C", action="store_true", default=None, help="Include enabled, named clubs (default: on)")
        clubs.add_argument("--noclub", dest="clubs", action="store_false", help="Exclude clubs for this action")
        timing = sub.add_mutually_exclusive_group()
        timing.add_argument("--late", "-l", action="store_true", help="Start/end 20 minutes later")
        timing.add_argument("--normal", "-N", action="store_true", help="Normal times (default)")
        if command == "export":
            sub.add_argument("--output", "-o", type=Path, metavar="FILE", help="Destination .ics file; relative to the current terminal folder. Default: ROOT/exports/PROFILE-SEMESTER-FIRST-LAST.ics")
            sub.add_argument("--overwrite", "-O", action="store_true", help="Replace the existing destination; add to the same export command (no value or prompt)")
        if command == "preview":
            sub.add_argument("--width", "-W", type=int, metavar="NUMBER", help="Terminal preview width (20–300); default: detect terminal, fallback 120")
            sub.add_argument("--layout", "-L", choices=["columns", "list"], default="columns", help="Default: days side by side when space permits")
    return result


def arguments(argv, root=None):
    """Resolve entry shortcuts, skipping global values before inspecting flags."""
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"-p", "-s"} and (index + 1 == len(argv) or argv[index + 1].startswith("-")):
            break
        if token in {"--root", "--profile", "--semester", "-r", "-p", "-s"}:
            index += 2
        elif any(token.startswith(flag + "=") for flag in ("--root", "--profile", "--semester")):
            index += 1
        elif len(token) > 2 and token[:2] in {"-r", "-p", "-s"}:
            index += 1
        else:
            break
    # Bare command names retain their old flags. An old profile/semester short
    # with an explicit value is also kept for existing scripts, never advertised.
    legacy = index < len(argv) and not argv[index].startswith("-")
    legacy = legacy or any(token in {"-p", "-s"} and i + 1 < len(argv) and not argv[i + 1].startswith("-") for i, token in enumerate(argv[:index]))
    legacy = legacy or any(token.startswith(("-p", "-s")) and not token.startswith("--") and len(token) > 2 for token in argv[:index])
    if legacy:
        if index < len(argv) and argv[index] in {"-a", "--activities"}:
            return argv[:index] + ["activities"] + argv[index + 1:]
        if index < len(argv) and argv[index].startswith("-") and argv[index] not in {"-h", "--help"}:
            return argv[:index] + ["export"] + argv[index:]
        return argv
    return normalize(argv, root if root is not None else parser())


def command_settings(args, settings=None, *, today=None):
    """Exports never inherit stale GUI dates, lateness or exception choices."""
    if getattr(args, "last_inspect", False):
        # A reviewed snapshot can choose a destination, but cannot silently be
        # reshaped by export options. Inspect again to change dates or events.
        if (args.end is not None or args.weeks is not None or args.schedule is not None
                or args.exception or args.only or args.exclude or args.cas is not None
                or args.clubs is not None or args.late or args.normal):
            raise CalendarError("--last-inspect cannot combine with date, timing, activity or event filters.\nInspect the revised options first; only --output and --overwrite can change the saved export.")
        return {"last_inspect": True}
    mode = args.schedule or ("inline" if args.exception else "weekdays")
    if args.exception and mode == "weekdays":
        raise CalendarError("--schedule weekdays ignores exceptions. Omit it when using --exception.")
    today = today or date.today()
    result = dict(mode="this", anchor="", end="", weeks=1, late=args.late, schedule_mode=mode, only=args.only, exclude=args.exclude, cas=bool(args.cas), clubs=args.clubs is not False, require_clubs=args.clubs is True)
    if (args.start is None) != (args.end is None):
        raise CalendarError("Provide --first-date and --last-date together, or use --day DATE / --day-range FIRST:LAST.")
    if args.day is not None:
        first, last = parse_cli_range(args.day, today=today)
        result.update(mode="day" if first == last else "custom", anchor=first.isoformat(), end=last.isoformat())
    elif args.start is not None:
        first, last = parse_cli_date(args.start, today=today), parse_cli_date(args.end, today=today)
        if first > last:
            raise CalendarError("The last date must be on or after the first date. Include both years for a range crossing New Year.")
        result.update(mode="custom", anchor=first.isoformat(), end=last.isoformat())
    elif args.week is not None:
        result.update(mode="week", anchor=parse_cli_date(args.week, today=today).isoformat())
    elif args.this_week or args.next_week:
        result["mode"] = "next" if args.next_week else "this"
    else:
        raise CalendarError("Choose dates with --day YYYY-MM-DD, --day-range FIRST:LAST, --this-week, --next-week, or --week YYYY-MM-DD.")
    if args.weeks is not None:
        if result["mode"] in {"custom", "day"}:
            raise CalendarError("--weeks applies only to --week, --this-week or --next-week.")
        result["weeks"] = args.weeks
    # Inline rules reach the existing exception composer with canonical dates.
    from .cli_dates import expand_cli_range
    result["inline_exceptions"] = [(day.isoformat(), rule) for dates, rule in args.exception for day in expand_cli_range(dates, today=today)]
    return result


def timing_choice(value, choices):
    if value in choices:
        return value
    matches = [key for key in choices if key.replace("_", "-") == value]
    if len(matches) == 1:
        return matches[0]
    raise CalendarError("Choose --timing " + " or ".join(key.replace("_", "-") for key in choices))


def course_command(args, ctx):
    if args.action == "path":
        emit(ctx.courses_path)
        return
    expected = digest(ctx.courses_path)
    if args.action == "import":
        # A valid import can also repair a manually damaged selections file.
        ctx.save_courses(load_courses(args.file, ctx.semester), expected)
        emit(f"Saved courses: {ctx.courses_path}")
        return
    courses = ctx.courses()
    by_block = {course.block: i for i, course in enumerate(courses)}
    blocks = getattr(args, "blocks", None) or ([args.block] if hasattr(args, "block") else list(by_block))
    if set(blocks) - set(by_block):
        raise CalendarError("Unknown block. This semester defines: " + ", ".join(by_block))
    if args.action == "list":
        emit("Courses\n")
        for course in courses:
            option = f" ({course.timing_option.replace('_', '-')})" if course.timing_option else ""
            emit(f"  {course.block}: {course.course or '(unused)'}{option}" + (" [disabled]" if course.course and not course.enabled else ""))
        return
    if args.action == "edit":
        emit("Courses\n\n  Enter keeps · - clears · Ctrl+C cancels\n")
        for block in blocks:
            i, old = by_block[block], courses[by_block[block]]
            name = ask(f"  {block} [{old.course or 'unused'}]: ").strip() or old.course
            name = "" if name == "-" else name
            option = old.timing_option
            choices = ctx.semester.timing_options.get(block, {})
            if name and choices:
                while True:
                    text = ask(f"  {block} timing ({', '.join(key.replace('_', '-') for key in choices)}) [{option.replace('_', '-')}]: ").strip() or option
                    try:
                        option = timing_choice(text, choices)
                        break
                    except CalendarError as exc:
                        emit(f"  {exc}")
            courses[i] = replace(old, course=name, enabled=bool(name) if name != old.course else old.enabled, timing_option=option)
    else:
        for block in blocks:
            i, old = by_block[block], courses[by_block[block]]
            if args.action == "set":
                choices = ctx.semester.timing_options.get(block, {})
                option = timing_choice(args.timing, choices) if args.timing is not None else old.timing_option
                if choices and not option:
                    raise CalendarError(f"{block} has different end times. Add --timing " + " or ".join(key.replace('_', '-') for key in choices))
                courses[i] = replace(old, course=args.name.strip(), enabled=True, timing_option=option,
                    location=old.location if args.room is None else args.room, teacher=old.teacher if args.teacher is None else args.teacher)
            elif args.action == "clear":
                courses[i] = replace(old, course="", enabled=False, timing_option="")
            else:
                courses[i] = replace(old, enabled=args.action == "enable")
    ctx.save_courses(courses, expected)
    emit(f"\nSaved courses:\n  {ctx.courses_path}")


def activity_command(args, ctx):
    expected = digest(ctx.activities_path)
    items = ctx.activities()
    if args.action == "list":
        emit("Activities\n")
        for item in items:
            kind = ctx.semester.activities[item.activity]
            label = "CAS (fixed title)" if kind == "cas" else item.name or "(unnamed club)"
            slots = ", ".join(f"{s.pattern} {s.start:%H:%M}–{s.end:%H:%M}" for s in ctx.semester.activity_sessions if s.block == item.activity)
            emit(f"  {item.activity}: {label}\n    {slots}\n")
        emit("  Clubs included by default; CAS with --cas · More: --activities --docs")
        return
    if args.action == "edit":
        # Predefined slots supply the clock; this batch edits names only. Keep
        # the loaded digest and save once so cancellation/conflicts lose no data.
        by_key = {item.activity: i for i, item in enumerate(items) if ctx.semester.activities[item.activity] == "club"}
        ids = args.ids or list(by_key)
        if not ids:
            raise CalendarError("This semester has no club slots in its activities.csv.")
        if set(ids) - set(by_key) or len(ids) != len(set(ids)):
            raise CalendarError("Choose each club slot at most once from: " + ", ".join(by_key))
        emit("Activities\n\n  Fixed times · Enter keeps · - clears · Ctrl+C cancels\n")
        for key in ids:
            index, old = by_key[key], items[by_key[key]]
            slots = ", ".join(f"{s.pattern} {s.start:%H:%M}–{s.end:%H:%M}" for s in ctx.semester.activity_sessions if s.block == key)
            emit(f"  {key} · {slots}")
            text = ask(f"  Club name [{old.name or 'unused'}]: ").strip()
            emit()
            name = old.name if not text else "" if text == "-" else text
            items[index] = replace(old, name=name, enabled=bool(name) if name != old.name else old.enabled)
        ctx.save_activities(items, expected)
        emit(f"Saved club names:\n  {ctx.activities_path}\n\n  Clubs included by default; exclude with --noclub · More: --activities --docs")
        return
    matches = [i for i, item in enumerate(items) if item.activity == args.id]
    if not matches or ctx.semester.activities[args.id] != "club":
        raise CalendarError("Choose a club ID from --inspect --activities. CAS always uses its fixed title.")
    i = matches[0]
    if args.action == "set":
        items[i] = replace(items[i], name=args.name.strip(), enabled=True, location=items[i].location if args.room is None else args.room)
    elif args.action == "clear":
        items[i] = replace(items[i], name="", enabled=False)
    else:
        items[i] = replace(items[i], enabled=args.action == "enable")
    ctx.save_activities(items, expected)
    emit(f"Saved activities:\n  {ctx.activities_path}")


def exception_changes(args):
    """Preflight range/time syntax before a workflow is allowed to save anything."""
    from .cli_dates import expand_cli_range
    from .exception_times import blank_windows
    days = expand_cli_range(args.date, today=date.today())
    if args.action == "remove":
        return []
    if args.shift is not None and not args.follow:
        raise CalendarError("--shift requires --follow; use --late or --normal for the usual weekday.")
    half = "no-morning" if args.no_morning else "no-afternoon" if args.no_afternoon else args.half_day or ""
    if args.half_day and half != args.half_day:
        raise CalendarError("Choose only one half-day filter.")
    if not any((args.off, args.follow, args.late, args.normal, half, args.blank_hours, args.morning_cutoff, args.afternoon_cutoff)):
        raise CalendarError("Choose --off, --follow, --late, --normal or a half-day/time filter.")
    if args.overlap and not (args.blank_hours or args.morning_cutoff or args.afternoon_cutoff):
        raise CalendarError("--overlap requires --blank-hours or a morning/afternoon cutoff.")
    action = "off" if args.off else "use" if args.follow else "adjust" if args.late or args.normal else "partial"
    shift = args.shift if args.follow else 20 if args.late else 0 if args.normal else None
    items = [DayOverride(day, action, args.follow or "", shift, args.note, half,
                             ",".join(args.blank_hours), args.morning_cutoff or "", args.afternoon_cutoff or "", args.overlap or "trim") for day in days]
    for item in items:
        blank_windows(item)
        if item.action == "off" and (item.half_day or item.blank_hours or item.morning_cutoff or item.afternoon_cutoff):
            raise CalendarError("--off cannot combine with half-day or time filters.")
    return items


def exception_command(args, ctx):
    if args.action == "list":
        emit("Exceptions\n")
        from .storage import load_overrides
        for source, items in (("school", load_overrides(ctx.folder / "exceptions.csv", ctx.semester)), ("yours", ctx.exceptions())):
            for item in items:
                shift = "inherit" if item.time_shift_minutes is None else f"{item.time_shift_minutes:+} min"
                half = f" · {item.half_day}" if item.half_day else ""
                from .exception_times import window_description
                windows = window_description(item)
                emit(f"  {item.date}: {item.action} {item.pattern} · {shift}{half}{' · ' + windows if windows else ''} · {source} · {item.note}")
        emit("\n  Apply with --schedule exceptions · More: --write --exceptions --docs")
        return
    from .cli_dates import expand_cli_range
    days = set(expand_cli_range(args.date, today=date.today()))
    expected = digest(ctx.exceptions_path)
    items = [item for item in ctx.exceptions() if item.date not in days]
    items.extend(exception_changes(args))
    ctx.save_exceptions(items, expected)
    emit(f"Saved exceptions:\n  {ctx.exceptions_path}")


def semester_command(args, workspace):
    if args.action == "list":
        emit("Semesters\n")
        ids = workspace.semesters()
        active = workspace.settings()["active_semester"]
        for sid in ids:
            try:
                describe_semester(safe_child(workspace.root / "semesters", sid))
                state = "active" if sid == active else "ready"
            except CalendarError as exc:
                state = f"draft / invalid: {exc}"
            emit(f"  {sid} · {state}")
        if not ids:
            emit("No semester definitions. Start with --write --semesters --new ID --blocks X,Y,Z.")
    elif args.action == "new":
        folder = create_semester(workspace, args.id, blocks=args.blocks, name=args.name, timetable=args.timetable,
                                 copy_from=args.copy_from, weekdays=args.weekdays, utc_offset=args.utc_offset, noon_cutoff=args.noon_cutoff)
        if args.timetable or args.copy_from:
            emit(f"Defined {args.id}. Review with --inspect --semesters --show {args.id}, then select with --write --semesters --use {args.id}.")
        else:
            emit(f"Draft created. Fill {folder / 'timetable.csv'} with pattern,block,start,end rows.\nThen run --write --semesters --use {args.id}. The draft cannot export yet.")
    elif args.action == "show":
        emit(describe_semester(safe_child(workspace.root / "semesters", args.id)))
    else:
        ctx = workspace.use_semester(args.id, getattr(args, "profile", None))
        emit(f"Using {ctx.semester.id} · blocks: {', '.join(ctx.semester.blocks)}\n\n  Next: --write --courses · More: --inspect --semesters --docs")


def main(argv=None, *, prepared=None):
    # Windows redirected streams may otherwise use a legacy code page, losing
    # Unicode course names even though the CSV and calendar are valid UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    # Redirected name-entry input follows the same UTF-8 contract as output.
    # Configure only before a workflow starts, never between reads in its stages.
    if prepared is None and hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty() and sys.stdin.encoding.lower().replace("-", "") != "utf8":
        sys.stdin.reconfigure(encoding="utf-8")
    cli = parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if prepared is None:
        from .cli_workflow import starts_workflow, run_workflow
        if starts_workflow(argv):
            return run_workflow(argv, cli)
    try:
        args = prepared if prepared is not None else cli.parse_args(arguments(argv, cli))
    except ValueError as exc:
        error_message(exc)
        return 2
    workspace = Workspace(getattr(args, "root", DEFAULT_ROOT))
    try:
        if args.command is None:
            cli.print_help()
            return 0
        if args.command == "help":
            if args.topics:
                help_parser(cli, args.topics).print_help()
            else:
                write_help(render_help(cli, detailed=True), sys.stdout)
            return 0
        if args.command == "activities" and args.action is None:
            args.action, args.ids = "edit", []
        if args.command == "courses" and args.action is None and any(token in {"--courses", "-c"} for token in (argv if argv is not None else sys.argv[1:])):
            args.action, args.blocks = "edit", []
        if args.command in {"semester", "courses", "activities", "exceptions"} and args.action is None:
            help_parser(cli, [args.command]).print_help()
            return 0
        if args.command == "semester":
            semester_command(args, workspace)
            return 0
        if args.command == "gui":
            from .gui import launch
            launch(workspace.root, semester_id=getattr(args, "semester", None), profile=getattr(args, "profile", None))
            return 0
        # Report bad date syntax before opening/creating any student files.
        export_settings = command_settings(args) if args.command in {"export", "preview", "validate"} else None
        if args.command == "exceptions" and args.action != "list":
            exception_changes(args)
        settings = workspace.settings()
        sid = workspace.selected_semester(getattr(args, "semester", None))
        profile = getattr(args, "profile", None) or settings["profile"]
        create = args.command == "init" or (args.command in {"courses", "exceptions", "activities"} and args.action not in {"list", "path"})
        ctx = workspace.context(profile, sid, create=create)
        if args.command == "init":
            emit(f"Course CSV: {ctx.courses_path}")
        elif args.command == "courses":
            course_command(args, ctx)
        elif args.command == "exceptions":
            exception_command(args, ctx)
        elif args.command == "activities":
            activity_command(args, ctx)
        else:
            from .inspection import load_inspection, remember_inspection
            last_inspect = export_settings.get("last_inspect", False)
            if last_inspect:
                preview, inspected_at = load_inspection(ctx)
            else:
                preview = ctx.preview(export_settings)
            if args.command == "preview":
                width = args.width if args.width is not None else max(20, min(300, shutil.get_terminal_size((120, 24)).columns))
                emit(preview_text(preview, width=width if args.layout == "columns" else None))
                remember_inspection(ctx, preview)
                emit("\n  Export this preview: --export --last-inspect / -e -l")
            elif args.command == "validate":
                emit(f"Valid: {len(preview.events)} events, {preview.start} to {preview.end}, {preview.clock}")
            else:
                if not preview.events:
                    if last_inspect:
                        raise CalendarError("The last inspection has no events to export.\nRun --inspect with dates and selections that contain events first.")
                    raise CalendarError("No events in this range.\nUse --inspect --courses and --inspect --day FIRST:LAST to check selections and dates. For clubs, inspect --activities and check that --noclub is absent.")
                output = ctx.export(preview, args.output, overwrite=args.overwrite)
                source = f"\nLast inspection: {ctx.profile} / {ctx.semester.id} · {inspected_at:%Y-%m-%d %H:%M} UTC" if last_inspect else ""
                emit(f"Exported {len(preview.events)} events · {preview.start} to {preview.end} · {preview.clock}{source}\n{output}")
        return 0
    except (CalendarError, OSError, ImportError, ValueError) as exc:
        path = [args.command] + ([args.action] if getattr(args, "action", None) else [])
        if isinstance(exc, DestinationExistsError) and args.command == "export":
            # Preserve the original command's dates, rules and destination; only
            # explain the extra flag rather than reconstructing shell quoting.
            exc = f'{exc}\nTo replace it, rerun the export action with --overwrite added.\nTo keep it, add --output "exports/another-name.ics" with an unused name.'
        error_message(exc, public_path(path) + " --docs")
        return 2
    except (EOFError, KeyboardInterrupt):
        emit("\nCancelled. Unsaved name inputs were discarded.")
        return 130
