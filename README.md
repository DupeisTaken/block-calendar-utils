# SHBS Calendar

Define a semester's blocks and timetable, name your selected courses and study periods, then export any inclusive date range to `.ics`. Terminal commands perform one action and exit. **Running without arguments shows help; there is no navigation menu.**

Python **3.11+**, Windows or macOS. No runtime pip packages, Excel, accounts or server required. Run commands from the project folder; use `python3` instead of `python` on macOS.

## First use

The supplied workbook has already been transcribed into the `2026-27-s1` definition. Review it, then explicitly select it:

```sh
python -m shbs-calendar semester show 2026-27-s1
python -m shbs-calendar semester use 2026-27-s1
python -m shbs-calendar courses edit
```

`courses edit` is the only terminal command that asks questions. It collects course names for the selected semester's blocks, then saves once. Enter keeps the current value (a blank block stays unused); `-` clears a name. Ctrl+C cancels unsaved input. Name a block **Study Hall** to include a study period. Optional timing choices come from the semester definition.

Prefer arguments for course entry? Use these instead:

```sh
python -m shbs-calendar courses set A "Mathematics"
python -m shbs-calendar courses set T "Study Hall" --timing study-hall
python -m shbs-calendar courses set T "TOEFL" --timing toefl
```

The last command replaces the earlier T selection. `--timing` accepts hyphenated names; existing CSV keys such as `study_hall` remain compatible.

**Upgrading from the menu version:** run `semester use 2026-27-s1` once to confirm the definition. Your existing course CSVs, exceptions and profile identity are retained. The old automatically chosen semester does not count as an explicit selection.

## Export with arguments

```sh
# First and last date, both included. No questions or confirmation menu.
python -m shbs-calendar --dayrange 2026-09-14:2026-09-18

# A single day, next week, or three weeks beginning with a selected week.
python -m shbs-calendar --dayrange 2026-09-17
python -m shbs-calendar --next-week
python -m shbs-calendar --week 2026-09-14 --weeks 3

# Inspect before exporting, or explicitly choose the destination.
python -m shbs-calendar preview --dayrange 2026-09-16:2026-09-18
python -m shbs-calendar export --next-week --late -o exports/next-week.ics
```

You can omit `export` when supplying export flags. `--this-week` is also available. `--first-date DATE --last-date DATE` and their shorter `--start`/`--end` aliases still work. Week shortcuts cover Monday–Sunday; unscheduled days have no events. Every export or preview requires a date range or week shortcut.

**Each terminal export defaults to normal times and the regular weekday timetable**, irrespective of saved GUI settings. Add `--late` to shift start/end times by 20 minutes. Add `--schedule exceptions` to apply saved unusual days. `--normal` and `--schedule weekdays` explicitly select the defaults. Commands do not change remembered GUI dates or timing.

Exports go to the gitignored `exports/` folder. Success reports the event count, dates and path. Existing files require `--overwrite`; an empty selection/range reports an error instead of writing an empty calendar.

To export only selected blocks, add `--only B` or `--only B,T`. To omit blocks, add `--exclude A` or `--exclude A,T`. Both accept repeated flags and unambiguous lowercase names. They filter enabled, named courses for this invocation without editing your CSV or enabling unused blocks. If combined, exclusions take precedence. The same flags work with `preview` and `validate`.

Terminal previews arrange days side by side when space permits, keeping each week together. Long names wrap instead of being cut off. Terminal width is detected automatically; use `preview --next-week --width 100` to set it explicitly, or `--layout list` for the original vertical layout. Redirected output defaults to 120 columns. The GUI keeps its scrollable list preview.

## Unusual school days

```sh
# Friday follows the complete Monday class pattern, on Friday's actual date.
python -m shbs-calendar exceptions set 2026-09-18 --follow monday

# No classes, or a late day with its usual pattern.
python -m shbs-calendar exceptions set 2026-09-21 --off
python -m shbs-calendar exceptions set 2026-09-22 --late

# Apply saved exceptions only when requested for an export.
python -m shbs-calendar --dayrange 2026-09-14:2026-09-25 --schedule exceptions

python -m shbs-calendar exceptions list
python -m shbs-calendar exceptions remove 2026-09-18
```

`--follow` takes a pattern listed by `semester show ID`. Add `--shift 0` or `--shift 20` with `--follow` to replace that date's timing; otherwise it inherits the export's timing. `--normal` sets a usual-pattern day to normal timing. `--note "Text"` records an optional explanation.

Exception scheduling requires at least one saved exception inside the chosen range. Other dates follow normal weekdays. Your date overrides the school's row for that date. Normal weekday exports ignore both files without changing them. No holidays or late days are guessed.

## A different semester

Blocks, their number, weekday arrangements, times and optional duration choices belong to each semester. No block names or shuffle are assumed for a new one.

```sh
python -m shbs-calendar semester new spring --blocks X,Y,Z
```

This creates a **draft**, with an empty `semesters/spring/timetable.csv`. Fill the CSV with the actual arrangements. Each row is one complete event interval:

```csv
pattern,block,start,end
monday,X,08:30,09:10
monday,Y,09:20,10:00
monday,Z,10:10,10:50
tuesday,Y,08:30,09:10
```

