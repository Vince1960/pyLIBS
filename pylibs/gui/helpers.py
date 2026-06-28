"""Generic GUI helpers for pyLIBS."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from pylibs.utils.formatting import safe_int


def _messagebox_parent(owner):
    root = owner
    for attr in ("master_app", "app"):
        parent = getattr(owner, attr, None)
        if parent is not None:
            root = parent
            break
    try:
        focused = root.focus_get()
        if focused is not None:
            top = focused.winfo_toplevel()
            if top is not None and top.winfo_exists():
                return top
    except Exception:
        pass
    return root


def _prepare_messagebox_parent(owner):
    parent = _messagebox_parent(owner)
    try:
        parent.lift()
        parent.focus_force()
    except Exception:
        try:
            parent.focus_set()
        except Exception:
            pass
    return parent


def _showinfo(owner, title, message):
    return messagebox.showinfo(title, message, parent=_prepare_messagebox_parent(owner))


def _showwarning(owner, title, message):
    return messagebox.showwarning(title, message, parent=_prepare_messagebox_parent(owner))


def _showerror(owner, title, message):
    return messagebox.showerror(title, message, parent=_prepare_messagebox_parent(owner))


def _askyesno(owner, title, message):
    return messagebox.askyesno(title, message, parent=_prepare_messagebox_parent(owner))


def legacy_geometry_to_tk(value: str, default: str = "") -> str:
    """Convert old 'left top width height' geometry to Tk 'WxH+X+Y'."""
    parts = str(value).split()
    if len(parts) == 4:
        x, y, w, h = [safe_int(p, 0) for p in parts]
        if w > 0 and h > 0:
            return f"{w}x{h}+{max(0,x)}+{max(0,y)}"
    return default


class ToolbarTooltip:
    """Small tooltip helper for toolbar image buttons."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tip, text=self.text, relief="solid", borderwidth=1, padding=(4, 2))
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None
