"""Icon loading helpers for pyLIBS menus and toolbar."""

from __future__ import annotations

import math
import tkinter as tk

from pylibs.utils.paths import find_icon_path


def get_cached_menu_icon(owner, filename, size=16):
    """Load and cache a menu icon without altering toolbar images."""
    if not hasattr(owner, "menu_icons"):
        owner.menu_icons = {}
    if not hasattr(owner, "menu_icon_files"):
        owner.menu_icon_files = {}
    if not hasattr(owner, "menu_missing_icons"):
        owner.menu_missing_icons = []
    key = (filename, size)
    if key in owner.menu_icons:
        return owner.menu_icons[key]
    icon_path = find_icon_path(filename)
    if not icon_path:
        if filename not in owner.menu_missing_icons:
            owner.menu_missing_icons.append(filename)
        return None
    try:
        image = tk.PhotoImage(file=str(icon_path))
        width = max(1, image.width())
        height = max(1, image.height())
        if width != size or height != size:
            # Existing icons are 24 px. zoom(2).subsample(3) gives a clean
            # 16 px menu copy while leaving the toolbar image untouched.
            if width == 24 and height == 24 and size == 16:
                image = image.zoom(2, 2).subsample(3, 3)
            elif width > size or height > size:
                factor = max(1, int(math.ceil(max(width / size, height / size))))
                image = image.subsample(factor, factor)
        owner.menu_icons[key] = image
        owner.menu_icon_files[filename] = str(icon_path)
        return image
    except Exception:
        if filename not in owner.menu_missing_icons:
            owner.menu_missing_icons.append(filename)
        return None


def find_icon_with_fallback(filename, fallback_filename=None):
    icon_path = find_icon_path(filename)
    if icon_path:
        return filename, icon_path
    if fallback_filename:
        fallback_path = find_icon_path(fallback_filename)
        if fallback_path:
            return fallback_filename, fallback_path
    return filename, None


def load_toolbar_icon(owner, label, filename, fallback_filename=None):
    icon_name, icon_path = find_icon_with_fallback(filename, fallback_filename)
    if not icon_path:
        return None, icon_name, None
    try:
        image = tk.PhotoImage(file=str(icon_path))
    except Exception:
        return None, icon_name, icon_path
    owner.toolbar_icons[label] = image
    owner.toolbar_icon_files[label] = str(icon_path)
    return image, icon_name, icon_path
