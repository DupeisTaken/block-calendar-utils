"""Validated text files and atomic local saves, shared by both interfaces."""

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from dataclasses import asdict
from datetime import date, time, timedelta, timezone
from pathlib import Path

from .models import CalendarError, Course, DayOverride, Semester, Session

COURSE_FIELDS = ("block", "course", "location", "teacher", "enabled", "timing_option")
EXCEPTION_FIELDS = ("date", "action", "pattern", "time_shift_minutes", "note")
SESSION_FIELDS = ("pattern", "session_id", "block", "start", "end")


def safe_child(parent: Path, name: str) -> Path:
    """Restrict user-chosen directory names and also reject escaping symlinks."""
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10))}
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name) or name.upper() in reserved:
        raise CalendarError("Use a name of 1–64 letters, numbers, dashes or underscores (e.g. my-profile).")
    target = parent / name
    if not target.resolve().is_relative_to(parent.resolve()):
        raise CalendarError(f"Folder escapes its parent: {target}")
    return target


def parse_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise CalendarError(f"Use YYYY-MM-DD for dates, got {value!r}.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CalendarError(f"Invalid date: {value!r}.") from exc


def parse_time(value: str) -> time:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise CalendarError(f"Use HH:MM for times, got {value!r}.")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise CalendarError(f"Invalid time: {value!r}.") from exc


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        return value
    except (ValueError, OSError) as exc:
        raise CalendarError(f"{path}: {exc}") from exc


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def atomic_write(path: Path, data: bytes, *, overwrite: bool = True, backup: bool = False) -> None:
    """Stage in the destination directory; failed writes leave the original intact.

    Exclusive creation uses a hard link, avoiding the check-then-replace race
    that could overwrite another export created while this file was staged.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        raise CalendarError(f"{path} already exists. Choose another name or allow overwrite.")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".shbs-", delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if backup and path.exists():
            atomic_write(path.with_suffix(path.suffix + ".bak"), path.read_bytes())
        if overwrite:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
    except OSError as exc:
        raise CalendarError(f"Could not save {path}: {exc}") from exc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def write_json(path: Path, value: dict, *, backup: bool = False) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), backup=backup)


def csv_bytes(fields: tuple[str, ...], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def read_rows(path: Path, fields: tuple[str, ...], required: tuple[str, ...]) -> list[tuple[int, dict]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            header = reader.fieldnames or []
            if len(header) != len(set(header)) or not set(required).issubset(header) or set(header) - set(fields):
                raise CalendarError(f"{path}: expected columns {', '.join(fields)}; required: {', '.join(required)}.")
            rows = []
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise CalendarError(f"{path}:{reader.line_num}: wrong number of CSV fields.")
                rows.append((reader.line_num, {k: v.strip() for k, v in row.items()}))
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CalendarError(f"{path}: {exc}") from exc


def load_semester(folder: Path) -> Semester:
    config = read_json(folder / "semester.json")
    try:
        sid, name, blocks = config["id"], config["name"], config["blocks"]
        if sid != folder.name or not isinstance(name, str) or not name:
            raise CalendarError("id must match the semester folder; name must be nonempty.")
        if not isinstance(blocks, list) or not blocks or not all(isinstance(b, str) and b.strip() == b and b and not any(ord(c) < 32 for c in b) for b in blocks) or len(set(blocks)) != len(blocks):
            raise CalendarError("blocks must be a nonempty list of unique names.")
        offset = config["utc_offset_minutes"]
        if type(offset) is not int or not -1439 <= offset <= 1439:
            raise CalendarError("utc_offset_minutes must be an integer between -1439 and 1439.")
        clock = timezone(timedelta(minutes=offset))
        days = config["weekdays"]
        if not isinstance(days, dict) or not days or not all(k in [str(i) for i in range(7)] and isinstance(v, str) and v for k, v in days.items()):
            raise CalendarError("weekdays must map 0 (Monday) through 6 (Sunday) to pattern names.")
        weekdays = {int(k): v for k, v in days.items()}
        sessions = []
        seen = set()
        occurrences = {}
        for line, row in read_rows(folder / "timetable.csv", SESSION_FIELDS, ("pattern", "block", "start", "end")):
            try:
                # Simple CSVs need no technical IDs. Derive identity from block
                # occurrence, not clock times, so timing edits retain event IDs.
                key = (row["pattern"], row["block"])
                occurrences[key] = occurrences.get(key, 0) + 1
                automatic_id = "auto-" + hashlib.sha256(repr((*key, occurrences[key])).encode()).hexdigest()[:24]
                session = Session(row["pattern"], row.get("session_id") or automatic_id, row["block"], parse_time(row["start"]), parse_time(row["end"]))
                if not session.pattern or not session.session_id or session.session_id in seen:
                    raise CalendarError("pattern and globally unique session_id are required.")
                if session.block not in blocks or session.start >= session.end:
                    raise CalendarError("unknown block or end not after start.")
                seen.add(session.session_id)
                sessions.append(session)
            except CalendarError as exc:
                raise CalendarError(f"timetable.csv:{line}: {exc}") from exc
        from .activities import load_activity_schedule
        activities, activity_sessions = load_activity_schedule(folder, blocks, sessions)
        patterns = {s.pattern for s in (*sessions, *activity_sessions)}
        if not sessions or set(weekdays.values()) - patterns:
            raise CalendarError("timetable is empty or weekdays refer to an unknown pattern.")
        if set(blocks) - {s.block for s in sessions}:
            raise CalendarError("Add timetable rows for every defined block: " + ", ".join(sorted(set(blocks) - {s.block for s in sessions})))
        options = config.get("timing_options", {})
        if not isinstance(options, dict) or set(options) - set(blocks):
            raise CalendarError("timing_options must map known blocks to choices.")
        by_id = {s.session_id: s for s in sessions}
        for block, choices in options.items():
            if not isinstance(choices, dict) or not choices:
                raise CalendarError(f"{block}: timing options must contain named choices.")
            for choice, overrides in choices.items():
                if not choice or not isinstance(overrides, dict):
                    raise CalendarError(f"{block}: invalid timing choice.")
                for session_id, times in overrides.items():
                    if session_id not in by_id or by_id[session_id].block != block or not isinstance(times, dict) or not times or set(times) - {"start", "end"}:
                        raise CalendarError(f"{block}/{choice}: invalid session override {session_id}.")
                    s = by_id[session_id]
                    start = parse_time(times["start"]) if "start" in times else s.start
                    end = parse_time(times["end"]) if "end" in times else s.end
                    if end <= start:
                        raise CalendarError(f"{session_id}: timing option ends before it starts.")
        return Semester(sid, name, clock, tuple(blocks), weekdays, tuple(sessions), options, activities, activity_sessions)
    except (KeyError, TypeError, ValueError) as exc:
        raise CalendarError(f"{folder}: {exc}") from exc


def validate_courses(courses: list[Course], semester: Semester) -> None:
    seen = set()
    for row, course in enumerate(courses, 2):
        for value in (course.course, course.location, course.teacher):
            if any(ord(char) < 32 and char not in "\t\r\n" for char in value):
                raise CalendarError(f"courses.csv:{row}: remove unsupported control characters from the text.")
        if course.block not in semester.blocks or course.block in seen:
            raise CalendarError(f"courses.csv:{row}: duplicate or unknown block {course.block!r}.")
        seen.add(course.block)
        if course.enabled and not course.course.strip():
            raise CalendarError(f"courses.csv:{row}: {course.block} is enabled but has no course name.")
        choices = semester.timing_options.get(course.block, {})
        if (course.timing_option and course.timing_option not in choices) or (course.enabled and choices and not course.timing_option):
            raise CalendarError(f"courses.csv:{row}: {course.block} timing_option must be one of {', '.join(choices)}.")


def load_courses(path: Path, semester: Semester) -> list[Course]:
    courses = []
    for line, row in read_rows(path, COURSE_FIELDS, ("block", "course")):
        enabled = row.get("enabled", "true" if row["course"] else "false").lower()
        if enabled not in {"true", "false", "1", "0", "yes", "no"}:
            raise CalendarError(f"{path}:{line}: enabled must be true or false.")
        courses.append(Course(row["block"], row["course"], row.get("location", ""), row.get("teacher", ""), enabled in {"true", "1", "yes"}, row.get("timing_option", "")))
    validate_courses(courses, semester)
    by_block = {c.block: c for c in courses}
    return [by_block.get(block, Course(block)) for block in semester.blocks]


def save_courses(path: Path, courses: list[Course], semester: Semester, expected: str | None) -> None:
    validate_courses(courses, semester)
    if digest(path) != expected:
        raise CalendarError("Courses changed on disk. Reload before saving to keep those edits.")
    rows = [dict(asdict(c), enabled=str(c.enabled).lower()) for c in courses]
    atomic_write(path, csv_bytes(COURSE_FIELDS, rows), backup=True)


def validate_overrides(overrides: list[DayOverride], semester: Semester) -> None:
    seen = set()
    for row, item in enumerate(overrides, 2):
        if item.date in seen:
            raise CalendarError(f"exceptions.csv:{row}: duplicate date {item.date}.")
        seen.add(item.date)
        if item.action not in {"off", "use", "adjust"}:
            raise CalendarError(f"exceptions.csv:{row}: action must be off, use, or adjust.")
        if item.action == "use" and item.pattern not in semester.patterns:
            raise CalendarError(f"exceptions.csv:{row}: unknown pattern {item.pattern!r}.")
        if item.action != "use" and item.pattern:
            raise CalendarError(f"exceptions.csv:{row}: only use accepts a pattern.")
        if item.action == "off" and item.time_shift_minutes is not None:
            raise CalendarError(f"exceptions.csv:{row}: off cannot have a time shift.")
        if item.action == "adjust" and item.time_shift_minutes is None:
            raise CalendarError(f"exceptions.csv:{row}: adjust needs a time shift (0 means normal).")
        if item.time_shift_minutes is not None and (type(item.time_shift_minutes) is not int or not -720 <= item.time_shift_minutes <= 720):
            raise CalendarError(f"exceptions.csv:{row}: shift must be a whole number from -720 to 720.")


def load_overrides(path: Path, semester: Semester) -> list[DayOverride]:
    if not path.exists():
        return []
    items = []
    for line, row in read_rows(path, EXCEPTION_FIELDS, ("date", "action")):
        try:
            shift = row.get("time_shift_minutes", "")
            items.append(DayOverride(parse_date(row["date"]), row["action"], row.get("pattern", ""), int(shift) if shift else None, row.get("note", "")))
        except ValueError as exc:
            raise CalendarError(f"{path}:{line}: {exc}") from exc
    validate_overrides(items, semester)
    return items


def save_overrides(path: Path, items: list[DayOverride], semester: Semester, expected: str | None) -> None:
    validate_overrides(items, semester)
    if digest(path) != expected:
        raise CalendarError("Exceptions changed on disk. Reload before saving.")
    rows = [dict(asdict(i), date=i.date.isoformat(), time_shift_minutes="" if i.time_shift_minutes is None else i.time_shift_minutes) for i in sorted(items, key=lambda i: i.date)]
    atomic_write(path, csv_bytes(EXCEPTION_FIELDS, rows), backup=True)
