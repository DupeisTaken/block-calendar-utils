"""Optional semester activities and local club names, separate from class blocks."""

from dataclasses import asdict

from .models import Activity, CalendarError, Session
from .storage import atomic_write, csv_bytes, digest, parse_time, read_rows

SCHEDULE_FIELDS = ("pattern", "session_id", "activity", "kind", "start", "end")
SELECTION_FIELDS = ("activity", "name", "enabled", "location")


def load_activity_schedule(folder, blocks, class_sessions):
    path = folder / "activities.csv"
    if not path.exists():
        return {}, ()
    kinds, sessions = {}, []
    seen = {s.session_id for s in class_sessions}
    for line, row in read_rows(path, SCHEDULE_FIELDS, SCHEDULE_FIELDS):
        key, kind = row["activity"], row["kind"]
        if not key or key in blocks or kind not in {"cas", "club"} or kinds.get(key, kind) != kind:
            raise CalendarError(f"{path}:{line}: use a unique activity key outside class blocks and kind cas or club.")
        session = Session(row["pattern"], row["session_id"], key, parse_time(row["start"]), parse_time(row["end"]))
        if not session.pattern or not session.session_id or session.session_id in seen or session.start >= session.end:
            raise CalendarError(f"{path}:{line}: pattern, unique session_id and increasing start/end are required.")
        kinds[key] = kind
        seen.add(session.session_id)
        sessions.append(session)
    return kinds, tuple(sessions)


def validate_activities(items, semester):
    seen = set()
    for item in items:
        kind = semester.activities.get(item.activity)
        if kind is None or item.activity in seen:
            raise CalendarError(f"Unknown or duplicate activity {item.activity!r}.")
        seen.add(item.activity)
        if kind == "cas" and item.name:
            raise CalendarError("CAS has a fixed title; leave its name blank.")
        if kind == "club" and item.enabled and not item.name.strip():
            raise CalendarError(f"Name club {item.activity!r} before enabling it.")
        for text in (item.name, item.location):
            if any(ord(c) < 32 and c not in "\t\r\n" for c in text):
                raise CalendarError("Remove unsupported control characters from activity text.")


def load_activities(path, semester):
    items = []
    if path.exists():
        for line, row in read_rows(path, SELECTION_FIELDS, ("activity", "name")):
            enabled = row.get("enabled", "true" if row["name"] else "false").lower()
            if enabled not in {"true", "false", "1", "0", "yes", "no"}:
                raise CalendarError(f"{path}:{line}: enabled must be true or false.")
            items.append(Activity(row["activity"], row["name"], enabled in {"true", "1", "yes"}, row.get("location", "")))
    validate_activities(items, semester)
    by_key = {item.activity: item for item in items}
    return [by_key.get(key, Activity(key)) for key in semester.activities]


def save_activities(path, items, semester, expected):
    validate_activities(items, semester)
    if digest(path) != expected:
        raise CalendarError("Activities changed on disk. Reload before saving.")
    rows = [dict(asdict(item), enabled=str(item.enabled).lower()) for item in items]
    atomic_write(path, csv_bytes(SELECTION_FIELDS, rows), backup=True)
