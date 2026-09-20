"""Resolve actual dates into concrete occurrences before serializing calendars."""

from datetime import date, datetime, timedelta
from uuid import UUID, uuid5

from .models import Activity, CalendarError, Course, DayOverride, Event, Preview, Semester
from .storage import parse_date, parse_time, validate_courses, validate_overrides


def date_range(mode: str, anchor: str = "", weeks: int = 1, end: str = "", *, today: date | None = None) -> tuple[date, date]:
    """Relative presets resolve afresh; a single day has identical endpoints."""
    today = today or date.today()
    if type(weeks) is not int or not 1 <= weeks <= 520:
        raise CalendarError("Choose between 1 and 520 weeks.")
    try:
        if mode == "day":
            first = last = parse_date(anchor)
        elif mode == "custom":
            first, last = parse_date(anchor), parse_date(end)
        elif mode in {"this", "next", "week"}:
            day = parse_date(anchor) if mode == "week" else today
            first = day - timedelta(days=day.weekday())
            if mode == "next":
                first += timedelta(days=7)
            last = first + timedelta(days=7 * weeks - 1)
        else:
            raise CalendarError("Choose day, this, next, week, or custom for the date range.")
    except OverflowError as exc:
        raise CalendarError("That range goes beyond supported calendar dates.") from exc
    if first > last:
        raise CalendarError("The end date must be on or after the start date.")
    if (last - first).days >= 3660:
        raise CalendarError("Export at most 3,660 days at a time.")
    return first, last


def build_preview(semester: Semester, courses: list[Course], profile_id: str, first: date, last: date,
                  shift: int = 0, school: list[DayOverride] = (), personal: list[DayOverride] = (),
                  *, activities: list[Activity] = ()) -> Preview:
    validate_courses(courses, semester)
    from .activities import validate_activities
    validate_activities(activities, semester)
    validate_overrides(school, semester)
    validate_overrides(personal, semester)
    if first > last or (last - first).days >= 3660:
        raise CalendarError("Choose an ordered range of at most 3,660 days.")
    if type(shift) is not int or not -720 <= shift <= 720:
        raise CalendarError("Time shift must be a whole number between -720 and 720.")
    try:
        namespace = UUID(profile_id)
    except (ValueError, TypeError) as exc:
        raise CalendarError("Invalid profile identity. Restore profile.json from a backup.") from exc
    selected = {c.block: c for c in courses if c.enabled}
    selected.update({a.activity: Course(a.activity, "CAS" if semester.activities[a.activity] == "cas" else a.name, a.location, enabled=True) for a in activities if a.enabled})
    school_by_date = {i.date: i for i in school}
    overrides = school_by_date | {i.date: i for i in personal}
    replaced = set(school_by_date) & {i.date for i in personal}
    patterns = {name: [s for s in semester.sessions + semester.activity_sessions if s.pattern == name] for name in semester.patterns}
    events, notes = [], []
    # Iterate offsets so even date.max is safe (no increment past the last day).
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        pattern = semester.weekdays.get(day.weekday())
        effective_shift = shift
        override = overrides.get(day)
        if override:
            detail = f"{day}: {override.action}"
            if day in replaced:
                detail += " (personal override replaces school exception)"
            if override.pattern:
                detail += f" {override.pattern}"
            if override.time_shift_minutes is not None:
                effective_shift = override.time_shift_minutes
                detail += f"; shift {effective_shift:+d} min"
            if override.note:
                detail += f" — {override.note}"
            if override.half_day:
                detail += f"; {override.half_day} (cutoff {semester.noon_cutoff:%H:%M})"
            notes.append(detail)
            if override.action == "off":
                continue
            if override.action == "use":
                pattern = override.pattern
            elif override.action == "adjust" and not pattern:
                raise CalendarError(f"{day}: no normal classes to adjust. Use a weekday pattern for a makeup day.")
        if not pattern:
            continue
        day_events = []
        for session in patterns[pattern]:
            course = selected.get(session.block)
            if course is None:
                continue
            times = semester.timing_options.get(course.block, {}).get(course.timing_option, {}).get(session.session_id, {})
            start_time = parse_time(times["start"]) if "start" in times else session.start
            end_time = parse_time(times["end"]) if "end" in times else session.end
            try:
                start = datetime.combine(day, start_time, semester.clock) + timedelta(minutes=effective_shift)
                end = datetime.combine(day, end_time, semester.clock) + timedelta(minutes=effective_shift)
            except OverflowError as exc:
                raise CalendarError(f"{day}: shifted time is outside the supported date range.") from exc
            if start.date() != day or end.date() != day or end <= start:
                raise CalendarError(f"{day}/{session.session_id}: shift crosses midnight or interval is invalid.")
            # Classify whole sessions by their effective local start time. A
            # lesson crossing the cutoff is never shortened into half a lesson.
            if override and ((override.half_day == "no-morning" and start.time() < semester.noon_cutoff)
                             or (override.half_day == "no-afternoon" and start.time() >= semester.noon_cutoff)):
                continue
            # Length-prefixed JSON-like components avoid ambiguous name joins.
            key = f"{len(semester.id)}:{semester.id}:{day}:{session.session_id}"
            uid = str(uuid5(namespace, key)) + "@shbs-calendar.local"
            # Calendar entries contain the selected name, times and location.
            # Keep scheduling explanations in the preview, not event notes.
            day_events.append(Event(uid, course.block, course.course, start, end, course.location))
        day_events.sort(key=lambda e: (e.start, e.uid))
        for before, after in zip(day_events, day_events[1:]):
            if before.end > after.start:
                raise CalendarError(f"{day}: {before.block} ({before.title}) overlaps {after.block} ({after.title}). Check the timetable/timing options.")
        events.extend(day_events)
    excluded = [b for b in semester.blocks if b not in selected]
    return Preview(events, notes, excluded, first, last, str(semester.clock))


def preview_text(preview: Preview, *, width: int | None = None) -> str:
    lines = [f"{preview.start} to {preview.end} · {len(preview.events)} events · {preview.clock}"]
    if preview.schedule_mode == "weekdays":
        lines.append("Schedule: normal weekdays. Saved exceptions are not applied to this export.")
    elif preview.schedule_mode == "exceptions":
        lines.append("Schedule: weekdays with your date exceptions.")
    elif preview.schedule_mode == "inline":
        lines.append("Schedule: weekdays with this command's exceptions. Saved exception files are not applied.")
    if preview.excluded:
        lines.append("Unselected blocks: " + ", ".join(preview.excluded))
    if preview.notes:
        lines.extend(["", "Date exceptions:", *preview.notes])
    if width is not None:
        if not 20 <= width <= 300:
            raise CalendarError("Preview width must be between 20 and 300 columns.")
        from .terminal import day_columns
        return day_columns(preview, lines, width)
    current = None
    for event in preview.events:
        day = event.start.date()
        if day != current:
            lines.extend(["", event.start.strftime("%A, %d %B %Y")])
            current = day
        # Keep each title on one line in the preview; preserve original in ICS.
        title = " ".join(event.title.splitlines())
        place = f"  · {event.location}" if event.location else ""
        lines.append(f"  {event.start:%H:%M}–{event.end:%H:%M}  {event.block:<3} {title}{place}")
    if not preview.events:
        lines.append("\nNo events in this range. Check course selections and date exceptions.")
    return "\n".join(lines)
