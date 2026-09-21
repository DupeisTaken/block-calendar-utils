"""A deliberately narrow RFC 5545 writer for concrete class occurrences."""

from datetime import datetime, timezone
from pathlib import Path

from .models import Event
from .storage import atomic_write


def escape_text(value: str) -> str:
    """TEXT values escape punctuation and normalized logical newlines."""
    return value.replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold_line(line: str) -> list[bytes]:
    """Fold at 75 UTF-8 octets, counting the continuation space as one octet."""
    parts, current = [], bytearray()
    for char in line:
        encoded = char.encode("utf-8")
        if len(current) + len(encoded) > 75:
            parts.append(bytes(current))
            current = bytearray(b" ")
        current.extend(encoded)
    parts.append(bytes(current))
    return parts


def calendar_bytes(events: list[Event], *, name: str = "Block calendar", now: datetime | None = None) -> bytes:
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Block Calendar Utils//Class Export 1.0//EN", "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{escape_text(name)}"]
    for event in sorted(events, key=lambda e: (e.start, e.uid)):
        lines.extend(["BEGIN:VEVENT", f"UID:{event.uid}", f"DTSTAMP:{stamp}",
                      f"DTSTART:{event.start.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
                      f"DTEND:{event.end.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
                      f"SUMMARY:{escape_text(event.title)}"])
        if event.location:
            lines.append(f"LOCATION:{escape_text(event.location)}")
        if event.description:
            lines.append(f"DESCRIPTION:{escape_text(event.description)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return b"\r\n".join(part for line in lines for part in fold_line(line)) + b"\r\n"


def export_calendar(path: Path, events: list[Event], *, overwrite: bool = False, name: str = "Block calendar") -> None:
    if path.suffix.lower() != ".ics":
        from .models import CalendarError
        raise CalendarError("Choose an output filename ending in .ics.")
    atomic_write(path, calendar_bytes(events, name=name), overwrite=overwrite)
