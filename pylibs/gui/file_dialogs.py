"""Cross-platform file chooser interface used throughout pyLIBS.

Linux uses Zenity's GTK file chooser when the executable is available. Windows
and macOS continue to use Tk's platform file dialogs, as does Linux when
Zenity cannot be started. Paths are passed as subprocess argument values (never
through a shell), so spaces, Unicode, quotes and shell metacharacters survive
unchanged.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog as _tk_filedialog
from typing import Any


_MULTIPLE_SEPARATOR = "\x1f"


def _zenity_path() -> str | None:
    if not sys.platform.startswith("linux"):
        return None
    return shutil.which("zenity")


def _widget_xid(parent: Any) -> str | None:
    """Return an X11 window id for Zenity's transient-parent option, if usable."""
    if parent is None or os.environ.get("WAYLAND_DISPLAY"):
        return None
    try:
        top = parent.winfo_toplevel()
        top.update_idletasks()
        xid = top.winfo_id()
    except Exception:
        return None
    return str(xid) if xid else None


def _append_parent(args: list[str], parent: Any) -> None:
    if parent is None:
        parent = tk._default_root
    xid = _widget_xid(parent)
    if xid:
        args.append(f"--attach={xid}")
    if parent is not None:
        # `--attach` remains useful with older Zenity releases; `--modal` is
        # honored by current releases even where explicit transient parenting
        # has been deprecated or is unavailable under Wayland.
        args.append("--modal")


def _initial_filename(kwargs: dict[str, Any], *, directory: bool = False) -> str | None:
    initialdir = kwargs.get("initialdir")
    initialfile = kwargs.get("initialfile")
    if initialfile:
        if os.path.isabs(os.fspath(initialfile)):
            return os.fspath(initialfile)
        return os.path.join(os.fspath(initialdir or os.getcwd()), os.fspath(initialfile))
    if initialdir:
        path = os.path.abspath(os.path.expanduser(os.fspath(initialdir)))
        return path if directory else path + os.sep
    return None


def _file_filter_args(filetypes: Any) -> list[str]:
    args: list[str] = []
    for item in filetypes or ():
        try:
            label, patterns = item[0], item[1]
        except (TypeError, IndexError):
            continue
        if isinstance(patterns, str):
            pattern_text = patterns
        else:
            pattern_text = " ".join(os.fspath(pattern) for pattern in patterns)
        pattern_text = " ".join(pattern_text.split())
        if pattern_text:
            args.append(f"--file-filter={label} | {pattern_text}")
    return args


def _run_zenity(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    executable = _zenity_path()
    if not executable:
        return None
    try:
        return subprocess.run(
            [executable, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _zenity_startup_failed(result: subprocess.CompletedProcess[str]) -> bool:
    diagnostic = (result.stderr or "").lower()
    return any(
        message in diagnostic
        for message in (
            "cannot open display",
            "failed to connect",
            "cannot connect",
            "no such file or directory",
            "unknown option",
            "unrecognized option",
            "invalid option",
        )
    )


def _gtk_file_dialog(mode: str, kwargs: dict[str, Any], *, multiple: bool = False) -> Any:
    args = ["--file-selection"]
    title = kwargs.get("title")
    if title:
        args.append(f"--title={title}")
    initial = _initial_filename(kwargs, directory=(mode == "directory"))
    if initial:
        args.append(f"--filename={initial}")
    if mode == "save":
        args.append("--save")
    elif mode == "directory":
        args.append("--directory")
    if multiple:
        args.extend(("--multiple", f"--separator={_MULTIPLE_SEPARATOR}"))
    if mode == "save":
        # Older Zenity versions use this flag; newer GTK file choosers perform
        # overwrite confirmation by default and mark the option deprecated.
        args.append("--confirm-overwrite")
    args.extend(_file_filter_args(kwargs.get("filetypes")))
    _append_parent(args, kwargs.get("parent"))

    result = _run_zenity(args)
    if result is None:
        return _fallback(mode, kwargs, multiple=multiple)
    if result.returncode == 1:
        # Zenity also uses status 1 for startup failures such as a missing
        # display. Ignore non-fatal warnings (for example deprecated options).
        if _zenity_startup_failed(result):
            return _fallback(mode, kwargs, multiple=multiple)
        return () if multiple else ""
    if result.returncode != 0:
        return _fallback(mode, kwargs, multiple=multiple)

    selected = result.stdout
    if selected.endswith("\n"):
        selected = selected[:-1]
    if multiple:
        paths = tuple(part for part in selected.split(_MULTIPLE_SEPARATOR) if part)
        return paths
    if mode == "save" and selected:
        extension = kwargs.get("defaultextension") or ""
        added_extension = bool(extension and not Path(selected).suffix)
        if added_extension:
            selected += extension if str(extension).startswith(".") else f".{extension}"
        # If the default extension changes the path after GTK's own overwrite
        # check, ask GTK to confirm the actual target explicitly.
        if added_extension and os.path.exists(selected):
            confirm_args = [
                "--question",
                f"--title={title or 'Confirm overwrite'}",
                f"--text=The file already exists:\n{selected}\n\nDo you want to replace it?",
                "--ok-label=Replace",
                "--cancel-label=Cancel",
            ]
            _append_parent(confirm_args, kwargs.get("parent"))
            confirmation = _run_zenity(confirm_args)
            if confirmation is None:
                return _fallback(mode, kwargs, multiple=multiple)
            if confirmation.returncode == 1 and _zenity_startup_failed(confirmation):
                return _fallback(mode, kwargs, multiple=multiple)
            if confirmation.returncode != 0:
                return ""
    return selected


def _fallback(mode: str, kwargs: dict[str, Any], *, multiple: bool = False) -> Any:
    if mode == "save":
        return _tk_filedialog.asksaveasfilename(**kwargs)
    if mode == "directory":
        return _tk_filedialog.askdirectory(**kwargs)
    if multiple:
        return _tk_filedialog.askopenfilenames(**kwargs)
    return _tk_filedialog.askopenfilename(**kwargs)


class FileDialogRouter:
    """Drop-in subset of tkinter.filedialog with a GTK backend on Linux."""

    def askopenfilename(self, **kwargs: Any) -> str:
        return _gtk_file_dialog("open", kwargs)

    def askopenfilenames(self, **kwargs: Any) -> tuple[str, ...]:
        return _gtk_file_dialog("open", kwargs, multiple=True)

    def asksaveasfilename(self, **kwargs: Any) -> str:
        return _gtk_file_dialog("save", kwargs)

    def askdirectory(self, **kwargs: Any) -> str:
        return _gtk_file_dialog("directory", kwargs)


filedialog = FileDialogRouter()
