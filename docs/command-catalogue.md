# Command catalogue

[README](../README.md) · [Setup](setup.md) · [Workflow examples](commands.md) · [GUI guide](gui.md)

Run `python -m bcalendar-utils` from the project folder, followed by the commands below. On macOS, use `python3`.

`python -m bcutils` is the equivalent short entry point, with the same flags, saved data and output.

| Command | Purpose |
| --- | --- |
| [Inspect](#inspect): `--inspect` / `-i` | List saved data or preview events. |
| [Write](#write): `--write` / `-w` | Save names, selections, exceptions or setup. |
| [Export](#export): `--export` / `-e` | Write an `.ics` calendar. |

`UPPERCASE` marks a value you supply; `[ ... ]` is optional; `...` is repeatable. Quote names and paths containing spaces. A dash in the Short column means long-only.

## Inspect

```text
-i TARGET [OPTIONS]
-i DATE-SELECTOR [EVENT-OPTIONS] [PREVIEW-OPTIONS]
```

### Inspection targets

| Command | Purpose |
| --- | --- |
| `-i --semesters` / `-i -s` | List definitions; works before profile setup. |
| `-i --semesters --show ID` | Show a definition's blocks, patterns, times and activities. `--show` has short form `-s`. |
| `-i --courses` / `-i -c` | List course names, block keys, timing choices and enabled state. |
| `-i --courses --path` | Print the course CSV path. `--path` has short form `-p`. |
| `-i --activities` / `-i -a` | List club IDs, names, times and enabled state. |
| `-i --exceptions` | List school and personal rules. |
| `-i DATE-SELECTOR` | Preview events; see [dates](#date-selectors) and [event options](#event-options). |
| `-i --validate DATE-SELECTOR` | Report event count, dates and clock. `--validate` has short form `-v`. |
| `--list` / `-l` | Optional after a listable target; listing is already the default. |

A dated preview remembers its exact events for `-e --last-inspect`. Lists, validation and help leave that snapshot unchanged. Inspection does not change profile files or settings. Empty previews are valid.

### Preview layout

| Argument | Purpose |
| --- | --- |
| `--width NUMBER` | 20–300 columns; default: terminal width, fallback 120. |
| `--layout columns` | Days side by side when space permits; default. |
| `--layout list` | Dates vertically. |

Layout options apply only to event previews.

```sh
python -m bcalendar-utils -i --day 0920-0924 --layout list
```

## Write

```text
-w TARGET [OPERATION] [OPTIONS]
```

| Target | Purpose |
| --- | --- |
| [`--courses` / `-c`](#write-course-names) | Save course names and selections. |
| [`--activities` / `-a`](#write-club-names) | Save club names and selections. |
| [`--exceptions`](#write-saved-exceptions) | Save date rules and time filters. |
| [`--semesters` / `-s`](#write-semester-definitions-and-initialize-profiles) | Create or activate a timetable. |
| [`--init`](#write-semester-definitions-and-initialize-profiles) | Create missing files for the selected profile and semester. |

### Write course names

Prefix operations with `-w --courses`. With no operation, enter names for all blocks.

| Operation | Short | Purpose |
| --- | --- | --- |
| `--edit [BLOCK ...]` | — | Prompt for all blocks or selected keys; save once. |
| `--set BLOCK NAME` | `-s` | Save and enable one course or study period. |
| `--clear BLOCK [BLOCK ...]` | `-c` | Clear names and timing choices; disable blocks. |
| `--enable BLOCK [BLOCK ...]` | — | Enable valid named selections. |
| `--disable BLOCK [BLOCK ...]` | `-d` | Exclude blocks while keeping their names. |
| `--import FILE` | — | Replace selections from a validated CSV; omitted blocks become blank/disabled. Back up the old file. |

Arguments for `--set`:

| Argument | Short | Purpose |
| --- | --- | --- |
| `--room TEXT` | — | Event location. |
| `--teacher TEXT` | `-t` | Local teacher name; excluded from calendar events. |
| `--timing CHOICE` | — | Required for blocks with duration choices, such as T: `study-hall` or `toefl`. |

Omitted fields keep their saved values. During name entry, Enter keeps the current selection, `-` clears it, and Ctrl+C/EOF cancels the unsaved batch. A changed name enables the selection.

```sh
python -m bcalendar-utils -w --courses --set T "Study Hall" --timing study-hall
```

### Write club names

Prefix operations with `-w --activities`. With no operation, enter names for all clubs. CAS has a fixed title and is never prompted for.

| Operation | Short | Purpose |
| --- | --- | --- |
| `--edit [ID ...]` | — | Prompt for all clubs or selected IDs; save once. |
| `--set ID NAME [--room TEXT]` | `-s` | Save and enable a club; omitted room keeps its value. |
| `--clear ID` | `-c` | Clear the name and disable the club. |
| `--enable ID` | — | Enable a valid named club. |
| `--disable ID` | `-d` | Exclude the club while keeping its name. |

Find IDs with `-i --activities`. Name-entry controls match courses; club times remain defined by the semester.

```sh
python -m bcalendar-utils -w --activities --set club-tue "Chess Club" --room Library
```

### Write saved exceptions

| Command | Purpose |
| --- | --- |
| `-w --exceptions --set DATE[:DATE] [RULE-OPTIONS]` | Replace your entire rule on each selected date. `--set` has short form `-s`. |
| `-w --exceptions --remove DATE[:DATE]` | Remove your rules; underlying school rules may apply again. |

Ranges save once, as one row per date. Include every field you want to retain when replacing a rule. Apply saved rules to a preview or direct export with `--schedule exceptions`.

Choose one base rule: `--off`, `--follow`, `--late`, `--normal`, `--no-morning` or `--no-afternoon`. Add time filters as needed, except with `--off`; time filters can also stand alone.

#### Exception types at a glance

```text
-w --exceptions --set DATE[:DATE] [RULE-OPTIONS]
```

| Saved argument | Effect |
| --- | --- |
| `--off` / `-o` | Close the date, including clubs/CAS. Cannot combine with other rules. |
| `--follow PATTERN` / `-f` | Use that pattern's classes and activity slots on the actual date. |
| `--late` / `-l` | Set the date's timing shift to +20 minutes. |
| `--normal` / `-n` | Set the date's timing shift to zero. |
| `--no-morning` | Remove sessions starting before the semester cutoff, default 12:30. |
| `--no-afternoon` | Remove sessions starting at or after the semester cutoff. |
| `--blank-hours HH:MM-HH:MM` / `-b` | Blank a time window; repeat or comma-separate windows. |
| `--morning-cutoff HH:MM` / `-m` | Blank time before this boundary. |
| `--afternoon-cutoff HH:MM` / `-a` | Blank time from this boundary onward. |
| `--overlap trim` | Shorten or split overlapping sessions; default. Requires a time filter. |
| `--overlap remove` | Remove overlapping sessions entirely. Requires a time filter. |
| `--shift MINUTES` / `-s` | With `--follow`: set a shift from -720 to 720 minutes; sessions must stay within the day. |
| `--half-day no-morning` or `--half-day no-afternoon` | Add a whole-session filter to a weekday/timing rule. |
| `--note TEXT` | Add an explanation shown in previews. |

Time filters use final school-clock times after pattern and timing changes, and affect classes and activities. Touching boundaries do not overlap; `24:00` is allowed as an exclusive end. [Details and precedence](commands.md#blank-dates-and-hours).

```sh
# Close two dates.
python -m bcalendar-utils -w --exceptions --set 2026-09-15:2026-09-16 --off

# Follow Monday on Friday; start late and cut off at 15:00.
python -m bcalendar-utils -w --exceptions --set 2026-09-18 --follow monday --shift 20 --afternoon-cutoff 15:00

# Preview the saved rules.
python -m bcalendar-utils -i --day 2026-09-14:2026-09-18 --schedule exceptions
```

### Write semester definitions and initialize profiles

| Command | Purpose |
| --- | --- |
| `-w --semesters --use ID` | Validate and activate a definition; create missing profile files. `--use` has short form `-u`. |
| `-w --semesters --new ID --blocks BLOCKS` | Create a draft, optionally importing a timetable. `--new` has short form `-n`. |
| `-w --semesters --new ID --copy SOURCE-ID` | Copy a valid definition and activity slots, without student selections or school exceptions. |
| `-i --semesters --templates` | List optional example templates; fresh checkouts have no installed semester. |
| `-w --semesters --new ID --template TEMPLATE` | Explicitly copy an example; review its times before use. |
| `-w --semesters --edit ID` | Open the interactive timetable editor; or pass edit arguments below. |
| `-w --init` | Create missing profile identity, course and personal-exception files; preserve existing files. |

Arguments for `--new`:

| Argument | Short | Purpose |
| --- | --- | --- |
| `--blocks BLOCKS` | `-b` | Unique comma-separated keys, e.g. `X,Y,Z`; choose this, `--copy`, or `--template`. |
| `--template ID` | — | Optional example source, e.g. `shbs-example`; only `--name` overrides template fields. |
| `--copy SOURCE-ID` | `-c` | Copy a definition; only `--name` can override copied fields. |
| `--name TEXT` | `-n` | Display name; default: new ID. |
| `--timetable FILE` | `-t` | Import CSV columns: pattern, block, start, end. |
| `--weekdays MAPPING` | — | E.g. `mon=red,tue=blue`; omitted days are off. Default: Monday–Friday use their lowercase full names. |
| `--utc-offset OFFSET` | `-u` | Fixed school clock; default `+08:00`. Use `--utc-offset=-05:00` for negative values. |
| `--noon-cutoff HH:MM` | — | Whole-session half-day boundary; default `12:30`. |

Existing semester folders cannot be replaced. Empty timetables remain drafts and cannot be activated. See [definition setup](configuration.md#a-new-semester).

Arguments for `--edit ID` (one validated save; no edit arguments opens prompts):

| Argument | Short | Purpose |
| --- | --- | --- |
| `--name TEXT` | `-n` | Change display name. |
| `--blocks BLOCKS` | `-b` | Replace the complete block-key list. |
| `--weekdays MAPPING` | — | Replace weekday-to-pattern mappings. |
| `--utc-offset OFFSET` | `-u` | Change the fixed school clock. |
| `--noon-cutoff HH:MM` | — | Change the default half-day cutoff. |
| `--session ID PATTERN BLOCK START END` | `-s` | Add/replace one class interval; repeatable. |
| `--activity ID PATTERN ACTIVITY KIND START END` | `-a` | Add/replace a `cas` or `club` interval; repeatable. |
| `--timing-option BLOCK CHOICE SESSION START END` | `-t` | Add/replace a duration override; `-` inherits a time. A session of `-` with both times `-` creates a choice without overrides. |
| `--remove-session ID` | — | Remove a class interval; repeatable. |
| `--remove-activity ID` | — | Remove an activity interval; repeatable. |
| `--remove-timing BLOCK CHOICE` | — | Remove a complete timing choice; repeatable. |

The editor rejects invalid definitions, external changes and edits that invalidate existing profiles. It preserves session IDs and keeps definition backups. [Interactive, CMD and GUI examples](timetables.md).

Exception `--set` and `--remove` additionally accept `--school` to edit the shared school rules. Omit it for personal rules; personal rows still override school rows for the same date.

## Export

```text
-e --last-inspect [--output FILE] [--overwrite]
-e DATE-SELECTOR [EVENT-OPTIONS] [--output FILE] [--overwrite]
```

| Argument | Short | Purpose |
| --- | --- | --- |
| `--last-inspect` | `-l` | Export the exact last dated inspection for this profile and semester, even across separate commands. |
| `--output FILE` | `-o` | Choose an `.ics` path; relative paths start at the terminal's current folder. Parent folders are created. |
| `--overwrite` | — | Replace the destination immediately, without a prompt or backup; applies only to this export. |

### Inline exception rules

```text
-e DATE-SELECTOR --exception DATE[:DATE] RULE [--exception DATE[:DATE] RULE ...]
```

Repeat `--exception` to combine rules. Dates must be inside the selected range. Also available with dated `-i`; unavailable with `--last-inspect`.

| Inline rule | Effect |
| --- | --- |
| `off` | Close the date, including clubs/CAS. Cannot combine with other rules. |
| `Mon`–`Sun` or a defined pattern | Use that weekday/pattern's classes and activities on the actual date. |
| `late` | Set the date's timing shift to +20 minutes. |
| `normal` | Set the date's timing shift to zero. |
| `no-morning` | Remove sessions starting before the semester cutoff, default 12:30. |
| `no-afternoon` | Remove sessions starting at or after the semester cutoff. |
| `blank=HH:MM-HH:MM` | Blank a time window; repeat the exception or comma-separate windows. |
| `no-morning=HH:MM` | Blank time before this boundary. |
| `no-afternoon=HH:MM` | Blank time from this boundary onward. |
| `overlap=trim` | Shorten or split overlapping sessions; default. Requires a time filter. |
| `overlap=remove` | Remove overlapping sessions entirely. Requires a time filter. |

Inline rules apply only to this action. Add `--schedule exceptions` to include saved rules; inline rules replace the saved row for their date.

```sh
python -m bcalendar-utils -e --day 2026-09-14:2026-09-18 --exception 2026-09-15:2026-09-16 off
python -m bcalendar-utils -e --day 2026-09-18 --exception 2026-09-18 blank=10:00-11:00 --exception 2026-09-18 overlap=remove
```

### Export examples and destination

```sh
python -m bcalendar-utils -i --day 0920-0924 --late
python -m bcalendar-utils -e --last-inspect

# Or inspect and export in one command, without pausing.
python -m bcalendar-utils -i --day 0920-0924 -e -l
```

With `--last-inspect`, only context, output and overwrite options may accompany it. Repeat context overrides across separate commands. To change events, inspect again. [Snapshot details](commands.md#export-the-last-inspection).

Without `--last-inspect`, supply [dates](#date-selectors) and [event options](#event-options) to compute from current data. Empty exports are rejected.

Default destination: `<root>/exports/<profile>-<semester>-<first-date>-<last-date>.ics`. If it exists, add `--overwrite` or choose a new `--output` path. After a successful write followed by a failed export, retry only the export.

## Shared options and syntax

### Syntax conventions

```text
python -m bcalendar-utils [CONTEXT] ACTION [TARGET] [OPTIONS]
python -m bcalendar-utils [CONTEXT] ACTION ... ACTION ...
```

Actions run left to right. All syntax and dates are checked before saving or prompting; file contents are checked when each action runs. Errors or cancellation stop later actions; completed saves remain. [Workflow examples](commands.md#navigation-and-sequential-actions).

### Actions, context and help

| Argument | Short | Purpose |
| --- | --- | --- |
| `--root PATH` | `-r` | Data folder containing `semesters/` and `local/`; default: this checkout. |
| `--profile NAME` | — | Student profile; default: remembered profile, initially `me`. |
| `--semester ID` | — | Use a valid definition without changing the active CLI selection. |
| `--help` | `-h` | Brief help; no actions execute. |
| `--docs` | — | Detailed help for the current command; no actions execute. |
| `--gui` | `-g` | Open the desktop interface separately; supplied profile/semester choices are remembered when activated. |

Context applies to every action; conflicting values are rejected. Other options belong only to their action. `--semester ID` must match any `--semesters --use ID` in the workflow. [Profile naming and storage](configuration.md#profiles-and-files).

### Date selectors

Use one selector per dated Inspect/Validate or direct Export action. The explicit first/last pair counts as one. These cannot combine with `--last-inspect`.

| Argument | Short | Purpose |
| --- | --- | --- |
| `--day DATE[:DATE]` | `-d` | One date or inclusive range; aliases: `--day-range`, `--dayrange`. |
| `--week DATE` | — | Monday–Sunday containing the date. |
| `--this-week` | `-t` | Current Monday–Sunday in the school clock. |
| `--next-week` | `-n` | Next Monday–Sunday in the school clock. |
| `--first-date DATE --last-date DATE` | `-f` for first date | Inclusive endpoints; both required. |
| `--weeks COUNT` | — | 1–520 consecutive weeks with a week selector; default 1. |

Dates accept `-`, `.`, `/`, `YYYYMMDD` or `MMDD`; e.g. `2026-09-20`, `9.20`, `0920-0924`. Omitted years mean the computer's current year, month-first. Across New Year, write both years. Maximum range: 3,660 days. [All date formats](commands.md#dates-and-selections).

### Event options

Apply to dated Inspect/Validate and direct Export, not `--last-inspect`. Defaults: normal weekdays/times, named enabled clubs on, CAS off. CLI options do not inherit or change GUI settings.

| Argument | Short | Purpose |
| --- | --- | --- |
| `--only BLOCKS` | — | Keep selected course/study blocks; comma-separated and repeatable. |
| `--exclude BLOCKS` | — | Omit course/study blocks; repeatable. Exclusion wins over `--only`. |
| `--cas` | `-c` | Include CAS. |
| `--nocas` | — | Exclude CAS; default. |
| `--clubs` | — | Include named enabled clubs; default. |
| `--noclub` | — | Exclude clubs. |
| `--late` | `-l` in Inspect/Validate only | Shift starts and ends +20 minutes. In Export, `-l` means `--last-inspect`. |
| `--normal` | — | Normal timing; cannot combine with `--late`. |
| `--schedule weekdays` | `-s weekdays` | Ignore saved rules; default without inline exceptions. Cannot combine with `--exception`. |
| `--schedule exceptions` | `-s exceptions` | Apply saved and inline rules; requires a rule inside the range. |
| `--exception DATE[:DATE] RULE` | — | Apply an inline rule; repeat to combine. See [inline exception rules](#inline-exception-rules). |

Block filters leave saved selections and included activities unchanged. Date rules affect activities too. Personal rules replace school rows; inline rules replace a saved row in full and never save. Conflicting rules, opposing activity flags and inline dates outside the range are rejected. [Precedence examples](commands.md#unusual-days).

### Shortcuts and literal values

`-i`, `-w` and `-e` always start actions. Write `--week`, `--weekdays`, `--exception`, `--edit`, `--import` and `--init` in full. Other shortcuts depend on the current target or operation; use full flags when unsure.

For a positional name starting with a dash, use `--` and put that action last: all remaining input is literal. For an option value, use `=`.

```sh
python -m bcalendar-utils -w --courses --set -- A "--Example"
python -m bcalendar-utils -w --activities --set club-tue "Debate" --room=--Example
```

Exit codes: **0** success/help, **2** invalid input or write failure, **130** cancelled input. Pipes use UTF-8 without styling; `NO_COLOR` or `TERM=dumb` also disables styling. [Troubleshooting](commands.md#when-a-command-fails).
