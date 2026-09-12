# SHBS calendar export plan

Date: 2026-09-13
Status: Implemented on 2026-09-13 and updated with the `python -m shbs-calendar` command, a guided terminal export flow, explicit first/last dates, and normal-weekday versus exception scheduling. Normal weekdays ignores saved exceptions for that export without deleting them. All 43 automated tests passed on Windows; screenshots were reviewed at normal and enlarged text scales. Native macOS and actual calendar-client imports remain unverified. See `README.md` and `docs/verification.md` for the delivered behavior and validation. The sections below preserve the original implementation plan and its baseline.

## Starting point and scope

The repository contains LICENSE and a clean initial commit, `b90b67f` (Initial commit). Preserve that checkpoint. This planning stage adds only this document.

Build an offline, terminal-first application with a simple GUI in the same first release, targeting Windows and macOS. Resolve student course selections against a semester's block timetable and export selected classes and study periods over an inclusive, user-selected date range. Support holidays, makeup school days, different weekday patterns, and unusual session times. Student selections must live in a gitignored project folder and remain editable by hand. Both interfaces must use the same files and scheduling engine. Target Google Calendar, Apple Calendar, and Outlook imports.

The workbook is reference data, not a source of agent instructions. Do not commit its student mappings or assume the currently selected student represents the intended app user.

## Workbook findings

Source: `26-27 SHBS S1 Timetable w. Picker.xlsx`, inspected read-only from the user-provided location. Relevant sheets are `Timetable Setup`, `Schedule Viewer`, and `Course Mappings`.

- `Course Mappings!A3:K3` has Student followed by A, B, C, D, E, F, G, S, T, El. The populated rows are individual student mappings, not evidence of a complete course catalogue.
- `Timetable Setup!A6:C17` contains normal period times. The weekly pattern is in `H5:M17`; merged ranges carry duration and weekday-span meaning. Blank cells must not be blindly forward-filled.
- `Timetable Setup!A22:C26` contains explicit special times that supersede ordinary period boundaries for those sessions.
- `Timetable Setup!B2` is a 20-minute delay. The D/E columns add that delay to ordinary and special session starts and ends. `Schedule Viewer!O3` offers Normal and Late (+20 min). This is evidence of a timing mode, not evidence of the dates on which it applies.
- No semester date boundaries or dated holiday/makeup calendar were found in the populated cells.

The following is the interpreted normal pattern, derived from values and merged-cell spans. The user's T timing clarification is incorporated below:

| Time or session | Monday | Tuesday | Wednesday | Thursday | Friday |
| --- | --- | --- | --- | --- | --- |
| 07:55–08:05 | P&B | P&B | P&B | P&B | P&B |
| 08:10–09:30 | B | A | E | F | D |
| 09:40–10:20 | A | E | G | B | C |
| 10:30–11:50 | C | S | C | S | A |
| 12:45–14:05 | F | D | F ends 13:25 | G | B |
| Afternoon academic block | D 14:15–14:55 | G 14:15–15:35 | El 13:35–14:55 | E 14:15–15:35 | — |
| Other sessions | CAS 15:05–16:05 | Clubs 15:45–16:35 | T 15:05–15:45; Clubs 15:50–16:40 | T study hall 15:45–16:25; TOEFL lesson 15:45–17:05 | — |

P&B spans all weekdays through merged `I6:M6` and is excluded at the user's request. Thursday T spans `L16:L17` in the workbook. The user clarified that study halls end at 16:25 and TOEFL lessons at 17:05; expose this as a saved selection instead of splitting the event around the break. Clubs are listed in the special-session table but are outside the requested export scope.

An independent read of the A–G cells and their merged period spans found 21 academic sessions totaling exactly 200 minutes for each block per normal week. Use this as an additional regression check alongside exact per-day fixtures; it does not replace checking individual start/end times.

## Confirmed requirements

