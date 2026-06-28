"""Small standalone dialogs for pyLIBS."""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from pylibs.gui.helpers import _showerror, _showinfo, center_window, restore_lift_focus, show_existing_or_create
from pylibs.utils.constants import APP_NAME, APP_VERSION
from pylibs.utils.paths import manual_path


def _fit_toplevel_to_content(win, min_width=0, min_height=0, max_width_fraction=0.90, max_height_fraction=0.85):
    """Shrink oversized toplevels to requested content without exceeding screen bounds."""
    try:
        win.update_idletasks()
        req_w = max(int(min_width or 0), win.winfo_reqwidth())
        req_h = max(int(min_height or 0), win.winfo_reqheight())
        max_w = max(1, int(win.winfo_screenwidth() * max_width_fraction))
        max_h = max(1, int(win.winfo_screenheight() * max_height_fraction))
        width = min(req_w, max_w)
        height = min(req_h, max_h)
        win.minsize(max(1, min(req_w, max_w)), max(1, min(req_h, max_h)))
        win.geometry(f"{width}x{height}")
    except Exception:
        pass


def _population_statistics(values):
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance <= 0:
        return {
            "Min": min(values),
            "Max": max(values),
            "Average": mean,
            "Variance": variance,
            "Skewness": 0.0,
            "Kurtosis": 0.0,
        }
    sigma = math.sqrt(variance)
    skewness = sum(((v - mean) / sigma) ** 3 for v in values) / n
    kurtosis = sum(((v - mean) / sigma) ** 4 for v in values) / n
    return {
        "Min": min(values),
        "Max": max(values),
        "Average": mean,
        "Variance": variance,
        "Skewness": skewness,
        "Kurtosis": kurtosis,
    }


class SpectrumStatisticsWindow(tk.Toplevel):
    """Historical LIBS++ Statistics window for the main spectrum."""

    rows = ("Min", "Max", "Average", "Variance", "Skewness", "Kurtosis")

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Statistics")
        self.resizable(False, False)

        sp = master.spectra[0]
        n = min(len(sp.x), len(sp.y))
        xstats = _population_statistics(list(sp.x[:n]))
        ystats = _population_statistics(list(sp.y[:n]))

        frame = ttk.Frame(self, padding=(14, 12))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="").grid(row=0, column=0, padx=8, pady=(0, 6))
        ttk.Label(frame, text="X", anchor="center").grid(row=0, column=1, padx=16, pady=(0, 6), sticky="ew")
        ttk.Label(frame, text="Y", anchor="center").grid(row=0, column=2, padx=16, pady=(0, 6), sticky="ew")
        for row, label in enumerate(self.rows, start=1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=3)
            ttk.Label(frame, text=self._fmt(xstats[label]), anchor="e").grid(row=row, column=1, sticky="e", padx=16, pady=3)
            ttk.Label(frame, text=self._fmt(ystats[label]), anchor="e").grid(row=row, column=2, sticky="e", padx=16, pady=3)
        ttk.Label(frame, text=f"Number of points: {n}").grid(row=len(self.rows) + 1, column=0, columnspan=3, sticky="w", padx=8, pady=(12, 4))
        ttk.Button(frame, text="Close", command=self.destroy).grid(row=len(self.rows) + 2, column=0, columnspan=3, pady=(8, 0))
        _fit_toplevel_to_content(self)

    def _fmt(self, value):
        return f"{value:.6g}"


def show_statistics(master):
    if not master.spectra or not master.spectra[0].x or not master.spectra[0].y:
        _showinfo(master, "Statistics", "Load a spectrum before opening Statistics.")
        return None
    return show_existing_or_create(master, "statistics_window", lambda: SpectrumStatisticsWindow(master), parent=master)


def show_manual(master):
    manual = manual_path()
    if not manual.exists():
        _showinfo(master, "Manual", f"Manual not found:\n{manual}")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(manual))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(manual)])
        else:
            subprocess.Popen(["xdg-open", str(manual)])
    except Exception as exc:
        _showerror(master, "Manual", f"Could not open the manual:\n{exc}")


