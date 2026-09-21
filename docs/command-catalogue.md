# Command catalogue

[README](../README.md) · [First setup](setup.md) · [Workflow examples](commands.md) · [GUI guide](gui.md)

Choose a mode, then its target and options.

| Mode | Command | Use it for | What it saves |
| --- | --- | --- | --- |
| [Inspect](#inspect) | `--inspect` / `-i` | View saved data, preview dates or validate events. | Dated previews remember a local snapshot; profile data/settings stay unchanged. |
| [Write](#write) | `--write` / `-w` | Edit courses, clubs, exceptions, semesters or profile setup. | The selected names, rules or setup files. |
| [Export](#export) | `--export` / `-e` | Create an `.ics` snapshot for selected dates. | A calendar file. |

| Reading the catalogue | Meaning |
| --- | --- |
| Command prefix | Run `python -m shbs-calendar` from the project folder; use `python3` on macOS. Add the syntax shown below. |
| `UPPERCASE` | A value you supply. |
| `[ ... ]` / `...` | Optional / repeatable. |
| `A \| B` | Choose one. |
| — in a shortcut column | Long-only option. |
| Spaces in names or paths | Surround the value with quotes. |

[Inspect](#inspect) · [Write](#write) · [Export](#export) · [Shared options and syntax](#shared-options-and-syntax)

## Inspect

View saved information or preview events with `--inspect` / `-i`.

```text
--inspect TARGET [OPERATION]
--inspect DATE-SELECTOR [EVENT-OPTIONS] [PREVIEW-OPTIONS]
--inspect --validate DATE-SELECTOR [EVENT-OPTIONS]
```

| Inspection behavior | Result |
| --- | --- |
| No target or dates | Show inspection choices. |
| Dated preview | Use [date selectors](#date-selectors) and [event options](#event-options); remember successful previews for `--export --last-inspect`. |
| Lists, validation or help | Leave the remembered preview unchanged. |
| Profile files and settings | Stay unchanged; no name-entry prompts. |
| Saved exceptions | `--inspect --exceptions` lists them; `--schedule exceptions` applies them to a dated preview. |

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

| Target or operation | Short | Scope |
| --- | --- | --- |
| `--semesters` | `-s` | Inspect definitions, including before profile setup. |
| `--courses` | `-c` | Inspect courses in an initialized profile. |
| `--activities` | `-a` | Inspect activities in an initialized profile. |
| `--validate` | `-v` | Validate dated events in an initialized profile. |
| `--exceptions` | — | List both sources; personal rows take precedence over school rows on the same date. Requires an initialized profile. |
| `--list` | `-l` | After a listable target. |
| `--show` | `-s` | After `--semesters`. |
| `--path` | `-p` | After `--courses`. |

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

Save names, selections, rules or setup with `--write` / `-w`. Running it alone shows the targets.

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

| Write behavior | Result |
| --- | --- |
| Action order | Save before the next action starts. |
| Batch name entry | Save once after all answers; cancellation discards the unsaved batch. |
| Saved exceptions | Apply to preview/export only with `--schedule exceptions`. |
| Calendar file | Created separately by [Export](#export). |

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

| Course entry | Behavior |
| --- | --- |
| Find block keys | Run `--inspect --courses`. |
| Omitted room, teacher or timing | Retain existing values. |
| Block with timing choices | Needs a valid choice before it can be enabled. |
| Enter during batch entry | Keep the name and enabled state. |
| `-` during batch entry | Clear the name. |
| New name during batch entry | Enable the course; retain room and teacher values. |
| Ctrl+C / EOF | Cancel unsaved names. |
| Storage | `local/profiles/<profile>/<semester>/courses.csv` |

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

| Club entry | Behavior |
| --- | --- |
| Find slot IDs | Run `--inspect --activities`. |
| Batch keep / clear / cancel | Same as [course entry](#write-course-names). |
| `--room` | Long-only; omission retains the saved value. |
| Names | Saved in the profile's `activities.csv`. |
| Times | Defined by the semester. |
| Inclusion | Named enabled clubs default on; `--noclub` excludes them. |

```sh
python -m shbs-calendar -w --activities --set club-tue "Chess Club" --room Library
python -m shbs-calendar -w --activities --enable club-tue
```

### Write saved exceptions

| Look up | Command or reference |
| --- | --- |
| Blank hours, cutoffs and overlap controls | `python -m shbs-calendar -w --exceptions` |
| All set arguments | `python -m shbs-calendar -w --exceptions --set --docs` |
| Saved and inline examples | [Exception types at a glance](#exception-types-at-a-glance) |

```text
--write --exceptions --set DATE[:DATE] [RULE] [TIME-FILTERS] [--note TEXT]
--write --exceptions --remove DATE[:DATE]
```

| Operation | Effect |
| --- | --- |
| `--set` / `-s` | Replace your entire row for each selected date; repeat every field you want to retain. |
| `--remove` | Long-only; remove your row. A school row may become effective again. |
| Date range | Expand to one row per date; at most 3,660 days. |
| Save | Write the batch once to the profile's `exceptions.csv`. |

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

Time filters work alone or with weekday/timing rules; they cannot combine with `--off`.

| Time option | Short | Behavior |
| --- | --- | --- |
| `--blank-hours HH:MM-HH:MM` | `-b` | Blank hours; repeat or comma-separate windows. |
| `--morning-cutoff HH:MM` | `-m` | Blank everything before this time. |
| `--afternoon-cutoff HH:MM` | `-a` | Blank everything from this time onward. |
| `--overlap trim` or `--overlap remove` | — | Trim/split around windows (default), or remove overlapping sessions. Requires a time filter. |

| Time-filter detail | Behavior |
| --- | --- |
| Inline equivalents | See the [comparison table](#exception-types-at-a-glance); repeat `--exception` to combine independent rules. |
| Time boundaries | Use final school-clock times; affect classes and activities. |
| Middle blank with trim | Can split one session into two events. |
| Touching boundaries | Do not overlap. |
| `24:00` | Allowed as an exclusive end boundary. |
| Legacy half-day filters | Default cutoff 12:30; keep or remove whole sessions by final start time. |
| Explicit cutoffs | Follow the `trim` or `remove` overlap policy. |
| Apply saved rules | Add `--schedule exceptions` to preview/export. |

```sh
python -m shbs-calendar -w --exceptions --set 9.18 --follow monday --half-day no-afternoon
python -m shbs-calendar -w --exceptions --remove 9.18
```

#### Exception types at a glance

| Rule form | How to use the table |
| --- | --- |
| Saved | Add **Saved options** after `-w --exceptions --set DATE[:DATE]`. |
| Inline | Add `--exception DATE[:DATE] RULE` to preview/export for each **Inline rule**; repeat when two rules are shown. |

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

| Policy | Example: 09:00–12:00 session, 10:00–11:00 blanked |
| --- | --- |
| `trim` | Keep **09:00–10:00** and **11:00–12:00** as separate events. |
| `remove` | Remove the entire session. |

Both policies apply after weekday substitution, duration choices and timing shifts.

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

| Combining rules | Result |
| --- | --- |
| Independent weekday, timing and time filters | Can combine. |
| `off` with another exception type | Rejected. |
| Saved `--set` | Replaces the entire row; include every field to retain in the same write. |
| Inline rules | Never save; replace the saved row for that date when saved-exception scheduling is enabled. |

### Write semester definitions and initialize profiles

Prefix semester operations with `--write --semesters` (or `-w -s`).

| Operation | Short | Function |
| --- | --- | --- |
| `--use ID` | `-u` | Validate and remember a definition and the chosen profile; create missing blank profile files. |
| `--new ID --blocks BLOCKS [OPTIONS]` | `--new` / `-n` | Create a draft definition, or import a timetable while creating it. |
| `--new ID --copy SOURCE-ID [--name TEXT]` | `--new` / `-n` | Copy a valid definition and its activity slots, without student selections or school exceptions. |

| Creation rule | Requirement |
| --- | --- |
| Definition source | Choose exactly one of `--blocks` or `--copy`. |
| Destination | Must be new; existing semester folders are never replaced. |
| Empty timetable | Remains a draft and cannot be activated. |

| Creation option | Short | Function |
| --- | --- | --- |
| `--blocks BLOCKS` | `-b` | Comma-separated unique block keys, such as `X,Y,Z`. |
| `--copy SOURCE-ID` | `-c` | Source definition to copy; only `--name` may override a field during copying. |
| `--name TEXT` | `-n` | Display name; default: the new ID. |
| `--timetable FILE` | `-t` | Import a timetable CSV with pattern, block, start and end columns. |
| `--weekdays MAPPING` | — | Map weekdays to patterns, e.g. `mon=red,tue=blue`; omitted weekdays are off. Default: Monday–Friday mapped to their full lowercase names. |
| `--utc-offset OFFSET` | `-u` | Fixed school clock; default `+08:00`. For a negative offset use `--utc-offset=-05:00`. |
| `--noon-cutoff HH:MM` | — | Half-day dividing time; default `12:30`. |

| Profile initialization | Behavior |
| --- | --- |
| Command | `--write --init`; a separate, long-only target. |
| Creates | Missing profile identity, blank course and personal-exception files for the selected semester. |
| Existing files | Preserved. |
| Next step | Enter course names before exporting courses. |

```sh
python -m shbs-calendar -w --semesters --new spring --blocks X,Y,Z
python -m shbs-calendar -w --semesters --new autumn --copy 2026-27-s1 --name "Autumn timetable"
python -m shbs-calendar --profile student-two --semester 2026-27-s1 -w --init
```

See [new-semester configuration](configuration.md#a-new-semester) for the files to complete before selection.

## Export

Write a calendar snapshot with `--export` / `-e`.

| Export source | Options | Events used |
| --- | --- | --- |
| Last dated inspection | `--last-inspect` / `-l` | Exactly the reviewed dates, names, times, activities and exception results. |
| Current data | [Date selectors](#date-selectors) and [event options](#event-options) | Recompute events; named enabled clubs default on, CAS off. Add `--schedule exceptions` for saved rules. |

Export does not accept preview layout options.

```text
--export --last-inspect [--output FILE] [--overwrite]
--export DATE-SELECTOR [EVENT-OPTIONS] [--output FILE] [--overwrite]
```

| Option | Short | Function |
| --- | --- | --- |
| `--last-inspect` | `-l` | Export the exact last successful dated preview for the current profile and semester; works across commands. |
| `--output FILE` | `-o` | Choose an `.ics` destination. Relative paths start in the terminal's current folder, independently of `--root`. Parent folders are created when saving. |
| `--overwrite` | — | Replace an existing destination in this export action. Takes no value and does not prompt or create an export backup. |

| Destination rule | Behavior |
| --- | --- |
| Default path | `<root>/exports/<profile>-<semester>-<first-date>-<last-date>.ics` |
| Same dates, different selections or rules | Still use the same default name. |
| Empty events | Export rejected. |

For the standard review-then-export workflow:

```sh
python -m shbs-calendar -i --day 0920-0924 --late
python -m shbs-calendar -e --last-inspect
python -m shbs-calendar -i --day 0920-0924 --noclub -e -l
```

| Last-inspection rule | Behavior |
| --- | --- |
| Later source edits | Do not change the snapshot; inspect again to include them. |
| Allowed accompanying options | Context, `--output` and `--overwrite` only. |
| Separate commands | Repeat the same profile/semester overrides. |
| Missing, invalid or empty snapshot | Run another dated inspection. |
| Lists, validation and help | Do not replace the snapshot. |
| More examples | [Full last-inspection workflow](commands.md#export-the-last-inspection). |

| Existing destination | What to do |
| --- | --- |
| Replace it | Add `--overwrite` to the failed export's original options. |
| Keep it | Choose an unused `--output` path. |
| Earlier write in a stack succeeded | Retry only the export. |
| Later export in the same stack | Needs its own `--overwrite`; permission does not carry forward. |

```sh
python -m shbs-calendar -e --day 0920-0924 --overwrite
python -m shbs-calendar -e --day 0920-0924 --output "exports/revised-week.ics"
```

## Shared options and syntax

| Option group | Applies to |
| --- | --- |
| [Context and help](#actions-context-and-help) | All three modes. |
| [Date selectors](#date-selectors) and [event options](#event-options) | Dated Inspect/Validate and explicit-date Export. |
| [Write fields](#write) | Their specific target and operation. |

### Syntax conventions

```text
python -m shbs-calendar [CONTEXT] ACTION [TARGET] [OPERATION] [OPTIONS]
python -m shbs-calendar [CONTEXT] ACTION ... ACTION ...
```

| Workflow rule | Behavior |
| --- | --- |
| Execution | Actions run left to right. |
| Syntax and dates | Checked for all stages before any save or prompt. |
| File-dependent validation | Happens when that stage runs. |
| Failure or cancellation | Stops later stages; completed saves remain saved. |
| Preview in a stack | Continues without an approval pause. |
| Dates and action options | Apply only to their stage; do not carry forward automatically. |
| `--last-inspect` | Explicitly selects the remembered preview. |

### Actions, context and help

| Syntax | Short | Function |
| --- | --- | --- |
| `--root PATH` | `-r` | Use a data folder containing `semesters/` and `local/`; default: this source checkout. |
| `--profile NAME` | — | Select the student profile; default: remembered profile, initially `me`. |
| `--semester ID` | — | Use a valid semester without changing the active selection. |
| `--help` | `-h` | Show brief help for the current action/operation. |
| `--docs` | — | Show detailed help for the current action/operation. |
| `--gui` | `-g` | Open the desktop interface as a separate command, with optional context flags. |

| Context or entry rule | Behavior |
| --- | --- |
| Context placement | Applies to **every stage**, wherever supplied. |
| Conflicting context | Rejected; `--semester ID` must match `--write --semesters --use ID` in the same workflow. |
| Profile / semester folder names | 1–64 ASCII letters, digits, dashes or underscores; start with a letter or digit. Windows device names are reserved. |
| Help anywhere | Executes no stages, including earlier writes. |
| `--gui` | Separate command; cannot be stacked with the three modes. |
| GUI context | `--gui --semester ID` remembers that semester; a supplied profile is remembered when activated. CLI overrides do not change the active selection. |

```sh
python -m shbs-calendar --help
python -m shbs-calendar --write --courses --set --docs
python -m shbs-calendar --profile student --write --courses --set A "Mathematics" --export --day 0920-0924
python -m shbs-calendar --gui
```

### Date selectors

Use one selector per dated Inspect/Validate or explicit-date Export action. `--last-inspect` excludes these selectors.

| Syntax | Short | Function |
| --- | --- | --- |
| `--day DATE-OR-RANGE` | `-d` | One day or an inclusive range; aliases `--day-range` and `--dayrange` have identical behavior. |
| `--week DATE` | — | The Monday–Sunday week containing the supplied date. |
| `--this-week` | `-t` | Current Monday–Sunday in the school clock. |
| `--next-week` | `-n` | Next Monday–Sunday in the school clock. |
| `--first-date DATE --last-date DATE` | `--first-date` / `-f`; last date long-only | Explicit inclusive endpoints; both are required. |
| `--weeks COUNT` | — | Add 1–520 consecutive weeks to a week selector; default 1. Invalid with a day or explicit range. |

| Date format or rule | Example / meaning |
| --- | --- |
| Short ranges | `0920-0924`, `9.20-9.24`, `9/20-9/24` |
| Full-year ranges | `20260920-20260924`, `2026-09-20:2026-09-24` |
| Single month-day | `9-20` means September 20. |
| Omitted year | Month-first, computer's current year; no semester-year inheritance or New Year rollover. |
| Compact dates | Four or eight digits. |
| Across New Year | Write both years: `2026.12.30:2027.1.2`. |
| Maximum range | 3,660 days. |
| All accepted forms | [Date formats and selections](commands.md#dates-and-selections). |

### Event options

Use these within dated Inspect/Validate or explicit-date Export. `--last-inspect` rejects them.

| Syntax | Short | Function |
| --- | --- | --- |
| `--only BLOCKS` | — | Keep only these saved course/study selections; comma-separated and repeatable. |
| `--exclude BLOCKS` | — | Remove these course/study blocks; comma-separated and repeatable. Exclusion wins if also listed in `--only`. |
| `--cas` | `-c` | Include CAS with its fixed title; default off. |
| `--clubs` | — | Include enabled, named clubs; default on. |
| `--noclub` | — | Exclude clubs for this action. |
| `--nocas` | — | Exclude CAS (default). |
| `--late` | `-l` in Inspect/Validate; long-only in Export | Shift event start and end by +20 minutes. Export uses `-l` for `--last-inspect`. |
| `--normal` | — | Normal times, the default; cannot combine with `--late`. |
| `--schedule weekdays` | `--schedule` / `-s` | Use regular weekdays and ignore saved rules; default without inline exceptions. Cannot combine explicitly with `--exception`. |
| `--schedule exceptions` | `--schedule` / `-s` | Apply saved school/personal rules plus inline rules; at least one rule must fall inside the range. |
| `--exception DATE[:DATE] RULE` | — | Add an invocation-only rule for one date or an inclusive range; repeat to combine rules. |

| Inline rule family | Accepted values |
| --- | --- |
| Weekday / pattern | `Mon`–`Sun` or a defined pattern; requires a mapped pattern. |
| Closure / timing | `off`, `late`, `normal` |
| Whole-session filters | `no-morning`, `no-afternoon` |
| Time windows / cutoffs | `blank=HH:MM-HH:MM`, `no-morning=HH:MM`, `no-afternoon=HH:MM` |
| Overlap policy | `overlap=trim`, `overlap=remove`; see [blank-window behavior](commands.md#blank-dates-and-hours). |

| Event rule | Behavior |
| --- | --- |
| Contradictory inline rules or dates outside the selected range | Rejected. |
| Opposing activity flags in one action | Rejected. |
| Precedence | Personal rows replace school rows; inline rules replace the saved row in full. [Examples](commands.md#unusual-days). |
| Inline persistence | Never saved to a CSV. |
| Course filters | Leave saved selections unchanged; do not filter included activities. |
| Half-day rules, blank windows, cutoffs and closures | Apply to activities too. |
| CLI timing, ranges and activities | Neither inherit nor change remembered GUI choices. |

```sh
python -m shbs-calendar -i --day 0920-0924 --only A,T --exception 0920 Thu
python -m shbs-calendar -e --day 0920-0924 --clubs --cas --late
```

### Shortcuts and literal values

| Shortcut or value | Rule |
| --- | --- |
| `-i`, `-w`, `-e` | Always start workflow actions. |
| Reserved-initial collisions | Write `--week`, `--weekdays`, `--exception`, `--edit`, `--import` and `--init` in full. |
| Other aliases | Scoped to the current target/operation; use full flags for clarity. Avoid uppercase or unrelated legacy shortcuts. |
| `-s` | Can mean the semester target, `--set`, or `--shift` after an exception-set operation. |
| `-l` | Export: `--last-inspect`. Dated Inspect/Validate: `--late`. Listable target: `--list`. |
| Positional name beginning with a dash | Precede with `--`; all remaining input is literal. Put that stage last or run it separately. |
| Option value beginning with a dash | Attach with `=`, such as `--room=--Example`. |

```sh
python -m shbs-calendar -w --courses --set -- A "--Example"
python -m shbs-calendar -w --activities --set club-tue "Debate" --room=--Example
```

| Exit code or output setting | Meaning |
| --- | --- |
| **0** | Success or help. |
| **2** | Invalid input or write failure. |
| **130** | Cancelled input. |
| Redirected input/output | UTF-8. |
| `NO_COLOR` or `TERM=dumb` | Disable terminal styling. |
| Troubleshooting | [Common corrections](commands.md#when-a-command-fails) and [CSV formats](configuration.md). |
