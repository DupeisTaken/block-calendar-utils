"""Workspace services: the CLI and GUI call exactly the same operations."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from .ical import export_calendar
from .models import CalendarError, Course
from .schedule import build_preview, date_range
from .storage import (COURSE_FIELDS, EXCEPTION_FIELDS, atomic_write, csv_bytes, digest,
                      load_courses, load_overrides, load_semester, read_json, safe_child,
                      save_courses, save_overrides, write_json)

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class Workspace:
    def __init__(self, root: Path = DEFAULT_ROOT):
        self.root = root.resolve()
        self.local = self.root / "local"
        self.settings_path = self.local / "settings.json"

    def semesters(self) -> list[str]:
        result = sorted(p.parent.name for p in (self.root / "semesters").glob("*/semester.json"))
        return result

    def settings(self) -> dict:
        settings = read_json(self.settings_path) if self.settings_path.exists() else {}
        defaults = {"profile": "me", "semester": "", "active_semester": "", "mode": "this", "anchor": "", "end": "", "weeks": 1, "late": False, "schedule_mode": "weekdays"}
        defaults.update(settings)
        for key in ("profile", "semester", "active_semester", "mode", "anchor", "end"):
            if not isinstance(defaults[key], str):
                raise CalendarError(f"settings.json: {key} must be text.")
        if type(defaults["weeks"]) is not int or type(defaults["late"]) is not bool:
            raise CalendarError("settings.json: weeks must be an integer and late must be true/false.")
        if defaults["schedule_mode"] not in {"saved", "weekdays", "exceptions"}:
            raise CalendarError("settings.json: schedule_mode must be weekdays, exceptions, or saved.")
        return defaults

    def save_settings(self, settings: dict) -> None:
        write_json(self.settings_path, settings, backup=True)

    def selected_semester(self, explicit=None) -> str:
        """Old implicit defaults never count as an explicit semester selection."""
        selected = explicit or self.settings()["active_semester"]
        if not selected:
            raise CalendarError("Select a defined timetable first: --inspect --semesters, then --write --semesters --use ID. For a new timetable: --write --semesters --new ID --blocks X,Y,Z.")
        return selected

    def use_semester(self, semester_id, profile=None):
        settings = self.settings()
        folder = safe_child(self.root / "semesters", semester_id)
        definition = load_semester(folder)
        load_overrides(folder / "exceptions.csv", definition)
        ctx = self.context(profile or settings["profile"], semester_id, create=True)
        ctx.courses()
        settings.update(profile=ctx.profile, semester=semester_id, active_semester=semester_id, cas=False, clubs=True)
        self.save_settings(settings)
        return ctx

    def context(self, profile: str, semester_id: str, *, create: bool = False):
        folder = safe_child(self.root / "semesters", semester_id)
        semester = load_semester(folder)
        profile_dir = safe_child(self.local / "profiles", profile)
        data_dir = safe_child(profile_dir, semester_id)
        identity_path = profile_dir / "profile.json"
        if create:
            if not identity_path.exists():
                atomic_write(identity_path, (f'{{"id": "{uuid4()}"}}\n').encode(), overwrite=False)
            courses_path = data_dir / "courses.csv"
            if not courses_path.exists():
                atomic_write(courses_path, csv_bytes(COURSE_FIELDS, [{"block": b, "course": "", "location": "", "teacher": "", "enabled": "false", "timing_option": ""} for b in semester.blocks]), overwrite=False)
            if not (data_dir / "exceptions.csv").exists():
                atomic_write(data_dir / "exceptions.csv", csv_bytes(EXCEPTION_FIELDS, []), overwrite=False)
        if not identity_path.exists() or not (data_dir / "courses.csv").exists():
            raise CalendarError(f"Profile {profile!r} is not set up for {semester_id}.\nRun --write --courses to enter names, or --write --init to create blank files; keep the same --profile and --semester options.")
        identity = read_json(identity_path).get("id")
        try:
            UUID(identity)
        except (ValueError, TypeError, AttributeError) as exc:
            raise CalendarError(f"{identity_path}: invalid identity; restore its original value to retain event IDs.") from exc
        return Context(self, profile, semester, folder, data_dir, identity)


class Context:
    def __init__(self, workspace, profile, semester, folder, data_dir, identity):
        self.workspace, self.profile, self.semester = workspace, profile, semester
        self.folder, self.data_dir, self.identity = folder, data_dir, identity
        self.courses_path = data_dir / "courses.csv"
        self.exceptions_path = data_dir / "exceptions.csv"
        self.activities_path = data_dir / "activities.csv"

    def courses(self):
        return load_courses(self.courses_path, self.semester)

    def exceptions(self):
        return load_overrides(self.exceptions_path, self.semester)

    def activities(self):
        from .activities import load_activities
        return load_activities(self.activities_path, self.semester)

    def save_activities(self, items, expected):
        from .activities import save_activities
        save_activities(self.activities_path, items, self.semester, expected)

    def save_courses(self, courses: list[Course], expected):
        save_courses(self.courses_path, courses, self.semester, expected)

    def save_exceptions(self, items, expected):
        save_overrides(self.exceptions_path, items, self.semester, expected)

    def dates(self, settings: dict):
        return date_range(settings["mode"], settings.get("anchor", ""), settings.get("weeks", 1), settings.get("end", ""), today=datetime.now(self.semester.clock).date())

    def overrides_in_range(self, first, last):
        school = load_overrides(self.folder / "exceptions.csv", self.semester)
        merged = {item.date: item for item in school + self.exceptions()}
        return [item for day, item in sorted(merged.items()) if first <= day <= last]

    def preview(self, settings: dict):
        first, last = self.dates(settings)
        mode = settings.get("schedule_mode", "saved")
        if mode not in {"weekdays", "exceptions", "saved", "inline"}:
            raise CalendarError("Choose a weekday or exception schedule.")
        # Regular weekdays is an export-only switch: never erase saved dates.
        # 'saved' preserves the behavior of scripts/settings from version 1.0.
        school = load_overrides(self.folder / "exceptions.csv", self.semester) if mode in {"exceptions", "saved"} else []
        personal = self.exceptions() if mode in {"exceptions", "saved"} else []
        from .exceptions import inline_overrides
        inline = inline_overrides(settings.get("inline_exceptions", []), self.semester, first, last)
        if inline and mode == "weekdays":
            raise CalendarError("--schedule weekdays ignores exceptions. Omit it when using --exception.")
        # Inline rules replace the saved row for that date; neither CSV changes.
        inline_days = {item.date for item in inline}
        personal = [item for item in personal if item.date not in inline_days] + inline
        if mode == "exceptions" and not any(first <= item.date <= last for item in school + personal):
            raise CalendarError("No exceptions fall inside the selected dates.\nIn the CLI, remove --schedule exceptions to use normal weekdays, or add --exception DATE RULE inside the range.\nIn the GUI, check Follows normal weekdays or save a rule in Exceptions.")
        courses = self.courses()
        only = self.resolve_blocks(settings.get("only", []))
        exclude = self.resolve_blocks(settings.get("exclude", []))
        # Filters belong to this invocation; never alter saved selections.
        courses = [replace(c, enabled=c.enabled and (not only or c.block in only) and c.block not in exclude) for c in courses]
        activities = []
        if settings.get("cas") or settings.get("clubs", True):
            saved = self.activities()
            if settings.get("cas"):
                cas = [replace(a, enabled=True) for a in saved if self.semester.activities[a.activity] == "cas"]
                if not cas:
                    raise CalendarError("This semester has no CAS slots in its activities.csv.")
                activities += cas
            if settings.get("clubs", True):
                clubs = [a for a in saved if self.semester.activities[a.activity] == "club" and a.enabled]
                if not clubs and settings.get("require_clubs", False):
                    raise CalendarError('No enabled clubs are available.\nUse --inspect --activities to find a slot, then --write --activities --set ID "Club name" or --write --activities --enable ID. In the GUI, use CAS & clubs.')
                activities += clubs
        preview = build_preview(self.semester, courses, self.identity, first, last, 20 if settings.get("late", False) else 0, school, personal, activities=activities)
        preview.schedule_mode = mode
        return preview

    def resolve_blocks(self, values):
        result = set()
        for value in values:
            for token in value.split(","):
                token = token.strip()
                matches = [b for b in self.semester.blocks if b.casefold() == token.casefold()]
                if token in self.semester.blocks:
                    result.add(token)
                elif len(matches) == 1:
                    result.add(matches[0])
                else:
                    raise CalendarError(f"Unknown or ambiguous block {token!r}. Choose from: {', '.join(self.semester.blocks)}.")
        return result

    def export(self, preview, output: Path | None = None, *, overwrite: bool = False) -> Path:
        if not preview.events:
            raise CalendarError("No classes in this range. Check your course selections and dates in the preview.")
        output = output or self.workspace.root / "exports" / f"{self.profile}-{self.semester.id}-{preview.start}-{preview.end}.ics"
        protected = [self.courses_path, self.exceptions_path, self.activities_path, self.workspace.settings_path]
        if output.resolve() in [p.resolve() for p in protected]:
            raise CalendarError("Choose a calendar destination outside your configuration files.")
        export_calendar(output, preview.events, overwrite=overwrite, name=f"Block Calendar · {self.profile}")
        return output
