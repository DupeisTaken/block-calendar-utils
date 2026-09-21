# Command catalogue

[README](../README.md) · [First setup](setup.md) · [Workflow examples](commands.md) · [GUI guide](gui.md)

Start with one of three modes. Choose **Inspect** to read or preview, **Write** to save profile data or setup, and **Export** to create a calendar file.

| Mode | Command | Use it for | What it saves |
| --- | --- | --- | --- |
| [Inspect](#inspect) | `--inspect` / `-i` | View saved data, preview dates or validate events. | Nothing; no name-entry prompts. |
| [Write](#write) | `--write` / `-w` | Edit courses, clubs, exceptions, semesters or profile setup. | The selected names, rules or setup files. |
| [Export](#export) | `--export` / `-e` | Create an `.ics` snapshot for selected dates. | A calendar file. |

All syntax fragments below follow `python -m shbs-calendar`; use `python3` on macOS and run from the project folder. Uppercase words are values you supply. `[ ... ]` means optional; `...` means repeatable; `A | B` means choose one. An em dash in a shortcut column means long-only. Quote names and paths containing spaces.

[Inspect](#inspect) · [Write](#write) · [Export](#export) · [Shared options and syntax](#shared-options-and-syntax)

## Inspect

Use `--inspect` / `-i` to view information without saving data. With no target or date selector, it shows the inspection choices.

```text
--inspect TARGET [OPERATION]
--inspect DATE-SELECTOR [EVENT-OPTIONS] [PREVIEW-OPTIONS]
--inspect --validate DATE-SELECTOR [EVENT-OPTIONS]
```

For dated previews and validation, use the shared [date selectors](#date-selectors) and [event options](#event-options). `--inspect --exceptions` lists saved rules; it does not apply them to a dated preview. Add `--schedule exceptions` to the preview to apply them.

### Inspection targets

| Syntax | Function |
| --- | --- |
| `--inspect --semesters [--list]` | List available definitions and their ready, active or draft/invalid state. |
| `--inspect --semesters --show ID` | Show blocks, weekday patterns, intervals, timing choices and activity slots. |
| `--inspect --courses [--list]` | List block keys, saved names, timing choices and disabled selections. |
| `--inspect --courses --path` | Print the profile's course CSV path. |
| `--inspect --activities [--list]` | List activity IDs, saved club names, enabled state and predefined slots. |
| `--inspect --exceptions [--list]` | List school and personal date rules with their source. |
| `--inspect DATE-SELECTOR [EVENT-OPTIONS]` | Preview the resolved events. An empty preview is valid. |
| `--inspect --validate DATE-SELECTOR [EVENT-OPTIONS]` | Validate the resolved events and report count, dates and clock without exporting. |

Target shortcuts: `--semesters` / `-s`, `--courses` / `-c`, `--activities` / `-a`, `--validate` / `-v`. `--exceptions` is long-only. After a target, `--list` / `-l`, `--show` / `-s` and `--path` / `-p` apply in their respective scopes.

Semester inspection works before profile setup. Other inspection requires an initialized profile. Personal exceptions take precedence over school rows on the same date, although the list shows both sources.

### Preview layout

| Syntax | Function |
| --- | --- |
| `--width NUMBER` | Width from 20 to 300 columns; default: detected terminal width, fallback 120. |
| `--layout columns` | Arrange days side by side when space permits; default layout. |
| `--layout list` | Display dates vertically. |

Validation and export do not accept `--width` or `--layout`.

```sh
python -m shbs-calendar -i --semesters --show 2026-27-s1
python -m shbs-calendar -i --courses --path
python -m shbs-calendar -i --day 0920-0924 --layout list
python -m shbs-calendar -i --validate --day 0920-0924
```

## Write

Use `--write` / `-w` to save names, selections, date rules or setup. Select a target first; its operations and options follow it. Running `--write` alone shows the available targets.

```text
--write TARGET [OPERATION] [OPTIONS]
```

| Target | What you can save | When the operation is omitted |
| --- | --- | --- |
| [Courses](#write-course-names): `--courses` / `-c` | Course names, enabled selections, rooms, teachers and timing choices. | Prompt for course names. |
| [Clubs](#write-club-names): `--activities` / `-a` | Club names, enabled state and rooms. | Prompt for club names. |
| [Exceptions](#write-saved-exceptions): `--exceptions` | Closures, weekday changes, blank hours and morning/afternoon cutoffs. | Show the available operations and time filters. |
| [Semesters](#write-semester-definitions-and-initialize-profiles): `--semesters` / `-s` | Create a definition or activate an existing one. | Show the available operations. |
| [Profile setup](#write-semester-definitions-and-initialize-profiles): `--init` | Create missing profile files for the selected semester. | Run initialization; no separate operation is needed. |

Each write saves before the next action starts. Batch name entry saves once after all answers; cancellation discards that unsaved batch. Saved exceptions affect preview/export only with `--schedule exceptions`. Writing names or rules does not create an `.ics` file; use [Export](#export) for that.

### Write course names

Prefix each operation with `--write --courses` (or `-w -c`). Without an operation, enter names for all blocks.

| Operation | Short | Function |
| --- | --- | --- |
| `--edit [BLOCK ...]` | — | Prompt for all blocks, or only the supplied keys; save the batch once. |
| `--set BLOCK NAME` | `-s` | Save and enable one course or study period immediately. |
| `--clear BLOCK [BLOCK ...]` | `-c` | Clear names and timing choices; disable those blocks. |
| `--enable BLOCK [BLOCK ...]` | — | Enable valid named selections. |
| `--disable BLOCK [BLOCK ...]` | `-d` | Keep saved names but exclude the blocks from events. |
| `--import FILE` | — | Validate and replace all course selections from a CSV; omitted blocks become blank/disabled. Back up the old CSV. |

Options for `--set`:

| Syntax | Short | Function |
| --- | --- | --- |
| `--room TEXT` | — | Set the calendar event's location. |
| `--teacher TEXT` | `-t` | Save a teacher name locally; not included in calendar events. |
| `--timing CHOICE` | — | Select a semester-defined duration, such as `study-hall` or `toefl` for T. |

Omitted room/teacher/timing options retain existing values. A block with timing choices needs a valid choice before it can be enabled. Find exact block keys with `--inspect --courses`.

During batch entry, Enter keeps the current name and enabled state, `-` clears it, and Ctrl+C/EOF cancels unsaved names. Changing a name enables it. Saved room/teacher values are retained. Course files are `local/profiles/<profile>/<semester>/courses.csv`.

```sh
python -m shbs-calendar -w --courses --edit A B
python -m shbs-calendar -w --courses --set T "Study Hall" --timing study-hall
python -m shbs-calendar -w --courses --disable A B
python -m shbs-calendar -w --courses --import "course-selections.csv"
```

### Write club names

Prefix each operation with `--write --activities` (or `-w -a`). Without an operation, enter names for all club slots. CAS has a fixed title and is excluded from name entry.

| Operation | Short | Function |
| --- | --- | --- |
| `--edit [ID ...]` | — | Enter names for all clubs or selected IDs; save once. |
| `--set ID NAME [--room TEXT]` | `-s` | Save and enable one club, optionally setting its event location. |
| `--clear ID` | `-c` | Clear the name and disable the club. |
| `--enable ID` | — | Enable an existing valid club name. |
| `--disable ID` | `-d` | Keep the name but exclude the club. |

Find slot IDs using `--inspect --activities`. Batch keep/clear/cancel behavior matches course entry. `--room` is long-only and retains its old value when omitted. Names save to the profile's `activities.csv`; times stay in the semester definition. Named enabled clubs are included by default; `--noclub` excludes them.

```sh
python -m shbs-calendar -w --activities --set club-tue "Chess Club" --room Library
python -m shbs-calendar -w --activities --enable club-tue
```

### Write saved exceptions

`python -m shbs-calendar -w --exceptions` shows the available blank-hours, morning/afternoon cutoff and overlap controls. For all arguments, use `-w --exceptions --set --docs`.

See [exception types at a glance](#exception-types-at-a-glance) for side-by-side saved/inline syntax and complete examples.

```text
--write --exceptions --set DATE[:DATE] [RULE] [TIME-FILTERS] [--note TEXT]
--write --exceptions --remove DATE[:DATE]
```

`--set` / `-s` replaces your entire saved row for each selected date. `--remove` is long-only and removes only your row; a school row may become effective again. A range expands to one row per date; the whole batch saves once to the profile's `exceptions.csv`.

Choose one `RULE`, or supply time filters below:

| Rule | Short | Function |
| --- | --- | --- |
| `--off` | `-o` | Remove every event for the date, including CAS and clubs. |
| `--follow PATTERN` | `-f` | Use a defined pattern such as `monday`; inspect the semester to find its pattern names. |
| `--late` | `-l` | Use the usual weekday pattern with a +20-minute shift. |
| `--normal` | `-n` | Use the usual pattern with a zero-minute shift. |
| `--no-morning` | — | Use the usual pattern and remove starts before the cutoff. |
| `--no-afternoon` | — | Use the usual pattern and remove starts at or after the cutoff. |

Additional fields:

| Syntax | Short | Function |
| --- | --- | --- |
| `--shift MINUTES` | `-s` | With `--follow` only: replace export timing with -720 to 720 minutes; sessions must stay within their day. |
| `--half-day no-morning` or `--half-day no-afternoon` | — | Add a whole-session filter to a weekday/timing rule; not valid with `--off`. |
| `--note TEXT` | — | Save an explanation shown in previews. |

Time filters may be used alone or with a weekday/timing rule; they cannot combine with `--off`. `--set` and `--remove` accept `DATE[:DATE]` (at most 3,660 days).

| Time option | Short | Behavior |
| --- | --- | --- |
| `--blank-hours HH:MM-HH:MM` | `-b` | Blank hours; repeat or comma-separate windows. |
| `--morning-cutoff HH:MM` | `-m` | Blank everything before this time. |
| `--afternoon-cutoff HH:MM` | `-a` | Blank everything from this time onward. |
| `--overlap trim` or `--overlap remove` | — | Trim/split around windows (default), or remove overlapping sessions. Requires a time filter. |

Inline equivalents are `--exception DATE[:DATE] blank=10:00-11:00`, `no-morning=09:30`, `no-afternoon=15:00` and `overlap=remove`. Repeat `--exception` to combine independent rules. Boundaries use final school-clock times and affect classes and activities. A middle blank can create two events; touching boundaries do not overlap. `24:00` is an exclusive end boundary. Opposing activity flags are rejected within one action.

Repeat fields you want to retain when replacing a rule. Saved rules affect preview/export only with `--schedule exceptions`. Legacy half-day filters default to 12:30 and use final start times. Explicit cutoffs use the overlap policy.

```sh
python -m shbs-calendar -w --exceptions --set 9.18 --follow monday --half-day no-afternoon
python -m shbs-calendar -w --exceptions --remove 9.18
```

#### Exception types at a glance

For saved rules, add the **Saved options** after `-w --exceptions --set DATE[:DATE]`. For a one-off preview/export, pass each **Inline rule** as `--exception DATE[:DATE] RULE`; repeat `--exception` when a row shows two rules.

| Exception type | Saved options | Inline rule | What happens |
| --- | --- | --- | --- |
| Whole day off | `--off` | `off` | Remove every event on the selected dates, including clubs/CAS. |
| Different weekday | `--follow monday` | `Mon` | Use Monday's timetable on the actual date, including its activity slots. |
| Late timing | `--late` | `late` | Replace that date's timing shift with +20 minutes. |
| Normal timing | `--normal` | `normal` | Use zero shift for that date, even if the export uses `--late`. |
| Skip morning sessions | `--no-morning` | `no-morning` | Remove sessions starting before the semester cutoff, default 12:30. |
| Skip afternoon sessions | `--no-afternoon` | `no-afternoon` | Remove sessions starting at or after the semester cutoff. |
| Blank hours, trim | `--blank-hours 10:00-11:00 --overlap trim` | `blank=10:00-11:00` and `overlap=trim` | Shorten or split sessions around the gap; trim is the default. |
| Blank hours, remove | `--blank-hours 10:00-11:00 --overlap remove` | `blank=10:00-11:00` and `overlap=remove` | Drop any session that overlaps the gap. |
| Morning time cutoff | `--morning-cutoff 09:30` | `no-morning=09:30` | Blank times before 09:30; trim overlapping sessions by default. |
| Afternoon time cutoff | `--afternoon-cutoff 15:00` | `no-afternoon=15:00` | Blank times from 15:00 onward; trim overlapping sessions by default. |
| Custom timing shift | `--follow monday --shift -10` | No arbitrary-shift inline rule | Use Monday's timetable 10 minutes earlier. Saved `--shift` requires `--follow`. |

The session filters keep or remove whole sessions by their final start time. Explicit time cutoffs and blank hours use `trim` or `remove` after weekday substitution, duration choices and timing shifts. A 09:00–12:00 session with 10:00–11:00 blanked becomes **09:00–10:00 and 11:00–12:00** under `trim`, or disappears under `remove`.

These examples are separate scenarios; replace the dates with your own.

```sh
# Save a two-day closure, then preview the week with saved exceptions.
python -m shbs-calendar -w --exceptions --set 2026-09-15:2026-09-16 --off
python -m shbs-calendar -i --day 2026-09-14:2026-09-18 --schedule exceptions

# Save a Friday that follows Monday, starts late and ends at 15:00.
python -m shbs-calendar -w --exceptions --set 2026-09-18 --follow monday --shift 20 --afternoon-cutoff 15:00
python -m shbs-calendar -i --day 2026-09-18 --schedule exceptions

# Preview a one-off gap, removing any interrupted session without saving a rule.
python -m shbs-calendar -i --day 2026-09-18 --exception 2026-09-18 blank=10:00-11:00 --exception 2026-09-18 overlap=remove
```

Independent weekday, timing and time-filter rules can combine. `off` cannot combine with other exception types. Saved `--set` replaces the entire row for each date, so include every field you want to retain in the same write. Inline rules never save and replace any saved row for the same date when saved-exception scheduling is enabled.

### Write semester definitions and initialize profiles

Prefix semester operations with `--write --semesters` (or `-w -s`).

| Operation | Short | Function |
| --- | --- | --- |
| `--use ID` | `-u` | Validate and remember a definition and the chosen profile; create missing blank profile files. |
| `--new ID --blocks BLOCKS [OPTIONS]` | `--new` / `-n` | Create a draft definition, or import a timetable while creating it. |
| `--new ID --copy SOURCE-ID [--name TEXT]` | `--new` / `-n` | Copy a valid definition and its activity slots, without student selections or school exceptions. |

Choose exactly one of `--blocks` or `--copy`. Existing semester folders are never replaced. An empty timetable is a draft and cannot be activated.

| Creation option | Short | Function |
| --- | --- | --- |
| `--blocks BLOCKS` | `-b` | Comma-separated unique block keys, such as `X,Y,Z`. |
| `--copy SOURCE-ID` | `-c` | Source definition to copy; only `--name` may override a field during copying. |
| `--name TEXT` | `-n` | Display name; default: the new ID. |
| `--timetable FILE` | `-t` | Import a timetable CSV with pattern, block, start and end columns. |
| `--weekdays MAPPING` | — | Map weekdays to patterns, e.g. `mon=red,tue=blue`; omitted weekdays are off. Default: Monday–Friday mapped to their full lowercase names. |
| `--utc-offset OFFSET` | `-u` | Fixed school clock; default `+08:00`. For a negative offset use `--utc-offset=-05:00`. |
| `--noon-cutoff HH:MM` | — | Half-day dividing time; default `12:30`. |

`--write --init` is a separate, long-only target. It creates missing profile identity, blank course and personal-exception files for the selected semester without replacing existing files. Names still need to be entered before exporting courses.

```sh
python -m shbs-calendar -w --semesters --new spring --blocks X,Y,Z
python -m shbs-calendar -w --semesters --new autumn --copy 2026-27-s1 --name "Autumn timetable"
python -m shbs-calendar --profile student-two --semester 2026-27-s1 -w --init
```

See [new-semester configuration](configuration.md#a-new-semester) for the files to complete before selection.

## Export

Use `--export` / `-e` to write a calendar snapshot. Supply a date selector on every export action; review the same dates and options with [Inspect](#inspect) first.

Use the shared [date selectors](#date-selectors) and [event options](#event-options) for ranges, clubs/CAS, timing, block filters and inline exceptions. Named enabled clubs are included by default; CAS is off. Add `--schedule exceptions` to apply saved date rules. Export does not accept the preview layout options.

```text
--export DATE-SELECTOR [EVENT-OPTIONS] [--output FILE] [--overwrite]
```

| Option | Short | Function |
| --- | --- | --- |
| `--output FILE` | `-o` | Choose an `.ics` destination. Relative paths start in the terminal's current folder, independently of `--root`. Parent folders are created when saving. |
| `--overwrite` | — | Replace an existing destination in this export action. Takes no value and does not prompt or create an export backup. |

Without `--output`, the file is `<root>/exports/<profile>-<semester>-<first-date>-<last-date>.ics`. Different selections or rules for the same dates still use that name. An empty export is rejected.

To replace a file, append `--overwrite` to the failed export's original options. To keep it, choose an unused output path. If a prior write in a stack succeeded, retry only the export. Replacement permission does not carry into later exports in the stack.

```sh
python -m shbs-calendar -e --day 0920-0924 --overwrite
python -m shbs-calendar -e --day 0920-0924 --output "exports/revised-week.ics"
```

## Shared options and syntax

These options support the three modes; the tables state where each applies. Date selectors and event options belong to **dated Inspect/Validate and Export**. Write operations use their own target-specific fields above.

### Syntax conventions

```text
python -m shbs-calendar [CONTEXT] ACTION [TARGET] [OPERATION] [OPTIONS]
python -m shbs-calendar [CONTEXT] ACTION ... ACTION ...
```

Actions execute left to right. Syntax and date input for every stage are checked before any save or prompt; file-dependent validation happens when that stage runs. A failure or cancellation stops later stages, but completed saves remain saved. A preview in a stack does not pause for approval. Dates and other action options do not carry into the next stage.

### Actions, context and help

| Syntax | Short | Function |
| --- | --- | --- |
| `--root PATH` | `-r` | Use a data folder containing `semesters/` and `local/`; default: this source checkout. |
| `--profile NAME` | — | Select the student profile; default: remembered profile, initially `me`. |
| `--semester ID` | — | Use a valid semester without changing the active selection. |
| `--help` | `-h` | Show brief help for the current action/operation. |
| `--docs` | — | Show detailed help for the current action/operation. |
| `--gui` | `-g` | Open the desktop interface as a separate command, with optional context flags. |

Context flags apply to **every stage** regardless of placement. Conflicting values are rejected. `--semester ID` must match a `--write --semesters --use ID` in the same workflow. Profile and semester folder names use 1–64 ASCII letters, digits, dashes or underscores, starting with a letter or digit; Windows device names are reserved.

Help executes no stages, even after a write stage. `--gui` is not a stackable inspect/write/export stage. Unlike a CLI context override, launching `--gui --semester ID` selects and remembers that semester; a supplied GUI profile is also remembered when activated.

```sh
python -m shbs-calendar --help
python -m shbs-calendar --write --courses --set --docs
python -m shbs-calendar --profile student --write --courses --set A "Mathematics" --export --day 0920-0924
python -m shbs-calendar --gui
```

### Date selectors

These work with event inspection, validation and export. Supply one selector per action; the explicit first/last pair counts as one selector.

| Syntax | Short | Function |
| --- | --- | --- |
| `--day DATE-OR-RANGE` | `-d` | One day or an inclusive range; aliases `--day-range` and `--dayrange` have identical behavior. |
| `--week DATE` | — | The Monday–Sunday week containing the supplied date. |
| `--this-week` | `-t` | Current Monday–Sunday in the school clock. |
| `--next-week` | `-n` | Next Monday–Sunday in the school clock. |
| `--first-date DATE --last-date DATE` | `--first-date` / `-f`; last date long-only | Explicit inclusive endpoints; both are required. |
| `--weeks COUNT` | — | Add 1–520 consecutive weeks to a week selector; default 1. Invalid with a day or explicit range. |

Examples: `0920-0924`, `9.20-9.24`, `9/20-9/24`, `20260920-20260924` and `2026-09-20:2026-09-24`. A single `9-20` is September 20. Yearless input is month-first and uses the computer's current year; it never inherits a semester year or rolls over New Year. Compact input needs four or eight digits. Across New Year, write both years, e.g. `2026.12.30:2027.1.2`. Ranges cannot exceed 3,660 days. [All date formats](commands.md#dates-and-selections).

### Event options

These apply to preview, validation and export, but only within their own action.

| Syntax | Short | Function |
| --- | --- | --- |
| `--only BLOCKS` | — | Keep only these saved course/study selections; comma-separated and repeatable. |
| `--exclude BLOCKS` | — | Remove these course/study blocks; comma-separated and repeatable. Exclusion wins if also listed in `--only`. |
| `--cas` | `-c` | Include CAS with its fixed title; default off. |
| `--clubs` | — | Include enabled, named clubs; default on. |
| `--noclub` | — | Exclude clubs for this action. |
| `--nocas` | — | Exclude CAS (default). |
| `--late` | `-l` | Shift event start and end by +20 minutes. |
| `--normal` | — | Normal times, the default; cannot combine with `--late`. |
| `--schedule weekdays` | `--schedule` / `-s` | Use regular weekdays and ignore saved rules; default without inline exceptions. Cannot combine explicitly with `--exception`. |
| `--schedule exceptions` | `--schedule` / `-s` | Apply saved school/personal rules plus inline rules; at least one rule must fall inside the range. |
| `--exception DATE[:DATE] RULE` | — | Add an invocation-only rule for one date or an inclusive range; repeat to combine rules. |

Inline rules are `Mon`–`Sun`, a defined pattern, `off`, `late`, `normal`, `no-morning`, `no-afternoon`, `blank=HH:MM-HH:MM`, `no-morning=HH:MM`, `no-afternoon=HH:MM` and `overlap=trim` / `overlap=remove`. Time rules follow the [blank-window behavior](commands.md#blank-dates-and-hours). Weekday rules require a mapped pattern. Contradictory rules and inline dates outside the selected range are rejected. Personal rows replace school rows, and inline rules replace a saved row for that date in full. Inline rules never save to a CSV. [Precedence and examples](commands.md#unusual-days).

Course filters never edit saved selections and do not filter included activities. Half-day rules, blank windows, cutoffs and closures do apply to activities. CLI timing/range/activity choices neither inherit nor change remembered GUI choices.

```sh
python -m shbs-calendar -i --day 0920-0924 --only A,T --exception 0920 Thu
python -m shbs-calendar -e --day 0920-0924 --clubs --cas --late
```

### Shortcuts and literal values

`-i`, `-w` and `-e` always start workflow actions. Therefore `--week`, `--weekdays`, `--exception`, `--edit`, `--import` and `--init` have no short spelling in their scopes. Other aliases in this catalogue are scoped to the current target/operation. For example, `-s` can select the semester target, select a `--set` operation, or supply `--shift` after a saved-exception set operation.

Use full flags when clarity matters. Do not use uppercase or unrelated legacy shortcuts. A positional name beginning with a dash needs `--`; all remaining input then becomes literal, so put that stage last or run it separately. Option values beginning with a dash can use `=`.

```sh
python -m shbs-calendar -w --courses --set -- A "--Example"
python -m shbs-calendar -w --activities --set club-tue "Debate" --room=--Example
```

Exit codes: **0** success/help, **2** invalid input or write failure, **130** cancelled input. Redirected input/output uses UTF-8; `NO_COLOR` or `TERM=dumb` disables terminal styling. See [common corrections](commands.md#when-a-command-fails) and [CSV formats](configuration.md) for recovery and file details.
