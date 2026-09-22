"""Terminal timetable editing: argument batches or a cancellable draft session."""

from .help_style import ask, emit
from .models import CalendarError
from .semester_editor import SemesterDraft

SETTINGS = ("name", "blocks", "weekdays", "utc_offset", "noon_cutoff")


def add_editor_arguments(parser):
    parser.add_argument("id", help="Semester to edit, including a new draft")
    for flag, hint in (("name", "Display name"), ("blocks", "Complete comma-separated block list"),
                       ("weekdays", "Complete weekday mapping, e.g. mon=red,tue=blue"),
                       ("utc-offset", "Fixed school clock, e.g. +08:00"), ("noon-cutoff", "Half-day cutoff, HH:MM")):
        parser.add_argument("--" + flag, help=hint)
    parser.add_argument("--session", nargs=5, action="append", default=[], metavar=("ID", "PATTERN", "BLOCK", "START", "END"), help="Add/replace a class interval; repeat for more")
    parser.add_argument("--activity", nargs=6, action="append", default=[], metavar=("ID", "PATTERN", "ACTIVITY", "KIND", "START", "END"), help="Add/replace a school cas/club interval")
    parser.add_argument("--timing-option", nargs=5, action="append", default=[], metavar=("BLOCK", "CHOICE", "SESSION", "START", "END"), help="Add/replace a duration override; - inherits a time; repeat for more")
    parser.add_argument("--remove-session", action="append", default=[], metavar="ID", help="Remove a class interval")
    parser.add_argument("--remove-activity", action="append", default=[], metavar="ID", help="Remove a school activity interval")
    parser.add_argument("--remove-timing", nargs=2, action="append", default=[], metavar=("BLOCK", "CHOICE"), help="Remove an entire timing choice")


def preflight(args):
    """Reject local syntax errors before any earlier workflow stage writes."""
    from .storage import parse_time
    from .semesters import weekday_map, utc_minutes
    if args.name is not None and not args.name.strip():
        raise CalendarError("Semester name cannot be blank.")
    if args.blocks is not None:
        blocks = [value.strip() for value in args.blocks.split(",")]
        if not all(blocks) or len(blocks) != len(set(blocks)) or any(any(ord(c) < 32 for c in value) for value in blocks):
            raise CalendarError("Use unique, nonempty comma-separated block keys.")
    if args.weekdays is not None:
        weekday_map(args.weekdays)
    if args.utc_offset is not None:
        utc_minutes(args.utc_offset)
    if args.noon_cutoff is not None:
        parse_time(args.noon_cutoff)
    for rows in (args.session, args.activity):
        ids = [row[0] for row in rows]
        if len(ids) != len(set(ids)):
            raise CalendarError("Specify each session ID only once in an edit batch.")
        for row in rows:
            if parse_time(row[-2]) >= parse_time(row[-1]):
                raise CalendarError("Session end must be after start.")
    for row in args.activity:
        if row[3] not in {"cas", "club"}:
            raise CalendarError("Activity kind must be cas or club.")
    for _, _, _, start, end in args.timing_option:
        for value in (start, end):
            if value != "-":
                parse_time(value)
    timing_keys = [(b, c.replace("-", "_"), s) for b, c, s, _, _ in args.timing_option]
    if len(timing_keys) != len(set(timing_keys)):
        raise CalendarError("Specify each timing override only once in an edit batch.")
    for rows, removed in ((args.session, args.remove_session), (args.activity, args.remove_activity)):
        if {r[0] for r in rows} & set(removed):
            raise CalendarError("Cannot replace and remove the same session in one batch.")
    if {(r[0], r[1].replace('-', '_')) for r in args.timing_option} & {(b, c.replace('-', '_')) for b, c in args.remove_timing}:
        raise CalendarError("Cannot set and remove the same timing choice in one batch.")


def show(draft):
    emit("\nTimetable draft\n")
    for key, value in draft.settings().items():
        emit(f"  {key.replace('_', ' '):<14} {value}")
    for heading, rows, fields in (("Classes", draft.sessions, ("session_id", "pattern", "block", "start", "end")),
                                   ("CAS & clubs", draft.activities, ("session_id", "pattern", "activity", "kind", "start", "end"))):
        emit(f"\n{heading}\n")
        for row in rows:
            emit("  " + " · ".join(row[key] for key in fields))
        if not rows:
            emit("  No sessions yet.")
    emit("\nTiming choices\n")
    for block, choices in draft.config.get("timing_options", {}).items():
        for choice, overrides in choices.items():
            emit(f"  {block} · {choice}")
            for sid, times in overrides.items():
                emit(f"    {sid}: {times.get('start', 'inherit')}–{times.get('end', 'inherit')}")


def prompt_fields(labels, old=None):
    old = old or [""] * len(labels)
    return [ask(f"  {label} [{value}]: ").strip() or value for label, value in zip(labels, old)]


def interactive(draft):
    show(draft)
    emit("\n  Changes stay in this draft until save. Enter keeps a field; Ctrl+C cancels.")
    emit("  Actions: settings, class, activity, timing, remove-class, remove-activity,")
    emit("           remove-timing, show, save, cancel\n")
    while True:
        action = ask("  Edit: ").strip().lower()
        try:
            if action == "cancel":
                raise KeyboardInterrupt
            if action == "save":
                draft.save()
                return
            if action == "show":
                show(draft)
            elif action == "settings":
                old = draft.settings()
                draft.update_settings(**dict(zip(SETTINGS, prompt_fields([k.replace('_', ' ') for k in SETTINGS], [old[k] for k in SETTINGS]))))
            elif action in {"class", "activity"}:
                activity = action == "activity"
                sid = ask("  Session ID (existing to edit, new to add): ").strip()
                fields = ("pattern", "activity", "kind", "start", "end") if activity else ("pattern", "block", "start", "end")
                old = next((row for row in (draft.activities if activity else draft.sessions) if row["session_id"] == sid), {})
                draft.put_session([sid, *prompt_fields(fields, [old.get(f, "") for f in fields])], activity=activity)
            elif action == "timing":
                emit("  Use - to inherit a time; session - creates a choice with no overrides.")
                draft.put_timing(*prompt_fields(("Block", "Choice", "Session", "Start", "End")))
            elif action in {"remove-class", "remove-activity"}:
                draft.remove_session(ask("  Session ID: ").strip(), activity=action == "remove-activity")
            elif action == "remove-timing":
                draft.remove_timing(*prompt_fields(("Block", "Choice")))
            elif action != "show":
                emit("  Choose an action above. Use save to finish, or cancel to discard.")
        except CalendarError as exc:
            emit(f"\n  {exc}\n")


def edit_semester(args, workspace):
    preflight(args)
    draft = SemesterDraft(workspace, args.id)
    supplied = any(getattr(args, key) is not None for key in SETTINGS) or any((args.session, args.activity, args.timing_option, args.remove_session, args.remove_activity, args.remove_timing))
    if not supplied:
        interactive(draft)
    else:
        draft.update_settings(**{key: getattr(args, key) for key in SETTINGS})
        for row in args.session:
            draft.put_session(row)
        for row in args.activity:
            draft.put_session(row, activity=True)
        for row in args.timing_option:
            draft.put_timing(*row)
        for sid in args.remove_session:
            draft.remove_session(sid)
        for sid in args.remove_activity:
            draft.remove_session(sid, activity=True)
        for row in args.remove_timing:
            draft.remove_timing(*row)
        draft.save()
    emit(f"\nSaved timetable: {args.id}\n\n  Review: --inspect --semesters --show {args.id}")
