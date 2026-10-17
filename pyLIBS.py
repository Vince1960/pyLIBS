#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyLIBS Python application
Originally developed as LIBS++ by Vincenzo Palleschi and coworkers,
© 2026 Vincenzo Palleschi. Licensed under CC BY-NC 4.0 for non-commercial use with attribution

"""

from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from datetime import datetime
import hashlib
import json
import logging
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
from collections import defaultdict
import tkinter as tk
from dataclasses import dataclass, field, replace
from pathlib import Path
from tkinter import filedialog, ttk, colorchooser, simpledialog
from typing import Optional

from pylibs.core.models import AtomicLine, TemplateLine
from pylibs.core.instrument_response import (
    InstrumentResponseLibrary,
    ResponseCurve,
    extract_window_tag,
    parse_lsf_widths,
    parse_response_paths,
    serialize_lsf_widths,
    serialize_response_paths,
)
from pylibs.core.preprocessing import subtract_dark
from pylibs.core.analysis_workflow import (
    irsac_correction_status,
    theoretical_spectrum_readiness,
)
from pylibs.core.boltzmann import (
    ENERGY_INTENSITY_MODE,
    PHOTON_INTENSITY_MODE,
    normalize_intensity_mode,
    radiometric_boltzmann_ordinate,
    radiometric_line_intensity_from_ordinate,
    wavelength_in_nm,
)
from pylibs.core.self_absorption import (
    LineCorrection,
    LineObservation,
    assess_self_absorption,
    hybrid_self_absorption,
    palleschi_sac_multiplier,
    thermometric_temperature,
)
from pylibs.core.theoretical_spectrum import (
    TheoreticalLine,
    rescale_model_to_observation,
    synthesize_voigt_spectrum,
)
from pylibs.core.wavelength_calibration import (
    CalibrationAnchor,
    WindowCalibration,
    calibration_for_window,
    estimate_window_calibration,
    fit_wavelength_calibration,
    parse_calibrations,
    serialize_calibrations,
)
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
    read_ascii_metadata,
    read_ascii_spectrum,
    read_ascii_spectrum_columns,
    convert_csv_batch,
    read_roh_spectrum,
    write_ascii_spectrum,
    is_roh_spectrum_file,
)
from pylibs.io.andor_sif import convert_sif_batch
from pylibs.gui.icons import get_cached_menu_icon
from pylibs.gui.toolbar import build_retro_toolbar
from pylibs.gui.helpers import (
    _prepare_messagebox_parent,
    add_context_help_button,
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
    _population_statistics,
    show_statistics,
)
from pylibs.utils.constants import (
    APP_TITLE,
    SPLASH_DURATION_MS,
    SPLASH_SECONDS,
    APP_VERSION,
)
from pylibs.utils.formatting import (
    format_scientific_display_value,
    format_template_display_value,
    safe_float,
    safe_int,
)
from pylibs.utils.paths import (
    app_base_dir,
    resource_path,
)

ANALYTICAL_LINE_LIBRARY_FILENAME = "analytical_line_library.txt"
DEFAULT_ANALYTICAL_LINE_LIBRARY_FILENAME = "analytical_line_library.default.txt"
HALPHA_CENTER_NM = 656.28


_DARK_SUBTRACTION_LABELS = {
    "auto_columns": "Automatic from auxiliary columns",
    "constant": "Constant dark level",
    "file": "Dark-spectrum file",
    "none": "No dark subtraction",
}
_VOIGT_BASELINE_LABELS = {
    "local_linear": "Local linear baseline",
    "origin_constant": "Local constant baseline",
    "libs_auto": "Adaptive baseline-to-baseline limits",
}
_SELF_ABSORPTION_MODE_LABELS = {
    "hybrid": "Combined Stark-width and IRSAC correction",
    "palleschi": "Stark-linewidth correction",
    "irsac": "IRSAC internal-reference correction",
}
_BOLTZMANN_INTENSITY_LABELS = {
    ENERGY_INTENSITY_MODE: "Energy-domain response (convert with λ/hc)",
    PHOTON_INTENSITY_MODE: "Photon-counting response (original pyLIBS)",
}


def _option_key_from_label(labels, value, default):
    """Return the stable option key for either a key or its GUI label."""
    text = str(value or "").strip()
    if text in labels:
        return text
    for key, label in labels.items():
        if text == label:
            return key
    return default


def _enable_windows_dpi_awareness() -> bool:
    """Opt out of Windows bitmap scaling before the first Tk window exists."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        user32 = ctypes.windll.user32
        try:
            if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                return True
        except Exception:
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return True
        except Exception:
            pass
        user32.SetProcessDPIAware()
        return True
    except Exception:
        return False


_WINDOWS_DPI_AWARE = _enable_windows_dpi_awareness()


def _configure_tk_scaling(root) -> float:
    dpi = 96.0
    try:
        root.update_idletasks()
        dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes

            detected = int(ctypes.windll.user32.GetDpiForWindow(root.winfo_id()))
            if detected > 0:
                dpi = float(detected)
        except Exception:
            pass
    dpi = min(max(dpi, 72.0), 384.0)
    try:
        root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass
    root.display_dpi = dpi
    return dpi


def _figure_dpi(widget) -> float:
    try:
        return min(max(float(widget.winfo_toplevel().display_dpi), 96.0), 220.0)
    except Exception:
        return 100.0

try:
    from openpyxl import Workbook
except Exception:  # pragma: no cover - optional dependency
    Workbook = None

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
    if not os.environ.get("MPLBACKEND"):
        matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.colors import to_hex as _matplotlib_to_hex
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
except Exception:
    Figure = None
    FigureCanvasTkAgg = None
    _matplotlib_to_hex = None
    Rectangle = None


@dataclass
class AppOptions:
    username: str = ""
    limit_low: float = 2000.0
    limit_high: float = 10000.0
    threshold: float = 1.0
    delta_min: float = 0.5
    search_range: float = 1.0
    apply_response: bool = False
    apply_before: bool = True
    apply_after: bool = False
    response_file: str = ""
    response_files: str = ""
    lsf_widths: str = "{}"
    libs_db_file: str = "LIBS.db"
    single_file_correction: bool = False
    single_file_path: str = ""
    instrumental_width: float = 0.0
    fix_wg: bool = False
    fixed_wg: float = 0.5
    fix_wl: bool = False
    fixed_wl: float = 0.5
    voigt_baseline_mode: str = "local_linear"
    voigt_fit_ranges: str = "{}"
    voigt_fit_range_sources: str = "{}"
    aki_threshold: float = 1.0e5
    boltzmann_intensity_mode: str = ENERGY_INTENSITY_MODE
    ne_low: float = 1e15
    ne_high: float = 1e18
    kt_low: float = 0.5
    kt_high: float = 3.0
    fix_wavelength: bool = False
    convert_to_angstrom: bool = False
    iterations: int = 20
    auto_offset: bool = False
    auto_shift: float = 0.0
    auto_wavelength_calibration: bool = True
    wavelength_calibrations: str = "[]"
    ha_lines: int = 1
    ha_range: float = 150.0
    ha_wl1: float = 6562.8
    ha_wl2: float = 6490.0
    ha_dl1: float = 40.0
    ha_dl2: float = 50.0
    ha_kt: float = 1.0
    remember_ne_for_series: bool = False
    echelle: bool = False
    input_dir: str = ""
    view_grid_x: bool = True
    view_grid_y: bool = True
    view_log_x: bool = False
    view_log_y: bool = False
    background_color: str = "#ffffff"
    dark_mode: str = "auto_columns"
    signal_column: int = 0
    dark_columns: str = ""
    dark_constant: float = 0.0
    dark_file: str = ""
    irsac_mode: str = "irsac"
    irsac_iterations: int = 100
    irsac_tolerance: float = 0.001
    irsac_thermometric_species: str = ""
    irsac_reference_lines: str = "{}"
    irsac_equation_mode: str = "staged"
    cflibs_intercept_mode: str = "fixed_temperature"
    cflibs_ionization_mode: str = "saha"
    cflibs_neutral_fractions: str = ""
    strict_quantitation: bool = True
    quality_min_temperature_lines: int = 4
    quality_min_temperature_levels: int = 3
    quality_min_energy_span_ev: float = 1.5
    quality_min_temperature_r2: float = 0.98
    quality_max_relative_slope_error: float = 0.15
    quality_max_loo_relative_span: float = 0.25
    quality_max_line_population_factor: float = 1.5
    quality_max_replicate_area_cv: float = 0.25
    quality_min_composition_lines: int = 3
    quality_max_composition_loo_relative_change: float = 0.20
    quality_max_replicate_composition_cv: float = 0.15
    quality_max_parameter_composition_relative_change: float = 0.20
    quality_require_replicate_composition: bool = True
    quality_min_halpha_r2: float = 0.90
    quality_min_halpha_snr: float = 5.0
    quality_max_ne_relative_uncertainty: float = 0.20
    quality_min_mcwhirter_margin: float = 3.0
    quality_min_observed_stage_fraction: float = 0.05
    quality_max_stage_balance_factor: float = 3.0
    theoretical_aki_threshold: float = 1.0e5
    ini_file: str = "pyLIBS.ini"
    window_positions: dict[str, str] = field(default_factory=dict)


def set_session_electron_density(app, value, source):
    """Store the active Ne together with its measurement provenance."""
    ne = safe_float(value, 0.0)
    if not math.isfinite(ne) or ne <= 0.0:
        app.session_ne = None
        app.session_ne_source = None
        return None
    label = str(source or "unspecified source").strip()
    app.session_ne = ne
    app.session_ne_source = label
    app.last_known_ne = ne
    app.last_known_ne_source = label
    return ne


def active_electron_density(app):
    """Return only a deliberately active Ne; never invent a default value."""
    ne = safe_float(getattr(app, "session_ne", 0.0), 0.0)
    if not math.isfinite(ne) or ne <= 0.0:
        return None, "not set"
    source = str(
        getattr(app, "session_ne_source", "") or "unspecified source"
    ).strip()
    return ne, source


def reset_measurement_session(app, *, preserve_series_ne=None):
    """Discard state that belongs to the previous measured sample.

    Instrument-response/OPC files remain loaded by design, but fitted results,
    thermodynamic inputs and nominal-standard entries must not silently leak
    into a newly opened spectrum. Ne is retained only when the dedicated
    series option is enabled, and its provenance is labelled accordingly.
    """
    previous_ne, previous_ne_source = active_electron_density(app)
    if previous_ne is not None:
        app.last_known_ne = previous_ne
        app.last_known_ne_source = previous_ne_source
    if preserve_series_ne is None:
        preserve_series_ne = bool(
            getattr(getattr(app, "options", None), "remember_ne_for_series", False)
        )

    app.last_halpha_result = None
    app.last_saha_boltzmann = None
    app.last_cflibs_rows = []
    app.last_cflibs_quality = None
    app.last_cflibs_robustness = None
    app.session_temperature = None
    app.session_temperature_source = None
    app.post_irsac_temperature = None
    app.post_irsac_temperature_source = None
    app.opc_nominal_percent = {}
    app.opc_nominal_inputs = {
        "mass_percent": {},
        "number_percent": {},
    }
    app.session_voigt_fit_range_keys = set()

    if previous_ne is not None and preserve_series_ne:
        set_session_electron_density(
            app,
            previous_ne,
            f"series carry-over from {previous_ne_source}",
        )
        return (
            f"Ne retained for series: {previous_ne:.6e} e/cm3 "
            f"(from {previous_ne_source})"
        )

    app.session_ne = None
    app.session_ne_source = None
    if previous_ne is None:
        return "Ne not set"
    return "Ne cleared for the new measurement"


_PENDING_SCIENTIFIC_SETTINGS = "pyLIBS.pending-scientific-settings.json"
_SCIENTIFIC_SETTING_CASTERS = {
    "delta_min": float,
    "voigt_baseline_mode": str,
    "voigt_fit_ranges": str,
    "irsac_reference_lines": str,
    "irsac_equation_mode": str,
    "cflibs_intercept_mode": str,
    "cflibs_ionization_mode": str,
    "cflibs_neutral_fractions": str,
}


def apply_pending_scientific_settings(
    options,
    pending_path=None,
    *,
    persist=True,
    consume=False,
):
    """Apply a one-shot validated settings update after an in-use deployment."""
    path = Path(
        pending_path
        if pending_path is not None
        else resource_path(_PENDING_SCIENTIFIC_SETTINGS)
    )
    if not path.exists():
        return False
    values = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(values, dict):
        raise ValueError("Pending scientific settings must be a JSON object.")
    missing = sorted(set(_SCIENTIFIC_SETTING_CASTERS) - set(values))
    if missing:
        raise ValueError(
            "Pending scientific settings are incomplete: "
            + ", ".join(missing)
        )
    for key, caster in _SCIENTIFIC_SETTING_CASTERS.items():
        setattr(options, key, caster(values[key]))
    if persist:
        save_pylibs_ini(options)
    if consume:
        path.unlink()
    return True


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
        style.configure(".", font=("Segoe UI", 9))
        style.configure("TFrame", background=RETRO_BG)
        style.configure("TLabel", background=RETRO_BG)
        style.configure("TLabelframe", background=RETRO_BG)
        style.configure("TLabelframe.Label", background=RETRO_BG)
        style.configure("TButton", padding=(5, 1))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=22)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
    except Exception:
        pass


def _main_window_status_text():
    return "pyLIBS Software for Spectral Analysis  |  Open a file to start"


def _menu_separator(menu):
    try:
        menu.add_separator()
    except Exception:
        pass


@dataclass(frozen=True)
class SpectrumSourceWindow:
    x: tuple[float, ...]
    y: tuple[float, ...]
    name: str
    filename: str = ""
    dark_corrected: bool = False
    dark_source: str = ""
    signal_column: int = 1
    dark_columns: tuple[int, ...] = ()
    raw_x: tuple[float, ...] = ()
    calibration_intercept: float = 0.0
    calibration_slope: float = 1.0
    calibration_model: str = ""
    calibration_rms: float = 0.0
    replicate_files: tuple[str, ...] = ()


@dataclass
class Spectrum:
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    name: str = "Spectrum"
    filename: str = ""
    visible: bool = True
    color: Optional[str] = None
    response_corrected: bool = False
    response_sources: tuple[str, ...] = field(default_factory=tuple)
    response_trim_info: str = ""
    dark_corrected: bool = False
    dark_source: str = ""
    signal_column: int = 1
    dark_columns: tuple[int, ...] = ()
    replicate_files: tuple[str, ...] = field(default_factory=tuple)
    source_windows: tuple[SpectrumSourceWindow, ...] = field(default_factory=tuple, repr=False)

    def __post_init__(self):
        if not self.source_windows:
            self.capture_source()

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

    def capture_source(self):
        self.source_windows = (
            SpectrumSourceWindow(
                tuple(self.x), tuple(self.y), self.name, self.filename,
                self.dark_corrected, self.dark_source, self.signal_column, self.dark_columns,
                tuple(self.x),
                replicate_files=tuple(self.replicate_files),
            ),
        )

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
        corrected_x, corrected_y, info = response.correct(self.x, self.y)
        self.x = corrected_x
        self.y = corrected_y
        self.response_corrected = True
        self.response_sources = (response.filename,)
        self.response_trim_info = info

    def shifted(self, offset: float, name: str) -> "Spectrum":
        return Spectrum(
            list(self.x), [v + offset for v in self.y], name=name,
            response_corrected=self.response_corrected,
            response_sources=self.response_sources,
            response_trim_info=self.response_trim_info,
            dark_corrected=self.dark_corrected,
            dark_source=self.dark_source,
            signal_column=self.signal_column,
            dark_columns=self.dark_columns,
            replicate_files=self.replicate_files,
        )

    def scaled(self, factor: float, name: str) -> "Spectrum":
        return Spectrum(
            list(self.x), [v * factor for v in self.y], name=name,
            response_corrected=self.response_corrected,
            response_sources=self.response_sources,
            response_trim_info=self.response_trim_info,
            dark_corrected=self.dark_corrected,
            dark_source=self.dark_source,
            signal_column=self.signal_column,
            dark_columns=self.dark_columns,
            replicate_files=self.replicate_files,
        )


def _source_raw_axis(source: SpectrumSourceWindow) -> tuple[float, ...]:
    raw = tuple(getattr(source, "raw_x", ()) or ())
    return raw if raw else tuple(source.x)


def _store_line_fit_provenance(line: TemplateLine, spectrum: Spectrum):
    """Remember the detector window and response curve that produced a fit."""
    sources = tuple(getattr(spectrum, "source_windows", ()) or ())
    source = sources[0] if len(sources) == 1 else None
    line.fit_source_window = str(
        getattr(source, "name", "") if source is not None else getattr(spectrum, "name", "")
    )
    response_sources = tuple(getattr(spectrum, "response_sources", ()) or ())
    line.fit_response_source = response_sources[0] if len(response_sources) == 1 else ""
    line.fit_calibration_intercept = safe_float(
        getattr(source, "calibration_intercept", 0.0) if source is not None else 0.0,
        0.0,
    )
    line.fit_calibration_slope = safe_float(
        getattr(source, "calibration_slope", 1.0) if source is not None else 1.0,
        1.0,
    )


def _calibrated_source_window(
    source: SpectrumSourceWindow,
    calibration: Optional[WindowCalibration] = None,
    legacy_shift: float = 0.0,
) -> SpectrumSourceWindow:
    raw_x = _source_raw_axis(source)
    if calibration is not None:
        intercept = float(calibration.intercept)
        slope = float(calibration.slope)
        model = str(calibration.model)
        rms = float(calibration.rms)
    else:
        intercept = float(legacy_shift)
        slope = 1.0
        model = "legacy-offset" if legacy_shift else ""
        rms = 0.0
    corrected_x = tuple(intercept + slope * float(x) for x in raw_x)
    return SpectrumSourceWindow(
        corrected_x,
        tuple(source.y),
        source.name,
        source.filename,
        source.dark_corrected,
        source.dark_source,
        source.signal_column,
        source.dark_columns,
        raw_x,
        intercept,
        slope,
        model,
        rms,
        tuple(getattr(source, "replicate_files", ()) or ()),
    )


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


def _quantile(values, fraction: float) -> float:
    ordered = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _short_display_crossfade(
    lower_points: list[tuple[float, float]],
    upper_points: list[tuple[float, float]],
    overlap_x: list[float],
    overlap_lo: float,
    overlap_hi: float,
) -> tuple[float, float]:
    """Locate a quiet central splice and blend about five detector samples.

    The quiet-point search is intentionally local to the middle of the overlap.
    Searching the whole overlap can let one detector dominate almost completely;
    a real line present in the more central window would then disappear from the
    joined display merely because the adjacent window is flat at that wavelength.
    """
    if overlap_hi <= overlap_lo or len(overlap_x) < 2:
        return 0.5 * (overlap_lo + overlap_hi), 0.0

    lower_y = [_interp_spectrum_value(lower_points, x) for x in overlap_x]
    upper_y = [_interp_spectrum_value(upper_points, x) for x in overlap_x]

    def normalized_levels(values):
        floor = _quantile(values, 0.10)
        ceiling = _quantile(values, 0.90)
        scale = max(ceiling - floor, max((abs(value) for value in values), default=0.0) * 1.0e-12, 1.0e-30)
        return [max(0.0, (value - floor) / scale) for value in values], scale

    lower_level, lower_scale = normalized_levels(lower_y)
    upper_level, upper_scale = normalized_levels(upper_y)

    def local_gradient(values, index, scale):
        left = values[max(0, index - 1)]
        right = values[min(len(values) - 1, index + 1)]
        return abs(right - left) / max(scale, 1.0e-30)

    def typical_step(points):
        steps = [
            right[0] - left[0]
            for left, right in zip(points, points[1:])
            if right[0] > left[0] and overlap_lo <= left[0] <= overlap_hi
        ]
        return _quantile(steps, 0.50) if steps else 0.0

    detector_step = max(typical_step(lower_points), typical_step(upper_points))
    overlap_span = overlap_hi - overlap_lo
    # Two samples on either side give a five-sample transition at equal sampling.
    half_width = min(2.0 * detector_step, 0.10 * overlap_span) if detector_step > 0.0 else 0.0
    interior = [
        index
        for index, wavelength in enumerate(overlap_x)
        if overlap_lo + half_width <= wavelength <= overlap_hi - half_width
    ] or list(range(len(overlap_x)))
    midpoint = 0.5 * (overlap_lo + overlap_hi)
    # Preserve the natural ownership of an overlap: the lower-wavelength window
    # supplies its first half and the upper-wavelength window its second half.
    # Within this central band we still choose the quietest point, so the splice
    # does not cut directly through a spectral line when a nearby valley exists.
    central_half_span = max(4.0 * detector_step, 0.10 * overlap_span)
    central_interior = [
        index
        for index in interior
        if abs(overlap_x[index] - midpoint) <= central_half_span
    ]
    if central_interior:
        interior = central_interior
    disagreement_scale = max(
        lower_scale,
        upper_scale,
        max((abs(value) for value in lower_y + upper_y), default=0.0),
        1.0e-30,
    )

    def splice_score(index):
        disagreement = abs(lower_y[index] - upper_y[index]) / disagreement_scale
        gradient = (
            local_gradient(lower_y, index, lower_scale)
            + local_gradient(upper_y, index, upper_scale)
        )
        central_tie_break = abs(overlap_x[index] - midpoint) / overlap_span
        return (
            lower_level[index]
            + upper_level[index]
            + 0.35 * gradient
            + 0.25 * disagreement
            + 0.01 * central_tie_break
        )

    best_index = min(interior, key=splice_score)
    return overlap_x[best_index], half_width


def merge_spectra_by_wavelength(first: Spectrum, second: Spectrum, name: str = "Merged spectrum") -> Spectrum:
    """Build a display spectrum using a short crossfade in a quiet overlap region."""
    p1 = sorted(zip(first.x, first.y), key=lambda p: p[0])
    p2 = sorted(zip(second.x, second.y), key=lambda p: p[0])
    if not p1:
        return Spectrum(
            [x for x, _ in p2], [y for _, y in p2], name=name, filename=second.filename,
            response_corrected=second.response_corrected,
            response_sources=second.response_sources,
            response_trim_info=second.response_trim_info,
            dark_corrected=second.dark_corrected,
            dark_source=second.dark_source,
            signal_column=second.signal_column,
            dark_columns=second.dark_columns,
            source_windows=second.source_windows,
            replicate_files=second.replicate_files,
        )
    if not p2:
        return Spectrum(
            [x for x, _ in p1], [y for _, y in p1], name=name, filename=first.filename,
            response_corrected=first.response_corrected,
            response_sources=first.response_sources,
            response_trim_info=first.response_trim_info,
            dark_corrected=first.dark_corrected,
            dark_source=first.dark_source,
            signal_column=first.signal_column,
            dark_columns=first.dark_columns,
            source_windows=first.source_windows,
            replicate_files=first.replicate_files,
        )

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
        first_is_lower = 0.5 * (lo1 + hi1) <= 0.5 * (lo2 + hi2)
        lower_points, upper_points = (p1, p2) if first_is_lower else (p2, p1)
        splice, blend_half_width = _short_display_crossfade(
            lower_points,
            upper_points,
            overlap_x,
            overlap_lo,
            overlap_hi,
        )
        blend_lo = splice - blend_half_width
        blend_hi = splice + blend_half_width
        for x in overlap_x:
            lower_y = _interp_spectrum_value(lower_points, x)
            upper_y = _interp_spectrum_value(upper_points, x)
            if blend_half_width <= 0.0:
                y = lower_y if x < splice else upper_y
            elif x <= blend_lo:
                y = lower_y
            elif x >= blend_hi:
                y = upper_y
            else:
                fraction = (x - blend_lo) / (blend_hi - blend_lo)
                y = (1.0 - fraction) * lower_y + fraction * upper_y
            merged.append((x, y))
    else:
        merged.extend(p1)
        merged.extend(p2)

    merged.sort(key=lambda p: p[0])
    response_sources = tuple(dict.fromkeys(first.response_sources + second.response_sources))
    trim_info = "; ".join(value for value in (first.response_trim_info, second.response_trim_info) if value)
    return Spectrum(
        [x for x, _ in merged], [y for _, y in merged], name=name,
        response_corrected=first.response_corrected and second.response_corrected,
        response_sources=response_sources,
        response_trim_info=trim_info,
        dark_corrected=first.dark_corrected and second.dark_corrected,
        dark_source="; ".join(value for value in (first.dark_source, second.dark_source) if value),
        signal_column=first.signal_column,
        dark_columns=tuple(dict.fromkeys(first.dark_columns + second.dark_columns)),
        source_windows=first.source_windows + second.source_windows,
        replicate_files=tuple(dict.fromkeys(first.replicate_files + second.replicate_files)),
    )


def spectrum_plot_segments(spectrum: Spectrum) -> list[tuple[list[float], list[float]]]:
    """Return continuous display segments without changing the spectral data.

    A joined spectrum can contain wavelength intervals that were never measured.
    Matplotlib would otherwise draw a straight line from the last sample of one
    detector window to the first sample of the next.
    """
    points = sorted(
        (
            (float(x), float(y))
            for x, y in zip(getattr(spectrum, "x", []) or [], getattr(spectrum, "y", []) or [])
            if math.isfinite(float(x)) and math.isfinite(float(y))
        ),
        key=lambda point: point[0],
    )
    if not points:
        return []

    def split_sampling_gaps(values):
        if len(values) < 3:
            return [values] if values else []
        steps = [b[0] - a[0] for a, b in zip(values, values[1:]) if b[0] > a[0]]
        typical_step = sorted(steps)[len(steps) // 2] if steps else 0.0
        gap_limit = typical_step * 20.0 if typical_step > 0.0 else math.inf
        result = []
        current = [values[0]]
        for previous, point in zip(values, values[1:]):
            if point[0] - previous[0] > gap_limit:
                result.append(current)
                current = []
            current.append(point)
        if current:
            result.append(current)
        return result

    intervals = []
    for source in getattr(spectrum, "source_windows", ()) or ():
        values = [float(x) for x in getattr(source, "x", ()) or () if math.isfinite(float(x))]
        if values:
            intervals.append((min(values), max(values)))
    intervals.sort()

    if intervals:
        data_low, data_high = points[0][0], points[-1][0]
        if not any(high >= data_low and low <= data_high for low, high in intervals):
            intervals = []

    if intervals:
        merged_intervals = []
        for low, high in intervals:
            if not merged_intervals or low > merged_intervals[-1][1]:
                merged_intervals.append([low, high])
            else:
                merged_intervals[-1][1] = max(merged_intervals[-1][1], high)
        segments = []
        for low, high in merged_intervals:
            segment = [(x, y) for x, y in points if low <= x <= high]
            for continuous in split_sampling_gaps(segment):
                segments.append(([x for x, _ in continuous], [y for _, y in continuous]))
        if segments:
            return segments

    segments = split_sampling_gaps(points)
    return [([x for x, _ in segment], [y for _, y in segment]) for segment in segments if segment]


def spectrum_wavelength_intervals(spectrum: Spectrum) -> list[tuple[float, float]]:
    """Return only wavelength intervals containing actually acquired samples."""
    intervals = []
    for segment_x, _segment_y in spectrum_plot_segments(spectrum):
        finite = [float(value) for value in segment_x if math.isfinite(float(value))]
        if finite:
            intervals.append((min(finite), max(finite)))
    return intervals


def wavelength_is_acquired(
    app: "MainWindow",
    wavelength: float,
    *,
    include_visible_comparisons: bool = False,
) -> bool:
    """Check a wavelength against each acquired detector window, not min/max."""
    value = safe_float(wavelength, math.nan)
    if not math.isfinite(value):
        return False
    spectra = list(getattr(app, "spectra", []) or [])
    if not spectra:
        # Coverage becomes authoritative as soon as a spectrum is loaded.
        return True
    use_all_windows = bool(getattr(app, "independent_window_mode", False))
    candidates = (
        [spectrum for spectrum in spectra if getattr(spectrum, "visible", True)]
        if include_visible_comparisons or use_all_windows
        else spectra[:1]
    )
    return any(
        low <= value <= high
        for spectrum in candidates
        for low, high in spectrum_wavelength_intervals(spectrum)
    )


def _selected_active_spectrum(app: "MainWindow") -> Optional[Spectrum]:
    """Return the spectrum selected in Active Spectra, when available."""
    try:
        window = getattr(app, "active_window", None)
        if window is not None and window.winfo_exists():
            index = safe_int(getattr(window, "selected_index", -1), -1)
            spectra = list(getattr(app, "spectra", []) or [])
            if 0 <= index < len(spectra):
                spectrum = spectra[index]
                if getattr(spectrum, "visible", True):
                    return spectrum
    except Exception:
        pass
    return None


def spectrum_covers_wavelengths(spectrum: Spectrum, wavelengths) -> bool:
    """True only when one spectrum contains every requested wavelength."""
    targets = [
        safe_float(value, math.nan)
        for value in list(wavelengths or [])
    ]
    targets = [value for value in targets if math.isfinite(value)]
    if not targets:
        return bool(getattr(spectrum, "x", None))
    intervals = spectrum_wavelength_intervals(spectrum)
    return all(
        any(low <= target <= high for low, high in intervals)
        for target in targets
    )


def select_spectrum_for_wavelengths(
    app: "MainWindow",
    wavelengths,
) -> Optional[Spectrum]:
    """Select one real detector window for an analytical operation.

    In independent-window mode no samples from different files are combined.
    The Active Spectra selection wins inside an overlap; otherwise the window
    whose centre is closest to the requested line group is used.
    """
    spectra = [
        spectrum
        for spectrum in list(getattr(app, "spectra", []) or [])
        if getattr(spectrum, "visible", True) and getattr(spectrum, "x", None)
    ]
    if not spectra:
        return None
    selected = _selected_active_spectrum(app)
    targets = [
        safe_float(value, math.nan)
        for value in list(wavelengths or [])
    ]
    targets = [value for value in targets if math.isfinite(value)]
    if not bool(getattr(app, "independent_window_mode", False)):
        display_spectrum = selected or spectra[0]
        if not targets:
            return display_spectrum
        sources = tuple(getattr(display_spectrum, "source_windows", ()) or ())
        if len(sources) <= 1:
            return display_spectrum if spectrum_covers_wavelengths(display_spectrum, targets) else None

        candidates = []
        target_center = 0.5 * (min(targets) + max(targets))
        for source in sources:
            holder = Spectrum(
                [],
                [],
                name=source.name,
                filename=source.filename,
                source_windows=(source,),
            )
            try:
                if getattr(display_spectrum, "response_corrected", False):
                    candidate = app._response_corrected_copy(holder)
                else:
                    candidate = Spectrum(
                        list(source.x),
                        list(source.y),
                        name=source.name,
                        filename=source.filename,
                        dark_corrected=source.dark_corrected,
                        dark_source=source.dark_source,
                        signal_column=source.signal_column,
                        dark_columns=source.dark_columns,
                        replicate_files=tuple(getattr(source, "replicate_files", ()) or ()),
                        source_windows=(source,),
                    )
            except Exception:
                continue
            if not spectrum_covers_wavelengths(candidate, targets):
                continue
            values = [
                safe_float(value, math.nan)
                for value in list(getattr(candidate, "x", []) or [])
            ]
            values = [value for value in values if math.isfinite(value)]
            if not values:
                continue
            low, high = min(values), max(values)
            margin = min(min(targets) - low, high - max(targets))
            center_distance = abs(0.5 * (low + high) - target_center)
            candidate.color = display_spectrum.color
            candidates.append((margin, -center_distance, candidate))
        if not candidates:
            # Analytical fits must never bridge two physical detector windows.
            return None
        return max(candidates, key=lambda item: item[:-1])[-1]
    if not targets:
        return selected or spectra[0]

    candidates = [
        spectrum
        for spectrum in spectra
        if spectrum_covers_wavelengths(spectrum, targets)
    ]
    if selected is not None and selected in candidates:
        return selected
    if not candidates:
        # A fit is not allowed to bridge detector windows.
        return None

    target_center = 0.5 * (min(targets) + max(targets))

    def rank(spectrum):
        values = [
            safe_float(value, math.nan)
            for value in list(getattr(spectrum, "x", []) or [])
        ]
        values = [value for value in values if math.isfinite(value)]
        if not values:
            return (-math.inf, -math.inf)
        low, high = min(values), max(values)
        margin = min(min(targets) - low, high - max(targets))
        center_distance = abs(0.5 * (low + high) - target_center)
        return (margin, -center_distance)

    return max(candidates, key=rank)


def template_line_is_acquired(app: "MainWindow", line: TemplateLine) -> bool:
    """Use the observed/fitted line center to validate spectral coverage."""
    center = template_line_plot_wavelength(line)
    return center > 0.0 and wavelength_is_acquired(app, center)


def template_line_plot_wavelength(line: TemplateLine) -> float:
    """Return the observed Voigt center when fitted, otherwise the marked line."""
    return (
        abs(safe_float(getattr(line, "fitwavelen", 0.0), 0.0))
        or abs(safe_float(getattr(line, "wavelen", 0.0), 0.0))
        or abs(safe_float(getattr(line, "asswavelen", 0.0), 0.0))
    )


def trace_marker_has_fitted_template(app: "MainWindow", marker) -> bool:
    """Avoid drawing a NIST trace marker over its observed Voigt marker."""
    marker_species = str(
        getattr(marker, "specie", "") or ""
    ).strip().capitalize()
    marker_ion = safe_int(getattr(marker, "ion", 0), 0)
    marker_wavelength = safe_float(getattr(marker, "wavelen", 0.0), 0.0)
    unit = str(app.current_wavelength_unit_label()).strip().lower()
    tolerance = 0.02 if unit == "nm" else 0.2
    for line in getattr(app, "template_lines", []) or []:
        fit_center = abs(
            safe_float(getattr(line, "fitwavelen", 0.0), 0.0)
        )
        if fit_center <= 0.0:
            continue
        line_species = str(
            getattr(line, "specie", "") or ""
        ).strip().capitalize()
        line_ion = safe_int(getattr(line, "ion", 0), 0)
        reference = safe_float(
            getattr(line, "asswavelen", 0.0)
            or getattr(line, "wavelen", 0.0),
            0.0,
        )
        if (
            line_species == marker_species
            and line_ion == marker_ion
            and abs(reference - marker_wavelength) <= tolerance
        ):
            return True
    return False


def merged_spectrum_display_name(spectrum: Spectrum) -> str:
    count = len(getattr(spectrum, "source_windows", ()) or ())
    return f"Merged spectrum ({count} windows)" if count > 1 else spectrum.name


def discover_replicate_spectrum_files(filename: str) -> tuple[str, ...]:
    """Return validated replicate files declared beside an averaged spectrum."""
    source = Path(str(filename or ""))
    if not source.name:
        return ()
    manifest_path = source.parent / "replicates.json"
    if not manifest_path.is_file():
        return ()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if payload.get("format") != "pylibs-replicates-v1":
            return ()
        entry = (payload.get("windows") or {}).get(source.name) or {}
        relative_files = list(entry.get("replicates") or [])
        root = manifest_path.parent.resolve()
        resolved = []
        for relative in relative_files:
            candidate = (root / str(relative)).resolve()
            candidate.relative_to(root)
            if not candidate.is_file():
                return ()
            resolved.append(str(candidate))
        return tuple(resolved) if len(resolved) >= 2 else ()
    except Exception as exc:
        logging.warning(
            "Ignoring invalid replicate manifest %s: %s",
            manifest_path,
            exc,
        )
        return ()


def load_spectrum_for_open(filename: str, options: AppOptions) -> Spectrum:
    if is_roh_spectrum_file(filename) or Path(filename).suffix.lower() == ".sif":
        return _load_spectrum_for_open(filename, options, Spectrum)
    xs, columns = read_ascii_spectrum_columns(filename, options.convert_to_angstrom)
    metadata = read_ascii_metadata(filename)
    already_dark_corrected = metadata.get("pylibs_dark_corrected", "").strip().lower() in {
        "1", "true", "yes",
    }
    dark_trace = None
    if not already_dark_corrected and str(getattr(options, "dark_mode", "")).strip().lower() == "file":
        dark_file = str(getattr(options, "dark_file", "") or "").strip()
        if not dark_file:
            raise ValueError("Dark mode is 'file', but no dark file is configured.")
        dark_trace = read_ascii_spectrum(dark_file, options.convert_to_angstrom)
    if already_dark_corrected:
        corrected = subtract_dark(xs, columns, mode="none", signal_column=1)
        dark_corrected = True
        dark_source = metadata.get(
            "pylibs_dark_source", "pre-corrected by ASC averager"
        ).replace("_", " ")
    else:
        corrected = subtract_dark(
            xs,
            columns,
            mode=getattr(options, "dark_mode", "auto_columns"),
            signal_column=getattr(options, "signal_column", 0),
            dark_columns=getattr(options, "dark_columns", ""),
            constant=getattr(options, "dark_constant", 0.0),
            dark_trace=dark_trace,
        )
        dark_corrected = any(abs(value) > 0.0 for value in corrected.dark)
        dark_source = corrected.source
    return Spectrum(
        list(xs),
        corrected.intensity,
        Path(filename).name,
        filename,
        dark_corrected=dark_corrected,
        dark_source=dark_source,
        signal_column=corrected.signal_column + 1,
        dark_columns=tuple(index + 1 for index in corrected.dark_columns),
        replicate_files=discover_replicate_spectrum_files(filename),
    )


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
        self.minsize(980, 540)
        geom = legacy_geometry_to_tk(getattr(master.options, "options_geometry", ""), "1080x640")
        if geom:
            self.geometry(geom)
        self.vars: dict[str, tk.Variable] = {}
        self.choice_display_vars: dict[str, tk.StringVar] = {}
        self._response_selection_pending = False
        self._build_original_layout()
        fit_toplevel_to_content(self, min_width=980, min_height=540, max_height_fraction=0.85)
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

    def choice(self, parent, attr, labels, row, col, default, width=28, **kw):
        """Show professional labels while persisting stable option keys."""
        internal_var = self.v(attr, default)
        key = _option_key_from_label(labels, internal_var.get(), default)
        internal_var.set(key)
        display_var = tk.StringVar(value=labels[key])
        self.choice_display_vars[attr] = display_var

        def update_internal(*_args):
            selected = _option_key_from_label(labels, display_var.get(), default)
            if internal_var.get() != selected:
                internal_var.set(selected)

        def update_display(*_args):
            selected = _option_key_from_label(labels, internal_var.get(), default)
            label = labels[selected]
            if display_var.get() != label:
                display_var.set(label)

        display_var.trace_add("write", update_internal)
        internal_var.trace_add("write", update_display)
        combo = ttk.Combobox(
            parent,
            textvariable=display_var,
            values=tuple(labels.values()),
            width=width,
            state="readonly",
        )
        combo.grid(
            row=row,
            column=col,
            columnspan=kw.get("colspan", 1),
            padx=kw.get("padx", 3),
            pady=kw.get("pady", 3),
            sticky=kw.get("sticky", "w"),
        )
        return combo

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

        g_ha = self.group(left, "Hα Parameters", 3, 0)
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
        self.check(
            g_ha,
            "remember_ne_for_series",
            "Keep active Ne after Clear Graph (measurement series)",
            3,
            0,
            colspan=6,
        )

        g_dark = self.group(left, "Dark-signal subtraction", 4, 0)
        ttk.Label(g_dark, text="Mode").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.choice(
            g_dark,
            "dark_mode",
            _DARK_SUBTRACTION_LABELS,
            0,
            1,
            "auto_columns",
            width=31,
            colspan=2,
        )
        ttk.Label(g_dark, text="Signal col. (0=auto)").grid(row=1, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_dark, "signal_column", 1, 1, width=7)
        ttk.Label(g_dark, text="Dark cols.").grid(row=2, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_dark, "dark_columns", 2, 1, width=12)
        ttk.Label(g_dark, text="Constant").grid(row=3, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_dark, "dark_constant", 3, 1, width=12)
        self.entry(g_dark, "dark_file", 4, 0, width=24, colspan=2, sticky="ew")
        ttk.Button(g_dark, text="Dark file...", command=self.browse_dark).grid(row=4, column=2, padx=3, pady=3)

        g_wave = self.group(mid, "Wavelength Limits", 0, 0)
        ttk.Label(g_wave, text="From:").grid(row=0, column=0, padx=4)
        self.entry(g_wave, "limit_low", 0, 1, width=8)
        ttk.Label(g_wave, text="To:").grid(row=0, column=2, padx=14)
        self.entry(g_wave, "limit_high", 0, 3, width=8)

        g_temp = self.group(mid, "Temperature Range", 1, 0)
        self.entry(g_temp, "kt_low", 0, 0, width=8)
        ttk.Label(g_temp, text="<  kT  <").grid(row=0, column=1, padx=14)
        self.entry(g_temp, "kt_high", 0, 2, width=8)

        g_ne = self.group(mid, "Electron Density Range", 2, 0)
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
        self.check(g_corr, "apply_response", "Instrument response", 0, 0)
        response_paths = parse_response_paths(
            getattr(self.master_app.options, "response_files", "")
            or getattr(self.master_app.options, "response_file", "")
        )
        self.v("response_file", response_paths[0] if response_paths else "")
        self.v("response_files", serialize_response_paths(response_paths))
        self.response_summary_var = tk.StringVar()
        self._set_response_summary(response_paths)
        ttk.Label(g_corr, textvariable=self.response_summary_var, width=30).grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ttk.Button(g_corr, text="Load files...", command=self.browse_response).grid(row=0, column=2, padx=4, pady=4)

        g_global = self.group(mid, "Global Correction", 5, 0)
        ttk.Radiobutton(g_global, text="Apply Before", variable=self.v("global_correction_mode", "after"), value="before",
                        command=lambda: self._set_global_mode("before")).grid(row=0, column=0, padx=8, pady=5, sticky="w")
        ttk.Radiobutton(g_global, text="Apply After", variable=self.vars["global_correction_mode"], value="after",
                        command=lambda: self._set_global_mode("after")).grid(row=0, column=1, padx=8, pady=5, sticky="w")
        self.vars["global_correction_mode"].set("before" if self.master_app.options.apply_before else "after")

        g_quality = self.group(mid, "Quantitative validation", 6, 0)
        self.check(
            g_quality,
            "strict_quantitation",
            "Suppress composition results that fail validation",
            0,
            0,
            colspan=4,
        )
        ttk.Label(g_quality, text="Temperature: minimum lines / levels").grid(row=1, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_min_temperature_lines", 1, 1, width=5)
        self.entry(g_quality, "quality_min_temperature_levels", 1, 2, width=5)
        ttk.Label(g_quality, text="Temperature: minimum ΔEk / R²").grid(row=2, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_min_energy_span_ev", 2, 1, width=5)
        self.entry(g_quality, "quality_min_temperature_r2", 2, 2, width=5)
        ttk.Label(g_quality, text="Temperature: maximum slope error / LOO").grid(row=3, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_max_relative_slope_error", 3, 1, width=5)
        self.entry(g_quality, "quality_max_loo_relative_span", 3, 2, width=5)
        ttk.Label(g_quality, text="Max line spread / stage balance").grid(row=4, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_max_line_population_factor", 4, 1, width=5)
        self.entry(g_quality, "quality_max_stage_balance_factor", 4, 2, width=5)
        ttk.Label(g_quality, text="H-alpha: min R2 / SNR").grid(row=5, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_min_halpha_r2", 5, 1, width=5)
        self.entry(g_quality, "quality_min_halpha_snr", 5, 2, width=5)
        ttk.Label(g_quality, text="McWhirter margin / min observed fraction").grid(row=6, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_min_mcwhirter_margin", 6, 1, width=5)
        self.entry(g_quality, "quality_min_observed_stage_fraction", 6, 2, width=5)
        ttk.Label(g_quality, text="Max relative Ne uncertainty").grid(row=7, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_max_ne_relative_uncertainty", 7, 1, width=5)
        ttk.Label(g_quality, text="Replicate Voigt-area CV warning").grid(row=8, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_max_replicate_area_cv", 8, 1, width=5)
        ttk.Label(g_quality, text="Composition: min lines / max LOO").grid(row=9, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_min_composition_lines", 9, 1, width=5)
        self.entry(g_quality, "quality_max_composition_loo_relative_change", 9, 2, width=5)
        ttk.Label(g_quality, text="Composition: max replicate CV / T-Ne shift").grid(row=10, column=0, padx=4, pady=2, sticky="w")
        self.entry(g_quality, "quality_max_replicate_composition_cv", 10, 1, width=5)
        self.entry(g_quality, "quality_max_parameter_composition_relative_change", 10, 2, width=5)
        self.check(
            g_quality,
            "quality_require_replicate_composition",
            "Require replicate-composition audit",
            11,
            0,
            colspan=4,
        )

        g_fit = self.group(right, "Data Fit", 0, 0)
        ttk.Label(g_fit, text="Voigt baseline model").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.choice(
            g_fit,
            "voigt_baseline_mode",
            _VOIGT_BASELINE_LABELS,
            0,
            1,
            "local_linear",
            width=33,
        )
        self.check(g_fit, "fix_wg", "Fix wg:", 1, 0)
        self.entry(g_fit, "fixed_wg", 1, 1, width=7)
        self.check(g_fit, "fix_wl", "Fix wl:", 2, 0)
        self.entry(g_fit, "fixed_wl", 2, 1, width=7)
        self.check(g_fit, "fix_wavelength", "Fix wavelength", 3, 0, colspan=2)
        ttk.Label(g_fit, text="Iterations").grid(row=4, column=0, padx=4, sticky="w")
        self.entry(g_fit, "iterations", 4, 1, width=7)
        ttk.Label(g_fit, text="Instr. FWHM @ H-alpha").grid(row=5, column=0, padx=4, sticky="w")
        self.entry(g_fit, "instrumental_width", 5, 1, width=7)
        self.check(g_fit, "echelle", "Echelle", 6, 0, colspan=2)

        g_aki = self.group(right, "Boltzmann analysis", 1, 0)
        ttk.Label(g_aki, text="Intensity convention").grid(row=0, column=0, padx=3, pady=3, sticky="w")
        self.choice(
            g_aki,
            "boltzmann_intensity_mode",
            _BOLTZMANN_INTENSITY_LABELS,
            1,
            0,
            ENERGY_INTENSITY_MODE,
            width=41,
            colspan=2,
        )
        ttk.Label(g_aki, text="Aki threshold").grid(row=2, column=0, padx=3, pady=(5, 2), sticky="w")
        self.entry(g_aki, "aki_threshold", 2, 1, width=9)
        ttk.Label(g_aki, text="Theory Aki threshold").grid(row=3, column=0, padx=3, pady=(5, 2), sticky="w")
        self.entry(g_aki, "theoretical_aki_threshold", 3, 1, width=9)

        g_shift = self.group(right, "Wavelength calibration", 2, 0)
        ttk.Label(g_shift, text="Legacy global Δλ").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_shift, "auto_shift", 0, 1, width=8)
        self.check(
            g_shift,
            "auto_wavelength_calibration",
            "Use saved per-window calibration",
            1,
            0,
            colspan=2,
        )
        ttk.Button(
            g_shift,
            text="Per-window calibration...",
            command=self.master_app.show_wavelength_calibration,
        ).grid(row=2, column=0, columnspan=2, padx=4, pady=4, sticky="ew")

        g_db = self.group(right, "Atomic library", 3, 0)
        self.entry(g_db, "libs_db_file", 0, 0, width=31, sticky="ew")
        ttk.Button(g_db, text="Browse...", command=self.browse_database).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(g_db, text="LIBS++", command=lambda: self.use_bundled_database("LIBS.db")).grid(row=1, column=0, padx=3, pady=3, sticky="w")
        ttk.Button(g_db, text="NIST ASD 5.12", command=lambda: self.use_bundled_database("LIBS_NIST_5_12.db")).grid(row=1, column=1, padx=3, pady=3, sticky="e")

        g_sa = self.group(right, "Self-absorption correction", 4, 0)
        ttk.Label(g_sa, text="Mode").grid(row=0, column=0, padx=4, pady=3, sticky="w")
        self.choice(
            g_sa,
            "irsac_mode",
            _SELF_ABSORPTION_MODE_LABELS,
            0,
            1,
            "hybrid",
            width=39,
        )
        ttk.Label(g_sa, text="Thermometric species").grid(row=1, column=0, padx=4, pady=3, sticky="w")
        self.entry(g_sa, "irsac_thermometric_species", 1, 1, width=14)
        ttk.Label(
            g_sa,
            text="IRSAC: raw T -> correct reference species -> freeze corrected T",
        ).grid(row=2, column=0, columnspan=2, padx=4, pady=3, sticky="w")

    def _set_global_mode(self, mode):
        self.vars["apply_before"].set(mode == "before") if "apply_before" in self.vars else None
        self.vars["apply_after"].set(mode == "after") if "apply_after" in self.vars else None

    def browse_response(self):
        initial = remembered_initial_dir(self.master_app.options)
        filenames = filedialog.askopenfilenames(
            title="One instrumental-response file per spectral window",
            initialdir=initial,
            filetypes=[("Instrument response / OPC", "*.xlsx *.xlsm *.dat *.txt *.asc *.csv *.CSV *.opc"), ("All", "*.*")]
        )
        if filenames:
            paths = list(filenames)
            kind = _response_paths_kind(paths)
            if kind == "mixed":
                _showwarning(
                    self,
                    "Correction files",
                    "Do not load an OPC together with physical instrumental-response files. "
                    "An OPC already contains the line-wise composite correction.",
                )
                return
            if kind == "opc" and len(paths) != 1:
                _showwarning(self, "OPC", "Select one OPC calibration file at a time.")
                return
            remember_working_dir(self.master_app.options, paths)
            self.vars["response_file"].set(paths[0])
            self.vars["response_files"].set(serialize_response_paths(paths))
            self.vars["apply_response"].set(True)
            # An OPC is necessarily line-wise Apply After. For a physical
            # response, preserve the mode explicitly chosen by the user;
            # selecting a file must not silently reset it to Apply Before.
            if kind == "opc":
                self.vars["global_correction_mode"].set("after")
            self._response_selection_pending = True
            self._set_response_summary(paths)

    def _set_response_summary(self, paths):
        paths = parse_response_paths(paths)
        if not paths:
            text = "No response files"
        elif len(paths) == 1:
            text = Path(paths[0]).name
        else:
            text = f"{len(paths)} response files"
        self.response_summary_var.set(text)

    def browse_database(self):
        filename = filedialog.askopenfilename(
            title="Select a pyLIBS atomic library",
            initialdir=str(app_base_dir()),
            filetypes=[("pyLIBS SQLite", "*.db *.sqlite"), ("All", "*.*")],
        )
        if filename:
            self.vars["libs_db_file"].set(filename)

    def browse_dark(self):
        filename = filedialog.askopenfilename(
            title="Select a wavelength/dark two-column file",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("Spectrum files", "*.txt *.dat *.asc *.csv *.CSV"), ("All", "*.*")],
        )
        if filename:
            remember_working_dir(self.master_app.options, filename)
            self.vars["dark_file"].set(filename)
            self.vars["dark_mode"].set("file")

    def use_bundled_database(self, filename):
        path = app_base_dir() / filename
        if not path.exists():
            _showwarning(self, "Atomic library", f"Library not found:\n{path}")
            return
        self.vars["libs_db_file"].set(str(path))

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
        if _response_paths_kind(
            getattr(opts, "response_files", "") or getattr(opts, "response_file", "")
        ) == "opc":
            opts.apply_response = True
            opts.apply_before = False
            opts.apply_after = True
    def ok(self):
        old_response_files = self.master_app.configured_response_paths()
        old_database = getattr(self.master_app.options, "libs_db_file", "")
        old_boltzmann_mode = _boltzmann_intensity_mode(self.master_app)
        self.apply_to_options()
        self.invalidate_boltzmann_if_changed(old_boltzmann_mode)
        if not self.reload_response_if_changed(old_response_files):
            return
        self.master_app.sync_response_application_mode(notify=True)
        self.reload_database_if_changed(old_database)
        self.master_app.status("Options updated")
        self.close()

    def cancel(self):
        self.close()

    def close(self):
        if getattr(self.master_app, "options_window", None) is self:
            self.master_app.options_window = None
        self.destroy()

    def save(self):
        old_response_files = self.master_app.configured_response_paths()
        old_database = getattr(self.master_app.options, "libs_db_file", "")
        old_boltzmann_mode = _boltzmann_intensity_mode(self.master_app)
        self.apply_to_options()
        self.invalidate_boltzmann_if_changed(old_boltzmann_mode)
        if not self.reload_response_if_changed(old_response_files):
            return
        self.reload_database_if_changed(old_database)
        path = save_pylibs_ini(self.master_app.options)
        self.master_app.status(f"Options saved: {path}")

    def invalidate_boltzmann_if_changed(self, old_mode):
        """Clear dependent results when the intensity convention changes."""
        new_mode = _boltzmann_intensity_mode(self.master_app)
        if new_mode == old_mode:
            return
        self.master_app.last_saha_boltzmann = None
        self.master_app.session_temperature = None
        self.master_app.session_temperature_source = None
        self.master_app.invalidate_self_absorption_analysis()
        self.master_app.invalidate_cflibs_results()
        self.master_app.status(
            "Boltzmann intensity convention changed; recalculate Saha-Boltzmann."
        )

    def reload_response_if_changed(self, old_response_files):
        new_paths = self.master_app.configured_response_paths()
        if self._response_selection_pending:
            # load_response_files is the authoritative path used by the
            # Instrument response submenu. Restore the previous path first so
            # its own rollback also works when the new file is invalid.
            self.master_app.options.response_files = serialize_response_paths(old_response_files)
            self.master_app.options.response_file = old_response_files[0] if old_response_files else ""
            loaded = self.master_app.load_response_files(new_paths)
            if loaded:
                self._response_selection_pending = False
            return bool(loaded)
        if new_paths != list(old_response_files):
            silent = not new_paths
            loaded = self.master_app.load_configured_responses(silent=silent)
            if new_paths and not loaded:
                return False
            if loaded and self.master_app.options.apply_response and self.master_app.spectra:
                if _response_paths_kind(new_paths) == "opc":
                    self.master_app.invalidate_self_absorption_analysis()
                    self.master_app.invalidate_cflibs_results()
                elif self.master_app.options.apply_before:
                    self.master_app.apply_response_now()
        return True

    def reload_database_if_changed(self, old_database):
        new_database = str(getattr(self.master_app.options, "libs_db_file", "") or "")
        if new_database == str(old_database or ""):
            return
        try:
            self.master_app.activate_database(new_database)
        except Exception as exc:
            self.master_app.options.libs_db_file = str(old_database or "")
            try:
                if old_database:
                    self.master_app.activate_database(str(old_database))
            except Exception:
                pass
            _showerror(self, "Atomic library", str(exc))


class ActiveSpectraWindow(tk.Toplevel):
    """Gestione spettri attivi, da Unit13."""

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Active Spectra")
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
                _showinfo(self, "Active Spectra", "The main spectrum remains visible.")
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
            _showinfo(self, "Active Spectra", "Right-click to select at least two spectra.")
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
        self.title("Instrument response")
        self.geometry("980x620")
        top = ttk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Button(top, text="1. Load response files...", command=master.ask_load_response).pack(side="left")
        ttk.Button(top, text="2. Apply signal / response", command=master.apply_response_now).pack(side="left", padx=4)
        ttk.Button(top, text="Global width @ 656 nm...", command=self.set_global_instrumental_width).pack(side="left", padx=4)
        ttk.Button(top, text="Remove responses", command=master.clear_response_library).pack(side="left", padx=4)
        add_context_help_button(
            top,
            self,
            "Instrument response",
            (
                "The correction curve adjusts detector sensitivity: corrected signal = signal / response.\n\n"
                "It does not measure instrumental line width. The global Gaussian FWHM is measured near "
                "H-alpha and may be applied to every spectral window as an explicit approximation."
            ),
        ).pack(side="right")
        self.info_var = tk.StringVar(value="Load one radiometric-response file for each spectral window.")
        ttk.Label(self, textvariable=self.info_var).pack(
            fill="x", padx=8, pady=(0, 4)
        )
        columns = ("file", "range", "assigned")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=6)
        self.tree.heading("file", text="Response file")
        self.tree.heading("range", text="Wavelength range")
        self.tree.heading("assigned", text="Matched window(s)")
        self.tree.column("file", width=250)
        self.tree.column("range", width=180, anchor="center")
        self.tree.column("assigned", width=430)
        self.tree.pack(fill="x", padx=6, pady=(0, 5))
        if Figure is None:
            ttk.Label(self, text="Matplotlib is not available.").pack(pady=30)
            self.ax = self.canvas = None
            return
        self.fig = Figure(figsize=(7,4), dpi=_figure_dpi(self))
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
        self.tree.delete(*self.tree.get_children())
        library = getattr(self.master_app, "response_library", InstrumentResponseLibrary())
        assignments = defaultdict(list)
        for spectrum in getattr(self.master_app, "spectra", []):
            sources = spectrum.source_windows or (
                SpectrumSourceWindow(tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename),
            )
            for source in sources:
                curve = library.best_for(source.name, source.x)
                if curve is not None:
                    assignments[curve.filename].append(source.name)
        for index, curve in enumerate(library.curves):
            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    curve.name,
                    f"{curve.minimum:.3f} - {curve.maximum:.3f}",
                    ", ".join(assignments.get(curve.filename, [])) or "not matched",
                ),
            )
            self.ax.plot(curve.x, curve.y, linewidth=0.9, label=curve.name)
        if library.curves:
            self.ax.legend(loc="best", fontsize=8)
        if library.curves:
            width = max(0.0, safe_float(getattr(self.master_app.options, "instrumental_width", 0.0), 0.0))
            width_text = (
                f"Global instrumental FWHM @ H-alpha: {width:.6g} {self.master_app.current_wavelength_unit_label()}."
                if width > 0.0
                else "Instrumental broadening is not configured; no width deconvolution is applied."
            )
            self.info_var.set(
                f"{len(library.curves)} instrument-response curve(s). Correction: signal / response. "
                f"{width_text}"
            )
        else:
            self.info_var.set("No radiometric-response curves loaded.")
        self.canvas.draw_idle()

    def set_global_instrumental_width(self):
        initial = max(0.0, safe_float(getattr(self.master_app.options, "instrumental_width", 0.0), 0.0))
        unit = self.master_app.current_wavelength_unit_label()
        value = simpledialog.askfloat(
            "Global instrumental broadening at H-alpha",
            (
                f"Instrumental Gaussian FWHM measured near H-alpha, 656 nm ({unit}).\n\n"
                "This one value will be applied unchanged to every spectral window and every theoretical line. "
                "Use the instrument-only contribution, not the total plasma H-alpha width dominated by Stark broadening.\n\n"
                "Enter 0 only if the instrumental width is unknown:"
            ),
            initialvalue=initial,
            minvalue=0.0,
            parent=_prepare_messagebox_parent(self),
        )
        if value is None:
            return
        self.master_app.options.instrumental_width = float(value)
        save_pylibs_ini(self.master_app.options)
        self.redraw()
        if value > 0.0:
            self.master_app.status(f"Global instrumental FWHM @ H-alpha: {value:.6g} {unit}")
        else:
            self.master_app.status("Instrumental-width deconvolution disabled")


class TemplateManager(tk.Toplevel):
    columns = ("wavelen", "specie", "ion", "asswavelen", "inte", "ei", "ek", "aki", "gk", "gi", "acc", "wg", "wl", "fitwavelen")
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Analytical-Line Manager")
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
                wavelength_unit = getattr(
                    self.master_app, "wavelength_unit", "angstrom"
                )
                res=self.master_app.libs_db.search_lines(
                    wave,
                    rg,
                    table=self.db_table_var.get(),
                    limit=1000,
                    wavelength_unit=wavelength_unit,
                )
                res=[
                    self.master_app.libs_db.enrich_line_from_element_table(
                        l,
                        tolerance=max(0.02, rg),
                        wavelength_unit=wavelength_unit,
                    )
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
        self.title("Element Locator")
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


def remove_traced_elements(app, elements) -> tuple[int, int]:
    """Remove elements from the active analysis without deleting measured fits."""
    normalized = {
        str(element or "").strip().capitalize()
        for element in elements
        if str(element or "").strip()
    }
    if not normalized:
        return 0, 0

    markers = list(getattr(app, "trace_markers", []) or [])
    kept_markers = [
        marker
        for marker in markers
        if str(getattr(marker, "specie", "") or "").strip().capitalize()
        not in normalized
    ]
    app.trace_markers = kept_markers

    selected = set(getattr(app, "analysis_elements", set()) or set())
    selected.difference_update(normalized)
    app.analysis_elements = selected

    cleared_assignments = 0
    for line in getattr(app, "template_lines", []) or []:
        species = str(getattr(line, "specie", "") or "").strip().capitalize()
        if species not in normalized:
            continue
        line.specie = ""
        line.ion = 0
        line.asswavelen = 0.0
        line.ei = 0.0
        line.ek = 0.0
        line.acc = 0
        line.aki = 0.0
        line.gk = 0
        line.gi = 0
        cleared_assignments += 1
    return len(markers) - len(kept_markers), cleared_assignments


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
        species_entry = ttk.Entry(top, textvariable=self.species_var, width=10)
        species_entry.grid(row=0, column=1, sticky="w", padx=3)
        self.mode_var = tk.StringVar(value="Both")
        ttk.Label(top, text="Mode").grid(row=0, column=2, sticky="w", padx=(8, 2))
        for c, mode in enumerate(("I", "II", "Both", "All"), start=3):
            ttk.Radiobutton(top, text=mode, variable=self.mode_var, value=mode).grid(row=0, column=c, padx=3)
        ttk.Label(top, text="Max Lines (all mode)").grid(row=0, column=7, sticky="w", padx=(16,3))
        self.max_var = tk.StringVar(value="5")
        ttk.Entry(top, textvariable=self.max_var, width=7).grid(row=0, column=8, sticky="w", padx=3)
        ttk.Button(top, text="OK", command=self.trace).grid(row=0, column=9, padx=8)
        ttk.Button(top, text="Assign", command=self.assign).grid(row=0, column=10, padx=3)
        ttk.Button(top, text="Clear", command=self.clear).grid(row=0, column=11, padx=3)
        add_context_help_button(
            top,
            self,
            "Trace Lines",
            (
                "By default, the selected element is matched only to observed peaks already selected in the spectrum. "
                "Disable 'Only near selected peaks' to browse all compatible database lines.\n\n"
                "Assign transfers the displayed identifications to the analytical-line list."
            ),
        ).grid(row=0, column=12, padx=(8, 3))
        self.selected_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top,
            text="Only near selected peaks",
            variable=self.selected_only_var,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=3, pady=(5, 0))
        ttk.Label(top, text="Tolerance").grid(
            row=1, column=4, sticky="e", padx=(8, 2), pady=(5, 0)
        )
        default_tolerance = (
            0.10
            if master.current_wavelength_unit_label() == "nm"
            else 1.0
        )
        self.tolerance_var = tk.StringVar(value=f"{default_tolerance:g}")
        ttk.Entry(top, textvariable=self.tolerance_var, width=7).grid(
            row=1, column=5, sticky="w", padx=3, pady=(5, 0)
        )
        ttk.Label(
            top, text=master.current_wavelength_unit_label()
        ).grid(row=1, column=6, sticky="w", pady=(5, 0))
        self.info_var = tk.StringVar(value="")
        tree_frame = ttk.Frame(self)
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings")
        for c in self.columns:
            self.tree.heading(c, text=c); self.tree.column(c, width=72, anchor="center")
        self.tree.pack(fill="both", expand=True)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.tree.bind("<Delete>", self.delete_selected_elements)
        species_entry.bind("<Double-Button-1>", lambda event: self.trace())
        ttk.Button(
            top,
            text="Remove element (Del)",
            command=self.delete_selected_elements,
        ).grid(row=1, column=8, columnspan=4, sticky="e", padx=3, pady=(5, 0))
        ttk.Label(top, textvariable=self.info_var).grid(
            row=2, column=0, columnspan=13, sticky="w", padx=3, pady=(5, 0)
        )
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
        wavelength_unit = getattr(self.master_app, "wavelength_unit", "angstrom")
        ions = [1] if mode == "I" else [2] if mode == "II" else [1, 2]
        selected_only = bool(self.selected_only_var.get())
        selected_wavelengths = []
        if selected_only:
            for selected_line in self.master_app.template_lines:
                if _template_line_has_fit_error(selected_line):
                    continue
                selected_species = str(
                    getattr(selected_line, "specie", "") or ""
                ).strip().capitalize()
                if selected_species and selected_species != element:
                    continue
                fitted = abs(
                    safe_float(
                        getattr(selected_line, "fitwavelen", 0.0), 0.0
                    )
                )
                wavelength = fitted or safe_float(
                    getattr(selected_line, "wavelen", 0.0), 0.0
                )
                if min(lo, hi) <= wavelength <= max(lo, hi):
                    selected_wavelengths.append(wavelength)
            if not selected_wavelengths:
                self.info_var.set(
                    "No selected observed peak is inside the visible interval."
                )
                return
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            if selected_only:
                tolerance = max(
                    0.0,
                    safe_float(
                        self.tolerance_var.get(),
                        0.10 if wavelength_unit == "nm" else 1.0,
                    ),
                )
                lines = self.master_app.libs_db.match_selected_lines(
                    element,
                    selected_wavelengths,
                    tolerance,
                    ions=ions,
                    wavelength_unit=wavelength_unit,
                )
            elif mode == "I":
                lines = self.master_app.libs_db.trace_lines(
                    element, lo, hi, ions=[1], max_lines=maxn,
                    table="Datalibs", wavelength_unit=wavelength_unit,
                )
            elif mode == "II":
                lines = self.master_app.libs_db.trace_lines(
                    element, lo, hi, ions=[2], max_lines=maxn,
                    table="Datalibs", wavelength_unit=wavelength_unit,
                )
            elif mode == "All":
                lines = self.master_app.libs_db.trace_lines(
                    element, lo, hi, ions=[1, 2], max_lines=maxn,
                    table="Datalibs", wavelength_unit=wavelength_unit,
                )
            else:
                lines = (
                    self.master_app.libs_db.trace_lines(
                        element, lo, hi, ions=[1], max_lines=maxn,
                        table="Datalibs", wavelength_unit=wavelength_unit,
                    ) +
                    self.master_app.libs_db.trace_lines(
                        element, lo, hi, ions=[2], max_lines=maxn,
                        table="Datalibs", wavelength_unit=wavelength_unit,
                    )
                )
            # Enrich each traced line with complete transition data when available.
            enriched = []
            for l in lines:
                try:
                    enriched.append(
                        self.master_app.libs_db.enrich_line_from_element_table(
                            l,
                            tolerance=0.005 if wavelength_unit == "nm" else 0.05,
                            wavelength_unit=wavelength_unit,
                        )
                    )
                except Exception:
                    enriched.append(l)
            lines = [
                line
                for line in enriched
                if wavelength_is_acquired(self.master_app, line.wavelen)
            ]
        except Exception as e:
            _showerror(self, "Trace Lines", str(e))
            return
        # Repeated Trace calls accumulate
        existing = getattr(self.master_app, "trace_markers", [])
        if selected_only:
            existing = [
                marker
                for marker in existing
                if not (
                    str(getattr(marker, "specie", "")).strip().capitalize()
                    == element
                    and safe_int(getattr(marker, "ion", 0), 0) in ions
                )
            ]
        for l in lines:
            if not any(abs(t.wavelen-l.wavelen) < 1e-6 and t.specie == l.specie and t.ion == l.ion for t in existing):
                existing.append(l)
        existing.sort(key=lambda x: x.wavelen)
        self.master_app.trace_markers = existing
        if lines:
            selected = getattr(self.master_app, "analysis_elements", None)
            if selected is None:
                selected = set()
                self.master_app.analysis_elements = selected
            selected.add(element)
            self.master_app.last_saha_boltzmann = None
            invalidate_self_absorption_analysis(self.master_app)
            self.master_app.invalidate_cflibs_results()
        self.refresh()
        self.master_app.redraw(preserve_view=True)
        self.master_app.restore_plot_view(view_xlim, view_ylim)
        unit_label = self.master_app.current_wavelength_unit_label()
        if selected_only:
            self.info_var.set(
                f"Matched {len(lines)} {element} candidate(s) to "
                f"{len(selected_wavelengths)} selected peak(s) within "
                f"+/-{tolerance:g} {unit_label}; total traced lines: "
                f"{len(existing)}."
            )
        else:
            self.info_var.set(
                f"Traced {len(lines)} {element} lines ({mode}) in the visible "
                f"interval {min(lo,hi):.2f}-{max(lo,hi):.2f} {unit_label}; "
                f"total traced lines: {len(existing)}."
            )
        self.master_app.status(self.info_var.get())

    def assign(self):
        n = self.master_app.assign_traced_lines()
        self.refresh()
        self.info_var.set(
            f"Assign: {n} analytical lines assigned within Range = "
            f"{self.master_app.options.search_range} "
            f"{self.master_app.current_wavelength_unit_label()}."
        )

    def _on_tree_double_click(self, event=None):
        item = self.tree.identify_row(event.y) if event else self.tree.focus()
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        values = self.tree.item(item, "values")
        if not values:
            return
        wavelength = safe_float(values[0], None)
        if wavelength is None:
            return
        self.master_app.goto_wavelength(wavelength)

    def delete_selected_elements(self, event=None):
        selected = list(self.tree.selection())
        if not selected:
            focused = self.tree.focus()
            if focused:
                selected = [focused]
        elements = {
            str(self.tree.item(item, "values")[1] or "").strip().capitalize()
            for item in selected
            if self.tree.item(item, "values")
        }
        elements.discard("")
        if not elements:
            self.info_var.set(
                "Select any row of the element to remove, then press Del."
            )
            return "break"

        removed_markers, cleared_assignments = remove_traced_elements(
            self.master_app,
            elements,
        )
        self.master_app.last_saha_boltzmann = None
        self.master_app.notify_template_changed(redraw=False)
        self.refresh()
        self.master_app.redraw(preserve_view=True)
        element_text = ", ".join(sorted(elements))
        self.info_var.set(
            f"Removed {element_text}: {removed_markers} traced line(s); "
            f"{cleared_assignments} analytical assignment(s) reset. "
            "Observed peaks and Voigt fits were preserved."
        )
        self.master_app.status(self.info_var.get())
        return "break"

    def clear(self):
        self.master_app.trace_markers = []
        self.master_app.analysis_elements = set()
        self.master_app.last_saha_boltzmann = None
        invalidate_self_absorption_analysis(self.master_app)
        self.master_app.invalidate_cflibs_results()
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
        self.title("Automatic Element Identification")
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
            _showinfo(self, "Automatic Element Identification", "No analytical line is available in the current range.")
            return
        scores: dict[str, float] = {}
        nls=0.0
        wavelength_unit = getattr(self.master_app, "wavelength_unit", "angstrom")
        for freq, imeas in candidates:
            lines=self.master_app.libs_db.search_lines(
                freq,
                rg,
                table="Datalibs",
                limit=200,
                wavelength_unit=wavelength_unit,
            )
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
                    t.wavelen,
                    rg,
                    table="Datalibs",
                    element=element,
                    ion=ion,
                    limit=1,
                    wavelength_unit=getattr(
                        self.master_app, "wavelength_unit", "angstrom"
                    ),
                )
                if lines:
                    self.master_app.assign_atomic_line_to_nearest_template(lines[0], redraw=False)
                    assigned+=1
        self.master_app.redraw()
        self.master_app.status(f"Automatic element identification: {assigned} line assignments")


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
        ttk.Button(top,text="MultiFit",command=self.multi_fit).pack(side="left", padx=3)
        ttk.Button(top,text="Join",command=self.join_pairs).pack(side="left", padx=3)
        ttk.Button(top,text="Average",command=self.average_files).pack(side="left", padx=3)
        ttk.Button(top,text="Convert Andor SIF to ASCII XY",command=self.convert_sif_to_ascii).pack(side="left", padx=3)
        self.calculate_sd = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Calculate SD", variable=self.calculate_sd).pack(side="left", padx=3)

        bottom=ttk.Frame(self); bottom.pack(fill="x", padx=6, pady=3)
        ttk.Button(bottom,text="Load List",command=self.load_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Clear List",command=self.clear_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Save List",command=self.save_list).pack(side="left", padx=3)
        ttk.Button(bottom,text="Convert CSV to ASCII XY",command=self.convert_csv_to_ascii).pack(side="left", padx=3)
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

    def convert_sif_to_ascii(self):
        filenames = filedialog.askopenfilenames(
            parent=self,
            title="Select Andor SIF files",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("Andor SIF files", "*.sif *.SIF"), ("All files", "*.*")],
        )
        if not filenames:
            return
        output_directory = filedialog.askdirectory(
            parent=self,
            title="Choose output directory for ASCII XY files",
            initialdir=remembered_initial_dir(self.master_app.options),
            mustexist=True,
        )
        if not output_directory:
            return
        remember_working_dir(self.master_app.options, output_directory)
        converted, failed = convert_sif_batch(filenames, output_directory)
        summary = f"Converted {len(converted)} of {len(filenames)} SIF file(s)."
        if failed:
            details = "\n".join(f"{source.name}: {error}" for source, error in failed[:12])
            if len(failed) > 12:
                details += f"\n…and {len(failed) - 12} more error(s)."
            _showwarning(self, "Convert Andor SIF to ASCII XY", summary + "\n\nFailed:\n" + details)
        else:
            _showinfo(self, "Convert Andor SIF to ASCII XY", summary)
        self.master_app.status(summary)

    def convert_csv_to_ascii(self):
        filenames = filedialog.askopenfilenames(
            parent=self,
            title="Select CSV spectrum files",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("CSV files", "*.csv *.CSV"), ("All files", "*.*")],
        )
        if not filenames:
            return
        output_directory = filedialog.askdirectory(
            parent=self,
            title="Choose output directory for ASCII XY files",
            initialdir=remembered_initial_dir(self.master_app.options),
            mustexist=True,
        )
        if not output_directory:
            return
        remember_working_dir(self.master_app.options, output_directory)
        converted, failed = convert_csv_batch(filenames, output_directory)
        summary = f"Converted {len(converted)} of {len(filenames)} CSV file(s)."
        if failed:
            details = "\n".join(f"{source.name}: {error}" for source, error in failed[:12])
            if len(failed) > 12:
                details += f"\n…and {len(failed) - 12} more error(s)."
            _showwarning(self, "Convert CSV to ASCII XY", summary + "\n\nFailed:\n" + details)
        else:
            _showinfo(self, "Convert CSV to ASCII XY", summary)
        self.master_app.status(summary)

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

    def _ask_multifit_save_path(self):
        try:
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
        except Exception:
            pass
        try:
            fn = filedialog.asksaveasfilename(
                parent=self,
                title="Save MultiFit Results",
                initialdir=remembered_initial_dir(self.master_app.options),
                defaultextension=".xlsx",
                filetypes=[("Excel workbook", "*.xlsx"), ("All Files", "*.*")],
            )
        finally:
            try:
                self.attributes("-topmost", False)
            except Exception:
                pass
        return fn

    def _pump_ui(self):
        for widget in (self.master_app, self):
            try:
                widget.update_idletasks()
            except Exception:
                pass
            try:
                widget.update()
            except Exception:
                pass

    def _fit_multifit_single_row(self, fit_window, template_row):
        original_template_lines = list(getattr(self.master_app, "template_lines", []) or [])
        row_clone = _clone_template_line(template_row)
        try:
            self.master_app.template_lines = [row_clone]
            try:
                self.master_app.notify_template_changed(redraw=False)
            except Exception:
                pass
            wave = safe_float(getattr(row_clone, "fitwavelen", 0.0), 0.0) or safe_float(getattr(row_clone, "wavelen", 0.0), 0.0)
            if wave:
                try:
                    self.master_app.zoom_around(wave)
                except Exception:
                    pass
            self._pump_ui()
            try:
                fit_window.refresh_content()
            except Exception:
                pass
            self._pump_ui()
            ok, _fit_lines = fit_window._fit_current_visible_window(
                "Single Fit",
                allow_previous_visible_fallback=False,
                show_errors=False,
            )
            self._pump_ui()
            if not ok:
                return {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
            inte = getattr(row_clone, "inte", None)
            wg = getattr(row_clone, "wg", None)
            wl = getattr(row_clone, "wl", None)
            if any(value in (None, "", "ERROR") for value in (inte, wg, wl)):
                return {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
            return {"Inte": inte, "wg": wg, "wl": wl}
        except Exception:
            return {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
        finally:
            self.master_app.template_lines = original_template_lines
            try:
                self.master_app.notify_template_changed(redraw=False)
            except Exception:
                pass

    def _load_spectrum(self, filename):
        return self.master_app.load_spectrum_with_corrections(filename)

    def _write_multifit_workbook(self, filename, files, template_lines, results_by_file):
        if Workbook is None:
            raise RuntimeError("openpyxl is not available")
        wb = Workbook()
        default = wb.active
        wb.remove(default)
        used_names = set()
        for idx, line in enumerate(template_lines):
            ws = wb.create_sheet(title=_excel_safe_sheet_name(_multifit_sheet_base_name(line, idx), used_names))
            ws.append(["Nome del file", "Inte", "wg", "wl", "Mean(X)*Mean(Y)", "Inte/(Mean(X)*Mean(Y))"])
            for fn in files:
                file_results = results_by_file.get(fn, {})
                row = file_results.get(idx, {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"})
                spectrum_integral = file_results.get("spectrum_integral", "ERROR")
                normalized_inte = _multifit_normalized_inte(row.get("Inte", ""), spectrum_integral)
                normalized_cell_value = normalized_inte if isinstance(normalized_inte, (int, float)) else normalized_inte
                values = [
                    Path(fn).name,
                    _format_excel_fit_value(row.get("Inte", "")),
                    _format_excel_fit_value(row.get("wg", "")),
                    _format_excel_fit_value(row.get("wl", "")),
                    _format_excel_fit_value(spectrum_integral),
                    normalized_cell_value,
                ]
                ws.append(values)
                row_num = ws.max_row
                for col_idx in (2, 3, 4, 5):
                    cell = ws.cell(row=row_num, column=col_idx)
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "0.###"
                norm_cell = ws.cell(row=row_num, column=6)
                if isinstance(norm_cell.value, (int, float)):
                    norm_cell.number_format = "0.000E+00"
            ws.freeze_panes = "A2"
        wb.save(filename)

    def multi_fit(self):
        files = self.paths()
        if len(files) == 0:
            self.master_app.status("MultiFit: no files loaded")
            _showinfo(self, "MultiFit", "Load at least one file in Batch Tools.")
            return
        template_lines = list(getattr(self.master_app, "template_lines", []) or [])
        if not template_lines:
            self.master_app.status("MultiFit: no analytical lines")
            _showinfo(self, "MultiFit", "Load an analytical-line list before running MultiFit.")
            return
        if Workbook is None:
            _showerror(self, "MultiFit", "openpyxl is not available.")
            return

        fit_window = None
        original_spectra = list(getattr(self.master_app, "spectra", []) or [])
        original_fit_overlay = getattr(self.master_app, "fit_overlay", None)
        original_template_lines = list(getattr(self.master_app, "template_lines", []) or [])
        results_by_file = {}
        load_errors = []
        spectrum_integrals_by_file = {}
        total = len(files)
        try:
            try:
                fit_window = RetroFitManagerWindow(self.master_app, single=True)
                try:
                    fit_window.withdraw()
                except Exception:
                    pass
            except Exception:
                fit_window = None

            for file_index, fn in enumerate(files, start=1):
                self.master_app.status(f"MultiFit: loading {file_index}/{total} {Path(fn).name}")
                self._pump_ui()
                try:
                    spectrum = self._load_spectrum(fn)
                except Exception as e:
                    load_errors.append(f"{Path(fn).name}: {e}")
                    spectrum_integrals_by_file[fn] = "ERROR"
                    results_by_file[fn] = {
                        idx: {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
                        for idx in range(len(template_lines))
                    }
                    continue

                try:
                    assign_default_spectrum_color(spectrum, 0)
                except Exception:
                    pass
                self.master_app.spectra = [spectrum]
                self.master_app.fit_overlay = None
                try:
                    self.master_app.redraw(preserve_view=False)
                except Exception:
                    pass
                self._pump_ui()

                spectrum_integrals_by_file[fn] = _multifit_spectrum_integral(spectrum)

                file_results = {}
                for row_index, template_row in enumerate(original_template_lines):
                    wave = safe_float(getattr(template_row, "fitwavelen", 0.0), 0.0) or safe_float(getattr(template_row, "wavelen", 0.0), 0.0)
                    self.master_app.status(
                        f"MultiFit: {Path(fn).name} -> row {row_index + 1}/{len(original_template_lines)}"
                        + (f" ({wave:.4f})" if wave else "")
                    )
                    self._pump_ui()
                    if fit_window is None:
                        file_results[row_index] = {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
                        continue
                    file_results[row_index] = self._fit_multifit_single_row(fit_window, template_row)
                    self._pump_ui()

                results_by_file[fn] = file_results or {
                    idx: {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
                    for idx in range(len(template_lines))
                }
                results_by_file[fn]["spectrum_integral"] = spectrum_integrals_by_file.get(fn, "ERROR")

                self.master_app.spectra = []
                self.master_app.fit_overlay = None
                try:
                    self.master_app.clear_fit_artists()
                except Exception:
                    pass
                try:
                    self.master_app.redraw(preserve_view=False)
                except Exception:
                    pass
                self._pump_ui()
        finally:
            if fit_window is not None:
                try:
                    fit_window.destroy()
                except Exception:
                    pass
            self.master_app.spectra = original_spectra
            self.master_app.template_lines = original_template_lines
            self.master_app.fit_overlay = original_fit_overlay
            try:
                self.master_app.notify_template_changed(redraw=False)
            except Exception:
                pass
            try:
                self.master_app.redraw(preserve_view=False)
            except Exception:
                pass
            self._pump_ui()

        fn = self._ask_multifit_save_path()
        if not fn:
            self.master_app.status("MultiFit: save cancelled")
            return
        remember_working_dir(self.master_app.options, fn)
        try:
            self._write_multifit_workbook(fn, files, template_lines, results_by_file)
        except Exception as e:
            _showerror(self, "MultiFit", str(e))
            return

        self.master_app.status(f"MultiFit: saved {fn}")
        if load_errors:
            _showwarning(self, "MultiFit", "\n".join(load_errors[:10]))

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
        self.title("Vertical Shift")
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

        self.shift_identifications_var = tk.BooleanVar(value=False)
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
            shifted_sources = []
            for source_window in sp.source_windows:
                raw_axis = _source_raw_axis(source_window)
                shifted_sources.append(
                    SpectrumSourceWindow(
                        tuple(x + shift for x in source_window.x),
                        tuple(source_window.y),
                        source_window.name,
                        source_window.filename,
                        source_window.dark_corrected,
                        source_window.dark_source,
                        source_window.signal_column,
                        source_window.dark_columns,
                        raw_axis,
                        safe_float(
                            getattr(source_window, "calibration_intercept", 0.0),
                            0.0,
                        )
                        + shift,
                        safe_float(
                            getattr(source_window, "calibration_slope", 1.0),
                            1.0,
                        ),
                        str(
                            getattr(
                                source_window, "calibration_model", ""
                            )
                            or "manual-offset"
                        ),
                        safe_float(
                            getattr(source_window, "calibration_rms", 0.0),
                            0.0,
                        ),
                        tuple(getattr(source_window, "replicate_files", ()) or ()),
                    )
                )
            sp.source_windows = tuple(shifted_sources)
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


class WavelengthCalibrationWindow(tk.Toplevel):
    """Estimate and persist an independent wavelength scale for each window."""

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self.title("Per-window wavelength calibration")
        self.geometry("980x590")
        self.minsize(880, 510)
        self.profiles = list(master.wavelength_calibration_profiles())
        self.window_errors = {}
        self.extra_reference_wavelengths = set()

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(controls, text="Maximum initial shift").pack(side="left")
        self.max_shift_var = tk.StringVar(value="0.8")
        ttk.Entry(controls, textvariable=self.max_shift_var, width=8).pack(
            side="left", padx=(4, 12)
        )
        ttk.Label(controls, text="nm").pack(side="left", padx=(0, 16))
        ttk.Label(controls, text="Model").pack(side="left")
        self.model_var = tk.StringVar(value="auto")
        ttk.Combobox(
            controls,
            textvariable=self.model_var,
            values=("auto", "offset", "linear"),
            state="readonly",
            width=10,
        ).pack(side="left", padx=4)
        ttk.Button(
            controls,
            text="Estimate from selected NIST lines",
            command=self.estimate_from_selected_lines,
        ).pack(side="left", padx=12)
        ttk.Button(
            controls,
            text="Use identified Voigt fits",
            command=self.estimate_from_fitted_lines,
        ).pack(side="left", padx=3)
        add_context_help_button(
            controls,
            self,
            "Wavelength calibration",
            (
                "Calibrate before identification and Auto Fit. Load or paste NIST wavelengths; "
                "they are also added to the selected-line list.\n\n"
                "The program locates measured maxima, refines their centers with a Voigt profile when SciPy "
                "is available, and calibrates each detector window independently. In Auto mode, one or two "
                "lines produce an offset; a linear scale requires at least three coherent lines spanning 5 nm."
            ),
        ).pack(side="right")

        reference_bar = ttk.Frame(self)
        reference_bar.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Button(
            reference_bar,
            text="Load NIST line list...",
            command=self.load_nist_line_list,
        ).pack(side="left", padx=(0, 8))
        ttk.Label(reference_bar, text="or paste wavelengths:").pack(side="left")
        self.pasted_references_var = tk.StringVar(value="")
        pasted_entry = ttk.Entry(
            reference_bar,
            textvariable=self.pasted_references_var,
            width=42,
        )
        pasted_entry.pack(side="left", fill="x", expand=True, padx=5)
        pasted_entry.bind("<Return>", lambda _event: self.add_pasted_references())
        ttk.Button(
            reference_bar,
            text="Add",
            command=self.add_pasted_references,
        ).pack(side="left", padx=3)
        self.reference_info_var = tk.StringVar(value="")
        ttk.Label(reference_bar, textvariable=self.reference_info_var).pack(
            side="left", padx=(10, 0)
        )

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=6)
        columns = (
            "window",
            "range",
            "model",
            "anchors",
            "delta",
            "slope",
            "rms",
            "status",
        )
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=10
        )
        widths = {
            "window": 170,
            "range": 145,
            "model": 70,
            "anchors": 65,
            "delta": 100,
            "slope": 90,
            "rms": 80,
            "status": 230,
        }
        headings = {
            "window": "Window",
            "range": "Raw range (nm)",
            "model": "Model",
            "anchors": "Lines",
            "delta": "Δλ at center",
            "slope": "Scale b",
            "rms": "RMS (nm)",
            "status": "Quality",
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                anchor="w" if column in {"window", "status"} else "center",
            )
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.show_selected_anchors)

        anchor_frame = ttk.LabelFrame(
            self, text="Calibration lines for the selected window"
        )
        anchor_frame.pack(fill="both", expand=True, padx=10, pady=6)
        anchor_actions = ttk.Frame(anchor_frame)
        anchor_actions.pack(fill="x", padx=3, pady=3)
        ttk.Button(
            anchor_actions,
            text="Include / exclude selected line",
            command=self.toggle_selected_anchor,
        ).pack(side="left", padx=3)
        ttk.Button(
            anchor_actions,
            text="Include all lines",
            command=self.include_all_anchors,
        ).pack(side="left", padx=3)
        anchor_columns = ("reference", "observed", "residual", "used")
        self.anchor_tree = ttk.Treeview(
            anchor_frame, columns=anchor_columns, show="headings", height=7
        )
        for column, title, width in (
            ("reference", "NIST (nm)", 135),
            ("observed", "Observed center (nm)", 155),
            ("residual", "Residual (nm)", 125),
            ("used", "Used", 75),
        ):
            self.anchor_tree.heading(column, text=title)
            self.anchor_tree.column(column, width=width, anchor="center")
        self.anchor_tree.pack(fill="both", expand=True)
        self.anchor_tree.bind(
            "<Double-1>", lambda _event: self.toggle_selected_anchor()
        )

        self.info_var = tk.StringVar(value="Ready")
        ttk.Label(
            self, textvariable=self.info_var
        ).pack(fill="x", padx=12, pady=4)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=10, pady=(4, 10))
        ttk.Button(
            buttons, text="Apply to loaded spectra", command=self.apply_profiles
        ).pack(side="left", padx=3)
        ttk.Button(
            buttons,
            text="Apply and remember",
            command=lambda: self.apply_profiles(save=True),
        ).pack(side="left", padx=3)
        ttk.Button(
            buttons, text="Clear saved calibration", command=self.clear_saved
        ).pack(side="left", padx=12)
        ttk.Button(buttons, text="Close", command=self.destroy).pack(
            side="right", padx=3
        )
        self.refresh()
        self._update_reference_info()
        center_window(self, master)

    def _source_windows(self):
        if not self.master_app.spectra:
            return []
        spectra = (
            list(self.master_app.spectra)
            if getattr(self.master_app, "independent_window_mode", False)
            else list(self.master_app.spectra[:1])
        )
        windows = []
        for spectrum in spectra:
            windows.extend(
                spectrum.source_windows
                or (
                    SpectrumSourceWindow(
                        tuple(spectrum.x),
                        tuple(spectrum.y),
                        spectrum.name,
                        spectrum.filename,
                        spectrum.dark_corrected,
                        spectrum.dark_source,
                        spectrum.signal_column,
                        spectrum.dark_columns,
                        tuple(spectrum.x),
                        replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
                    ),
                )
            )
        return windows

    def _reference_wavelengths(self):
        references = list(self.extra_reference_wavelengths)
        for line in self.master_app.template_lines:
            assigned = safe_float(getattr(line, "asswavelen", 0.0), 0.0)
            marked = safe_float(getattr(line, "wavelen", 0.0), 0.0)
            value = assigned or marked
            if value > 0.0 and math.isfinite(value):
                references.append(value)
        return sorted(set(references))

    def _update_reference_info(self):
        count = len(self._reference_wavelengths())
        self.reference_info_var.set(
            f"{count} NIST wavelength{'s' if count != 1 else ''} ready"
        )

    @staticmethod
    def _parse_pasted_wavelengths(text):
        values = []
        pattern = r"[-+]?(?:\d+(?:[\.,]\d*)?|[\.,]\d+)(?:[Ee][-+]?\d+)?"
        for token in re.findall(pattern, str(text or "")):
            value = safe_float(token.replace(",", "."), None)
            if value is not None and value > 0.0 and math.isfinite(value):
                values.append(float(value))
        return sorted(set(values))

    def _add_references_to_selected_lines(self, references):
        added = 0
        for reference in references:
            if any(
                abs(
                    (
                        safe_float(getattr(line, "asswavelen", 0.0), 0.0)
                        or safe_float(getattr(line, "wavelen", 0.0), 0.0)
                    )
                    - reference
                )
                <= 1.0e-7
                for line in self.master_app.template_lines
            ):
                continue
            self.master_app.template_lines.append(
                TemplateLine(wavelen=float(reference))
            )
            added += 1
        if added:
            self.master_app.notify_template_changed(redraw=True)
        return added

    def load_nist_line_list(self):
        filename = filedialog.askopenfilename(
            title="Load a list containing NIST wavelengths",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[
                ("NIST wavelength lists", "*.txt *.csv *.dat"),
                ("All files", "*.*"),
            ],
        )
        if not filename:
            return False
        remember_working_dir(self.master_app.options, filename)
        try:
            lines = load_template_lines(filename, RetroTemplateManager.columns)
        except Exception as exc:
            _showerror(self, "Wavelength calibration", str(exc))
            return False
        references = sorted(
            {
                safe_float(getattr(line, "asswavelen", 0.0), 0.0)
                or safe_float(getattr(line, "wavelen", 0.0), 0.0)
                for line in lines
                if (
                    safe_float(getattr(line, "asswavelen", 0.0), 0.0)
                    or safe_float(getattr(line, "wavelen", 0.0), 0.0)
                )
                > 0.0
            }
        )
        if not references:
            _showerror(
                self,
                "Wavelength calibration",
                "The selected file contains no readable wavelength values.",
            )
            return False
        self.extra_reference_wavelengths.update(references)
        self._add_references_to_selected_lines(references)
        self._update_reference_info()
        self.info_var.set(
            f"Loaded {len(references)} NIST wavelengths from {Path(filename).name}."
        )
        self.master_app.status(
            f"Wavelength calibration: {len(references)} NIST wavelengths loaded"
        )
        return True

    def add_pasted_references(self):
        references = self._parse_pasted_wavelengths(
            self.pasted_references_var.get()
        )
        if not references:
            _showinfo(
                self,
                "Wavelength calibration",
                "Paste one or more wavelengths separated by spaces or semicolons.",
            )
            return False
        self.extra_reference_wavelengths.update(references)
        added = self._add_references_to_selected_lines(references)
        self.pasted_references_var.set("")
        self._update_reference_info()
        self.info_var.set(
            f"{len(references)} pasted NIST wavelengths are ready "
            f"({added} new selected lines)."
        )
        return True

    @staticmethod
    def _quality_text(profile):
        count = profile.used_anchor_count
        if count == 1:
            return "Limited: one-line offset"
        if count == 2 and profile.model == "offset":
            return "Limited: offset from two lines"
        if profile.rms > 0.05:
            return "Check: large residuals"
        if profile.rms > 0.025:
            return "Review residuals"
        return "Good"

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        sources = self._source_windows()
        for index, source in enumerate(sources):
            raw_axis = _source_raw_axis(source)
            if not raw_axis:
                continue
            profile = calibration_for_window(
                self.profiles, raw_axis, source.filename or source.name
            )
            low, high = min(raw_axis), max(raw_axis)
            if profile is None:
                error = self.window_errors.get(index, "")
                values = (
                    Path(source.filename or source.name).name,
                    f"{low:.3f} – {high:.3f}",
                    "—",
                    "0",
                    "—",
                    "—",
                    "—",
                    error or "Not calibrated",
                )
            else:
                delta = profile.correction_at(0.5 * (low + high))
                values = (
                    Path(source.filename or source.name).name,
                    f"{low:.3f} – {high:.3f}",
                    profile.model,
                    str(profile.used_anchor_count),
                    f"{delta:+.5f}",
                    f"{profile.slope:.8f}",
                    f"{profile.rms:.5f}",
                    self._quality_text(profile),
                )
            self.tree.insert("", "end", iid=str(index), values=values)
        if sources:
            self.tree.selection_set("0")
            self.tree.focus("0")
            self.show_selected_anchors()

    def show_selected_anchors(self, _event=None):
        self.anchor_tree.delete(*self.anchor_tree.get_children())
        item = self.tree.focus()
        if not item:
            return
        index = safe_int(item, -1)
        sources = self._source_windows()
        if not 0 <= index < len(sources):
            return
        source = sources[index]
        profile = calibration_for_window(
            self.profiles,
            _source_raw_axis(source),
            source.filename or source.name,
        )
        if profile is None:
            return
        for anchor_index, anchor in enumerate(profile.anchors):
            self.anchor_tree.insert(
                "",
                "end",
                iid=str(anchor_index),
                values=(
                    f"{anchor.reference:.6f}",
                    f"{anchor.observed:.6f}",
                    f"{anchor.residual:+.6f}",
                    "Yes" if anchor.used else "No",
                ),
            )

    def _selected_profile(self):
        item = self.tree.focus()
        if not item:
            return None
        index = safe_int(item, -1)
        sources = self._source_windows()
        if not 0 <= index < len(sources):
            return None
        source = sources[index]
        return calibration_for_window(
            self.profiles,
            _source_raw_axis(source),
            source.filename or source.name,
        )

    def _refit_profile_with_anchors(self, profile, anchors):
        updated = fit_wavelength_calibration(
            anchors,
            name=profile.name,
            raw_min=profile.raw_min,
            raw_max=profile.raw_max,
            model=self.model_var.get(),
        )
        profile_index = self.profiles.index(profile)
        self.profiles[profile_index] = updated
        selected_window = self.tree.focus()
        self.refresh()
        if selected_window in self.tree.get_children():
            self.tree.selection_set(selected_window)
            self.tree.focus(selected_window)
            self.show_selected_anchors()

    def toggle_selected_anchor(self):
        profile = self._selected_profile()
        anchor_item = self.anchor_tree.focus()
        if profile is None or not anchor_item:
            return
        anchor_index = safe_int(anchor_item, -1)
        if not 0 <= anchor_index < len(profile.anchors):
            return
        if profile.used_anchor_count == 1 and profile.anchors[anchor_index].used:
            _showinfo(
                self,
                "Wavelength calibration",
                "At least one calibration line must remain included.",
            )
            return
        anchors = list(profile.anchors)
        anchor = anchors[anchor_index]
        anchors[anchor_index] = CalibrationAnchor(
            reference=anchor.reference,
            observed=anchor.observed,
            prominence=anchor.prominence,
            residual=anchor.residual,
            used=not anchor.used,
        )
        self._refit_profile_with_anchors(profile, anchors)

    def include_all_anchors(self):
        profile = self._selected_profile()
        if profile is None:
            return
        anchors = [
            CalibrationAnchor(
                reference=anchor.reference,
                observed=anchor.observed,
                prominence=anchor.prominence,
                residual=anchor.residual,
                used=True,
            )
            for anchor in profile.anchors
        ]
        self._refit_profile_with_anchors(profile, anchors)

    def estimate_from_selected_lines(self):
        sources = self._source_windows()
        if not sources:
            _showinfo(self, "Wavelength calibration", "Load the spectra first.")
            return
        references = self._reference_wavelengths()
        if not references:
            if not self.load_nist_line_list():
                return
            references = self._reference_wavelengths()
        max_shift = max(
            0.01, abs(safe_float(self.max_shift_var.get(), 0.8))
        )
        model = self.model_var.get()
        profiles = []
        self.window_errors = {}
        for index, source in enumerate(sources):
            raw_axis = _source_raw_axis(source)
            try:
                profile = estimate_window_calibration(
                    raw_axis,
                    source.y,
                    references,
                    name=source.filename or source.name,
                    max_shift=max_shift,
                    model=model,
                )
                profiles.append(profile)
            except Exception as exc:
                self.window_errors[index] = str(exc)
        self.profiles = profiles
        self.refresh()
        calibrated = len(profiles)
        self.info_var.set(
            f"Estimated {calibrated}/{len(sources)} windows. Review line count, "
            "RMS and residuals before applying."
        )
        self.master_app.status(
            f"Wavelength calibration: {calibrated}/{len(sources)} windows estimated"
        )

    def estimate_from_fitted_lines(self):
        sources = self._source_windows()
        if not sources:
            _showinfo(self, "Wavelength calibration", "Load the spectra first.")
            return
        grouped = [[] for _ in sources]
        for line in self.master_app.template_lines:
            reference = safe_float(getattr(line, "asswavelen", 0.0), 0.0)
            observed = abs(
                safe_float(getattr(line, "fitwavelen", 0.0), 0.0)
            )
            if reference <= 0.0 or observed <= 0.0:
                continue
            for index, source in enumerate(sources):
                raw_axis = _source_raw_axis(source)
                intercept = safe_float(
                    getattr(source, "calibration_intercept", 0.0), 0.0
                )
                slope = safe_float(
                    getattr(source, "calibration_slope", 1.0), 1.0
                )
                low = intercept + slope * min(raw_axis)
                high = intercept + slope * max(raw_axis)
                if min(low, high) <= observed <= max(low, high):
                    raw_observed = (
                        (observed - intercept) / slope
                        if abs(slope) > 1.0e-12
                        else observed
                    )
                    grouped[index].append(
                        CalibrationAnchor(
                            reference=reference,
                            observed=raw_observed,
                            prominence=max(
                                abs(
                                    safe_float(
                                        getattr(line, "inte", 0.0), 0.0
                                    )
                                ),
                                1.0,
                            ),
                        )
                    )
                    break
        profiles = []
        self.window_errors = {}
        for index, (source, anchors) in enumerate(zip(sources, grouped)):
            if not anchors:
                self.window_errors[index] = "No identified Voigt fit"
                continue
            raw_axis = _source_raw_axis(source)
            try:
                profiles.append(
                    fit_wavelength_calibration(
                        anchors,
                        name=source.filename or source.name,
                        raw_min=min(raw_axis),
                        raw_max=max(raw_axis),
                        model=self.model_var.get(),
                    )
                )
            except Exception as exc:
                self.window_errors[index] = str(exc)
        self.profiles = profiles
        self.refresh()
        self.info_var.set(
            f"Built {len(profiles)}/{len(sources)} windows from identified Voigt centers."
        )

    def apply_profiles(self, save=False):
        if not self.profiles:
            _showinfo(
                self,
                "Wavelength calibration",
                "Estimate at least one window before applying the calibration.",
            )
            return
        self.master_app.options.wavelength_calibrations = serialize_calibrations(
            self.profiles
        )
        self.master_app.options.auto_wavelength_calibration = True
        self.master_app.options.auto_shift = 0.0
        self.master_app.apply_wavelength_calibration_profiles(self.profiles)
        if save:
            path = save_pylibs_ini(self.master_app.options)
            self.info_var.set(
                f"Calibration applied and saved in {path}. Future spectra use it automatically."
            )
        else:
            self.info_var.set(
                "Calibration applied for this session. Use 'Apply and remember' "
                "after reviewing the residuals."
            )
        self.master_app.status(
            f"Per-window wavelength calibration applied ({len(self.profiles)} profiles)"
        )

    def clear_saved(self):
        self.profiles = []
        self.window_errors = {}
        self.master_app.options.wavelength_calibrations = "[]"
        self.master_app.options.auto_wavelength_calibration = False
        self.master_app.options.auto_shift = 0.0
        self.master_app.apply_wavelength_calibration_profiles([])
        path = save_pylibs_ini(self.master_app.options)
        self.refresh()
        self.info_var.set(f"Saved calibration cleared in {path}.")


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
        raise RuntimeError("NumPy is not available.")
    x = np.asarray(x, dtype=float)
    y = np.full_like(x, float(params[0])) + float(params[1]) * x
    for i in range(2, len(params), 3):
        amp, cen, sig = params[i], params[i + 1], abs(params[i + 2]) or 1e-12
        y += amp * np.exp(-((x - cen) / sig) ** 2)
    return y


def palleschi_gaussian_area(amplitude: float, sigma: float) -> float:
    """Analytical area of Palleschi's ``A*exp(-((x-x0)/sigma)^2)``."""
    return float(amplitude) * abs(float(sigma)) * math.sqrt(math.pi)




def voigt_profile_unit(x, center, sigma, gamma):
    """Area-normalized Voigt profile.

    sigma is the Gaussian sigma and gamma is the Lorentzian HWHM.  The
    implementation uses scipy.special.wofz when available; otherwise it falls
    back to a pseudo-Voigt approximation so the program remains usable.
    """
    if np is None:
        raise RuntimeError("NumPy is not available.")
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
    """Optional centered-linear baseline plus area-normalized Voigt components."""
    if np is None:
        raise RuntimeError("NumPy is not available.")
    x = np.asarray(x, dtype=float)
    x_center = 0.5 * (float(np.min(x)) + float(np.max(x))) if x.size else 0.0
    y = np.full_like(x, float(params[0])) + float(params[1]) * (x - x_center)
    for i in range(2, len(params), 4):
        area, cen, sigma, gamma = params[i], params[i + 1], params[i + 2], params[i + 3]
        y += area * voigt_profile_unit(x, cen, sigma, gamma)
    return y


def _voigt_initial_height(peak_y, y_values, baseline):
    """Scale-aware starting height for raw-count and radiometric spectra."""
    values = np.asarray(y_values, dtype=float)
    if values.size == 0:
        return 1.0e-12
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 1.0e-12
    signal_span = max(float(np.max(finite) - np.min(finite)), 0.0)
    absolute_scale = max(
        float(np.max(np.abs(finite))),
        abs(float(baseline)),
        1.0e-300,
    )
    floor = max(
        signal_span * 1.0e-4,
        absolute_scale * 1.0e-9,
        1.0e-300,
    )
    return max(float(peak_y) - float(baseline), floor)


def _voigt_initial_area(height, center, sigma, gamma, dx):
    """Convert a peak-height estimate to the area parameter of our Voigt."""
    try:
        unit_height = float(
            voigt_profile_unit(
                np.asarray([float(center)], dtype=float),
                float(center),
                float(sigma),
                float(gamma),
            )[0]
        )
    except Exception:
        unit_height = 0.0
    if not math.isfinite(unit_height) or unit_height <= 0.0:
        unit_height = 1.0 / max(abs(float(dx)), 1.0e-12)
    scale_floor = max(
        abs(float(height)) * max(abs(float(dx)), 1.0e-12) * 1.0e-6,
        1.0e-300,
    )
    return max(float(height) / unit_height, scale_floor)


def _voigt_auto_fwhm(dx, fit_width):
    """Sampling-based free-width initializer in the current wavelength unit."""
    step = max(abs(float(dx)), 1.0e-12)
    width = max(abs(float(fit_width)), step)
    return min(max(2.0 * step, 0.02 * width), 0.20 * width)


def _voigt_quality_assessment(
    *,
    center,
    bound_center,
    bound_half_window,
    dx,
    fit_span,
    gaussian_width,
    lorentzian_width,
    peak_snr,
    fixed_center=False,
):
    """Reject Voigt solutions that are not identified inside the fitted ROI."""
    center = float(center)
    bound_center = float(bound_center)
    bound_half_window = abs(float(bound_half_window))
    dx = abs(float(dx))
    fit_span = abs(float(fit_span))
    gaussian_width = abs(float(gaussian_width))
    lorentzian_width = abs(float(lorentzian_width))
    peak_snr = float(peak_snr)

    center_margin = bound_half_window - abs(center - bound_center)
    bound_tolerance = max(dx * 0.30, bound_half_window * 0.01, 1.0e-9)
    at_center_bound = not bool(fixed_center) and center_margin <= bound_tolerance

    # Olivero-Longbothum approximation of the Voigt FWHM. A component whose
    # FWHM fills almost the whole fitted interval has no independently observed
    # baseline and its normalized area is therefore unconstrained.
    voigt_fwhm = (
        0.5346 * lorentzian_width
        + math.sqrt(
            0.2166 * lorentzian_width * lorentzian_width
            + gaussian_width * gaussian_width
        )
    )
    fwhm_roi_fraction = (
        voigt_fwhm / fit_span
        if fit_span > 0.0
        else math.inf
    )

    warnings = []
    rejections = []
    if at_center_bound:
        warnings.append(
            "center reached search boundary; area retained, but line identity and blend must be reviewed"
        )
    if not math.isfinite(fwhm_roi_fraction) or fwhm_roi_fraction >= 0.80:
        rejections.append(
            f"Voigt FWHM occupies {fwhm_roi_fraction:.3g} of fitted ROI; "
            "area is not constrained by two visible baseline sides"
        )
    if not math.isfinite(peak_snr) or peak_snr < 3.0:
        rejections.append(f"fitted peak S/N {peak_snr:.3g} < 3")

    return {
        "at_center_bound": at_center_bound,
        "voigt_fwhm": voigt_fwhm,
        "fwhm_roi_fraction": fwhm_roi_fraction,
        "quality_ok": not rejections,
        "quality_warning": "; ".join(warnings),
        "quality_message": "; ".join(warnings + rejections),
    }


def _voigt_low_envelope_baseline(x_values, y_values):
    """Estimate the local linear baseline from the low envelope at both sides."""
    xs = np.asarray(x_values, dtype=float)
    ys = np.asarray(y_values, dtype=float)
    if xs.size < 8 or ys.size != xs.size:
        level = float(np.median(ys)) if ys.size else 0.0
        return np.full_like(ys, level, dtype=float)
    xmin = float(np.min(xs))
    xmax = float(np.max(xs))
    span = max(xmax - xmin, np.finfo(float).eps)
    trim = max(0.08 * span, np.finfo(float).eps)
    band = max(0.14 * span, np.finfo(float).eps)
    left_mask = (xs >= xmin + trim) & (xs <= min(xmin + trim + band, xmax))
    right_mask = (xs >= max(xmax - trim - band, xmin)) & (xs <= xmax - trim)
    if np.count_nonzero(left_mask) < 2 or np.count_nonzero(right_mask) < 2:
        return np.full_like(ys, float(np.median(ys)), dtype=float)

    fit_x = []
    fit_y = []
    for mask in (left_mask, right_mask):
        band_x = xs[mask]
        band_y = ys[mask]
        cutoff = (
            float(np.percentile(band_y, 35.0))
            if band_y.size >= 4
            else float(np.max(band_y))
        )
        keep = band_y <= cutoff
        if np.count_nonzero(keep) >= 2:
            band_x = band_x[keep]
            band_y = band_y[keep]
        fit_x.extend(band_x.tolist())
        fit_y.extend(band_y.tolist())
    try:
        slope, intercept = np.polyfit(
            np.asarray(fit_x, dtype=float),
            np.asarray(fit_y, dtype=float),
            1,
        )
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return np.full_like(ys, float(np.median(ys)), dtype=float)
    return slope * xs + intercept


def _voigt_baseline_reaching_limits(
    x_values,
    y_values,
    lines,
    line_overrides=None,
):
    """Find the first stable return to the local baseline around a line group.

    This is the multi-line counterpart of the automatic tangent limits used by
    the earlier LIBS analysis program. The broad graph interval remains the
    search domain; only the part from the left baseline return to the right
    baseline return is sent to the Voigt optimizer.
    """
    xs = np.asarray(x_values, dtype=float)
    ys = np.asarray(y_values, dtype=float)
    if xs.size < 9 or ys.size != xs.size:
        return None
    baseline = _voigt_low_envelope_baseline(xs, ys)
    signal = ys - baseline
    kernel = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
    kernel /= float(np.sum(kernel))
    smooth = np.convolve(signal, kernel, mode="same")
    derivative = np.gradient(smooth, xs)
    spacing_values = np.diff(xs)
    spacing_values = spacing_values[spacing_values > 0.0]
    spacing = (
        float(np.median(spacing_values))
        if spacing_values.size
        else max(float(np.ptp(xs)) / max(xs.size - 1, 1), 1.0e-12)
    )
    span = max(float(np.ptp(xs)), spacing)
    search_half = max(0.05 * span, 4.0 * spacing)
    overrides = line_overrides or {}
    peak_indices = []
    for line in list(lines or []):
        override = overrides.get(line.get("key"), {})
        target = safe_float(
            override.get("center") if override else line.get("fitwavelen"),
            0.0,
        )
        if target <= 0.0:
            target = safe_float(line.get("wavelen"), 0.0)
        mask = np.flatnonzero(
            (xs >= target - search_half)
            & (xs <= target + search_half)
        )
        if mask.size:
            peak_indices.append(int(mask[int(np.argmax(smooth[mask]))]))
    if not peak_indices:
        peak_indices = [int(np.argmax(smooth))]
    left_peak = min(peak_indices)
    right_peak = max(peak_indices)
    peak_value = max(float(smooth[index]) for index in peak_indices)
    if not math.isfinite(peak_value) or peak_value <= 0.0:
        return None

    differences = np.diff(signal)
    diff_median = float(np.median(differences)) if differences.size else 0.0
    diff_mad = (
        float(np.median(np.abs(differences - diff_median)))
        if differences.size
        else 0.0
    )
    noise = (
        diff_mad / (0.67448975 * math.sqrt(2.0))
        if diff_mad > 0.0
        else 0.0
    )
    amplitude_threshold = max(
        0.015 * peak_value,
        2.0 * noise,
        max(abs(peak_value), 1.0e-300) * 1.0e-10,
    )
    slope_threshold = max(
        float(np.percentile(np.abs(derivative), 35.0)),
        amplitude_threshold / max(span, spacing) * 1.0e-6,
        1.0e-300,
    )

    left_index = None
    for index in range(left_peak - 1, 1, -1):
        if (
            abs(float(smooth[index])) <= amplitude_threshold
            and abs(float(derivative[index])) <= slope_threshold
        ):
            left_index = index
            break
    if left_index is None and left_peak > 0:
        scale = max(slope_threshold, 1.0e-300)
        score = (
            np.abs(smooth[:left_peak])
            + 0.2 * amplitude_threshold * np.abs(derivative[:left_peak]) / scale
        )
        left_index = int(np.argmin(score))

    right_index = None
    for index in range(right_peak + 1, len(xs) - 2):
        if (
            abs(float(smooth[index])) <= amplitude_threshold
            and abs(float(derivative[index])) <= slope_threshold
        ):
            right_index = index
            break
    if right_index is None and right_peak < len(xs) - 1:
        scale = max(slope_threshold, 1.0e-300)
        score = (
            np.abs(smooth[right_peak + 1:])
            + 0.2
            * amplitude_threshold
            * np.abs(derivative[right_peak + 1:])
            / scale
        )
        right_index = int(np.argmin(score)) + right_peak + 1

    if left_index is None or right_index is None:
        return None
    left_index = max(left_index - 1, 0)
    right_index = min(right_index + 1, len(xs) - 1)
    if (
        left_index >= left_peak
        or right_index <= right_peak
        or right_index - left_index < 7
    ):
        return None
    return float(xs[left_index]), float(xs[right_index])


def _voigt_expanded_baseline_limits(
    x_values,
    y_values,
    lines,
    current_limits,
    *,
    search_range=1.0,
    line_overrides=None,
):
    """Expand a truncated saved ROI to measured baseline returns.

    A manually selected ROI can be valid for one acquisition and truncate a
    broader line in the next.  The saved interval is retained whenever it
    still contains the complete profile; this helper is only used after the
    fitted FWHM/quality checks have demonstrated truncation.
    """
    pairs = sorted(
        (
            (float(x), float(y))
            for x, y in zip(x_values, y_values)
            if math.isfinite(float(x)) and math.isfinite(float(y))
        ),
        key=lambda pair: pair[0],
    )
    if len(pairs) < 9:
        return None
    xs = np.asarray([pair[0] for pair in pairs], dtype=float)
    ys = np.asarray([pair[1] for pair in pairs], dtype=float)
    lo, hi = sorted((float(current_limits[0]), float(current_limits[1])))
    steps = np.diff(xs)
    positive_steps = steps[steps > 0.0]
    spacing = (
        float(np.median(positive_steps))
        if positive_steps.size
        else max(float(np.ptp(xs)) / max(len(xs) - 1, 1), 1.0e-12)
    )
    targets = []
    for line in list(lines or []):
        target = safe_float(line.get("fitwavelen"), 0.0)
        if target <= 0.0:
            target = safe_float(line.get("wavelen"), math.nan)
        if math.isfinite(target):
            targets.append(target)
    if not targets:
        return None
    margin = max(
        abs(safe_float(search_range, 1.0)),
        0.5,
        12.0 * spacing,
        hi - lo,
    )
    broad_lo = max(float(xs[0]), min(targets) - margin)
    broad_hi = min(float(xs[-1]), max(targets) + margin)
    mask = (xs >= broad_lo) & (xs <= broad_hi)
    if np.count_nonzero(mask) < 9:
        return None
    measured = _voigt_baseline_reaching_limits(
        xs[mask],
        ys[mask],
        lines,
        line_overrides=line_overrides,
    )
    if measured is None:
        return None
    expanded = (min(lo, measured[0]), max(hi, measured[1]))
    if expanded[1] - expanded[0] <= hi - lo + spacing:
        return None
    return float(expanded[0]), float(expanded[1])


def _voigt_integral_to_baseline(
    x_values,
    area,
    center,
    sigma,
    gamma,
    threshold_fraction=0.005,
):
    """Integrate one fitted Voigt until its curve has returned to baseline."""
    xs = np.asarray(x_values, dtype=float)
    if xs.size < 3:
        return float(area), math.nan, math.nan
    curve = np.maximum(
        float(area)
        * voigt_profile_unit(
            xs,
            float(center),
            float(sigma),
            float(gamma),
        ),
        0.0,
    )
    center_index = int(np.argmin(np.abs(xs - float(center))))
    peak_value = float(
        float(area)
        * voigt_profile_unit(
            np.asarray([float(center)], dtype=float),
            float(center),
            float(sigma),
            float(gamma),
        )[0]
    )
    if not math.isfinite(peak_value) or peak_value <= 0.0:
        return float(area), float(xs[0]), float(xs[-1])
    threshold = max(
        float(threshold_fraction) * peak_value,
        peak_value * 1.0e-12,
    )
    left_index = 0
    for index in range(center_index, -1, -1):
        if curve[index] <= threshold:
            left_index = max(index - 1, 0)
            break
    right_index = len(xs) - 1
    for index in range(center_index, len(xs)):
        if curve[index] <= threshold:
            right_index = min(index + 1, len(xs) - 1)
            break
    if right_index - left_index < 2:
        left_index = 0
        right_index = len(xs) - 1
    integral_x = xs[left_index : right_index + 1]
    integral_y = curve[left_index : right_index + 1]
    trapezoid = getattr(np, "trapezoid", None)
    integrated = (
        float(trapezoid(integral_y, integral_x))
        if trapezoid is not None
        else float(np.trapz(integral_y, integral_x))
    )
    return integrated, float(integral_x[0]), float(integral_x[-1])


def _voigt_fit_visualization(
    source_x,
    fit_x,
    popt,
    component_count,
    threshold_fraction=0.005,
):
    """Extend a fitted Voigt model until it visibly returns to its baseline.

    This is diagnostic-only: neither optimizer inputs nor analytical areas are
    changed. The display ends where the summed fitted peak contribution falls
    below ``threshold_fraction`` of its maximum on both sides.
    """
    source_axis = np.asarray(source_x, dtype=float)
    source_axis = source_axis[np.isfinite(source_axis)]
    source_axis = np.unique(np.sort(source_axis))
    fitted_axis = np.asarray(fit_x, dtype=float)
    if (
        source_axis.size < 3
        or fitted_axis.size < 3
        or component_count < 1
    ):
        return None

    source_components = []
    centers = []
    for index in range(component_count):
        area = max(float(popt[2 + 4 * index]), 0.0)
        center = float(popt[3 + 4 * index])
        sigma = abs(float(popt[4 + 4 * index]))
        gamma = abs(float(popt[5 + 4 * index]))
        centers.append(center)
        source_components.append(
            area * voigt_profile_unit(
                source_axis,
                center,
                sigma,
                gamma,
            )
        )
    summed = np.sum(source_components, axis=0)
    peak = float(np.max(summed))
    if not math.isfinite(peak) or peak <= 0.0:
        return None
    threshold = max(float(threshold_fraction) * peak, 1.0e-300)

    left_candidates = np.flatnonzero(source_axis < min(centers))
    right_candidates = np.flatnonzero(source_axis > max(centers))
    left_index = int(left_candidates[0]) if left_candidates.size else 0
    for index in left_candidates[::-1]:
        if float(summed[index]) <= threshold:
            left_index = int(index)
            break
    right_index = (
        int(right_candidates[-1])
        if right_candidates.size
        else len(source_axis) - 1
    )
    for index in right_candidates:
        if float(summed[index]) <= threshold:
            right_index = int(index)
            break

    left_index = max(left_index - 1, 0)
    right_index = min(right_index + 1, len(source_axis) - 1)
    if right_index - left_index < 2:
        return None
    display_x = source_axis[left_index:right_index + 1]
    fit_reference = 0.5 * (
        float(np.min(fitted_axis)) + float(np.max(fitted_axis))
    )
    baseline = (
        float(popt[0])
        + float(popt[1]) * (display_x - fit_reference)
    )
    display_components = []
    bounds = []
    for index in range(component_count):
        area = max(float(popt[2 + 4 * index]), 0.0)
        center = float(popt[3 + 4 * index])
        sigma = abs(float(popt[4 + 4 * index]))
        gamma = abs(float(popt[5 + 4 * index]))
        display_components.append(
            area * voigt_profile_unit(
                display_x,
                center,
                sigma,
                gamma,
            )
        )
        _truncated_area, left, right = _voigt_integral_to_baseline(
            source_axis,
            area,
            center,
            sigma,
            gamma,
            threshold_fraction=threshold_fraction,
        )
        bounds.append((float(left), float(right)))
    total = baseline + np.sum(display_components, axis=0)
    return {
        "x": display_x.tolist(),
        "baseline": baseline.tolist(),
        "total": total.tolist(),
        "components": [curve.tolist() for curve in display_components],
        "bounds": bounds,
        "threshold_fraction": float(threshold_fraction),
    }


def _voigt_peak_candidates(x_values, y_values):
    """Locate measured maxima for initialization and blend deconvolution."""
    if np is None or scipy_find_peaks is None:
        return []
    xs = np.asarray(x_values, dtype=float)
    ys = np.asarray(y_values, dtype=float)
    if xs.size < 5 or ys.size != xs.size:
        return []
    finite = np.isfinite(xs) & np.isfinite(ys)
    xs = xs[finite]
    ys = ys[finite]
    if xs.size < 5:
        return []
    differences = np.diff(ys)
    if differences.size:
        diff_median = float(np.median(differences))
        diff_mad = float(np.median(np.abs(differences - diff_median)))
        noise_sigma = diff_mad / (0.67448975 * math.sqrt(2.0)) if diff_mad else 0.0
    else:
        noise_sigma = 0.0
    low, high = np.percentile(ys, [5.0, 99.5])
    signal_span = max(float(high - low), 0.0)
    absolute_scale = max(float(np.max(np.abs(ys))), 1.0e-300)
    prominence_floor = max(
        # Candidate detection only initializes the multi-Voigt model. Keep it
        # permissive enough to retain shoulders in a blend; fitted components
        # are subjected to the stricter residual S/N quality check afterwards.
        3.0 * noise_sigma,
        0.015 * signal_span,
        absolute_scale * 1.0e-10,
        1.0e-300,
    )
    peak_indices, properties = scipy_find_peaks(
        ys,
        prominence=prominence_floor,
        distance=2,
    )
    prominences = properties.get("prominences", np.zeros(len(peak_indices)))
    return [
        {
            "index": int(index),
            "x": float(xs[index]),
            "y": float(ys[index]),
            "prominence": float(prominences[position]),
        }
        for position, index in enumerate(peak_indices)
    ]


def identify_halpha_peak(
    x_values,
    y_values,
    expected_center,
    search_half_width,
):
    """Identify a measured H-alpha maximum close to the expected wavelength."""
    if np is None:
        raise RuntimeError("NumPy is required for H-alpha peak identification.")
    expected_center = float(expected_center)
    search_half_width = abs(float(search_half_width))
    if search_half_width <= 0.0:
        raise ValueError("H-alpha peak-search width must be positive.")
    pairs = [
        (float(x), float(y))
        for x, y in zip(x_values, y_values)
        if math.isfinite(float(x))
        and math.isfinite(float(y))
        and abs(float(x) - expected_center) <= search_half_width
    ]
    if len(pairs) < 5:
        raise ValueError(
            "Too few measured points around the expected H-alpha wavelength."
        )
    xs = np.asarray([pair[0] for pair in pairs], dtype=float)
    ys = np.asarray([pair[1] for pair in pairs], dtype=float)
    candidates = _voigt_peak_candidates(xs, ys)
    if not candidates:
        raise ValueError(
            "No real measured maximum was found near H-alpha. "
            "Check wavelength calibration and the selected spectrum."
        )
    maximum_prominence = max(candidate["prominence"] for candidate in candidates)
    plausible = [
        candidate
        for candidate in candidates
        if candidate["prominence"] >= 0.2 * maximum_prominence
    ]
    plausible.sort(
        key=lambda candidate: (
            abs(candidate["x"] - expected_center),
            -candidate["prominence"],
        )
    )
    primary = plausible[0]
    other_candidates = [
        candidate for candidate in plausible if candidate is not primary
    ]
    other_candidates.sort(
        key=lambda candidate: candidate["prominence"],
        reverse=True,
    )
    secondary = other_candidates[0] if other_candidates else None
    ambiguity_ratio = (
        secondary["prominence"] / primary["prominence"]
        if secondary is not None and primary["prominence"] > 0.0
        else 0.0
    )
    large_shift = abs(primary["x"] - expected_center) > 0.5 * search_half_width
    differences = np.diff(ys)
    if differences.size:
        difference_median = float(np.median(differences))
        difference_mad = float(
            np.median(np.abs(differences - difference_median))
        )
        noise_sigma = (
            difference_mad / (0.67448975 * math.sqrt(2.0))
            if difference_mad
            else 0.0
        )
    else:
        noise_sigma = 0.0
    prominence_to_noise = (
        primary["prominence"] / noise_sigma
        if noise_sigma > 0.0
        else float("inf")
    )
    low_signal_to_noise = prominence_to_noise < 5.0
    return {
        "expected_center": expected_center,
        "observed_center": primary["x"],
        "shift": primary["x"] - expected_center,
        "prominence": primary["prominence"],
        "search_half_width": search_half_width,
        "candidate_count": len(candidates),
        "ambiguity_ratio": ambiguity_ratio,
        "secondary_center": (
            secondary["x"] if secondary is not None else None
        ),
        "secondary_prominence": (
            secondary["prominence"] if secondary is not None else 0.0
        ),
        "large_shift": large_shift,
        "noise_sigma": noise_sigma,
        "prominence_to_noise": prominence_to_noise,
        "low_signal_to_noise": low_signal_to_noise,
        "quality": (
            "check"
            if ambiguity_ratio >= 0.5 or large_shift or low_signal_to_noise
            else "compatible"
        ),
    }


def _voigt_prepare_components(
    lines,
    line_overrides,
    xs,
    ys,
    half_window,
    dx,
    extra_nuisance_centers=None,
):
    """Initialize selected components on data maxima and add nearby nuisances.

    Nuisance components model real neighbouring peaks, but are deliberately
    excluded from the analytical-line output.
    """
    selected = [dict(line) for line in list(lines or [])]
    overrides = line_overrides or {}
    candidates = _voigt_peak_candidates(xs, ys)
    fixed_keys = set()
    target_centers = {}
    for line in selected:
        override = overrides.get(line.get("key"), {})
        target = (
            abs(safe_float(override.get("center"), line.get("fitwavelen") or line.get("wavelen")))
            if override
            else safe_float(line.get("wavelen"), 0.0)
        )
        target_centers[line.get("key")] = target
        fixed = bool(override.get("fix_center", False)) if override else (
            bool(line.get("_global_fix_wavelength", False))
            or safe_float(line.get("fitwavelen"), 0.0) < 0.0
        )
        if fixed:
            fixed_keys.add(line.get("key"))

    assignments = {}
    available = set(range(len(candidates)))
    possible = sorted(
        (
            -candidate["prominence"],
            abs(candidate["x"] - target),
            line.get("key"),
            candidate_index,
        )
        for line in selected
        if line.get("key") not in fixed_keys
        for candidate_index, candidate in enumerate(candidates)
        for target in (target_centers.get(line.get("key"), 0.0),)
        if abs(candidate["x"] - target) <= half_window
    )
    assigned_keys = set()
    for _negative_prominence, _distance, key, candidate_index in possible:
        if key in assigned_keys or candidate_index not in available:
            continue
        assignments[key] = candidate_index
        assigned_keys.add(key)
        available.remove(candidate_index)

    for line in selected:
        key = line.get("key")
        target = target_centers.get(key, safe_float(line.get("wavelen"), 0.0))
        candidate_index = assignments.get(key)
        observed_center = (
            candidates[candidate_index]["x"]
            if candidate_index is not None
            else target
        )
        line["_nuisance"] = False
        # NIST identifies the transition and defines the candidate-search
        # interval. Once a compatible measured maximum has been found, the
        # Voigt center must be bounded around that observation; otherwise a
        # legitimate shifted peak can start at the old NIST-centered boundary
        # and be rejected without the optimizer ever being able to cross it.
        line["_target_center"] = target
        # Allow the optimizer to move across the complete interval connecting
        # the theoretical line and the detected maximum. A shoulder can hide
        # the true Voigt center from scipy.find_peaks; bounding only around the
        # first discrete maximum would then pin the fit to the wrong component.
        line["_bound_center"] = 0.5 * (target + observed_center)
        line["_bound_half_window"] = (
            half_window + 0.5 * abs(observed_center - target)
        )
        line["_observed_candidate"] = candidate_index is not None
        line["_center0"] = observed_center

    maximum_prominence = max(
        (candidate["prominence"] for candidate in candidates),
        default=0.0,
    )
    minimum_separation = max(abs(float(dx)) * 1.25, 1.0e-9)
    nuisance_candidates = [
        candidate
        for candidate_index, candidate in enumerate(candidates)
        if candidate_index in available
        and candidate["prominence"] >= maximum_prominence * 0.03
        and all(
            abs(candidate["x"] - component["_center0"]) > minimum_separation
            for component in selected
        )
    ]
    nuisance_candidates.sort(key=lambda candidate: candidate["prominence"], reverse=True)
    nuisances = []
    for index, candidate in enumerate(nuisance_candidates[:12]):
        nuisances.append({
            "key": f"__nuisance_{index}",
            "wavelen": candidate["x"],
            "fitwavelen": 0.0,
            "wg": 0.0,
            "wl": 0.0,
            "specie": "",
            "_nuisance": True,
            "_bound_center": candidate["x"],
            "_bound_half_window": max(half_window * 0.5, abs(float(dx)) * 2.0),
            "_observed_candidate": True,
            "_center0": candidate["x"],
        })
    existing_centers = [
        safe_float(component.get("_center0"), 0.0)
        for component in selected + nuisances
    ]
    xmin = float(np.min(xs))
    xmax = float(np.max(xs))
    for center in list(extra_nuisance_centers or []):
        center = safe_float(center, math.nan)
        if (
            not math.isfinite(center)
            or not xmin <= center <= xmax
            or any(
                abs(center - existing) <= minimum_separation
                for existing in existing_centers
            )
        ):
            continue
        index = len(nuisances)
        nuisances.append({
            "key": f"__residual_nuisance_{index}",
            "wavelen": center,
            "fitwavelen": 0.0,
            "wg": 0.0,
            "wl": 0.0,
            "specie": "",
            "_nuisance": True,
            "_bound_center": center,
            "_bound_half_window": max(
                half_window * 0.75,
                abs(float(dx)) * 3.0,
            ),
            "_observed_candidate": True,
            "_center0": center,
        })
        existing_centers.append(center)
    return selected + nuisances, len(nuisances)


def _voigt_baseline_mode(options=None):
    """Return the analytical Voigt baseline model.

    ``local_linear`` is Palleschi's authoritative model. The optional
    ``palleschi_bic_diagnostic`` mode compares it with a constant baseline but
    still returns the Palleschi fit; legacy ``auto_bic`` settings are treated
    as the same non-authoritative diagnostic.
    ``libs_auto`` preserves the baseline-reaching integration used by the
    earlier LIBS+ program. Origin's Voigt5 model (y0 + Voigt) and a free local
    linear baseline remain available for reproducibility and diagnostics.
    """
    if isinstance(options, dict):
        value = options.get("voigt_baseline_mode", "local_linear")
    else:
        value = getattr(options, "voigt_baseline_mode", "local_linear")
    value = str(value or "local_linear").strip().lower()
    if value in {
        "auto_bic",
        "palleschi_bic_diagnostic",
        "libs_auto",
        "origin_constant",
        "local_linear",
    }:
        return value
    return "local_linear"


def _voigt_result_bic(result):
    """Return the ordinary least-squares BIC for one completed Voigt fit."""
    if not result or result.get("status") != "success":
        return math.inf
    payload = result.get("payload") or {}
    sample_count = len(payload.get("residual_y") or [])
    parameter_count = safe_int(result.get("free_parameter_count"), 0)
    sse = 2.0 * safe_float(result.get("cost"), math.inf)
    if (
        sample_count < 2
        or parameter_count < 1
        or not math.isfinite(sse)
    ):
        return math.inf
    sse = max(sse, np.finfo(float).tiny if np is not None else 1.0e-300)
    return (
        sample_count * math.log(sse / sample_count)
        + parameter_count * math.log(sample_count)
    )


def _voigt_fit_range_key(line):
    """Return a stable key for a selected analytical transition."""
    if isinstance(line, dict):
        species = str(line.get("specie", "") or "").strip().capitalize()
        ion = safe_int(line.get("ion", 0), 0)
        wavelength = safe_float(
            line.get("wavelen", line.get("asswavelen", 0.0)),
            0.0,
        )
    else:
        species = str(getattr(line, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(line, "ion", 0), 0)
        wavelength = safe_float(
            getattr(line, "wavelen", 0.0)
            or getattr(line, "asswavelen", 0.0),
            0.0,
        )
    prefix = f"{species}:{ion}" if species else "line"
    return f"{prefix}:{wavelength:.6f}"


def parse_voigt_fit_ranges(value):
    """Parse persisted per-transition Voigt regions of interest."""
    if isinstance(value, dict):
        raw = value
    else:
        try:
            raw = json.loads(str(value or "{}"))
        except Exception:
            raw = {}
    parsed = {}
    for key, limits in dict(raw or {}).items():
        if not isinstance(limits, (list, tuple)) or len(limits) != 2:
            continue
        lo = safe_float(limits[0], math.nan)
        hi = safe_float(limits[1], math.nan)
        if not math.isfinite(lo) or not math.isfinite(hi) or lo == hi:
            continue
        parsed[str(key)] = list(sorted((float(lo), float(hi))))
    return parsed


def parse_voigt_fit_range_sources(value):
    """Parse the spectrum fingerprints associated with saved Voigt ROIs."""
    if isinstance(value, dict):
        raw = value
    else:
        try:
            raw = json.loads(str(value or "{}"))
        except Exception:
            raw = {}
    return {
        str(key): str(signature).strip().lower()
        for key, signature in dict(raw or {}).items()
        if str(key).strip()
        and re.fullmatch(r"[0-9a-fA-F]{16,64}", str(signature).strip())
    }


def measurement_spectrum_signature(app) -> str:
    """Identify the exact numerical spectra entering the line fitter.

    Saved absolute ROIs are safe to restore only for the same processed
    spectrum. Hashing the fitted x/y arrays also captures dark subtraction,
    wavelength calibration, merge mode and Apply Before corrections without
    relying on a filename that may have been overwritten.
    """
    spectra = list(getattr(app, "spectra", []) or [])
    if not spectra:
        return ""
    digest = hashlib.sha256()
    digest.update(
        f"independent={bool(getattr(app, 'independent_window_mode', False))}\n".encode(
            "ascii"
        )
    )
    for spectrum_index, spectrum in enumerate(spectra):
        x_values = list(getattr(spectrum, "x", []) or [])
        y_values = list(getattr(spectrum, "y", []) or [])
        digest.update(
            (
                f"spectrum={spectrum_index};name={getattr(spectrum, 'name', '')};"
                f"response_corrected={bool(getattr(spectrum, 'response_corrected', False))};"
                f"points={len(x_values)}:{len(y_values)}\n"
            ).encode("utf-8", errors="replace")
        )
        for x_value, y_value in zip(x_values, y_values):
            try:
                encoded = f"{float(x_value):.17g},{float(y_value):.17g};"
            except (TypeError, ValueError):
                encoded = f"{x_value!r},{y_value!r};"
            digest.update(encoded.encode("ascii", errors="backslashreplace"))
        digest.update(b"\n")
    return digest.hexdigest()[:16]


def _voigt_saved_fit_range(options, lines):
    """Return a shared saved ROI only when every analytical line has one."""
    if isinstance(options, dict):
        stored = options.get("voigt_fit_ranges", "{}")
    else:
        stored = getattr(options, "voigt_fit_ranges", "{}")
    ranges = parse_voigt_fit_ranges(stored)
    selected = list(lines or [])
    if not selected:
        return None
    limits = []
    for line in selected:
        saved = ranges.get(_voigt_fit_range_key(line))
        if not saved:
            return None
        limits.append(saved)
    return (
        min(item[0] for item in limits),
        max(item[1] for item in limits),
    )


def _session_voigt_saved_fit_range(app, lines):
    """Use a manual ROI only for the spectrum data that created it.

    Detector shifts vary between acquisitions. Reusing absolute wavelength
    limits from an older sample can therefore exclude the current measured
    maximum and make the fitter lock onto a neighbouring feature. The exact
    same processed spectra, however, must reproduce the same ROI after an app
    restart.
    """
    selected = list(lines or [])
    keys = {_voigt_fit_range_key(line) for line in selected}
    active_keys = set(
        getattr(app, "session_voigt_fit_range_keys", set()) or set()
    )
    if not keys:
        return None
    if not keys.issubset(active_keys):
        signature = measurement_spectrum_signature(app)
        provenance = parse_voigt_fit_range_sources(
            getattr(
                getattr(app, "options", None),
                "voigt_fit_range_sources",
                "{}",
            )
        )
        if not signature or any(
            provenance.get(key) != signature for key in keys
        ):
            return None
        active_keys.update(keys)
        app.session_voigt_fit_range_keys = active_keys
    return _voigt_saved_fit_range(app.options, selected)


def _voigt_free_parameter_count(lines, options=None, line_overrides=None):
    """Count the free parameters implied by the current Voigt fit setup."""
    baseline_mode = _voigt_baseline_mode(options)
    count = {
        "auto_bic": 2,
        "palleschi_bic_diagnostic": 2,
        "libs_auto": 1,
        "origin_constant": 1,
        "local_linear": 2,
    }[baseline_mode]
    overrides = line_overrides or {}
    for line in list(lines or []):
        if isinstance(line, dict):
            key = line.get("key")
            fitwavelen = safe_float(line.get("fitwavelen", 0.0), 0.0)
            wg = safe_float(line.get("wg", 0.0), 0.0)
            wl = safe_float(line.get("wl", 0.0), 0.0)
        else:
            key = id(line)
            fitwavelen = safe_float(getattr(line, "fitwavelen", 0.0), 0.0)
            wg = safe_float(getattr(line, "wg", 0.0), 0.0)
            wl = safe_float(getattr(line, "wl", 0.0), 0.0)
        override = overrides.get(key, {})
        if override:
            fix_center = bool(override.get("fix_center", False))
            fix_wg = bool(override.get("fix_wg", False))
            fix_wl = bool(override.get("fix_wl", False))
        else:
            fix_center = bool(getattr(options, "fix_wavelength", False)) or fitwavelen < 0
            fix_wg = bool(getattr(options, "fix_wg", False)) or wg < 0
            fix_wl = bool(getattr(options, "fix_wl", False)) or wl < 0
        count += 1
        if not fix_center:
            count += 1
        if not fix_wg:
            count += 1
        if not fix_wl:
            count += 1
    return count


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
        raise RuntimeError("NumPy is not available.")
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
        raise RuntimeError("NumPy is not available.")
    x = np.asarray(x, dtype=float)
    width = abs(float(width)) or 1e-12
    return amp / (1.0 + 4.0 * ((x - center) / width) ** 2)


def halpha_lorentzian_model(x, *params):
    """baseline + one or more Lorentzian components.

    Parameter order: baseline, then repeated amp, center, FWHM triples.
    """
    if np is None:
        raise RuntimeError("NumPy is not available.")
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


def _halpha_ne_relative_uncertainty(
    width_angstrom: float,
    width_std_angstrom: float,
    kt_ev: float,
) -> float:
    """Propagate the fitted Stark-width standard error numerically to Ne."""
    width = safe_float(width_angstrom, 0.0)
    width_std = safe_float(width_std_angstrom, math.inf)
    kt = safe_float(kt_ev, 0.0)
    if (
        width <= 0.0
        or kt <= 0.0
        or not math.isfinite(width_std)
        or width_std < 0.0
    ):
        return math.inf
    if width_std == 0.0:
        return 0.0
    try:
        central, _temperature, _alpha = libspp_halpha_ne(width, kt)
        lower, _temperature, _alpha = libspp_halpha_ne(
            max(width - width_std, width * 1.0e-6),
            kt,
        )
        upper, _temperature, _alpha = libspp_halpha_ne(
            width + width_std,
            kt,
        )
    except Exception:
        return math.inf
    return abs(upper - lower) / (2.0 * central) if central > 0.0 else math.inf


def recompute_halpha_ne_for_temperature(app: "MainWindow", kt_ev: float) -> Optional[float]:
    """Re-evaluate the stored H-alpha width at the current plasma temperature.

    The fitted width is the measured quantity. Ne is temperature dependent in
    the Palleschi H-alpha relation, so Saha-Boltzmann and H-alpha must use the
    same kT instead of silently retaining the initial H-alpha guess.
    """
    result = getattr(app, "last_halpha_result", None)
    kt_ev = safe_float(kt_ev, 0.0)
    if not isinstance(result, dict) or not result.get("available") or kt_ev <= 0.0:
        return None
    width_angstrom = safe_float(
        result.get("corrected_lorentzian_width_angstrom"),
        0.0,
    )
    if width_angstrom <= 0.0:
        return None
    try:
        ne_value, temperature_k, alpha = libspp_halpha_ne(width_angstrom, kt_ev)
    except Exception:
        return None
    result.setdefault("initial_ne_evaluation_kt", result.get("kt"))
    result["kt"] = kt_ev
    result["ne_evaluation_kt"] = kt_ev
    result["temperature_k"] = temperature_k
    result["ne"] = ne_value
    result["alpha"] = alpha
    width_std_angstrom = safe_float(
        result.get("corrected_lorentzian_width_std_angstrom"),
        math.inf,
    )
    result["ne_relative_uncertainty"] = _halpha_ne_relative_uncertainty(
        width_angstrom,
        width_std_angstrom,
        kt_ev,
    )
    result["temperature_coupled"] = True
    set_session_electron_density(
        app,
        ne_value,
        "H-alpha coupled to Saha-Boltzmann temperature",
    )
    return ne_value


def hydrogen_doppler_fwhm(wavelength: float, kt_ev: float) -> float:
    """Hydrogen Doppler FWHM in the same wavelength unit as ``wavelength``."""
    wavelength = abs(float(wavelength))
    kt_ev = float(kt_ev)
    if wavelength <= 0.0 or kt_ev <= 0.0:
        return 0.0
    hydrogen_rest_energy_ev = 938.783073793e6
    return wavelength * math.sqrt(8.0 * math.log(2.0) * kt_ev / hydrogen_rest_energy_ev)


class MultiGaussianFitWindow(tk.Toplevel):
    """Functional v6 replacement for the old dummy fit window.

    It uses the SDIMain autogauss model and scipy.optimize.curve_fit when available.
    Results are written back to TemplateLine.fitwavelen, .inte and .wg.
    """

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Gaussian / Voigt Fit - visible marked lines")
        self.geometry("900x560")
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Label(top, text="Range around selected analytical lines").pack(side="left")
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
        lines = self.candidate_lines()
        ok, message, results = self.fit_gaussian_lines(lines=lines)
        if ok:
            self.tree.delete(*self.tree.get_children())
            for idx, row in enumerate(results, start=1):
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        f"{row['fit_center']:.5f}",
                        f"{row['integrated_area']:.6g}",
                        f"{row['gaussian_width']:.6g}",
                        "0",
                        row.get("status", "Gaussian OK"),
                    ),
                )
        elif message:
            _showerror(self, "Fit Gaussian", message)

    def fit_gaussian_lines(
        self,
        lines=None,
        preserve_view=True,
        show_messages=True,
        line_overrides=None,
    ):
        """Fit the historical Palleschi multi-Gaussian on the current ROI.

        The model is exactly ``b0 + b1*x + sum(A*exp(-((x-x0)/s)^2))``.
        The analytical area passed to Saha-Boltzmann is ``A*s*sqrt(pi)``.
        This is an alternative profile for the same manual-fit workflow, not
        a second independent analysis path.
        """
        if np is None:
            message = "NumPy is not available."
            if show_messages:
                _showerror(self, "Fit Gaussian", message)
            return False, message, []
        try:
            from scipy.optimize import curve_fit
        except Exception:
            message = "SciPy optimization is not available. Install SciPy."
            if show_messages:
                _showerror(self, "Fit Gaussian", message)
            return False, message, []
        if not self.master_app.spectra:
            message = "Load a spectrum first."
            if show_messages:
                _showinfo(self, "Fit Gaussian", message)
            return False, message, []
        lines = list(lines or self.candidate_lines())
        if not lines:
            message = "No selected analytical line is visible in the current range."
            if show_messages:
                _showinfo(self, "Fit Gaussian", message)
            return False, message, []
        sp = select_spectrum_for_wavelengths(
            self.master_app,
            [safe_float(getattr(line, "wavelen", 0.0), 0.0) for line in lines],
        )
        if sp is None:
            message = "The selected lines do not belong to one acquired detector window."
            if show_messages:
                _showerror(self, "Fit Gaussian", message)
            return False, message, []
        xlim, ylim = self.master_app.current_plot_view()
        lo, hi = sorted(xlim)
        min_points = 2 + 3 * len(lines)
        xs = np.asarray([x for x in sp.x if lo <= x <= hi], dtype=float)
        ys = np.asarray([sp.y[i] for i,x in enumerate(sp.x) if lo <= x <= hi], dtype=float)
        if len(xs) < min_points:
            message = f"Too few spectrum points for Gaussian fit: {len(xs)} found, {min_points} required."
            if show_messages:
                _showinfo(self, "Fit Gaussian", message)
            return False, message, []
        line_overrides = line_overrides or {}
        width = max(float(xs[-1] - xs[0]), 1.0e-12)
        dx = float(np.median(np.diff(np.sort(xs)))) if len(xs) > 2 else width / 100.0
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        signal_scale = max(float(np.ptp(ys)), max(abs(float(value)) for value in ys), 1.0e-12)
        sigma_default = max(abs(safe_float(self.sigma_var.get(), 0.5)) / 2.0, abs(dx) * 0.5, 1.0e-9)
        half_window = max(
            abs(safe_float(getattr(self.master_app.options, "search_range", 0.1), 0.1)),
            width * 0.02,
            abs(dx) * 2.0,
        )
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        for t in lines:
            override = line_overrides.get(id(t), {})
            center0 = abs(safe_float(
                override.get("center"),
                getattr(t, "fitwavelen", 0.0) or getattr(t, "wavelen", 0.0),
            ))
            stored_wg = abs(safe_float(
                override.get("wg"),
                getattr(t, "wg", 0.0),
            ))
            sigma0 = stored_wg / 2.0 if stored_wg > 0.0 else sigma_default
            sigma0 = min(max(sigma0, abs(dx) * 0.25, 1.0e-9), width)
            amp = max(_nearest_y(sp.x, sp.y, center0) - baseline, signal_scale * 1.0e-9)
            p0.extend([amp, center0, sigma0])
            fix_center = bool(override.get("fix_center", False)) or safe_float(
                getattr(t, "fitwavelen", 0.0), 0.0
            ) < 0.0
            fix_sigma = bool(override.get("fix_wg", False))
            center_eps = max(abs(center0) * 1.0e-12, 1.0e-10)
            sigma_eps = max(abs(sigma0) * 1.0e-9, 1.0e-10)
            bounds_lo.extend([
                0.0,
                center0 - center_eps if fix_center else max(lo, center0 - half_window),
                max(1.0e-12, sigma0 - sigma_eps) if fix_sigma else max(abs(dx) * 0.25, 1.0e-12),
            ])
            bounds_hi.extend([
                np.inf,
                center0 + center_eps if fix_center else min(hi, center0 + half_window),
                sigma0 + sigma_eps if fix_sigma else max(width, sigma0 * 20.0),
            ])
        try:
            popt, _pcov = curve_fit(
                multigaussian_model,
                xs,
                ys,
                p0=p0,
                bounds=(bounds_lo, bounds_hi),
                maxfev=max(2000, self.master_app.options.iterations * 400),
            )
        except Exception as e:
            message = str(e)
            if show_messages:
                _showerror(self, "Fit Gaussian", message)
            return False, message, []
        fitted_y = multigaussian_model(xs, *popt)
        baseline_y = np.asarray(popt[0] + popt[1] * xs, dtype=float)
        component_overlays = []
        integration_bounds = []
        results = []
        for idx, t in enumerate(lines):
            amp, cen, sig = popt[2+3*idx], popt[3+3*idx], abs(popt[4+3*idx])
            area = palleschi_gaussian_area(amp, sig)
            t.fitwavelen = float(cen)
            t.inte = area
            t.wg = float(2.0 * sig)  # Historical pyLIBS Gaussian width convention.
            t.wl = 0.0
            t.fit_profile = "gaussian"
            _store_line_fit_provenance(t, sp)
            t.fitinte = float(amp)
            t.error_inte = 0.0
            curve = amp * np.exp(-((xs - cen) / max(sig, 1.0e-12)) ** 2)
            component_overlays.append((xs.tolist(), curve.tolist()))
            display_half_width = sig * math.sqrt(-math.log(0.005))
            integration_bounds.append((float(cen - display_half_width), float(cen + display_half_width)))
            results.append({
                "key": id(t),
                "template_wavelength": float(getattr(t, "wavelen", cen)),
                "fit_center": float(cen),
                "peak_intensity": float(amp),
                "lorentzian_width": 0.0,
                "gaussian_width": float(t.wg),
                "integrated_area": area,
                "replicate_area_count": 0,
                "replicate_area_total": 0,
                "line_label": (
                    f"{str(getattr(t, 'specie', '') or '').strip()} "
                    f"{_roman_ion(safe_int(getattr(t, 'ion', 0), 0))} "
                    f"{_template_line_nist_wavelength(t):.5f}"
                ).strip(),
                "source_window": str(getattr(sp, "name", "") or ""),
                "status": "Gaussian OK",
            })
        self.master_app.fit_overlay = (xs.tolist(), fitted_y.tolist())
        self.master_app.fit_baseline_overlay = (xs.tolist(), baseline_y.tolist())
        self.master_app.fit_component_overlays = component_overlays
        self.master_app.fit_integration_bounds = integration_bounds
        self.master_app.fit_overlay_label = "Gaussian sum"
        self.master_app.fit_component_label = "Gaussian"
        try:
            self.master_app.notify_template_changed(redraw=False)
        except Exception:
            pass
        self.master_app.redraw(preserve_view=preserve_view)
        if preserve_view:
            self.master_app.restore_plot_view(xlim, ylim)
        self.master_app.status(
            f"Gaussian fit: {len(lines)} line(s); area = A*sigma*sqrt(pi); "
            f"source={getattr(sp, 'name', '') or 'spectrum'}"
        )
        return True, f"Gaussian fit: {len(lines)} line(s)", results


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
        self._fit_current_visible_window("Fit Voigt")

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
                _showerror(self, "Fit Voigt", "NumPy is not available.")
            return False, "NumPy is not available.", []
        try:
            from scipy.optimize import curve_fit
        except Exception:
            msg = "SciPy optimization is not available. Install SciPy."
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
        if lines is None:
            lines = [t for t in self.master_app.template_lines if lo <= t.wavelen <= hi]
        else:
            lines = list(lines)
        if not lines:
            msg = "No marked line in the visible window. Use search/manual marking before fitting."
            if show_messages:
                _showinfo(self, "Fit Voigt", msg)
            return False, msg, []
        line_overrides = line_overrides or {}
        baseline_mode = _voigt_baseline_mode(self.master_app.options)
        integration_x = np.asarray(xs, dtype=float).copy()
        min_points = _voigt_free_parameter_count(lines, options=self.master_app.options, line_overrides=line_overrides)
        if len(xs) < min_points:
            msg = f"Too few spectrum points for Voigt fit: {len(xs)} found, {min_points} required."
            if show_messages:
                _showinfo(self, "Fit Voigt", msg)
            return False, msg, []
        xmin, xmax = float(xs.min()), float(xs.max())
        width = max(xmax - xmin, 1e-9)
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        # Estimate a sensible initial width from the x sampling and Options.
        dx = float(np.median(np.diff(np.sort(xs)))) if len(xs) > 2 else width/100.0
        # Options are used only to initialize fit windows.  During a fit,
        # per-row values edited in the open Manual/Automatic/Single Fit window
        # take precedence through line_overrides.  For the standalone Voigt
        # window, fall back to the template sign convention/options.
        default_fixed_wg = abs(safe_float(getattr(self.master_app.options, "fixed_wg", 0.5), 0.5))
        default_fixed_wl = abs(safe_float(getattr(self.master_app.options, "fixed_wl", 0.5), 0.5))
        auto_fwhm = _voigt_auto_fwhm(dx, width)
        min_sigma0 = max(abs(dx) * 0.25, 1e-6)
        min_gamma0 = max(abs(dx) * 0.25, 1e-6)
        sigma0 = max(auto_fwhm / 2.354820045, min_sigma0)
        gamma0 = max(auto_fwhm / 2.0, min_gamma0)
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        fixed_mask = [
            False,
            baseline_mode != "local_linear",
        ]
        half_window = max(abs(safe_float(self.range_var.get(), width / 20.0)), width * 0.02, abs(dx) * 2.0)
        for t in lines:
            override = line_overrides.get(id(t), {})
            center0 = abs(safe_float(override.get("center"), t.fitwavelen or t.wavelen)) if override else t.wavelen
            peak_y = _nearest_y(sp.x, sp.y, center0)
            height = _voigt_initial_height(peak_y, ys, baseline)
            if override:
                # Manual/Automatic/Single Fit rows are initialized from Options
                # when the window opens, but the user-edited row values and
                # checkboxes must take precedence at fit time.
                row_fix_wg = bool(override.get("fix_wg", False))
                row_fix_wl = bool(override.get("fix_wl", False))
                wg_fwhm = (
                    abs(safe_float(override.get("wg"), default_fixed_wg))
                    if row_fix_wg
                    else abs(safe_float(getattr(t, "wg", 0.0), 0.0)) or auto_fwhm
                )
                wl_fwhm = (
                    abs(safe_float(override.get("wl"), default_fixed_wl))
                    if row_fix_wl
                    else abs(safe_float(getattr(t, "wl", 0.0), 0.0)) or auto_fwhm
                )
            else:
                # Standalone Voigt Fit has no editor overrides, so use the
                # template sign convention and the current Options defaults.
                row_fix_wg = bool(getattr(self.master_app.options, "fix_wg", False)) or getattr(t, "wg", 0.0) < 0
                row_fix_wl = bool(getattr(self.master_app.options, "fix_wl", False)) or getattr(t, "wl", 0.0) < 0
                wg_fwhm = default_fixed_wg if row_fix_wg else (abs(t.wg) if getattr(t, "wg", 0.0) else auto_fwhm)
                wl_fwhm = default_fixed_wl if row_fix_wl else (abs(t.wl) if getattr(t, "wl", 0.0) else auto_fwhm)
            if row_fix_wg:
                sig0 = max(wg_fwhm / 2.354820045, 1e-12)
            else:
                sig0 = max(wg_fwhm / 2.354820045, min_sigma0)
            if row_fix_wl:
                gam0 = max(wl_fwhm / 2.0, 1e-12)
            else:
                gam0 = max(wl_fwhm / 2.0, min_gamma0)
            area0 = _voigt_initial_area(height, center0, sig0, gam0, dx)
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
                x_scale="jac",
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
            if baseline_mode == "libs_auto":
                integrated_area, integral_left, integral_right = (
                    _voigt_integral_to_baseline(
                        integration_x,
                        area,
                        cen,
                        sigma,
                        gamma,
                    )
                )
            else:
                integrated_area = float(area)
                integral_left = math.nan
                integral_right = math.nan
            t.fitwavelen = float(cen)
            t.inte = float(integrated_area)
            t.fit_profile = "voigt"
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
            self.tree.insert("", "end", values=(idx+1, f"{cen:.5f}", f"{integrated_area:.5g}", f"{t.wg:.5g}", f"{t.wl:.5g}", status))
            fit_results.append({
                "key": id(t),
                "template_wavelength": float(t.wavelen),
                "fit_center": float(cen),
                "peak_intensity": peak_height,
                "lorentzian_width": float(t.wl),
                "gaussian_width": float(t.wg),
                "profile_area": float(area),
                "integrated_area": float(integrated_area),
                "integration_left": float(integral_left),
                "integration_right": float(integral_right),
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
            ttk.Label(self, text="Matplotlib is not available.").pack(padx=20, pady=20)
            return
        self.fig = Figure(figsize=(12, 2.5), dpi=_figure_dpi(self))
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


class FitMaxfevDialog(tk.Toplevel):
    """Modal choice dialog for a fit stopped by the maxfev limit."""

    def __init__(self, master, message, can_accept=True):
        super().__init__(master)
        self.master_app = master
        self.choice = None
        self.title("Fit limit reached")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text=message,
            justify="left",
            wraplength=420,
        ).pack(fill="x", pady=(0, 10))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Continue fit", command=self.continue_fit).pack(side="left", padx=(0, 6))
        accept_state = "normal" if can_accept else "disabled"
        ttk.Button(buttons, text="Stop and accept", command=self.accept_fit, state=accept_state).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel fit", command=self.cancel).pack(side="right")

        self.grab_set()
        center_window(self, master)

    def _finish(self, choice):
        self.choice = choice
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def continue_fit(self):
        self._finish("continue")

    def accept_fit(self):
        self._finish("accept")

    def cancel(self):
        self._finish("cancel")


class NeHalphaWindow(tk.Toplevel):
    """H-alpha electron density checkpoint from SDIMain calcolh()/Ne_from_H flow."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.halpha_spectrum = None
        self._previous_spectra = None
        self._previous_wavelength_unit = None
        self.title("Electron Density from Hα")
        self.geometry("820x410")
        self.minsize(760, 350)
        self.protocol("WM_DELETE_WINDOW", self.close)
        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, padx=10, pady=10)
        primary_wavelength = safe_float(master.options.ha_wl1, 6562.8)
        if abs(primary_wavelength - 6565.0) < 1.0e-6:
            primary_wavelength = 6562.8
        labels = [
            ("Number of lines", str(master.options.ha_lines)),
            ("wl1", str(primary_wavelength)),
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
        actions = ttk.Frame(frm)
        actions.grid(row=0, column=2, rowspan=4, padx=15, sticky="n")
        ttk.Button(
            actions,
            text="Load H-alpha spectrum (no radiometric response)",
            command=self.load_halpha_spectrum,
        ).pack(fill="x", pady=(0, 5))
        ttk.Button(actions, text="Fit Hα and estimate Ne", command=self.run).pack(fill="x", pady=(0, 5))
        add_context_help_button(
            actions,
            self,
            "H-alpha electron density",
            (
                "Original Palleschi procedure: fit one or two Lorentzian H-alpha components, "
                "correct the primary Lorentzian width with the configured instrumental width, "
                "then calculate Ne with the SDIMain H-alpha relation. The dedicated loader applies "
                "dark/background and wavelength calibration, but radiometric response is not required."
            ),
        ).pack(anchor="e", pady=(8, 0))
        self.out = tk.Text(frm, height=13, width=92)
        self.out.grid(row=len(labels), column=0, columnspan=3, pady=8, sticky="nsew")
        frm.rowconfigure(len(labels), weight=1)
        frm.columnconfigure(2, weight=1)
        self.show_fit_window_on_spectrum()
        center_window(self, master)

    def load_halpha_spectrum(self):
        filename = filedialog.askopenfilename(
            parent=_prepare_messagebox_parent(self),
            title="Load H-alpha spectrum for Ne (radiometric response not required)",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=SPECTRUM_FILETYPES,
        )
        if not filename:
            return False
        return self.load_halpha_spectrum_path(filename)

    def load_halpha_spectrum_path(self, filename):
        remember_working_dir(self.master_app.options, filename)
        try:
            spectrum = self.master_app.load_halpha_spectrum_for_ne(filename)
        except Exception as exc:
            _showerror(self, "H-alpha spectrum", str(exc))
            return False
        if self._previous_spectra is None:
            self._previous_spectra = list(self.master_app.spectra)
            self._previous_wavelength_unit = getattr(self.master_app, "wavelength_unit", "nm")
        self.halpha_spectrum = spectrum
        spectrum.name = f"H-alpha width only: {Path(filename).name}"
        assign_default_spectrum_color(spectrum, 0)
        self.master_app.spectra = [spectrum]
        self.master_app.wavelength_unit = self.master_app.infer_wavelength_unit()
        self.master_app.fit_overlay = None
        self.master_app.redraw()
        self.show_fit_window_on_spectrum()
        self.master_app.status(
            "H-alpha loaded for Ne: dark/background and wavelength calibration applied; "
            "radiometric response bypassed."
        )
        return True

    def close(self):
        if self._previous_spectra is not None:
            self.master_app.spectra = self._previous_spectra
            self.master_app.wavelength_unit = self._previous_wavelength_unit
            self.master_app.fit_overlay = None
            try:
                self.master_app.redraw()
            except Exception:
                pass
        self.destroy()

    def _fit_spectrum(self):
        if self.halpha_spectrum is not None:
            return self.halpha_spectrum
        if self.master_app.spectra:
            return self.master_app.spectra[0]
        return None

    @staticmethod
    def _radiometric_response_note(spectrum):
        if getattr(spectrum, "halpha_response_bypassed", False):
            return "Radiometric response: bypassed for H-alpha width-only Ne analysis"
        if getattr(spectrum, "response_corrected", False):
            return "Radiometric response: applied"
        return "Radiometric response: not applied"

    def _identify_primary_halpha(self, spectrum, expected_center, fit_half_width, unit):
        search_limit = 1.5 if unit == "nm" else 15.0
        search_half_width = min(abs(float(fit_half_width)), search_limit)
        try:
            identification = identify_halpha_peak(
                spectrum.x,
                spectrum.y,
                expected_center,
                search_half_width,
            )
        except Exception as exc:
            _showerror(self, "H-alpha identification", str(exc))
            return None
        if identification["quality"] == "check":
            secondary = identification.get("secondary_center")
            secondary_text = (
                (
                    f"Second plausible maximum: {secondary:.6g} {unit}\n"
                    f"Second/selected prominence: "
                    f"{identification['ambiguity_ratio']:.3f}\n"
                )
                if secondary is not None
                else ""
            )
            shift_warning = (
                "The selected maximum is far from the expected wavelength.\n"
                if identification.get("large_shift")
                else ""
            )
            noise_warning = (
                "The peak prominence is less than five times the local noise.\n"
                if identification.get("low_signal_to_noise")
                else ""
            )
            proceed = _askyesno(
                self,
                "Ambiguous H-alpha identification",
                (
                    "The H-alpha assignment needs confirmation.\n\n"
                    f"Expected: {expected_center:.6g} {unit}\n"
                    f"Selected measured maximum: "
                    f"{identification['observed_center']:.6g} {unit}\n"
                    f"{secondary_text}"
                    f"{shift_warning}\n"
                    f"{noise_warning}"
                    "Continue using the selected maximum?"
                ),
            )
            if not proceed:
                return None
        return identification

    @staticmethod
    def _halpha_identification_output(identification, fitted_center, unit):
        return [
            "Identification: H I alpha",
            f"Expected/input center: {identification['expected_center']:.6g} {unit}",
            f"Observed local maximum: {identification['observed_center']:.6g} {unit}",
            f"Observed - expected: {identification['shift']:+.6g} {unit}",
            f"Fitted center: {fitted_center:.6g} {unit}",
            (
                "Fitted - observed maximum: "
                f"{fitted_center - identification['observed_center']:+.6g} {unit}"
            ),
            (
                f"Peak check: {identification['quality']}; "
                f"{identification['candidate_count']} local maximum/maxima in "
                f"+/-{identification['search_half_width']:.6g} {unit}"
            ),
            (
                "Peak prominence / local noise: "
                f"{identification['prominence_to_noise']:.4g}"
            ),
        ]

    def show_fit_window_on_spectrum(self):
        if self._fit_spectrum() is None or not getattr(self.master_app, "ax", None):
            self.master_app.status("H-alpha fit: load a spectrum before fitting.")
            return
        wl1 = safe_float(self.vars["wl1"].get(), self.master_app.options.ha_wl1)
        delta = abs(safe_float(self.vars["Delta"].get(), self.master_app.options.ha_range)) or 1.0
        unit = self.master_app.current_wavelength_unit_label()
        if unit == "nm" and wl1 > 1500.0:
            wl1, delta = wl1 / 10.0, delta / 10.0
        elif unit != "nm" and wl1 < 1500.0:
            wl1, delta = wl1 * 10.0, delta * 10.0
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

    def run_voigt(self):
        """Fit H-alpha as Voigt and propose one global instrumental FWHM."""
        if np is None:
            _showerror(self, "H-alpha Voigt", "NumPy is not available.")
            return
        try:
            from scipy.optimize import curve_fit
        except Exception:
            _showerror(self, "H-alpha Voigt", "SciPy optimization is not available.")
            return
        sp = self._fit_spectrum()
        if sp is None:
            _showinfo(self, "H-alpha Voigt", "Load the H-alpha spectrum first.")
            return

        nlines = 2 if safe_int(self.vars["Number of lines"].get(), self.master_app.options.ha_lines) == 2 else 1
        wl1 = safe_float(self.vars["wl1"].get(), self.master_app.options.ha_wl1)
        dl1 = abs(safe_float(self.vars["dl1"].get(), self.master_app.options.ha_dl1)) or 1.0
        wl2 = safe_float(self.vars["wl2"].get(), self.master_app.options.ha_wl2)
        dl2 = abs(safe_float(self.vars["dl2"].get(), self.master_app.options.ha_dl2)) or dl1
        delta = abs(safe_float(self.vars["Delta"].get(), self.master_app.options.ha_range)) or 1.0
        kt = safe_float(self.vars["kT"].get(), 1.0)
        unit = self.master_app.current_wavelength_unit_label()
        if unit == "nm" and wl1 > 1500.0:
            wl1, dl1, wl2, dl2, delta = wl1 / 10.0, dl1 / 10.0, wl2 / 10.0, dl2 / 10.0, delta / 10.0
        elif unit != "nm" and wl1 < 1500.0:
            wl1, dl1, wl2, dl2, delta = wl1 * 10.0, dl1 * 10.0, wl2 * 10.0, dl2 * 10.0, delta * 10.0

        identification = self._identify_primary_halpha(sp, wl1, delta, unit)
        if identification is None:
            return
        observed_primary_center = identification["observed_center"]
        center_search_half_width = identification["search_half_width"]
        lo, hi = wl1 - delta, wl1 + delta
        points = [(x, sp.y[i]) for i, x in enumerate(sp.x) if lo <= x <= hi]
        xs = np.asarray([x for x, _ in points], dtype=float)
        ys = np.asarray([y for _, y in points], dtype=float)
        minimum_points = 10 if nlines == 1 else 16
        if len(xs) < minimum_points:
            _showinfo(
                self,
                "H-alpha Voigt",
                f"Too few points around H-alpha: {len(xs)} found, {minimum_points} required.",
            )
            return

        baseline = float(np.percentile(ys, 5))
        signal_range = max(float(np.max(ys) - np.min(ys)), 1.0e-12)
        steps = sorted(abs(float(b - a)) for a, b in zip(xs, xs[1:]) if b != a)
        sampling = steps[len(steps) // 2] if steps else max(delta / 100.0, 1.0e-6)
        configured_width = max(
            0.0, safe_float(getattr(self.master_app.options, "instrumental_width", 0.0), 0.0)
        )
        doppler_guess = hydrogen_doppler_fwhm(wl1, kt)
        gaussian_fwhm0 = max(configured_width, doppler_guess, 2.0 * sampling)

        p0 = [baseline, 0.0]
        lower = [float(np.min(ys) - signal_range), -np.inf]
        upper = [float(np.max(ys) + signal_range), np.inf]
        expected = [(observed_primary_center, dl1)]
        if nlines == 2:
            expected.append((wl2, dl2))
        for line_index, (center0, lorentzian_fwhm0) in enumerate(expected):
            idx = int(np.argmin(np.abs(xs - center0)))
            height0 = max(float(ys[idx] - baseline), 0.25 * signal_range, 1.0e-12)
            area0 = height0 * max(lorentzian_fwhm0, gaussian_fwhm0, sampling) * 1.5
            sigma0 = gaussian_fwhm0 / 2.354820045
            gamma0 = max(lorentzian_fwhm0, 2.0 * sampling) / 2.0
            p0.extend([area0, min(max(center0, lo), hi), sigma0, gamma0])
            center_low = (
                max(lo, wl1 - center_search_half_width)
                if line_index == 0
                else lo
            )
            center_high = (
                min(hi, wl1 + center_search_half_width)
                if line_index == 0
                else hi
            )
            lower.extend([0.0, center_low, sampling * 0.05, sampling * 0.05])
            upper.extend([np.inf, center_high, max(delta, sampling), max(delta, sampling)])

        try:
            popt, pcov = curve_fit(
                multivoigt_model,
                xs,
                ys,
                p0=p0,
                bounds=(lower, upper),
                maxfev=max(20000, safe_int(getattr(self.master_app.options, "iterations", 20), 20) * 1000),
            )
        except Exception as exc:
            _showerror(self, "H-alpha Voigt", str(exc))
            return

        fitted = []
        for offset in range(2, len(popt), 4):
            area = abs(float(popt[offset]))
            center = float(popt[offset + 1])
            gaussian_fwhm = 2.354820045 * abs(float(popt[offset + 2]))
            lorentzian_fwhm = 2.0 * abs(float(popt[offset + 3]))
            fitted.append((area, center, gaussian_fwhm, lorentzian_fwhm))
        primary_area, primary_center, gaussian_fwhm, lorentzian_fwhm = fitted[0]
        try:
            lorentzian_width_std = 2.0 * math.sqrt(max(float(pcov[5, 5]), 0.0))
        except Exception:
            lorentzian_width_std = math.inf
        doppler_fwhm = hydrogen_doppler_fwhm(primary_center, kt)
        instrument_fwhm = math.sqrt(max(gaussian_fwhm * gaussian_fwhm - doppler_fwhm * doppler_fwhm, 0.0))
        width_angstrom = lorentzian_fwhm * (10.0 if unit == "nm" else 1.0)
        width_std_angstrom = lorentzian_width_std * (10.0 if unit == "nm" else 1.0)
        ne_relative_uncertainty = _halpha_ne_relative_uncertainty(
            width_angstrom,
            width_std_angstrom,
            kt,
        )
        try:
            ne_value, temperature_k, alfa = libspp_halpha_ne(width_angstrom, kt)
            ne_error = None
        except Exception as exc:
            ne_value, temperature_k, alfa = None, 11600.0 * kt, None
            ne_error = str(exc)

        fitted_y = multivoigt_model(xs, *popt)
        residual = ys - fitted_y
        ss_res = float(np.sum(residual * residual))
        centered = ys - float(np.mean(ys))
        ss_tot = float(np.sum(centered * centered))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else float("nan")
        self.master_app.fit_overlay = (xs.tolist(), fitted_y.tolist())
        self.master_app.redraw(preserve_view=True)

        output = [
            f"Model: baseline + slope + {nlines} Voigt component{'s' if nlines == 2 else ''}",
            self._radiometric_response_note(sp),
            f"Fit window: {lo:.6g} - {hi:.6g} {unit}",
            f"R^2: {r_squared:.7g}",
            f"kT: {kt:.6g} eV  (T approximately {temperature_k:.0f} K)",
            "",
        ]
        output.extend(
            self._halpha_identification_output(
                identification,
                primary_center,
                unit,
            )
        )
        output.append("")
        for index, (area, center, width_g, width_l) in enumerate(fitted, start=1):
            output.append(
                f"Line {index}: center={center:.6g} {unit}; area={area:.6g}; "
                f"Gaussian FWHM={width_g:.6g} {unit}; Lorentzian FWHM={width_l:.6g} {unit}"
            )
        output.extend([
            "",
            f"Hydrogen Doppler FWHM: {doppler_fwhm:.6g} {unit}",
            f"Estimated global instrumental FWHM: {instrument_fwhm:.6g} {unit}",
            "Calculation: sqrt(Gaussian FWHM^2 - hydrogen Doppler FWHM^2)",
        ])
        if ne_error:
            output.extend(["", f"Ne calculation failed: {ne_error}"])
        else:
            output.extend([
                f"Stark/Lorentzian FWHM used for Ne: {lorentzian_fwhm:.6g} {unit}",
                f"Lorentzian FWHM standard error: {lorentzian_width_std:.4g} {unit}",
                f"Estimated relative Ne uncertainty: {ne_relative_uncertainty:.3g}",
                f"Alpha correction: {alfa:.6g}",
                f"Ne: {ne_value:.6e} cm^-3",
            ])
            invalidate_self_absorption_analysis(self.master_app)
            set_session_electron_density(
                self.master_app,
                ne_value,
                "H-alpha Voigt fit",
            )

        self.master_app.last_halpha_result = {
            "available": ne_value is not None,
            "model": "Voigt",
            "center": primary_center,
            "lorentzian_width": lorentzian_fwhm,
            "corrected_lorentzian_width": lorentzian_fwhm,
            "corrected_lorentzian_width_angstrom": width_angstrom,
            "lorentzian_width_std": lorentzian_width_std,
            "corrected_lorentzian_width_std_angstrom": width_std_angstrom,
            "ne_relative_uncertainty": ne_relative_uncertainty,
            "gaussian_width": gaussian_fwhm,
            "doppler_width": doppler_fwhm,
            "estimated_instrumental_width": instrument_fwhm,
            "expected_center": identification["expected_center"],
            "observed_peak_center": identification["observed_center"],
            "observed_peak_shift": identification["shift"],
            "peak_identification_quality": identification["quality"],
            "peak_candidate_count": identification["candidate_count"],
            "peak_prominence_to_noise": identification["prominence_to_noise"],
            "intensity": float(
                primary_area
                * voigt_profile_unit(
                    np.asarray([primary_center], dtype=float),
                    primary_center,
                    gaussian_fwhm / 2.354820045,
                    lorentzian_fwhm / 2.0,
                )[0]
            ),
            "integral": primary_area,
            "kt": kt,
            "ne_evaluation_kt": kt,
            "temperature_k": temperature_k,
            "ne": ne_value,
            "alpha": alfa,
            "r_squared": r_squared,
            "formula": "Voigt H-alpha: Lorentzian FWHM -> Ne; Gaussian^2 = instrument^2 + Doppler^2",
            "radiometric_response_applied": bool(getattr(sp, "response_corrected", False)),
            "width_only_response_bypass": bool(getattr(sp, "halpha_response_bypassed", False)),
            "error": ne_error,
        }
        self.out.delete("1.0", "end")
        self.out.insert("end", "\n".join(output) + "\n")

        if instrument_fwhm > 0.0:
            use_width = _askyesno(
                self,
                "Use global instrumental width",
                (
                    f"Use {instrument_fwhm:.6g} {unit} as the single global instrumental FWHM "
                    "for every theoretical spectral line?\n\n"
                    "This is an effective estimate from the H-alpha Voigt Gaussian component after "
                    "subtracting hydrogen Doppler broadening."
                ),
            )
            if use_width:
                self.master_app.options.instrumental_width = instrument_fwhm
                save_pylibs_ini(self.master_app.options)
                theoretical = getattr(self.master_app, "theoretical_window", None)
                try:
                    if theoretical is not None and theoretical.winfo_exists():
                        theoretical.lsf_var.set(f"{instrument_fwhm:.7g}")
                except Exception:
                    pass
                output.append(f"Global instrumental FWHM saved: {instrument_fwhm:.6g} {unit}")
                self.out.delete("1.0", "end")
                self.out.insert("end", "\n".join(output) + "\n")

        status = (
            f"H-alpha Voigt complete; Ne={ne_value:.3e} cm^-3; global width estimate={instrument_fwhm:.4g} {unit}"
            if ne_value is not None
            else f"H-alpha Voigt complete; global width estimate={instrument_fwhm:.4g} {unit}"
        )
        self.master_app.status(status)

    def run(self):
        if np is None:
            _showerror(self, "Ne", "NumPy is not available.")
            return
        try:
            from scipy.optimize import curve_fit
        except Exception:
            _showerror(self, "Ne", "SciPy optimization is not available.")
            return
        sp = self._fit_spectrum()
        if sp is None:
            _showinfo(self, "Ne", "Load a spectrum first.")
            return
        nlines = 2 if safe_int(self.vars["Number of lines"].get(), self.master_app.options.ha_lines) == 2 else 1
        wl1 = safe_float(self.vars["wl1"].get(), self.master_app.options.ha_wl1)
        dl1 = abs(safe_float(self.vars["dl1"].get(), self.master_app.options.ha_dl1)) or 1.0
        wl2 = safe_float(self.vars["wl2"].get(), self.master_app.options.ha_wl2)
        dl2 = abs(safe_float(self.vars["dl2"].get(), self.master_app.options.ha_dl2)) or dl1
        delta = abs(safe_float(self.vars["Delta"].get(), self.master_app.options.ha_range)) or 1.0
        unit = self.master_app.current_wavelength_unit_label()
        if unit == "nm" and wl1 > 1500.0:
            wl1, dl1, wl2, dl2, delta = wl1 / 10.0, dl1 / 10.0, wl2 / 10.0, dl2 / 10.0, delta / 10.0
        elif unit != "nm" and wl1 < 1500.0:
            wl1, dl1, wl2, dl2, delta = wl1 * 10.0, dl1 * 10.0, wl2 * 10.0, dl2 * 10.0, delta * 10.0
        identification = self._identify_primary_halpha(sp, wl1, delta, unit)
        if identification is None:
            return
        observed_primary_center = identification["observed_center"]
        center_search_half_width = identification["search_half_width"]
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
        p0 = [
            baseline,
            self._initial_amplitude(xs, ys, observed_primary_center, baseline),
            observed_primary_center,
            dl1,
        ]
        lower = [
            float(min(ys) - abs(max(ys) - min(ys))),
            0.0,
            max(lo, wl1 - center_search_half_width),
            1e-9,
        ]
        upper = [
            float(max(ys) + abs(max(ys) - min(ys))),
            np.inf,
            min(hi, wl1 + center_search_half_width),
            max(2.0 * delta, dl1),
        ]
        if nlines == 2:
            wl2_start = min(max(wl2, lo), hi)
            p0.extend([self._initial_amplitude(xs, ys, wl2_start, baseline), wl2_start, dl2])
            lower.extend([0.0, lo, 1e-9])
            upper.extend([np.inf, hi, max(2.0 * delta, dl2)])
        try:
            popt, pcov = curve_fit(halpha_lorentzian_model, xs, ys, p0=p0, bounds=(lower, upper), maxfev=8000)
        except Exception as e:
            _showerror(self, "Ne", str(e)); return
        fitted = []
        for i in range(1, len(popt), 3):
            fitted.append((float(popt[i]), float(popt[i + 1]), abs(float(popt[i + 2]))))
        primary_width = fitted[0][2]
        primary_center = fitted[0][1]
        try:
            primary_width_std = math.sqrt(max(float(pcov[3, 3]), 0.0))
        except Exception:
            primary_width_std = math.inf
        fitted_y = halpha_lorentzian_model(xs, *popt)
        residual = ys - fitted_y
        ss_res = float(np.sum(residual * residual))
        centered = ys - float(np.mean(ys))
        ss_tot = float(np.sum(centered * centered))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else float("nan")
        inst = max(0.0, safe_float(getattr(self.master_app.options, "instrumental_width", 0.0), 0.0))
        if inst > 0.0 and getattr(self.master_app.options, "echelle", False):
            inst = inst / 5000.0 * primary_center
        if primary_width <= 0:
            corrected_lorentz = primary_width
        else:
            corrected_lorentz = max(primary_width - inst*inst/primary_width, 0.0)
        corrected_width_std = (
            primary_width_std * (1.0 + inst * inst / (primary_width * primary_width))
            if primary_width > 0.0 and math.isfinite(primary_width_std)
            else math.inf
        )
        kt = safe_float(self.vars["kT"].get(), 1.0)
        try:
            halpha_width_angstrom = corrected_lorentz * (
                10.0 if self.master_app.current_wavelength_unit_label() == "nm" else 1.0
            )
            halpha_width_std_angstrom = corrected_width_std * (
                10.0 if self.master_app.current_wavelength_unit_label() == "nm" else 1.0
            )
            ne_relative_uncertainty = _halpha_ne_relative_uncertainty(
                halpha_width_angstrom,
                halpha_width_std_angstrom,
                kt,
            )
            ne_value, T, alfa = libspp_halpha_ne(halpha_width_angstrom, kt)
            ne_error = None
        except Exception as e:
            halpha_width_angstrom = corrected_lorentz
            halpha_width_std_angstrom = math.inf
            ne_relative_uncertainty = math.inf
            ne_value, T, alfa = None, 11600.0 * kt, None
            ne_error = str(e)
        self.master_app.fit_overlay = (xs.tolist(), fitted_y.tolist())
        self.master_app.redraw(preserve_view=True)
        self.out.delete("1.0", "end")
        wavelength_unit = self.master_app.current_wavelength_unit_label()
        lines = [
            f"Fit window: {lo:.4f} - {hi:.4f} {wavelength_unit}",
            f"Model: baseline + {nlines} Lorentzian component{'s' if nlines == 2 else ''}",
            self._radiometric_response_note(sp),
            f"R^2: {r_squared:.7g}",
            f"kT: {kt:.6g}  (T ≈ {T:.0f} K)",
            "",
        ]
        lines.extend(
            self._halpha_identification_output(
                identification,
                primary_center,
                wavelength_unit,
            )
        )
        lines.append("")
        for idx, (_, center, width) in enumerate(fitted, start=1):
            lines.append(
                f"Line {idx}: center = {center:.4f} {wavelength_unit}, "
                f"Lorentzian FWHM = {width:.4f} {wavelength_unit}"
            )
        lines.extend([
            "",
            (
                f"Instrumental width: {inst:.4f} {wavelength_unit}"
                if inst > 0.0
                else "Instrumental width: not configured (no deconvolution)"
            ),
            f"Corrected primary Lorentzian width: {corrected_lorentz:.4f} {wavelength_unit}",
            f"Corrected width standard error: {corrected_width_std:.4g} {wavelength_unit}",
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
                "corrected_lorentzian_width_angstrom": halpha_width_angstrom,
                "lorentzian_width_std": primary_width_std,
                "corrected_lorentzian_width_std_angstrom": halpha_width_std_angstrom,
                "ne_relative_uncertainty": ne_relative_uncertainty,
                "gaussian_width": None,
                "expected_center": identification["expected_center"],
                "observed_peak_center": identification["observed_center"],
                "observed_peak_shift": identification["shift"],
                "peak_identification_quality": identification["quality"],
                "peak_candidate_count": identification["candidate_count"],
                "peak_prominence_to_noise": identification["prominence_to_noise"],
                "intensity": fitted[0][0] if fitted else None,
                "integral": None,
                "kt": kt,
                "ne_evaluation_kt": kt,
                "temperature_k": T,
                "ne": None,
                "alpha": alfa,
                "r_squared": r_squared,
                "formula": "H-alpha Stark broadening: Ne = 8.02e12 * (FWHM/alpha)^1.5",
                "radiometric_response_applied": bool(getattr(sp, "response_corrected", False)),
                "width_only_response_bypass": bool(getattr(sp, "halpha_response_bypassed", False)),
                "error": ne_error,
            }
            status = "H-alpha fit complete; Ne calculation failed"
        else:
            lines.extend([
                f"Alpha correction: {alfa:.6g}",
                f"Ne: {ne_value:.6e} cm^-3",
                f"Ne / 1e17: {ne_value / 1.0e17:.6g}",
                f"Estimated relative Ne uncertainty: {ne_relative_uncertainty:.3g}",
            ])
            invalidate_self_absorption_analysis(self.master_app)
            set_session_electron_density(
                self.master_app,
                ne_value,
                "H-alpha fit",
            )
            self.master_app.last_halpha_result = {
                "available": True,
                "center": primary_center,
                "lorentzian_width": primary_width,
                "corrected_lorentzian_width": corrected_lorentz,
                "corrected_lorentzian_width_angstrom": halpha_width_angstrom,
                "lorentzian_width_std": primary_width_std,
                "corrected_lorentzian_width_std_angstrom": halpha_width_std_angstrom,
                "ne_relative_uncertainty": ne_relative_uncertainty,
                "gaussian_width": None,
                "expected_center": identification["expected_center"],
                "observed_peak_center": identification["observed_center"],
                "observed_peak_shift": identification["shift"],
                "peak_identification_quality": identification["quality"],
                "peak_candidate_count": identification["candidate_count"],
                "peak_prominence_to_noise": identification["prominence_to_noise"],
                "intensity": fitted[0][0] if fitted else None,
                "integral": None,
                "kt": kt,
                "ne_evaluation_kt": kt,
                "temperature_k": T,
                "ne": ne_value,
                "alpha": alfa,
                "r_squared": r_squared,
                "formula": "H-alpha Stark broadening: Ne = 8.02e12 * (FWHM/alpha)^1.5",
                "radiometric_response_applied": bool(getattr(sp, "response_corrected", False)),
                "width_only_response_bypass": bool(getattr(sp, "halpha_response_bypassed", False)),
                "error": None,
            }
            status = f"H-alpha fit complete; Ne={ne_value:.3e} cm^-3"
        self.out.insert("end", "\n".join(lines) + "\n")
        self.master_app.status(status)


def _locked_post_irsac_saha_element(
    app: "MainWindow",
    fits: dict,
    included_elements: Optional[set[str]] = None,
) -> Optional[str]:
    """Keep the actual IRSAC thermometric element after corrections are applied."""
    correction_ready, _message = irsac_correction_status(
        getattr(app, "last_self_absorption_result", None),
        bool(getattr(app, "apply_sac_correction", False)),
    )
    if not correction_ready:
        return None
    workflow = getattr(app, "last_self_absorption_result", None) or {}
    thermometric = workflow.get("thermometric_species")
    if isinstance(thermometric, (tuple, list)) and thermometric:
        irsac_element = str(thermometric[0] or "").strip().capitalize()
        if (
            irsac_element
            and irsac_element in fits
            and (
                included_elements is None
                or irsac_element in included_elements
            )
        ):
            return irsac_element
    saha = getattr(app, "last_saha_boltzmann", None)
    if not isinstance(saha, dict):
        return None
    if str(saha.get("representative_mode", "") or "") != "most reliable element":
        return None
    element = str(saha.get("selected_element", "") or "").strip().capitalize()
    if not element or element not in fits:
        return None
    admitted = {
        str(row.get("element", "") or "").strip().capitalize()
        for row in saha.get("elements", [])
        if row.get("included")
    }
    if admitted and element not in admitted:
        return None
    if included_elements is not None and element not in included_elements:
        return None
    return element


def _worksheet_irsac_temperature_ev(app: "MainWindow") -> Optional[float]:
    """Return the applied IRSAC temperature when it is authoritative."""
    correction_ready, _message = irsac_correction_status(
        getattr(app, "last_self_absorption_result", None),
        bool(getattr(app, "apply_sac_correction", False)),
    )
    if not correction_ready:
        return None
    workflow = getattr(app, "last_self_absorption_result", None) or {}
    equation_mode = _canonical_irsac_equation_mode(
        workflow.get("equation_mode", "staged")
    )
    if equation_mode not in ("staged", "iterative", "excel_worksheet"):
        return None
    temperature_k = safe_float(workflow.get("temperature_k"), 0.0)
    return temperature_k / 11604.45 if temperature_k > 0.0 else None


def _canonical_irsac_equation_mode(value) -> str:
    mode = str(value or "staged").strip().lower()
    if mode in ("iterative", "pso", "yang2018", "yang_2018"):
        return "iterative"
    if mode in ("excel", "excel_worksheet", "worksheet"):
        return "excel_worksheet"
    return "staged"


def _irsac_configuration_mismatch(app: "MainWindow") -> str:
    """Explain why applied IRSAC factors no longer match the visible controls."""
    if not bool(getattr(app, "apply_sac_correction", False)):
        return ""
    workflow = getattr(app, "last_self_absorption_result", None)
    if not isinstance(workflow, dict):
        return "the applied IRSAC result is missing"
    used_equation = _canonical_irsac_equation_mode(
        workflow.get("equation_mode", "staged")
    )
    selected_equation = _canonical_irsac_equation_mode(
        getattr(app.options, "irsac_equation_mode", "staged")
    )
    if used_equation != selected_equation:
        return (
            f"the applied factors use {used_equation}, while the controls select "
            f"{selected_equation}"
        )
    used_mode = str(workflow.get("mode", "") or "").strip().lower()
    selected_mode = str(
        getattr(app.options, "irsac_mode", "") or ""
    ).strip().lower()
    if used_mode and selected_mode and used_mode != selected_mode:
        return (
            f"the applied factors use mode {used_mode}, while the controls select "
            f"{selected_mode}"
        )
    used_references = _parse_irsac_reference_lines(
        workflow.get("reference_lines", {})
    )
    selected_references = _active_irsac_reference_lines(app)
    if used_references != selected_references:
        return "the selected IRSAC line references changed after calculation"
    requested = workflow.get("requested_thermometric_species")
    if isinstance(requested, list):
        requested = tuple(requested)
    selected_thermometric = _parse_thermometric_species(
        getattr(app.options, "irsac_thermometric_species", "")
    )
    if requested != selected_thermometric:
        return "the thermometric IRSAC species changed after calculation"
    return ""


def _self_absorption_quantification_blocker(app: "MainWindow") -> str:
    """Reject diagnostic/manual corrections that are unsafe for quantification."""
    if not bool(getattr(app, "apply_sac_correction", False)):
        return ""
    workflow = getattr(app, "last_self_absorption_result", None)
    if not isinstance(workflow, dict):
        return "the applied self-absorption assessment is missing"
    mode = str(workflow.get("mode", "") or "").strip().lower()
    equation_mode = _canonical_irsac_equation_mode(
        workflow.get("equation_mode", "staged")
    )
    if mode in ("hybrid", "irsac", "yang", "yang/aslam"):
        if equation_mode == "staged":
            if not bool(workflow.get("converged", False)):
                return (
                    "the staged IRSAC temperature could not be calculated from "
                    "the selected thermometric species"
                )
            invalid = []
            for line in getattr(app, "template_lines", []) or []:
                if not bool(getattr(line, "sa_use", False)):
                    continue
                factor = safe_float(getattr(line, "sa_sac", 0.0), 0.0)
                if factor <= 0.0 or not math.isfinite(factor):
                    invalid.append(str(getattr(line, "specie", "") or "line"))
            if invalid:
                return "staged IRSAC contains a non-positive or non-finite factor"
            return ""
        if equation_mode != "iterative":
            return (
                "the selected IRSAC equation is a legacy worksheet comparison"
            )
        if not bool(workflow.get("converged", False)):
            return (
                "the selective IRSAC factors, decisions and thermometric "
                "temperature did not converge"
            )
    status = str(workflow.get("assessment_status", "") or "").strip()
    if status == "Correction unsafe":
        return (
            "the self-absorption assessment is Correction unsafe; remove the "
            "correction or refit/select a physically valid reference"
        )
    if not bool(workflow.get("assessment_can_apply", False)):
        return (
            f"the self-absorption assessment is {status or 'not assessable'} "
            "and has no independent support for quantitative correction"
        )
    unsupported = []
    for line in getattr(app, "template_lines", []) or []:
        if not bool(getattr(line, "sa_use", False)):
            continue
        factor = safe_float(getattr(line, "sa_sac", 0.0), 0.0)
        if factor <= 0.0 or not math.isfinite(factor):
            continue
        if not bool(getattr(line, "sa_recommended", False)):
            label = (
                f"{getattr(line, 'specie', '')} "
                f"{_roman_ion(safe_int(getattr(line, 'ion', 0), 0))} "
                f"{abs(safe_float(getattr(line, 'asswavelen', 0.0), 0.0)):.6g}"
            ).strip()
            unsupported.append(label or "unidentified line")
    if unsupported:
        preview = ", ".join(unsupported[:4])
        if len(unsupported) > 4:
            preview += ", ..."
        return (
            "manual override enabled unsupported correction row(s): "
            f"{preview}"
        )
    return ""


def _worksheet_irsac_temperature_source(app: "MainWindow") -> str:
    workflow = getattr(app, "last_self_absorption_result", None) or {}
    thermometric = workflow.get("thermometric_species")
    if isinstance(thermometric, (tuple, list)) and len(thermometric) >= 2:
        element = str(thermometric[0] or "").strip().capitalize()
        ion = safe_int(thermometric[1], 0)
        label = f"{element} {_roman_ion(ion)}".strip()
    else:
        label = "selected reference"
    equation_mode = _canonical_irsac_equation_mode(
        workflow.get("equation_mode", "staged")
    )
    if equation_mode == "staged":
        return f"staged IRSAC T ({label})"
    if equation_mode == "iterative":
        temperature_mode = str(
            workflow.get("thermometric_temperature_mode", "thermometric lines")
            or "thermometric lines"
        )
        return f"selective IRSAC T ({label}; {temperature_mode})"
    return f"legacy IRSAC worksheet T ({label})"


def _saha_visible_groups(groups, included_elements):
    """Return only elements explicitly included in the current Saha analysis."""
    included = {
        str(element or "").strip().capitalize()
        for element in (included_elements or set())
        if str(element or "").strip()
    }
    return {
        element: points
        for element, points in groups.items()
        if str(element or "").strip().capitalize() in included
    }


def _saha_merge_display_groups(groups, diagnostic_groups):
    """Merge quantitative and diagnostic points without changing fit inputs."""
    merged = {
        element: list(points)
        for element, points in (groups or {}).items()
    }
    seen = {
        id(point.get("line"))
        for points in merged.values()
        for point in points
        if point.get("line") is not None
    }
    for element, points in (diagnostic_groups or {}).items():
        target = merged.setdefault(element, [])
        for point in points:
            line = point.get("line")
            if line is not None and id(line) in seen:
                continue
            target.append(point)
            if line is not None:
                seen.add(id(line))
    return merged


def _saha_plot_fit_results(app, groups, fits, representative_kt):
    """Use free slopes before IRSAC and a common slope only after application."""
    correction_ready, _message = irsac_correction_status(
        getattr(app, "last_self_absorption_result", None),
        bool(getattr(app, "apply_sac_correction", False)),
    )
    if not correction_ready or not representative_kt or representative_kt <= 0.0:
        return fits, False
    return (
        libspp_refit_saha_fixed_temperature(app, groups, representative_kt),
        True,
    )


class SahaBoltzmannWindow(tk.Toplevel):
    """v6 Saha-Boltzmann front-end using current fitted template lines."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Saha-Boltzmann")
        self.geometry("1050x700")
        self.minsize(880, 560)
        self.saha_groups = {}
        self.saha_display_groups = {}
        self.saha_fits = {}
        self.included_elements = set()
        self.diagnostic_elements = set()
        self.blocked_elements = set()
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
        self.mode_var = tk.StringVar(value="Most reliable element")
        ttk.Label(left, text="Temperature").pack(side="left", padx=(12, 3))
        ttk.Combobox(
            left,
            textvariable=self.mode_var,
            values=("Most reliable element", "Single element temperature", "Mean temperature"),
            width=24,
            state="readonly",
        ).pack(side="left")
        self.mode_var.trace_add("write", lambda *_args: self.on_mode_changed())
        ttk.Label(left, text="Initial kT (eV)").pack(side="left", padx=(12, 3))
        self.initial_kt_var = tk.StringVar(value="1")
        ttk.Entry(left, textvariable=self.initial_kt_var, width=8).pack(side="left")
        right = ttk.Frame(top)
        right.pack(side="right", fill="x", expand=True)
        self.summary_var = tk.StringVar(value="Ready")
        ttk.Label(right, textvariable=self.summary_var, width=38).pack(side="left", padx=(12, 8), fill="x", expand=True)
        ttk.Button(right, text="Check SA", command=self.open_sac_check).pack(side="right")
        ttk.Button(right, text="Check Lines", command=self.open_line_diagnostics).pack(side="right", padx=(0, 4))
        cols=("use", "element", "lines", "levels", "dEk eV", "kT eV", "R2", "LOO dT/T", "q", "Z I", "Z II")
        self.tree=ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=90, anchor="center")
        self.tree.heading("use", text="Use / role")
        self.tree.column("use", width=95, anchor="center")
        self.tree.column("element", width=70, anchor="center")
        self.tree.pack(fill="x", padx=6, pady=5)
        self.tree.bind("<Double-1>", self.toggle_selected_element)
        self.tree.bind("<space>", self.toggle_selected_element)
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_changed)
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(self, text="Matplotlib is not available.").pack(fill="both", expand=True, padx=10, pady=10)
            self.fig = self.ax = self.canvas = None
        else:
            self.fig = Figure(figsize=(9, 4.8), dpi=_figure_dpi(self))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
            self.canvas.mpl_connect("button_press_event", self.on_plot_click)
        self.plot_points = []
        self.after(100, self.compute)

    def compute(self):
        selected_before = self.selected_element() if self.saha_fits else None
        if selected_before:
            self._selected_element_override = selected_before
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
            coupled_ne = recompute_halpha_ne_for_temperature(
                self.master_app,
                kt,
            )
            if coupled_ne is not None and coupled_ne > 0.0:
                ne = coupled_ne
            groups, skipped = libspp_saha_boltzmann_groups(
                self.master_app,
                ne,
                kt,
            )
            fits = libspp_fit_saha_boltzmann(self.master_app, groups)
            mode = self.mode_var.get()
            if mode == "Most reliable element":
                reference = (
                    _locked_post_irsac_saha_element(self.master_app, fits)
                    or select_most_reliable_saha_element(
                        self.master_app,
                        fits,
                        self.master_app.options.kt_low,
                        self.master_app.options.kt_high,
                    )
                )
                new_kt = (
                    _worksheet_irsac_temperature_ev(self.master_app)
                    or safe_float(fits.get(reference, {}).get("kt", 0.0), 0.0)
                )
            elif mode == "Single element temperature":
                reference = getattr(self, "_selected_element_override", None)
                new_kt = safe_float(fits.get(reference, {}).get("kt", 0.0), 0.0)
            else:
                new_kt = libspp_weighted_temperature(
                    fits,
                    self.master_app.options.kt_low,
                    self.master_app.options.kt_high,
                )
            if new_kt <= 0.0:
                new_kt = libspp_weighted_temperature(fits, 0.0, float("inf"))
            if new_kt <= 0.0:
                break
            temperature_converged = abs(new_kt - kt) / new_kt <= 0.01
            final_ne = recompute_halpha_ne_for_temperature(
                self.master_app,
                new_kt,
            )
            ne_converged = True
            if final_ne is not None and final_ne > 0.0:
                ne_converged = abs(final_ne - ne) / final_ne <= 0.01
                ne = final_ne
            if temperature_converged and ne_converged:
                kt = new_kt
                groups, skipped = libspp_saha_boltzmann_groups(
                    self.master_app,
                    ne,
                    kt,
                )
                fits = libspp_fit_saha_boltzmann(self.master_app, groups)
                break
            kt = new_kt
        if fits and kt > 0.0:
            final_ne = recompute_halpha_ne_for_temperature(
                self.master_app,
                kt,
            )
            if final_ne is not None and final_ne > 0.0:
                ne = final_ne
            groups, skipped = libspp_saha_boltzmann_groups(
                self.master_app,
                ne,
                kt,
            )
            fits = libspp_fit_saha_boltzmann(self.master_app, groups)
        diagnostic_groups = libspp_saha_boltzmann_diagnostic_groups(
            self.master_app,
            ne,
            kt,
        )
        display_groups = _saha_merge_display_groups(groups, diagnostic_groups)
        selected_elements = _selected_analysis_elements(self.master_app)
        if selected_elements is None:
            selected_elements = set(display_groups)
        if not fits:
            diagnostics = saha_template_line_diagnostics(self.master_app, ne=ne, kt=kt)
            message = saha_no_fit_message(diagnostics, groups)
            usable = sum(1 for item in diagnostics if item["usable"])
            self.summary_var.set(
                f"No valid Saha-Boltzmann fit; {usable}/{len(diagnostics)} line(s) ready"
            )
            _showinfo(
                self,
                "Saha-Boltzmann",
                message + "\n\nUse Check Lines to inspect every row.",
            )
            self.saha_groups = groups
            self.saha_display_groups = display_groups
            self.saha_fits = {}
            self.skipped_lines = skipped
            self.current_ne = ne
            self.included_elements = set()
            self.diagnostic_elements = set(display_groups)
            self.blocked_elements = set(selected_elements) - set(display_groups)
            self.auto_excluded_elements = set()
            self.representative_kt = None
            self.populate_tree()
            self._draw_plot(display_groups, {}, None)
            return
        self.saha_groups = groups
        self.saha_display_groups = display_groups
        self.saha_fits = fits
        self.skipped_lines = skipped
        self.current_ne = ne
        self.included_elements = self._default_included_elements(fits)
        self.auto_excluded_elements = set(fits.keys()) - set(self.included_elements)
        self.diagnostic_elements = (
            set(display_groups) - set(self.included_elements)
        )
        self.blocked_elements = set(selected_elements) - set(display_groups)
        self.representative_kt = self._representative_temperature()
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
        reliable = self._most_reliable_element()
        mode = self.mode_var.get()
        for element, result in sorted(self.saha_fits.items()):
            quality = saha_fit_quality(self.master_app, result)
            if element not in self.included_elements:
                role = "No"
            elif mode == "Most reliable element":
                if element == reliable:
                    role = (
                        "Reference"
                        if quality["quantitative_eligible"]
                        else "Reference CHECK"
                    )
                else:
                    role = "Fit"
            elif mode == "Single element temperature":
                role = "Selected" if element == self.selected_element() else "Fit"
            else:
                role = "Yes" if element in self.included_elements else "No"
            loo = quality["loo_relative_span"]
            self.tree.insert("", "end", iid=element, values=(
                role,
                element,
                result["nlines"],
                quality["distinct_levels"],
                f"{quality['energy_span_ev']:.4g}",
                f"{result['kt']:.4g}",
                f"{quality['r2']:.4f}",
                f"{loo:.3f}" if math.isfinite(loo) else "N/A",
                f"{result['q']:.4g}",
                f"{result['z1']:.4g}",
                f"{result['z2']:.4g}",
            ))
        missing_fit_elements = (
            set(self.saha_display_groups)
            | set(self.blocked_elements)
        ) - set(self.saha_fits)
        for element in sorted(missing_fit_elements):
            points = list(self.saha_display_groups.get(element, []) or [])
            active_points = [point for point in points if not point.get("inactive")]
            energies = sorted({
                round(safe_float(point.get("x"), 0.0), 12)
                for point in active_points
            })
            energy_span = (
                max(energies) - min(energies)
                if len(energies) >= 2
                else 0.0
            )
            role = "Diagnostic" if active_points else "Blocked"
            self.tree.insert("", "end", iid=element, values=(
                role,
                element,
                len(active_points),
                len(energies),
                f"{energy_span:.4g}",
                "--",
                "--",
                "--",
                "--",
                "--",
                "--",
            ))
        preferred = (
            reliable if mode == "Most reliable element"
            else getattr(self, "_selected_element_override", None)
        )
        if preferred in self.saha_fits:
            self.tree.selection_set(preferred)
            self.tree.focus(preferred)

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

    def _most_reliable_element(self):
        low, high = self._temperature_range()
        candidate_fits = {
            element: result
            for element, result in self.saha_fits.items()
            if element in self.included_elements
        }
        locked = _locked_post_irsac_saha_element(
            self.master_app,
            candidate_fits,
            self.included_elements,
        )
        if locked:
            return locked
        return select_most_reliable_saha_element(
            self.master_app,
            candidate_fits,
            low,
            high,
        )

    def _representative_temperature(self):
        if self.mode_var.get() == "Mean temperature":
            return self._mean_temperature()
        if self.mode_var.get() == "Single element temperature":
            element = self.selected_element()
            result = self.saha_fits.get(element) if element in self.included_elements else None
            return safe_float(result.get("kt", 0.0), 0.0) if result else None
        worksheet_temperature = _worksheet_irsac_temperature_ev(self.master_app)
        if worksheet_temperature:
            return worksheet_temperature
        element = self._most_reliable_element()
        result = self.saha_fits.get(element) if element else None
        return safe_float(result.get("kt", 0.0), 0.0) if result else None

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
        preferred = getattr(self, "_selected_element_override", None)
        if preferred in self.saha_fits:
            return preferred
        return next(iter(sorted(self.saha_fits)), None)

    def toggle_selected_element(self, event=None):
        element = self.selected_element()
        if not element:
            return "break"
        if element not in self.saha_fits:
            points = list(self.saha_display_groups.get(element, []) or [])
            _showinfo(
                self,
                "Saha-Boltzmann",
                f"{element} is recognized and shown diagnostically, but it has "
                f"only {len(points)} usable point(s). At least two accepted lines "
                "with different upper energies are required before it can enter "
                "the fit, IRSAC, or CF-LIBS.",
            )
            return "break"
        if element in self.included_elements:
            self.included_elements.remove(element)
        else:
            self.included_elements.add(element)
        self.populate_tree()
        self.tree.selection_set(element)
        self.representative_kt = self._representative_temperature()
        if self.mode_var.get() == "Mean temperature":
            if self.representative_kt is None:
                self.representative_kt = self.last_valid_mean_kt
                self.summary_var.set("All elements excluded; mean temperature unchanged")
                _showwarning(self, "Saha-Boltzmann", "All elements are excluded from the analysis.")
            else:
                self.last_valid_mean_kt = self.representative_kt
        action = "included in" if element in self.included_elements else "excluded from"
        self.master_app.status(
            f"Saha-Boltzmann: {element} {action} IRSAC and CF-LIBS; double-click to toggle."
        )
        self.refresh_temperature_display()
        return "break"

    def on_mode_changed(self, event=None):
        self.representative_kt = self._representative_temperature()
        self.refresh_temperature_display()

    def on_selection_changed(self, event=None):
        if self.mode_var.get() == "Single element temperature":
            selected = self.tree.selection()
            if selected:
                self._selected_element_override = selected[0]
            self.refresh_temperature_display()

    def refresh_temperature_display(self):
        if not self.saha_fits:
            return
        if _loaded_response_is_opc(self.master_app):
            opc_name = Path(
                str(getattr(self.master_app, "active_opc_path", "") or "")
            ).name or "OPC"
            opc_id = str(
                getattr(self.master_app, "active_opc_id", "") or "unknown"
            )
            response_text = f"OPC {opc_name} [ID {opc_id}]"
        else:
            response_text = (
                "Apply After response correction used"
                if _apply_after_response_enabled(self.master_app)
                else "no Apply After response correction"
            )
        selected_element = None
        representative_mode = "mean temperature"
        if self.mode_var.get() == "Single element temperature":
            element = self.selected_element()
            selected_element = element
            representative_mode = "selected element"
            result = (
                self.saha_fits.get(element)
                if element and element in self.included_elements
                else None
            )
            if result:
                representative_kt = result["kt"]
                self.summary_var.set(
                    f"{element} kT={representative_kt:.4g} eV, Ne={self.current_ne:.3e} e/cm3, skipped {self.skipped_lines}; {response_text}"
                )
                self.master_app.status(f"Saha-Boltzmann: {element} kT={representative_kt:.4g} eV")
            else:
                representative_kt = None
                self.summary_var.set("Select an element for single-element temperature")
        elif self.mode_var.get() == "Most reliable element":
            selected_element = self._most_reliable_element()
            representative_mode = "most reliable element"
            result = self.saha_fits.get(selected_element) if selected_element else None
            worksheet_temperature = _worksheet_irsac_temperature_ev(self.master_app)
            representative_kt = worksheet_temperature or (
                safe_float(result.get("kt", 0.0), 0.0) if result else None
            )
            if representative_kt:
                quality = saha_fit_quality(self.master_app, result)
                source_label = (
                    _worksheet_irsac_temperature_source(self.master_app)
                    if worksheet_temperature
                    else f"Widest dEk reference {selected_element}"
                )
                quality_label = (
                    "quantitative quality passed"
                    if quality["quantitative_eligible"]
                    else "diagnostic reference only"
                )
                self.summary_var.set(
                    f"{source_label}: kT={representative_kt:.4g} eV, "
                    f"{quality['nlines']} lines/{quality['distinct_levels']} levels, "
                    f"LOO dT/T={quality['loo_relative_span']:.3f}; {quality_label}; "
                    + (
                        "post-IRSAC common slope used for other elements; "
                        if worksheet_temperature
                        else "pre-IRSAC slopes remain independently fitted; "
                    )
                    + response_text
                )
                self.master_app.status(
                    f"Saha-Boltzmann: dEk reference {selected_element}, kT={representative_kt:.4g} eV"
                )
            else:
                self.summary_var.set("No reliable element has at least 3 lines and 3 distinct energies")
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
            worksheet_temperature = _worksheet_irsac_temperature_ev(self.master_app)
            if worksheet_temperature and representative_mode == "most reliable element":
                temperature_source = _worksheet_irsac_temperature_source(self.master_app)
            else:
                temperature_source = (
                    "selected element" if representative_mode == "selected element"
                    else "most reliable element" if representative_mode == "most reliable element"
                    else "Saha-Boltzmann mean"
                )
            self.master_app.session_temperature = representative_kt
            self.master_app.session_temperature_source = temperature_source
            correction_ready, _correction_message = irsac_correction_status(
                getattr(self.master_app, "last_self_absorption_result", None),
                bool(getattr(self.master_app, "apply_sac_correction", False)),
            )
            if correction_ready and representative_mode == "most reliable element":
                post_source = (
                    _worksheet_irsac_temperature_source(self.master_app)
                    if worksheet_temperature
                    else f"post-IRSAC most reliable element: {selected_element}"
                )
                self.master_app.post_irsac_temperature = representative_kt
                self.master_app.post_irsac_temperature_source = post_source
                self.master_app.session_temperature_source = post_source
                workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
                if isinstance(workflow_result, dict):
                    workflow_result["post_temperature_ev"] = representative_kt
                    workflow_result["post_temperature_source"] = post_source
            else:
                self.master_app.post_irsac_temperature = None
                self.master_app.post_irsac_temperature_source = None
                workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
                if isinstance(workflow_result, dict):
                    workflow_result.pop("post_temperature_ev", None)
                    workflow_result.pop("post_temperature_source", None)
        else:
            self.master_app.post_irsac_temperature = None
            self.master_app.post_irsac_temperature_source = None
            workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
            if isinstance(workflow_result, dict):
                workflow_result.pop("post_temperature_ev", None)
                workflow_result.pop("post_temperature_source", None)
        low, high = self._temperature_range()
        self.master_app.last_saha_boltzmann = {
            "elements": [
                {
                    "element": element,
                    "temperature": result.get("kt"),
                    "nlines": result.get("nlines"),
                    "quality": saha_fit_quality(self.master_app, result),
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
            "electron_density_source": str(
                getattr(self.master_app, "session_ne_source", "")
                or "unspecified source"
            ),
            "intensity_mode": _boltzmann_intensity_mode(self.master_app),
            "ordinate_formula": _boltzmann_formula(self.master_app),
            "skipped_lines": self.skipped_lines,
            "post_irsac_temperature": getattr(self.master_app, "post_irsac_temperature", None),
            "post_irsac_temperature_source": getattr(self.master_app, "post_irsac_temperature_source", None),
        }
        _refresh_theoretical_workflow_ui(self.master_app)
        diagnostic_count = len(self.diagnostic_elements)
        blocked_count = len(self.blocked_elements)
        if diagnostic_count or blocked_count:
            current = self.summary_var.get()
            self.summary_var.set(
                current
                + f"; diagnostic elements={diagnostic_count}, blocked={blocked_count}"
            )
        current = self.summary_var.get()
        ne_source = str(
            getattr(self.master_app, "session_ne_source", "")
            or "unspecified source"
        )
        self.summary_var.set(current + f"; Ne source={ne_source}")
        self._draw_plot(
            self.saha_display_groups,
            self.saha_fits,
            representative_kt,
        )

    def _electron_density(self):
        ne, _source = active_electron_density(self.master_app)
        if ne is not None:
            return ne
        previous = safe_float(
            getattr(self.master_app, "last_known_ne", 0.0),
            0.0,
        )
        previous_source = str(
            getattr(self.master_app, "last_known_ne_source", "")
            or "unknown source"
        )
        prompt = "No electron density is active for this measurement.\nEnter Ne (e/cm3)."
        kwargs = {}
        if previous > 0.0:
            prompt += (
                f"\n\nPrevious value: {previous:.6e} e/cm3"
                f"\nSource: {previous_source}"
                "\nConfirm it deliberately or replace it."
            )
            kwargs["initialvalue"] = previous
        ne = simpledialog.askfloat(
            "Electron Density",
            prompt,
            minvalue=0.0,
            parent=_prepare_messagebox_parent(self),
            **kwargs,
        )
        if ne is None:
            return None
        source = "manual entry in Saha-Boltzmann"
        if previous > 0.0 and abs(ne - previous) <= max(previous * 1.0e-9, 1.0):
            source = f"confirmed previous Ne ({previous_source})"
        return set_session_electron_density(self.master_app, ne, source)

    def _clear_plot(self):
        if self.ax is None:
            return
        self.plot_points = []
        self.ax.clear()
        self.canvas.draw_idle()

    def _draw_plot(self, groups, fits, representative_kt=None):
        if self.ax is None:
            return
        visible_elements = set(self.included_elements) | set(self.diagnostic_elements)
        groups = _saha_visible_groups(groups, visible_elements)
        quantitative_groups = {
            element: [
                point for point in points
                if not point.get("diagnostic_only", False)
            ]
            for element, points in groups.items()
        }
        plot_fits, common_slope = _saha_plot_fit_results(
            self.master_app,
            quantitative_groups,
            fits,
            representative_kt,
        )
        plot_xlim = self._plot_x_limits(groups)
        self.plot_points = []
        self.ax.clear()
        self.ax.set_title("Saha-Boltzmann")
        self.ax.set_xlabel("Upper energy / Saha-Boltzmann coordinate (eV)")
        self.ax.set_ylabel(_boltzmann_formula(self.master_app))
        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]
        for group_idx, (element, pts) in enumerate(sorted(groups.items())):
            if not pts:
                continue
            alpha = 1.0
            color = colors[group_idx % len(colors)] if colors else "#1f77b4"
            label_used = False
            for p in pts:
                inactive = bool(p.get("inactive"))
                diagnostic_only = bool(p.get("diagnostic_only")) or (
                    element not in self.included_elements
                )
                point_color = "0.6" if inactive else color
                label = (
                    f"{element} (diagnostic)"
                    if diagnostic_only and not label_used
                    else element if not label_used
                    else "_nolegend_"
                )
                plot_y, sac_marker = _sac_corrected_plot_y(self.master_app, p)
                marker = "*" if sac_marker else "D" if diagnostic_only else "o"
                size = 70 if sac_marker else 24
                scatter_kwargs = {
                    "s": size,
                    "marker": marker,
                    "alpha": 0.65 if inactive or diagnostic_only else alpha,
                    "label": label,
                }
                if diagnostic_only and not sac_marker:
                    scatter_kwargs.update(
                        facecolors="none",
                        edgecolors=point_color,
                        linewidths=1.2,
                    )
                else:
                    scatter_kwargs["color"] = point_color
                self.ax.scatter([p["x"]], [plot_y], **scatter_kwargs)
                self.plot_points.append({"x": p["x"], "y": plot_y, "line": p.get("line"), "inactive": inactive})
                label_used = True
            result = fits.get(element)
            if result:
                plot_fit = plot_fits.get(element)
                if plot_fit and plot_xlim:
                    x0, x1 = plot_xlim
                    intercept = (
                        plot_fit.get("q_fixed")
                        if common_slope
                        else plot_fit.get("q")
                    )
                    y0 = plot_fit["slope"] * x0 + intercept
                    y1 = plot_fit["slope"] * x1 + intercept
                    self.ax.plot(
                        [x0, x1],
                        [y0, y1],
                        linewidth=1.0,
                        alpha=0.55 if element in self.diagnostic_elements else alpha,
                        linestyle="--" if element in self.diagnostic_elements else "-",
                    )
        if plot_xlim:
            self.ax.set_xlim(*plot_xlim)
        self.ax.margins(x=0.05, y=0.05)
        if plot_xlim:
            self.ax.set_xlim(*plot_xlim)
        if any(groups.values()):
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
        sync = getattr(win, "sync_session_inputs", None)
        if callable(sync):
            sync()
            win.compute()
        bring_window_to_front(win, self)
        return win

    def open_sac_check(self):
        win = self.master_app.show_sac_check()
        bring_window_to_front(win, self)
        return win

    def open_line_diagnostics(self):
        win = getattr(self, "line_diagnostics_window", None)
        try:
            if win is not None and win.winfo_exists():
                win.refresh()
                bring_window_to_front(win, self)
                return win
        except Exception:
            pass
        self.line_diagnostics_window = SahaLineDiagnosticsWindow(self)
        return self.line_diagnostics_window

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


class SahaLineDiagnosticsWindow(tk.Toplevel):
    """Explain why each selected line can or cannot enter Saha-Boltzmann."""

    columns = ("row", "wavelength", "fit_center", "species", "ion", "area", "Ek", "Aki", "gk", "status")

    def __init__(self, master):
        super().__init__(master)
        self.saha_window = master
        self.master_app = master.master_app
        self.title("Saha-Boltzmann Line Check")
        self.geometry("1220x560")
        self.minsize(900, 380)

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(top, text="Selected Lines", command=self.open_selected_lines).pack(side="right", padx=4)
        ttk.Button(top, text="Auto Fit (Voigt)", command=self.open_auto_fit).pack(side="right")

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        widths = {
            "row": 48,
            "wavelength": 105,
            "fit_center": 105,
            "species": 75,
            "ion": 55,
            "area": 105,
            "Ek": 100,
            "Aki": 105,
            "gk": 55,
            "status": 430,
        }
        headings = {
            "wavelength": "NIST wavelength",
            "fit_center": "Voigt center",
        }
        for column in self.columns:
            self.tree.heading(column, text=headings.get(column, column))
            self.tree.column(
                column,
                width=widths[column],
                anchor="w" if column == "status" else "center",
                stretch=column == "status",
            )
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self.zoom_selected)
        self.refresh()
        center_window(self, master)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        ne = safe_float(getattr(self.master_app, "session_ne", 0.0), 0.0)
        kt = safe_float(self.saha_window.initial_kt_var.get(), 1.0)
        diagnostics = saha_template_line_diagnostics(self.master_app, ne=ne, kt=kt)
        usable = sum(1 for item in diagnostics if item["usable"])
        self.summary_var.set(
            f"{usable}/{len(diagnostics)} lines ready. Saha-Boltzmann needs at least two ready lines "
            "of the same element with different upper energies."
        )
        for item in diagnostics:
            self.tree.insert(
                "",
                "end",
                iid=str(item["index"]),
                values=(
                    item["index"],
                    format_template_display_value(item["wavelength"]),
                    format_template_display_value(item["fit_center"]),
                    item["species"] or "-",
                    item["ion"] or "-",
                    format_scientific_display_value(item["area"]),
                    format_template_display_value(item["ek"]),
                    format_template_display_value(item["aki"]),
                    format_template_display_value(item["gk"]),
                    item["status"],
                ),
            )

    def open_auto_fit(self):
        win = self.master_app.show_auto_fit_manager()
        bring_window_to_front(win, self)
        return win

    def open_selected_lines(self):
        win = self.master_app.show_template_manager()
        bring_window_to_front(win, self)
        return win

    def zoom_selected(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        idx = safe_int(selected[0], -1) - 1
        lines = list(getattr(self.master_app, "template_lines", []) or [])
        if 0 <= idx < len(lines):
            self.master_app.zoom_around(_template_line_center(lines[idx]))


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
    spectra = list(getattr(app, "spectra", []) or [])
    return bool(spectra) and all(getattr(sp, "response_corrected", False) for sp in spectra)


def _clear_template_fit_measurements(lines) -> int:
    """Discard measurements that belong to a different intensity domain."""
    cleared = 0
    for line in list(lines or []):
        if (
            getattr(line, "inte", None) not in (None, 0.0, "")
            or safe_float(getattr(line, "fitwavelen", 0.0), 0.0) != 0.0
        ):
            cleared += 1
        line.inte = None
        line.wl = None
        line.wg = None
        line.fitwavelen = None
        line.error_inte = 0.0
        line.fit_profile = ""
        for attr in list(vars(line)):
            if attr.startswith("fit_") and attr != "fit_profile":
                delattr(line, attr)
    return cleared


def _apply_after_response_enabled(app: "MainWindow") -> bool:
    try:
        return (
            bool(getattr(app.options, "apply_response", False))
            and bool(getattr(app.options, "apply_after", False))
            and bool(getattr(getattr(app, "response_library", None), "curves", []))
            and not _fit_values_already_response_corrected(app)
        )
    except Exception:
        return False


def _response_paths_kind(paths) -> str:
    """Classify correction files without conflating OPC with a full response."""
    normalized = parse_response_paths(paths)
    if not normalized:
        return "none"
    opc_flags = [Path(path).suffix.lower() == ".opc" for path in normalized]
    if all(opc_flags):
        return "opc"
    if any(opc_flags):
        return "mixed"
    return "instrument"


def read_opc_metadata(filename: str) -> dict[str, object]:
    """Read the auditable comment header of an OPC without using it as state."""
    path = Path(str(filename or ""))
    if path.suffix.lower() != ".opc" or not path.is_file():
        return {}
    metadata: dict[str, object] = {}
    json_fields = {
        "nominal_number_percent",
        "source_cflibs_number_percent",
        "source_cflibs_mass_percent",
        "population_multipliers",
        "round_trip_number_percent",
        "physical_response_files",
        "source_spectrum_files",
        "voigt_fit_ranges",
        "analytical_lines_json",
    }
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.startswith("#"):
                    break
                text = line[1:].strip()
                if ":" not in text:
                    continue
                key, value = (part.strip() for part in text.split(":", 1))
                normalized_key = key.casefold().replace(" ", "_")
                if normalized_key in json_fields:
                    try:
                        metadata[normalized_key] = json.loads(value)
                        continue
                    except (TypeError, ValueError, json.JSONDecodeError):
                        pass
                metadata[normalized_key] = value
    except OSError:
        return {}
    return metadata


def opc_calibration_id(filename: str) -> str:
    """Return the saved calibration id, or a stable hash for legacy OPC files."""
    metadata = read_opc_metadata(filename)
    saved = str(metadata.get("calibration_id", "") or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{12,64}", saved):
        return saved[:12]
    try:
        digest = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
    except OSError:
        return ""
    return digest[:12]


def opc_rows_calibration_id(calibration_rows) -> str:
    """Identify the numerical OPC curve independently of filename and header."""
    canonical = "\n".join(
        f"{float(wavelength):.12g}\t{float(response):.12g}\t{element}\t{species}"
        for wavelength, response, element, species in calibration_rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _loaded_response_is_opc(app: "MainWindow") -> bool:
    library = getattr(app, "response_library", None)
    paths = [str(getattr(curve, "filename", "") or "") for curve in getattr(library, "curves", []) or []]
    return bool(paths) and _response_paths_kind(paths) == "opc"


def _template_line_center(line: TemplateLine) -> float:
    return abs(line.fitwavelen) if getattr(line, "fitwavelen", 0.0) else (line.asswavelen or line.wavelen)


def _template_line_nist_wavelength(line: TemplateLine) -> float:
    """Return the tabulated transition wavelength, never the fitted center."""
    return (
        abs(safe_float(getattr(line, "asswavelen", 0.0), 0.0))
        or abs(safe_float(getattr(line, "wavelen", 0.0), 0.0))
    )


def _template_line_intensity(line: TemplateLine) -> float:
    """Return the fitted profile area, never a marked-peak height."""
    if _template_line_has_fit_error(line):
        return 0.0
    inte = safe_float(getattr(line, "inte", 0.0), 0.0)
    fit_center = abs(safe_float(getattr(line, "fitwavelen", 0.0), 0.0))
    wg = abs(safe_float(getattr(line, "wg", 0.0), 0.0))
    wl = abs(safe_float(getattr(line, "wl", 0.0), 0.0))
    profile = str(getattr(line, "fit_profile", "") or "voigt").strip().lower()
    if min(inte, fit_center, wg) <= 0.0:
        return 0.0
    if profile != "gaussian" and wl <= 0.0:
        return 0.0
    return inte


def _is_template_error_value(value) -> bool:
    return isinstance(value, str) and value.strip().upper() == "ERROR"


def _template_line_has_fit_error(line: TemplateLine) -> bool:
    return any(
        _is_template_error_value(getattr(line, attr, ""))
        for attr in ("inte", "wl", "wg", "error_inte", "fitinte")
    )


def saha_template_line_diagnostics(
    app: "MainWindow",
    *,
    ne: float = 0.0,
    kt: float = 1.0,
) -> list[dict]:
    """Return an auditable readiness result for every Saha-Boltzmann row."""
    diagnostics = []
    metadata_cache = {}
    selected_elements = _selected_analysis_elements(app)
    for index, line in enumerate(getattr(app, "template_lines", []) or [], start=1):
        if not template_line_is_acquired(app, line):
            continue
        species = str(getattr(line, "specie", "") or "").strip().capitalize()
        if selected_elements is not None and species not in selected_elements:
            continue
        blockers = []
        fit_warning = str(
            getattr(line, "fit_quality_warning", "") or ""
        ).strip()
        if _template_line_has_fit_error(line):
            blockers.append(
                "Voigt rejected: " + fit_warning
                if fit_warning
                else "Voigt fit failed"
            )

        ion = safe_int(getattr(line, "ion", 0), 0)
        aki = safe_float(getattr(line, "aki", 0.0), 0.0)
        aki_threshold = max(
            0.0,
            safe_float(getattr(getattr(app, "options", None), "aki_threshold", 1.0e5), 1.0e5),
        )
        gk = safe_float(getattr(line, "gk", 0.0), 0.0)
        ek = safe_float(getattr(line, "ek", 0.0), 0.0)
        area = safe_float(getattr(line, "inte", 0.0), 0.0)
        fit_center = abs(safe_float(getattr(line, "fitwavelen", 0.0), 0.0))
        nist_wavelength = _template_line_nist_wavelength(line)
        wg = abs(safe_float(getattr(line, "wg", 0.0), 0.0))
        wl = abs(safe_float(getattr(line, "wl", 0.0), 0.0))
        profile = str(
            getattr(line, "fit_profile", "") or "voigt"
        ).strip().lower()

        if not species:
            blockers.append("missing element assignment")
        if ion not in (1, 2):
            blockers.append("ion must be I or II")
        if abs(aki) <= 0.0:
            blockers.append("missing Aki")
        elif abs(aki) < aki_threshold:
            blockers.append(f"Aki below threshold ({aki_threshold:.3g})")
        if gk <= 0.0:
            blockers.append("missing gk")
        if ek <= 0.0:
            blockers.append("missing Ek")
        if area <= 0.0:
            blockers.append(
                "missing positive Gaussian area"
                if profile == "gaussian"
                else "missing positive Voigt area"
            )
        if fit_center <= 0.0:
            blockers.append("missing fitted center")
        if nist_wavelength <= 0.0:
            blockers.append("missing assigned NIST wavelength")
        if wg <= 0.0:
            blockers.append(
                "missing Gaussian width"
                if profile == "gaussian"
                else "missing Gaussian Voigt width"
            )
        if profile != "gaussian" and wl <= 0.0:
            blockers.append("missing Lorentzian Voigt width")

        if ion == 2:
            if ne <= 0.0:
                blockers.append("missing electron density Ne")
            if kt <= 0.0:
                blockers.append("invalid initial kT")
            if species:
                if species not in metadata_cache:
                    try:
                        metadata_cache[species] = app.libs_db.element_metadata(species)
                    except Exception:
                        metadata_cache[species] = {}
                eion = safe_float(metadata_cache[species].get("en_ion"), 0.0)
                if eion <= 0.0:
                    blockers.append("missing ionization energy")

        inactive = aki < 0.0
        if blockers:
            status = "Blocked: " + "; ".join(blockers)
        elif inactive:
            status = "Excluded from fit"
        elif fit_warning:
            status = "Ready; WARNING: " + fit_warning
        else:
            status = "Ready"
        diagnostics.append({
            "index": index,
            "line": line,
            "wavelength": nist_wavelength,
            "fit_center": fit_center,
            "species": species,
            "ion": ion,
            "area": area,
            "ek": ek,
            "aki": aki,
            "gk": gk,
            "blockers": blockers,
            "inactive": inactive,
            "usable": not blockers and not inactive,
            "fit_warning": fit_warning,
            "status": status,
        })
    return diagnostics


def saha_no_fit_message(diagnostics: list[dict], groups: dict) -> str:
    """Build a specific explanation instead of the old generic skip count."""
    total = len(diagnostics)
    usable_rows = [item for item in diagnostics if item.get("usable")]
    usable = len(usable_rows)
    if total == 0:
        return (
            "No selected lines are available. Create or load the selected-line list, "
            "identify the lines, then run the Voigt Auto Fit."
        )

    reason_counts = defaultdict(int)
    for item in diagnostics:
        for reason in item.get("blockers", []):
            reason_counts[reason] += 1
    if not usable_rows:
        ordered = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        reasons = "; ".join(f"{reason}: {count}" for reason, count in ordered[:4])
        message = f"No plot point is ready (0/{total})."
        if reasons:
            message += "\nMain blockers: " + reasons + "."
        if any("Voigt" in reason for reason in reason_counts):
            message += (
                "\nA line label is only an identification: Saha-Boltzmann uses the "
                "integrated Voigt area produced by Auto Fit."
            )
        return message

    by_element = defaultdict(int)
    for item in usable_rows:
        by_element[item["species"]] += 1
    if max(by_element.values(), default=0) < 2:
        counts = ", ".join(f"{element}: {count}" for element, count in sorted(by_element.items()))
        return (
            f"{usable}/{total} line(s) are ready, but no element has at least two active "
            f"lines ({counts}). A temperature cannot be fitted from one point."
        )

    group_counts = {
        element: sum(1 for point in points if not point.get("inactive"))
        for element, points in groups.items()
    }
    counts = ", ".join(f"{element}: {count}" for element, count in sorted(group_counts.items()))
    return (
        f"{usable}/{total} line(s) are ready ({counts}), but no physical Boltzmann slope "
        "was obtained. Check the assigned transitions, Voigt areas, upper energies, and "
        "excluded points."
    )


def _self_absorption_observations(app: "MainWindow") -> list[LineObservation]:
    observations = []
    selected_elements = _selected_analysis_elements(app)
    for line in getattr(app, "template_lines", []) or []:
        if not template_line_is_acquired(app, line):
            continue
        if _template_line_has_fit_error(line):
            continue
        species = str(getattr(line, "specie", "") or "").strip().capitalize()
        if selected_elements is not None and species not in selected_elements:
            continue
        ion = safe_int(getattr(line, "ion", 0), 0)
        aki = abs(safe_float(getattr(line, "aki", 0.0), 0.0))
        gk = safe_float(getattr(line, "gk", 0.0), 0.0)
        ek = safe_float(getattr(line, "ek", 0.0), 0.0)
        ei = safe_float(getattr(line, "ei", 0.0), 0.0)
        intensity = _template_line_intensity(line)
        center = _template_line_center(line)
        nist_wavelength = _template_line_nist_wavelength(line)
        if (
            not species
            or ion not in (1, 2)
            or min(aki, gk, ek, intensity, center, nist_wavelength) <= 0.0
        ):
            continue
        intensity /= _response_factor(app, nist_wavelength)
        if intensity <= 0.0:
            continue
        observations.append(LineObservation(
            line=line,
            species=species,
            ion=ion,
            wavelength=center,
            intensity=intensity,
            ei_cm=ei,
            ek_cm=ek,
            aki=aki,
            gk=gk,
            accuracy_percent=safe_float(getattr(line, "acc", 0.0), 0.0),
            snr=safe_float(getattr(line, "fit_snr", 0.0), 0.0),
            fit_warning=str(getattr(line, "fit_quality_warning", "") or ""),
            deconvolved_interference=bool(
                safe_int(getattr(line, "fit_nuisance_components", 0), 0) > 0
            ),
            transition_wavelength=nist_wavelength,
            intensity_mode=_boltzmann_intensity_mode(app),
        ))
    return observations


def _parse_thermometric_species(value: str) -> Optional[tuple[str, int]]:
    text = str(value or "").strip()
    if text.lower().startswith("auto"):
        return None
    if not text:
        return None
    match = re.match(r"^([A-Za-z]{1,2})\s*(I{1,2}|[12])?$", text, re.IGNORECASE)
    if not match:
        return None
    ion_text = (match.group(2) or "I").upper()
    ion = 2 if ion_text in ("II", "2") else 1
    return match.group(1).capitalize(), ion


def _parse_irsac_reference_lines(value) -> dict[tuple[str, int], float]:
    """Decode persisted IRSAC line references keyed as ``Cd I`` or ``Pb II``."""
    if isinstance(value, dict):
        raw = value
    else:
        try:
            raw = json.loads(str(value or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = {}
    result = {}
    if not isinstance(raw, dict):
        return result
    for label, wavelength in raw.items():
        key = _parse_thermometric_species(label)
        numeric = abs(safe_float(wavelength, 0.0))
        if key is not None and numeric > 0.0:
            result[key] = numeric
    return result


def _serialize_irsac_reference_lines(values: dict[tuple[str, int], float]) -> str:
    payload = {
        f"{key[0]} {_roman_ion(key[1])}": float(wavelength)
        for key, wavelength in sorted(values.items())
        if key[0] and key[1] in (1, 2) and safe_float(wavelength, 0.0) > 0.0
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _available_irsac_thermometric_keys(app: "MainWindow") -> list[tuple[str, int]]:
    """Return identified species/ion stages that can drive IRSAC T iteration."""
    selected_elements = _selected_analysis_elements(app)
    keys = {
        (
            str(getattr(line, "specie", "") or "").strip().capitalize(),
            safe_int(getattr(line, "ion", 0), 0),
        )
        for line in getattr(app, "template_lines", []) or []
        if not _template_line_has_fit_error(line)
        and template_line_is_acquired(app, line)
    }
    return sorted(
        key
        for key in keys
        if key[0]
        and key[1] in (1, 2)
        and (selected_elements is None or key[0] in selected_elements)
    )


def _active_irsac_reference_lines(
    app: "MainWindow",
    observations: Optional[list[LineObservation]] = None,
) -> dict[tuple[str, int], float]:
    """Return saved references that belong to the current selected dataset."""
    saved = _parse_irsac_reference_lines(
        getattr(app.options, "irsac_reference_lines", "{}")
    )
    if not hasattr(app, "template_lines"):
        return saved
    available = (
        {observation.key for observation in observations}
        if observations is not None
        else set(_available_irsac_thermometric_keys(app))
    )
    return {
        key: wavelength
        for key, wavelength in saved.items()
        if key in available and wavelength_is_acquired(app, wavelength)
    }


def _saha_temperature_for_irsac_reference(
    app: "MainWindow",
    key: Optional[tuple[str, int]],
) -> Optional[float]:
    """Return the pre-IRSAC Saha temperature in kelvin for a manual reference."""
    if key is None:
        return None
    workflow = getattr(app, "last_self_absorption_result", None)
    if isinstance(workflow, dict):
        pre_temperatures = workflow.get("pre_saha_temperatures")
        if isinstance(pre_temperatures, dict):
            kt = safe_float(pre_temperatures.get(key[0]), 0.0)
            if kt > 0.0:
                return kt * 11604.45
    saha = getattr(app, "last_saha_boltzmann", None)
    if not isinstance(saha, dict):
        return None
    for row in saha.get("elements", []):
        element = str(row.get("element", "") or "").strip().capitalize()
        kt = safe_float(row.get("temperature", 0.0), 0.0)
        if element == key[0] and kt > 0.0:
            return kt * 11604.45
    return None


def _saha_thermometric_key(
    app: "MainWindow",
    observations: list[LineObservation],
) -> Optional[tuple[str, int]]:
    """Reuse the Saha-Boltzmann reference instead of making a second choice."""
    saha = getattr(app, "last_saha_boltzmann", None) or {}
    element = str(saha.get("selected_element", "") or "").strip().capitalize()
    mode = str(saha.get("representative_mode", "") or "")
    if not element or mode not in ("most reliable element", "selected element"):
        return None
    candidates = defaultdict(list)
    for observation in observations:
        if observation.species == element:
            candidates[observation.key].append(observation)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda key: (
            len(candidates[key]),
            len({round(obs.ek_cm, 6) for obs in candidates[key]}),
            max(obs.ek_cm for obs in candidates[key]) - min(obs.ek_cm for obs in candidates[key]),
        ),
    )


def _selected_analysis_elements(app: "MainWindow") -> Optional[set[str]]:
    """Return the Saha rows explicitly admitted to IRSAC and CF-LIBS.

    None means that Saha-Boltzmann has not established a selection yet.
    An empty set means that the user explicitly excluded every element.
    """
    traced_selection = getattr(app, "analysis_elements", None)
    if traced_selection is not None:
        return {
            str(element or "").strip().capitalize()
            for element in traced_selection
            if str(element or "").strip()
        }
    saha = getattr(app, "last_saha_boltzmann", None)
    if not isinstance(saha, dict) or "elements" not in saha:
        return None
    return {
        str(row.get("element", "") or "").strip().capitalize()
        for row in saha.get("elements", [])
        if row.get("included") and str(row.get("element", "") or "").strip()
    }


def _stark_row_map(
    observations: list[LineObservation],
    tolerance: float,
    wavelength_scale: float = 1.0,
) -> dict[int, tuple[float, float]]:
    """Match observations to Stark.db, whose wavelengths are stored in Angstrom."""
    path = resource_path("Stark.db")
    if not path.exists():
        return {}
    result = {}
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
    except Exception:
        return {}
    try:
        for obs in observations:
            observed_wavelength = (
                abs(safe_float(getattr(obs.line, "asswavelen", 0.0), 0.0))
                or obs.wavelength
            )
            lookup_wavelength = observed_wavelength * wavelength_scale
            lookup_tolerance = tolerance * wavelength_scale
            row = conn.execute(
                '''
                SELECT "w-T5000", "w-T10000"
                FROM Stark
                WHERE UPPER(TRIM(Element)) = ?
                  AND CAST(Ion AS INTEGER) = ?
                  AND CAST(Wavelength AS REAL) BETWEEN ? AND ?
                ORDER BY ABS(CAST(Wavelength AS REAL) - ?)
                LIMIT 1
                ''',
                (
                    obs.species.upper(), obs.ion,
                    lookup_wavelength - lookup_tolerance, lookup_wavelength + lookup_tolerance,
                    lookup_wavelength,
                ),
            ).fetchone()
            if row is not None:
                result[id(obs.line)] = (
                    safe_float(row["w-T5000"], 0.0),
                    safe_float(row["w-T10000"], 0.0),
                )
    except Exception:
        result = {}
    finally:
        conn.close()
    return result


def calculate_hybrid_self_absorption(
    app: "MainWindow",
    *,
    mode: Optional[str] = None,
    thermometric_species: str = "",
    temperature_k: float = 0.0,
):
    selected_mode = str(mode or getattr(app.options, "irsac_mode", "hybrid")).strip().lower()
    previous_workflow = getattr(app, "last_self_absorption_result", None)
    pre_saha_temperatures = (
        dict(previous_workflow.get("pre_saha_temperatures", {}))
        if isinstance(previous_workflow, dict)
        else {}
    )
    if not pre_saha_temperatures:
        saha = getattr(app, "last_saha_boltzmann", None)
        if isinstance(saha, dict):
            pre_saha_temperatures = {
                str(row.get("element", "") or "").strip().capitalize():
                safe_float(row.get("temperature"), 0.0)
                for row in saha.get("elements", [])
                if str(row.get("element", "") or "").strip()
                and safe_float(row.get("temperature"), 0.0) > 0.0
            }
    app.post_irsac_temperature = None
    app.post_irsac_temperature_source = None
    app.last_theoretical_spectrum = None
    app.last_self_absorption_result = None
    _refresh_theoretical_workflow_ui(app)
    observations = _self_absorption_observations(app)
    for line in getattr(app, "template_lines", []) or []:
        line.sa_sac = ""
        line.sa_method = ""
        line.sa_reference = ""
        line.sa_flagged = False
        line.sa_stark_width = ""
        line.sa_has_stark_data = False
        line.sa_use = False
        line.sa_diagnostic_status = "Not assessed"
        line.sa_diagnostic_reason = "No independent check available"
        line.sa_is_reference = False
        line.sa_recommended = False
    if not observations:
        return None
    if temperature_k <= 0.0:
        kt = safe_float(getattr(app, "session_temperature", 0.0), 0.0)
        temperature_k = kt * 11604.45 if kt > 0.0 else 11604.45
    ne = safe_float(getattr(app, "session_ne", 0.0), 0.0)
    tolerance = max(0.05, abs(safe_float(getattr(app.options, "search_range", 0.2), 0.2)) * 0.02)
    wavelength_scale = 10.0 if app.current_wavelength_unit_label() == "nm" else 1.0
    stark_rows = _stark_row_map(observations, tolerance, wavelength_scale) if ne > 0.0 else {}

    def palleschi_provider(obs: LineObservation, current_temperature: float):
        widths = stark_rows.get(id(obs.line))
        if widths is None:
            return None
        w5000, w10000 = widths
        w_t = w5000 + (current_temperature - 5000.0) * (w10000 - w5000) / 5000.0
        # Stark.db widths are Angstrom; compare them with the fitted width in
        # the active spectrum unit.
        stark_width = 2.0 * (ne / 1.0e17) * w_t / wavelength_scale
        obs.line.sa_stark_width = _format_sa_numeric(stark_width)
        obs.line.sa_has_stark_data = stark_width > 0.0
        return palleschi_sac_multiplier(getattr(obs.line, "wl", 0.0), stark_width)

    configured_key = _parse_thermometric_species(
        thermometric_species or getattr(app.options, "irsac_thermometric_species", "")
    )
    if configured_key is not None and not any(
        observation.key == configured_key for observation in observations
    ):
        label = f"{configured_key[0]} {_roman_ion(configured_key[1])}"
        raise ValueError(
            f"The selected IRSAC temperature reference {label} has no valid "
            "fitted lines. Check the I/II assignments or choose another reference."
        )
    if configured_key is None:
        configured_key = _saha_thermometric_key(app, observations)
    equation_mode = _canonical_irsac_equation_mode(
        getattr(app.options, "irsac_equation_mode", "staged")
    )
    if selected_mode in ("hybrid", "irsac", "yang", "yang/aslam"):
        # Migrate projects saved while the superseded iterative/worksheet
        # implementation was the default. The application exposes one
        # quantitative IRSAC path so identical inputs cannot silently select a
        # different equation through a stale INI value.
        equation_mode = "staged"
        app.options.irsac_equation_mode = "staged"
    result = hybrid_self_absorption(
        observations,
        temperature_k,
        mode=selected_mode,
        thermometric_key=configured_key,
        reference_wavelengths=_active_irsac_reference_lines(app, observations),
        equation_mode=equation_mode,
        palleschi_factor=palleschi_provider,
        max_iterations=max(1, safe_int(getattr(app.options, "irsac_iterations", 100), 100)),
        relative_tolerance=max(1.0e-9, safe_float(getattr(app.options, "irsac_tolerance", 0.001), 0.001)),
    )
    assessment = assess_self_absorption(observations, result.corrections)
    if equation_mode in ("staged", "iterative"):
        selected_line_ids = set(result.selected_line_ids)
    else:
        selected_line_ids = {
            line_id
            for line_id, line_assessment in assessment.lines.items()
            if line_assessment.recommended_use
        }
    selected_corrections = {
        line_id: correction
        for line_id, correction in result.corrections.items()
        if line_id in selected_line_ids
    }
    if equation_mode == "excel_worksheet":
        selected_temperature_k = thermometric_temperature(
            observations,
            selected_corrections,
            result.thermometric_key,
        )
        if selected_temperature_k > 0.0 and math.isfinite(selected_temperature_k):
            result = replace(result, temperature_k=selected_temperature_k)
    initial_iterative_temperature_k = (
        result.temperature_history[0]
        if result.temperature_history
        else temperature_k
    )
    slope_rejected_keys = set(result.slope_rejected_keys)
    thermometric_corrected = any(
        observation.key == result.thermometric_key
        and id(observation.line) in selected_corrections
        for observation in observations
    )
    temperature_mode = (
        "staged IRSAC on thermometric species"
        if thermometric_corrected
        else "raw thermometric lines"
    )
    species_decisions = {}
    for key, species_assessment in assessment.species.items():
        if key in slope_rejected_keys:
            decision = "Raw (post-IRSAC slope incompatible)"
        elif any(
            observation.key == key
            and id(observation.line) in selected_corrections
            for observation in observations
        ):
            decision = "IRSAC"
        elif species_assessment.status == "No significant evidence":
            decision = "Raw (no significant self-absorption evidence)"
        elif species_assessment.status == "Correction unsafe":
            decision = "Raw (IRSAC unsafe)"
        else:
            decision = "Raw (not assessable)"
        species_decisions[f"{key[0]} {_roman_ion(key[1])}"] = decision
    assessment_status = assessment.status
    assessment_message = assessment.message
    if slope_rejected_keys:
        rejected_labels = ", ".join(
            f"{key[0]} {_roman_ion(key[1])}"
            for key in sorted(slope_rejected_keys)
        )
        if selected_corrections:
            assessment_status = "Selective correction available"
            assessment_message = (
                f"IRSAC was rejected for {rejected_labels} because the "
                "independent post-correction slope is incompatible with the "
                "thermometric temperature. Other validated corrections remain enabled."
            )
        else:
            assessment_status = "Correction unsafe"
            assessment_message = (
                f"IRSAC was rejected for {rejected_labels}: the independent "
                "post-correction slope is incompatible with the thermometric temperature."
            )
    for obs in observations:
        correction = result.corrections.get(id(obs.line))
        line_assessment = assessment.lines.get(id(obs.line))
        if line_assessment is not None:
            obs.line.sa_diagnostic_status = line_assessment.status
            obs.line.sa_diagnostic_reason = line_assessment.reason
            obs.line.sa_is_reference = line_assessment.is_reference
            final_recommended = id(obs.line) in selected_line_ids
            obs.line.sa_recommended = final_recommended
            obs.line.sa_use = final_recommended
            if obs.key in slope_rejected_keys:
                obs.line.sa_diagnostic_status = "Slope incompatible"
                obs.line.sa_diagnostic_reason = (
                    f"{line_assessment.reason}; post-IRSAC independent slope "
                    "does not agree with the thermometric temperature"
                )
        if correction is None:
            continue
        obs.line.sa_sac = correction.multiplier
        obs.line.sa_method = correction.method
        obs.line.sa_reference = correction.reference_wavelength
        obs.line.sa_flagged = (
            correction.flagged
            or (
                line_assessment is not None
                and line_assessment.status == "Unsafe"
            )
        )
    app.last_self_absorption_result = {
        "mode": selected_mode,
        "irsac_completed": (
            selected_mode in ("hybrid", "irsac", "yang", "yang/aslam")
            and result.converged
        ),
        "input_temperature_k": temperature_k,
        "temperature_k": result.temperature_k,
        "initial_iterative_temperature_k": initial_iterative_temperature_k,
        "thermometric_temperature_mode": temperature_mode,
        "thermometric_species": result.thermometric_key,
        "requested_thermometric_species": configured_key,
        "reference_lines": {
            f"{key[0]} {_roman_ion(key[1])}": wavelength
            for key, wavelength in _active_irsac_reference_lines(
                app, observations
            ).items()
        },
        "equation_mode": equation_mode,
        "pre_saha_temperatures": pre_saha_temperatures,
        "iterations": result.iterations,
        "converged": result.converged,
        "rmse": result.rmse,
        "max_log_factor_change": result.max_log_factor_change,
        "relative_temperature_change": result.relative_temperature_change,
        "decisions_stable": result.decisions_stable,
        "slope_rejected_species": [
            f"{key[0]} {_roman_ion(key[1])}"
            for key in sorted(slope_rejected_keys)
        ],
        "species_slope_validation": {
            f"{key[0]} {_roman_ion(key[1])}": dict(value)
            for key, value in result.species_slope_validation.items()
        },
        "reference_absorption": {
            f"{key[0]} {_roman_ion(key[1])}": value
            for key, value in result.reference_absorption.items()
        },
        "temperature_history": list(result.temperature_history),
        "candidate_lines": len(result.corrections),
        "corrected_lines": len(selected_corrections),
        "palleschi_lines": sum(1 for correction in selected_corrections.values() if correction.method.startswith("Palleschi")),
        "irsac_lines": sum(1 for correction in selected_corrections.values() if correction.method.startswith("IRSAC")),
        "applied": bool(getattr(app, "apply_sac_correction", False)),
        "enabled_lines": 0,
        "assessment_status": assessment_status,
        "assessment_message": assessment_message,
        "assessment_can_apply": bool(selected_corrections),
        "species_decisions": species_decisions,
        "assessment_basis": (
            "Current spectrum only: same-upper-level radiometric ratios, "
            "Voigt fit quality and Palleschi/Stark width where available. "
            "No curve of growth or multi-delay trend inferred."
        ),
        "species_assessments": {
            f"{key[0]} {_roman_ion(key[1])}": {
                "status": value.status,
                "message": value.message,
                "equivalent_level_checks": value.equivalent_level_checks,
                "failed_checks": value.failed_checks,
                "reference_quality": value.reference_quality,
                "recommended_lines": value.recommended_lines,
                "decision": species_decisions.get(
                    f"{key[0]} {_roman_ion(key[1])}",
                    "Raw (not assessable)",
                ),
            }
            for key, value in assessment.species.items()
        },
    }
    _refresh_theoretical_workflow_ui(app)
    return result


def _refresh_selective_irsac_temperature(app: "MainWindow") -> float:
    """Recompute the common T from the chosen species and enabled rows only."""
    workflow = getattr(app, "last_self_absorption_result", None)
    if not isinstance(workflow, dict):
        return 0.0
    thermometric_key = workflow.get("thermometric_species")
    if isinstance(thermometric_key, list):
        thermometric_key = tuple(thermometric_key)
    if not (
        isinstance(thermometric_key, tuple)
        and len(thermometric_key) >= 2
    ):
        thermometric_key = None
    observations = _self_absorption_observations(app)
    selected_corrections = {}
    thermometric_corrected = False
    for observation in observations:
        line = observation.line
        multiplier = safe_float(getattr(line, "sa_sac", 0.0), 0.0)
        if (
            not bool(getattr(line, "sa_use", False))
            or multiplier <= 0.0
            or not math.isfinite(multiplier)
        ):
            continue
        selected_corrections[id(line)] = LineCorrection(
            multiplier=multiplier,
            method=str(getattr(line, "sa_method", "") or "Selected IRSAC"),
            reference_wavelength=safe_float(
                getattr(line, "sa_reference", 0.0),
                0.0,
            ),
        )
        if observation.key == thermometric_key:
            thermometric_corrected = True
    temperature_k = thermometric_temperature(
        observations,
        selected_corrections,
        thermometric_key,
    )
    if temperature_k > 0.0 and math.isfinite(temperature_k):
        workflow["temperature_k"] = temperature_k
        workflow["thermometric_temperature_mode"] = (
            "accepted IRSAC corrections"
            if thermometric_corrected
            else "raw thermometric lines"
        )
    return temperature_k


def _sac_factor_for_line(line: TemplateLine) -> Optional[float]:
    """Return the SAC factor selected in the Show SA table for this line.

    SAC is not recomputed here. It is used only when the Show SA row has
    Use/checkbox = Yes and the already-calculated relative factor is positive.
    """
    try:
        if not bool(getattr(line, "sa_use", False)):
            return None
        sac = safe_float(getattr(line, "sa_sac", ""), 0.0)
        if sac > 0.0 and math.isfinite(sac):
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


def saha_fit_quality(app: "MainWindow", result: dict) -> dict:
    """Quantify how strongly the fitted temperature depends on its line set.

    R2 alone is not sufficient: it is exactly one for any non-degenerate
    two-point fit. The leave-one-out range exposes fits whose slope is
    controlled by one influential line or energy level.
    """
    points = [point for point in result.get("points", []) if not point.get("inactive")]
    values = [
        (
            safe_float(point.get("x", 0.0), 0.0),
            _sac_corrected_fit_y(app, point),
        )
        for point in points
    ]
    values = [(x, y) for x, y in values if math.isfinite(x) and math.isfinite(y)]
    xs = [item[0] for item in values]
    ys = [item[1] for item in values]
    nlines = len(xs)
    distinct_levels = len({round(x, 8) for x in xs})
    span = max(xs) - min(xs) if xs else 0.0
    slope = safe_float(result.get("slope", 0.0), 0.0)
    intercept = safe_float(result.get("q", result.get("q_fixed", 0.0)), 0.0)

    r2 = 0.0
    relative_slope_error = float("inf")
    if nlines >= 2 and span > 0.0 and slope:
        predictions = [slope * x + intercept for x in xs]
        mean_y = sum(ys) / nlines
        ss_total = sum((y - mean_y) ** 2 for y in ys)
        ss_residual = sum((y - estimate) ** 2 for y, estimate in zip(ys, predictions))
        r2 = 1.0 - ss_residual / ss_total if ss_total > 0.0 else 0.0
        mean_x = sum(xs) / nlines
        sxx = sum((x - mean_x) ** 2 for x in xs)
        if nlines > 2 and sxx > 0.0:
            slope_error = math.sqrt(max(0.0, ss_residual / (nlines - 2)) / sxx)
            relative_slope_error = slope_error / abs(slope)

    leave_one_out_temperatures = []
    if nlines >= 3:
        for omitted in range(nlines):
            loo_x = xs[:omitted] + xs[omitted + 1:]
            loo_y = ys[:omitted] + ys[omitted + 1:]
            if len({round(x, 8) for x in loo_x}) < 2:
                continue
            fit = linear_fit(loo_x, loo_y)
            if fit and fit[0] < 0.0:
                leave_one_out_temperatures.append(-1.0 / fit[0])
    loo_relative_span = float("inf")
    if len(leave_one_out_temperatures) >= 2:
        ordered = sorted(leave_one_out_temperatures)
        middle = len(ordered) // 2
        median = (
            ordered[middle]
            if len(ordered) % 2
            else 0.5 * (ordered[middle - 1] + ordered[middle])
        )
        if median > 0.0:
            loo_relative_span = (ordered[-1] - ordered[0]) / median

    eligible = (
        nlines >= 3
        and distinct_levels >= 3
        and span > 0.0
        and slope < 0.0
        and math.isfinite(loo_relative_span)
    )
    options = getattr(app, "options", None)
    thresholds = {
        "min_lines": max(3, safe_int(getattr(options, "quality_min_temperature_lines", 4), 4)),
        "min_levels": max(3, safe_int(getattr(options, "quality_min_temperature_levels", 3), 3)),
        "min_energy_span_ev": max(0.0, safe_float(getattr(options, "quality_min_energy_span_ev", 1.5), 1.5)),
        "min_r2": safe_float(getattr(options, "quality_min_temperature_r2", 0.98), 0.98),
        "max_relative_slope_error": max(0.0, safe_float(getattr(options, "quality_max_relative_slope_error", 0.15), 0.15)),
        "max_loo_relative_span": max(0.0, safe_float(getattr(options, "quality_max_loo_relative_span", 0.25), 0.25)),
    }
    quantitative_failures = []
    if nlines < thresholds["min_lines"]:
        quantitative_failures.append(
            f"{nlines} lines < {thresholds['min_lines']}"
        )
    if distinct_levels < thresholds["min_levels"]:
        quantitative_failures.append(
            f"{distinct_levels} independent levels < {thresholds['min_levels']}"
        )
    if span < thresholds["min_energy_span_ev"]:
        quantitative_failures.append(
            f"dEk={span:.4g} eV < {thresholds['min_energy_span_ev']:.4g} eV"
        )
    if slope >= 0.0:
        quantitative_failures.append("non-negative Boltzmann slope")
    if not math.isfinite(r2) or r2 < thresholds["min_r2"]:
        quantitative_failures.append(
            f"R2={r2:.4g} < {thresholds['min_r2']:.4g}"
        )
    if (
        not math.isfinite(relative_slope_error)
        or relative_slope_error > thresholds["max_relative_slope_error"]
    ):
        quantitative_failures.append(
            "relative slope error="
            f"{relative_slope_error:.4g} > {thresholds['max_relative_slope_error']:.4g}"
        )
    if (
        not math.isfinite(loo_relative_span)
        or loo_relative_span > thresholds["max_loo_relative_span"]
    ):
        quantitative_failures.append(
            f"LOO dT/T={loo_relative_span:.4g} > {thresholds['max_loo_relative_span']:.4g}"
        )
    quantitative_eligible = eligible and not quantitative_failures
    return {
        "eligible": eligible,
        "quantitative_eligible": quantitative_eligible,
        "quantitative_failures": quantitative_failures,
        "thresholds": thresholds,
        "nlines": nlines,
        "distinct_levels": distinct_levels,
        "energy_span_ev": span,
        "r2": r2,
        "relative_slope_error": relative_slope_error,
        "loo_relative_span": loo_relative_span,
        "leave_one_out_temperatures": leave_one_out_temperatures,
    }


def select_most_reliable_saha_element(
    app: "MainWindow",
    fits: dict,
    kt_low: float = 0.0,
    kt_high: float = float("inf"),
) -> Optional[str]:
    """Select the eligible thermometric element with the broadest Ek span."""
    low = safe_float(kt_low, 0.0)
    high = safe_float(kt_high, float("inf"))
    if high and low > high:
        low, high = high, low
    best = None
    for element, result in fits.items():
        kt = safe_float(result.get("kt", 0.0), 0.0)
        if kt <= 0.0 or (low and kt <= low) or (high and kt >= high):
            continue
        quality = saha_fit_quality(app, result)
        if not quality["eligible"]:
            continue
        # A broad upper-energy interval is the primary thermometric criterion.
        # Independent levels and leave-one-out stability resolve ties.
        rank = (
            quality["energy_span_ev"],
            quality["distinct_levels"],
            -quality["loo_relative_span"],
            -quality["relative_slope_error"],
            quality["r2"],
            quality["nlines"],
        )
        if best is None or rank > best[0]:
            best = (rank, element)
    return best[1] if best else None


def _response_factor(app: "MainWindow", wavelength: float) -> float:
    """Return the instrumental-response divisor at a NIST wavelength."""
    return _physical_response_value(app, wavelength) if _apply_after_response_enabled(app) else 1.0


def _physical_response_value(app: "MainWindow", wavelength: float) -> float:
    """Return the loaded detector response even when it was applied before fitting."""
    try:
        val = app.response_library.value_at(wavelength)
        return val if val not in (0, None) and math.isfinite(val) and val > 0.0 else 1.0
    except Exception:
        pass
    return 1.0


def _opc_base_response_for_line(
    app: "MainWindow",
    line: TemplateLine,
    point: dict,
) -> tuple[float, float, str]:
    """Return Palleschi's line-wise Apply After divisor and NIST coordinate."""
    nist_wavelength = safe_float(
        point.get("nist_wavelength", _template_line_nist_wavelength(line)),
        0.0,
    )
    if nist_wavelength <= 0.0:
        raise ValueError("The selected line has no valid tabulated wavelength.")

    options = getattr(app, "options", None)
    library = getattr(app, "response_library", None)
    curves = list(getattr(library, "curves", []) or [])
    if not bool(getattr(options, "apply_response", False)) or not curves:
        return 1.0, nist_wavelength, "none"
    if _loaded_response_is_opc(app):
        raise ValueError("An OPC cannot be generated from a spectrum already corrected by another OPC.")
    if not _apply_after_response_enabled(app):
        if bool(getattr(options, "apply_after", False)) and _fit_values_already_response_corrected(app):
            raise ValueError(
                "Apply After is selected, but the loaded spectrum still contains an earlier Apply Before "
                "correction. Confirm Apply After in Options to restore the raw spectrum, then fit the "
                "analytical lines again before generating OPC."
            )
        raise ValueError(
            "Generate OPC from raw fitted areas with the physical instrumental response set to "
            "Apply After. Apply Before areas cannot reproduce Palleschi's line-wise OPC procedure."
        )
    factor = safe_float(point.get("eff", 0.0), 0.0)
    if factor <= 0.0 or not math.isfinite(factor):
        raise ValueError("The instrumental response used by this line is unavailable.")
    return factor, nist_wavelength, "Apply After response"


def _boltzmann_wavelength_nm(app: "MainWindow", wavelength: float) -> float:
    """Normalize the displayed spectrum wavelength for radiometric plots."""
    return wavelength_in_nm(wavelength, app.current_wavelength_unit_label())


def _boltzmann_intensity_mode(app: "MainWindow") -> str:
    """Return the configured energy- or photon-domain convention."""
    value = getattr(
        getattr(app, "options", None),
        "boltzmann_intensity_mode",
        ENERGY_INTENSITY_MODE,
    )
    try:
        return normalize_intensity_mode(value)
    except ValueError:
        return ENERGY_INTENSITY_MODE


def _boltzmann_formula(app: "MainWindow") -> str:
    """Return an auditable formula for labels and reports."""
    if _boltzmann_intensity_mode(app) == PHOTON_INTENSITY_MODE:
        return "ln(Icorr / |Aki gk|)"
    return "ln[(1e-9/(h c)) Icorr lambda_NIST,nm / |Aki gk|]"


def _boltzmann_ordinate(app, intensity, wavelength_nm, aki, gk) -> float:
    """Evaluate the ordinate with the convention selected in Options."""
    return radiometric_boltzmann_ordinate(
        intensity,
        wavelength_nm,
        aki,
        gk,
        _boltzmann_intensity_mode(app),
    )


def libspp_boltzmann_groups_with_skips(
    app: "MainWindow",
):
    """Build Boltzmann groups from current template lines.

    Uses the energy- or photon-domain convention selected in Options:
        x = Ek * 1.23985e-4  # cm^-1 -> eV
        y_energy = ln( 5.0341166e15 * Icorr * lambda_nm / |Aki*gk| )
        y_photon = ln( Icorr / |Aki*gk| )
        Icorr = I / instrument_response

    Returns a dictionary keyed by (specie, ion) with point dictionaries.
    """
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    aki_threshold = max(
        0.0,
        safe_float(getattr(getattr(app, "options", None), "aki_threshold", 1.0e5), 1.0e5),
    )
    selected_elements = _selected_analysis_elements(app)
    for idx, t in enumerate(app.template_lines, start=1):
        if not template_line_is_acquired(app, t):
            continue
        if _template_line_has_fit_error(t):
            continue
        specie = str(getattr(t, "specie", "") or "").strip().capitalize()
        if selected_elements is not None and specie not in selected_elements:
            continue
        ion = safe_int(getattr(t, "ion", 0), 0)
        aki = safe_float(getattr(t, "aki", 0.0), 0.0)
        gk = safe_float(getattr(t, "gk", 0.0), 0.0)
        ek = safe_float(getattr(t, "ek", 0.0), 0.0)
        if not specie or not ion or not aki or abs(aki) < aki_threshold or not gk or not ek:
            continue
        inte = _template_line_intensity(t)
        if inte <= 0:
            continue
        center = _template_line_center(t)
        nist_wavelength = _template_line_nist_wavelength(t)
        if center <= 0.0 or nist_wavelength <= 0.0:
            continue
        eff = _response_factor(app, nist_wavelength)
        icorr = inte / eff
        if icorr <= 0:
            continue
        wavelength_nm = _boltzmann_wavelength_nm(app, nist_wavelength)
        ek_ev = ek * 1.23985e-4
        y = _boltzmann_ordinate(app, icorr, wavelength_nm, aki, gk)
        groups[(specie, ion)].append({
            "x": ek_ev,
            "y": y,
            "line": t,
            "icorr": icorr,
            "eff": eff,
            "center": center,
            "nist_wavelength": nist_wavelength,
            "wavelength_nm": wavelength_nm,
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
        y(I)  = the configured energy- or photon-domain ordinate
        x(II) = Eion + Ek
        y(II) = y(I)
                - ln(6.04e21/Ne * kT^1.5)
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    skipped = 0
    metadata_cache: dict[str, dict] = {}
    aki_threshold = max(
        0.0,
        safe_float(getattr(getattr(app, "options", None), "aki_threshold", 1.0e5), 1.0e5),
    )
    selected_elements = _selected_analysis_elements(app)
    for idx, t in enumerate(app.template_lines, start=1):
        if not template_line_is_acquired(app, t):
            skipped += 1
            continue
        if _template_line_has_fit_error(t):
            skipped += 1
            continue
        specie = str(getattr(t, "specie", "") or "").strip().capitalize()
        if selected_elements is not None and specie not in selected_elements:
            skipped += 1
            continue
        ion = safe_int(getattr(t, "ion", 0), 0)
        aki = safe_float(getattr(t, "aki", 0.0), 0.0)
        gk = safe_float(getattr(t, "gk", 0.0), 0.0)
        ek = safe_float(getattr(t, "ek", 0.0), 0.0)
        if (
            not specie
            or ion not in (1, 2)
            or not aki
            or abs(aki) < aki_threshold
            or not gk
            or not ek
        ):
            skipped += 1
            continue
        inte = _template_line_intensity(t)
        if inte <= 0.0:
            skipped += 1
            continue
        center = _template_line_center(t)
        nist_wavelength = _template_line_nist_wavelength(t)
        if center <= 0.0 or nist_wavelength <= 0.0:
            skipped += 1
            continue
        eff = _response_factor(app, nist_wavelength)
        icorr = inte / eff
        if icorr <= 0.0:
            skipped += 1
            continue
        wavelength_nm = _boltzmann_wavelength_nm(app, nist_wavelength)
        ek_ev = ek * 1.23985e-4
        y = _boltzmann_ordinate(app, icorr, wavelength_nm, aki, gk)
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
            "nist_wavelength": nist_wavelength,
            "wavelength_nm": wavelength_nm,
            "inactive": aki < 0.0,
        })
    skipped += sum(1 for pts in groups.values() for p in pts if p.get("inactive"))
    return groups, skipped


def libspp_saha_boltzmann_diagnostic_groups(
    app: "MainWindow",
    ne: float,
    kt: float,
):
    """Return rejected mean-spectrum fits for display only.

    These points never enter a regression, IRSAC, or CF-LIBS. They make the
    distinction between atomic recognition and quantitative acceptance visible.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    metadata_cache: dict[str, dict] = {}
    aki_threshold = max(
        0.0,
        safe_float(
            getattr(getattr(app, "options", None), "aki_threshold", 1.0e5),
            1.0e5,
        ),
    )
    selected_elements = _selected_analysis_elements(app)
    for line in getattr(app, "template_lines", []) or []:
        if not template_line_is_acquired(app, line):
            continue
        if not _template_line_has_fit_error(line):
            continue
        if not bool(getattr(line, "fit_mean_quality_ok", False)):
            continue
        specie = str(getattr(line, "specie", "") or "").strip().capitalize()
        if selected_elements is not None and specie not in selected_elements:
            continue
        ion = safe_int(getattr(line, "ion", 0), 0)
        aki = safe_float(getattr(line, "aki", 0.0), 0.0)
        gk = safe_float(getattr(line, "gk", 0.0), 0.0)
        ek = safe_float(getattr(line, "ek", 0.0), 0.0)
        area = safe_float(
            getattr(line, "fit_mean_spectrum_area", math.nan),
            math.nan,
        )
        if (
            not specie
            or ion not in (1, 2)
            or not aki
            or abs(aki) < aki_threshold
            or not gk
            or not ek
            or not math.isfinite(area)
            or area <= 0.0
        ):
            continue
        center = _template_line_center(line)
        nist_wavelength = _template_line_nist_wavelength(line)
        if center <= 0.0 or nist_wavelength <= 0.0:
            continue
        eff = _response_factor(app, nist_wavelength)
        icorr = area / eff
        if icorr <= 0.0:
            continue
        wavelength_nm = _boltzmann_wavelength_nm(app, nist_wavelength)
        ek_ev = ek * 1.23985e-4
        y_value = _boltzmann_ordinate(
            app,
            icorr,
            wavelength_nm,
            aki,
            gk,
        )
        x_value = ek_ev
        if ion == 2:
            if ne <= 0.0 or kt <= 0.0:
                continue
            if specie not in metadata_cache:
                try:
                    metadata_cache[specie] = app.libs_db.element_metadata(specie)
                except Exception:
                    metadata_cache[specie] = {}
            eion = (
                safe_float(metadata_cache[specie].get("en_ion"), 0.0)
                * 1.23985e-4
            )
            if eion <= 0.0:
                continue
            x_value = eion + ek_ev
            y_value -= math.log(6.04e21 / ne * math.pow(kt, 1.5))
        groups[specie].append({
            "x": x_value,
            "y": y_value,
            "line": line,
            "ion": ion,
            "icorr": icorr,
            "eff": eff,
            "center": center,
            "nist_wavelength": nist_wavelength,
            "wavelength_nm": wavelength_nm,
            "inactive": False,
            "diagnostic_only": True,
            "diagnostic_reason": str(
                getattr(line, "fit_quality_warning", "") or ""
            ),
            "replicate_area_sd": safe_float(
                getattr(line, "fit_replicate_area_sd", math.nan),
                math.nan,
            ),
            "replicate_area_cv": safe_float(
                getattr(line, "fit_replicate_area_cv", math.nan),
                math.nan,
            ),
        })
    return groups


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
    selected_elements = _selected_analysis_elements(app)
    for key, pts in groups.items():
        if selected_elements is not None and key[0] not in selected_elements:
            continue
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
        # q is the intercept of the configured energy- or photon-domain ordinate.
        results[key] = {"species": specie, "ion": ion, "nlines": len(active_pts), "kt": kt, "q": intercept, "z": z, "points": active_pts}
    return results


def libspp_fit_boltzmann_fixed_temperature(app: "MainWindow", groups, kt: float):
    """Fit Boltzmann intercepts at fixed kT for CF-LIBS concentration work."""
    results = {}
    if kt <= 0.0:
        return results
    selected_elements = _selected_analysis_elements(app)
    for key, pts in groups.items():
        if selected_elements is not None and key[0] not in selected_elements:
            continue
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


def _voigt_fwhm_nm(app: "MainWindow", line: TemplateLine) -> float:
    """Return the fitted Voigt FWHM in nm (Olivero-Longbothum estimate)."""
    # TemplateLine stores both widths as FWHM, while voigt_profile_unit uses
    # Gaussian sigma and Lorentzian HWHM internally.
    gaussian_fwhm = abs(safe_float(getattr(line, "wg", 0.0), 0.0))
    lorentzian_fwhm = abs(safe_float(getattr(line, "wl", 0.0), 0.0))
    fwhm = (
        0.5346 * lorentzian_fwhm
        + math.sqrt(
            0.2166 * lorentzian_fwhm * lorentzian_fwhm
            + gaussian_fwhm * gaussian_fwhm
        )
    )
    unit = str(app.current_wavelength_unit_label() or "nm").strip().lower()
    if unit in ("a", "aa", "angstrom", "angstroms", "angstroem", "angstroems", "å"):
        fwhm /= 10.0
    return max(fwhm, 0.0)


def _unresolved_line_interferences(
    app: "MainWindow",
    line: TemplateLine,
    selected_elements: Optional[set[str]],
) -> list[dict]:
    """Find strong selected-element transitions unresolved by the fitted Voigt.

    This is deliberately a diagnostic, not an automatic line deletion.  A
    candidate must carry at least 10% of the selected transition's Aki*gk and
    lie within one fitted FWHM (bounded to a practical 0.05-0.15 nm interval).
    """
    database = getattr(app, "libs_db", None)
    if database is None or not hasattr(database, "search_lines"):
        return []
    element = str(getattr(line, "specie", "") or "").strip().capitalize()
    ion = safe_int(getattr(line, "ion", 0), 0)
    wavelength = abs(
        safe_float(
            getattr(line, "asswavelen", 0.0)
            or getattr(line, "wavelen", 0.0),
            0.0,
        )
    )
    if not element or ion not in (1, 2) or wavelength <= 0.0:
        return []
    wavelength_nm = _boltzmann_wavelength_nm(app, wavelength)
    radius_nm = min(0.15, max(0.05, _voigt_fwhm_nm(app, line)))
    main_strength = abs(
        safe_float(getattr(line, "aki", 0.0), 0.0)
        * safe_float(getattr(line, "gk", 0.0), 0.0)
    )
    if main_strength <= 0.0:
        return []
    elements = selected_elements or {element}
    found = []
    seen = set()
    for candidate_element in sorted(elements):
        for candidate_ion in (1, 2):
            try:
                candidates = database.search_lines(
                    wavelength_nm,
                    radius_nm,
                    table=candidate_element,
                    element=candidate_element,
                    ion=candidate_ion,
                    limit=100,
                    prefer_full_element_table=True,
                    wavelength_unit="nm",
                )
            except Exception:
                continue
            for candidate in candidates:
                candidate_wavelength = abs(safe_float(candidate.wavelen, 0.0))
                candidate_strength = abs(
                    safe_float(candidate.aki, 0.0)
                    * safe_float(candidate.gk, 0.0)
                )
                same_transition = (
                    str(candidate.specie or "").strip().capitalize() == element
                    and safe_int(candidate.ion, 0) == ion
                    and abs(candidate_wavelength - wavelength_nm) <= 0.005
                    and abs(
                        safe_float(candidate.ek, 0.0)
                        - safe_float(getattr(line, "ek", 0.0), 0.0)
                    ) <= 1.0
                )
                if (
                    same_transition
                    or candidate_strength < 0.10 * main_strength
                    or abs(candidate_wavelength - wavelength_nm) > radius_nm
                ):
                    continue
                key = (
                    str(candidate.specie or "").strip().capitalize(),
                    safe_int(candidate.ion, 0),
                    round(candidate_wavelength, 6),
                )
                if key in seen:
                    continue
                seen.add(key)
                found.append({
                    "element": key[0],
                    "ion": key[1],
                    "wavelength": candidate_wavelength,
                    "separation_nm": abs(candidate_wavelength - wavelength_nm),
                    "relative_ag": candidate_strength / main_strength,
                    "label": (
                        f"{key[0]} {_roman_ion(key[1])} "
                        f"{candidate_wavelength:.6g} nm"
                    ),
                })
    return sorted(found, key=lambda item: item["separation_nm"])


def libspp_cflibs_line_audit(
    app: "MainWindow",
    fits: dict,
    kt: float,
) -> dict[str, dict]:
    """Expose exactly which lines determine each fixed-slope intercept.

    The audit is diagnostic only. It never removes a line or changes the
    concentration, because an expected composition must not be used to tune
    the analytical-line selection.
    """
    if kt <= 0.0:
        return {}
    audits: dict[str, dict] = {}
    active_line_ids = set()
    for (element, ion), fit in sorted(fits.items()):
        active_points = [
            point
            for point in fit.get("points", [])
            if not point.get("inactive")
        ]
        if not active_points:
            continue
        element_audit = audits.setdefault(
            element,
            {
                "element": element,
                "active_lines": [],
                "excluded_lines": [],
                "omitted_lines": [],
                "replicate_rejected_lines": [],
                "stages": [],
            },
        )
        line_rows = []
        q_values = []
        for point in active_points:
            line = point["line"]
            active_line_ids.add(id(line))
            q_value = _sac_corrected_fit_y(app, point) + point["x"] / kt
            q_values.append(q_value)
            wavelength = abs(
                safe_float(
                    getattr(line, "asswavelen", 0.0)
                    or getattr(line, "wavelen", 0.0),
                    0.0,
                )
            )
            label = f"{element} {_roman_ion(ion)} {wavelength:.6g} nm"
            interferences = _unresolved_line_interferences(
                app,
                line,
                _selected_analysis_elements(app),
            )
            line_row = {
                "label": label,
                "element": element,
                "ion": ion,
                "wavelength": wavelength,
                "upper_energy_cm": safe_float(
                    getattr(line, "ek", 0.0),
                    0.0,
                ),
                "q_contribution": q_value,
                "q_residual": q_value - safe_float(fit.get("q"), q_value),
                "snr": safe_float(getattr(line, "fit_snr", 0.0), 0.0),
                "replicate_area_sd": safe_float(
                    getattr(line, "fit_replicate_area_sd", math.nan),
                    math.nan,
                ),
                "replicate_area_cv": safe_float(
                    getattr(line, "fit_replicate_area_cv", math.nan),
                    math.nan,
                ),
                "replicate_area_count": safe_int(
                    getattr(line, "fit_replicate_area_count", 0),
                    0,
                ),
                "replicate_area_total": safe_int(
                    getattr(line, "fit_replicate_area_total", 0),
                    0,
                ),
                "interferences": interferences,
                "clean_feature": not interferences,
            }
            line_rows.append(line_row)
            element_audit["active_lines"].append(label)
        q_min = min(q_values)
        q_max = max(q_values)
        q_span = q_max - q_min
        stage = {
            "ion": ion,
            "q": safe_float(fit.get("q"), sum(q_values) / len(q_values)),
            "q_min": q_min,
            "q_max": q_max,
            "q_span": q_span,
            "population_factor": math.exp(min(q_span, 700.0)),
            "lines": line_rows,
        }
        element_audit["stages"].append(stage)

    selected_elements = _selected_analysis_elements(app)
    for line in getattr(app, "template_lines", []) or []:
        element = str(getattr(line, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(line, "ion", 0), 0)
        if (
            not element
            or ion not in (1, 2)
            or selected_elements is not None
            and element not in selected_elements
            or not template_line_is_acquired(app, line)
        ):
            continue
        audit = audits.setdefault(
            element,
            {
                "element": element,
                "active_lines": [],
                "excluded_lines": [],
                "omitted_lines": [],
                "replicate_rejected_lines": [],
                "stages": [],
            },
        )
        wavelength = abs(
            safe_float(
                getattr(line, "asswavelen", 0.0)
                or getattr(line, "wavelen", 0.0),
                0.0,
            )
        )
        label = f"{element} {_roman_ion(ion)} {wavelength:.6g} nm"
        if safe_float(getattr(line, "aki", 0.0), 0.0) < 0.0:
            audit["excluded_lines"].append(label)
        elif id(line) not in active_line_ids:
            audit["omitted_lines"].append(label)
            replicate_total = safe_int(
                getattr(line, "fit_replicate_area_total", 0),
                0,
            )
            if replicate_total >= 2:
                replicate_count = safe_int(
                    getattr(line, "fit_replicate_area_count", 0),
                    0,
                )
                replicate_cv = safe_float(
                    getattr(line, "fit_replicate_area_cv", math.nan),
                    math.nan,
                )
                warning = str(
                    getattr(line, "fit_quality_warning", "") or ""
                )
                audit["replicate_rejected_lines"].append({
                    "line": label,
                    "valid": replicate_count,
                    "total": replicate_total,
                    "cv": replicate_cv,
                    "reason": warning,
                })

    for audit in audits.values():
        stages = audit["stages"]
        worst_span = max(
            (stage["q_span"] for stage in stages),
            default=math.inf,
        )
        population_factor = (
            math.exp(min(worst_span, 700.0))
            if math.isfinite(worst_span)
            else math.inf
        )
        active_count = len(audit["active_lines"])
        line_rows = [
            line_row
            for stage in stages
            for line_row in stage.get("lines", [])
        ]
        clean_feature_count = sum(
            bool(line_row.get("clean_feature", False))
            for line_row in line_rows
        )
        unresolved_interferences = [
            {
                "line": line_row.get("label", ""),
                "candidates": list(line_row.get("interferences", []) or []),
            }
            for line_row in line_rows
            if line_row.get("interferences")
        ]
        branching_groups = []
        for stage in stages:
            pending = sorted(
                stage.get("lines", []),
                key=lambda row: safe_float(row.get("upper_energy_cm"), 0.0),
            )
            while pending:
                seed = pending.pop(0)
                seed_energy = safe_float(seed.get("upper_energy_cm"), 0.0)
                group = [seed]
                remaining = []
                for candidate in pending:
                    candidate_energy = safe_float(
                        candidate.get("upper_energy_cm"),
                        0.0,
                    )
                    if seed_energy > 0.0 and abs(candidate_energy - seed_energy) <= 1.0:
                        group.append(candidate)
                    else:
                        remaining.append(candidate)
                pending = remaining
                if len(group) < 2:
                    continue
                q_group = [safe_float(row.get("q_contribution"), math.nan) for row in group]
                q_group = [value for value in q_group if math.isfinite(value)]
                if len(q_group) < 2:
                    continue
                factor = math.exp(min(max(q_group) - min(q_group), 700.0))
                branching_groups.append({
                    "ion": stage.get("ion"),
                    "upper_energy_cm": seed_energy,
                    "factor": factor,
                    "lines": [row.get("label", "") for row in group],
                })
        branching_factor = max(
            (group["factor"] for group in branching_groups),
            default=1.0,
        )
        if active_count < 2 or not stages:
            status = "Insufficient"
        elif clean_feature_count < 2:
            status = "Blended"
        elif branching_factor >= 3.0 * (1.0 - 1.0e-9):
            status = "Poor"
        elif branching_factor > 1.5:
            status = "Review"
        elif population_factor <= 1.5:
            status = "Stable"
        elif population_factor <= 3.0:
            status = "Review"
        else:
            status = "Poor"
        audit.update(
            {
                "active_count": active_count,
                "clean_feature_count": clean_feature_count,
                "excluded_count": len(audit["excluded_lines"]),
                "omitted_count": len(audit["omitted_lines"]),
                "replicate_rejected_count": len(
                    audit.get("replicate_rejected_lines", [])
                ),
                "q_span": worst_span,
                "population_factor": population_factor,
                "branching_groups": branching_groups,
                "branching_factor": branching_factor,
                "unresolved_interferences": unresolved_interferences,
                "status": status,
                "q_display": "; ".join(
                    f"{_roman_ion(stage['ion'])}: {stage['q']:.5g}"
                    for stage in stages
                ),
            }
        )
    return audits


def libspp_fit_boltzmann_excel_intercepts(app: "MainWindow", groups, kt: float):
    """Fit free per-species intercepts as used by the comparison Excel sheet.

    The supplied common temperature is still used for partition functions and
    ionization balance. The regression slope and intercept, however, come from
    each species' own points, matching Excel ``INTERCEPT(y, x)``.
    """
    results = {}
    if kt <= 0.0:
        return results
    selected_elements = _selected_analysis_elements(app)
    for key, pts in groups.items():
        if selected_elements is not None and key[0] not in selected_elements:
            continue
        active_pts = [point for point in pts if not point.get("inactive")]
        if len(active_pts) < 2:
            continue
        fit = linear_fit(
            [point["x"] for point in active_pts],
            [_sac_corrected_fit_y(app, point) for point in active_pts],
        )
        if not fit:
            continue
        slope, intercept = fit
        specie, ion = key
        try:
            z = app.libs_db.partition_function(specie, ion, kt * 11604.45)
        except Exception:
            z = 1.0
        results[key] = {
            "species": specie,
            "ion": ion,
            "nlines": len(active_pts),
            "kt": kt,
            "regression_kt": -1.0 / slope if slope < 0.0 else 0.0,
            "q": intercept,
            "q_at_t": intercept,
            "z": z,
            "points": active_pts,
            "slope": slope,
            "intercept_mode": "excel_free",
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


def _parse_neutral_fractions(value) -> dict[str, float]:
    """Parse ``Cd=0.03; Ni=0.024`` or a JSON object into 0-1 fractions."""
    if isinstance(value, dict):
        raw = value
    else:
        text = str(value or "").strip()
        try:
            parsed = json.loads(text) if text else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            raw = parsed
        else:
            raw = {
                match.group(1): match.group(2)
                for match in re.finditer(
                    r"([A-Za-z]{1,2})\s*=\s*([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)",
                    text,
                )
            }
    fractions = {}
    for element, value in raw.items():
        fraction = safe_float(value, 0.0)
        if 1.0 < fraction <= 100.0:
            fraction /= 100.0
        symbol = str(element or "").strip().capitalize()
        if symbol and 0.0 < fraction <= 1.0:
            fractions[symbol] = fraction
    return fractions


def libspp_saha_cflibs(
    app: "MainWindow",
    fits: dict,
    kt: float,
    ne: Optional[float] = None,
    *,
    ionization_mode: Optional[str] = None,
    neutral_fractions=None,
):
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
    ionization_mode = str(
        ionization_mode
        or getattr(app.options, "cflibs_ionization_mode", "saha")
    ).strip().lower()
    manual_fractions = _parse_neutral_fractions(
        neutral_fractions
        if neutral_fractions is not None
        else getattr(app.options, "cflibs_neutral_fractions", "")
    )
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
        manual_fraction = manual_fractions.get(sp) if ionization_mode == "manual" else None
        if manual_fraction is not None:
            if n1 > 0.0:
                conc_from_fraction = n1 / manual_fraction
                n2 = max(conc_from_fraction - n1, 0.0)
            elif n2 > 0.0 and manual_fraction < 1.0:
                conc_from_fraction = n2 / (1.0 - manual_fraction)
                n1 = max(conc_from_fraction - n2, 0.0)
            ionization_source = "manual neutral fraction"
        else:
            # Fill the missing stage with the same Saha balance used in
            # Unit9/calcola().
            saha_factor = (
                6.04e21 / ne
                * (kt ** 1.5)
                * (z2 / z1 if z1 else 1.0)
                * math.exp(-eion / kt)
                if ne
                else 0.0
            )
            if n1 > 0 and n2 <= 0:
                n2 = n1 * saha_factor
            elif n2 > 0 and n1 <= 0 and saha_factor > 0:
                n1 = n2 / saha_factor
            ionization_source = "Saha-Eggert"
        conc = n1 + n2
        fit_points = [
            point
            for fit_result in (r1, r2)
            if fit_result
            for point in fit_result.get("points", [])
            if not point.get("inactive")
        ]
        neutral_ratio = n1 / conc if conc > 0 else 0.0
        ion_neutral_ratio = n2 / n1 if n1 > 0 else float("inf") if n2 > 0 else 0.0
        rows.append({
            "element": sp,
            "nlines": len(fit_points),
            "distinct_levels": len({
                round(safe_float(point.get("x", 0.0), 0.0), 8)
                for point in fit_points
            }),
            "neutral_conc": n1,
            "ionized_conc": n2,
            "conc": conc,
            "mass_rel": mass * conc,
            "atomic_mass": mass,
            "neutral_ratio": neutral_ratio,
            "ionized_neutral_ratio": ion_neutral_ratio,
            "ionization_source": ionization_source,
            "manual_neutral_fraction": manual_fraction,
            "ne": ne,
        })
    total_n = sum(r["conc"] for r in rows) or 1.0
    total_m = sum(r["mass_rel"] for r in rows) or 1.0
    for r in rows:
        r["number_percent"] = r["conc"] / total_n * 100.0
        r["mass_percent"] = r["mass_rel"] / total_m * 100.0
    rows.sort(key=lambda r: r["mass_percent"], reverse=True)
    return rows


def validated_cflibs_rows(rows, quality) -> list[dict]:
    """Publish concentrations only after the quantitative quality gate passes."""
    if (
        not isinstance(quality, dict)
        or not bool(quality.get("approved", False))
        or str(quality.get("status", "") or "").strip().upper() != "PASS"
    ):
        return []
    return list(rows or [])


def libspp_cflibs_robustness(
    app: "MainWindow",
    groups: dict,
    fits: dict,
    rows: list[dict],
    kt: float,
    ne: float,
    *,
    ionization_mode: str = "saha",
    neutral_fractions=None,
) -> dict:
    """Stress-test a multielement result without using a nominal composition.

    The audit isolates three internal sensitivities: omission of each analytical
    line, the stored replicate Voigt areas at fixed T/Ne, and the measured
    uncertainty intervals of T and Ne.  It never deletes a line from the real
    analysis and never tunes a result toward an expected alloy composition.
    """
    baseline = {
        str(row.get("element", "") or "").strip().capitalize(): {
            "number_percent": safe_float(row.get("number_percent"), math.nan),
            "mass_percent": safe_float(row.get("mass_percent"), math.nan),
        }
        for row in rows
        if str(row.get("element", "") or "").strip()
    }
    selected = _selected_analysis_elements(app)
    expected_elements = set(selected) if selected is not None else set(baseline)
    active_points = [
        point
        for fit in fits.values()
        for point in fit.get("points", [])
        if not point.get("inactive")
    ]

    def line_label(point):
        line = point.get("line")
        element = str(getattr(line, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(line, "ion", 0), 0)
        wavelength = abs(
            safe_float(
                getattr(line, "asswavelen", 0.0)
                or getattr(line, "wavelen", 0.0),
                0.0,
            )
        )
        return f"{element} {_roman_ion(ion)} {wavelength:.6g} nm"

    def copied_groups(*, omit_point=None, replicate_index=None):
        copied = {}
        omitted_id = id(omit_point) if omit_point is not None else None
        for key, points in groups.items():
            copied_points = []
            for point in points:
                clone = dict(point)
                if omitted_id is not None and id(point) == omitted_id:
                    clone["inactive"] = True
                elif replicate_index is not None and not clone.get("inactive"):
                    line = clone.get("line")
                    replicate_areas = list(
                        getattr(line, "fit_replicate_areas", ()) or ()
                    )
                    replicate_area = (
                        replicate_areas[replicate_index]
                        if replicate_index < len(replicate_areas)
                        else None
                    )
                    mean_area = safe_float(
                        getattr(line, "fit_replicate_area_mean", math.nan),
                        math.nan,
                    )
                    replicate_area = safe_float(replicate_area, math.nan)
                    if (
                        not math.isfinite(replicate_area)
                        or replicate_area <= 0.0
                        or not math.isfinite(mean_area)
                        or mean_area <= 0.0
                    ):
                        clone["inactive"] = True
                    else:
                        clone["y"] = safe_float(clone.get("y"), 0.0) + math.log(
                            replicate_area / mean_area
                        )
                copied_points.append(clone)
            copied[key] = copied_points
        return copied

    def trial(label, trial_groups, trial_kt, trial_ne, *, source, omitted=""):
        trial_fits = libspp_fit_boltzmann_fixed_temperature(
            app,
            trial_groups,
            trial_kt,
        )
        trial_rows = libspp_saha_cflibs(
            app,
            trial_fits,
            trial_kt,
            trial_ne,
            ionization_mode=ionization_mode,
            neutral_fractions=neutral_fractions,
        )
        percentages = {
            str(row.get("element", "") or "").strip().capitalize(): {
                "number_percent": safe_float(row.get("number_percent"), math.nan),
                "mass_percent": safe_float(row.get("mass_percent"), math.nan),
            }
            for row in trial_rows
            if str(row.get("element", "") or "").strip()
        }
        complete = set(percentages) == expected_elements
        max_relative_change = 0.0
        for element, base_values in baseline.items():
            values = percentages.get(element, {})
            for field in ("number_percent", "mass_percent"):
                base_value = safe_float(base_values.get(field), math.nan)
                value = safe_float(values.get(field), math.nan)
                if not math.isfinite(base_value) or base_value <= 0.0 or not math.isfinite(value):
                    max_relative_change = math.inf
                    continue
                max_relative_change = max(
                    max_relative_change,
                    abs(value - base_value) / base_value,
                )
        return {
            "label": label,
            "source": source,
            "omitted_line": omitted,
            "kt": trial_kt,
            "ne": trial_ne,
            "complete": complete,
            "percentages": percentages,
            "max_relative_change": max_relative_change,
        }

    line_counts = defaultdict(int)
    for point in active_points:
        line = point.get("line")
        element = str(getattr(line, "specie", "") or "").strip().capitalize()
        if element:
            line_counts[element] += 1

    line_trials = []
    for point in active_points:
        label = line_label(point)
        line_trials.append(
            trial(
                f"without {label}",
                copied_groups(omit_point=point),
                kt,
                ne,
                source="leave-one-line-out",
                omitted=label,
            )
        )

    replicate_totals = []
    missing_replicate_lines = []
    for point in active_points:
        line = point.get("line")
        total = safe_int(getattr(line, "fit_replicate_area_total", 0), 0)
        areas = list(getattr(line, "fit_replicate_areas", ()) or ())
        if total >= 2 and len(areas) >= total:
            replicate_totals.append(total)
        else:
            missing_replicate_lines.append(line_label(point))
    replicate_total = (
        min(replicate_totals)
        if active_points and not missing_replicate_lines and replicate_totals
        else 0
    )
    replicate_trials = [
        trial(
            f"replicate {index + 1}",
            copied_groups(replicate_index=index),
            kt,
            ne,
            source="replicate",
        )
        for index in range(replicate_total)
    ]

    temperature_relative_uncertainty = math.nan
    saha = getattr(app, "last_saha_boltzmann", None)
    if isinstance(saha, dict):
        selected_element = str(
            saha.get("selected_element", "") or ""
        ).strip().capitalize()
        for item in saha.get("elements", []) or []:
            if str(item.get("element", "") or "").strip().capitalize() != selected_element:
                continue
            quality = item.get("quality") or {}
            candidates = [
                safe_float(quality.get("relative_slope_error"), math.nan),
                safe_float(quality.get("loo_relative_span"), math.nan),
            ]
            candidates = [
                value for value in candidates
                if math.isfinite(value) and value > 0.0
            ]
            if candidates:
                temperature_relative_uncertainty = max(candidates)
            break
    halpha = getattr(app, "last_halpha_result", None)
    ne_relative_uncertainty = (
        safe_float(halpha.get("ne_relative_uncertainty"), math.nan)
        if isinstance(halpha, dict)
        else math.nan
    )
    parameter_trials = []
    if math.isfinite(temperature_relative_uncertainty) and temperature_relative_uncertainty > 0.0:
        for sign, suffix in ((-1.0, "low"), (1.0, "high")):
            trial_kt = kt * max(0.05, 1.0 + sign * temperature_relative_uncertainty)
            parameter_trials.append(
                trial(
                    f"T {suffix}",
                    copied_groups(),
                    trial_kt,
                    ne,
                    source="temperature uncertainty",
                )
            )
    if math.isfinite(ne_relative_uncertainty) and ne_relative_uncertainty > 0.0:
        for sign, suffix in ((-1.0, "low"), (1.0, "high")):
            trial_ne = ne * max(0.05, 1.0 + sign * ne_relative_uncertainty)
            parameter_trials.append(
                trial(
                    f"Ne {suffix}",
                    copied_groups(),
                    kt,
                    trial_ne,
                    source="electron-density uncertainty",
                )
            )

    def finite_trial_values(trials, element, field):
        values = [
            safe_float(
                item.get("percentages", {}).get(element, {}).get(field),
                math.nan,
            )
            for item in trials
            if item.get("complete")
        ]
        return [value for value in values if math.isfinite(value)]

    def relative_cv(values):
        if len(values) < 2:
            return math.inf
        mean = math.fsum(values) / len(values)
        if mean == 0.0:
            return math.inf
        variance = math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
        return math.sqrt(max(variance, 0.0)) / abs(mean)

    element_summaries = {}
    for element, base_values in baseline.items():
        loo_number = finite_trial_values(line_trials, element, "number_percent")
        loo_mass = finite_trial_values(line_trials, element, "mass_percent")
        replicate_number = finite_trial_values(
            replicate_trials, element, "number_percent"
        )
        replicate_mass = finite_trial_values(
            replicate_trials, element, "mass_percent"
        )
        parameter_number = finite_trial_values(
            parameter_trials, element, "number_percent"
        )
        parameter_mass = finite_trial_values(
            parameter_trials, element, "mass_percent"
        )

        def maximum_relative(values, field):
            base_value = safe_float(base_values.get(field), math.nan)
            if not values or not math.isfinite(base_value) or base_value <= 0.0:
                return math.inf
            return max(abs(value - base_value) / base_value for value in values)

        worst_trial = max(
            line_trials,
            key=lambda item: max(
                abs(
                    safe_float(
                        item.get("percentages", {}).get(element, {}).get(field),
                        math.nan,
                    )
                    - safe_float(base_values.get(field), math.nan)
                ) / max(abs(safe_float(base_values.get(field), math.nan)), 1.0e-30)
                if math.isfinite(
                    safe_float(
                        item.get("percentages", {}).get(element, {}).get(field),
                        math.nan,
                    )
                )
                else math.inf
                for field in ("number_percent", "mass_percent")
            ),
            default=None,
        )
        loo_relative = max(
            maximum_relative(loo_number, "number_percent"),
            maximum_relative(loo_mass, "mass_percent"),
        )
        replicate_cv = max(
            relative_cv(replicate_number),
            relative_cv(replicate_mass),
        )
        parameter_relative = max(
            maximum_relative(parameter_number, "number_percent"),
            maximum_relative(parameter_mass, "mass_percent"),
        )
        element_summaries[element] = {
            "element": element,
            "active_lines": line_counts.get(element, 0),
            "baseline_number_percent": base_values["number_percent"],
            "baseline_mass_percent": base_values["mass_percent"],
            "loo_number_min": min(loo_number) if loo_number else math.nan,
            "loo_number_max": max(loo_number) if loo_number else math.nan,
            "loo_mass_min": min(loo_mass) if loo_mass else math.nan,
            "loo_mass_max": max(loo_mass) if loo_mass else math.nan,
            "loo_max_relative_change": loo_relative,
            "loo_worst_line": (
                worst_trial.get("omitted_line", "") if worst_trial else ""
            ),
            "replicate_count": len(replicate_number),
            "replicate_number_cv": relative_cv(replicate_number),
            "replicate_mass_cv": relative_cv(replicate_mass),
            "replicate_max_cv": replicate_cv,
            "parameter_trial_count": min(len(parameter_number), len(parameter_mass)),
            "parameter_max_relative_change": parameter_relative,
        }

    return {
        "expected_elements": sorted(expected_elements),
        "baseline_elements": sorted(baseline),
        "line_counts": dict(line_counts),
        "line_trials": line_trials,
        "line_trials_complete": bool(line_trials) and all(
            item.get("complete") for item in line_trials
        ),
        "line_loo_max_relative_change": max(
            (item.get("max_relative_change", math.inf) for item in line_trials),
            default=math.inf,
        ),
        "replicate_total": replicate_total,
        "replicate_trials": replicate_trials,
        "replicate_trials_complete": bool(replicate_trials) and all(
            item.get("complete") for item in replicate_trials
        ),
        "missing_replicate_lines": missing_replicate_lines,
        "replicate_max_composition_cv": max(
            (item.get("replicate_max_cv", math.inf) for item in element_summaries.values()),
            default=math.inf,
        ),
        "temperature_relative_uncertainty": temperature_relative_uncertainty,
        "ne_relative_uncertainty": ne_relative_uncertainty,
        "parameter_trials": parameter_trials,
        "parameter_trials_complete": bool(parameter_trials) and all(
            item.get("complete") for item in parameter_trials
        ),
        "parameter_max_relative_change": max(
            (item.get("parameter_max_relative_change", math.inf) for item in element_summaries.values()),
            default=math.inf,
        ),
        "elements": element_summaries,
    }


def format_cflibs_robustness_report(robustness: Optional[dict]) -> str:
    if not isinstance(robustness, dict) or not robustness:
        return "Multielement robustness audit has not been run."
    lines = [
        "CF-LIBS multielement robustness",
        (
            f"Leave-one-line-out: {len(robustness.get('line_trials', []) or [])} trials; "
            f"maximum relative composition change "
            f"{safe_float(robustness.get('line_loo_max_relative_change'), math.inf):.1%}"
        ),
        (
            f"Replicate compositions: {robustness.get('replicate_total', 0)}; "
            f"maximum CV "
            f"{safe_float(robustness.get('replicate_max_composition_cv'), math.inf):.1%}"
        ),
        (
            f"T/Ne uncertainty trials: {len(robustness.get('parameter_trials', []) or [])}; "
            f"maximum relative composition change "
            f"{safe_float(robustness.get('parameter_max_relative_change'), math.inf):.1%}"
        ),
        "",
        "Element | lines | LOO max | worst omitted line | replicate CV | T/Ne max",
    ]
    for element, item in sorted((robustness.get("elements") or {}).items()):
        lines.append(
            f"{element} | {item.get('active_lines', 0)} | "
            f"{safe_float(item.get('loo_max_relative_change'), math.inf):.1%} | "
            f"{item.get('loo_worst_line', '') or 'N/A'} | "
            f"{safe_float(item.get('replicate_max_cv'), math.inf):.1%} | "
            f"{safe_float(item.get('parameter_max_relative_change'), math.inf):.1%}"
        )
    missing = list(robustness.get("missing_replicate_lines", []) or [])
    if missing:
        lines.extend(["", "Lines without a complete replicate fit:", *missing])
    return "\n".join(lines)


def cflibs_quantitation_quality(
    app: "MainWindow",
    fits: dict,
    rows: list[dict],
    line_audit: dict[str, dict],
    kt: float,
    ne: float,
    robustness: Optional[dict] = None,
) -> dict:
    """Validate whether a CF-LIBS result is fit for quantitative reporting.

    These are conservative, configurable engineering gates. They do not turn
    McWhirter or a good regression into proof of LTE or stoichiometric
    ablation; those irreducible assumptions remain explicit in the report.
    """
    options = getattr(app, "options", None)
    strict = bool(getattr(options, "strict_quantitation", True))
    checks = []
    blockers = []
    warnings = []

    def add(name, passed, detail, *, blocking=True):
        passed = bool(passed)
        checks.append({
            "name": name,
            "passed": passed,
            "blocking": bool(blocking),
            "detail": str(detail),
        })
        if not passed:
            (blockers if blocking else warnings).append(f"{name}: {detail}")

    # A relative radiometric response is required because line intensities
    # from different detector windows enter the same intercept comparison.
    apply_response = bool(getattr(options, "apply_response", False))
    apply_after = bool(getattr(options, "apply_after", False))
    curves = list(getattr(getattr(app, "response_library", None), "curves", []) or [])
    analytical_spectra = [
        spectrum
        for spectrum in (getattr(app, "spectra", []) or [])
        if not bool(getattr(spectrum, "halpha_response_bypassed", False))
    ]
    if apply_after:
        response_ready = apply_response and bool(curves)
        response_detail = f"Apply After with {len(curves)} response curve(s)"
    else:
        response_ready = (
            apply_response
            and bool(analytical_spectra)
            and all(bool(getattr(spectrum, "response_corrected", False)) for spectrum in analytical_spectra)
        )
        corrected = sum(
            bool(getattr(spectrum, "response_corrected", False))
            for spectrum in analytical_spectra
        )
        response_detail = (
            f"Apply Before, {corrected}/{len(analytical_spectra)} analytical "
            "spectrum window(s) corrected"
        )
    add("Radiometric response", response_ready, response_detail)

    saha = getattr(app, "last_saha_boltzmann", None)
    selected_element = ""
    temperature_quality = None
    representative_temperature = 0.0
    representative_mode = ""
    if isinstance(saha, dict):
        selected_element = str(saha.get("selected_element", "") or "").strip().capitalize()
        representative_temperature = safe_float(saha.get("representative_temperature"), 0.0)
        representative_mode = str(saha.get("representative_mode", "") or "")
        for item in saha.get("elements", []) or []:
            if str(item.get("element", "") or "").strip().capitalize() == selected_element:
                temperature_quality = item.get("quality")
                break
    source_matches = (
        representative_temperature > 0.0
        and abs(representative_temperature - kt) / max(abs(kt), 1.0e-12) <= 0.02
    )
    add(
        "Temperature provenance",
        bool(selected_element)
        and representative_mode in ("most reliable element", "selected element")
        and source_matches,
        (
            f"{selected_element or 'none'}, mode={representative_mode or 'none'}, "
            f"stored kT={representative_temperature:.5g} eV, used kT={kt:.5g} eV"
        ),
    )
    if isinstance(temperature_quality, dict):
        temperature_ok = bool(temperature_quality.get("quantitative_eligible", False))
        failures = temperature_quality.get("quantitative_failures", []) or []
        temperature_detail = (
            f"{selected_element}: {temperature_quality.get('nlines', 0)} lines, "
            f"{temperature_quality.get('distinct_levels', 0)} levels, "
            f"dEk={safe_float(temperature_quality.get('energy_span_ev'), 0.0):.4g} eV, "
            f"R2={safe_float(temperature_quality.get('r2'), 0.0):.4g}, "
            f"LOO dT/T={safe_float(temperature_quality.get('loo_relative_span'), math.inf):.4g}"
        )
        if failures:
            temperature_detail += "; " + ", ".join(str(item) for item in failures)
    else:
        temperature_ok = False
        temperature_detail = "no stored quality audit for the thermometric element"
    add("Thermometric fit", temperature_ok, temperature_detail)

    halpha = getattr(app, "last_halpha_result", None)
    min_halpha_r2 = safe_float(getattr(options, "quality_min_halpha_r2", 0.90), 0.90)
    min_halpha_snr = safe_float(getattr(options, "quality_min_halpha_snr", 5.0), 5.0)
    max_ne_uncertainty = safe_float(
        getattr(options, "quality_max_ne_relative_uncertainty", 0.20),
        0.20,
    )
    halpha_ne = safe_float(halpha.get("ne"), 0.0) if isinstance(halpha, dict) else 0.0
    halpha_r2 = safe_float(halpha.get("r_squared"), 0.0) if isinstance(halpha, dict) else 0.0
    halpha_snr = safe_float(halpha.get("peak_prominence_to_noise"), 0.0) if isinstance(halpha, dict) else 0.0
    halpha_quality = str(halpha.get("peak_identification_quality", "") or "") if isinstance(halpha, dict) else ""
    ne_relative_uncertainty = safe_float(
        halpha.get("ne_relative_uncertainty"),
        math.inf,
    ) if isinstance(halpha, dict) else math.inf
    ne_matches = halpha_ne > 0.0 and abs(halpha_ne - ne) / max(abs(ne), 1.0e-30) <= 0.02
    halpha_kt = safe_float(
        halpha.get("ne_evaluation_kt", halpha.get("kt")),
        0.0,
    ) if isinstance(halpha, dict) else 0.0
    halpha_temperature_matches = (
        halpha_kt > 0.0
        and abs(halpha_kt - kt) / max(abs(kt), 1.0e-12) <= 0.02
    )
    halpha_ok = (
        isinstance(halpha, dict)
        and bool(halpha.get("available"))
        and safe_float(halpha.get("corrected_lorentzian_width"), 0.0) > 0.0
        and halpha_quality == "compatible"
        and halpha_r2 >= min_halpha_r2
        and halpha_snr >= min_halpha_snr
        and ne_matches
        and halpha_temperature_matches
        and math.isfinite(ne_relative_uncertainty)
        and ne_relative_uncertainty <= max_ne_uncertainty
    )
    add(
        "Electron density from H-alpha",
        halpha_ok,
        (
            f"quality={halpha_quality or 'missing'}, R2={halpha_r2:.4g} "
            f"(min {min_halpha_r2:.4g}), S/N={halpha_snr:.4g} "
            f"(min {min_halpha_snr:.4g}), Ne fit/used={halpha_ne:.4e}/{ne:.4e} cm^-3"
            f", kT for Ne/used={halpha_kt:.4g}/{kt:.4g} eV"
            f", relative Ne uncertainty={ne_relative_uncertainty:.4g} "
            f"(max {max_ne_uncertainty:.4g})"
        ),
    )
    ne_low = safe_float(getattr(options, "ne_low", 0.0), 0.0)
    ne_high = safe_float(getattr(options, "ne_high", 0.0), 0.0)
    add(
        "Electron-density range",
        ne > 0.0 and (not ne_low or ne > ne_low) and (not ne_high or ne < ne_high),
        f"Ne={ne:.4e} cm^-3; configured range {ne_low:.4e}-{ne_high:.4e}",
    )

    energy_span = (
        safe_float(temperature_quality.get("energy_span_ev"), 0.0)
        if isinstance(temperature_quality, dict)
        else 0.0
    )
    mcwhirter_threshold = (
        1.6e12 * math.sqrt(max(kt * 11604.45, 0.0)) * energy_span ** 3
        if energy_span > 0.0 and kt > 0.0
        else math.inf
    )
    mcwhirter_margin = ne / mcwhirter_threshold if mcwhirter_threshold > 0.0 else 0.0
    min_margin = safe_float(getattr(options, "quality_min_mcwhirter_margin", 3.0), 3.0)
    add(
        "McWhirter necessary criterion",
        math.isfinite(mcwhirter_margin) and mcwhirter_margin >= min_margin,
        (
            f"Ne/Nmin={mcwhirter_margin:.4g} (required safety margin {min_margin:.4g}); "
            f"Nmin={mcwhirter_threshold:.4e} cm^-3 using dE={energy_span:.4g} eV. "
            "Passing is necessary, not proof of LTE"
        ),
    )

    workflow = getattr(app, "last_self_absorption_result", None)
    applied = bool(getattr(app, "apply_sac_correction", False))
    sa_status = str(workflow.get("assessment_status", "") or "") if isinstance(workflow, dict) else ""
    sa_blocker = _self_absorption_quantification_blocker(app)
    sa_ok = False
    if isinstance(workflow, dict):
        if sa_status == "No significant evidence" and not applied:
            sa_ok = True
        elif sa_status in (
            "Self-absorption compatible",
            "Selective correction available",
        ) and applied and not sa_blocker:
            sa_ok = True
    add(
        "Self-absorption decision",
        sa_ok,
        f"status={sa_status or 'Not assessed'}, correction applied={applied}"
        + (f"; {sa_blocker}" if sa_blocker else ""),
    )

    selected_elements = _selected_analysis_elements(app)
    quantified_elements = {
        str(row.get("element", "") or "").strip().capitalize()
        for row in rows
        if str(row.get("element", "") or "").strip()
    }
    if selected_elements is None:
        coverage_ok = False
        coverage_detail = "no explicit analytical-element selection is available"
    else:
        missing_elements = sorted(selected_elements - quantified_elements)
        unexpected_elements = sorted(quantified_elements - selected_elements)
        coverage_ok = bool(selected_elements) and not missing_elements and not unexpected_elements
        coverage_detail = (
            f"selected={','.join(sorted(selected_elements)) or 'none'}; "
            f"quantified={','.join(sorted(quantified_elements)) or 'none'}"
        )
        if missing_elements:
            coverage_detail += "; missing=" + ",".join(missing_elements)
        if unexpected_elements:
            coverage_detail += "; unexpected=" + ",".join(unexpected_elements)
    add("Selected-element coverage", coverage_ok, coverage_detail)

    if isinstance(robustness, dict):
        min_composition_lines = max(
            1,
            safe_int(
                getattr(options, "quality_min_composition_lines", 3),
                3,
            ),
        )
        line_counts = dict(robustness.get("line_counts", {}) or {})
        insufficient = {
            element: safe_int(line_counts.get(element, 0), 0)
            for element in sorted(selected_elements or quantified_elements)
            if safe_int(line_counts.get(element, 0), 0) < min_composition_lines
        }
        add(
            "Multielement line redundancy",
            bool(line_counts) and not insufficient,
            (
                ", ".join(
                    f"{element}={safe_int(line_counts.get(element, 0), 0)}"
                    for element in sorted(selected_elements or quantified_elements)
                )
                + f"; required at least {min_composition_lines} per element"
                + (
                    "; insufficient="
                    + ",".join(f"{element}:{count}" for element, count in insufficient.items())
                    if insufficient
                    else ""
                )
            ),
        )

        max_loo_change = max(
            0.0,
            safe_float(
                getattr(
                    options,
                    "quality_max_composition_loo_relative_change",
                    0.20,
                ),
                0.20,
            ),
        )
        loo_change = safe_float(
            robustness.get("line_loo_max_relative_change"),
            math.inf,
        )
        loo_complete = bool(robustness.get("line_trials_complete"))
        add(
            "Leave-one-line-out composition stability",
            loo_complete and math.isfinite(loo_change) and loo_change <= max_loo_change,
            (
                f"max relative Number/Mass change={loo_change:.3g} "
                f"(max {max_loo_change:.3g}); "
                f"complete trials={loo_complete}; "
                f"trials={len(robustness.get('line_trials', []) or [])}"
            ),
        )

        require_replicates = bool(
            getattr(options, "quality_require_replicate_composition", True)
        )
        max_replicate_cv = max(
            0.0,
            safe_float(
                getattr(options, "quality_max_replicate_composition_cv", 0.15),
                0.15,
            ),
        )
        replicate_total = safe_int(robustness.get("replicate_total", 0), 0)
        replicate_cv = safe_float(
            robustness.get("replicate_max_composition_cv"),
            math.inf,
        )
        replicate_complete = bool(robustness.get("replicate_trials_complete"))
        replicate_ok = (
            replicate_total >= 2
            and replicate_complete
            and math.isfinite(replicate_cv)
            and replicate_cv <= max_replicate_cv
        )
        add(
            "Replicate composition stability",
            replicate_ok,
            (
                f"replicates={replicate_total}, complete={replicate_complete}, "
                f"max Number/Mass CV={replicate_cv:.3g} (max {max_replicate_cv:.3g})"
                + (
                    "; missing replicate fits="
                    + ", ".join(robustness.get("missing_replicate_lines", []) or [])
                    if robustness.get("missing_replicate_lines")
                    else ""
                )
            ),
            blocking=require_replicates,
        )

        max_parameter_change = max(
            0.0,
            safe_float(
                getattr(
                    options,
                    "quality_max_parameter_composition_relative_change",
                    0.20,
                ),
                0.20,
            ),
        )
        parameter_change = safe_float(
            robustness.get("parameter_max_relative_change"),
            math.inf,
        )
        parameter_complete = bool(robustness.get("parameter_trials_complete"))
        parameter_count = len(robustness.get("parameter_trials", []) or [])
        add(
            "T/Ne composition sensitivity",
            parameter_complete
            and parameter_count >= 4
            and math.isfinite(parameter_change)
            and parameter_change <= max_parameter_change,
            (
                f"trials={parameter_count}, complete={parameter_complete}, "
                f"max relative Number/Mass change={parameter_change:.3g} "
                f"(max {max_parameter_change:.3g}); "
                f"dT/T={safe_float(robustness.get('temperature_relative_uncertainty'), math.inf):.3g}, "
                f"dNe/Ne={safe_float(robustness.get('ne_relative_uncertainty'), math.inf):.3g}"
            ),
        )

    max_population_factor = safe_float(
        getattr(options, "quality_max_line_population_factor", 1.5),
        1.5,
    )
    min_observed_fraction = safe_float(
        getattr(options, "quality_min_observed_stage_fraction", 0.05),
        0.05,
    )
    max_stage_factor = safe_float(
        getattr(options, "quality_max_stage_balance_factor", 3.0),
        3.0,
    )
    for row in rows:
        element = str(row.get("element", "") or "").strip().capitalize()
        audit = line_audit.get(element, {})
        active_count = safe_int(audit.get("active_count", 0), 0)
        clean_feature_count = safe_int(
            audit.get("clean_feature_count", active_count),
            active_count,
        )
        distinct_levels = safe_int(row.get("distinct_levels", 0), 0)
        population_factor = safe_float(audit.get("population_factor"), math.inf)
        branching_factor = safe_float(audit.get("branching_factor", 1.0), 1.0)
        unresolved_count = len(audit.get("unresolved_interferences", []) or [])
        line_ok = (
            active_count >= 2
            and clean_feature_count >= 2
            and math.isfinite(population_factor)
            and population_factor <= max_population_factor
            and math.isfinite(branching_factor)
            and branching_factor <= max_population_factor
        )
        add(
            f"Analytical lines {element}",
            line_ok,
            (
                f"{active_count} lines/{clean_feature_count} clean spectral features/"
                f"{distinct_levels} Ek levels; fixed-slope population spread "
                f"x{population_factor:.4g}, same-upper branching spread "
                f"x{branching_factor:.4g} (max x{max_population_factor:.4g}); "
                f"unresolved features={unresolved_count}"
            ),
        )

        observed_stages = {
            safe_int(ion, 0)
            for species, ion in fits
            if str(species or "").strip().capitalize() == element
        }
        neutral_fraction = safe_float(row.get("neutral_ratio"), 0.0)
        observed_fraction = (
            1.0
            if observed_stages == {1, 2}
            else neutral_fraction
            if observed_stages == {1}
            else 1.0 - neutral_fraction
            if observed_stages == {2}
            else 0.0
        )
        stage_ok = bool(observed_stages) and observed_fraction >= min_observed_fraction
        add(
            f"Observed ionization stage {element}",
            stage_ok,
            (
                f"observed={','.join(_roman_ion(stage) for stage in sorted(observed_stages)) or 'none'}; "
                f"represented population fraction={observed_fraction:.4g} "
                f"(min {min_observed_fraction:.4g})"
            ),
        )
        if observed_stages == {1, 2}:
            observed_ratio = safe_float(row.get("ionized_neutral_ratio"), 0.0)
            try:
                metadata = app.libs_db.element_metadata(element)
                ionization_ev = safe_float(metadata.get("en_ion"), 0.0) * 1.23985e-4
                z1 = app.libs_db.partition_function(element, 1, kt * 11604.45)
                z2 = app.libs_db.partition_function(element, 2, kt * 11604.45)
                saha_ratio = (
                    6.04e21 / ne * kt ** 1.5 * z2 / z1 * math.exp(-ionization_ev / kt)
                )
            except Exception:
                saha_ratio = 0.0
            balance_factor = (
                max(observed_ratio / saha_ratio, saha_ratio / observed_ratio)
                if observed_ratio > 0.0 and saha_ratio > 0.0
                else math.inf
            )
            add(
                f"Saha stage balance {element}",
                math.isfinite(balance_factor) and balance_factor <= max_stage_factor,
                (
                    f"observed/theoretical discrepancy x{balance_factor:.4g} "
                    f"(max x{max_stage_factor:.4g})"
                ),
            )
        elif stage_ok:
            warnings.append(
                f"Ionization stage {element}: the unobserved stage is inferred by Saha-Eggert; "
                f"the observed stage represents {observed_fraction:.3g} of the population"
            )

    warnings.extend([
        "McWhirter does not prove LTE; spatial/temporal homogeneity is not established by one spectrum.",
        "Stoichiometric ablation and complete atomization cannot be verified from the line fit alone.",
        "Repeatability across independent laser shots is not yet part of this result.",
    ])
    approved = not blockers if strict else True
    status = "PASS" if approved and strict else "LEGACY OVERRIDE" if approved else "BLOCKED"
    result = {
        "strict": strict,
        "approved": approved,
        "status": status,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "thermometric_element": selected_element,
        "mcwhirter_threshold_cm3": mcwhirter_threshold,
        "mcwhirter_margin": mcwhirter_margin,
    }
    app.last_cflibs_quality = result
    return result


def format_cflibs_quality_report(quality: Optional[dict]) -> str:
    if not isinstance(quality, dict):
        return "Quantitative quality gate has not been run."
    lines = [f"CF-LIBS quantitative quality: {quality.get('status', 'UNKNOWN')}"]
    for check in quality.get("checks", []) or []:
        mark = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"[{mark}] {check.get('name')}: {check.get('detail')}")
    warnings = quality.get("warnings", []) or []
    if warnings:
        lines.append("")
        lines.append("Explicit limitations:")
        lines.extend(f"- {warning}" for warning in warnings)
    if not quality.get("strict", True):
        lines.extend([
            "",
            "Strict validation is disabled: displayed percentages are diagnostic only.",
        ])
    return "\n".join(lines)




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
            active_unit = getattr(app, "wavelength_unit", "angstrom")
            cand = app.libs_db.search_lines(
                wave,
                0.004 if active_unit == "nm" else 0.04,
                table=t.specie.capitalize(),
                ion=int(t.ion),
                limit=1,
                prefer_full_element_table=True,
                wavelength_unit=active_unit,
            )
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
        # Palleschi's SAC calculation uses the current CF-LIBS composition.
        # Quality checks remain visible to the operator but do not replace a
        # mathematically computed composition with an empty result.
        rows = getattr(self.master_app, "last_cflibs_rows", []) or []
        return {
            r["element"]: safe_float(r.get("number_percent"), 0.0)
            for r in rows
            if safe_float(r.get("number_percent"), 0.0) > 0.0
        }

    def compute(self):
        if not self.master_app.template_lines:
            _showinfo(self, "SAC", "Assigned analytical lines are required before calculating SAC factors.")
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
        element_percentages = self._element_percentages()
        if not element_percentages:
            message = (
                "SAC requires a current CF-LIBS composition. Compute CF-LIBS first. "
                "No equal-composition fallback is used."
            )
            self.master_app.status(message)
            _showwarning(self, "SAC", message)
            return
        rows = compute_sac_for_template_lines(
            self.master_app,
            kt,
            ne,
            lu,
            ntot,
            element_percentages,
        )
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


def _refresh_theoretical_workflow_ui(app):
    window = getattr(app, "theoretical_window", None)
    try:
        if window is not None and window.winfo_exists():
            window.sync_workflow_state()
    except Exception:
        pass


def _sync_self_absorption_temperature(app, applied):
    """Publish or remove the authoritative post-correction temperature."""
    workflow = getattr(app, "last_self_absorption_result", None)
    if not isinstance(workflow, dict):
        return False
    workflow.pop("post_temperature_ev", None)
    workflow.pop("post_temperature_source", None)
    app.post_irsac_temperature = None
    app.post_irsac_temperature_source = None
    if not applied:
        input_temperature_k = safe_float(workflow.get("input_temperature_k"), 0.0)
        if input_temperature_k > 0.0:
            app.session_temperature = input_temperature_k / 11604.45
            app.session_temperature_source = "pre-IRSAC temperature"
        return False
    corrected_lines = safe_int(workflow.get("enabled_lines"), 0)
    temperature_k = safe_float(workflow.get("temperature_k"), 0.0)
    if corrected_lines <= 0 or temperature_k <= 0.0:
        return False
    thermometric = workflow.get("thermometric_species")
    if isinstance(thermometric, (tuple, list)) and len(thermometric) >= 2:
        element = str(thermometric[0] or "").strip().capitalize()
        ion = safe_int(thermometric[1], 0)
        reference = f"{element} {_roman_ion(ion)}".strip()
    else:
        reference = "selected thermometric species"
    kt_ev = temperature_k / 11604.45
    mode = str(workflow.get("mode", "") or "").strip().lower()
    stage = (
        "IRSAC"
        if mode in ("hybrid", "irsac", "yang", "yang/aslam")
        else "Palleschi"
    )
    temperature_mode = str(
        workflow.get("thermometric_temperature_mode", "thermometric lines")
        or "thermometric lines"
    )
    source = (
        f"post-{stage} thermometric species: {reference} "
        f"({temperature_mode})"
    )
    app.post_irsac_temperature = kt_ev
    app.post_irsac_temperature_source = source
    app.session_temperature = kt_ev
    app.session_temperature_source = source
    workflow["post_temperature_ev"] = kt_ev
    workflow["post_temperature_source"] = source
    return True


def _irsac_voigt_refit_groups(lines, delta_min):
    """Group nearby analytical transitions for a shared multi-Voigt fit."""
    ordered = sorted(
        list(lines or []),
        key=lambda line: safe_float(getattr(line, "wavelen", 0.0), 0.0),
    )
    if not ordered:
        return []
    separation = max(abs(safe_float(delta_min, 0.5)), 1.0e-9)
    groups = []
    current = [ordered[0]]
    for line in ordered[1:]:
        previous = current[-1]
        if abs(
            safe_float(getattr(line, "wavelen", 0.0), 0.0)
            - safe_float(getattr(previous, "wavelen", 0.0), 0.0)
        ) < separation:
            current.append(line)
        else:
            groups.append(current)
            current = [line]
    groups.append(current)
    return groups


def _irsac_voigt_snapshot(app, runner, lines, limits, *, locked):
    """Build a GUI-independent Voigt request for an IRSAC area refresh."""
    options = app.options
    fit_spectrum = runner._active_spectrum_snapshot(lines)
    if not fit_spectrum:
        return None
    return {
        "spectrum": fit_spectrum,
        "xlim": tuple(sorted((float(limits[0]), float(limits[1])))),
        "ylim": (0.0, 1.0),
        "fit_range_locked": bool(locked),
        "preserve_view": True,
        "line_overrides": {},
        "lines": [
            {
                "key": id(line),
                "wavelen": safe_float(getattr(line, "wavelen", 0.0), 0.0),
                "fitwavelen": safe_float(
                    getattr(line, "fitwavelen", 0.0),
                    0.0,
                ),
                "wg": safe_float(getattr(line, "wg", 0.0), 0.0),
                "wl": safe_float(getattr(line, "wl", 0.0), 0.0),
                "specie": str(getattr(line, "specie", "") or ""),
                "ion": safe_int(getattr(line, "ion", 0), 0),
            }
            for line in lines
        ],
        "options": {
            "voigt_baseline_mode": _voigt_baseline_mode(options),
            "voigt_fit_ranges": getattr(options, "voigt_fit_ranges", "{}"),
            "fixed_wg": safe_float(
                getattr(options, "fixed_wg", 0.5),
                0.5,
            ),
            "fixed_wl": safe_float(
                getattr(options, "fixed_wl", 0.5),
                0.5,
            ),
            "fix_wg": bool(getattr(options, "fix_wg", False)),
            "fix_wl": bool(getattr(options, "fix_wl", False)),
            "fix_wavelength": bool(
                getattr(options, "fix_wavelength", False)
            ),
            "search_range": safe_float(
                getattr(options, "search_range", 0.1),
                0.1,
            ),
            "iterations": safe_int(
                getattr(options, "iterations", 20),
                20,
            ),
            # In this Origin-parity refresh, only user-selected analytical
            # transitions may contribute Voigt components. Selected close
            # lines are still solved together as a multi-Voigt group.
            "_selected_components_only": True,
        },
        "max_nfev": max(
            4000,
            safe_int(getattr(options, "iterations", 20), 20) * 400,
        ),
        "initial_free": None,
    }


def _irsac_stable_voigt_result(results, tolerance=0.075):
    """Choose the first ROI whose fitted areas are stable across three sizes."""
    valid = [
        result
        for result in list(results or [])
        if result
        and result.get("status") == "success"
        and (result.get("payload") or {}).get("fit_values")
        and all(
            item.get("quality_ok", True)
            and safe_float(item.get("integrated_area"), 0.0) > 0.0
            for item in (result.get("payload") or {}).get("fit_values", [])
        )
    ]
    if not valid:
        return None
    if len(valid) < 3:
        return valid[-1]
    for index in range(1, len(valid) - 1):
        triplet = valid[index - 1:index + 2]
        by_result = [
            {
                item.get("key"): safe_float(
                    item.get("integrated_area"),
                    0.0,
                )
                for item in (result.get("payload") or {}).get(
                    "fit_values",
                    [],
                )
            }
            for result in triplet
        ]
        common_keys = set(by_result[0])
        for values in by_result[1:]:
            common_keys.intersection_update(values)
        if not common_keys:
            continue
        stable = True
        for key in common_keys:
            areas = [values[key] for values in by_result]
            median = float(np.median(np.asarray(areas, dtype=float)))
            spread = (
                (max(areas) - min(areas)) / median
                if median > 0.0
                else math.inf
            )
            if not math.isfinite(spread) or spread > tolerance:
                stable = False
                break
        if stable:
            return valid[index]
    return valid[-1]


def _apply_irsac_voigt_payload(app, lines, payload):
    """Commit a headless Voigt result without opening an Auto Fit window."""
    values = {
        item.get("key"): item
        for item in list((payload or {}).get("fit_values") or [])
    }
    applied = 0
    rejected = 0
    nuisance_components = safe_int(
        (payload or {}).get("nuisance_components", 0),
        0,
    )
    for line in list(lines or []):
        item = values.get(id(line))
        if not item:
            continue
        line.fit_snr = safe_float(item.get("peak_snr"), 0.0)
        line.fit_quality_warning = str(item.get("quality_warning", "") or "")
        line.fit_at_center_bound = bool(item.get("at_center_bound", False))
        line.fit_nuisance_components = nuisance_components
        line.fitwavelen = safe_float(
            item.get("fit_center"),
            getattr(line, "wavelen", 0.0),
        )
        if not item.get("quality_ok", True):
            line.inte = "ERROR"
            line.wg = "ERROR"
            line.wl = "ERROR"
            line.error_inte = "ERROR"
            rejected += 1
            continue
        line.inte = safe_float(item.get("integrated_area"), 0.0)
        line.wg = abs(safe_float(item.get("gaussian_width"), 0.0))
        line.wl = abs(safe_float(item.get("lorentzian_width"), 0.0))
        line.error_inte = 0.0
        try:
            line.fitinte = safe_float(item.get("peak_intensity"), 0.0)
        except Exception:
            pass
        try:
            app.enrich_identified_template_line(
                line,
                tolerance=max(
                    0.02,
                    safe_float(getattr(app.options, "search_range", 0.2), 0.2),
                ),
            )
        except Exception:
            pass
        applied += 1
    return applied, rejected


def refit_irsac_voigt_areas(app, lines):
    """Refit IRSAC inputs from spectra, honoring saved ROIs before auto ROIs."""
    assigned = list(lines or [])
    if not assigned:
        return {
            "fitted": 0,
            "rejected": 0,
            "failed_groups": 0,
            "saved_roi_groups": 0,
            "adaptive_roi_groups": 0,
        }
    runner = object.__new__(RetroFitManagerWindow)
    runner.master_app = app
    runner.last_fit_result = None
    wavelength_scale = (
        10.0
        if str(app.current_wavelength_unit_label()).strip().lower()
        in {"a", "å", "angstrom"}
        else 1.0
    )
    half_widths = [
        value * wavelength_scale
        for value in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
    ]
    fitted = 0
    rejected = 0
    failed_groups = 0
    saved_roi_groups = 0
    adaptive_roi_groups = 0
    selected_payload = None
    groups = _irsac_voigt_refit_groups(
        assigned,
        getattr(app.options, "delta_min", 0.5),
    )
    for group in groups:
        session_roi_keys = set(
            getattr(app, "session_voigt_fit_range_keys", set()) or set()
        )
        group_keys = {
            _voigt_fit_range_key(line)
            for line in group
        }
        saved_limits = (
            _voigt_saved_fit_range(app.options, group)
            if group_keys and group_keys.issubset(session_roi_keys)
            else None
        )
        results = []
        if saved_limits:
            snapshot = _irsac_voigt_snapshot(
                app,
                runner,
                group,
                saved_limits,
                locked=True,
            )
            if snapshot:
                results.append(
                    runner._run_voigt_fit_snapshot(snapshot, lambda: False)
                )
            saved_roi_groups += 1
        else:
            low_center = min(
                safe_float(getattr(line, "wavelen", 0.0), 0.0)
                for line in group
            )
            high_center = max(
                safe_float(getattr(line, "wavelen", 0.0), 0.0)
                for line in group
            )
            for half_width in half_widths:
                snapshot = _irsac_voigt_snapshot(
                    app,
                    runner,
                    group,
                    (
                        low_center - half_width,
                        high_center + half_width,
                    ),
                    locked=False,
                )
                if snapshot:
                    results.append(
                        runner._run_voigt_fit_snapshot(
                            snapshot,
                            lambda: False,
                        )
                    )
            adaptive_roi_groups += 1
        chosen = _irsac_stable_voigt_result(results)
        if chosen is None:
            failed_groups += 1
            continue
        payload = chosen.get("payload") or {}
        group_fitted, group_rejected = _apply_irsac_voigt_payload(
            app,
            group,
            payload,
        )
        fitted += group_fitted
        rejected += group_rejected
        selected_payload = payload
    if selected_payload:
        app.fit_overlay = selected_payload.get("overlay")
        app.fit_baseline_overlay = selected_payload.get("baseline_overlay")
        app.fit_component_overlays = list(
            selected_payload.get("component_overlays") or []
        )
        app.fit_integration_bounds = list(
            selected_payload.get("integration_bounds") or []
        )
    app.notify_template_changed(redraw=False)
    app.redraw(preserve_view=True)
    summary = {
        "fitted": fitted,
        "rejected": rejected,
        "failed_groups": failed_groups,
        "saved_roi_groups": saved_roi_groups,
        "adaptive_roi_groups": adaptive_roi_groups,
    }
    app.last_irsac_voigt_refit = dict(summary)
    return summary


class SelfAbsorptionCheckWindow(tk.Toplevel):
    """Auditable Palleschi/Stark and iterative Yang IRSAC window."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Self-Absorption Check")
        self.geometry("1050x525")
        self.minsize(900, 460)
        self._rows = []
        self._stark_db_warning_shown = False
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=5)
        self.apply_sac_button = ttk.Button(top, text="Apply correction", command=self.apply_sac)
        self.apply_sac_button.pack(side="left")
        ttk.Label(top, text="Mode").pack(side="left", padx=(12, 3))
        configured_mode = _option_key_from_label(
            _SELF_ABSORPTION_MODE_LABELS,
            getattr(master.options, "irsac_mode", "hybrid"),
            "hybrid",
        )
        self.mode_var = tk.StringVar(value=configured_mode)
        self.mode_display_var = tk.StringVar(
            value=_SELF_ABSORPTION_MODE_LABELS[configured_mode]
        )
        self.mode_combo = ttk.Combobox(
            top,
            textvariable=self.mode_display_var,
            values=tuple(_SELF_ABSORPTION_MODE_LABELS.values()),
            width=39,
            state="readonly",
        )
        self.mode_combo.pack(side="left")
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)
        ttk.Label(top, text="Thermometric species").pack(side="left", padx=(10, 3))
        configured_thermo = str(getattr(master.options, "irsac_thermometric_species", "") or "").strip()
        configured_key = _parse_thermometric_species(configured_thermo)
        configured_label = (
            f"{configured_key[0]} {_roman_ion(configured_key[1])}"
            if configured_key is not None
            else "Auto (from Saha)"
        )
        reference_values = ("Auto (from Saha)",) + tuple(
            f"{element} {_roman_ion(ion)}"
            for element, ion in _available_irsac_thermometric_keys(master)
        )
        if configured_label not in reference_values:
            configured_label = "Auto (from Saha)"
            configured_key = None
            master.options.irsac_thermometric_species = ""
        self.thermo_var = tk.StringVar(value=configured_label)
        self.thermo_combo = ttk.Combobox(
            top,
            textvariable=self.thermo_var,
            values=reference_values,
            width=19,
            state="readonly",
        )
        self.thermo_combo.pack(side="left")
        self.thermo_combo.bind("<<ComboboxSelected>>", self._on_thermo_changed)
        ttk.Label(top, text="Fallback T (K)").pack(side="left", padx=(10, 3))
        initial_t = (
            _saha_temperature_for_irsac_reference(master, configured_key)
            or safe_float(getattr(master, "session_temperature", 0.0), 0.0) * 11604.45
        )
        self.temperature_var = tk.StringVar(value=f"{initial_t if initial_t > 0.0 else 11604.45:.7g}")
        ttk.Entry(top, textvariable=self.temperature_var, width=10).pack(side="left")
        ttk.Button(
            top,
            text="Recalculate IRSAC",
            command=self.recalculate,
        ).pack(side="left", padx=4)
        ttk.Button(top, text="Close", command=self.close).pack(side="left", padx=4)
        self.summary_var = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.summary_var).pack(side="right", padx=6)
        add_context_help_button(
            top,
            self,
            "Staged IRSAC temperature",
            (
                "pyLIBS first fits the raw Boltzmann temperature of the selected thermometric "
                "species. It applies Aslam Eq. (6) to that species once, refits its corrected "
                "temperature, and freezes that T. Every other species is then corrected once at "
                "the frozen T using its own internal reference. Their independent slopes are not "
                "forced to be parallel.\n\n"
                "IRSAC never refits the spectrum. It applies correction factors to the "
                "areas already measured by the selected Gaussian or Voigt fit. If a fit "
                "range must change, repeat that fit explicitly before opening IRSAC."
            ),
        ).pack(side="right", padx=(2, 6))
        reference_bar = ttk.Frame(self)
        reference_bar.pack(fill="x", padx=6, pady=(0, 5))
        ttk.Button(
            reference_bar,
            text="Use selected line as IRSAC reference",
            command=self._set_selected_line_reference,
        ).pack(side="left")
        ttk.Button(
            reference_bar,
            text="Automatic line references",
            command=self._clear_line_references,
        ).pack(side="left", padx=4)
        ttk.Label(reference_bar, text="Equation").pack(side="left", padx=(10, 3))
        configured_equation = _canonical_irsac_equation_mode(
            getattr(master.options, "irsac_equation_mode", "staged")
        )
        if configured_equation != "staged":
            configured_equation = "staged"
            master.options.irsac_equation_mode = "staged"
        equation_labels = {
            "staged": "Staged Aslam IRSAC (internal references)",
            "iterative": "Selective iterative IRSAC (internal reference)",
            "excel_worksheet": "Legacy radiometric worksheet (comparison only)",
        }
        equation_label = equation_labels[configured_equation]
        self.equation_var = tk.StringVar(value=equation_label)
        self.equation_combo = ttk.Combobox(
            reference_bar,
            textvariable=self.equation_var,
            values=("Staged Aslam IRSAC (internal references)",),
            state="readonly",
            width=47,
        )
        self.equation_combo.pack(side="left")
        self.equation_combo.bind("<<ComboboxSelected>>", self._on_equation_changed)
        self.reference_note_var = tk.StringVar(value=self._reference_summary())
        ttk.Label(reference_bar, textvariable=self.reference_note_var).pack(
            side="left", padx=8, fill="x", expand=True
        )

        diagnostic_bar = ttk.Frame(self)
        diagnostic_bar.pack(fill="x", padx=6, pady=(0, 5))
        self.diagnostic_var = tk.StringVar(value="Not calculated")
        ttk.Label(
            diagnostic_bar,
            textvariable=self.diagnostic_var,
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            diagnostic_bar,
            text="Diagnostic details",
            command=self._show_diagnostic_details,
        ).pack(side="right")

        columns = (
            "line",
            "wl",
            "stark_width",
            "snr",
            "method",
            "factor",
            "reference",
            "diagnostic",
            "flag",
            "use",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        headings = {
            "line": "Line",
            "wl": "Observed Lorentz FWHM",
            "stark_width": "Stark width",
            "snr": "Voigt S/N",
            "method": "Method",
            "factor": "Intensity factor",
            "reference": "IRSAC reference",
            "diagnostic": "Independent check",
            "flag": "Check",
            "use": "Use",
        }
        widths = {
            "line": 150,
            "wl": 135,
            "stark_width": 90,
            "snr": 75,
            "method": 135,
            "factor": 95,
            "reference": 100,
            "diagnostic": 150,
            "flag": 58,
            "use": 45,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=widths[col], stretch=False, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.protocol("WM_DELETE_WINDOW", self.close)
        fit_toplevel_to_content(self, min_width=900, min_height=460, max_width_fraction=0.90, max_height_fraction=0.80)
        center_window(self, master)
        self._update_apply_sac_button()
        self.lift(master)
        try:
            self.focus_force()
        except Exception:
            self.focus_set()

    def _show_diagnostic_details(self):
        workflow = getattr(self.master_app, "last_self_absorption_result", None)
        if not isinstance(workflow, dict):
            _showinfo(
                self,
                "Self-absorption assessment",
                "Calculate or refit the lines before opening the diagnostic details.",
            )
            return
        sections = [
            str(workflow.get("assessment_status", "Not assessed")),
            str(workflow.get("assessment_message", "") or ""),
            str(workflow.get("assessment_basis", "") or ""),
            (
                "Interpretation: a branching-ratio mismatch is compatible with "
                "self-absorption but is not unique proof; blends, response "
                "calibration, Aki uncertainty and fit quality are also checked."
            ),
        ]
        equation_mode = _canonical_irsac_equation_mode(
            workflow.get("equation_mode", "staged")
        )
        if equation_mode == "staged":
            history = workflow.get("temperature_history", [])
            raw_temperature = (
                safe_float(history[0], 0.0)
                if isinstance(history, (list, tuple)) and history
                else safe_float(workflow.get("input_temperature_k"), 0.0)
            )
            sections.append(
                (
                    "Staged Aslam IRSAC\n"
                    f"  raw thermometric T: {raw_temperature:.2f} K\n"
                    f"  corrected frozen T: {safe_float(workflow.get('temperature_k'), 0.0):.2f} K\n"
                    f"  thermometric species: {workflow.get('thermometric_species')}\n"
                    f"  corrected fitted areas: {safe_int(workflow.get('corrected_lines'), 0)}\n"
                    "  non-thermometric slopes are diagnostic only and are not forced"
                )
            )
        elif equation_mode == "iterative":
            reference_absorption = workflow.get("reference_absorption", {})
            reference_text = ", ".join(
                f"{label}: f_ref={safe_float(value, 0.0):.3f}"
                for label, value in sorted(reference_absorption.items())
            )
            sections.append(
                (
                    "Selective iterative IRSAC\n"
                    f"  cycles: {safe_int(workflow.get('iterations'), 0)}\n"
                    f"  converged: {'yes' if workflow.get('converged') else 'no'}\n"
                    f"  decisions stable: {'yes' if workflow.get('decisions_stable') else 'no'}\n"
                    f"  relative dT: {safe_float(workflow.get('relative_temperature_change'), math.inf):.6g}\n"
                    f"  max |d ln(f)|: {safe_float(workflow.get('max_log_factor_change'), math.inf):.6g}\n"
                    f"  thermometric RMSE: {safe_float(workflow.get('rmse'), math.nan):.6g}\n"
                    f"  initial T: {safe_float(workflow.get('initial_iterative_temperature_k'), 0.0):.2f} K\n"
                    f"  final common T: {safe_float(workflow.get('temperature_k'), 0.0):.2f} K\n"
                    f"  T basis: {workflow.get('thermometric_temperature_mode', 'thermometric lines')}\n"
                    f"  {reference_text or 'no valid internal references'}"
                )
            )
        species = workflow.get("species_assessments", {})
        slope_checks = workflow.get("species_slope_validation", {})
        if isinstance(species, dict):
            for label, assessment in sorted(species.items()):
                if not isinstance(assessment, dict):
                    continue
                slope_check = (
                    slope_checks.get(label, {})
                    if isinstance(slope_checks, dict)
                    else {}
                )
                compatible = slope_check.get("compatible")
                slope_status = (
                    "compatible"
                    if compatible is True
                    else "incompatible"
                    if compatible is False
                    else "not testable"
                )
                sections.append(
                    (
                        f"{label}: {assessment.get('status', 'Not assessed')}\n"
                        f"  same-upper-level checks: "
                        f"{assessment.get('equivalent_level_checks', 0)}, "
                        f"failed: {assessment.get('failed_checks', 0)}\n"
                        f"  IRSAC reference quality: "
                        f"{assessment.get('reference_quality', 'unknown')}\n"
                        f"  recommended rows: "
                        f"{assessment.get('recommended_lines', 0)}\n"
                        f"  final decision: "
                        f"{assessment.get('decision', 'Raw (not assessable)')}\n"
                        f"  independent slope: {slope_status}; "
                        f"m={safe_float(slope_check.get('slope'), math.nan):.6g}, "
                        f"expected={safe_float(slope_check.get('expected_slope'), math.nan):.6g}\n"
                        f"  {assessment.get('message', '')}"
                    )
                )
        selected = self.tree.focus()
        try:
            selected_line = self._rows[int(selected)]
        except (TypeError, ValueError, IndexError):
            selected_line = None
        if selected_line is not None:
            sections.append(
                (
                    f"Selected line: {self._line_label(selected_line)}\n"
                    f"  {getattr(selected_line, 'sa_diagnostic_reason', '')}"
                )
            )
        _showinfo(
            self,
            "Self-absorption assessment",
            "\n\n".join(section for section in sections if section),
        )

    def _update_apply_sac_button(self):
        state = bool(getattr(self.master_app, "apply_sac_correction", False))
        if hasattr(self, "apply_sac_button"):
            self.apply_sac_button.config(text="Remove correction" if state else "Apply correction")

    def _on_thermo_changed(self, _event=None):
        text = self.thermo_var.get().strip()
        self.master_app.options.irsac_thermometric_species = (
            "" if text.lower().startswith("auto") else text
        )
        manual_temperature = _saha_temperature_for_irsac_reference(
            self.master_app,
            _parse_thermometric_species(text),
        )
        if manual_temperature is not None:
            self.temperature_var.set(f"{manual_temperature:.7g}")
        elif text.lower().startswith("auto"):
            session_kt = safe_float(
                getattr(self.master_app, "session_temperature", 0.0),
                0.0,
            )
            if session_kt > 0.0:
                self.temperature_var.set(f"{session_kt * 11604.45:.7g}")
        self.recalculate(show_message=True)

    def _on_mode_changed(self, _event=None):
        mode = _option_key_from_label(
            _SELF_ABSORPTION_MODE_LABELS,
            self.mode_display_var.get(),
            "hybrid",
        )
        self.mode_var.set(mode)
        self.master_app.options.irsac_mode = mode
        self.recalculate(show_message=True)

    def _reference_summary(self):
        references = _active_irsac_reference_lines(self.master_app)
        if not references:
            return "IRSAC line references: automatic"
        values = ", ".join(
            f"{key[0]} {_roman_ion(key[1])} {wavelength:.6g} nm"
            for key, wavelength in sorted(references.items())
        )
        return f"IRSAC line references: {values}"

    def _on_equation_changed(self, _event=None):
        self.equation_var.set("Staged Aslam IRSAC (internal references)")
        self.master_app.options.irsac_equation_mode = "staged"
        self.recalculate(show_message=True)

    def _set_selected_line_reference(self):
        item = self.tree.focus()
        try:
            index = int(item)
        except (TypeError, ValueError):
            _showinfo(
                self,
                "IRSAC line reference",
                "Select one fitted line in the table first.",
            )
            return
        if index < 0 or index >= len(self._rows):
            return
        line = self._rows[index]
        species = str(getattr(line, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(line, "ion", 0), 0)
        wavelength = (
            abs(safe_float(getattr(line, "asswavelen", 0.0), 0.0))
            or abs(safe_float(getattr(line, "wavelen", 0.0), 0.0))
            or _template_line_center(line)
        )
        if not species or ion not in (1, 2) or wavelength <= 0.0:
            _showwarning(self, "IRSAC line reference", "The selected row is not a valid identified line.")
            return
        references = _parse_irsac_reference_lines(
            getattr(self.master_app.options, "irsac_reference_lines", "{}")
        )
        references[(species, ion)] = wavelength
        self.master_app.options.irsac_reference_lines = _serialize_irsac_reference_lines(references)
        self.reference_note_var.set(self._reference_summary())
        self.recalculate(show_message=True)

    def _clear_line_references(self):
        self.master_app.options.irsac_reference_lines = "{}"
        self.reference_note_var.set(self._reference_summary())
        self.recalculate(show_message=True)

    def _recompute_open_analyses(self):
        for attr in ("saha_window", "cflibs_window"):
            win = getattr(self.master_app, attr, None)
            try:
                if win is not None and win.winfo_exists():
                    if attr == "cflibs_window":
                        sync = getattr(win, "sync_session_inputs", None)
                        if callable(sync):
                            sync()
                    compute = getattr(win, "compute", None)
                    if callable(compute):
                        compute()
            except Exception:
                pass

    def recalculate(self, show_message=True):
        fitted_areas = {
            id(line): getattr(line, "inte", None)
            for line in self._assigned_lines()
        }
        result = self.refresh(show_message=show_message)

        def _unchanged(before, after):
            if before == after:
                return True
            try:
                return math.isnan(float(before)) and math.isnan(float(after))
            except (TypeError, ValueError):
                return False

        changed = [
            line
            for line in self._assigned_lines()
            if not _unchanged(
                fitted_areas.get(id(line)),
                getattr(line, "inte", None),
            )
        ]
        if changed:
            for line in changed:
                line.inte = fitted_areas[id(line)]
            message = (
                "IRSAC attempted to change fitted peak areas. The original areas "
                "were restored and the correction was not applied."
            )
            self.summary_var.set(message)
            _showerror(self, "IRSAC area invariant", message)
            return None
        if result is not None and bool(getattr(self.master_app, "apply_sac_correction", False)):
            _sync_self_absorption_temperature(self.master_app, True)
            self._recompute_open_analyses()
        return result

    def _assigned_lines(self):
        selected_elements = _selected_analysis_elements(self.master_app)
        return [
            line for line in getattr(self.master_app, "template_lines", []) or []
            if getattr(line, "specie", "")
            and getattr(line, "ion", 0)
            and template_line_is_acquired(self.master_app, line)
            and not _template_line_has_fit_error(line)
            and (
                selected_elements is None
                or str(getattr(line, "specie", "") or "").strip().capitalize()
                in selected_elements
            )
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
        ne, _source = active_electron_density(self.master_app)
        return ne or 0.0

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
        if ne <= 0.0:
            return ""
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
        snr = safe_float(getattr(line, "fit_snr", 0.0), 0.0)
        sac_value = safe_float(getattr(line, "sa_sac", ""), 0.0)
        method = str(getattr(line, "sa_method", "") or "")
        reference = safe_float(getattr(line, "sa_reference", 0.0), 0.0)
        diagnostic = str(
            getattr(line, "sa_diagnostic_status", "Not assessed") or "Not assessed"
        )
        use_value = "No" if not bool(getattr(line, "sa_use", True)) else "Yes"
        return (
            self._line_label(line),
            _format_sa_numeric(wl) if wl > 0.0 else "",
            stark if stark else "",
            f"{snr:.4g}" if snr > 0.0 else "",
            method,
            f"{sac_value:.6g}" if sac_value > 0.0 else "",
            f"{reference:.6g}" if reference > 0.0 else "",
            diagnostic,
            "CHECK" if bool(getattr(line, "sa_flagged", False)) else "",
            use_value,
        )

    def refresh(self, show_message=True):
        lines = self._assigned_lines()
        self._rows = list(lines)
        self.tree.delete(*self.tree.get_children())
        if not lines:
            self.summary_var.set("No assigned analytical lines are available")
            if show_message:
                _showinfo(self, "Self-Absorption Check", "Assigned analytical lines are required before assessing self-absorption.")
            return None
        mode = self.mode_var.get().strip().lower()
        self.master_app.options.irsac_mode = mode
        thermo_text = self.thermo_var.get().strip()
        configured_thermo = "" if thermo_text.lower().startswith("auto") else thermo_text
        self.master_app.options.irsac_thermometric_species = configured_thermo
        try:
            save_pylibs_ini(self.master_app.options)
        except Exception:
            pass
        try:
            result = calculate_hybrid_self_absorption(
                self.master_app,
                mode=mode,
                thermometric_species=configured_thermo,
                temperature_k=safe_float(self.temperature_var.get(), 11604.45),
            )
        except ValueError as exc:
            self.summary_var.set(str(exc))
            if show_message:
                _showerror(self, "IRSAC temperature reference", str(exc))
            return None
        workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
        if isinstance(workflow_result, dict):
            applied = bool(getattr(self.master_app, "apply_sac_correction", False))
            enabled_lines = sum(
                1 for line in self._rows
                if bool(getattr(line, "sa_use", False))
                and safe_float(getattr(line, "sa_sac", 0.0), 0.0) > 0.0
            )
            if applied and enabled_lines <= 0:
                self.master_app.apply_sac_correction = False
                applied = False
            workflow_result["applied"] = applied
            workflow_result["enabled_lines"] = enabled_lines if applied else 0
            assessment_status = str(
                workflow_result.get("assessment_status", "Not assessed")
            )
            assessment_message = str(
                workflow_result.get("assessment_message", "") or ""
            )
            self.diagnostic_var.set(
                f"{assessment_status}. {assessment_message}".strip()
            )
        else:
            self.diagnostic_var.set("Not assessed")
        for idx, line in enumerate(self._rows):
            self.tree.insert("", "end", iid=str(idx), values=self._line_values(line))
        self._update_apply_sac_button()
        if result is None:
            self.summary_var.set("No valid fitted/identified lines")
        else:
            thermo = result.thermometric_key or ("-", 0)
            ion_label = _roman_ion(thermo[1]) if thermo[1] else ""
            equation_mode = _canonical_irsac_equation_mode(
                getattr(self.master_app.options, "irsac_equation_mode", "staged")
            )
            if equation_mode == "staged":
                history = result.temperature_history
                raw_temperature = history[0] if history else safe_float(
                    self.temperature_var.get(),
                    0.0,
                )
                numerical = (
                    f"raw T={raw_temperature:.1f} K; "
                    f"corrected frozen T={result.temperature_k:.1f} K; "
                    f"thermometric={thermo[0]} {ion_label}"
                )
            elif equation_mode == "iterative":
                numerical = (
                    f"T={result.temperature_k:.1f} K; cycles={result.iterations}; "
                    f"dT/T={result.relative_temperature_change:.3g}; "
                    f"dlnf={result.max_log_factor_change:.3g}; "
                    f"converged={'yes' if result.converged else 'no'}"
                )
            else:
                numerical = (
                    f"T={result.temperature_k:.1f} K; reference={thermo[0]} {ion_label}; "
                    f"legacy equation={equation_mode}"
                )
            self.summary_var.set(
                f"{safe_int(getattr(self.master_app, 'last_self_absorption_result', {}).get('corrected_lines'), 0)} selected correction(s); "
                f"{numerical}; "
                f"assessment={getattr(self.master_app, 'last_self_absorption_result', {}).get('assessment_status', 'not assessed')}"
            )
        if bool(getattr(self.master_app, "apply_sac_correction", False)):
            _sync_self_absorption_temperature(self.master_app, True)
        _refresh_theoretical_workflow_ui(self.master_app)
        return result

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
        if bool(getattr(self.master_app, "apply_sac_correction", False)):
            enabled_rows = sum(
                1 for row in self._rows
                if bool(getattr(row, "sa_use", False))
                and safe_float(getattr(row, "sa_sac", 0.0), 0.0) > 0.0
            )
            workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
            if isinstance(workflow_result, dict):
                workflow_result["enabled_lines"] = enabled_rows
                workflow_result.pop("post_temperature_ev", None)
                workflow_result.pop("post_temperature_source", None)
            self.master_app.post_irsac_temperature = None
            self.master_app.post_irsac_temperature_source = None
            self.master_app.last_theoretical_spectrum = None
            _refresh_selective_irsac_temperature(self.master_app)
            _sync_self_absorption_temperature(self.master_app, True)
            self._recompute_open_analyses()
            _refresh_theoretical_workflow_ui(self.master_app)
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
        """Toggle the selected correction in plots, temperature and CF-LIBS fits."""
        enabling = not bool(getattr(self.master_app, "apply_sac_correction", False))
        workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
        if enabling and not isinstance(workflow_result, dict):
            self.refresh(show_message=False)
            workflow_result = getattr(
                self.master_app,
                "last_self_absorption_result",
                None,
            )
        if enabling:
            mode = str((workflow_result or {}).get("mode", "") or "").strip().lower()
            equation_mode = _canonical_irsac_equation_mode(
                (workflow_result or {}).get("equation_mode", "staged")
            )
            if (
                mode in ("hybrid", "irsac", "yang", "yang/aslam")
                and equation_mode in ("staged", "iterative")
                and not bool((workflow_result or {}).get("converged", False))
            ):
                _showerror(
                    self,
                    "IRSAC temperature",
                    (
                        "The corrected temperature could not be calculated from "
                        "the selected thermometric species. The factors cannot be "
                        "applied. Check fitted lines, energy span and internal "
                        "references, then recalculate."
                    ),
                )
                return
            selected_rows = [
                line for line in self._rows
                if bool(getattr(line, "sa_use", False))
                and safe_float(getattr(line, "sa_sac", 0.0), 0.0) > 0.0
            ]
            if not selected_rows:
                _showinfo(
                    self,
                    "Self-absorption correction",
                    (
                        "No supported correction row is selected.\n\n"
                        "Read the diagnostic details first. A manual override remains "
                        "possible by double-clicking a row to set Use=Yes, but a "
                        "numerical IRSAC factor alone is not evidence of "
                        "self-absorption."
                    ),
                )
                return
            unsupported = [
                line for line in selected_rows
                if not bool(getattr(line, "sa_recommended", False))
            ]
            if unsupported:
                labels = ", ".join(
                    self._line_label(line) for line in unsupported[:6]
                )
                if len(unsupported) > 6:
                    labels += ", ..."
                proceed = _askyesno(
                    self,
                    "Manual IRSAC override",
                    (
                        "The independent diagnostic does not support these "
                        f"selected corrections:\n{labels}\n\n"
                        "Applying them can move the temperature and "
                        "concentrations without demonstrating self-absorption. "
                        "Apply this manual override anyway?"
                    ),
                )
                if not proceed:
                    return
        self.master_app.apply_sac_correction = enabling
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
            sac = safe_float(self.tree.set(item, "factor"), 0.0)
            use_text = str(self.tree.set(item, "use")).strip().lower()
            use_yes = use_text in ("yes", "y", "true", "1", "si", "sì")
            valid = sac > 0.0 and math.isfinite(sac)
            line.sa_sac = sac if valid else ""
            line.sa_use = bool(use_yes and valid)
            if state and line.sa_use:
                enabled_rows += 1

        self.master_app.post_irsac_temperature = None
        self.master_app.post_irsac_temperature_source = None
        self.master_app.last_theoretical_spectrum = None
        workflow_result = getattr(self.master_app, "last_self_absorption_result", None)
        if isinstance(workflow_result, dict):
            workflow_result["applied"] = state
            workflow_result["enabled_lines"] = enabled_rows if state else 0
            workflow_result.pop("post_temperature_ev", None)
            workflow_result.pop("post_temperature_source", None)
        if state:
            _refresh_selective_irsac_temperature(self.master_app)
        _sync_self_absorption_temperature(self.master_app, state)

        msg = f"Self-absorption correction applied to {enabled_rows} line(s)" if state else "Self-absorption correction removed"
        self.summary_var.set(msg)
        self.master_app.status(msg)
        self._update_apply_sac_button()
        self._recompute_open_analyses()
        _refresh_theoretical_workflow_ui(self.master_app)

    def close(self):
        try:
            if getattr(self.master_app, "sac_check_window", None) is self:
                self.master_app.sac_check_window = None
        except Exception:
            pass
        self.destroy()


class TheoreticalSpectrumWindow(tk.Toplevel):
    """Diagnostic synthesis after the explicit self-absorption decision."""

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Theoretical spectrum - after self-absorption assessment")
        self.geometry("1120x700")
        self.minsize(900, 540)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Analysis kT (eV)").pack(side="left")
        self.kt_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.kt_var, width=9, state="readonly").pack(side="left", padx=3)
        ttk.Label(top, text="Aki min").pack(side="left", padx=(10, 2))
        self.aki_var = tk.StringVar(value=f"{safe_float(master.options.theoretical_aki_threshold, 1.0e5):.7g}")
        ttk.Entry(top, textvariable=self.aki_var, width=10).pack(side="left", padx=3)
        ttk.Label(top, text="Domain").pack(side="left", padx=(10, 2))
        self.domain_var = tk.StringVar(value="Auto")
        ttk.Combobox(
            top,
            textvariable=self.domain_var,
            values=("Auto", "Response-corrected", "Detector counts"),
            width=18,
            state="readonly",
        ).pack(side="left", padx=3)
        self.rescale_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Display-only least-squares scale", variable=self.rescale_var).pack(side="left", padx=8)
        self.calculate_button = ttk.Button(top, text="Calculate diagnostic spectrum", command=self.calculate)
        self.calculate_button.pack(side="left", padx=5)
        broadening = ttk.Frame(self)
        broadening.pack(fill="x", padx=8, pady=(0, 4))
        unit = master.current_wavelength_unit_label()
        ttk.Label(broadening, text=f"Global instrumental Gaussian FWHM @ H-alpha 656 nm ({unit})").pack(side="left")
        self.lsf_var = tk.StringVar(
            value=f"{max(0.0, safe_float(getattr(master.options, 'instrumental_width', 0.0), 0.0)):.7g}"
        )
        ttk.Entry(broadening, textvariable=self.lsf_var, width=10).pack(side="left", padx=4)
        add_context_help_button(
            broadening,
            self,
            "Instrumental broadening",
            (
                "Enter the instrument-only Gaussian FWHM measured near H-alpha. The same value is applied "
                "unchanged to all spectral windows. Do not enter the total Stark-broadened H-alpha FWHM."
            ),
        ).pack(side="left", padx=6)
        self.source_var = tk.StringVar(value="Temperature source: not available")
        ttk.Label(self, textvariable=self.source_var).pack(fill="x", padx=8, pady=(0, 2))
        self.summary_var = tk.StringVar(
            value="Assess self-absorption before diagnostic synthesis."
        )
        ttk.Label(self, textvariable=self.summary_var).pack(fill="x", padx=8, pady=(0, 4))
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(self, text="Matplotlib is not available.").pack(fill="both", expand=True)
            self.fig = self.ax = self.canvas = None
        else:
            self.fig = Figure(figsize=(9.5, 5.2), dpi=_figure_dpi(self))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=5)
        self.protocol("WM_DELETE_WINDOW", self.close)
        center_window(self, master)
        self.sync_workflow_state()
        self.after(100, self.calculate)

    def _workflow_readiness(self):
        workflow = getattr(
            self.master_app,
            "last_self_absorption_result",
            None,
        )
        applied = bool(getattr(self.master_app, "apply_sac_correction", False))
        assessment_status = str(
            workflow.get("assessment_status", "")
            if isinstance(workflow, dict)
            else ""
        ).strip().lower()
        if assessment_status == "no significant evidence" and not applied:
            temperature = safe_float(
                getattr(self.master_app, "session_temperature", 0.0),
                0.0,
            )
            source = str(
                getattr(self.master_app, "session_temperature_source", "")
                or "pre-correction thermometric temperature"
            )
        else:
            temperature = getattr(
                self.master_app,
                "post_irsac_temperature",
                None,
            )
            source = getattr(
                self.master_app,
                "post_irsac_temperature_source",
                "",
            )
        return theoretical_spectrum_readiness(
            workflow,
            applied,
            temperature,
            source,
        )

    def sync_workflow_state(self):
        readiness = self._workflow_readiness()
        if readiness.ready:
            self.kt_var.set(f"{readiness.temperature_ev:.7g}")
            self.source_var.set(f"Temperature source: {readiness.temperature_source}")
            self.calculate_button.configure(state="normal")
            self.summary_var.set(readiness.message)
        else:
            self.kt_var.set("")
            self.source_var.set("Temperature source: not available")
            self.calculate_button.configure(state="disabled")
            self.summary_var.set(readiness.message)
            self.master_app.last_theoretical_spectrum = None
        return readiness

    def _fit_is_response_calibrated(self):
        return bool(
            _fit_values_already_response_corrected(self.master_app)
            or _apply_after_response_enabled(self.master_app)
        )

    def _comparison_spectrum(self, domain):
        spectrum = select_spectrum_for_wavelengths(self.master_app, [])
        if spectrum is None:
            raise ValueError("Load a spectrum first.")
        if domain == "detector" and spectrum.response_corrected:
            return self.master_app._raw_spectrum_copy(spectrum)
        if domain == "response-corrected" and not spectrum.response_corrected:
            return self.master_app._response_corrected_copy(spectrum)
        return spectrum

    def _selected_domain(self):
        choice = self.domain_var.get()
        calibrated = self._fit_is_response_calibrated()
        if choice == "Detector counts":
            if not calibrated:
                raise ValueError(
                    "Detector-domain synthesis requires a fit calibrated with the instrumental response."
                )
            return "detector"
        if choice == "Response-corrected":
            if not calibrated:
                raise ValueError(
                    "Response-corrected synthesis requires Apply Before or Apply After response correction."
                )
            return "response-corrected"
        spectrum = select_spectrum_for_wavelengths(self.master_app, [])
        if spectrum is None:
            return "uncalibrated"
        if not calibrated:
            return "uncalibrated"
        return "detector" if not spectrum.response_corrected else "response-corrected"

    def _database_lines(self, fits, kt, low, high, aki_threshold):
        theory = []
        unit_scale = 10.0 if self.master_app.current_wavelength_unit_label() == "nm" else 1.0
        db_low, db_high = low * unit_scale, high * unit_scale
        center = 0.5 * (db_low + db_high)
        half_range = 0.5 * (db_high - db_low)
        for (species, ion), fit in fits.items():
            try:
                candidates = self.master_app.libs_db.search_lines(
                    center,
                    half_range,
                    table=species,
                    element=species,
                    ion=ion,
                    limit=10000,
                    prefer_full_element_table=True,
                )
            except Exception:
                candidates = []
            fitted_widths = [
                abs(safe_float(getattr(point.get("line"), "wl", 0.0), 0.0))
                for point in fit.get("points", [])
                if point.get("line") is not None and abs(safe_float(getattr(point.get("line"), "wl", 0.0), 0.0)) > 0.0
            ]
            lorentzian = sum(fitted_widths) / len(fitted_widths) if fitted_widths else 0.0
            for line in candidates:
                aki = abs(safe_float(line.aki, 0.0))
                gk = safe_float(line.gk, 0.0)
                ek_ev = safe_float(line.ek, 0.0) * 1.23985e-4
                if aki < aki_threshold or gk <= 0.0 or ek_ev <= 0.0:
                    continue
                try:
                    wavelength_nm = safe_float(line.wavelen, 0.0) / 10.0
                    area = radiometric_line_intensity_from_ordinate(
                        fit["q"] - ek_ev / kt,
                        wavelength_nm,
                        aki,
                        gk,
                        _boltzmann_intensity_mode(self.master_app),
                    )
                except (OverflowError, ValueError):
                    continue
                theory.append(TheoreticalLine(
                    wavelength=safe_float(line.wavelen, 0.0) / unit_scale,
                    area=area,
                    species=species,
                    ion=ion,
                    lorentzian_fwhm=lorentzian,
                ))
        return theory

    def calculate(self):
        if self.ax is None:
            return
        readiness = self.sync_workflow_state()
        if not readiness.ready:
            return
        if not self.master_app.spectra:
            self.summary_var.set("Load a spectrum first.")
            return
        kt = readiness.temperature_ev
        aki_threshold = max(0.0, safe_float(self.aki_var.get(), 1.0e5))
        self.master_app.options.theoretical_aki_threshold = aki_threshold
        groups, _skipped = libspp_boltzmann_groups_with_skips(self.master_app)
        fits = libspp_fit_boltzmann_fixed_temperature(self.master_app, groups, kt)
        if not fits:
            self.summary_var.set("No fitted and identified species are available for fixed-temperature intercepts.")
            return
        try:
            domain = self._selected_domain()
        except ValueError as exc:
            self.summary_var.set(str(exc))
            return
        detector_domain = domain == "detector"
        if detector_domain and not self.master_app.response_library.curves:
            self.summary_var.set("Detector-domain synthesis requires the instrumental-response files.")
            return
        try:
            spectrum = self._comparison_spectrum(domain)
        except Exception as exc:
            self.summary_var.set(str(exc))
            return
        low, high = min(spectrum.x), max(spectrum.x)
        lines = self._database_lines(fits, kt, low, high, aki_threshold)
        if not lines:
            self.summary_var.set("No database lines satisfy the current elements, ions and Aki threshold.")
            return
        default_lsf = max(safe_float(self.lsf_var.get(), 0.0), 0.0)
        if default_lsf <= 0.0:
            self.summary_var.set(
                "Enter the single instrumental Gaussian FWHM measured near H-alpha. "
                "It will be used globally for all spectral windows."
            )
            return
        self.master_app.options.instrumental_width = default_lsf
        save_pylibs_ini(self.master_app.options)
        model = synthesize_voigt_spectrum(
            spectrum.x,
            lines,
            lsf_fwhm=lambda _wavelength: default_lsf,
            response=(self.master_app.response_library.value_at if detector_domain else None),
            detector_domain=detector_domain,
        )
        scale = 1.0
        if self.rescale_var.get():
            model, scale = rescale_model_to_observation(spectrum.y, model)
        self.ax.clear()
        for index, (segment_x, segment_y) in enumerate(spectrum_plot_segments(spectrum)):
            self.ax.plot(
                segment_x, segment_y, color="#1f77b4", linewidth=0.8,
                label="Observed" if index == 0 else "_nolegend_",
            )
        model_spectrum = Spectrum(
            list(spectrum.x), list(model), name="LTE theoretical", source_windows=spectrum.source_windows
        )
        for index, (segment_x, segment_y) in enumerate(spectrum_plot_segments(model_spectrum)):
            self.ax.plot(
                segment_x, segment_y, color="#d62728", linewidth=0.9, alpha=0.9,
                label="LTE theoretical" if index == 0 else "_nolegend_",
            )
        self.ax.set_xlabel(f"Wavelength ({self.master_app.current_wavelength_unit_label()})")
        ylabel = {
            "detector": "Detector counts",
            "response-corrected": "Response-corrected intensity",
            "uncalibrated": "Current uncalibrated intensity",
        }[domain]
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True, alpha=0.25)
        self.ax.legend(loc="best")
        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()
        self.summary_var.set(
            f"{len(lines)} database line(s), {len(fits)} fitted species, {domain} domain; display scale={scale:.6g}. "
            f"Diagnostic only after the self-absorption decision; global instrumental FWHM @ H-alpha={default_lsf:.6g} "
            f"{self.master_app.current_wavelength_unit_label()} is applied to every line."
        )
        self.master_app.last_theoretical_spectrum = {
            "x": list(spectrum.x), "y": model, "lines": lines, "kt": kt,
            "detector_domain": detector_domain, "domain": domain, "display_scale": scale,
            "temperature_source": readiness.temperature_source,
            "diagnostic_only": True,
            "workflow": (
                "self-absorption assessment -> corrected or optically-thin "
                "temperature -> theoretical diagnostic"
            ),
        }

    def close(self):
        if getattr(self.master_app, "theoretical_window", None) is self:
            self.master_app.theoretical_window = None
        self.destroy()


class StandardCorrectionWindow(tk.Toplevel):
    """Unit31 OPC / .STD standard correction window."""
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Standard Correction / OPC")
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


OPC_NUMBER_PERCENT_BASIS = "number_percent"
OPC_MASS_PERCENT_BASIS = "mass_percent"
OPC_BASIS_LABELS = {
    OPC_NUMBER_PERCENT_BASIS: "Number %",
    OPC_MASS_PERCENT_BASIS: "Mass %",
}
OPC_NOMINAL_SUM_TOLERANCE_PERCENT = 1.1
OPC_ROUND_TRIP_TOLERANCE_PERCENT = 0.02


def opc_nominal_number_percent(rows, nominal_values, basis):
    """Convert an OPC nominal composition to Palleschi's Number % basis."""
    basis = str(basis or OPC_NUMBER_PERCENT_BASIS).strip().lower()
    if basis not in (OPC_NUMBER_PERCENT_BASIS, OPC_MASS_PERCENT_BASIS):
        raise ValueError(f"Unsupported OPC nominal-composition basis: {basis}")

    clean = {}
    atomic_masses = {}
    for row in rows or []:
        element = str(row.get("element", "") or "").strip().capitalize()
        value = safe_float((nominal_values or {}).get(element), 0.0)
        if not element or value <= 0.0:
            continue
        clean[element] = value
        if basis == OPC_MASS_PERCENT_BASIS:
            atomic_mass = safe_float(row.get("atomic_mass"), 0.0)
            if atomic_mass <= 0.0 or not math.isfinite(atomic_mass):
                raise ValueError(f"{element}: atomic mass is unavailable for Mass % conversion.")
            atomic_masses[element] = atomic_mass

    if basis == OPC_NUMBER_PERCENT_BASIS:
        return clean

    relative_moles = {
        element: value / atomic_masses[element]
        for element, value in clean.items()
    }
    total_moles = sum(relative_moles.values())
    if total_moles <= 0.0 or not math.isfinite(total_moles):
        return {}
    return {
        element: 100.0 * amount / total_moles
        for element, amount in relative_moles.items()
    }


def opc_number_percent_to_nominal(rows, number_values, basis):
    """Render canonical Number % values in the selected OPC input basis."""
    basis = str(basis or OPC_NUMBER_PERCENT_BASIS).strip().lower()
    clean = {
        str(row.get("element", "") or "").strip().capitalize(): safe_float(
            (number_values or {}).get(
                str(row.get("element", "") or "").strip().capitalize()
            ),
            0.0,
        )
        for row in rows or []
        if str(row.get("element", "") or "").strip()
    }
    clean = {element: value for element, value in clean.items() if value > 0.0}
    if basis == OPC_NUMBER_PERCENT_BASIS:
        return clean
    if basis != OPC_MASS_PERCENT_BASIS:
        raise ValueError(f"Unsupported OPC nominal-composition basis: {basis}")

    weighted = {}
    for row in rows or []:
        element = str(row.get("element", "") or "").strip().capitalize()
        if element not in clean:
            continue
        atomic_mass = safe_float(row.get("atomic_mass"), 0.0)
        if atomic_mass <= 0.0 or not math.isfinite(atomic_mass):
            raise ValueError(f"{element}: atomic mass is unavailable for Mass % conversion.")
        weighted[element] = clean[element] * atomic_mass
    total_mass = sum(weighted.values())
    if total_mass <= 0.0 or not math.isfinite(total_mass):
        return {}
    return {
        element: 100.0 * amount / total_mass
        for element, amount in weighted.items()
    }


def validate_opc_nominal_number_percent(rows, nominal_values):
    """Require one complete, normalized nominal composition for OPC."""
    expected_elements = {
        str(row.get("element", "") or "").strip().capitalize()
        for row in rows or []
        if str(row.get("element", "") or "").strip()
        and safe_float(row.get("number_percent"), 0.0) > 0.0
    }
    nominal = {
        str(element or "").strip().capitalize(): safe_float(value, 0.0)
        for element, value in (nominal_values or {}).items()
        if str(element or "").strip() and safe_float(value, 0.0) > 0.0
    }
    missing = sorted(expected_elements - set(nominal))
    if missing:
        raise ValueError(
            "Nominal composition is missing: " + ", ".join(missing) + "."
        )
    nominal = {
        element: nominal[element]
        for element in sorted(expected_elements)
    }
    total = sum(nominal.values())
    if abs(total - 100.0) > OPC_NOMINAL_SUM_TOLERANCE_PERCENT:
        raise ValueError(
            f"Nominal composition totals {total:.6g}%; expected 100%."
        )
    return {
        element: 100.0 * value / total
        for element, value in nominal.items()
    }


class CFLibsOPCWindow(tk.Toplevel):
    """Palleschi One Point Calibration from CF-LIBS number percentages."""

    def __init__(self, owner: "CFLibsWindow"):
        super().__init__(owner)
        self.owner = owner
        self.master_app = owner.master_app
        self.title("One Point Calibration (.OPC)")
        self.geometry("820x500")
        self.minsize(720, 340)
        self.factors: dict[str, float] = {}
        self.nominal_vars: dict[str, tk.StringVar] = {}
        self.nominal_entries: list[ttk.Entry] = []
        basis = str(
            getattr(self.master_app, "opc_nominal_basis", OPC_MASS_PERCENT_BASIS)
            or OPC_MASS_PERCENT_BASIS
        ).strip().lower()
        if basis not in OPC_BASIS_LABELS:
            basis = OPC_MASS_PERCENT_BASIS
        self._display_basis = basis
        self.nominal_basis_var = tk.StringVar(value=OPC_BASIS_LABELS[basis])
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Compute OPC", command=self.compute).pack(side="left")
        ttk.Button(top, text="Save Calibration...", command=self.save).pack(side="left", padx=4)
        ttk.Button(top, text="Close", command=self.close).pack(side="left", padx=4)
        ttk.Label(top, text="Nominal composition:").pack(side="left", padx=(18, 4))
        basis_box = ttk.Combobox(
            top,
            textvariable=self.nominal_basis_var,
            values=("Mass %", "Number %"),
            state="readonly",
            width=12,
        )
        basis_box.pack(side="left")
        basis_box.bind("<<ComboboxSelected>>", self._basis_changed)

        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="both", expand=True, padx=6, pady=5)
        self.column_headers = []
        for col, title in enumerate(("Element", "CF-LIBS Mass %", "Nominal Mass %")):
            label = ttk.Label(self.rows_frame, text=title, anchor="center", font=("TkDefaultFont", 9, "bold"))
            label.grid(
                row=0, column=col, sticky="ew", padx=4, pady=(0, 4)
            )
            self.column_headers.append(label)
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
        basis = self._selected_basis()
        field = "mass_percent" if basis == OPC_MASS_PERCENT_BASIS else "number_percent"
        basis_label = OPC_BASIS_LABELS[basis]
        self.column_headers[1].configure(text=f"CF-LIBS {basis_label}")
        self.column_headers[2].configure(text=f"Nominal {basis_label}")
        inputs = self._nominal_inputs()
        saved_values = inputs.get(basis, {})
        if basis == OPC_NUMBER_PERCENT_BASIS and not saved_values:
            saved_values = dict(getattr(self.master_app, "opc_nominal_percent", {}) or {})
            inputs[basis] = saved_values
        for display_row, row in enumerate(rows, start=1):
            element = row.get("element", "")
            calculated_percent = safe_float(row.get(field, 0.0), 0.0)
            saved = saved_values.get(element, "")
            var = self.nominal_vars.get(element)
            if var is None:
                text = format_template_display_value(saved) if safe_float(saved, 0.0) > 0.0 else ""
                var = tk.StringVar(value=text)
                self.nominal_vars[element] = var
            ttk.Label(self.rows_frame, text=element, anchor="center").grid(
                row=display_row, column=0, sticky="ew", padx=4, pady=2
            )
            ttk.Label(self.rows_frame, text=format_template_display_value(calculated_percent), anchor="center").grid(
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

    def _selected_basis(self):
        label = str(self.nominal_basis_var.get() or "").strip().casefold()
        return OPC_MASS_PERCENT_BASIS if label.startswith("mass") else OPC_NUMBER_PERCENT_BASIS

    def _nominal_inputs(self):
        inputs = getattr(self.master_app, "opc_nominal_inputs", None)
        if not isinstance(inputs, dict):
            inputs = {
                OPC_MASS_PERCENT_BASIS: {},
                OPC_NUMBER_PERCENT_BASIS: {},
            }
            self.master_app.opc_nominal_inputs = inputs
        inputs.setdefault(OPC_MASS_PERCENT_BASIS, {})
        inputs.setdefault(OPC_NUMBER_PERCENT_BASIS, {})
        return inputs

    def _nominal_value(self, element, text, basis=None):
        text = str(text or "").strip()
        if not text:
            return None
        value = safe_float(text, None)
        if value is None or value < 0.0 or value > 100.0:
            basis_label = OPC_BASIS_LABELS[basis or self._selected_basis()]
            raise ValueError(f"{element}: Nominal {basis_label} must be between 0 and 100.")
        return value

    def _current_rows(self):
        return self.owner.last_rows or getattr(self.master_app, "last_cflibs_rows", []) or []

    def _capture_nominal_inputs(self, basis):
        values = {}
        for row in self._current_rows():
            element = row.get("element", "")
            var = self.nominal_vars.get(element)
            if var is None:
                continue
            value = self._nominal_value(element, var.get(), basis)
            if value is not None:
                values[element] = value
        self._nominal_inputs()[basis] = values
        return values

    def _store_nominal_values(self):
        basis = self._selected_basis()
        values = self._capture_nominal_inputs(basis)
        nominal = opc_nominal_number_percent(self._current_rows(), values, basis)
        nominal = validate_opc_nominal_number_percent(
            self._current_rows(), nominal
        )
        self.master_app.opc_nominal_percent = nominal
        self.master_app.opc_nominal_basis = basis

    def _basis_changed(self, _event=None):
        new_basis = self._selected_basis()
        old_basis = self._display_basis
        if new_basis == old_basis:
            return
        try:
            old_values = self._capture_nominal_inputs(old_basis)
            canonical = opc_nominal_number_percent(
                self._current_rows(), old_values, old_basis
            )
            inputs = self._nominal_inputs()
            if canonical and not inputs.get(new_basis):
                inputs[new_basis] = opc_number_percent_to_nominal(
                    self._current_rows(), canonical, new_basis
                )
        except ValueError as exc:
            self.nominal_basis_var.set(OPC_BASIS_LABELS[old_basis])
            self._show_nominal_error(str(exc))
            return
        self._display_basis = new_basis
        self.master_app.opc_nominal_basis = new_basis
        self.nominal_vars = {}
        self.refresh()

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
        conversion_note = (
            " Nominal Mass % converted internally to Number %."
            if self._selected_basis() == OPC_MASS_PERCENT_BASIS
            else ""
        )
        self.master_app.status(
            f"OPC correction factors computed for {len(self.factors)} element(s)."
            + conversion_note
        )
        return True

    def _source_spectrum_filename(self):
        spectra = getattr(self.master_app, "spectra", []) or []
        if not spectra:
            return ""
        return getattr(spectra[0], "filename", "") or getattr(spectra[0], "name", "")

    def _calibration_rows(self):
        if not self.compute():
            return []
        if bool(getattr(self.master_app, "apply_sac_correction", False)) and any(
            _sac_factor_for_line(point.get("line")) is not None
            for points in (getattr(self.owner, "last_groups", {}) or {}).values()
            for point in points
            if point.get("line") is not None
        ):
            raise ValueError(
                "Remove the self-absorption correction before generating OPC. "
                "In Palleschi's procedure SAC remains separate from the composite OPC response."
            )
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
                observed_corrected = safe_float(
                    point.get("icorr", _template_line_intensity(line)),
                    0.0,
                )
                aki = safe_float(getattr(line, "aki", 0.0), 0.0)
                gk = safe_float(getattr(line, "gk", 0.0), 0.0)
                x = safe_float(point.get("x", 0.0), 0.0)
                nist_wavelength = safe_float(
                    point.get("nist_wavelength", _template_line_nist_wavelength(line)),
                    0.0,
                )
                wavelength_nm = safe_float(point.get("wavelength_nm", 0.0), 0.0)
                if wavelength_nm <= 0.0 and nist_wavelength > 0.0:
                    wavelength_nm = _boltzmann_wavelength_nm(self.master_app, nist_wavelength)
                if min(observed_corrected, abs(aki * gk), nist_wavelength, wavelength_nm) <= 0.0:
                    continue
                yp = fit["slope"] * x + fit.get("q_at_t", fit.get("q", 0.0)) + math.log(ratio)
                try:
                    target_corrected = radiometric_line_intensity_from_ordinate(
                        yp,
                        wavelength_nm,
                        aki,
                        gk,
                        _boltzmann_intensity_mode(self.master_app),
                    )
                    base_response, response_wavelength, _response_source = _opc_base_response_for_line(
                        self.master_app,
                        line,
                        point,
                    )
                    residual = observed_corrected / target_corrected
                    response_value = base_response * residual
                except (OverflowError, ZeroDivisionError, ValueError):
                    raise
                if not math.isfinite(response_value) or response_value <= 0.0:
                    continue
                species = f"{element} {_roman_ion(ion)}"
                rows.append((float(response_wavelength), response_value, element, species))
        rows.sort(key=lambda r: r[0])
        return rows

    def _round_trip_validation(self, calibration_rows):
        """Reapply a candidate OPC to its source lines before saving it."""
        if len(calibration_rows) < 2:
            raise ValueError(
                "At least two valid analytical lines are required to validate an OPC curve."
            )
        kt = safe_float(getattr(self.owner, "last_kt", 0.0), 0.0)
        ne = safe_float(getattr(self.owner, "last_ne", 0.0), 0.0)
        if kt <= 0.0 or ne <= 0.0:
            raise ValueError(
                "The source CF-LIBS temperature and electron density are required for OPC validation."
            )
        curve = ResponseCurve(
            [row[0] for row in calibration_rows],
            [row[1] for row in calibration_rows],
            "candidate.opc",
        )
        corrected_groups = {}
        for key, points in (getattr(self.owner, "last_groups", {}) or {}).items():
            corrected_points = []
            for point in points:
                clone = dict(point)
                if point.get("inactive"):
                    corrected_points.append(clone)
                    continue
                line = point.get("line")
                nist_wavelength = safe_float(
                    point.get(
                        "nist_wavelength",
                        _template_line_nist_wavelength(line) if line is not None else 0.0,
                    ),
                    0.0,
                )
                response_value = curve.value_at(nist_wavelength)
                raw_intensity = _template_line_intensity(line) if line is not None else 0.0
                aki = abs(safe_float(getattr(line, "aki", 0.0), 0.0))
                gk = safe_float(getattr(line, "gk", 0.0), 0.0)
                wavelength_nm = safe_float(point.get("wavelength_nm", 0.0), 0.0)
                if wavelength_nm <= 0.0 and nist_wavelength > 0.0:
                    wavelength_nm = _boltzmann_wavelength_nm(
                        self.master_app, nist_wavelength
                    )
                if (
                    response_value is None
                    or response_value <= 0.0
                    or min(raw_intensity, aki, gk, wavelength_nm) <= 0.0
                ):
                    raise ValueError(
                        f"The candidate OPC cannot reconstruct {key[0]} "
                        f"{nist_wavelength:.6g} nm."
                    )
                corrected_intensity = raw_intensity / response_value
                clone["eff"] = response_value
                clone["icorr"] = corrected_intensity
                clone["y"] = _boltzmann_ordinate(
                    self.master_app,
                    corrected_intensity,
                    wavelength_nm,
                    aki,
                    gk,
                )
                corrected_points.append(clone)
            corrected_groups[key] = corrected_points

        fits = libspp_fit_boltzmann_fixed_temperature(
            self.master_app,
            corrected_groups,
            kt,
        )
        rows = libspp_saha_cflibs(
            self.master_app,
            fits,
            kt,
            ne,
            ionization_mode="saha",
            neutral_fractions={},
        )
        expected = validate_opc_nominal_number_percent(
            self._current_rows(),
            getattr(self.master_app, "opc_nominal_percent", {}),
        )
        observed = {
            str(row.get("element", "") or "").strip().capitalize(): safe_float(
                row.get("number_percent"), 0.0
            )
            for row in rows
        }
        missing = sorted(set(expected) - set(observed))
        if missing:
            raise ValueError(
                "OPC round-trip did not return: " + ", ".join(missing) + "."
            )
        errors = {
            element: abs(observed[element] - expected[element])
            for element in expected
        }
        maximum_error = max(errors.values(), default=math.inf)
        return {
            "passed": maximum_error <= OPC_ROUND_TRIP_TOLERANCE_PERCENT,
            "expected_number_percent": expected,
            "observed_number_percent": observed,
            "absolute_errors_percentage_points": errors,
            "maximum_error_percentage_points": maximum_error,
            "tolerance_percentage_points": OPC_ROUND_TRIP_TOLERANCE_PERCENT,
        }

    def _calibration_audit(self, calibration_rows, validation):
        curve = ResponseCurve(
            [row[0] for row in calibration_rows],
            [row[1] for row in calibration_rows],
            "candidate.opc",
        )
        source_rows = self._current_rows()
        line_rows = []
        for key, points in (getattr(self.owner, "last_groups", {}) or {}).items():
            fit = (getattr(self.owner, "last_fits", {}) or {}).get(key, {})
            for point in points:
                if point.get("inactive"):
                    continue
                line = point.get("line")
                if line is None:
                    continue
                nist_wavelength = safe_float(
                    point.get("nist_wavelength", _template_line_nist_wavelength(line)),
                    0.0,
                )
                line_rows.append({
                    "element": str(key[0]),
                    "ion": safe_int(key[1], 0),
                    "nist_wavelength_nm": nist_wavelength,
                    "fitted_center_nm": _template_line_center(line),
                    "raw_fitted_area": _template_line_intensity(line),
                    "area_standard_error": safe_float(
                        getattr(line, "error_inte", 0.0), 0.0
                    ),
                    "profile": str(getattr(line, "fit_profile", "") or "voigt"),
                    "gaussian_fwhm_nm": abs(
                        safe_float(getattr(line, "wg", 0.0), 0.0)
                    ),
                    "lorentzian_fwhm_nm": abs(
                        safe_float(getattr(line, "wl", 0.0), 0.0)
                    ),
                    "aki": safe_float(getattr(line, "aki", 0.0), 0.0),
                    "gk": safe_float(getattr(line, "gk", 0.0), 0.0),
                    "upper_energy_cm_1": safe_float(
                        getattr(line, "ek", 0.0), 0.0
                    ),
                    "physical_response_divisor": safe_float(point.get("eff"), 1.0),
                    "corrected_area_before_opc": safe_float(point.get("icorr"), 0.0),
                    "opc_response_divisor": safe_float(curve.value_at(nist_wavelength), 0.0),
                    "boltzmann_x_ev": safe_float(point.get("x"), 0.0),
                    "boltzmann_y_before_opc": safe_float(point.get("y"), 0.0),
                    "fixed_slope": safe_float(fit.get("slope"), 0.0),
                    "fixed_intercept": safe_float(
                        fit.get("q_at_t", fit.get("q", 0.0)), 0.0
                    ),
                })
        source_files = []
        for spectrum in getattr(self.master_app, "spectra", []) or []:
            sources = list(getattr(spectrum, "source_windows", ()) or ())
            if not sources:
                sources = [spectrum]
            for source in sources:
                filename = str(getattr(source, "filename", "") or "").strip()
                name = Path(filename).name if filename else str(
                    getattr(source, "name", "") or ""
                ).strip()
                if name and name not in source_files:
                    source_files.append(name)
        response_files = [
            Path(str(getattr(response, "filename", "") or "")).name
            for response in getattr(
                getattr(self.master_app, "response_library", None),
                "curves",
                [],
            )
            if str(getattr(response, "filename", "") or "").strip()
        ]
        return {
            "source_cflibs_number_percent": {
                str(row.get("element", "")): safe_float(row.get("number_percent"), 0.0)
                for row in source_rows
            },
            "source_cflibs_mass_percent": {
                str(row.get("element", "")): safe_float(row.get("mass_percent"), 0.0)
                for row in source_rows
            },
            "nominal_number_percent": dict(
                getattr(self.master_app, "opc_nominal_percent", {}) or {}
            ),
            "population_multipliers": dict(self.factors),
            "round_trip": validation,
            "intensity_mode": _boltzmann_intensity_mode(self.master_app),
            "physical_response_files": response_files,
            "source_spectrum_files": source_files,
            "voigt_baseline_mode": str(
                getattr(self.master_app.options, "voigt_baseline_mode", "") or ""
            ),
            "voigt_fit_ranges": parse_voigt_fit_ranges(
                getattr(self.master_app.options, "voigt_fit_ranges", "{}")
            ),
            "analytical_lines": line_rows,
        }

    def save(self):
        try:
            calibration_rows = self._calibration_rows()
            validation = self._round_trip_validation(calibration_rows)
        except ValueError as exc:
            _showerror(self, "OPC", str(exc))
            return
        if not calibration_rows:
            _showinfo(self, "OPC", "No OPC calibration rows are available to save.")
            return
        if len(calibration_rows) < 2:
            _showerror(self, "OPC", "At least two valid analytical lines are required to save an OPC curve.")
            return
        if not validation["passed"]:
            details = ", ".join(
                f"{element}: expected {validation['expected_number_percent'][element]:.6g}%, "
                f"obtained {validation['observed_number_percent'].get(element, 0.0):.6g}%"
                for element in validation["expected_number_percent"]
            )
            _showerror(
                self,
                "OPC validation failed",
                "The candidate OPC does not reproduce its own calibration standard. "
                "No file was saved.\n\n" + details,
            )
            return
        audit = self._calibration_audit(calibration_rows, validation)
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
        calibration_id = opc_rows_calibration_id(calibration_rows)
        lines = [
            "# pyLIBS One Point Calibration",
            f"# date: {datetime.now().isoformat(timespec='seconds')}",
            f"# calibration_id: {calibration_id}",
            f"# source spectrum: {self._source_spectrum_filename() or 'N/A'}",
            f"# temperature_eV: {self.owner.last_kt:.8g}",
            f"# electron_density_e_cm3: {self.owner.last_ne:.8g}",
            "# composition_basis: number_percent",
            f"# nominal_input_basis: {getattr(self.master_app, 'opc_nominal_basis', OPC_NUMBER_PERCENT_BASIS)}",
            "# formula: line-wise Apply After response from fixed-temperature Boltzmann line shifted by log(nominal_number_percent / cflibs_number_percent)",
            "# round_trip_validation: PASS",
            f"# round_trip_max_error_percentage_points: {validation['maximum_error_percentage_points']:.12g}",
            f"# round_trip_tolerance_percentage_points: {validation['tolerance_percentage_points']:.12g}",
            "# nominal_number_percent: " + json.dumps(
                audit["nominal_number_percent"], ensure_ascii=True, sort_keys=True
            ),
            "# source_cflibs_number_percent: " + json.dumps(
                audit["source_cflibs_number_percent"], ensure_ascii=True, sort_keys=True
            ),
            "# source_cflibs_mass_percent: " + json.dumps(
                audit["source_cflibs_mass_percent"], ensure_ascii=True, sort_keys=True
            ),
            "# population_multipliers: " + json.dumps(
                audit["population_multipliers"], ensure_ascii=True, sort_keys=True
            ),
            "# round_trip_number_percent: " + json.dumps(
                validation["observed_number_percent"], ensure_ascii=True, sort_keys=True
            ),
            "# physical_response_files: " + json.dumps(
                audit["physical_response_files"], ensure_ascii=True
            ),
            "# source_spectrum_files: " + json.dumps(
                audit["source_spectrum_files"], ensure_ascii=True
            ),
            f"# intensity_mode: {audit['intensity_mode']}",
            f"# voigt_baseline_mode: {audit['voigt_baseline_mode']}",
            "# voigt_fit_ranges: " + json.dumps(
                audit["voigt_fit_ranges"], ensure_ascii=True, sort_keys=True,
                separators=(",", ":"),
            ),
            "# analytical_lines_json: " + json.dumps(
                audit["analytical_lines"], ensure_ascii=True, sort_keys=True,
                separators=(",", ":"),
            ),
            "# columns: NIST_wavelength_nm correction_factor element species",
        ]
        lines.extend(
            f"{wavelength:.12g} {factor:.12g} {element} {species}"
            for wavelength, factor, element, species in calibration_rows
        )
        try:
            Path(fn).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e:
            _showerror(self, "OPC", f"Could not save OPC calibration:\n{e}")
            return
        self.master_app.status(
            f"Line-wise Apply After OPC saved and validated: {fn} "
            f"[ID {calibration_id}; max round-trip error "
            f"{validation['maximum_error_percentage_points']:.3g} percentage points]"
        )
        _showinfo(
            self,
            "OPC",
            f"OPC calibration saved and internally validated:\n{fn}\n\n"
            f"Calibration ID: {calibration_id}\n"
            f"Maximum round-trip error: "
            f"{validation['maximum_error_percentage_points']:.3g} percentage points.\n"
            "Load it as an OPC correction; it must be applied after line integration.\n\n"
            "A one-point calibration remains valid only for samples with comparable matrix "
            "and plasma conditions; this internal check does not establish transferability "
            "to a substantially different sample.",
        )

    def close(self):
        try:
            if getattr(self.owner, "opc_window", None) is self:
                self.owner.opc_window = None
        except Exception:
            pass
        self.destroy()


def _cflibs_visible_groups(groups, fits):
    """Return only line groups admitted to the current CF-LIBS calculation."""
    return {
        key: groups[key]
        for key in fits
        if key in groups
    }


_CFLIBS_INTERCEPT_LABELS = {
    "fixed_temperature": "Common T (fixed slope)",
    "excel_free": "Diagnostic only (free slopes)",
}
_CFLIBS_IONIZATION_LABELS = {
    "saha": "Saha-Eggert (database)",
    "manual": "Manual neutral fractions",
}


def _cflibs_intercept_mode_is_quantitative(mode: str) -> bool:
    """Only the common-temperature model may produce CF-LIBS percentages."""
    return str(mode or "").strip().lower() == "fixed_temperature"


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
        self.geometry("1100x690")
        self.minsize(940, 600)
        top=ttk.Frame(self); top.pack(fill="x", padx=6, pady=5)
        ttk.Button(top, text="Compute CF-LIBS", command=self.compute).pack(side="left")
        self.opc_button = ttk.Button(top, text="OPC", command=self.show_opc, state="disabled")
        self.opc_button.pack(side="left", padx=4)
        ttk.Button(top, text="Show Report", command=self.show_report).pack(side="left", padx=4)
        ttk.Button(top, text="Quality Check", command=self.show_quality_report).pack(side="left", padx=4)
        ttk.Button(top, text="Robustness", command=self.show_robustness_report).pack(side="left", padx=4)
        ttk.Button(top, text="Use current T / Ne", command=self.use_current_inputs).pack(side="left", padx=4)
        ttk.Label(top, text="kT eV").pack(side="left", padx=(12,2))
        default_kt = safe_float(getattr(master, "session_temperature", 0.0), 0.0)
        self.kt_var = tk.StringVar(value=f"{default_kt:.6g}" if default_kt > 0.0 else "")
        ttk.Entry(top, textvariable=self.kt_var, width=9).pack(side="left")
        ttk.Label(top, text="Ne cm⁻³").pack(side="left", padx=(12,2))
        default_ne, default_ne_source = active_electron_density(master)
        self.ne_var = tk.StringVar(
            value=f"{default_ne:.6g}" if default_ne is not None else ""
        )
        ttk.Entry(top, textvariable=self.ne_var, width=12).pack(side="left")
        self.status_var = tk.StringVar(
            value=(
                f"Ready; Ne source: {default_ne_source}"
                if default_kt > 0.0 and default_ne is not None
                else "Compute Saha-Boltzmann T / confirm Ne first"
            )
        )
        ttk.Label(top, textvariable=self.status_var, width=34).pack(side="left", padx=12, fill="x", expand=True)
        settings = ttk.Frame(self)
        settings.pack(fill="x", padx=6, pady=(0, 5))
        ttk.Label(settings, text="Intercepts").pack(side="left")
        intercept_key = _option_key_from_label(
            _CFLIBS_INTERCEPT_LABELS,
            getattr(master.options, "cflibs_intercept_mode", "fixed_temperature"),
            "fixed_temperature",
        )
        self.intercept_mode_var = tk.StringVar(
            value=_CFLIBS_INTERCEPT_LABELS[intercept_key]
        )
        ttk.Combobox(
            settings,
            textvariable=self.intercept_mode_var,
            values=tuple(_CFLIBS_INTERCEPT_LABELS.values()),
            state="readonly",
            width=25,
        ).pack(side="left", padx=(3, 12))
        ttk.Label(settings, text="Ionization").pack(side="left")
        ionization_key = "saha"
        self.ionization_mode_var = tk.StringVar(
            value=_CFLIBS_IONIZATION_LABELS[ionization_key]
        )
        ttk.Label(
            settings,
            text=_CFLIBS_IONIZATION_LABELS[ionization_key],
        ).pack(side="left", padx=(3, 12))
        self.neutral_fractions_var = tk.StringVar(value="")
        add_context_help_button(
            settings,
            self,
            "CF-LIBS calculation",
            (
                "The default uses the selected common temperature and fixes its slope for every element, "
                "fitting only each intercept. Free slopes are a diagnostic comparison and do not produce percentages.\n\n"
                "Ionized/neutral populations are calculated automatically from temperature, electron density, "
                "ionization energy and database partition functions."
            ),
        ).pack(side="right")
        self.audit_var = tk.StringVar(
            value="Line audit available after calculation."
        )

        self.results_pane = ttk.Panedwindow(self, orient="vertical")
        self.results_pane.pack(fill="both", expand=True, padx=6, pady=(0, 5))
        plot_panel = ttk.Frame(self.results_pane)
        table_panel = ttk.Frame(self.results_pane)
        self.results_pane.add(plot_panel, weight=3)
        self.results_pane.add(table_panel, weight=2)
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(plot_panel, text="Matplotlib is not available.").pack(fill="both", expand=True, padx=10, pady=10)
            self.fig = self.ax = self.canvas = None
        else:
            self.fig = Figure(figsize=(9.5, 4.2), dpi=_figure_dpi(self))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_panel)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvas.mpl_connect("button_press_event", self.on_plot_click)
        self.last_rows = []
        self.last_skipped = 0
        self.last_kt = safe_float(self.kt_var.get(), 0.0)
        self.last_ne = safe_float(self.ne_var.get(), 0.0)
        self.last_response_used = False
        self.last_temperature_source = "default"
        self.last_ne_source = default_ne_source
        self.last_groups = {}
        self.last_fits = {}
        self.last_line_audit = {}
        self.last_robustness = {}
        self.last_quality = None
        self.last_unvalidated_rows = []
        self.report_window = None
        self.report_temp_dir = None
        self.opc_window = None
        self.plot_points = []
        cols=(
            "Element", "Lines", "Energy levels", "q at T",
            "q spread factor", "Line check", "Ionized / Neutral ratio",
            "Neutral fraction", "Number %", "Mass %", "LOO max %",
            "Replicate CV %", "T/Ne max %"
        )
        tree_frame = ttk.Frame(table_panel)
        self.tree=ttk.Treeview(tree_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c); self.tree.column(c, width=135, anchor="center")
        xscroll = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree.xview,
        )
        yscroll = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(
            xscrollcommand=xscroll.set,
            yscrollcommand=yscroll.set,
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.pack(fill="both", expand=True)
        self.after_idle(self._set_initial_results_split)
        if default_kt > 0.0 and default_ne is not None:
            self.after(100, self.compute)
        center_window(self, master)

    def _set_initial_results_split(self):
        pane = getattr(self, "results_pane", None)
        if pane is None:
            return
        try:
            available = pane.winfo_height()
            if available > 100:
                pane.sashpos(0, max(180, int(available * 0.62)))
        except tk.TclError:
            pass

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

    def sync_session_inputs(self):
        """Load the latest authoritative Saha/IRSAC temperature and Ne."""
        kt = safe_float(getattr(self.master_app, "session_temperature", 0.0), 0.0)
        ne = safe_float(getattr(self.master_app, "session_ne", 0.0), 0.0)
        changed = False
        if kt > 0.0:
            self.kt_var.set(f"{kt:.8g}")
            changed = True
        if ne > 0.0:
            self.ne_var.set(f"{ne:.8g}")
            changed = True
        if changed:
            temperature_source = str(
                getattr(self.master_app, "session_temperature_source", "")
                or "current analysis"
            )
            ne_source = str(
                getattr(self.master_app, "session_ne_source", "")
                or "not set"
            )
            self.status_var.set(
                f"Loaded current T ({temperature_source}); Ne source: {ne_source}"
            )
        return changed

    def use_current_inputs(self):
        if not self.sync_session_inputs():
            _showinfo(
                self,
                "CF-LIBS",
                "No current Saha-Boltzmann temperature is available. Compute the temperature first.",
            )
            return
        self.compute()

    def compute(self):
        self.tree.delete(*self.tree.get_children())
        self.last_rows = []
        self.last_quality = None
        self.last_robustness = {}
        self.last_unvalidated_rows = []
        self.master_app.last_cflibs_rows = []
        self.master_app.last_cflibs_quality = None
        self.master_app.last_cflibs_robustness = None
        self.audit_var.set("Line audit: computing...")
        try:
            self.master_app.libs_db.filename = self.master_app.options.libs_db_file
            self.master_app.libs_db.connect()
        except Exception as e:
            _showerror(self, "LIBS.db", str(e)); return
        irsac_mismatch = _irsac_configuration_mismatch(self.master_app)
        if irsac_mismatch:
            msg = (
                "IRSAC controls and applied factors are inconsistent: "
                + irsac_mismatch
                + ". Recalculate IRSAC before CF-LIBS."
            )
            self.status_var.set(msg)
            self.disable_opc()
            _showwarning(self, "CF-LIBS IRSAC state", msg)
            return
        quantification_blocker = _self_absorption_quantification_blocker(
            self.master_app
        )
        if quantification_blocker:
            msg = (
                "CF-LIBS stopped: "
                + quantification_blocker
                + ". A manual IRSAC override may be inspected graphically, "
                "but it cannot be used for final concentrations."
            )
            self.status_var.set(msg)
            self.disable_opc()
            _showwarning(self, "CF-LIBS self-absorption quality", msg)
            return
        worksheet_kt = _worksheet_irsac_temperature_ev(self.master_app)
        if worksheet_kt:
            kt = worksheet_kt
            self.kt_var.set(f"{kt:.8g}")
            self.master_app.session_temperature = kt
            self.master_app.session_temperature_source = (
                _worksheet_irsac_temperature_source(self.master_app)
            )
        else:
            kt = safe_float(self.kt_var.get(), 0.0)
        if kt <= 0:
            msg = (
                "No plasma temperature is available. Compute Saha-Boltzmann first, "
                "then use current T / Ne, or enter kT manually."
            )
            self.status_var.set(msg)
            self.disable_opc()
            _showinfo(self, "CF-LIBS temperature", msg)
            return
        kt_low = safe_float(getattr(self.master_app.options, "kt_low", 0.0), 0.0)
        kt_high = safe_float(getattr(self.master_app.options, "kt_high", 0.0), 0.0)
        if kt_high and kt_low > kt_high:
            kt_low, kt_high = kt_high, kt_low
        if (kt_low and kt <= kt_low) or (kt_high and kt >= kt_high):
            msg = (
                f"kT={kt:.4g} eV is outside the configured valid range "
                f"{kt_low:g}-{kt_high:g} eV. Use current T / Ne or change the "
                "range deliberately in Options."
            )
            self.status_var.set(msg)
            self.disable_opc()
            _showwarning(self, "CF-LIBS temperature", msg)
            return
        ne = safe_float(self.ne_var.get(), 0.0)
        if ne <= 0.0:
            msg = (
                "No electron density is active. Compute Saha-Boltzmann and "
                "confirm Ne, calculate it from H-alpha, or enter Ne deliberately."
            )
            self.status_var.set(msg)
            self.disable_opc()
            _showinfo(self, "CF-LIBS electron density", msg)
            return
        intercept_mode = _option_key_from_label(
            _CFLIBS_INTERCEPT_LABELS,
            self.intercept_mode_var.get(),
            "fixed_temperature",
        )
        ionization_mode = "saha"
        fraction_text = ""
        self.master_app.options.cflibs_intercept_mode = intercept_mode
        self.master_app.options.cflibs_ionization_mode = ionization_mode
        self.master_app.options.cflibs_neutral_fractions = fraction_text
        save_pylibs_ini(self.master_app.options)
        groups, skipped = libspp_boltzmann_groups_with_skips(
            self.master_app,
        )
        if intercept_mode == "excel_free":
            fits = libspp_fit_boltzmann_excel_intercepts(
                self.master_app, groups, kt
            )
        else:
            fits = libspp_fit_boltzmann_fixed_temperature(
                self.master_app, groups, kt
            )
        visible_groups = _cflibs_visible_groups(groups, fits)
        if not fits:
            msg = f"No valid Boltzmann data. Skipped {skipped} incomplete analytical line(s)."
            self.status_var.set(msg)
            self.last_groups = visible_groups
            self.last_fits = {}
            self.disable_opc()
            _showinfo(self, "CF-LIBS", msg)
            self._draw_boltzmann(visible_groups, fits, kt)
            return
        if not _cflibs_intercept_mode_is_quantitative(intercept_mode):
            self.last_groups = visible_groups
            self.last_fits = fits
            self.last_rows = []
            self.master_app.last_cflibs_rows = []
            self.last_skipped = skipped
            self.last_kt = kt
            self.last_ne = ne
            self.disable_opc()
            self._draw_boltzmann(visible_groups, fits, kt)
            msg = (
                "Diagnostic free-slope plot computed. Percentages are intentionally "
                "disabled: select Common T (fixed slope) for quantitative CF-LIBS."
            )
            self.status_var.set(msg)
            self.master_app.status(msg)
            return
        rows = libspp_saha_cflibs(
            self.master_app,
            fits,
            kt,
            ne,
            ionization_mode=ionization_mode,
            neutral_fractions={},
        )
        robustness = libspp_cflibs_robustness(
            self.master_app,
            groups,
            fits,
            rows,
            kt,
            ne,
            ionization_mode=ionization_mode,
            neutral_fractions={},
        )
        line_audit = libspp_cflibs_line_audit(
            self.master_app,
            fits,
            kt,
        )
        for row in rows:
            audit = line_audit.get(row["element"], {})
            stability = (robustness.get("elements") or {}).get(
                row["element"],
                {},
            )
            row["line_audit"] = audit
            row["q_display"] = audit.get("q_display", "")
            row["q_span"] = audit.get("q_span", math.nan)
            row["q_population_factor"] = audit.get(
                "population_factor",
                math.nan,
            )
            row["line_consistency"] = audit.get(
                "status",
                "Insufficient",
            )
            row["loo_max_relative_change"] = stability.get(
                "loo_max_relative_change",
                math.inf,
            )
            row["replicate_composition_cv"] = stability.get(
                "replicate_max_cv",
                math.inf,
            )
            row["parameter_max_relative_change"] = stability.get(
                "parameter_max_relative_change",
                math.inf,
            )
        quality = cflibs_quantitation_quality(
            self.master_app,
            fits,
            rows,
            line_audit,
            kt,
            ne,
            robustness,
        )
        self.last_quality = quality
        self.last_unvalidated_rows = rows
        quantitative_approved = bool(validated_cflibs_rows(rows, quality))
        self.last_groups = visible_groups
        self.last_fits = fits
        self.last_line_audit = line_audit
        self.last_robustness = robustness
        self.master_app.last_cflibs_robustness = robustness
        # Always publish the result produced by the Palleschi equations. The
        # quality gate is advisory: it reports PASS/CHECK, but it must never
        # hide percentages or block the original OPC workflow.
        published_rows = list(rows)
        self.master_app.last_cflibs_rows = published_rows
        self.last_rows = published_rows
        self.last_skipped = skipped
        self.last_kt = kt
        self.last_ne = ne
        self.last_response_used = _apply_after_response_enabled(self.master_app)
        self.last_temperature_source = self._temperature_source(kt)
        self.last_ne_source = self._ne_source(ne)
        self.master_app.session_temperature = kt
        self.master_app.session_temperature_source = self.last_temperature_source
        set_session_electron_density(
            self.master_app,
            ne,
            self.last_ne_source,
        )
        for r in rows:
            number_display = self._fmt3(r["number_percent"])
            mass_display = self._fmt3(r["mass_percent"])
            self.tree.insert("", "end", values=(
                r["element"],
                r.get("nlines", 0),
                r.get("distinct_levels", 0),
                r.get("q_display", ""),
                self._fmt3(r.get("q_population_factor")),
                r.get("line_consistency", ""),
                self._fmt3(r["ionized_neutral_ratio"]),
                self._fmt3(r["neutral_ratio"]),
                number_display,
                mass_display,
                self._fmt_percent(r.get("loo_max_relative_change")),
                self._fmt_percent(r.get("replicate_composition_cv")),
                self._fmt_percent(r.get("parameter_max_relative_change")),
            ))
        audit_parts = []
        audit_warning = False
        for element, audit in sorted(line_audit.items()):
            excluded = audit.get("excluded_lines", [])
            omitted = audit.get("omitted_lines", [])
            status = audit.get("status", "Insufficient")
            factor = safe_float(
                audit.get("population_factor"),
                math.inf,
            )
            detail = (
                f"{element}: {audit.get('active_count', 0)} used"
                f", {audit.get('clean_feature_count', 0)} clean"
                f", q spread x{factor:.3g}"
                f", branching x{safe_float(audit.get('branching_factor'), 1.0):.3g}"
                f", {status}"
            )
            unresolved = audit.get("unresolved_interferences", []) or []
            if unresolved:
                blends = []
                for item in unresolved:
                    candidates = ", ".join(
                        candidate.get("label", "")
                        for candidate in item.get("candidates", [])
                    )
                    blends.append(f"{item.get('line', '')} <- {candidates}")
                detail += "; unresolved " + " | ".join(blends)
            if excluded:
                detail += "; excluded " + ", ".join(excluded)
            if omitted:
                detail += "; omitted " + ", ".join(omitted)
            replicate_rejected = audit.get("replicate_rejected_lines", []) or []
            if replicate_rejected:
                details = []
                for item in replicate_rejected:
                    cv = safe_float(item.get("cv"), math.nan)
                    cv_text = f"CV={cv:.1%}" if math.isfinite(cv) else "CV=N/A"
                    details.append(
                        f"{item.get('line', '')} ({cv_text}, "
                        f"{item.get('valid', 0)}/{item.get('total', 0)} valid)"
                    )
                detail += "; replicate-rejected " + ", ".join(details)
            audit_parts.append(detail)
            audit_warning = audit_warning or status != "Stable" or bool(
                excluded or omitted
            )
        quality_prefix = (
            "Quantitative quality PASS. "
            if quantitative_approved
            else (
                f"Quantitative quality CHECK: {len(quality.get('blockers', []) or [])} "
                "condition(s) failed; percentages are shown as diagnostic. "
            )
        )
        self.audit_var.set(
            quality_prefix
            + (
                f"Robustness: LOO max "
                f"{self._fmt_percent(robustness.get('line_loo_max_relative_change'))}, "
                f"replicate CV max "
                f"{self._fmt_percent(robustness.get('replicate_max_composition_cv'))}, "
                f"T/Ne max "
                f"{self._fmt_percent(robustness.get('parameter_max_relative_change'))}. "
            )
            + (
                "Line audit: " + " | ".join(audit_parts)
                if audit_parts
                else "Line audit: no valid analytical lines."
            )
        )
        self._draw_boltzmann(visible_groups, fits, kt)
        if published_rows:
            self.enable_opc()
        else:
            self.disable_opc()
        if _loaded_response_is_opc(self.master_app):
            opc_name = Path(
                str(getattr(self.master_app, "active_opc_path", "") or "")
            ).name or "OPC"
            opc_id = str(
                getattr(self.master_app, "active_opc_id", "") or "unknown"
            )
            response_text = (
                f"OPC {opc_name} [ID {opc_id}] applied once after integration"
            )
        else:
            response_text = (
                "Apply After response correction used"
                if _apply_after_response_enabled(self.master_app)
                else "no Apply After response correction"
            )
        model_text = (
            f"{_CFLIBS_INTERCEPT_LABELS[intercept_mode]}; "
            f"{_CFLIBS_IONIZATION_LABELS[ionization_mode]}"
        )
        self.status_var.set(
            f"Quality {quality['status']}; kT={kt:.4g} eV ({self.last_temperature_source}), "
            f"Ne={ne:.3e} e/cm3 ({self.last_ne_source}), "
            f"elements={len(rows)}, skipped={skipped}; {model_text}; {response_text}"
            + ("; CHECK LINE AUDIT" if audit_warning else "")
        )
        self.master_app.status(f"CF-LIBS: kT={kt:.4g} eV, Ne={ne:.3e} e/cm3, {len(rows)} element(s), skipped {skipped}")

    def show_quality_report(self):
        quality = self.last_quality or getattr(
            self.master_app,
            "last_cflibs_quality",
            None,
        )
        _showinfo(
            self,
            "CF-LIBS quantitative quality",
            format_cflibs_quality_report(quality),
        )

    def show_robustness_report(self):
        robustness = self.last_robustness or getattr(
            self.master_app,
            "last_cflibs_robustness",
            None,
        )
        _showinfo(
            self,
            "CF-LIBS multielement robustness",
            format_cflibs_robustness_report(robustness),
        )

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

    def _fmt_percent(self, value):
        number = safe_float(value, math.inf)
        return f"{100.0 * number:.2f}" if math.isfinite(number) else "N/A"

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
        intercept_mode = _option_key_from_label(
            _CFLIBS_INTERCEPT_LABELS,
            self.intercept_mode_var.get(),
            "fixed_temperature",
        )
        ionization_mode = "saha"
        source = self._temperature_source(kt)
        self.ax.set_title(
            "CF-LIBS Boltzmann plots\n"
            f"kT={kt:.6g} eV ({source}); "
            f"{_CFLIBS_INTERCEPT_LABELS[intercept_mode]}; "
            f"{_CFLIBS_IONIZATION_LABELS[ionization_mode]}"
        )
        self.ax.set_xlabel("Upper energy Ek (eV)")
        self.ax.set_ylabel(_boltzmann_formula(self.master_app))
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
        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            self.ax.legend(handles, labels, loc="best", fontsize=8)
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
        "wavelen", "specie", "ion", "asswavelen", "inte", "wg", "wl", "ei",
        "ek", "aki", "gk", "gi", "fitwavelen", "templint", "error_inte", "acc"
    )

    def __init__(self, master: "MainWindow"):
        super().__init__(master)
        self.master_app = master
        self._hide_template_pending = False
        self.title("Selected analytical lines")
        try:
            self.transient(master)
        except Exception:
            pass
        try:
            self.wm_attributes("-toolwindow", True)
        except Exception:
            pass
        try:
            self.wm_attributes("-type", "dialog")
        except Exception:
            pass
        self.geometry(legacy_geometry_to_tk(getattr(master.options, "template_geometry", ""), "1280x560"))
        self.minsize(1180, 420)
        self.configure(bg=RETRO_BG)
        self.protocol("WM_DELETE_WINDOW", master.close_template_window)
        self.bind("<Unmap>", self._on_unmap, add="+")
        self._build()

    def _on_unmap(self, event=None):
        if self._hide_template_pending:
            return
        try:
            if str(self.state()) != "iconic":
                return
        except Exception:
            return
        self._hide_template_window()

    def _hide_template_window(self):
        if self._hide_template_pending:
            return
        self._hide_template_pending = True
        try:
            try:
                self.master_app.template_window_geometry = self.geometry()
            except Exception:
                pass
            try:
                if self.winfo_exists():
                    self.withdraw()
            except Exception:
                pass
        finally:
            self._hide_template_pending = False

    def hide_template(self):
        self._hide_template_window()

    def _build(self):
        panel = ttk.Frame(self)
        panel.pack(side="top", fill="x", padx=2, pady=2)
        ttk.Button(panel, text="Import lines...", command=self.load_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Save lines", command=self.save_template).pack(side="left", padx=2)
        ttk.Button(panel, text="Clear fit", command=self.clear_fit).pack(side="left", padx=2)
        ttk.Button(panel, text="Delete row", command=self.delete_selected_row).pack(side="left", padx=2)
        ttk.Button(panel, text="Saha-Boltzmann", command=self.master_app.show_saha_boltzmann).pack(side="left", padx=2)
        more_button = ttk.Menubutton(panel, text="More")
        more_menu = tk.Menu(more_button, tearoff=0)
        more_menu.add_command(label="Line summary", command=self.template_info)
        more_menu.add_separator()
        more_menu.add_command(label="Clear selected lines", command=self.clear_template)
        more_menu.add_command(label="Close line list", command=self.close_template)
        more_menu.add_command(label="Delete saved list", command=self.delete_template)
        more_button.configure(menu=more_menu)
        more_button.pack(side="left", padx=2)
        ttk.Frame(panel).pack(side="left", fill="x", expand=True)
        ttk.Button(panel, text="Hide", command=self.hide_template).pack(side="right", padx=2)
        library_panel = ttk.LabelFrame(self, text="Analytical-line library")
        library_panel.pack(side="top", fill="x", padx=3, pady=(1, 3))
        library_button = ttk.Menubutton(library_panel, text="Manage library")
        library_menu = tk.Menu(library_button, tearoff=0)
        library_menu.add_command(
            label="Reload main library",
            command=self.master_app.reload_analytical_line_library,
        )
        library_menu.add_command(
            label="Add secondary list...",
            command=self.master_app.add_secondary_analytical_line_list,
        )
        library_menu.add_command(
            label="Replace main library...",
            command=self.master_app.replace_analytical_line_library,
        )
        library_menu.add_command(
            label="Save current lines as main",
            command=self.master_app.save_current_lines_to_analytical_library,
        )
        library_menu.add_separator()
        library_menu.add_command(
            label="Restore included library",
            command=self.master_app.restore_default_analytical_line_library,
        )
        library_button.configure(menu=library_menu)
        library_button.pack(side="left", padx=2, pady=2)
        self.library_status_var = tk.StringVar()
        ttk.Label(
            library_panel,
            textvariable=self.library_status_var,
        ).pack(side="right", padx=6)
        add_context_help_button(
            library_panel,
            self,
            "Selected analytical lines",
            (
                "This table is the current analytical workspace. Each row stores the observed peak, "
                "atomic assignment and Voigt fit. The main analytical-line library is loaded automatically "
                "for every new analysis."
            ),
        ).pack(side="right", padx=3, pady=2)

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
        library_lines = len(
            getattr(self.master_app, "analytical_line_library", []) or []
        )
        try:
            self.library_status_var.set(f"{library_lines} persistent lines")
        except Exception:
            pass
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
            title="Import lines for the current analysis",
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
            title="Save selected-line list",
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
        _showinfo(self, "Selected-Line Summary", msg)

    def clear_template(self):
        if _askyesno(self, "Analytical-Line List", "This will clear the current analytical-line list. Continue?"):
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
        if _askyesno(self, "Analytical-Line List", "This will close the current analytical-line list. Continue?"):
            self.master_app.template_lines.clear()
            self.master_app.notify_template_changed(redraw=True)
            self.on_window_close()

    def on_window_close(self):
        self.master_app.close_template_window()

    def delete_template(self):
        fn = filedialog.askopenfilename(
            title="Delete Analytical-Line List",
            initialdir=remembered_initial_dir(self.master_app.options),
            filetypes=[("Templates", "*.db *.DB *.csv"), ("All", "*.*")]
        )
        if fn:
            remember_working_dir(self.master_app.options, fn)
        if fn and _askyesno(self, "Delete Analytical-Line List", f"Delete this analytical-line list?\n{fn}"):
            try:
                Path(fn).unlink()
                _showinfo(self, "Delete Analytical-Line List", "Analytical-line list deleted.")
            except Exception:
                _showerror(self, "Delete Analytical-Line List", "The analytical-line list could not be deleted.")

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
        self.title("Auto Fit - selected observed peaks" if self.automatic else "Single Fit" if self.single else "Manual Fit")
        self.geometry(legacy_geometry_to_tk(getattr(master.options, "fit_geometry", ""), "840x540"))
        self.minsize(1000, 520)
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
        self.last_fit_result = None
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
        if self.automatic and not self.master_app.template_lines:
            self.msg_var.set(
                "No peaks selected. Use 'Find visible peaks' or 'Add peak from graph'; no external line-list file is required."
            )

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=4, pady=3)
        if self.automatic:
            ttk.Button(top, text="1. Find visible peaks", command=self.find_visible_peaks).pack(side="left", padx=2)
            ttk.Button(top, text="Add peak from graph", command=self.select_peak_from_graph).pack(side="left", padx=2)
            ttk.Button(top, text="2. Fit selected peaks (Voigt)", command=self.run_fit).pack(side="left", padx=8)
        else:
            ttk.Button(
                top,
                text="Fit Gaussian",
                command=self.run_gaussian_fit,
            ).pack(side="left", padx=2)
            ttk.Button(top, text="Fit Voigt", command=self.run_fit).pack(side="left", padx=2)
        ttk.Button(top, text="Stop", command=self.stop_fit).pack(side="left", padx=2)
        ttk.Button(top, text="Close", command=self.close_window).pack(side="left", padx=2)
        if not self.automatic and not self.single:
            ttk.Button(top, text="Next Region", command=self.next_region).pack(side="left", padx=8)
            ttk.Button(top, text="Refresh", command=self.refresh_region).pack(side="left", padx=2)
            ttk.Button(top, text="Previous Region", command=self.previous_region).pack(side="left", padx=2)
        if not self.automatic:
            ttk.Button(top, text="Show Residuals", command=self.show_residuals).pack(side="left", padx=8)
        add_context_help_button(
            top,
            self,
            "Gaussian / Voigt peak fitting",
            (
                "Automatic search selects measured local maxima in the visible wavelength interval. "
                "A selected line is an observed peak position used by the fitter; atomic identification "
                "is a later step. Add a missed peak directly from the graph.\n\n"
                "Gaussian uses b0+b1*x+A*exp(-((x-x0)/sigma)^2) and stores "
                "the analytical area A*sigma*sqrt(pi). Voigt stores the fitted Voigt area. "
                "Both profiles use the same selected lines and the same manual ROI."
            ),
        ).pack(side="right", padx=2)
        roi_bar = ttk.Frame(self)
        roi_bar.pack(fill="x", padx=4, pady=(0, 2))
        ttk.Label(roi_bar, text="Area ROI:").pack(side="left", padx=(3, 5))
        ttk.Button(
            roi_bar,
            text="Select ROI limits",
            command=self.select_fit_range_from_graph,
        ).pack(side="left", padx=2)
        ttk.Button(
            roi_bar,
            text="Save current zoom",
            command=self.remember_visible_fit_range,
        ).pack(side="left", padx=2)
        ttk.Button(
            roi_bar,
            text="Reset ROI",
            command=self.reset_visible_fit_range,
        ).pack(side="left", padx=2)
        self.msg_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.msg_var, wraplength=810, justify="left").pack(fill="x", padx=7, pady=2)

        self.progress = ttk.Progressbar(self, maximum=100)
        self.progress.pack(fill="x", padx=5, pady=2)

        grid = ttk.LabelFrame(self, text="Selected lines and fit parameters")
        grid.pack(fill="x", padx=5, pady=5)

        headers = ["Line", "Wavelength", "Fix", "Gaussian", "Fix", "Lorentzian (Voigt)", "Fix"]
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
            columns=(
                "line",
                "source",
                "center",
                "intensity",
                "lorentzian",
                "gaussian",
                "integral",
                "replicate_cv",
                "status",
            ),
            show="headings",
            height=7,
        )
        for c, label, w in [
            ("line", "NIST transition", 135),
            ("source", "Detector window", 120),
            ("center", "Fit Center Wavelength", 145),
            ("intensity", "Fit Intensity", 110),
            ("lorentzian", "Fit Lorentzian Width", 135),
            ("gaussian", "Fit Gaussian Width", 130),
            ("integral", "Fit Integral", 110),
            ("replicate_cv", "Replicate area CV", 115),
            ("status", "Quality", 260),
        ]:
            self.results.heading(c, text=label)
            self.results.column(
                c,
                width=w,
                anchor="w" if c == "status" else "center",
            )
        self.results.pack(fill="both", expand=True)
        results_frame.pack(fill="both", expand=True, padx=5, pady=4)

    def find_visible_peaks(self):
        if not self.master_app.spectra:
            _showinfo(self, "Auto Fit", "Load a spectrum first.")
            return
        before = len(self.master_app.template_lines)
        result = self.master_app.find_peaks_basic(adaptive=True)
        self.prepare_initial_region(preserve_user_values=False)
        after = len(self.master_app.template_lines)
        if result and after > before:
            self.msg_var.set(
                f"{after - before} observed peak(s) added. Review the markers, then press 'Fit selected peaks (Voigt)'."
            )
        elif after:
            self.msg_var.set(
                "No new peak was added; existing selected peaks are ready. "
                "Add a missed peak from the graph if needed."
            )
        else:
            self.msg_var.set(
                "No measured maximum passed the automatic noise threshold in the visible interval. "
                "Zoom in or use 'Add peak from graph'."
            )

    def select_peak_from_graph(self):
        if not self.master_app.spectra:
            _showinfo(self, "Auto Fit", "Load a spectrum first.")
            return
        self.master_app.fit_roi_capture_window = None
        self.master_app.fit_peak_capture_window = self
        self.msg_var.set("Click the desired observed peak on the main graph. The nearest measured sample will be selected.")
        self.master_app.status("Auto Fit: click an observed peak on the graph")

    def add_peak_from_graph(self, wavelength):
        self.master_app.fit_peak_capture_window = None
        self.master_app.add_template_peak_at(float(wavelength), intensity=None, refresh=True)
        self.prepare_initial_region(preserve_user_values=False)
        self.msg_var.set(
            f"Peak near {float(wavelength):.6g} selected. Add other peaks or press 'Fit selected peaks (Voigt)'."
        )

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
        self.update_idletasks()

    def close_window(self):
        self.manual_fit_stop = True
        self.fit_stop_requested = True
        if getattr(self.master_app, "fit_peak_capture_window", None) is self:
            self.master_app.fit_peak_capture_window = None
        if getattr(self.master_app, "fit_roi_capture_window", None) is self:
            self.master_app.fit_roi_capture_window = None
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
        lines = list(
            lines
            if lines is not None
            else self._eligible_template_lines()[:10]
        )
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

    def _eligible_template_lines(self):
        lines = [
            line
            for line in getattr(self.master_app, "template_lines", []) or []
            if template_line_is_acquired(self.master_app, line)
        ]
        if not self.automatic:
            return lines
        selected_elements = _selected_analysis_elements(self.master_app)
        if selected_elements is None:
            return lines
        return [
            line
            for line in lines
            if str(getattr(line, "specie", "") or "").strip().capitalize()
            in selected_elements
        ]

    def _sorted_template_lines(self):
        return sorted(
            [
                line
                for line in self._eligible_template_lines()
                if getattr(line, "wavelen", 0.0)
            ],
            key=lambda t: t.wavelen,
        )

    def _manual_template_lines_source(self):
        visible = self._visible_template_lines()
        return visible if visible else self._sorted_template_lines()

    def _get_template_rows_sorted_by_wavelength(self):
        rows = []
        all_lines = list(getattr(self.master_app, "template_lines", []) or [])
        for line in self._eligible_template_lines():
            try:
                wavelength = float(getattr(line, "wavelen", 0.0) or 0.0)
            except Exception:
                continue
            if wavelength:
                rows.append((all_lines.index(line), wavelength, line))
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

    def _persist_fit_ranges(self, ranges):
        self.master_app.options.voigt_fit_ranges = json.dumps(
            ranges,
            sort_keys=True,
            separators=(",", ":"),
        )
        provenance = parse_voigt_fit_range_sources(
            getattr(
                self.master_app.options,
                "voigt_fit_range_sources",
                "{}",
            )
        )
        provenance = {
            key: signature
            for key, signature in provenance.items()
            if key in ranges
        }
        self.master_app.options.voigt_fit_range_sources = json.dumps(
            provenance,
            sort_keys=True,
            separators=(",", ":"),
        )
        save_pylibs_ini(self.master_app.options)

    def _bind_fit_ranges_to_current_spectrum(self, lines):
        signature = measurement_spectrum_signature(self.master_app)
        if not signature:
            return
        provenance = parse_voigt_fit_range_sources(
            getattr(
                self.master_app.options,
                "voigt_fit_range_sources",
                "{}",
            )
        )
        for line in list(lines or []):
            provenance[_voigt_fit_range_key(line)] = signature
        self.master_app.options.voigt_fit_range_sources = json.dumps(
            provenance,
            sort_keys=True,
            separators=(",", ":"),
        )
        save_pylibs_ini(self.master_app.options)

    def select_fit_range_from_graph(self):
        lines = self._visible_template_lines() or list(self.displayed_lines or [])
        if not lines:
            self.msg_var.set(
                "No analytical line is visible. Open the line region first."
            )
            return
        self._pending_fit_roi_points = []
        self.master_app.fit_peak_capture_window = None
        self.master_app.fit_roi_capture_window = self
        message = (
            "ROI: click the baseline on the left of the peak, then the "
            "baseline on the right."
        )
        self.msg_var.set(message)
        self.master_app.status(message)

    def add_fit_range_point_from_graph(self, wavelength):
        points = list(getattr(self, "_pending_fit_roi_points", []) or [])
        points.append(float(wavelength))
        self._pending_fit_roi_points = points
        if len(points) < 2:
            message = "Left ROI limit selected. Now click the right baseline."
            self.msg_var.set(message)
            self.master_app.status(message)
            return

        self.master_app.fit_roi_capture_window = None
        self._pending_fit_roi_points = []
        lo, hi = sorted(points[-2:])
        if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
            self.msg_var.set("The selected ROI limits are not valid.")
            return
        lines = self._visible_template_lines() or list(self.displayed_lines or [])
        if not lines:
            self.msg_var.set("No analytical line is associated with this ROI.")
            return
        if not all(lo < safe_float(line.wavelen, lo) < hi for line in lines):
            self.msg_var.set(
                "The ROI must contain every analytical line in the current group."
            )
            return

        ranges = parse_voigt_fit_ranges(
            getattr(self.master_app.options, "voigt_fit_ranges", "{}")
        )
        for line in lines:
            ranges[_voigt_fit_range_key(line)] = [lo, hi]
        self._persist_fit_ranges(ranges)
        self._bind_fit_ranges_to_current_spectrum(lines)
        session_keys = set(
            getattr(
                self.master_app,
                "session_voigt_fit_range_keys",
                set(),
            )
            or set()
        )
        session_keys.update(_voigt_fit_range_key(line) for line in lines)
        self.master_app.session_voigt_fit_range_keys = session_keys
        self.master_app.clear_fit_artists()
        self.master_app.ax.set_xlim(lo, hi)
        self.master_app.full_y_main_visible_x()
        self.master_app.canvas.draw_idle()
        self.master_app._update_xscroll()
        message = (
            f"Origin-compatible ROI saved for {len(lines)} line(s): "
            f"{lo:.6f} - {hi:.6f} nm. Run the Voigt fit."
        )
        self.msg_var.set(message)
        self.master_app.status(message)

    def remember_visible_fit_range(self):
        lines = self._visible_template_lines() or list(self.displayed_lines or [])
        if not lines or not getattr(self.master_app, "ax", None):
            self.msg_var.set("No analytical line is visible in the current graph interval.")
            return
        lo, hi = sorted(self.master_app.ax.get_xlim())
        if not math.isfinite(lo) or not math.isfinite(hi) or lo == hi:
            self.msg_var.set("The current graph interval is not valid.")
            return
        ranges = parse_voigt_fit_ranges(
            getattr(self.master_app.options, "voigt_fit_ranges", "{}")
        )
        for line in lines:
            ranges[_voigt_fit_range_key(line)] = [float(lo), float(hi)]
        self._persist_fit_ranges(ranges)
        self._bind_fit_ranges_to_current_spectrum(lines)
        session_keys = set(
            getattr(
                self.master_app,
                "session_voigt_fit_range_keys",
                set(),
            )
            or set()
        )
        session_keys.update(_voigt_fit_range_key(line) for line in lines)
        self.master_app.session_voigt_fit_range_keys = session_keys
        message = (
            f"Voigt ROI saved for {len(lines)} line(s): "
            f"{lo:.6f} - {hi:.6f} nm. It will be reused only for these same spectral data."
        )
        self.msg_var.set(message)
        self.master_app.status(message)

    def reset_visible_fit_range(self):
        lines = self._visible_template_lines() or list(self.displayed_lines or [])
        if not lines:
            self.msg_var.set("No analytical line is visible in the current graph interval.")
            return
        ranges = parse_voigt_fit_ranges(
            getattr(self.master_app.options, "voigt_fit_ranges", "{}")
        )
        removed = 0
        for line in lines:
            if ranges.pop(_voigt_fit_range_key(line), None) is not None:
                removed += 1
        session_keys = set(
            getattr(
                self.master_app,
                "session_voigt_fit_range_keys",
                set(),
            )
            or set()
        )
        for line in lines:
            session_keys.discard(_voigt_fit_range_key(line))
        self.master_app.session_voigt_fit_range_keys = session_keys
        self._persist_fit_ranges(ranges)
        message = f"Saved Voigt ROI removed for {removed} line(s)."
        self.msg_var.set(message)
        self.master_app.status(message)

    def _display_manual_group(self, group, preserve_user_values=False):
        if not group or not getattr(self.master_app, "ax", None):
            return
        delta = self._manual_delta_min()
        saved_range = _session_voigt_saved_fit_range(
            self.master_app,
            group,
        )
        if saved_range:
            xmin, xmax = saved_range
        else:
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
        min_points = self._minimum_fit_points(group, line_overrides=self._line_overrides_from_editor(group, apply_to_template=False))
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
            else:
                self.load_from_template([], preserve_user_values=False)
                self.msg_var.set(
                    "No peaks selected. Find visible peaks or add them from the graph; loading a line-list file is optional."
                )
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
            self.msg_var.set("No selected analytical lines are visible in the current spectrum window")

    def prepare_single_region(self, preserve_user_values=False):
        self.manual_fit_lines = self._visible_template_lines()
        self.manual_fit_index = 0
        self.load_from_template(self.manual_fit_lines, preserve_user_values=preserve_user_values)
        if self.manual_fit_lines:
            lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
            self.msg_var.set(f"Single Fit: {len(self.manual_fit_lines)} visible line(s) in {lo:.4f} - {hi:.4f}")
        else:
            self.msg_var.set("Single Fit: no selected analytical lines are visible in the current window")
            self.after(100, lambda: _showinfo(self, "Single Fit", "No selected analytical lines are visible in the current spectrum window."))

    def _current_group(self):
        if not self.manual_fit_lines:
            self.manual_fit_lines = self._manual_template_lines_source() if self.automatic else self._visible_template_lines()
        return self._group_from_index(self.manual_fit_index)

    def _current_fit_point_count(self):
        if not self.master_app.spectra or not getattr(self.master_app, "ax", None):
            return 0
        lo, hi = sorted(self.master_app.ax.get_xlim())
        lines = list(getattr(self, "displayed_lines", []) or []) or self._visible_template_lines()
        sp = select_spectrum_for_wavelengths(
            self.master_app,
            [getattr(line, "wavelen", 0.0) for line in lines],
        )
        if sp is None:
            return 0
        return sum(1 for x in sp.x if lo <= x <= hi)

    def _visible_template_lines(self):
        if not getattr(self.master_app, "ax", None):
            return []
        lo, hi = sorted(self.master_app.ax.get_xlim())
        return sorted(
            [
                line
                for line in self._eligible_template_lines()
                if lo <= getattr(line, "wavelen", 0.0) <= hi
            ],
            key=lambda t: t.wavelen,
        )

    def _minimum_fit_points(self, group, line_overrides=None):
        return _voigt_free_parameter_count(group, options=getattr(self.master_app, "options", None), line_overrides=line_overrides)

    def _independent_window_conflict(self, lines):
        if not getattr(self.master_app, "independent_window_mode", False):
            return False
        targets = [
            safe_float(getattr(line, "wavelen", 0.0), 0.0)
            for line in list(lines or [])
            if safe_float(getattr(line, "wavelen", 0.0), 0.0) > 0.0
        ]
        return bool(targets) and select_spectrum_for_wavelengths(
            self.master_app,
            targets,
        ) is None

    def _data_x_limits(self):
        if not self.master_app.spectra:
            return None
        lines = list(getattr(self, "displayed_lines", []) or []) or self._visible_template_lines()
        spectrum = select_spectrum_for_wavelengths(
            self.master_app,
            [getattr(line, "wavelen", 0.0) for line in lines],
        )
        xs = list(getattr(spectrum, "x", []) or []) if spectrum is not None else []
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

    def _expanded_window_for_min_points(self, min_points):
        data_limits = self._data_x_limits()
        if not data_limits or not getattr(self.master_app, "ax", None):
            return None
        lines = list(getattr(self, "displayed_lines", []) or []) or self._visible_template_lines()
        spectrum = select_spectrum_for_wavelengths(
            self.master_app,
            [getattr(line, "wavelen", 0.0) for line in lines],
        )
        if spectrum is None:
            return None
        xs = sorted(float(x) for x in list(getattr(spectrum, "x", []) or []) if x is not None)
        if len(xs) < min_points or not xs:
            return None
        lo, hi = sorted(self.master_app.ax.get_xlim())
        current_count = bisect_right(xs, hi) - bisect_left(xs, lo)
        if current_count >= min_points:
            return (lo, hi)
        current_center = (lo + hi) / 2.0
        best_limits = None
        best_key = None
        last_start = len(xs) - min_points
        for start in range(last_start + 1):
            end = start + min_points - 1
            new_lo = min(lo, xs[start])
            new_hi = max(hi, xs[end])
            left_ext = lo - new_lo
            right_ext = new_hi - hi
            key = (
                new_hi - new_lo,
                abs(((new_lo + new_hi) / 2.0) - current_center),
                abs(left_ext - right_ext),
                left_ext + right_ext,
            )
            if best_key is None or key < best_key:
                best_key = key
                best_limits = (new_lo, new_hi)
        return best_limits

    def _expand_manual_window_to_points(self, group, min_points, max_retries=20):
        point_count = self._current_fit_point_count()
        if point_count >= min_points:
            return point_count, False, 0
        new_limits = self._expanded_window_for_min_points(min_points)
        if not new_limits:
            return point_count, False, 0
        old_limits = tuple(sorted(self.master_app.ax.get_xlim())) if getattr(self.master_app, "ax", None) else None
        new_lo, new_hi = new_limits
        if old_limits == (new_lo, new_hi):
            return point_count, False, 0
        self.master_app.clear_fit_artists()
        self.master_app.ax.set_xlim(new_lo, new_hi)
        self.master_app.full_y_main_visible_x()
        self.master_app.canvas.draw_idle()
        self.master_app._update_xscroll()
        point_count = self._current_fit_point_count()
        return point_count, True, 1

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

    def _active_spectrum_snapshot(self, lines=None):
        replicate_source = None
        targets = [
            safe_float(getattr(line, "wavelen", 0.0), 0.0)
            for line in list(lines or [])
            if safe_float(getattr(line, "wavelen", 0.0), 0.0) > 0.0
        ]
        sp = select_spectrum_for_wavelengths(self.master_app, targets)
        if sp is None:
            return None
        response_corrected = bool(getattr(sp, "response_corrected", False))
        sources = tuple(getattr(sp, "source_windows", ()) or ())
        if len(sources) == 1:
            replicate_source = sources[0]
        if targets and len(sources) > 1:
            candidates = []
            target_center = 0.5 * (min(targets) + max(targets))
            for source in sources:
                source_x = tuple(getattr(source, "x", ()) or ())
                if not source_x:
                    continue
                source_low, source_high = min(source_x), max(source_x)
                if source_low <= min(targets) and source_high >= max(targets):
                    margin = min(
                        min(targets) - source_low,
                        source_high - max(targets),
                    )
                    tag_text = extract_window_tag(
                        getattr(source, "name", "")
                        or getattr(source, "filename", "")
                    )
                    try:
                        tag_distance = abs(float(tag_text) - target_center)
                        has_numeric_tag = True
                    except (TypeError, ValueError):
                        tag_distance = math.inf
                        has_numeric_tag = False
                    candidates.append(
                        (
                            has_numeric_tag,
                            -tag_distance,
                            margin,
                            source,
                        )
                    )
            if candidates:
                source = max(candidates, key=lambda item: item[:-1])[-1]
                replicate_source = source
                holder = Spectrum(
                    [],
                    [],
                    name=source.name,
                    filename=source.filename,
                    source_windows=(source,),
                )
                try:
                    if getattr(sp, "response_corrected", False):
                        sp = self.master_app._response_corrected_copy(holder)
                    else:
                        sp = self.master_app._raw_spectrum_copy(holder)
                except Exception:
                    sp = Spectrum(
                        list(source.x),
                        list(source.y),
                        name=source.name,
                        filename=source.filename,
                        source_windows=(source,),
                    )
        replicates = []
        if replicate_source is not None and hasattr(
            self.master_app,
            "replicate_spectrum_snapshots",
        ):
            replicates = self.master_app.replicate_spectrum_snapshots(
                replicate_source,
                response_corrected=response_corrected,
            )
        return {
            "x": list(getattr(sp, "x", []) or []),
            "y": list(getattr(sp, "y", []) or []),
            "name": getattr(sp, "name", ""),
            "response_sources": list(getattr(sp, "response_sources", ()) or ()),
            "source_window": str(getattr(replicate_source, "name", "") or "") if replicate_source else "",
            "calibration_intercept": safe_float(
                getattr(replicate_source, "calibration_intercept", 0.0) if replicate_source else 0.0,
                0.0,
            ),
            "calibration_slope": safe_float(
                getattr(replicate_source, "calibration_slope", 1.0) if replicate_source else 1.0,
                1.0,
            ),
            "replicates": replicates,
        }

    def _build_voigt_fit_snapshot(self, lines, line_overrides=None, preserve_view=True, max_nfev=None, initial_free=None):
        xlim, ylim = self.master_app.current_plot_view()
        opts = self.master_app.options
        spectrum = self._active_spectrum_snapshot(lines)
        saved_fit_range = _session_voigt_saved_fit_range(
            self.master_app,
            lines,
        )
        overrides = (
            self._line_overrides_from_editor(
                list(lines),
                apply_to_template=False,
            )
            if line_overrides is None
            else dict(line_overrides)
        )
        line_records = [
            {
                "key": id(t),
                "wavelen": safe_float(getattr(t, "wavelen", 0.0), 0.0),
                "fitwavelen": safe_float(getattr(t, "fitwavelen", 0.0), 0.0),
                "wg": safe_float(getattr(t, "wg", 0.0), 0.0),
                "wl": safe_float(getattr(t, "wl", 0.0), 0.0),
                "specie": getattr(t, "specie", ""),
                "ion": safe_int(getattr(t, "ion", 0), 0),
            }
            for t in list(lines)
        ]
        if (
            bool(getattr(self, "automatic", False))
            and not saved_fit_range
            and spectrum
        ):
            measured_limits = _voigt_expanded_baseline_limits(
                spectrum.get("x") or [],
                spectrum.get("y") or [],
                line_records,
                xlim,
                search_range=max(
                    abs(safe_float(getattr(opts, "search_range", 0.1), 0.1)),
                    abs(safe_float(getattr(opts, "delta_min", 0.5), 0.5)),
                ),
                line_overrides=overrides,
            )
            if measured_limits is not None:
                xlim = measured_limits
        return {
            "spectrum": spectrum,
            "replicates": list((spectrum or {}).get("replicates", []) or []),
            "xlim": tuple(xlim),
            "ylim": tuple(ylim),
            "fit_range_locked": bool(saved_fit_range),
            "preserve_view": bool(preserve_view),
            "line_overrides": overrides,
            "lines": line_records,
            "options": {
                "voigt_baseline_mode": _voigt_baseline_mode(opts),
                "voigt_fit_ranges": getattr(opts, "voigt_fit_ranges", "{}"),
                "fixed_wg": safe_float(getattr(opts, "fixed_wg", 0.5), 0.5),
                "fixed_wl": safe_float(getattr(opts, "fixed_wl", 0.5), 0.5),
                "fix_wg": bool(getattr(opts, "fix_wg", False)),
                "fix_wl": bool(getattr(opts, "fix_wl", False)),
                "fix_wavelength": bool(getattr(opts, "fix_wavelength", False)),
                "search_range": safe_float(
                    getattr(opts, "search_range", 0.1),
                    0.1,
                ),
                "iterations": safe_int(getattr(opts, "iterations", 20), 20),
                "quality_max_replicate_area_cv": safe_float(
                    getattr(opts, "quality_max_replicate_area_cv", 0.25),
                    0.25,
                ),
                "_allow_residual_nuisance": bool(
                    getattr(self, "automatic", False)
                ),
            },
            "max_nfev": max_nfev,
            "initial_free": list(initial_free) if initial_free is not None else None,
        }

    @staticmethod
    def _is_maxfev_result(result):
        try:
            status = int(getattr(result, "status", -1))
        except Exception:
            status = -1
        message = str(getattr(result, "message", "")).lower()
        return status == 0 and "maximum number of function evaluations" in message

    @staticmethod
    def _voigt_selected_component_indices(lines, fit_lines, popt):
        """Associate fitted components with analytical NIST transitions.

        Free Voigt components can cross during optimization.  Their array
        order is therefore not a reliable identity once nuisance peaks are
        present.
        """
        selected = list(lines or [])
        components = list(fit_lines or [])
        if not selected:
            return []
        centers = [
            float(popt[3 + 4 * index])
            for index in range(len(components))
        ]
        pairs = []
        for line_index, line in enumerate(selected):
            target = safe_float(
                line.get("_target_center"),
                line.get("wavelen"),
            )
            for component_index, center in enumerate(centers):
                pairs.append((
                    abs(center - target),
                    line_index,
                    component_index,
                ))
        assignments = {}
        used_components = set()
        for _distance, line_index, component_index in sorted(pairs):
            if (
                line_index in assignments
                or component_index in used_components
            ):
                continue
            assignments[line_index] = component_index
            used_components.add(component_index)
            if len(assignments) == len(selected):
                break
        return [
            assignments.get(index, min(index, len(components) - 1))
            for index in range(len(selected))
        ]

    def _voigt_fit_payload_from_params(
        self,
        lines,
        popt,
        xs,
        ys,
        snapshot,
        component_indices=None,
        integration_x=None,
        integrate_to_baseline=False,
    ):
        fit_values = []
        integration_axis = (
            np.asarray(integration_x, dtype=float)
            if integration_x is not None
            else np.asarray(xs, dtype=float)
        )
        for idx, line in enumerate(lines):
            component_index = (
                int(component_indices[idx])
                if component_indices is not None
                else idx
            )
            area = float(popt[2 + 4 * component_index])
            cen = float(popt[3 + 4 * component_index])
            sigma = abs(float(popt[4 + 4 * component_index]))
            gamma = abs(float(popt[5 + 4 * component_index]))
            fitted_wg = float(2.354820045 * sigma)
            fitted_wl = float(2.0 * gamma)
            peak_height = float(area * voigt_profile_unit(np.asarray([cen], dtype=float), cen, sigma, gamma)[0])
            baseline_area, integral_left, integral_right = (
                _voigt_integral_to_baseline(
                    integration_axis,
                    area,
                    cen,
                    sigma,
                    gamma,
                )
            )
            integrated_area = baseline_area if integrate_to_baseline else area
            fit_values.append({
                "key": line["key"],
                "component_index": component_index,
                "template_wavelength": float(line["wavelen"]),
                "fit_center": cen,
                "peak_intensity": peak_height,
                "lorentzian_width": abs(fitted_wl),
                "gaussian_width": abs(fitted_wg),
                "profile_area": area,
                "integrated_area": integrated_area,
                "integration_left": integral_left,
                "integration_right": integral_right,
                "sigma": sigma,
                "gamma": gamma,
            })
        fitted_y = multivoigt_model(xs, *popt)
        return {
            "fit_values": fit_values,
            "baseline_mode": _voigt_baseline_mode(snapshot.get("options")),
            "baseline_offset": float(popt[0]),
            "baseline_slope": float(popt[1]),
            "overlay": (xs.tolist(), fitted_y.tolist()),
            "residual_x": xs.tolist(),
            "residual_y": (ys - fitted_y).tolist(),
            "xlim": snapshot.get("xlim"),
            "ylim": snapshot.get("ylim"),
        }

    def _attach_replicate_voigt_statistics(
        self,
        snapshot,
        payload,
        stop_requested,
    ):
        """Fit every acquisition independently and summarize area precision.

        The quantitative area remains the Voigt integral fitted on the mean
        spectrum. Replicate fits measure repeatability only: poor precision is
        reported explicitly, but it does not invalidate an otherwise valid
        mean-spectrum fit or silently remove its Boltzmann point.
        """
        replicates = list(snapshot.get("replicates") or [])
        if snapshot.get("_replicate_pass", False) or len(replicates) < 2:
            return
        mean_items = {
            item.get("key"): item
            for item in list(payload.get("fit_values") or [])
        }
        if not mean_items:
            return
        values_by_key = {key: [] for key in mean_items}
        valid_by_key = {key: 0 for key in mean_items}
        for item in mean_items.values():
            item["mean_fit_quality_ok"] = bool(
                item.get("quality_ok", True)
            )
            item["mean_fit_quality_message"] = str(
                item.get("quality_message", "") or ""
            )
        mean_lines = list(snapshot.get("lines") or [])
        for replicate in replicates:
            if stop_requested():
                raise FitStoppedError()
            replicate_lines = []
            for source_line in mean_lines:
                line = dict(source_line)
                fitted = mean_items.get(line.get("key"))
                if fitted:
                    line["fitwavelen"] = safe_float(
                        fitted.get("fit_center"),
                        line.get("fitwavelen", 0.0),
                    )
                    line["wg"] = abs(safe_float(
                        fitted.get("gaussian_width"),
                        line.get("wg", 0.0),
                    ))
                    line["wl"] = abs(safe_float(
                        fitted.get("lorentzian_width"),
                        line.get("wl", 0.0),
                    ))
                replicate_lines.append(line)
            replicate_snapshot = dict(snapshot)
            replicate_snapshot["spectrum"] = dict(replicate)
            replicate_snapshot["replicates"] = []
            replicate_snapshot["lines"] = replicate_lines
            replicate_snapshot["initial_free"] = None
            replicate_snapshot["_replicate_pass"] = True
            replicate_snapshot["_residual_refit_done"] = True
            result = self._run_voigt_fit_snapshot(
                replicate_snapshot,
                stop_requested,
            )
            result_items = {
                item.get("key"): item
                for item in list((result.get("payload") or {}).get("fit_values") or [])
            }
            for key in mean_items:
                item = result_items.get(key)
                area = safe_float(
                    item.get("integrated_area") if item else None,
                    math.nan,
                )
                if (
                    result.get("status") == "success"
                    and item
                    and item.get("quality_ok", True)
                    and math.isfinite(area)
                    and area > 0.0
                ):
                    values_by_key[key].append(area)
                    valid_by_key[key] += 1
                else:
                    values_by_key[key].append(None)

        total = len(replicates)
        max_cv = max(
            0.0,
            safe_float(
                (snapshot.get("options") or {}).get(
                    "quality_max_replicate_area_cv",
                    0.25,
                ),
                0.25,
            ),
        )
        payload["replicate_count"] = total
        payload["replicate_area_cv_limit"] = max_cv
        for key, item in mean_items.items():
            raw_values = list(values_by_key.get(key, []))
            valid_values = [
                float(value)
                for value in raw_values
                if value is not None and math.isfinite(float(value))
            ]
            count = len(valid_values)
            item["mean_spectrum_area"] = safe_float(
                item.get("integrated_area"),
                math.nan,
            )
            item["replicate_areas"] = raw_values
            item["replicate_area_count"] = count
            item["replicate_area_total"] = total
            item["replicate_area_cv_limit"] = max_cv
            if count:
                mean_area = math.fsum(valid_values) / count
                area_sd = (
                    math.sqrt(
                        math.fsum(
                            (value - mean_area) ** 2
                            for value in valid_values
                        ) / (count - 1)
                    )
                    if count > 1
                    else math.nan
                )
                area_cv = (
                    area_sd / abs(mean_area)
                    if count > 1 and mean_area != 0.0
                    else math.nan
                )
                item["replicate_area_mean"] = mean_area
                item["replicate_area_sd"] = area_sd
                item["replicate_area_cv"] = area_cv
            else:
                mean_area = math.nan
                area_cv = math.nan
                item["replicate_area_mean"] = math.nan
                item["replicate_area_sd"] = math.nan
                item["replicate_area_cv"] = math.nan

            precision_warning = ""
            if count != total:
                precision_warning = (
                    f"only {count}/{total} replicate Voigt areas passed quality"
                )
            elif not math.isfinite(area_cv):
                precision_warning = "replicate Voigt-area CV is not finite"
            elif area_cv > max_cv:
                precision_warning = (
                    f"replicate Voigt-area CV {area_cv:.3f} > {max_cv:.3f}"
                )
            item["replicate_precision_ok"] = not bool(precision_warning)
            item["replicate_precision_warning"] = precision_warning
            if precision_warning:
                previous = str(item.get("quality_warning", "") or "")
                item["quality_warning"] = "; ".join(
                    part for part in (previous, precision_warning) if part
                )

    def _run_voigt_fit_snapshot(self, snapshot, stop_requested):
        if np is None:
            return {"status": "error", "message": "NumPy is not available.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        try:
            from scipy.optimize import least_squares
        except Exception:
            return {"status": "error", "message": "SciPy optimization is not available. Install SciPy.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        if stop_requested():
            raise FitStoppedError()
        spectrum = snapshot.get("spectrum")
        if not spectrum or not spectrum.get("x"):
            return {"status": "error", "message": "Load a spectrum first.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        x_values = list(spectrum.get("x") or [])
        y_values = list(spectrum.get("y") or [])
        lo, hi = sorted(snapshot.get("xlim", (-math.inf, math.inf)))
        selected_lines = list(snapshot.get("lines") or [])
        if not selected_lines:
            return {"status": "error", "message": "No marked line in the visible window. Use search/manual marking before fitting.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        options = snapshot.get("options") or {}
        baseline_mode = _voigt_baseline_mode(options)
        if (
            baseline_mode in {"auto_bic", "palleschi_bic_diagnostic"}
            and not snapshot.get("_baseline_model_selection_done", False)
        ):
            # The Palleschi model is authoritative. BIC is deliberately only
            # a diagnostic comparison and must never replace its areas with a
            # constant-baseline result.
            linear_snapshot = dict(snapshot)
            linear_options = dict(options)
            linear_options["voigt_baseline_mode"] = "local_linear"
            linear_snapshot["options"] = linear_options
            linear_snapshot["_baseline_model_selection_done"] = True
            linear_snapshot["_skip_replicate_statistics"] = True
            linear_snapshot["initial_free"] = None
            authoritative = self._run_voigt_fit_snapshot(
                linear_snapshot,
                stop_requested,
            )
            linear_payload = authoritative.get("payload") or {}
            linear_bic = _voigt_result_bic(authoritative)
            constant_result = None
            constant_bic = math.inf
            comparable = False
            fit_range = linear_payload.get("fit_range")
            if authoritative.get("status") == "success" and fit_range:
                constant_snapshot = dict(snapshot)
                constant_options = dict(options)
                constant_options["voigt_baseline_mode"] = "origin_constant"
                constant_snapshot["options"] = constant_options
                constant_snapshot["xlim"] = tuple(fit_range)
                constant_snapshot["fit_range_locked"] = False
                constant_snapshot["_baseline_model_selection_done"] = True
                constant_snapshot["_baseline_roi_retry_done"] = True
                constant_snapshot["_skip_replicate_statistics"] = True
                constant_snapshot["initial_free"] = None
                constant_result = self._run_voigt_fit_snapshot(
                    constant_snapshot,
                    stop_requested,
                )
                constant_payload = constant_result.get("payload") or {}
                comparable = (
                    constant_result.get("status") == "success"
                    and len(constant_payload.get("residual_y") or [])
                    == len(linear_payload.get("residual_y") or [])
                )
                if comparable:
                    constant_bic = _voigt_result_bic(constant_result)

            bic_threshold = 6.0
            improvement = constant_bic - linear_bic
            if comparable and math.isfinite(improvement):
                if improvement >= bic_threshold:
                    recommendation = "linear baseline strongly supported"
                elif improvement <= -bic_threshold:
                    recommendation = (
                        "constant baseline would be statistically sufficient"
                    )
                else:
                    recommendation = "baseline comparison inconclusive"
            else:
                recommendation = "baseline BIC comparison unavailable"

            payload = authoritative.get("payload") or {}
            payload["baseline_mode_requested"] = baseline_mode
            payload["baseline_mode_selected"] = "local_linear"
            payload["baseline_bic_threshold"] = bic_threshold
            payload["baseline_bic"] = {
                "origin_constant": constant_bic,
                "local_linear": linear_bic,
            }
            payload["baseline_bic_comparable"] = comparable
            payload["baseline_bic_recommendation"] = recommendation
            payload["baseline_selection_reason"] = (
                "Local-linear baseline retained; BIC is diagnostic only"
            )
            if (
                authoritative.get("status") == "success"
                and not snapshot.get("_skip_replicate_statistics", False)
            ):
                self._attach_replicate_voigt_statistics(
                    snapshot,
                    payload,
                    stop_requested,
                )
                payload["warning_lines"] = sum(
                    1
                    for item in payload.get("fit_values", [])
                    if str(item.get("quality_warning", "") or "")
                )
            authoritative["payload"] = payload
            if authoritative.get("status") == "success":
                authoritative["message"] = (
                    f"{authoritative.get('message', 'Fit Voigt')}, "
                    "local-linear baseline; BIC diagnostic only"
                )
            self.last_fit_result = authoritative
            return authoritative
        line_overrides = snapshot.get("line_overrides") or {}
        pairs = [(x, y_values[i]) for i, x in enumerate(x_values) if i < len(y_values) and lo <= x <= hi]
        xs = np.asarray([x for x, _y in pairs], dtype=float)
        ys = np.asarray([y for _x, y in pairs], dtype=float)
        if len(xs) < 5:
            return {"status": "error", "message": f"Too few spectrum points for Voigt fit: {len(xs)} found.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        integration_x = np.asarray(xs, dtype=float).copy()
        xmin, xmax = float(xs.min()), float(xs.max())
        width = max(xmax - xmin, 1e-9)
        baseline = float(np.percentile(ys, 5))
        slope = 0.0
        dx = float(np.median(np.diff(np.sort(xs)))) if len(xs) > 2 else width / 100.0
        default_fixed_wg = abs(safe_float(options.get("fixed_wg"), 0.5))
        default_fixed_wl = abs(safe_float(options.get("fixed_wl"), 0.5))
        auto_fwhm = _voigt_auto_fwhm(dx, width)
        min_sigma0 = max(abs(dx) * 0.25, 1e-6)
        min_gamma0 = max(abs(dx) * 0.25, 1e-6)
        sigma0 = max(auto_fwhm / 2.354820045, min_sigma0)
        gamma0 = max(auto_fwhm / 2.0, min_gamma0)
        p0 = [baseline, slope]
        bounds_lo = [-np.inf, -np.inf]
        bounds_hi = [np.inf, np.inf]
        fixed_mask = [
            False,
            baseline_mode != "local_linear",
        ]
        center_bound_scale = max(
            safe_float(options.get("_center_bound_scale"), 1.0),
            1.0,
        )
        half_window = center_bound_scale * max(
            width * 0.02,
            width / 20.0,
            abs(dx) * 2.0,
        )
        for line in selected_lines:
            line["_global_fix_wavelength"] = bool(options.get("fix_wavelength", False))
        fit_lines, nuisance_count = _voigt_prepare_components(
            selected_lines,
            line_overrides,
            xs,
            ys,
            half_window,
            dx,
            extra_nuisance_centers=options.get(
                "_residual_nuisance_centers",
                (),
            ),
        )
        if options.get("_selected_components_only", False):
            fit_lines = [
                line
                for line in fit_lines
                if not bool(line.get("_nuisance", False))
            ]
            nuisance_count = 0
        else:
            # Nearby maxima are hypotheses, not automatic analytical
            # components. Only residual peaks explicitly proposed by the
            # BIC-controlled refit are allowed into the optimized model.
            fit_lines = [
                line
                for line in fit_lines
                if (
                    not bool(line.get("_nuisance", False))
                    or str(line.get("key", "")).startswith(
                        "__residual_nuisance_"
                    )
                )
            ]
            nuisance_count = sum(
                1
                for line in fit_lines
                if bool(line.get("_nuisance", False))
            )
        min_points = _voigt_free_parameter_count(
            fit_lines,
            options=options,
            line_overrides=line_overrides,
        )
        if len(xs) < min_points:
            return {"status": "error", "message": f"Too few spectrum points for Voigt fit: {len(xs)} found, {min_points} required.", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
        for line in fit_lines:
            if stop_requested():
                raise FitStoppedError()
            override = line_overrides.get(line["key"], {})
            if override:
                center0 = safe_float(line.get("_center0"), abs(safe_float(
                    override.get("center"), line["fitwavelen"] or line["wavelen"]
                )))
            else:
                center0 = safe_float(line.get("_center0"), line["wavelen"])
            peak_y = _nearest_y(x_values, y_values, center0)
            height = _voigt_initial_height(peak_y, ys, baseline)
            if override:
                row_fix_wg = bool(override.get("fix_wg", False))
                row_fix_wl = bool(override.get("fix_wl", False))
                wg_fwhm = (
                    abs(safe_float(override.get("wg"), default_fixed_wg))
                    if row_fix_wg
                    else abs(line["wg"]) or auto_fwhm
                )
                wl_fwhm = (
                    abs(safe_float(override.get("wl"), default_fixed_wl))
                    if row_fix_wl
                    else abs(line["wl"]) or auto_fwhm
                )
            else:
                row_fix_wg = bool(options.get("fix_wg", False)) or line["wg"] < 0
                row_fix_wl = bool(options.get("fix_wl", False)) or line["wl"] < 0
                wg_fwhm = default_fixed_wg if row_fix_wg else (abs(line["wg"]) if line["wg"] else auto_fwhm)
                wl_fwhm = default_fixed_wl if row_fix_wl else (abs(line["wl"]) if line["wl"] else auto_fwhm)
            sig0 = max(wg_fwhm / 2.354820045, 1e-12 if row_fix_wg else min_sigma0)
            gam0 = max(wl_fwhm / 2.0, 1e-12 if row_fix_wl else min_gamma0)
            area0 = _voigt_initial_area(height, center0, sig0, gam0, dx)
            p0.extend([area0, center0, max(sig0, 1e-6), max(gam0, 1e-6)])
            bound_center = safe_float(line.get("_bound_center"), center0)
            bound_half_window = abs(safe_float(
                line.get("_bound_half_window"), half_window
            ))
            c_lo = max(xmin, bound_center - bound_half_window)
            c_hi = min(xmax, bound_center + bound_half_window)
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

        optimizer_y = ys

        def _multivoigt_residuals(p_free):
            if stop_requested():
                raise FitStoppedError()
            return (
                multivoigt_model(xs, *_expand_fit_parameters(p_free))
                - optimizer_y
            )

        max_nfev = snapshot.get("max_nfev")
        if max_nfev is None:
            max_nfev = max(2000, safe_int(options.get("iterations"), 20) * 400)
        requested_initial = snapshot.get("initial_free")
        if requested_initial is not None:
            requested_initial = np.asarray(requested_initial, dtype=float)
            if requested_initial.shape != p0_full[free_mask].shape:
                requested_initial = None

        initial_full_candidates = [p0_full.copy()]
        if requested_initial is None:
            for style in ("gaussian", "lorentzian"):
                candidate = p0_full.copy()
                for index, _line in enumerate(fit_lines):
                    area_index = 2 + 4 * index
                    sigma_index = area_index + 2
                    gamma_index = area_index + 3
                    old_sigma = candidate[sigma_index]
                    old_gamma = candidate[gamma_index]
                    old_height = candidate[area_index] * voigt_profile_unit(
                        np.asarray([0.0], dtype=float),
                        0.0,
                        old_sigma,
                        old_gamma,
                    )[0]
                    if style == "gaussian":
                        if not fixed_mask[sigma_index]:
                            candidate[sigma_index] = max(
                                auto_fwhm / 2.354820045,
                                bounds_lo_full[sigma_index] * 1.1,
                            )
                        if not fixed_mask[gamma_index]:
                            candidate[gamma_index] = bounds_lo_full[gamma_index] * 1.1
                    else:
                        if not fixed_mask[sigma_index]:
                            candidate[sigma_index] = bounds_lo_full[sigma_index] * 1.1
                        if not fixed_mask[gamma_index]:
                            candidate[gamma_index] = max(
                                auto_fwhm * 2.0,
                                bounds_lo_full[gamma_index] * 1.1,
                            )
                    candidate[sigma_index] = min(
                        candidate[sigma_index],
                        bounds_hi_full[sigma_index] * (1.0 - 1.0e-9),
                    )
                    candidate[gamma_index] = min(
                        candidate[gamma_index],
                        bounds_hi_full[gamma_index] * (1.0 - 1.0e-9),
                    )
                    candidate[area_index] = _voigt_initial_area(
                        old_height,
                        candidate[area_index + 1],
                        candidate[sigma_index],
                        candidate[gamma_index],
                        dx,
                    )
                initial_full_candidates.append(candidate)
        else:
            candidate = p0_full.copy()
            candidate[free_mask] = requested_initial
            initial_full_candidates = [candidate]

        unique_initials = []
        for candidate in initial_full_candidates:
            free_candidate = np.asarray(candidate[free_mask], dtype=float)
            if not any(
                np.allclose(free_candidate, existing, rtol=1.0e-12, atol=1.0e-15)
                for existing in unique_initials
            ):
                unique_initials.append(free_candidate)

        result = None
        initial_free = unique_initials[0]
        last_exception = None
        for candidate in unique_initials:
            try:
                current = least_squares(
                    _multivoigt_residuals,
                    candidate,
                    bounds=(bounds_lo_full[free_mask], bounds_hi_full[free_mask]),
                    method="trf",
                    jac="2-point",
                    max_nfev=int(max_nfev),
                    x_scale="jac",
                )
            except FitStoppedError:
                raise
            except Exception as exc:
                last_exception = exc
                continue
            if result is None or current.cost < result.cost:
                result = current
                initial_free = candidate
        if result is None:
            return {
                "status": "error",
                "message": str(last_exception or "Voigt optimization failed"),
                "payload": None,
                "best_free": None,
                "initial_free": np.asarray(initial_free, dtype=float).tolist(),
                "max_nfev": int(max_nfev),
            }
        if stop_requested():
            raise FitStoppedError()
        popt = _expand_fit_parameters(result.x)
        preliminary_y = multivoigt_model(xs, *popt)
        preliminary_residuals = ys - preliminary_y
        if (
            bool(options.get("_allow_residual_nuisance", False))
            and not snapshot.get("_residual_refit_done", False)
        ):
            residual_median = float(np.median(preliminary_residuals))
            residual_mad = float(
                np.median(np.abs(preliminary_residuals - residual_median))
            )
            residual_noise = 1.4826 * residual_mad
            if not math.isfinite(residual_noise) or residual_noise <= 0.0:
                residual_noise = float(np.std(preliminary_residuals))
            residual_noise = max(residual_noise, 1.0e-300)
            selected_peak_height = max(
                (
                    abs(float(popt[2 + 4 * index]))
                    * float(
                        voigt_profile_unit(
                            np.asarray(
                                [float(popt[3 + 4 * index])],
                                dtype=float,
                            ),
                            float(popt[3 + 4 * index]),
                            abs(float(popt[4 + 4 * index])),
                            abs(float(popt[5 + 4 * index])),
                        )[0]
                    )
                    for index in range(len(selected_lines))
                ),
                default=0.0,
            )
            residual_threshold = max(
                4.0 * residual_noise,
                0.03 * selected_peak_height,
                1.0e-300,
            )
            existing_centers = [
                float(popt[3 + 4 * index])
                for index in range(len(fit_lines))
            ]
            minimum_residual_separation = max(abs(dx) * 0.45, 1.0e-9)
            residual_candidates = [
                candidate
                for candidate in _voigt_peak_candidates(
                    xs,
                    preliminary_residuals,
                )
                if candidate["y"] - residual_median >= residual_threshold
                and candidate["prominence"] >= residual_threshold
                and all(
                    abs(candidate["x"] - center)
                    > minimum_residual_separation
                    for center in existing_centers
                )
            ]
            residual_candidates.sort(
                key=lambda candidate: candidate["prominence"],
                reverse=True,
            )
            extra_centers = [
                candidate["x"]
                for candidate in residual_candidates[:2]
            ]
            if extra_centers:
                retry_snapshot = dict(snapshot)
                retry_options = dict(options)
                retry_options["_residual_nuisance_centers"] = list(
                    options.get("_residual_nuisance_centers", ())
                ) + extra_centers
                retry_snapshot["options"] = retry_options
                retry_snapshot["_residual_refit_done"] = True
                retry_snapshot["initial_free"] = None
                retry_result = self._run_voigt_fit_snapshot(
                    retry_snapshot,
                    stop_requested,
                )
                if retry_result.get("status") == "success":
                    current_sse = max(
                        2.0 * float(result.cost),
                        1.0e-300,
                    )
                    retry_sse = max(
                        2.0 * safe_float(
                            retry_result.get("cost"),
                            math.inf,
                        ),
                        1.0e-300,
                    )
                    current_parameter_count = int(np.count_nonzero(free_mask))
                    retry_parameter_count = safe_int(
                        retry_result.get("free_parameter_count"),
                        current_parameter_count + 4 * len(extra_centers),
                    )
                    sample_count = max(len(xs), 2)
                    current_bic = (
                        sample_count
                        * math.log(current_sse / sample_count)
                        + current_parameter_count * math.log(sample_count)
                    )
                    retry_bic = (
                        sample_count
                        * math.log(retry_sse / sample_count)
                        + retry_parameter_count * math.log(sample_count)
                    )
                    if retry_bic <= current_bic - 6.0:
                        retry_payload = retry_result.get("payload") or {}
                        retry_payload["residual_refit"] = True
                        retry_payload["residual_bic_improvement"] = (
                            current_bic - retry_bic
                        )
                        return retry_result
        analytical_lines = fit_lines[:len(selected_lines)]
        component_indices = self._voigt_selected_component_indices(
            analytical_lines,
            fit_lines,
            popt,
        )
        payload = self._voigt_fit_payload_from_params(
            analytical_lines,
            popt,
            xs,
            ys,
            snapshot,
            component_indices=component_indices,
            integration_x=np.asarray(x_values, dtype=float),
            integrate_to_baseline=baseline_mode == "libs_auto",
        )
        visualization = _voigt_fit_visualization(
            x_values,
            xs,
            popt,
            len(fit_lines),
        )
        if visualization:
            payload["overlay"] = (
                visualization["x"],
                visualization["total"],
            )
            payload["baseline_overlay"] = (
                visualization["x"],
                visualization["baseline"],
            )
            payload["component_overlays"] = [
                (
                    visualization["x"],
                    visualization["components"][component_index],
                )
                for component_index in component_indices
            ]
            payload["integration_bounds"] = [
                visualization["bounds"][component_index]
                for component_index in component_indices
            ]
            payload["display_xlim"] = (
                float(visualization["x"][0]),
                float(visualization["x"][-1]),
            )
            payload["display_threshold_fraction"] = visualization[
                "threshold_fraction"
            ]
        payload["fit_range_mode"] = (
            "saved ROI"
            if snapshot.get("fit_range_locked", False)
            else "visible ROI"
        )
        payload["fit_range"] = (float(xs[0]), float(xs[-1]))
        payload["integration_method"] = (
            "LIBS+ baseline-reaching Voigt (0.5% height)"
            if baseline_mode == "libs_auto"
            else (
                "Full normalized Voigt profile; diagnostic display to "
                "0.5% height"
            )
        )
        fitted_y = preliminary_y
        residuals = ys - fitted_y
        residual_median = float(np.median(residuals))
        residual_mad = float(np.median(np.abs(residuals - residual_median)))
        residual_noise = 1.4826 * residual_mad
        if not math.isfinite(residual_noise) or residual_noise <= 0.0:
            residual_noise = float(np.std(residuals))
        residual_noise = max(residual_noise, 1.0e-300)
        for item in payload.get("fit_values", []):
            component_index = safe_int(item.get("component_index"), 0)
            component = fit_lines[component_index]
            bound_center = safe_float(
                component.get("_bound_center"),
                item.get("template_wavelength"),
            )
            bound_half = abs(safe_float(
                component.get("_bound_half_window"),
                half_window,
            ))
            peak_snr = abs(safe_float(item.get("peak_intensity"), 0.0)) / residual_noise
            item["peak_snr"] = peak_snr
            item["observed_center"] = safe_float(
                component.get("_center0"),
                bound_center,
            )
            item["target_center"] = safe_float(
                component.get("_target_center"),
                item.get("template_wavelength"),
            )
            item.update(
                _voigt_quality_assessment(
                    center=safe_float(item.get("fit_center"), bound_center),
                    bound_center=bound_center,
                    bound_half_window=bound_half,
                    dx=dx,
                    fit_span=float(xs[-1] - xs[0]),
                    gaussian_width=safe_float(
                        item.get("gaussian_width"),
                        0.0,
                    ),
                    lorentzian_width=safe_float(
                        item.get("lorentzian_width"),
                        0.0,
                    ),
                    peak_snr=peak_snr,
                    fixed_center=bool(options.get("fix_wavelength", False)),
                )
            )
        boundary_hits = [
            item
            for item in payload.get("fit_values", [])
            if bool(item.get("at_center_bound", False))
        ]
        if boundary_hits and not snapshot.get("_center_bound_retry_done", False):
            retry_snapshot = dict(snapshot)
            retry_snapshot["_center_bound_retry_done"] = True
            retry_snapshot["initial_free"] = None
            retry_options = dict(options)
            retry_options["_center_bound_scale"] = max(
                center_bound_scale * 2.5,
                2.5,
            )
            retry_snapshot["options"] = retry_options
            retry_result = self._run_voigt_fit_snapshot(
                retry_snapshot,
                stop_requested,
            )
            retry_payload = retry_result.get("payload") or {}
            retry_values = list(retry_payload.get("fit_values") or [])
            retry_boundary_hits = sum(
                bool(item.get("at_center_bound", False))
                for item in retry_values
            )
            retry_rejections = sum(
                not item.get("quality_ok", True)
                for item in retry_values
            )
            current_rejections = sum(
                not item.get("quality_ok", True)
                for item in payload.get("fit_values", [])
            )
            retry_by_key = {
                item.get("key"): item
                for item in retry_values
            }
            retry_resolved_without_drift = all(
                (
                    retry_by_key.get(item.get("key")) is not None
                    and not retry_by_key[item.get("key")].get(
                        "at_center_bound",
                        False,
                    )
                    and retry_by_key[item.get("key")].get(
                        "quality_ok",
                        True,
                    )
                    and abs(
                        safe_float(
                            retry_by_key[item.get("key")].get("fit_center"),
                            math.inf,
                        )
                        - safe_float(item.get("observed_center"), math.inf)
                    )
                    <= abs(
                        safe_float(item.get("fit_center"), math.inf)
                        - safe_float(item.get("observed_center"), math.inf)
                    )
                    + 0.25 * abs(dx)
                )
                for item in boundary_hits
            )
            if (
                retry_result.get("status") == "success"
                and retry_values
                and retry_boundary_hits < len(boundary_hits)
                and retry_rejections <= current_rejections
                and retry_resolved_without_drift
            ):
                retry_payload["center_bound_retry"] = True
                retry_result["payload"] = retry_payload
                return retry_result
        truncated_saved_roi = (
            bool(snapshot.get("fit_range_locked", False))
            and not snapshot.get("_baseline_roi_retry_done", False)
            and any(
                not item.get("quality_ok", True)
                and (
                    safe_float(item.get("fwhm_roi_fraction"), 0.0) >= 0.80
                    or "baseline sides" in str(
                        item.get("quality_message", "")
                    ).lower()
                )
                for item in payload.get("fit_values", [])
            )
        )
        if truncated_saved_roi:
            fitted_by_key = {
                item.get("key"): item
                for item in payload.get("fit_values", [])
            }
            baseline_lines = []
            for line in selected_lines:
                baseline_line = dict(line)
                fitted = fitted_by_key.get(line.get("key"))
                if fitted:
                    baseline_line["fitwavelen"] = safe_float(
                        fitted.get("fit_center"),
                        baseline_line.get("wavelen", 0.0),
                    )
                baseline_lines.append(baseline_line)
            expanded_limits = _voigt_expanded_baseline_limits(
                x_values,
                y_values,
                baseline_lines,
                (lo, hi),
                search_range=options.get("search_range", 1.0),
                line_overrides=line_overrides,
            )
            if expanded_limits is not None:
                retry_snapshot = dict(snapshot)
                retry_snapshot["xlim"] = expanded_limits
                retry_snapshot["fit_range_locked"] = False
                retry_snapshot["_baseline_roi_retry_done"] = True
                retry_snapshot["initial_free"] = None
                retry_result = self._run_voigt_fit_snapshot(
                    retry_snapshot,
                    stop_requested,
                )
                retry_payload = retry_result.get("payload") or {}
                current_rejected = sum(
                    1
                    for item in payload.get("fit_values", [])
                    if not item.get("quality_ok", True)
                )
                retry_rejected = safe_int(
                    retry_payload.get("rejected_lines"),
                    len(selected_lines),
                )
                if (
                    retry_result.get("status") == "success"
                    and retry_rejected < current_rejected
                ):
                    retry_payload["fit_range_mode"] = (
                        "saved ROI expanded to measured baselines"
                    )
                    retry_payload["original_fit_range"] = (
                        float(lo),
                        float(hi),
                    )
                    retry_payload["saved_roi_auto_expanded"] = True
                    retry_result["message"] += (
                        ", saved ROI expanded to both baselines"
                    )
                    self.last_fit_result = retry_result
                    return retry_result
        if not snapshot.get("_skip_replicate_statistics", False):
            self._attach_replicate_voigt_statistics(
                snapshot,
                payload,
                stop_requested,
            )
        payload["nuisance_components"] = nuisance_count
        payload["fit_spectrum_name"] = spectrum.get("name", "")
        payload["fit_response_sources"] = list(spectrum.get("response_sources", []) or [])
        payload["fit_source_window"] = str(spectrum.get("source_window", "") or "")
        payload["fit_calibration_intercept"] = safe_float(
            spectrum.get("calibration_intercept", 0.0),
            0.0,
        )
        payload["fit_calibration_slope"] = safe_float(
            spectrum.get("calibration_slope", 1.0),
            1.0,
        )
        payload["rejected_lines"] = sum(
            1 for item in payload.get("fit_values", [])
            if not item.get("quality_ok", True)
        )
        payload["warning_lines"] = sum(
            1 for item in payload.get("fit_values", [])
            if str(item.get("quality_warning", "") or "")
        )
        status = "success" if result.success else ("maxfev" if self._is_maxfev_result(result) else "error")
        if status == "success":
            message = f"Fit Voigt: {len(selected_lines)} line(s)"
            if nuisance_count:
                message += f", {nuisance_count} interfering peak(s) deconvolved"
            if payload["rejected_lines"]:
                message += f", {payload['rejected_lines']} rejected by quality checks"
            if payload["warning_lines"]:
                message += f", {payload['warning_lines']} precision warning(s)"
            if payload.get("replicate_count", 0):
                message += (
                    f", {payload['replicate_count']} replicate spectra fitted"
                )
        else:
            message = str(getattr(result, "message", "Fit failed"))
        fit_result = {
            "status": status,
            "message": message,
            "payload": payload,
            "best_free": np.asarray(result.x, dtype=float).tolist(),
            "initial_free": np.asarray(initial_free, dtype=float).tolist(),
            "max_nfev": int(max_nfev),
            "cost": float(result.cost),
            "free_parameter_count": int(np.count_nonzero(free_mask)),
        }
        self.last_fit_result = fit_result
        return fit_result

    def _apply_voigt_fit_payload(self, lines, payload, mode_label):
        self.master_app.fit_overlay_label = "Voigt sum"
        self.master_app.fit_component_label = "Voigt"
        by_key = {item.get("key"): item for item in list(payload.get("fit_values") or [])}
        results = []
        nuisance_components = safe_int(payload.get("nuisance_components", 0), 0)
        for t in list(lines):
            item = by_key.get(id(t))
            if not item:
                continue
            response_sources = tuple(payload.get("fit_response_sources", []) or ())
            t.fit_response_source = response_sources[0] if len(response_sources) == 1 else ""
            t.fit_source_window = str(
                payload.get("fit_source_window", "")
                or payload.get("fit_spectrum_name", "")
                or ""
            )
            t.fit_calibration_intercept = safe_float(
                payload.get("fit_calibration_intercept", 0.0),
                0.0,
            )
            t.fit_calibration_slope = safe_float(
                payload.get("fit_calibration_slope", 1.0),
                1.0,
            )
            t.fit_snr = safe_float(item.get("peak_snr"), 0.0)
            t.fit_quality_warning = str(item.get("quality_warning", "") or "")
            t.fit_at_center_bound = bool(item.get("at_center_bound", False))
            t.fit_nuisance_components = nuisance_components
            t.fit_replicate_areas = tuple(item.get("replicate_areas") or ())
            t.fit_replicate_area_mean = safe_float(
                item.get("replicate_area_mean"),
                math.nan,
            )
            t.fit_replicate_area_sd = safe_float(
                item.get("replicate_area_sd"),
                math.nan,
            )
            t.fit_replicate_area_cv = safe_float(
                item.get("replicate_area_cv"),
                math.nan,
            )
            t.fit_replicate_area_count = safe_int(
                item.get("replicate_area_count"),
                0,
            )
            t.fit_replicate_area_total = safe_int(
                item.get("replicate_area_total"),
                0,
            )
            t.fit_mean_spectrum_area = safe_float(
                item.get("mean_spectrum_area"),
                math.nan,
            )
            t.fit_mean_quality_ok = bool(
                item.get("mean_fit_quality_ok", item.get("quality_ok", True))
            )
            t.fit_mean_quality_message = str(
                item.get("mean_fit_quality_message", "") or ""
            )
            t.fitwavelen = float(item["fit_center"])
            t.fit_profile = "voigt"
            enriched = False
            try:
                enriched = bool(self.master_app.enrich_identified_template_line(
                    t,
                    tolerance=max(0.02, self.master_app.options.search_range),
                ))
            except Exception:
                enriched = False
            if not item.get("quality_ok", True):
                t.inte = "ERROR"
                t.wg = "ERROR"
                t.wl = "ERROR"
                t.error_inte = "ERROR"
                try:
                    t.fitinte = "ERROR"
                except Exception:
                    pass
                result = {
                    "key": id(t),
                    "template_wavelength": float(getattr(t, "wavelen", item["template_wavelength"])),
                    "line_label": (
                        f"{str(getattr(t, 'specie', '') or '').strip()} "
                        f"{_roman_ion(safe_int(getattr(t, 'ion', 0), 0))} "
                        f"{_template_line_nist_wavelength(t):.5f}"
                    ).strip(),
                    "source_window": str(
                        payload.get("fit_spectrum_name", "") or ""
                    ),
                    "fit_center": float(item["fit_center"]),
                    "peak_intensity": float(item["peak_intensity"]),
                    "lorentzian_width": "",
                    "gaussian_width": "",
                    "integrated_area": "",
                    "replicate_area_sd": item.get("replicate_area_sd"),
                    "replicate_area_cv": item.get("replicate_area_cv"),
                    "replicate_area_count": item.get("replicate_area_count", 0),
                    "replicate_area_total": item.get("replicate_area_total", 0),
                    "status": f"Rejected: {item.get('quality_message', 'quality check failed')}",
                }
                results.append(result)
                continue
            t.inte = float(item["integrated_area"])
            t.wg = abs(float(item["gaussian_width"]))
            t.wl = abs(float(item["lorentzian_width"]))
            replicate_sd = safe_float(
                item.get("replicate_area_sd"),
                math.nan,
            )
            t.error_inte = replicate_sd if math.isfinite(replicate_sd) else 0.0
            try:
                t.fitinte = float(item["peak_intensity"])
            except Exception:
                pass
            result = {
                "key": id(t),
                "template_wavelength": float(getattr(t, "wavelen", item["template_wavelength"])),
                "line_label": (
                    f"{str(getattr(t, 'specie', '') or '').strip()} "
                    f"{_roman_ion(safe_int(getattr(t, 'ion', 0), 0))} "
                    f"{_template_line_nist_wavelength(t):.5f}"
                ).strip(),
                "source_window": str(
                    payload.get("fit_spectrum_name", "") or ""
                ),
                "fit_center": float(item["fit_center"]),
                "peak_intensity": float(item["peak_intensity"]),
                "lorentzian_width": float(t.wl),
                "gaussian_width": float(t.wg),
                "integrated_area": float(item["integrated_area"]),
                "replicate_area_sd": item.get("replicate_area_sd"),
                "replicate_area_cv": item.get("replicate_area_cv"),
                "replicate_area_count": item.get("replicate_area_count", 0),
                "replicate_area_total": item.get("replicate_area_total", 0),
            }
            result["status"] = "Voigt OK + DB" if enriched else "Voigt OK"
            quality_warning = str(item.get("quality_warning", "") or "")
            if quality_warning:
                result["status"] += f"; WARNING: {quality_warning}"
            if safe_int(item.get("replicate_area_total"), 0) >= 2:
                precision_warning = str(item.get("replicate_precision_warning", "") or "")
                if precision_warning:
                    result["status"] = (
                        f"{result.get('status', 'Voigt OK')}; WARNING: "
                        f"{precision_warning}"
                    )
                else:
                    result["status"] = (
                        f"{result.get('status', 'Voigt OK')}; "
                        f"replicate CV={safe_float(item.get('replicate_area_cv'), math.nan):.1%}"
                    )
            results.append(result)
        self.master_app.fit_overlay = payload.get("overlay")
        self.master_app.fit_baseline_overlay = payload.get(
            "baseline_overlay"
        )
        self.master_app.fit_component_overlays = list(
            payload.get("component_overlays") or []
        )
        self.master_app.fit_integration_bounds = list(
            payload.get("integration_bounds") or []
        )
        self.residual_x = list(payload.get("residual_x") or [])
        self.residual_y = list(payload.get("residual_y") or [])
        self.master_app.notify_template_changed(redraw=False)
        self.master_app.redraw(preserve_view=True)
        self.master_app.restore_plot_view(
            payload.get("display_xlim") or payload.get("xlim"),
            payload.get("ylim"),
        )
        if not self.automatic:
            self.update_residuals_plot(lift_window=False)
        source_name = str(payload.get("fit_spectrum_name", "") or "spectrum")
        self.master_app.status(
            f"Voigt fit: {len(results)} lines; source={source_name}"
        )
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
            self._clear_maxfev_overlay_backup()
            return
        if status == "maxfev":
            if self.automatic:
                if callback:
                    callback(False, fit_lines, message, stopped=False, fit_result=result)
                return
            self._ensure_maxfev_overlay_backup()
            preview_drawn = self._preview_voigt_fit_overlay(result)
            can_accept = bool(result.get("payload")) and bool(result.get("best_free")) and preview_drawn
            choice = self._fit_maxfev_dialog(
                "The fit stopped because the maximum number of function evaluations was reached.\n\n"
                "Continue fit increases the limit by 2000 and retries from the best parameters found so far.",
                can_accept=can_accept,
            )
            if choice == "continue":
                next_limit = int(result.get("max_nfev") or 0) + 2000
                best_free = result.get("best_free") or result.get("initial_free")
                self._start_visible_fit_async(
                    mode_label,
                    allow_previous_visible_fallback=False,
                    show_errors=show_errors,
                    callback=callback,
                    reset_stop=False,
                    max_nfev=next_limit,
                    initial_free=best_free,
                )
                return
            if choice == "accept" and can_accept:
                results = self._apply_voigt_fit_result(fit_lines, result, mode_label)
                self.region_fit_results[self._group_key(fit_lines)] = list(results)
                if callback:
                    callback(True, fit_lines, message, stopped=False, fit_result=result)
                self._clear_maxfev_overlay_backup()
                return
            self._restore_maxfev_overlay_backup()
            self.msg_var.set("Fit canceled")
            self.master_app.status("Fit canceled")
            if callback:
                callback(False, fit_lines, "Fit canceled", stopped=False, fit_result=result)
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
                callback(False, fit_lines, message, stopped=False, fit_result=result)
            self._clear_maxfev_overlay_backup()
            return
        results = self._apply_voigt_fit_result(fit_lines, result, mode_label)
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        if callback:
            callback(True, fit_lines, message, stopped=False, fit_result=result)
        self._clear_maxfev_overlay_backup()

    def _start_visible_fit_async(self, mode_label, allow_previous_visible_fallback=True, show_errors=True, callback=None, reset_stop=True, max_nfev=None, initial_free=None):
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
            message = f"{mode_label}: no selected analytical lines are visible in the current window"
            self.msg_var.set(message)
            if show_errors:
                _showinfo(self, mode_label, "No selected analytical lines are visible in the current spectrum window.")
            elif callback:
                callback(False, [], message, stopped=False)
            return False
        if self._independent_window_conflict(fit_lines):
            message = (
                "The selected line group spans multiple detector windows. "
                "Independent-window mode never mixes their samples; fit the lines in separate regions."
            )
            self.msg_var.set(message)
            if show_errors:
                _showerror(self, mode_label, message)
            elif callback:
                callback(False, fit_lines, message, stopped=False)
            return False
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
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
                    message = "No selected analytical lines are visible in the current Manual Fit window."
                    self.msg_var.set(f"{report}; {message}")
                    if show_errors:
                        _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}")
                    elif callback:
                        callback(False, fit_lines, message, stopped=False)
                    return False
                self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
                min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
                report = f"{mode_label}: expanded window, fitting {len(fit_lines)} visible line(s) using {point_count} points"
                self.msg_var.set(report)
                self.master_app.status(report)
            if point_count < min_points:
                message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
                self.msg_var.set(f"{report}; {message}")
                if show_errors:
                    _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}\nExpansion retries: {retries}")
                elif callback:
                    callback(False, fit_lines, message, stopped=False, fit_result={"status": "error", "message": message})
                return False
        snapshot = self._build_voigt_fit_snapshot(
            fit_lines,
            preserve_view=True,
            max_nfev=max_nfev,
            initial_free=initial_free,
        )
        self._fit_running = True

        def worker():
            try:
                result = self._run_voigt_fit_snapshot(
                    snapshot,
                    lambda: bool(getattr(self, "fit_stop_requested", False)),
                )
            except FitStoppedError:
                result = {"status": "stopped", "message": "Fit stopped by user", "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
            except Exception as exc:
                result = {"status": "error", "message": str(exc), "payload": None, "best_free": None, "initial_free": None, "max_nfev": None}
            try:
                self.after(0, lambda: self._finish_async_fit(mode_label, fit_lines, report, result, show_errors, callback))
            except Exception:
                pass

        self._fit_worker = threading.Thread(target=worker, daemon=True)
        self._fit_worker.start()
        return True

    def _fit_manual_group(self, lines, max_nfev=None, initial_free=None):
        tmp = None
        try:
            tmp = MultiGaussianFitWindow(self.master_app)
            tmp.withdraw()
            overrides = self._line_overrides_from_editor(list(lines))
            snapshot = tmp._build_voigt_fit_snapshot(
                lines,
                line_overrides=overrides,
                preserve_view=True,
                max_nfev=max_nfev,
                initial_free=initial_free,
            )
            result = tmp._run_voigt_fit_snapshot(snapshot, lambda: False)
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e),
                "payload": None,
                "best_free": None,
                "initial_free": None,
                "max_nfev": max_nfev,
            }
        finally:
            try:
                if tmp is not None:
                    tmp.destroy()
            except Exception:
                pass
        return result

    def _fit_maxfev_dialog(self, message, can_accept):
        dlg = FitMaxfevDialog(self, message, can_accept=can_accept)
        try:
            self.wait_window(dlg)
        except Exception:
            return "cancel"
        return dlg.choice or "cancel"

    def _apply_voigt_fit_result(self, fit_lines, result, mode_label):
        payload = result.get("payload") or {}
        results = self._apply_voigt_fit_payload(fit_lines, payload, mode_label)
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{mode_label}: fitted")
        self.master_app.status(f"{mode_label}: fitted")
        return results

    def _preview_voigt_fit_overlay(self, result):
        payload = result.get("payload") or {}
        overlay = payload.get("overlay")
        if not overlay:
            return False
        self.master_app.fit_overlay = overlay
        self.master_app.redraw(preserve_view=True)
        return True

    def _ensure_maxfev_overlay_backup(self):
        if not hasattr(self, "_maxfev_overlay_backup"):
            self._maxfev_overlay_backup = getattr(self.master_app, "fit_overlay", None)
        return getattr(self, "_maxfev_overlay_backup", None)

    def _restore_maxfev_overlay_backup(self):
        self.master_app.fit_overlay = getattr(self, "_maxfev_overlay_backup", None)
        self.master_app.redraw(preserve_view=True)
        self._clear_maxfev_overlay_backup()

    def _clear_maxfev_overlay_backup(self):
        if hasattr(self, "_maxfev_overlay_backup"):
            delattr(self, "_maxfev_overlay_backup")

    def _retry_voigt_fit_after_maxfev(self, fit_lines, result):
        best_free = result.get("best_free")
        initial_free = result.get("initial_free")
        next_limit = int(result.get("max_nfev") or 0) + 2000
        if best_free is not None:
            return self._fit_manual_group(fit_lines, max_nfev=next_limit, initial_free=best_free)
        return self._fit_manual_group(fit_lines, max_nfev=next_limit, initial_free=initial_free)

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
        if self._independent_window_conflict(group):
            message = (
                "This line group spans multiple detector windows. Independent-window mode "
                "does not join their samples; fit the lines in separate regions."
            )
            self.msg_var.set(message)
            self.master_app.status(message)
            return False, message, message, 0
        min_points = self._minimum_fit_points(group, line_overrides=self._line_overrides_from_editor(group, apply_to_template=False))
        point_count = self._current_fit_point_count()
        if point_count < min_points:
            point_count, expanded, retries = self._expand_manual_window_to_points(group, min_points)
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
                message = "No selected analytical lines are visible in the current Manual Fit window."
                self.manual_fit_failed = True
                self.msg_var.set(f"{report}; {message}")
                _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}")
                return False
            fit_lines = list(group)
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
        expanded_for_visible = False
        if point_count < min_points:
            point_count, expanded_for_visible, retries = self._expand_manual_window_to_points(fit_lines, min_points)
            if point_count < min_points:
                message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
                self.manual_fit_failed = True
                self.msg_var.set(f"{report}; {message}")
                _showerror(self, mode_label, f"{message}\nRegion: {first:.4f} - {last:.4f}\nExpansion retries: {retries}")
                return False
            fit_lines = self._visible_template_lines() or list(fit_lines)
            min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
            report = f"{mode_label}: expanded window, fitting {len(fit_lines)} line(s) using {point_count} points"
            self.msg_var.set(report)
            self.master_app.status(report)
        elif len(fit_lines) != len(group):
            report = f"{mode_label}: fitting {len(fit_lines)} visible line(s) using {point_count} points"
            self.msg_var.set(report)
            self.master_app.status(report)
        result = self._fit_manual_group(fit_lines)
        while result.get("status") == "maxfev":
            self._ensure_maxfev_overlay_backup()
            preview_drawn = self._preview_voigt_fit_overlay(result)
            can_accept = bool(result.get("payload")) and bool(result.get("best_free")) and preview_drawn
            choice = self._fit_maxfev_dialog(
                "The fit stopped because the maximum number of function evaluations was reached.\n\n"
                "Continue fit increases the limit by 2000 and retries from the best parameters found so far.",
                can_accept=can_accept,
            )
            if choice == "continue":
                result = self._retry_voigt_fit_after_maxfev(fit_lines, result)
                continue
            if choice == "accept" and can_accept:
                results = self._apply_voigt_fit_result(fit_lines, result, mode_label)
                self.region_fit_results[self._group_key(group)] = list(results)
                self.region_fit_results[self._group_key(fit_lines)] = list(results)
                self.populate_results(results)
                self.msg_var.set(f"{report}; fitted")
                self.master_app.status(f"{report}; fitted")
                self.update_idletasks()
                self._clear_maxfev_overlay_backup()
                return True
            self._restore_maxfev_overlay_backup()
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; Fit canceled")
            return False
        ok = result.get("status") == "success"
        message = result.get("message", "")
        results = self._apply_voigt_fit_payload(fit_lines, result.get("payload") or {}, mode_label) if ok else []
        if not ok:
            if result.get("status") == "maxfev":
                self.manual_fit_failed = True
                self.msg_var.set(f"{report}; Fit stopped by maximum evaluations")
                self._clear_maxfev_overlay_backup()
                return False
            self.manual_fit_failed = True
            self.msg_var.set(f"{report}; Fit failed: {message}")
            _showerror(self, mode_label, f"Fit failed for {first:.4f} - {last:.4f}:\n{message}")
            self._clear_maxfev_overlay_backup()
            return False
        self.region_fit_results[self._group_key(group)] = list(results)
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{report}; fitted")
        self.master_app.status(f"{report}; fitted")
        self.update_idletasks()
        self._clear_maxfev_overlay_backup()
        return True

    def run_gaussian_fit(self):
        """Run Palleschi's Gaussian model on the current manual-fit ROI."""
        if self._fit_running:
            self.msg_var.set("A fit is already running")
            return
        if not self.master_app.spectra:
            _showinfo(self, "Fit Gaussian", "Load a spectrum first.")
            return
        fit_lines = self._visible_template_lines()
        self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
        if not fit_lines:
            message = "No selected analytical lines are visible in the current spectrum window."
            self.msg_var.set(message)
            _showinfo(self, "Fit Gaussian", message)
            return
        min_points = 2 + 3 * len(fit_lines)
        point_count = self._current_fit_point_count()
        if point_count < min_points:
            point_count, _expanded, retries = self._expand_manual_window_to_points(
                fit_lines,
                min_points,
            )
            fit_lines = self._visible_template_lines() or fit_lines
            self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
            if point_count < min_points:
                message = (
                    f"Too few spectrum points for Gaussian fit: {point_count} found, "
                    f"{min_points} required (expansion retries: {retries})."
                )
                self.msg_var.set(message)
                _showerror(self, "Fit Gaussian", message)
                return
        overrides = self._line_overrides_from_editor(
            fit_lines,
            apply_to_template=False,
        )
        temporary = None
        try:
            temporary = MultiGaussianFitWindow(self.master_app)
            temporary.withdraw()
            ok, message, results = temporary.fit_gaussian_lines(
                lines=fit_lines,
                preserve_view=True,
                show_messages=False,
                line_overrides=overrides,
            )
        except Exception as exc:
            ok, message, results = False, str(exc), []
        finally:
            try:
                if temporary is not None:
                    temporary.destroy()
            except Exception:
                pass
        if not ok:
            self.msg_var.set(f"Gaussian fit failed: {message}")
            _showerror(self, "Fit Gaussian", message)
            return
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.residual_x = []
        self.residual_y = []
        self.msg_var.set(
            f"Gaussian fit: {len(results)} line(s); "
            "area = A*sigma*sqrt(pi)"
        )
        self.master_app.status(self.msg_var.get())

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
                    self.msg_var.set("No observed peaks are selected")
                    _showinfo(
                        self,
                        "Auto Fit",
                        "Select peaks with 'Find visible peaks' or 'Add peak from graph'. "
                        "An external template file is not required.",
                    )
                    return
            self._run_automatic_fit()
            return

        def _manual_done(ok, _fit_lines, _message, stopped=False, fit_result=None):
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
            self.msg_var.set("Manual Fit: no selected analytical lines are visible in the current window")
            _showinfo(self, "Manual Fit", "No selected analytical lines are visible in the current spectrum window.")
            return
        self._set_visible_fit_lines(visible_lines, preserve_user_values=True)
        self.displayed_lines = list(visible_lines)
        self.displayed_group_key = self._group_key(visible_lines)
        self.manual_fit_index = 0
        lo, hi = sorted(self.master_app.ax.get_xlim()) if getattr(self.master_app, "ax", None) else (0.0, 0.0)
        self.msg_var.set(f"Manual Fit refreshed: {len(visible_lines)} visible line(s) in {lo:.4f} - {hi:.4f}")
        self.master_app.status(self.msg_var.get())

    def _fit_current_visible_window(self, mode_label, allow_previous_visible_fallback=True, show_errors=True):
        fit_lines = self._visible_template_lines()
        self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
        if not fit_lines:
            self.msg_var.set(f"{mode_label}: no selected analytical lines are visible in the current window")
            if show_errors:
                _showinfo(self, mode_label, "No selected analytical lines are visible in the current spectrum window.")
            return False, []
        point_count = self._current_fit_point_count()
        min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
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
                    message = "No selected analytical lines are visible in the current Manual Fit window."
                    self.msg_var.set(f"{report}; {message}")
                    if show_errors:
                        _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}")
                    return False, []
                self._set_visible_fit_lines(fit_lines, preserve_user_values=True)
                min_points = self._minimum_fit_points(fit_lines, line_overrides=self._line_overrides_from_editor(fit_lines, apply_to_template=False))
                report = f"{mode_label}: expanded window, fitting {len(fit_lines)} visible line(s) using {point_count} points"
                self.msg_var.set(report)
                self.master_app.status(report)
            if point_count < min_points:
                message = f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required."
                self.msg_var.set(f"{report}; {message}")
                if show_errors:
                    _showerror(self, mode_label, f"{message}\nCurrent window: {lo:.4f} - {hi:.4f}\nExpansion retries: {retries}")
                return False, fit_lines
        result = self._fit_manual_group(fit_lines)
        retries = 0
        while result.get("status") == "maxfev":
            self._ensure_maxfev_overlay_backup()
            preview_drawn = self._preview_voigt_fit_overlay(result)
            can_accept = bool(result.get("payload")) and bool(result.get("best_free")) and preview_drawn
            choice = self._fit_maxfev_dialog(
                "The fit stopped because the maximum number of function evaluations was reached.\n\n"
                "Continue fit increases the limit by 2000 and retries from the best parameters found so far.",
                can_accept=can_accept,
            )
            if choice == "continue":
                result = self._retry_voigt_fit_after_maxfev(fit_lines, result)
                continue
            if choice == "accept" and can_accept:
                results = self._apply_voigt_fit_result(fit_lines, result, mode_label)
                self.region_fit_results[self._group_key(fit_lines)] = list(results)
                self.populate_results(results)
                self.msg_var.set(f"{report}; fitted")
                self.master_app.status(f"{report}; fitted")
                return True, fit_lines
            self._restore_maxfev_overlay_backup()
            self.msg_var.set(f"{report}; Fit canceled")
            return False, fit_lines
        ok = result.get("status") == "success"
        message = result.get("message", "")
        results = self._apply_voigt_fit_payload(fit_lines, result.get("payload") or {}, mode_label) if ok else []
        if not ok:
            if result.get("status") == "maxfev":
                self.msg_var.set(f"{report}; Fit stopped by maximum evaluations")
                if show_errors:
                    _showerror(self, mode_label, f"Fit stopped by maximum evaluations for current window {lo:.4f} - {hi:.4f}.")
                elif callback:
                    callback(False, fit_lines, message, stopped=False, fit_result=result)
                self._clear_maxfev_overlay_backup()
                return False, fit_lines
            self.msg_var.set(f"{report}; Fit failed: {message}")
            if show_errors:
                _showerror(self, mode_label, f"Fit failed for current window {lo:.4f} - {hi:.4f}:\n{message}")
            elif callback:
                callback(False, fit_lines, message, stopped=False, fit_result=result)
            self._clear_maxfev_overlay_backup()
            return False, fit_lines
        self.region_fit_results[self._group_key(fit_lines)] = list(results)
        self.populate_results(results)
        self.msg_var.set(f"{report}; fitted")
        self.master_app.status(f"{report}; fitted")
        self._clear_maxfev_overlay_backup()
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

        def _auto_done(ok, fit_lines, _message, stopped=False, fit_result=None):
            if stopped or self.manual_fit_stop or self.fit_stop_requested:
                self.msg_var.set("Automatic Fit stopped")
                self.master_app.status("Automatic Fit stopped")
                return
            if fit_result and fit_result.get("status") == "maxfev":
                retry_count = getattr(self, "_auto_maxfev_retry_count", 0)
                if retry_count < 1:
                    self._auto_maxfev_retry_count = retry_count + 1
                    next_limit = int(fit_result.get("max_nfev") or 0) + 2000
                    best_free = fit_result.get("best_free") or fit_result.get("initial_free")
                    self.after(0, lambda: self._start_visible_fit_async(
                        "Automatic Fit",
                        allow_previous_visible_fallback=False,
                        show_errors=False,
                        callback=_auto_done,
                        reset_stop=False,
                        max_nfev=next_limit,
                        initial_free=best_free,
                    ))
                    return
                current_lines = fit_lines or self._visible_template_lines()
                self._mark_fit_error(current_lines)
                self.msg_var.set(f"Automatic Fit: ERROR marked for {len(current_lines)} line(s)")
            elif not ok:
                current_lines = fit_lines or self._visible_template_lines()
                self._mark_fit_error(current_lines)
                self.msg_var.set(f"Automatic Fit: ERROR marked for {len(current_lines)} line(s)")
            self._auto_maxfev_retry_count = 0
            self.progress["value"] = self._manual_visible_progress()
            if not self._move_manual_region("next", preserve_user_values=True):
                self.progress["value"] = 100
                self.msg_var.set("Automatic Fit completed.")
                payload = (fit_result or {}).get("payload") or {}
                display_xlim = payload.get("display_xlim")
                if display_xlim and getattr(self.master_app, "ax", None):
                    self.master_app.ax.set_xlim(display_xlim)
                    self.master_app.full_y_main_visible_x()
                    self.master_app.canvas.draw_idle()
                    self.master_app._update_xscroll()
                _showinfo(self, "Automatic Fit", "Automatic Fit completed.")
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
        self._auto_maxfev_retry_count = 0
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
            replicate_total = safe_int(row.get("replicate_area_total"), 0)
            replicate_cv = safe_float(row.get("replicate_area_cv"), math.nan)
            if replicate_total >= 2:
                cv_text = (
                    f"{replicate_cv:.1%}"
                    if math.isfinite(replicate_cv)
                    else "N/A"
                )
            else:
                cv_text = "Mean only"
            self.results.insert("", "end", values=(
                row.get("line_label") or f"Line {i}",
                row.get("source_window", ""),
                format_template_display_value(row.get("fit_center", "")),
                format_template_display_value(row.get("peak_intensity", "")),
                format_template_display_value(row.get("lorentzian_width", "")),
                format_template_display_value(row.get("gaussian_width", "")),
                format_scientific_display_value(row.get("integrated_area", "")),
                cv_text,
                row.get("status", "Voigt OK"),
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
        _configure_tk_scaling(self)
        self.withdraw()
        self._startup_splash = show_startup_splash(self, SPLASH_DURATION_MS)
        configure_retro_style(self)
        self.options=AppOptions()
        self.loaded_ini_path = load_pylibs_ini(self.options)
        self.pending_scientific_settings_applied = False
        try:
            if apply_pending_scientific_settings(self.options):
                self.loaded_ini_path = resource_path("pyLIBS.ini")
                self.pending_scientific_settings_applied = True
        except Exception as exc:
            logging.warning(
                "Could not apply pending scientific settings: %s",
                exc,
                exc_info=True,
            )
        self.use_saved_window_positions = False
        self.title(APP_TITLE); self.geometry("1280x720")
        self.libs_db=LibsDatabase(self.options.libs_db_file)
        self.spectra: list[Spectrum]=[]
        # False keeps the historical Append behaviour. True means that every
        # loaded detector window remains an independent analytical spectrum.
        self.independent_window_mode = False
        self._replicate_spectrum_cache: dict[tuple, list[dict]] = {}
        self.response_library = InstrumentResponseLibrary()
        self.response = None
        self.active_opc_path = ""
        self.active_opc_id = ""
        self.active_opc_metadata: dict[str, object] = {}
        self.load_configured_responses(silent=True)
        try:
            (
                self.analytical_line_library,
                self.analytical_line_library_path,
            ) = load_or_create_analytical_line_library()
        except Exception as exc:
            logging.warning(
                "Could not load the persistent analytical-line library: %s",
                exc,
                exc_info=True,
            )
            self.analytical_line_library = []
            self.analytical_line_library_path = (
                app_base_dir() / ANALYTICAL_LINE_LIBRARY_FILENAME
            )
        self.template_lines: list[TemplateLine] = _clone_template_lines(
            self.analytical_line_library
        )
        self.atomic_lines: list[AtomicLine]=[]
        self.element_markers: list[AtomicLine]=[]
        self.trace_markers: list[AtomicLine]=[]
        # This is the authoritative element set for Saha, IRSAC and CF-LIBS.
        # Identified template rows from other experiments are never admitted
        # unless the element is explicitly requested in Trace Lines.
        self.analysis_elements: set[str] = set()
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
        self.fit_baseline_overlay: Optional[
            tuple[list[float], list[float]]
        ] = None
        self.fit_component_overlays: list[
            tuple[list[float], list[float]]
        ] = []
        self.fit_integration_bounds: list[tuple[float, float]] = []
        self.fit_overlay_label = "Voigt sum"
        self.fit_component_label = "Voigt"
        # Manual Voigt ROIs describe the current spectrum, not a permanent
        # instrumental setting. Legacy persisted ranges remain available to
        # the fit manager, but IRSAC trusts only ROIs selected this session.
        self.session_voigt_fit_range_keys: set[str] = set()
        self.last_cflibs_rows: list[dict] = []
        self.last_halpha_result: Optional[dict] = None
        self.last_saha_boltzmann: Optional[dict] = None
        self.last_cflibs_quality: Optional[dict] = None
        self.last_cflibs_robustness: Optional[dict] = None
        self.last_self_absorption_result: Optional[dict] = None
        self.last_theoretical_spectrum: Optional[dict] = None
        self.apply_sac_correction = False
        self.post_irsac_temperature: Optional[float] = None
        self.post_irsac_temperature_source: Optional[str] = None
        self.standard_refs: dict[str, str] = {}
        self.opc_nominal_percent: dict[str, float] = {}
        self.opc_nominal_basis = OPC_MASS_PERCENT_BASIS
        self.opc_nominal_inputs: dict[str, dict[str, float]] = {
            OPC_MASS_PERCENT_BASIS: {},
            OPC_NUMBER_PERCENT_BASIS: {},
        }
        self.session_ne: Optional[float] = None
        self.session_ne_source: Optional[str] = None
        self.last_known_ne: Optional[float] = None
        self.last_known_ne_source: Optional[str] = None
        self.session_temperature: Optional[float] = None
        self.session_temperature_source: Optional[str] = None
        self.wavelength_unit = "angstrom"
        self.template_window=None; self.line_window=None; self.response_window=None; self.active_window=None; self.options_window=None
        self.template_window_geometry = ""
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
        self.theoretical_window = None
        self.statistics_window = None
        self.about_window = None
        self.goto_window = None
        self.shift_capture_window=None
        self.fit_peak_capture_window=None
        self.fit_roi_capture_window=None
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
        f=tk.Menu(m,tearoff=False); f.add_command(label="Open",command=self.open_spectrum); f.add_command(label="Append/import",command=self.append_spectrum); f.add_command(label="Load independent windows",command=self.load_independent_windows); f.add_command(label="Save main",command=self.save_spectrum); f.add_separator(); f.add_command(label="Exit",command=self.on_close); m.add_cascade(label="File",menu=f)
        e=tk.Menu(m,tearoff=False); e.add_command(label="Options",command=self.show_options); m.add_cascade(label="Edit",menu=e)
        u=tk.Menu(m,tearoff=False); u.add_command(label="Instrument response",command=self.show_response_window); u.add_command(label="Apply instrument response now",command=self.apply_response_now); u.add_separator(); u.add_command(label="Vertical shift",command=lambda:VerticalShiftWindow(self)); u.add_command(label="Smooth main",command=self.smooth_main); u.add_command(label="nm → Å main",command=self.nm_to_a_main); m.add_cascade(label="Utilities",menu=u)
        t=tk.Menu(m,tearoff=False); t.add_command(label="Template Manager",command=self.show_template); t.add_command(label="Line Identification",command=self.show_line_identification); t.add_command(label="Element Locator",command=lambda:ElementLocatorWindow(self)); t.add_command(label="Auto Element Identification",command=lambda:AutoElementIdentificationWindow(self)); m.add_cascade(label="Template",menu=t)
        a=tk.Menu(m,tearoff=False); a.add_command(label="Active Spectra",command=self.show_active_spectra); a.add_command(label="Trace Lines",command=self.show_trace_lines); a.add_command(label="Batch / Statistics",command=lambda:BatchStatisticsWindow(self)); a.add_command(label="Gaussian / Voigt Fit",command=self.show_fit); a.add_command(label="Manual Fit",command=self.show_retro_fit_manager); a.add_command(label="Auto Fit",command=self.show_auto_fit_manager); a.add_command(label="Ne from H-alpha",command=self.show_ne_halpha); a.add_command(label="SAC factors",command=self.show_sac); a.add_command(label="Saha-Boltzmann",command=self.show_saha); a.add_command(label="CF-LIBS",command=self.show_cflibs); a.add_command(label="Theoretical spectrum (after SA assessment)",command=self.show_theoretical_spectrum); a.add_command(label="Standard correction / OPC",command=self.show_standard_correction); m.add_cascade(label="Analyse",menu=a)
        h=tk.Menu(m,tearoff=False)
        manual_menu=tk.Menu(h,tearoff=False)
        manual_menu.add_command(label="Italiano",command=lambda:self.show_manual("it"))
        manual_menu.add_command(label="English",command=lambda:self.show_manual("en"))
        h.add_cascade(label="Manual",menu=manual_menu)
        h.add_separator()
        h.add_command(label="About pyLIBS...",command=self.show_about)
        m.add_cascade(label="Help",menu=h)
        self.config(menu=m)

    def _toolbar(self):
        tb=ttk.Frame(self); tb.pack(fill="x", padx=4, pady=3)
        for label,cmd in [("Open",self.open_spectrum),("Append",self.append_spectrum),("Active Spectra",self.show_active_spectra),("Options",self.show_options),("Response",self.show_response_window),("Template",self.show_template),("Identify",self.show_line_identification),("Trace",self.show_trace_lines),("Element",lambda:ElementLocatorWindow(self)),("Auto ID",lambda:AutoElementIdentificationWindow(self)),("Batch",lambda:BatchStatisticsWindow(self)),("Shift",lambda:VerticalShiftWindow(self)),("Fit",self.show_fit),("Ne Hα",self.show_ne_halpha),("SAC",self.show_sac),("Saha",self.show_saha),("CF-LIBS",self.show_cflibs),("STD",self.show_standard_correction)]:
            ttk.Button(tb,text=label,command=cmd).pack(side="left",padx=2)

    def _plot(self):
        self.plot_frame=ttk.Frame(self); self.plot_frame.pack(fill="both", expand=True)
        if Figure is None:
            ttk.Label(self.plot_frame,text="Matplotlib is not available.").pack(pady=30)
            self.ax=self.canvas=None; return
        self.fig=Figure(figsize=(8,5),dpi=_figure_dpi(self)); self.ax=self.fig.add_subplot(111)
        self.canvas=FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        # Navigation state: left drag zoom, right drag pan.
        self._nav_press = None
        self._nav_dragged = False
        self._zoom_rectangle = None
        self._xscroll_updating = False
        self.canvas.mpl_connect("motion_notify_event", self._mouse)
        self.canvas.mpl_connect("button_press_event", self._click)
        self.canvas.mpl_connect("button_release_event", self._release)
        self.canvas.mpl_connect("scroll_event", self._scroll_zoom)
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
        spectra = list(getattr(self, "spectra", []) or [])
        if spectra and all(getattr(spectrum, "response_corrected", False) for spectrum in spectra):
            label = "Response-corrected intensity"
        elif spectra and any(getattr(spectrum, "dark_corrected", False) for spectrum in spectra):
            label = "Dark-corrected intensity (counts)"
        else:
            label = "Intensity (counts)"
        self.ax.set_ylabel(label)

    def add_spectrum(self, sp):
        assign_default_spectrum_color(sp, len(self.spectra))
        self.spectra.append(sp)
        self.wavelength_unit = self.infer_wavelength_unit()
        self.redraw(); self.status(f"Added spectrum: {sp.name}")
        if self.active_window and self.active_window.winfo_exists(): self.active_window.refresh()

    def configured_response_paths(self):
        return parse_response_paths(
            getattr(self.options, "response_files", "")
            or getattr(self.options, "response_file", "")
        )

    def load_configured_responses(self, silent=False):
        paths = self.configured_response_paths()
        if not paths:
            self.response_library = InstrumentResponseLibrary()
            self.response = None
            self.active_opc_path = ""
            self.active_opc_id = ""
            self.active_opc_metadata = {}
            return False
        missing = [path for path in paths if not Path(path).exists()]
        if missing:
            self.response_library = InstrumentResponseLibrary()
            self.response = None
            self.active_opc_path = ""
            self.active_opc_id = ""
            self.active_opc_metadata = {}
            if not silent:
                _showwarning(self, "Response", "Response file(s) not found:\n" + "\n".join(missing))
            return False
        kind = _response_paths_kind(paths)
        if kind == "mixed" or (kind == "opc" and len(paths) != 1):
            self.response_library = InstrumentResponseLibrary()
            self.response = None
            self.active_opc_path = ""
            self.active_opc_id = ""
            self.active_opc_metadata = {}
            if not silent:
                message = (
                    "Do not mix OPC and physical instrumental-response files."
                    if kind == "mixed"
                    else "Select one OPC calibration file at a time."
                )
                _showwarning(self, "Response", message)
            return False
        if kind == "opc":
            self.options.apply_response = True
            self.options.apply_before = False
            self.options.apply_after = True
        try:
            library = InstrumentResponseLibrary.from_files(
                paths,
                False if kind == "opc" else self.options.convert_to_angstrom,
                getattr(self.options, "lsf_widths", "{}"),
            )
            self.response_library = library
            self.response = library.curves[0] if library.curves else None
            if kind == "opc":
                self.active_opc_path = paths[0]
                self.active_opc_id = opc_calibration_id(paths[0])
                self.active_opc_metadata = read_opc_metadata(paths[0])
            else:
                self.active_opc_path = ""
                self.active_opc_id = ""
                self.active_opc_metadata = {}
            response_window = getattr(self, "response_window", None)
            if response_window and response_window.winfo_exists():
                response_window.redraw()
            return bool(library.curves)
        except Exception as exc:
            self.response_library = InstrumentResponseLibrary()
            self.response = None
            self.active_opc_path = ""
            self.active_opc_id = ""
            self.active_opc_metadata = {}
            if not silent:
                _showwarning(self, "Response", f"Could not load instrumental response:\n\n{exc}")
            return False

    def load_configured_response(self, silent=False):
        """Compatibility wrapper for older pyLIBS call sites."""
        return self.load_configured_responses(silent=silent)

    def _raw_spectrum_copy(self, spectrum):
        sources = spectrum.source_windows or (
            SpectrumSourceWindow(
                tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename,
                spectrum.dark_corrected, spectrum.dark_source, spectrum.signal_column, spectrum.dark_columns,
                replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
            ),
        )
        rebuilt = None
        for source in sources:
            piece = Spectrum(
                list(source.x), list(source.y), name=source.name, filename=source.filename,
                dark_corrected=source.dark_corrected,
                dark_source=source.dark_source,
                signal_column=source.signal_column,
                dark_columns=source.dark_columns,
                replicate_files=tuple(getattr(source, "replicate_files", ()) or ()),
                source_windows=(source,),
            )
            rebuilt = piece if rebuilt is None else merge_spectra_by_wavelength(
                rebuilt, piece, name=spectrum.name
            )
        rebuilt.name = spectrum.name
        rebuilt.filename = spectrum.filename
        rebuilt.color = spectrum.color
        rebuilt.visible = spectrum.visible
        rebuilt.source_windows = sources
        return rebuilt

    def restore_raw_spectra_for_apply_after(self):
        """Undo an earlier Apply Before operation using preserved source windows."""
        corrected = [
            spectrum for spectrum in self.spectra
            if bool(getattr(spectrum, "response_corrected", False))
        ]
        if not corrected:
            return 0, 0
        restored = []
        for spectrum in self.spectra:
            if bool(getattr(spectrum, "response_corrected", False)):
                restored.append(MainWindow._raw_spectrum_copy(self, spectrum))
            else:
                restored.append(spectrum)
        self.spectra = restored
        cleared = _clear_template_fit_measurements(self.template_lines)
        self.clear_fit_artists()
        invalidate_self_absorption_analysis(self)
        self.invalidate_cflibs_results()
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.refresh()
        if self.response_window and self.response_window.winfo_exists():
            self.response_window.redraw()
        self.status(
            f"Apply After: restored {len(corrected)} raw spectrum/spectra; "
            f"cleared {cleared} fit measurement(s)"
        )
        return len(corrected), cleared

    def sync_response_application_mode(self, notify=False):
        """Make loaded spectra agree with the selected correction domain."""
        if not bool(getattr(self.options, "apply_response", False)):
            return "disabled"
        if not list(getattr(self.response_library, "curves", []) or []):
            return "no-response"
        if bool(getattr(self.options, "apply_after", False)):
            restored, cleared = MainWindow.restore_raw_spectra_for_apply_after(self)
            if restored and notify:
                _showinfo(
                    self,
                    "Apply After",
                    f"Restored {restored} spectrum/spectra from their raw source data. "
                    f"Cleared {cleared} previous fit measurement(s), because they belonged to "
                    "Apply Before. Fit the analytical lines again before generating OPC.",
                )
            return "restored" if restored else "after"
        if bool(getattr(self.options, "apply_before", False)):
            if any(
                not bool(getattr(spectrum, "response_corrected", False))
                for spectrum in self.spectra
            ):
                return "corrected" if MainWindow.apply_response_now(self) else "error"
            return "before"
        return "disabled"

    def _response_corrected_copy(self, spectrum):
        if not self.response_library.curves:
            raise ValueError("No instrumental-response curves are loaded.")
        sources = spectrum.source_windows or (
            SpectrumSourceWindow(
                tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename,
                spectrum.dark_corrected, spectrum.dark_source, spectrum.signal_column, spectrum.dark_columns,
                replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
            ),
        )
        assignments = self.response_library.assign_windows(
            [(source.name, _source_raw_axis(source)) for source in sources]
        )
        corrected = None
        for source_index, source in enumerate(sources):
            curve = assignments.get(source_index)
            if curve is None:
                raw_axis = _source_raw_axis(source)
                low, high = min(raw_axis), max(raw_axis)
                raise ValueError(
                    f"No response curve matches {source.name} ({low:.3f}-{high:.3f})."
                )
            raw_axis = _source_raw_axis(source)
            piece = Spectrum(
                list(raw_axis), list(source.y), name=source.name, filename=source.filename,
                dark_corrected=source.dark_corrected,
                dark_source=source.dark_source,
                signal_column=source.signal_column,
                dark_columns=source.dark_columns,
                replicate_files=tuple(getattr(source, "replicate_files", ()) or ()),
                source_windows=(source,),
            )
            piece.apply_response(curve)
            intercept = safe_float(getattr(source, "calibration_intercept", 0.0), 0.0)
            slope = safe_float(getattr(source, "calibration_slope", 1.0), 1.0)
            piece.x = [intercept + slope * x for x in piece.x]
            corrected = piece if corrected is None else merge_spectra_by_wavelength(
                corrected, piece, name=spectrum.name
            )
        corrected.name = spectrum.name
        corrected.filename = spectrum.filename
        corrected.color = spectrum.color
        corrected.source_windows = sources
        return corrected

    def load_spectrum_with_corrections(self, filename):
        sp = load_spectrum_for_open(filename, self.options)
        self.apply_auto_offset_if_enabled(sp)
        sp.capture_source()
        if self.options.apply_response and self.options.apply_before:
            sp = self._response_corrected_copy(sp)
        self.apply_wavelength_calibration_if_enabled(sp)
        return sp

    def replicate_spectrum_snapshots(self, source, *, response_corrected=False):
        """Load and preprocess replicate traces exactly like their mean window."""
        files = tuple(getattr(source, "replicate_files", ()) or ())
        if len(files) < 2:
            return []
        mtimes = []
        for filename in files:
            try:
                mtimes.append(Path(filename).stat().st_mtime_ns)
            except OSError:
                return []
        key = (
            files,
            tuple(mtimes),
            bool(response_corrected),
            str(getattr(self.options, "dark_mode", "")),
            safe_int(getattr(self.options, "signal_column", 0), 0),
            str(getattr(self.options, "dark_columns", "")),
            safe_float(getattr(self.options, "dark_constant", 0.0), 0.0),
            str(getattr(self.options, "dark_file", "")),
            tuple(parse_response_paths(getattr(self.options, "response_files", ""))),
            safe_float(getattr(source, "calibration_intercept", 0.0), 0.0),
            safe_float(getattr(source, "calibration_slope", 1.0), 1.0),
        )
        cached = self._replicate_spectrum_cache.get(key)
        if cached is not None:
            return [dict(item) for item in cached]
        snapshots = []
        try:
            for filename in files:
                spectrum = load_spectrum_for_open(filename, self.options)
                self.apply_auto_offset_if_enabled(spectrum)
                spectrum.capture_source()
                if response_corrected:
                    spectrum = self._response_corrected_copy(spectrum)
                intercept = safe_float(
                    getattr(source, "calibration_intercept", 0.0),
                    0.0,
                )
                slope = safe_float(
                    getattr(source, "calibration_slope", 1.0),
                    1.0,
                )
                spectrum.x = [intercept + slope * value for value in spectrum.x]
                snapshots.append({
                    "x": list(spectrum.x),
                    "y": list(spectrum.y),
                    "name": Path(filename).name,
                    "filename": str(filename),
                })
        except Exception as exc:
            logging.warning(
                "Could not preprocess replicate spectra for %s: %s",
                getattr(source, "name", "window"),
                exc,
                exc_info=True,
            )
            return []
        self._replicate_spectrum_cache[key] = [dict(item) for item in snapshots]
        return snapshots

    def load_halpha_spectrum_for_ne(self, filename):
        """Load an H-alpha width trace without requiring radiometric response."""
        sp = load_spectrum_for_open(filename, self.options)
        self.apply_auto_offset_if_enabled(sp)
        sp.capture_source()
        self.apply_wavelength_calibration_if_enabled(sp)
        sp.halpha_width_only = True
        sp.halpha_response_bypassed = bool(
            self.options.apply_response and self.options.apply_before
        )
        return sp

    def _replace_analysis_lines_from_library(
        self,
        *,
        redraw=True,
        preserve_analysis_elements=False,
    ):
        selected_elements = set(getattr(self, "analysis_elements", set()) or set())
        self.template_lines = _clone_template_lines(
            getattr(self, "analytical_line_library", []) or []
        )
        self.analysis_elements = (
            selected_elements if preserve_analysis_elements else set()
        )
        self.element_markers = []
        self.trace_markers = []
        self.notify_template_changed(redraw=redraw)

    def reload_analytical_line_library(self):
        try:
            lines, path = load_or_create_analytical_line_library()
        except Exception as exc:
            _showerror(self, "Analytical line library", str(exc))
            return False
        self.analytical_line_library = lines
        self.analytical_line_library_path = path
        self._replace_analysis_lines_from_library(redraw=True)
        self.status(f"Main analytical line library loaded: {len(lines)} lines")
        return True

    def add_secondary_analytical_line_list(self):
        filename = _template_file_dialog(
            self,
            filedialog.askopenfilename,
            title="Add a secondary list to the main analytical library",
            initialdir=remembered_initial_dir(self.options),
            filetypes=[("Line lists", "*.txt *.csv"), ("All", "*.*")],
        )
        if not filename:
            return False
        remember_working_dir(self.options, filename)
        try:
            additions = load_template_lines(filename, RetroTemplateManager.columns)
            merged, added, skipped = merge_analytical_line_libraries(
                self.analytical_line_library,
                additions,
            )
            if added <= 0:
                message = "No new assigned analytical lines were found."
                if skipped:
                    message += f"\n{skipped} row(s) lacked element, ion stage or wavelength."
                _showinfo(self, "Analytical line library", message)
                return False
            save_analytical_line_library(self.analytical_line_library_path, merged)
        except Exception as exc:
            _showerror(self, "Analytical line library", str(exc))
            return False
        existing_keys = {
            analytical_line_library_key(line)
            for line in self.template_lines
            if analytical_line_library_key(line) is not None
        }
        for line in merged:
            key = analytical_line_library_key(line)
            if key not in existing_keys:
                self.template_lines.append(_clone_template_line(line))
                existing_keys.add(key)
        self.analytical_line_library = merged
        self.notify_template_changed(redraw=True)
        message = (
            f"Added {added} line(s) to the persistent main library "
            f"({len(merged)} total)."
        )
        if skipped:
            message += f" Skipped {skipped} incomplete row(s)."
        self.status(message)
        _showinfo(self, "Analytical line library", message)
        return True

    def replace_analytical_line_library(self):
        filename = _template_file_dialog(
            self,
            filedialog.askopenfilename,
            title="Replace the main analytical line library",
            initialdir=remembered_initial_dir(self.options),
            filetypes=[("Line lists", "*.txt *.csv"), ("All", "*.*")],
        )
        if not filename:
            return False
        remember_working_dir(self.options, filename)
        if not _askyesno(
            self,
            "Replace analytical line library",
            "Replace the persistent main library and the current analytical workspace?",
        ):
            return False
        try:
            loaded = load_template_lines(filename, RetroTemplateManager.columns)
            clean_lines, _added, skipped = merge_analytical_line_libraries([], loaded)
            if not clean_lines:
                raise ValueError(
                    "The selected file contains no lines with element, ion stage and wavelength."
                )
            save_analytical_line_library(
                self.analytical_line_library_path,
                clean_lines,
            )
        except Exception as exc:
            _showerror(self, "Analytical line library", str(exc))
            return False
        self.analytical_line_library = clean_lines
        self._replace_analysis_lines_from_library(redraw=True)
        message = f"Main analytical line library replaced: {len(clean_lines)} lines."
        if skipped:
            message += f" Skipped {skipped} incomplete row(s)."
        self.status(message)
        return True

    def save_current_lines_to_analytical_library(self):
        clean_lines, _added, skipped = merge_analytical_line_libraries(
            [],
            self.template_lines,
        )
        if not clean_lines:
            _showinfo(
                self,
                "Analytical line library",
                "The current workspace has no assigned lines to save.",
            )
            return False
        if not _askyesno(
            self,
            "Save main analytical line library",
            (
                f"Save the {len(clean_lines)} assigned current lines as the persistent "
                "main library?\n\nFit results and measured intensities are not stored."
            ),
        ):
            return False
        try:
            save_analytical_line_library(
                self.analytical_line_library_path,
                clean_lines,
            )
        except Exception as exc:
            _showerror(self, "Analytical line library", str(exc))
            return False
        self.analytical_line_library = clean_lines
        message = f"Persistent main analytical library saved: {len(clean_lines)} lines."
        if skipped:
            message += f" Skipped {skipped} incomplete row(s)."
        self.status(message)
        return True

    def restore_default_analytical_line_library(self):
        if not _askyesno(
            self,
            "Restore included analytical lines",
            "Restore the analytical line library included with pyLIBS?",
        ):
            return False
        default_path = app_base_dir() / DEFAULT_ANALYTICAL_LINE_LIBRARY_FILENAME
        try:
            loaded = load_template_lines(default_path, RetroTemplateManager.columns)
            clean_lines, _added, _skipped = merge_analytical_line_libraries([], loaded)
            if not clean_lines:
                raise ValueError("The included analytical line library is unavailable.")
            save_analytical_line_library(
                self.analytical_line_library_path,
                clean_lines,
            )
        except Exception as exc:
            _showerror(self, "Analytical line library", str(exc))
            return False
        self.analytical_line_library = clean_lines
        self._replace_analysis_lines_from_library(redraw=True)
        self.status(f"Included analytical line library restored: {len(clean_lines)} lines")
        return True

    def _offer_halpha_ne_import(self, filename, error):
        if "No response curve matches" not in str(error):
            return False
        try:
            probe = load_spectrum_for_open(filename, self.options)
        except Exception:
            return False
        if not spectrum_contains_halpha(probe):
            return False
        if not _askyesno(
            self,
            "H-alpha spectrum for Ne",
            (
                "This file contains H-alpha, but no radiometric response covers its window.\n\n"
                "Load it only in the H-alpha electron-density workflow? Dark/background "
                "and wavelength calibration will still be applied."
            ),
        ):
            return False
        window = self.show_ne_halpha()
        return bool(window.load_halpha_spectrum_path(filename))

    def apply_autoshift_if_enabled(self, spectrum):
        """Apply the legacy global offset after radiometric correction."""
        shift = safe_float(getattr(self.options, "auto_shift", 0.0), 0.0)
        if not shift:
            return spectrum
        sources = spectrum.source_windows or (
            SpectrumSourceWindow(
                tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename,
                spectrum.dark_corrected, spectrum.dark_source, spectrum.signal_column,
                spectrum.dark_columns, tuple(spectrum.x),
                replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
            ),
        )
        spectrum.x = [x + shift for x in spectrum.x]
        spectrum.source_windows = tuple(
            _calibrated_source_window(source, legacy_shift=shift)
            for source in sources
        )
        return spectrum

    def wavelength_calibration_profiles(self):
        return parse_calibrations(
            getattr(self.options, "wavelength_calibrations", "[]")
        )

    def apply_wavelength_calibration_if_enabled(self, spectrum):
        profiles = (
            self.wavelength_calibration_profiles()
            if _view_bool(
                getattr(self.options, "auto_wavelength_calibration", True),
                True,
            )
            else []
        )
        sources = spectrum.source_windows or (
            SpectrumSourceWindow(
                tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename,
                spectrum.dark_corrected, spectrum.dark_source, spectrum.signal_column,
                spectrum.dark_columns, tuple(spectrum.x),
                replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
            ),
        )
        if len(sources) != 1:
            return spectrum
        source = sources[0]
        raw_axis = _source_raw_axis(source)
        calibration = calibration_for_window(
            profiles, raw_axis, source.filename or source.name
        )
        if calibration is None:
            return self.apply_autoshift_if_enabled(spectrum)
        spectrum.x = [calibration.correct(x) for x in spectrum.x]
        spectrum.source_windows = (
            _calibrated_source_window(source, calibration=calibration),
        )
        return spectrum

    def apply_wavelength_calibration_profiles(self, profiles):
        """Rebuild loaded spectra from raw source windows using new profiles."""
        profiles = list(profiles or [])
        rebuilt_spectra = []
        for spectrum in self.spectra:
            sources = spectrum.source_windows or (
                SpectrumSourceWindow(
                    tuple(spectrum.x), tuple(spectrum.y), spectrum.name, spectrum.filename,
                    spectrum.dark_corrected, spectrum.dark_source, spectrum.signal_column,
                    spectrum.dark_columns, tuple(spectrum.x),
                    replicate_files=tuple(getattr(spectrum, "replicate_files", ()) or ()),
                ),
            )
            calibrated_sources = []
            for source in sources:
                raw_axis = _source_raw_axis(source)
                calibration = calibration_for_window(
                    profiles, raw_axis, source.filename or source.name
                )
                calibrated_sources.append(
                    _calibrated_source_window(source, calibration=calibration)
                )
            holder = Spectrum(
                [],
                [],
                name=spectrum.name,
                filename=spectrum.filename,
                color=spectrum.color,
                source_windows=tuple(calibrated_sources),
            )
            if spectrum.response_corrected:
                rebuilt = self._response_corrected_copy(holder)
            else:
                rebuilt = self._raw_spectrum_copy(holder)
            rebuilt.name = spectrum.name
            rebuilt.filename = spectrum.filename
            rebuilt.color = spectrum.color
            rebuilt.visible = spectrum.visible
            rebuilt_spectra.append(rebuilt)
        self.spectra = rebuilt_spectra
        self.invalidate_cflibs_results()
        invalidate_self_absorption_analysis(self)
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.refresh()

    def apply_auto_offset_if_enabled(self, spectrum):
        if not _view_bool(getattr(self.options, "auto_offset", False), False):
            return spectrum
        y_values = getattr(spectrum, "y", None)
        try:
            if y_values is None or len(y_values) == 0:
                return spectrum
        except TypeError:
            return spectrum
        try:
            numeric_y = [float(y) for y in y_values]
            finite_y = [y for y in numeric_y if math.isfinite(y)]
        except (TypeError, ValueError):
            return spectrum
        if not finite_y:
            return spectrum
        offset = min(finite_y)
        if offset == 0:
            return spectrum
        spectrum.y = [y - offset for y in numeric_y]
        return spectrum

    def open_spectrum(self):
        fns=filedialog.askopenfilenames(initialdir=remembered_initial_dir(self.options), filetypes=SPECTRUM_FILETYPES)
        if not fns: return
        self.independent_window_mode = False
        self.invalidate_cflibs_results()
        invalidate_self_absorption_analysis(self)
        self.analysis_elements = set()
        remember_working_dir(self.options, fns)
        first_fn=fns[0]
        try:
            sp=self.load_spectrum_with_corrections(first_fn)
            assign_default_spectrum_color(sp, 0)
            self.spectra=[sp]
            self.wavelength_unit = self.infer_wavelength_unit()
        except Exception as e:
            if len(fns) == 1 and self._offer_halpha_ne_import(first_fn, e):
                return
            _showerror(self, "Open",str(e)); return
        ne_status = reset_measurement_session(self)
        self._replace_analysis_lines_from_library(redraw=False)
        for fn in fns[1:]:
            try:
                self.add_spectrum(self.load_spectrum_with_corrections(fn))
            except Exception as e:
                _showerror(self, "Compare", f"{fn}: {e}")
        self.redraw()
        if len(fns) == 1:
            self.status(f"Spectrum loaded: {first_fn}; {ne_status}")
        else:
            self.status(
                f"Spectrum loaded: {first_fn}; comparisons: {len(fns)-1}; "
                f"{ne_status}"
            )

    def append_spectrum(self):
        fns=filedialog.askopenfilenames(initialdir=remembered_initial_dir(self.options), filetypes=SPECTRUM_FILETYPES)
        remember_working_dir(self.options, fns)
        if not fns:
            return
        self.invalidate_cflibs_results()
        invalidate_self_absorption_analysis(self)
        existing = (
            list(self.spectra)
            if self.independent_window_mode
            else list(self.spectra[:1])
        )
        self.independent_window_mode = False
        merged = None
        for spectrum in existing:
            merged = spectrum if merged is None else merge_spectra_by_wavelength(
                merged, spectrum
            )
        for fn in fns:
            try:
                sp=self.load_spectrum_with_corrections(fn)
                if merged is None:
                    merged = sp
                else:
                    merged = merge_spectra_by_wavelength(merged, sp)
                    merged.name = merged_spectrum_display_name(merged)
            except Exception as e:
                if len(fns) == 1 and self._offer_halpha_ne_import(fn, e):
                    return
                _showerror(self, "Append",f"{fn}: {e}")
        if merged is not None:
            assign_default_spectrum_color(merged, 0)
            self.spectra = [merged]
            self.wavelength_unit = self.infer_wavelength_unit()
        self.redraw()
        if self.active_window and self.active_window.winfo_exists(): self.active_window.refresh()

    def load_independent_windows(self):
        """Load one measurement as untouched, independent detector windows."""
        fns = filedialog.askopenfilenames(
            title="Load independent detector windows (no merging)",
            initialdir=remembered_initial_dir(self.options),
            filetypes=SPECTRUM_FILETYPES,
        )
        if not fns:
            return False
        remember_working_dir(self.options, fns)
        loaded = []
        errors = []
        for filename in fns:
            try:
                spectrum = self.load_spectrum_with_corrections(filename)
                assign_default_spectrum_color(spectrum, len(loaded))
                loaded.append(spectrum)
            except Exception as exc:
                errors.append(f"{Path(filename).name}: {exc}")
        if not loaded:
            _showerror(
                self,
                "Independent windows",
                "No detector window could be loaded.\n\n" + "\n".join(errors),
            )
            return False

        self.invalidate_cflibs_results()
        invalidate_self_absorption_analysis(self)
        self.analysis_elements = set()
        self.independent_window_mode = True
        self.spectra = loaded
        self.wavelength_unit = self.infer_wavelength_unit()
        ne_status = reset_measurement_session(self)
        self._replace_analysis_lines_from_library(redraw=False)
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.selected_index = 0
            self.active_window.refresh()
        message = (
            f"Independent-window mode: {len(loaded)} detector windows loaded; "
            f"no interpolation, cross-fade or overlap merging; {ne_status}."
        )
        if errors:
            message += f" {len(errors)} file(s) skipped."
            _showwarning(
                self,
                "Independent windows",
                message + "\n\n" + "\n".join(errors),
            )
        self.status(message)
        return True

    def save_spectrum(self):
        if not self.spectra: return
        fn=filedialog.asksaveasfilename(initialdir=remembered_initial_dir(self.options), defaultextension=".dat")
        if fn:
            remember_working_dir(self.options, fn)
            self.spectra[0].save_ascii(fn)

    def ask_load_response(self):
        fns=filedialog.askopenfilenames(
            title="One instrumental-response file per spectral window",
            initialdir=remembered_initial_dir(self.options),
            filetypes=[("Instrument response / OPC","*.xlsx *.xlsm *.txt *.dat *.asc *.csv *.CSV *.opc"),("All","*.*")],
        )
        if fns:
            remember_working_dir(self.options, fns)
            self.load_response_files(fns)

    def load_response_files(self, filenames):
        paths = parse_response_paths(filenames)
        if not paths:
            return False
        kind = _response_paths_kind(paths)
        physical_apply_after = (
            kind == "instrument"
            and bool(getattr(self.options, "apply_after", False))
            and not bool(getattr(self.options, "apply_before", False))
        )
        if kind == "mixed":
            _showerror(
                self,
                "Correction files",
                "Do not load an OPC together with physical instrumental-response files. "
                "The OPC is already the composite line-wise correction.",
            )
            return False
        if kind == "opc" and len(paths) != 1:
            _showerror(self, "OPC", "Select one OPC calibration file at a time.")
            return False
        previous_paths = self.configured_response_paths()
        previous_apply_response = bool(getattr(self.options, "apply_response", False))
        previous_apply_before = bool(getattr(self.options, "apply_before", False))
        previous_apply_after = bool(getattr(self.options, "apply_after", False))
        self.options.response_files = serialize_response_paths(paths)
        self.options.response_file = paths[0]
        self.options.apply_response = True
        self.options.apply_before = kind != "opc" and not physical_apply_after
        self.options.apply_after = kind == "opc" or physical_apply_after
        if not self.load_configured_responses(silent=False):
            self.options.response_files = serialize_response_paths(previous_paths)
            self.options.response_file = previous_paths[0] if previous_paths else ""
            self.options.apply_response = previous_apply_response
            self.options.apply_before = previous_apply_before
            self.options.apply_after = previous_apply_after
            self.load_configured_responses(silent=True)
            return False
        save_pylibs_ini(self.options)
        MainWindow.sync_response_application_mode(self, notify=True)
        if kind == "opc" or self.options.apply_after:
            invalidate_self_absorption_analysis(self)
            self.invalidate_cflibs_results()
        if self.response_window and self.response_window.winfo_exists():
            self.response_window.redraw()
        if kind == "opc":
            opc_id = self.active_opc_id or "unknown"
            self.status(
                f"OPC loaded: {Path(paths[0]).name} [ID {opc_id}] in Apply After mode; "
                "spectrum and fitted areas were not modified"
            )
        else:
            self.status(
                f"Instrument response library: {len(self.response_library.curves)} curve(s) "
                f"from {len(paths)} file(s)"
            )
        return True

    def load_response_file(self, fn):
        return self.load_response_files([fn])

    def apply_response_now(self):
        if not self.response_library.curves:
            _showinfo(self, "Response", "Load at least one response curve first.")
            return False
        if _loaded_response_is_opc(self):
            self.options.apply_response = True
            self.options.apply_before = False
            self.options.apply_after = True
            save_pylibs_ini(self.options)
            _showinfo(
                self,
                "OPC",
                "OPC is a sparse line calibration and is applied automatically after line integration. "
                "The spectrum and fitted areas have not been modified.",
            )
            return False
        try:
            corrected = [self._response_corrected_copy(spectrum) for spectrum in self.spectra]
        except Exception as exc:
            _showerror(self, "Instrument response", str(exc))
            return False
        self.spectra = corrected
        invalidate_self_absorption_analysis(self)
        self.invalidate_cflibs_results()
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.refresh()
        if self.response_window and self.response_window.winfo_exists():
            self.response_window.redraw()
        details = sum(len(spectrum.source_windows) for spectrum in self.spectra)
        self.status(f"Instrument response applied to {details} spectral window(s)")
        return True

    def clear_response_library(self):
        self.spectra = [self._raw_spectrum_copy(spectrum) for spectrum in self.spectra]
        invalidate_self_absorption_analysis(self)
        self.invalidate_cflibs_results()
        self.response_library = InstrumentResponseLibrary()
        self.response = None
        self.active_opc_path = ""
        self.active_opc_id = ""
        self.active_opc_metadata = {}
        self.options.response_file = ""
        self.options.response_files = ""
        save_pylibs_ini(self.options)
        self.redraw()
        if self.response_window and self.response_window.winfo_exists():
            self.response_window.redraw()
        self.status("Instrument response library cleared; raw window data restored")

    def activate_database(self, filename):
        path = Path(str(filename or "")).expanduser()
        if not path.is_absolute():
            path = app_base_dir() / path
        self.libs_db.switch(str(path))
        self.options.libs_db_file = self.libs_db.filename
        self.atomic_lines = []
        self.element_markers = []
        self.trace_markers = []
        self.analysis_elements = set()
        self.invalidate_cflibs_results()
        label = self.libs_db.display_name()
        self.status(f"Atomic library active: {label} ({Path(self.libs_db.filename).name})")
        return label

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
        self.fit_baseline_overlay = None
        self.fit_component_overlays = []
        self.fit_integration_bounds = []

    def clear_fit_artists(self):
        self.fit_overlay = None
        self.fit_baseline_overlay = None
        self.fit_component_overlays = []
        self.fit_integration_bounds = []
        ax = getattr(self, "ax", None)
        if not ax:
            return False
        try:
            self.redraw(preserve_view=True)
            return True
        except Exception:
            return False

    def _active_spectrum_y_at(self, wavelength):
        """Intensity of the selected active spectrum at the nearest wavelength.

        If the Active Spectra window is open, use its selected row; otherwise
        fall back to the main/first visible spectrum.  This keeps Trace and
        manual markers anchored to the spectrum the user is working on.
        """
        try:
            sp = select_spectrum_for_wavelengths(self, [wavelength])
            if sp is None:
                return 0.0
            idx = min(range(len(sp.x)), key=lambda i: abs(sp.x[i] - wavelength))
            return float(sp.y[idx]) if idx < len(sp.y) else 0.0
        except Exception:
            return 0.0

    def redraw(self, preserve_view=False):
        if not getattr(self,"ax",None): return
        old_xlim = old_ylim = None
        previous_legend_location = getattr(
            getattr(self, "plot_legend", None),
            "_loc",
            "best",
        )
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
                for segment_index, (segment_x, segment_y) in enumerate(spectrum_plot_segments(sp)):
                    self.ax.plot(
                        segment_x,
                        segment_y,
                        linewidth=0.8,
                        label=sp.name if segment_index == 0 else "_nolegend_",
                        **kwargs,
                    )
        ymin,ymax=self.ax.get_ylim()
        h=ymax-ymin if ymax>ymin else 1
        selected_elements = _selected_analysis_elements(self)
        for line in (self.template_lines if self.spectra else []):
            species = str(getattr(line, "specie", "") or "").strip().capitalize()
            if not template_line_is_acquired(self, line):
                continue
            if species and selected_elements is not None and species not in selected_elements:
                continue
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
            # After fitting, mark the observed Voigt center. The NIST
            # wavelength remains stored in asswavelen/wavelen for assignment.
            marker_wave = template_line_plot_wavelength(line)
            fitted = bool(abs(safe_float(getattr(line, "fitwavelen", 0.0), 0.0)))
            ytop = self._active_spectrum_y_at(marker_wave)
            self.ax.vlines(marker_wave, 0.0, ytop, linestyles="solid", linewidth=0.9, colors=color)
            label = (
                f"{marker_wave:.2f}"
                if not line.specie
                else (
                    f"{line.specie} {_roman_ion(line.ion)} fit {marker_wave:.2f}"
                    if fitted
                    else f"{line.specie} {_roman_ion(line.ion)} {line.asswavelen or line.wavelen:.2f}"
                )
            )
            self.ax.text(
                marker_wave, ytop, label,
                rotation=0, fontsize=7, va=("bottom" if ytop >= 0 else "top"), ha="center",
                color="black", bbox=label_bbox, clip_on=True,
            )
        # Trace Lines overlay: green segments with readable species labels.
        # Like the manual/identified markers, traced lines start at y=0 and
        # reach the intensity of the selected active spectrum at that wavelength.
        trace_markers = getattr(self, "trace_markers", [])
        if trace_markers:
            for l in trace_markers:
                species = str(getattr(l, "specie", "") or "").strip().capitalize()
                if trace_marker_has_fitted_template(self, l):
                    continue
                if not wavelength_is_acquired(self, l.wavelen, include_visible_comparisons=True):
                    continue
                if selected_elements is not None and species not in selected_elements:
                    continue
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
                if not wavelength_is_acquired(self, l.wavelen, include_visible_comparisons=True):
                    continue
                y=ymin+(l.inte/maxint)*0.8*h
                self.ax.vlines(l.wavelen,ymin,y,colors="green",linewidth=1.0)
                self.ax.text(
                    l.wavelen, y, f"{l.specie} {'I' if l.ion==1 else 'II'}",
                    rotation=0, fontsize=7, va="bottom", ha="center",
                    color="black", bbox=label_bbox, clip_on=True,
                )
        if self.fit_overlay:
            fx, fy = self.fit_overlay
            self.ax.plot(
                fx,
                fy,
                linewidth=1.8,
                label=getattr(self, "fit_overlay_label", "Fit sum"),
            )
        baseline_overlay = getattr(self, "fit_baseline_overlay", None)
        if baseline_overlay:
            bx, by = baseline_overlay
            self.ax.plot(
                bx,
                by,
                linewidth=1.1,
                linestyle="--",
                color="#6e6e73",
                label="Local baseline",
            )
        component_overlays = list(
            getattr(self, "fit_component_overlays", []) or []
        )
        integration_bounds = list(
            getattr(self, "fit_integration_bounds", []) or []
        )
        component_colors = ("#0071e3", "#ff375f", "#34c759", "#af52de")
        for index, component in enumerate(component_overlays):
            cx, curve = component
            color = component_colors[index % len(component_colors)]
            baseline_values = (
                np.interp(cx, baseline_overlay[0], baseline_overlay[1])
                if baseline_overlay
                else np.zeros(len(cx), dtype=float)
            )
            component_values = (
                baseline_values + np.asarray(curve, dtype=float)
            )
            self.ax.plot(
                cx,
                component_values,
                linewidth=1.2,
                linestyle=":",
                color=color,
                label=f"{getattr(self, 'fit_component_label', 'Fit')} {index + 1}",
            )
            self.ax.fill_between(
                cx,
                baseline_values,
                component_values,
                color=color,
                alpha=0.12,
            )
            if index < len(integration_bounds):
                left, right = integration_bounds[index]
                self.ax.axvline(
                    left,
                    color=color,
                    linewidth=0.9,
                    linestyle="--",
                    alpha=0.7,
                )
                self.ax.axvline(
                    right,
                    color=color,
                    linewidth=0.9,
                    linestyle="--",
                    alpha=0.7,
                )
        if any(sp.visible for sp in self.spectra) or self.fit_overlay:
            legend_location = (
                previous_legend_location
                if isinstance(previous_legend_location, tuple)
                else "best"
            )
            self.plot_legend = self.ax.legend(loc=legend_location)
            try:
                self.plot_legend.set_draggable(True, use_blit=True)
            except TypeError:
                self.plot_legend.set_draggable(True)
        else:
            self.plot_legend = None
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

    def show_wavelength_calibration(self):
        self.wavelength_calibration_window = show_existing_or_create(
            self,
            "wavelength_calibration_window",
            lambda: WavelengthCalibrationWindow(self),
            refresh=lambda window: window.refresh(),
            parent=self,
        )
        return self.wavelength_calibration_window

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
            selected_species = str(
                getattr(t, "specie", "") or ""
            ).strip().capitalize()
            selected_ion = safe_int(getattr(t, "ion", 0), 0)
            candidates = [
                line
                for line in trace_markers
                if abs(line.wavelen - t.wavelen) <= rg
                and (
                    not selected_species
                    or str(getattr(line, "specie", "") or "").strip().capitalize()
                    == selected_species
                )
                and (
                    selected_ion not in (1, 2)
                    or safe_int(getattr(line, "ion", 0), 0) == selected_ion
                )
            ]
            if not candidates:
                continue
            atomic = min(candidates, key=lambda l: abs(l.wavelen - t.wavelen))
            try:
                atomic = self.libs_db.enrich_line_from_element_table(
                    atomic,
                    tolerance=max(0.02, rg),
                    wavelength_unit=getattr(self, "wavelength_unit", "angstrom"),
                )
            except Exception:
                pass
            self.copy_atomic_line_to_template_line(t, atomic)
            assigned += 1
        self.notify_template_changed(redraw=False)
        self.redraw(preserve_view=True)
        self.status(f"Trace Assign: {assigned} analytical lines assigned")
        return assigned

    def assign_atomic_line_to_nearest_template(self, atomic, redraw=True):
        # When possible, enrich the fast Datalibs/Daticerti match with the
        # complete spectroscopic parameters stored in the element table.
        try:
            atomic = self.libs_db.enrich_line_from_element_table(
                atomic,
                tolerance=max(0.02, self.options.search_range),
                wavelength_unit=getattr(self, "wavelength_unit", "angstrom"),
            )
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
        self.status(
            f"Assigned {atomic.specie} {_roman_ion(atomic.ion)} at "
            f"{atomic.wavelen:.4f} {self.current_wavelength_unit_label()}"
        )

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
            # Atomic identification follows the selected/theoretical NIST
            # wavelength. The observed Voigt center may be shifted by the
            # instrument and must not silently select a different ion stage.
            wave = float(
                getattr(t, "asswavelen", 0.0)
                or getattr(t, "wavelen", 0.0)
                or getattr(t, "fitwavelen", 0.0)
            )
            ion = int(getattr(t, "ion", 0) or 0)
            if not wave:
                return False
            atomic = AtomicLine(wavelen=wave, specie=str(t.specie).strip(), ion=ion)
            unit = self.current_wavelength_unit_label()
            maximum_tolerance = 0.02 if unit == "nm" else 0.2
            requested_tolerance = (
                tolerance
                if tolerance is not None
                else maximum_tolerance
            )
            tol = min(abs(safe_float(requested_tolerance, maximum_tolerance)), maximum_tolerance)
            enriched = self.libs_db.enrich_line_from_element_table(
                atomic,
                tolerance=tol,
                wavelength_unit=getattr(self, "wavelength_unit", "angstrom"),
            )
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

    def show_fit(self):
        # Keep the legacy command as an alias, but use the single manual-fit
        # workflow where Gaussian and Voigt act on the same lines and ROI.
        return self.show_retro_fit_manager()
    def show_ne_halpha(self): self.ne_halpha_window = _show_persistent_window(self, "ne_halpha_window", lambda: NeHalphaWindow(self), "HAlpha", parent=self, center_on_create=True)
    def show_sac(self): self.sac_window = show_existing_or_create(self, "sac_window", lambda: SACWindow(self), parent=self)
    def show_saha(self): self.saha_window = _show_persistent_window(self, "saha_window", lambda: SahaBoltzmannWindow(self), "SahaBoltzmann", parent=self, center_on_create=True)
    def show_cflibs(self): self.cflibs_window = _show_persistent_window(self, "cflibs_window", lambda: CFLibsWindow(self), "CFLIBS", parent=self, center_on_create=True)
    def show_standard_correction(self): self.standard_correction_window = show_existing_or_create(self, "standard_correction_window", lambda: StandardCorrectionWindow(self), parent=self)
    def show_theoretical_spectrum(self):
        self.theoretical_window = show_existing_or_create(
            self, "theoretical_window", lambda: TheoreticalSpectrumWindow(self), parent=self
        )
        return self.theoretical_window
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
            press = getattr(self, "_nav_press", None)
            rectangle = getattr(self, "_zoom_rectangle", None)
            if press and press[0] == 1 and rectangle is not None:
                _button, x0, y0, _px0, _py0, _xlim, _ylim = press
                rectangle.set_x(min(x0, float(event.xdata)))
                rectangle.set_y(min(y0, float(event.ydata)))
                rectangle.set_width(abs(float(event.xdata) - x0))
                rectangle.set_height(abs(float(event.ydata) - y0))
                self.canvas.draw_idle()

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

def _add_menu_cascade(self, menu, label, submenu, icon=""):
    """Add a consistently styled submenu, with an icon when available."""
    image = get_menu_icon(self, icon) if icon else None
    kwargs = {"label": label, "menu": submenu}
    if image is not None:
        kwargs["image"] = image
        kwargs["compound"] = "left"
    menu.add_cascade(**kwargs)

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
    _add_menu_command(
        self,
        file_menu,
        shortcut_items,
        "Load independent windows...",
        self.load_independent_windows,
        "",
        "",
        "open.png",
    )
    file_menu.add_separator()
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
    spectra_menu = tk.Menu(edit_menu, tearoff=0)
    _add_menu_cascade(self, edit_menu, "Spectrum Management", spectra_menu, "Active_spectra.png")
    _add_menu_command(self, spectra_menu, shortcut_items, "Swap Spectra", self.swap_spectra, "Ctrl+W", "<Control-w>", "compare.png")
    _add_menu_command(self, spectra_menu, shortcut_items, "Show Active Spectra", self.show_active_spectra, "Ctrl+Shift+A", "<Control-Shift-A>", "Active_spectra.png")
    spectra_menu.add_separator()
    _add_menu_command(self, spectra_menu, shortcut_items, "Clear Graph", self.clear_all_spectra, "Ctrl+Del", "<Control-Delete>", "clear.png")
    edit_menu.add_separator()
    _add_menu_command(self, edit_menu, shortcut_items, "Options...", self.show_options, "Ctrl+Alt+O", "<Control-Alt-o>", "options.png")
    _add_menu_command(
        self,
        edit_menu,
        shortcut_items,
        "Restore Factory Settings...",
        self.restore_factory_settings,
        "",
        "",
        "options.png",
    )

    view_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="View", menu=view_menu)
    self.view_grid_x_var = tk.BooleanVar(value=_view_bool(getattr(self, "view_grid_x", True), True))
    self.view_grid_y_var = tk.BooleanVar(value=_view_bool(getattr(self, "view_grid_y", True), True))
    self.view_log_x_var = tk.BooleanVar(value=getattr(self, "view_log_x", False))
    self.view_log_y_var = tk.BooleanVar(value=getattr(self, "view_log_y", False))
    appearance_menu = tk.Menu(view_menu, tearoff=0)
    _add_menu_cascade(self, view_menu, "Appearance", appearance_menu, "background.png")
    _add_menu_command(self, appearance_menu, shortcut_items, "Background Color...", self.change_background, "Ctrl+B", "<Control-b>", "background.png")
    appearance_menu.add_separator()
    _add_menu_checkbutton(self, appearance_menu, shortcut_items, "X-axis Grid", lambda: self.toggle_grid(axis="x"), self.view_grid_x_var, "Ctrl+Alt+X", "<Control-Alt-x>", "grid.png")
    _add_menu_checkbutton(self, appearance_menu, shortcut_items, "Y-axis Grid", lambda: self.toggle_grid(axis="y"), self.view_grid_y_var, "Ctrl+Alt+Y", "<Control-Alt-y>", "grid_xy.png")
    appearance_menu.add_separator()
    _add_menu_checkbutton(self, appearance_menu, shortcut_items, "Logarithmic X Axis", lambda: self.toggle_log(axis="x"), self.view_log_x_var, "Ctrl+Alt+G", "<Control-Alt-g>", "log_x.png")
    _add_menu_checkbutton(self, appearance_menu, shortcut_items, "Logarithmic Y Axis", lambda: self.toggle_log(axis="y"), self.view_log_y_var, "Ctrl+Alt+L", "<Control-Alt-l>", "log_y.png")

    scale_menu = tk.Menu(view_menu, tearoff=0)
    _add_menu_cascade(self, view_menu, "Zoom and Scale", scale_menu, "full_view.png")
    _add_menu_command(self, scale_menu, shortcut_items, "Fit X Axis", self.full_x, "", "", "zoom_x_out.png")
    _add_menu_command(self, scale_menu, shortcut_items, "Fit Y Axis", self.full_y, "", "", "zoom_y_out.png")
    _add_menu_command(self, scale_menu, shortcut_items, "Expand X by 50%", self.expand_x_50, "F2", "<F2>", "zoom_x_in.png")
    _add_menu_command(self, scale_menu, shortcut_items, "Full Y Scale", self.full_y, "F3", "<F3>", "zoom_y_out.png")
    _add_menu_command(self, scale_menu, shortcut_items, "Show Full Spectrum", self.full_scale, "F4", "<F4>", "full_view.png")

    layout_menu = tk.Menu(view_menu, tearoff=0)
    _add_menu_cascade(self, view_menu, "Window Layout", layout_menu, "full_view.png")
    _add_menu_command(self, layout_menu, shortcut_items, "Save Window Positions", self.save_window_positions)
    _add_menu_command(self, layout_menu, shortcut_items, "Restore Window Positions", self.load_window_positions)

    util_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Utilities", menu=util_menu)
    calibration_menu = tk.Menu(util_menu, tearoff=0)
    _add_menu_cascade(self, util_menu, "Instrument Calibration", calibration_menu, "calibration.png")
    _add_menu_command(
        self,
        calibration_menu,
        shortcut_items,
        "Instrument Response...",
        self.show_response_window,
        "Ctrl+Alt+R",
        "<Control-Alt-r>",
        "calibration.png",
    )
    _add_menu_command(
        self,
        calibration_menu,
        shortcut_items,
        "Apply Instrument Response",
        self.apply_response_now,
        "",
        "",
        "calibration.png",
    )
    calibration_menu.add_separator()
    _add_menu_command(
        self,
        calibration_menu,
        shortcut_items,
        "Wavelength Calibration...",
        self.show_wavelength_calibration,
        "",
        "",
        "calibration.png",
    )
    _add_menu_command(self, calibration_menu, shortcut_items, "Manual Wavelength Shift...", self.show_spectrum_shift, "Ctrl+F1", "<Control-F1>", "calibration.png")

    processing_menu = tk.Menu(util_menu, tearoff=0)
    _add_menu_cascade(self, util_menu, "Signal Processing", processing_menu, "fit.png")
    _add_menu_command(self, processing_menu, shortcut_items, "Intensity Offset...", self.show_spectrum_offset, "Ctrl+F2", "<Control-F2>", "")
    _add_menu_command(self, processing_menu, shortcut_items, "Smooth Spectrum", self.smooth_main_spectrum, "Ctrl+F3", "<Control-F3>", "")
    _add_menu_command(self, processing_menu, shortcut_items, "Convert nm to Å", self.convert_nm_to_angstrom, "Ctrl+F4", "<Control-F4>", "")

    line_menu = tk.Menu(util_menu, tearoff=0)
    _add_menu_cascade(self, util_menu, "Analytical Line Lists", line_menu, "show_Template.png")
    _add_menu_command(
        self, line_menu, shortcut_items, "Import Lines for Current Analysis...",
        self.load_template_from_menu, "Ctrl+F5", "<Control-F5>", "load_template.png"
    )
    _add_menu_command(
        self, line_menu, shortcut_items, "Main Analytical-Line Library...",
        self.show_template_manager, "Ctrl+F6", "<Control-F6>", "show_Template.png"
    )
    line_menu.add_separator()
    _add_menu_command(self, line_menu, shortcut_items, "Selected-Line Summary", self.template_info_from_menu, "Ctrl+F7", "<Control-F7>", "show_Template.png")
    _add_menu_command(self, line_menu, shortcut_items, "Clear Selected Lines", self.close_template_from_menu, "", "", "clear.png")

    batch_menu = tk.Menu(util_menu, tearoff=0)
    _add_menu_cascade(self, util_menu, "Batch and Statistics", batch_menu, "calculator.png")
    _add_menu_command(self, batch_menu, shortcut_items, "Batch Operations...", self.show_batch_statistics, "", "", "calculator.png")
    _add_menu_command(self, batch_menu, shortcut_items, "Statistics", self.show_statistics, "Shift+Ctrl+F4", "<Control-Shift-F4>", "calculator.png")
    util_menu.add_separator()
    _add_menu_command(self, util_menu, shortcut_items, "Go To Wavelength...", self.show_goto_dialog, "Ctrl+F9", "<Control-F9>", "goto.png")

    analysis_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Analyse", menu=analysis_menu)
    detection_menu = tk.Menu(analysis_menu, tearoff=0)
    _add_menu_cascade(self, analysis_menu, "Peak and Line Detection", detection_menu, "find_peaks.png")
    _add_menu_command(self, detection_menu, shortcut_items, "Find Peaks", self.find_peaks_basic, "", "", "find_peaks.png")
    _add_menu_command(self, detection_menu, shortcut_items, "Trace Lines...", self.show_trace_lines, "", "", "trace.png")

    fitting_menu = tk.Menu(analysis_menu, tearoff=0)
    _add_menu_cascade(self, analysis_menu, "Spectral Fitting", fitting_menu, "fit.png")
    _add_menu_command(self, fitting_menu, shortcut_items, "Manual Fit...", self.show_retro_fit_manager, "", "", "fit_manual.png")
    _add_menu_command(self, fitting_menu, shortcut_items, "Automatic Fit...", self.show_auto_fit_manager, "", "", "fit_auto.png")

    plasma_menu = tk.Menu(analysis_menu, tearoff=0)
    _add_menu_cascade(self, analysis_menu, "Plasma Diagnostics", plasma_menu, "H_alpha.png")
    _add_menu_command(self, plasma_menu, shortcut_items, "Electron Density from Hα...", self.show_ne_halpha, "", "", "H_alpha.png")
    _add_menu_command(self, plasma_menu, shortcut_items, "Saha-Boltzmann Plot...", self.show_saha_boltzmann, "", "", "calculator.png")
    plasma_menu.add_separator()
    _add_menu_command(self, plasma_menu, shortcut_items, "Self-Absorption / IRSAC...", self.show_sac_check, "", "", "calibration.png")
    _add_menu_command(self, plasma_menu, shortcut_items, "SAC Factors...", self.show_sac_window, "", "", "calibration.png")

    quantitative_menu = tk.Menu(analysis_menu, tearoff=0)
    _add_menu_cascade(self, analysis_menu, "Quantitative Analysis", quantitative_menu, "database.png")
    _add_menu_command(self, quantitative_menu, shortcut_items, "CF-LIBS...", self.show_cf_libs, "", "", "database.png")
    _add_menu_command(self, quantitative_menu, shortcut_items, "Theoretical Spectrum...", self.show_theoretical_spectrum, "", "", "calculator.png")
    quantitative_menu.add_separator()
    _add_menu_command(self, quantitative_menu, shortcut_items, "Standard Correction...", self.show_standard_correction, "", "", "database.png")

    help_menu = tk.Menu(menu, tearoff=0)
    menu.add_cascade(label="Help", menu=help_menu)
    manual_menu = tk.Menu(help_menu, tearoff=0)
    _add_menu_cascade(self, help_menu, "User Manual", manual_menu, "help.png")
    _add_menu_command(self, manual_menu, shortcut_items, "Italiano", lambda: self.show_manual("it"), "", "", "help.png")
    _add_menu_command(self, manual_menu, shortcut_items, "English", lambda: self.show_manual("en"), "", "", "help.png")
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
        ("Append", self.ask_import_multiple),
        ("Clear", self.clear_all_spectra),
        ("Active Spectra", self.show_active_spectra),
        ("Response", self.show_response_window),
        ("Full Scale", self.full_scale),
        ("Selected Lines", self.show_template_manager),
        ("Trace", self.show_trace_lines),
        ("Ne from Hα", self.show_ne_halpha),
        ("Auto Fit", self.show_auto_fit_manager),
        ("Manual Fit", self.show_retro_fit_manager),
        ("Saha-Boltzmann", self.show_saha_boltzmann),
        ("CF-LIBS", self.show_cf_libs),
    ]
    icon_names = {
        "Open": "open.png",
        "Append": "append.png",
        "Clear": "clear.png",
        "Active Spectra": "fit.png",
        "Response": "calibration.png",
        "Full Scale": "full_view.png",
        "Selected Lines": "show_template.png",
        "Trace": "trace.png",
        "Ne from Hα": "H_alpha.png",
        "Auto Fit": "fit_auto.png",
        "Manual Fit": "fit_manual.png",
        "Saha-Boltzmann": "calculator.png",
        "CF-LIBS": "database.png",
    }
    icon_fallbacks = {
        "Auto Fit": "fit.png",
        "Manual Fit": "fit.png",
    }
    tooltip_text = {
        "Trace": "Trace Lines",
        "Full Scale": "Full View",
        "Response": "Instrument Response",
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
        self.title(APP_TITLE)
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
    geometry = getattr(self, "template_window_geometry", "")
    if geometry:
        try:
            win.geometry(geometry)
        except Exception:
            pass
    try:
        win.deiconify()
    except Exception:
        pass
    if geometry:
        try:
            win.geometry(geometry)
        except Exception:
            pass
    try:
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
    invalidate_self_absorption_analysis(self)
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
        self.independent_window_mode = False
        self.clear_plot_annotations()
        self._replace_analysis_lines_from_library(
            redraw=False,
            preserve_analysis_elements=True,
        )
        ne_status = reset_measurement_session(self)
        self.redraw()
        if self.active_window and self.active_window.winfo_exists():
            self.active_window.refresh()
        line_count = len(getattr(self, "template_lines", []) or [])
        self.status(
            f"Clear Graph: spectra cleared; analytical list restored "
            f"({line_count} lines); {ne_status}."
        )

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
    _showinfo(self, "Copy", "Direct clipboard export is unavailable. Use File > Print to export the plot.")

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
    invalidate_self_absorption_analysis(self)
    for sp in self.spectra:
        sp.x = [x*10 if x < 1500 else x for x in sp.x]
    self.options.convert_to_angstrom = True
    self.wavelength_unit = "angstrom"
    self.redraw()

def load_template_from_menu(self):
    fn = _template_file_dialog(
        self,
        filedialog.askopenfilename,
        title="Import lines for the current analysis",
        initialdir=remembered_initial_dir(self.options),
        filetypes=[("Templates", "*.csv *.db *.DB *.txt"), ("All", "*.*")]
    )
    if not fn:
        return
    remember_working_dir(self.options, fn)
    try:
        self.load_template_file(fn)
        self.redraw()
        self.status(f"Selected-line list imported: {fn}")
    except Exception as e:
        _showerror(self, "Import selected-line list", str(e))

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
    _showinfo(self, "Selected-Line Summary", msg)

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
    self.last_cflibs_quality = None
    self.last_cflibs_robustness = None
    try:
        for child in self.winfo_children():
            if isinstance(child, CFLibsWindow) and child.winfo_exists():
                child.last_rows = []
                child.last_groups = {}
                child.last_fits = {}
                child.last_quality = None
                child.last_robustness = {}
                child.last_unvalidated_rows = []
                child.disable_opc()
    except Exception:
        pass


def invalidate_self_absorption_analysis(self):
    """Discard IRSAC/theory state whenever spectra, fits or assignments change."""
    self.apply_sac_correction = False
    self.last_self_absorption_result = None
    self.post_irsac_temperature = None
    self.post_irsac_temperature_source = None
    self.last_theoretical_spectrum = None
    for line in getattr(self, "template_lines", []) or []:
        line.sa_sac = ""
        line.sa_method = ""
        line.sa_reference = ""
        line.sa_flagged = False
        line.sa_stark_width = ""
        line.sa_has_stark_data = False
        line.sa_use = False
    _refresh_theoretical_workflow_ui(self)

def notify_template_changed(self, redraw=False):
    self.invalidate_cflibs_results()
    self.invalidate_self_absorption_analysis()
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
    sp = select_spectrum_for_wavelengths(self, [wavelength])
    if sp is None:
        return (wavelength, 0.0, -1)
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
    legend = getattr(self, "plot_legend", None)
    if legend is not None:
        try:
            if legend.contains(event)[0]:
                self._nav_press = None
                return
        except Exception:
            pass
    fit_capture = getattr(self, "fit_peak_capture_window", None)
    if fit_capture is not None and fit_capture.winfo_exists() and event.button == 1:
        self._nav_press = None
        fit_capture.add_peak_from_graph(float(event.xdata))
        return
    roi_capture = getattr(self, "fit_roi_capture_window", None)
    if roi_capture is not None and roi_capture.winfo_exists() and event.button == 1:
        self._nav_press = None
        roi_capture.add_fit_range_point_from_graph(float(event.xdata))
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
        old_rectangle = getattr(self, "_zoom_rectangle", None)
        if old_rectangle is not None:
            try:
                old_rectangle.remove()
            except Exception:
                pass
            self._zoom_rectangle = None
        if event.button == 1 and Rectangle is not None:
            self._zoom_rectangle = Rectangle(
                (float(event.xdata), float(event.ydata)),
                0.0,
                0.0,
                facecolor="#0071e3",
                edgecolor="#0071e3",
                linewidth=1.0,
                linestyle="--",
                alpha=0.15,
                zorder=20,
            )
            self.ax.add_patch(self._zoom_rectangle)
    except Exception:
        pass

def find_peaks_basic(self, adaptive=False):
    """Mark observed local maxima in the visible wavelength interval.

    The classic menu command retains the Palleschi threshold option. Auto Fit
    uses a scale-independent five-sigma threshold estimated from first
    differences, so radiometric correction does not invalidate the setting.
    """
    if not self.spectra:
        return None
    if scipy_find_peaks is None:
        _showerror(self, "Find Peaks", "SciPy signal processing is not available. Install SciPy to use Find Peaks.")
        return None
    spectra = (
        [sp for sp in self.spectra if getattr(sp, "visible", True)]
        if getattr(self, "independent_window_mode", False)
        else list(self.spectra[:1])
    )
    if not any(len(getattr(sp, "x", []) or []) >= 3 for sp in spectra):
        return None

    if getattr(self, "ax", None):
        lo, hi = self.current_xlim()
        if lo > hi:
            lo, hi = hi, lo
    else:
        lo, hi = -math.inf, math.inf
    visible_segments = []
    for sp in spectra:
        for segment_x, segment_y in spectrum_plot_segments(sp):
            points = [(x, y) for x, y in zip(segment_x, segment_y) if lo <= x <= hi]
            if len(points) >= 3:
                visible_segments.append(points)
    if not visible_segments:
        self.status("Find Peaks: no points in the current wavelength window")
        return None

    peaks = []
    thresholds = []
    classic_threshold = max(0.0, safe_float(getattr(self.options, "threshold", 1.0), 1.0))
    for points in visible_segments:
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        ordered = sorted(ys)
        baseline = ordered[max(0, int(0.50 * len(ordered)) - 1)]
        if adaptive:
            differences = [b - a for a, b in zip(ys, ys[1:])]
            ordered_differences = sorted(differences)
            median_difference = ordered_differences[len(ordered_differences) // 2]
            deviations = sorted(abs(value - median_difference) for value in differences)
            mad_difference = deviations[len(deviations) // 2] if deviations else 0.0
            noise_sigma = 1.4826 * mad_difference / math.sqrt(2.0)
            signal_scale = max((abs(value) for value in ys), default=1.0)
            prominence = max(5.0 * noise_sigma, signal_scale * 1.0e-6, 1.0e-12)
            height = None
            min_distance = 2
        else:
            prominence = classic_threshold
            height = baseline + classic_threshold
            dx = [abs(b - a) for a, b in zip(xs, xs[1:]) if b != a]
            median_dx = sorted(dx)[len(dx) // 2] if dx else 1.0
            delta_min = max(0.0, safe_float(getattr(self.options, "delta_min", 1.0), 1.0))
            min_distance = max(3, min(50, int(max(1.0, 0.25 * delta_min / max(median_dx, 1e-12)))))
        thresholds.append(prominence)
        peak_indices, props = scipy_find_peaks(
            ys,
            prominence=prominence,
            height=height,
            distance=min_distance,
        )
        prominences = props.get("prominences", [])
        for pos, prom in zip(peak_indices, prominences):
            peaks.append((xs[int(pos)], ys[int(pos)], float(prom)))
    peaks.sort(key=lambda p: p[2], reverse=True)
    selected = peaks[:100]
    selected.sort(key=lambda p: p[0])
    added = 0
    updated = 0
    tol = max(1e-6, abs(getattr(self.options, "search_range", 0.2)) * 0.02)
    for x, y, _ in selected:
        _, was_added = self._merge_template_line(
            TemplateLine(
                wavelen=x,
                inte=None,
                templint=y,
                wg=None,
                wl=None,
                fitwavelen=None,
            ),
            tolerance=tol,
        )
        if was_added:
            added += 1
        else:
            updated += 1
    self.notify_template_changed(redraw=False)
    self.redraw()
    if adaptive:
        threshold_text = f"automatic 5-sigma threshold ({min(thresholds):.3g}-{max(thresholds):.3g})"
    else:
        threshold_text = f"classic threshold {classic_threshold:.3g}"
    self.status(
        f"Find Peaks: {added} new lines, {updated} updated; {threshold_text}; "
        f"selected-line total {len(self.template_lines)}"
    )
    return {"added": added, "updated": updated, "thresholds": thresholds, "adaptive": bool(adaptive)}

def on_close(self):
    try:
        self.options.view_grid_x = _view_bool(getattr(self, "view_grid_x", True), True)
        self.options.view_grid_y = _view_bool(getattr(self, "view_grid_y", True), True)
        self.options.view_log_x = bool(getattr(self, "view_log_x", False))
        self.options.view_log_y = bool(getattr(self, "view_log_y", False))
        self.options.background_color = _background_color(getattr(self, "plot_background", "#ffffff"), "#ffffff")
        save_pylibs_ini(self.options)
        if getattr(self, "pending_scientific_settings_applied", False):
            pending_path = resource_path(_PENDING_SCIENTIFIC_SETTINGS)
            pending_path.unlink(missing_ok=True)
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
        try:
            dialect = (
                csv.Sniffer().sniff(sample, delimiters=",;\t ")
                if sample.strip()
                else csv.excel
            )
        except csv.Error:
            dialect = None
        reader = csv.DictReader(f, dialect=dialect) if dialect is not None else None
        if (
            reader is not None
            and reader.fieldnames
            and any(name in reader.fieldnames for name in cols)
        ):
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
            current_species = ""
            current_ion = 0
            for raw_line in f:
                stripped = raw_line.strip()
                heading = re.fullmatch(
                    r"([A-Za-z]{1,2})(?:\s+(I{1,2}|[12]))?\s*:\s*",
                    stripped,
                    re.IGNORECASE,
                )
                if heading:
                    current_species = heading.group(1).capitalize()
                    ion_text = str(heading.group(2) or "I").upper()
                    current_ion = 2 if ion_text in ("II", "2") else 1
                    continue
                parts = stripped.replace(",", ".").split()
                if not parts:
                    continue
                try:
                    rows.append(
                        TemplateLine(
                            wavelen=float(parts[0]),
                            specie=current_species,
                            ion=current_ion,
                        )
                    )
                except Exception:
                    pass
    return rows


def analytical_line_library_key(line):
    species = str(getattr(line, "specie", "") or "").strip().capitalize()
    ion = safe_int(getattr(line, "ion", 0), 0)
    wavelength = safe_float(getattr(line, "wavelen", 0.0), 0.0)
    if not species or ion not in (1, 2) or wavelength <= 0.0:
        return None
    return species, ion, round(wavelength, 6)


def clean_analytical_line(line):
    key = analytical_line_library_key(line)
    if key is None:
        return None
    species, ion, _rounded_wavelength = key
    return TemplateLine(
        wavelen=safe_float(getattr(line, "wavelen", 0.0), 0.0),
        specie=species,
        ion=ion,
    )


def merge_analytical_line_libraries(existing, additions):
    merged = []
    keys = set()
    skipped = 0
    added = 0
    for line in list(existing or []):
        clean = clean_analytical_line(line)
        key = analytical_line_library_key(clean) if clean is not None else None
        if key is None:
            skipped += 1
            continue
        if key in keys:
            continue
        keys.add(key)
        merged.append(clean)
    for line in list(additions or []):
        clean = clean_analytical_line(line)
        key = analytical_line_library_key(clean) if clean is not None else None
        if key is None:
            skipped += 1
            continue
        if key in keys:
            continue
        keys.add(key)
        merged.append(clean)
        added += 1
    return merged, added, skipped


def save_analytical_line_library(filename, lines):
    clean_lines, _added, skipped = merge_analytical_line_libraries([], lines)
    groups = {}
    for line in clean_lines:
        key = (line.specie, line.ion)
        groups.setdefault(key, []).append(line.wavelen)
    output = []
    for (species, ion), wavelengths in groups.items():
        output.append(f"{species} {_roman_ion(ion)}:")
        for wavelength in wavelengths:
            text = f"{wavelength:.8f}".rstrip("0").rstrip(".")
            output.append(text)
        output.append("")
    path = Path(filename)
    path.write_text("\n".join(output).rstrip() + "\n", encoding="ascii")
    return len(clean_lines), skipped


def load_or_create_analytical_line_library():
    custom_path = app_base_dir() / ANALYTICAL_LINE_LIBRARY_FILENAME
    default_path = app_base_dir() / DEFAULT_ANALYTICAL_LINE_LIBRARY_FILENAME
    if not custom_path.exists() and default_path.exists():
        shutil.copy2(default_path, custom_path)
    source_path = custom_path if custom_path.exists() else default_path
    if not source_path.exists():
        return [], custom_path
    loaded = load_template_lines(source_path, RetroTemplateManager.columns)
    clean_lines, _added, _skipped = merge_analytical_line_libraries([], loaded)
    return clean_lines, custom_path


def spectrum_contains_halpha(spectrum):
    wavelengths = [
        safe_float(value, float("nan"))
        for value in list(getattr(spectrum, "x", []) or [])
    ]
    wavelengths = [value for value in wavelengths if math.isfinite(value)]
    if not wavelengths:
        return False
    center = HALPHA_CENTER_NM if max(wavelengths) < 1500.0 else HALPHA_CENTER_NM * 10.0
    return min(wavelengths) <= center <= max(wavelengths)


def _clone_template_line(line):
    return TemplateLine(
        wavelen=getattr(line, "wavelen", 0.0),
        specie=getattr(line, "specie", ""),
        ion=getattr(line, "ion", 0),
        asswavelen=getattr(line, "asswavelen", 0.0),
        inte=getattr(line, "inte", 0.0),
        ei=getattr(line, "ei", 0.0),
        wg=getattr(line, "wg", 0.0),
        wl=getattr(line, "wl", 0.0),
        ek=getattr(line, "ek", 0.0),
        aki=getattr(line, "aki", 0.0),
        gk=getattr(line, "gk", 0),
        gi=getattr(line, "gi", 0),
        fitwavelen=getattr(line, "fitwavelen", 0.0),
        templint=getattr(line, "templint", 0.0),
        error_inte=getattr(line, "error_inte", 0.0),
        acc=getattr(line, "acc", 0),
        fit_profile=getattr(line, "fit_profile", ""),
    )


def _clone_template_lines(lines):
    return [_clone_template_line(line) for line in list(lines or [])]


def _multifit_sheet_base_name(line, index):
    specie = str(getattr(line, "specie", "") or "").strip()
    ion = safe_int(getattr(line, "ion", 0), 0)
    asswavelen = safe_float(getattr(line, "asswavelen", 0.0), 0.0)
    wavelen = safe_float(getattr(line, "wavelen", 0.0), 0.0)
    if specie:
        parts = [specie]
        if ion:
            parts.append(_roman_ion(ion))
        parts.append(f"{asswavelen or wavelen:.6g}")
        label = " ".join(part for part in parts if part)
    else:
        label = f"{wavelen:.6g}" if wavelen else ""
    if label:
        return label
    return f"Row_{index + 1}"


def _excel_safe_sheet_name(name, used_names):
    text = re.sub(r"[\[\]:*?/\\]", "_", str(name or "").strip())
    text = text.strip("'")
    if not text:
        text = "Sheet"
    text = text[:31]
    base = text
    suffix = 1
    used_key = text.lower()
    while not text or used_key in used_names:
        extra = f"_{suffix}"
        text = f"{base[:31 - len(extra)]}{extra}" if len(base) + len(extra) > 31 else f"{base}{extra}"
        text = text[:31] or "Sheet"
        used_key = text.lower()
        suffix += 1
    used_names.add(used_key)
    return text


def _format_excel_fit_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        if text.upper() == "ERROR":
            return "ERROR"
        try:
            value = float(text)
        except Exception:
            return value
    try:
        rounded = round(float(value), 3)
    except Exception:
        return value
    if abs(rounded - round(rounded)) < 1e-12:
        return int(round(rounded))
    return rounded


def _multifit_spectrum_integral(spectrum):
    try:
        x_values = getattr(spectrum, "x", None)
        y_values = getattr(spectrum, "y", None)
        if x_values is None or y_values is None:
            return "ERROR"
        n = min(len(x_values), len(y_values))
        if n <= 0:
            return "ERROR"
        xstats = _population_statistics(list(x_values[:n]))
        ystats = _population_statistics(list(y_values[:n]))
        avg_x = xstats.get("Average")
        avg_y = ystats.get("Average")
        if avg_x is None or avg_y is None:
            return "ERROR"
        product = float(avg_x) * float(avg_y)
        if not math.isfinite(product):
            return "ERROR"
        return product
    except Exception:
        return "ERROR"


def _multifit_normalized_inte(inte_value, spectrum_integral):
    if inte_value is None:
        return ""
    if isinstance(inte_value, str):
        text = inte_value.strip()
        if not text:
            return ""
        if text.upper() == "ERROR":
            return "ERROR"
        try:
            inte_value = float(text)
        except Exception:
            return "ERROR"
    if isinstance(spectrum_integral, str):
        text = spectrum_integral.strip()
        if not text:
            return "ERROR"
        if text.upper() == "ERROR":
            return "ERROR"
        try:
            spectrum_integral = float(text)
        except Exception:
            return "ERROR"
    try:
        numerator = float(inte_value)
        denominator = float(spectrum_integral)
    except Exception:
        return "ERROR"
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator == 0.0:
        return "ERROR"
    normalized = numerator / denominator
    if not math.isfinite(normalized):
        return "ERROR"
    return normalized


def _multifit_group_from_anchor(sorted_rows, anchor_pos, delta_min):
    if anchor_pos < 0 or anchor_pos >= len(sorted_rows):
        return [], anchor_pos + 1
    positions = [anchor_pos]
    pos = anchor_pos + 1
    while pos < len(sorted_rows) and abs(sorted_rows[pos][1] - sorted_rows[pos - 1][1]) < delta_min:
        positions.append(pos)
        pos += 1
    return [sorted_rows[p] for p in positions], pos


def _multifit_expand_limits(lo, hi, data_min, data_max):
    current_width = abs(hi - lo)
    full_width = data_max - data_min
    if current_width <= 0 or full_width <= 0:
        return lo, hi, False
    center = (lo + hi) / 2.0
    new_width = min(current_width * 1.5, full_width)
    new_lo = center - new_width / 2.0
    new_hi = center + new_width / 2.0
    if new_lo < data_min:
        new_lo = data_min
        new_hi = min(data_max, data_min + new_width)
    if new_hi > data_max:
        new_hi = data_max
        new_lo = max(data_min, data_max - new_width)
    new_lo, new_hi = sorted((new_lo, new_hi))
    return new_lo, new_hi, (new_lo, new_hi) != (lo, hi)


def _multifit_build_snapshot(spectrum, lines, options, xlim):
    x_values = list(getattr(spectrum, "x", []) or [])
    y_values = list(getattr(spectrum, "y", []) or [])
    saved_fit_range = _voigt_saved_fit_range(options, lines)
    return {
        "spectrum": {"x": x_values, "y": y_values},
        "xlim": tuple(xlim),
        "ylim": (0.0, 1.0),
        "fit_range_locked": bool(saved_fit_range),
        "line_overrides": {},
        "lines": [
            {
                "key": id(t),
                "wavelen": safe_float(getattr(t, "wavelen", 0.0), 0.0),
                "fitwavelen": safe_float(getattr(t, "fitwavelen", 0.0), 0.0),
                "wg": safe_float(getattr(t, "wg", 0.0), 0.0),
                "wl": safe_float(getattr(t, "wl", 0.0), 0.0),
                "specie": getattr(t, "specie", ""),
                "ion": safe_int(getattr(t, "ion", 0), 0),
            }
            for t in list(lines)
        ],
        "options": {
            "voigt_baseline_mode": _voigt_baseline_mode(options),
            "voigt_fit_ranges": getattr(options, "voigt_fit_ranges", "{}"),
            "fixed_wg": safe_float(getattr(options, "fixed_wg", 0.5), 0.5),
            "fixed_wl": safe_float(getattr(options, "fixed_wl", 0.5), 0.5),
            "fix_wg": bool(getattr(options, "fix_wg", False)),
            "fix_wl": bool(getattr(options, "fix_wl", False)),
            "fix_wavelength": bool(getattr(options, "fix_wavelength", False)),
            "search_range": safe_float(
                getattr(options, "search_range", 0.1),
                0.1,
            ),
            "iterations": safe_int(getattr(options, "iterations", 20), 20),
        },
    }


def _multifit_fit_group(spectrum, group_rows, options):
    if np is None:
        return False, "NumPy is not available.", None

    x_values = list(getattr(spectrum, "x", []) or [])
    y_values = list(getattr(spectrum, "y", []) or [])
    if not x_values or not y_values:
        return False, "Load a spectrum first.", None

    delta_min = max(safe_float(getattr(options, "delta_min", 1.0), 1.0), 1e-9)
    data_min = min(x_values)
    data_max = max(x_values)
    group_lines = [line for _idx, _wave, line in group_rows]
    saved_range = _voigt_saved_fit_range(options, group_lines)
    if saved_range:
        lo, hi = saved_range
    else:
        lo = group_rows[0][1] - delta_min
        hi = group_rows[-1][1] + delta_min
    min_points = _voigt_free_parameter_count([line for _idx, _wave, line in group_rows], options=options)

    while True:
        point_count = sum(1 for x in x_values if lo <= x <= hi)
        if point_count >= min_points:
            break
        new_lo, new_hi, expanded = _multifit_expand_limits(lo, hi, data_min, data_max)
        if not expanded:
            return False, f"Too few spectrum points for Voigt fit: {point_count} found, {min_points} required.", None
        lo, hi = new_lo, new_hi

    snapshot = _multifit_build_snapshot(spectrum, group_lines, options, (lo, hi))
    try:
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None
        result = RetroFitManagerWindow._run_voigt_fit_snapshot(
            runner,
            snapshot,
            lambda: False,
        )
    except Exception as exc:
        return False, str(exc), None
    status = str(result.get("status", "error"))
    message = str(result.get("message", "Fit failed"))
    payload = result.get("payload")
    if status != "success" or not payload:
        return False, message, None
    by_key = {item.get("key"): item for item in list((payload or {}).get("fit_values") or [])}
    results = {}
    for orig_idx, _wave, line in group_rows:
        item = by_key.get(id(line))
        if not item or not item.get("quality_ok", True):
            continue
        results[orig_idx] = {
            "Inte": float(item.get("integrated_area", 0.0)),
            "wg": abs(float(item.get("gaussian_width", 0.0))),
            "wl": abs(float(item.get("lorentzian_width", 0.0))),
        }
    return True, message, results


def _multifit_results_for_spectrum(spectrum, template_lines, options):
    rows = {
        idx: {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
        for idx in range(len(template_lines))
    }
    x_values = list(getattr(spectrum, "x", []) or [])
    y_values = list(getattr(spectrum, "y", []) or [])
    if len(x_values) < 8 or len(y_values) < 8:
        return rows
    indexed_lines = []
    for idx, line in enumerate(list(template_lines or [])):
        try:
            wave = safe_float(getattr(line, "wavelen", 0.0), 0.0)
        except Exception:
            wave = 0.0
        if not wave:
            continue
        indexed_lines.append((idx, wave, _clone_template_line(line)))
    if not indexed_lines:
        return rows
    indexed_lines.sort(key=lambda item: item[1])
    delta_min = max(safe_float(getattr(options, "delta_min", 1.0), 1.0), 1e-9)
    pos = 0
    while pos < len(indexed_lines):
        group, next_pos = _multifit_group_from_anchor(indexed_lines, pos, delta_min)
        if not group:
            pos += 1
            continue
        ok, _message, group_results = _multifit_fit_group(spectrum, group, options)
        if ok and group_results:
            for idx, values in group_results.items():
                rows[idx] = values
        else:
            for idx, _wave, _line in group:
                rows[idx] = {"Inte": "ERROR", "wg": "ERROR", "wl": "ERROR"}
        pos = next_pos if next_pos > pos else pos + 1
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
    spectra = (
        [sp for sp in self.spectra if getattr(sp, "visible", True)]
        if getattr(self, "independent_window_mode", False)
        else list(self.spectra[:1])
    )
    ys = [
        y
        for sp in spectra
        for x, y in zip(sp.x, sp.y)
        if lo <= x <= hi
    ]
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

def restore_factory_settings(self):
    confirmed = _askyesno(
        self,
        "Restore Factory Settings",
        (
            "Restore all pyLIBS settings to their factory values?\n\n"
            "This resets saved response files, dark/background options, the "
            "selected database, wavelength calibrations, fit settings and "
            "window positions. Spectrum and database files on disk are not deleted.\n\n"
            "The current settings file will be backed up. Restart pyLIBS after "
            "the reset to use the factory settings."
        ),
    )
    if not confirmed:
        return False
    ini_path = resource_path("pyLIBS.ini")
    backup_path = None
    try:
        if ini_path.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = ini_path.with_name(f"pyLIBS.ini.backup-{stamp}")
            shutil.copy2(ini_path, backup_path)
        factory_options = AppOptions()
        load_pylibs_ini(factory_options, "pyLIBS.ini.example")
        factory_options.window_positions = {}
        saved_path = save_pylibs_ini(factory_options, "pyLIBS.ini")
    except Exception as exc:
        _showerror(self, "Restore Factory Settings", str(exc))
        return False
    backup_text = (
        f"\nBackup: {backup_path}"
        if backup_path is not None
        else "\nNo previous settings file was present."
    )
    self.status(f"Factory settings restored in {saved_path}; restart pyLIBS")
    _showinfo(
        self,
        "Restore Factory Settings",
        (
            f"Factory settings were written to:\n{saved_path}"
            f"{backup_text}\n\nRestart pyLIBS now. The currently displayed "
            "spectra have not been modified."
        ),
    )
    return True

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
    sync = getattr(self.cflibs_window, "sync_session_inputs", None)
    if callable(sync):
        sync()
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
    rectangle = getattr(self, "_zoom_rectangle", None)
    if rectangle is not None:
        try:
            rectangle.remove()
        except Exception:
            pass
        self._zoom_rectangle = None
    if not press or event.xdata is None or event.ydata is None or event.inaxes is not getattr(self, "ax", None) or not getattr(self, "ax", None):
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
        return
    button, x0, y0, px0, py0, old_xlim, old_ylim = press
    dxpix = (event.x or px0) - px0
    dypix = (event.y or py0) - py0
    if abs(dxpix) < 6 or abs(dypix) < 6:
        self._nav_dragged = False
        self.canvas.draw_idle()
        return
    if button == 1:
        # A box zoom works in every drag direction. Full view remains the F4
        # command/toolbar button, so the gesture is no longer directional.
        self.ax.set_xlim(min(x0, event.xdata), max(x0, event.xdata))
        self.ax.set_ylim(min(y0, event.ydata), max(y0, event.ydata))
        self.canvas.draw_idle(); self._update_xscroll()
    elif button == 3:
        dx = event.xdata - x0
        dy = event.ydata - y0
        self.ax.set_xlim(old_xlim[0]-dx, old_xlim[1]-dx)
        self.ax.set_ylim(old_ylim[0]-dy, old_ylim[1]-dy)
        self.canvas.draw_idle(); self._update_xscroll()
    self._nav_dragged = True

def _zoom_limits_around_cursor(limits, cursor, factor, logarithmic=False):
    """Scale one axis about the cursor while preserving its relative position."""
    lo, hi = map(float, limits)
    cursor = float(cursor)
    if not math.isfinite(lo + hi + cursor) or hi <= lo or factor <= 0.0:
        return lo, hi
    if logarithmic:
        if lo <= 0.0 or hi <= 0.0 or cursor <= 0.0:
            return lo, hi
        lo_t, hi_t, cursor_t = math.log10(lo), math.log10(hi), math.log10(cursor)
        new_lo = cursor_t - (cursor_t - lo_t) * factor
        new_hi = cursor_t + (hi_t - cursor_t) * factor
        return 10.0 ** new_lo, 10.0 ** new_hi
    return (
        cursor - (cursor - lo) * factor,
        cursor + (hi - cursor) * factor,
    )

def _scroll_zoom(self, event):
    """Mouse-wheel zoom centred on the pointer.

    Wheel zooms both axes; Shift+wheel changes X only and Ctrl+wheel Y only.
    The fitted curve is deliberately retained while navigating.
    """
    if (
        not getattr(self, "ax", None)
        or event.inaxes is not self.ax
        or event.xdata is None
        or event.ydata is None
    ):
        return
    direction = getattr(event, "button", None)
    if direction == "up":
        factor = 0.80
    elif direction == "down":
        factor = 1.25
    else:
        step = safe_float(getattr(event, "step", 0.0), 0.0)
        if step == 0.0:
            return
        factor = 0.80 if step > 0.0 else 1.25
    key = str(getattr(event, "key", "") or "").lower()
    zoom_x = "control" not in key
    zoom_y = "shift" not in key
    if zoom_x:
        self.ax.set_xlim(*_zoom_limits_around_cursor(
            self.ax.get_xlim(),
            event.xdata,
            factor,
            logarithmic=getattr(self, "view_log_x", False),
        ))
    if zoom_y:
        self.ax.set_ylim(*_zoom_limits_around_cursor(
            self.ax.get_ylim(),
            event.ydata,
            factor,
            logarithmic=getattr(self, "view_log_y", False),
        ))
    self.canvas.draw_idle()
    self._update_xscroll()

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
    close_template_from_menu, clear_template_data, invalidate_cflibs_results, invalidate_self_absorption_analysis, notify_template_changed, _nearest_spectrum_point, _template_match_index, _merge_template_line, add_template_peak_at, delete_template_peak_at, _click, find_peaks_basic, show_manual, show_about, on_close,
    ask_open_spectrum, ask_import_multiple, ask_save_spectrum, full_x, full_y,
    full_y_main_visible_x,
    expand_x_50, full_scale, show_options, restore_factory_settings, show_vertical_shift, show_spectrum_shift, show_spectrum_offset, show_batch_statistics, show_statistics,
    show_auto_element_identification, show_saha_boltzmann, show_cf_libs,
    show_sac_window, load_template_file, save_template_file, _show_fit_manager,
    _full_x_limits, _update_xscroll, _xscroll_changed, _zoom_out_from_box, _release, _scroll_zoom,
    goto_wavelength, show_goto_dialog,
]
for _m in _RETRO_METHODS:
    setattr(MainWindow, _m.__name__, _m)

if __name__ == "__main__":
    root = MainWindow()
    root.install_retro_ui()
    root.mainloop()
