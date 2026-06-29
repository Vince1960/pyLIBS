#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Small Tkinter editor for the pyLIBS Stark SQLite database.

Usage:
    python3 stark_db_editor.py
    python3 stark_db_editor.py /path/to/Stark.db

Features:
- Opens the Stark table.
- Search/filter rows by element, ion and wavelength range.
- Add a new row.
- Edit the selected row.
- Delete the selected row.
- Creates a timestamped .bak copy before destructive writes.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


TABLE = "Stark"
COLUMNS = [
    "Element",
    "Ion",
    "Wavelength",
    "w-T5000",
    "a-T5000",
    "w-T10000",
    "a-T10000",
    "note",
    "acc",
]

NUMERIC_COLUMNS = {
    "Ion": int,
    "Wavelength": float,
    "w-T5000": float,
    "a-T5000": float,
    "w-T10000": float,
    "a-T10000": float,
}


def qident(name: str) -> str:
    """Quote an SQLite identifier, needed for names like w-T5000."""
    return '"' + name.replace('"', '""') + '"'


def convert_value(column: str, value: str):
    value = value.strip()
    if value == "":
        return None
    converter = NUMERIC_COLUMNS.get(column)
    if converter is None:
        return value
    try:
        return converter(value)
    except ValueError as exc:
        raise ValueError(f"Invalid value for {column}: {value!r}") from exc


