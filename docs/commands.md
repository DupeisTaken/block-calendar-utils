# Command guide

[README](../README.md) · [First setup](setup.md) · [Command catalogue](command-catalogue.md) · [GUI guide](gui.md)

This guide explains workflows and common corrections. For an operation-by-operation syntax reference, use the [command catalogue](command-catalogue.md).

Run code-block commands from the source folder; use `python3` on macOS. Inline fragments are arguments to `python -m shbs-calendar`, not standalone shell commands. Replace uppercase placeholders such as `ID`, `DATE` and `NAME`; brackets in help mean optional arguments and are not typed.

## Navigation and sequential actions

Start with an intent, then its target and options:

| Intent | Form | Effect |
| --- | --- | --- |
| Inspect | `--inspect` / `-i` | Read saved entries or compute a preview without writing files |
| Write | `--write` / `-w` | Save names, selections, rules or semester setup |
| Export | `--export` / `-e` | Write an `.ics` snapshot |

```sh
python -m shbs-calendar -i --courses
python -m shbs-calendar -w --courses
python -m shbs-calendar -e --day 0920-0924
python -m shbs-calendar -w --courses -i --day 0920-0924 -e --day 0920-0924
```

A new intent starts a new action. Actions run left to right. Repeat `-w` to write more than one target. Each write saves once before the next action; later actions read the saved result. Syntax and date input for the whole workflow are checked before any prompt or save. File contents and scheduling are validated when each action runs, after earlier writes have completed.

An error or Ctrl+C/EOF stops subsequent actions. Completed saves remain saved; the workflow is not a transaction. A preview displays events and continues without a confirmation prompt. To review before exporting, run inspection and export separately. After a failed export following a successful write, retry only the export.

`--root PATH`, `--profile NAME` and `--semester ID` apply to the entire workflow wherever they appear. Conflicting values are rejected. Other options apply only to their action: repeat dates, clubs, filters and exception rules for both preview and export.

```sh
python -m shbs-calendar --profile student -w --courses --set A "Mathematics" -w --activities --set club-tue "Chess Club" -e --day 9.14:9.18 --clubs
```

`-i`, `-w` and `-e` always start workflow actions. Use `--week`, `--exception`, `--edit` and `--import` in full. Other short flags use the first letter within their scope; colliding secondary options stay long-only. For example, `-d` means `--day` in an export, but `--disable` in a course-write action. `--profile`, `--semester`, `--clubs`, `--only`, `--exclude`, `--overwrite` and `--docs` are long-only.

Use `--` before literal positional values that start with a dash, for example `-w --courses --set -- A "--export"`. Everything after `--` is literal, so put that action last or run it separately. Option values starting with a dash can use `=`, for example `--room=--write`. Ordinary names and paths are never interpreted as actions.

## Inspect

```sh
python -m shbs-calendar -i --semesters
python -m shbs-calendar -i --semesters --show 2026-27-s1
python -m shbs-calendar -i --courses
python -m shbs-calendar -i --courses --path
python -m shbs-calendar -i --activities
python -m shbs-calendar -i --exceptions
python -m shbs-calendar -i --day 0920-0924
python -m shbs-calendar -i --validate --day 0920-0924
```

With a target, inspection lists saved data; `--semesters --show ID` reviews a full definition and `--courses --path` prints its CSV location. Without a target, date options select an event preview. `--validate` reports the event count, dates and school clock without writing a calendar. Empty previews/validation are valid.

Semester inspection works before setup. Course, activity, exception and event inspection needs an initialized profile. `--exceptions` lists school and personal rules labeled `school` and `yours`; personal rows take precedence on matching dates.

Preview-only options are `--width NUMBER` (20–300 columns; default terminal width, fallback 120) and `--layout columns` or `--layout list`. Columns show days side by side where space permits; list stacks them vertically. Validation and export accept neither option.

## Write names and setup

```sh
python -m shbs-calendar -w --semesters --use 2026-27-s1
python -m shbs-calendar -w --courses
python -m shbs-calendar -w --activities
python -m shbs-calendar -w --courses --set A "Mathematics" --room "Room 1"
python -m shbs-calendar -w --courses --set T "Study Hall" --timing study-hall
python -m shbs-calendar -w --activities --set club-tue "Chess Club" --room Library
```

Select a reviewed semester before entering names. Courses and activities default to batch name entry. **Enter** keeps the current value, **-** clears it, and **Ctrl+C** or EOF discards the unsaved batch. Enter preserves a disabled selection's state. New names enable the selection. Timing choices, room and teacher values are retained unless explicitly changed. CAS has a fixed title and is never prompted for.

| Write target | Operations |
| --- | --- |
| `--courses` | Default name entry; `--edit [BLOCK ...]`, `--set BLOCK NAME`, `--clear BLOCK ...`, `--enable BLOCK ...`, `--disable BLOCK ...`, `--import FILE` |
| `--activities` | Default club-name entry; `--edit [ID ...]`, `--set ID NAME`, `--clear ID`, `--enable ID`, `--disable ID` |
| `--exceptions` | `--set DATE` with a rule, or `--remove DATE` |
| `--semesters` | `--use ID` to select a timetable, or `--new ID` to create one |
| `--init` | Create missing blank course and personal-exception files without replacing existing data |