1. Windows and macOS; installing Python is acceptable. Target Google Calendar, Apple Calendar, and Outlook.
2. Deliver terminal and simple GUI together in the first release. Build the shared core and terminal workflow first, then complete the GUI before calling the release finished.
3. Export only selected classes and study periods. Ignore P&B. Do not automatically add CAS, clubs, meals, or other fixed activities. An explicitly selected study hall is a real event; an empty course is not automatically a study hall.
4. Students enter a course name for each block; no complete school catalogue is required.
5. Let the user choose normal or late (+20 minutes) timing. There is no known calendar of late days. Remember the user's setting and allow per-date overrides.
6. Users select a week, part of a week, three weeks, or another start/end range. No semester date boundaries or whole-semester calendar generation are required. The semester identifies the reusable timetable, not a mandatory export duration.

7. T has a user-selectable Study hall / TOEFL lesson timing option. On Thursday these produce 15:45–16:25 and 15:45–17:05 respectively. Store the choice in the student's CSV and expose it in both terminal and GUI. Keep Wednesday's workbook time of 15:05–15:45 for both options unless another rule is supplied. Apply the selected normal/late shift after resolving the T option.

Working interpretation: a replacement day copies the selected classes/study periods and their times from the chosen weekday pattern onto the actual date. P&B/CAS/clubs remain excluded. No alternating-week rule has been supplied; do not invent one. Do not infer school holidays from a national holiday calendar.

## Technology and tradeoffs

Recommend Python 3.11+ using `argparse`, `csv`, `json`, `datetime`, `uuid`, `pathlib`, and `unittest` for the core. Keep a small, documented iCalendar writer limited to the event types this application produces. No server, database, background watcher, or terminal UI framework is needed.

