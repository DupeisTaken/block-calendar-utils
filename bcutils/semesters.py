"""Shared semester definitions; drafts must validate before they can be used."""

import re
import tempfile
from pathlib import Path

from .models import CalendarError
from .storage import (EXCEPTION_FIELDS, atomic_write, csv_bytes, load_overrides,
                      load_semester, parse_time, read_json, safe_child, write_json)

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
SIMPLE_FIELDS = ("pattern", "block", "start", "end")
TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "examples" / "semesters"


def templates():
    """Examples are opt-in sources, never installed or activated on startup."""
    return sorted(p.parent.name for p in TEMPLATE_ROOT.glob("*/semester.json"))


def weekday_map(value):
    if value is None:
        return {str(i): day for i, day in enumerate(DAYS[:5])}
    result = {}
    aliases = {name: str(i) for i, day in enumerate(DAYS) for name in (day, day[:3])}
    for pair in value.split(","):
        day, sep, pattern = pair.partition("=")
        key = aliases.get(day.strip().lower())
        if not sep or key is None or not pattern.strip() or key in result:
            raise CalendarError("Use --weekdays mon=red,tue=blue (each weekday once; omitted days have no classes).")
        result[key] = pattern.strip()
    return result


def utc_minutes(value):
    if not re.fullmatch(r"[+-]\d{2}:\d{2}", value):
        raise CalendarError("Use --utc-offset +08:00 or --utc-offset=-05:00 (fixed school clock).")
    hours, minutes = map(int, value[1:].split(":"))
    if hours > 23 or minutes > 59:
        raise CalendarError("Invalid UTC offset.")
    return (hours * 60 + minutes) * (-1 if value.startswith("-") else 1)


def create_semester(workspace, sid, *, blocks=None, name=None, timetable=None,
                    copy_from=None, weekdays=None, utc_offset=None, noon_cutoff=None, template=None):
    """Stage supplied data together; a failed import cannot leave a half-definition."""
    parent = workspace.root / "semesters"
    target = safe_child(parent, sid)
    if target.exists():
        raise CalendarError(f"Semester {sid!r} already exists. Edit its files or choose a new ID.")
    if copy_from and template:
        raise CalendarError("Choose either --copy or --template.")
    if copy_from or template:
        if any(value is not None for value in (blocks, timetable, weekdays, utc_offset, noon_cutoff)):
            raise CalendarError("--copy/--template cannot be combined with --blocks, --timetable, --weekdays, --utc-offset or --noon-cutoff.")
        source = safe_child(TEMPLATE_ROOT if template else parent, template or copy_from)
        load_semester(source)
        config = read_json(source / "semester.json")
        data = (source / "timetable.csv").read_bytes()
        # Date exceptions and student courses never carry into another semester.
    else:
        names = [b.strip() for b in (blocks or "").split(",")]
        if not all(names) or len(set(names)) != len(names) or any(any(ord(c) < 32 for c in b) for b in names):
            raise CalendarError("Define unique block names with --blocks X,Y,Z, or reuse a timetable with --copy ID.")
        config = dict(blocks=names, weekdays=weekday_map(weekdays),
                      utc_offset_minutes=utc_minutes(utc_offset or "+08:00"), noon_cutoff=parse_time(noon_cutoff or "12:30").strftime("%H:%M"))
        data = Path(timetable).read_bytes() if timetable else csv_bytes(SIMPLE_FIELDS, [])
    config.update(id=sid, name=name or sid)
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".semester-", dir=parent) as tmp:
        staged = Path(tmp) / sid
        write_json(staged / "semester.json", config)
        atomic_write(staged / "timetable.csv", data)
        atomic_write(staged / "exceptions.csv", csv_bytes(EXCEPTION_FIELDS, []))
        if (copy_from or template) and (source / "activities.csv").exists():
            atomic_write(staged / "activities.csv", (source / "activities.csv").read_bytes())
        if timetable or copy_from or template:
            load_semester(staged)
        staged.rename(target)
    return target


def describe_semester(folder):
    semester = load_semester(folder)
    load_overrides(folder / "exceptions.csv", semester)
    lines = [f"{semester.id} · {semester.name} · {semester.clock}",
             "Blocks: " + ", ".join(semester.blocks), f"Half-day cutoff: {semester.noon_cutoff:%H:%M}", "Weekdays:"]
    lines += [f"  {DAYS[i].title()}: {semester.weekdays.get(i, 'no classes')}" for i in range(7)]
    lines.append("Timetable:")
    for pattern in semester.patterns:
        lines.append(f"  {pattern}")
        lines += [f"    {s.start:%H:%M}–{s.end:%H:%M}  {s.block} · {s.session_id}" for s in sorted(semester.sessions, key=lambda s: s.start) if s.pattern == pattern]
    for block, choices in semester.timing_options.items():
        lines.append(f"Timing choices for {block}: " + ", ".join(key.replace("_", "-") for key in choices))
        by_id = {s.session_id: s for s in semester.sessions}
        for choice, overrides in choices.items():
            for sid, times in overrides.items():
                session = by_id[sid]
                start = times.get("start", session.start.strftime("%H:%M"))
                end = times.get("end", session.end.strftime("%H:%M"))
                lines.append(f"    {choice.replace('_', '-')} · {sid}: {start}–{end}")
    if semester.activity_sessions:
        lines.append("Optional activities (named clubs on; CAS opt-in):")
        lines += [f"  {s.block} ({semester.activities[s.block]}) · {s.pattern} {s.start:%H:%M}–{s.end:%H:%M} · {s.session_id}" for s in semester.activity_sessions]
    return "\n".join(lines)
