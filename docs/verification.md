# Verification record

## Linked setup, command catalogue and GUI guide — 2026-09-19

**128 tests passed**, including native Tk tests and the independent calendar parser. This documentation pass shortened the README to a starting page and added `docs/setup.md`, `docs/command-catalogue.md` and `docs/gui.md`. Existing workflow/configuration guides and working agreements link to the new references; application behavior was not changed in this pass.

Documentation tests now parse the runnable CLI examples in all user guides and verify that their operations belong to the selected inspect/write/export action. Two additional checks validate local Markdown links, section anchors and code fences, and check the catalogue against the complete public long-option vocabulary.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -q
python tools/verify_gui.py --setup
python tools/verify_gui.py
```

Reviewed fresh synthetic screenshots in `local/qa/`: `setup-1.333.png`, `courses-1.333.png`, `preview-1.333.png`, `exceptions-1.333.png`, `activities-1.333.png` and `single-day-1.333.png`. The guide's tab names, fields and buttons match the current window. Save/preview/export handlers were inspected to document automatic selection saves, remembered preferences, exception-form saves, replacement confirmation and cancellation accurately.

Each screenshot run used one short-lived window and removed its temporary workspace. No personal files were touched or dependencies installed. Bytecode generation was disabled for this pass. Native macOS and real calendar-client import checks remain unverified.

## Inspect, write and export workflows — 2026-09-19

**126 tests passed**, including native Tk tests and the independent calendar parser. The CLI now presents three intents and accepts separate or stacked actions. New checks cover write → inspect → export, shared profile/root/semester context, conflicting context, read-only inspection, stage-local options, syntax/date preflight before writes, help without execution, cancellation without partial batch saves, and stopping after a runtime failure while retaining completed writes.

Range checks exercise `0920-0924`, `9.20-9.24`, `9/20-9/24` and full compact dates through the new inspection route. An actual module subprocess enters a Unicode course name and exports a range; this exposed and fixed Windows redirected-input decoding by configuring UTF-8 before reading a workflow's input. Existing scheduling, stale-save, GUI and calendar serialization checks still pass.

Overwrite tests follow both documented corrections, verify that rejected exports preserve existing bytes, check permission does not leak to another export action, and cover a destination appearing during an exclusive save. Help tests verify required arguments, choices, contextual routes and all operation help before setup. Documentation examples are parsed without executing writes. Local links, anchors and code fences were checked in the README, four guides and historical plan.

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -q
python tools/verify_preview.py --help-page overview
python tools/verify_preview.py --workflow
python tools/verify_preview.py --help-page export
```

Reviewed `local/qa/help-overview.png`, `terminal-workflow.png` and `help-export.png`: the three navigation actions, stacked write/export, existing-file error, explicit `--overwrite` recovery, required date options and full flag spellings are readable without clipping. These are actual CLI output rendered with the shared ANSI styling in synthetic Tk QA windows, not screenshots of the user's terminal. Each capture used one short-lived window and removed its temporary profile after closing.

README, command/configuration guides, architecture notes and working agreements now describe the same navigation. The original implementation plan remains clearly labeled as historical. No personal CSVs, school definitions or workbook data were changed by QA; no packages or background services were added. Generated project bytecode caches were removed. Native macOS execution and actual calendar-client imports remain unverified.

The records below describe earlier iterations. Use [commands.md](commands.md) for current syntax.

## Consistent CLI and public command grammar — 2026-09-19

**111 tests passed**, including native Tk and independent calendar-parser checks. New coverage exercises the public dash workflow, mnemonic shortcuts in overlapping scopes, long-only collisions, club-name input and export, literal names and attached paths, contextual help before setup, malformed/conflicting actions without writes, and a real module subprocess. Shared presentation tests cover help, prompts, preview dates/times, saved results, error corrections, one accent, plain output and Windows console-mode restoration.

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -q
python tools/verify_preview.py --help-page overview
python tools/verify_preview.py --help-page activities
python tools/verify_preview.py --entry
python tools/verify_preview.py --syntax
```

Reviewed `local/qa/help-overview.png`, `help-activities.png`, `terminal-entry.png` and `terminal-syntax.png`. They render actual CLI output with the same bold/cyan ANSI semantics used at the terminal boundary. Checked compact help, contextual options, spacing around fixed-slot club prompts, the save destination, aligned preview columns and a concise invalid-date correction. The synthetic capture uses a muted palette; the user's terminal controls its actual colors. Windows console API behavior is unit-tested; these screenshots use a temporary Tk rendering window.

The existing system Python supplies Pillow for screenshots; `.venv-verify` supplies the independent calendar parser for the test suite. No packages were installed. Captures ran sequentially, closing each window and deleting its temporary data. No personal selections or timetable files were changed. Native macOS and calendar-client import checks remain unverified.

The records below describe earlier iterations, not the current command reference. Current syntax is in [commands.md](commands.md).

## Help readability and color — 2026-09-19

**104 tests passed** with native Tk and independent calendar-parser checks enabled. Six new help tests cover blank lines between command/option entries, separated examples, narrow paragraph wrapping, unchanged text after stripping ANSI, one accent color, plain redirected output, `NO_COLOR`/basic-terminal opt-out, all help routes, and Windows console-mode restoration/failure fallback (mocked console API).

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -q
python tools/verify_preview.py --help-page overview
python tools/verify_preview.py --help-page activities
```

