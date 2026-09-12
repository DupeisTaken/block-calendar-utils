# Configuration

The scheduling engine reads the semester files every time a context is opened. Restart or switch/reopen the context after editing a semester. Student files are reread for previews and exports. Neither interface maintains a separate database.

## Student course file

Path: `local/profiles/<profile>/<semester>/courses.csv`.

```csv
block,course,location,teacher,enabled,timing_option
A,"Chemistry, advanced",Lab 1,Example Teacher,true,
B,Study Hall,,,true,
T,TOEFL Study Hall,,,true,study_hall
El,,,,false,
```

Only `block` and `course` headers are mandatory; all other headers may be omitted. Unknown/duplicate headers are errors, so misspellings are not silently discarded. Values may use CSV quoting, Unicode, and embedded newlines. UTF-8 with or without a BOM is accepted; app-written CSVs have a BOM for desktop spreadsheet compatibility.

| Field | Meaning |
| --- | --- |
| `block` | Exact configured block key, including case (`El`, not `EL`). One row per block. |
| `course` | Event title. A named Study Hall is exported like any other selection. |
| `location` | Optional event location. |
| `teacher` | Optional teacher included in the event description. |
| `enabled` | `true`/`false` (also accepts yes/no and 1/0). If the header is omitted, a nonempty course is enabled. |
| `timing_option` | For an enabled T block, `study_hall` or `toefl`. Other blocks use blank unless their semester defines choices. |

Missing block rows are treated as disabled and are restored as blank rows the next time the interface saves. Blank enabled titles, duplicate blocks, unknown blocks, and invalid timing choices are rejected. Leading/trailing whitespace is trimmed. The choice is independent of the course's free-form name.

Interface saves retain optional room/teacher fields, use atomic replacement, and keep the previous contents in a sibling `.bak` file. The GUI and terminal refuse stale saves when the CSV changed after it was loaded. Editing the same profile simultaneously in multiple interfaces is not recommended.

## Date exceptions

Shared path: `semesters/<semester>/exceptions.csv`.
Personal path: `local/profiles/<profile>/<semester>/exceptions.csv`.

The examples below illustrate the format; they are **not a confirmed school calendar**:

```csv
date,action,pattern,time_shift_minutes,note
2026-09-18,use,monday,,Friday follows Monday
2026-09-19,use,thursday,0,Makeup day with normal timing
2026-09-21,off,,,No classes
2026-09-22,adjust,,20,Late day
```

- `off`: no events. Pattern and shift must be blank.
- `use`: use a named pattern on this actual date. A weekday does not point to another date's exceptions, so swaps cannot form date-following loops.
- `adjust`: use this date's normal weekday pattern with an explicit shift. A weekend without a base pattern needs `use`, not `adjust`.
- A blank shift on `use` inherits the export setting. Explicit `0` or `20` **replaces** that setting. Shifts are never added twice. The CSV supports any whole-minute shift from -720 to 720 if it stays within the same day.
- One row per date per file. Personal rows replace shared rows in full. Removing a personal row restores the school/default behavior, which may itself be a closure or different pattern.

Use `--schedule exceptions` in a terminal export, or uncheck **Follows normal weekdays** in the GUI, to apply these files. That choice requires at least one exception inside the inclusive first/last date range. Dates without exceptions keep their normal weekday pattern. `--schedule weekdays` (the terminal default) uses only the regular timetable and leaves both exception files untouched. Commands such as `exceptions set 2026-09-18 --follow monday` collect all their information through arguments.

The GUI supports the common normal/late shifts. A CSV-edited custom shift is preserved when selecting that row. Exceptions outside the export range are retained for later exports; malformed rows are reported when exception scheduling reads the files.

## Semester timetable

Each folder in `semesters/` contains:

- `semester.json`: ID, display name, fixed UTC offset, block keys, weekday mapping, timing choices.
- `timetable.csv`: explicit class/study intervals by pattern.
- `exceptions.csv`: optional shared overrides; a missing file means none.

`semester.json` uses weekday keys `0` for Monday through `6` for Sunday. Omit normal non-school weekdays. `utc_offset_minutes: 480` means UTC+08:00. All input times and date presets use that clock; export UTC instants do not depend on the machine timezone.

