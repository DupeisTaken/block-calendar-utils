"""Developer-only screenshot smoke test. Requires Pillow, never used by the app.

Uses one application-owned Tk window and temporary synthetic data. Captures its
client area, then destroys the window and cleans the temporary workspace.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bcutils.app import DEFAULT_ROOT, Workspace
from bcutils.gui import CalendarApp, SemesterSetup


def main():
    import tkinter as tk
    from PIL import ImageGrab

    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1.333)
    parser.add_argument("--setup", action="store_true", help="Capture the semester review screen")
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT / "local/qa")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bcutils-visual-") as tmp:
        root_path = Path(tmp)
        shutil.copytree(DEFAULT_ROOT / "semesters", root_path / "semesters")
        root = tk.Tk()
        root.tk.call("tk", "scaling", args.scale)
        workspace = Workspace(root_path)
        if args.setup:
            setup = SemesterSetup(root, workspace)
            setup.semester_var.set("2026-27-s1")
            setup.review()
            def capture_setup():
                try:
                    root.update_idletasks()
                    button = setup.use_button
                    assert button.winfo_rooty() + button.winfo_height() <= root.winfo_rooty() + root.winfo_height(), "Semester activation button clipped"
                    if sys.platform == "win32":
                        image = ImageGrab.grab(window=int(root.frame(), 16))
                    else:
                        x, y = root.winfo_rootx(), root.winfo_rooty()
                        image = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()))
                    path = args.output / f"setup-{args.scale}.png"
                    image.save(path)
                    print(path)
                finally:
                    root.destroy()
            root.after(500, capture_setup)
            root.mainloop()
            return
        workspace.use_semester("2026-27-s1")
        app = CalendarApp(root, workspace)
        names = ["Chemistry", "Study Hall", "Advanced Mathematics", "World History", "Physics", "Music Theory", "English Language", "Physical Education", "TOEFL Study Hall", "Creative Writing"]
        for (block, fields), name in zip(app.course_vars, names):
            fields["course"].set(name)
            if block == "T":
                fields["timing_option"].set("Study hall")
        app.activity_vars["club-tue"][0].set("Chess Club")
        app.activity_vars["club-wed"][0].set("Robotics Club")
        app.mode_var.set("Choose a week")
        app.anchor_var.set("2026-09-14")
        app.update_date_fields()
        app.exc_date.set("2026-09-18")
        app.exc_pattern.set("monday")
        app.exc_note.set("Friday follows Monday's classes")
        app.exc_blank.set("10:00-11:00")
        app.exc_morning.set("09:00")
        app.exc_afternoon.set("16:00")
        app.save_exception()
        app.save()
        root.geometry("1120x800+30+30")
        root.lift()

        def capture(name):
            root.update_idletasks()
            button = app.export_button
            assert button.winfo_rooty() + button.winfo_height() <= root.winfo_rooty() + root.winfo_height(), "Export button clipped"
            if sys.platform == "win32":
                # Capture only our window even when another app occludes it.
                image = ImageGrab.grab(window=int(root.frame(), 16))
            else:
                x, y = root.winfo_rootx(), root.winfo_rooty()
                image = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()))
            path = args.output / f"{name}-{args.scale}.png"
            image.save(path)
            print(path)
            if name == "exceptions":
                button = app.save_date_button
                assert button.winfo_rooty() + button.winfo_height() <= app.exceptions_tab.winfo_rooty() + app.exceptions_tab.winfo_height(), "Exception save button clipped"
                bbox = app.exception_tree.bbox(app.exception_tree.get_children()[0])
                assert bbox and bbox[1] + bbox[3] <= app.exception_tree.winfo_height(), "First exception row clipped"

        failures = []

        def step(number=0):
            try:
                if number == 0:
                    capture("courses")
                    app.preview()
                elif number == 1:
                    capture("preview")
                    app.tabs.select(app.exceptions_tab)
                elif number == 2:
                    capture("exceptions")
                    app.cas_var.set(True)
                    app.clubs_var.set(True)
                    app.tabs.select(app.activities_tab)
                elif number == 3:
                    capture("activities")
                    app.mode_var.set("Single day")
                    app.anchor_var.set("2026-09-17")
                    app.weekdays_var.set(True)
                    app.update_date_fields()
                    app.preview()
                else:
                    capture("single-day")
                    root.destroy()
                    return
                root.after(400, lambda: step(number + 1))
            except Exception as exc:
                # Tk otherwise prints callback failures but exits successfully.
                failures.append(exc)
                root.destroy()

        root.after(500, step)
        try:
            root.mainloop()
            if failures:
                raise failures[0]
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass


if __name__ == "__main__":
    main()
