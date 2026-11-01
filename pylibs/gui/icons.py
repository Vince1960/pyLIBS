"""Icon loading helpers for pyLIBS menus and toolbar."""

from __future__ import annotations

import math
import tkinter as tk

from pylibs.utils.paths import app_base_dir, find_icon_path

_SIZES = (16, 20, 24, 32)


def _scaled_size(owner, size: int) -> int:
    try:
        scale = max(1.0, float(owner.tk.call("tk", "scaling")) / (96.0 / 72.0))
    except Exception:
        scale = 1.0
    desired = size * scale
    return min(_SIZES, key=lambda candidate: (abs(candidate - desired), -candidate))


def find_sized_icon(filename: str, size: int):
    if filename:
        for folder in ("icons", "Icons"):
            path = app_base_dir() / folder / str(size) / filename
            if path.exists():
                return path
    return find_icon_path(filename)


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
    effective_size = _scaled_size(owner, size)
    icon_path = find_sized_icon(filename, effective_size)
    if not icon_path:
        if filename not in owner.menu_missing_icons:
            owner.menu_missing_icons.append(filename)
        return None
    try:
        image = tk.PhotoImage(master=owner, file=str(icon_path))
        width = max(1, image.width())
        height = max(1, image.height())
        if width != effective_size or height != effective_size:
            # Existing icons are 24 px. zoom(2).subsample(3) gives a clean
            # 16 px menu copy while leaving the toolbar image untouched.
            if width == 24 and height == 24 and effective_size == 16:
                image = image.zoom(2, 2).subsample(3, 3)
            elif width > effective_size or height > effective_size:
                factor = max(1, int(math.ceil(max(width / effective_size, height / effective_size))))
                image = image.subsample(factor, factor)
        owner.menu_icons[key] = image
        owner.menu_icon_files[filename] = str(icon_path)
        return image
    except Exception:
        if filename not in owner.menu_missing_icons:
            owner.menu_missing_icons.append(filename)
        return None


def get_icon(owner, filename, size=16):
    return get_cached_menu_icon(owner, filename, size)


def find_icon_with_fallback(filename, fallback_filename=None, size=24):
    icon_path = find_sized_icon(filename, size)
    if icon_path:
        return filename, icon_path
    if fallback_filename:
        fallback_path = find_sized_icon(fallback_filename, size)
        if fallback_path:
            return fallback_filename, fallback_path
    return filename, None


def load_toolbar_icon(owner, label, filename, fallback_filename=None, size=24):
    effective_size = _scaled_size(owner, size)
    icon_name, icon_path = find_icon_with_fallback(filename, fallback_filename, effective_size)
    if not icon_path:
        return None, icon_name, None
    try:
        image = tk.PhotoImage(master=owner, file=str(icon_path))
    except Exception:
        return None, icon_name, icon_path
    owner.toolbar_icons[label] = image
    owner.toolbar_icon_files[label] = str(icon_path)
    return image, icon_name, icon_path
