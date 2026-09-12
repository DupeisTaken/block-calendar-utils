# Verification record

Date: 2026-09-13. Host: Windows, Python 3.14.5, Tk 8.6.

## Automated checks

**52 tests passed** after the argument-driven interaction rework, with native Tk tests enabled and the independent `icalendar` parser installed in a local verification environment (5.15 seconds for the final suite run):

- 20 core/storage tests: all five weekdays, 200 minutes per A–G block, both Thursday T options, late shifts, partial and multi-week ranges, Friday following Monday, weekend makeup, closures, exception precedence, custom patterns, a different semester, invalid inputs, CSV round trips, stale saves, and interrupted-write preservation.
- 19 terminal/setup tests: no-argument help without writes/prompts; explicit activation including legacy settings; course commands, timing choices, Unicode metadata, repair by CSV import and atomic input cancellation; dayrange/single-day/endpoints/week shortcuts; exception commands and weekday defaults independent of GUI settings; overwrite/empty export handling; flags before/after actions; actual subprocess execution of both module entry points; no Tk import; empty-workspace drafts; arbitrary X/Y/Z blocks and red/blue patterns; failed-import cleanup; stable generated IDs after clock changes; explicit copies without courses/exceptions; revalidation of edited definitions; per-command semester selection; read-only commands without profile creation; and activation failure without creating student data.
- 11 native Tk controller tests: save/preview/export parity with shared services, both T choices, external CSV conflicts, exceptions, invalid dates, cancellation, export errors, profile switching, editable endpoints and weekday/exception switching. New setup tests verify explicit review/activation, invalid draft rejection, arbitrary X/Y blocks and a red pattern without a hardcoded Monday default.
- 2 independent parser tests: exact round-trip titles, locations, descriptions, UTC instants, unique IDs, Unicode/escaped text, and an empty valid calendar. The three-week exception fixture produced the independently expected 74 events.

Command used in the temporary environment:

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
```

Actual subprocess tests also force an ASCII inherited stream encoding and verify that the CLI emits UTF-8 summaries and Chinese course names correctly. This covers Windows redirected-output behavior without relying on the test runner to supply UTF-8 defaults.

The local verification environment and Python caches remain ignored in this checkout. All verification windows and processes finished. Install `requirements-dev.txt` in a local virtual environment for the optional tools; the application itself does not need those packages. The parser tests used `.venv-verify`; screenshots used the existing system Python with Pillow because Pillow was not installed in that local environment. No additional installation was needed for this rework.

## Visual checks

Reviewed actual application-window screenshots for Courses, Dates & preview, and Exceptions at Tk scaling 1.333 and 2.0. All screenshots used synthetic selections. Only one application-owned window was open at a time and it was destroyed after capture.

After the command/semester rework, rechecked all three main tabs and the new semester review screen at both scales. The timetable review is scrollable, semester activation remains visible, and date fields, normal-weekday choice and export controls remain accessible. Setup screenshots are `local/qa/setup-1.333.png` and `local/qa/setup-2.0.png`.

Screenshot review found and fixed clipping of the export bar and exception editor at enlarged text sizes. The screenshot helper now asserts that Export and Save date remain visible. Course fields scroll, including when keyboard focus moves to a lower row. All ten course rows, including T's timing choice, fit at the standard tested scale. Larger text uses the scrollable course area.

No unrelated app state was changed. Screenshots are local QA artifacts under ignored `local/qa/`; no personal course data or workbook was committed.

## Resource check

A single synthetic three-year export (2026-09-14 through 2029-09-13) produced 4,078 events and 832,365 bytes in **0.54 seconds** while Python allocation tracing was enabled. Peak **traced Python allocations** were **8.8 MiB**; this is not total process memory. Results are a measurement on this machine, not a cross-platform performance guarantee.

## Remaining checks

- macOS execution and native UI have not been run on a Mac. The CI configuration includes Windows/macOS and Python 3.11/3.14 for non-GUI tests, but no remote CI run has been performed here.
- Actual Google Calendar, Apple Calendar, and Outlook imports/reimports have not been performed. Independent parser success is not a substitute for client testing.
- The user reported dragging an ICS into new Outlook and seeing one event. Further client investigation was explicitly deferred while the command workflow and project structure were implemented. The serializer was not changed by this rework; no claim is made that Outlook drag-in behavior is fixed.
- Real calendar notifications, account synchronization, and recurring subscriptions are outside this exporter's scope.

For a client check, import a short synthetic export into a disposable school-test calendar. Check the number of events, local time display, Thursday T end, a replacement weekday, and a holiday. Then test importing an overlapping range and a changed event. Do not assume stable UIDs alone remove old events or update them in every client's file-import flow.
