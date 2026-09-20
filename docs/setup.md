# Setup and your first export

[README](../README.md) · [Command catalogue](command-catalogue.md) · [GUI guide](gui.md)

This guide takes you from the downloaded project folder to your first calendar file. You only need to enter names once; later exports reuse them.

## Open the project

Use Python **3.11 or newer**. Open a terminal in the folder containing `README.md`, `shbs-calendar.py` and `semesters/`. Keep those files together: the app runs directly from the source folder and needs no package installation.

On Windows, check Python with:

```sh
python --version
python -m shbs-calendar --help
```

On macOS, use `python3` in place of `python` throughout these guides. If the command is unavailable or reports an older version, install or select Python 3.11+ before continuing. A “No module named shbs-calendar” error usually means the terminal is outside the project folder.

Choose either route:

- **Desktop:** run `python -m shbs-calendar --gui`, then follow [first launch in the GUI guide](gui.md#first-launch). The window requires Tkinter; the terminal workflow does not.
- **Terminal:** continue below.

## Review and select a timetable

```sh
python -m shbs-calendar -i --semesters
python -m shbs-calendar -i --semesters --show 2026-27-s1
```

Compare the supplied definition with your school timetable, including blocks, activity slots and special T timings. Select it only after reviewing it:

```sh
python -m shbs-calendar -w --semesters --use 2026-27-s1
```

This remembers the semester and creates missing blank files for the initial profile, `me`. Existing names are preserved. If you need different blocks or times, follow [new-semester setup](configuration.md#a-new-semester) first; an empty draft cannot be selected.

For another student, add `--profile student-two` to the selection command. That profile is then remembered. [Profiles and data locations](configuration.md#profiles-and-files).

## Enter course and club names

```sh
python -m shbs-calendar -w --courses
```

Name each block you attend. Leave unused blocks blank; name study periods **Study Hall** if you want them in the calendar. For T, choose `study-hall` or `toefl` when prompted—the name alone does not select its duration.

During entry, **Enter** keeps the current value, **-** clears it, and **Ctrl+C** or EOF cancels the unsaved batch. The whole batch saves once. Existing room/teacher fields and disabled selections are preserved when keeping a name.

For clubs, run:

```sh
python -m shbs-calendar -w --activities
```

Enter club names for the predefined slots. This saves names, not meeting times. CAS has a fixed title and is never prompted for. You can skip this step if you do not attend clubs.

Check the saved entries:

```sh
python -m shbs-calendar -i --courses
python -m shbs-calendar -i --activities
```

## Preview and export

Choose your actual dates; this example uses September 20–24 of the computer's current year:

```sh
python -m shbs-calendar -i --day 0920-0924
python -m shbs-calendar -e --day 0920-0924
```

Preview first, check the titles and times, then run export. Add `--clubs` and/or `--cas` to **both** commands if you want those activities. Normal weekday patterns and normal timing are the terminal defaults. [Date formats, makeup days and closures](commands.md#dates-and-selections).

The command reports the calendar's path under `exports/`. An empty preview is valid, but an empty export is rejected; check names, enabled selections, dates and closures if no events appear.

If the destination already exists, keep the export's options and append `--overwrite` to replace it, or choose an unused path:

```sh
python -m shbs-calendar -e --day 0920-0924 --overwrite
python -m shbs-calendar -e --day 0920-0924 --output "exports/revised-week.ics"
```

`--overwrite` replaces the whole file immediately, without a prompt or export backup. [Export reference](command-catalogue.md#export).

## Import the calendar

Use your calendar app's file-import flow to import the `.ics` file. Check the event count and displayed local times. A separate calendar for these exports makes removing an old import easier.

Exports are snapshots, not subscriptions: later edits require another export and import. Reimporting overlapping ranges may create duplicates or retain old events. Stable event IDs do not guarantee that a calendar client updates or removes events. Actual Google, Apple and Outlook imports/reimports have not been verified; see the [verification record](verification.md#remaining-checks).

## Next time

Reuse saved names and export new dates. To revise a course or club, use the [write commands](command-catalogue.md#write-course-names) or the GUI's [Courses](gui.md#courses) and [CAS & clubs](gui.md#cas-and-clubs) tabs.

For quick terminal help, run `python -m shbs-calendar --docs`. The [workflow guide](commands.md) covers stacked actions, exceptions and corrections; the [command catalogue](command-catalogue.md) lists every public operation and option.
