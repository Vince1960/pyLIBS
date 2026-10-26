from __future__ import annotations

import subprocess
from unittest.mock import patch

from pylibs.gui import file_dialogs


def _completed(stdout: str, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_linux_open_multiple_uses_zenity_and_preserves_paths():
    paths = ("/tmp/sp ace/échantillon[1].dat", "/tmp/autre; fichier.txt")
    with patch.object(file_dialogs.sys, "platform", "linux"), patch.object(
        file_dialogs.shutil, "which", return_value="/usr/bin/zenity"
    ), patch.object(
        file_dialogs.subprocess, "run", return_value=_completed("\x1f".join(paths))
    ) as run:
        result = file_dialogs.filedialog.askopenfilenames(
            title="Open spectra",
            initialdir="/tmp/start here",
            filetypes=[("Spectra", "*.dat *.txt"), ("All", "*.*")],
        )

    assert result == paths
    argv = run.call_args.args[0]
    assert argv[0] == "/usr/bin/zenity"
    assert "--multiple" in argv
    assert "--filename=/tmp/start here/" in argv
    assert "--file-filter=Spectra | *.dat *.txt" in argv


def test_linux_save_uses_save_mode_and_default_extension():
    with patch.object(file_dialogs.sys, "platform", "linux"), patch.object(
        file_dialogs.shutil, "which", return_value="/usr/bin/zenity"
    ), patch.object(
        file_dialogs.subprocess,
        "run",
        return_value=_completed("/tmp/hasil akhir"),
    ) as run:
        result = file_dialogs.filedialog.asksaveasfilename(
            initialdir="/tmp",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )

    assert result == "/tmp/hasil akhir.csv"
    argv = run.call_args.args[0]
    assert "--save" in argv
    assert "--confirm-overwrite" in argv
    assert "--file-filter=CSV | *.csv" in argv


def test_missing_zenity_falls_back_to_tk_dialog():
    with patch.object(file_dialogs.sys, "platform", "linux"), patch.object(
        file_dialogs.shutil, "which", return_value=None
    ), patch.object(
        file_dialogs._tk_filedialog,
        "askopenfilename",
        return_value="/tmp/選択.dat",
    ) as fallback:
        result = file_dialogs.filedialog.askopenfilename(
            initialdir="/tmp", filetypes=[("Data", "*.dat")]
        )

    assert result == "/tmp/選択.dat"
    fallback.assert_called_once()


def test_linux_directory_uses_gtk_directory_mode():
    with patch.object(file_dialogs.sys, "platform", "linux"), patch.object(
        file_dialogs.shutil, "which", return_value="/usr/bin/zenity"
    ), patch.object(
        file_dialogs.subprocess,
        "run",
        return_value=_completed("/tmp/output folder"),
    ) as run:
        result = file_dialogs.filedialog.askdirectory(
            initialdir="/tmp", title="Choose output"
        )

    assert result == "/tmp/output folder"
    argv = run.call_args.args[0]
    assert "--directory" in argv
    assert "--filename=/tmp" in argv


def test_spectrum_and_time_resolved_flows_share_the_router():
    import pyLIBS

    assert pyLIBS.filedialog is file_dialogs.filedialog
    assert pyLIBS.MainWindow.open_spectrum.__globals__["filedialog"] is file_dialogs.filedialog
    assert pyLIBS.MainWindow.save_spectrum.__globals__["filedialog"] is file_dialogs.filedialog
    assert pyLIBS.TimeResolvedSpectraDialog._choose.__globals__["filedialog"] is file_dialogs.filedialog
    assert pyLIBS.TimeResolvedSpectraDialog._choose_output.__globals__["filedialog"] is file_dialogs.filedialog
