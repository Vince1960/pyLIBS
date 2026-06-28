"""Toolbar helpers for pyLIBS."""

from __future__ import annotations

from tkinter import ttk

from pylibs.gui.helpers import ToolbarTooltip
from pylibs.gui.icons import load_toolbar_icon


def build_retro_toolbar(self):
    """Build original-like toolbar order."""
    if hasattr(self, "retro_toolbar"):
        return
    self.retro_toolbar = ttk.Frame(self)
    # Try to place toolbar at top without disturbing existing content too much.
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
        ("Single Fit", self.show_single_fit_manager),
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
        "Single Fit": "fit-single.png",
        "Saha Boltzmann": "calculator.png",
        "CF LIBS": "database.png",
    }
    icon_fallbacks = {
        "Full Y": "zoom_y_out.png",
        "Full X": "zoom_x_out.png",
        "Autofit": "fit.png",
        "Manual Fit": "fit.png",
        "Single Fit": "fit_single.png",
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
