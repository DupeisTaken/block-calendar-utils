"""Workspace services: the CLI and GUI call exactly the same operations."""

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
        if not result:
            raise CalendarError(f"No semesters found in {self.root / 'semesters'}. Run from a complete project checkout.")
        return result

    def settings(self) -> dict:
        settings = read_json(self.settings_path) if self.settings_path.exists() else {}
        defaults = {"profile": "me", "semester": self.semesters()[0], "mode": "this", "anchor": "", "end": "", "weeks": 1, "late": False}
        defaults.update(settings)
        for key in ("profile", "semester", "mode", "anchor", "end"):
            if not isinstance(defaults[key], str):
                raise CalendarError(f"settings.json: {key} must be text.")
        if type(defaults["weeks"]) is not int or type(defaults["late"]) is not bool:
            raise CalendarError("settings.json: weeks must be an integer and late must be true/false.")
        return defaults

    def save_settings(self, settings: dict) -> None:
        write_json(self.settings_path, settings, backup=True)

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
            raise CalendarError(f"Profile {profile!r} is not set up for {semester_id}. Run the menu, GUI, or init command first.")
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

    def courses(self):
        return load_courses(self.courses_path, self.semester)

    def exceptions(self):
        return load_overrides(self.exceptions_path, self.semester)

    def save_courses(self, courses: list[Course], expected):
        save_courses(self.courses_path, courses, self.semester, expected)

    def save_exceptions(self, items, expected):
        save_overrides(self.exceptions_path, items, self.semester, expected)

    def preview(self, settings: dict):
        first, last = date_range(settings["mode"], settings.get("anchor", ""), settings.get("weeks", 1), settings.get("end", ""), today=datetime.now(self.semester.clock).date())
        return build_preview(self.semester, self.courses(), self.identity, first, last, 20 if settings.get("late", False) else 0,
                             load_overrides(self.folder / "exceptions.csv", self.semester), self.exceptions())

    def export(self, preview, output: Path | None = None, *, overwrite: bool = False) -> Path:
        output = output or self.workspace.root / "exports" / f"{self.profile}-{self.semester.id}-{preview.start}-{preview.end}.ics"
        protected = [self.courses_path, self.exceptions_path, self.workspace.settings_path]
        if output.resolve() in [p.resolve() for p in protected]:
            raise CalendarError("Choose a calendar destination outside your configuration files.")
        export_calendar(output, preview.events, overwrite=overwrite, name=f"SHBS · {self.profile}")
        return output
