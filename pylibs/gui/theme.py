"""Modern light theme for pyLIBS-dev (ttk 'clam' based, no extra dependency)."""

from __future__ import annotations

import configparser
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from pylibs.utils.paths import app_base_dir, resource_path

UI_INI = "pyLIBS_ui.ini"

PALETTE = {
    "bg": "#F3F5F9",          # window background
    "surface": "#FFFFFF",     # entries, tables, menus
    "border": "#CBD3DF",
    "border_dark": "#A9B4C4",
    "text": "#1E293B",
    "muted": "#64748B",
    "accent": "#2563EB",
    "accent_light": "#DBEAFE",
    "hover": "#E6ECF5",
    "pressed": "#D3DDEC",
    "heading": "#E9EEF5",
    "toolbar": "#FFFFFF",
}


def ui_style() -> str:
    cp = configparser.ConfigParser()
    try:
        cp.read(resource_path(UI_INI), encoding="utf-8")
        s = cp.get("Interface", "style", fallback="modern").strip().lower()
        return s if s in ("modern", "classic") else "modern"
    except Exception:
        return "modern"


def set_ui_style(style: str) -> bool:
    if style not in ("modern", "classic"):
        return False
    cp = configparser.ConfigParser()
    path = app_base_dir() / UI_INI
    try:
        cp.read(path, encoding="utf-8")
        if not cp.has_section("Interface"):
            cp.add_section("Interface")
        cp.set("Interface", "style", style)
        with open(path, "w", encoding="utf-8") as fh:
            cp.write(fh)
        return True
    except Exception:
        return False


def _family(root) -> str:
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()
    for f in ("Segoe UI", "Inter", "Noto Sans", "Ubuntu", "DejaVu Sans", "Helvetica"):
        if f in fams:
            return f
    return "TkDefaultFont"


def icon_scale(root) -> float:
    """Screen scale relative to 96 dpi (1.0, 1.25, 1.5 ...)."""
    try:
        return max(1.0, float(root.tk.call("tk", "scaling")) / (96.0 / 72.0))
    except Exception:
        return 1.0


