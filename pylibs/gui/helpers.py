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
    restore_lift_focus(parent)
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


def restore_lift_focus(win, parent=None):
    """Restore an existing toplevel and bring it to the foreground."""
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


def center_window(win, parent=None):
    """Center a toplevel on the current screen without changing its size."""
    try:
        if win is None or not win.winfo_exists():
            return False
    except Exception:
        return False
    try:
        win.update_idletasks()
        width = max(1, win.winfo_width() or win.winfo_reqwidth())
        height = max(1, win.winfo_height() or win.winfo_reqheight())
        if parent is not None and getattr(parent, "winfo_exists", lambda: False)():
            screen_w = max(1, parent.winfo_screenwidth())
            screen_h = max(1, parent.winfo_screenheight())
        else:
            screen_w = max(1, win.winfo_screenwidth())
            screen_h = max(1, win.winfo_screenheight())
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        win.geometry(f"+{x}+{y}")
        return True
    except Exception:
        return False


def show_existing_or_create(owner, attr_name, factory, *, refresh=None, parent=None, center=True):
    """Return the existing single-instance window or create and center it."""
    win = getattr(owner, attr_name, None)
    exists = False
    try:
        exists = win is not None and win.winfo_exists()
    except Exception:
        exists = False
    if not exists:
        win = factory()
        setattr(owner, attr_name, win)
        if center:
            center_window(win, parent or owner)
        restore_lift_focus(win, parent or owner)
        return win
    if callable(refresh):
        try:
            refresh(win)
        except TypeError:
            refresh()
        except Exception:
            pass
    restore_lift_focus(win, parent or owner)
    return win


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
