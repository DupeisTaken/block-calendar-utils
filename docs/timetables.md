# Create and edit a timetable

[Setup](setup.md) · [Command catalogue](command-catalogue.md) · [GUI guide](gui.md)

A fresh checkout has no installed semesters. Enter your own block keys and school times. Course names and personal exceptions are separate from this shared definition. No raw CSV or JSON editing is required.

## From Windows CMD

Open CMD in your checkout. This small example has two blocks on Mondays; replace the keys, days and times with your own:

```bat
cd /d "D:\Working Directory\block-calendar-utils"
python -m bcutils -w --semesters --new mine --blocks X,Y --weekdays mon=red
python -m bcutils -w --semesters --edit mine ^
  --session red-x red X 09:00 09:40 ^
  --session red-y red Y 09:50 10:30 ^
  --activity red-club red club-one club 10:40 11:20
python -m bcutils -i --semesters --show mine
python -m bcutils -w --semesters --use mine
python -m bcutils -w --courses
python -m bcutils -w --activities
```

`^` is CMD's line-continuation character; leave it as the last character on the line. Every mapped weekday must reference a pattern with sessions, and every block needs at least one interval. Omitted weekdays are off. Use comma-separated mappings such as `mon=red,tue=blue,wed=red` to reuse patterns.

For prompts instead of arguments:

```sh
python -m bcalendar-utils -w --semesters --edit mine
```

The editor displays settings and sessions, then accepts these actions:

| Action | What it edits |
| --- | --- |
| `settings` | Display name, complete block list, weekday mapping, UTC offset, half-day cutoff |
| `class` | Add a session or edit one by its existing ID; prompts for pattern, block and times |
| `activity` | Add/edit school CAS or club times; prompts for activity key and kind (`cas`/`club`) |
| `timing` | Add/edit a timing choice for a block and session; `-` inherits a time |
| `remove-class`, `remove-activity` | Remove an interval by session ID |
| `remove-timing` | Remove a block's entire timing choice |
| `show` | Review the current unsaved draft |
| `save` | Validate and save the complete draft |
| `cancel` | Discard changes since opening the editor |

Enter keeps a prompted field. Ctrl+C or EOF cancels the unsaved batch. Invalid saves leave the draft open so you can correct them. If a definition changed externally, cancel and reopen the editor. Nothing is activated automatically.

## Editing individual details

Repeated options compose a single save. `-i --semesters --show ID` displays session IDs and timing overrides. Existing session IDs update the corresponding intervals; new IDs add intervals. Keep IDs stable when changing times so calendar event identities stay stable.

```sh
python -m bcalendar-utils -w --semesters --edit mine --session red-x red X 09:05 09:45
python -m bcalendar-utils -w --semesters --edit mine --timing-option X normal - - - --timing-option X long red-x - 09:50
python -m bcalendar-utils -w --courses --set X "Mathematics" --timing long
python -m bcalendar-utils -w --exceptions --set 2026-09-25 --off --school
```

The first timing option above creates a choice with no overrides; the second changes the end of `red-x`. A `-` time inherits the base session time. Supplying both times as `-` for an existing session removes that override but keeps the choice. `--remove-timing BLOCK CHOICE` removes the entire choice. Existing selected choices must remain valid.

For school closures, substitutions and blank hours, use the existing [exception commands](commands.md#blank-dates-and-hours) with `--school`. Omit `--school` for personal rules. Saved rules still require `--schedule exceptions` in dated inspections/exports.

## In the GUI

Run `python -m bcutils --gui`. On first launch, click **New timetable**. In the main window use **Timetable → New timetable** or **Edit this timetable**.

1. **Semester:** enter your ID, name, blocks, weekday mapping, clock and cutoff. New definitions default to **Start blank**. Click **Create draft**.
2. **Classes:** click **New row**, enter a session ID, pattern, block and start/end, then **Apply row**. Select a saved draft row to load its fields. Keep its ID to update it, or use a new ID to add another interval.
3. **CAS & clubs:** enter meeting intervals with kind `cas` or `club`. Club names are entered later in the main window.
4. **Timing choices:** enter the block, choice and optional session/time override, then **Apply row**. Blank times inherit the base time. Removing an override leaves its choice; remove the remaining blank-session row to remove that choice entirely.
5. **Save timetable** validates all changes together. **Reload** reads the latest files. Closing an unsaved editor asks whether to discard the draft changes.

Unapplied row edits must be applied or discarded before saving or loading a different row. **Remove selected** removes the selected draft row. The setup screen lets you review a complete definition and choose **Use this timetable**. The main window refreshes a saved active definition; preview again to review its new times.

Use the main **Exceptions** tab for date rules. **Save / remove in: School** edits shared exceptions; **Yours** edits personal exceptions. Selecting an existing row also selects its source. Personal rules replace school rules for the same date.

## Optional templates and existing data

```sh
python -m bcalendar-utils -i --semesters --templates
python -m bcalendar-utils -w --semesters --new example --template shbs-example
python -m bcalendar-utils -w --semesters --edit example
```

The SHBS example under `examples/semesters/` is not a confirmed timetable for any school year. It is never installed or activated automatically. Review every interval before use. To reuse your own timetable instead, choose `--new next --copy mine`.

Timetable saves preserve student names, locations, teachers, enabled selections and profile UUIDs. A change that would invalidate an existing profile is rejected; keep its referenced keys/choices or create a separate semester. Changed definition files retain sibling `.bak` backups. Cancellation and validation errors write nothing; detected stale data requires reloading. A caught write error restores earlier replacements, but a power failure is not a multi-file transaction.

User-created semester/profile files remain locally managed. Keep a copy of `semesters/` and `local/` when updating or moving a checkout. Git may remove the previously tracked `2026-27-s1` example during an update; restore your saved definition under the same ID before using its existing profiles. If it was unchanged from the old example, `--new 2026-27-s1 --template shbs-example` reconstructs it without replacing student names or UUIDs. This is an explicit recovery option, not automatic first-run setup. A previously inspected export snapshot remains unchanged after edits; inspect again before exporting the updated timetable.
