"""Friendly terminal date syntax, normalized before reaching the strict engine.

CSV files, persisted settings and the GUI retain their ISO date contract. Only
this input boundary accepts abbreviations, so convenience cannot change stored
data interpretation. Yearless dates always use the computer's current year.
"""

import re
from datetime import date, timedelta

from .models import CalendarError


DATE_HELP = "Use YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD or YYYYMMDD; omit the year with M-D, M.D, M/D or MMDD (month first, current year)."
RANGE_HELP = 'Use --day 9.18 for one day; --day 0920-0924 or --day 9.20-9.24 for a range. With hyphenated dates, prefer --day 2026-09-20:2026-09-24. Separators also include .. and quoted " to ".'

# A full date is recognized before considering hyphens as range separators.
# Backreferences require consistent separators within each individual date.
FULL_DATE = re.compile(r"([0-9]{4})([-./])([0-9]{1,2})\2([0-9]{1,2})")
SHORT_DATE = re.compile(r"([0-9]{1,2})([-./])([0-9]{1,2})")
RANGE_SEPARATOR = re.compile(r"\s*(?::|\.\.|\bto\b|[-–—])\s*", re.IGNORECASE)


def _parts(text, year):
    """Return date parts for a recognized shape, even if the date is invalid."""
    if match := FULL_DATE.fullmatch(text):
        return int(match[1]), int(match[3]), int(match[4])
    if match := SHORT_DATE.fullmatch(text):
        return year, int(match[1]), int(match[3])
    if re.fullmatch(r"[0-9]{8}", text):
        return int(text[:4]), int(text[4:6]), int(text[6:])
    if re.fullmatch(r"[0-9]{4}", text):
        return year, int(text[:2]), int(text[2:])
    return None


def parse_cli_date(value: str, *, today: date | None = None) -> date:
    """Parse one month-first date; never infer two-digit years or roll years."""
    today = today or date.today()
    parts = _parts(value.strip(), today.year)
    if parts is None:
        raise CalendarError(f"Unrecognized date {value!r}. {DATE_HELP}")
    try:
        return date(*parts)
    except ValueError as exc:
        raise CalendarError(f"Invalid date {value!r}: {exc}. {DATE_HELP}") from exc


def parse_cli_range(value: str, *, today: date | None = None) -> tuple[date, date]:
    """Accept a date or two complete date tokens separated by a range marker.

    Match endpoint shapes before validating dates. An impossible single date
    must stay an error, never get reinterpreted as a different range. Trying
    structural splits preserves the existing ISO-to-ISO hyphen syntax without
    confusing the hyphens inside either date with the range boundary.
    """
    today = today or date.today()
    text = value.strip()
    if _parts(text, today.year) is not None:
        day = parse_cli_date(text, today=today)
        return day, day
    candidates = []
    for separator in RANGE_SEPARATOR.finditer(text):
        left, right = text[:separator.start()].strip(), text[separator.end():].strip()
        if _parts(left, today.year) is not None and _parts(right, today.year) is not None:
            candidates.append((left, right))
    if len(candidates) != 1:
        raise CalendarError(f"Unrecognized or ambiguous date range {value!r}. {RANGE_HELP} {DATE_HELP}")
    first, last = (parse_cli_date(part, today=today) for part in candidates[0])
    if first > last:
        raise CalendarError(f"End date {last} is before start date {first}. Put the earlier date first. For a range crossing New Year, include both years, e.g. -d 2026-12-30:2027-01-02.")
    return first, last


def expand_cli_range(value, *, today=None):
    """Bound expansion before allocating per-date exception rows."""
    first, last = parse_cli_range(value, today=today)
    if (last - first).days >= 3660:
        raise CalendarError("Choose at most 3,660 days for an exception range.")
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