```csv
pattern,session_id,block,start,end
monday,mon-b,B,08:10,09:30
monday,mon-a,A,09:40,10:20
half-day,half-a,A,09:00,09:40
half-day,half-b,B,09:50,10:30
```

`pattern`, `block`, `start` and `end` are required headers. `session_id` is optional: a missing/blank ID is generated from the pattern, block and occurrence number for that block in that pattern. Each row is one interval, including any intended double period. Times use 24-hour `HH:MM`; end must be after start. Do not list separate period rows that should become one event. The engine does not infer merges from adjacent titles or blank spreadsheet cells.

Add a custom half-day by adding its rows to `timetable.csv` and using action `use` with pattern `half-day` on the desired date. Custom patterns may also adjust individual times while keeping other sessions unchanged.

Session IDs must be globally unique within a semester. Keep explicit IDs stable when editing the same session's time or title so occurrence IDs remain stable. Give a new session a new ID. With generated IDs, reordering or inserting occurrences of the same block in the same pattern changes those occurrence identities; use explicit IDs when that stability matters. Advanced timing overrides refer to explicit session IDs. Missing timetable rows for any declared block, unknown weekday patterns, duplicate IDs, invalid option overrides, and selected-event overlaps stop export.

For example, this configuration adjusts Thursday T while leaving Wednesday T unchanged:

```json
"timing_options": {
  "T": {
    "study_hall": {"thu-t": {"end": "16:25"}},
    "toefl": {"thu-t": {"end": "17:05"}}
  }
}
```

The sequence is: select actual day's pattern → apply course timing option → apply effective date shift → resolve UTC event. If a Saturday follows Thursday, it uses Thursday's T option too.

## A new semester

1. Run `python -m shbs-calendar semester new 2026-27-s2 --blocks X,Y,Z`, supplying the actual block names. This creates a draft with an empty timetable. Alternatively pass `--timetable path.csv` to import complete rows immediately; invalid imports leave no installed folder.
2. Fill `timetable.csv` with the actual pattern/block/start/end arrangements. The default `semester.json` maps Monday–Friday to `monday`–`friday` and uses UTC+08:00. Set `--weekdays mon=red,tue=blue` or `--utc-offset +08:00` when creating a different mapping/clock. Omitted weekdays have no classes. You may also edit the JSON, including optional timing choices.
3. Run `semester show 2026-27-s2` and compare the entire timetable to the school source. `semester list` reports incomplete definitions as drafts/invalid. A draft cannot export.
4. Run `semester use 2026-27-s2`, or review and select the valid definition in the GUI. Activation validates the definition and creates a separate blank `courses.csv`. Previous selections remain available. Use `courses edit` or `courses set X "Course name"` to select courses.
5. Run `preview --week 2027-02-22` (substitute a suitable date) and inspect special dates. Each export needs its own dates; a whole-semester calendar is never assumed.

To deliberately copy an existing arrangement, use `semester new 2026-27-s2 --copy 2026-27-s1`. This copies the definition and timing options, sets the new ID/name, and creates an empty school exception file. It never copies student selections or activates the result. Edit the copied files before selection. Existing semester folders are never replaced by `semester new`.

The original workbook is a reference. No runtime spreadsheet dependency or student mapping data is committed.

## Profiles and files

Profile/folder names use letters, numbers, dashes, and underscores; names cannot escape their parent directories. Each profile has a persistent UUID in `local/profiles/<profile>/profile.json`. Preserve it when copying your local data to another machine. Profile identity, semester ID, actual date, and session ID form stable occurrence IDs. Course title, duration, export range, and export time do not affect them.

`local/settings.json` stores the explicitly chosen `active_semester`, profile, and GUI range/timing preferences. Legacy `semester` values were sometimes selected automatically, so upgrading requires `semester use ID` once. Existing course files and UUIDs are preserved. CLI commands require dates and default to normal timing/weekday scheduling regardless of saved GUI preferences; explicit `--semester ID` is a per-command selection without changing the active semester. The legacy internal `saved` schedule mode is still understood by shared services for compatibility, but terminal exports never use it as a default.

Copy `local/` deliberately between your own machines if you want the same selections and event identities. It is not synchronized by Git. Export files and backups can contain course details and are also ignored.

No source workbooks are needed after the timetable has been configured. No school holiday dates or late-day dates are supplied by default.
