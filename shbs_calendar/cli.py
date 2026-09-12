"""A short numbered workflow plus noninteractive commands for repeat exports."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .app import DEFAULT_ROOT, Workspace
from .models import CalendarError, DayOverride
from .schedule import preview_text
from .storage import digest, parse_date


def ask(label, default=""):
    suffix = f" [{default}]" if str(default) else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or str(default)


def choose(label, options, default=0):
    print(f"\n{label}")
    for i, option in enumerate(options, 1):
        print(f"  {i} {option}")
    while True:
        answer = ask("Choice", default + 1)
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"Enter a number from 1 to {len(options)}.")


def edit_courses(ctx, *, first_run=False):
    courses = ctx.courses()
    expected = digest(ctx.courses_path)

    def edit(index):
        old = courses[index]
        name = ask(f"{old.block} course (- clears)", old.course)
        name = "" if name == "-" else name
        option = old.timing_option
        choices = list(ctx.semester.timing_options.get(old.block, {}))
        if name and choices:
            default = choices.index(option) if option in choices else 0
            option = choices[choose(f"{old.block} timing", [c.replace("_", " ").title() for c in choices], default)]
        courses[index] = replace(old, course=name, enabled=bool(name), timing_option=option)

    if first_run:
        print("\nEnter your courses once. Leave a block blank to skip it; enter Study Hall to include it.")
        for index in range(len(courses)):
            edit(index)
        ctx.save_courses(courses, expected)
        print(f"Saved {ctx.courses_path}")
        return
    while True:
        print("\nYour courses (0 saves and returns)")
        for i, c in enumerate(courses, 1):
            option = f" · {c.timing_option.replace('_', ' ')}" if c.timing_option else ""
            print(f"  {i:>2} {c.block:<3} {c.course or '—'}{' (disabled)' if c.course and not c.enabled else ''}{option}")
        answer = ask("Block number", "0")
        if answer == "0":
            if courses != ctx.courses():
                ctx.save_courses(courses, expected)
            return
        if not answer.isdigit() or not 1 <= int(answer) <= len(courses):
            print("Enter one of the block numbers.")
            continue
        index = int(answer) - 1
        action = choose("Edit", ["Course name / timing", "Room and teacher", "Enable / disable"])
        if action == 0:
            edit(index)
        elif action == 1:
            old = courses[index]
            room, teacher = ask("Room (- clears)", old.location), ask("Teacher (- clears)", old.teacher)
            courses[index] = replace(old, location="" if room == "-" else room, teacher="" if teacher == "-" else teacher)
        else:
            old = courses[index]
            courses[index] = replace(old, enabled=not old.enabled)


def edit_dates(settings):
    modes = ["this", "next", "week", "custom"]
    current = settings.get("mode", "this")
    mode = modes[choose("Export dates", ["This week", "Next week", "Choose a week / several weeks", "Custom start and end"], modes.index(current) if current in modes else 0)]
    result = dict(settings, mode=mode)
    if mode == "week":
        result["anchor"] = ask("Any date in the first week (YYYY-MM-DD)", settings.get("anchor", ""))
    if mode in {"this", "next", "week"}:
        result["weeks"] = int(ask("Number of weeks", settings.get("weeks", 1)))
    else:
        result["anchor"] = ask("Start (YYYY-MM-DD)", settings.get("anchor", ""))
        result["end"] = ask("End, included (YYYY-MM-DD)", settings.get("end", ""))
    result["late"] = bool(choose("Timing", ["Normal", "Late (+20 minutes)"], int(settings.get("late", False))))
    return result


def edit_exceptions(ctx):
    while True:
        items = ctx.exceptions()
        print("\nYour date exceptions")
        for item in items:
            shift = "inherit" if item.time_shift_minutes is None else str(item.time_shift_minutes)
            print(f"  {item.date}: {item.action} {item.pattern} · shift {shift} · {item.note}")
        print("School exceptions, if any, are also applied; your row takes precedence.")
        action = choose("Exceptions", ["Add / replace a date", "Remove a date", "Back"], 2)
        if action == 2:
            return
        day = parse_date(ask("Date (YYYY-MM-DD)"))
        expected = digest(ctx.exceptions_path)
        items = [item for item in items if item.date != day]
        if action == 0:
            kind = ["off", "use", "adjust"][choose("What happens?", ["No classes", "Use another day's pattern", "Change timing only"])]
            pattern, shift = "", None
            if kind == "use":
                patterns = ctx.semester.patterns
                pattern = patterns[choose("Use this pattern", [p.title() for p in patterns])]
            if kind != "off":
                selected = choose("Timing for this date", ["Inherit export setting", "Normal", "Late (+20 min)"] if kind == "use" else ["Normal", "Late (+20 min)"])
                shift = [None, 0, 20][selected] if kind == "use" else [0, 20][selected]
            items.append(DayOverride(day, kind, pattern, shift, ask("Note (optional)")))
        ctx.save_exceptions(items, expected)


def menu(workspace):
    settings = workspace.settings()
    ctx = workspace.context(settings["profile"], settings["semester"], create=True)
    workspace.save_settings(settings)
    if not any(c.course for c in ctx.courses()):
        edit_courses(ctx, first_run=True)
    while True:
        print(f"\nSHBS Calendar · {ctx.semester.name} · {ctx.profile}")
        print("  1 Export calendar\n  2 Edit courses\n  3 Dates and timing\n  4 Date exceptions\n  5 Preview timetable\n  6 Semester / profile\n  7 Open GUI\n  0 Quit")
        action = ask("Choice", "1")
        try:
            if action == "0":
                return 0
            if action in {"1", "5"}:
                preview = ctx.preview(settings)
                print("\n" + preview_text(preview))
                if action == "1" and ask("Export? (y/n)", "y").lower() == "y":
                    default = workspace.root / "exports" / f"{ctx.profile}-{ctx.semester.id}-{preview.start}-{preview.end}.ics"
                    output = Path(ask("Save as", str(default))).expanduser()
                    overwrite = output.exists() and ask("Replace existing file? (y/n)", "n").lower() == "y"
                    if output.exists() and not overwrite:
                        print("Export cancelled.")
                        continue
                    print(f"Saved {ctx.export(preview, output, overwrite=overwrite)}")
            elif action == "2":
                edit_courses(ctx)
            elif action == "3":
                candidate = edit_dates(settings)
                preview = ctx.preview(candidate)
                settings = candidate
                workspace.save_settings(settings)
                print(f"Saved: {preview.start} to {preview.end} · {'Late' if settings['late'] else 'Normal'}")
            elif action == "4":
                edit_exceptions(ctx)
            elif action == "6":
                semesters = workspace.semesters()
                semester = semesters[choose("Semester", semesters, semesters.index(settings["semester"]))]
                profile = ask("Profile name", settings["profile"])
                candidate = workspace.context(profile, semester, create=True)
                candidate.courses()  # Validate before switching the saved context.
                ctx = candidate
                settings.update(profile=profile, semester=semester)
                workspace.save_settings(settings)
                if not any(c.course for c in ctx.courses()):
                    edit_courses(ctx, first_run=True)
            elif action == "7":
                from .gui import launch
                launch(workspace.root)
                settings = workspace.settings()
                ctx = workspace.context(settings["profile"], settings["semester"])
            else:
                print("Choose a number from 0 to 7.")
        except (CalendarError, OSError, ValueError) as exc:
            print(f"Please check: {exc}")


def parser():
    result = argparse.ArgumentParser(description="Export SHBS classes and study periods. Run without a command for the menu.")
    result.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Project/data folder (default: this checkout)")
    subs = result.add_subparsers(dest="command")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", help="Saved profile name")
    common.add_argument("--semester", help="Semester folder name")
    subs.add_parser("gui", help="Open the simple desktop interface")
    subs.add_parser("init", parents=[common], help="Create blank course CSVs without prompting")
    dates = argparse.ArgumentParser(add_help=False)
    group = dates.add_mutually_exclusive_group()
    group.add_argument("--week", metavar="YYYY-MM-DD", help="Any date in the first week")
    group.add_argument("--start", metavar="YYYY-MM-DD", help="Inclusive custom start")
    group.add_argument("--this-week", action="store_true")
    group.add_argument("--next-week", action="store_true")
    dates.add_argument("--end", metavar="YYYY-MM-DD", help="Inclusive custom end; requires --start")
    dates.add_argument("--weeks", type=int, help="Week count for a week preset")
    timing = dates.add_mutually_exclusive_group()
    timing.add_argument("--late", action="store_true", default=None)
    timing.add_argument("--normal", action="store_true")
    for cmd in ("preview", "validate", "export"):
        sub = subs.add_parser(cmd, parents=[common, dates])
        if cmd == "export":
            sub.add_argument("--output", "-o", type=Path)
            sub.add_argument("--overwrite", action="store_true")
    return result


def command_settings(args, settings):
    """Explicit CLI date flags override saved presets without modifying them."""
    result = dict(settings)
    if args.end and not args.start or args.start and not args.end:
        raise CalendarError("Provide --start and --end together.")
    if args.start and args.weeks is not None:
        raise CalendarError("--weeks applies to week presets, not a custom range.")
    if args.week:
        result.update(mode="week", anchor=args.week, weeks=1)
    elif args.start:
        result.update(mode="custom", anchor=args.start, end=args.end)
    elif args.this_week or args.next_week:
        result.update(mode="next" if args.next_week else "this", weeks=1)
    if args.weeks is not None:
        if result["mode"] == "custom":
            raise CalendarError("Use --week, --this-week or --next-week with --weeks.")
        result["weeks"] = args.weeks
    if args.late:
        result["late"] = True
    if args.normal:
        result["late"] = False
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    workspace = Workspace(args.root)
    try:
        if args.command == "gui":
            from .gui import launch
            launch(args.root)
            return 0
        if args.command is None:
            return menu(workspace)
        settings = workspace.settings()
        profile, semester = args.profile or settings["profile"], args.semester or settings["semester"]
        ctx = workspace.context(profile, semester, create=args.command == "init")
        if args.command == "init":
            settings.update(profile=profile, semester=semester)
            workspace.save_settings(settings)
            print(f"Edit your courses: {ctx.courses_path}")
            return 0
        settings = command_settings(args, settings)
        preview = ctx.preview(settings)
        if args.command == "preview":
            print(preview_text(preview))
        elif args.command == "validate":
            print(f"Valid: {len(preview.events)} events, {preview.start} to {preview.end}, {preview.clock}")
        else:
            output = ctx.export(preview, args.output, overwrite=args.overwrite)
            print(f"Saved {len(preview.events)} events: {output}")
        return 0
    except (CalendarError, OSError, ImportError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled. Any unsaved edits were discarded.")
        return 130
