"""One lightweight Tk window. All file/date/export rules live in shared services."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from .app import DEFAULT_ROOT, Workspace
from .models import CalendarError, Course, DayOverride
from .schedule import preview_text
from .storage import digest, parse_date

BG, INK, MUTED, ACCENT = "#f4f5f1", "#1b302d", "#626e69", "#24695b"
MODES = {"First and last dates": "custom", "This week": "this", "Next week": "next", "Choose a week": "week"}


def option_label(option):
    return {"study_hall": "Study hall", "toefl": "TOEFL lesson"}.get(option, option.replace("_", " ").title())


class CalendarApp:
    def __init__(self, root, workspace):
        self.root, self.workspace = root, workspace
        self.settings = workspace.settings()
        self.ctx = workspace.context(self.settings["profile"], self.settings["semester"], create=True)
        self.baseline, self.course_vars = [], []
        self.course_digest = None
        root.title("SHBS Calendar")
        root.geometry("1120x800")
        root.minsize(980, 700)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._style()
        self._layout()
        self.load_courses()
        self.refresh_exceptions()
        self.update_date_fields()
        root.bind("<Control-s>", lambda _: self.run(self.save))
        root.bind("<Command-s>", lambda _: self.run(self.save))

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        font = "Helvetica" if self.root.tk.call("tk", "windowingsystem") == "aqua" else "Segoe UI"
        self.font = font
        style.configure(".", font=(font, 10), background=BG, foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=(font, 25, "bold"))
        style.configure("Section.TLabel", font=(font, 14, "bold"))
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground="white", borderwidth=0, padding=(18, 9))
        style.map("Accent.TButton", background=[("active", "#1d554a"), ("disabled", "#8faba3")])
        style.configure("TEntry", padding=5, fieldbackground="white")
        style.configure("TCombobox", padding=5, fieldbackground="white")
        style.configure("TNotebook", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(20, 10))
        style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", ACCENT)])
        style.configure("Treeview", rowheight=30, fieldbackground="white", background="white", borderwidth=0)
        style.configure("Treeview.Heading", padding=8, font=(font, 10, "bold"))

    def _layout(self):
        header = ttk.Frame(self.root, padding=(28, 18, 28, 10))
        header.pack(fill="x")
        ttk.Label(header, text="SHBS Calendar", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Your classes. Your week.", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        context = ttk.Frame(self.root, padding=(28, 0, 28, 10))
        context.pack(fill="x")
        ttk.Label(context, text="SEMESTER", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.semester_var = tk.StringVar(value=self.ctx.semester.id)
        ttk.Combobox(context, textvariable=self.semester_var, values=self.workspace.semesters(), state="readonly", width=18).pack(side="left")
        ttk.Label(context, text="PROFILE", style="Muted.TLabel").pack(side="left", padx=(24, 8))
        self.profile_var = tk.StringVar(value=self.ctx.profile)
        ttk.Entry(context, textvariable=self.profile_var, width=16).pack(side="left")
        ttk.Button(context, text="Switch / create", command=lambda: self.run(self.switch)).pack(side="left", padx=8)
        self.clock_label = ttk.Label(context, text=str(self.ctx.semester.clock), style="Muted.TLabel")
        self.clock_label.pack(side="right")
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=28)
        self.courses_tab, self.preview_tab, self.exceptions_tab = [ttk.Frame(self.tabs, padding=18) for _ in range(3)]
        self.tabs.add(self.courses_tab, text="01  Courses")
        self.tabs.add(self.preview_tab, text="02  Dates & preview")
        self.tabs.add(self.exceptions_tab, text="03  Exceptions")
        self._courses_layout()
        self._preview_layout()
        self._exceptions_layout()
        footer = ttk.Frame(self.root, padding=(28, 16))
        # Reserve the action bar before the expandable notebook. Otherwise Tk
        # can allocate all height to notebook content at enlarged font scales.
        footer.pack(side="bottom", fill="x", before=self.tabs)
        self.status = tk.StringVar(value="Choose your classes, then preview a week.")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=590).pack(side="left")
        self.export_button = ttk.Button(footer, text="Export .ics", style="Accent.TButton", command=lambda: self.run(self.export))
        self.export_button.pack(side="right")
        ttk.Button(footer, text="Save courses", command=lambda: self.run(self.save)).pack(side="right", padx=10)

    def _courses_layout(self):
        bar = ttk.Frame(self.courses_tab)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Make this timetable yours", style="Section.TLabel").pack(side="left")
        ttk.Button(bar, text="Reload CSV", command=lambda: self.run(self.reload)).pack(side="right")
        ttk.Label(self.courses_tab, text="Name each selected block. Leave unused blocks blank. Include study periods by giving them a name.", style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
        # Scrolling keeps larger font/display scales and future block lists usable.
        holder = ttk.Frame(self.courses_tab)
        holder.pack(fill="both", expand=True)
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        self.course_canvas = tk.Canvas(holder, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.course_canvas.yview)
        horizontal = ttk.Scrollbar(holder, orient="horizontal", command=self.course_canvas.xview)
        self.course_canvas.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        scroll.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.course_canvas.grid(row=0, column=0, sticky="nsew")
        self.course_grid = ttk.Frame(self.course_canvas)
        window = self.course_canvas.create_window((0, 0), window=self.course_grid, anchor="nw")
        self.course_grid.bind("<Configure>", lambda _: self.course_canvas.configure(scrollregion=self.course_canvas.bbox("all")))
        self.course_canvas.bind("<Configure>", lambda event: self.course_canvas.itemconfigure(window, width=max(event.width, self.course_grid.winfo_reqwidth())))
        self.course_grid.bind("<MouseWheel>", lambda event: self.course_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
        self.path_label = ttk.Label(self.courses_tab, text="", style="Muted.TLabel", wraplength=950)
        self.path_label.pack(anchor="w", pady=(12, 0))

    def _preview_layout(self):
        row = ttk.Frame(self.preview_tab)
        row.pack(fill="x")
        self.mode_var = tk.StringVar(value=next((label for label, key in MODES.items() if key == self.settings["mode"]), "This week"))
        self.anchor_var = tk.StringVar(value=self.settings.get("anchor", ""))
        self.end_var = tk.StringVar(value=self.settings.get("end", ""))
        self.weeks_var = tk.StringVar(value=str(self.settings.get("weeks", 1)))
        self.late_var = tk.BooleanVar(value=self.settings.get("late", False))
        first, last = self.ctx.dates(self.settings)
        saved_mode = self.settings.get("schedule_mode", "saved")
        self.weekdays_var = tk.BooleanVar(value=saved_mode == "weekdays" or (saved_mode == "saved" and not self.ctx.overrides_in_range(first, last)))
        mode = ttk.Combobox(row, textvariable=self.mode_var, values=list(MODES), state="readonly", width=20)
        mode.pack(side="left")
        mode.bind("<<ComboboxSelected>>", lambda _: self.run(self.update_date_fields))
        ttk.Label(row, text="Weeks").pack(side="left", padx=(12, 6))
        self.weeks_entry = ttk.Spinbox(row, from_=1, to=520, textvariable=self.weeks_var, width=4, command=lambda: self.run(self.update_date_fields))
        self.weeks_entry.bind("<Return>", lambda _: self.run(self.update_date_fields))
        self.weeks_entry.pack(side="left")
        ttk.Checkbutton(row, text="Late (+20 min)", variable=self.late_var).pack(side="left", padx=16)
        ttk.Button(row, text="Refresh preview", command=lambda: self.run(self.preview)).pack(side="right")
        dates = ttk.Frame(self.preview_tab)
        dates.pack(fill="x", pady=12)
        ttk.Label(dates, text="First date").pack(side="left")
        self.anchor_entry = ttk.Entry(dates, textvariable=self.anchor_var, width=13)
        self.anchor_entry.pack(side="left", padx=8)
        ttk.Label(dates, text="Last date (included)").pack(side="left", padx=(12, 0))
        self.end_entry = ttk.Entry(dates, textvariable=self.end_var, width=13)
        self.end_entry.pack(side="left", padx=8)
        ttk.Label(dates, text="YYYY-MM-DD", style="Muted.TLabel").pack(side="left", padx=8)
        for entry in (self.anchor_entry, self.end_entry):
            entry.bind("<KeyRelease>", lambda _: self.mark_custom_dates())
            entry.bind("<<Paste>>", lambda _: self.root.after_idle(self.mark_custom_dates))
            entry.bind("<<Cut>>", lambda _: self.root.after_idle(self.mark_custom_dates))
        schedule_row = ttk.Frame(self.preview_tab)
        schedule_row.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(schedule_row, text="Follows normal weekdays (ignore saved exceptions)", variable=self.weekdays_var, command=self.schedule_changed).pack(side="left")
        ttk.Button(schedule_row, text="Edit exceptions", command=self.open_exceptions).pack(side="right")
        text_frame = ttk.Frame(self.preview_tab)
        text_frame.pack(fill="both", expand=True)
        self.preview_widget = tk.Text(text_frame, wrap="word", font=(self.font, 11), bg="white", fg=INK, relief="flat", padx=18, pady=14, height=10)
        scroll = ttk.Scrollbar(text_frame, command=self.preview_widget.yview)
        self.preview_widget.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.preview_widget.pack(fill="both", expand=True)
        self.set_preview_text("Choose a range above, then refresh the preview.\n\nOnly enabled courses and study periods are included.")

    def _exceptions_layout(self):
        ttk.Label(self.exceptions_tab, text="When a school day is different", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self.exceptions_tab, text="Use another weekday, skip a date, or change its timing. Your saved date replaces a school exception.", style="Muted.TLabel", wraplength=970).pack(anchor="w", pady=(5, 12))
        columns = ("date", "action", "pattern", "shift", "note", "source")
        self.exception_holder = ttk.Frame(self.exceptions_tab)
        self.exception_holder.pack(fill="both", expand=True)
        self.exception_tree = ttk.Treeview(self.exception_holder, columns=columns, show="headings", height=4)
        for column, width in zip(columns, [110, 70, 110, 80, 330, 80]):
            self.exception_tree.heading(column, text=column.title())
            self.exception_tree.column(column, width=width, minwidth=55, stretch=column == "note")
        scroll = ttk.Scrollbar(self.exception_holder, command=self.exception_tree.yview)
        self.exception_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.exception_tree.pack(side="left", fill="both", expand=True)
        self.exception_tree.bind("<<TreeviewSelect>>", lambda _: self.select_exception())
        form = ttk.Frame(self.exceptions_tab)
        form.pack(fill="x", pady=(16, 8))
        self.exc_date = tk.StringVar()
        self.exc_action = tk.StringVar(value="use")
        self.exc_pattern = tk.StringVar(value="monday")
        self.exc_shift = tk.StringVar(value="Inherit")
        self.exc_note = tk.StringVar()
        for col, label in enumerate(["Date · YYYY-MM-DD", "Action", "Follow pattern", "Timing"]):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 12), pady=(0, 5))
        ttk.Entry(form, textvariable=self.exc_date, width=17).grid(row=1, column=0, sticky="ew", padx=(0, 12))
        action = ttk.Combobox(form, textvariable=self.exc_action, values=["off", "use", "adjust"], state="readonly", width=12)
        action.grid(row=1, column=1, padx=(0, 12))
        action.bind("<<ComboboxSelected>>", lambda _: self.update_exception_fields())
        self.exc_pattern_box = ttk.Combobox(form, textvariable=self.exc_pattern, values=self.ctx.semester.patterns, state="readonly", width=17)
        self.exc_pattern_box.grid(row=1, column=2, padx=(0, 12))
        self.exc_shift_box = ttk.Combobox(form, textvariable=self.exc_shift, values=["Inherit", "Normal", "Late (+20 min)"], state="readonly", width=18)
        self.exc_shift_box.grid(row=1, column=3)
        hint = ttk.Label(self.exceptions_tab, text="off = no classes     use = another pattern     adjust = same day, different timing", style="Muted.TLabel", wraplength=970)
        hint.pack(anchor="w", pady=(2, 10))
        row = ttk.Frame(self.exceptions_tab)
        row.pack(fill="x")
        ttk.Label(row, text="Note").pack(side="left", padx=(0, 8))
        ttk.Entry(row, textvariable=self.exc_note).pack(side="left", fill="x", expand=True)
        self.save_date_button = ttk.Button(row, text="Save date", command=lambda: self.run(self.save_exception))
        self.save_date_button.pack(side="left", padx=8)
        ttk.Button(row, text="Remove my date", command=lambda: self.run(self.remove_exception)).pack(side="left")
        # Reserve the editor before giving remaining height to the date list.
        row.pack_configure(side="bottom", before=self.exception_holder)
        hint.pack_configure(side="bottom", before=self.exception_holder)
        form.pack_configure(side="bottom", before=self.exception_holder)

    def run(self, callback):
        try:
            return callback()
        except (CalendarError, OSError, ValueError) as exc:
            messagebox.showerror("Please check", str(exc), parent=self.root)
            self.status.set("Please correct the reported issue and try again.")
            return None

    def read_course_form(self):
        courses = []
        for block, fields in self.course_vars:
            labels = {option_label(key): key for key in self.ctx.semester.timing_options.get(block, {})}
            option = fields["timing_option"].get()
            courses.append(Course(block, fields["course"].get().strip(), fields["location"].get().strip(), fields["teacher"].get().strip(), fields["enabled"].get(), labels.get(option, option)))
        return courses

    def dirty(self):
        return self.read_course_form() != self.baseline

    def load_courses(self):
        courses = self.ctx.courses()
        self.course_digest = digest(self.ctx.courses_path)
        self.baseline = courses
        for child in self.course_grid.winfo_children():
            child.destroy()
        for col, label in enumerate(["Use", "Block", "Course / study period", "Room", "Teacher", "Timing option"]):
            ttk.Label(self.course_grid, text=label, style="Muted.TLabel").grid(row=0, column=col, sticky="w", padx=5, pady=(0, 10))
        self.course_grid.columnconfigure(2, weight=3)
        self.course_grid.columnconfigure(4, weight=1)
        self.course_vars = []
        for row, course in enumerate(courses, 1):
            fields = {key: tk.StringVar(value=getattr(course, key)) for key in ("course", "location", "teacher", "timing_option")}
            fields["timing_option"].set(option_label(course.timing_option))
            fields["enabled"] = tk.BooleanVar(value=course.enabled)
            ttk.Checkbutton(self.course_grid, variable=fields["enabled"]).grid(row=row, column=0, padx=5, pady=3)
            ttk.Label(self.course_grid, text=course.block, font=(self.font, 11, "bold")).grid(row=row, column=1, sticky="w", padx=5)
            for col, key, width in [(2, "course", 28), (3, "location", 8), (4, "teacher", 12)]:
                entry = ttk.Entry(self.course_grid, textvariable=fields[key], width=width)
                entry.grid(row=row, column=col, sticky="ew", padx=5, pady=3)
                # Keyboard focus scrolls a row into view, including at high DPI.
                entry.bind("<FocusIn>", lambda event: self.show_course_field(event.widget))
            choices = list(self.ctx.semester.timing_options.get(course.block, {}))
            if choices:
                ttk.Combobox(self.course_grid, textvariable=fields["timing_option"], values=[option_label(c) for c in choices], state="readonly", width=13).grid(row=row, column=5, padx=5)
            else:
                ttk.Label(self.course_grid, text="Standard", style="Muted.TLabel").grid(row=row, column=5, padx=5, sticky="w")
            # Typing a name enables a previously blank block, with a checkbox
            # available to keep a named course saved but excluded.
            def name_changed(*_, values=fields):
                if values["course"].get().strip():
                    values["enabled"].set(True)
                else:
                    values["enabled"].set(False)
            fields["course"].trace_add("write", name_changed)
            self.course_vars.append((course.block, fields))
        self.path_label.configure(text=f"Saved locally · {self.ctx.courses_path}")

    def save(self):
        if self.dirty():
            self.ctx.save_courses(self.read_course_form(), self.course_digest)
        self.load_courses()
        self.status.set("Courses saved. Your CSV is ready for the next export.")

    def show_course_field(self, widget):
        self.root.update_idletasks()
        full_height = self.course_grid.winfo_height()
        top = self.course_canvas.canvasy(0)
        bottom = top + self.course_canvas.winfo_height()
        if widget.winfo_y() < top or widget.winfo_y() + widget.winfo_height() > bottom:
            self.course_canvas.yview_moveto(max(0, widget.winfo_y() - 10) / max(1, full_height))

    def reload(self):
        if self.dirty() and not messagebox.askyesno("Reload CSV", "Discard unsaved course edits and reload the CSV?", parent=self.root):
            return
        self.load_courses()
        self.refresh_exceptions()
        self.clock_label.configure(text=str(self.ctx.semester.clock))
        self.status.set("Reloaded the latest files.")

    def keep_edits(self):
        if not self.dirty():
            return True
        answer = messagebox.askyesnocancel("Unsaved courses", "Save your course edits before continuing?", parent=self.root)
        if answer is None:
            return False
        if answer:
            self.save()
        return True

    def switch(self):
        try:
            if not self.keep_edits():
                return
            candidate = self.workspace.context(self.profile_var.get(), self.semester_var.get(), create=True)
            candidate.courses()
            self.ctx = candidate
            self.settings.update(profile=self.ctx.profile, semester=self.ctx.semester.id)
            self.workspace.save_settings(self.settings)
            self.load_courses()
            self.refresh_exceptions()
            self.exc_pattern_box.configure(values=self.ctx.semester.patterns)
            self.exc_pattern.set(self.ctx.semester.patterns[0])
            self.set_preview_text("Profile changed. Refresh the preview to see this timetable.")
            self.status.set(f"Using {self.ctx.profile} · {self.ctx.semester.name}")
        finally:
            # A failed/cancelled switch must not label the old data as a new user.
            self.profile_var.set(self.ctx.profile)
            self.semester_var.set(self.ctx.semester.id)
            self.clock_label.configure(text=str(self.ctx.semester.clock))

    def update_date_fields(self):
        mode = MODES[self.mode_var.get()]
        self.weeks_entry.configure(state="disabled" if mode == "custom" else "normal")
        # Presets fill both endpoints. Editing either date turns the range into
        # an explicit range, so visible values always match the exported dates.
        if mode != "custom":
            first, last = self.ctx.dates(self.range_settings())
            self.anchor_var.set(str(first))
            self.end_var.set(str(last))
        self.displayed_dates = (self.anchor_var.get(), self.end_var.get())

    def mark_custom_dates(self):
        if (self.anchor_var.get(), self.end_var.get()) != self.displayed_dates:
            self.mode_var.set("First and last dates")
            self.weeks_entry.configure(state="disabled")

    def schedule_changed(self):
        if not self.weekdays_var.get():
            self.open_exceptions()

    def open_exceptions(self):
        self.weekdays_var.set(False)
        self.refresh_exceptions()
        self.tabs.select(self.exceptions_tab)
        self.status.set("Add or review exceptions within the first and last dates, then return to Dates & preview.")

    def range_settings(self):
        return dict(self.settings, mode=MODES[self.mode_var.get()], anchor=self.anchor_var.get().strip(), end=self.end_var.get().strip(), weeks=1 if MODES[self.mode_var.get()] == "custom" else int(self.weeks_var.get()), late=self.late_var.get(), schedule_mode="weekdays" if self.weekdays_var.get() else "exceptions")

    def set_preview_text(self, text):
        self.preview_widget.configure(state="normal")
        self.preview_widget.delete("1.0", "end")
        self.preview_widget.insert("1.0", text)
        self.preview_widget.configure(state="disabled")

    def preview(self):
        if self.profile_var.get() != self.ctx.profile or self.semester_var.get() != self.ctx.semester.id:
            raise CalendarError("Click Switch / create to apply the profile or semester before previewing/exporting.")
        if MODES[self.mode_var.get()] != "custom":
            self.update_date_fields()
        self.save()
        settings = self.range_settings()
        preview = self.ctx.preview(settings)
        self.settings = settings
        self.workspace.save_settings(settings)
        self.set_preview_text(preview_text(preview))
        self.tabs.select(self.preview_tab)
        self.status.set(f"{len(preview.events)} events · {preview.start} to {preview.end} · {preview.clock}")
        return preview

    def export(self):
        preview = self.preview()
        initial = f"{self.ctx.profile}-{self.ctx.semester.id}-{preview.start}-{preview.end}.ics"
        output = filedialog.asksaveasfilename(parent=self.root, title="Export school calendar", initialdir=self.workspace.root / "exports", initialfile=initial, defaultextension=".ics", filetypes=[("iCalendar", "*.ics")])
        if not output:
            self.status.set("Export cancelled. Your courses are saved.")
            return
        # The native Save dialog confirms replacements; no second modal needed.
        self.ctx.export(preview, Path(output), overwrite=True)
        self.status.set(f"Exported {len(preview.events)} events · {Path(output).name}")

    def update_exception_fields(self):
        kind = self.exc_action.get()
        self.exc_pattern_box.configure(state="readonly" if kind == "use" else "disabled")
        self.exc_shift_box.configure(state="disabled" if kind == "off" else "readonly")
        if kind == "adjust" and self.exc_shift.get() == "Inherit":
            self.exc_shift.set("Normal")

    def refresh_exceptions(self):
        from .storage import load_overrides
        self.exception_digest = digest(self.ctx.exceptions_path)
        self.exception_items = self.ctx.exceptions()
        school = load_overrides(self.ctx.folder / "exceptions.csv", self.ctx.semester)
        for item in self.exception_tree.get_children():
            self.exception_tree.delete(item)
        for source, items in [("School", school), ("Yours", self.exception_items)]:
            for i in items:
                self.exception_tree.insert("", "end", values=(str(i.date), i.action, i.pattern, "Inherit" if i.time_shift_minutes is None else i.time_shift_minutes, i.note, source))

    def select_exception(self):
        selected = self.exception_tree.selection()
        if not selected:
            return
        day, action, pattern, shift, note, _ = self.exception_tree.item(selected[0], "values")
        self.exc_date.set(day)
        self.exc_action.set(action)
        self.exc_pattern.set(pattern)
        self.exc_shift.set({"0": "Normal", "20": "Late (+20 min)"}.get(str(shift), str(shift)))
        self.exc_note.set(note)
        self.update_exception_fields()

    def save_exception(self):
        day, action = parse_date(self.exc_date.get().strip()), self.exc_action.get()
        shifts = {"Inherit": None, "Normal": 0, "Late (+20 min)": 20}
        text = self.exc_shift.get()
        shift = None if action == "off" else shifts[text] if text in shifts else int(text)
        item = DayOverride(day, action, self.exc_pattern.get() if action == "use" else "", shift, self.exc_note.get().strip())
        items = [i for i in self.exception_items if i.date != day] + [item]
        self.ctx.save_exceptions(items, self.exception_digest)
        self.weekdays_var.set(False)
        self.refresh_exceptions()
        self.status.set(f"Saved exception for {day}. Refresh the preview to see it.")

    def remove_exception(self):
        day = parse_date(self.exc_date.get().strip())
        self.ctx.save_exceptions([i for i in self.exception_items if i.date != day], self.exception_digest)
        self.refresh_exceptions()
        self.status.set(f"Removed your exception for {day}. School/default rules apply again.")

    def close(self):
        try:
            if self.keep_edits():
                self.root.destroy()
        except (CalendarError, OSError) as exc:
            messagebox.showerror("Could not save", str(exc), parent=self.root)


def launch(root_path=DEFAULT_ROOT):
    root = tk.Tk()
    try:
        CalendarApp(root, Workspace(root_path))
        root.mainloop()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
