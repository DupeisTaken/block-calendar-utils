# GUI guide

[README](../README.md) · [First setup](setup.md) · [Command catalogue](command-catalogue.md)

The desktop interface edits the same local files as the terminal. It needs Python 3.11+ with Tkinter. No account, server or spreadsheet application is required.

[First launch](#first-launch) · [Courses](#courses) · [CAS & clubs](#cas-and-clubs) · [Dates](#dates-and-preview) · [Exceptions](#exceptions) · [Export](#export-and-replace-a-file) · [Recovery](#reload-and-recover)

## Open the window

From the project folder, run:

```sh
python -m bcalendar-utils --gui
```

On macOS use `python3`. On Windows you can also double-click `bcutils-gui.pyw` if `.pyw` files are associated with Python. If double-clicking does nothing, launch from the terminal to see the error.

If Python reports that `tkinter` is missing, use a Python installation with Tk support. You can continue with the [terminal setup](setup.md#review-and-select-a-timetable) without Tkinter.

## First launch

When no valid semester is selected, the **Start with your semester** screen appears:

1. Click **New timetable**. A fresh checkout has no installed semester.
2. Enter an ID, display name, block keys, weekday patterns and school clock. Keep **Start blank**, or deliberately choose an optional example.
3. Click **Create draft**, add your class intervals and CAS/club slots, then **Save timetable**. Use **Timing choices** for alternative durations.
4. Close the editor, review the completed definition, then click **Use this timetable**.

This creates missing blank profile files and preserves existing names. Invalid/incomplete definitions cannot be selected. **Edit timetable** reopens an existing draft. [Timetable editor guide](timetables.md).

In the main window, **Timetable → Edit this timetable** opens the school editor; **Timetable → New timetable** creates another definition. **Apply row** updates the in-memory draft; **Save timetable** validates and commits it. **Reload** discards unsaved edits after confirmation. Closing an unsaved editor offers to discard it. School saves refresh the current definition and require a fresh preview.

The main window has four tabs: **01 Courses**, **02 Dates & preview**, **03 Exceptions**, and **04 CAS & clubs**. **Save selections** and **Export .ics** are in the bottom action bar and remain available across tabs.

## Courses

In **01 Courses**, fill each block you attend:

| Field | What to enter |
| --- | --- |
| **Use** | Checked means include this named block in events. Uncheck to retain its name but leave it out. |
| **Course / study period** | The event title. A study period needs a name such as `Study Hall`. Leave unused blocks blank. |
| **Room** | Optional event location. |
| **Teacher** | Optional local reference; not included in calendar events. |
| **Timing option** | Select a duration where offered. Standard blocks have no alternative. |

Typing or changing a nonblank name checks **Use**; clearing the name unchecks it. To keep an edited name disabled, uncheck **Use** after typing. To clear a GUI field, delete its text—`-` is only a special clear instruction in terminal name prompts.

For this preset, T needs **Study hall** or **TOEFL lesson**. Wednesday T is 15:05–15:45 for either choice. Thursday T is 15:45–16:25 for study hall or 15:45–17:05 for TOEFL. The title you type does not choose the duration.

Click **Save selections** to save course and club changes. Ctrl+S also saves; Command+S is bound on macOS, though native macOS verification remains pending. Use the scrollbars if enlarged text or a longer timetable exceeds the visible area.

## CAS and clubs

Open **04 CAS & clubs**:

1. Enter a name for each club slot you attend and optionally a **Room**.
2. Keep its slot checkbox checked to enable the saved club.
3. **Include enabled, named clubs** starts checked. Uncheck it to exclude clubs from preview/export.
4. Check **Include CAS** if wanted. CAS always uses the title `CAS`.
5. Click **Save selections** for the names, then refresh the preview to apply the inclusion choices.

Named enabled clubs default on and CAS defaults off. Previously remembered inclusion choices are restored when reopening the GUI. Typing a club name enables its slot; clearing the name disables it. CAS has no editable name. With no named enabled clubs, preview/export continues with the other selections.

Slot times are displayed below the entries. In the supplied preset they are Monday CAS 15:05–16:05, Tuesday club 15:45–16:35 and Wednesday club 15:50–16:40. This tab edits names, not school times. A semester without an activity definition has no slots to name.

## Dates and preview

Open **02 Dates & preview**. GUI date fields require **`YYYY-MM-DD`**, such as `2026-09-20`; terminal shortcuts such as `0920` are not accepted here.

| Mode | How to use it |
| --- | --- |
| **Single day** | Enter **Date**. The disabled last-date field mirrors it; Weeks is disabled. |
| **First and last dates** | Enter both inclusive endpoints. Weeks is disabled. |
| **This week** | Select the current Monday–Sunday using the school clock. Set **Weeks** for consecutive weeks. |
| **Next week** | Select the next Monday–Sunday, optionally for several weeks. |
| **Choose a week** | Enter a date in the desired week, then select this mode to fill the Monday–Sunday endpoints. Set **Weeks** if needed. |

Editing a date after choosing a week preset switches the mode to **First and last dates**. Reselect **Choose a week** if you want whole-week boundaries. Single-day editing stays in **Single day** mode. Date ranges are limited to 3,660 days.

- **Late (+20 min)** shifts event start and end by 20 minutes unless a saved date rule supplies its own timing.
- **Follows normal weekdays (ignore saved exceptions)** uses the regular weekly pattern when checked. Uncheck it to apply saved school/personal rules; at least one must fall within the selected range.
- **Edit exceptions** unchecks that box and opens the exception editor. Selecting the Exceptions tab directly only opens the tab.

Click **Refresh preview**, then check titles, dates, local times and the event count. The clock shown near the top is the semester's school clock (UTC+08:00 for the supplied preset).

**Refresh preview saves pending course and club edits before computing events.** A successful refresh also remembers the GUI's dates, timing and inclusion settings. If the later date/schedule check fails, already-saved selections remain saved. To inspect without saving edits, use the terminal's `--inspect` action.

An empty preview is valid. Check enabled names, activity inclusion, date range and closures if you expected events. Terminal exports have their own normal-time/weekday defaults and do not inherit GUI preferences.

The terminal's `--export --last-inspect` reuses only a dated CLI inspection. GUI preview/export continues to use the current GUI controls and does not replace that remembered CLI snapshot.

## Exceptions

Choose **Yours** or **School** under **Save / remove in**. School rules apply to every profile; personal rules override them on the same date. Selecting a table row selects its source. **Save date** and **Remove date** affect only the selected source.

Use **03 Exceptions** to save closures, makeup days, timing changes or time filters. The table labels each row **School** or **Yours**, with time filters and notes under **Details**. Your row replaces the school's entire rule on the same date.

Enter **Date · YYYY-MM-DD**, then select an **Action**:

| Action | Function | Fields to set |
| --- | --- | --- |
| `off` | Remove all events for the selected dates, including activities. | Date, optional Through date and Note. Clear blank hours/cutoffs and select `trim`; pattern, timing and session filter are disabled. |
| `use` | Follow a different timetable pattern on the actual dates. | **Follow pattern**, **Timing**, and optional session/time filters. |
| `adjust` | Change timing on the normal weekday pattern. | **Normal** or **Late (+20 min)** timing; optional session/time filters. |
| `partial` | Keep the normal pattern and filter sessions or hours. | At least one session filter, blank window or cutoff. |

**Timing** choices:

- **Inherit** uses the export-wide Late setting where allowed.
- **Normal** replaces that setting with no shift.
- **Late (+20 min)** replaces it with a 20-minute shift; shifts are not added twice.

**Session filter** uses final start times after pattern and timing changes. **No morning** removes starts before the semester cutoff (12:30 by default); **No afternoon** removes starts at or after it. Without a matching explicit cutoff, whole sessions are kept or removed. Custom cutoffs below instead use the selected overlap behavior. Both types affect classes and included CAS/clubs.

For a Friday following Monday morning only, enter the Friday's date, select `use`, choose `monday`, leave Timing at **Inherit**, choose **No afternoon**, then click **Save date**. This saves the rule immediately and enables exception scheduling. Return to **Dates & preview** and refresh.

To edit a row, select it, change its fields, and click **Save date**. Selecting a row restores its filters and note and clears **Through date**, so editing one row affects just that date unless you enter an end date again. Saving replaces each selected date's whole personal row. Selecting a School row and saving creates a personal override; it does not edit the shared school file. **Remove my date** removes your rows for the selected date/range, which may reveal school rules underneath.

Exception-form changes require **Save date**; **Save selections** does not save them, and closing the window does not prompt for an unsaved exception form. Saved exceptions outside the export range remain available for later. Custom minute shifts entered through CSV files are preserved when loading/editing their rows. [Exception file formats](configuration.md#date-exceptions).

### Blank date ranges and hours

Optionally fill **Through date** with an inclusive `YYYY-MM-DD` end date. Leave it blank for one date. Saving or removing applies to the entire range in one save, limited to 3,660 days. Use `off` to blank dates; use `partial` for time filters, or combine them with `use`/`adjust`.

| Control | Meaning |
| --- | --- |
| **Blank hours** | A window such as `10:00-11:00`, or comma-separated windows such as `10:00-11:00,14:00-14:30`. |
| **Morning cutoff** | Blank times before this `HH:MM` boundary. |
| **Afternoon cutoff** | Blank times from this `HH:MM` boundary onward. |
| **Overlapping sessions** | `trim` (default) shortens or splits sessions; `remove` drops any session overlapping a blank window. |

For a 09:00–12:00 session with 10:00–11:00 blanked, `trim` produces 09:00–10:00 and 11:00–12:00; `remove` drops the whole session. A session merely touching a window boundary remains unchanged. Both cutoffs can combine: 09:30 and 15:00 keep only time between those boundaries when trimming. The morning cutoff cannot be later than the afternoon cutoff. `24:00` is allowed as an end-of-day boundary.

Times refer to the school clock after pattern changes, duration choices and timing shifts. Click **Save date**, then refresh **Dates & preview** to review the result. [Exception file formats](configuration.md#date-exceptions).

## Export and replace a file

1. Check dates, timing, exceptions and activity inclusion in the preview.
2. Click **Export .ics** in the bottom action bar.
3. Choose a destination and an `.ics` filename in the save dialog.
4. Save, then check the success message at the bottom of the window.

Export refreshes the preview first, so it also saves course/club changes and remembers successful preview settings before the save dialog opens. Cancelling that dialog cancels the calendar write; it does **not** undo saved selections or preferences. Empty calendars cannot be exported.

The suggested filename includes the profile, semester and inclusive endpoints. Changing names or rules for the same dates gives the same suggested filename. To keep a previous export, enter another name. To replace it, accept the native save dialog's replacement confirmation. There is no separate GUI overwrite checkbox; `--overwrite` belongs to terminal commands. Replacing an export does not create a backup or merge calendars.

Import the resulting file through your calendar app's import flow. Exports are snapshots rather than subscriptions; see [import and reimport limitations](setup.md#import-the-calendar).

## Switch profiles or semesters

At the top of the main window, select **SEMESTER**, enter **PROFILE**, and click **Switch / create**. Editing those controls alone does not change the active data.

A new profile gets separate blank selections. When course/club edits are pending, the window asks whether to save, discard or cancel the switch. A completed switch remembers the new profile/semester and resets inclusion to **clubs on, CAS off**. Recheck dates and inclusion choices, then refresh the preview.

Profile names follow the [name and path rules](configuration.md#profiles-and-files). Preserve each profile's `profile.json` when copying data to another machine so event IDs remain stable.

## Reload and recover

**Reload CSV** on Courses reloads courses, clubs and saved exceptions. It asks before discarding pending course/club edits. It does not save an unfinished exception form. Use it after a terminal command or external CSV editor changes the same profile.

The app refuses a stale save if a file changed after loading. Record any edits you want to keep, reload the latest files, then reenter them. Avoid editing the same profile in multiple interfaces at once. Close and reopen the GUI after changing semester definitions; Reload CSV refreshes student data, not the school timetable.

| Message or symptom | Next step |
| --- | --- |
| T has no timing choice | Choose **Study hall** or **TOEFL lesson** on Courses, then save. |
| No exceptions in the selected range | Check **Follows normal weekdays**, or save a date rule inside the range. |
| A weekend has no normal pattern to adjust | Use `use` with a defined weekday pattern for the makeup day. |
| Expected club is missing | Name and enable its slot, check **Include enabled, named clubs**, and review exceptions for its date/time. |
| Profile/semester must be applied | Click **Switch / create**, then refresh. |
| Saved file changed externally | Reload CSV and reenter the intended edits. |
| Timetable definition is invalid | Follow [configuration guidance](configuration.md#a-new-semester), then reopen the GUI. |

Closing the window asks about pending course/club changes. Previously saved date rules remain saved. For recovery from an earlier file version, see [backups and profile files](configuration.md#profiles-and-files).