Reviewed `local/qa/help-overview.png` and `local/qa/help-activities.png`. These QA windows render the actual help's ANSI output with bold headings and a muted cyan flag color; native terminal colors follow the user's terminal palette. Main help remains compact, and detailed entries/examples have clear spacing. One short-lived window was used at a time; both windows and temporary workspaces were cleaned up. No dependencies or user terminal settings were changed during verification.

## Compact help and club-name entry — 2026-09-18

**98 tests passed**, including native Tk and independent calendar-parser checks. The main help is limited to 12 lines by a regression test (currently 10); first-use and command-specific help are separate, read-only paths.

Six new tests cover activity entry through both public activity-entry flags and compatibility forms; fixed day/time prompts; Unicode club names; exact ICS times; keep/clear/subset edits; room and disabled-state preservation; cancellation without partial saves; unknown/duplicate slot rejection; and external-edit conflicts. Both module entry points were also exercised in subprocesses with club-name input. Nested saved-exception compatibility aliases were also exercised.

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover
python tools/verify_preview.py --entry
```

Reviewed `local/qa/terminal-entry.png`: compact help and both predefined club prompts fit in the synthetic terminal QA window. The window/process finished, its temporary workspace was removed, and no personal selections or school slot times were changed during verification.

## Friendly commands and dates — 2026-09-18

**92 tests passed** with native Tk tests and the independent calendar parser enabled, using the existing `.venv-verify` environment on Windows. The 13 added tests cover flexible date/range spellings, literal current-year/month-first interpretation, leap dates, invalid/ambiguous input, explicit cross-year ranges, unchanged strict CSV parsing, and canonical engine settings.

Command tests exercise short setup/course/activity/exception/export workflows, mixed full/short forms, global options before/after commands, attached short-option values, exact exported event times, and syntax errors without writes or input prompts. Both module entry points were run in actual subprocesses with short commands. That iteration checked a short alternative for every command and option; the later redesign supersedes this with mnemonic initials and long-only collisions.

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
python tools/verify_preview.py --syntax
```

Reviewed `local/qa/terminal-syntax.png`, showing an actual compact-date range preview with a dotted-date exception and guidance for an invalid date. The synthetic QA window and temporary workspace were closed/removed after capture. No dependencies were installed. GUI behavior and persisted date formats were not changed by this command-layer extension; earlier platform and calendar-client limitations still apply.

## Single-day export — 2026-09-18

**79 tests passed**, with native Tk tests enabled and the independent `icalendar` parser installed in `.venv-verify` (Windows, Python 3.14.5). The six added tests cover:

- `--day` preview/validation parity with the existing one-date range, exact exported UTC times, overwrite protection, and unchanged saved settings/course selections.
- Weekend makeup, named clubs, late timing, block exclusions, saved closures, and refusal to write empty exports.
- Invalid dates, conflicting date/week flags, and exceptions outside the selected day.
- Leap days and minimum/maximum supported dates without expanding to a week.
- GUI date edits, incomplete input, disabled controls, one-day export, restored settings, and switching back to range/week modes.

