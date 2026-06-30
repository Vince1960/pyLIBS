#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyLIBS Python ver. 1.0.2
Originally developed as LIBS++ by Vincenzo Palleschi and coworkers,
© 2026 Vincenzo Palleschi. Licensed under CC BY-NC 4.0 for non-commercial use with attribution

"""

from __future__ import annotations

import csv
from bisect import bisect_right
from datetime import datetime
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import threading
from collections import defaultdict
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, ttk, colorchooser, simpledialog
from typing import Optional

from pylibs.core.models import AtomicLine, TemplateLine
from pylibs.db.libs_database import LibsDatabase
from pylibs.io.ini import load_pylibs_ini, load_window_positions as load_window_positions_from_ini, save_pylibs_ini
from pylibs.io.report_io import (
    build_cflibs_report_html as _build_cflibs_report_html,
    build_cflibs_report_text as _build_cflibs_report_text,
    export_spectrum_png as _export_spectrum_png,
    definition_table as _report_definition_table,
    ensure_report_temp_dir as _report_ensure_temp_dir,
    halpha_section_html as _report_halpha_section_html,
    html_table as _report_html_table,
    plasma_parameter_rows as _report_plasma_parameter_rows,
    report_temp_path as _report_temp_path,
    response_info as _report_response_info,
    result_rows as _report_result_rows,
    saha_rows as _report_saha_rows,
    saha_section_html as _report_saha_section_html,
    spectrum_info as _report_spectrum_info,
    template_rows as _report_template_rows,
    _fmt as _report_fmt,
    _fmt3 as _report_fmt3,
    _ne_source as _report_ne_source,
    _temperature_source as _report_temperature_source,
    _finite_values as _report_finite_values,
    open_file_with_default_app as _open_file_with_default_app,
    write_report_content as _write_report_content,
    write_temp_cflibs_report as _write_temp_cflibs_report,
)
from pylibs.io.template_io import save_template_lines
from pylibs.io.spectrum_io import (
    SPECTRUM_FILETYPES,
    load_spectrum_for_open as _load_spectrum_for_open,
    read_ascii_spectrum,
    read_roh_spectrum,
    write_ascii_spectrum,
)
from pylibs.gui.icons import get_cached_menu_icon
from pylibs.gui.toolbar import build_retro_toolbar
from pylibs.gui.helpers import (
    _prepare_messagebox_parent,
    center_window,
    legacy_geometry_to_tk,
    _askyesno,
    _showerror,
    _showinfo,
    _showwarning,
    restore_lift_focus,
    show_existing_or_create,
)
from pylibs.gui.simple_dialogs import (
    show_about,
    show_goto_dialog,
    show_manual,
    show_statistics,
)
from pylibs.utils.constants import (
    APP_TITLE,
    SPLASH_DURATION_MS,
    SPLASH_SECONDS,
    APP_VERSION,
)
from pylibs.utils.formatting import (
    format_template_display_value,
    safe_float,
    safe_int,
)
from pylibs.utils.paths import (
    app_base_dir,
    resource_path,
)

try:
    import numpy as np
except Exception:
    np = None

try:
    from scipy.signal import find_peaks as scipy_find_peaks
    from scipy.signal import savgol_filter
except Exception:
    scipy_find_peaks = None
    savgol_filter = None

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.colors import to_hex as _matplotlib_to_hex
    from matplotlib.figure import Figure
except Exception:
    Figure = None
    FigureCanvasTkAgg = None
    _matplotlib_to_hex = None


@dataclass
class AppOptions:
    username: str = ""
    limit_low: float = 2000.0
    limit_high: float = 10000.0
    threshold: float = 1.0
    delta_min: float = 1.0
    search_range: float = 1.0
    apply_response: bool = False
    apply_before: bool = False
    apply_after: bool = True
    response_file: str = ""
    libs_db_file: str = "LIBS.db"
    single_file_correction: bool = False
    single_file_path: str = ""
    instrumental_width: float = 0.5
    fix_wg: bool = False
    fixed_wg: float = 0.5
    fix_wl: bool = False
    fixed_wl: float = 0.5
    aki_threshold: float = 0.0
    ne_low: float = 1e15
    ne_high: float = 1e18
    kt_low: float = 0.5
    kt_high: float = 3.0
    show_progress: bool = True
    fix_wavelength: bool = False
    convert_to_angstrom: bool = False
    iterations: int = 20
    auto_offset: bool = False
    auto_shift: float = 0.0
    ha_lines: int = 1
    ha_range: float = 150.0
    ha_wl1: float = 6565.0
    ha_wl2: float = 6490.0
    ha_dl1: float = 40.0
    ha_dl2: float = 50.0
    ha_kt: float = 1.0
    echelle: bool = False
    input_dir: str = ""
    view_grid_x: bool = True
    view_grid_y: bool = True
    view_log_x: bool = False
    view_log_y: bool = False
    background_color: str = "#ffffff"
    ini_file: str = "pyLIBS.ini"
    window_positions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# pyLIBS v8.3 resource / ini / splash helpers
# ---------------------------------------------------------------------------

def remembered_initial_dir(options=None) -> str:
    """Return the last working directory stored in pyLIBS.ini, if valid."""
    try:
        d = getattr(options, "input_dir", "") if options is not None else ""
        if d and Path(d).exists():
            return str(Path(d))
    except Exception:
        pass
    return str(app_base_dir())


def remember_working_dir(options, filename_or_files) -> None:
    """Update options.input_dir from an opened/saved filename or filename list."""
    if options is None or not filename_or_files:
        return
    try:
        if isinstance(filename_or_files, (list, tuple)):
            if not filename_or_files:
                return
            filename_or_files = filename_or_files[0]
        parent = Path(str(filename_or_files)).expanduser().resolve().parent
        if parent.exists():
            options.input_dir = str(parent)
    except Exception:
        pass

def show_startup_splash(root, seconds: float = SPLASH_SECONDS):
    """Show pyLIBS splash for a few seconds before the main window is displayed."""
    img_path = resource_path("pyLIBS_splash.png")
    if not img_path.exists():
        return None
    splash_win = tk.Toplevel(root)
    splash_win.overrideredirect(True)
    splash_win.configure(bg="black")
    splash_win.attributes("-topmost", True)
    try:
        photo = tk.PhotoImage(file=str(img_path))
    except Exception:
        return None
    label = tk.Label(splash_win, image=photo, bd=0, bg="black")
    label.image = photo
    label.pack()
    splash_win.update_idletasks()
    sw = splash_win.winfo_screenwidth()
    sh = splash_win.winfo_screenheight()
    ww = splash_win.winfo_reqwidth()
    wh = splash_win.winfo_reqheight()
    splash_win.geometry(f"{ww}x{wh}+{max(0,(sw-ww)//2)}+{max(0,(sh-wh)//2)}")
    splash_win.after(int(seconds * 1000), splash_win.destroy)
    return splash_win


# ---------------------------------------------------------------------------
# pyLIBS v8.3 Retro GUI helpers
# ---------------------------------------------------------------------------

RETRO_BG = "#d4d0c8"
RETRO_PANEL = "#ece9d8"
RETRO_FREE = "#c0dcc0"   # close to Borland clMoneyGreen
RETRO_FIXED = "#ff7070"  # fixed parameters, original visual cue was red


def configure_retro_style(root):
    """Approximate the original Windows/Borland visual style using ttk."""
    try:
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", font=("MS Sans Serif", 8))
        style.configure("TFrame", background=RETRO_BG)
        style.configure("TLabel", background=RETRO_BG)
        style.configure("TLabelframe", background=RETRO_BG)
        style.configure("TLabelframe.Label", background=RETRO_BG)
        style.configure("TButton", padding=(5, 1))
        style.configure("Treeview", font=("MS Sans Serif", 8), rowheight=18)
        style.configure("Treeview.Heading", font=("MS Sans Serif", 8, "bold"))
    except Exception:
        pass


def _main_window_status_text():
    return "pyLIBS Software for Spectral Analysis  |  Open a file to start"


def _menu_separator(menu):
    try:
        menu.add_separator()
    except Exception:
        pass


@dataclass
class Spectrum:
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    name: str = "Spectrum"
    filename: str = ""
    visible: bool = True
    color: Optional[str] = None
    response_corrected: bool = False

    @classmethod
    def from_ascii(cls, filename: str, convert_nm_to_a: bool = False, name: Optional[str] = None) -> "Spectrum":
        xs, ys = read_ascii_spectrum(filename, convert_nm_to_a)
        return cls(xs, ys, name or Path(filename).name, filename)

    @classmethod
    def from_roh(cls, filename: str, convert_nm_to_a: bool = False, limit_low: Optional[float] = None, limit_high: Optional[float] = None, name: Optional[str] = None) -> "Spectrum":
        xs, ys = read_roh_spectrum(filename, convert_nm_to_a, limit_low, limit_high)
        return cls(xs, ys, name or Path(filename).name, filename)

    def save_ascii(self, filename: str):
        write_ascii_spectrum(filename, self.x, self.y)

    def smooth(self, window: int = 11, polyorder: int = 4):
        if len(self.y) < 3:
            return
        if window % 2 == 0:
            window += 1
        window = max(3, min(window, len(self.y) - (1 - len(self.y) % 2)))
        if savgol_filter is not None and np is not None and len(self.y) > window:
            self.y = savgol_filter(np.asarray(self.y), window, min(polyorder, window - 1)).tolist()
        else:
            half = window // 2
            self.y = [sum(self.y[max(0, i-half):min(len(self.y), i+half+1)]) / (min(len(self.y), i+half+1)-max(0, i-half)) for i in range(len(self.y))]

    def apply_response(self, response: Optional["ResponseCurve"]):
        if self.response_corrected or response is None or not response.x:
            return
        response_values = response.values_at(self.x)
        if np is not None:
            yy = np.asarray(self.y, dtype=float)
            rv = np.asarray(response_values, dtype=float)
            corrected = yy.copy()
            valid = np.isfinite(rv) & (rv != 0.0)
            corrected[valid] = yy[valid] / rv[valid]
            self.y = corrected.tolist()
        else:
            corrected = []
            for xx, yy in zip(response_values, self.y):
                corrected.append(yy / xx if xx and math.isfinite(xx) else yy)
            self.y = corrected
        self.response_corrected = True

    def shifted(self, offset: float, name: str) -> "Spectrum":
        return Spectrum(list(self.x), [v + offset for v in self.y], name=name)

    def scaled(self, factor: float, name: str) -> "Spectrum":
        return Spectrum(list(self.x), [v * factor for v in self.y], name=name)


LIBS_SPECTRUM_COLORS = ["black", "red", "blue", "green", "magenta", "cyan", "orange", "brown"]


def default_spectrum_color(index: int) -> str:
    if index < len(LIBS_SPECTRUM_COLORS):
        return LIBS_SPECTRUM_COLORS[index]
    try:
        cycle = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", [])
    except Exception:
        cycle = []
    if cycle:
        return cycle[(index - len(LIBS_SPECTRUM_COLORS)) % len(cycle)]
    return LIBS_SPECTRUM_COLORS[index % len(LIBS_SPECTRUM_COLORS)]


def assign_default_spectrum_color(sp: Spectrum, index: int) -> Spectrum:
    if not getattr(sp, "color", None):
        sp.color = default_spectrum_color(index)
    return sp


def _interp_spectrum_value(points: list[tuple[float, float]], wavelength: float) -> float:
    if wavelength <= points[0][0]:
        return points[0][1]
    if wavelength >= points[-1][0]:
        return points[-1][1]
    for i in range(1, len(points)):
        x1, y1 = points[i]
        if wavelength <= x1:
            x0, y0 = points[i - 1]
            if x1 == x0:
                return (y0 + y1) / 2.0
            return y0 + (y1 - y0) * (wavelength - x0) / (x1 - x0)
    return points[-1][1]


def merge_spectra_by_wavelength(first: Spectrum, second: Spectrum, name: str = "Merged spectrum") -> Spectrum:
    """Merge two spectra by wavelength, averaging intensities in the overlap."""
    p1 = sorted(zip(first.x, first.y), key=lambda p: p[0])
    p2 = sorted(zip(second.x, second.y), key=lambda p: p[0])
    if not p1:
        return Spectrum([x for x, _ in p2], [y for _, y in p2], name=name, filename=second.filename)
    if not p2:
        return Spectrum([x for x, _ in p1], [y for _, y in p1], name=name, filename=first.filename)

    lo1, hi1 = p1[0][0], p1[-1][0]
    lo2, hi2 = p2[0][0], p2[-1][0]
    overlap_lo = max(lo1, lo2)
    overlap_hi = min(hi1, hi2)

    merged: list[tuple[float, float]] = []
    if overlap_lo <= overlap_hi:
        merged.extend((x, y) for x, y in p1 if x < overlap_lo or x > overlap_hi)
        merged.extend((x, y) for x, y in p2 if x < overlap_lo or x > overlap_hi)
        overlap_x = sorted({x for x, _ in p1 if overlap_lo <= x <= overlap_hi} |
                           {x for x, _ in p2 if overlap_lo <= x <= overlap_hi})
        for x in overlap_x:
            y = (_interp_spectrum_value(p1, x) + _interp_spectrum_value(p2, x)) / 2.0
            merged.append((x, y))
    else:
        merged.extend(p1)
        merged.extend(p2)

    merged.sort(key=lambda p: p[0])
    return Spectrum([x for x, _ in merged], [y for _, y in merged], name=name)


def load_spectrum_for_open(filename: str, options: AppOptions) -> Spectrum:
    return _load_spectrum_for_open(filename, options, Spectrum)


@dataclass
class ResponseCurve:
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    filename: str = ""
    _x_sorted: list[float] = field(default_factory=list, init=False, repr=False)
    _y_sorted: list[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self._prepare_cache()

    @classmethod
    def from_ascii(cls, filename: str, convert_nm_to_a: bool = False):
        sp = Spectrum.from_ascii(filename, convert_nm_to_a)
        return cls(sp.x, sp.y, filename)

    def _prepare_cache(self):
        cleaned = []
        for xx, yy in zip(self.x, self.y):
            try:
                xx = float(xx)
                yy = float(yy)
            except (TypeError, ValueError):
                continue
            if math.isfinite(xx) and math.isfinite(yy):
                cleaned.append((xx, yy))
        cleaned.sort(key=lambda p: p[0])
        if not cleaned:
            self.x = []
            self.y = []
            self._x_sorted = []
            self._y_sorted = []
            return

        x_sorted = []
        y_sorted = []
        for xx, yy in cleaned:
            if x_sorted and xx == x_sorted[-1]:
                y_sorted[-1] = yy
            else:
                x_sorted.append(xx)
                y_sorted.append(yy)
        self.x = list(x_sorted)
        self.y = list(y_sorted)
        self._x_sorted = x_sorted
        self._y_sorted = y_sorted

    def value_at(self, wavelength: float) -> float:
        if not self._x_sorted:
            return 1.0
        xs, ys = self._x_sorted, self._y_sorted
        if wavelength <= xs[0]:
            return ys[0]
        if wavelength >= xs[-1]:
            return ys[-1]
        i = bisect_right(xs, wavelength)
        x0, x1, y0, y1 = xs[i-1], xs[i], ys[i-1], ys[i]
        return y1 + (y0 - y1) / (x0 - x1) * (wavelength - x1) if x0 != x1 else y1

    def values_at(self, wavelengths: list[float]) -> list[float]:
        if not self._x_sorted:
            return [1.0 for _ in wavelengths]
        if np is not None:
            return np.interp(
                np.asarray(wavelengths, dtype=float),
                np.asarray(self._x_sorted, dtype=float),
                np.asarray(self._y_sorted, dtype=float),
                left=self._y_sorted[0],
                right=self._y_sorted[-1],
            ).tolist()
        return [self.value_at(wavelength) for wavelength in wavelengths]


class SimpleTableWindow(tk.Toplevel):
    def __init__(self, master, title, columns):
        super().__init__(master)
        self.title(title)
        self.geometry("900x480")
        self.minsize(520, 260)
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for c in columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)


def fit_toplevel_to_content(win, min_width=0, min_height=0, max_width_fraction=0.90, max_height_fraction=0.85):
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


class OptionsWindow(tk.Toplevel):
    """pyLIBS Options dialog, dynamically initialized from pyLIBS.ini.
    """

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Options")
        self.resizable(True, True)
        self.minsize(820, 360)
        geom = legacy_geometry_to_tk(getattr(master.options, "options_geometry", ""), "900x430")
        if geom:
            self.geometry(geom)
        self.vars: dict[str, tk.Variable] = {}
        self._build_original_layout()
        fit_toplevel_to_content(self, min_width=860, min_height=390)
        center_window(self, master)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def v(self, attr, default="", kind="str"):
        opts = self.master_app.options
        value = getattr(opts, attr, default)
        if kind == "bool":
            var = tk.BooleanVar(value=bool(value))
        else:
            var = tk.StringVar(value=str(value))
        self.vars[attr] = var
        return var

    def entry(self, parent, attr, row, col, width=8, default="", kind="str", **kw):
        e = ttk.Entry(parent, textvariable=self.v(attr, default, kind), width=width)
        e.grid(row=row, column=col, padx=kw.get("padx", 3), pady=kw.get("pady", 3), sticky=kw.get("sticky", "w"))
        return e

    def check(self, parent, attr, text, row, col, default=False, colspan=1):
        cb = ttk.Checkbutton(parent, text=text, variable=self.v(attr, default, "bool"))
        cb.grid(row=row, column=col, columnspan=colspan, padx=4, pady=3, sticky="w")
        return cb

    def group(self, parent, title, row, col, colspan=1, rowspan=1, sticky="nsew"):
        lf = ttk.LabelFrame(parent, text=title)
        lf.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, padx=4, pady=3, sticky=sticky)
        return lf

    def _build_original_layout(self):
        buttons = ttk.Frame(self, padding=(6, 6))
        buttons.pack(fill="x", side="bottom")
        buttons_inner = ttk.Frame(buttons)
        buttons_inner.pack(side="right")
        ttk.Button(buttons_inner, text="Save Options", command=self.save).pack(side="left", padx=4)
        ttk.Button(buttons_inner, text="OK", command=self.ok).pack(side="left", padx=4)
        ttk.Button(buttons_inner, text="Cancel", command=self.cancel).pack(side="left", padx=4)

        outer = ttk.Frame(self, padding=6)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=0)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(2, weight=0)

        left = ttk.Frame(outer)
        mid = ttk.Frame(outer)
        right = ttk.Frame(outer)
        left.grid(row=0, column=0, sticky="n", padx=(0, 6))
        mid.grid(row=0, column=1, sticky="n", padx=6)
        right.grid(row=0, column=2, sticky="n", padx=(6, 0))

        g_user = self.group(left, "Username", 0, 0)
        self.entry(g_user, "username", 0, 0, width=18)

        g_auto = self.group(left, "", 1, 0)
        self.check(g_auto, "auto_offset", "Auto Offset", 0, 0)

        g_convert = self.group(left, "", 2, 0)
        self.check(g_convert, "convert_to_angstrom", "Convert to Angstrom", 0, 0)

        g_ha = self.group(left, "Ha parameters", 3, 0)
        ttk.Label(g_ha, text="Lines").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_ha, "ha_lines", 0, 1, width=5)
        ttk.Label(g_ha, text="wl1").grid(row=0, column=2, padx=4, sticky="w")
        self.entry(g_ha, "ha_wl1", 0, 3, width=7)
        ttk.Label(g_ha, text="dl1").grid(row=0, column=4, padx=4, sticky="w")
        self.entry(g_ha, "ha_dl1", 0, 5, width=5)
        ttk.Label(g_ha, text="Delta").grid(row=1, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_ha, "ha_range", 1, 1, width=5)
        ttk.Label(g_ha, text="wl2").grid(row=1, column=2, padx=4, sticky="w")
        self.entry(g_ha, "ha_wl2", 1, 3, width=7)
        ttk.Label(g_ha, text="dl2").grid(row=1, column=4, padx=4, sticky="w")
        self.entry(g_ha, "ha_dl2", 1, 5, width=5)
        ttk.Label(g_ha, text="kT").grid(row=2, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_ha, "ha_kt", 2, 1, width=5)

        g_wave = self.group(mid, "Wavelength Limits", 0, 0)
        ttk.Label(g_wave, text="From:").grid(row=0, column=0, padx=4)
        self.entry(g_wave, "limit_low", 0, 1, width=8)
        ttk.Label(g_wave, text="To:").grid(row=0, column=2, padx=14)
        self.entry(g_wave, "limit_high", 0, 3, width=8)

        g_temp = self.group(mid, "Temperature Range", 1, 0)
        self.entry(g_temp, "kt_low", 0, 0, width=8)
        ttk.Label(g_temp, text="<  kT  <").grid(row=0, column=1, padx=14)
        self.entry(g_temp, "kt_high", 0, 2, width=8)

        g_ne = self.group(mid, "electron density Range", 2, 0)
        self.entry(g_ne, "ne_low", 0, 0, width=9)
        ttk.Label(g_ne, text="<  Ne  <").grid(row=0, column=1, padx=14)
        self.entry(g_ne, "ne_high", 0, 2, width=9)

        mid2 = ttk.Frame(mid)
        mid2.grid(row=3, column=0, sticky="ew")
        g_thr = self.group(mid2, "Threshold", 0, 0)
        self.entry(g_thr, "threshold", 0, 0, width=8)
        g_dm = self.group(mid2, "Delta min.", 1, 0)
        self.entry(g_dm, "delta_min", 0, 0, width=7)
        g_rg = self.group(mid2, "Range", 1, 1)
        self.entry(g_rg, "search_range", 0, 0, width=7)

        g_corr = self.group(mid, "Correction", 4, 0)
        self.check(g_corr, "apply_response", "Apply", 0, 0)
        self.entry(g_corr, "response_file", 0, 1, width=28)
        ttk.Button(g_corr, text="Browse...", command=self.browse_response).grid(row=0, column=2, padx=4, pady=4)

        g_global = self.group(mid, "Global Correction", 5, 0)
        ttk.Radiobutton(g_global, text="Apply Before", variable=self.v("global_correction_mode", "after"), value="before",
                        command=lambda: self._set_global_mode("before")).grid(row=0, column=0, padx=8, pady=5, sticky="w")
        ttk.Radiobutton(g_global, text="Apply After", variable=self.vars["global_correction_mode"], value="after",
                        command=lambda: self._set_global_mode("after")).grid(row=0, column=1, padx=8, pady=5, sticky="w")
        self.vars["global_correction_mode"].set("before" if self.master_app.options.apply_before else "after")

        g_fit = self.group(right, "Data Fit", 0, 0)
        self.check(g_fit, "fix_wg", "Fix wg:", 0, 0)
        self.entry(g_fit, "fixed_wg", 0, 1, width=7)
        self.check(g_fit, "fix_wl", "Fix wl:", 1, 0)
        self.entry(g_fit, "fixed_wl", 1, 1, width=7)
        self.check(g_fit, "fix_wavelength", "Fix wavelength", 2, 0, colspan=2)
        ttk.Label(g_fit, text="Iterations").grid(row=3, column=0, padx=4, sticky="w")
        self.entry(g_fit, "iterations", 3, 1, width=7)
        self.check(g_fit, "show_progress", "Show Progress", 4, 0, colspan=2)
        ttk.Label(g_fit, text="Instr. width").grid(row=5, column=0, padx=4, sticky="w")
        self.entry(g_fit, "instrumental_width", 5, 1, width=7)
        self.check(g_fit, "echelle", "Echelle", 6, 0, colspan=2)

        g_aki = self.group(right, "Aki Threshold", 1, 0)
        self.entry(g_aki, "aki_threshold", 0, 0, width=8)

        g_shift = self.group(right, "AutoShift", 2, 0)
        self.entry(g_shift, "auto_shift", 0, 0, width=8)

    def _set_global_mode(self, mode):
        self.vars["apply_before"].set(mode == "before") if "apply_before" in self.vars else None
        self.vars["apply_after"].set(mode == "after") if "apply_after" in self.vars else None

    def browse_response(self):
        initial = remembered_initial_dir(self.master_app.options)
        filename = filedialog.askopenfilename(
            title="Instrumental correction / normalization file",
            initialdir=initial,
            filetypes=[("Data files", "*.dat *.txt *.asc *.csv *.opc"), ("All", "*.*")]
        )
        if filename:
            remember_working_dir(self.master_app.options, filename)
            self.vars["response_file"].set(filename)

    def apply_to_options(self):
        opts = self.master_app.options
        # explicit mode
        mode = self.vars.get("global_correction_mode")
        if mode is not None:
            opts.apply_before = (mode.get() == "before")
            opts.apply_after = (mode.get() == "after")
        for attr, var in self.vars.items():
            if attr == "global_correction_mode":
                continue
            if not hasattr(opts, attr):
                continue
            cur = getattr(opts, attr)
            if isinstance(cur, bool):
                setattr(opts, attr, bool(var.get()))
            elif isinstance(cur, int):
                setattr(opts, attr, safe_int(var.get(), cur))
            elif isinstance(cur, float):
                setattr(opts, attr, safe_float(var.get(), cur))
            else:
                setattr(opts, attr, str(var.get()))
        # keep DB beside executable if available
        dbp = resource_path("LIBS.db")
        if dbp.exists():
            opts.libs_db_file = str(dbp)
            self.master_app.libs_db.filename = str(dbp)

    def ok(self):
        old_response_file = getattr(self.master_app.options, "response_file", "")
        self.apply_to_options()
        self.reload_response_if_changed(old_response_file)
        self.master_app.status("Options updated")
        self.close()

    def cancel(self):
        self.close()

    def close(self):
        if getattr(self.master_app, "options_window", None) is self:
            self.master_app.options_window = None
        self.destroy()

    def save(self):
        old_response_file = getattr(self.master_app.options, "response_file", "")
        self.apply_to_options()
        self.reload_response_if_changed(old_response_file)
        path = save_pylibs_ini(self.master_app.options)
        self.master_app.status(f"Options saved: {path}")

    def reload_response_if_changed(self, old_response_file):
        if self.master_app.options.response_file != old_response_file:
            silent = not str(self.master_app.options.response_file or "").strip()
            self.master_app.load_configured_response(silent=silent)


class ActiveSpectraWindow(tk.Toplevel):
    """Gestione spettri attivi, da Unit13."""

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Active Spectra - Unit13")
        self.geometry("720x430")
        self.selected = set()
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=4)
        ttk.Label(top, text="Offset:").pack(side="left")
        self.offset_var = tk.StringVar(value="1000")
        ttk.Entry(top, textvariable=self.offset_var, width=10).pack(side="left", padx=3)
        ttk.Button(top, text="Shift copy", command=self.shift_copy).pack(side="left", padx=3)
        ttk.Label(top, text="Scale:").pack(side="left", padx=(15, 2))
        self.scale_var = tk.StringVar(value="1.0")
        ttk.Entry(top, textvariable=self.scale_var, width=10).pack(side="left", padx=3)
        ttk.Button(top, text="Scale copy", command=self.scale_copy).pack(side="left", padx=3)

        cols = ("sel", "visible", "name", "points")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.tree.bind("<Double-1>", self.toggle_visible)
        self.tree.bind("<Button-3>", self.toggle_selected)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=6, pady=4)
        ttk.Button(bottom, text="Average selected", command=self.average_selected).pack(side="left", padx=2)
        ttk.Button(bottom, text="Max selected", command=self.max_selected).pack(side="left", padx=2)
        ttk.Button(bottom, text="Min selected", command=self.min_selected).pack(side="left", padx=2)
        ttk.Button(bottom, text="Delete selected", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Button(bottom, text="Refresh", command=self.refresh).pack(side="right", padx=2)
        self.refresh()

    def refresh(self, show_message=True):
        self.tree.delete(*self.tree.get_children())
        for i, sp in enumerate(self.master_app.spectra):
            self.tree.insert("", "end", iid=str(i), values=("X" if i in self.selected else "", "yes" if sp.visible else "no", sp.name, len(sp.x)))

    def _current_index(self):
        item = self.tree.focus()
        return int(item) if item != "" else None

    def toggle_visible(self, _event=None):
        idx = self._current_index()
        if idx is None or idx == 0:
            if idx == 0:
                _showinfo(self, "Active Spectra", "The main spectrum always remains visible.")
            return
        self.master_app.spectra[idx].visible = not self.master_app.spectra[idx].visible
        self.refresh()
        self.master_app.redraw()

    def toggle_selected(self, _event=None):
        idx = self._current_index()
        if idx is None:
            return
        if idx in self.selected:
            self.selected.remove(idx)
        else:
            self.selected.add(idx)
        self.refresh()

    def _selected_spectra(self):
        return [self.master_app.spectra[i] for i in sorted(self.selected) if 0 <= i < len(self.master_app.spectra)]

    def shift_copy(self):
        idx = self._current_index()
        if idx is None:
            return
        off = safe_float(self.offset_var.get(), 0.0)
        src = self.master_app.spectra[idx]
        self.master_app.add_spectrum(src.shifted(off, f"{src.name} shifted"))
        self.refresh()

    def scale_copy(self):
        idx = self._current_index()
        if idx is None:
            return
        fac = safe_float(self.scale_var.get(), 1.0)
        src = self.master_app.spectra[idx]
        self.master_app.add_spectrum(src.scaled(fac, f"{src.name} scaled"))
        self.refresh()

    def average_selected(self):
        self.combine_selected("Average", "avg")

    def max_selected(self):
        self.combine_selected("Max", "max")

    def min_selected(self):
        self.combine_selected("Min", "min")

    def combine_selected(self, label, mode):
        specs = self._selected_spectra()
        if len(specs) < 2:
            _showinfo(self, "Active Spectra", "Select at least two spectra with right-click.")
            return
        n = min(len(s.y) for s in specs)
        x = specs[0].x[:n]
        ys = list(zip(*[s.y[:n] for s in specs]))
        if mode == "avg":
            y = [sum(row) / len(row) for row in ys]
        elif mode == "max":
            y = [max(row) for row in ys]
        else:
            y = [min(row) for row in ys]
        self.master_app.add_spectrum(Spectrum(list(x), y, label))
        self.refresh()

    def delete_selected(self):
        keep = [s for i, s in enumerate(self.master_app.spectra) if i == 0 or i not in self.selected]
        self.master_app.spectra = keep
        self.selected.clear()
        self.refresh()
        self.master_app.redraw()


class ResponseWindow(tk.Toplevel):
    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Instrument Response - Unit10/12")
        self.geometry("760x460")
        top = ttk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Button(top, text="Load response", command=master.ask_load_response).pack(side="left")
        if Figure is None:
            ttk.Label(self, text="matplotlib not available").pack(pady=30)
            self.ax = self.canvas = None
            return
        self.fig = Figure(figsize=(7,4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.redraw()

    def redraw(self):
        if not self.ax:
            return
        self.ax.clear()
        self.ax.set_xlabel("Wavelength")
        self.ax.set_ylabel("Response")
        self.ax.grid(True)
        r = self.master_app.response
        if r is not None and r.x:
            self.ax.plot(r.x, r.y, linewidth=0.9)
        self.canvas.draw_idle()


class TemplateManager(tk.Toplevel):
    columns = ("wavelen", "specie", "ion", "asswavelen", "inte", "ei", "ek", "aki", "gk", "gi", "acc", "wg", "wl", "fitwavelen")
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Template Manager - Unit6")
        self.geometry("1180x520")
        self.minsize(1040, 360)
        bar = ttk.Frame(self); bar.pack(fill="x", padx=5, pady=5)
        ttk.Button(bar, text="Load CSV", command=self.load).pack(side="left")
        ttk.Button(bar, text="Save CSV", command=self.save).pack(side="left", padx=3)
        ttk.Button(bar, text="Delete Row", command=self.delete_selected_row).pack(side="left", padx=3)
        ttk.Button(bar, text="Line Identification", command=master.show_line_identification).pack(side="left", padx=3)
        tree_frame = ttk.Frame(self)
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings")
        for c in self.columns:
            self.tree.heading(c, text=c); self.tree.column(c, width=78, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.zoom)
        self.refresh()

    def refresh(self, show_message=True):
        selected = list(self.tree.selection())
        focus = self.tree.focus()
        self.tree.delete(*self.tree.get_children())
        for i,l in enumerate(self.master_app.template_lines):
            self.tree.insert("", "end", iid=str(i), values=[format_template_display_value(getattr(l,c)) for c in self.columns])
        children = set(self.tree.get_children())
        for item in selected:
            if item in children:
                self.tree.selection_add(item)
        if focus in children:
            self.tree.focus(focus)
            self.tree.see(focus)

    def load(self):
        fn = filedialog.askopenfilename(initialdir=remembered_initial_dir(self.master_app.options), filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not fn: return
        remember_working_dir(self.master_app.options, fn)
        lines=[]
        with open(fn, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for r in reader:
                lines.append(TemplateLine(
                    wavelen=safe_float(r.get("wavelen")),
                    specie=r.get("specie",""), ion=safe_int(r.get("ion")),
                    asswavelen=safe_float(r.get("asswavelen")), inte=safe_float(r.get("inte")),
                    ei=safe_float(r.get("ei") or r.get("Ei")),
                    ek=safe_float(r.get("ek") or r.get("Ek")), aki=safe_float(r.get("aki") or r.get("Aki")),
                    gk=safe_int(r.get("gk")), gi=safe_int(r.get("gi")),
                    acc=safe_int(r.get("acc")), wg=safe_float(r.get("wg")), wl=safe_float(r.get("wl")),
                    fitwavelen=safe_float(r.get("fitwavelen"))
                ))
        self.master_app.template_lines = lines
        self.master_app.notify_template_changed(redraw=True)

    def save(self):
        fn = filedialog.asksaveasfilename(initialdir=remembered_initial_dir(self.master_app.options), defaultextension=".csv")
        if not fn: return
        remember_working_dir(self.master_app.options, fn)
        with open(fn, "w", newline="", encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(self.columns)
            for l in self.master_app.template_lines:
                w.writerow([getattr(l,c) for c in self.columns])

    def zoom(self, _=None):
        item=self.tree.focus()
        if item:
            self.master_app.zoom_around(self.master_app.template_lines[int(item)].wavelen)

    def delete_selected_row(self):
        item = self.tree.focus()
        if item == "":
            return
        idx = int(item)
        if 0 <= idx < len(self.master_app.template_lines):
            self.master_app.template_lines.pop(idx)
            self.master_app.notify_template_changed(redraw=True)


class LineIdentificationWindow(tk.Toplevel):
    columns = ("wavelen", "specie", "ion", "inte", "ei", "ek", "gi", "gk", "aki", "acc")
    def __init__(self, master):
        super().__init__(master)
        self.master_app=master
        self.title("Identifications")
        self.geometry("1020x520")
        self.minsize(940, 380)
        self.atomic_lines=[]
        self.results=[]
        top=ttk.Frame(self); top.pack(fill="x", padx=5, pady=5)
        ttk.Button(top, text="Load atomic CSV", command=self.load_db).pack(side="left")
        ttk.Button(top, text="Use LIBS.db", command=self.load_sqlite_db).pack(side="left", padx=3)
        ttk.Label(top, text="DB table").pack(side="left", padx=(8,2))
        self.db_table_var=tk.StringVar(value="Datalibs")
        ttk.Combobox(top, textvariable=self.db_table_var, width=10, values=("Datalibs","Daticerti")).pack(side="left", padx=3)
        ttk.Label(top, text="λ").pack(side="left", padx=(12,2))
        self.wave_var=tk.StringVar(); ttk.Entry(top, textvariable=self.wave_var, width=12).pack(side="left")
        ttk.Label(top, text="range").pack(side="left", padx=(8,2))
        self.range_var=tk.StringVar(value=str(master.options.search_range)); ttk.Entry(top, textvariable=self.range_var, width=8).pack(side="left")
        ttk.Button(top, text="Search", command=self.search).pack(side="left", padx=5)
        tree_frame = ttk.Frame(self)
        self.tree=ttk.Treeview(tree_frame, columns=self.columns, show="headings")
        for c in self.columns:
            self.tree.heading(c,text=c); self.tree.column(c,width=85,anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.assign)
        center_window(self, master)

    def load_db(self):
        fn=filedialog.askopenfilename(initialdir=remembered_initial_dir(self.master_app.options), filetypes=[("CSV/TXT","*.csv *.txt *.dat"),("All","*.*")])
        if not fn: return
        remember_working_dir(self.master_app.options, fn)
        lines=[]
        with open(fn, newline="", encoding="utf-8", errors="ignore") as f:
            sample=f.read(2048); f.seek(0)
            if "," in sample:
                for r in csv.DictReader(f):
                    lines.append(AtomicLine(safe_float(r.get("wavelen")), (r.get("specie") or r.get("element") or "").replace("+",""),
                                            safe_int(r.get("ion")), safe_float(r.get("inte")), safe_float(r.get("Ei") or r.get("ei")),
                                            safe_float(r.get("Ek") or r.get("ek")), safe_int(r.get("gi")), safe_int(r.get("gk")),
                                            safe_float(r.get("Aki") or r.get("aki")), safe_int(r.get("acc"))))
            else:
                for line in f:
                    p=line.split()
                    if len(p)>=3:
                        lines.append(AtomicLine(safe_float(p[0]), p[1].replace("+",""), safe_int(p[2]),
                                                safe_float(p[3]) if len(p)>3 else 0, safe_float(p[4]) if len(p)>4 else 0,
                                                safe_float(p[5]) if len(p)>5 else 0, safe_int(p[6]) if len(p)>6 else 0,
                                                safe_int(p[7]) if len(p)>7 else 0, safe_float(p[8]) if len(p)>8 else 0,
                                                safe_int(p[9]) if len(p)>9 else 0))
        self.atomic_lines=[l for l in lines if l.wavelen]
        self.populate(self.atomic_lines[:1000])
        self.master_app.atomic_lines = self.atomic_lines
        self.master_app.status(f"Atomic DB loaded: {len(self.atomic_lines)} lines")

    def load_sqlite_db(self):
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            self.master_app.libs_db.connect()
            self.atomic_lines = []  # ricerca lazy da SQLite
            self.master_app.atomic_lines = []
            self.master_app.status(f"LIBS.db active: {self.master_app.libs_db.filename}")
            _showinfo(self, "LIBS.db", "SQLite database is active. Searches will use the selected table.")
        except Exception as e:
            _showerror(self, "LIBS.db", str(e))

    def populate(self, lines):
        self.results=lines
        self.tree.delete(*self.tree.get_children())
        for i,l in enumerate(lines):
            self.tree.insert("", "end", iid=str(i), values=[getattr(l,c) for c in self.columns])

    def search(self):
        wave=safe_float(self.wave_var.get(), None)
        if wave is None:
            return
        rg=safe_float(self.range_var.get(), self.master_app.options.search_range)
        res=[]
        # Preferisci SQLite se disponibile; altrimenti usa righe CSV caricate.
        try:
            if self.master_app.libs_db.conn is not None or Path(self.master_app.options.libs_db_file).exists():
                res=self.master_app.libs_db.search_lines(
                    wave, rg, table=self.db_table_var.get(), limit=1000
                )
                res=[
                    self.master_app.libs_db.enrich_line_from_element_table(l, tolerance=max(0.02, rg))
                    for l in res
                ]
        except Exception:
            res=[]
        if not res:
            res=[l for l in self.atomic_lines if abs(l.wavelen-wave)<=rg]
            res.sort(key=lambda l:abs(l.wavelen-wave))
        self.populate(res)

    def assign(self, _=None):
        item=self.tree.focus()
        if item:
            self.master_app.assign_atomic_line_to_nearest_template(self.results[int(item)])


class ElementLocatorWindow(tk.Toplevel):
    """Unit2: cerca righe di un elemento nel range visibile e auto-assegna."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app=master
        self.title("Element Locator - Unit2")
        self.resizable(False, False)
        ttk.Label(self, text="Element symbol").grid(row=0,column=0,padx=8,pady=8,sticky="w")
        self.el_var=tk.StringVar(value="Fe")
        ttk.Entry(self, textvariable=self.el_var, width=12).grid(row=0,column=1,pady=8)
        ttk.Label(self, text="Max lines").grid(row=1,column=0,padx=8,sticky="w")
        self.max_var=tk.StringVar(value="20")
        ttk.Entry(self, textvariable=self.max_var,width=12).grid(row=1,column=1)
        self.mode=tk.IntVar(value=3)
        ttk.Radiobutton(self,text="I",variable=self.mode,value=0).grid(row=2,column=0,sticky="w",padx=8)
        ttk.Radiobutton(self,text="II",variable=self.mode,value=1).grid(row=2,column=1,sticky="w")
        ttk.Radiobutton(self,text="I + II",variable=self.mode,value=3).grid(row=2,column=2,sticky="w")
        ttk.Button(self,text="Locate",command=self.locate).grid(row=3,column=0,padx=8,pady=12)
        ttk.Button(self,text="Clear markers",command=self.master_app.clear_element_markers).grid(row=3,column=1,pady=12)
        ttk.Button(self,text="Auto assign",command=self.auto_assign).grid(row=3,column=2,pady=12)
        fit_toplevel_to_content(self)

    def locate(self):
        element=self.el_var.get().strip()
        if not element: return
        element=element[0].upper()+element[1:]
        mode=self.mode.get()
        maxn=safe_int(self.max_var.get(),20)
        lo,hi=self.master_app.current_xlim()
        lines=[l for l in self.master_app.atomic_lines if l.specie==element and lo<=l.wavelen<=hi and (mode==3 or (mode==0 and l.ion==1) or (mode==1 and l.ion==2))]
        lines.sort(key=lambda l: -l.inte)
        self.master_app.element_markers=lines[:maxn]
        self.master_app.redraw()
        self.master_app.status(f"Element Locator: {len(self.master_app.element_markers)} lines {element}")

    def auto_assign(self):
        if not self.master_app.element_markers:
            self.locate()
        for l in self.master_app.element_markers:
            self.master_app.assign_atomic_line_to_nearest_template(l, redraw=False)
        self.master_app.redraw()
        self.master_app.status(f"Auto-assign completed: {len(self.master_app.element_markers)} lines")


class TraceLinesWindow(tk.Toplevel):
    """Analyse > Trace Lines:

    The command traces the strongest expected lines for the selected element and
    ionization stage(s) inside the wavelength interval displayed in the main
    plot.  Assign applies to all traced species currently drawn, not only the
    species shown in the dialog.
    """
    columns = ("wavelen", "specie", "ion", "inte", "ei", "ek", "gi", "gk", "aki", "acc")

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Trace Lines")
        self.geometry("900x460")
        self.minsize(840, 360)
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Trace Species").grid(row=0, column=0, sticky="w", padx=3, pady=3)
        self.species_var = tk.StringVar(value="Si")
        ttk.Entry(top, textvariable=self.species_var, width=10).grid(row=0, column=1, sticky="w", padx=3)
        self.mode_var = tk.StringVar(value="Both")
        ttk.Label(top, text="Mode").grid(row=0, column=2, sticky="w", padx=(8, 2))
        for c, mode in enumerate(("I", "II", "Both", "All"), start=3):
            ttk.Radiobutton(top, text=mode, variable=self.mode_var, value=mode).grid(row=0, column=c, padx=3)
        ttk.Label(top, text="Max Lines").grid(row=0, column=7, sticky="w", padx=(16,3))
        self.max_var = tk.StringVar(value="5")
        ttk.Entry(top, textvariable=self.max_var, width=7).grid(row=0, column=8, sticky="w", padx=3)
        ttk.Button(top, text="OK", command=self.trace).grid(row=0, column=9, padx=8)
        ttk.Button(top, text="Assign", command=self.assign).grid(row=0, column=10, padx=3)
        ttk.Button(top, text="Clear", command=self.clear).grid(row=0, column=11, padx=3)
        self.info_var = tk.StringVar(value="Trace uses the currently visible wavelength range.")
        ttk.Label(self, textvariable=self.info_var).pack(anchor="w", padx=8)
        tree_frame = ttk.Frame(self)
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings")
        for c in self.columns:
            self.tree.heading(c, text=c); self.tree.column(c, width=72, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.refresh()
        center_window(self, master)

    def refresh(self, show_message=True):
        self.tree.delete(*self.tree.get_children())
        for i, l in enumerate(getattr(self.master_app, "trace_markers", [])):
            self.tree.insert("", "end", iid=str(i), values=[getattr(l, c) for c in self.columns])

    def trace(self):
        element = self.species_var.get().strip().capitalize()
        if not element:
            return
        mode = self.mode_var.get()
        # Use exactly the wavelength interval that is visible in the main plot
        # at the moment the user presses OK.  This 
        # avoids searching the full spectrum after a zoom.
        view_xlim, view_ylim = self.master_app.current_plot_view()
        lo, hi = view_xlim
        maxn = safe_int(self.max_var.get(), 20)
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            if mode == "I":
                lines = self.master_app.libs_db.trace_lines(element, lo, hi, ions=[1], max_lines=maxn, table="Datalibs")
            elif mode == "II":
                lines = self.master_app.libs_db.trace_lines(element, lo, hi, ions=[2], max_lines=maxn, table="Datalibs")
            elif mode == "All":
                lines = self.master_app.libs_db.trace_lines(element, lo, hi, ions=[1, 2], max_lines=maxn, table="Datalibs")
            else:
                lines = (
                    self.master_app.libs_db.trace_lines(element, lo, hi, ions=[1], max_lines=maxn, table="Datalibs") +
                    self.master_app.libs_db.trace_lines(element, lo, hi, ions=[2], max_lines=maxn, table="Datalibs")
                )
            # Enrich each traced line with complete transition data when available.
            enriched = []
            for l in lines:
                try:
                    enriched.append(self.master_app.libs_db.enrich_line_from_element_table(l, tolerance=0.05))
                except Exception:
                    enriched.append(l)
            lines = enriched
        except Exception as e:
            _showerror(self, "Trace Lines", str(e))
            return
        # Repeated Trace calls accumulate
        existing = getattr(self.master_app, "trace_markers", [])
        for l in lines:
            if not any(abs(t.wavelen-l.wavelen) < 1e-6 and t.specie == l.specie and t.ion == l.ion for t in existing):
                existing.append(l)
        existing.sort(key=lambda x: x.wavelen)
        self.master_app.trace_markers = existing
        self.refresh()
        self.master_app.redraw(preserve_view=True)
        self.master_app.restore_plot_view(view_xlim, view_ylim)
        self.info_var.set(f"Traced {len(lines)} {element} lines ({mode}) in the visible interval {min(lo,hi):.2f}-{max(lo,hi):.2f} Å; total traced lines: {len(existing)}.")
        self.master_app.status(self.info_var.get())

    def assign(self):
        n = self.master_app.assign_traced_lines()
        self.refresh()
        self.info_var.set(f"Assign: {n} template lines assigned within Range = {self.master_app.options.search_range} Å.")

    def clear(self):
        self.master_app.trace_markers = []
        self.refresh()
        self.master_app.redraw(preserve_view=True)
        self.master_app.status("Trace Lines: marcatori cancellati")


class AutoElementIdentificationWindow(tk.Toplevel):
    """Unit77: ranking automatico degli elementi presenti nello spettro/template.

    Implementa la logica ricostruita:
        score = maxnt * log(30/rc) * I_meas * exp(-(dw^2)/(2*range^2))
    dove maxnt = intensità database / 100630.
    """

    def __init__(self, master):
        super().__init__(master)
        self.master_app=master
        self.title("Auto Element Identification - Unit77")
        self.geometry("760x500")
        self.minsize(720, 340)
        self.results: list[tuple[str, float]] = []

        top=ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Label(top,text="λ min").pack(side="left")
        self.min_var=tk.StringVar(value=str(master.options.limit_low))
        ttk.Entry(top,textvariable=self.min_var,width=9).pack(side="left", padx=2)
        ttk.Label(top,text="λ max").pack(side="left")
        self.max_var=tk.StringVar(value=str(master.options.limit_high))
        ttk.Entry(top,textvariable=self.max_var,width=9).pack(side="left", padx=2)
        ttk.Label(top,text="range").pack(side="left")
        self.range_var=tk.StringVar(value=str(master.options.search_range))
        ttk.Entry(top,textvariable=self.range_var,width=7).pack(side="left", padx=2)
        ttk.Label(top,text="Top").pack(side="left")
        self.top_var=tk.StringVar(value="20")
        ttk.Entry(top,textvariable=self.top_var,width=5).pack(side="left", padx=2)
        ttk.Button(top,text="Rank elements",command=self.rank).pack(side="left", padx=4)
        ttk.Button(top,text="Auto assign top",command=self.auto_assign_top).pack(side="left", padx=4)

        cols=("sel","species","score")
        tree_frame = ttk.Frame(self)
        self.tree=ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c,text=c)
            self.tree.column(c,width=120 if c!="species" else 180,anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=5)
        self.tree.bind("<Button-1>", self.toggle)

    def template_candidates(self):
        lo=safe_float(self.min_var.get(), self.master_app.options.limit_low)
        hi=safe_float(self.max_var.get(), self.master_app.options.limit_high)
        lines=[t for t in self.master_app.template_lines if lo <= t.wavelen <= hi]
        if lines:
            return [(t.wavelen, t.inte if t.inte else t.templint if t.templint else 1.0) for t in lines]
        # fallback: picchi grezzi dal massimo locale semplice dello spettro principale
        if not self.master_app.spectra:
            return []
        sp=self.master_app.spectra[0]
        pts=[]
        for i in range(1, len(sp.y)-1):
            if lo <= sp.x[i] <= hi and sp.y[i] > sp.y[i-1] and sp.y[i] >= sp.y[i+1]:
                pts.append((sp.x[i], sp.y[i]))
        pts.sort(key=lambda p: -p[1])
        return pts[:80]

    def rank(self):
        try:
            self.master_app.libs_db.filename=self.master_app.options.libs_db_file
            self.master_app.libs_db.connect()
        except Exception as e:
            _showerror(self, "LIBS.db", str(e)); return
        rg=safe_float(self.range_var.get(), self.master_app.options.search_range)
        candidates=self.template_candidates()
        if not candidates:
            _showinfo(self, "Auto Element Identification", "No line/template in range.")
            return
        scores: dict[str, float] = {}
        nls=0.0
        for freq, imeas in candidates:
            lines=self.master_app.libs_db.search_lines(freq, rg, table="Datalibs", limit=200)
            rc=max(len(lines),1)
            nls+=rc
            rcc=30.0/rc
            # evita score negativi se rc > 30; conserva il senso dell'algoritmo ma stabilizza.
            logterm=math.log(max(rcc, 1.000001))
            for l in lines:
                spec=f"{l.specie} {'I' if l.ion==1 else 'II' if l.ion==2 else l.ion}"
                maxnt=l.inte/100630.0
                score=maxnt*logterm*imeas*math.exp(-((l.wavelen-freq)**2)/(2.0*rg*rg))
                scores[spec]=scores.get(spec,0.0)+score
        norm=sum(abs(v) for _,v in candidates) or 1.0
        factor=math.log(max(nls, math.e))/math.log(30.0)
        ranked=[(k, v*factor/norm) for k,v in scores.items() if k.strip() not in ("H+","Al+")]
        ranked.sort(key=lambda kv: kv[1], reverse=True)
        top=safe_int(self.top_var.get(),20)
        self.results=ranked[:top]
        self.tree.delete(*self.tree.get_children())
        for i,(spec,score) in enumerate(self.results):
            self.tree.insert("", "end", iid=str(i), values=("", spec, f"{score:.5g}"))
        self.master_app.status(f"Auto ID: {len(self.results)} specie candidate")

    def toggle(self, event=None):
        item=self.tree.identify_row(event.y) if event else self.tree.focus()
        if item:
            vals=list(self.tree.item(item,"values"))
            vals[0]="" if vals[0]=="X" else "X"
            self.tree.item(item, values=vals)

    def selected_specs(self):
        specs=[]
        for iid in self.tree.get_children():
            vals=self.tree.item(iid,"values")
            if vals and vals[0]!="X":  # come Unit77: righe non marcate vengono usate
                specs.append(vals[1])
        return specs

    def auto_assign_top(self):
        if not self.results:
            self.rank()
        rg=safe_float(self.range_var.get(), self.master_app.options.search_range)
        assigned=0
        for spec_label in self.selected_specs():
            parts=spec_label.split()
            if not parts: continue
            element=parts[0]
            ion=1 if len(parts)<2 or parts[1]=="I" else 2
            for t in self.master_app.template_lines:
                lines=self.master_app.libs_db.search_lines(
                    t.wavelen, rg, table="Datalibs", element=element, ion=ion, limit=1
                )
                if lines:
                    self.master_app.assign_atomic_line_to_nearest_template(lines[0], redraw=False)
                    assigned+=1
        self.master_app.redraw()
        self.master_app.status(f"Auto-assign Unit77: {assigned} assegnazioni")


class BatchStatisticsWindow(tk.Toplevel):
    """Historical Batch Operations window."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app=master
        self.title("Batch Operations")
        self.geometry("860x500")
        self.minsize(800, 340)
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="Load List", command=self.load_list)
        file_menu.add_command(label="Save List", command=self.save_list)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)

        top=ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top,text="Add Files",command=self.add_files).pack(side="left")
        opts = ttk.LabelFrame(top, text="Add Files Options")
        opts.pack(side="left", padx=8)
        self.add_mode = tk.StringVar(value="all")
        ttk.Radiobutton(opts, text="Load all", variable=self.add_mode, value="all").pack(side="left", padx=3)
        ttk.Radiobutton(opts, text="Load odd only", variable=self.add_mode, value="odd").pack(side="left", padx=3)
        ttk.Radiobutton(opts, text="Load even only", variable=self.add_mode, value="even").pack(side="left", padx=3)
        ttk.Button(top,text="Join",command=self.join_pairs).pack(side="left", padx=3)
        ttk.Button(top,text="Average",command=self.average_files).pack(side="left", padx=3)
        self.calculate_sd = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Calculate SD", variable=self.calculate_sd).pack(side="left", padx=3)

        bottom=ttk.Frame(self); bottom.pack(fill="x", padx=6, pady=3)
        ttk.Button(bottom,text="Load List",command=self.load_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Clear List",command=self.clear_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Save List",command=self.save_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Close",command=self.destroy).pack(side="right", padx=3)
        self.listbox=tk.Listbox(self)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        center_window(self, master)

    def _last_numeric_index(self, filename):
        nums = re.findall(r"\d+", Path(filename).stem)
        return int(nums[-1]) if nums else None

    def _include_file(self, filename):
        mode = self.add_mode.get()
        if mode == "all":
            return True
        idx = self._last_numeric_index(filename)
        if idx is None:
            return False
        return (idx % 2 == 1) if mode == "odd" else (idx % 2 == 0)

    def add_files(self):
        fns=filedialog.askopenfilenames(initialdir=remembered_initial_dir(self.master_app.options), filetypes=SPECTRUM_FILETYPES)
        remember_working_dir(self.master_app.options, fns)
        for fn in fns:
            if self._include_file(fn):
                self.listbox.insert("end", fn)

    def paths(self):
        return [self.listbox.get(i) for i in range(self.listbox.size())]

    def load_list(self):
        fn=filedialog.askopenfilename(initialdir=remembered_initial_dir(self.master_app.options), filetypes=[("File list", "*.lst"), ("Legacy file list", "*.fls"), ("All","*.*")])
        if not fn: return
        remember_working_dir(self.master_app.options, fn)
        self.listbox.delete(0,"end")
        for line in Path(fn).read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                self.listbox.insert("end", line.strip())

    def save_list(self):
        fn=filedialog.asksaveasfilename(initialdir=remembered_initial_dir(self.master_app.options), defaultextension=".lst", filetypes=[("File list","*.lst"), ("All","*.*")])
        if not fn: return
        remember_working_dir(self.master_app.options, fn)
        Path(fn).write_text("\n".join(self.paths()) + ("\n" if self.paths() else ""), encoding="utf-8")

    def clear_list(self):
        self.listbox.delete(0,"end")

    def _load_spectrum(self, filename):
        return self.master_app.load_spectrum_with_corrections(filename)

    def _load_generated_average_outputs(self, outputs):
        loaded = []
        load_errors = []
        for filename, display_name in outputs:
            try:
                sp = self.master_app.load_spectrum_with_corrections(filename)
                sp.name = display_name
                self.master_app.add_spectrum(sp)
                loaded.append(filename)
            except Exception as e:
                load_errors.append(f"{filename}: {e}")
        if load_errors:
            saved_paths = "\n".join(filename for filename, _ in outputs)
            _showwarning(
                self,
                "Batch Average",
                "Average output was saved, but one or more generated spectra could not be loaded.\n\n"
                f"Saved file(s):\n{saved_paths}\n\n"
                + "\n".join(load_errors[:10])
            )
        return loaded, load_errors

    def join_pairs(self):
        files = self.paths()
        if len(files) < 2:
            self.master_app.status("Batch Join: select at least two files")
            return
        saved = []
        errors = []
        skipped = files[-1] if len(files) % 2 else None
        for i in range(0, len(files) - 1, 2):
            f1, f2 = files[i], files[i + 1]
            try:
                sp1 = self._load_spectrum(f1)
                sp2 = self._load_spectrum(f2)
                merged = merge_spectra_by_wavelength(sp1, sp2, name=f"{Path(f1).stem} joined")
                out = str(Path(f1).with_suffix(".jnd"))
                merged.save_ascii(out)
                saved.append(out)
            except Exception as e:
                errors.append(f"{Path(f1).name} + {Path(f2).name}: {e}")
        msg = f"Batch Join: saved {len(saved)} .jnd file(s)"
        if skipped:
            msg += f"; skipped odd last file {Path(skipped).name}"
        self.master_app.status(msg)
        if errors:
            _showwarning(self, "Batch Join", "\n".join(errors[:10]))

    def _common_grid_values(self, specs):
        base = sorted(zip(specs[0].x, specs[0].y), key=lambda p: p[0])
        grid = [x for x, _ in base]
        rows = []
        for sp in specs:
            pts = sorted(zip(sp.x, sp.y), key=lambda p: p[0])
            if len(pts) == len(base) and all(abs(a[0] - b[0]) < 1e-9 for a, b in zip(pts, base)):
                rows.append([y for _, y in pts])
            else:
                rows.append([_interp_spectrum_value(pts, x) for x in grid])
        return grid, rows

    def average_files(self):
        files = self.paths()
        specs=[]
        loaded_files=[]
        errors=[]
        for fn in files:
            try:
                specs.append(self._load_spectrum(fn))
                loaded_files.append(fn)
            except Exception as e:
                errors.append(f"{Path(fn).name}: {e}")
        if not specs:
            if errors:
                _showerror(self, "Batch Average", "\n".join(errors[:10]))
            return
        x, rows = self._common_grid_values(specs)
        avg=[sum(vals)/len(vals) for vals in zip(*rows)]
        out_avg = str(Path(loaded_files[0]).with_suffix(".avg"))
        Spectrum(list(x), avg, name="Batch average").save_ascii(out_avg)
        outputs = [out_avg]
        generated_outputs = [(out_avg, "Batch Average")]
        if len(rows)>1:
            std=[math.sqrt(sum((v-a)**2 for v in vals)/len(rows)) for vals,a in zip(zip(*rows),avg)]
        else:
            std=[0.0]*len(x)
        if self.calculate_sd.get():
            out_sd = str(Path(loaded_files[0]).with_suffix(".sd"))
            Spectrum(list(x), std, name="Batch SD").save_ascii(out_sd)
            outputs.append(out_sd)
            generated_outputs.append((out_sd, "Batch Standard Deviation"))
        loaded_outputs, load_errors = self._load_generated_average_outputs(generated_outputs)
        saved_names = ", ".join(Path(o).name for o in outputs)
        if loaded_outputs and not load_errors:
            self.master_app.status(f"Batch average saved and loaded into comparison view: {saved_names}")
        elif loaded_outputs:
            self.master_app.status(f"Batch Average: saved {saved_names}; some generated spectra could not be loaded")
        else:
            self.master_app.status(f"Batch Average: saved {saved_names} from {len(specs)} file(s)")
        if errors:
            _showwarning(self, "Batch Average", "\n".join(errors[:10]))

    def load_fls(self):
        self.load_list()

    def save_fls(self):
        self.save_list()

    def average_std(self):
        self.calculate_sd.set(True)
        self.average_files()

    def total_intensity(self):
        rows=[]
        for fn in self.paths():
            try:
                sp=self._load_spectrum(fn)
                rows.append((fn, sum(sp.y)))
            except Exception:
                pass
        win=SimpleTableWindow(self.master_app, "Total intensity report", ("file","total_intensity"))
        for i,(fn,total) in enumerate(rows):
            win.tree.insert("", "end", iid=str(i), values=(Path(fn).name, f"{total:.6g}"))

class VerticalShiftWindow(tk.Toplevel):
    """Unit4: shift verticale dello spettro principale."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app=master
        self.title("Vertical Shift - Unit4")
        ttk.Label(self,text="Current value").grid(row=0,column=0,padx=8,pady=8)
        ttk.Label(self,text="Desired value").grid(row=1,column=0,padx=8,pady=8)
        self.v1=tk.StringVar(value="0")
        self.v2=tk.StringVar(value="0")
        ttk.Entry(self,textvariable=self.v1).grid(row=0,column=1)
        ttk.Entry(self,textvariable=self.v2).grid(row=1,column=1)
        ttk.Button(self,text="Apply to main spectrum",command=self.apply).grid(row=2,column=0,columnspan=2,pady=8)
        fit_toplevel_to_content(self)
        center_window(self, master)

    def apply(self):
        if not self.master_app.spectra: return
        shift=safe_float(self.v2.get())-safe_float(self.v1.get())
        self.master_app.spectra[0].y=[y+shift for y in self.master_app.spectra[0].y]
        self.master_app.redraw()
        self.destroy()


class SpectrumShiftWindow(tk.Toplevel):
    """Shift wavelength dialog."""
    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Shift")
        self.resizable(False, False)
        self.transient(master)
        self.capture_target = None
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        ttk.Label(self, text="Move Point at:").grid(row=0, column=0, sticky="e", padx=8, pady=(10, 4))
        ttk.Label(self, text="to:").grid(row=1, column=0, sticky="e", padx=8, pady=4)
        self.source_var = tk.StringVar(value="")
        self.target_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.source_var, width=16).grid(row=0, column=1, padx=4, pady=(10, 4))
        ttk.Entry(self, textvariable=self.target_var, width=16).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(self, text="Pick", command=lambda: self.begin_capture("source")).grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=(10, 4))

        self.shift_identifications_var = tk.BooleanVar(value=True)
        self.shift_all_spectra_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Shift Identifications", variable=self.shift_identifications_var).grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 2))
        ttk.Checkbutton(self, text="Shift all spectra", variable=self.shift_all_spectra_var).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=2)

        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", padx=8, pady=(10, 8))
        ttk.Button(buttons, text="OK", command=self.ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="left", padx=4)
        fit_toplevel_to_content(self)
        center_window(self, master)

    def begin_capture(self, target):
        self.capture_target = target
        self.master_app.shift_capture_window = self
        self._set_capture_topmost(True)
        self._raise_dialog()
        self.master_app.status("Shift: click the spectrum to set " + ("Move Point at" if target == "source" else "to"))

    def set_from_plot(self, wavelength, intensity=None):
        if self.capture_target == "source":
            self.source_var.set(f"{wavelength:.6g}")
            self.capture_target = "target"
            self.master_app.shift_capture_window = self
            self._set_capture_topmost(True)
            self._raise_dialog()
            self.master_app.status("Shift: click the spectrum to set target wavelength")
        elif self.capture_target == "target":
            self.target_var.set(f"{wavelength:.6g}")
            self.capture_target = None
            self.master_app.shift_capture_window = None
            self._set_capture_topmost(False)
            self._raise_dialog()
            self.master_app.status("Shift: source and target wavelengths selected")

    def _set_capture_topmost(self, enabled):
        try:
            self.attributes("-topmost", bool(enabled))
        except Exception:
            pass

    def _raise_dialog(self):
        try:
            self.deiconify()
            self.lift(self.master_app)
            self.focus_force()
        except Exception:
            try:
                self.focus_set()
            except Exception:
                pass

    def _shift_identifications(self, shift):
        for line in self.master_app.template_lines:
            line.wavelen += shift
            if line.asswavelen:
                line.asswavelen += shift
            if line.fitwavelen:
                fitwavelen = safe_float(getattr(line, "fitwavelen", 0.0), 0.0)
                sign = -1.0 if fitwavelen < 0 else 1.0
                line.fitwavelen = sign * (abs(fitwavelen) + shift)
        for markers_name in ("element_markers", "trace_markers"):
            for line in getattr(self.master_app, markers_name, []):
                line.wavelen += shift

    def ok(self):
        if not self.master_app.spectra:
            self.master_app.status("Shift: no spectrum loaded")
            _showinfo(self, "Shift", "Load a spectrum before shifting.")
            return
        source = safe_float(self.source_var.get(), None)
        target = safe_float(self.target_var.get(), None)
        if source is None or target is None:
            _showerror(self, "Shift", "Enter both source and target wavelengths.")
            return
        shift = target - source
        if self.shift_all_spectra_var.get():
            spectra = [sp for sp in self.master_app.spectra if getattr(sp, "visible", True)]
        else:
            spectra = [self.master_app.spectra[0]]
        for sp in spectra:
            sp.x = [x + shift for x in sp.x]
        if self.shift_identifications_var.get():
            self._shift_identifications(shift)
            self.master_app.notify_template_changed(redraw=False)
        self.master_app.redraw(preserve_view=True)
        self.master_app.status(f"Shift: applied {shift:.6g} to {len(spectra)} spectrum/spectra")
        self.cancel()

    def cancel(self):
        if getattr(self.master_app, "shift_capture_window", None) is self:
            self.master_app.shift_capture_window = None
        self._set_capture_topmost(False)
        self.destroy()


class SpectrumOffsetWindow(SpectrumShiftWindow):
    """ Offset intensity dialog."""
    def __init__(self, master: "MainWindow"):
        tk.Toplevel.__init__(self, master)
        self.master_app = master
        self.title("Offset")
        self.resizable(False, False)
        self.transient(master)
        self.capture_target = None
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        ttk.Label(self, text="Move Point at:").grid(row=0, column=0, sticky="e", padx=8, pady=(10, 4))
        ttk.Label(self, text="to:").grid(row=1, column=0, sticky="e", padx=8, pady=4)
        self.source_var = tk.StringVar(value="")
        self.target_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.source_var, width=16).grid(row=0, column=1, padx=4, pady=(10, 4))
        ttk.Entry(self, textvariable=self.target_var, width=16).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(self, text="Pick", command=lambda: self.begin_capture("source")).grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=(10, 4))

        self.offset_all_spectra_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Offset all spectra", variable=self.offset_all_spectra_var).grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 2))

        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, columnspan=3, sticky="e", padx=8, pady=(10, 8))
        ttk.Button(buttons, text="OK", command=self.ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="left", padx=4)
        fit_toplevel_to_content(self)

    def begin_capture(self, target):
        self.capture_target = target
        self.master_app.shift_capture_window = self
        self._set_capture_topmost(True)
        self._raise_dialog()
        self.master_app.status("Offset: click the spectrum to set " + ("Move Point at" if target == "source" else "to"))

    def set_from_plot(self, wavelength, intensity=None):
        value = wavelength if intensity is None else intensity
        if self.capture_target == "source":
            self.source_var.set(f"{value:.6g}")
            self.capture_target = "target"
            self.master_app.shift_capture_window = self
            self._set_capture_topmost(True)
            self._raise_dialog()
            self.master_app.status("Offset: click the spectrum to set target intensity")
        elif self.capture_target == "target":
            self.target_var.set(f"{value:.6g}")
            self.capture_target = None
            self.master_app.shift_capture_window = None
            self._set_capture_topmost(False)
            self._raise_dialog()
            self.master_app.status("Offset: source and target intensities selected")

    def ok(self):
        if not self.master_app.spectra:
            self.master_app.status("Offset: no spectrum loaded")
            _showinfo(self, "Offset", "Load a spectrum before applying an offset.")
            return
        source = safe_float(self.source_var.get(), None)
        target = safe_float(self.target_var.get(), None)
        if source is None or target is None:
            _showerror(self, "Offset", "Enter both source and target intensities.")
            return
        offset = target - source
        if self.offset_all_spectra_var.get():
            spectra = [sp for sp in self.master_app.spectra if getattr(sp, "visible", True)]
        else:
            spectra = [self.master_app.spectra[0]]
        for sp in spectra:
            sp.y = [y + offset for y in sp.y]
        self.master_app.redraw(preserve_view=True)
        self.master_app.status(f"Offset: applied {offset:.6g} to {len(spectra)} spectrum/spectra")
        self.cancel()


# ---------------------------------------------------------------------------
# v6 analysis engines reconstructed from SDIMain / Unit14 / Unit37
# ---------------------------------------------------------------------------

def _nearest_y(xvals: list[float], yvals: list[float], x0: float) -> float:
    if not xvals:
        return 0.0
    idx = min(range(len(xvals)), key=lambda i: abs(xvals[i] - x0))
    return yvals[idx]


def multigaussian_model(x, *params):
    """SDIMain autogauss model: baseline + slope*x + sum(A*exp(-((x-x0)/sigma)^2)).

    Parameter order used here:
        params[0] = baseline
        params[1] = slope
        then repeated triples: amplitude, center, sigma
    """
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    y = np.full_like(x, float(params[0])) + float(params[1]) * x
    for i in range(2, len(params), 3):
        amp, cen, sig = params[i], params[i + 1], abs(params[i + 2]) or 1e-12
        y += amp * np.exp(-((x - cen) / sig) ** 2)
    return y




def voigt_profile_unit(x, center, sigma, gamma):
    """Area-normalized Voigt profile.

    sigma is the Gaussian sigma and gamma is the Lorentzian HWHM.  The
    implementation uses scipy.special.wofz when available; otherwise it falls
    back to a pseudo-Voigt approximation so the program remains usable.
    """
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    sigma = max(abs(float(sigma)), 1e-12)
    gamma = max(abs(float(gamma)), 1e-12)
    try:
        from scipy.special import wofz
        z = ((x - center) + 1j * gamma) / (sigma * math.sqrt(2.0))
        return np.real(wofz(z)) / (sigma * math.sqrt(2.0 * math.pi))
    except Exception:
        # Thompson-Cox-Hastings-like pseudo-Voigt fallback, normalized by area.
        f_g = 2.0 * math.sqrt(2.0 * math.log(2.0)) * sigma
        f_l = 2.0 * gamma
        f = (f_g**5 + 2.69269*f_g**4*f_l + 2.42843*f_g**3*f_l**2 +
             4.47163*f_g**2*f_l**3 + 0.07842*f_g*f_l**4 + f_l**5) ** 0.2
        r = f_l / f if f else 0.0
        eta = max(0.0, min(1.0, 1.36603*r - 0.47719*r*r + 0.11116*r*r*r))
        gaussian = math.sqrt(4.0*math.log(2.0)/math.pi) / f * np.exp(-4.0*math.log(2.0)*((x-center)/f)**2)
        lorentz = (2.0/math.pi) * f / (4.0*(x-center)**2 + f*f)
        return (1.0-eta)*gaussian + eta*lorentz


def multivoigt_model(x, *params):
    """baseline + slope*x + sum(area_i * Voigt(center_i, sigma_i, gamma_i))."""
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    y = np.full_like(x, float(params[0])) + float(params[1]) * x
    for i in range(2, len(params), 4):
        area, cen, sigma, gamma = params[i], params[i + 1], params[i + 2], params[i + 3]
        y += area * voigt_profile_unit(x, cen, sigma, gamma)
    return y


class FitStoppedError(Exception):
    """Controlled interruption for Manual/Automatic Fit workers."""


def linear_fit(x: list[float], y: list[float]):
    if len(x) < 2:
        return None
    if np is None:
        n = len(x)
        sx, sy = sum(x), sum(y)
        sxx = sum(v*v for v in x)
        sxy = sum(a*b for a,b in zip(x,y))
        den = n*sxx - sx*sx
        if den == 0:
            return None
        slope = (n*sxy - sx*sy)/den
        intercept = (sy - slope*sx)/n
        return slope, intercept
    coeff = np.polyfit(np.asarray(x, dtype=float), np.asarray(y, dtype=float), 1)
    return float(coeff[0]), float(coeff[1])


def pseudo_voigt(x, amp, center, wg, wl, baseline, slope, eta):
    """Simple pseudo-Voigt used for H-alpha checkpoint.

    wg and wl are FWHM-like widths. This preserves the parameters: center, Gaussian width, Lorentzian width.
    """
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    wg = abs(wg) or 1e-12
    wl = abs(wl) or 1e-12
    eta = min(max(float(eta), 0.0), 1.0)
    gaussian = np.exp(-4.0 * math.log(2.0) * ((x - center) / wg) ** 2)
    lorentz = 1.0 / (1.0 + 4.0 * ((x - center) / wl) ** 2)
    return baseline + slope*x + amp * ((1.0 - eta) * gaussian + eta * lorentz)


def lorentzian_component(x, amp, center, width):
    """Lorentzian peak with width interpreted as FWHM."""
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    width = abs(float(width)) or 1e-12
    return amp / (1.0 + 4.0 * ((x - center) / width) ** 2)


def halpha_lorentzian_model(x, *params):
    """baseline + one or more Lorentzian components.

    Parameter order: baseline, then repeated amp, center, FWHM triples.
    """
    if np is None:
        raise RuntimeError("numpy not available")
    x = np.asarray(x, dtype=float)
    y = np.full_like(x, float(params[0]))
    for i in range(1, len(params), 3):
        y += lorentzian_component(x, params[i], params[i + 1], params[i + 2])
    return y


def libspp_halpha_ne(width_angstrom, kt_ev):
    """H-alpha Ne iteration from SDIMain.cpp Ne()."""
    d = float(width_angstrom)
    kt = float(kt_ev)
    if d <= 0.0:
        raise ValueError("Corrected Lorentzian width must be positive.")
    if kt <= 0.0:
        raise ValueError("kT must be positive.")
    temperature = 11600.0 * kt
    a = math.sqrt(4033.8 - 24.45 * math.pow(math.log(temperature), 2))
    b = 1.028e9 + 174576.3 * temperature
    sol = 1.0e17
    for _ in range(1000):
        nestart = sol
        alfa = 1.0 / (a + b / math.sqrt(nestart))
        sol = 8.02e12 * math.pow(d / alfa, 1.5)
        if sol != 0.0 and abs(sol - nestart) / sol <= 0.01:
            return sol, temperature, alfa
    return sol, temperature, alfa


class MultiGaussianFitWindow(tk.Toplevel):
    """Functional v6 replacement for the old dummy fit window.

    It uses the SDIMain autogauss model and scipy.optimize.curve_fit when available.
    Results are written back to TemplateLine.fitwavelen, .inte and .wg.
    """

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Voigt Fit - visible marked lines")
        self.geometry("900x560")
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Label(top, text="Range around template lines").pack(side="left")
        self.range_var = tk.StringVar(value="2.0")
        ttk.Entry(top, textvariable=self.range_var, width=7).pack(side="left", padx=4)
        ttk.Label(top, text="Initial sigma").pack(side="left")
        self.sigma_var = tk.StringVar(value=str(master.options.fixed_wg or 0.5))
        ttk.Entry(top, textvariable=self.sigma_var, width=7).pack(side="left", padx=4)
        ttk.Button(top, text="Fit Gaussian", command=self.fit_region).pack(side="left", padx=5)
        ttk.Button(top, text="Fit Voigt visible", command=self.fit_voigt_visible).pack(side="left", padx=5)
        ttk.Button(top, text="Clear fit overlay", command=self.clear_overlay).pack(side="left", padx=5)
        cols = ("line", "center", "area", "wg", "wl", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=5)

    def candidate_lines(self):
        lo, hi = self.master_app.current_xlim()
        lines = [t for t in self.master_app.template_lines if lo <= t.wavelen <= hi]
        if not lines:
            lines = list(self.master_app.template_lines[:10])
        return lines[:10]

    def fit_region(self):
        if np is None:
            _showerror(self, "Fit", "numpy not available")
            return
        try:
            from scipy.optimize import curve_fit
        except Exception:
            _showerror(self, "Fit", "scipy.optimize not available. Install scipy.")
            return
        if not self.master_app.spectra:
            _showinfo(self, "Fit", "Load a spectrum first.")
            return
        sp = self.master_app.spectra[0]
        lines = self.candidate_lines()
        if not lines:
            _showinfo(self, "Fit", "No template line in the visible range.")
            return
        rg = safe_float(self.range_var.get(), 2.0)
        lo = min(t.wavelen for t in lines) - rg
        hi = max(t.wavelen for t in lines) + rg
        xs = np.asarray([x for x in sp.x if lo <= x <= hi], dtype=float)
        ys = np.asarray([sp.y[i] for i,x in enumerate(sp.x) if lo <= x <= hi], dtype=float)
        if len(xs) < 6:
            _showinfo(self, "Fit", "Too few points in the selected range.")
            return
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        sigma0 = abs(safe_float(self.sigma_var.get(), 0.5)) or 0.5
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        for t in lines:
            amp = max(_nearest_y(sp.x, sp.y, t.wavelen) - baseline, 1.0)
            center0 = abs(t.fitwavelen) if t.fitwavelen else t.wavelen
            p0.extend([amp, center0, abs(t.wg) if t.wg else sigma0])
            # fixed parameters are represented as negative in templates.
            if safe_float(getattr(t, "fitwavelen", 0.0), 0.0) < 0:
                bounds_lo.extend([0, center0 - 1e-9, 1e-6])
                bounds_hi.extend([np.inf, center0 + 1e-9, max(10.0, sigma0*20)])
            else:
                bounds_lo.extend([0, center0 - rg, 1e-6])
                bounds_hi.extend([np.inf, center0 + rg, max(10.0, sigma0*20)])
        try:
            popt, pcov = curve_fit(multigaussian_model, xs, ys, p0=p0, bounds=(bounds_lo, bounds_hi), maxfev=max(1000, self.master_app.options.iterations*200))
        except Exception as e:
            _showerror(self, "Fit", str(e))
            return
        self.tree.delete(*self.tree.get_children())
        for idx, t in enumerate(lines):
            amp, cen, sig = popt[2+3*idx], popt[3+3*idx], abs(popt[4+3*idx])
            t.fitwavelen = float(cen)
            t.inte = float(amp * sig * math.sqrt(math.pi))
            t.wg = float(2.0 * sig)  # H-alpha code uses wgau = 2*a[3]
            self.tree.insert("", "end", values=(idx+1, f"{cen:.5f}", f"{amp:.5g}", f"{sig:.5g}", f"{t.wg:.5g}", "OK"))
        self.master_app.fit_overlay = (xs.tolist(), multigaussian_model(xs, *popt).tolist())
        self.master_app.redraw()
        self.master_app.status(f"Multi-Gaussian fit: {len(lines)} lines")


    def _active_spectrum(self):
        try:
            aw = getattr(self.master_app, "active_window", None)
            if aw is not None and aw.winfo_exists():
                idx = getattr(aw, "selected_index", 0)
                if 0 <= idx < len(self.master_app.spectra):
                    return self.master_app.spectra[idx]
        except Exception:
            pass
        return self.master_app.spectra[0] if self.master_app.spectra else None

    def fit_voigt_visible(self):
        """Fit marked automatic/manual lines with Voigt profiles in current visible window."""
        self.fit_voigt_lines()

    def fit_voigt_lines(self, lines=None, preserve_view=True, show_messages=True, line_overrides=None):
        """Fit explicit template lines with the existing visible-window Voigt model.

        line_overrides is an optional dict keyed by id(template_line).  It is
        used by the Manual/Automatic/Single Fit editor so values initialized
        from Options can be changed by the user before pressing Fit without
        being overwritten by the global defaults.
        """
        self.last_residual_x = []
        self.last_residual_y = []
        if np is None:
            if show_messages:
                _showerror(self, "Fit Voigt", "numpy not available")
            return False, "numpy not available", []
        try:
            from scipy.optimize import curve_fit
        except Exception:
            msg = "scipy.optimize not available. Install scipy."
            if show_messages:
                _showerror(self, "Fit Voigt", msg)
            return False, msg, []
        sp = self._active_spectrum()
        if sp is None or not getattr(sp, "x", None):
            msg = "Load a spectrum first."
            if show_messages:
                _showinfo(self, "Fit Voigt", msg)
            return False, msg, []
        xlim, ylim = self.master_app.current_plot_view()
        lo, hi = sorted(xlim)
        xs = np.asarray([x for x in sp.x if lo <= x <= hi], dtype=float)
        ys = np.asarray([sp.y[i] for i, x in enumerate(sp.x) if lo <= x <= hi], dtype=float)
        if len(xs) < 8:
            msg = "Too few points in the visible window."
            if show_messages:
                _showinfo(self, "Fit Voigt", msg)
            return False, msg, []
        if lines is None:
            lines = [t for t in self.master_app.template_lines if lo <= t.wavelen <= hi]
        else:
            lines = list(lines)
        if not lines:
            msg = "No marked line in the visible window. Use search/manual marking before fitting."
            if show_messages:
                _showinfo(self, "Fit Voigt", msg)
            return False, msg, []
        xmin, xmax = float(xs.min()), float(xs.max())
        width = max(xmax - xmin, 1e-9)
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        # Estimate a sensible initial width from the x sampling and Options.
        dx = float(np.median(np.diff(np.sort(xs)))) if len(xs) > 2 else width/100.0
        line_overrides = line_overrides or {}
        # Options are used only to initialize fit windows.  During a fit,
        # per-row values edited in the open Manual/Automatic/Single Fit window
        # take precedence through line_overrides.  For the standalone Voigt
        # window, fall back to the template sign convention/options.
        default_fixed_wg = abs(safe_float(getattr(self.master_app.options, "fixed_wg", 0.5), 0.5))
        default_fixed_wl = abs(safe_float(getattr(self.master_app.options, "fixed_wl", 0.5), 0.5))
        min_sigma0 = max(abs(safe_float(self.sigma_var.get(), default_fixed_wg)) / 2.354820045, abs(dx), 1e-6)
        min_gamma0 = max(default_fixed_wl / 2.0, abs(dx), 1e-6)
        sigma0 = max(abs(safe_float(self.sigma_var.get(), default_fixed_wg)), abs(dx), 1e-6)
        gamma0 = max(default_fixed_wl / 2.0, abs(dx), 1e-6)
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        fixed_mask = [False, False]
        half_window = max(abs(safe_float(self.range_var.get(), width / 20.0)), width * 0.02, abs(dx) * 2.0)
        for t in lines:
            override = line_overrides.get(id(t), {})
            center0 = abs(safe_float(override.get("center"), t.fitwavelen or t.wavelen)) if override else t.wavelen
            peak_y = _nearest_y(sp.x, sp.y, center0)
            height = max(float(peak_y) - baseline, max(ys)-baseline, 1.0)
            area0 = max(height * sigma0 * math.sqrt(2.0 * math.pi), 1e-12)
            if override:
                # Manual/Automatic/Single Fit rows are initialized from Options
                # when the window opens, but the user-edited row values and
                # checkboxes must take precedence at fit time.
                row_fix_wg = bool(override.get("fix_wg", False))
                row_fix_wl = bool(override.get("fix_wl", False))
                wg_fwhm = abs(safe_float(override.get("wg"), getattr(t, "wg", 0.0) or default_fixed_wg))
                wl_fwhm = abs(safe_float(override.get("wl"), getattr(t, "wl", 0.0) or default_fixed_wl))
            else:
                # Standalone Voigt Fit has no editor overrides, so use the
                # template sign convention and the current Options defaults.
                row_fix_wg = bool(getattr(self.master_app.options, "fix_wg", False)) or getattr(t, "wg", 0.0) < 0
                row_fix_wl = bool(getattr(self.master_app.options, "fix_wl", False)) or getattr(t, "wl", 0.0) < 0
                wg_fwhm = default_fixed_wg if bool(getattr(self.master_app.options, "fix_wg", False)) else (abs(t.wg) if getattr(t, "wg", 0.0) else default_fixed_wg)
                wl_fwhm = default_fixed_wl if bool(getattr(self.master_app.options, "fix_wl", False)) else (abs(t.wl) if getattr(t, "wl", 0.0) else default_fixed_wl)
            if row_fix_wg:
                sig0 = max(wg_fwhm / 2.354820045, 1e-12)
            else:
                sig0 = max(wg_fwhm / 2.354820045, min_sigma0)
            if row_fix_wl:
                gam0 = max(wl_fwhm / 2.0, 1e-12)
            else:
                gam0 = max(wl_fwhm / 2.0, min_gamma0)
            p0.extend([area0, center0, max(sig0, 1e-6), max(gam0, 1e-6)])
            c_lo = max(xmin, center0 - half_window)
            c_hi = min(xmax, center0 + half_window)
            row_fix_center = bool(override.get("fix_center", False)) if override else (
                bool(getattr(self.master_app.options, "fix_wavelength", False))
                or safe_float(getattr(t, "fitwavelen", 0.0), 0.0) < 0
            )
            sigma_lo = max(abs(dx)*0.05, 1e-9)
            sigma_hi = max(width, sigma0*50.0)
            gamma_lo = max(abs(dx)*0.05, 1e-9)
            gamma_hi = max(width, gamma0*50.0)
            bounds_lo.extend([0.0, c_lo, sigma_lo, gamma_lo])
            bounds_hi.extend([np.inf, c_hi, sigma_hi, gamma_hi])
            fixed_mask.extend([False, row_fix_center, row_fix_wg, row_fix_wl])
        p0_full = np.asarray(p0, dtype=float)
        bounds_lo_full = np.asarray(bounds_lo, dtype=float)
        bounds_hi_full = np.asarray(bounds_hi, dtype=float)
        fixed_mask = np.asarray(fixed_mask, dtype=bool)
        free_mask = ~fixed_mask

        # Fixed parameters are removed from the optimizer parameter vector.
        # This keeps them exactly locked at the values currently visible in
        # the fit window, instead of only constraining them with narrow bounds.
        def _expand_fit_parameters(p_free):
            p_all = p0_full.copy()
            p_all[free_mask] = np.asarray(p_free, dtype=float)
            return p_all

        def _multivoigt_model_free(x, *p_free):
            return multivoigt_model(x, *_expand_fit_parameters(p_free))

        old_xlim, old_ylim = xlim, ylim
        try:
            popt_free, pcov = curve_fit(
                _multivoigt_model_free,
                xs,
                ys,
                p0=p0_full[free_mask],
                bounds=(bounds_lo_full[free_mask], bounds_hi_full[free_mask]),
                maxfev=max(2000, self.master_app.options.iterations*400),
            )
            popt = _expand_fit_parameters(popt_free)
        except Exception as e:
            msg = str(e)
            if show_messages:
                _showerror(self, "Fit Voigt", msg)
            return False, msg, []
        self.tree.delete(*self.tree.get_children())
        fit_results = []
        for idx, t in enumerate(lines):
            area, cen, sigma, gamma = popt[2+4*idx], popt[3+4*idx], abs(popt[4+4*idx]), abs(popt[5+4*idx])
            t.fitwavelen = float(cen)
            t.inte = float(area)
            fitted_wg = float(2.354820045 * sigma)   # Gaussian FWHM
            fitted_wl = float(2.0 * gamma)           # Lorentzian FWHM
            # Store/report both Voigt widths as positive FWHM values.  Fixed
            # widths are enforced by removing them from the optimizer vector;
            # the sign is not used as an output marker because it makes the
            # reported fit result misleading and has no physical meaning.
            t.wg = abs(fitted_wg)
            t.wl = abs(fitted_wl)
            peak_height = float(area * voigt_profile_unit(np.asarray([cen], dtype=float), cen, sigma, gamma)[0])
            # If the row is already identified, keep the identification and
            # complete Ek/Aki/gk/gi from LIBS.db so Save Template writes a
            # self-contained fit+assignment record.
            enriched = False
            try:
                enriched = bool(self.master_app.enrich_identified_template_line(t, tolerance=max(0.02, self.master_app.options.search_range)))
            except Exception:
                enriched = False
            status = "Voigt OK + DB" if enriched else ("Voigt OK" if getattr(t, "specie", "") else "Voigt OK, not ID")
            self.tree.insert("", "end", values=(idx+1, f"{cen:.5f}", f"{area:.5g}", f"{t.wg:.5g}", f"{t.wl:.5g}", status))
            fit_results.append({
                "key": id(t),
                "template_wavelength": float(t.wavelen),
                "fit_center": float(cen),
                "peak_intensity": peak_height,
                "lorentzian_width": float(t.wl),
                "gaussian_width": float(t.wg),
                "integrated_area": float(area),
            })
        fitted_y = multivoigt_model(xs, *popt)
        self.master_app.fit_overlay = (xs.tolist(), fitted_y.tolist())
        self.last_residual_x = xs.tolist()
        self.last_residual_y = (ys - fitted_y).tolist()
        self.master_app.notify_template_changed(redraw=False)
        self.master_app.redraw(preserve_view=True)
        if preserve_view:
            self.master_app.restore_plot_view(old_xlim, old_ylim)
        self.master_app.status(f"Voigt fit: {len(lines)} lines in the visible window")
        return True, f"Fit Voigt: {len(lines)} line(s)", fit_results

    def clear_overlay(self):
        self.master_app.fit_overlay = None
        self.master_app.redraw()


class ResidualsWindow(tk.Toplevel):
    """Compact residual plot for Manual Fit."""

    def __init__(self, master, x_values, residuals):
        super().__init__(master)
        self.fit_window = master
        self.master_app = master.master_app
        self.title("Residuals")
        self.geometry("900x260")
        self.minsize(500, 160)
        self.protocol("WM_DELETE_WINDOW", master.on_residuals_window_close)
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(self, text="matplotlib not available").pack(padx=20, pady=20)
            return
        self.fig = Figure(figsize=(12, 2.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._plot(x_values, residuals)
        center_window(self, master)

    def update_plot(self, x_values, residuals):
        self._plot(x_values, residuals)

    def _plot(self, x_values, residuals):
        self.ax.clear()
        self.ax.set_title("Residuals")
        self.ax.set_xlabel(f"Wavelength ({self.master_app.current_wavelength_unit_label()})")
        self.ax.set_ylabel("Residual (counts)")
        self.ax.plot(x_values, residuals, color="red", linewidth=1.0)
        self.ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.65)
        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()


class NeHalphaWindow(tk.Toplevel):
    """H-alpha electron density checkpoint from SDIMain calcolh()/Ne_from_H flow."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Ne from H-alpha - Unit16/SDIMain")
        self.geometry("620x360")
        self.minsize(560, 320)
        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, padx=10, pady=10)
        labels = [
            ("Number of lines", str(master.options.ha_lines)),
            ("wl1", str(master.options.ha_wl1)),
            ("dl1", str(master.options.ha_dl1)),
            ("Delta", str(master.options.ha_range)),
            ("wl2", str(master.options.ha_wl2)),
            ("dl2", str(master.options.ha_dl2)),
            ("kT", str(master.options.ha_kt)),
        ]
        self.vars = {}
        for r,(lab, val) in enumerate(labels):
            ttk.Label(frm, text=lab).grid(row=r, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=val); self.vars[lab]=v
            ttk.Entry(frm, textvariable=v, width=16).grid(row=r, column=1, sticky="w")
        ttk.Button(frm, text="Fit Hα and estimate Ne", command=self.run).grid(row=0, column=2, rowspan=2, padx=15, sticky="n")
        self.out = tk.Text(frm, height=10, width=72)
        self.out.grid(row=len(labels), column=0, columnspan=3, pady=8, sticky="nsew")
        frm.rowconfigure(len(labels), weight=1)
        frm.columnconfigure(2, weight=1)
        self.show_fit_window_on_spectrum()
        center_window(self, master)

    def show_fit_window_on_spectrum(self):
        if not self.master_app.spectra or not getattr(self.master_app, "ax", None):
            self.master_app.status("H-alpha fit: load a spectrum before fitting.")
            return
        wl1 = safe_float(self.vars["wl1"].get(), self.master_app.options.ha_wl1)
        delta = abs(safe_float(self.vars["Delta"].get(), self.master_app.options.ha_range)) or 1.0
        self.master_app.clear_fit_artists()
        self.master_app.ax.set_xlim(wl1 - delta, wl1 + delta)
        self.master_app.full_y_main_visible_x()
        self.master_app.canvas.draw_idle()
        self.master_app._update_xscroll()
        self.lift(self.master_app)
        try:
            self.focus_set()
        except Exception:
            pass

    def _initial_amplitude(self, xs, ys, center, baseline):
        idx = int(np.argmin(np.abs(xs - center)))
        return max(float(ys[idx] - baseline), float(max(ys) - baseline) * 0.25, 1.0)

    def run(self):
        if np is None:
            _showerror(self, "Ne", "numpy not available")
            return
        try:
            from scipy.optimize import curve_fit
        except Exception:
            _showerror(self, "Ne", "scipy.optimize not available")
            return
        if not self.master_app.spectra:
            _showinfo(self, "Ne", "Load a spectrum first.")
            return
        sp = self.master_app.spectra[0]
        nlines = 2 if safe_int(self.vars["Number of lines"].get(), self.master_app.options.ha_lines) == 2 else 1
        wl1 = safe_float(self.vars["wl1"].get(), self.master_app.options.ha_wl1)
        dl1 = abs(safe_float(self.vars["dl1"].get(), self.master_app.options.ha_dl1)) or 1.0
        wl2 = safe_float(self.vars["wl2"].get(), self.master_app.options.ha_wl2)
        dl2 = abs(safe_float(self.vars["dl2"].get(), self.master_app.options.ha_dl2)) or dl1
        delta = abs(safe_float(self.vars["Delta"].get(), self.master_app.options.ha_range)) or 1.0
        lo, hi = wl1 - delta, wl1 + delta
        if getattr(self.master_app, "ax", None):
            self.master_app.clear_fit_artists()
            self.master_app.ax.set_xlim(lo, hi)
            self.master_app.full_y_main_visible_x()
            self.master_app.canvas.draw_idle()
            self.master_app._update_xscroll()
            try:
                self.master_app.update_idletasks()
            except Exception:
                pass
        points = [(x, sp.y[i]) for i, x in enumerate(sp.x) if lo <= x <= hi]
        xs = np.asarray([x for x, _ in points], dtype=float)
        ys = np.asarray([y for _, y in points], dtype=float)
        min_points = 7 if nlines == 1 else 10
        if len(xs) < min_points:
            _showinfo(self, "Ne", "Too few points around Hα.")
            return
        baseline = float(np.percentile(ys, 5))
        p0 = [baseline, self._initial_amplitude(xs, ys, wl1, baseline), wl1, dl1]
        lower = [float(min(ys) - abs(max(ys) - min(ys))), 0.0, lo, 1e-9]
        upper = [float(max(ys) + abs(max(ys) - min(ys))), np.inf, hi, max(2.0 * delta, dl1)]
        if nlines == 2:
            wl2_start = min(max(wl2, lo), hi)
            p0.extend([self._initial_amplitude(xs, ys, wl2_start, baseline), wl2_start, dl2])
            lower.extend([0.0, lo, 1e-9])
            upper.extend([np.inf, hi, max(2.0 * delta, dl2)])
        try:
            popt, _ = curve_fit(halpha_lorentzian_model, xs, ys, p0=p0, bounds=(lower, upper), maxfev=8000)
        except Exception as e:
            _showerror(self, "Ne", str(e)); return
        fitted = []
        for i in range(1, len(popt), 3):
            fitted.append((float(popt[i]), float(popt[i + 1]), abs(float(popt[i + 2]))))
        primary_width = fitted[0][2]
        primary_center = fitted[0][1]
        inst = float(self.master_app.options.instrumental_width)
        if getattr(self.master_app.options, "echelle", False):
            inst = inst / 5000.0 * primary_center
        if primary_width <= 0:
            corrected_lorentz = primary_width
        else:
            corrected_lorentz = max(primary_width - inst*inst/primary_width, 0.0)
        kt = safe_float(self.vars["kT"].get(), 1.0)
        try:
            ne_value, T, alfa = libspp_halpha_ne(corrected_lorentz, kt)
            ne_error = None
        except Exception as e:
            ne_value, T, alfa = None, 11600.0 * kt, None
            ne_error = str(e)
        self.master_app.fit_overlay = (xs.tolist(), halpha_lorentzian_model(xs, *popt).tolist())
        self.master_app.redraw(preserve_view=True)
        self.out.delete("1.0", "end")
        lines = [
            f"Fit window: {lo:.4f} - {hi:.4f} Å",
            f"Model: baseline + {nlines} Lorentzian component{'s' if nlines == 2 else ''}",
            f"kT: {kt:.6g}  (T ≈ {T:.0f} K)",
            "",
        ]
        for idx, (_, center, width) in enumerate(fitted, start=1):
            lines.append(f"Line {idx}: center = {center:.4f} Å, Lorentzian FWHM = {width:.4f} Å")
        lines.extend([
            "",
            f"Instrumental width: {inst:.4f} Å",
            f"Corrected primary Lorentzian width: {corrected_lorentz:.4f} Å",
        ])
        if ne_error:
            lines.extend([
                "Ne calculation failed:",
                ne_error,
            ])
            self.master_app.last_halpha_result = {
                "available": False,
                "center": primary_center,
                "lorentzian_width": primary_width,
                "corrected_lorentzian_width": corrected_lorentz,
                "gaussian_width": None,
                "intensity": fitted[0][0] if fitted else None,
                "integral": None,
                "kt": kt,
                "temperature_k": T,
                "ne": None,
                "alpha": alfa,
                "formula": "H-alpha Stark broadening: Ne = 8.02e12 * (FWHM/alpha)^1.5",
                "error": ne_error,
            }
            status = "H-alpha fit complete; Ne calculation failed"
        else:
            lines.extend([
                f"Alpha correction: {alfa:.6g}",
                f"Ne: {ne_value:.6e} cm^-3",
                f"Ne / 1e17: {ne_value / 1.0e17:.6g}",
            ])
            self.master_app.session_ne = ne_value
            self.master_app.session_ne_source = "H-alpha"
            self.master_app.last_halpha_result = {
                "available": True,
                "center": primary_center,
                "lorentzian_width": primary_width,
                "corrected_lorentzian_width": corrected_lorentz,
                "gaussian_width": None,
                "intensity": fitted[0][0] if fitted else None,
                "integral": None,
                "kt": kt,
                "temperature_k": T,
                "ne": ne_value,
                "alpha": alfa,
                "formula": "H-alpha Stark broadening: Ne = 8.02e12 * (FWHM/alpha)^1.5",
                "error": None,
            }
            status = f"H-alpha fit complete; Ne={ne_value:.3e} cm^-3"
        self.out.insert("end", "\n".join(lines) + "\n")
        self.master_app.status(status)


class SahaBoltzmannWindow(tk.Toplevel):
    """v6 Saha-Boltzmann front-end using current fitted template lines."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Saha-Boltzmann")
        self.geometry("1050x700")
        self.minsize(880, 560)
        self.saha_groups = {}
        self.saha_fits = {}
        self.included_elements = set()
        self.skipped_lines = 0
        self.current_ne = None
        self.representative_kt = None
        self.last_valid_mean_kt = None
        self.auto_excluded_elements = set()
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        left = ttk.Frame(top)
        left.pack(side="left")
        ttk.Button(left, text="Compute Plot", command=self.compute).pack(side="left")
        ttk.Button(left, text="CF-LIBS", command=self.open_cflibs).pack(side="left", padx=(12, 3))
        self.mode_var = tk.StringVar(value="Mean temperature")
        ttk.Label(left, text="Initial kT (eV)").pack(side="left", padx=(12, 3))
        self.initial_kt_var = tk.StringVar(value="1")
        ttk.Entry(left, textvariable=self.initial_kt_var, width=8).pack(side="left")
        right = ttk.Frame(top)
        right.pack(side="right", fill="x", expand=True)
        self.summary_var = tk.StringVar(value="Ready")
        ttk.Label(right, textvariable=self.summary_var, width=38).pack(side="left", padx=(12, 8), fill="x", expand=True)
        ttk.Button(right, text="Check SA", command=self.open_sac_check).pack(side="right")
        cols=("use", "element", "lines", "kT eV", "q", "Z I", "Z II")
        self.tree=ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=115, anchor="center")
        self.tree.column("use", width=95, anchor="center")
        self.tree.pack(fill="x", padx=6, pady=5)
        self.tree.bind("<Double-1>", self.toggle_selected_element)
        self.tree.bind("<space>", self.toggle_selected_element)
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_changed)
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(self, text="matplotlib not available").pack(fill="both", expand=True, padx=10, pady=10)
            self.fig = self.ax = self.canvas = None
        else:
            self.fig = Figure(figsize=(9, 4.8), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
            self.canvas.mpl_connect("button_press_event", self.on_plot_click)
        self.plot_points = []
        self.after(100, self.compute)

    def compute(self):
        self.tree.delete(*self.tree.get_children())
        ne = self._electron_density()
        if ne is None:
            return
        kt = safe_float(self.initial_kt_var.get(), 1.0)
        if kt <= 0.0:
            kt = 1.0
        skipped = 0
        groups = {}
        fits = {}
        for _ in range(25):
            groups, skipped = libspp_saha_boltzmann_groups(
                self.master_app,
                ne,
                kt,
            )
            fits = libspp_fit_saha_boltzmann(self.master_app, groups)
            new_kt = libspp_weighted_temperature(fits, self.master_app.options.kt_low, self.master_app.options.kt_high)
            if new_kt <= 0.0:
                new_kt = libspp_weighted_temperature(fits, 0.0, float("inf"))
            if new_kt <= 0.0:
                break
            if abs(new_kt - kt) / new_kt <= 0.01:
                kt = new_kt
                groups, skipped = libspp_saha_boltzmann_groups(
                    self.master_app,
                    ne,
                    kt,
                )
                fits = libspp_fit_saha_boltzmann(self.master_app, groups)
                break
            kt = new_kt
        if not fits:
            self.summary_var.set(f"No valid Saha-Boltzmann fit; skipped {skipped} template line(s)")
            _showinfo(self, "Saha-Boltzmann", f"No valid plot points. Skipped {skipped} incomplete template line(s).")
            self.saha_groups = groups
            self.saha_fits = {}
            self.skipped_lines = skipped
            self.current_ne = ne
            self.included_elements = set()
            self.auto_excluded_elements = set()
            self.representative_kt = None
            self.populate_tree()
            self._draw_plot(groups, {}, None)
            return
        self.saha_groups = groups
        self.saha_fits = fits
        self.skipped_lines = skipped
        self.current_ne = ne
        self.included_elements = self._default_included_elements(fits)
        self.auto_excluded_elements = set(fits.keys()) - set(self.included_elements)
        self.representative_kt = self._mean_temperature()
        self.last_valid_mean_kt = self.representative_kt
        if self.representative_kt is None:
            self.summary_var.set("No elements inside the configured temperature range")
            _showwarning(self, "Saha-Boltzmann", "No element temperatures are inside the configured Options temperature range.")
        self.populate_tree()
        self.refresh_temperature_display()

    def _temperature_range(self):
        low = safe_float(getattr(self.master_app.options, "kt_low", 0.0), 0.0)
        high = safe_float(getattr(self.master_app.options, "kt_high", 0.0), 0.0)
        if high and low > high:
            low, high = high, low
        return low, high

    def _temperature_in_range(self, kt):
        low, high = self._temperature_range()
        if low and kt <= low:
            return False
        if high and kt >= high:
            return False
        return kt > 0.0

    def _default_included_elements(self, fits):
        return {element for element, result in fits.items() if self._temperature_in_range(safe_float(result.get("kt", 0.0), 0.0))}

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for element, result in sorted(self.saha_fits.items()):
            self.tree.insert("", "end", iid=element, values=(
                "Yes" if element in self.included_elements else "No",
                element,
                result["nlines"],
                f"{result['kt']:.4g}",
                f"{result['q']:.4g}",
                f"{result['z1']:.4g}",
                f"{result['z2']:.4g}",
            ))

    def _mean_temperature(self):
        total = 0.0
        weight = 0.0
        for element in self.included_elements:
            result = self.saha_fits.get(element)
            if not result:
                continue
            nlines = max(1, safe_int(result.get("nlines", 0), 0))
            kt = safe_float(result.get("kt", 0.0), 0.0)
            if kt > 0.0:
                total += kt * nlines
                weight += nlines
        return total / weight if weight else None

    def _fixed_temperature_refits(self, representative_kt):
        if not representative_kt or representative_kt <= 0.0:
            return {}
        return libspp_refit_saha_fixed_temperature(self.master_app, self.saha_groups, representative_kt)

    def _plot_x_limits(self, groups):
        xs = [p["x"] for pts in groups.values() for p in pts]
        if not xs:
            return None
        x0, x1 = min(xs), max(xs)
        if x0 == x1:
            pad = max(abs(x0) * 0.05, 0.05)
        else:
            pad = abs(x1 - x0) * 0.05
        return x0 - pad, x1 + pad

    def selected_element(self):
        selected = self.tree.selection()
        if selected:
            return selected[0]
        return next(iter(sorted(self.saha_fits)), None)

    def toggle_selected_element(self, event=None):
        if self.mode_var.get() != "Mean temperature":
            self.master_app.status("Saha-Boltzmann: element exclusion is used only in Mean temperature mode.")
            return "break"
        element = self.selected_element()
        if not element:
            return "break"
        if element in self.included_elements:
            self.included_elements.remove(element)
        else:
            self.included_elements.add(element)
        self.populate_tree()
        self.tree.selection_set(element)
        mean_kt = self._mean_temperature()
        if mean_kt is None:
            self.representative_kt = self.last_valid_mean_kt
            self.summary_var.set("All elements excluded; mean temperature unchanged")
            _showwarning(self, "Saha-Boltzmann", "All elements are excluded from the mean temperature.")
            self.master_app.status("Saha-Boltzmann: all elements excluded; mean temperature unchanged.")
        else:
            self.representative_kt = mean_kt
            self.last_valid_mean_kt = mean_kt
        self.refresh_temperature_display()
        return "break"

    def on_mode_changed(self, event=None):
        self.refresh_temperature_display()

    def on_selection_changed(self, event=None):
        if self.mode_var.get() == "Single element temperature":
            self.refresh_temperature_display()

    def refresh_temperature_display(self):
        if not self.saha_fits:
            return
        response_text = "Apply After response correction used" if _apply_after_response_enabled(self.master_app) else "no Apply After response correction"
        selected_element = None
        representative_mode = "mean temperature"
        if self.mode_var.get() == "Single element temperature":
            element = self.selected_element()
            selected_element = element
            representative_mode = "selected element"
            result = self.saha_fits.get(element) if element else None
            if result:
                representative_kt = result["kt"]
                self.summary_var.set(
                    f"{element} kT={representative_kt:.4g} eV, Ne={self.current_ne:.3e} e/cm3, skipped {self.skipped_lines}; {response_text}"
                )
                self.master_app.status(f"Saha-Boltzmann: {element} kT={representative_kt:.4g} eV")
            else:
                representative_kt = None
                self.summary_var.set("Select an element for single-element temperature")
        else:
            representative_kt = self.representative_kt or self.last_valid_mean_kt
            included = len(self.included_elements)
            total = len(self.saha_fits)
            low, high = self._temperature_range()
            if representative_kt is None:
                self.summary_var.set(
                    f"No included elements in kT range {low:g} - {high:g} eV; "
                    f"Ne={self.current_ne:.3e} e/cm3, skipped {self.skipped_lines}"
                )
            else:
                self.summary_var.set(
                    f"Mean kT={representative_kt:.4g} eV, Ne={self.current_ne:.3e} e/cm3, "
                    f"included {included}/{total}, range {low:g}-{high:g} eV, skipped {self.skipped_lines}; {response_text}"
                )
                self.master_app.status(
                    f"Saha-Boltzmann: mean kT={representative_kt:.4g} eV, included {included}/{total}, Ne={self.current_ne:.3e} e/cm3"
                )
        if representative_kt and representative_kt > 0.0:
            self.master_app.session_temperature = representative_kt
            self.master_app.session_temperature_source = (
                "selected element" if representative_mode == "selected element" else "Saha-Boltzmann mean"
            )
        low, high = self._temperature_range()
        self.master_app.last_saha_boltzmann = {
            "elements": [
                {
                    "element": element,
                    "temperature": result.get("kt"),
                    "nlines": result.get("nlines"),
                    "included": element in self.included_elements,
                }
                for element, result in sorted(self.saha_fits.items())
            ],
            "temperature_range": (low, high),
            "mean_temperature": self._mean_temperature(),
            "representative_temperature": representative_kt,
            "representative_mode": representative_mode,
            "selected_element": selected_element,
            "electron_density": self.current_ne,
            "skipped_lines": self.skipped_lines,
        }
        self._draw_plot(self.saha_groups, self.saha_fits, representative_kt)

    def _electron_density(self):
        ne = safe_float(getattr(self.master_app, "session_ne", 0.0), 0.0)
        if ne > 0.0:
            return ne
        ne = simpledialog.askfloat(
            "Electron Density",
            "Electron density Ne (e/cm3):",
            initialvalue=1.0e17,
            minvalue=0.0,
            parent=_prepare_messagebox_parent(self),
        )
        if ne is None:
            return None
        self.master_app.session_ne = ne
        self.master_app.session_ne_source = "user input"
        return ne

    def _clear_plot(self):
        if self.ax is None:
            return
        self.plot_points = []
        self.ax.clear()
        self.canvas.draw_idle()

    def _draw_plot(self, groups, fits, representative_kt=None):
        if self.ax is None:
            return
        fixed_refits = self._fixed_temperature_refits(representative_kt)
        plot_xlim = self._plot_x_limits(groups)
        self.plot_points = []
        self.ax.clear()
        self.ax.set_title("Saha-Boltzmann")
        self.ax.set_xlabel("Upper energy / Saha-Boltzmann coordinate (eV)")
        self.ax.set_ylabel("ln(I / |Aki gk|)")
        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
        for group_idx, (element, pts) in enumerate(sorted(groups.items())):
            if not pts:
                continue
            included = element in self.included_elements
            alpha = 1.0 if included or self.mode_var.get() != "Mean temperature" else 0.35
            color = colors[group_idx % len(colors)] if colors else "#1f77b4"
            label_used = False
            for p in pts:
                inactive = bool(p.get("inactive"))
                point_color = "0.6" if inactive else color
                label = element if not label_used else "_nolegend_"
                plot_y, sac_marker = _sac_corrected_plot_y(self.master_app, p)
                marker = "*" if sac_marker else "o"
                size = 70 if sac_marker else 24
                self.ax.scatter([p["x"]], [plot_y], s=size, marker=marker, alpha=(0.65 if inactive else alpha), color=point_color, label=label)
                self.plot_points.append({"x": p["x"], "y": plot_y, "line": p.get("line"), "inactive": inactive})
                label_used = True
            result = fits.get(element)
            if result:
                fixed = fixed_refits.get(element)
                if fixed and plot_xlim:
                    x0, x1 = plot_xlim
                    y0 = fixed["slope"] * x0 + fixed["q_fixed"]
                    y1 = fixed["slope"] * x1 + fixed["q_fixed"]
                    self.ax.plot([x0, x1], [y0, y1], linewidth=1.0, alpha=alpha)
        if plot_xlim:
            self.ax.set_xlim(*plot_xlim)
        self.ax.margins(x=0.05, y=0.05)
        if plot_xlim:
            self.ax.set_xlim(*plot_xlim)
        self.ax.legend(loc="best", fontsize=8)
        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()

    def on_plot_click(self, event):
        if event.inaxes is not self.ax or not _matplotlib_event_has_shift(event) or event.button not in (1, 3):
            return
        point = self._nearest_plot_point(event)
        if not point or point.get("line") is None:
            return
        activate = event.button == 3
        _set_template_line_active(point["line"], activate)
        self.master_app.notify_template_changed(redraw=True)
        self.master_app.status("Point reactivated" if activate else "Point excluded from Saha-Boltzmann fit")
        self.compute()

    def open_cflibs(self):
        win = self.master_app.show_cflibs()
        bring_window_to_front(win, self)
        return win

    def open_sac_check(self):
        win = self.master_app.show_sac_check()
        bring_window_to_front(win, self)
        return win

    def _nearest_plot_point(self, event, max_pixels=12.0):
        if not self.plot_points or event.x is None or event.y is None:
            return None
        best = None
        best_dist = None
        for point in self.plot_points:
            try:
                px, py = self.ax.transData.transform((point["x"], point["y"]))
            except Exception:
                continue
            dist = math.hypot(px - event.x, py - event.y)
            if best_dist is None or dist < best_dist:
                best = point
                best_dist = dist
        return best if best is not None and best_dist is not None and best_dist <= max_pixels else None


def _roman_ion(ion: int) -> str:
    return "I" if int(ion) == 1 else "II" if int(ion) == 2 else str(ion)


def _matplotlib_event_has_shift(event) -> bool:
    key = str(getattr(event, "key", "") or "").lower()
    if "shift" in key:
        return True
    gui_event = getattr(event, "guiEvent", None)
    try:
        return bool(gui_event.state & 0x0001)
    except Exception:
        return False


def _set_template_line_active(line: TemplateLine, active: bool):
    aki = safe_float(getattr(line, "aki", 0.0), 0.0)
    if aki == 0.0:
        return
    line.aki = abs(aki) if active else -abs(aki)


def _fit_values_already_response_corrected(app: "MainWindow") -> bool:
    return any(getattr(sp, "response_corrected", False) for sp in getattr(app, "spectra", []))


def _apply_after_response_enabled(app: "MainWindow") -> bool:
    try:
        return (
            bool(getattr(app.options, "apply_response", False))
            and bool(getattr(app.options, "apply_after", False))
            and getattr(app, "response", None) is not None
            and bool(getattr(app.response, "x", []))
            and not _fit_values_already_response_corrected(app)
        )
    except Exception:
        return False


def _template_line_center(line: TemplateLine) -> float:
    return abs(line.fitwavelen) if getattr(line, "fitwavelen", 0.0) else (line.asswavelen or line.wavelen)


def _template_line_intensity(line: TemplateLine) -> float:
    if _template_line_has_fit_error(line):
        return 0.0
    inte = safe_float(getattr(line, "inte", 0.0), 0.0)
    return inte if inte > 0.0 else safe_float(getattr(line, "templint", 0.0), 0.0)


def _is_template_error_value(value) -> bool:
    return isinstance(value, str) and value.strip().upper() == "ERROR"


def _template_line_has_fit_error(line: TemplateLine) -> bool:
    return any(
        _is_template_error_value(getattr(line, attr, ""))
        for attr in ("inte", "wl", "wg", "error_inte", "fitinte")
    )


def _sac_factor_for_line(line: TemplateLine) -> Optional[float]:
    """Return the SAC factor selected in the Show SA table for this line.

    SAC is not recomputed here.  It is used only when the Show SA row has
    Use/checkbox = Yes and the already-calculated SAC value is >= 1.
    """
    try:
        if not bool(getattr(line, "sa_use", False)):
            return None
        sac = safe_float(getattr(line, "sa_sac", ""), 0.0)
        if sac >= 1.0 and math.isfinite(sac):
            return sac
    except Exception:
        pass
    return None


def _sac_corrected_plot_y(app: "MainWindow", point: dict) -> tuple[float, bool]:
    """Return plot ordinate and whether the SAC marker must be used."""
    y = safe_float(point.get("y"), 0.0)
    if not bool(getattr(app, "apply_sac_correction", False)):
        return y, False
    line = point.get("line")
    if line is None:
        return y, False
    sac = _sac_factor_for_line(line)
    if sac is None:
        return y, False
    try:
        return y + math.log(sac), True
    except Exception:
        return y, False


def _sac_corrected_fit_y(app: "MainWindow", point: dict) -> float:
    """Return the same ordinate used in the plot, for refitting after Apply SAC."""
    return _sac_corrected_plot_y(app, point)[0]


def _response_factor(app: "MainWindow", wavelength: float) -> float:
    """Original showboltz()/calcola(): divide line intensity by instrumental efficiency."""
    try:
        if _apply_after_response_enabled(app):
            val = app.response.value_at(wavelength)
            return val if val not in (0, None) and math.isfinite(val) else 1.0
    except Exception:
        pass
    return 1.0


def libspp_boltzmann_groups_with_skips(
    app: "MainWindow",
):
    """Build Boltzmann groups from current template lines.

    Reconstructed from Unit6/showboltz(), Unit9 and SDIMain/calcola():
        x = Ek * 1.23985e-4  # cm^-1 -> eV
        y = ln( Icorr / |Aki*gk| )
        Icorr = I / instrument_response

    Returns a dictionary keyed by (specie, ion) with point dictionaries.
    """
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for idx, t in enumerate(app.template_lines, start=1):
        if _template_line_has_fit_error(t):
            continue
        specie = str(getattr(t, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(t, "ion", 0), 0)
        aki = safe_float(getattr(t, "aki", 0.0), 0.0)
        gk = safe_float(getattr(t, "gk", 0.0), 0.0)
        ek = safe_float(getattr(t, "ek", 0.0), 0.0)
        if not specie or not ion or not aki or not gk or not ek:
            continue
        inte = safe_float(getattr(t, "inte", 0.0), 0.0)
        if inte <= 0.0:
            inte = safe_float(getattr(t, "templint", 0.0), 0.0)
        if inte <= 0:
            continue
        fit_center = safe_float(getattr(t, "fitwavelen", 0.0), 0.0)
        center = abs(fit_center) if fit_center else (
            safe_float(getattr(t, "asswavelen", 0.0), 0.0)
            or safe_float(getattr(t, "wavelen", 0.0), 0.0)
        )
        if center <= 0.0:
            continue
        eff = _response_factor(app, center)
        icorr = inte / eff
        if icorr <= 0:
            continue
        ek_ev = ek * 1.23985e-4
        y = math.log(icorr / abs(aki * gk))
        groups[(specie, ion)].append({
            "x": ek_ev,
            "y": y,
            "line": t,
            "icorr": icorr,
            "eff": eff,
            "inactive": aki < 0.0,
        })
    skipped = len(app.template_lines) - sum(1 for pts in groups.values() for p in pts if not p.get("inactive"))
    return groups, skipped


def libspp_boltzmann_groups(
    app: "MainWindow",
):
    groups, _skipped = libspp_boltzmann_groups_with_skips(app)
    return groups


def libspp_saha_boltzmann_groups(
    app: "MainWindow",
    ne: float,
    kt: float,
):
    """Build Unit27 Saha-Boltzmann plot points grouped by element.

    Unit6/Unit27 uses neutral lines as ordinary Boltzmann points and shifts
    singly-ionized points by Eion and the Saha electron-density term:
        x(I)  = Ek
        y(I)  = ln(I / |Aki*gk|)
        x(II) = Eion + Ek
        y(II) = ln(I / |Aki*gk|) - ln(6.04e21/Ne * kT^1.5)
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    skipped = 0
    metadata_cache: dict[str, dict] = {}
    for idx, t in enumerate(app.template_lines, start=1):
        if _template_line_has_fit_error(t):
            skipped += 1
            continue
        specie = str(getattr(t, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(t, "ion", 0), 0)
        aki = safe_float(getattr(t, "aki", 0.0), 0.0)
        gk = safe_float(getattr(t, "gk", 0.0), 0.0)
        ek = safe_float(getattr(t, "ek", 0.0), 0.0)
        if not specie or ion not in (1, 2) or not aki or not gk or not ek:
            skipped += 1
            continue
        inte = safe_float(getattr(t, "inte", 0.0), 0.0)
        if inte <= 0.0:
            inte = safe_float(getattr(t, "templint", 0.0), 0.0)
        if inte <= 0.0:
            skipped += 1
            continue
        fit_center = safe_float(getattr(t, "fitwavelen", 0.0), 0.0)
        center = abs(fit_center) if fit_center else (
            safe_float(getattr(t, "asswavelen", 0.0), 0.0)
            or safe_float(getattr(t, "wavelen", 0.0), 0.0)
        )
        if center <= 0.0:
            skipped += 1
            continue
        eff = _response_factor(app, center)
        icorr = inte / eff
        if icorr <= 0.0:
            skipped += 1
            continue
        ek_ev = ek * 1.23985e-4
        y = math.log(icorr / abs(aki * gk))
        x = ek_ev
        if ion == 2:
            if ne <= 0.0 or kt <= 0.0:
                skipped += 1
                continue
            if specie not in metadata_cache:
                try:
                    metadata_cache[specie] = app.libs_db.element_metadata(specie)
                except Exception:
                    metadata_cache[specie] = {}
            eion = safe_float(metadata_cache[specie].get("en_ion"), 0.0) * 1.23985e-4
            if eion <= 0.0:
                skipped += 1
                continue
            x = eion + ek_ev
            y -= math.log(6.04e21 / ne * math.pow(kt, 1.5))
        groups[specie].append({
            "x": x,
            "y": y,
            "line": t,
            "ion": ion,
            "icorr": icorr,
            "eff": eff,
            "center": center,
            "inactive": aki < 0.0,
        })
    skipped += sum(1 for pts in groups.values() for p in pts if p.get("inactive"))
    return groups, skipped


def libspp_fit_saha_boltzmann(app: "MainWindow", groups: dict[str, list[dict]]):
    results = {}
    for element, pts in groups.items():
        active_pts = [p for p in pts if not p.get("inactive")]
        if len(active_pts) < 2:
            continue
        fit = linear_fit([p["x"] for p in active_pts], [_sac_corrected_fit_y(app, p) for p in active_pts])
        if not fit:
            continue
        slope, intercept = fit
        kt = -1.0 / slope if slope != 0.0 else 0.0
        if kt <= 0.0:
            continue
        try:
            z1 = app.libs_db.partition_function(element, 1, kt * 11604.45)
        except Exception:
            z1 = 1.0
        try:
            z2 = app.libs_db.partition_function(element, 2, kt * 11604.45)
        except Exception:
            z2 = 1.0
        results[element] = {
            "species": element, "nlines": len(active_pts), "kt": kt, "q": intercept,
            "slope": slope, "z1": z1, "z2": z2, "points": active_pts
        }
    return results


def libspp_refit_saha_fixed_temperature(app: "MainWindow", groups: dict[str, list[dict]], kt: float):
    if kt <= 0.0:
        return {}
    slope = -1.0 / kt
    results = {}
    for element, pts in groups.items():
        active_pts = [p for p in pts if not p.get("inactive")]
        if not active_pts:
            continue
        intercept = sum(_sac_corrected_fit_y(app, p) - slope * p["x"] for p in active_pts) / len(active_pts)
        results[element] = {
            "species": element,
            "nlines": len(active_pts),
            "kt": kt,
            "slope": slope,
            "q_fixed": intercept,
            "points": active_pts,
        }
    return results


def libspp_fit_boltzmann(app: "MainWindow", groups):
    """Fit Boltzmann lines and compute kT, q and Z(T), as in calcbo()/calcola()."""
    results = {}
    for key, pts in groups.items():
        active_pts = [p for p in pts if not p.get("inactive")]
        if len(active_pts) < 2:
            continue
        x = [p["x"] for p in active_pts]
        y = [_sac_corrected_fit_y(app, p) for p in active_pts]
        # y = [p["y"] for p in active_pts]
        fit = linear_fit(x, y)
        if not fit:
            continue
        slope, intercept = fit
        kt = -1.0 / slope if slope != 0 else 0.0
        if kt <= 0:
            continue
        specie, ion = key
        try:
            z = app.libs_db.partition_function(specie, ion, kt * 11604.45)
        except Exception:
            z = 1.0
        # q is the intercept of ln(I/Ag) = q - Ek/kT
        results[key] = {"species": specie, "ion": ion, "nlines": len(active_pts), "kt": kt, "q": intercept, "z": z, "points": active_pts}
    return results


def libspp_fit_boltzmann_fixed_temperature(app: "MainWindow", groups, kt: float):
    """Fit Boltzmann intercepts at fixed kT for CF-LIBS concentration work."""
    results = {}
    if kt <= 0.0:
        return results
    for key, pts in groups.items():
        active_pts = [p for p in pts if not p.get("inactive")]
        if not active_pts:
            continue
        specie, ion = key
        intercept = sum(_sac_corrected_fit_y(app, p) + p["x"] / kt for p in active_pts) / len(active_pts)
        # intercept = sum(p["y"] + p["x"] / kt for p in active_pts) / len(active_pts)
        try:
            z = app.libs_db.partition_function(specie, ion, kt * 11604.45)
        except Exception:
            z = 1.0
        results[key] = {
            "species": specie,
            "ion": ion,
            "nlines": len(active_pts),
            "kt": kt,
            "q": intercept,
            "q_at_t": intercept,
            "z": z,
            "points": active_pts,
            "slope": -1.0 / kt,
        }
    return results


def libspp_weighted_temperature(fits: dict, kt_low: float, kt_high: float) -> float:
    """Original calcola(): weighted mean kT by number of lines, excluding out-of-range fits."""
    num = 0.0
    den = 0.0
    for r in fits.values():
        kt = r.get("kt", 0.0)
        n = r.get("nlines", 0)
        if kt_low < kt < kt_high and n > 0:
            num += kt * n
            den += n
    return num / den if den else 0.0


def libspp_recompute_q_at_temperature(fits: dict, kt: float):
    """Recompute q at selected/mean temperature, as recovered from calcola()."""
    if kt <= 0:
        return
    for r in fits.values():
        pts = r.get("points", [])
        if not pts:
            continue
        vals = [p["y"] + p["x"] / kt for p in pts]
        r["q_at_t"] = sum(vals) / len(vals)


def libspp_saha_cflibs(app: "MainWindow", fits: dict, kt: float, ne: Optional[float] = None):
    """Original-like CF-LIBS concentration estimate.

    The recovered Borland code uses:
        population_i = exp(q_i) * Z_i(T)
        conc = N_I + N_II
        neutral_ratio = N_I / (N_I + N_II)
    If only one ionization stage is present, Saha is used to infer the missing stage.
    """
    if kt <= 0:
        return []
    ne = ne or app.options.ne_low or 1e16
    libs = app.libs_db
    elements = sorted({sp for sp, _ion in fits.keys()})
    rows = []
    for sp in elements:
        r1 = fits.get((sp, 1))
        r2 = fits.get((sp, 2))
        try:
            meta = libs.element_metadata(sp)
        except Exception:
            meta = {}
        mass = safe_float(meta.get("m_atomica"), 1.0) or 1.0
        eion = safe_float(meta.get("en_ion"), 0.0) * 0.000123985
        z1 = r1.get("z") if r1 else libs.partition_function(sp, 1, kt * 11604.45)
        z2 = r2.get("z") if r2 else libs.partition_function(sp, 2, kt * 11604.45)
        n1 = math.exp(r1.get("q_at_t", r1.get("q", 0.0))) * z1 if r1 else 0.0
        n2 = math.exp(r2.get("q_at_t", r2.get("q", 0.0))) * z2 if r2 else 0.0
        # Fill missing stage with the same Saha balance used in Unit9/calcola().
        saha_factor = 6.04e21 / ne * (kt ** 1.5) * (z2 / z1 if z1 else 1.0) * math.exp(-eion / kt) if ne else 0.0
        if n1 > 0 and n2 <= 0:
            n2 = n1 * saha_factor
        elif n2 > 0 and n1 <= 0 and saha_factor > 0:
            n1 = n2 / saha_factor
        conc = n1 + n2
        neutral_ratio = n1 / conc if conc > 0 else 0.0
        ion_neutral_ratio = n2 / n1 if n1 > 0 else float("inf") if n2 > 0 else 0.0
        rows.append({
            "element": sp,
            "neutral_conc": n1,
            "ionized_conc": n2,
            "conc": conc,
            "mass_rel": mass * conc,
            "atomic_mass": mass,
            "neutral_ratio": neutral_ratio,
            "ionized_neutral_ratio": ion_neutral_ratio,
            "ne": ne,
        })
    total_n = sum(r["conc"] for r in rows) or 1.0
    total_m = sum(r["mass_rel"] for r in rows) or 1.0
    for r in rows:
        r["number_percent"] = r["conc"] / total_n * 100.0
        r["mass_percent"] = r["mass_rel"] / total_m * 100.0
    rows.sort(key=lambda r: r["mass_percent"], reverse=True)
    return rows




def _bisect_root(func, x1: float, x2: float, xacc: float = 1e-10, max_iter: int = 100) -> float:
    """Small rtbis() equivalent used by the reconstructed Unit21 SAC routine."""
    f1 = func(x1)
    f2 = func(x2)
    if f1 == 0:
        return x1
    if f2 == 0:
        return x2
    if f1 * f2 > 0:
        # Fall back to the least-bad end point instead of aborting the whole table.
        return x1 if abs(f1) < abs(f2) else x2
    lo, hi = x1, x2
    flo = f1
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = func(mid)
        if abs(fm) < xacc or abs(hi - lo) < xacc:
            return mid
        if flo * fm <= 0:
            hi = mid
        else:
            lo = mid
            flo = fm
    return 0.5 * (lo + hi)


def _experimental_lorentzian_width(line: TemplateLine, instrumental_width: float) -> float:
    """Unit21 width correction: wtot = sqrt((wl/2)^2 + wg^2) + wl/2; wl = wtot - inst^2/wtot."""
    if _template_line_has_fit_error(line):
        return 0.0
    wl = abs(line.wl) if line.wl else 0.0
    wg = abs(line.wg) if line.wg else 0.0
    wtot = math.sqrt((wl / 2.0) ** 2 + wg ** 2) + wl / 2.0
    if wtot <= 0:
        return 0.0
    return abs(wtot - instrumental_width * instrumental_width / wtot)


def compute_sac_for_template_lines(app: "MainWindow", kt: float, ne: float, path_length: float, total_density: float, element_percent: dict[str, float]):
    """Diagnostic SAC factor calculation from Unit21.

    Original Unit21 computes:
        knu0 = 9E-2*Nl*|Aki|*1.5E-8*wave^4*gk/gi /(pi^1.5*3.6E18) * (1/sl2)/lor * lu
        fun(x) = 1 - knu0*x^0.46 - exp(-knu0*x^-0.54)
        ssa = rtbis(fun, 1e-10, 1.1e-7)
        SAC = ssa^0.46
        Wl0 = lor*ssa^0.54

    The C++ version obtains element percentages from the current CF-LIBS table. Here the same
    value is taken from the last pyLIBS CF-LIBS result when available, otherwise from the user table.
    """
    rows = []
    if kt <= 0:
        kt = max(app.options.kt_low, 1.0)
    temperature_k = kt * 11600.0
    sl2 = 0.832554611
    pi = 3.1415
    for idx, t in enumerate(app.template_lines, start=1):
        if _template_line_has_fit_error(t):
            continue
        if not t.specie or not t.ion or not t.aki or t.aki == -1 or not t.gk or not t.gi:
            continue
        wave = t.asswavelen or t.fitwavelen or t.wavelen
        if not wave:
            continue
        try:
            meta = app.libs_db.element_metadata(t.specie)
            eio = safe_float(meta.get("en_ion"), 0.0)
            zi = app.libs_db.partition_function(t.specie, 1, temperature_k)
            zii = app.libs_db.partition_function(t.specie, 2, temperature_k)
        except Exception:
            eio, zi, zii = 0.0, 1.0, 1.0
        # Lower-level energy Ei is not stored in TemplateLine; use database lookup around the assigned wavelength.
        ei = 0.0
        try:
            cand = app.libs_db.search_lines(wave, 0.04, table=t.specie.capitalize(), ion=int(t.ion), limit=1, prefer_full_element_table=True)
            if cand:
                ei = cand[0].ei
        except Exception:
            pass
        try:
            if int(t.ion) == 1:
                denom = ne + 4.8e15 * (temperature_k ** 1.5) * math.exp(-1.44 * eio / temperature_k) * (zii / zi if zi else 1.0)
                nq = ne / denom * t.gi * math.exp(-1.44 * ei / temperature_k) / (zi or 1.0)
            else:
                denom = ne + 4.8e15 * (temperature_k ** 1.5) * math.exp(-1.44 * eio / temperature_k) * (zii / zi if zi else 1.0)
                nq = (1.0 - ne / denom) * t.gi * math.exp(-1.44 * ei / temperature_k) / (zii or 1.0)
        except Exception:
            nq = 0.0
        perc = element_percent.get(t.specie, element_percent.get(t.specie.capitalize(), 0.0))
        nl = nq * total_density * perc / 100.0
        lor = _experimental_lorentzian_width(t, app.options.instrumental_width)
        if lor <= 0 or nl <= 0:
            sac, wl0, knu0, ssa = 1.0, lor, 0.0, 1.0
        else:
            knu0 = 9e-2 * nl * abs(t.aki) * 1.5e-8 * (wave ** 4) * t.gk / t.gi
            knu0 /= (pi ** 1.5 * 3.6e18)
            knu0 *= (1.0 / sl2) / lor * path_length
            def fun(x):
                return 1.0 - knu0 * (x ** 0.46) - math.exp(-knu0 * (x ** -0.54))
            ssa = _bisect_root(fun, 1e-10, 1.1e-7, 1e-10)
            sac = max(ssa ** 0.46, 1e-30)
            wl0 = lor * (ssa ** 0.54)
        rows.append({"index": idx, "species": f"{t.specie} {_roman_ion(t.ion)}", "wavelength": wave, "sac": sac, "wl": lor, "wl0": wl0, "knu0": knu0, "ssa": ssa})
    return rows


class SACWindow(tk.Toplevel):
    """Diagnostic SAC factors window."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("SAC factors")
        self.geometry("940x540")
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Label(top, text="kT eV").pack(side="left")
        self.kt_var = tk.StringVar(value="1.0")
        ttk.Entry(top, textvariable=self.kt_var, width=8).pack(side="left", padx=2)
        ttk.Label(top, text="Ne cm⁻³").pack(side="left", padx=(8,2))
        self.ne_var = tk.StringVar(value=f"{master.options.ne_low:.3g}")
        ttk.Entry(top, textvariable=self.ne_var, width=12).pack(side="left", padx=2)
        ttk.Label(top, text="path lu").pack(side="left", padx=(8,2))
        self.lu_var = tk.StringVar(value="1.0")
        ttk.Entry(top, textvariable=self.lu_var, width=8).pack(side="left", padx=2)
        ttk.Label(top, text="N total").pack(side="left", padx=(8,2))
        self.ntot_var = tk.StringVar(value="1e18")
        ttk.Entry(top, textvariable=self.ntot_var, width=10).pack(side="left", padx=2)
        ttk.Button(top, text="Compute SAC", command=self.compute).pack(side="left", padx=5)
        ttk.Button(top, text="Clear SAC", command=self.clear).pack(side="left", padx=2)
        cols = ("row", "species", "wavelength", "SAC", "Wl", "Wl0", "knu0")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=5)

    def _element_percentages(self):
        rows = getattr(self.master_app, "last_cflibs_rows", []) or []
        if rows:
            return {r["element"]: safe_float(r.get("number_percent"), 0.0) for r in rows}
        elems = sorted({t.specie for t in self.master_app.template_lines if t.specie})
        if not elems:
            return {}
        return {e: 100.0 / len(elems) for e in elems}

    def compute(self):
        if not self.master_app.template_lines:
            _showinfo(self, "SAC", "A template with assigned lines is required first.")
            return
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            self.master_app.libs_db.connect()
        except Exception:
            pass
        kt = safe_float(self.kt_var.get(), 1.0)
        ne = safe_float(self.ne_var.get(), self.master_app.options.ne_low)
        lu = safe_float(self.lu_var.get(), 1.0)
        ntot = safe_float(self.ntot_var.get(), 1e18)
        rows = compute_sac_for_template_lines(self.master_app, kt, ne, lu, ntot, self._element_percentages())
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["index"], r["species"], f"{r['wavelength']:.4f}", f"{r['sac']:.6g}", f"{r['wl']:.6g}", f"{r['wl0']:.6g}", f"{r['knu0']:.4g}"))
        self.master_app.status(f"SAC: {len(rows)} factors calculated")

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.master_app.status("SAC reset")


def _format_sa_numeric(value):
    try:
        num = float(value)
    except Exception:
        return ""
    if not math.isfinite(num):
        return ""
    text = f"{num:.3f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


class SelfAbsorptionCheckWindow(tk.Toplevel):
    """Preliminary self-absorption inspection window."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Self-Absorption Check")
        self.geometry("585x400")
        self.minsize(560, 360)
        self._rows = []
        self._stark_db_warning_shown = False
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=5)
        self.apply_sac_button = ttk.Button(top, text="Apply SAC", command=self.apply_sac)
        self.apply_sac_button.pack(side="left")
        ttk.Button(top, text="Close", command=self.close).pack(side="left", padx=4)
        self.summary_var = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.summary_var).pack(side="right", padx=6)

        self.tree = ttk.Treeview(self, columns=("line", "wl", "stark_width", "sa", "sac", "use"), show="headings", height=14)
        headings = {
            "line": "Line",
            "wl": "wl",
            "stark_width": "Stark width",
            "sa": "SA",
            "sac": "SAC",
            "use": "Use",
        }
        widths = {"line": 166, "wl": 64, "stark_width": 84, "sa": 54, "sac": 54, "use": 48}
        for col in ("line", "wl", "stark_width", "sa", "sac", "use"):
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=widths[col], stretch=False, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.protocol("WM_DELETE_WINDOW", self.close)
        fit_toplevel_to_content(self, min_width=560, min_height=360, max_width_fraction=0.55, max_height_fraction=0.60)
        center_window(self, master)
        self._update_apply_sac_button()
        self.lift(master)
        try:
            self.focus_force()
        except Exception:
            self.focus_set()

    def _update_apply_sac_button(self):
        state = bool(getattr(self.master_app, "apply_sac_correction", False))
        if hasattr(self, "apply_sac_button"):
            self.apply_sac_button.config(text="Remove SAC" if state else "Apply SAC")

    def _assigned_lines(self):
        return [
            line for line in getattr(self.master_app, "template_lines", []) or []
            if getattr(line, "specie", "") and getattr(line, "ion", 0) and not _template_line_has_fit_error(line)
        ]

    def _stark_db_path(self):
        return resource_path("Stark.db")

    def _stark_match_tolerance(self):
        base = abs(safe_float(getattr(self.master_app.options, "search_range", 0.2), 0.2)) * 0.02
        return max(0.05, base)

    def _current_temperature_k(self):
        kt_ev = safe_float(getattr(self.master_app, "session_temperature", 0.0), 0.0)
        if kt_ev <= 0.0:
            kt_ev = 1.0
        return kt_ev * 11600.0

    def _current_electron_density(self):
        ne = safe_float(getattr(self.master_app, "session_ne", 0.0), 0.0)
        if ne <= 0.0:
            ne = 1.0e17
        return ne

    def _stark_species(self, line):
        return str(getattr(line, "specie", "")).strip().capitalize()

    def _stark_ion(self, line):
        try:
            ion = int(getattr(line, "ion", 0) or 0)
        except Exception:
            ion = 0
        if ion == 1:
            return 1
        if ion == 2:
            return 2
        return 0

    def _lookup_stark_row(self, conn, line, tolerance):
        specie = self._stark_species(line)
        ion = self._stark_ion(line)
        asswl = abs(safe_float(getattr(line, "asswavelen", 0.0), 0.0))
        if not specie or ion not in (1, 2) or asswl <= 0.0:
            return None
        try:
            return conn.execute(
                """
                SELECT Element, Ion, Wavelength, "w-T5000", "w-T10000"
                FROM Stark
                WHERE UPPER(TRIM(Element)) = ?
                  AND CAST(Ion AS INTEGER) = ?
                  AND CAST(Wavelength AS REAL) BETWEEN ? AND ?
                LIMIT 1
                """,
                (specie.upper(), ion, asswl - tolerance, asswl + tolerance),
            ).fetchone()
        except Exception:
            return None

    def _stark_width_for_row(self, row):
        if not row:
            return ""
        w5000 = safe_float(row["w-T5000"], 0.0)
        w10000 = safe_float(row["w-T10000"], 0.0)
        if w5000 == 0.0 and w10000 == 0.0:
            return ""
        temp_k = self._current_temperature_k()
        w_t = w5000 + (temp_k - 5000.0) * (w10000 - w5000) / 5000.0
        ne = self._current_electron_density()
        width = 2.0 * (ne / 1.0e17) * w_t
        return _format_sa_numeric(width)

    def _sa_value_for_line(self, wl_text, stark_text):
        wl = safe_float(wl_text, 0.0)
        stark = safe_float(stark_text, 0.0)
        if wl <= 0.0 or stark <= 0.0:
            return ""
        ratio = wl / stark
        if ratio >= 1.0:
            try:
                value = ratio ** (-1.85)
            except Exception:
                return ""
        else:
            value = 1.0
        return _format_sa_numeric(value)

    def _line_label(self, line):
        wave = safe_float(getattr(line, "asswavelen", 0.0), 0.0)
        if not wave:
            return ""
        return f"{line.specie} {_roman_ion(line.ion)} {_format_sa_numeric(wave)}"

    def _line_values(self, line):
        wl = abs(safe_float(getattr(line, "wl", 0.0), 0.0))
        stark = getattr(line, "sa_stark_width", "")
        sa = getattr(line, "sa_value", "")
        sac = ""
        if not sa and wl > 0.0 and stark:
            sa = self._sa_value_for_line(_format_sa_numeric(wl), stark)
        sa_num = safe_float(sa, 0.0)
        if sa_num > 0.0 and sa_num <= 1.0:
            sac_value = sa_num ** (-0.46)
            sac = _format_sa_numeric(sac_value)
            line.sa_sac = sac_value
        else:
            line.sa_sac = ""
        use_value = "No" if not bool(getattr(line, "sa_use", True)) else "Yes"
        return (
            self._line_label(line),
            _format_sa_numeric(wl) if wl > 0.0 else "",
            stark if stark else "",
            sa if sa else "",
            sac,
            use_value,
        )

    def refresh(self, show_message=True):
        lines = self._assigned_lines()
        self._rows = list(lines)
        tolerance = self._stark_match_tolerance()
        stark_conn = None
        stark_error = False
        stark_path = self._stark_db_path()
        try:
            if not stark_path.exists():
                raise FileNotFoundError(str(stark_path))
            stark_conn = sqlite3.connect(str(stark_path))
            stark_conn.row_factory = sqlite3.Row
        except Exception:
            stark_conn = None
            stark_error = True
        if stark_error and not self._stark_db_warning_shown:
            self._stark_db_warning_shown = True
            _showwarning(self, "Self-Absorption Check", "Stark.db not found or could not be opened. Self-absorption data are unavailable.")
        if not stark_error:
            self._stark_db_warning_shown = False
        self.tree.delete(*self.tree.get_children())
        if not lines:
            self.summary_var.set("No assigned template lines available")
            if show_message:
                _showinfo(self, "Self-Absorption Check", "A template with assigned lines is required first.")
            return
        for idx, line in enumerate(self._rows):
            stark_row = None
            has_stark_data = False
            if stark_conn is not None:
                stark_row = self._lookup_stark_row(stark_conn, line, tolerance)
                has_stark_data = stark_row is not None
            line.sa_has_stark_data = has_stark_data
            line.sa_use = has_stark_data
            line.sa_stark_row = stark_row
            line.sa_stark_width = self._stark_width_for_row(stark_row)
            line.sa_value = self._sa_value_for_line(
                _format_sa_numeric(abs(safe_float(getattr(line, "wl", 0.0), 0.0))) if abs(safe_float(getattr(line, "wl", 0.0), 0.0)) > 0.0 else "",
                line.sa_stark_width,
            )
            self.tree.insert("", "end", iid=str(idx), values=self._line_values(line))
        self._update_apply_sac_button()
        self.summary_var.set(f"{len(lines)} template line(s)")
        if stark_conn is not None:
            try:
                stark_conn.close()
            except Exception:
                pass

    def _toggle_selected_use(self, _event=None):
        item = self.tree.focus()
        if item:
            self._toggle_use_value(item)
        return "break"

    def _toggle_use_value(self, item):
        try:
            idx = int(item)
        except Exception:
            return
        if idx < 0 or idx >= len(self._rows):
            return
        line = self._rows[idx]
        current = bool(getattr(line, "sa_use", True))
        line.sa_use = not current
        if item in self.tree.get_children():
            self.tree.item(item, values=self._line_values(line))
            try:
                self.tree.selection_set(item)
                self.tree.focus(item)
            except Exception:
                pass
        return "break"

    def _on_double_click(self, event):
        # Toggle Yes/No for the clicked Show SA row, independently of the
        # column/cell that was double-clicked.  Ignore clicks outside rows
        # (for example on the heading or in empty table space).
        item = self.tree.identify_row(event.y)
        if not item:
            return
        return self._toggle_use_value(item)

    def apply_sac(self):
        """Toggle plotting-only SAC correction using the current Show SA table.

        The SAC value is already calculated in this window.  For each displayed
        row, the correction is enabled only if SAC >= 1 and the Use/checkbox
        column is Yes.  No SAC value is recalculated here and the template data
        are not otherwise modified.
        """
        self.master_app.apply_sac_correction = not bool(getattr(self.master_app, "apply_sac_correction", False))
        state = bool(getattr(self.master_app, "apply_sac_correction", False))

        # Read the current visible Show SA table before redrawing any plot.
        # Do not call refresh() here: it would rebuild the table and could reset
        # the user-selected Yes/No values.
        enabled_rows = 0
        for item in self.tree.get_children():
            try:
                idx = int(item)
            except Exception:
                continue
            if idx < 0 or idx >= len(self._rows):
                continue
            line = self._rows[idx]
            values = list(self.tree.item(item, "values") or [])
            sac = safe_float(values[4] if len(values) > 4 else "", 0.0)
            use_text = str(values[5] if len(values) > 5 else "").strip().lower()
            use_yes = use_text in ("yes", "y", "true", "1", "si", "sì")
            line.sa_sac = sac if sac >= 1.0 and math.isfinite(sac) else ""
            line.sa_use = bool(use_yes and sac >= 1.0 and math.isfinite(sac))
            if state and line.sa_use:
                enabled_rows += 1

        msg = f"SAC applied to {enabled_rows} plot point(s)" if state else "SAC removed from plots"
        self.summary_var.set(msg)
        self.master_app.status(msg)
        self._update_apply_sac_button()
        for attr in ("saha_window", "cflibs_window"):
            win = getattr(self.master_app, attr, None)
            try:
                if win is not None and win.winfo_exists():
                    compute = getattr(win, "compute", None)
                    if callable(compute):
                        compute()
            except Exception:
                pass

    def close(self):
        try:
            if getattr(self.master_app, "sac_check_window", None) is self:
                self.master_app.sac_check_window = None
        except Exception:
            pass
        self.destroy()


class StandardCorrectionWindow(tk.Toplevel):
    """Unit31 OPC / .STD standard correction window."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Standard Correction / OPC - Unit31")
        self.geometry("760x500")
        self.minsize(700, 340)
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Refresh from CF-LIBS", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Load .STD", command=self.load_std).pack(side="left", padx=3)
        ttk.Button(top, text="Save .STD", command=self.save_std).pack(side="left", padx=3)
        ttk.Button(top, text="Apply correction", command=self.apply_correction).pack(side="left", padx=8)
        cols = ("element", "mass %", "ref %", "factor", "corrected %")
        tree_frame = ttk.Frame(self)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=5)
        self.tree.bind("<Double-1>", self.edit_ref)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = getattr(self.master_app, "last_cflibs_rows", []) or []
        refs = getattr(self.master_app, "standard_refs", {})
        for r in rows:
            el = r["element"]
            ref = refs.get(el, "")
            self.tree.insert("", "end", iid=el, values=(el, f"{r['mass_percent']:.6g}", ref, "", ""))

    def edit_ref(self, _event=None):
        item = self.tree.focus()
        if not item:
            return
        vals = list(self.tree.item(item, "values"))
        win = tk.Toplevel(self); win.title(f"Reference {vals[0]}")
        win.resizable(False, False)
        v = tk.StringVar(value=str(vals[2]))
        ttk.Label(win, text=f"{vals[0]} reference %").pack(pady=(10,2))
        ttk.Entry(win, textvariable=v).pack()
        def ok():
            self.master_app.standard_refs[vals[0]] = v.get()
            self.refresh(); win.destroy()
        ttk.Button(win, text="OK", command=ok).pack(pady=6)
        fit_toplevel_to_content(win)

    def load_std(self):
        fn = filedialog.askopenfilename(initialdir=remembered_initial_dir(self.master_app.options), filetypes=[("Standard Data", "*.STD *.std"), ("All", "*.*")])
        if not fn:
            return
        remember_working_dir(self.master_app.options, fn)
        refs = {}
        mismatch = []
        current = [self.tree.item(i, "values")[0] for i in self.tree.get_children()]
        for line in Path(fn).read_text(encoding="utf-8", errors="ignore").splitlines():
            p = line.split()
            if len(p) >= 2:
                refs[p[0]] = p[1]
        for el in current:
            if el not in refs:
                mismatch.append(el)
        self.master_app.standard_refs.update(refs)
        self.refresh()
        if mismatch:
            _showwarning(self, "STD", "WARNING: Standard mismatch for: " + ", ".join(mismatch))
        self.master_app.status(f"STD loaded: {fn}")

    def save_std(self):
        fn = filedialog.asksaveasfilename(initialdir=remembered_initial_dir(self.master_app.options), defaultextension=".STD", filetypes=[("Standard Data", "*.STD"), ("All", "*.*")])
        if not fn:
            return
        remember_working_dir(self.master_app.options, fn)
        lines = []
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            if vals and str(vals[2]).strip():
                lines.append(f"{vals[0]} {vals[2]}")
        Path(fn).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        self.master_app.status(f"STD saved: {fn}")

    def apply_correction(self):
        rows = getattr(self.master_app, "last_cflibs_rows", []) or []
        refs = getattr(self.master_app, "standard_refs", {})
        corrected = []
        for r in rows:
            ref = safe_float(refs.get(r["element"], 0.0), 0.0)
            if ref > 0 and r["mass_percent"] > 0:
                factor = ref / r["mass_percent"]
            else:
                factor = 1.0
            corrected.append((r["element"], r["mass_percent"], ref, factor, r["mass_percent"] * factor))
        total = sum(v[-1] for v in corrected) or 1.0
        self.tree.delete(*self.tree.get_children())
        for el, mass, ref, factor, corr in corrected:
            self.tree.insert("", "end", iid=el, values=(el, f"{mass:.6g}", f"{ref:.6g}" if ref else "", f"{factor:.6g}", f"{corr/total*100:.6g}"))
        self.master_app.status("Standard correction applicata alla tabella corrente")


class CFLibsOPCWindow(tk.Toplevel):
    """One Point Calibration from current CF-LIBS number percentages."""

    def __init__(self, owner: "CFLibsWindow"):
        super().__init__(owner)
        self.owner = owner
        self.master_app = owner.master_app
        self.title("One Point Calibration")
        self.geometry("760x500")
        self.minsize(680, 340)
        self.factors: dict[str, float] = {}
        self.nominal_vars: dict[str, tk.StringVar] = {}
        self.nominal_entries: list[ttk.Entry] = []
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Compute OPC", command=self.compute).pack(side="left")
        ttk.Button(top, text="Save Calibration...", command=self.save).pack(side="left", padx=4)
        ttk.Button(top, text="Close", command=self.close).pack(side="left", padx=4)

        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="both", expand=True, padx=6, pady=5)
        for col, title in enumerate(("Element", "CF-LIBS Number %", "Nominal Number %")):
            ttk.Label(self.rows_frame, text=title, anchor="center", font=("TkDefaultFont", 9, "bold")).grid(
                row=0, column=col, sticky="ew", padx=4, pady=(0, 4)
            )
        self.rows_frame.columnconfigure(0, weight=1, minsize=160)
        self.rows_frame.columnconfigure(1, weight=1, minsize=180)
        self.rows_frame.columnconfigure(2, weight=1, minsize=180)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        center_window(self, owner)
        self.lift(owner)
        try:
            self.focus_force()
        except Exception:
            self.focus_set()

    def refresh(self):
        for child in self.rows_frame.grid_slaves():
            if int(child.grid_info().get("row", 0)) > 0:
                child.destroy()
        self.nominal_entries = []
        rows = self.owner.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or []
        for display_row, row in enumerate(rows, start=1):
            element = row.get("element", "")
            number_percent = safe_float(row.get("number_percent", 0.0), 0.0)
            saved = getattr(self.master_app, "opc_nominal_percent", {}).get(element, "")
            var = self.nominal_vars.get(element)
            if var is None:
                text = format_template_display_value(saved) if safe_float(saved, 0.0) > 0.0 else ""
                var = tk.StringVar(value=text)
                self.nominal_vars[element] = var
            ttk.Label(self.rows_frame, text=element, anchor="center").grid(
                row=display_row, column=0, sticky="ew", padx=4, pady=2
            )
            ttk.Label(self.rows_frame, text=format_template_display_value(number_percent), anchor="center").grid(
                row=display_row, column=1, sticky="ew", padx=4, pady=2
            )
            entry = ttk.Entry(self.rows_frame, textvariable=var, justify="center")
            entry.grid(row=display_row, column=2, sticky="ew", padx=4, pady=2)
            entry.bind("<Return>", lambda event, idx=len(self.nominal_entries): self._entry_return(idx))
            entry.bind("<KP_Enter>", lambda event, idx=len(self.nominal_entries): self._entry_return(idx))
            entry.bind("<Shift-Tab>", lambda event, idx=len(self.nominal_entries): self._focus_nominal_entry(idx - 1))
            self.nominal_entries.append(entry)

    def _focus_nominal_entry(self, index):
        if not self.nominal_entries:
            return "break"
        index = max(0, min(index, len(self.nominal_entries) - 1))
        self.nominal_entries[index].focus_set()
        self.nominal_entries[index].selection_range(0, "end")
        return "break"

    def _entry_return(self, index):
        if index + 1 < len(self.nominal_entries):
            return self._focus_nominal_entry(index + 1)
        self.compute()
        return "break"

    def _nominal_value(self, element, text):
        text = str(text or "").strip()
        if not text:
            return None
        value = safe_float(text, None)
        if value is None or value < 0.0 or value > 100.0:
            raise ValueError(f"{element}: Nominal Number % must be between 0 and 100.")
        return value

    def _current_rows(self):
        return self.owner.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or []

    def _store_nominal_values(self):
        nominal = getattr(self.master_app, "opc_nominal_percent", None)
        if nominal is None:
            self.master_app.opc_nominal_percent = {}
            nominal = self.master_app.opc_nominal_percent
        for row in self._current_rows():
            element = row.get("element", "")
            var = self.nominal_vars.get(element)
            if var is None:
                continue
            value = self._nominal_value(element, var.get())
            if value is None:
                nominal.pop(element, None)
            else:
                nominal[element] = value

    def _show_nominal_error(self, message):
        _showwarning(self, "OPC", message)
        element = str(message).split(":", 1)[0]
        rows = [row.get("element", "") for row in self._current_rows()]
        if element in rows:
            idx = rows.index(element)
            if idx < len(self.nominal_entries):
                self._focus_nominal_entry(idx)

    def _compute_factors_from_entries(self):
        factors = {}
        nominal = getattr(self.master_app, "opc_nominal_percent", {})
        for row in self._current_rows():
            element = row.get("element", "")
            cflibs_percent = safe_float(row.get("number_percent", 0.0), 0.0)
            nominal_percent = safe_float(nominal.get(element, 0.0), 0.0)
            if 0.0 < cflibs_percent <= 100.0 and 0.0 < nominal_percent <= 100.0:
                factors[element] = nominal_percent / cflibs_percent
        return factors

    def compute(self):
        try:
            self._store_nominal_values()
        except ValueError as e:
            self.factors = {}
            self._show_nominal_error(str(e))
            return False
        self.factors = self._compute_factors_from_entries()
        self.master_app.status(f"OPC correction factors computed for {len(self.factors)} element(s).")
        return True

    def _source_spectrum_filename(self):
        spectra = getattr(self.master_app, "spectra", []) or []
        if not spectra:
            return ""
        return getattr(spectra[0], "filename", "") or getattr(spectra[0], "name", "")

    def _calibration_rows(self):
        if not self.compute():
            return []
        rows = []
        cflibs_percent = {
            str(row.get("element", "")).strip().capitalize(): safe_float(row.get("number_percent", 0.0), 0.0)
            for row in (self.owner.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or [])
        }
        groups = getattr(self.owner, "last_groups", {}) or {}
        fits = getattr(self.owner, "last_fits", {}) or {}
        for key, points in groups.items():
            fit = fits.get(key)
            if not fit:
                continue
            species_name, ion = key
            element = str(species_name).strip().capitalize()
            ratio = safe_float(self.factors.get(element, 0.0), 0.0)
            nominal = safe_float(getattr(self.master_app, "opc_nominal_percent", {}).get(element, 0.0), 0.0)
            calculated = safe_float(cflibs_percent.get(element, 0.0), 0.0)
            if ratio <= 0.0 or nominal <= 0.0 or calculated <= 0.0:
                continue
            for point in points:
                if point.get("inactive"):
                    continue
                line = point.get("line")
                if line is None:
                    continue
                raw_intensity = _template_line_intensity(line)
                ag = abs(safe_float(getattr(line, "aki", 0.0), 0.0) * safe_float(getattr(line, "gk", 0.0), 0.0))
                sac = safe_float(point.get("sac", 1.0), 1.0) or 1.0
                x = safe_float(point.get("x", 0.0), 0.0)
                if raw_intensity <= 0.0 or ag <= 0.0:
                    continue
                yp = fit["slope"] * x + fit.get("q_at_t", fit.get("q", 0.0)) + math.log(ratio)
                try:
                    response_value = raw_intensity / (sac * ag * math.exp(yp))
                except (OverflowError, ZeroDivisionError, ValueError):
                    continue
                if not math.isfinite(response_value) or response_value <= 0.0:
                    continue
                wavelength = abs(getattr(line, "fitwavelen", 0.0)) or getattr(line, "wavelen", 0.0)
                if not wavelength:
                    continue
                species = f"{element} {_roman_ion(ion)}"
                rows.append((float(wavelength), response_value, element, species))
        rows.sort(key=lambda r: r[0])
        return rows

    def save(self):
        calibration_rows = self._calibration_rows()
        if not calibration_rows:
            _showinfo(self, "OPC", "No OPC calibration rows are available to save.")
            return
        fn = filedialog.asksaveasfilename(
            parent=_prepare_messagebox_parent(self),
            title="Save OPC Calibration",
            initialdir=remembered_initial_dir(self.master_app.options),
            defaultextension=".opc",
            filetypes=[("OPC calibration", "*.opc"), ("Text files", "*.txt"), ("All", "*.*")],
        )
        if not fn:
            return
        remember_working_dir(self.master_app.options, fn)
        lines = [
            "# pyLIBS One Point Calibration",
            f"# date: {datetime.now().isoformat(timespec='seconds')}",
            f"# source spectrum: {self._source_spectrum_filename() or 'N/A'}",
            f"# temperature_eV: {self.owner.last_kt:.8g}",
            f"# electron_density_e_cm3: {self.owner.last_ne:.8g}",
            "# formula: OPC response from fixed-temperature Boltzmann line shifted by log(nominal_number_percent / cflibs_number_percent)",
            "# columns: wavelength correction_factor element species",
        ]
        for wavelength, factor, element, species in calibration_rows:
            lines.append(f"{wavelength:.8g} {factor:.8g} {element} {species}")
        try:
            Path(fn).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e:
            _showerror(self, "OPC", f"Could not save OPC calibration:\n{e}")
            return
        self.master_app.status(f"OPC calibration saved: {fn}")
        _showinfo(self, "OPC", f"OPC calibration saved:\n{fn}")

    def close(self):
        try:
            if getattr(self.owner, "opc_window", None) is self:
                self.owner.opc_window = None
        except Exception:
            pass
        self.destroy()


class CFLibsWindow(tk.Toplevel):
    """CF-LIBS v8 original-like engine.

    Consolidates the recovered Borland flow from showboltz(), Unit9/zZ(), Unit27 and
    SDIMain/calcola(): Boltzmann plots, weighted kT, q recomputation at selected kT,
    Saha balance, number % and mass %.
    """
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("CF-LIBS")
        self.geometry("1100x720")
        self.minsize(940, 600)
        top=ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Compute CF-LIBS", command=self.compute).pack(side="left")
        self.opc_button = ttk.Button(top, text="OPC", command=self.show_opc, state="disabled")
        self.opc_button.pack(side="left", padx=4)
        ttk.Button(top, text="Show Report", command=self.show_report).pack(side="left", padx=4)
        ttk.Label(top, text="kT eV").pack(side="left", padx=(12,2))
        default_kt = safe_float(getattr(master, "session_temperature", 0.0), 0.0) or 1.0
        self.kt_var = tk.StringVar(value=f"{default_kt:.6g}")
        ttk.Entry(top, textvariable=self.kt_var, width=9).pack(side="left")
        ttk.Label(top, text="Ne cm⁻³").pack(side="left", padx=(12,2))
        default_ne = safe_float(getattr(master, "session_ne", 0.0), 0.0) or 1.0e17
        self.ne_var = tk.StringVar(value=f"{default_ne:.6g}")
        ttk.Entry(top, textvariable=self.ne_var, width=12).pack(side="left")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.status_var, width=34).pack(side="left", padx=12, fill="x", expand=True)
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(self, text="matplotlib not available").pack(fill="both", expand=True, padx=10, pady=10)
            self.fig = self.ax = self.canvas = None
        else:
            self.fig = Figure(figsize=(9.5, 4.2), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=5)
            self.canvas.mpl_connect("button_press_event", self.on_plot_click)
        self.last_rows = []
        self.last_skipped = 0
        self.last_kt = safe_float(self.kt_var.get(), 1.0) or 1.0
        self.last_ne = safe_float(self.ne_var.get(), 1.0e17) or 1.0e17
        self.last_response_used = False
        self.last_temperature_source = "default"
        self.last_ne_source = "default"
        self.last_groups = {}
        self.last_fits = {}
        self.report_window = None
        self.report_temp_dir = None
        self.opc_window = None
        self.plot_points = []
        cols=("Element", "Ionized / Neutral ratio", "Number %", "Mass %")
        tree_frame = ttk.Frame(self)
        self.tree=ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=135, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=5)
        self.after(100, self.compute)
        center_window(self, master)

    def enable_opc(self):
        try:
            self.opc_button.configure(state="normal")
        except Exception:
            pass

    def disable_opc(self):
        try:
            self.opc_button.configure(state="disabled")
        except Exception:
            pass
        if self.opc_window is not None and self.opc_window.winfo_exists():
            try:
                self.opc_window.close()
            except Exception:
                pass

    def compute(self):
        self.tree.delete(*self.tree.get_children())
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            self.master_app.libs_db.connect()
        except Exception as e:
            _showerror(self, "LIBS.db", str(e)); return
        kt = safe_float(self.kt_var.get(), 1.0) or 1.0
        if kt <= 0:
            kt = 1.0
            self.kt_var.set("1")
        ne = safe_float(self.ne_var.get(), 1.0e17) or 1.0e17
        groups, skipped = libspp_boltzmann_groups_with_skips(
            self.master_app,
        )
        fits = libspp_fit_boltzmann_fixed_temperature(self.master_app, groups, kt)
        if not fits:
            msg = f"No valid Boltzmann data. Skipped {skipped} incomplete template line(s)."
            self.status_var.set(msg)
            self.last_groups = groups
            self.last_fits = {}
            self.disable_opc()
            _showinfo(self, "CF-LIBS", msg)
            self._draw_boltzmann(groups, fits, kt)
            return
        rows = libspp_saha_cflibs(self.master_app, fits, kt, ne)
        self.last_groups = groups
        self.last_fits = fits
        self.master_app.last_cflibs_rows = rows
        self.last_rows = rows
        self.last_skipped = skipped
        self.last_kt = kt
        self.last_ne = ne
        self.last_response_used = _apply_after_response_enabled(self.master_app)
        self.last_temperature_source = self._temperature_source(kt)
        self.last_ne_source = self._ne_source(ne)
        self.master_app.session_temperature = kt
        self.master_app.session_ne = ne
        self.master_app.session_temperature_source = self.last_temperature_source
        self.master_app.session_ne_source = self.last_ne_source
        for r in rows:
            self.tree.insert("", "end", values=(
                r["element"],
                self._fmt3(r["ionized_neutral_ratio"]),
                self._fmt3(r["number_percent"]),
                self._fmt3(r["mass_percent"]),
            ))
        self._draw_boltzmann(groups, fits, kt)
        self.enable_opc()
        response_text = "Apply After response correction used" if _apply_after_response_enabled(self.master_app) else "no Apply After response correction"
        self.status_var.set(f"kT={kt:.4g} eV, Ne={ne:.3e} e/cm3, elements={len(rows)}, skipped={skipped}; {response_text}")
        self.master_app.status(f"CF-LIBS: kT={kt:.4g} eV, Ne={ne:.3e} e/cm3, {len(rows)} element(s), skipped {skipped}")

    def show_opc(self):
        rows = self.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or []
        if not rows:
            _showinfo(self, "OPC", "No CF-LIBS results are available for OPC.")
            return
        if self.opc_window is not None and self.opc_window.winfo_exists():
            self.opc_window.refresh()
            restore_lift_focus(self.opc_window, self)
            return
        self.opc_window = CFLibsOPCWindow(self)

    def show_report(self):
        rows = self.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or []
        if not rows:
            _showinfo(self, "CF-LIBS", "No CF-LIBS results are available to show.")
            return
        try:
            report_path, content = _write_temp_cflibs_report(self, rows)
            _open_file_with_default_app(report_path)
            preview_text = (
                "Report opened in the default HTML viewer.\n\n"
                f"Temporary HTML file:\n{report_path}\n\n"
                "Use Save... to save the generated report content to a permanent location."
            )
            fallback = False
        except Exception as e:
            _showwarning(self, "CF-LIBS", f"Could not open the default HTML viewer:\n{e}\n\nShowing the report source instead.")
            report_path = None
            image_path = _report_temp_path(self, "cflibs_report_spectrum.png")
            image_info = _export_spectrum_png(self, image_path)
            content = _build_cflibs_report_html(self, rows, image_info)
            preview_text = None
            fallback = True
        if self.report_window is not None and self.report_window.winfo_exists():
            self.report_window.update_report(content, "html", ".html", preview_text=preview_text)
            restore_lift_focus(self.report_window, self)
            return
        self.report_window = CFLibsReportPreviewWindow(self, content, "html", ".html", preview_text=preview_text)
        if fallback:
            self.master_app.status("CF-LIBS report shown as HTML source preview.")
        else:
            self.master_app.status(f"CF-LIBS report opened: {report_path}")

    def _ensure_report_temp_dir(self) -> Path:
        return _report_ensure_temp_dir(self)

    def _report_temp_path(self, filename: str) -> Path:
        return _report_temp_path(self, filename)

    def write_temp_cflibs_report(self, rows):
        return _write_temp_cflibs_report(self, rows)

    def open_file_with_default_app(self, path: Path):
        return _open_file_with_default_app(path)

    def on_report_window_close(self):
        self.report_window = None

    def save_report(self):
        self.show_report()

    def write_report_content(self, filename: str, content: str):
        try:
            _write_report_content(self, filename, content)
        except Exception as e:
            _showerror(self, "CF-LIBS", f"Could not save report:\n{e}")
            return
        remember_working_dir(self.master_app.options, filename)
        self.master_app.status(f"CF-LIBS report saved: {filename}")
        _showinfo(self, "CF-LIBS", f"Report saved:\n{filename}")

    def _fmt(self, value):
        return _report_fmt(value)

    def _fmt3(self, value):
        return _report_fmt3(value)

    def _temperature_source(self, kt):
        return _report_temperature_source(self, kt)

    def _ne_source(self, ne):
        return _report_ne_source(self, ne)

    def _export_spectrum_png(self, image_path: Path):
        return _export_spectrum_png(self, image_path)

    def _finite_values(self, values):
        return _report_finite_values(values)

    def _spectrum_info(self):
        return _report_spectrum_info(self)

    def _response_info(self):
        return _report_response_info(self)

    def _template_rows(self):
        return _report_template_rows(self)

    def _saha_rows(self):
        return _report_saha_rows(self)

    def _plasma_parameter_rows(self):
        return _report_plasma_parameter_rows(self)

    def _result_rows(self, rows):
        return _report_result_rows(rows)

    def _html_table(self, headers, rows):
        return _report_html_table(headers, rows)

    def _definition_table(self, mapping):
        return _report_definition_table(mapping)

    def _halpha_section_html(self):
        return _report_halpha_section_html(self)

    def _saha_section_html(self):
        return _report_saha_section_html(self)

    def build_cflibs_report_html(self, rows, image_info, report_path: Optional[Path] = None):
        return _build_cflibs_report_html(self, rows, image_info, report_path)

    def build_cflibs_report_text(self, rows, image_info):
        return _build_cflibs_report_text(self, rows, image_info)

    def _draw_boltzmann(self, groups, fits, kt):
        if self.ax is None:
            return
        self.plot_points = []
        self.ax.clear()
        self.ax.set_title("CF-LIBS Boltzmann plots")
        self.ax.set_xlabel("Upper energy Ek (eV)")
        self.ax.set_ylabel("ln(I / |Aki gk|)")
        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        all_x = [p["x"] for pts in groups.values() for p in pts]
        if all_x:
            xmin, xmax = min(all_x), max(all_x)
            pad = max((xmax - xmin) * 0.05, 0.05)
            xmin, xmax = xmin - pad, xmax + pad
        else:
            xmin, xmax = 0.0, 1.0
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
        for group_idx, (key, pts) in enumerate(sorted(groups.items())):
            if not pts:
                continue
            specie, ion = key
            label = f"{specie} {_roman_ion(ion)}"
            color = colors[group_idx % len(colors)] if colors else "#1f77b4"
            label_used = False
            for p in pts:
                inactive = bool(p.get("inactive"))
                point_color = "0.6" if inactive else color
                point_label = label if not label_used else "_nolegend_"
                plot_y, sac_marker = _sac_corrected_plot_y(self.master_app, p)
                marker = "*" if sac_marker else "o"
                size = 70 if sac_marker else 24
                self.ax.scatter([p["x"]], [plot_y], s=size, marker=marker, color=point_color, alpha=(0.65 if inactive else 1.0), label=point_label)
                self.plot_points.append({"x": p["x"], "y": plot_y, "line": p.get("line"), "inactive": inactive})
                label_used = True
            fit = fits.get(key)
            if fit:
                y0 = fit["slope"] * xmin + fit["q_at_t"]
                y1 = fit["slope"] * xmax + fit["q_at_t"]
                self.ax.plot([xmin, xmax], [y0, y1], linewidth=1.0)
        self.ax.set_xlim(xmin, xmax)
        self.ax.margins(y=0.05)
        self.ax.legend(loc="best", fontsize=8)
        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()

    def on_plot_click(self, event):
        if event.inaxes is not self.ax or not _matplotlib_event_has_shift(event) or event.button not in (1, 3):
            return
        point = self._nearest_plot_point(event)
        if not point or point.get("line") is None:
            return
        activate = event.button == 3
        _set_template_line_active(point["line"], activate)
        self.master_app.notify_template_changed(redraw=True)
        self.master_app.status("Point reactivated" if activate else "Point excluded from CF-LIBS calculation")
        self.compute()

    def _nearest_plot_point(self, event, max_pixels=12.0):
        if not self.plot_points or event.x is None or event.y is None:
            return None
        best = None
        best_dist = None
        for point in self.plot_points:
            try:
                px, py = self.ax.transData.transform((point["x"], point["y"]))
            except Exception:
                continue
            dist = math.hypot(px - event.x, py - event.y)
            if best_dist is None or dist < best_dist:
                best = point
                best_dist = dist
        return best if best is not None and best_dist is not None and best_dist <= max_pixels else None


class CFLibsReportPreviewWindow(tk.Toplevel):
    """Single CF-LIBS report preview window with explicit save action."""

    def __init__(self, owner: CFLibsWindow, content: str, report_format: str, default_extension: str, preview_text: Optional[str] = None):
        super().__init__(owner)
        self.owner = owner
        self.content = content
        self.report_format = report_format
        self.default_extension = default_extension
        self.title("CF-LIBS Report Preview")
        self.geometry("950x720")
        self.minsize(720, 480)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Save...", command=self.save).pack(side="left")
        ttk.Button(top, text="Close", command=self.close).pack(side="left", padx=4)
        self.mode_label = ttk.Label(top, text="")
        self.mode_label.pack(side="left", padx=12)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.text = tk.Text(frame, wrap="word", font=("TkFixedFont", 10))
        self.text.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_report(content, report_format, default_extension, preview_text=preview_text)
        center_window(self, owner)
        self.lift(owner)
        try:
            self.focus_force()
        except Exception:
            self.focus_set()

    def update_report(self, content: str, report_format: str, default_extension: str, preview_text: Optional[str] = None):
        self.content = content
        self.report_format = report_format
        self.default_extension = default_extension
        display_text = preview_text if preview_text is not None else content
        self.mode_label.configure(text="Report opened in default HTML viewer" if preview_text is not None else "HTML report source preview")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", display_text)
        self.text.configure(state="disabled")
        self.text.see("1.0")

    def save(self):
        filetypes = [("HTML report", "*.html"), ("Text report", "*.txt"), ("All", "*.*")]
        if self.report_format == "text":
            filetypes = [("Text report", "*.txt"), ("HTML report", "*.html"), ("All", "*.*")]
        fn = filedialog.asksaveasfilename(
            parent=_prepare_messagebox_parent(self),
            title="Save CF-LIBS Report",
            initialdir=remembered_initial_dir(self.owner.master_app.options),
            defaultextension=self.default_extension,
            filetypes=filetypes,
        )
        if not fn:
            return
        self.owner.write_report_content(fn, self.content)

    def close(self):
        try:
            self.owner.on_report_window_close()
        except Exception:
            pass
        self.destroy()


def show_startup_splash(root: tk.Tk, duration_ms: int = SPLASH_DURATION_MS):
    """Show a borderless startup splash screen for a few seconds."""
    try:
        splash = tk.Toplevel(root)
        splash.overrideredirect(True)
        splash.configure(bg="black")
        img_path = resource_path("pyLIBS_splash.png")
        if not img_path.exists():
            return None
        image = tk.PhotoImage(file=str(img_path))
        splash._image_ref = image
        canvas = tk.Canvas(splash, width=image.width(), height=image.height(), bd=0, highlightthickness=0, bg="black")
        canvas.pack()
        canvas.create_image(0, 0, image=image, anchor="nw")
        lines = [
            f"ver. {APP_VERSION}",
            "Originally developed as LIBS++ by Vincenzo Palleschi and coworkers",
            "© 2026 Vincenzo Palleschi. Licensed under CC BY-NC 4.0 for non-commercial use with attribution.",
        ]
        margin_x = 18
        margin_y = 16
        font = ("TkDefaultFont", 8)
        text_x = image.width() - margin_x
        text_y = image.height() - margin_y
        shadow = canvas.create_text(
            text_x + 1,
            text_y + 1,
            text="\n".join(lines),
            anchor="se",
            fill="#000000",
            font=font,
            justify="right",
            width=max(1, image.width() - 2 * margin_x),
        )
        text = canvas.create_text(
            text_x,
            text_y,
            text="\n".join(lines),
            anchor="se",
            fill="#f0f0f0",
            font=font,
            justify="right",
            width=max(1, image.width() - 2 * margin_x),
        )
        splash.update_idletasks()
        bbox = canvas.bbox(text)
        if bbox:
            pad_x = 7
            pad_y = 5
            canvas.create_rectangle(
                bbox[0] - pad_x,
                bbox[1] - pad_y,
                bbox[2] + pad_x,
                bbox[3] + pad_y,
                fill="#000000",
                outline="",
                stipple="gray75",
            )
            canvas.tag_raise(shadow)
            canvas.tag_raise(text)
        splash.update_idletasks()
        w, h = image.width(), image.height()
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        splash.geometry(f"{w}x{h}+{x}+{y}")
        splash.lift()
        splash.attributes("-topmost", True)
        splash.update_idletasks()
        splash.update()
        splash.after(200, lambda: splash.attributes("-topmost", False))
        splash.after(duration_ms, splash.destroy)
        return splash
    except Exception:
        return None


class DummyWindow(tk.Toplevel):
    def __init__(self, master, title, text):
        super().__init__(master)
        self.title(title); self.geometry("620x360")
        ttk.Label(self,text=title,font=("TkDefaultFont",14,"bold")).pack(pady=(14,6))
        ttk.Label(self,text=text,wraplength=560,justify="left").pack(padx=20,pady=6)



class RetroTemplateManager(tk.Toplevel):
    """Template manager reconstructed from Unit6.

    Original fields:
    wavelen, specie, asswavelen, inte, ei, wg, wl, ek, aki, gk, gi, ion,
    fitwavelen, templint, Errorinte, acc.
    """
    columns = (
        "wavelen", "specie", "asswavelen", "inte", "ei", "wg", "wl",
        "ek", "aki", "gk", "gi", "ion", "fitwavelen", "templint",
        "error_inte", "acc"
    )
    display_columns = (
        "wavelen", "specie", "ion", "asswavelen", "inte", "ei", "wg", "wl",
        "ek", "aki", "gk", "gi", "fitwavelen", "templint", "error_inte", "acc"
    )

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Template")
        self.geometry(legacy_geometry_to_tk(getattr(master.options, "template_geometry", ""), "1280x560"))
        self.minsize(1180, 420)
        self.configure(bg=RETRO_BG)
        self.protocol("WM_DELETE_WINDOW", master.close_template_window)
        self._build()

    def _build(self):
        panel = ttk.Frame(self)
        panel.pack(side="top", fill="x", padx=2, pady=2)
        ttk.Button(panel, text="Load Template", command=self.load_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Save Template As", command=self.save_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Template Info", command=self.template_info).pack(side="left", padx=2)
        ttk.Button(panel, text="Clear fit", command=self.clear_fit).pack(side="left", padx=2)
        ttk.Button(panel, text="Clear Template", command=self.clear_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Close Template", command=self.close_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Delete Row", command=self.delete_selected_row).pack(side="left", padx=2)
        ttk.Button(panel, text="Delete Template", command=self.delete_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Saha-Boltzmann", command=self.master_app.show_saha_boltzmann).pack(side="left", padx=2)

        tree_frame = ttk.Frame(self)
        self.tree = ttk.Treeview(tree_frame, columns=self.display_columns, show="headings", height=18)
        for c in self.display_columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=72, anchor="center")
        self.tree.column("specie", width=55)
        self.tree.column("ion", width=35)
        self.tree.column("wavelen", width=80)
        self.tree.column("fitwavelen", width=80)
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.refresh()

    def refresh(self):
        selected = list(self.tree.selection())
        focus = self.tree.focus()
        self.tree.delete(*self.tree.get_children())
        for i, l in enumerate(self.master_app.template_lines):
            vals = []
            for c in self.display_columns:
                vals.append(format_template_display_value(getattr(l, c, "")))
            self.tree.insert("", "end", iid=str(i), values=vals)
        children = set(self.tree.get_children())
        for item in selected:
            if item in children:
                self.tree.selection_add(item)
        if focus in children:
            self.tree.focus(focus)
            self.tree.see(focus)

    def load_template(self):
        fn = _template_file_dialog(
            self,
            filedialog.askopenfilename,
            title="Load Template",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("Templates / CSV", "*.csv *.db *.DB *.txt"), ("All", "*.*")]
        )
        if not fn:
            return
        remember_working_dir(self.master_app.options, fn)
        try:
            self.master_app.load_template_file(fn)
        except Exception as e:
            _showerror(self, "Template", str(e))
        self.master_app.notify_template_changed(redraw=True)

    def save_template(self):
        fn = _template_file_dialog(
            self,
            filedialog.asksaveasfilename,
            title="Save Template",
            initialdir=remembered_initial_dir(self.master_app.options),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")]
        )
        if not fn:
            return
        remember_working_dir(self.master_app.options, fn)
        try:
            self.master_app.save_template_file(fn)
            self.master_app.status(f"Template saved: {fn}")
        except Exception as e:
            _showerror(self, "Template", str(e))

    def template_info(self):
        lines = self.master_app.template_lines
        by_species = {}
        for l in lines:
            if l.specie:
                key = f"{l.specie} {_roman_ion(l.ion) if l.ion else ''}".strip()
                by_species[key] = by_species.get(key, 0) + 1
        msg = f"Lines: {len(lines)}\nAssigned lines: {sum(1 for l in lines if l.specie)}"
        if by_species:
            msg += "\n\n" + "\n".join(f"{k}: {v}" for k, v in sorted(by_species.items()))
        _showinfo(self, "Template Info", msg)

    def clear_template(self):
        if _askyesno(self, "Template", "This will clear the current template. Continue?"):
            self.master_app.template_lines.clear()
            self.master_app.clear_element_markers()
            self.master_app.notify_template_changed(redraw=True)

    def clear_fit(self):
        if not self.master_app.template_lines:
            return
        for line in self.master_app.template_lines:
            line.inte = None
            line.wl = None
            line.wg = None
            line.fitwavelen = None
        self.master_app.notify_template_changed(redraw=False)

    def close_template(self):
        if _askyesno(self, "Template", "This will close the current template. Continue?"):
            self.master_app.template_lines.clear()
            self.master_app.notify_template_changed(redraw=True)
            self.on_window_close()

    def on_window_close(self):
        self.master_app.close_template_window()

    def delete_template(self):
        fn = filedialog.askopenfilename(
            title="Delete Template",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("Templates", "*.db *.DB *.csv"), ("All", "*.*")]
        )
        if fn:
            remember_working_dir(self.master_app.options, fn)
        if fn and _askyesno(self, "Delete Template", f"Delete template?\n{fn}"):
            try:
                Path(fn).unlink()
                _showinfo(self, "Delete Template", "Template deleted")
            except Exception:
                _showerror(self, "Delete Template", "Template not deleted")

    def on_double_click(self, event=None):
        item = self.tree.focus()
        if item == "":
            return
        idx = int(item)
        if idx < 0 or idx >= len(self.master_app.template_lines):
            return
        line = self.master_app.template_lines[idx]
        self.master_app.zoom_around(line.wavelen)
        self.master_app.show_line_identification()
        # pre-fill wavelength in the Line Identification window when possible
        try:
            for w in self.master_app.winfo_children():
                if isinstance(w, LineIdentificationWindow):
                    w.wave_var.set(str(line.wavelen))
                    w.search()
        except Exception:
            pass

    def delete_selected_row(self):
        selected = list(self.tree.selection())
        if not selected:
            item = self.tree.focus()
            if item == "":
                return
            selected = [item]
        indices = []
        for item in selected:
            try:
                indices.append(int(item))
            except Exception:
                pass
        if not indices:
            return
        for idx in sorted(set(indices), reverse=True):
            if 0 <= idx < len(self.master_app.template_lines):
                self.master_app.template_lines.pop(idx)
        self.master_app.notify_template_changed(redraw=True)


class RetroActiveSpectraWindow(tk.Toplevel):
    """Active Spectra window reconstructed from Unit13."""
    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Active Spectra")
        self.geometry("760x430")
        self.minsize(720, 340)
        self.configure(bg=RETRO_BG)
        self.selected_index = 0
        self._build()

    def _build(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("n", "visible", "name", "points")
        self.tree = ttk.Treeview(main, columns=cols, show="headings", height=18)
        for c, w in [("n", 35), ("visible", 60), ("name", 360), ("points", 80)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center" if c != "name" else "w")
        self.tree.grid(row=0, column=0, columnspan=5, sticky="nsew")
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.bind("<Double-1>", self.visible_on_off)

        ttk.Label(main, text="Shift").grid(row=1, column=0, sticky="e", padx=3, pady=3)
        self.shift_var = tk.StringVar(value="0.0")
        ttk.Entry(main, textvariable=self.shift_var, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(main, text="Scale").grid(row=1, column=2, sticky="e", padx=3)
        self.scale_var = tk.StringVar(value="1.0")
        ttk.Entry(main, textvariable=self.scale_var, width=10).grid(row=1, column=3, sticky="w")

        btns = ttk.Frame(main)
        btns.grid(row=2, column=0, columnspan=5, sticky="ew", pady=4)
        for label, cmd in [
            ("Set to Main", self.set_to_main),
            ("Visible ON/OFF", self.visible_on_off),
            ("Change Color", self.change_color),
            ("Swap", self.swap),
            ("Min", self.min_selected),
            ("Average", self.average_selected),
            ("Max", self.max_selected),
            ("Shift", self.shift_copy),
            ("Scale", self.scale_copy),
            ("Delete", self.delete_selected),
            ("Close", self.destroy),
        ]:
            ttk.Button(btns, text=label, command=cmd).pack(side="left", padx=2, pady=2)

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, sp in enumerate(self.master_app.spectra):
            self.tree.insert("", "end", iid=str(i), values=(i+1, "Yes" if sp.visible else "No", sp.name, len(sp.x)))
        if self.master_app.spectra:
            self.tree.selection_set(str(min(self.selected_index, len(self.master_app.spectra)-1)))

    def _select(self, event=None):
        item = self.tree.focus()
        if item != "":
            self.selected_index = int(item)

    def selected_indices(self):
        out = []
        for iid in self.tree.selection():
            try:
                out.append(int(iid))
            except Exception:
                pass
        return out or [self.selected_index]

    def set_to_main(self):
        idx = self.selected_index
        if 0 <= idx < len(self.master_app.spectra):
            sp = self.master_app.spectra.pop(idx)
            self.master_app.spectra.insert(0, sp)
            self.selected_index = 0
            self.refresh()
            self.master_app.redraw()

    def visible_on_off(self):
        idx = self.selected_index
        if idx == 0:
            return
        if 0 <= idx < len(self.master_app.spectra):
            self.master_app.spectra[idx].visible = not self.master_app.spectra[idx].visible
            self.refresh()
            self.master_app.redraw()

    def change_color(self):
        # matplotlib auto-colors are currently used; keep this as a retro-compatible placeholder.
        _showinfo(self, "Active Spectra", "Color selection will be stored in a later pyLIBS build.")

    def swap(self):
        idx = self.selected_index
        if 0 < idx < len(self.master_app.spectra):
            self.master_app.spectra[idx-1], self.master_app.spectra[idx] = self.master_app.spectra[idx], self.master_app.spectra[idx-1]
            self.master_app.spectra[idx-1].color, self.master_app.spectra[idx].color = self.master_app.spectra[idx].color, self.master_app.spectra[idx-1].color
            self.selected_index = idx-1
            self.refresh()
            self.master_app.redraw()

    def _combine(self, mode):
        specs = [self.master_app.spectra[i] for i in self.selected_indices() if 0 <= i < len(self.master_app.spectra)]
        if len(specs) < 2:
            _showinfo(self, "Active Spectra", "Select at least two spectra.")
            return
        n = min(len(s.y) for s in specs)
        x = specs[0].x[:n]
        rows = list(zip(*[s.y[:n] for s in specs]))
        if mode == "Average":
            y = [sum(r)/len(r) for r in rows]
        elif mode == "Max":
            y = [max(r) for r in rows]
        else:
            y = [min(r) for r in rows]
        self.master_app.add_spectrum(Spectrum(list(x), y, mode))
        self.refresh()

    def min_selected(self): self._combine("Min")
    def average_selected(self): self._combine("Average")
    def max_selected(self): self._combine("Max")

    def shift_copy(self):
        idx = self.selected_index
        if 0 <= idx < len(self.master_app.spectra):
            off = safe_float(self.shift_var.get(), 0.0)
            src = self.master_app.spectra[idx]
            self.master_app.add_spectrum(src.shifted(off, f"{src.name} shifted"))
            self.refresh()

    def scale_copy(self):
        idx = self.selected_index
        if 0 <= idx < len(self.master_app.spectra):
            fac = safe_float(self.scale_var.get(), 1.0)
            src = self.master_app.spectra[idx]
            self.master_app.add_spectrum(src.scaled(fac, f"{src.name} scaled"))
            self.refresh()

    def delete_selected(self):
        indices = set(self.selected_indices())
        self.master_app.spectra = [s for i, s in enumerate(self.master_app.spectra) if i == 0 or i not in indices]
        self.selected_index = 0
        self.refresh()
        self.master_app.redraw()


class RetroFitManagerWindow(tk.Toplevel):
    """Manual/Auto Fit editor reconstructed from Unit14.

    Up to 10 template lines are edited, each with wavelength, wg, wl and fixed/free flags.
    """
    def __init__(self, master: "MainWindow", automatic=False, single=False):
        super().__init__(master)
        self.master_app = master
        self.automatic = bool(automatic)
        self.single = bool(single)
        self._auto_fit_after_id = None
        self.title("Automatic Fit" if self.automatic else "Single Fit" if self.single else "Manual Fit")
        self.geometry(legacy_geometry_to_tk(getattr(master.options, "fit_geometry", ""), "840x540"))
        self.minsize(800, 520)
        self.configure(bg=RETRO_BG)
        self.line_vars = []
        self.displayed_group_key = None
        self.displayed_lines = []
        self.manual_fit_current_indices = []
        self.manual_fit_lines = []
        self.manual_fit_index = 0
        self.manual_fit_failed = False
        self.manual_fit_stop = False
        self.fit_stop_requested = False
        self._fit_worker = None
        self._fit_running = False
        self.region_fit_results = {}
        self.residual_x = []
        self.residual_y = []
        self.residuals_window = None
        self._build()
        try:
            self.protocol("WM_DELETE_WINDOW", self.close_window)
        except Exception:
            pass
        self.load_from_template()
        if self.single:
            self.prepare_single_region()
        else:
            self.prepare_initial_region()
        if self.automatic:
            self._auto_fit_after_id = self.after(100, self.run_fit)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=4, pady=3)
        ttk.Button(top, text=("Auto Fit" if self.automatic else "Single Fit" if self.single else "Fit"), command=self.run_fit).pack(side="left", padx=2)
        ttk.Button(top, text="Stop", command=self.stop_fit).pack(side="left", padx=2)
        ttk.Button(top, text="Close", command=self.close_window).pack(side="left", padx=2)
        if not self.automatic and not self.single:
            ttk.Button(top, text="Next Region", command=self.next_region).pack(side="left", padx=8)
            ttk.Button(top, text="Refresh", command=self.refresh_region).pack(side="left", padx=2)
            ttk.Button(top, text="Previous Region", command=self.previous_region).pack(side="left", padx=2)
        if not self.automatic:
            ttk.Button(top, text="Show Residuals", command=self.show_residuals).pack(side="left", padx=8)
        self.msg_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.msg_var).pack(fill="x", padx=5, pady=2)

        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.pack(fill="x", padx=5, pady=2)

        grid = ttk.LabelFrame(self, text="Fit Parameters")
        grid.pack(fill="x", padx=5, pady=5)

        headers = ["Line", "λ", "Fix", "wg", "Fix", "wl", "Fix"]
        for c, h in enumerate(headers):
            ttk.Label(grid, text=h).grid(row=0, column=c, padx=3, pady=2)

        for r in range(10):
            ttk.Label(grid, text=str(r+1)).grid(row=r+1, column=0, padx=3, pady=2)
            lam = tk.StringVar(value="")
            wg = tk.StringVar(value="")
            wl = tk.StringVar(value="")
            flam = tk.BooleanVar(value=False)
            fwg = tk.BooleanVar(value=False)
            fwl = tk.BooleanVar(value=False)
            e1 = tk.Entry(grid, textvariable=lam, width=10, bg=RETRO_FREE)
            e2 = tk.Entry(grid, textvariable=wg, width=8, bg=RETRO_FREE)
            e3 = tk.Entry(grid, textvariable=wl, width=8, bg=RETRO_FREE)
            c1 = ttk.Checkbutton(grid, variable=flam, command=lambda rr=r: self._color_row(rr))
            c2 = ttk.Checkbutton(grid, variable=fwg, command=lambda rr=r: self._color_row(rr))
            c3 = ttk.Checkbutton(grid, variable=fwl, command=lambda rr=r: self._color_row(rr))
            e1.grid(row=r+1, column=1, padx=2, pady=1)
            c1.grid(row=r+1, column=2)
            e2.grid(row=r+1, column=3, padx=2, pady=1)
            c2.grid(row=r+1, column=4)
            e3.grid(row=r+1, column=5, padx=2, pady=1)
            c3.grid(row=r+1, column=6)
            self.line_vars.append((lam, wg, wl, flam, fwg, fwl, e1, e2, e3))

        results_frame = ttk.Frame(self)
        self.results = ttk.Treeview(
            results_frame,
            columns=("line", "center", "intensity", "lorentzian", "gaussian", "integral"),
            show="headings",
            height=7,
        )
        for c, label, w in [
            ("line", "Line", 70),
            ("center", "Fit Center Wavelength", 145),
            ("intensity", "Fit Intensity", 110),
            ("lorentzian", "Fit Lorentzian Width", 135),
            ("gaussian", "Fit Gaussian Width", 130),
            ("integral", "Fit Integral", 110),
        ]:
            self.results.heading(c, text=label)
            self.results.column(c, width=w, anchor="center")
        self.results.pack(fill="both", expand=True)
        results_frame.pack(fill="both", expand=True, padx=5, pady=4)

    def _window_ref_name(self):
        if self.automatic:
            return "auto_fit_window"
        if self.single:
            return "single_fit_window"
        return "manual_fit_window"

    def _clear_window_ref(self):
        ref_name = self._window_ref_name()
        if getattr(self.master_app, ref_name, None) is self:
            setattr(self.master_app, ref_name, None)

    def refresh_content(self):
        if self.single:
            self.prepare_single_region(preserve_user_values=True)
        else:
            self.prepare_initial_region(preserve_user_values=True)
        if self.automatic:
            try:
                if self._auto_fit_after_id is not None:
                    self.after_cancel(self._auto_fit_after_id)
            except Exception:
                pass
            self._auto_fit_after_id = self.after(100, self.run_fit)
        self.update_idletasks()

    def close_window(self):
        self.manual_fit_stop = True
        self.fit_stop_requested = True
        try:
            if self._auto_fit_after_id is not None:
                self.after_cancel(self._auto_fit_after_id)
        except Exception:
            pass
        self._auto_fit_after_id = None
        self._clear_window_ref()
        try:
            self.destroy()
        except Exception:
            pass

    def _color_row(self, r):
        lam, wg, wl, flam, fwg, fwl, e1, e2, e3 = self.line_vars[r]
        e1.configure(bg=RETRO_FIXED if flam.get() else RETRO_FREE)
        e2.configure(bg=RETRO_FIXED if fwg.get() else RETRO_FREE)
        e3.configure(bg=RETRO_FIXED if fwl.get() else RETRO_FREE)

    def load_from_template(self, lines=None, preserve_user_values=False):
        lines = list(lines if lines is not None else self.master_app.template_lines[:10])
        opts = self.master_app.options
        option_fix_wavelength = bool(getattr(opts, "fix_wavelength", False))
        option_fix_wg = bool(getattr(opts, "fix_wg", False))
        option_fix_wl = bool(getattr(opts, "fix_wl", False))
        option_fixed_wg = abs(safe_float(getattr(opts, "fixed_wg", 0.5), 0.5))
        option_fixed_wl = abs(safe_float(getattr(opts, "fixed_wl", 0.5), 0.5))
        preserved_values = {}
        if preserve_user_values:
            for r, t in enumerate(getattr(self, "displayed_lines", [])[:10]):
                if r >= len(self.line_vars):
                    break
                lam, wg, wl, flam, fwg, fwl, *_ = self.line_vars[r]
                preserved_values[id(t)] = {
                    "lam": lam.get(),
                    "wg": wg.get(),
                    "wl": wl.get(),
                    "flam": bool(flam.get()),
                    "fwg": bool(fwg.get()),
                    "fwl": bool(fwl.get()),
                }
        for r in range(10):
            lam, wg, wl, flam, fwg, fwl, e1, e2, e3 = self.line_vars[r]
            # Empty rows are not part of the current fit.  Do not preload
            # Options fixed widths there, otherwise Manual/Single/Auto Fit
            # appears to constrain lines that will not actually be fitted.
            lam.set("")
            wg.set("")
            wl.set("")
            flam.set(False)
            fwg.set(False)
            fwl.set(False)
            self._color_row(r)
        for r, t in enumerate(lines):
            if r >= 10:
                break
            lam, wg, wl, flam, fwg, fwl, e1, e2, e3 = self.line_vars[r]
            center = t.fitwavelen if t.fitwavelen else t.wavelen
            preserved = preserved_values.get(id(t))
            if preserved is not None:
                lam.set(preserved["lam"])
                wg.set(preserved["wg"])
                wl.set(preserved["wl"])
                flam.set(option_fix_wavelength or preserved["flam"])
                fwg.set(option_fix_wg or preserved["fwg"])
                fwl.set(option_fix_wl or preserved["fwl"])
            else:
                lam.set(f"{abs(center):.6g}")
                flam.set(option_fix_wavelength or center < 0)
                template_wg = safe_float(getattr(t, "wg", 0.0), 0.0)
                template_wl = safe_float(getattr(t, "wl", 0.0), 0.0)
                wg_value = option_fixed_wg if option_fix_wg else (abs(template_wg) if template_wg else option_fixed_wg)
                wl_value = option_fixed_wl if option_fix_wl else (abs(template_wl) if template_wl else option_fixed_wl)
                wg.set(f"{wg_value:.6g}")
                wl.set(f"{wl_value:.6g}")
                fwg.set(option_fix_wg or template_wg < 0)
                fwl.set(option_fix_wl or template_wl < 0)
            self._color_row(r)
        if len(lines) > 10:
            self.msg_var.set("Too many lines for fitting (> 10)")
        elif not lines:
            self.msg_var.set("No lines for fitting")
        else:
            self.msg_var.set(f"{len(lines)} line(s) ready for fitting")

    def apply_to_template(self):
        for r, t in enumerate(self.master_app.template_lines[:10]):
            lam, wg, wl, flam, fwg, fwl, *_ = self.line_vars[r]
            center = safe_float(lam.get(), t.fitwavelen or t.wavelen)
            gw = safe_float(wg.get(), t.wg or self.master_app.options.fixed_wg)
            lw = safe_float(wl.get(), t.wl or self.master_app.options.fixed_wl)
            t.fitwavelen = -abs(center) if flam.get() else abs(center)
            t.wg = abs(gw)
            t.wl = abs(lw)

    def _sorted_template_lines(self):
        return sorted(
            [t for t in self.master_app.template_lines if getattr(t, "wavelen", 0.0)],
            key=lambda t: t.wavelen,
        )

    def _manual_template_lines_source(self):
        visible = self._visible_template_lines()
        return visible if visible else self._sorted_template_lines()

    def _get_template_rows_sorted_by_wavelength(self):
        rows = []
        for idx, line in enumerate(getattr(self.master_app, "template_lines", []) or []):
            try:
                wavelength = float(getattr(line, "wavelen", 0.0) or 0.0)
            except Exception:
                continue
            if wavelength:
                rows.append((idx, wavelength, line))
        rows.sort(key=lambda item: item[1])
        return rows

    def _current_template_indices(self):
        indices = []
        all_lines = list(getattr(self.master_app, "template_lines", []) or [])
        visible_lines = self._visible_template_lines()
        source_lines = visible_lines or list(getattr(self, "displayed_lines", []) or [])
        for line in source_lines:
            try:
                indices.append(all_lines.index(line))
            except ValueError:
                pass
        self.manual_fit_current_indices = list(indices)
        return indices

    def _build_manual_fit_group_from_anchor(self, sorted_rows, anchor_pos, direction):
        if anchor_pos < 0 or anchor_pos >= len(sorted_rows):
            return [], []
        delta = self._manual_delta_min()
        positions = [anchor_pos]
        if direction == "previous":
            pos = anchor_pos - 1
            while pos >= 0 and abs(sorted_rows[pos + 1][1] - sorted_rows[pos][1]) < delta:
                positions.insert(0, pos)
                pos -= 1
        else:
            pos = anchor_pos + 1
            while pos < len(sorted_rows) and abs(sorted_rows[pos][1] - sorted_rows[pos - 1][1]) < delta:
                positions.append(pos)
                pos += 1
        return [sorted_rows[pos][2] for pos in positions], [sorted_rows[pos][0] for pos in positions]

    def _manual_delta_min(self):
        return max(safe_float(getattr(self.master_app.options, "delta_min", 1.0), 1.0), 1e-9)

    def _group_from_index(self, index):
        lines = self.manual_fit_lines
        if index < 0 or index >= len(lines):
            return [], index
        delta = self._manual_delta_min()
        group = [lines[index]]
        next_index = index + 1
        while next_index < len(lines):
            previous = lines[next_index - 1].wavelen
            current = lines[next_index].wavelen
            if abs(current - previous) < delta:
                group.append(lines[next_index])
                next_index += 1
            else:
                break
        return group, next_index

    def _group_center(self, group):
        return (group[0].wavelen + group[-1].wavelen) / 2.0

    def _group_key(self, group):
        return tuple(id(t) for t in group)

    def _display_manual_group(self, group, preserve_user_values=False):
        if not group or not getattr(self.master_app, "ax", None):
            return
        delta = self._manual_delta_min()
        xmin = group[0].wavelen - delta
        xmax = group[-1].wavelen + delta
        self.master_app.clear_fit_artists()
        self.master_app.ax.set_xlim(xmin, xmax)
        self.master_app.full_y_main_visible_x()
        self.master_app.canvas.draw_idle()
        self.master_app._update_xscroll()
        self.load_from_template(group, preserve_user_values=preserve_user_values)
        self.displayed_lines = list(group)
        self.displayed_group_key = self._group_key(group)
        rows_by_line = {id(line): idx for idx, _w, line in self._get_template_rows_sorted_by_wavelength()}
        self.manual_fit_current_indices = [
            rows_by_line[id(line)]
            for line in self.displayed_lines
            if id(line) in rows_by_line
        ]

    def _set_visible_fit_lines(self, lines, preserve_user_values=True):
        lines = list(lines or [])
        self.manual_fit_lines = list(lines)
        self.manual_fit_index = 0
        group_key = self._group_key(lines)
        if self.displayed_group_key != group_key:
            self.load_from_template(lines, preserve_user_values=preserve_user_values)
            self.displayed_lines = list(lines)
            self.displayed_group_key = group_key
        all_lines = list(getattr(self.master_app, "template_lines", []) or [])
        indices = []
        for line in lines:
            try:
                indices.append(all_lines.index(line))
            except ValueError:
                pass
        self.manual_fit_current_indices = indices

    def _show_group_region(self, group, preserve_user_values=False):
        if not group:
            return 0, False
        self._display_manual_group(group, preserve_user_values=preserve_user_values)
        min_points = self._minimum_fit_points(group)
        point_count = self._current_fit_point_count()
        expanded = False
        if point_count < min_points:
            point_count, expanded, _retries = self._expand_manual_window_to_points(group, min_points)
        visible_group = self._visible_template_lines()
        if visible_group and not self.automatic:
            group = visible_group
            self._set_visible_fit_lines(group, preserve_user_values=preserve_user_values)
        status = (
            f"Region: {group[0].wavelen:.4f} - {group[-1].wavelen:.4f}; "
            f"{len(group)} line(s), {point_count} point(s)"
        )
        if expanded:
            status += ", expanded"
        self.msg_var.set(status)
        self.master_app.status(status)
        self.populate_results(self.region_fit_results.get(self._group_key(group), []))
        return point_count, expanded

    def prepare_initial_region(self, preserve_user_values=False):
        if self.automatic:
            sorted_rows = self._get_template_rows_sorted_by_wavelength()
            self.manual_fit_lines = []
            self.manual_fit_index = 0
            group = []
            if sorted_rows:
                group, indices = self._build_manual_fit_group_from_anchor(sorted_rows, 0, "next")
                self.manual_fit_current_indices = list(indices)
            if group:
                self.manual_fit_lines = list(group)
                self._show_group_region(group, preserve_user_values=preserve_user_values)
            return
        self._set_visible_fit_lines(self._visible_template_lines(), preserve_user_values=preserve_user_values)
        if self.manual_fit_lines:
            lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
            self.msg_var.set(f"Manual Fit: {len(self.manual_fit_lines)} visible line(s) in {lo:.4f} - {hi:.4f}")
        else:
            self.manual_fit_current_indices = []
            self.manual_fit_lines = []
            self.displayed_lines = []
            self.displayed_group_key = None
            self.load_from_template([], preserve_user_values=preserve_user_values)
            self.msg_var.set("No visible template lines in the current spectrum window")

    def prepare_single_region(self, preserve_user_values=False):
        self.manual_fit_lines = self._visible_template_lines()
        self.manual_fit_index = 0
        self.load_from_template(self.manual_fit_lines, preserve_user_values=preserve_user_values)
        if self.manual_fit_lines:
            lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
            self.msg_var.set(f"Single Fit: {len(self.manual_fit_lines)} visible line(s) in {lo:.4f} - {hi:.4f}")
        else:
            self.msg_var.set("Single Fit: no template lines are visible in the current window")
            self.after(100, lambda: _showinfo(self, "Single Fit", "No template lines are visible in the current spectrum window."))

    def _current_group(self):
        if not self.manual_fit_lines:
            self.manual_fit_lines = self._manual_template_lines_source() if self.automatic else self._visible_template_lines()
        return self._group_from_index(self.manual_fit_index)

    def _current_fit_point_count(self):
        if not self.master_app.spectra or not getattr(self.master_app, "ax", None):
            return 0
        lo, hi = sorted(self.master_app.ax.get_xlim())
        sp = self.master_app.spectra[0]
        return sum(1 for x in sp.x if lo <= x <= hi)

    def _visible_template_lines(self):
        if not getattr(self.master_app, "ax", None):
            return []
        lo, hi = sorted(self.master_app.ax.get_xlim())
        return sorted(
            [t for t in self.master_app.template_lines if lo <= getattr(t, "wavelen", 0.0) <= hi],
            key=lambda t: t.wavelen,
        )

    def _minimum_fit_points(self, group):
        nparams = 2 + 4 * len(group)
        return max(8, 3 * nparams)

    def _data_x_limits(self):
        if not self.master_app.spectra:
            return None
        xs = list(getattr(self.master_app.spectra[0], "x", []) or [])
        if not xs:
            return None
        return min(xs), max(xs)

    def _is_too_few_fit_points_error(self, message):
        text = str(message or "").lower()
        return (
            "too few" in text
            or "not enough" in text
            or ("number of func parameters" in text and "must not exceed" in text)
            or ("input vector length" in text and "must not exceed" in text)
        )

    def _at_full_x_range(self, tol=1e-12):
        data_limits = self._data_x_limits()
        if not data_limits or not getattr(self.master_app, "ax", None):
            return True
        data_min, data_max = data_limits
        lo, hi = sorted(self.master_app.ax.get_xlim())
        span = max(abs(data_max - data_min), 1.0)
        eps = tol * span
        return lo <= data_min + eps and hi >= data_max - eps

    def _expand_current_window_50(self):
        data_limits = self._data_x_limits()
        if not data_limits or not getattr(self.master_app, "ax", None):
            return False
        if self._at_full_x_range():
            return False
        data_min, data_max = data_limits
        xmin, xmax = self.master_app.ax.get_xlim()
        old_limits = tuple(sorted((xmin, xmax)))
        current_width = abs(xmax - xmin)
        full_width = data_max - data_min
        if current_width <= 0 or full_width <= 0:
            return False
        center = (xmin + xmax) / 2.0
        new_width = min(current_width * 1.5, full_width)
        new_xmin = center - new_width / 2.0
        new_xmax = center + new_width / 2.0
        if new_xmin < data_min:
            new_xmin = data_min
            new_xmax = min(data_max, data_min + new_width)
        if new_xmax > data_max:
            new_xmax = data_max
            new_xmin = max(data_min, data_max - new_width)
        new_limits = tuple(sorted((new_xmin, new_xmax)))
        if new_limits == old_limits:
            return False
        self.master_app.clear_fit_artists()
        self.master_app.ax.set_xlim(new_xmin, new_xmax)
        self.master_app.full_y_main_visible_x()
        self.master_app.canvas.draw_idle()
        self.master_app._update_xscroll()
        return True

    def _expand_manual_window_to_points(self, group, min_points, max_retries=20):
        expanded = False
        retries = 0
        point_count = self._current_fit_point_count()
        while point_count < min_points and retries < max_retries:
            if not self._expand_current_window_50():
                break
            expanded = True
            retries += 1
            point_count = self._current_fit_point_count()
        return point_count, expanded, retries

    def _line_overrides_from_editor(self, lines, apply_to_template=True):
        overrides = {}
        displayed = list(getattr(self, "displayed_lines", []) or [])
        for r, t in enumerate(displayed[:10]):
            if t not in lines or r >= len(self.line_vars):
                continue
            lam, wg, wl, flam, fwg, fwl, *_ = self.line_vars[r]
            center = safe_float(lam.get(), getattr(t, "fitwavelen", 0.0) or getattr(t, "wavelen", 0.0))
            gw = abs(safe_float(wg.get(), getattr(t, "wg", 0.0) or getattr(self.master_app.options, "fixed_wg", 0.5)))
            lw = abs(safe_float(wl.get(), getattr(t, "wl", 0.0) or getattr(self.master_app.options, "fixed_wl", 0.5)))
            if apply_to_template:
                t.fitwavelen = -abs(center) if flam.get() else abs(center)
                # Keep both widths positive in the template/output, even when fixed.
                t.wg = abs(gw)
                t.wl = abs(lw)
            overrides[id(t)] = {
                "center": abs(center),
                "fix_center": bool(flam.get()),
                "wg": gw,
                "wl": lw,
                "fix_wg": bool(fwg.get()),
                "fix_wl": bool(fwl.get()),
            }
        return overrides

    def _active_spectrum_snapshot(self):
        sp = None
        try:
            aw = getattr(self.master_app, "active_window", None)
            if aw is not None and aw.winfo_exists():
                idx = getattr(aw, "selected_index", 0)
                if 0 <= idx < len(self.master_app.spectra):
                    sp = self.master_app.spectra[idx]
        except Exception:
            sp = None
        if sp is None and self.master_app.spectra:
            sp = self.master_app.spectra[0]
        if sp is None:
            return None
        return {
            "x": list(getattr(sp, "x", []) or []),
            "y": list(getattr(sp, "y", []) or []),
        }

    def _build_voigt_fit_snapshot(self, lines):
        xlim, ylim = self.master_app.current_plot_view()
        opts = self.master_app.options
        spectrum = self._active_spectrum_snapshot()
        return {
            "spectrum": spectrum,
            "xlim": tuple(xlim),
            "ylim": tuple(ylim),
            "line_overrides": self._line_overrides_from_editor(list(lines), apply_to_template=False),
            "lines": [
                {
                    "key": id(t),
                    "wavelen": safe_float(getattr(t, "wavelen", 0.0), 0.0),
                    "fitwavelen": safe_float(getattr(t, "fitwavelen", 0.0), 0.0),
                    "wg": safe_float(getattr(t, "wg", 0.0), 0.0),
                    "wl": safe_float(getattr(t, "wl", 0.0), 0.0),
                    "specie": getattr(t, "specie", ""),
                }
                for t in list(lines)
            ],
            "options": {
                "fixed_wg": safe_float(getattr(opts, "fixed_wg", 0.5), 0.5),
                "fixed_wl": safe_float(getattr(opts, "fixed_wl", 0.5), 0.5),
                "fix_wg": bool(getattr(opts, "fix_wg", False)),
                "fix_wl": bool(getattr(opts, "fix_wl", False)),
                "fix_wavelength": bool(getattr(opts, "fix_wavelength", False)),
                "iterations": safe_int(getattr(opts, "iterations", 20), 20),
            },
        }

    def _run_voigt_fit_snapshot(self, snapshot, stop_requested):
        if np is None:
            return False, "numpy not available", None
        try:
            from scipy.optimize import curve_fit
        except Exception:
            return False, "scipy.optimize not available. Install scipy.", None
        if stop_requested():
            raise FitStoppedError()
        spectrum = snapshot.get("spectrum")
        if not spectrum or not spectrum.get("x"):
            return False, "Load a spectrum first.", None
        x_values = list(spectrum.get("x") or [])
        y_values = list(spectrum.get("y") or [])
        lo, hi = sorted(snapshot.get("xlim", (-math.inf, math.inf)))
        pairs = [(x, y_values[i]) for i, x in enumerate(x_values) if i < len(y_values) and lo <= x <= hi]
        if not pairs:
            return False, "Too few points in the visible window.", None
        xs = np.asarray([x for x, _y in pairs], dtype=float)
        ys = np.asarray([y for _x, y in pairs], dtype=float)
        if len(xs) < 8:
            return False, "Too few points in the visible window.", None
        lines = list(snapshot.get("lines") or [])
        if not lines:
            return False, "No marked line in the visible window. Use search/manual marking before fitting.", None
        xmin, xmax = float(xs.min()), float(xs.max())
        width = max(xmax - xmin, 1e-9)
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        dx = float(np.median(np.diff(np.sort(xs)))) if len(xs) > 2 else width / 100.0
        options = snapshot.get("options") or {}
        default_fixed_wg = abs(safe_float(options.get("fixed_wg"), 0.5))
        default_fixed_wl = abs(safe_float(options.get("fixed_wl"), 0.5))
        min_sigma0 = max(default_fixed_wg / 2.354820045, abs(dx), 1e-6)
        min_gamma0 = max(default_fixed_wl / 2.0, abs(dx), 1e-6)
        sigma0 = max(default_fixed_wg, abs(dx), 1e-6)
        gamma0 = max(default_fixed_wl / 2.0, abs(dx), 1e-6)
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        fixed_mask = [False, False]
        line_overrides = snapshot.get("line_overrides") or {}
        half_window = max(width / 20.0, width * 0.02, abs(dx) * 2.0)
        for line in lines:
            if stop_requested():
                raise FitStoppedError()
            override = line_overrides.get(line["key"], {})
            if override:
                center0 = abs(safe_float(override.get("center"), line["fitwavelen"] or line["wavelen"]))
            else:
                center0 = line["wavelen"]
            peak_y = _nearest_y(x_values, y_values, center0)
            height = max(float(peak_y) - baseline, float(max(ys)) - baseline, 1.0)
            area0 = max(height * sigma0 * math.sqrt(2.0 * math.pi), 1e-12)
            if override:
                row_fix_wg = bool(override.get("fix_wg", False))
                row_fix_wl = bool(override.get("fix_wl", False))
                wg_fwhm = abs(safe_float(override.get("wg"), line["wg"] or default_fixed_wg))
                wl_fwhm = abs(safe_float(override.get("wl"), line["wl"] or default_fixed_wl))
            else:
                row_fix_wg = bool(options.get("fix_wg", False)) or line["wg"] < 0
                row_fix_wl = bool(options.get("fix_wl", False)) or line["wl"] < 0
                wg_fwhm = default_fixed_wg if bool(options.get("fix_wg", False)) else (abs(line["wg"]) if line["wg"] else default_fixed_wg)
                wl_fwhm = default_fixed_wl if bool(options.get("fix_wl", False)) else (abs(line["wl"]) if line["wl"] else default_fixed_wl)
            sig0 = max(wg_fwhm / 2.354820045, 1e-12 if row_fix_wg else min_sigma0)
            gam0 = max(wl_fwhm / 2.0, 1e-12 if row_fix_wl else min_gamma0)
            p0.extend([area0, center0, max(sig0, 1e-6), max(gam0, 1e-6)])
            c_lo = max(xmin, center0 - half_window)
            c_hi = min(xmax, center0 + half_window)
            row_fix_center = bool(override.get("fix_center", False)) if override else (
                bool(options.get("fix_wavelength", False)) or line["fitwavelen"] < 0
            )
            sigma_lo = max(abs(dx) * 0.05, 1e-9)
            sigma_hi = max(width, sigma0 * 50.0)
            gamma_lo = max(abs(dx) * 0.05, 1e-9)
            gamma_hi = max(width, gamma0 * 50.0)
            bounds_lo.extend([0.0, c_lo, sigma_lo, gamma_lo])
            bounds_hi.extend([np.inf, c_hi, sigma_hi, gamma_hi])
            fixed_mask.extend([False, row_fix_center, row_fix_wg, row_fix_wl])
        p0_full = np.asarray(p0, dtype=float)
        bounds_lo_full = np.asarray(bounds_lo, dtype=float)
        bounds_hi_full = np.asarray(bounds_hi, dtype=float)
        fixed_mask = np.asarray(fixed_mask, dtype=bool)
        free_mask = ~fixed_mask

        def _expand_fit_parameters(p_free):
            p_all = p0_full.copy()
            p_all[free_mask] = np.asarray(p_free, dtype=float)
            return p_all

        def _multivoigt_model_free(x, *p_free):
            if stop_requested():
                raise FitStoppedError()
            return multivoigt_model(x, *_expand_fit_parameters(p_free))

        popt_free, _pcov = curve_fit(
            _multivoigt_model_free,
            xs,
            ys,
            p0=p0_full[free_mask],
            bounds=(bounds_lo_full[free_mask], bounds_hi_full[free_mask]),
            maxfev=max(2000, safe_int(options.get("iterations"), 20) * 400),
        )
        if stop_requested():
            raise FitStoppedError()
        popt = _expand_fit_parameters(popt_free)
        fitted_values = []
        for idx, line in enumerate(lines):
            area = float(popt[2 + 4 * idx])
            cen = float(popt[3 + 4 * idx])
            sigma = abs(float(popt[4 + 4 * idx]))
            gamma = abs(float(popt[5 + 4 * idx]))
            fitted_wg = float(2.354820045 * sigma)
            fitted_wl = float(2.0 * gamma)
            peak_height = float(area * voigt_profile_unit(np.asarray([cen], dtype=float), cen, sigma, gamma)[0])
            fitted_values.append({
                "key": line["key"],
                "template_wavelength": float(line["wavelen"]),
                "fit_center": cen,
                "peak_intensity": peak_height,
                "lorentzian_width": abs(fitted_wl),
                "gaussian_width": abs(fitted_wg),
                "integrated_area": area,
                "sigma": sigma,
                "gamma": gamma,
            })
        fitted_y = multivoigt_model(xs, *popt)
        payload = {
            "fit_values": fitted_values,
            "overlay": (xs.tolist(), fitted_y.tolist()),
            "residual_x": xs.tolist(),
            "residual_y": (ys - fitted_y).tolist(),
            "xlim": snapshot.get("xlim"),
            "ylim": snapshot.get("ylim"),
        }
        return True, f"Fit Voigt: {len(lines)} line(s)", payload

    def _apply_voigt_fit_payload(self, lines, payload, mode_label):
        by_key = {item.get("key"): item for item in list(payload.get("fit_values") or [])}
        results = []
        for t in list(lines):
            item = by_key.get(id(t))
            if not item:
                continue
            t.fitwavelen = float(item["fit_center"])
            t.inte = float(item["integrated_area"])
            t.wg = abs(float(item["gaussian_width"]))
            t.wl = abs(float(item["lorentzian_width"]))
            enriched = False
            try:
                enriched = bool(self.master_app.enrich_identified_template_line(
                    t,
                    tolerance=max(0.02, self.master_app.options.search_range),
                ))
            except Exception:
                enriched = False
            result = {
                "key": id(t),
                "template_wavelength": float(getattr(t, "wavelen", item["template_wavelength"])),
                "fit_center": float(item["fit_center"]),
                "peak_intensity": float(item["peak_intensity"]),
                "lorentzian_width": float(t.wl),
                "gaussian_width": float(t.wg),
                "integrated_area": float(item["integrated_area"]),
            }
            if enriched:
                result["status"] = "Voigt OK + DB"
            results.append(result)
        self.master_app.fit_overlay = payload.get("overlay")
        self.residual_x = list(payload.get("residual_x") or [])
        self.residual_y = list(payload.get("residual_y") or [])
        self.master_app.notify_template_changed(redraw=False)
        self.master_app.redraw(preserve_view=True)
        self.master_app.restore_plot_view(payload.get("xlim"), payload.get("ylim"))
        if not self.automatic:
            self.update_residuals_plot(lift_window=False)
        self.master_app.status(f"Voigt fit: {len(results)} lines in the visible window")
        return results

    def _finish_async_fit(self, mode_label, fit_lines, report, result, show_errors, callback):
        self._fit_running = False
        self._fit_worker = None
        status = result.get("status")
        message = result.get("message", "")
        if status == "stopped":
            self.manual_fit_stop = True
            self.msg_var.set("Fit stopped by user")
            self.master_app.status("Fit stopped by user")
            if callback:
                callback(False, fit_lines, message, stopped=True)
            return
        if self.fit_stop_requested:
            self.manual_fit_stop = True
            self.msg_var.set("Fit stopped by user")
            self.master_app.status("Fit stopped by user")
            if callback:
                callback(False, fit_lines, "Fit stopped by user", stopped=True)
            return
        if status == "error":
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; Fit failed: {message}")
            if show_errors:
                lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
                _showerror(self, mode_label, f"Fit failed for current window {lo:.4f} - {hi:.4f}:\n{message}")
            if callback:
                callback(False, fit_lines, message, stopped=False)
            return
        results = self._apply_voigt_fit_payload(fit_lines, result.get("payload") or {}, mode_label)
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{report}; fitted")
        self.master_app.status(f"{report}; fitted")
        if callback:
            callback(True, fit_lines, message, stopped=False)

    def _start_visible_fit_async(self, mode_label, allow_previous_visible_fallback=True, show_errors=True, callback=None, reset_stop=True):
        if self._fit_running:
            self.msg_var.set(f"{mode_label}: fit already running")
            return False
        if reset_stop:
            self.manual_fit_stop = False
            self.fit_stop_requested = False
        elif self.manual_fit_stop or self.fit_stop_requested:
            if callback:
                callback(False, [], "Fit stopped by user", stopped=True)
            return False
        fit_lines = self._visible_template_lines()
        self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
        if not fit_lines:
            message = f"{mode_label}: no template lines are visible in the current window"
            self.msg_var.set(message)
            if show_errors:
                _showinfo(self, mode_label, "No template lines are visible in the current spectrum window.")
            elif callback:
                callback(False, [], message, stopped=False)
            return False
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines)
        lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
        report = f"{mode_label}: fitting {len(fit_lines)} visible line(s) using {point_count} points"
        self.msg_var.set(report)
        self.master_app.status(report)
        if point_count < min_points:
            point_count, expanded, retries = self._expand_manual_window_to_points(fit_lines, min_points)
            if expanded:
                updated_lines = self._visible_template_lines()
                if updated_lines:
                    fit_lines = updated_lines
                elif not allow_previous_visible_fallback:
                    message = "No visible template lines in the current Manual Fit window."
                    self.msg_var.set(f"{report}; {message}")
                    if show_errors:
                        _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}")
                    elif callback:
                        callback(False, fit_lines, message, stopped=False)
                    return False
                self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
                min_points = self._minimum_fit_points(fit_lines)
                report = f"{mode_label}: expanded window, fitting {len(fit_lines)} visible line(s) using {point_count} points"
                self.msg_var.set(report)
                self.master_app.status(report)
            if point_count < min_points:
                message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
                self.msg_var.set(f"{report}; {message}")
                if show_errors:
                    _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}\nExpansion retries: {retries}")
                elif callback:
                    callback(False, fit_lines, message, stopped=False)
                return False
        snapshot = self._build_voigt_fit_snapshot(fit_lines)
        self._fit_running = True

        def worker():
            try:
                ok, message, payload = self._run_voigt_fit_snapshot(
                    snapshot,
                    lambda: bool(getattr(self, "fit_stop_requested", False)),
                )
                result = {"status": "success" if ok else "error", "message": message, "payload": payload}
            except FitStoppedError:
                result = {"status": "stopped", "message": "Fit stopped by user", "payload": None}
            except Exception as exc:
                result = {"status": "error", "message": str(exc), "payload": None}
            try:
                self.after(0, lambda: self._finish_async_fit(mode_label, fit_lines, report, result, show_errors, callback))
            except Exception:
                pass

        self._fit_worker = threading.Thread(target=worker, daemon=True)
        self._fit_worker.start()
        return True

    def _fit_manual_group(self, lines):
        tmp = None
        try:
            tmp = MultiGaussianFitWindow(self.master_app)
            tmp.withdraw()
            overrides = self._line_overrides_from_editor(list(lines))
            ok, message, results = tmp.fit_voigt_lines(
                lines=lines,
                preserve_view=True,
                show_messages=False,
                line_overrides=overrides,
            )
            if ok and not self.automatic:
                self.residual_x = list(getattr(tmp, "last_residual_x", []) or [])
                self.residual_y = list(getattr(tmp, "last_residual_y", []) or [])
                self.update_residuals_plot(lift_window=False)
        except Exception as e:
            ok, message, results = False, str(e), []
        finally:
            try:
                if tmp is not None:
                    tmp.destroy()
            except Exception:
                pass
        return ok, message, results

    def _residuals_window_exists(self):
        try:
            return self.residuals_window is not None and self.residuals_window.winfo_exists()
        except Exception:
            return False

    def show_residuals(self):
        if not self.residual_x or not self.residual_y:
            self.msg_var.set(f"No residuals available. Run {'Single Fit' if self.single else 'Manual Fit'} first.")
            return
        if self._residuals_window_exists():
            self.update_residuals_plot(lift_window=True)
            return
        self.residuals_window = ResidualsWindow(self, self.residual_x, self.residual_y)
        self.residuals_window.transient(self)
        restore_lift_focus(self.residuals_window, self)

    def update_residuals_plot(self, lift_window=False):
        if not self._residuals_window_exists():
            self.residuals_window = None
            return
        self.residuals_window.update_plot(self.residual_x, self.residual_y)
        if lift_window:
            restore_lift_focus(self.residuals_window, self)

    def on_residuals_window_close(self):
        if self._residuals_window_exists():
            try:
                self.residuals_window.destroy()
            except Exception:
                pass
        self.residuals_window = None

    def _prepare_group_for_fit(self, group, mode_label):
        first = group[0].wavelen
        last = group[-1].wavelen
        self.msg_var.set(f"Fitting {len(group)} line(s): {first:.4f} - {last:.4f}")
        # Do not reload the editor rows when the same group is already shown:
        # the user may have changed widths or fixed/free checkboxes before Fit.
        if self.displayed_group_key != self._group_key(group):
            self._display_manual_group(group, preserve_user_values=True)
        self.update_idletasks()
        min_points = self._minimum_fit_points(group)
        point_count = self._current_fit_point_count()
        if point_count < min_points:
            point_count, expanded, retries = self._expand_manual_window_to_points(group, min_points)
            self.update_idletasks()
        else:
            expanded = False
            retries = 0
        report = (
            f"{mode_label}: {'expanded window, ' if expanded else ''}"
            f"fitting {len(group)} line(s) using {point_count} points"
        )
        self.msg_var.set(report)
        self.master_app.status(report)
        if point_count < min_points:
            message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
            return False, report, message, retries
        return True, report, "", retries

    def _fit_group_once(self, group, mode_label):
        ready, report, message, retries = self._prepare_group_for_fit(group, mode_label)
        first = group[0].wavelen
        last = group[-1].wavelen
        if not ready:
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; {message}")
            _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}\nExpansion retries: {retries}")
            return False
        fit_lines = self._visible_template_lines()
        if not fit_lines:
            if mode_label == "Manual Fit":
                message = "No visible template lines in the current Manual Fit window."
                self.manual_fit_failed = True
                self.msg_var.set(f"{report}; {message}")
                _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}")
                return False
            fit_lines = list(group)
        expanded_for_visible = False
        extra_retries = 0
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines)
        while point_count < min_points and extra_retries < 20:
            old_count = point_count
            point_count, expanded, retries_used = self._expand_manual_window_to_points(group, min_points)
            expanded_for_visible = expanded_for_visible or expanded
            extra_retries += max(1, retries_used)
            fit_lines = self._visible_template_lines()
            if not fit_lines:
                if mode_label == "Manual Fit":
                    message = "No visible template lines in the current Manual Fit window."
                    self.manual_fit_failed = True
                    self.msg_var.set(f"{report}; {message}")
                    _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}")
                    return False
                fit_lines = list(group)
            min_points = self._minimum_fit_points(fit_lines)
            if point_count >= min_points or point_count == old_count:
                break
        if point_count < min_points:
            message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; {message}")
            _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}")
            return False
        if expanded_for_visible:
            report = (
                f"{mode_label}: expanded window, "
                f"fitting {len(fit_lines)} line(s) using {point_count} points"
            )
            self.msg_var.set(report)
            self.master_app.status(report)
        elif len(fit_lines) != len(group):
            report = f"{mode_label}: fitting {len(fit_lines)} visible line(s) using {point_count} points"
            self.msg_var.set(report)
            self.master_app.status(report)
        ok, message, results = self._fit_manual_group(fit_lines)
        while not ok and self._is_too_few_fit_points_error(message) and extra_retries < 20:
            old_limits = tuple(sorted(self.master_app.ax.get_xlim()))
            if not self._expand_current_window_50():
                break
            extra_retries += 1
            if tuple(sorted(self.master_app.ax.get_xlim())) == old_limits:
                break
            fit_lines = self._visible_template_lines()
            if not fit_lines:
                if mode_label == "Manual Fit":
                    message = "No visible template lines in the current Manual Fit window."
                    self.manual_fit_failed = True
                    self.msg_var.set(f"{report}; {message}")
                    _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}")
                    return False
                fit_lines = list(group)
            point_count = self._current_fit_point_count()
            report = (
                f"{mode_label}: expanded window, "
                f"fitting {len(fit_lines)} line(s) using {point_count} points"
            )
            self.msg_var.set(report)
            self.master_app.status(report)
            ok, message, results = self._fit_manual_group(fit_lines)
        if not ok:
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; Fit failed: {message}")
            _showerror(self, mode_label, f"Fit failed for {first:.4f} - {last:.4f}:\n{message}")
            return False
        self.region_fit_results[self._group_key(group)] = list(results)
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{report}; fitted")
        self.master_app.status(f"{report}; fitted")
        self.update_idletasks()
        return True

    def run_fit(self):
        if not self.master_app.spectra:
            _showinfo(self, "Fit", "Load a spectrum first.")
            return
        if self.single:
            self.run_single_fit()
            return
        self.manual_fit_failed = False
        self.manual_fit_stop = False
        self.fit_stop_requested = False
        if self.automatic:
            if not self.manual_fit_lines:
                sorted_rows = self._get_template_rows_sorted_by_wavelength()
                if not sorted_rows:
                    self.msg_var.set("No lines for fitting")
                    _showinfo(self, "Fit", "No template lines to fit.")
                    return
            self._run_automatic_fit()
            return

        def _manual_done(ok, _fit_lines, _message, stopped=False):
            if ok:
                self.progress["value"] = self._manual_visible_progress()

        self._start_visible_fit_async(
            "Manual Fit",
            allow_previous_visible_fallback=False,
            show_errors=True,
            callback=_manual_done,
        )

    def refresh_region(self):
        if self.automatic:
            return
        visible_lines = self._visible_template_lines()
        if not visible_lines:
            self.manual_fit_lines = []
            self.manual_fit_current_indices = []
            self.msg_var.set("Manual Fit: no template lines are visible in the current window")
            _showinfo(self, "Manual Fit", "No template lines are visible in the current spectrum window.")
            return
        self._display_manual_group(visible_lines, preserve_user_values=True)
        self.manual_fit_lines = list(visible_lines)
        self.manual_fit_index = 0
        self.manual_fit_failed = False
        self.populate_results([])
        self.progress["value"] = self._manual_visible_progress()
        lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
        self.msg_var.set(f"Manual Fit refreshed: {len(visible_lines)} visible line(s) in {lo:.4f} - {hi:.4f}")
        self.master_app.status(self.msg_var.get())

    def _fit_current_visible_window(self, mode_label, allow_previous_visible_fallback=True, show_errors=True):
        fit_lines = self._visible_template_lines()
        self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
        if not fit_lines:
            self.msg_var.set(f"{mode_label}: no template lines are visible in the current window")
            if show_errors:
                _showinfo(self, mode_label, "No template lines are visible in the current spectrum window.")
            return False, []
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines)
        lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
        report = f"{mode_label}: fitting {len(fit_lines)} visible line(s) using {point_count} points"
        self.msg_var.set(report)
        self.master_app.status(report)
        if point_count < min_points:
            point_count, expanded, retries = self._expand_manual_window_to_points(fit_lines, min_points)
            if expanded:
                updated_lines = self._visible_template_lines()
                if updated_lines:
                    fit_lines = updated_lines
                elif not allow_previous_visible_fallback:
                    message = "No visible template lines in the current Manual Fit window."
                    self.msg_var.set(f"{report}; {message}")
                    if show_errors:
                        _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}")
                    return False, []
                self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
                min_points = self._minimum_fit_points(fit_lines)
                report = f"{mode_label}: expanded window, fitting {len(fit_lines)} visible line(s) using {point_count} points"
                self.msg_var.set(report)
                self.master_app.status(report)
            if point_count < min_points:
                message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
                self.msg_var.set(f"{report}; {message}")
                if show_errors:
                    _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}\nExpansion retries: {retries}")
                return False, fit_lines
        ok, message, results = self._fit_manual_group(fit_lines)
        retries = 0
        while not ok and self._is_too_few_fit_points_error(message) and retries < 20:
            old_limits = tuple(sorted(self.master_app.ax.get_xlim()))
            if not self._expand_current_window_50():
                break
            retries += 1
            if tuple(sorted(self.master_app.ax.get_xlim())) == old_limits:
                break
            updated_lines = self._visible_template_lines()
            if updated_lines:
                fit_lines = updated_lines
            elif not allow_previous_visible_fallback:
                message = "No visible template lines in the current Manual Fit window."
                self.msg_var.set(f"{report}; {message}")
                if show_errors:
                    _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}")
                return False, []
            self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
            point_count = self._current_fit_point_count()
            report = f"{mode_label}: expanded window, fitting {len(fit_lines)} visible line(s) using {point_count} points"
            self.msg_var.set(report)
            self.master_app.status(report)
            ok, message, results = self._fit_manual_group(fit_lines)
        if not ok:
            self.msg_var.set(f"{report}; Fit failed: {message}")
            if show_errors:
                _showerror(self, mode_label, f"Fit failed for current window {lo:.4f} - {hi:.4f}:\n{message}")
            return False, fit_lines
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{report}; fitted")
        self.master_app.status(f"{report}; fitted")
        return True, fit_lines

    def run_single_fit(self):
        ok, _fit_lines = self._fit_current_visible_window("Single Fit")
        if ok:
            self.progress["value"] = 100

    def _manual_visible_progress(self):
        sorted_rows = self._get_template_rows_sorted_by_wavelength()
        current_indices = set(self._current_template_indices())
        if not sorted_rows or not current_indices:
            return 0
        positions = [pos for pos, (idx, _w, _line) in enumerate(sorted_rows) if idx in current_indices]
        if not positions:
            return 0
        return min(100, int(100 * (max(positions) + 1) / len(sorted_rows)))

    def _mark_fit_error(self, lines):
        for line in list(lines or []):
            line.inte = "ERROR"
            line.wl = "ERROR"
            line.wg = "ERROR"
            line.error_inte = "ERROR"
            try:
                line.fitinte = "ERROR"
            except Exception:
                pass
        try:
            self.master_app.notify_template_changed(redraw=False)
        except Exception:
            pass

    def _run_automatic_fit(self):
        sorted_rows = self._get_template_rows_sorted_by_wavelength()
        if not sorted_rows:
            self.msg_var.set("No lines for fitting")
            return
        self.manual_fit_stop = False
        self.fit_stop_requested = False
        self.msg_var.set("Starting Automatic Fit....")
        if not self.manual_fit_lines:
            group, indices = self._build_manual_fit_group_from_anchor(sorted_rows, 0, "next")
            if not group:
                self.msg_var.set("No lines for fitting")
                return
            self.manual_fit_lines = list(group)
            self.manual_fit_current_indices = list(indices)
            self._show_group_region(group, preserve_user_values=True)

        def _auto_done(ok, fit_lines, _message, stopped=False):
            if stopped or self.manual_fit_stop or self.fit_stop_requested:
                self.msg_var.set("Automatic Fit stopped")
                self.master_app.status("Automatic Fit stopped")
                return
            if not ok:
                current_lines = fit_lines or self._visible_template_lines()
                self._mark_fit_error(current_lines)
                self.msg_var.set(f"Automatic Fit: ERROR marked for {len(current_lines)} line(s)")
            self.progress["value"] = self._manual_visible_progress()
            if not self._move_manual_region("next", preserve_user_values=True):
                self.progress["value"] = 100
                self.msg_var.set("Automatic Fit completed")
                _showinfo(self, "Automatic Fit", "Automatic Fit completed")
                return
            self.after(0, lambda: self._start_visible_fit_async(
                "Automatic Fit",
                allow_previous_visible_fallback=False,
                show_errors=False,
                callback=_auto_done,
                reset_stop=False,
            ))

        if not self._visible_template_lines():
            self.msg_var.set("No lines for fitting")
            return
        self._start_visible_fit_async(
            "Automatic Fit",
            allow_previous_visible_fallback=False,
            show_errors=False,
            callback=_auto_done,
            reset_stop=False,
        )

    def populate_results(self, rows=None):
        self.results.delete(*self.results.get_children())
        for i, row in enumerate(list(rows or []), start=1):
            self.results.insert("", "end", values=(
                f"Line {i}",
                format_template_display_value(row.get("fit_center", "")),
                format_template_display_value(row.get("peak_intensity", "")),
                format_template_display_value(row.get("lorentzian_width", "")),
                format_template_display_value(row.get("gaussian_width", "")),
                format_template_display_value(row.get("integrated_area", "")),
            ))

    def stop_fit(self):
        self.manual_fit_stop = True
        self.fit_stop_requested = True
        self.msg_var.set("Stopping fit..." if self._fit_running else "Fit stopped")
        try:
            self.master_app.status("Stopping fit..." if self._fit_running else "Fit stopped")
        except Exception:
            pass

    def _move_manual_region(self, direction, preserve_user_values=True):
        sorted_rows = self._get_template_rows_sorted_by_wavelength()
        current_indices = set(self._current_template_indices())
        if not sorted_rows or not current_indices:
            self.msg_var.set("No lines for fitting")
            return False
        current_positions = [pos for pos, (idx, _w, _line) in enumerate(sorted_rows) if idx in current_indices]
        if not current_positions:
            self.msg_var.set("No current region")
            return False
        if direction == "previous":
            anchor_pos = min(current_positions) - 1
            if anchor_pos < 0:
                return False
        else:
            anchor_pos = max(current_positions) + 1
            if anchor_pos >= len(sorted_rows):
                return False
        group, indices = self._build_manual_fit_group_from_anchor(sorted_rows, anchor_pos, direction)
        if not group:
            return False
        self.manual_fit_failed = False
        self.manual_fit_lines = list(group)
        self.manual_fit_index = 0
        self.manual_fit_current_indices = list(indices)
        self._show_group_region(group, preserve_user_values=preserve_user_values)
        return True

    def next_region(self):
        self._move_manual_region("next", preserve_user_values=True)

    def previous_region(self):
        self._move_manual_region("previous", preserve_user_values=True)

    def toggle_expand(self):
        if self.winfo_width() > 500:
            self.geometry("420x520")
        else:
            self.geometry("760x520")


def _view_bool(value, default=False):
    """Return a real bool for view options read from pyLIBS.ini or Tk variables."""
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _background_color(value, default="#ffffff"):
    """Return a Matplotlib/Tk-compatible background colour, preferably #rrggbb."""
    text = str(value or "").strip()
    if not text:
        return default
    if _matplotlib_to_hex is not None:
        try:
            return _matplotlib_to_hex(text)
        except ValueError:
            return default
        except Exception:
            pass
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return text.lower()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", text):
        return "#" + "".join(ch * 2 for ch in text[1:].lower())
    return default


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self._startup_splash = show_startup_splash(self, SPLASH_DURATION_MS)
        configure_retro_style(self)
        self.options=AppOptions()
        self.loaded_ini_path = load_pylibs_ini(self.options)
        self.use_saved_window_positions = False
        self.title(APP_TITLE); self.geometry("1280x720")
        self.libs_db=LibsDatabase(self.options.libs_db_file)
        self.spectra: list[Spectrum]=[]
        self.response = None
        self.load_configured_response(silent=True)
        self.template_lines: list[TemplateLine]=[]
        self.atomic_lines: list[AtomicLine]=[]
        self.element_markers: list[AtomicLine]=[]
        self.trace_markers: list[AtomicLine]=[]
        self.trace_window=None
        # View menu state: independent X/Y grids,
        # independent logarithmic axes and spectrum-area background colour.
        self.view_grid_x = _view_bool(getattr(self.options, "view_grid_x", True), True)
        self.view_grid_y = _view_bool(getattr(self.options, "view_grid_y", True), True)
        self.view_log_x = bool(getattr(self.options, "view_log_x", False))
        self.view_log_y = bool(getattr(self.options, "view_log_y", False))
        self.plot_background = _background_color(getattr(self.options, "background_color", "#ffffff"), "#ffffff")
        self.options.background_color = self.plot_background
        self.fit_overlay: Optional[tuple[list[float], list[float]]] = None
        self.last_cflibs_rows: list[dict] = []
        self.last_halpha_result: Optional[dict] = None
        self.last_saha_boltzmann: Optional[dict] = None
        self.standard_refs: dict[str, str] = {}
        self.opc_nominal_percent: dict[str, float] = {}
        self.session_ne: Optional[float] = None
        self.session_ne_source: Optional[str] = None
        self.session_temperature: Optional[float] = None
        self.session_temperature_source: Optional[str] = None
        self.wavelength_unit = "angstrom"
        self.template_window=None; self.line_window=None; self.response_window=None; self.active_window=None; self.options_window=None
        self.manual_fit_window = None
        self.single_fit_window = None
        self.auto_fit_window = None
        self.batch_window = None
        self.shift_window = None
        self.offset_window = None
        self.saha_window = None
        self.cflibs_window = None
        self.standard_correction_window = None
        self.sac_check_window = None
        self.sac_window = None
        self.ne_halpha_window = None
        self.statistics_window = None
        self.about_window = None
        self.goto_window = None
        self.shift_capture_window=None
        self._build()
        try:
            self.protocol("WM_DELETE_WINDOW", self.on_close)
        except Exception:
            pass
        self.after(SPLASH_DURATION_MS, self.deiconify)

    def _build(self):
        self._menu(); self._plot(); self._status()

    def _menu(self):
        m=tk.Menu(self)
        f=tk.Menu(m,tearoff=False); f.add_command(label="Open",command=self.open_spectrum); f.add_command(label="Append/import",command=self.append_spectrum); f.add_command(label="Save main",command=self.save_spectrum); f.add_separator(); f.add_command(label="Exit",command=self.on_close); m.add_cascade(label="File",menu=f)
        e=tk.Menu(m,tearoff=False); e.add_command(label="Options",command=self.show_options); m.add_cascade(label="Edit",menu=e)
        u=tk.Menu(m,tearoff=False); u.add_command(label="Instrument response",command=self.show_response_window); u.add_command(label="Apply response now",command=self.apply_response_now); u.add_command(label="Vertical shift",command=lambda:VerticalShiftWindow(self)); u.add_command(label="Smooth main",command=self.smooth_main); u.add_command(label="nm → Å main",command=self.nm_to_a_main); m.add_cascade(label="Utilities",menu=u)
        t=tk.Menu(m,tearoff=False); t.add_command(label="Template Manager",command=self.show_template); t.add_command(label="Line Identification",command=self.show_line_identification); t.add_command(label="Element Locator",command=lambda:ElementLocatorWindow(self)); t.add_command(label="Auto Element Identification",command=lambda:AutoElementIdentificationWindow(self)); m.add_cascade(label="Template",menu=t)
        a=tk.Menu(m,tearoff=False); a.add_command(label="Active Spectra",command=self.show_active_spectra); a.add_command(label="Trace Lines",command=self.show_trace_lines); a.add_command(label="Batch / Statistics",command=lambda:BatchStatisticsWindow(self)); a.add_command(label="Manual Fit",command=self.show_retro_fit_manager); a.add_command(label="Auto Fit",command=self.show_auto_fit_manager); a.add_command(label="Ne from H-alpha",command=self.show_ne_halpha); a.add_command(label="SAC factors",command=self.show_sac); a.add_command(label="Saha-Boltzmann",command=self.show_saha); a.add_command(label="CF-LIBS",command=self.show_cflibs); a.add_command(label="Standard correction / OPC",command=self.show_standard_correction); m.add_cascade(label="Analyse",menu=a)
        h=tk.Menu(m,tearoff=False); h.add_command(label="Manual...",command=self.show_manual); h.add_separator(); h.add_command(label="About pyLIBS...",command=self.show_about); m.add_cascade(label="Help",menu=h)
        self.config(menu=m)

    def _toolbar(self):
        tb=ttk.Frame(self); tb.pack(fill="x", padx=4, pady=3)
        for label,cmd in [("Open",self.open_spectrum),("Append",self.append_spectrum),("Active Spectra",self.show_active_spectra),("Options",self.show_options),("Response",self.show_response_window),("Template",self.show_template),("Identify",self.show_line_identification),("Trace",self.show_trace_lines),("Element",lambda:ElementLocatorWindow(self)),("Auto ID",lambda:AutoElementIdentificationWindow(self)),("Batch",lambda:BatchStatisticsWindow(self)),("Shift",lambda:VerticalShiftWindow(self)),("Fit",self.show_fit),("Ne Hα",self.show_ne_halpha),("SAC",self.show_sac),("Saha",self.show_saha),("CF-LIBS",self.show_cflibs),("STD",self.show_standard_correction)]:
            ttk.Button(tb,text=label,command=cmd).pack(side="left",padx=2)

    def _plot(self):
        self.plot_frame=ttk.Frame(self); self.plot_frame.pack(fill="both", expand=True)
        if Figure is None:
            ttk.Label(self.plot_frame,text="matplotlib not available").pack(pady=30)
            self.ax=self.canvas=None; return
        self.fig=Figure(figsize=(8,5),dpi=100); self.ax=self.fig.add_subplot(111)
        self.canvas=FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        # Navigation state: left drag zoom, right drag pan.
        self._nav_press = None
        self._nav_dragged = False
        self._xscroll_updating = False
        self.canvas.mpl_connect("motion_notify_event", self._mouse)
        self.canvas.mpl_connect("button_press_event", self._click)
        self.canvas.mpl_connect("button_release_event", self._release)
        # Bottom horizontal quick-position bar, like the original viewer.
        self.xscroll_var = tk.DoubleVar(value=0.0)
        self.xscroll = ttk.Scale(self.plot_frame, orient="horizontal", from_=0.0, to=100.0, variable=self.xscroll_var, command=self._xscroll_changed)
        self.xscroll.pack(fill="x", padx=6, pady=(0, 2))
        self.redraw()

    def _status(self):
        self.status_var=tk.StringVar(value=f"Ready - options: {Path(self.options.ini_file).name}"); self.cursor_var=tk.StringVar(value="Wavelength: --  Intensity: --")
        bar=ttk.Frame(self); bar.pack(fill="x",side="bottom")
        ttk.Label(bar,textvariable=self.status_var).pack(side="left",fill="x",expand=True,padx=6)
        ttk.Label(bar,textvariable=self.cursor_var).pack(side="right",padx=6)

    def status(self,msg): self.status_var.set(msg)

    def infer_wavelength_unit(self):
        xs = [x for sp in self.spectra for x in sp.x]
        if xs and max(xs) < 1500:
            return "nm"
        return "angstrom"

    def current_wavelength_unit_label(self):
        return "nm" if getattr(self, "wavelength_unit", "angstrom") == "nm" else "Å"

    def update_axis_labels(self):
        if not getattr(self, "ax", None):
            return
        self.ax.set_xlabel(f"Wavelength ({self.current_wavelength_unit_label()})")
        self.ax.set_ylabel("Intensity (counts)")

    def add_spectrum(self, sp):
        assign_default_spectrum_color(sp, len(self.spectra))
        self.spectra.append(sp)
        self.wavelength_unit = self.infer_wavelength_unit()
        self.redraw(); self.status(f"Added spectrum: {sp.name}")
        if self.active_window and self.active_window.winfo_exists(): self.active_window.refresh()

    def load_configured_response(self, silent=False):
        response_file = str(getattr(self.options, "response_file", "") or "").strip()
        if not response_file:
            self.response = None
            return False
        path = Path(response_file)
        if not path.exists():
            self.response = None
            if not silent:
                _showwarning(self, "Response", f"Response file not found:\n{response_file}")
            return False
        try:
            self.response = ResponseCurve.from_ascii(str(path), self.options.convert_to_angstrom)
            response_window = getattr(self, "response_window", None)
            if response_window and response_window.winfo_exists():
                self.response_window.redraw()
            return True
        except Exception as e:
            self.response = None
            if not silent:
                _showwarning(self, "Response", f"Could not load response file:\n{response_file}\n\n{e}")
            return False

    def load_spectrum_with_corrections(self, filename):
        sp = load_spectrum_for_open(filename, self.options)
        if self.options.apply_response and self.options.apply_before and self.response is not None:
            sp.apply_response(self.response)
        return sp

    def open_spectrum(self):
        fns=filedialog.askopenfilenames(initialdir=remembered_initial_dir(self.options), filetypes=SPECTRUM_FILETYPES)
        if not fns: return
        self.invalidate_cflibs_results()
        remember_working_dir(self.options, fns)
        first_fn=fns[0]
        try:
            sp=self.load_spectrum_with_corrections(first_fn)
            if self.options.auto_shift: sp.x=[x+self.options.auto_shift for x in sp.x]
            assign_default_spectrum_color(sp, 0)
            self.spectra=[sp]
            self.wavelength_unit = self.infer_wavelength_unit()
        except Exception as e:
            _showerror(self, "Open",str(e)); return
        for fn in fns[1:]:
            try:
                self.add_spectrum(self.load_spectrum_with_corrections(fn))
            except Exception as e:
                _showerror(self, "Compare", f"{fn}: {e}")
        self.redraw()
        if len(fns) == 1:
            self.status(f"Spectrum loaded: {first_fn}")
        else:
            self.status(f"Spectrum loaded: {first_fn}; comparisons: {len(fns)-1}")

    def append_spectrum(self):
        fns=filedialog.askopenfilenames(initialdir=remembered_initial_dir(self.options), filetypes=SPECTRUM_FILETYPES)
        remember_working_dir(self.options, fns)
        if not fns:
            return
        self.invalidate_cflibs_results()
        merged = self.spectra[0] if self.spectra else None
        for fn in fns:
            try:
                sp=self.load_spectrum_with_corrections(fn)
                if merged is None:
                    merged = sp
                else:
                    merged = merge_spectra_by_wavelength(merged, sp, name=f"{merged.name} + {sp.name}")
            except Exception as e:
                _showerror(self, "Append",f"{fn}: {e}")
        if merged is not None:
            assign_default_spectrum_color(merged, 0)
            self.spectra = [merged]
            self.wavelength_unit = self.infer_wavelength_unit()
        self.redraw()
        if self.active_window and self.active_window.winfo_exists(): self.active_window.refresh()

    def save_spectrum(self):
        if not self.spectra: return
        fn=filedialog.asksaveasfilename(initialdir=remembered_initial_dir(self.options), defaultextension=".dat")
        if fn:
            remember_working_dir(self.options, fn)
            self.spectra[0].save_ascii(fn)

    def ask_load_response(self):
        fn=filedialog.askopenfilename(initialdir=remembered_initial_dir(self.options), filetypes=[("ASCII","*.txt *.dat *.asc *.csv"),("All","*.*")])
        if fn:
            remember_working_dir(self.options, fn)
            self.load_response_file(fn)

    def load_response_file(self, fn):
        self.options.response_file=fn
        if not self.load_configured_response(silent=False):
            return
        if self.response_window and self.response_window.winfo_exists(): self.response_window.redraw()
        self.status(f"Response loaded: {fn}")

    def apply_response_now(self):
        if self.response is None or not self.response.x: _showinfo(self, "Response","Load the curve first."); return
        for sp in self.spectra: sp.apply_response(self.response)
        self.redraw()

    def smooth_main(self):
        if self.spectra: self.spectra[0].smooth(); self.redraw()

    def nm_to_a_main(self):
        if self.spectra:
            self.spectra[0].x=[x*10 for x in self.spectra[0].x]
            self.wavelength_unit = "angstrom"
            self.redraw()

    def current_xlim(self):
        if self.ax:
            lo,hi=self.ax.get_xlim(); return lo,hi
        return -math.inf, math.inf

    def current_plot_view(self):
        """Return the current visible x/y limits of the main plot.

        Trace Lines must query only the wavelength interval actually displayed
        in the main window, and the search must not alter the user's zoom.
        """
        if self.ax:
            try:
                return tuple(self.ax.get_xlim()), tuple(self.ax.get_ylim())
            except Exception:
                pass
        return (-math.inf, math.inf), (0.0, 1.0)

    def restore_plot_view(self, xlim=None, ylim=None):
        """Restore a saved plot view after redrawing overlays."""
        if not self.ax:
            return
        try:
            if xlim is not None:
                self.ax.set_xlim(xlim)
            if ylim is not None:
                self.ax.set_ylim(ylim)
            self.canvas.draw_idle()
        except Exception:
            pass

    def clear_element_markers(self):
        self.element_markers=[]; self.redraw()

    def clear_plot_annotations(self):
        self.element_markers = []
        self.trace_markers = []
        self.fit_overlay = None

    def clear_fit_artists(self):
        self.fit_overlay = None
        ax = getattr(self, "ax", None)
        if not ax:
            return False
        removed = False
        for artist in list(getattr(ax, "lines", [])):
            try:
                if artist.get_label() == "fit":
                    artist.remove()
                    removed = True
            except Exception:
                pass
        if removed:
            try:
                legend = ax.get_legend()
                if legend is not None:
                    legend.remove()
                handles, labels = ax.get_legend_handles_labels()
                pairs = [(h, l) for h, l in zip(handles, labels) if l and not l.startswith("_") and l != "fit"]
                if pairs:
                    ax.legend([p[0] for p in pairs], [p[1] for p in pairs], loc="best")
            except Exception:
                pass
        return removed

    def _active_spectrum_y_at(self, wavelength):
        """Intensity of the selected active spectrum at the nearest wavelength.

        If the Active Spectra window is open, use its selected row; otherwise
        fall back to the main/first visible spectrum.  This keeps Trace and
        manual markers anchored to the spectrum the user is working on.
        """
        try:
            sp = None
            aw = getattr(self, "active_window", None)
            if aw is not None and aw.winfo_exists():
                idx_sel = getattr(aw, "selected_index", 0)
                if 0 <= idx_sel < len(self.spectra):
                    cand = self.spectra[idx_sel]
                    if getattr(cand, "visible", True) and getattr(cand, "x", None):
                        sp = cand
            if sp is None:
                candidates = [sp0 for sp0 in self.spectra if getattr(sp0, "visible", True) and getattr(sp0, "x", None)]
                if not candidates:
                    return 0.0
                sp = candidates[0]
            idx = min(range(len(sp.x)), key=lambda i: abs(sp.x[i] - wavelength))
            return float(sp.y[idx]) if idx < len(sp.y) else 0.0
        except Exception:
            return 0.0

    def redraw(self, preserve_view=False):
        if not getattr(self,"ax",None): return
        old_xlim = old_ylim = None
        if preserve_view:
            try:
                old_xlim = self.ax.get_xlim(); old_ylim = self.ax.get_ylim()
            except Exception:
                old_xlim = old_ylim = None
        self.ax.clear(); self.update_axis_labels()
        self.ax.set_facecolor(_background_color(getattr(self, "plot_background", "#ffffff"), "#ffffff"))
        try:
            self.ax.set_xscale("log" if getattr(self, "view_log_x", False) else "linear", nonpositive="clip")
        except TypeError:
            self.ax.set_xscale("log" if getattr(self, "view_log_x", False) else "linear")
        try:
            self.ax.set_yscale("log" if getattr(self, "view_log_y", False) else "linear", nonpositive="clip")
        except TypeError:
            self.ax.set_yscale("log" if getattr(self, "view_log_y", False) else "linear")
        for spine in self.ax.spines.values():
            spine.set_linewidth(1.2)
        self.ax.tick_params(direction="in", length=5, width=1.0)
        grid_x = _view_bool(getattr(self, "view_grid_x", True), True)
        grid_y = _view_bool(getattr(self, "view_grid_y", True), True)
        if grid_x:
            self.ax.xaxis.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.5)
        else:
            self.ax.xaxis.grid(False)
        if grid_y:
            self.ax.yaxis.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.5)
        else:
            self.ax.yaxis.grid(False)
        label_bbox = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1)
        for sp in self.spectra:
            if sp.visible and sp.x:
                kwargs = {"color": sp.color} if getattr(sp, "color", None) else {}
                self.ax.plot(sp.x, sp.y, linewidth=0.8, label=sp.name, **kwargs)
        ymin,ymax=self.ax.get_ylim()
        h=ymax-ymin if ymax>ymin else 1
        for line in (self.template_lines if self.spectra else []):
            # Convention: unassigned marked peaks are blue; assigned
            # peaks with complete transition data are yellow; assigned peaks
            # without Aki/levels/statistical weights are light blue.
            has_transition_data = bool(line.aki or line.ek or line.gk or line.gi)
            if safe_float(getattr(line, "aki", 0.0), 0.0) < 0.0:
                color = "lightskyblue"
            elif line.specie:
                color = "gold" if has_transition_data else "lightskyblue"
            else:
                color = "blue"
            # Manual/identified marker: from baseline y=0 to the
            # intensity of the active spectrum at the marked wavelength.
            ytop = self._active_spectrum_y_at(line.wavelen)
            self.ax.vlines(line.wavelen, 0.0, ytop, linestyles="solid", linewidth=0.9, colors=color)
            label = f"{line.wavelen:.2f}" if not line.specie else f"{line.specie} {_roman_ion(line.ion)} {line.asswavelen or line.wavelen:.2f}"
            self.ax.text(
                line.wavelen, ytop, label,
                rotation=0, fontsize=7, va=("bottom" if ytop >= 0 else "top"), ha="center",
                color="black", bbox=label_bbox, clip_on=True,
            )
        # Trace Lines overlay: green segments with readable species labels.
        # Like the manual/identified markers, traced lines start at y=0 and
        # reach the intensity of the selected active spectrum at that wavelength.
        trace_markers = getattr(self, "trace_markers", [])
        if trace_markers:
            for l in trace_markers:
                ytop = self._active_spectrum_y_at(l.wavelen)
                label = f"{l.specie} {_roman_ion(l.ion)}".strip()
                self.ax.vlines(l.wavelen, 0.0, ytop, colors="green", linewidth=2.0)
                self.ax.text(
                    l.wavelen, ytop, label,
                    rotation=0, fontsize=10, fontweight="bold",
                    va=("bottom" if ytop >= 0 else "top"), ha="center",
                    color="black",
                    bbox=label_bbox,
                    clip_on=True,
                )
        if self.element_markers:
            maxint=max([l.inte for l in self.element_markers] or [1]) or 1
            for l in self.element_markers:
                y=ymin+(l.inte/maxint)*0.8*h
                self.ax.vlines(l.wavelen,ymin,y,colors="green",linewidth=1.0)
                self.ax.text(
                    l.wavelen, y, f"{l.specie} {'I' if l.ion==1 else 'II'}",
                    rotation=0, fontsize=7, va="bottom", ha="center",
                    color="black", bbox=label_bbox, clip_on=True,
                )
        if self.fit_overlay:
            fx, fy = self.fit_overlay
            self.ax.plot(fx, fy, linewidth=1.0, label="fit")
        if any(sp.visible for sp in self.spectra) or self.fit_overlay: self.ax.legend(loc="best")
        if preserve_view and old_xlim and old_ylim:
            try:
                self.ax.set_xlim(old_xlim); self.ax.set_ylim(old_ylim)
            except Exception:
                pass
        self.canvas.draw_idle()
        try:
            self._update_xscroll()
        except Exception:
            pass

    def show_active_spectra(self):
        self.active_window = show_existing_or_create(self, "active_window", lambda: ActiveSpectraWindow(self), refresh=lambda w: w.refresh(), parent=self)

    def show_response_window(self):
        self.response_window = show_existing_or_create(self, "response_window", lambda: ResponseWindow(self), refresh=lambda w: w.redraw(), parent=self)

    def show_template(self):
        return self.show_template_window()

    def show_line_identification(self):
        self.line_window = show_existing_or_create(self, "line_window", lambda: LineIdentificationWindow(self), parent=self)

    def show_trace_lines(self):
        self.trace_window = _show_persistent_window(
            self,
            "trace_window",
            lambda: TraceLinesWindow(self),
            "Trace",
            refresh=lambda w: w.refresh(),
            parent=self,
            center_on_create=True,
        )

    def copy_atomic_line_to_template_line(self, template_line, atomic):
        """Copy database transition fields into a template row."""
        template_line.specie = atomic.specie
        template_line.ion = atomic.ion
        template_line.asswavelen = atomic.wavelen
        template_line.ei = atomic.ei
        template_line.ek = atomic.ek
        template_line.acc = atomic.acc
        template_line.aki = atomic.aki
        template_line.gk = atomic.gk
        template_line.gi = atomic.gi

    def assign_traced_lines(self):
        """Assign all currently traced database lines to already marked template
        peaks when |marked wavelength - traced wavelength| <= Options.Range.
        Applies to all traced species, not only the last trace query.
        """
        trace_markers = getattr(self, "trace_markers", [])
        if not self.template_lines or not trace_markers:
            return 0
        rg = max(0.0, safe_float(getattr(self.options, "search_range", 0.2), 0.2))
        assigned = 0
        for t in self.template_lines:
            candidates = [l for l in trace_markers if abs(l.wavelen - t.wavelen) <= rg]
            if not candidates:
                continue
            atomic = min(candidates, key=lambda l: abs(l.wavelen - t.wavelen))
            try:
                atomic = self.libs_db.enrich_line_from_element_table(atomic, tolerance=max(0.02, rg))
            except Exception:
                pass
            self.copy_atomic_line_to_template_line(t, atomic)
            assigned += 1
        self.notify_template_changed(redraw=False)
        self.redraw(preserve_view=True)
        self.status(f"Trace Assign: {assigned} template lines assigned")
        return assigned

    def assign_atomic_line_to_nearest_template(self, atomic, redraw=True):
        # When possible, enrich the fast Datalibs/Daticerti match with the
        # complete spectroscopic parameters stored in the element table.
        try:
            atomic = self.libs_db.enrich_line_from_element_table(atomic, tolerance=max(0.02, self.options.search_range))
        except Exception:
            pass
        if not self.template_lines:
            base_wave = getattr(self, "current_identification_wavelength", atomic.wavelen)
            self.template_lines.append(TemplateLine(wavelen=base_wave))
        target_wave = getattr(self, "current_identification_wavelength", atomic.wavelen)
        idx = min(range(len(self.template_lines)), key=lambda i: abs(self.template_lines[i].wavelen - target_wave))
        t = self.template_lines[idx]
        self.copy_atomic_line_to_template_line(t, atomic)
        self.notify_template_changed(redraw=False)
        if redraw:
            self.redraw(preserve_view=True)
        self.status(f"Assigned {atomic.specie} {_roman_ion(atomic.ion)} at {atomic.wavelen:.4f} Å")

    def enrich_identified_template_line(self, t, tolerance=None):
        """Complete an already identified template row with spectroscopic
        parameters from the element-specific table in LIBS.db.

        The fast Datalibs table only contains wavelength/species/intensity/ion;
        the element table contains Ek, gi, gk, Aki and acc.  This method is used
        after a Voigt fit so the template row keeps both the measured fit
        parameters and the transition parameters, when available.
        """
        if t is None or not getattr(t, "specie", ""):
            return False
        try:
            self.libs_db.filename = self.options.libs_db_file
            wave = float(getattr(t, "asswavelen", 0.0) or getattr(t, "fitwavelen", 0.0) or getattr(t, "wavelen", 0.0))
            ion = int(getattr(t, "ion", 0) or 0)
            if not wave:
                return False
            atomic = AtomicLine(wavelen=wave, specie=str(t.specie).strip(), ion=ion)
            tol = tolerance if tolerance is not None else max(0.02, safe_float(getattr(self.options, "search_range", 0.2), 0.2))
            enriched = self.libs_db.enrich_line_from_element_table(atomic, tolerance=tol)
            if not enriched:
                return False
            self.copy_atomic_line_to_template_line(t, enriched)
            return True
        except Exception:
            return False

    def zoom_around(self,wave):
        if self.ax:
            width=max(5,self.options.search_range*5)
            self.clear_fit_artists()
            self.ax.set_xlim(wave-width,wave+width); self.canvas.draw_idle()

    def show_fit(self): MultiGaussianFitWindow(self)
    def show_ne_halpha(self): self.ne_halpha_window = _show_persistent_window(self, "ne_halpha_window", lambda: NeHalphaWindow(self), "HAlpha", parent=self, center_on_create=True)
    def show_sac(self): self.sac_window = show_existing_or_create(self, "sac_window", lambda: SACWindow(self), parent=self)
    def show_saha(self): self.saha_window = _show_persistent_window(self, "saha_window", lambda: SahaBoltzmannWindow(self), "SahaBoltzmann", parent=self, center_on_create=True)
    def show_cflibs(self): self.cflibs_window = _show_persistent_window(self, "cflibs_window", lambda: CFLibsWindow(self), "CFLIBS", parent=self, center_on_create=True)
    def show_standard_correction(self): self.standard_correction_window = show_existing_or_create(self, "standard_correction_window", lambda: StandardCorrectionWindow(self), parent=self)
    def show_sac_check(self):
        self.sac_check_window = _show_persistent_window(
            self,
            "sac_check_window",
            lambda: SelfAbsorptionCheckWindow(self),
            "ShowSA",
            refresh=lambda w: w.refresh(show_message=False),
            parent=self,
            center_on_create=True,
        )
        try:
            self.sac_check_window.refresh(show_message=False)
        except Exception:
            pass
        return self.sac_check_window

    def _mouse(self,event):
        if event.inaxes is not getattr(self, "ax", None) or event.xdata is None or event.ydata is None:
            self.cursor_var.set("Wavelength: --  Intensity: --")
        else:
            self.cursor_var.set(f"Wavelength: {event.xdata:.3f}  Intensity: {event.ydata:.3g}")

    def _click(self,event):
        if event.xdata is not None and event.button==1 and event.key=="control":
            self.show_line_identification()
            self.line_window.wave_var.set(f"{event.xdata:.4f}")
            if self.line_window.atomic_lines: self.line_window.search()



# -----------------------------------------------------------------------
# pyLIBS v8.10 Retro menus and windows
# -----------------------------------------------------------------------

def get_menu_icon(self, filename, size=16):
    return get_cached_menu_icon(self, filename, size)

def _menu_shortcut_handler(self, command):
    def handler(event=None):
        try:
            focus = self.focus_get()
            if focus is not None:
                widget_class = focus.winfo_class()
                if widget_class in {"Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "Combobox", "TCombobox"}:
                    return None
        except Exception:
            pass
        command()
        return "break"
    return handler

def _bind_menu_shortcuts(self, shortcut_items):
    for item in shortcut_items:
        sequence = item.get("event")
        command = item.get("command")
        if not sequence or command is None:
            continue
        try:
            self.bind(sequence, _menu_shortcut_handler(self, command))
        except Exception:
            pass

def _add_menu_command(self, menu, shortcut_items, label, command, accelerator="", event="", icon=""):
    image = get_menu_icon(self, icon) if icon else None
    kwargs = {"label": label, "command": command}
    if accelerator:
        kwargs["accelerator"] = accelerator
    if image is not None:
        kwargs["image"] = image
        kwargs["compound"] = "left"
    menu.add_command(**kwargs)
    if accelerator and event:
        shortcut_items.append({"label": label, "accelerator": accelerator, "event": event, "command": command})

def _add_menu_checkbutton(self, menu, shortcut_items, label, command, variable=None, accelerator="", event="", icon=""):
    image = get_menu_icon(self, icon) if icon else None
    kwargs = {"label": label, "command": command}
    if variable is not None:
        kwargs["variable"] = variable
    if accelerator:
        kwargs["accelerator"] = accelerator
    if image is not None:
        kwargs["image"] = image
        kwargs["compound"] = "left"
    menu.add_checkbutton(**kwargs)
    if accelerator and event:
        shortcut_items.append({"label": label, "accelerator": accelerator, "event": event, "command": command})

def build_retro_menu(self):
    """Build the menu tree."""
    menu = tk.Menu(self)
    self.config(menu=menu)
    shortcut_items = []
    self.menu_icons = {}
    self.menu_icon_files = {}
    self.menu_missing_icons = []

    file_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="File", menu=file_menu)
    _add_menu_command(self, file_menu, shortcut_items, "Open...", self.ask_open_spectrum, "Ctrl+O", "<Control-o>", "open.png")
    _add_menu_command(self, file_menu, shortcut_items, "Compare...", self.compare_spectrum, "Ctrl+M", "<Control-m>", "compare.png")
    _add_menu_command(self, file_menu, shortcut_items, "Append...", self.ask_import_multiple, "Ctrl+A", "<Control-a>", "append.png")
    _add_menu_command(self, file_menu, shortcut_items, "Save", self.ask_save_spectrum, "Ctrl+S", "<Control-s>", "save.png")
    _add_menu_command(self, file_menu, shortcut_items, "Save with Labels", self.save_with_labels, "Ctrl+L", "<Control-l>", "save.png")
    file_menu.add_separator()
    _add_menu_command(self, file_menu, shortcut_items, "Print", self.print_plot, "Ctrl+P", "<Control-p>", "print.png")
    file_menu.add_separator()
    _add_menu_command(self, file_menu, shortcut_items, "Exit", self.on_close, "Ctrl+X", "<Control-x>", "")

    edit_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Edit", menu=edit_menu)
    _add_menu_command(self, edit_menu, shortcut_items, "Copy", self.copy_plot, "Ctrl+C", "<Control-c>", "")
    edit_menu.add_separator()
    _add_menu_command(self, edit_menu, shortcut_items, "Swap Spectra", self.swap_spectra, "Ctrl+W", "<Control-w>", "compare.png")
    _add_menu_command(self, edit_menu, shortcut_items, "Show Active Spectra", self.show_active_spectra, "Ctrl+Shift+A", "<Control-Shift-A>", "Active_spectra.png")
    _add_menu_command(self, edit_menu, shortcut_items, "Clear Graph", self.clear_all_spectra, "Ctrl+Del", "<Control-Delete>", "clear.png")
    edit_menu.add_separator()
    _add_menu_command(self, edit_menu, shortcut_items, "Options", self.show_options, "Ctrl+Alt+O", "<Control-Alt-o>", "options.png")

    view_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="View", menu=view_menu)
    _add_menu_command(self, view_menu, shortcut_items, "Change Background", self.change_background, "Ctrl+B", "<Control-b>", "background.png")
    view_menu.add_separator()
    self.view_grid_x_var = tk.BooleanVar(value=_view_bool(getattr(self, "view_grid_x", True), True))
    self.view_grid_y_var = tk.BooleanVar(value=_view_bool(getattr(self, "view_grid_y", True), True))
    self.view_log_x_var = tk.BooleanVar(value=getattr(self, "view_log_x", False))
    self.view_log_y_var = tk.BooleanVar(value=getattr(self, "view_log_y", False))
    _add_menu_checkbutton(self, view_menu, shortcut_items, "GridX", lambda: self.toggle_grid(axis="x"), self.view_grid_x_var, "Ctrl+Alt+X", "<Control-Alt-x>", "grid.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "GridY", lambda: self.toggle_grid(axis="y"), self.view_grid_y_var, "Ctrl+Alt+Y", "<Control-Alt-y>", "grid_xy.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "LogX", lambda: self.toggle_log(axis="x"), self.view_log_x_var, "Ctrl+Alt+G", "<Control-Alt-g>", "log_x.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "LogY", lambda: self.toggle_log(axis="y"), self.view_log_y_var, "Ctrl+Alt+L", "<Control-Alt-l>", "log_y.png")
    view_menu.add_separator()
    _add_menu_command(self, view_menu, shortcut_items, "Auto X", self.full_x, "", "", "zoom_x_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Auto Y", self.full_y, "", "", "zoom_y_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Expand X 50%", self.expand_x_50, "F2", "<F2>", "zoom_x_in.png")
    _add_menu_command(self, view_menu, shortcut_items, "Full Y Scale", self.full_y, "F3", "<F3>", "zoom_y_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Show All", self.full_scale, "F4", "<F4>", "full_view.png")
    view_menu.add_separator()
    _add_menu_command(self, view_menu, shortcut_items, "Save Window Position", self.save_window_positions, "", "", "")
    _add_menu_command(self, view_menu, shortcut_items, "Load Window Position", self.load_window_positions, "", "", "")

    util_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Utilities", menu=util_menu)
    _add_menu_command(self, util_menu, shortcut_items, "Shift", self.show_spectrum_shift, "Ctrl+F1", "<Control-F1>", "")
    _add_menu_command(self, util_menu, shortcut_items, "Offset", self.show_spectrum_offset, "Ctrl+F2", "<Control-F2>", "")
    _add_menu_command(self, util_menu, shortcut_items, "Smooth", self.smooth_main_spectrum, "Ctrl+F3", "<Control-F3>", "")
    _add_menu_command(self, util_menu, shortcut_items, "nm -> A", self.convert_nm_to_angstrom, "Ctrl+F4", "<Control-F4>", "")
    util_menu.add_separator()
    _add_menu_command(self, util_menu, shortcut_items, "Batch Ops.", self.show_batch_statistics, "", "", "")
    util_menu.add_separator()
    _add_menu_command(self, util_menu, shortcut_items, "Load Template", self.load_template_from_menu, "Ctrl+F5", "<Control-F5>", "load_template.png")
    _add_menu_command(self, util_menu, shortcut_items, "Show Template", self.show_template_manager, "Ctrl+F6", "<Control-F6>", "show_Template.png")
    _add_menu_command(self, util_menu, shortcut_items, "Info Template", self.template_info_from_menu, "Ctrl+F7", "<Control-F7>", "")
    _add_menu_command(self, util_menu, shortcut_items, "Close Template", self.close_template_from_menu)
    util_menu.add_separator()
    _add_menu_command(self, util_menu, shortcut_items, "Statistics", self.show_statistics, "Shift+Ctrl+F4", "<Control-Shift-F4>", "calculator.png")
    util_menu.add_separator()
    _add_menu_command(self, util_menu, shortcut_items, "GoTo...", self.show_goto_dialog, "Ctrl+F9", "<Control-F9>", "goto.png")

    analysis_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Analyse", menu=analysis_menu)
    _add_menu_command(self, analysis_menu, shortcut_items, "Find Peaks", self.find_peaks_basic, "", "", "find_peaks.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "Trace Lines", self.show_trace_lines, "", "", "trace.png")
    analysis_menu.add_separator()
    _add_menu_command(self, analysis_menu, shortcut_items, "Calculate Ne from Ha", self.show_ne_halpha, "", "", "H_alpha.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "Manual Fit", self.show_retro_fit_manager, "", "", "fit_manual.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "Auto Fit", self.show_auto_fit_manager, "", "", "fit_auto.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "Saha Boltzmann plot", self.show_saha_boltzmann, "", "", "calculator.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "CF LIBS", self.show_cf_libs, "", "", "database.png")
    analysis_menu.add_separator()
    _add_menu_command(self, analysis_menu, shortcut_items, "SAC", self.show_sac_window, "", "", "calibration.png")
    _add_menu_command(self, analysis_menu, shortcut_items, "Standard Correction", self.show_standard_correction, "", "", "database.png")

    help_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Help", menu=help_menu)
    _add_menu_command(self, help_menu, shortcut_items, "Manual...", self.show_manual, "", "", "help.png")
    help_menu.add_separator()
    _add_menu_command(self, help_menu, shortcut_items, "About pyLIBS...", self.show_about, "Ctrl+T", "<Control-t>", "about.png")
    self.menu_shortcuts = shortcut_items
    self.menu_shortcut_conflicts = [
        "Ctrl+A: kept File > Append; Edit > Show Active Spectra uses Ctrl+Shift+A.",
        "Ctrl+O: kept File > Open; Edit > Options uses Ctrl+Alt+O.",
    ]
    _bind_menu_shortcuts(self, shortcut_items)

def build_retro_toolbar(self):
    """Build original-like toolbar order without exposing Single Fit."""
    if hasattr(self, "retro_toolbar"):
        return
    from pylibs.gui.helpers import ToolbarTooltip
    from pylibs.gui.icons import load_toolbar_icon

    self.retro_toolbar = ttk.Frame(self)
    try:
        self.retro_toolbar.pack(side="top", fill="x", before=self.children.get("!frame"))
    except Exception:
        self.retro_toolbar.pack(side="top", fill="x")

    buttons = [
        ("Open", self.ask_open_spectrum),
        ("Compare", self.compare_spectrum),
        ("Append", self.ask_import_multiple),
        ("Clear", self.clear_all_spectra),
        ("Active Spectra", self.show_active_spectra),
        ("Save", self.ask_save_spectrum),
        ("Print", self.print_plot),
        ("Full Y", self.full_y),
        ("Full X", self.full_x),
        ("Full Scale", self.full_scale),
        ("Load Template", self.load_template_from_menu),
        ("Show Template", self.show_template_manager),
        ("Trace", self.show_trace_lines),
        ("Ne from H", self.show_ne_halpha),
        ("Autofit", self.show_auto_fit_manager),
        ("Manual Fit", self.show_retro_fit_manager),
        ("Saha Boltzmann", self.show_saha_boltzmann),
        ("CF LIBS", self.show_cf_libs),
    ]
    icon_names = {
        "Open": "open.png",
        "Compare": "compare.png",
        "Append": "append.png",
        "Clear": "clear.png",
        "Active Spectra": "fit.png",
        "Save": "save.png",
        "Print": "print.png",
        "Full Y": "full_y.png",
        "Full X": "full_x.png",
        "Full Scale": "full_view.png",
        "Load Template": "load_template.png",
        "Show Template": "show_template.png",
        "Trace": "trace.png",
        "Ne from H": "H_alpha.png",
        "Autofit": "fit_auto.png",
        "Manual Fit": "fit_manual.png",
        "Saha Boltzmann": "calculator.png",
        "CF LIBS": "database.png",
    }
    icon_fallbacks = {
        "Full Y": "zoom_y_out.png",
        "Full X": "zoom_x_out.png",
        "Autofit": "fit.png",
        "Manual Fit": "fit.png",
    }
    tooltip_text = {
        "Trace": "Trace Lines",
        "Full Scale": "Full View",
    }
    self.toolbar_icons = {}
    self.toolbar_icon_files = {}
    self.toolbar_tooltips = []
    self.toolbar_missing_icons = []
    for label, cmd in buttons:
        icon_name = icon_names.get(label)
        image, icon_name, icon_path = load_toolbar_icon(self, label, icon_name, icon_fallbacks.get(label))
        if image is not None:
            button = ttk.Button(self.retro_toolbar, image=image, command=cmd)
            button.pack(side="left", padx=1, pady=1)
            self.toolbar_tooltips.append(ToolbarTooltip(button, tooltip_text.get(label, label)))
        else:
            self.toolbar_missing_icons.append(label)
            ttk.Button(self.retro_toolbar, text=label, command=cmd).pack(side="left", padx=1, pady=1)

def install_retro_ui(self):
    self.build_retro_menu()
    self.build_retro_toolbar()
    try:
        self.title("pyLIBS")
    except Exception:
        pass
    try:
        self.status(_main_window_status_text())
    except Exception:
        pass

def show_template_window(self):
    win = _template_window_reference(self)
    if win is None:
        win = RetroTemplateManager(self)
        self.template_window = win
        _bind_template_window_close(self, win)
        geometry = _saved_window_geometry(self, "Template")
        if geometry:
            _set_window_geometry(win, geometry, self)
        else:
            center_window(win, self)
    else:
        self.template_window = win
        _bind_template_window_close(self, win)
        try:
            win.refresh()
        except Exception:
            pass
    _raise_template_window(self)
    return self.template_window

def show_template_manager(self):
    return self.show_template_window()

def close_template_window(self):
    win = getattr(self, "template_window", None)
    try:
        if win is not None and win.winfo_exists():
            win.destroy()
    except Exception:
        pass
    if getattr(self, "template_window", None) is win:
        self.template_window = None

def _existing_template_windows(self):
    windows = []
    try:
        for child in self.winfo_children():
            try:
                if child.winfo_exists() and isinstance(child, (RetroTemplateManager, TemplateManager)):
                    windows.append(child)
            except Exception:
                pass
    except Exception:
        pass
    return windows

def _template_window_reference(self):
    current = getattr(self, "template_window", None)
    valid_current = None
    try:
        if current is not None and current.winfo_exists() and isinstance(current, (RetroTemplateManager, TemplateManager)):
            valid_current = current
    except Exception:
        valid_current = None
    windows = _existing_template_windows(self)
    if valid_current is not None and valid_current in windows:
        chosen = valid_current
    elif windows:
        chosen = _preferred_template_window(windows)
    else:
        self.template_window = None
        return None
    for other in windows:
        if other is chosen:
            continue
        try:
            other.destroy()
        except Exception:
            pass
    self.template_window = chosen
    _bind_template_window_close(self, chosen)
    return chosen

def _preferred_template_window(windows):
    for win in windows:
        try:
            if str(win.state()) in {"iconic", "withdrawn"}:
                return win
        except Exception:
            pass
    return windows[0] if windows else None

def _bind_template_window_close(self, win):
    try:
        win.protocol("WM_DELETE_WINDOW", self.close_template_window)
    except Exception:
        pass

def _raise_template_window(self):
    win = getattr(self, "template_window", None)
    try:
        if win is None or not win.winfo_exists():
            self.template_window = None
            return False
    except Exception:
        self.template_window = None
        return False
    try:
        state = str(win.state())
    except Exception:
        state = ""
    try:
        win.deiconify()
    except Exception:
        pass
    try:
        win.state("normal")
    except Exception:
        pass
    try:
        win.update_idletasks()
    except Exception:
        pass
    if state in {"iconic", "withdrawn"}:
        try:
            win.withdraw()
            win.update_idletasks()
            win.deiconify()
            win.state("normal")
            win.update_idletasks()
        except Exception:
            pass
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass
    try:
        win.lift()
    except Exception:
        pass
    try:
        win.focus_force()
    except Exception:
        try:
            win.focus_set()
        except Exception:
            pass
    try:
        win.after(250, lambda w=win: _clear_template_topmost(w))
    except Exception:
        pass
    return True

def _clear_template_topmost(win):
    try:
        if win is not None and win.winfo_exists():
            win.attributes("-topmost", False)
    except Exception:
        pass

def show_active_spectra(self):
    if self.active_window is None or not self.active_window.winfo_exists():
        self.active_window = RetroActiveSpectraWindow(self)
        center_window(self.active_window, self)
        bring_window_to_front(self.active_window, self)
    else:
        self.active_window.refresh()
        bring_window_to_front(self.active_window, self)
    return self.active_window

def show_retro_fit_manager(self):
    return self._show_fit_manager("manual_fit_window", automatic=False, single=False)

def show_single_fit_manager(self):
    return self._show_fit_manager("single_fit_window", automatic=False, single=True)

def show_auto_fit_manager(self):
    return self._show_fit_manager("auto_fit_window", automatic=True, single=False)

def bring_window_to_front(win, parent=None):
    try:
        if win is None or not win.winfo_exists():
            return False
    except Exception:
        return False
    try:
        if str(win.state()) == "iconic":
            win.deiconify()
    except Exception:
        try:
            win.deiconify()
        except Exception:
            pass
    try:
        if parent is not None and getattr(parent, "winfo_exists", lambda: False)():
            win.lift(parent)
        else:
            win.lift()
    except Exception:
        pass
    try:
        win.focus_force()
    except Exception:
        try:
            win.focus_set()
        except Exception:
            pass
    return True

def _show_fit_manager(self, ref_name, automatic=False, single=False):
    key_map = {"manual_fit_window": "ManualFit", "auto_fit_window": "AutoFit"}
    key = key_map.get(ref_name)
    win = getattr(self, ref_name, None)
    try:
        exists = win is not None and win.winfo_exists()
    except Exception:
        exists = False
    if exists:
        try:
            win.refresh_content()
        except Exception:
            pass
        bring_window_to_front(win, self)
        return win
    try:
        setattr(self, ref_name, None)
    except Exception:
        pass
    win = RetroFitManagerWindow(self, automatic=automatic, single=single)
    setattr(self, ref_name, win)
    if key:
        geometry = _saved_window_geometry(self, key)
        if geometry:
            _set_window_geometry(win, geometry, self)
    bring_window_to_front(win, self)
    return win

def swap_spectra(self):
    count = len(getattr(self, "spectra", []))
    if count < 2:
        self.status("Swap Spectra: load at least two spectra.")
        _showinfo(self, "Swap Spectra", "Load at least two spectra before swapping.")
        return
    if count == 2:
        first, second = 0, 1
    else:
        names = "\n".join(f"{i + 1}: {sp.name}" for i, sp in enumerate(self.spectra))
        first_num = simpledialog.askinteger(
            "Swap Spectra",
            f"Select first spectrum number:\n\n{names}",
            parent=self,
            minvalue=1,
            maxvalue=count,
        )
        if first_num is None:
            return
        second_num = simpledialog.askinteger(
            "Swap Spectra",
            f"Select second spectrum number:\n\n{names}",
            parent=self,
            minvalue=1,
            maxvalue=count,
        )
        if second_num is None:
            return
        if first_num == second_num:
            self.status("Swap Spectra: choose two different spectra.")
            _showinfo(self, "Swap Spectra", "Choose two different spectra.")
            return
        first, second = first_num - 1, second_num - 1
    self.spectra[first], self.spectra[second] = self.spectra[second], self.spectra[first]
    self.spectra[first].color, self.spectra[second].color = self.spectra[second].color, self.spectra[first].color
    self.redraw()
    if self.active_window and self.active_window.winfo_exists():
        self.active_window.refresh()
    self.status(f"Swap Spectra: swapped {first + 1} and {second + 1}.")

def compare_spectrum(self):
    files = filedialog.askopenfilenames(
        title="Compare Spectra",
        initialdir=remembered_initial_dir(self.options),
        filetypes=SPECTRUM_FILETYPES
    )
    remember_working_dir(self.options, files)
    for fn in files:
        try:
            self.add_spectrum(self.load_spectrum_with_corrections(fn))
        except Exception as e:
            _showerror(self, "Compare", f"{fn}: {e}")
    self.redraw()

def clear_all_spectra(self):
    if _askyesno(self, "Clear", "Clear all spectra?"):
        self.spectra.clear()
        self.clear_plot_annotations()
        self.clear_template_data()
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.refresh()
        self.status("Clear Graph: all spectra cleared.")

def save_with_labels(self):
    if not getattr(self, "spectra", None):
        _showinfo(self, "Save with Labels", "Load a spectrum before exporting.")
        return
    sp = self.spectra[0]
    if not getattr(sp, "x", None) or not getattr(sp, "y", None):
        _showinfo(self, "Save with Labels", "The main spectrum has no data to export.")
        return
    fn = filedialog.asksaveasfilename(
        title="Save Spectrum with Labels",
        initialdir=remembered_initial_dir(self.options),
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    if not fn:
        return
    remember_working_dir(self.options, fn)
    try:
        labels_by_index = defaultdict(list)
        xs = list(sp.x)
        sorted_x = all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))

        def nearest_index(wavelength):
            if not xs:
                return None
            if sorted_x:
                pos = bisect_right(xs, wavelength)
                if pos <= 0:
                    return 0
                if pos >= len(xs):
                    return len(xs) - 1
                before = pos - 1
                return before if abs(xs[before] - wavelength) <= abs(xs[pos] - wavelength) else pos
            return min(range(len(xs)), key=lambda i: abs(xs[i] - wavelength))

        for line in getattr(self, "template_lines", []) or []:
            specie = str(getattr(line, "specie", "") or "").strip()
            if not specie:
                continue
            ion = safe_int(getattr(line, "ion", 0), 0)
            label = specie if ion <= 0 else f"{specie} {_roman_ion(ion)}"
            wavelength = safe_float(getattr(line, "wavelen", 0.0), 0.0)
            idx = nearest_index(wavelength)
            if idx is not None and label not in labels_by_index[idx]:
                labels_by_index[idx].append(label)

        with open(fn, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["wavelength", "intensity", "label"])
            for idx, (x, y) in enumerate(zip(sp.x, sp.y)):
                writer.writerow([x, y, "; ".join(labels_by_index.get(idx, []))])
        self.status(f"Saved spectrum with labels: {fn}")
        _showinfo(self, "Save with Labels", f"Spectrum exported to:\n{fn}")
    except Exception as e:
        _showerror(self, "Save with Labels", str(e))

def print_plot(self):
    fn = filedialog.asksaveasfilename(
        title="Print / Export Plot",
        initialdir=remembered_initial_dir(self.options),
        defaultextension=".png",
        filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("All", "*.*")]
    )
    if not fn:
        return
    remember_working_dir(self.options, fn)
    try:
        self.fig.savefig(fn)
        self.status(f"Plot exported: {fn}")
    except Exception as e:
        _showerror(self, "Print", str(e))

def copy_plot(self):
    _showinfo(self, "Copy", "Clipboard copy is not available in this prototype. Use File > Print to export the plot.")

def change_background(self):
    try:
        initial = _background_color(getattr(self, "plot_background", "#ffffff"), "#ffffff")
        _rgb, color = colorchooser.askcolor(color=initial, title="Change spectrum background")
    except Exception:
        color = None
    if color and hasattr(self, "ax"):
        self.plot_background = _background_color(color, "#ffffff")
        self.options.background_color = self.plot_background
        self.redraw(preserve_view=True)
        self.status(f"Spectrum background: {color}")

def toggle_grid(self, axis="both"):
    def _update_one(attr, var_name, default=True):
        current = _view_bool(getattr(self, attr, default), default)
        var = getattr(self, var_name, None)
        if var is None:
            new_value = not current
        else:
            try:
                var_value = _view_bool(var.get(), default)
            except Exception:
                var_value = current
            # From the View menu, Tk has already changed the BooleanVar.
            # From the keyboard shortcut, it has not: in that case toggle it here.
            new_value = (not current) if var_value == current else var_value
            try:
                var.set(new_value)
            except Exception:
                pass
        setattr(self, attr, new_value)
        return new_value

    if axis in ("x", "both"):
        self.options.view_grid_x = _update_one("view_grid_x", "view_grid_x_var", True)

    if axis in ("y", "both"):
        self.options.view_grid_y = _update_one("view_grid_y", "view_grid_y_var", True)

    self.redraw(preserve_view=True)

def toggle_log(self, axis="y"):
    if axis == "x":
        if hasattr(self, "view_log_x_var"):
            self.view_log_x = bool(self.view_log_x_var.get())
        else:
            self.view_log_x = not getattr(self, "view_log_x", False)
    else:
        if hasattr(self, "view_log_y_var"):
            self.view_log_y = bool(self.view_log_y_var.get())
        else:
            self.view_log_y = not getattr(self, "view_log_y", False)
    self.options.view_log_x = bool(getattr(self, "view_log_x", False))
    self.options.view_log_y = bool(getattr(self, "view_log_y", False))
    try:
        self.redraw(preserve_view=True)
    except Exception as e:
        _showerror(self, "Log Scale", str(e))

def toggle_labels(self):
    self.status("Show Labels toggled")

def smooth_main_spectrum(self):
    if not self.spectra:
        return
    self.spectra[0].smooth()
    self.redraw()

def convert_nm_to_angstrom(self):
    for sp in self.spectra:
        sp.x = [x*10 if x < 1500 else x for x in sp.x]
    self.options.convert_to_angstrom = True
    self.wavelength_unit = "angstrom"
    self.redraw()

def load_template_from_menu(self):
    fn = _template_file_dialog(
        self,
        filedialog.askopenfilename,
        title="Load Template",
        initialdir=remembered_initial_dir(self.options),
        filetypes=[("Templates", "*.csv *.db *.DB *.txt"), ("All", "*.*")]
    )
    if not fn:
        return
    remember_working_dir(self.options, fn)
    try:
        self.load_template_file(fn)
        self.redraw()
        self.status(f"Template loaded: {fn}")
    except Exception as e:
        _showerror(self, "Load Template", str(e))

def template_info_from_menu(self):
    lines = self.template_lines
    by_species = {}
    for line in lines:
        if line.specie:
            key = f"{line.specie} {_roman_ion(line.ion) if line.ion else ''}".strip()
            by_species[key] = by_species.get(key, 0) + 1
    msg = f"Lines: {len(lines)}\nAssigned lines: {sum(1 for line in lines if line.specie)}"
    if by_species:
        msg += "\n\n" + "\n".join(f"{key}: {value}" for key, value in sorted(by_species.items()))
    _showinfo(self, "Template Info", msg)

def save_window_positions(self):
    positions = {}
    for key, spec in WINDOW_POSITION_SPECS.items():
        attr = spec["attr"]
        if attr is None:
            win = self
            fallback = self.geometry()
        else:
            win = getattr(self, attr, None)
            fallback = _default_window_geometry(self, key)
        parts = _collect_window_geometry(win, fallback)
        if parts is None:
            continue
        width, height, x, y = parts
        if x is None or y is None:
            saved = _parse_geometry_string(fallback)
            if saved is not None:
                width, height, x, y = saved
        if x is None or y is None:
            x = 0
            y = 0
        positions[f"{key}_X"] = str(x)
        positions[f"{key}_Y"] = str(y)
        positions[f"{key}_W"] = str(width)
        positions[f"{key}_H"] = str(height)
    self.options.window_positions = positions
    path = save_pylibs_ini(self.options)
    self.status(f"Window positions saved: {path}")
    return path

def load_window_positions(self):
    positions = load_window_positions_from_ini("pyLIBS.ini")
    self.options.window_positions = positions
    self.use_saved_window_positions = True
    updated = 0
    for key, spec in WINDOW_POSITION_SPECS.items():
        attr = spec["attr"]
        win = self if attr is None else getattr(self, attr, None)
        try:
            exists = win is not None and win.winfo_exists()
        except Exception:
            exists = False
        if not exists:
            continue
        geometry = _window_geometry_from_positions(positions, key)
        if not geometry:
            continue
        if _set_window_geometry(win, geometry, self if attr is None else self):
            updated += 1
    self.status(f"Window positions loaded: {updated} window(s) updated")
    return positions

def close_template_from_menu(self):
    self.template_lines.clear()
    self.notify_template_changed(redraw=False)
    self.close_template_window()
    self.redraw()
    self.status("Template closed")

def clear_template_data(self):
    self.template_lines.clear()
    self.notify_template_changed(redraw=False)

def invalidate_cflibs_results(self):
    self.last_cflibs_rows = []
    try:
        for child in self.winfo_children():
            if isinstance(child, CFLibsWindow) and child.winfo_exists():
                child.last_rows = []
                child.last_groups = {}
                child.last_fits = {}
                child.disable_opc()
    except Exception:
        pass

def notify_template_changed(self, redraw=False):
    self.invalidate_cflibs_results()
    refreshed = set()
    if self.template_window and self.template_window.winfo_exists():
        try:
            self.template_window.refresh()
            refreshed.add(self.template_window)
        except Exception:
            pass
    try:
        for child in self.winfo_children():
            if child in refreshed:
                continue
            if isinstance(child, (TemplateManager, RetroTemplateManager)) and child.winfo_exists():
                child.refresh()
                refreshed.add(child)
    except Exception:
        pass
    if redraw:
        self.redraw(preserve_view=True)


def _nearest_spectrum_point(self, wavelength):
    """Return (x, y, index) for nearest point in main visible spectrum."""
    if not getattr(self, "spectra", None):
        return (wavelength, 0.0, -1)
    sp = self.spectra[0]
    if not getattr(sp, "x", None):
        return (wavelength, 0.0, -1)
    idx = min(range(len(sp.x)), key=lambda i: abs(sp.x[i] - wavelength))
    return (sp.x[idx], sp.y[idx] if idx < len(sp.y) else 0.0, idx)


def _template_match_index(self, line_or_wavelength, tolerance=None):
    """Return the index of an existing template row matching the same line."""
    if not getattr(self, "template_lines", None):
        return None
    try:
        wave = float(getattr(line_or_wavelength, "fitwavelen", 0.0) or getattr(line_or_wavelength, "wavelen", line_or_wavelength))
    except Exception:
        return None
    if not wave:
        return None
    if tolerance is None:
        tolerance = max(1e-6, abs(safe_float(getattr(self.options, "search_range", 0.2), 0.2)) * 0.02)
    best_i = None
    best_d = None
    for i, t in enumerate(self.template_lines):
        candidates = []
        for attr in ("fitwavelen", "wavelen", "asswavelen"):
            try:
                v = abs(float(getattr(t, attr, 0.0) or 0.0))
                if v:
                    candidates.append(v)
            except Exception:
                pass
        if not candidates:
            continue
        d = min(abs(v - wave) for v in candidates)
        if d <= tolerance and (best_d is None or d < best_d):
            best_i, best_d = i, d
    return best_i


def _merge_template_line(self, new_line, tolerance=None, overwrite_fit=False):
    """Append or update a template row without changing the CSV/template format."""
    idx = self._template_match_index(new_line, tolerance=tolerance)
    if idx is None:
        self.template_lines.append(new_line)
        self.template_lines.sort(key=lambda t: abs(t.fitwavelen) if getattr(t, "fitwavelen", 0.0) else t.wavelen)
        return new_line, True
    old = self.template_lines[idx]
    for attr in ("wavelen", "inte", "templint"):
        val = getattr(new_line, attr, None)
        if val not in (None, ""):
            try:
                if attr == "wavelen" or float(val) != 0.0:
                    setattr(old, attr, val)
            except Exception:
                setattr(old, attr, val)
    for attr in ("specie", "ion", "asswavelen", "ei", "ek", "aki", "gk", "gi", "acc", "wg", "wl", "fitwavelen", "error_inte"):
        val = getattr(new_line, attr, None)
        if attr in ("wg", "wl", "fitwavelen", "error_inte") and not overwrite_fit:
            continue
        if isinstance(val, str):
            if val:
                setattr(old, attr, val)
        else:
            try:
                if val is not None and float(val) != 0.0:
                    setattr(old, attr, val)
            except Exception:
                if val not in (None, ""):
                    setattr(old, attr, val)
    return old, False

def add_template_peak_at(self, wavelength, intensity=None, refresh=True):
    """Manual peak marking: Shift+left click adds a template row."""
    x, y, idx = self._nearest_spectrum_point(wavelength)
    if intensity is None or not intensity:
        intensity = y
    # update existing row if the same line is already present; otherwise append.
    tol = max(1e-6, abs(getattr(self.options, "search_range", 0.2)) * 0.02)
    line, added = self._merge_template_line(
        TemplateLine(
            wavelen=x,
            templint=float(intensity or 0.0),
            inte=None,
            wg=None,
            wl=None,
            fitwavelen=None,
        ),
        tolerance=tol,
    )
    self.notify_template_changed(redraw=False)
    if refresh:
        self.redraw(preserve_view=True)
    self.status(("Marked peak" if added else "Updated marked peak") + f": {x:.4f}")

def delete_template_peak_at(self, wavelength, refresh=True):
    """Delete nearest manually marked/template line, as Shift+right click."""
    if not self.template_lines:
        return
    lo, hi = self.current_xlim()
    pix_tol = abs(hi - lo) * 0.01 if hi > lo else max(0.1, getattr(self.options, "search_range", 0.2))
    idx = min(range(len(self.template_lines)), key=lambda i: abs(self.template_lines[i].wavelen - wavelength))
    if abs(self.template_lines[idx].wavelen - wavelength) > max(pix_tol, getattr(self.options, "search_range", 0.2)):
        self.status("No marked peak close enough to delete")
        return
    removed = self.template_lines.pop(idx)
    self.notify_template_changed(redraw=False)
    if refresh:
        self.redraw(preserve_view=True)
    self.status(f"Deleted marked peak: {removed.wavelen:.4f}")

def _click(self, event):
    """Mouse behavior:

    Shift+left: mark peak and append a template row.
    Shift+right: delete the nearest marked/template line.
    Double left click: query LIBS.db around the clicked wavelength and open
    the Identifications window. Ctrl+left is kept as a compatibility shortcut.
    """
    if event.xdata is None or event.inaxes is not getattr(self, "ax", None):
        return
    capture_window = getattr(self, "shift_capture_window", None)
    if capture_window is not None and capture_window.winfo_exists() and event.button == 1:
        self._nav_press = None
        capture_window.set_from_plot(float(event.xdata), float(event.ydata))
        return
    key = (event.key or "").lower()
    if "shift" in key and event.button == 1:
        self._nav_press = None
        self.add_template_peak_at(event.xdata, event.ydata)
        return
    if "shift" in key and event.button == 3:
        self._nav_press = None
        self.delete_template_peak_at(event.xdata)
        return
    if event.button == 1 and (getattr(event, "dblclick", False) or "control" in key):
        self._nav_press = None
        self.current_identification_wavelength = float(event.xdata)
        self.show_line_identification()
        self.line_window.wave_var.set(f"{event.xdata:.4f}")
        self.line_window.range_var.set(str(self.options.search_range))
        self.line_window.search()
        return
    # Store press point for zoom/pan.  Release decides whether it was
    # a navigation drag or just a click.
    try:
        self._nav_press = (event.button, float(event.xdata), float(event.ydata), int(event.x), int(event.y), tuple(self.ax.get_xlim()), tuple(self.ax.get_ylim()))
        self._nav_dragged = False
    except Exception:
        pass

def find_peaks_basic(self):
    """Prominence-based automatic peak finder used by Analyse > Find Peaks."""
    if not self.spectra:
        return
    if scipy_find_peaks is None:
        _showerror(self, "Find Peaks", "scipy.signal.find_peaks is not available. Install scipy to use Find Peaks.")
        return
    sp = self.spectra[0]
    if len(sp.x) < 3:
        return

    if getattr(self, "ax", None):
        lo, hi = self.current_xlim()
        if lo > hi:
            lo, hi = hi, lo
        points = [(x, y) for x, y in zip(sp.x, sp.y) if lo <= x <= hi]
    else:
        points = list(zip(sp.x, sp.y))
    if len(points) < 3:
        self.status("Find Peaks: no points in the current wavelength window")
        return

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    threshold = max(0.0, safe_float(getattr(self.options, "threshold", 1.0), 1.0))
    ordered = sorted(ys)
    baseline = ordered[max(0, int(0.50 * len(ordered)) - 1)]
    height = baseline + threshold
    dx = [abs(b - a) for a, b in zip(xs, xs[1:]) if b != a]
    median_dx = sorted(dx)[len(dx) // 2] if dx else 1.0
    delta_min = max(0.0, safe_float(getattr(self.options, "delta_min", 1.0), 1.0))
    min_distance = max(3, min(50, int(max(1.0, 0.25 * delta_min / max(median_dx, 1e-12)))))

    peak_indices, props = scipy_find_peaks(
        ys,
        prominence=threshold,
        height=height,
        distance=min_distance,
    )
    prominences = props.get("prominences", [])
    peaks = []
    for pos, prom in zip(peak_indices, prominences):
        peaks.append((xs[int(pos)], ys[int(pos)], float(prom)))
    peaks.sort(key=lambda p: p[2], reverse=True)
    selected = peaks[:100]
    selected.sort(key=lambda p: p[0])
    added = 0
    updated = 0
    tol = max(1e-6, abs(getattr(self.options, "search_range", 0.2)) * 0.02)
    for x, y, _ in selected:
        _, was_added = self._merge_template_line(TemplateLine(wavelen=x, inte=y, templint=y), tolerance=tol)
        if was_added:
            added += 1
        else:
            updated += 1
    self.notify_template_changed(redraw=False)
    self.redraw()
    self.status(f"Find Peaks: {added} new lines, {updated} updated; template total {len(self.template_lines)}")

def on_close(self):
    try:
        self.options.view_grid_x = _view_bool(getattr(self, "view_grid_x", True), True)
        self.options.view_grid_y = _view_bool(getattr(self, "view_grid_y", True), True)
        self.options.view_log_x = bool(getattr(self, "view_log_x", False))
        self.options.view_log_y = bool(getattr(self, "view_log_y", False))
        self.options.background_color = _background_color(getattr(self, "plot_background", "#ffffff"), "#ffffff")
        save_pylibs_ini(self.options)
    except Exception as e:
        logging.warning("Could not save pyLIBS.ini on close: %s", e, exc_info=True)
    self.destroy()

# ---------------------------------------------------------------------------
# Template dialog / file helpers
# ---------------------------------------------------------------------------

def _template_field_value(raw, *, integer=False):
    text = "" if raw is None else str(raw).strip()
    if not text or text == "Empty":
        return None
    if not integer and text.upper() == "ERROR":
        return "ERROR"
    return safe_int(text, None) if integer else safe_float(text, None)


def load_template_lines(filename, columns=None):
    cols = list(columns if columns is not None else RetroTemplateManager.columns)
    rows = []
    with open(filename, "r", encoding="utf-8", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ") if sample.strip() else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if reader.fieldnames and any(name in reader.fieldnames for name in cols):
            for r in reader:
                kw = {}
                for c in cols:
                    v = (r.get(c) or "").strip()
                    if c == "specie":
                        kw[c] = "" if v == "Empty" else v
                    elif c in ("ion", "gk", "gi", "acc"):
                        kw[c] = _template_field_value(v, integer=True)
                    else:
                        kw[c] = _template_field_value(v)
                if kw.get("wavelen") not in (None, "", 0, 0.0):
                    rows.append(TemplateLine(**kw))
        else:
            f.seek(0)
            for line in f:
                parts = line.replace(",", ".").split()
                if not parts:
                    continue
                try:
                    rows.append(TemplateLine(wavelen=float(parts[0])))
                except Exception:
                    pass
    return rows


def _template_window_geometry(template_win, master_win):
    try:
        template_win.update_idletasks()
        if master_win is not None and getattr(master_win, "winfo_exists", lambda: False)():
            master_win.update_idletasks()
            parent_x = master_win.winfo_rootx()
            parent_y = master_win.winfo_rooty()
            parent_w = max(1, master_win.winfo_width() or master_win.winfo_reqwidth())
            parent_h = max(1, master_win.winfo_height() or master_win.winfo_reqheight())
            screen_w = max(1, master_win.winfo_screenwidth())
            screen_h = max(1, master_win.winfo_screenheight())
        else:
            parent_x = 0
            parent_y = 0
            parent_w = 0
            parent_h = 0
            screen_w = max(1, template_win.winfo_screenwidth())
            screen_h = max(1, template_win.winfo_screenheight())
        width = max(1, template_win.winfo_width() or template_win.winfo_reqwidth())
        height = max(1, template_win.winfo_height() or template_win.winfo_reqheight())
        margin = 16
        x = parent_x + parent_w + margin
        y = parent_y
        if x + width > screen_w:
            left_x = parent_x - width - margin
            if left_x >= 0:
                x = left_x
            else:
                x = max(0, min(parent_x, screen_w - width))
        if y + height > screen_h:
            y = max(0, screen_h - height)
        template_win.geometry(f"+{x}+{y}")
        return True
    except Exception:
        return False


def _position_template_window(template_win, master_win):
    return _template_window_geometry(template_win, master_win)


WINDOW_POSITION_SPECS = {
    "Main": {"attr": None, "size": (1280, 720)},
    "ManualFit": {"attr": "manual_fit_window", "size": (840, 540)},
    "AutoFit": {"attr": "auto_fit_window", "size": (840, 540)},
    "Trace": {"attr": "trace_window", "size": (900, 460)},
    "Template": {"attr": "template_window", "size": (1280, 560)},
    "HAlpha": {"attr": "ne_halpha_window", "size": (620, 360)},
    "SahaBoltzmann": {"attr": "saha_window", "size": (1050, 700)},
    "ShowSA": {"attr": "sac_check_window", "size": (585, 400)},
    "CFLIBS": {"attr": "cflibs_window", "size": (1100, 720)},
}


def _parse_geometry_string(geometry):
    text = str(geometry or "").strip()
    if not text:
        return None
    match = re.fullmatch(r"(\d+)x(\d+)(?:([+-]\d+)([+-]\d+))?", text)
    if not match:
        return None
    width = safe_int(match.group(1), 0)
    height = safe_int(match.group(2), 0)
    if width <= 0 or height <= 0:
        return None
    x_text = match.group(3)
    y_text = match.group(4)
    x = safe_int(x_text, 0) if x_text is not None else None
    y = safe_int(y_text, 0) if y_text is not None else None
    return width, height, x, y


def _geometry_string_from_parts(width, height, x, y):
    return f"{max(1, int(width))}x{max(1, int(height))}+{int(x)}+{int(y)}"


def _centered_geometry_for_size(master, width, height):
    try:
        screen_w = master.winfo_screenwidth() if master is not None else 0
        screen_h = master.winfo_screenheight() if master is not None else 0
    except Exception:
        screen_w = 0
        screen_h = 0
    if screen_w <= 0:
        screen_w = 1920
    if screen_h <= 0:
        screen_h = 1080
    x = max(0, (screen_w - max(1, int(width))) // 2)
    y = max(0, (screen_h - max(1, int(height))) // 2)
    return _geometry_string_from_parts(width, height, x, y)


def _default_window_geometry(master, key):
    spec = WINDOW_POSITION_SPECS.get(key)
    if not spec:
        return ""
    width, height = spec["size"]
    return _centered_geometry_for_size(master, width, height)


def _window_geometry_from_positions(positions, key, fallback=""):
    if not positions:
        return fallback
    values = [positions.get(f"{key}_{suffix}", "") for suffix in ("X", "Y", "W", "H")]
    if any(str(v).strip() == "" for v in values):
        return fallback
    x = safe_int(values[0], None)
    y = safe_int(values[1], None)
    width = safe_int(values[2], None)
    height = safe_int(values[3], None)
    if None in (x, y, width, height):
        return fallback
    if width <= 0 or height <= 0:
        return fallback
    return _geometry_string_from_parts(width, height, x, y)


def _set_window_geometry(win, geometry, parent=None):
    if win is None or not geometry:
        return False
    try:
        win.geometry(geometry)
    except Exception:
        return False
    try:
        win.update_idletasks()
    except Exception:
        pass
    try:
        win.state("normal")
    except Exception:
        pass
    return bring_window_to_front(win, parent)


def _saved_window_geometry(owner, key, fallback=""):
    if not getattr(owner, "use_saved_window_positions", False):
        return fallback
    return _window_geometry_from_positions(getattr(owner.options, "window_positions", {}), key, fallback)


def _show_persistent_window(owner, attr_name, factory, key, *, refresh=None, parent=None, center_on_create=True):
    win = getattr(owner, attr_name, None)
    exists = False
    try:
        exists = win is not None and win.winfo_exists()
    except Exception:
        exists = False
    if exists:
        if callable(refresh):
            try:
                refresh(win)
            except TypeError:
                try:
                    refresh()
                except Exception:
                    pass
            except Exception:
                pass
        bring_window_to_front(win, parent or owner)
        return win
    try:
        setattr(owner, attr_name, None)
    except Exception:
        pass
    win = factory()
    setattr(owner, attr_name, win)
    geometry = _saved_window_geometry(owner, key)
    if geometry:
        _set_window_geometry(win, geometry, parent or owner)
    elif center_on_create:
        center_window(win, parent or owner)
        bring_window_to_front(win, parent or owner)
    return win


def _collect_window_geometry(win, fallback_geometry=""):
    try:
        if win is None or not win.winfo_exists():
            return _parse_geometry_string(fallback_geometry)
    except Exception:
        return _parse_geometry_string(fallback_geometry)
    try:
        win.update_idletasks()
    except Exception:
        pass
    try:
        geometry = win.geometry()
    except Exception:
        geometry = ""
    parsed = _parse_geometry_string(geometry)
    if parsed is not None:
        width, height, x, y = parsed
        if x is None or y is None:
            try:
                x = win.winfo_x()
                y = win.winfo_y()
            except Exception:
                pass
        return width, height, x, y
    return _parse_geometry_string(fallback_geometry)


def _template_file_dialog(owner, dialog_func, **kwargs):
    kwargs.setdefault("parent", owner)
    parent = getattr(owner, "master_app", None) or owner
    try:
        restore_lift_focus(owner, parent)
    except Exception:
        pass
    topmost_enabled = False
    try:
        owner.attributes("-topmost", True)
        topmost_enabled = True
    except Exception:
        pass
    try:
        return dialog_func(**kwargs)
    finally:
        if topmost_enabled:
            try:
                owner.attributes("-topmost", False)
            except Exception:
                pass
        try:
            restore_lift_focus(owner, parent)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def ask_open_spectrum(self):
    return self.open_spectrum()

def ask_import_multiple(self):
    return self.append_spectrum()

def ask_save_spectrum(self):
    return self.save_spectrum()

def full_x(self):
    if not getattr(self, "ax", None) or not self.spectra:
        return
    xs = [x for sp in self.spectra if sp.visible for x in sp.x]
    if xs:
        self.clear_fit_artists()
        self.ax.set_xlim(min(xs), max(xs)); self.canvas.draw_idle(); self._update_xscroll()

def full_y(self):
    if not getattr(self, "ax", None) or not self.spectra:
        return
    lo, hi = self.current_xlim()
    ys = []
    for sp in self.spectra:
        if sp.visible:
            ys.extend([y for x, y in zip(sp.x, sp.y) if lo <= x <= hi])
    if not ys:
        ys = [y for sp in self.spectra if sp.visible for y in sp.y]
    if ys:
        pad = 0.03 * (max(ys)-min(ys) or 1.0)
        self.clear_fit_artists()
        self.ax.set_ylim(min(ys)-pad, max(ys)+pad); self.canvas.draw_idle(); self._update_xscroll()

def full_y_main_visible_x(self):
    if not getattr(self, "ax", None) or not self.spectra:
        return False
    lo, hi = self.ax.get_xlim()
    sp = self.spectra[0]
    ys = [y for x, y in zip(sp.x, sp.y) if lo <= x <= hi]
    if not ys:
        return False
    pad = 0.03 * (max(ys) - min(ys) or 1.0)
    self.clear_fit_artists()
    self.ax.set_ylim(min(ys) - pad, max(ys) + pad)
    return True

def expand_x_50(self):
    if not getattr(self, "ax", None) or not self.spectra:
        self.status("Expand X: no spectrum loaded")
        return
    lim = self._full_x_limits()
    if not lim:
        self.status("Expand X: no visible spectrum")
        return
    data_min, data_max = lim
    xmin, xmax = self.ax.get_xlim()
    center = (xmin + xmax) / 2.0
    current_width = abs(xmax - xmin)
    if current_width <= 0:
        return
    new_width = min(current_width * 1.5, data_max - data_min)
    new_xmin = center - new_width / 2.0
    new_xmax = center + new_width / 2.0
    if new_xmin < data_min:
        new_xmin = data_min
        new_xmax = min(data_max, data_min + new_width)
    if new_xmax > data_max:
        new_xmax = data_max
        new_xmin = max(data_min, data_max - new_width)
    self.clear_fit_artists()
    self.ax.set_xlim(new_xmin, new_xmax)
    self.canvas.draw_idle()
    self._update_xscroll()
    self.status(f"Expand X 50%: {new_xmin:.3f} - {new_xmax:.3f}")

def full_scale(self):
    if not getattr(self, "ax", None):
        return
    self.clear_fit_artists()
    self.ax.relim(); self.ax.autoscale(True); self.canvas.draw_idle(); self._update_xscroll()

def show_options(self):
    self.options_window = show_existing_or_create(self, "options_window", lambda: OptionsWindow(self), parent=self)
    return self.options_window

def show_vertical_shift(self):
    self.shift_window = show_existing_or_create(self, "shift_window", lambda: VerticalShiftWindow(self), parent=self)
    return self.shift_window

def show_spectrum_shift(self):
    self.shift_window = show_existing_or_create(self, "shift_window", lambda: SpectrumShiftWindow(self), parent=self)
    return self.shift_window

def show_spectrum_offset(self):
    self.offset_window = show_existing_or_create(self, "offset_window", lambda: SpectrumOffsetWindow(self), parent=self)
    return self.offset_window

def show_batch_statistics(self):
    self.batch_window = show_existing_or_create(self, "batch_window", lambda: BatchStatisticsWindow(self), parent=self)
    return self.batch_window

def show_auto_element_identification(self):
    return AutoElementIdentificationWindow(self)

def show_saha_boltzmann(self):
    self.saha_window = _show_persistent_window(self, "saha_window", lambda: SahaBoltzmannWindow(self), "SahaBoltzmann", parent=self)
    return self.saha_window

def show_cf_libs(self):
    self.cflibs_window = _show_persistent_window(self, "cflibs_window", lambda: CFLibsWindow(self), "CFLIBS", parent=self)
    return self.cflibs_window

def show_sac_window(self):
    self.sac_window = show_existing_or_create(self, "sac_window", lambda: SACWindow(self), parent=self)
    return self.sac_window

def load_template_file(self, filename):
    self.template_lines = load_template_lines(filename, RetroTemplateManager.columns)
    self.notify_template_changed(redraw=False)
    self.redraw()

def save_template_file(self, filename):
    save_template_lines(filename, self.template_lines, RetroTemplateManager.columns)

def _full_x_limits(self):
    xs = [x for sp in getattr(self, "spectra", []) if getattr(sp, "visible", True) for x in getattr(sp, "x", [])]
    if not xs:
        return None
    return (min(xs), max(xs))

def _update_xscroll(self):
    if not hasattr(self, "xscroll_var") or not getattr(self, "ax", None):
        return
    lim = self._full_x_limits()
    if not lim:
        return
    f0, f1 = lim
    lo, hi = self.ax.get_xlim()
    width = hi - lo
    span = f1 - f0
    value = 0.0 if span <= width or span <= 0 else max(0.0, min(100.0, 100.0 * (lo - f0) / (span - width)))
    self._xscroll_updating = True
    try:
        self.xscroll_var.set(value)
    finally:
        self._xscroll_updating = False

def _xscroll_changed(self, value):
    if getattr(self, "_xscroll_updating", False) or not getattr(self, "ax", None):
        return
    lim = self._full_x_limits()
    if not lim:
        return
    f0, f1 = lim
    lo, hi = self.ax.get_xlim()
    width = hi - lo
    span = f1 - f0
    if span <= 0 or width >= span:
        return
    frac = max(0.0, min(100.0, float(value))) / 100.0
    new_lo = f0 + frac * (span - width)
    self.clear_fit_artists()
    self.ax.set_xlim(new_lo, new_lo + width)
    self.canvas.draw_idle()

def _zoom_out_from_box(self, x0, x1, y0, y1):
    curx = self.ax.get_xlim(); cury = self.ax.get_ylim()
    cx = (x0 + x1) / 2.0; cy = (y0 + y1) / 2.0
    # Make the chosen rectangle represent the old window inside a larger view.
    box_w = abs(x1 - x0) or (curx[1] - curx[0]) * 0.5
    box_h = abs(y1 - y0) or (cury[1] - cury[0]) * 0.5
    factor_x = max(1.5, min(20.0, (curx[1] - curx[0]) / box_w))
    factor_y = max(1.5, min(20.0, (cury[1] - cury[0]) / box_h))
    new_w = (curx[1] - curx[0]) * factor_x
    new_h = (cury[1] - cury[0]) * factor_y
    self.clear_fit_artists()
    self.ax.set_xlim(cx - new_w/2, cx + new_w/2)
    self.ax.set_ylim(cy - new_h/2, cy + new_h/2)

def _release(self, event):
    press = getattr(self, "_nav_press", None)
    self._nav_press = None
    if not press or event.xdata is None or event.ydata is None or event.inaxes is not getattr(self, "ax", None) or not getattr(self, "ax", None):
        return
    button, x0, y0, px0, py0, old_xlim, old_ylim = press
    dxpix = (event.x or px0) - px0
    dypix = (event.y or py0) - py0
    if abs(dxpix) < 6 or abs(dypix) < 6:
        self._nav_dragged = False
        return
    dxdata = event.xdata - x0
    dydata = event.ydata - y0
    if button == 1:
        # Old convention: drag left-high -> right-low to zoom in;
        # reverse direction restores the full spectrum.
        if dxdata > 0 and dydata < 0:
            self.clear_fit_artists()
            self.ax.set_xlim(min(x0, event.xdata), max(x0, event.xdata))
            self.ax.set_ylim(min(y0, event.ydata), max(y0, event.ydata))
        elif dxdata < 0 and dydata > 0:
            self.full_scale()
            self._nav_dragged = True
            return
        self.canvas.draw_idle(); self._update_xscroll()
    elif button == 3:
        dx = event.xdata - x0
        dy = event.ydata - y0
        self.clear_fit_artists()
        self.ax.set_xlim(old_xlim[0]-dx, old_xlim[1]-dx)
        self.ax.set_ylim(old_ylim[0]-dy, old_ylim[1]-dy)
        self.canvas.draw_idle(); self._update_xscroll()
    self._nav_dragged = True

def goto_wavelength(self, wavelength):
    if not getattr(self, "ax", None):
        return
    delta = max(float(getattr(self.options, "delta_min", 1.0) or 1.0), 1e-9)
    half_window = 3.0 * delta
    self.clear_fit_artists()
    self.ax.set_xlim(wavelength - half_window, wavelength + half_window)
    self.full_y_main_visible_x()
    self.canvas.draw_idle(); self._update_xscroll()
    self.status(f"GoTo: {wavelength:.4f} Å  (window ±{half_window:g} Å)")

# Compatibility glue for the retro UI layer. Keep these monkey patches until
# the corresponding class methods are migrated in a dedicated pass.
_RETRO_METHODS = [
    build_retro_menu, build_retro_toolbar, install_retro_ui,
    show_template_window, show_template_manager, close_template_window, show_active_spectra, show_retro_fit_manager, show_single_fit_manager, show_auto_fit_manager,
    compare_spectrum, swap_spectra, clear_all_spectra, save_with_labels, print_plot,
    copy_plot, change_background, toggle_grid, toggle_log,
    toggle_labels, smooth_main_spectrum,
    convert_nm_to_angstrom, load_template_from_menu, template_info_from_menu, save_window_positions, load_window_positions,
    close_template_from_menu, clear_template_data, invalidate_cflibs_results, notify_template_changed, _nearest_spectrum_point, _template_match_index, _merge_template_line, add_template_peak_at, delete_template_peak_at, _click, find_peaks_basic, show_manual, show_about, on_close,
    ask_open_spectrum, ask_import_multiple, ask_save_spectrum, full_x, full_y,
    full_y_main_visible_x,
    expand_x_50, full_scale, show_options, show_vertical_shift, show_spectrum_shift, show_spectrum_offset, show_batch_statistics, show_statistics,
    show_auto_element_identification, show_saha_boltzmann, show_cf_libs,
    show_sac_window, load_template_file, save_template_file, _show_fit_manager,
    _full_x_limits, _update_xscroll, _xscroll_changed, _zoom_out_from_box, _release,
    goto_wavelength, show_goto_dialog,
]
for _m in _RETRO_METHODS:
    setattr(MainWindow, _m.__name__, _m)

if __name__ == "__main__":
    root = MainWindow()
    root.install_retro_ui()
    root.mainloop()
