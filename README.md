# SHBS Calendar

Save your classes and clubs, preview selected dates, and export an `.ics` calendar.

**Python 3.11+ · Windows or macOS · No account, server, Excel or runtime packages.** Tkinter is needed only for the desktop interface.

## Start here

1. [Set up your timetable and names](docs/setup.md).
2. Follow the [terminal workflow guide](docs/commands.md) or the [GUI guide](docs/gui.md) to preview and export.
3. Use the [command catalogue](docs/command-catalogue.md) to look up syntax, options and shortcuts.

## After setup

Run from this folder; on macOS use `python3`:

```sh
python -m shbs-calendar -i --day 0920-0924
python -m shbs-calendar -e --day 0920-0924
```

`-i` inspects, `-w` writes names/rules, and `-e` exports. `0920-0924` means September 20–24 of the current year. Learn to [stack actions](docs/commands.md#navigation-and-sequential-actions) or [choose other dates](docs/commands.md#dates-and-selections).

Named enabled clubs are included by default; use `--noclub` to exclude them. CAS stays off unless you add `--cas`; `--nocas` explicitly excludes it. [Blank dates or hours and set morning/afternoon cutoffs](docs/commands.md#blank-dates-and-hours), with a choice to trim or remove overlapping sessions.

If the export already exists, append **`--overwrite`** to that export action, or choose a new file with `--output "exports/revised.ics"`. [Replacement details](docs/command-catalogue.md#export).

Prefer a window? Run `python -m shbs-calendar --gui` and follow the [GUI guide](docs/gui.md).

## Guides

| Guide | Use it to |
| --- | --- |
| [Setup and first export](docs/setup.md) | Choose a semester, enter names and import your first calendar. |
| [Terminal workflows](docs/commands.md) | Follow examples for stacked actions, date rules, exports and error recovery. |
| [Command catalogue](docs/command-catalogue.md) | Look up commands and options by **Inspect**, **Write** or **Export** mode. |
| [GUI guide](docs/gui.md) | Use the desktop controls for courses, clubs, exceptions and calendars. |
| [Configuration and CSV formats](docs/configuration.md) | Edit definitions and profile files, create semesters and restore backups. |
| [Architecture](docs/architecture.md) | Understand the shared services, data ownership and validation boundaries. |
| [Verification and limitations](docs/verification.md) | Review test results, visual checks and remaining platform/import limitations. |

Your names stay in `local/`; default exports go to `exports/`. Both are gitignored. Calendar files are snapshots, not subscriptions; actual calendar-client imports/reimports remain unverified. [Importing your first export](docs/setup.md#import-the-calendar).
