"""Export of plots and plotted data (Saha-Boltzmann and CF-LIBS windows)."""

from __future__ import annotations

import csv
import math
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

from pylibs.gui.helpers import _showerror, _showinfo, center_window

FIG_FORMATS = ("png", "pdf", "svg", "eps", "tiff")


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, float):
        if not math.isfinite(v):
            return ""
        return float(f"{v:.8g}")
    return v


def write_csv(path: Path, headers, rows, ptbr: bool = False):
    with open(path, "w", newline="", encoding="utf-8-sig" if ptbr else "utf-8") as fh:
        w = csv.writer(fh, delimiter=";" if ptbr else ",")
        w.writerow(headers)
        for r in rows:
            out = []
            for v in r:
                v = _cell(v)
                if ptbr and isinstance(v, float):
                    v = repr(v).replace(".", ",")
                out.append(v)
            w.writerow(out)


def write_xlsx(path: Path, tables: dict):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)
    for name, (headers, rows) in tables.items():
        ws = wb.create_sheet(title=name[:31])
        ws.append(list(headers))
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([_cell(v) for v in r])
        for i, h in enumerate(headers, start=1):
            width = max([len(str(h))] + [len(str(_cell(r[i - 1]))) for r in rows[:200] if i - 1 < len(r)])
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(max(10, width + 2), 45)
        ws.freeze_panes = "A2"
    wb.save(path)


class ExportDialog(tk.Toplevel):
    """Generic export dialog: figure + tables {name: (headers, rows)}."""

    def __init__(self, master, title: str, figure, tables_provider, default_name: str, workdir: str = ""):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.figure = figure
        self.tables_provider = tables_provider
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        self.v_fig = tk.BooleanVar(value=figure is not None)
        self.v_fmt = tk.StringVar(value="png")
        self.v_dpi = tk.StringVar(value="300")
        self.v_csv = tk.BooleanVar(value=True)
        self.v_xlsx = tk.BooleanVar(value=True)
        self.v_ptbr = tk.BooleanVar(value=False)
        self.v_dir = tk.StringVar(value=workdir or str(Path.home()))
        self.v_name = tk.StringVar(value=default_name)

        r = 0
        ttk.Label(frm, text="Folder").grid(row=r, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(frm, textvariable=self.v_dir, width=46).grid(row=r, column=1, columnspan=3, sticky="we")
        ttk.Button(frm, text="...", width=3, command=self._pick_dir).grid(row=r, column=4, padx=3)
        r += 1
        ttk.Label(frm, text="Base name").grid(row=r, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(frm, textvariable=self.v_name, width=46).grid(row=r, column=1, columnspan=3, sticky="we")
        r += 1
        ttk.Separator(frm).grid(row=r, column=0, columnspan=5, sticky="we", pady=6)
        r += 1
        cb = ttk.Checkbutton(frm, text="Figure (as shown)", variable=self.v_fig)
        cb.grid(row=r, column=0, columnspan=2, sticky="w")
        if figure is None:
            cb.state(["disabled"])
        ttk.Combobox(frm, textvariable=self.v_fmt, values=FIG_FORMATS, width=6, state="readonly").grid(row=r, column=2, sticky="w")
        ttk.Label(frm, text="dpi").grid(row=r, column=3, sticky="e")
        ttk.Entry(frm, textvariable=self.v_dpi, width=6).grid(row=r, column=4, sticky="w")
        r += 1
        ttk.Checkbutton(frm, text="Data as CSV files (points, fits, info)", variable=self.v_csv).grid(row=r, column=0, columnspan=5, sticky="w")
        r += 1
        ttk.Checkbutton(frm, text="    CSV for Excel in Portuguese (';' separator, decimal comma)",
                        variable=self.v_ptbr).grid(row=r, column=0, columnspan=5, sticky="w")
        r += 1
        cbx = ttk.Checkbutton(frm, text="Excel workbook (.xlsx, one sheet per table)", variable=self.v_xlsx)
        cbx.grid(row=r, column=0, columnspan=5, sticky="w")
        try:
            import openpyxl  # noqa: F401
        except Exception:
            self.v_xlsx.set(False)
            cbx.state(["disabled"])
        r += 1
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=5, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Export", command=self.export).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")
        center_window(self, master)
        self.transient(master)
        self.grab_set()

    def _pick_dir(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.v_dir.get() or None)
        if d:
            self.v_dir.set(d)

    def export(self):
        try:
            folder = Path(self.v_dir.get().strip())
            folder.mkdir(parents=True, exist_ok=True)
            base = self.v_name.get().strip() or "export"
            written = []
            if self.v_fig.get() and self.figure is not None:
                fmt = self.v_fmt.get()
                p = folder / f"{base}.{fmt}"
                self.figure.savefig(p, dpi=int(float(self.v_dpi.get())), bbox_inches="tight", format=fmt)
                written.append(p.name)
            tables = self.tables_provider()
            if self.v_csv.get():
                for name, (headers, rows) in tables.items():
                    p = folder / f"{base}_{name}.csv"
                    write_csv(p, headers, rows, self.v_ptbr.get())
                    written.append(p.name)
            if self.v_xlsx.get():
                p = folder / f"{base}.xlsx"
                write_xlsx(p, tables)
                written.append(p.name)
        except Exception as e:  # noqa: BLE001
            _showerror(self, "Export", str(e))
            return
        _showinfo(self, "Export", f"Saved in {folder}:\n" + "\n".join(written))
        self.destroy()


def info_rows(app, extra: list) -> tuple:
    sp = (getattr(app, "spectra", None) or [None])[0]
    rows = [
        ["Date/time", datetime.now().isoformat(timespec="seconds")],
        ["Spectrum", getattr(sp, "filename", "") or getattr(sp, "name", "") if sp else ""],
        ["Self-absorption correction applied", "yes" if getattr(app, "apply_sac_correction", False) else "no"],
    ]
    return ["Field", "Value"], rows + extra
