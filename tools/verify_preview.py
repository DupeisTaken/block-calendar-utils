"""Render real CLI output in one temporary monospace window for visual QA."""

import argparse
import io
import os
import re
import shutil
import sys
import tempfile
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shbs_calendar.app import DEFAULT_ROOT, Workspace
from shbs_calendar.cli import main
from shbs_calendar.models import Course
from shbs_calendar.storage import digest


def capture(syntax=False, entry=False, help_page=None, workflow=False):
    import tkinter as tk
    from PIL import ImageGrab
    with tempfile.TemporaryDirectory(prefix="shbs-preview-") as tmp:
        workspace = Workspace(Path(tmp))
        shutil.copytree(DEFAULT_ROOT / "semesters", workspace.root / "semesters")
        ctx = workspace.use_semester("2026-27-s1")
        names = ["Chemistry", "Study Hall", "Advanced Mathematics", "World History", "Physics", "Music Theory", "English Language", "Physical Education", "Study Hall", "Creative Writing"]
        ctx.save_courses([Course(b, name, enabled=True, timing_option="study_hall" if b == "T" else "") for b, name in zip(ctx.semester.blocks, names)], digest(ctx.courses_path))
        output = io.StringIO()
        # Render every interaction as an ANSI-capable terminal without changing
        # the user's console mode or environment outside this capture.
        with redirect_stdout(output), patch.object(output, "isatty", return_value=True), patch.dict(os.environ, {}, clear=True), patch("shbs_calendar.help_style.windows_vt", side_effect=lambda _: nullcontext(True)):
            if workflow:
                # Exercise the real sequence and recovery using only this
                # temporary profile. Each screenshot owns one short-lived window.
                flags = ["-r", str(workspace.root)]
                print('python -m shbs-calendar -i --day 2026-09-18 --late -e -l\n')
                assert main(flags + ["-i", "--day", "2026-09-18", "--late", "-e", "-l"]) == 0
                print('\npython -m shbs-calendar -e --last-inspect\n')
                with redirect_stderr(output):
                    assert main(flags + ["-e", "--last-inspect"]) == 2
                print('\npython -m shbs-calendar -e -l --overwrite\n')
                assert main(flags + ["-e", "-l", "--overwrite"]) == 0
            elif help_page:
                # Emulate an ANSI-capable terminal, then render the exact output
                # below with Tk tags. No native console or user data is changed.
                with patch.object(output, "isatty", return_value=True), patch.dict(os.environ, {}, clear=True), patch("shbs_calendar.help_style.windows_vt", side_effect=lambda _: nullcontext(True)):
                    try:
                        route = ["--write", "--exceptions"] if help_page == "exceptions" else ["--" + help_page] if help_page != "overview" else []
                        main(route + ["-h"])
                    except SystemExit as exc:
                        assert exc.code == 0
            elif entry:
                print("python -m shbs-calendar -h\n")
                try:
                    main(["-h"])
                except SystemExit as exc:
                    assert exc.code == 0
                print("\npython -m shbs-calendar -w --activities\n")
                names = iter(["Chess Club", "Robotics Club"])
                def answer(prompt):
                    value = next(names)
                    print(prompt + value)
                    return value
                with patch("builtins.input", side_effect=answer):
                    assert main(["-r", str(workspace.root), "-w", "--activities"]) == 0
            elif syntax:
                print("python -m shbs-calendar -i -d 20260917-20260918 --exception 2026.9.18 Mon\n")
                assert main(["-r", str(workspace.root), "-i", "-d", "20260917-20260918", "--exception", "2026.9.18", "Mon", "--width", "100"]) == 0
                print("\npython -m shbs-calendar -e -d 2026.2.30\n")
                with redirect_stderr(output):
                    assert main(["-r", str(workspace.root), "-e", "-d", "2026.2.30"]) == 2
            else:
                assert main(["--root", str(workspace.root), "--inspect", "--week", "2026-09-14", "--width", "100"]) == 0
        path = DEFAULT_ROOT / "local/qa" / ("terminal-workflow.png" if workflow else f"help-{help_page}.png" if help_page else "terminal-entry.png" if entry else "terminal-syntax.png" if syntax else "terminal-preview.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        root = tk.Tk()
        root.title("Calendar preview · synthetic data")
        height = min(45, len(output.getvalue().splitlines()) + 2)
        text = tk.Text(root, font=("Consolas", 11), width=103, height=height, bg="#101414", fg="#e0e8e3", padx=18, pady=18, wrap="word" if syntax or entry or workflow else "none")
        text.pack(fill="both", expand=True)
        text.tag_configure("1", font=("Consolas", 11, "bold"))
        text.tag_configure("36", foreground="#5fa9a5")
        chunks = re.split(r"\x1b\[([0-9]+)m", output.getvalue())
        text.insert("end", chunks[0])
        for code, chunk in zip(chunks[1::2], chunks[2::2]):
            text.insert("end", chunk, (code,))
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
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--syntax", action="store_true", help="Capture short commands, flexible dates and a syntax error")
    mode.add_argument("--entry", action="store_true", help="Capture compact help and interactive club-name entry")
    mode.add_argument("--workflow", action="store_true", help="Capture stacked write/export and overwrite recovery")
    mode.add_argument("--help-page", choices=["overview", "activities", "export", "exceptions"], help="Capture subtly colored help")
    args = parser.parse_args()
    capture(args.syntax, args.entry, args.help_page, args.workflow)
