"""Editable semester batches shared by the terminal and desktop editors.

Keep incomplete work in memory. Validate the entire candidate and dependent
profiles before replacing any files; an editor never migrates student data.
"""

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from .activities import SCHEDULE_FIELDS, load_activities
from .models import CalendarError
from .semesters import DAYS, utc_minutes, weekday_map
from .storage import (SESSION_FIELDS, atomic_write, csv_bytes, digest, load_courses,
                      load_overrides, load_semester, parse_time, read_json,
                      read_rows, safe_child)

FILES = ("semester.json", "timetable.csv", "activities.csv", "exceptions.csv")


class SemesterDraft:
    def __init__(self, workspace, sid):
        self.workspace = workspace
        self.folder = safe_child(workspace.root / "semesters", sid)
        self.expected = self.fingerprints()
        self.config = read_json(self.folder / "semester.json")
        self.sessions = [row for _, row in read_rows(self.folder / "timetable.csv", SESSION_FIELDS, ("pattern", "block", "start", "end"))]
        # Freeze implicit identities before rows can be reordered or removed.
        occurrences = {}
        for row in self.sessions:
            key = (row["pattern"], row["block"])
            occurrences[key] = occurrences.get(key, 0) + 1
            row["session_id"] = row.get("session_id") or "auto-" + hashlib.sha256(repr((*key, occurrences[key])).encode()).hexdigest()[:24]
        path = self.folder / "activities.csv"
        self.activities = [row for _, row in read_rows(path, SCHEDULE_FIELDS, SCHEDULE_FIELDS)] if path.exists() else []
        self.assert_current()

    def fingerprints(self):
        return {name: digest(self.folder / name) for name in FILES}

    def assert_current(self):
        if self.fingerprints() != self.expected:
            raise CalendarError("Semester changed on disk. Reload the timetable editor before saving.")

    def settings(self):
        offset = self.config["utc_offset_minutes"]
        return dict(name=self.config["name"], blocks=",".join(self.config["blocks"]),
                    weekdays=",".join(f"{DAYS[int(k)][:3]}={v}" for k, v in self.config["weekdays"].items()),
                    utc_offset=f"{'-' if offset < 0 else '+'}{abs(offset) // 60:02}:{abs(offset) % 60:02}",
                    noon_cutoff=self.config.get("noon_cutoff", "12:30"))

    def update_settings(self, **values):
        config = copy.deepcopy(self.config)
        for key, value in values.items():
            if value is None:
                continue
            value = value.strip()
            if key == "blocks":
                blocks = [b.strip() for b in value.split(",")]
                if not all(blocks) or len(blocks) != len(set(blocks)):
                    raise CalendarError("Use unique, nonempty comma-separated block keys.")
                config[key] = blocks
            elif key == "weekdays":
                config[key] = weekday_map(value)
            elif key == "utc_offset":
                config["utc_offset_minutes"] = utc_minutes(value)
            elif key == "noon_cutoff":
                config[key] = parse_time(value).strftime("%H:%M")
            elif key == "name":
                if not value:
                    raise CalendarError("Semester name cannot be blank.")
                config[key] = value
        self.config = config

    def put_session(self, values, *, activity=False):
        fields = ("session_id", "pattern", "activity", "kind", "start", "end") if activity else ("session_id", "pattern", "block", "start", "end")
        row = dict(zip(fields, (v.strip() for v in values), strict=True))
        if not all(row.values()):
            raise CalendarError("Complete every session field.")
        if parse_time(row["start"]) >= parse_time(row["end"]):
            raise CalendarError("Session end must be after start.")
        if activity and row["kind"] not in {"cas", "club"}:
            raise CalendarError("Activity kind must be cas or club.")
        rows = self.activities if activity else self.sessions
        index = next((i for i, old in enumerate(rows) if old["session_id"] == row["session_id"]), len(rows))
        if index == len(rows):
            rows.append(row)
        else:
            rows[index] = row

    def remove_session(self, sid, *, activity=False):
        rows = self.activities if activity else self.sessions
        found = [row for row in rows if row["session_id"] == sid]
        if not found:
            raise CalendarError(f"Unknown session {sid!r}.")
        rows.remove(found[0])

    def put_timing(self, block, choice, session, start, end):
        choice = choice.replace("-", "_")
        if not block or not choice:
            raise CalendarError("Timing choices need a block and a choice name.")
        times = {key: parse_time(value).strftime("%H:%M") for key, value in (("start", start), ("end", end)) if value not in {"", "-"}}
        if session in {"", "-"} and times:
            raise CalendarError("Choose a session for a timing override.")
        if session not in {"", "-"} and not any(row["session_id"] == session and row["block"] == block for row in self.sessions):
            raise CalendarError("Choose a session belonging to this block for the timing override.")
        overrides = self.config.setdefault("timing_options", {}).setdefault(block, {}).setdefault(choice, {})
        if session not in {"", "-"}:
            if times:
                overrides[session] = times
            else:
                overrides.pop(session, None)

    def remove_timing(self, block, choice):
        choice = choice.replace("-", "_")
        options = self.config.get("timing_options", {})
        if choice not in options.get(block, {}):
            raise CalendarError(f"Unknown timing choice {block}/{choice}.")
        del options[block][choice]
        if not options[block]:
            del options[block]

    def save(self):
        self.assert_current()
        payloads = {
            "semester.json": (json.dumps(self.config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            "timetable.csv": csv_bytes(SESSION_FIELDS, self.sessions),
            "activities.csv": csv_bytes(SCHEDULE_FIELDS, self.activities),
        }
        # Validate using the real loader, including school rules and every local
        # profile. Renames/removals must not silently orphan saved selections.
        with tempfile.TemporaryDirectory(prefix="bcutils-definition-") as tmp:
            staged = Path(tmp) / self.folder.name
            for name, data in payloads.items():
                atomic_write(staged / name, data)
            school = self.folder / "exceptions.csv"
            if school.exists():
                atomic_write(staged / school.name, school.read_bytes())
            semester = load_semester(staged)
            load_overrides(staged / "exceptions.csv", semester)
            dependent = {}
            for folder in (self.workspace.local / "profiles").glob(f"*/{self.folder.name}"):
                for name, loader in (("courses.csv", load_courses), ("activities.csv", load_activities), ("exceptions.csv", load_overrides)):
                    path = folder / name
                    dependent[path] = digest(path)
                    if path.exists():
                        try:
                            loader(path, semester)
                        except CalendarError as exc:
                            raise CalendarError(f"This change would invalidate profile {folder.parent.name!r}: {exc}\nKeep its referenced keys/choices, or create a separate semester.") from exc
        self.assert_current()
        if any(digest(path) != expected for path, expected in dependent.items()):
            raise CalendarError("A student profile changed during validation. Try saving again.")
        # Each replacement is atomic. Roll back earlier replacements if an I/O
        # error interrupts this batch, retaining originals as sibling backups.
        originals = {name: (self.folder / name).read_bytes() if (self.folder / name).exists() else None for name in payloads}
        written = []
        try:
            for name, data in payloads.items():
                if data != originals[name]:
                    atomic_write(self.folder / name, data, backup=True)
                    written.append(name)
        except (CalendarError, OSError, KeyboardInterrupt):
            for name in reversed(written):
                if originals[name] is None:
                    (self.folder / name).unlink(missing_ok=True)
                else:
                    atomic_write(self.folder / name, originals[name])
            raise
        self.expected = self.fingerprints()
        return semester
