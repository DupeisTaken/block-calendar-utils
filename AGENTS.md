# SHBS Calendar — working agreements

## Product and interaction design

- Keep the entire CLI quiet, minimal and consistent: help, lists, name prompts,
  previews, success, cancellation and errors share the same presentation layer.
  Use whitespace, aligned labels and short headings. No banners, emoji, boxes,
  spinners, animation, rainbow palettes or repeated introductions.
- Color carries meaning. Apply the same treatment to every similar element:
  one accent for flags, dates and times; weight for headings and outcomes; plain
  prose and values. Format text before adding ANSI so alignment stays correct.
- Keep normal interactions brief. `--help` gives essentials; `--docs` provides
  detailed, contextual documentation. Show one useful next step when appropriate.
  Help must never activate a profile, save data or start input prompts.
- Public navigation is --inspect/-i, --write/-w and --export/-e. Targets follow
  the intent; repeated intents run left to right. Older standalone entry points
  are not a compatibility requirement and must not drive the public design.
- Reserve -i, -w and -e as action markers throughout workflows. Use --week,
  --exception, --edit and --import in full. Context flags apply to the whole
  workflow; other options belong to one action. Parse all stages before writing.
  Stop on error/cancellation; completed writes remain saved. Help never executes
  earlier actions. Inspection must not write or prompt for names.
- Short flags use the long name's first letter, e.g. `--day` / `-d`,
  `--activities` / `-a`. If an initial is already used in that scope, keep the
  secondary option long-only, including collisions with workflow markers. Do not
  invent uppercase or unrelated shortcuts.
  Keep old script aliases private to the compatibility path where feasible.
- The friendly CLI layer normalizes input into existing services. Do not add a
  second scheduler or interpret names/file paths as commands. Consume option
  values before looking for command flags. Never silently reinterpret conflicts.
- No ANSI in pipes/files or with `NO_COLOR` / `TERM=dumb`. Use standard-library
  Windows console support with restoration; no runtime package dependency.

## Calendar basics and data ownership

- Python 3.11+; Windows and macOS. The app runs from a source checkout. Tkinter
  is optional for the GUI. No account, server, Excel or synchronization is needed.
- A valid semester is selected explicitly before entering names. Definitions
  live in `semesters/<id>/`: `semester.json`, `timetable.csv`, `activities.csv`,
  and school `exceptions.csv`. Blocks, intervals and weekday patterns are data.
- Student courses, club names and personal exceptions live under
  `local/profiles/<profile>/<semester>/`. Club-name entry changes the profile's
  `activities.csv`; club times are predefined in the semester. There is no
  `schedule.csv` to append club names to. Never alter student files for tests.
- Course and club prompts save once after the whole batch. Enter keeps the old
  value, `-` clears, Ctrl+C/EOF cancels unsaved names. Preserve room/teacher data,
  disabled selections and stable profile UUIDs. Detect external edits before save.
- `--day`, `--day-range`, `--dayrange` and `-d` accept one date or an inclusive
  range. CLI dates allow `-`, `.`, `/`, `YYYYMMDD`, and `MMDD`; omitted years mean
  the current year, month-first. No implicit year inheritance or New Year rollover.
  Saved dates and GUI fields remain ISO `YYYY-MM-DD`.
- Weeks are Monday–Sunday. Normal times/normal weekdays are CLI defaults, without
  inheriting or changing remembered GUI choices. Late timing shifts by +20 min.
- CAS and named clubs are opt-in per export. CAS has a fixed title and is never
  prompted for. Block filters affect class/study selections, not opted-in clubs.
- Date exceptions can replace a weekday pattern, close a day, change timing or
  filter morning/afternoon sessions. Half-day cutoff defaults to 12:30 and uses
  the final session start time after substitutions, timing choices and shifts.
  Never split a session. Inline rules apply only to this invocation; saved rules
  require `--schedule exceptions`. Personal/inline rows replace earlier rows.
- This preset: CAS Monday 15:05–16:05; clubs Tuesday 15:45–16:35 and Wednesday
  15:50–16:40. Wednesday T is 15:05–15:45. Thursday T starts 15:45 and ends 16:25
  for study hall or 17:05 for TOEFL. P&B and meals are excluded.
- Preview/export share one event pipeline. ICS uses UTC instants from the fixed
  school clock (preset UTC+08:00), stable UIDs and clean course titles. Export
  snapshots are not subscriptions; actual calendar-client reimports are unverified.
- Empty previews are valid; empty exports are rejected. Existing destinations
  require overwrite authorization. Ranges are capped at 3,660 days.

## Working and verification practices

- Do not spawn subagents unless the user explicitly asks. Ask when intent is
  unclear; continue independent work while clarifying. Explain tradeoffs before
  coding an alternative to the user's proposed approach.
- Preserve uncommitted work. Use local environments and synthetic temporary
  workspaces. Do not edit personal course/club files during implementation or QA.
- Annotate core implementation ideas. Keep README short and link to
  `docs/setup.md` for onboarding, `docs/commands.md` for workflows,
  `docs/command-catalogue.md` for syntax and functions, and `docs/gui.md` for
  desktop controls. `docs/architecture.md` describes boundaries;
  `docs/verification.md` records checks. Update the relevant guides when behavior changes.
- Add meaningful tests after features. Verify grammar collisions, malformed
  input, help without writes, cancellation, stale saves, export times, Unicode,
  redirected output and compatibility when those areas change.
- Run `.venv-verify/Scripts/python.exe -m unittest discover` with
  `SHBS_GUI_TESTS=1` for the full local suite. Use screenshots for CLI/GUI design
  changes; `tools/verify_preview.py` and `tools/verify_gui.py` use synthetic data.
- Be conservative with machine resources: one short-lived QA window at a time,
  no background servers for this CLI, no redundant test runs. Close owned windows
  and processes and clean generated caches after finishing.
