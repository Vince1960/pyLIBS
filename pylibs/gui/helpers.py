"""Generic GUI helpers for pyLIBS."""

from __future__ import annotations

import tkinter as tk
import os
import re
import subprocess
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


def primary_monitor_geometry(win=None):
    """Return the primary monitor rectangle as ``(x, y, width, height)``.

    On X11, xrandr reports monitor origins in virtual-desktop coordinates. On
    other platforms, Tk's screen dimensions provide a safe single-screen
    fallback without adding a runtime dependency.
    """
    if os.name == "posix" and os.environ.get("DISPLAY"):
        try:
            result = subprocess.run(
                ["xrandr", "--listmonitors"], capture_output=True, text=True,
                timeout=2, check=False,
            )
            if result.returncode == 0:
                monitors = []
                for line in result.stdout.splitlines():
                    match = re.search(r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", line)
                    if match:
                        monitors.append(("+*" in line or "*+" in line,
                                         int(match.group(3)), int(match.group(4)),
                                         int(match.group(1)), int(match.group(2))))
                if monitors:
                    return next((m[1:] for m in monitors if m[0]), monitors[0][1:])
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    try:
        if win is not None:
            return 0, 0, max(1, int(win.winfo_screenwidth())), max(1, int(win.winfo_screenheight()))
    except Exception:
        pass
    return 0, 0, 1920, 1080


def center_window(win, parent=None):
    """Center a new toplevel on its parent or the primary monitor."""
    try:
        if win is None or not win.winfo_exists():
            return False
    except Exception:
        return False
    try:
        win.update_idletasks()
        width = max(1, win.winfo_width() or win.winfo_reqwidth())
        height = max(1, win.winfo_height() or win.winfo_reqheight())
        sx, sy, screen_w, screen_h = primary_monitor_geometry(win)
        x = sx + max(0, (screen_w - width) // 2)
        y = sy + max(0, (screen_h - height) // 2)
        if parent is not None and getattr(parent, "winfo_exists", lambda: False)():
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw = max(1, parent.winfo_width() or parent.winfo_reqwidth())
            ph = max(1, parent.winfo_height() or parent.winfo_reqheight())
            if px >= sx and py >= sy and px + pw <= sx + screen_w and py + ph <= sy + screen_h:
                x = px + (pw - width) // 2
                y = py + (ph - height) // 2
        x = min(max(x, sx), sx + max(0, screen_w - width))
        y = min(max(y, sy), sy + max(0, screen_h - height))
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


def add_context_help_button(parent, owner, title, message):
    """Create a compact help button without occupying the work area."""
    button = ttk.Button(
        parent,
        text="?",
        width=3,
        command=lambda: _showinfo(owner, title, message),
    )
    button._context_help_tooltip = ToolbarTooltip(button, f"Help: {title}")
    return button