Continue with all your scheduled days and blocks. The default weekday mapping is Monday–Friday using lowercase `monday` through `friday`. A mapped pattern must have rows, and every defined block must appear. A semester with fewer days or different patterns can specify, for example, `--weekdays mon=red,tue=blue,fri=red`; omitted weekdays have no classes. The fixed school clock defaults to UTC+08:00 and can be set with `--utc-offset +08:00`.

If you already have a complete CSV, supply it at creation:

```sh
python -m shbs-calendar semester new spring --blocks X,Y,Z --timetable my-timetable.csv
python -m shbs-calendar semester show spring
python -m shbs-calendar semester use spring
python -m shbs-calendar courses edit
```

Use either creation approach, not both for the same ID. A malformed supplied CSV is rejected without creating the semester. A draft cannot be used until its definition validates. `semester use` creates separate blank selections for the new semester; previous semesters stay intact. Definitions are validated again whenever a command opens them.

To deliberately reuse an arrangement, `semester new spring --copy 2026-27-s1` copies only the definition, including timing choices. It does not copy date exceptions or student courses, or activate the result. Review and edit it before use. `semester list` shows available definitions, drafts and the active selection.

Advanced choices, half-day patterns and CSV details: [configuration](docs/configuration.md). Project boundaries and setup rules: [architecture](docs/architecture.md).

## Courses, profiles and GUI

| Command | Action |
| --- | --- |
| `courses list` | Show selected and unused blocks |
| `courses path` | Show the CSV to edit directly |
| `courses edit A T` | Collect inputs only for those blocks |
| `courses set A "Math" --room "Lab 1" --teacher "Example"` | Set a name and optional details |
| `courses disable A T` / `courses enable A T` | Keep names but change inclusion |
| `courses clear A` | Clear a selection |
| `courses import choices.csv` | Validate and replace selections, backing up the old file |
| `validate --next-week` | Validate a selected range without exporting |
| `gui` | Open the simple desktop interface |

Prefix each command with `python -m shbs-calendar`. Use `COMMAND --help` for details. `--root PATH`, `--profile NAME` and `--semester ID` can appear before or after commands. `--semester` selects an existing valid definition for that invocation; `semester use ID` remembers it. To select a default student profile, use `semester use ID --profile NAME`. `init --semester ID --profile NAME` only creates blank files for direct editing.

Courses are saved under `local/profiles/<profile>/<semester>/courses.csv`; personal exceptions sit beside them. **`local/` and `exports/` are gitignored.** Keep the profile's `profile.json` when moving your local data to another machine so event identities remain stable. Semester definitions are shared project data and may be committed; they contain no student selections.

The GUI has courses, dates/preview and exceptions tabs. On first use it asks you to select and review a semester definition. Create new definitions through the terminal or configuration files. After changing definitions on disk, reopen the GUI. The GUI retains its own last-used range; those choices do not affect terminal exports. Its CSV reload and save operations detect conflicting external edits.

Tkinter is needed only for the GUI and is normally included in Python.org desktop installers. On Windows, `shbs-gui.pyw` is also a double-click launcher. The legacy `python -m shbs_calendar` entry point still works.

## Included timetable and calendar files

Exported events contain the course name, start/end times and optional location. No block, teacher or timetable-following annotations are appended. Teacher details remain saved locally; date-exception explanations remain in the preview.

The supplied 2026–27 S1 preset includes only classes/study periods; P&B, CAS, clubs and meals are excluded. Wednesday T runs 15:05–15:45 for both choices. Thursday T ends at **16:25 for study hall** and **17:05 for TOEFL**, starting at 15:45. Late timing adds 20 minutes. Those rules belong to this preset, not every semester.

Files use UTC instants derived from the school's fixed offset. Independent parser checks pass, but actual imports in Google Calendar, Apple Calendar and Outlook remain unverified. Further investigation of dragging files into new Outlook is deferred while the interaction design takes priority.

Use the destination app's calendar import flow: [Google](https://support.google.com/calendar/answer/37118?hl=en), [Apple](https://support.apple.com/guide/calendar/import-or-export-calendars-icl1023/mac), [Outlook web](https://support.microsoft.com/en-us/outlook/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web). Exports are snapshots, not subscriptions. Reimports are not guaranteed to update or delete older events; a separate school calendar and nonoverlapping ranges make them easier to manage.

## Development

```sh
python -m unittest discover -v
```

Opt into native GUI tests with `SHBS_GUI_TESTS=1` (PowerShell: `$env:SHBS_GUI_TESTS='1'`). Optional parser and screenshot tools use `requirements-dev.txt` in a local virtual environment; none are application dependencies. Run `python tools/verify_gui.py` for the main screens, or add `--setup` for semester review. Screenshots use synthetic data, one short-lived window, and ignored `local/qa/` output. See [verification](docs/verification.md) for checks and platform limitations.

Exit codes: `0` success, `2` invalid input/write failure, `130` cancelled course input. The fixed-offset clock does not implement daylight saving. Automatic Excel import, alternating-week rotation and account synchronization are not implemented. Export ranges are capped at 3,660 days. Keep the project folder together; this runs from a source checkout.
