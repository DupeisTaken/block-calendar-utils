"""One lightweight Tk window. All file/date/export rules live in shared services."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from .app import DEFAULT_ROOT, Workspace
from .models import CalendarError, Course, DayOverride
from .schedule import preview_text
from .semesters import describe_semester
from .storage import digest, parse_date, safe_child

BG, INK, MUTED, ACCENT = "#f4f5f1", "#1b302d", "#626e69", "#24695b"
MODES = {"Single day": "day", "First and last dates": "custom", "This week": "this", "Next week": "next", "Choose a week": "week"}


def option_label(option):
    return {"study_hall": "Study hall", "toefl": "TOEFL lesson"}.get(option, option.replace("_", " ").title())


class CalendarApp:
    def __init__(self, root, workspace):
        self.root, self.workspace = root, workspace
        self.settings = workspace.settings()
        self.ctx = workspace.context(self.settings["profile"], workspace.selected_semester(), create=True)
        self.baseline, self.course_vars = [], []
        self.activity_baseline, self.activity_vars = [], {}
        self.course_digest = None
        root.title("Block Calendar Utils")
        root.geometry("1120x800")
        root.minsize(980, 700)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._style()
        self._layout()
        self.load_courses()
        self.load_activities()
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
        ttk.Label(header, text="Block Calendar Utils", style="Title.TLabel").pack(anchor="w")
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
        self.activities_tab = ttk.Frame(self.tabs, padding=18)
        self.tabs.add(self.activities_tab, text="04  CAS & clubs")
        self._courses_layout()
        self._preview_layout()
        self._exceptions_layout()
        self._activities_layout()
        footer = ttk.Frame(self.root, padding=(28, 16))
        # Reserve the action bar before the expandable notebook. Otherwise Tk
        # can allocate all height to notebook content at enlarged font scales.
        footer.pack(side="bottom", fill="x", before=self.tabs)
        self.status = tk.StringVar(value="Choose your classes, then preview a week.")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=590).pack(side="left")
        self.export_button = ttk.Button(footer, text="Export .ics", style="Accent.TButton", command=lambda: self.run(self.export))
        self.export_button.pack(side="right")
        ttk.Button(footer, text="Save selections", command=lambda: self.run(self.save)).pack(side="right", padx=10)

    def _activities_layout(self):
        ttk.Label(self.activities_tab, text="Optional CAS and clubs", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self.activities_tab, text="CAS uses its fixed title. Name the clubs you attend, then choose what to include in this export.", style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(8, 14))
        self.cas_var = tk.BooleanVar(value=self.settings.get("cas", False))
        self.clubs_var = tk.BooleanVar(value=self.settings.get("clubs", True))
        ttk.Checkbutton(self.activities_tab, text="Include CAS", variable=self.cas_var).pack(anchor="w")
        ttk.Checkbutton(self.activities_tab, text="Include enabled, named clubs", variable=self.clubs_var).pack(anchor="w", pady=(4, 16))
        holder = ttk.Frame(self.activities_tab)
        holder.pack(fill="both", expand=True)
        self.activity_canvas = tk.Canvas(holder, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(holder, command=self.activity_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.activity_canvas.configure(yscrollcommand=scrollbar.set)
        self.activity_canvas.pack(fill="both", expand=True)
        self.activity_grid = ttk.Frame(self.activity_canvas)
        window = self.activity_canvas.create_window((0, 0), window=self.activity_grid, anchor="nw")
        self.activity_canvas.bind("<Configure>", lambda e: self.activity_canvas.itemconfigure(window, width=e.width))
        self.activity_grid.bind("<Configure>", lambda _: self.activity_canvas.configure(scrollregion=self.activity_canvas.bbox("all")))

    def load_activities(self):
        self.activity_baseline = self.ctx.activities()
        self.activity_digest = digest(self.ctx.activities_path)
        self.activity_vars = {}
        for child in self.activity_grid.winfo_children():
            child.destroy()
        self.activity_grid.columnconfigure(1, weight=1)
        for row, item in enumerate(self.activity_baseline):
            slots = ", ".join(f"{s.pattern.title()} {s.start:%H:%M}–{s.end:%H:%M}" for s in self.ctx.semester.activity_sessions if s.block == item.activity)
            if self.ctx.semester.activities[item.activity] == "cas":
                ttk.Label(self.activity_grid, text="CAS", font=(self.font, 11, "bold")).grid(row=row * 2, column=0, sticky="w", pady=(12, 3))
            else:
                name, enabled, room = tk.StringVar(value=item.name), tk.BooleanVar(value=item.enabled), tk.StringVar(value=item.location)
                self.activity_vars[item.activity] = (name, enabled, room)
                ttk.Checkbutton(self.activity_grid, text=item.activity, variable=enabled).grid(row=row * 2, column=0, sticky="w", pady=(12, 3), padx=(0, 12))
                ttk.Entry(self.activity_grid, textvariable=name, width=30).grid(row=row * 2, column=1, sticky="ew", pady=(12, 3))
                ttk.Label(self.activity_grid, text="Room").grid(row=row * 2, column=2, padx=8)
                ttk.Entry(self.activity_grid, textvariable=room, width=12).grid(row=row * 2, column=3)
                name.trace_add("write", lambda *_, n=name, use=enabled: use.set(bool(n.get().strip())))
            ttk.Label(self.activity_grid, text=slots, style="Muted.TLabel", wraplength=750).grid(row=row * 2 + 1, column=0, columnspan=4, sticky="w", pady=(0, 10))
        if not self.activity_baseline:
            ttk.Label(self.activity_grid, text="No activities are defined for this semester. Add its activities.csv first.", wraplength=750).grid(sticky="w")

    def read_activity_form(self):
        from dataclasses import replace
        result = []
        for item in self.activity_baseline:
            if item.activity in self.activity_vars:
                name, enabled, room = self.activity_vars[item.activity]
                item = replace(item, name=name.get().strip(), enabled=enabled.get(), location=room.get().strip())
            result.append(item)
        return result

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
        self.anchor_label = ttk.Label(dates, text="First date")
        self.anchor_label.pack(side="left")
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
        self.set_preview_text("Choose Single day, a date range or a week above, then refresh the preview.\n\nOnly enabled courses and study periods are included.")

    def _exceptions_layout(self):
        ttk.Label(self.exceptions_tab, text="Exceptions · dates, weekday patterns and time filters", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        columns = ("date", "action", "pattern", "shift", "skip", "note", "source")
        self.exception_holder = ttk.Frame(self.exceptions_tab)
        self.exception_holder.pack(fill="both", expand=True)
        self.exception_tree = ttk.Treeview(self.exception_holder, columns=columns, show="headings", height=4)
        for column, width in zip(columns, [130, 90, 110, 90, 100, 230, 90]):
            self.exception_tree.heading(column, text="Details" if column == "note" else column.title())
            self.exception_tree.column(column, width=width, minwidth=55, stretch=column == "note")
        scroll = ttk.Scrollbar(self.exception_holder, command=self.exception_tree.yview)
        self.exception_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.exception_tree.pack(side="left", fill="both", expand=True)
        self.exception_tree.bind("<<TreeviewSelect>>", lambda _: self.select_exception())
        form = ttk.Frame(self.exceptions_tab)
        form.pack(fill="x", pady=(16, 8))
        for column in range(5):
            form.columnconfigure(column, weight=1)
        self.exc_date = tk.StringVar()
        self.exc_action = tk.StringVar(value="use")
        self.exc_pattern = tk.StringVar(value=self.ctx.semester.patterns[0])
        self.exc_shift = tk.StringVar(value="Inherit")
        self.exc_half = tk.StringVar(value="All sessions")
        self.exc_note = tk.StringVar()
        self.exc_end = tk.StringVar()
        self.exc_blank = tk.StringVar()
        self.exc_morning = tk.StringVar()
        self.exc_afternoon = tk.StringVar()
        self.exc_overlap = tk.StringVar(value="trim")
        for col, label in enumerate(["Date · YYYY-MM-DD", "Action", "Follow pattern", "Timing", "Session filter"]):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 12), pady=(0, 5))
        ttk.Entry(form, textvariable=self.exc_date, width=15).grid(row=1, column=0, sticky="ew", padx=(0, 12))
        action = ttk.Combobox(form, textvariable=self.exc_action, values=["off", "use", "adjust", "partial"], state="readonly", width=10)
        action.grid(row=1, column=1, padx=(0, 12))
        action.bind("<<ComboboxSelected>>", lambda _: self.update_exception_fields())
        self.exc_pattern_box = ttk.Combobox(form, textvariable=self.exc_pattern, values=self.ctx.semester.patterns, state="readonly", width=14)
        self.exc_pattern_box.grid(row=1, column=2, padx=(0, 12))
        self.exc_shift_box = ttk.Combobox(form, textvariable=self.exc_shift, values=["Inherit", "Normal", "Late (+20 min)"], state="readonly", width=15)
        self.exc_shift_box.grid(row=1, column=3, padx=(0, 12))
        self.exc_half_box = ttk.Combobox(form, textvariable=self.exc_half, values=["All sessions", "No morning", "No afternoon"], state="readonly", width=14)
        self.exc_half_box.grid(row=1, column=4, sticky="w")
        # A second compact row keeps date ranges and blank windows together.
        for col, (label, variable) in enumerate([
                ("Through date · optional", self.exc_end), ("Blank hours", self.exc_blank),
                ("Morning cutoff", self.exc_morning), ("Afternoon cutoff", self.exc_afternoon)]):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=2, column=col, sticky="w", pady=(10, 5))
            ttk.Entry(form, textvariable=variable, width=15).grid(row=3, column=col, sticky="ew", padx=(0, 12))
        ttk.Label(form, text="Overlapping sessions", style="Muted.TLabel").grid(row=2, column=4, sticky="w", pady=(10, 5))
        ttk.Combobox(form, textvariable=self.exc_overlap, values=["trim", "remove"], state="readonly", width=14).grid(row=3, column=4, sticky="w")
        self.cutoff_label = hint = ttk.Label(self.exceptions_tab, text=self.exception_hint(), style="Muted.TLabel", wraplength=970)
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
        return self.read_course_form() != self.baseline or self.read_activity_form() != self.activity_baseline

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
        from .activities import validate_activities
        from .storage import validate_courses
        # Validate both forms before saving either; input errors keep edits intact.
        validate_courses(self.read_course_form(), self.ctx.semester)
        validate_activities(self.read_activity_form(), self.ctx.semester)
        if self.read_course_form() != self.baseline:
            self.ctx.save_courses(self.read_course_form(), self.course_digest)
        if self.read_activity_form() != self.activity_baseline:
            self.ctx.save_activities(self.read_activity_form(), self.activity_digest)
        self.load_courses()
        self.load_activities()
        self.status.set("Selections saved. Your CSV files are ready for the next export.")

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
        self.load_activities()
        self.refresh_exceptions()
        self.clock_label.configure(text=str(self.ctx.semester.clock))
        self.status.set("Reloaded the latest files.")

    def keep_edits(self):
        if not self.dirty():
            return True
        answer = messagebox.askyesnocancel("Unsaved selections", "Save your course and club edits before continuing?", parent=self.root)
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
            self.settings.update(profile=self.ctx.profile, semester=self.ctx.semester.id, active_semester=self.ctx.semester.id, cas=False, clubs=True)
            self.workspace.save_settings(self.settings)
            self.load_courses()
            self.load_activities()
            self.cas_var.set(False)
            self.clubs_var.set(True)
            self.refresh_exceptions()
            self.exc_pattern_box.configure(values=self.ctx.semester.patterns)
            self.exc_pattern.set(self.ctx.semester.patterns[0])
            self.cutoff_label.configure(text=self.exception_hint())
            self.set_preview_text("Profile changed. Refresh the preview to see this timetable.")
            self.status.set(f"Using {self.ctx.profile} · {self.ctx.semester.name}")
        finally:
            # A failed/cancelled switch must not label the old data as a new user.
            self.profile_var.set(self.ctx.profile)
            self.semester_var.set(self.ctx.semester.id)
            self.clock_label.configure(text=str(self.ctx.semester.clock))

    def update_date_fields(self):
        mode = MODES[self.mode_var.get()]
        self.weeks_entry.configure(state="disabled" if mode in {"custom", "day"} else "normal")
        self.anchor_label.configure(text="Date" if mode == "day" else "First date")
        self.end_entry.configure(state="disabled" if mode == "day" else "normal")
        # Presets fill both endpoints. Week edits become custom ranges; day
        # edits keep identical endpoints so visible and exported dates agree.
        if mode != "custom":
            first, last = self.ctx.dates(self.range_settings())
            self.anchor_var.set(str(first))
            self.end_var.set(str(last))
        self.displayed_dates = (self.anchor_var.get(), self.end_var.get())

    def mark_custom_dates(self):
        # Keep single-day edits in this mode, including paste/cut and incomplete
        # input. Validation happens on preview; the end always mirrors the date.
        if MODES[self.mode_var.get()] == "day":
            self.end_var.set(self.anchor_var.get())
            self.displayed_dates = (self.anchor_var.get(), self.end_var.get())
            return
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
        mode = MODES[self.mode_var.get()]
        anchor = self.anchor_var.get().strip()
        return dict(self.settings, mode=mode, anchor=anchor, end=anchor if mode == "day" else self.end_var.get().strip(), weeks=1 if mode in {"custom", "day"} else int(self.weeks_var.get()), late=self.late_var.get(), schedule_mode="weekdays" if self.weekdays_var.get() else "exceptions", cas=self.cas_var.get(), clubs=self.clubs_var.get())

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

    def exception_hint(self):
        return f"partial: filter times · Blank hours: 10:00-11:00 (comma-separated) · Cutoffs: HH:MM · Session filter default: {self.ctx.semester.noon_cutoff:%H:%M}"

    def update_exception_fields(self):
        kind = self.exc_action.get()
        self.exc_pattern_box.configure(state="readonly" if kind == "use" else "disabled")
        self.exc_shift_box.configure(state="disabled" if kind == "off" else "readonly")
        self.exc_half_box.configure(state="disabled" if kind == "off" else "readonly")
        if kind == "adjust" and self.exc_shift.get() == "Inherit":
            self.exc_shift.set("Normal")

    def refresh_exceptions(self):
        from .storage import load_overrides
        self.exception_digest = digest(self.ctx.exceptions_path)
        self.exception_items = self.ctx.exceptions()
        self.exception_rows = {}
        school = load_overrides(self.ctx.folder / "exceptions.csv", self.ctx.semester)
        for item in self.exception_tree.get_children():
            self.exception_tree.delete(item)
        for source, items in [("School", school), ("Yours", self.exception_items)]:
            for i in items:
                from .exception_times import window_description
                description = " · ".join(filter(None, [window_description(i), i.note]))
                row = self.exception_tree.insert("", "end", values=(str(i.date), i.action, i.pattern, "Inherit" if i.time_shift_minutes is None else i.time_shift_minutes, i.half_day.removeprefix("no-"), description, source))
                self.exception_rows[row] = i

    def select_exception(self):
        selected = self.exception_tree.selection()
        if not selected:
            return
        day, action, pattern, shift, skip, note, _ = self.exception_tree.item(selected[0], "values")
        item = self.exception_rows[selected[0]]
        self.exc_end.set("")
        self.exc_blank.set(item.blank_hours)
        self.exc_morning.set(item.morning_cutoff)
        self.exc_afternoon.set(item.afternoon_cutoff)
        self.exc_overlap.set(item.overlap)
        self.exc_date.set(day)
        self.exc_action.set(action)
        self.exc_pattern.set(pattern)
        self.exc_shift.set({"0": "Normal", "20": "Late (+20 min)"}.get(str(shift), str(shift)))
        self.exc_note.set(item.note)
        self.exc_half.set({"": "All sessions", "morning": "No morning", "afternoon": "No afternoon"}[skip])
        self.update_exception_fields()

    def save_exception(self):
        day, action = parse_date(self.exc_date.get().strip()), self.exc_action.get()
        shifts = {"Inherit": None, "Normal": 0, "Late (+20 min)": 20}
        text = self.exc_shift.get()
        shift = None if action == "off" else shifts[text] if text in shifts else int(text)
        half = "" if action == "off" else {"All sessions": "", "No morning": "no-morning", "No afternoon": "no-afternoon"}[self.exc_half.get()]
        from dataclasses import replace
        item = DayOverride(day, action, self.exc_pattern.get() if action == "use" else "", shift, self.exc_note.get().strip(), half,
                           self.exc_blank.get().strip(), self.exc_morning.get().strip(), self.exc_afternoon.get().strip(), self.exc_overlap.get())
        days = self.exception_dates()
        items = [i for i in self.exception_items if i.date not in days] + [replace(item, date=d) for d in days]
        self.ctx.save_exceptions(items, self.exception_digest)
        self.weekdays_var.set(False)
        self.refresh_exceptions()
        self.status.set(f"Saved exceptions for {min(days)} to {max(days)}. Refresh the preview to see them.")

    def remove_exception(self):
        days = self.exception_dates()
        self.ctx.save_exceptions([i for i in self.exception_items if i.date not in days], self.exception_digest)
        self.refresh_exceptions()
        self.status.set("Removed your exceptions for the selected dates. School/default rules apply again.")

    def exception_dates(self):
        """GUI fields stay ISO even though the terminal accepts short dates."""
        from datetime import timedelta
        first = parse_date(self.exc_date.get().strip())
        last = parse_date(self.exc_end.get().strip()) if self.exc_end.get().strip() else first
        if not 0 <= (last - first).days < 3660:
            raise CalendarError("Choose an ordered exception range of at most 3,660 days.")
        return {first + timedelta(days=offset) for offset in range((last - first).days + 1)}

    def close(self):
        try:
            if self.keep_edits():
                self.root.destroy()
        except (CalendarError, OSError) as exc:
            messagebox.showerror("Could not save", str(exc), parent=self.root)


class SemesterSetup:
    """Review a real definition before opening courses; never choose one silently."""

    def __init__(self, root, workspace, profile=None):
        self.root, self.workspace, self.profile = root, workspace, profile
        root.title("Block Calendar Utils · Select semester")
        root.geometry("920x720")
        root.minsize(760, 620)
        root.configure(bg=BG)
        CalendarApp._style(self)
        self.frame = ttk.Frame(root, padding=28)
        self.frame.pack(fill="both", expand=True)
        ttk.Label(self.frame, text="Start with your semester", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.frame, text="Review the blocks and weekly arrangement before entering courses.", style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(8, 18))
        self.semester_var = tk.StringVar()
        picker = ttk.Combobox(self.frame, textvariable=self.semester_var, values=workspace.semesters(), state="readonly", width=30)
        picker.pack(anchor="w", pady=(0, 14))
        picker.bind("<<ComboboxSelected>>", lambda _: self.review())
        footer = ttk.Frame(self.frame)
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        self.use_button = ttk.Button(footer, text="Use this timetable", style="Accent.TButton", command=self.activate, state="disabled")
        self.use_button.pack(side="right")
        ttk.Label(footer, text="New semester? Define it from the terminal first.", style="Muted.TLabel", wraplength=400).pack(side="left")
        holder = ttk.Frame(self.frame)
        holder.pack(fill="both", expand=True)
        self.text = tk.Text(holder, wrap="word", bg="white", fg=INK, font=(self.font, 11), relief="flat", padx=18, pady=14)
        scroll = ttk.Scrollbar(holder, command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(fill="both", expand=True)
        self.set_text("Choose an existing semester above to review its timetable.\n\nTo define different blocks and times:\n\npython -m bcalendar-utils --write --semesters --new spring --blocks X,Y,Z\n\nFill semesters/spring/timetable.csv, then run:\n\npython -m bcalendar-utils --write --semesters --use spring\n\nClose and reopen this window after creating a new definition.")

    def set_text(self, value):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.configure(state="disabled")

    def review(self):
        try:
            self.set_text(describe_semester(safe_child(self.workspace.root / "semesters", self.semester_var.get())))
            self.use_button.configure(state="normal")
        except (CalendarError, OSError) as exc:
            self.set_text(f"This definition needs attention before use.\n\n{exc}\n\nEdit its semester.json and timetable.csv, then select it again.")
            self.use_button.configure(state="disabled")

    def activate(self):
        try:
            self.workspace.use_semester(self.semester_var.get(), self.profile)
        except (CalendarError, OSError) as exc:
            self.set_text(str(exc))
            return
        self.frame.destroy()
        self.app = CalendarApp(self.root, self.workspace)


def launch(root_path=DEFAULT_ROOT, *, semester_id=None, profile=None):
    root = tk.Tk()
    try:
        workspace = Workspace(root_path)
        if semester_id:
            workspace.use_semester(semester_id, profile)
        elif profile and workspace.settings()["active_semester"]:
            workspace.use_semester(workspace.selected_semester(), profile)
        if workspace.settings()["active_semester"]:
            try:
                describe_semester(safe_child(workspace.root / "semesters", workspace.selected_semester()))
            except CalendarError:
                SemesterSetup(root, workspace, profile)
            else:
                CalendarApp(root, workspace)
        else:
            SemesterSetup(root, workspace, profile)
        root.mainloop()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
