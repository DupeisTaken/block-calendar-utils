# Application workflow and boundaries

## Definition → selection → dated export

The public CLI starts with intent: `--inspect` / `-i`, `--write` / `-w`, or `--export` / `-e`. Targets follow the intent. Repeated intents form a sequence, for example `-w --courses -e --day 0920-0924`. Inspect leaves profiles/settings unchanged and remembers successful dated previews in a separate local snapshot; write owns CSV/setup changes; export writes calendars. `--gui` opens the separate desktop interface.

1. **Define the school timetable.** `--write --semesters --new` creates independent shared files. A blank timetable is a draft; an imported or copied timetable is validated before its folder is installed. Block names/counts, intervals, weekday patterns and duration options are data, not CLI constants.
2. **Choose a valid definition.** `--write --semesters --use` validates and remembers a semester, then creates missing student files. A whole-workflow `--semester` also requires a valid definition. Neither path invents missing block arrangements. The GUI presents a review screen when no selection exists. Selecting a new semester creates blank courses, not guessed mappings from the old one.
3. **Name selected blocks and clubs.** Commands, the GUI and CSV edits use the same profile/semester files. Named study periods are normal selections. `--write --courses --edit` and `--write --activities --edit` collect names and save each batch once; `--write --activities` starts club-name entry. Club slots keep their semester-defined times. Other actions accept arguments and exit. Existing files and profile UUIDs survive activation and upgrades.
4. **Choose dates and selections for this invocation.** New previews and direct exports require inclusive endpoints or explicit week presets. `--export --last-inspect` instead selects a remembered preview. `--only`/`--exclude` filter saved class selections without modifying them. Named enabled clubs default on; CAS defaults off. `--noclub` and `--nocas` explicitly exclude activities. Normal weekday scheduling and normal timing are independent defaults. Inline `--exception DATE[:DATE] RULE` types compose by date; saved rules apply only with `--schedule exceptions`. Terminal exports never inherit or change GUI range/timing preferences.
5. **Preview or export through shared services.** Resolve the actual date to a pattern, apply course duration choices, apply the date's effective shift, then remove whole sessions with the half-day filter (default cutoff 12:30). Explicit blank windows and custom morning/afternoon cutoffs then trim sessions (possibly splitting them), or remove overlapping sessions. Activities follow the same resolution. Preview and export use the same computed events. Terminal previews arrange days in width-aware columns; calendar serialization remains independent of presentation.

## Code and data ownership

`bcutils/` contains the shared Python package. `python -m bcutils` and the root `bcalendar-utils.py` module (`python -m bcalendar-utils`) call the same CLI. `bcutils-gui.pyw` is the Windows desktop launcher. The default data root is the package's parent folder, independent of the checkout's name. The maintained guides replace the original implementation plan.

| Layer | Responsibility |
| --- | --- |
| `cli.py` | Existing argparse handlers; course/club name entry; workspace/service calls |
| `cli_workflow.py` | Split intent stages, enforce read/write boundaries, share context options, preflight all syntax/dates, and run stages in order |
| `cli_interface.py` | Public dash grammar, mnemonic shortcuts and contextual help; normalize to existing handlers |
| `cli_dates.py` | Normalize flexible terminal dates/ranges to ISO before shared validation; current-year, month-first yearless dates |
| `help_style.py` | Shared presentation for help, prompts, lists, previews, outcomes and errors; one accent, terminal opt-out and Windows mode restoration |
| `gui.py` | Semester review and course/activity/date/exception forms; call shared services |
| `semesters.py` | Draft/import/copy definitions and readable timetable summaries |
| `activities.py` | Validate optional school CAS/club slots and local club selections |
| `exceptions.py` | Parse/compose inline exception types and reject conflicts |
| `exception_times.py` | Validate and merge blank windows; trim/split intervals or remove overlaps |
| `terminal.py` | Wrap and align side-by-side day previews, including wide Unicode text |
| `app.py` | Workspace selection, profile initialization, preview/export services |
| `inspection.py` | Store/validate resolved CLI preview snapshots, isolated by root, profile and semester |
| `storage.py` | Validate JSON/CSV, stable file paths, atomic saves and conflicting-edit checks |
| `schedule.py` | Date ranges, pattern resolution, exceptions, options, overlap checks, event identity |
| `ical.py` | Serialize computed events; no UI or semester-specific rules |
| `semesters/<id>/` | Shared school definition and school exceptions; may be versioned |
| `local/profiles/<name>/<id>/` | Course/club selections and personal exceptions; gitignored |
| `local/settings.json` | Active semester/profile and GUI preferences; gitignored |
| `local/inspections/<profile>/<semester>/preview.json` | Last successful dated CLI preview; gitignored and independent of GUI preferences |
| `exports/` | Calendar snapshots; gitignored |

No runtime third-party dependencies are introduced. Tkinter is imported only when opening the GUI. A change to semester files is revalidated on the next CLI command; reopen the GUI after editing them.

## Input and failure behavior