class RowEditor(tk.Toplevel):
    def __init__(self, master, title: str, initial: dict[str, object] | None = None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.vars: dict[str, tk.StringVar] = {}

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        initial = initial or {}
        for r, col in enumerate(COLUMNS):
            ttk.Label(frame, text=col).grid(row=r, column=0, padx=4, pady=3, sticky="e")
            var = tk.StringVar(value="" if initial.get(col) is None else str(initial.get(col)))
            self.vars[col] = var
            width = 42 if col in ("note", "acc") else 18
            ttk.Entry(frame, textvariable=var, width=width).grid(row=r, column=1, padx=4, pady=3, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(COLUMNS), column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(buttons, text="OK", command=self.ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.transient(master)
        self.grab_set()
        self.wait_visibility()
        self.focus()

    def ok(self):
        try:
            self.result = {col: convert_value(col, self.vars[col].get()) for col in COLUMNS}
        except ValueError as exc:
            messagebox.showerror("Invalid value", str(exc), parent=self)
            return
        self.destroy()


class StarkDbEditor(tk.Tk):
    def __init__(self, db_path: str | None = None):
        super().__init__()
        self.title("Stark.db editor")
        self.geometry("1180x620")
        self.minsize(950, 480)

        self.db_path: Path | None = None
        self.conn: sqlite3.Connection | None = None
        self._backup_done = False

        self._build_ui()

        if db_path:
            self.open_database(Path(db_path))
        else:
            default = Path.cwd() / "Stark.db"
            if default.exists():
                self.open_database(default)

    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")

        ttk.Button(top, text="Open DB", command=self.ask_open_database).pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="left", padx=3)
        ttk.Button(top, text="Add", command=self.add_row).pack(side="left", padx=(12, 3))
        ttk.Button(top, text="Edit selected", command=self.edit_selected).pack(side="left", padx=3)
        ttk.Button(top, text="Delete selected", command=self.delete_selected).pack(side="left", padx=3)

        ttk.Label(top, text="Element").pack(side="left", padx=(18, 3))
        self.element_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.element_var, width=8).pack(side="left")

        ttk.Label(top, text="Ion").pack(side="left", padx=(8, 3))
        self.ion_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.ion_var, width=5).pack(side="left")

        ttk.Label(top, text="λ min").pack(side="left", padx=(8, 3))
        self.wmin_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.wmin_var, width=9).pack(side="left")

        ttk.Label(top, text="λ max").pack(side="left", padx=(8, 3))
        self.wmax_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.wmax_var, width=9).pack(side="left")

        ttk.Button(top, text="Search", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(top, text="Clear filters", command=self.clear_filters).pack(side="left")

        self.status_var = tk.StringVar(value="Open a Stark.db file.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=8, pady=(0, 4))

        columns = ["rowid"] + COLUMNS
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        widths = {
            "rowid": 70,
            "Element": 80,
            "Ion": 60,
            "Wavelength": 110,
            "w-T5000": 100,
            "a-T5000": 100,
            "w-T10000": 105,
            "a-T10000": 105,
            "note": 300,
            "acc": 110,
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 100), anchor="center" if col != "note" else "w")

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        yscroll = ttk.Scrollbar(container, orient="vertical")
        xscroll = ttk.Scrollbar(container, orient="horizontal")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.configure(command=self.tree.yview)
        xscroll.configure(command=self.tree.xview)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

    def ask_open_database(self):
        filename = filedialog.askopenfilename(
            title="Open Stark SQLite database",
            filetypes=[("SQLite database", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")],
        )
        if filename:
            self.open_database(Path(filename))

    def open_database(self, path: Path):
        path = path.expanduser().resolve()
        if not path.exists():
            messagebox.showerror("Open DB", f"File not found:\n{path}", parent=self)
            return

        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            self._validate_schema(conn)
        except Exception as exc:
            messagebox.showerror("Open DB", str(exc), parent=self)
            return

        if self.conn is not None:
            self.conn.close()

        self.db_path = path
        self.conn = conn
        self._backup_done = False
        self.refresh()

    def _validate_schema(self, conn: sqlite3.Connection):
        rows = conn.execute(f"PRAGMA table_info({qident(TABLE)})").fetchall()
        existing = [r[1] for r in rows]
        missing = [c for c in COLUMNS if c not in existing]
        if missing:
            raise RuntimeError(f"The table {TABLE!r} is missing columns: {', '.join(missing)}")

    def _ensure_open(self) -> bool:
        if self.conn is None or self.db_path is None:
            messagebox.showinfo("Database", "Open a database first.", parent=self)
            return False
        return True

    def _make_backup_once(self):
        if self._backup_done or self.db_path is None:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = self.db_path.with_suffix(self.db_path.suffix + f".bak_{stamp}")
        shutil.copy2(self.db_path, backup)
        self._backup_done = True
        self.status_var.set(f"Backup created: {backup.name}")

    def _filters(self):
        where = []
        params = []

        element = self.element_var.get().strip()
        if element:
            where.append("Element LIKE ?")
            params.append(element + "%")

        ion = self.ion_var.get().strip()
        if ion:
            try:
                params.append(int(ion))
            except ValueError:
                raise ValueError("Ion must be an integer.")
            where.append("Ion = ?")

        wmin = self.wmin_var.get().strip()
        if wmin:
            try:
                params.append(float(wmin))
            except ValueError:
                raise ValueError("λ min must be numeric.")
            where.append("Wavelength >= ?")

        wmax = self.wmax_var.get().strip()
        if wmax:
            try:
                params.append(float(wmax))
            except ValueError:
                raise ValueError("λ max must be numeric.")
            where.append("Wavelength <= ?")

        clause = " AND ".join(where)
        return clause, params

    def refresh(self):
        if not self._ensure_open():
            return
        try:
            clause, params = self._filters()
            select_cols = ", ".join([qident(c) for c in COLUMNS])
            sql = f"SELECT rowid, {select_cols} FROM {qident(TABLE)}"
            if clause:
                sql += " WHERE " + clause
            sql += " ORDER BY Element, Ion, Wavelength"
            rows = self.conn.execute(sql, params).fetchall()
        except Exception as exc:
            messagebox.showerror("Search", str(exc), parent=self)
            return

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            values = [row["rowid"]] + [row[c] for c in COLUMNS]
            self.tree.insert("", "end", iid=str(row["rowid"]), values=values)

        self.status_var.set(f"{self.db_path} — {len(rows)} row(s) shown")

    def clear_filters(self):
        self.element_var.set("")
        self.ion_var.set("")
        self.wmin_var.set("")
        self.wmax_var.set("")
        self.refresh()

    def _selected_rowid(self):
        item = self.tree.focus()
        if not item:
            messagebox.showinfo("Selection", "Select a row first.", parent=self)
            return None
        return int(item)

    def _row_by_id(self, rowid: int):
        select_cols = ", ".join([qident(c) for c in COLUMNS])
        return self.conn.execute(
            f"SELECT rowid, {select_cols} FROM {qident(TABLE)} WHERE rowid = ?",
            (rowid,),
        ).fetchone()

    def add_row(self):
        if not self._ensure_open():
            return
        dialog = RowEditor(self, "Add Stark row")
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            self._make_backup_once()
            cols_sql = ", ".join(qident(c) for c in COLUMNS)
            placeholders = ", ".join("?" for _ in COLUMNS)
            values = [dialog.result[c] for c in COLUMNS]
            self.conn.execute(
                f"INSERT INTO {qident(TABLE)} ({cols_sql}) VALUES ({placeholders})",
                values,
            )
            self.conn.commit()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Add row", str(exc), parent=self)

    def edit_selected(self):
        if not self._ensure_open():
            return
        rowid = self._selected_rowid()
        if rowid is None:
            return
        row = self._row_by_id(rowid)
        if row is None:
            messagebox.showerror("Edit row", "Selected row no longer exists.", parent=self)
            self.refresh()
            return

        initial = {c: row[c] for c in COLUMNS}
        dialog = RowEditor(self, f"Edit Stark row {rowid}", initial)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            self._make_backup_once()
            assignments = ", ".join(f"{qident(c)} = ?" for c in COLUMNS)
            values = [dialog.result[c] for c in COLUMNS] + [rowid]
            self.conn.execute(
                f"UPDATE {qident(TABLE)} SET {assignments} WHERE rowid = ?",
                values,
            )
            self.conn.commit()
            self.refresh()
            self.tree.selection_set(str(rowid))
            self.tree.focus(str(rowid))
        except Exception as exc:
            messagebox.showerror("Edit row", str(exc), parent=self)

    def delete_selected(self):
        if not self._ensure_open():
            return
        rowid = self._selected_rowid()
        if rowid is None:
            return
        row = self._row_by_id(rowid)
        if row is None:
            self.refresh()
            return

        label = f"{row['Element']} {row['Ion']}  λ={row['Wavelength']}"
        ok = messagebox.askyesno(
            "Delete row",
            f"Delete selected row?\n\n{label}",
            parent=self,
        )
        if not ok:
            return

        try:
            self._make_backup_once()
            self.conn.execute(f"DELETE FROM {qident(TABLE)} WHERE rowid = ?", (rowid,))
            self.conn.commit()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Delete row", str(exc), parent=self)

    def destroy(self):
        if self.conn is not None:
            self.conn.close()
        super().destroy()


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = StarkDbEditor(db_path)
    app.mainloop()


if __name__ == "__main__":
    main()
