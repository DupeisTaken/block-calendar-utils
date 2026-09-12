# Verification record

Date: 2026-09-13. Host: Windows, Python 3.14.5, Tk 8.6.

## Automated checks

**35 tests passed**, with native Tk tests enabled and the independent `icalendar` parser installed in a temporary local virtual environment:

- 20 core/storage tests: all five weekdays, 200 minutes per A–G block, both Thursday T options, late shifts, partial and multi-week ranges, Friday following Monday, weekend makeup, closures, exception precedence, custom patterns, a different semester, invalid inputs, CSV round trips, stale saves, and interrupted-write preservation.
- 6 terminal tests: first-run selection, repeat menu, EOF cancellation, direct CSV changes, date flags, preview/export, overwrite behavior, paths with spaces, and operation without importing Tkinter.
- 7 native Tk controller tests: save/preview/export parity with shared services, both T choices, external CSV conflicts, exceptions, invalid dates, cancellation, export errors, and profile switching.
- 2 independent parser tests: exact round-trip titles, locations, descriptions, UTC instants, unique IDs, Unicode/escaped text, and an empty valid calendar. The three-week exception fixture produced the independently expected 74 events.

Command used in the temporary environment:

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
```

The temporary environment and Python caches remain ignored in this checkout: automatic approval review blocked the recursive cleanup command with the reason "blocked by policy." All verification windows and processes finished. For reproducible setup, follow the README's local-venv instructions and install `requirements-dev.txt`. The application itself does not need those packages.

## Visual checks

Reviewed actual application-window screenshots for Courses, Dates & preview, and Exceptions at Tk scaling 1.333 and 2.0. All screenshots used synthetic selections. Only one application-owned window was open at a time and it was destroyed after capture.

Screenshot review found and fixed clipping of the export bar and exception editor at enlarged text sizes. The screenshot helper now asserts that Export and Save date remain visible. Course fields scroll, including when keyboard focus moves to a lower row. All ten course rows, including T's timing choice, fit at the standard tested scale. Larger text uses the scrollable course area.

No unrelated app state was changed. Screenshots are local QA artifacts under ignored `local/qa/`; no personal course data or workbook was committed.

## Resource check

A single synthetic three-year export (2026-09-14 through 2029-09-13) produced 4,078 events and 832,365 bytes in **0.54 seconds** while Python allocation tracing was enabled. Peak **traced Python allocations** were **8.8 MiB**; this is not total process memory. Results are a measurement on this machine, not a cross-platform performance guarantee.

## Remaining checks

- macOS execution and native UI have not been run on a Mac. The CI configuration includes Windows/macOS and Python 3.11/3.14 for non-GUI tests, but no remote CI run has been performed here.
- Actual Google Calendar, Apple Calendar, and Outlook imports/reimports have not been performed. Independent parser success is not a substitute for client testing.
- Real calendar notifications, account synchronization, and recurring subscriptions are outside this exporter's scope.

For a client check, import a short synthetic export into a disposable school-test calendar. Check the number of events, local time display, Thursday T end, a replacement weekday, and a holiday. Then test importing an overlapping range and a changed event. Do not assume stable UIDs alone remove old events or update them in every client's file-import flow.
