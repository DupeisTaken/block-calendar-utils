# Setup and your first export

[README](../README.md) · [Command catalogue](command-catalogue.md) · [GUI guide](gui.md)

This guide takes you from the downloaded project folder to your first calendar file. You only need to enter names once; later exports reuse them.

## Open the project

Use Python **3.11 or newer**. Open a terminal in the folder containing `README.md`, `bcalendar-utils.py` and `bcutils/`. Keep those files together: the app runs directly from the source folder and needs no package installation.

On Windows, check Python with:

```sh
python --version
python -m bcalendar-utils --help
```

On macOS, use `python3` in place of `python` throughout these guides. If the command is unavailable or reports an older version, install or select Python 3.11+ before continuing. A “No module named bcalendar-utils” error usually means the terminal is outside the project folder.

The checkout is named `block-calendar-utils`. You can replace `python -m bcalendar-utils` with `python -m bcutils` in every example. These are source-checkout commands; no global installation or PATH changes are needed.

### Existing checkout after the rename

Keep `semesters/`, `local/` and `exports/` together when moving the checkout. The default data root follows the source folder, so existing profiles and settings need no migration. Update shortcuts, editor project paths and any explicit `--root` paths to the new location. Existing exports and profile UUIDs remain valid; event UIDs deliberately retain their original suffix.

For another clone, update its remote with `git remote set-url origin https://github.com/DupeisTaken/block-calendar-utils.git`. Recreate any Python virtual environment after moving its folder, because activation scripts and installed launchers may embed the previous absolute path. See the [verification record](verification.md) for the optional development environment.

Choose either route:

- **Desktop:** run `python -m bcalendar-utils --gui`, then follow [first launch in the GUI guide](gui.md#first-launch). The window requires Tkinter; the terminal workflow does not.
- **Terminal:** continue below.

## Review and select a timetable

A fresh checkout has **no installed semester**. Define your own block keys and times; no school or year is assumed. Start a draft and open the terminal editor:

```sh
python -m bcalendar-utils -w --semesters --new mine --blocks X,Y,Z
python -m bcalendar-utils -w --semesters --edit mine
```

Use `settings` to set weekday patterns and the school clock. Use `class` to add each interval, `activity` for CAS/club meeting slots, and `timing` for alternative durations. `show` reviews the draft; `save` validates and saves everything together. `cancel`, Ctrl+C or EOF discards unsaved edits. The GUI has the same controls under **New timetable**. [Editor walkthrough and CMD examples](timetables.md).

Review the completed timetable, then activate it:

```sh
python -m bcalendar-utils -i --semesters --show mine
python -m bcalendar-utils -w --semesters --use mine
```

This remembers the semester and creates missing blank files for the initial profile, `me`. Existing names are preserved. An incomplete draft cannot be selected.

Optional examples are listed with `-i --semesters --templates`. Explicitly choose `--new mine --template shbs-example` instead of `--blocks` to copy the SHBS example. It is not a confirmed timetable for any year; review and edit its times before use.

For another student, add `--profile student-two` to the selection command. That profile is then remembered. [Profiles and data locations](configuration.md#profiles-and-files).

## Enter course and club names

```sh
python -m bcalendar-utils -w --courses
```

Name each block you attend. Leave unused blocks blank; name study periods **Study Hall** if you want them in the calendar. For any block with timing choices, select its duration when prompted—the course name alone does not choose times.

During entry, **Enter** keeps the current value, **-** clears it, and **Ctrl+C** or EOF cancels the unsaved batch. The whole batch saves once. Existing room/teacher fields and disabled selections are preserved when keeping a name.

For clubs, run:

```sh
python -m bcalendar-utils -w --activities
```

Enter club names for the slots you defined in the timetable editor. This saves names, not meeting times. CAS has a fixed title and is never prompted for. You can skip this step if you do not attend clubs.

Check the saved entries:

```sh
python -m bcalendar-utils -i --courses
python -m bcalendar-utils -i --activities
```

## Preview and export

Choose your actual dates; this example uses September 20–24 of the computer's current year:

```sh
python -m bcalendar-utils -i --day 0920-0924
python -m bcalendar-utils -e --last-inspect
```

Preview first, check the titles and times, then use `-e --last-inspect` (or `-e -l`). This exports the exact inspected dates and events. Named enabled clubs are included by default. Add `--noclub` to exclude them, or `--cas` to include CAS, on the **inspection** command. CAS stays off by default; `--nocas` explicitly excludes it. Normal weekday patterns and normal timing are the terminal defaults. [Date formats, makeup days and closures](commands.md#dates-and-selections).

For a closure, appointment or shorter day, [blank dates/hours or set morning and afternoon cutoffs](commands.md#blank-dates-and-hours). Preview with the same rules before exporting; choose whether overlapping sessions should be trimmed or removed.

The command reports the calendar's path under `exports/`. An empty preview is valid, but an empty export is rejected; check names, enabled selections, dates and closures if no events appear.

If the destination already exists, keep the export's options and append `--overwrite` to replace it, or choose an unused path:

```sh
python -m bcalendar-utils -e --last-inspect --overwrite
python -m bcalendar-utils -e --last-inspect --output "exports/revised-week.ics"
```

`--overwrite` replaces the whole file immediately, without a prompt or export backup. [Export reference](command-catalogue.md#export).

## Import the calendar

Use your calendar app's file-import flow to import the `.ics` file. Check the event count and displayed local times. A separate calendar for these exports makes removing an old import easier.

Exports are snapshots, not subscriptions: later edits require another export and import. Reimporting overlapping ranges may create duplicates or retain old events. Stable event IDs do not guarantee that a calendar client updates or removes events. Actual Google, Apple and Outlook imports/reimports have not been verified; see the [verification record](verification.md#remaining-checks).

## Next time

Reuse saved names and export new dates. To revise a course or club, use the [write commands](command-catalogue.md#write-course-names) or the GUI's [Courses](gui.md#courses) and [CAS & clubs](gui.md#cas-and-clubs) tabs.

For quick terminal help, run `python -m bcalendar-utils --docs`. The [workflow guide](commands.md) covers stacked actions, exceptions and corrections; the [command catalogue](command-catalogue.md) lists every public operation and option.
