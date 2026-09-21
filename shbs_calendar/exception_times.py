"""Validate blank windows and subtract them from concrete session intervals."""

from .models import CalendarError


def minute(value):
    from .storage import parse_time
    # 24:00 is useful as an exclusive end boundary, never as an event time.
    if value == "24:00":
        return 1440
    parsed = parse_time(value)
    return parsed.hour * 60 + parsed.minute


def blank_windows(item):
    """Merge overlapping/touching windows so subtraction cannot duplicate events."""
    windows = []
    if item.overlap not in {"trim", "remove"}:
        raise CalendarError("Overlap must be trim or remove.")
    if item.blank_hours:
        for text in item.blank_hours.split(","):
            parts = text.strip().split("-")
            if len(parts) != 2:
                raise CalendarError("Blank hours need HH:MM-HH:MM, separated by commas.")
            start, end = (minute(p.strip()) for p in parts)
            if start >= end:
                raise CalendarError("Blank hours must end after they start, within the same day.")
            windows.append((start, end))
    if item.morning_cutoff:
        windows.append((0, minute(item.morning_cutoff)))
    if item.afternoon_cutoff:
        windows.append((minute(item.afternoon_cutoff), 1440))
    if item.morning_cutoff and item.afternoon_cutoff and minute(item.morning_cutoff) > minute(item.afternoon_cutoff):
        raise CalendarError("Morning cutoff must be on or before afternoon cutoff; use off to blank the whole day.")
    if item.overlap != "trim" and not windows:
        raise CalendarError("Overlap requires blank hours or a morning/afternoon cutoff.")
    merged = []
    for start, end in sorted(windows):
        if start == end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def remaining_intervals(start, end, windows, overlap):
    """Half-open windows leave touching sessions intact; trim may split a session."""
    if overlap == "remove":
        return [] if any(start < right and end > left for left, right in windows) else [(start, end)]
    pieces = [(start, end)]
    for left, right in windows:
        remaining = []
        for first, last in pieces:
            if first >= right or last <= left:
                remaining.append((first, last))
            else:
                if first < left:
                    remaining.append((first, left))
                if last > right:
                    remaining.append((right, last))
        pieces = remaining
    return pieces


def window_description(item):
    details = []
    if item.blank_hours:
        details.append("blank " + item.blank_hours)
    if item.morning_cutoff:
        details.append("morning cutoff " + item.morning_cutoff)
    if item.afternoon_cutoff:
        details.append("afternoon cutoff " + item.afternoon_cutoff)
    if details:
        details.append("overlap " + item.overlap)
    return "; ".join(details)
