"""One reusable form editor for semester setup and the main desktop window."""

import copy
import tkinter as tk
from tkinter import messagebox, ttk

from .models import CalendarError
from .semester_editor import SemesterDraft
from .semesters import create_semester, templates


class SemesterEditor(ttk.Frame):
    def __init__(self, parent, workspace, sid=None, on_saved=None, on_close=None):
        super().__init__(parent, padding=22)
        self.workspace, self.on_saved, self.on_close = workspace, on_saved, on_close
        self.draft = SemesterDraft(workspace, sid) if sid else None
        self.saved = False
        self.pack(fill="both", expand=True)
        ttk.Label(self, text="Edit school timetable" if sid else "Create school timetable", style="Section.TLabel").pack(anchor="w")
        ttk.Label(self, text="Shared by every profile using this semester. Changes save together after validation.", style="Muted.TLabel", wraplength=850).pack(anchor="w", pady=(6, 14))
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        self.status = tk.StringVar(value="Edit a row, then apply it to the draft. Save timetable when ready.")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=510).pack(side="left")
        self.save_button = ttk.Button(footer, text="Save timetable", style="Accent.TButton", command=lambda: self.run(self.save))
        self.save_button.pack(side="right")
        ttk.Button(footer, text="Close", command=self.close).pack(side="right", padx=8)
        if sid:
            ttk.Button(footer, text="Reload", command=lambda: self.run(self.reload)).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self.settings_tab = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(self.settings_tab, text="Semester")
        defaults = self.draft.settings() if self.draft else dict(name="", blocks="", weekdays="mon=monday,tue=tuesday,wed=wednesday,thu=thursday,fri=friday", utc_offset="+08:00", noon_cutoff="12:30")
        self.settings_vars = {key: tk.StringVar(value=value) for key, value in defaults.items()}
        self.id_var = tk.StringVar(value=sid or "")
        self.template_var = tk.StringVar(value="Start blank")
        if not sid:
            source = ttk.Frame(self.settings_tab)
            source.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            ttk.Label(source, text="Starting point").pack(side="left", padx=(0, 16))
            picker = ttk.Combobox(source, textvariable=self.template_var, values=("Start blank", *templates()), state="readonly", width=24)
            picker.pack(side="left")
            picker.bind("<<ComboboxSelected>>", lambda _: self.choose_template())
            ttk.Label(source, text="Examples are optional; verify their times.", style="Muted.TLabel").pack(side="left", padx=12)
        labels = [("Semester ID", self.id_var, "Letters, numbers, dashes or underscores; fixed after creation.")]
        labels += [(label, self.settings_vars[key], hint) for key, label, hint in (
            ("name", "Display name", "Name shown when choosing a semester."),
            ("blocks", "Block keys", "Comma-separated, e.g. A,B,C,T. Existing student keys must remain valid."),
            ("weekdays", "Weekday patterns", "Example: mon=red,tue=blue. Omitted weekdays have no classes."),
            ("utc_offset", "School UTC offset", "Fixed clock, e.g. +08:00."),
            ("noon_cutoff", "Half-day cutoff", "HH:MM, e.g. 12:30."))]
        self.settings_tab.columnconfigure(1, weight=1)
        self.settings_entries = {}
        for i, (label, variable, hint) in enumerate(labels):
            row = i * 2 + (0 if sid else 1)
            ttk.Label(self.settings_tab, text=label).grid(row=row, column=0, sticky="w", padx=(0, 16))
            entry = ttk.Entry(self.settings_tab, textvariable=variable, state="readonly" if i == 0 and sid else "normal")
            entry.grid(row=row, column=1, sticky="ew")
            self.settings_entries[label] = entry
            ttk.Label(self.settings_tab, text=hint, style="Muted.TLabel", wraplength=640).grid(row=row + 1, column=1, sticky="w", pady=(2, 10))
        if not sid:
            self.save_button.configure(text="Create draft")
            self.status.set("Create the semester first, then add its sessions in the editor.")
        self.tables = {}
        self.build_table("classes", "Classes", ("session_id", "pattern", "block", "start", "end"), "Each row is one complete interval. Keep its session ID when changing times.")
        self.build_table("activities", "CAS & clubs", ("session_id", "pattern", "activity", "kind", "start", "end"), "Kind is cas or club. Student club names are entered separately under CAS & clubs.")
        self.build_table("timing", "Timing choices", ("block", "choice", "session_id", "start", "end"), "Blank times inherit the session time. A blank session creates a choice without overrides.")
        if not sid:
            for item in self.tables.values():
                self.tabs.tab(item["tab"], state="disabled")
        self.refresh()
        self.baseline = self.state()

    def build_table(self, key, label, fields, hint):
        tab = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(tab, text=label)
        ttk.Label(tab, text=hint, style="Muted.TLabel", wraplength=830).pack(anchor="w", pady=(0, 10))
        form = ttk.Frame(tab)
        form.pack(side="bottom", fill="x", pady=(14, 0))
        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=len(fields), sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="New row", command=lambda: self.new_row(key)).pack(side="left")
        ttk.Button(buttons, text="Apply row", command=lambda: self.run(lambda: self.apply_row(key))).pack(side="left", padx=8)
        ttk.Button(buttons, text="Remove selected", command=lambda: self.run(lambda: self.remove_row(key))).pack(side="left")
        variables = {}
        for i, field in enumerate(fields):
            form.columnconfigure(i, weight=1)
            ttk.Label(form, text={"session_id": "Session ID", "start": "Start · HH:MM", "end": "End · HH:MM"}.get(field, field.title())).grid(row=0, column=i, sticky="w", padx=(0, 8))
            variable = tk.StringVar()
            variables[field] = variable
            if field == "kind":
                entry = ttk.Combobox(form, textvariable=variable, values=("cas", "club"), state="readonly", width=9)
            else:
                entry = ttk.Entry(form, textvariable=variable, width=13)
            entry.grid(row=1, column=i, sticky="ew", padx=(0, 8))
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        tree = ttk.Treeview(holder, columns=fields, show="headings", selectmode="browse", height=8)
        scroll = ttk.Scrollbar(holder, command=tree.yview)
        scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(fill="both", expand=True)
        for field in fields:
            tree.heading(field, text=field.replace("_", " ").title())
            tree.column(field, width=110, minwidth=60)
        self.tables[key] = dict(tab=tab, tree=tree, fields=fields, variables=variables, baseline=tuple("" for _ in fields))
        tree.bind("<<TreeviewSelect>>", lambda _: self.select_row(key))

    def rows(self, key):
        if not self.draft:
            return []
        if key == "classes":
            return self.draft.sessions
        if key == "activities":
            return self.draft.activities
        result = []
        for block, choices in self.draft.config.get("timing_options", {}).items():
            for choice, overrides in choices.items():
                for sid, times in (overrides or {"": {}}).items():
                    result.append(dict(block=block, choice=choice, session_id=sid, start=times.get("start", ""), end=times.get("end", "")))
        return result

    def refresh(self):
        for key, table in self.tables.items():
            tree = table["tree"]
            tree.delete(*tree.get_children())
            for i, row in enumerate(self.rows(key)):
                tree.insert("", "end", iid=str(i), values=[row[field] for field in table["fields"]])

    def form_values(self, key):
        return tuple(v.get().strip() for v in self.tables[key]["variables"].values())

    def row_dirty(self, key):
        return self.form_values(key) != self.tables[key]["baseline"]

    def new_row(self, key):
        table = self.tables[key]
        if self.row_dirty(key) and not messagebox.askyesno("Unapplied row", "Discard the changes in this row?", parent=self):
            return
        table["tree"].selection_remove(*table["tree"].selection())
        for variable in table["variables"].values():
            variable.set("")
        table["baseline"] = self.form_values(key)

    def select_row(self, key):
        table = self.tables[key]
        selection = table["tree"].selection()
        if not selection:
            return
        if self.row_dirty(key):
            self.status.set("Apply the current row or choose New row to discard its edits before loading another.")
            return
        for variable, value in zip(table["variables"].values(), table["tree"].item(selection[0], "values")):
            variable.set(value)
        table["baseline"] = self.form_values(key)

    def apply_row(self, key):
        table = self.tables[key]
        values = self.form_values(key)
        if key == "timing":
            self.draft.put_timing(*values)
        else:
            self.draft.put_session(values, activity=key == "activities")
        table["baseline"] = values
        self.refresh()
        self.status.set("Row applied to the draft. Save timetable to commit all changes.")

    def remove_row(self, key):
        table = self.tables[key]
        selection = table["tree"].selection()
        if not selection:
            raise CalendarError("Select a row to remove.")
        if self.row_dirty(key):
            raise CalendarError("Apply or discard the row edits before removing a session.")
        row = self.rows(key)[int(selection[0])]
        if key == "timing":
            if row["session_id"]:
                self.draft.put_timing(row["block"], row["choice"], row["session_id"], "", "")
            else:
                self.draft.remove_timing(row["block"], row["choice"])
        else:
            self.draft.remove_session(row["session_id"], activity=key == "activities")
        for variable in table["variables"].values():
            variable.set("")
        table["baseline"] = self.form_values(key)
        self.refresh()
        self.status.set("Row removed from the draft. Save timetable when ready.")

    def state(self):
        return copy.deepcopy((self.id_var.get(), self.template_var.get(), {k: v.get() for k, v in self.settings_vars.items()},
                              (self.draft.config, self.draft.sessions, self.draft.activities) if self.draft else None))

    def choose_template(self):
        chosen = self.template_var.get() != "Start blank"
        for label in ("Block keys", "Weekday patterns", "School UTC offset", "Half-day cutoff"):
            self.settings_entries[label].configure(state="disabled" if chosen else "normal")
        self.status.set("The example supplies blocks and times; edit them after creating it." if chosen else "Enter your block keys and weekday patterns, then create a draft.")

    def reload(self):
        if (self.state() != self.baseline or any(self.row_dirty(key) for key in self.tables)) and not messagebox.askyesno("Reload timetable", "Discard unsaved timetable edits and reload?", parent=self):
            return
        candidate = SemesterDraft(self.workspace, self.draft.folder.name)
        self.draft = candidate
        for key, value in candidate.settings().items():
            self.settings_vars[key].set(value)
        for key, table in self.tables.items():
            for variable in table["variables"].values():
                variable.set("")
            table["baseline"] = self.form_values(key)
        self.refresh()
        self.baseline = self.state()
        self.status.set("Reloaded the latest timetable. Unsaved edits were discarded.")

    def save(self):
        values = {key: var.get() for key, var in self.settings_vars.items()}
        if self.draft is None:
            sid = self.id_var.get().strip()
            if self.template_var.get() == "Start blank":
                create_semester(self.workspace, sid, **values)
            else:
                create_semester(self.workspace, sid, name=values["name"] or sid, template=self.template_var.get())
            self.draft = SemesterDraft(self.workspace, sid)
            # Rebuild to freeze the ID and enable session tabs for this draft.
            callback, close = self.on_saved, self.on_close
            parent = self.master
            self.destroy()
            editor = SemesterEditor(parent, self.workspace, sid, callback, close)
            parent.editor = editor
            if callback:
                callback(sid)
            editor.tabs.select(editor.tables["classes"]["tab"])
            return
        if any(self.row_dirty(key) for key in self.tables):
            raise CalendarError("Apply each edited row before saving the timetable.")
        self.draft.update_settings(**values)
        self.draft.save()
        self.saved = True
        self.baseline = self.state()
        self.status.set("Timetable saved. Existing selections are preserved; refresh your preview.")
        if self.on_saved:
            self.on_saved(self.draft.folder.name)

    def run(self, operation):
        try:
            operation()
        except (CalendarError, OSError) as exc:
            self.status.set(str(exc))
            messagebox.showerror("Timetable not saved", str(exc), parent=self)

    def close(self):
        if (self.state() != self.baseline or any(self.row_dirty(key) for key in self.tables)) and not messagebox.askyesno("Unsaved timetable", "Discard unsaved timetable edits?", parent=self):
            return
        if self.on_close:
            self.on_close()


def open_editor(owner, workspace, sid=None, on_saved=None):
    """Reuse one modal editor window; never spawn a window per row."""
    previous = getattr(owner, "timetable_window", None)
    if previous is not None and previous.winfo_exists():
        previous.lift()
        return previous.editor
    window = tk.Toplevel(owner.root)
    owner.timetable_window = window
    window.title("Block Calendar Utils · School timetable")
    window.geometry("1000x760")
    window.minsize(900, 700)
    window.transient(owner.root)
    try:
        window.editor = SemesterEditor(window, workspace, sid, on_saved, window.destroy)
    except Exception:
        window.destroy()
        raise
    window.protocol("WM_DELETE_WINDOW", lambda: window.editor.close())
    window.grab_set()
    return window.editor