Commands:

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
python tools/verify_gui.py
python tools/verify_gui.py --scale 2.0
```

Reviewed `local/qa/single-day-1.333.png` and `local/qa/single-day-2.0.png`: the selected date, matching disabled last date, preview and export action are visible. Enlarged text uses the existing preview scrollbar. Screenshot runs used synthetic data and one short-lived window at a time; their temporary workspaces and windows were cleaned up. No dependencies were installed. Calendar-client imports and macOS remain unverified.

## Previous verification — 2026-09-13

Date: 2026-09-13. Host: Windows, Python 3.14.5, Tk 8.6.

## Automated checks

**73 tests passed** with native Tk tests enabled and the independent `icalendar` parser installed in a local verification environment. The latest work adds temporary course filters, day-column previews, optional CAS/named clubs, and composable inline exceptions with a configurable 12:30 cutoff:

- 21 core/storage tests: all five weekdays, 200 minutes per A–G block, both Thursday T options, late shifts, partial and multi-week ranges, Friday following Monday, weekend makeup, closures, exception precedence, custom patterns, a different semester, invalid inputs, CSV round trips, stale saves, interrupted-write preservation, and annotation-free events on regular/makeup days while preserving titles, times, locations, IDs and preview explanations.
- 22 terminal/setup tests: previous setup/course/date/Unicode cases plus per-export block filters without CSV edits, opt-in CAS/named clubs, the hyphenated date-range spelling and separator, inline-rule exports, conflicting flags, and saved half-day commands. Both module entry points are exercised in actual subprocesses.
- 13 native Tk controller tests: shared-service parity, input/save failures, profile/semester switching, and the original date/exception controls; new cases cover club-name saves, activity opt-in/reset across profiles, and preservation of half-day rules when editing saved exceptions.
- 3 terminal layout tests: adjacent day columns, separate calendar weeks, narrow displays, long Chinese and combining-character text without truncation, vertical fallback and empty previews.
- 4 activity tests: workbook-derived CAS/club intervals and titles, opt-in defaults, late shifts, preserved IDs/locations, makeup days and closures, invalid definitions/selections, stale saves and copied semester slots without student names.
- 8 inline-exception tests: order-independent weekday/half-day composition, effective start-time boundaries, whole-session retention across noon, configurable cutoff through semester files, explicit saved/inline precedence without persistence, malformed/conflicting/out-of-range rules, custom weekday mappings, late composition, saved CSV round trips, weekend no-op filters and club filtering after timetable substitution.
- 2 independent parser tests: exact round-trip titles, locations, UTC instants, unique IDs, Unicode/escaped text, absence of event descriptions, and an empty valid calendar. The three-week exception fixture produced the independently expected 74 events.

Command used in the temporary environment:

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
```

Actual subprocess tests also force an ASCII inherited stream encoding and verify that the CLI emits UTF-8 summaries and Chinese course names correctly. This covers Windows redirected-output behavior without relying on the test runner to supply UTF-8 defaults.

The local verification environment and Python caches remain ignored in this checkout. All verification windows and processes finished. Install `requirements-dev.txt` in a local virtual environment for the optional tools; the application itself does not need those packages. The parser tests used `.venv-verify`; screenshots used the existing system Python with Pillow because Pillow was not installed in that local environment. No additional installation was needed for this rework.

## Visual checks

Reviewed actual application-window screenshots for Courses, Dates & preview, and Exceptions at Tk scaling 1.333 and 2.0. All screenshots used synthetic selections. Only one application-owned window was open at a time and it was destroyed after capture.

The current four main tabs were checked at both scales, including club-name forms and the expanded exception editor. Review found the half-day controls squeezed the exception list at enlarged text size; placing all five inputs in one row restored visibility. The screenshot helper asserts that the first exception row and save/export actions fit. Earlier semester-setup screenshots remain under `local/qa/setup-*.png`.

The actual terminal preview command was also rendered in a single monospace QA window (`tools/verify_preview.py`) with synthetic selections, verifying adjacent Monday/Tuesday and Wednesday/Thursday columns. Its screenshot is `local/qa/terminal-preview.png`.

Screenshot review found and fixed clipping of the export bar and exception editor at enlarged text sizes. The screenshot helper now asserts that Export and Save date remain visible. Course fields scroll, including when keyboard focus moves to a lower row. All ten course rows, including T's timing choice, fit at the standard tested scale. Larger text uses the scrollable course area.

No unrelated app state was changed. Screenshots are local QA artifacts under ignored `local/qa/`; no personal course data or workbook was committed.

## Earlier resource check

A single synthetic three-year export (2026-09-14 through 2029-09-13) produced 4,078 events and 832,365 bytes in **0.54 seconds** while Python allocation tracing was enabled. Peak **traced Python allocations** were **8.8 MiB**; this is not total process memory. Results are a measurement on this machine, not a cross-platform performance guarantee.

## Remaining checks

- macOS execution and native UI have not been run on a Mac. The CI configuration includes Windows/macOS and Python 3.11/3.14 for non-GUI tests, but no remote CI run has been performed here.
- Actual Google Calendar, Apple Calendar, and Outlook imports/reimports have not been performed. Independent parser success is not a substitute for client testing.
- The user reported dragging an ICS into new Outlook and seeing one event. Further client investigation was explicitly deferred while the command workflow and project structure were implemented. The serializer was not changed by this rework; no claim is made that Outlook drag-in behavior is fixed.
- Real calendar notifications, account synchronization, and recurring subscriptions are outside this exporter's scope.

For a client check, import a short synthetic export into a disposable school-test calendar. Check the number of events, local time display, Thursday T end, a replacement weekday, and a holiday. Then test importing an overlapping range and a changed event. Do not assume stable UIDs alone remove old events or update them in every client's file-import flow.
