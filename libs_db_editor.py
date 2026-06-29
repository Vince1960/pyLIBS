#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic Tkinter editor for pyLIBS LIBS.db SQLite databases.

Usage:
    python3 libs_db_editor.py
    python3 libs_db_editor.py /path/to/LIBS.db

Features:
- Opens any SQLite LIBS.db file.
- Shows all user tables in a drop-down list.
- Dynamically adapts to the selected table columns.
- Browse, filter/search, add, edit and delete rows.
- Uses SQLite rowid for safe row selection.
- Creates a timestamped .bak copy before the first write operation.

Notes:
- Editing large tables is limited to the first N rows shown, to keep the GUI responsive.
- Tables with unusual column names are supported by quoting SQLite identifiers.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


DEFAULT_LIMIT = 1000


def qident(name: str) -> str:
    """Quote an SQLite identifier."""
    return '"' + str(name).replace('"', '""') + '"'


def infer_converter(sqlite_type: str):
    t = (sqlite_type or "").upper()
    if "INT" in t:
        return int
    if any(k in t for k in ("REAL", "FLOA", "DOUB", "NUM", "DEC")):
        return float
    return None


def convert_value(column: str, sqlite_type: str, value: str):
    value = value.strip()
    if value == "":
        return None
    converter = infer_converter(sqlite_type)
    if converter is None:
        return value
    try:
        return converter(value)
    except ValueError as exc:
        raise ValueError(f"Invalid value for {column} ({sqlite_type}): {value!r}") from exc


class RowEditor(tk.Toplevel):
    def __init__(self, master, title: str, columns, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("560x520")
        self.minsize(480, 360)
        self.result = None
        self.columns = list(columns)
        self.vars = {}

        initial = initial or {}

        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)

        self.form.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for r, colinfo in enumerate(self.columns):
            name = colinfo["name"]
            ctype = colinfo["type"]
            ttk.Label(self.form, text=f"{name} ({ctype or 'TEXT'})").grid(
                row=r, column=0, padx=4, pady=3, sticky="e"
            )
            var = tk.StringVar(value="" if initial.get(name) is None else str(initial.get(name)))
            self.vars[name] = var
            width = 48 if len(name) < 20 else 40
            ttk.Entry(self.form, textvariable=var, width=width).grid(
                row=r, column=1, padx=4, pady=3, sticky="we"
            )

        self.form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self, padding=(8, 4, 8, 8))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="OK", command=self.ok).pack(side="right", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=4)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.transient(master)
        self.grab_set()
        self.wait_visibility()
        self.focus()

    def ok(self):
        try:
            result = {}
            for c in self.columns:
                name = c["name"]
                result[name] = convert_value(name, c["type"], self.vars[name].get())
            self.result = result
        except ValueError as exc:
            messagebox.showerror("Invalid value", str(exc), parent=self)
            return
        self.destroy()