def apply_modern_theme(root) -> str:
    """Apply the modern theme to the whole application. Returns the font family used."""
    p = PALETTE
    fam = _family(root)
    size = 9
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont",
                 "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
        try:
            f = tkfont.nametofont(name, root)
            f.configure(family=fam, size=size if name not in ("TkSmallCaptionFont", "TkTooltipFont") else size - 1)
            if name == "TkHeadingFont":
                f.configure(weight="bold")
        except Exception:
            pass
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    base = (fam, size)
    style.configure(".", font=base, background=p["bg"], foreground=p["text"], bordercolor=p["border"],
                    lightcolor=p["bg"], darkcolor=p["bg"], troughcolor="#E2E8F0", focuscolor=p["accent"],
                    selectbackground=p["accent_light"], selectforeground=p["text"], insertcolor=p["text"])
    style.configure("TFrame", background=p["bg"])
    style.configure("TLabel", background=p["bg"], foreground=p["text"])
    style.configure("TLabelframe", background=p["bg"], bordercolor=p["border"], relief="solid")
    style.configure("TLabelframe.Label", background=p["bg"], foreground=p["muted"], font=(fam, size, "bold"))
    style.configure("TSeparator", background=p["border"])
    # buttons
    style.configure("TButton", background=p["surface"], foreground=p["text"], bordercolor=p["border_dark"],
                    lightcolor=p["surface"], darkcolor=p["surface"], padding=(10, 3), relief="solid", borderwidth=1,
                    focusthickness=1)
    style.map("TButton",
              background=[("disabled", p["bg"]), ("pressed", p["pressed"]), ("active", p["hover"])],
              bordercolor=[("focus", p["accent"]), ("active", p["border_dark"])],
              foreground=[("disabled", "#A0AEC0")])
    style.configure("Accent.TButton", background=p["accent"], foreground="white", bordercolor=p["accent"],
                    lightcolor=p["accent"], darkcolor=p["accent"])
    style.map("Accent.TButton", background=[("pressed", "#1D4ED8"), ("active", "#3B82F6")],
              foreground=[("disabled", "#E2E8F0")])
    # flat toolbar buttons
    style.configure("Toolbar.TFrame", background=p["toolbar"])
    style.configure("Tool.TButton", background=p["toolbar"], bordercolor=p["toolbar"], lightcolor=p["toolbar"],
                    darkcolor=p["toolbar"], relief="flat", padding=(5, 4), focusthickness=0)
    style.map("Tool.TButton", background=[("pressed", p["pressed"]), ("active", p["hover"])],
              bordercolor=[("active", p["border"])], lightcolor=[("active", p["hover"])],
              darkcolor=[("active", p["hover"])])
    style.configure("ToolText.TButton", background=p["toolbar"], bordercolor=p["toolbar"], lightcolor=p["toolbar"],
                    darkcolor=p["toolbar"], relief="flat", padding=(6, 4), focusthickness=0)
    style.map("ToolText.TButton", background=[("pressed", p["pressed"]), ("active", p["hover"])],
              bordercolor=[("active", p["border"])])
    style.configure("Toolbar.TSeparator", background=p["border"])
    # inputs
    for w in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(w, fieldbackground=p["surface"], background=p["surface"], bordercolor=p["border_dark"],
                        lightcolor=p["surface"], darkcolor=p["surface"], padding=(4, 2), arrowcolor=p["muted"])
        style.map(w, bordercolor=[("focus", p["accent"])], lightcolor=[("focus", p["accent_light"])],
                  fieldbackground=[("readonly", p["surface"]), ("disabled", p["bg"])])
    style.configure("TCheckbutton", background=p["bg"], indicatorbackground=p["surface"], indicatorcolor=p["surface"])
    style.map("TCheckbutton", indicatorcolor=[("selected", p["accent"]), ("pressed", p["accent_light"])],
              background=[("active", p["bg"])])
    style.configure("TRadiobutton", background=p["bg"], indicatorcolor=p["surface"])
    style.map("TRadiobutton", indicatorcolor=[("selected", p["accent"])], background=[("active", p["bg"])])
    # tables
    style.configure("Treeview", background=p["surface"], fieldbackground=p["surface"], foreground=p["text"],
                    bordercolor=p["border"], rowheight=int(size * 2.6), font=base)
    style.map("Treeview", background=[("selected", p["accent_light"])], foreground=[("selected", p["text"])])
    style.configure("Treeview.Heading", background=p["heading"], foreground=p["text"], relief="flat",
                    bordercolor=p["border"], font=(fam, size, "bold"), padding=(4, 3))
    style.map("Treeview.Heading", background=[("active", p["hover"])])
    # notebook, scrollbars, panes
    style.configure("TNotebook", background=p["bg"], bordercolor=p["border"], tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=p["heading"], padding=(12, 4), bordercolor=p["border"])
    style.map("TNotebook.Tab", background=[("selected", p["surface"])], expand=[("selected", (1, 1, 1, 0))])
    for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(sb, background="#D5DCE6", troughcolor=p["bg"], bordercolor=p["bg"], arrowcolor=p["muted"],
                        lightcolor="#D5DCE6", darkcolor="#D5DCE6", gripcount=0)
        style.map(sb, background=[("active", "#B8C3D2")])
    style.configure("TPanedwindow", background=p["bg"])
    style.configure("Sash", sashthickness=6, gripcount=0, background=p["bg"])
    style.configure("TProgressbar", background=p["accent"], troughcolor="#E2E8F0", bordercolor=p["border"])
    style.configure("Status.TLabel", background=p["heading"], foreground=p["muted"], padding=(8, 3))
    # classic tk widgets and menus (option database: affects widgets created afterwards)
    root.option_add("*Menu.font", (fam, size))
    root.option_add("*Menu.background", p["surface"])
    root.option_add("*Menu.foreground", p["text"])
    root.option_add("*Menu.activeBackground", p["accent_light"])
    root.option_add("*Menu.activeForeground", p["text"])
    root.option_add("*Menu.selectColor", p["accent"])
    root.option_add("*Menu.relief", "flat")
    root.option_add("*Menu.borderWidth", 1)
    root.option_add("*Menu.activeBorderWidth", 0)
    root.option_add("*Toplevel.background", p["bg"])
    root.option_add("*Frame.background", p["bg"])
    root.option_add("*Label.background", p["bg"])
    root.option_add("*Label.foreground", p["text"])
    root.option_add("*Button.background", p["surface"])
    root.option_add("*Button.activeBackground", p["hover"])
    root.option_add("*Button.relief", "solid")
    root.option_add("*Button.borderWidth", 1)
    root.option_add("*Entry.background", p["surface"])
    root.option_add("*Entry.relief", "solid")
    root.option_add("*Entry.borderWidth", 1)
    root.option_add("*Text.font", ("Consolas" if "Consolas" in tkfont.families(root) else "TkFixedFont", size))
    root.option_add("*Text.background", p["surface"])
    root.option_add("*Text.relief", "flat")
    root.option_add("*Text.highlightThickness", 1)
    root.option_add("*Text.highlightColor", p["accent"])
    root.option_add("*Text.highlightBackground", p["border"])
    root.option_add("*Listbox.background", p["surface"])
    root.option_add("*Listbox.selectBackground", p["accent_light"])
    root.option_add("*Listbox.selectForeground", p["text"])
    root.option_add("*Listbox.relief", "flat")
    root.option_add("*Listbox.font", base)
    root.option_add("*TCombobox*Listbox.font", base)
    root.option_add("*TCombobox*Listbox.selectBackground", p["accent_light"])
    root.option_add("*TCombobox*Listbox.selectForeground", p["text"])
    try:
        root.configure(background=p["bg"])
    except Exception:
        pass
    return fam