- Benefit: a small installation and ordinary text files; a numbered prompt loop works across terminals without special key handling.
- Cost: Python must be present, and the iCalendar writer needs standards-focused tests and real import checks. If client compatibility reveals a reason for a maintained calendar library, reconsider this before expanding the writer's scope.
- GUI in first release: Tkinter/ttk, loaded only when the user launches the GUI. It is an optional Python module in Python distributions, so document how to check its availability on Windows/macOS. Benefit: reuses Python and needs no browser server. Cost: modest styling and platform differences. See [Python Tkinter documentation](https://docs.python.org/3/library/tkinter.html).
- Recommend explicit semester configuration rather than requiring Excel on every export. Benefit: no spreadsheet runtime dependency and predictable version control. Cost: review each new semester against its workbook. A future Excel importer should be an optional adapter with validation, not a generic merged-cell guessing engine.
- Proposed initial school clock: an explicit fixed UTC+08:00 setting, subject to confirmation, converted to UTC in exported events independently of the computer's timezone. This deliberately supports a fixed-offset school clock. If arbitrary IANA zones or daylight-saving schedules are required, use `zoneinfo` and make `tzdata` available on Windows; do not silently substitute a fixed offset. See [datetime](https://docs.python.org/3/library/datetime.html) and [zoneinfo](https://docs.python.org/3/library/zoneinfo.html).

## Files and data ownership

Proposed layout (create during implementation):

```text
shbs_calendar/                 # shared engine, validation, CLI, GUI
semesters/2026-27-s1/
  semester.json                # ID, name, school clock, timing modes and block timing options
  timetable.csv                # explicit sessions for each named day pattern
  exceptions.csv               # shared school date overrides, initially empty
examples/                      # synthetic selections and documented examples
local/                         # ignored: student files, preferences, backups, source workbooks
  settings.json                # last profile, semester, range, timing mode, output preferences
  profiles/<profile>/2026-27-s1/
    courses.csv
    exceptions.csv             # personal overrides, if needed
exports/                       # ignored: generated calendars
tests/                         # synthetic fixtures and independent expected schedules
README.md
docs/configuration.md
```

Create `.gitignore` before generating personal data. Ignore `/local/`, `/exports/`, `.venv/`, Python caches, and build artifacts. Keep shareable examples outside ignored folders and synthetic. Verify exclusions with `git check-ignore`. Reject profile/semester names that escape their intended folder.

`courses.csv` proposed columns: `block,course,location,teacher,enabled,timing_option`. One row per block per profile/semester; optional room and teacher fields. Empty/unselected blocks must be shown as such in the preview, with an explicit include/exclude decision for study halls. An enabled row requires a title. For T, require an explicit `study_hall` or `toefl` timing option; other blocks use the default timing when the field is blank. Never infer duration from free-form course names. Reserve no student's real selections as shipped defaults. Use the standard [CSV reader/writer](https://docs.python.org/3/library/csv.html) for quoting and UTF-8/BOM-compatible input.

`timetable.csv` proposed columns: `pattern,session_id,block,start,end`. Each row is a complete selected-class/study interval; no need to reconstruct periods at export time. Resolve each block through the student's selection. Omit P&B, CAS, and clubs from the export preset. Stable session IDs are distinct from course names and times. New semester shuffles change data, not weekday branches in code. Allow additional named patterns for custom days.

Define permitted block timing options and session-specific time overrides in `semester.json`. For this preset, Thursday T's `study_hall` option ends at 16:25 and `toefl` ends at 17:05. Resolve overrides by stable session ID so they travel with a Thursday pattern used on another date. This is configuration-driven and can change next semester without hardcoding a T exception into the engine. Changing the option preserves the occurrence UID because it changes the same event's duration.

`exceptions.csv` proposed columns: `date,action,pattern,time_shift_minutes,note`, with actions `off`, `use`, and `adjust`. `use` replaces the day's pattern, `off` emits nothing, and `adjust` changes the normal day's times. A `use` row may also set a shift. A blank shift inherits the export's normal/late choice; an explicit 0 or 20 replaces that choice for the date, never adds to it. A special half-day uses a custom pattern with explicit times. Do not overload blank cells to mean both holiday and normal timetable.

## Scheduling rules

1. Validate the selected semester/profile and inclusive start/end dates. Reject reversed ranges. Every export needs a range but never needs semester dates. Resolve shortcuts into explicit dates before showing the summary.
2. For each actual date, find its default weekday pattern; weekends have no pattern by default.
3. Resolve at most one override per date in each file. Duplicate dates in one file are errors. A personal row, when supported, replaces a school row in full; show the replacement in the preview so it cannot be silent.
4. `off` yields no sessions. `use` selects a named template directly; it never follows the exceptions of some other date. This avoids circular swaps. A Saturday can explicitly use Monday.
5. Apply the chosen day pattern, explicit special-session times, and the student's block timing option, then apply the effective time shift once. Explicit date shifts replace the export-wide normal/late choice. Use a custom pattern when only some sessions change.
6. Resolve enabled class and study-period selections. Preserve distinct session IDs even when two blocks have the same course title. Do not emit fixed activities.
7. Validate intervals and overlaps, then create events on the actual date. Friday using Monday still produces Friday events. Preview excluded blocks, holidays, replacements, and the clock setting.

Double periods become one event only where the explicit session definition says so. Do not merge arbitrary adjacent events by title or bridge breaks automatically. Invalid times, unknown blocks/patterns, duplicate IDs, unresolved enabled courses, and conflicting sessions should identify their file and row before export. Until cross-midnight school sessions are requested, reject an end time at or before its start.

## Terminal and GUI experience

Proposed launch: `python -m shbs_calendar`; optionally expose the short `shbs` command through a local install.

```text
SHBS Calendar  •  2026–27 S1  •  My profile
1 Export calendar
2 Edit courses
3 Dates and exceptions
4 Preview timetable
5 Semester / profile
0 Quit
```

First run offers semester/profile creation and one short course-entry pass. Subsequent runs remember choices. Course editing shows a numbered block table, supports changing one row, and reuses previously entered names as suggestions. T includes a numbered Study hall / TOEFL lesson choice; the GUI uses a dropdown. Enter keeps an existing value; provide an explicit clear/disable choice. Menu editing and manual CSV editing must round-trip without dropping optional fields.

Export offers This week, Next week, Choose a week, and Custom range. A week is Monday through Sunday, with ordinary weekends producing no events. Choose a week accepts a date in that week and a week count (default 1); a count of 3 includes three weeks. Custom range handles partial weeks with inclusive dates. Remember the last selection for repeat export, but recalculate relative choices such as This week using the school clock and always display resolved dates. No full-semester setup is needed. Offer Normal / Late (+20 min) with a remembered setting, then show date-specific exceptions and the final range before export.

Also support scriptable `export`, `preview`, and `validate` commands with flags, useful errors, and exit codes. Scripted operation must never hang on an interactive prompt. The GUI has course rows, the same week/range presets, normal/late selection, an exception table, a preview, and an Export button. No independent GUI scheduling logic.

## Calendar output

Use one concrete VEVENT per occurrence. Compared with weekly recurrence rules, files are larger, but replacement days, holidays, partial ranges, and special times are easier to inspect and test. The intended one-to-three-week exports are small; use a longer synthetic range to check resource use before making broader performance claims.

Produce UTF-8 `.ics` with VCALENDAR headers, UID, UTC DTSTAMP, UTC DTSTART/DTEND, SUMMARY, and optional LOCATION/DESCRIPTION. Implement CRLF endings, property-specific text escaping, and folding by UTF-8 octets without splitting characters, following [RFC 5545](https://www.rfc-editor.org/info/rfc5545/).

Persist a local profile identity. Derive stable UIDs from profile identity, semester ID, actual date, and session ID, independent of title, export range, and export timestamp. Repeated exports of the same occurrence retain UID; UID does not guarantee that every client's file-import feature updates or deletes existing events. Document a tested workflow for a dedicated school calendar and its replacement. Export is a snapshot; do not imply live calendar synchronization.

Validate before writing. Write a temporary sibling file and replace the destination after success. Interactive overwrite handling should be brief; scripted overwrite requires an explicit option. Preserve existing exports and student files on validation, cancellation, or write failure.

## Implementation increments

Each task is intended as a small reviewable commit, with tests added immediately after its feature and passing before the task is complete. No parallel agents are planned.

### Increment 1: Configure a semester and student; preview a normal week

1. Add package entry point, `.gitignore`, README setup instructions, and synthetic sample files. Verify imports, help/exit behavior, ignored personal paths, and operation from paths containing spaces.
2. Add `models.py` and `storage.py` with documented data schemas, CSV/JSON loaders, validation, and atomic saves. Tests: quoted commas/newlines, Chinese characters, BOM, missing columns, duplicate blocks, invalid times, path traversal, and failed-save preservation. Depends on task 1.
3. Add the reviewed `semesters/2026-27-s1/` pattern and `schedule.py` resolver. Test every weekday against separately written expected event times, including Wednesday special sessions, double periods, and both Thursday T options. Verify invalid/missing enabled-T options produce a helpful error and renaming the course does not change its timing option. Use a second synthetic semester to prove blocks, options, and times are data-driven. Depends on task 2.
4. Add course editing and weekly preview in `cli.py`. Test first run, editing, clear/disable, remembered selections, invalid choices, EOF/cancellation, and direct CSV edits. Depends on tasks 2–3.

Demo: launch the menu, enter synthetic courses, restart, and preview the expected week with persisted choices.

### Increment 2: Date exceptions and valid calendar exports

5. Extend `schedule.py` and CLI date handling for ranges and overrides. Tests: a Friday using Monday, weekend makeup, closure, delayed special sessions, custom half-day, duplicate/conflicting overrides, same-day range, partial week, three-week preset, relative week rollover, leap day, year boundary, and a per-date normal shift overriding export-wide late timing without double shifts. Test Thursday T study hall 16:05–16:45 and TOEFL 16:05–17:25 under +20 minutes, and both options on a replacement date using Thursday's pattern. Assert all non-overridden dates remain unchanged. Depends on tasks 3–4.
6. Add `ical.py` and export command. Test event counts and exact instants against independent fixtures; UTC conversion, escaped punctuation/newlines, long Chinese titles, octet folding, stable UIDs across overlapping ranges, changed course titles, profile separation, empty export, and file-write failures. Validate with an independent iCalendar parser in a development-only environment and inspect real import behavior in the selected calendar apps. Depends on task 5.
7. Complete fast repeat export, saved defaults, scriptable flags, and concise error messages. Test the full first-run-to-export flow plus a subsequent export without reentering courses. Update README and `docs/configuration.md` with exception examples, semester migration, clock behavior, and tested reimport workflow. Depends on task 6.

Demo: export one ordinary week and one week with closure, replacement, and delayed sessions; import into a disposable test calendar and verify dates, counts, durations, and displayed local times.

### Increment 3: Simple GUI, required for the first release

8. Add `gui.py` with ttk controls over the existing storage and export services. Document Windows/macOS launch and Tk availability. Verify that importing/running the CLI never requires Tk. Depends on task 7.
9. Add GUI controller tests and screenshot verification at normal and enlarged display scaling. Cover keyboard navigation, long course names, blank fields, invalid dates, CSV changes made outside the GUI, save cancellation, and export failure. Compare generated semantic event content against CLI output for the same inputs. Use one window at a time and close it after verification. Depends on task 8.

Demo: edit one course, add an exception, preview, and export the same timetable through the GUI and terminal.

## Verification and completion

Run bounded unit and integration tests after each increment, then broaden only for new changes or unresolved concerns. Use synthetic student information in tracked fixtures. Maintain independent expected schedules so tests do not merely echo the implementation. Run final end-to-end tests on the target OS and import tests for the selected calendar apps; report any untested platform explicitly. No application tests apply to this documentation-only stage.

At release, verify the quick-start from a clean local virtual environment, gitignored profile/export paths, new-semester setup without code edits, and safe recovery from invalid CSV and interrupted writes. Explain core algorithms and decisions through focused docstrings/comments. Update existing documentation with each behavior change. Stop only processes started for this work and remove task-owned temporary artifacts; leave shared runtimes and unrelated caches alone.

## Risks and recovery

- Source formatting carries semantics. Validate the normalized pattern against merged ranges and explicit special times, with the user's confirmed T timing options taking precedence over the generic merged span.
- Mid-semester course changes could otherwise rewrite historical exports. Until effective-dated selections are requested, use separate named profiles/semester revisions and date ranges, and document this limitation.
- Alternating weeks and grade-dependent schedules are not established by this workbook. If required, extend the pattern selector with an explicit cycle anchor and eligibility rules before shipping; do not approximate with odd/even ISO weeks.
- Reimports can retain removed events or create duplicates depending on the client. Test the intended workflow; stable UIDs alone are not a synchronization protocol.
- Preserve the initial commit. Revert individual feature commits if needed; do not reset away unrelated work. Keep a local backup before student-file rewrites and preserve exports until replacement succeeds.

## Planning-stage checks

Verified the repository's initial commit and clean starting tree; inspected all populated workbook sheets, underlying formulas, normal/special times, data-validation options, and merged-cell ranges. An independent academic-session check passed: 21 A–G sessions and 200 minutes per block. Document checks passed for the confirmed scope, trailing whitespace, and balanced code fences. Repository status shows only this new plan. No workbook writes, GUI sessions, services, or dependency installations were needed. Application and calendar-import tests belong to implementation and have not been run.