- The CLI normalizes all date entry points before invoking shared services: date/week selectors, first/last endpoints, inline exceptions and saved-exception edits. `--day`, `--day-range`, `--dayrange` and `-d` share one parser; a single date becomes `day` mode and two different dates become `custom` mode. Yearless dates use the current year, with no inferred rollover or year inheritance. Stored CSVs and GUI date fields keep strict ISO syntax.
- Workflow action markers `-i`, `-w` and `-e` are reserved throughout the sequence. `--week`, `--exception`, `--edit` and `--import` stay long-only in that grammar. Other short forms follow initials in the selected scope. Attached values and arguments following `--` remain literal. Internal handler names and earlier standalone entry points are implementation details, not a compatibility promise or a second public navigation system.
- `--root`, `--profile` and `--semester` apply to every stage; conflicting values fail. Each other option belongs to its stage. All stages parse before execution and date syntax is normalized before any prompts or saves. File-dependent validation runs at each stage so later actions see earlier saves. Failures and cancellation stop subsequent stages but do not roll back completed writes. Inspecting in a stack displays results without pausing for approval; separate commands provide a manual review point.
- `--help` is compact; `--docs` expands the selected action, including before setup. Help in any stage exits without executing earlier writes. Unknown prefixes are rejected with spelling suggestions; invalid syntax returns code 2 with correction guidance and a contextual documentation route. Duplicate day selectors fail rather than overwrite one another. Hyphen-separated ranges such as `0920-0924` and `9.20-9.24` use the existing date normalizer.
- Help derives positional arguments, required option groups, allowed values and public short forms from the parser and public vocabulary. Recovery guidance names the actual flag or GUI control. `DestinationExistsError` carries a storage conflict to the CLI, which explains `--overwrite` and an unused `--output` path; storage itself has no command syntax. This also handles a destination created while an exclusive save is being staged.
- `--write --activities` and `--write --courses` default to name entry. Club entry skips CAS, preserves rooms/disabled selections on Enter, validates IDs before prompting, saves once and rejects external edits with the existing digest check. Cancellation discards the unsaved batch.
- Layout is computed as plain text before styling. All terminal interactions use one presentation boundary with bold headings/outcomes and cyan flags/dates/times. Pipes, `NO_COLOR` and `TERM=dumb` remain plain; console modes are restored. Preview alignment and ICS bytes do not depend on ANSI styling.
- Single-day GUI selection uses the shared `date_range("day", anchor)` resolver with identical start/end dates. The GUI mirrors the date into its disabled last-date field and remembers the mode across restarts. CLI selectors remain mutually exclusive; `--weeks` applies only to week presets.

- Both `bcalendar-utils` and `bcutils` are public module entry points. Hyphens are used in flags and timing-choice arguments.
- Legacy `semester` settings were sometimes filled automatically. The new `active_semester` key is set only by explicit activation; old student files are not migrated or overwritten. The user confirms a definition once after upgrading.
- Existing timetable session IDs stay unchanged. Simple CSVs can omit the ID column; generated IDs depend on pattern, block and occurrence order within that pattern/block, so clock changes do not alter identities. Advanced duration overrides should use explicit IDs.
- Event UIDs retain the historical `@shbs-calendar.local` suffix across the project rename. It is a persisted identity marker, not a server address or product label; changing it would change every exported event's identity.
- New semesters never overwrite existing folders. A failed supplied-CSV validation leaves no installed definition. Copying a semester excludes school exceptions and student selections.
- Normal weekday and inline-only exports ignore saved exception files without deleting them. Saved-exception mode validates files and requires at least one saved/inline exception in range. Inline rows replace saved rows in full; independent inline rule types for the same date compose before resolution. Contradictory rules and out-of-range inline dates fail explicitly.
- Exception ranges expand into at most 3,660 per-date rules. Saved batches use one atomic replacement. Optional CSV window fields keep old files readable. A matching custom cutoff replaces its legacy half-day start-time filter; other legacy filters retain whole-session behavior. Merged blank windows operate on final session times, with half-open boundaries. The first surviving piece keeps the occurrence UID; later pieces derive distinct UIDs from the original identity and their start boundary.
- Optional activity files do not add academic blocks or change existing student CSVs. Missing activity files mean none are defined/selected. CAS uses a fixed title; named clubs use their own profile CSV. Semester copies include school activity slots but exclude student names. Activation and profile switches reset GUI inclusion to clubs on and CAS off. Previously remembered choices are restored when reopening the GUI.
- Save validation and fingerprint checks precede atomic replacement. Course input cancellation discards the unsaved batch. Imports can repair a malformed course file while retaining its previous bytes as a backup.
- Empty previews are valid information; exporting an empty calendar through the application is rejected with guidance.
- Successful dated CLI previews atomically remember resolved occurrences after display. `--export --last-inspect` (`-e -l`) reloads these events without invoking the scheduler, fixing relative dates and preserving reviewed values through later source edits. Snapshots are scoped by root/profile/semester and checked against the profile UUID. Empty previews replace prior snapshots; failed previews, lists, help and validation do not. This intentional inspection cache is separate from profile CSVs and GUI settings. `--last-inspect` rejects date/event modifiers and permits destination/overwrite choices; explicit-date exports continue to compute current events independently.
- Default export names include profile, semester and inclusive endpoints, so different selections/rules for the same dates still collide. CLI replacement requires `--overwrite` on that invocation; GUI replacement uses the native save dialog. Replacement writes a complete snapshot without an export backup. Explicit relative output paths use the process working directory, independently of the data root.

Calendar-client behavior is a separate integration concern. The interaction rework preserves the serializer; Outlook drag-in behavior still needs a client-level reproduction.
