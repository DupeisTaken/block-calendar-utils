# Application workflow and boundaries

## Definition → selection → dated export

1. **Define the school timetable.** `semester new` creates independent shared files. A blank timetable is a draft; an imported or copied timetable is validated before its folder is installed. Block names/counts, intervals, weekday patterns and duration options are data, not CLI constants.
2. **Choose a valid definition.** `semester use` validates and remembers a semester, then creates missing student files. A per-command `--semester` also requires a valid definition. Neither path invents missing block arrangements. The GUI presents a review screen when no selection exists. Selecting a new semester creates blank courses, not guessed mappings from the old one.
3. **Name selected blocks.** Commands, the GUI and CSV edits use the same profile/semester files. Named study periods are normal selections. `courses edit` is the only interactive terminal input collector; other actions accept arguments and exit. Existing files and profile UUIDs survive activation and upgrades.
4. **Choose dates for this invocation.** Inclusive endpoints or explicit week presets are required. Normal weekday scheduling and normal timing are independent defaults. Saved exceptions apply only with `--schedule exceptions`; unspecified dates still follow weekdays. Terminal exports never inherit or change GUI range/timing preferences.
5. **Preview or export through shared services.** Resolve the actual date to a pattern, then course duration options, then the date's effective time shift. Preview and export use the same computed events. No account/client API is involved.

## Code and data ownership

| Layer | Responsibility |
| --- | --- |
| `cli.py` | Parse one action; collect course inputs only on explicit request; concise success/errors |
| `gui.py` | Semester review and course/date/exception forms; call shared services |
| `semesters.py` | Draft/import/copy definitions and readable timetable summaries |
| `app.py` | Workspace selection, profile initialization, preview/export services |
| `storage.py` | Validate JSON/CSV, stable file paths, atomic saves and conflicting-edit checks |
| `schedule.py` | Date ranges, pattern resolution, exceptions, options, overlap checks, event identity |
| `ical.py` | Serialize computed events; no UI or semester-specific rules |
| `semesters/<id>/` | Shared school definition and school exceptions; may be versioned |
| `local/profiles/<name>/<id>/` | Student selections and personal exceptions; gitignored |
| `local/settings.json` | Active semester/profile and GUI preferences; gitignored |
| `exports/` | Calendar snapshots; gitignored |

No runtime third-party dependencies are introduced. Tkinter is imported only when opening the GUI. A change to semester files is revalidated on the next CLI command; reopen the GUI after editing them.

## Compatibility and failure behavior

- The legacy underscore module entry remains an alias. Hyphens are used in documented commands, flags and timing-choice arguments.
- Legacy `semester` settings were sometimes filled automatically. The new `active_semester` key is set only by explicit activation; old student files are not migrated or overwritten. The user confirms a definition once after upgrading.
- Existing timetable session IDs stay unchanged. Simple CSVs can omit the ID column; generated IDs depend on pattern, block and occurrence order within that pattern/block, so clock changes do not alter identities. Advanced duration overrides should use explicit IDs.
- New semesters never overwrite existing folders. A failed supplied-CSV validation leaves no installed definition. Copying a semester excludes school exceptions and student selections.
- Normal weekday exports ignore exception files without deleting them. Exception mode validates them and requires at least one exception in range.
- Save validation and fingerprint checks precede atomic replacement. Course input cancellation discards the unsaved batch. Imports can repair a malformed course file while retaining its previous bytes as a backup.
- Empty previews are valid information; exporting an empty calendar through the application is rejected with guidance.

Calendar-client behavior is a separate integration concern. The interaction rework preserves the serializer; Outlook drag-in behavior still needs a client-level reproduction.