def show_about(master):
    win = show_existing_or_create(master, "about_window", lambda: tk.Toplevel(master), parent=master, center=False)
    win.title(f"About {APP_NAME}")
    win.resizable(False, False)
    win.transient(master)
    for child in win.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass

    body = ttk.Frame(win, padding=(28, 26))
    body.pack(fill="both", expand=True)

    text_font = ("TkDefaultFont", 11)
    ttk.Label(body, text=APP_NAME, font=text_font, anchor="center").pack(fill="x", pady=(0, 8))
    ttk.Label(body, text="Python Laser-Induced Breakdown Spectroscopy", font=text_font, anchor="center").pack(fill="x", pady=(0, 10))
    ttk.Label(body, text=f"Version {APP_VERSION}", font=text_font, anchor="center").pack(fill="x", pady=(0, 12))
    ttk.Label(body, text="Originally developed as LIBS++ by Vincenzo Palleschi and coworkers", font=text_font, anchor="center", justify="center", wraplength=520).pack(fill="x", pady=(0, 12))
    ttk.Label(
        body,
        text="© 2026 Vincenzo Palleschi. Licensed under CC BY-NC 4.0 for non-commercial use with attribution.",
        font=text_font,
        anchor="center",
    ).pack(fill="x")
    ttk.Button(body, text="OK", command=win.destroy).pack(pady=(22, 0))

    if not getattr(win, "_about_centered_once", False):
        center_window(win, master)
        win._about_centered_once = True
    restore_lift_focus(win, master)


class GoToWindow(tk.Toplevel):
    """Small LIBS++-style Utilities/GoTo dialog.

    The typed wavelength becomes the centre of the main window.  The displayed
    interval is center +/- 3*Delta min.
    """

    common_lines = (
        "H I 6562.8",
        "H I 4861.3",
        "C I 2478.6",
        "N I 7468.3",
        "O I 7771.9",
        "Na I 5890.0",
        "Mg I 2852.1",
        "Al I 3961.5",
        "Si I 2881.6",
        "Ca II 3933.7",
        "Ca II 3968.5",
        "Fe I 2483.3",
        "Fe I 3581.2",
        "Cu I 3247.5",
        "Cu I 3274.0",
        "Zn I 2138.6",
        "Pb I 4057.8",
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("GoTo...")
        self.resizable(False, False)
        ttk.Label(self, text="Common line:").grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 2), sticky="w")
        self.line_var = tk.StringVar(value="")
        line_box = ttk.Combobox(self, textvariable=self.line_var, values=self.common_lines, state="readonly", width=24)
        line_box.grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky="ew")
        line_box.bind("<<ComboboxSelected>>", self.select_common_line)
        ttk.Label(self, text="Central wavelength (Angstrom):").grid(row=2, column=0, columnspan=2, padx=10, pady=(8, 2), sticky="w")
        self.wave_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.wave_var, width=18).grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="ew")
        ttk.Button(self, text="OK", command=self.go).grid(row=4, column=0, padx=10, pady=10)
        ttk.Button(self, text="Cancel", command=self.destroy).grid(row=4, column=1, padx=10, pady=10)
        self.bind("<Return>", lambda e: self.go())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(app)
        self.grab_set()
        self.wave_var.set("")
        _fit_toplevel_to_content(self)
        center_window(self, app)
        self.after(50, lambda: self.focus_force())

    def select_common_line(self, _event=None):
        parts = self.line_var.get().split()
        if parts:
            self.wave_var.set(parts[-1])

    def go(self):
        try:
            wave = float(self.wave_var.get().replace(",", "."))
        except Exception:
            _showerror(self, "GoTo", "Insert a valid wavelength.")
            return
        self.app.goto_wavelength(wave)
        self.destroy()


def show_goto_dialog(master):
    return GoToWindow(master)
