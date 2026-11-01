"""Resolution-aware, workflow-grouped toolbar for pyLIBS."""

from __future__ import annotations

from tkinter import ttk

from pylibs.gui.helpers import ToolbarTooltip
from pylibs.gui.icons import load_toolbar_icon


def build_retro_toolbar(self):
    """Build the grouped toolbar while retaining every 1.2.1 toolbar action."""
    if getattr(self, "retro_toolbar", None) is not None:
        return
    modern = getattr(self, "ui_style", "modern") == "modern"
    self.retro_toolbar = ttk.Frame(
        self, style="Toolbar.TFrame" if modern else "TFrame",
        padding=(4, 2) if modern else 0,
    )
    try:
        self.retro_toolbar.pack(side="top", fill="x", before=self.children.get("!frame"))
    except Exception:
        self.retro_toolbar.pack(side="top", fill="x")
    if modern:
        self.retro_toolbar_line = ttk.Separator(self, orient="horizontal")
        try:
            self.retro_toolbar_line.pack(side="top", fill="x", after=self.retro_toolbar)
        except Exception:
            pass

    # None marks a visual group boundary. Base actions remain available,
    # including Response and Single Fit.
    buttons = [
        ("Open", self.ask_open_spectrum, "open.png"),
        ("Compare", self.compare_spectrum, "compare.png"),
        ("Append", self.ask_import_multiple, "append.png"),
        ("Save", self.ask_save_spectrum, "save.png"),
        ("Print", self.print_plot, "print.png"), None,
        ("Open Session", self.open_session, "session_open.png"),
        ("Save Session", self.save_session_as, "session_save.png"), None,
        ("Active Spectra", self.show_active_spectra, "Active_spectra.png"),
        ("Clear", self.clear_all_spectra, "clear.png"),
        ("Response", self.show_response_window, "calibration.png"), None,
        ("Full Y", self.full_y, "full_y.png"),
        ("Full X", self.full_x, "full_x.png"),
        ("Full Scale", self.full_scale, "full_view.png"), None,
        ("Load Template", self.load_template_from_menu, "load_template.png"),
        ("Show Template", self.show_template_manager, "show_template.png"), None,
        ("Trace", self.show_trace_lines, "trace.png"),
        ("Ne from Hα", self.show_ne_halpha, "H_alpha.png"),
        ("Auto Fit", self.show_auto_fit_manager, "fit_auto.png"),
        ("Manual Fit", self.show_retro_fit_manager, "fit_manual.png"),
        ("Single Fit", self.show_single_fit_manager, "fit-single.png"), None,
        ("Saha-Boltzmann", self.show_saha_boltzmann, "saha.png"),
        ("CF-LIBS", self.show_cf_libs, "cflibs.png"),
    ]
    optional = (
        ("LTE", "show_lte_check", "lte.png"),
        ("T–Ne", "show_selfconsistent", "tne.png"),
        ("Self-absorption", "show_self_absorption", "self_absorption.png"),
        ("Uncertainty", "show_uncertainty", "uncertainty.png"),
        ("Outliers", "show_outliers", "outliers.png"),
    )
    buttons.append(None)
    buttons.extend((label, getattr(self, method), icon) for label, method, icon in optional
                   if callable(getattr(self, method, None)))

    fallbacks = {
        "saha.png": "calculator.png", "cflibs.png": "database.png",
        "full_y.png": "zoom_y_out.png", "full_x.png": "zoom_x_out.png",
        "fit_auto.png": "fit.png", "fit_manual.png": "fit.png",
        "Active_spectra.png": "fit.png", "fit-single.png": "fit_single.png",
    }
    self.toolbar_icons = {}
    self.toolbar_icon_files = {}
    self.toolbar_tooltips = []
    self.toolbar_missing_icons = []
    tool_style = "Tool.TButton" if modern else "TButton"
    for item in buttons:
        if item is None:
            if modern:
                ttk.Separator(self.retro_toolbar, orient="vertical").pack(
                    side="left", fill="y", padx=4, pady=3
                )
            continue
        label, command, icon = item
        image, _name, _path = load_toolbar_icon(
            self, label, icon, fallbacks.get(icon)
        )
        if image is not None:
            button = ttk.Button(
                self.retro_toolbar, image=image, command=command,
                style=tool_style, takefocus=False,
            )
            button.pack(side="left", padx=0 if modern else 1, pady=1)
            self.toolbar_tooltips.append(ToolbarTooltip(button, label))
        else:
            self.toolbar_missing_icons.append(label)
            ttk.Button(
                self.retro_toolbar, text=label, command=command,
                style="ToolText.TButton" if modern else "TButton",
            ).pack(side="left", padx=1, pady=1)
