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

If the export already exists, append **`--overwrite`** to that export action, or choose a new file with `--output "exports/revised.ics"`. [Replacement details](docs/command-catalogue.md#export).

Prefer a window? Run `python -m shbs-calendar --gui` and follow the [GUI guide](docs/gui.md).

## Reference

- [Configuration, CSV formats and backups](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Tests, verification and known limitations](docs/verification.md)

Your names stay in `local/`; default exports go to `exports/`. Both are gitignored. Calendar files are snapshots, not subscriptions; actual calendar-client imports/reimports remain unverified. [Importing your first export](docs/setup.md#import-the-calendar).
