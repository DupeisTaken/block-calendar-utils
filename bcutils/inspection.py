"""Remember concrete CLI previews without changing profiles or GUI settings."""

from dataclasses import asdict
from datetime import datetime, timezone

from .models import CalendarError, Event, Preview
from .storage import parse_date, read_json, safe_child, write_json


def inspection_path(ctx):
    """Each data root, profile and semester owns one replaceable snapshot."""
    folder = safe_child(ctx.workspace.local, "inspections")
    folder = safe_child(folder, ctx.profile)
    return safe_child(folder, ctx.semester.id) / "preview.json"


def remember_inspection(ctx, preview):
    # Save resolved occurrences, not options: relative dates and edited source
    # files must never change what the user already inspected.
    value = asdict(preview)
    value.update(start=preview.start.isoformat(), end=preview.end.isoformat())
    value["events"] = [dict(asdict(event), start=event.start.isoformat(), end=event.end.isoformat()) for event in preview.events]
    write_json(inspection_path(ctx), dict(version=1, profile=ctx.profile, semester=ctx.semester.id,
                                         identity=ctx.identity, inspected_at=datetime.now(timezone.utc).isoformat(), preview=value))


def load_inspection(ctx):
    path = inspection_path(ctx)
    hint = "Run --inspect --day DATE[:DATE] for this profile and semester first."
    if not path.exists():
        raise CalendarError(f"No last inspection for {ctx.profile} / {ctx.semester.id}.\n{hint}")
    try:
        record = read_json(path)
        if type(record["version"]) is not int or record["version"] != 1:
            raise CalendarError("Unsupported inspection snapshot version.")
        if (record["profile"], record["semester"], record["identity"]) != (ctx.profile, ctx.semester.id, ctx.identity):
            raise CalendarError("Inspection belongs to a different profile or semester.")
        stamp = datetime.fromisoformat(record["inspected_at"])
        if stamp.tzinfo is None:
            raise CalendarError("Inspection timestamp needs a timezone.")
        value = record["preview"]
        first, last = parse_date(value["start"]), parse_date(value["end"])
        if not 0 <= (last - first).days < 3660:
            raise CalendarError("Invalid inspection date range.")
        if not isinstance(value["clock"], str) or not value["clock"]:
            raise CalendarError("Invalid inspection clock.")
        if value["schedule_mode"] not in {"saved", "weekdays", "exceptions", "inline"}:
            raise CalendarError("Invalid inspection schedule mode.")
        for field in ("notes", "excluded"):
            if not isinstance(value[field], list) or not all(isinstance(item, str) for item in value[field]):
                raise CalendarError(f"Invalid inspection {field}.")
        if not isinstance(value["events"], list):
            raise CalendarError("Invalid inspection events.")
        events, seen = [], set()
        for row in value["events"]:
            for field in ("uid", "block", "title", "location", "description"):
                if not isinstance(row[field], str) or field in {"uid", "block", "title"} and not row[field]:
                    raise CalendarError(f"Invalid inspected event {field}.")
            start, end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
            if (start.tzinfo is None or end.tzinfo is None or start.utcoffset() != end.utcoffset()
                    or str(start.tzinfo) != value["clock"] or end <= start or end.date() != start.date()
                    or not first <= start.date() <= last or row["uid"] in seen):
                raise CalendarError("Invalid inspected event interval or identity.")
            seen.add(row["uid"])
            events.append(Event(row["uid"], row["block"], row["title"], start, end, row["location"], row["description"]))
        return Preview(events, value["notes"], value["excluded"], first, last, value["clock"], value["schedule_mode"]), stamp.astimezone(timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise CalendarError(f"Cannot use the last inspection: {exc}\n{hint}") from exc
