"""Small shared records; neither scheduling nor persistence depends on a UI."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone


class CalendarError(ValueError):
    """An actionable configuration/input error safe to display to a student."""


@dataclass(frozen=True)
class Course:
    block: str
    course: str = ""
    location: str = ""
    teacher: str = ""
    enabled: bool = False
    timing_option: str = ""


@dataclass(frozen=True)
class Session:
    pattern: str
    session_id: str
    block: str
    start: time
    end: time


@dataclass(frozen=True)
class DayOverride:
    date: date
    action: str
    pattern: str = ""
    time_shift_minutes: int | None = None
    note: str = ""


@dataclass(frozen=True)
class Semester:
    id: str
    name: str
    clock: timezone
    blocks: tuple[str, ...]
    weekdays: dict[int, str]
    sessions: tuple[Session, ...]
    # block -> choice -> session ID -> {start and/or end}. Choices travel with
    # the selected pattern, including when Thursday is taught on a Saturday.
    timing_options: dict = field(default_factory=dict)

    @property
    def patterns(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(s.pattern for s in self.sessions))


@dataclass(frozen=True)
class Event:
    uid: str
    block: str
    title: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""


@dataclass
class Preview:
    events: list[Event]
    notes: list[str]
    excluded: list[str]
    start: date
    end: date
    clock: str
