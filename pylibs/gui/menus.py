"""Menu and shortcut helpers for pyLIBS."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pylibs.gui.icons import get_cached_menu_icon, load_toolbar_icon


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
    """Build the original-like LIBS++ menu tree."""
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
    self.view_grid_x_var = tk.BooleanVar(value=getattr(self, "view_grid_x", True))
    self.view_grid_y_var = tk.BooleanVar(value=getattr(self, "view_grid_y", True))
    self.view_log_x_var = tk.BooleanVar(value=getattr(self, "view_log_x", False))
    self.view_log_y_var = tk.BooleanVar(value=getattr(self, "view_log_y", False))
    _add_menu_checkbutton(self, view_menu, shortcut_items, "GridX", lambda: self.toggle_grid(axis="x"), self.view_grid_x_var, "Ctrl+Alt+X", "<Control-Alt-x>", "grid.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "GridY", lambda: self.toggle_grid(axis="y"), self.view_grid_y_var, "Ctrl+Alt+Y", "<Control-Alt-y>", "grid_xy.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "LogX", lambda: self.toggle_log(axis="x"), self.view_log_x_var, "Ctrl+Alt+G", "<Control-Alt-g>", "log_x.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "LogY", lambda: self.toggle_log(axis="y"), self.view_log_y_var, "Ctrl+Alt+L", "<Control-Alt-l>", "log_y.png")
    _add_menu_checkbutton(self, view_menu, shortcut_items, "Show Labels", self.toggle_labels, None, "Ctrl+Shift+W", "<Control-Shift-W>", "")
    view_menu.add_separator()
    _add_menu_command(self, view_menu, shortcut_items, "Auto X", self.full_x, "", "", "zoom_x_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Auto Y", self.full_y, "", "", "zoom_y_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Expand X 50%", self.expand_x_50, "F2", "<F2>", "zoom_x_in.png")
    _add_menu_command(self, view_menu, shortcut_items, "Full Y Scale", self.full_y, "F3", "<F3>", "zoom_y_out.png")
    _add_menu_command(self, view_menu, shortcut_items, "Show All", self.full_scale, "F4", "<F4>", "full_view.png")

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
    _add_menu_command(self, analysis_menu, shortcut_items, "Single Fit", self.show_single_fit_manager, "", "", "fit_single.png")
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
        "Ctrl+W: kept Edit > Swap Spectra; View > Show Labels uses Ctrl+Shift+W.",
    ]
    _bind_menu_shortcuts(self, shortcut_items)


def build_retro_toolbar(self):
    """Build original-like toolbar order."""
    if hasattr(self, "retro_toolbar"):
        return
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
