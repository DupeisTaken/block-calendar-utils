# SHBS Calendar

Export your selected classes and study periods to an `.ics` file. Use the numbered terminal menu or the simple desktop interface. Choose a week, several weeks, or any inclusive start/end dates. No semester dates, accounts, server, or Excel installation are required.

## Start

Install **Python 3.11 or newer**, download/clone this project, and open a terminal in its folder. The application uses only Python's standard library; there are **no pip packages to install**.

Windows:

```powershell
python -m shbs_calendar
```

macOS:

```sh
python3 -m shbs_calendar
```

For the GUI, add `gui`:

```powershell
python -m shbs_calendar gui
```

On macOS use `python3`. On Windows you can also double-click `shbs-gui.pyw` if `.pyw` is associated with Python. The GUI needs Tkinter, normally supplied by the Python.org desktop installers. Check your installation with `python -m tkinter` (or `python3 -m tkinter`); close its test window afterward. The terminal workflow works without Tkinter.

## Everyday workflow

1. Enter a name for each block once. Leave unused blocks blank. Enter **Study Hall** to include a study period. For T, choose **Study hall** or **TOEFL lesson**.
2. Choose **Dates and timing** in the menu, or **Dates & preview** in the GUI. Select This week, Next week, Choose a week, or Custom range. Three weeks is simply a week count of `3`.
3. Add any date exceptions: no classes, another weekday's timetable, or a timing change.
4. Preview and export. Files go into `exports/` unless you choose another destination.

The menu remembers your profile, semester, dates, and normal/late choice. The GUI saves date choices when you preview/export. Relative choices such as This week recalculate when used again; the preview always shows actual dates. Week ranges are Monday–Sunday, with weekends empty unless a makeup day is added. Start and end dates are both included.

Course names, optional rooms/teachers, and the T choice are stored in:

```text
local/profiles/me/2026-27-s1/courses.csv
```

You can edit that CSV directly. The GUI's **Reload CSV** button picks up external edits; it will refuse to overwrite conflicting unsaved changes. The `local/` and `exports/` folders are gitignored. The app ships no real student selections.

## Timing and exceptions

The included 2026–27 S1 preset uses the supplied workbook, with your clarified T rule:

| Session | Normal | Late (+20 minutes) |
| --- | --- | --- |
| Wednesday T, both choices | 15:05–15:45 | 15:25–16:05 |
| Thursday T, Study hall | 15:45–16:25 | 16:05–16:45 |
| Thursday T, TOEFL lesson | 15:45–17:05 | 16:05–17:25 |

P&B, CAS, clubs, and meals are excluded. Only named, enabled classes/study periods are exported. The preset's school clock is **UTC+08:00**, independent of the computer's clock. Events are written in UTC, so calendar apps can display them in their selected timezone.

For example, to make Friday 18 September use Monday's classes, add a date exception with date `2026-09-18`, action `use`, and pattern `monday`. The events stay on Friday. Timing can inherit the export setting, be Normal, or be Late. This does not change other days.

School-wide exceptions are in `semesters/2026-27-s1/exceptions.csv`; your personal file is next to `courses.csv`. One personal row replaces the school row for the same date, and the preview reports that replacement. No holidays or late days are guessed automatically.

See [configuration details](docs/configuration.md) for CSV formats, custom half-days, and adding a new semester.

## Direct commands

Use `python3` instead of `python` on macOS. Commands never prompt, and do not change your saved date settings.

```sh
# Create your blank profile files, then edit courses.csv.
python -m shbs_calendar init --profile me

# A selected week, or three weeks starting with that week.
python -m shbs_calendar preview --week 2026-09-14
python -m shbs_calendar export --week 2026-09-14 --weeks 3

# Part of a week; both endpoint dates are included.
python -m shbs_calendar export --start 2026-09-16 --end 2026-09-18

# Override remembered timing for this export.
python -m shbs_calendar export --next-week --late
python -m shbs_calendar export --this-week --normal

# Check inputs and the resulting schedule without writing a calendar.
python -m shbs_calendar validate --week 2026-09-14

# Explicit output; replacing an existing file requires --overwrite.
python -m shbs_calendar export --week 2026-09-14 -o exports/my-week.ics --overwrite
```

Use `--profile NAME` and `--semester ID` after a command to select other saved data. Use `--root PATH` **before** the command to point at another complete project/data folder. `--help` lists the commands. Exit codes: `0` success, `2` invalid input/write failure, `130` cancelled terminal input.

## Import the calendar

Create a separate calendar for your school exports, then import the file into it:

- **Google Calendar (computer):** Settings → Import & export → select the `.ics` file and destination calendar → Import. [Google's instructions](https://support.google.com/calendar/answer/37118?hl=en).
- **Apple Calendar (Mac):** File → Import, then select the `.ics` file and destination calendar. [Apple's instructions](https://support.apple.com/guide/calendar/import-or-export-calendars-icl1023/mac).
- **Outlook on the web:** Calendar → Add calendar → Upload from file, select the file and destination, then import. [Microsoft's instructions](https://support.microsoft.com/en-us/outlook/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web).

An export is a snapshot, not a subscription. Stable event IDs help identify the same occurrence, but repeated file imports are not guaranteed to update or delete prior events in every app. Prefer nonoverlapping export ranges. For a changed range already imported, inspect and replace the affected imported events in your dedicated school calendar. Keep unrelated personal events in a separate calendar.

The files pass independent iCalendar parser checks. Actual imports and repeat-import behavior in Google Calendar, Apple Calendar, and Outlook have **not** been tested in this environment.

## Development and verification

Run the dependency-free tests:

```sh
python -m unittest discover -v
```

Native GUI tests are opt-in so ordinary test runs do not create windows. Windows PowerShell:

```powershell
$env:SHBS_GUI_TESTS = '1'
python -m unittest discover -v
Remove-Item Env:SHBS_GUI_TESTS
```

On macOS: `SHBS_GUI_TESTS=1 python3 -m unittest discover -v` from a desktop session.

Optional independent parser and screenshot tools stay in a **local virtual environment**:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest tests.test_ical_interop -v
.\.venv\Scripts\python.exe tools/verify_gui.py
```

On macOS, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`. Screenshot tools use synthetic data and close their window after capture. [Verification notes](docs/verification.md) record what was checked and the remaining platform/client checks.

## Limits

- The school clock is a fixed offset; arbitrary daylight-saving timezones are not implemented.
- No automatic Excel importer, account synchronization, reminders, or alternating-week rotation.
- Changing a course mapping changes future **and past** exports made with that mapping. For a mid-semester change, preserve the old profile and use a new one for subsequent dates.
- An export is capped at 3,660 days to avoid accidental oversized jobs.
- Keep the whole project folder together; this version runs from a source checkout rather than an installed wheel.
