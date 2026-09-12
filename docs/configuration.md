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

Select **No** for normal weekday scheduling in the terminal export flow, or uncheck **Follows normal weekdays** in the GUI, to apply these files. That choice requires at least one exception inside the inclusive first/last date range. Dates without exceptions keep their normal weekday pattern. Selecting **Yes** uses only the regular timetable and leaves both exception files untouched. The direct-command equivalents are `--schedule exceptions` and `--schedule weekdays`.

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

All five headers are required. Each row is one interval, including any intended double period. Times use 24-hour `HH:MM`; end must be after start. Do not list separate period rows that should become one event. The engine does not infer merges from adjacent titles or blank spreadsheet cells.

Add a custom half-day by adding its rows to `timetable.csv` and using action `use` with pattern `half-day` on the desired date. Custom patterns may also adjust individual times while keeping other sessions unchanged.

Session IDs must be globally unique within a semester. Keep IDs stable when editing the same session's time or title so occurrence IDs remain stable. Give a new session a new ID. Missing blocks, unknown weekday patterns, duplicate IDs, invalid option overrides, and selected-event overlaps stop export.

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

1. Copy the previous folder to a new ID such as `2026-27-s2`.
2. Update `id` to match the folder, display `name`, blocks, weekday patterns, explicit intervals, and timing options. Empty the copied school exception CSV unless those dates really apply.
3. Compare all weekdays and special sessions with the new school's timetable. Do not reuse this semester's shuffle without checking it.
4. Select the new semester in the menu/GUI. The app creates a separate blank `courses.csv` for the selected profile and semester. Previous selections remain available.
5. Preview a representative week and any special dates; run `validate` before exporting.

The original workbook is a reference. No runtime spreadsheet dependency or student mapping data is committed.

## Profiles and files

Profile/folder names use letters, numbers, dashes, and underscores; names cannot escape their parent directories. Each profile has a persistent UUID in `local/profiles/<profile>/profile.json`. Preserve it when copying your local data to another machine. Profile identity, semester ID, actual date, and session ID form stable occurrence IDs. Course title, duration, export range, and export time do not affect them.

`local/settings.json` stores the last context, range preset, timing, and `schedule_mode` (`weekdays` or `exceptions`). Older settings default internally to `saved`, preserving the original optional-exception behavior until an explicit choice is saved. Copy `local/` deliberately between your own machines if you want the same selections and event identities. It is not synchronized by Git. Export files and backups can contain course details and are also ignored.

No source workbooks are needed after the timetable has been configured. No school holiday dates or late-day dates are supplied by default.
