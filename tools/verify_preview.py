"""Render real CLI output in one temporary monospace window for visual QA."""

import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.cli import main
from shbs_calendar.models import Course
from shbs_calendar.storage import digest


def capture():
    import tkinter as tk
    from PIL import ImageGrab
    with tempfile.TemporaryDirectory(prefix="shbs-preview-") as tmp:
        workspace = Workspace(Path(tmp))
        shutil.copytree(DEFAULT_ROOT / "semesters", workspace.root / "semesters")
        ctx = workspace.use_semester("2026-27-s1")
        names = ["Chemistry", "Study Hall", "Advanced Mathematics", "World History", "Physics", "Music Theory", "English Language", "Physical Education", "Study Hall", "Creative Writing"]
        ctx.save_courses([Course(b, name, enabled=True, timing_option="study_hall" if b == "T" else "") for b, name in zip(ctx.semester.blocks, names)], digest(ctx.courses_path))
        output = io.StringIO()
        with redirect_stdout(output):
            assert main(["--root", str(workspace.root), "preview", "--week", "2026-09-14", "--width", "100"]) == 0
        path = DEFAULT_ROOT / "local/qa/terminal-preview.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        root = tk.Tk()
        root.title("Calendar preview · synthetic data")
        text = tk.Text(root, font=("Consolas", 11), width=103, height=29, bg="#101414", fg="#e0e8e3", padx=18, pady=18, wrap="none")
        text.pack(fill="both", expand=True)
        text.insert("1.0", output.getvalue())
        text.configure(state="disabled")
        def screenshot():
            try:
                root.update_idletasks()
                if sys.platform == "win32":
                    image = ImageGrab.grab(window=int(root.frame(), 16))
                else:
                    x, y = root.winfo_rootx(), root.winfo_rooty()
                    image = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()))
                image.save(path)
                print(path)
            finally:
                root.destroy()
        root.after(400, screenshot)
        root.mainloop()


if __name__ == "__main__":
    capture()
