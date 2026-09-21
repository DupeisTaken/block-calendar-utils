"""Compose repeatable command-line changes into one resolved rule per date."""

from .models import CalendarError, DayOverride
from .semesters import DAYS
from .storage import parse_date, validate_overrides


def inline_overrides(pairs, semester, first, last):
    """Compose independent rule types; reject contradictory input without guessing."""
    changes = {}
    weekdays = {label: index for index, day in enumerate(DAYS) for label in (day, day[:3])}
    for date_text, rule_text in pairs:
        day = parse_date(date_text)
        if not first <= day <= last:
            raise CalendarError(f"Exception {day} is outside the export range {first} to {last}.")
        rule = rule_text.strip().casefold()
        values = changes.setdefault(day, {})
        if rule in {"off", "no-school"}:
            key, value = "off", True
        elif rule in {"no-morning", "no-afternoon"}:
            key, value = "half_day", rule
        elif rule in {"late", "normal"}:
            key, value = "shift", 20 if rule == "late" else 0
        elif rule.startswith("blank="):
            # Multiple windows compose, unlike contradictory weekday/timing rules.
            values["blank_hours"] = ",".join(filter(None, [values.get("blank_hours"), rule[6:]]))
            if not rule[6:]:
                raise CalendarError("Blank hours need HH:MM-HH:MM.")
            key, value = "blank_hours", values["blank_hours"]
        elif "=" in rule and rule.split("=", 1)[0] in {"no-morning", "no-afternoon", "overlap"}:
            label, value = rule.split("=", 1)
            key = {"no-morning": "morning_cutoff", "no-afternoon": "afternoon_cutoff", "overlap": "overlap"}[label]
            if not value:
                raise CalendarError(f"{label} needs a value after =.")
        else:
            key = "pattern"
            if rule in weekdays:
                value = semester.weekdays.get(weekdays[rule])
                if value is None:
                    raise CalendarError(f"No {DAYS[weekdays[rule]]} timetable is defined. Use off for a day without classes.")
            else:
                matches = [p for p in semester.patterns if p.casefold() == rule]
                value = rule_text if rule_text in semester.patterns else matches[0] if len(matches) == 1 else None
                if value is None:
                    raise CalendarError(f"Unknown exception rule {rule_text!r}. Use Mon–Sun, a defined pattern, off, no-morning[=HH:MM], no-afternoon[=HH:MM], blank=HH:MM-HH:MM, overlap=trim/remove, late or normal.")
        if key in values and values[key] != value:
            raise CalendarError(f"Conflicting {key.replace('_', ' ')} rules for {day}.")
        values[key] = value
        if values.get("off") and len(values) > 1:
            raise CalendarError(f"{day}: off cannot be combined with another exception type.")
    result = []
    for day, values in sorted(changes.items()):
        if "overlap" in values and not any(key in values for key in ("blank_hours", "morning_cutoff", "afternoon_cutoff")):
            raise CalendarError("Overlap requires blank hours or a morning/afternoon cutoff.")
        action = "off" if values.get("off") else "use" if "pattern" in values else "adjust" if "shift" in values else "partial"
        result.append(DayOverride(day, action, values.get("pattern", ""), values.get("shift"), half_day=values.get("half_day", ""),
                                  **{key: values[key] for key in ("blank_hours", "morning_cutoff", "afternoon_cutoff", "overlap") if key in values}))
    validate_overrides(result, semester)
    return result