class LibsDbEditor(tk.Tk):
    def __init__(self, db_path=None):
        super().__init__()
        self.title("LIBS.db editor")
        self.geometry("1280x720")
        self.minsize(980, 520)

        self.db_path = None
        self.conn = None
        self.tables = []
        self.columns = []
        self._backup_done = False

        self._build_ui()

        if db_path:
            self.open_database(Path(db_path))
        else:
            for candidate in (Path.cwd() / "LIBS.db", Path.cwd() / "LIBS(3).db"):
                if candidate.exists():
                    self.open_database(candidate)
                    break

    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")

        ttk.Button(top, text="Open DB", command=self.ask_open_database).pack(side="left")
        ttk.Label(top, text="Table").pack(side="left", padx=(12, 3))
        self.table_var = tk.StringVar()
        self.table_combo = ttk.Combobox(top, textvariable=self.table_var, width=22, state="readonly")
        self.table_combo.pack(side="left")
        self.table_combo.bind("<<ComboboxSelected>>", lambda _e: self.load_table())

        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="left", padx=(8, 3))
        ttk.Button(top, text="Add", command=self.add_row).pack(side="left", padx=(14, 3))
        ttk.Button(top, text="Edit selected", command=self.edit_selected).pack(side="left", padx=3)
        ttk.Button(top, text="Delete selected", command=self.delete_selected).pack(side="left", padx=3)

        filter_frame = ttk.Frame(self, padding=(6, 0, 6, 4))
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="Filter column").pack(side="left")
        self.filter_col_var = tk.StringVar()
        self.filter_col_combo = ttk.Combobox(filter_frame, textvariable=self.filter_col_var, width=18, state="readonly")
        self.filter_col_combo.pack(side="left", padx=3)

        ttk.Label(filter_frame, text="contains / =").pack(side="left", padx=(8, 3))
        self.filter_value_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_value_var, width=22).pack(side="left")

        ttk.Label(filter_frame, text="λ min").pack(side="left", padx=(16, 3))
        self.wmin_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.wmin_var, width=9).pack(side="left")

        ttk.Label(filter_frame, text="λ max").pack(side="left", padx=(8, 3))
        self.wmax_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.wmax_var, width=9).pack(side="left")

        ttk.Label(filter_frame, text="Limit").pack(side="left", padx=(16, 3))
        self.limit_var = tk.StringVar(value=str(DEFAULT_LIMIT))
        ttk.Entry(filter_frame, textvariable=self.limit_var, width=8).pack(side="left")

        ttk.Button(filter_frame, text="Search", command=self.refresh).pack(side="left", padx=8)
        ttk.Button(filter_frame, text="Clear filters", command=self.clear_filters).pack(side="left")

        self.status_var = tk.StringVar(value="Open a LIBS.db file.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=8, pady=(0, 4))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(container, show="headings")
        yscroll = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

    def ask_open_database(self):
        filename = filedialog.askopenfilename(
            title="Open LIBS SQLite database",
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
            tables = [
                r["name"]
                for r in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                      AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()
            ]
        except Exception as exc:
            messagebox.showerror("Open DB", str(exc), parent=self)
            return

        if self.conn is not None:
            self.conn.close()

        self.db_path = path
        self.conn = conn
        self.tables = tables
        self._backup_done = False

        self.table_combo.configure(values=self.tables)
        if "Datalibs" in self.tables:
            self.table_var.set("Datalibs")
        elif self.tables:
            self.table_var.set(self.tables[0])
        else:
            self.table_var.set("")

        self.load_table()

    def _ensure_open(self):
        if self.conn is None or self.db_path is None:
            messagebox.showinfo("Database", "Open a database first.", parent=self)
            return False
        return True

    def _current_table(self):
        table = self.table_var.get().strip()
        if not table:
            return None
        if table not in self.tables:
            messagebox.showerror("Table", f"Unknown table: {table}", parent=self)
            return None
        return table

    def _make_backup_once(self):
        if self._backup_done or self.db_path is None:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = self.db_path.with_suffix(self.db_path.suffix + f".bak_{stamp}")
        shutil.copy2(self.db_path, backup)
        self._backup_done = True
        self.status_var.set(f"Backup created: {backup.name}")

    def load_table(self):
        if not self._ensure_open():
            return
        table = self._current_table()
        if table is None:
            return

        rows = self.conn.execute(f"PRAGMA table_info({qident(table)})").fetchall()
        self.columns = [
            {
                "cid": r["cid"],
                "name": r["name"],
                "type": r["type"],
                "notnull": r["notnull"],
                "pk": r["pk"],
            }
            for r in rows
        ]

        values = [""] + [c["name"] for c in self.columns]
        self.filter_col_combo.configure(values=values)
        self.filter_col_var.set("specie" if any(c["name"] == "specie" for c in self.columns) else values[0])

        self.refresh()

    def _row_count(self, table):
        try:
            return self.conn.execute(f"SELECT COUNT(*) FROM {qident(table)}").fetchone()[0]
        except Exception:
            return None

    def _limit(self):
        try:
            return max(1, int(self.limit_var.get().strip() or DEFAULT_LIMIT))
        except ValueError:
            raise ValueError("Limit must be an integer.")

    def _where_clause(self):
        where = []
        params = []

        col = self.filter_col_var.get().strip()
        value = self.filter_value_var.get().strip()
        colnames = [c["name"] for c in self.columns]
        colinfo = {c["name"]: c for c in self.columns}

        if col and value:
            if col not in colnames:
                raise ValueError(f"Unknown filter column: {col}")
            converter = infer_converter(colinfo[col]["type"])
            if converter is None:
                where.append(f"{qident(col)} LIKE ?")
                params.append(f"%{value}%")
            else:
                where.append(f"{qident(col)} = ?")
                params.append(convert_value(col, colinfo[col]["type"], value))

        # Optional wavelength range if the table has wavelen or Wavelength.
        wavelen_col = None
        for candidate in ("wavelen", "Wavelength", "lambda", "Lambda"):
            if candidate in colnames:
                wavelen_col = candidate
                break

        if wavelen_col is not None:
            wmin = self.wmin_var.get().strip()
            wmax = self.wmax_var.get().strip()
            if wmin:
                where.append(f"{qident(wavelen_col)} >= ?")
                params.append(float(wmin))
            if wmax:
                where.append(f"{qident(wavelen_col)} <= ?")
                params.append(float(wmax))

        return (" AND ".join(where), params)

    def _order_clause(self):
        colnames = [c["name"] for c in self.columns]
        if "wavelen" in colnames:
            return " ORDER BY wavelen"
        if "Wavelength" in colnames:
            return " ORDER BY Wavelength"
        if "element" in colnames:
            return " ORDER BY element"
        if "specie" in colnames:
            return " ORDER BY specie"
        return " ORDER BY rowid"

    def refresh(self):
        if not self._ensure_open():
            return
        table = self._current_table()
        if table is None:
            return
        try:
            limit = self._limit()
            clause, params = self._where_clause()
            select_cols = ", ".join(qident(c["name"]) for c in self.columns)
            sql = f"SELECT rowid, {select_cols} FROM {qident(table)}"
            if clause:
                sql += " WHERE " + clause
            sql += self._order_clause()
            sql += " LIMIT ?"
            rows = self.conn.execute(sql, params + [limit]).fetchall()
        except Exception as exc:
            messagebox.showerror("Search", str(exc), parent=self)
            return

        display_columns = ["rowid"] + [c["name"] for c in self.columns]
        self.tree.configure(columns=display_columns)
        for col in display_columns:
            self.tree.heading(col, text=col)
            width = 80
            if col in ("rowid", "ion", "gi", "gk", "acc"):
                width = 70
            elif col in ("wavelen", "Wavelength", "Ei", "Ek", "Aki"):
                width = 110
            elif len(col) > 12:
                width = 140
            self.tree.column(col, width=width, anchor="center")

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            values = [row["rowid"]] + [row[c["name"]] for c in self.columns]
            self.tree.insert("", "end", iid=str(row["rowid"]), values=values)

        total = self._row_count(table)
        total_msg = f" / {total}" if total is not None else ""
        self.status_var.set(f"{self.db_path} — table {table}: {len(rows)}{total_msg} row(s) shown")

    def clear_filters(self):
        self.filter_col_var.set("")
        self.filter_value_var.set("")
        self.wmin_var.set("")
        self.wmax_var.set("")
        self.refresh()

    def _selected_rowid(self):
        item = self.tree.focus()
        if not item:
            messagebox.showinfo("Selection", "Select a row first.", parent=self)
            return None
        return int(item)

    def _row_by_id(self, table, rowid):
        select_cols = ", ".join(qident(c["name"]) for c in self.columns)
        return self.conn.execute(
            f"SELECT rowid, {select_cols} FROM {qident(table)} WHERE rowid = ?",
            (rowid,),
        ).fetchone()

    def add_row(self):
        if not self._ensure_open():
            return
        table = self._current_table()
        if table is None:
            return

        dialog = RowEditor(self, f"Add row to {table}", self.columns)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            self._make_backup_once()
            colnames = [c["name"] for c in self.columns]
            cols_sql = ", ".join(qident(c) for c in colnames)
            placeholders = ", ".join("?" for _ in colnames)
            values = [dialog.result[c] for c in colnames]
            self.conn.execute(
                f"INSERT INTO {qident(table)} ({cols_sql}) VALUES ({placeholders})",
                values,
            )
            self.conn.commit()
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Add row", str(exc), parent=self)

    def edit_selected(self):
        if not self._ensure_open():
            return
        table = self._current_table()
        if table is None:
            return
        rowid = self._selected_rowid()
        if rowid is None:
            return

        row = self._row_by_id(table, rowid)
        if row is None:
            messagebox.showerror("Edit row", "Selected row no longer exists.", parent=self)
            self.refresh()
            return

        initial = {c["name"]: row[c["name"]] for c in self.columns}
        dialog = RowEditor(self, f"Edit {table} row {rowid}", self.columns, initial)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            self._make_backup_once()
            colnames = [c["name"] for c in self.columns]
            assignments = ", ".join(f"{qident(c)} = ?" for c in colnames)
            values = [dialog.result[c] for c in colnames] + [rowid]
            self.conn.execute(
                f"UPDATE {qident(table)} SET {assignments} WHERE rowid = ?",
                values,
            )
            self.conn.commit()
            self.refresh()
            if str(rowid) in self.tree.get_children():
                self.tree.selection_set(str(rowid))
                self.tree.focus(str(rowid))
        except Exception as exc:
            messagebox.showerror("Edit row", str(exc), parent=self)

    def delete_selected(self):
        if not self._ensure_open():
            return
        table = self._current_table()
        if table is None:
            return
        rowid = self._selected_rowid()
        if rowid is None:
            return

        row = self._row_by_id(table, rowid)
        if row is None:
            self.refresh()
            return

        preview_parts = []
        for key in ("specie", "element", "ion", "wavelen", "Wavelength"):
            if key in row.keys():
                preview_parts.append(f"{key}={row[key]}")
        preview = ", ".join(preview_parts) if preview_parts else f"rowid={rowid}"

        ok = messagebox.askyesno(
            "Delete row",
            f"Delete selected row from {table}?\n\n{preview}",
            parent=self,
        )
        if not ok:
            return

        try:
            self._make_backup_once()
            self.conn.execute(f"DELETE FROM {qident(table)} WHERE rowid = ?", (rowid,))
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
    app = LibsDbEditor(db_path)
    app.mainloop()


if __name__ == "__main__":
    main()
