# Verification record

Date: 2026-09-13. Host: Windows, Python 3.14.5, Tk 8.6.

## Automated checks

**73 tests passed** with native Tk tests enabled and the independent `icalendar` parser installed in a local verification environment. The latest work adds temporary course filters, day-column previews, optional CAS/named clubs, and composable inline exceptions with a configurable 12:30 cutoff:

- 21 core/storage tests: all five weekdays, 200 minutes per A–G block, both Thursday T options, late shifts, partial and multi-week ranges, Friday following Monday, weekend makeup, closures, exception precedence, custom patterns, a different semester, invalid inputs, CSV round trips, stale saves, interrupted-write preservation, and annotation-free events on regular/makeup days while preserving titles, times, locations, IDs and preview explanations.
- 22 terminal/setup tests: previous setup/course/date/Unicode cases plus per-export block filters without CSV edits, opt-in CAS/named clubs, the hyphenated date-range spelling and separator, inline-rule exports, conflicting flags, and saved half-day commands. Both module entry points are exercised in actual subprocesses.
- 13 native Tk controller tests: shared-service parity, input/save failures, profile/semester switching, and the original date/exception controls; new cases cover club-name saves, activity opt-in/reset across profiles, and preservation of half-day rules when editing saved exceptions.
- 3 terminal layout tests: adjacent day columns, separate calendar weeks, narrow displays, long Chinese and combining-character text without truncation, vertical fallback and empty previews.
- 4 activity tests: workbook-derived CAS/club intervals and titles, opt-in defaults, late shifts, preserved IDs/locations, makeup days and closures, invalid definitions/selections, stale saves and copied semester slots without student names.
- 8 inline-exception tests: order-independent weekday/half-day composition, effective start-time boundaries, whole-session retention across noon, configurable cutoff through semester files, explicit saved/inline precedence without persistence, malformed/conflicting/out-of-range rules, custom weekday mappings, late composition, saved CSV round trips, weekend no-op filters and club filtering after timetable substitution.
- 2 independent parser tests: exact round-trip titles, locations, UTC instants, unique IDs, Unicode/escaped text, absence of event descriptions, and an empty valid calendar. The three-week exception fixture produced the independently expected 74 events.

Command used in the temporary environment:

```powershell
$env:SHBS_GUI_TESTS = '1'
.\.venv-verify\Scripts\python.exe -m unittest discover -v
```

Actual subprocess tests also force an ASCII inherited stream encoding and verify that the CLI emits UTF-8 summaries and Chinese course names correctly. This covers Windows redirected-output behavior without relying on the test runner to supply UTF-8 defaults.

The local verification environment and Python caches remain ignored in this checkout. All verification windows and processes finished. Install `requirements-dev.txt` in a local virtual environment for the optional tools; the application itself does not need those packages. The parser tests used `.venv-verify`; screenshots used the existing system Python with Pillow because Pillow was not installed in that local environment. No additional installation was needed for this rework.

## Visual checks

Reviewed actual application-window screenshots for Courses, Dates & preview, and Exceptions at Tk scaling 1.333 and 2.0. All screenshots used synthetic selections. Only one application-owned window was open at a time and it was destroyed after capture.

The current four main tabs were checked at both scales, including club-name forms and the expanded exception editor. Review found the half-day controls squeezed the exception list at enlarged text size; placing all five inputs in one row restored visibility. The screenshot helper asserts that the first exception row and save/export actions fit. Earlier semester-setup screenshots remain under `local/qa/setup-*.png`.

The actual terminal preview command was also rendered in a single monospace QA window (`tools/verify_preview.py`) with synthetic selections, verifying adjacent Monday/Tuesday and Wednesday/Thursday columns. Its screenshot is `local/qa/terminal-preview.png`.

Screenshot review found and fixed clipping of the export bar and exception editor at enlarged text sizes. The screenshot helper now asserts that Export and Save date remain visible. Course fields scroll, including when keyboard focus moves to a lower row. All ten course rows, including T's timing choice, fit at the standard tested scale. Larger text uses the scrollable course area.

No unrelated app state was changed. Screenshots are local QA artifacts under ignored `local/qa/`; no personal course data or workbook was committed.

## Earlier resource check

A single synthetic three-year export (2026-09-14 through 2029-09-13) produced 4,078 events and 832,365 bytes in **0.54 seconds** while Python allocation tracing was enabled. Peak **traced Python allocations** were **8.8 MiB**; this is not total process memory. Results are a measurement on this machine, not a cross-platform performance guarantee.

## Remaining checks

- macOS execution and native UI have not been run on a Mac. The CI configuration includes Windows/macOS and Python 3.11/3.14 for non-GUI tests, but no remote CI run has been performed here.
- Actual Google Calendar, Apple Calendar, and Outlook imports/reimports have not been performed. Independent parser success is not a substitute for client testing.
- The user reported dragging an ICS into new Outlook and seeing one event. Further client investigation was explicitly deferred while the command workflow and project structure were implemented. The serializer was not changed by this rework; no claim is made that Outlook drag-in behavior is fixed.
- Real calendar notifications, account synchronization, and recurring subscriptions are outside this exporter's scope.

For a client check, import a short synthetic export into a disposable school-test calendar. Check the number of events, local time display, Thursday T end, a replacement weekday, and a holiday. Then test importing an overlapping range and a changed event. Do not assume stable UIDs alone remove old events or update them in every client's file-import flow.