`--clear` removes a name and disables it. `--disable` keeps its name; `--enable` requires a valid existing name. `--set` saves and enables one selection immediately. Course `--set` also accepts `--room`, `--teacher` and `--timing`; club `--set` accepts `--room`. T's name does not choose its duration: this preset requires `--timing study-hall` or `--timing toefl`.

Course import validates and replaces all course selections from the supplied CSV; omitted blocks become blank/disabled. It retains the previous CSV as `.bak`. Names with spaces need quotes. Find exact block keys or club IDs with `-i --courses` or `-i --activities`. Club writes change the profile's names, never school slot times.

## Export and overwrite

```sh
python -m shbs-calendar -e --day 9.18
python -m shbs-calendar -e --day 9.14:9.18 --clubs --cas
python -m shbs-calendar -e --week 0914 --weeks 2
python -m shbs-calendar -e --day 9.18 --output "exports/friday.ics"
```

The default file is `<root>/exports/<profile>-<semester>-<first-date>-<last-date>.ics`. Changing names, filters, timing or rules does not change that filename. `--output FILE` selects another `.ics` path; relative paths start in the terminal's current folder, independently of `--root`. Quote paths with spaces. Saving creates missing parent folders. An empty export is rejected.

If the file exists, append **`--overwrite` to the export action**. It takes no value and replaces the entire file without prompting, merging or making an export backup. To keep the old file, choose an unused `--output` path:

```sh
python -m shbs-calendar -e --day 0920-0924 --exception 0920 Thu --exception 0924 Fri --overwrite
python -m shbs-calendar -e --day 0920-0924 --exception 0920 Thu --exception 0924 Fri --output "exports/revised-week.ics"
```

Keep the failed export's other options when retrying. `--overwrite` applies only to its export action, not every export in a stack.

## Dates and selections

Preview, validation and export share these options:

| Option | Meaning |
| --- | --- |
| `--day DATE` / `-d DATE` | One day or inclusive date range |
| `--week DATE` | Monday–Sunday containing the date |
| `--this-week`, `--next-week` | Current or next Monday–Sunday in the school clock |
| `--weeks COUNT` | 1–520 consecutive weeks; default 1, only with week selectors |
| `--first-date DATE`, `--last-date DATE` | Inclusive endpoints; supply both |
| `--only BLOCKS`, `--exclude BLOCKS` | Comma-separated course/study block filters; repeatable |
| `--clubs`, `--cas` | Include named enabled clubs or fixed-title CAS; default off |
| `--late`, `--normal` | Shift start/end +20 minutes or use normal timing; normal is default |
| `--exception DATE RULE` | Change one date for this action; repeatable |
| `--schedule exceptions` | Also apply saved school/personal rules |

Supply one date selector per action. `--day 9.14 --day 9.18` is rejected; use a range. A week selector takes one date, not a range. All ranges are capped at 3,660 days. Filters never edit saved selections and do not filter opted-in CAS/clubs. CLI choices do not inherit or change remembered GUI export preferences.

| Date or range | Meaning |
| --- | --- |
| `2026-09-20`, `2026.9.20`, `2026/9/20`, `20260920` | September 20, 2026 |
| `9-20`, `9.20`, `9/20`, `0920` | September 20 of the computer's current year |
| `1.2`, `0102` | January 2 of the current year |
| `0920-0924`, `9.20-9.24`, `9/20-9/24` | Inclusive September 20–24 |
| `20260920-20260924` | Full compact dates with a hyphen between them |
| `2026-09-20:2026-09-24` | Recommended separator when each date contains hyphens |
| `9.20..9.24`, `"9.20 to 9.24"` | Other inclusive range forms; quote spaces |
| `2026.12.30:2027.1.2` | Explicit range across New Year |

`--day-range` and `--dayrange` also accept these inputs. Yearless input is current-year and month-first; it never inherits another endpoint's year or the semester's year. `12.30:1.2` is reversed, so write both years. Compact dates need four or eight digits with leading zeroes. Use consistent separators within each date. Day-first input, two-digit years, three-digit compact input and nonexistent dates are rejected. A single `9-20` is a date, not a range. CSVs and GUI fields keep ISO `YYYY-MM-DD`.

## Unusual days

Inline rules change only the inspection/export action where they appear:

```sh
python -m shbs-calendar -i --day 9.14:9.18 --exception 9.18 Mon
python -m shbs-calendar -e --day 9.14:9.18 --exception 9.18 Mon --exception 9.18 no-afternoon
```

Rules include `Mon`–`Sun`, a semester-defined pattern, `off`, `late`, `normal`, `no-morning` and `no-afternoon`. A weekday rule needs a pattern mapped to that weekday. `off` removes every event, including activities. Independent weekday, timing and half-day rules compose on the same date; contradictory rules and dates outside the selected range are errors.

To save a rule for future exports, write it to the personal exception CSV:

```sh
python -m shbs-calendar -w --exceptions --set 9.18 --follow monday --half-day no-afternoon
python -m shbs-calendar -e --day 9.14:9.18 --schedule exceptions
python -m shbs-calendar -w --exceptions --remove 9.18
```

For `--set DATE`, choose exactly one of `--off`, `--follow PATTERN`, `--late`, `--normal`, `--no-morning` or `--no-afternoon`. `--follow` takes the full pattern name (`monday` in this preset). With `--follow`, `--shift MINUTES` replaces the export shift with -720 to 720 minutes, staying within the same day. Add `--half-day no-morning` or `--half-day no-afternoon` to a weekday/timing rule; `--note TEXT` adds a preview explanation. A closure cannot have a half-day filter.

Saved rows apply only with `--schedule exceptions`, which requires a saved or inline rule inside the range. Personal rows replace school rows in full. `--set` replaces the entire personal row, so repeat fields you want to keep. Removing a personal rule can reveal a school rule underneath. An inline rule replaces the whole saved row for its date, too: an inline `late` alone discards a saved weekday substitution; repeat both inline rules to retain both effects. Explicit `--schedule weekdays` cannot accompany inline exceptions.

Half-day filtering uses final start times after pattern substitution, duration choices and shifts. At the semester cutoff (default **12:30**), `no-morning` removes earlier starts; `no-afternoon` removes starts at or after it. Whole sessions, including activities, are kept or removed without splitting.

## Context and definitions

`--root PATH` / `-r PATH` selects a folder containing `semesters/`, `local/` and default `exports/`; it defaults to this source checkout. The initial profile is `me`. `--profile NAME` selects a student for the workflow; `--semester ID` selects a valid timetable without activating it. `-w --semesters --use ID` remembers the semester and selected profile. Names contain 1–64 ASCII letters, digits, dashes or underscores, starting with a letter or digit; Windows device names are reserved.

```sh
python -m shbs-calendar --profile student-two -w --semesters --use 2026-27-s1 -w --courses
python -m shbs-calendar --profile student-two -i --day 9.18
python -m shbs-calendar -w --semesters --new spring --blocks X,Y,Z
python -m shbs-calendar -w --semesters --new autumn --copy 2026-27-s1
```

Name-entry/set operations create missing profile files. Inspecting student data and exporting require an initialized profile. Personal CSVs live in `local/profiles/<profile>/<semester>/`; stable identity lives in `local/profiles/<profile>/profile.json`.

A new definition requires exactly one of `--blocks` or `--copy`. With `--blocks`, optional fields are `--name`, `--timetable FILE`, `--weekdays`, `--utc-offset` and `--noon-cutoff HH:MM`. With `--copy`, only `--name` may override a definition field; edit the copied files for other changes. Empty timetables are drafts and cannot be activated. Copies include school activity slots but omit school exceptions and student names. [CSV formats and new-semester setup](configuration.md#a-new-semester).

## When a command fails

Keep the same context options when following a correction. The fragments below follow `python -m shbs-calendar`.

| Problem | Next action |
| --- | --- |
| Destination exists | Retry the export with `--overwrite`, or an unused `--output "exports/another-name.ics"`. |
| No timetable selected | Inspect `-i --semesters`, review `-i --semesters --show ID`, then select `-w --semesters --use ID`. |
| Profile not set up | Run `-w --courses` with that profile/semester to enter names. |
| No events | Replace `-e` with `-i` and remove `--output`/`--overwrite`. Inspect courses, filters, dates and closures; for clubs inspect `-i --activities` and include `--clubs`. |
| No enabled clubs | Use `-w --activities --set ID "Club name"` or `-w --activities --enable ID`. |
| T needs timing | Add `--timing study-hall` or `--timing toefl` to `-w --courses --set T "Name"`. |
| No exceptions in range | Remove `--schedule exceptions`, or add/save a rule inside the selected dates. |
| CSV changed during name entry | Rerun name entry to load the latest file, then reenter edits. In the GUI use **Reload CSV** on Courses. |
| Invalid destination | Use an `.ics` filename in a writable folder, such as `--output "exports/revised.ics"`. |

For desktop export, run `python -m shbs-calendar --gui`, use **Dates & preview → Export .ics**, then choose a filename or accept the native save dialog's replacement confirmation. `--overwrite` is a terminal option.

## Help and presentation

```sh
python -m shbs-calendar --help
python -m shbs-calendar --docs
python -m shbs-calendar -i --docs
python -m shbs-calendar -i --day 0920-0924 --docs
python -m shbs-calendar -w --courses --set --docs
python -m shbs-calendar -e --docs
```

Help works before setup and never prompts or writes, even if earlier actions in the same command would write. `--help` gives essentials; `--docs` expands the current action. Running `-i` or `-w` alone shows its navigation choices.

Errors return **2**, cancelled input **130**, and success/help **0**. Lists, prompts, results and errors share aligned labels, whitespace and one accent for flags, dates and times. Pipes and files receive plain text. `NO_COLOR` or `TERM=dumb` disables color; Windows console settings are restored after output.
