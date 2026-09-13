"""Argument-driven commands; only `courses edit` collects interactive input."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .app import DEFAULT_ROOT, Workspace
from .models import CalendarError, DayOverride
from .schedule import preview_text
from .semesters import create_semester, describe_semester
from .storage import digest, load_courses, parse_date, safe_child

EXAMPLES = """Start once:
  python -m shbs-calendar semester list
  python -m shbs-calendar semester show 2026-27-s1
  python -m shbs-calendar semester use 2026-27-s1
  python -m shbs-calendar courses edit

Then export:
  python -m shbs-calendar --dayrange 2026-09-14:2026-09-18
  python -m shbs-calendar preview --next-week
  python -m shbs-calendar --next-week --late

A different semester:
  python -m shbs-calendar semester new spring --blocks X,Y,Z
  (fill its timetable.csv, then run semester use spring)

Use COMMAND --help for options. macOS: use python3 instead of python.
"""


def parser():
    # Suppression lets context flags work before OR after an action without
    # child-parser defaults erasing the values already read by its parent.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=argparse.SUPPRESS, help="Project/data folder")
    common.add_argument("--profile", default=argparse.SUPPRESS, help="Student profile (default: active profile or me)")
    common.add_argument("--semester", default=argparse.SUPPRESS, help="Use this defined semester for this command")
    result = argparse.ArgumentParser(prog="python -m shbs-calendar", parents=[common],
        description="Define a timetable, name your courses, export selected dates.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = result.add_subparsers(dest="command")
    subs.add_parser("gui", parents=[common], help="Open the desktop interface")
    subs.add_parser("init", parents=[common], help="Create blank course CSVs for a selected semester")
    semester = subs.add_parser("semester", parents=[common], help="Define, inspect and select a semester")
    actions = semester.add_subparsers(dest="action", required=True)
    actions.add_parser("list", parents=[common], help="List definitions and incomplete drafts")
    for action in ("show", "use"):
        sub = actions.add_parser(action, parents=[common], help="Display the timetable" if action == "show" else "Validate and select a timetable; create blank courses")
        sub.add_argument("id")
    new = actions.add_parser("new", parents=[common], help="Create a definition; without a CSV it starts as a draft")
    new.add_argument("id")
    source = new.add_mutually_exclusive_group(required=True)
    source.add_argument("--blocks", help="Comma-separated block names, e.g. X,Y,Z")
    source.add_argument("--copy", dest="copy_from", help="Explicitly reuse another semester's definition")
    new.add_argument("--name", help="Display name")
    new.add_argument("--timetable", type=Path, help="CSV with pattern,block,start,end columns")
    new.add_argument("--weekdays", help="e.g. mon=red,tue=blue; omitted days off. Default: Monday–Friday patterns")
    new.add_argument("--utc-offset", help="Fixed school clock, default +08:00")

    courses = subs.add_parser("courses", parents=[common], help="Name classes or study periods for this semester")
    actions = courses.add_subparsers(dest="action", required=True)
    for action in ("list", "path"):
        actions.add_parser(action, parents=[common])
    edit = actions.add_parser("edit", parents=[common], help="Prompt for course names, then save once")
    edit.add_argument("blocks", nargs="*", help="Only ask about these blocks (default: all)")
    sub = actions.add_parser("set", parents=[common], help="Set one course; saves immediately")
    sub.add_argument("block")
    sub.add_argument("name", help="Course name, or Study Hall")
    sub.add_argument("--room")
    sub.add_argument("--teacher")
    sub.add_argument("--timing", help="Semester-defined choice, e.g. study-hall or toefl")
    for action in ("clear", "enable", "disable"):
        sub = actions.add_parser(action, parents=[common])
        sub.add_argument("blocks", nargs="+")
    sub = actions.add_parser("import", parents=[common], help="Validate and replace selections from a CSV (old file backed up)")
    sub.add_argument("file", type=Path)

    exceptions = subs.add_parser("exceptions", parents=[common], help="Save unusual days; apply with --schedule exceptions")
    actions = exceptions.add_subparsers(dest="action", required=True)
    actions.add_parser("list", parents=[common])
    sub = actions.add_parser("remove", parents=[common], help="Remove your exception; school rules may still apply")
    sub.add_argument("date")
    sub = actions.add_parser("set", parents=[common], help="Save or replace one unusual date")
    sub.add_argument("date")
    choice = sub.add_mutually_exclusive_group(required=True)
    choice.add_argument("--off", action="store_true", help="No classes")
    choice.add_argument("--follow", help="Timetable pattern, e.g. monday")
    choice.add_argument("--late", action="store_true", help="Usual pattern, 20 minutes later")
    choice.add_argument("--normal", action="store_true", help="Usual pattern, normal times")
    sub.add_argument("--shift", type=int, help="With --follow only: replace export timing by this many minutes")
    sub.add_argument("--note", default="")

    for command in ("export", "preview", "validate"):
        sub = subs.add_parser(command, parents=[common], help={"export": "Write a calendar file", "preview": "Show dates and classes", "validate": "Check courses, timetable and selected dates"}[command])
        dates = sub.add_mutually_exclusive_group()
        dates.add_argument("--dayrange", metavar="FIRST:LAST", help="Inclusive dates, e.g. 2026-09-14:2026-09-18; one date also works")
        dates.add_argument("--first-date", "--start", dest="start", metavar="YYYY-MM-DD")
        dates.add_argument("--week", metavar="YYYY-MM-DD", help="Any date in the first Monday–Sunday week")
        dates.add_argument("--this-week", action="store_true")
        dates.add_argument("--next-week", action="store_true")
        sub.add_argument("--last-date", "--end", dest="end", metavar="YYYY-MM-DD")
        sub.add_argument("--weeks", type=int, help="Number of weeks, with a week shortcut")
        sub.add_argument("--schedule", choices=["weekdays", "exceptions"], default="weekdays", help="Default: weekdays, ignoring saved exceptions")
        sub.add_argument("--only", action="append", default=[], metavar="BLOCKS", help="Only these saved selections, e.g. B or B,T; repeatable")
        sub.add_argument("--exclude", action="append", default=[], metavar="BLOCKS", help="Omit these blocks for this export, e.g. A or A,T; repeatable")
        timing = sub.add_mutually_exclusive_group()
        timing.add_argument("--late", action="store_true", help="Start/end 20 minutes later")
        timing.add_argument("--normal", action="store_true", help="Normal times (default)")
        if command == "export":
            sub.add_argument("--output", "-o", type=Path)
            sub.add_argument("--overwrite", action="store_true")
    return result


def arguments(argv):
    """Insert `export` for a flag-only invocation, skipping global flag values."""
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"--root", "--profile", "--semester"}:
            index += 2
        elif any(token.startswith(flag + "=") for flag in ("--root", "--profile", "--semester")):
            index += 1
        else:
            break
    if index < len(argv) and argv[index].startswith("-") and argv[index] not in {"-h", "--help"}:
        return argv[:index] + ["export"] + argv[index:]
    return argv


def command_settings(args, settings=None):
    """Exports never inherit stale GUI dates, lateness or exception choices."""
    result = dict(mode="this", anchor="", end="", weeks=1, late=args.late, schedule_mode=args.schedule, only=args.only, exclude=args.exclude)
    if bool(args.start) != bool(args.end):
        raise CalendarError("Provide --first-date and --last-date together, or use --dayrange FIRST:LAST.")
    if args.dayrange:
        endpoints = args.dayrange.split(":")
        if len(endpoints) not in (1, 2) or not all(endpoints):
            raise CalendarError("Use --dayrange YYYY-MM-DD:YYYY-MM-DD (both dates included).")
        result.update(mode="custom", anchor=endpoints[0], end=endpoints[-1])
    elif args.start:
        result.update(mode="custom", anchor=args.start, end=args.end)
    elif args.week:
        result.update(mode="week", anchor=args.week)
    elif args.this_week or args.next_week:
        result["mode"] = "next" if args.next_week else "this"
    else:
        raise CalendarError("Choose dates with --dayrange FIRST:LAST, --this-week, --next-week, or --week YYYY-MM-DD.")
    if args.weeks is not None:
        if result["mode"] == "custom":
            raise CalendarError("--weeks applies to a week shortcut, not a date range.")
        result["weeks"] = args.weeks
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
        print(ctx.courses_path)
        return
    expected = digest(ctx.courses_path)
    if args.action == "import":
        # A valid import can also repair a manually damaged selections file.
        ctx.save_courses(load_courses(args.file, ctx.semester), expected)
        print(f"Saved courses: {ctx.courses_path}")
        return
    courses = ctx.courses()
    by_block = {course.block: i for i, course in enumerate(courses)}
    blocks = getattr(args, "blocks", None) or ([args.block] if hasattr(args, "block") else list(by_block))
    if set(blocks) - set(by_block):
        raise CalendarError("Unknown block. This semester defines: " + ", ".join(by_block))
    if args.action == "list":
        for course in courses:
            option = f" ({course.timing_option.replace('_', '-')})" if course.timing_option else ""
            print(f"{course.block}: {course.course or '(unused)'}{option}" + (" [disabled]" if course.course and not course.enabled else ""))
        return
    if args.action == "edit":
        print("Enter a name to include a block. Enter keeps its current value; - clears it. Ctrl+C cancels unsaved changes.")
        for block in blocks:
            i, old = by_block[block], courses[by_block[block]]
            name = input(f"{block} [{old.course or 'unused'}]: ").strip() or old.course
            name = "" if name == "-" else name
            option = old.timing_option
            choices = ctx.semester.timing_options.get(block, {})
            if name and choices:
                while True:
                    text = input(f"{block} timing ({', '.join(key.replace('_', '-') for key in choices)}) [{option.replace('_', '-')}]: ").strip() or option
                    try:
                        option = timing_choice(text, choices)
                        break
                    except CalendarError as exc:
                        print(exc)
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
    print(f"Saved courses: {ctx.courses_path}")


def exception_command(args, ctx):
    if args.action == "list":
        from .storage import load_overrides
        for source, items in (("school", load_overrides(ctx.folder / "exceptions.csv", ctx.semester)), ("yours", ctx.exceptions())):
            for item in items:
                shift = "inherit" if item.time_shift_minutes is None else f"{item.time_shift_minutes:+} min"
                print(f"{item.date}: {item.action} {item.pattern} · {shift} · {source} · {item.note}")
        print("Applied only with --schedule exceptions. Your row replaces a school row on the same date.")
        return
    day = parse_date(args.date)
    expected = digest(ctx.exceptions_path)
    items = [item for item in ctx.exceptions() if item.date != day]
    if args.action == "set":
        if args.shift is not None and not args.follow:
            raise CalendarError("--shift requires --follow; use --late or --normal for the usual weekday.")
        action = "off" if args.off else "use" if args.follow else "adjust"
        shift = args.shift if args.follow else 20 if args.late else 0 if args.normal else None
        items.append(DayOverride(day, action, args.follow or "", shift, args.note))
    ctx.save_exceptions(items, expected)
    print(f"Saved exceptions: {ctx.exceptions_path}")


def semester_command(args, workspace):
    if args.action == "list":
        ids = workspace.semesters()
        active = workspace.settings()["active_semester"]
        for sid in ids:
            try:
                describe_semester(safe_child(workspace.root / "semesters", sid))
                state = "active" if sid == active else "ready"
            except CalendarError as exc:
                state = f"draft / invalid: {exc}"
            print(f"{sid} · {state}")
        if not ids:
            print("No semester definitions. Start with semester new ID --blocks X,Y,Z.")
    elif args.action == "new":
        folder = create_semester(workspace, args.id, blocks=args.blocks, name=args.name, timetable=args.timetable,
                                 copy_from=args.copy_from, weekdays=args.weekdays, utc_offset=args.utc_offset)
        if args.timetable or args.copy_from:
            print(f"Defined {args.id}. Review with semester show {args.id}, then select with semester use {args.id}.")
        else:
            print(f"Draft created. Fill {folder / 'timetable.csv'} with pattern,block,start,end rows.\nThen run semester use {args.id}. The draft cannot export yet.")
    elif args.action == "show":
        print(describe_semester(safe_child(workspace.root / "semesters", args.id)))
    else:
        ctx = workspace.use_semester(args.id, getattr(args, "profile", None))
        print(f"Using {ctx.semester.id} · blocks: {', '.join(ctx.semester.blocks)}\nEnter your courses: courses edit (or courses set BLOCK NAME).")


def main(argv=None):
    # Windows redirected streams may otherwise use a legacy code page, losing
    # Unicode course names even though the CSV and calendar are valid UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    cli = parser()
    args = cli.parse_args(arguments(list(sys.argv[1:] if argv is None else argv)))
    workspace = Workspace(getattr(args, "root", DEFAULT_ROOT))
    try:
        if args.command is None:
            cli.print_help()
            return 0
        if args.command == "semester":
            semester_command(args, workspace)
            return 0
        if args.command == "gui":
            from .gui import launch
            launch(workspace.root, semester_id=getattr(args, "semester", None), profile=getattr(args, "profile", None))
            return 0
        settings = workspace.settings()
        sid = workspace.selected_semester(getattr(args, "semester", None))
        profile = getattr(args, "profile", None) or settings["profile"]
        create = args.command == "init" or (args.command in {"courses", "exceptions"} and args.action not in {"list", "path"})
        ctx = workspace.context(profile, sid, create=create)
        if args.command == "init":
            print(f"Course CSV: {ctx.courses_path}")
        elif args.command == "courses":
            course_command(args, ctx)
        elif args.command == "exceptions":
            exception_command(args, ctx)
        else:
            preview = ctx.preview(command_settings(args))
            if args.command == "preview":
                print(preview_text(preview))
            elif args.command == "validate":
                print(f"Valid: {len(preview.events)} events, {preview.start} to {preview.end}, {preview.clock}")
            else:
                if not preview.events:
                    raise CalendarError("No classes in this range. Use courses list and preview --dayrange FIRST:LAST to check selections and dates.")
                output = ctx.export(preview, args.output, overwrite=args.overwrite)
                print(f"Exported {len(preview.events)} events · {preview.start} to {preview.end} · {preview.clock}\n{output}")
        return 0
    except (CalendarError, OSError, ImportError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled. Unsaved course inputs were discarded.")
        return 130
