from types import SimpleNamespace

import pytest

from pylibs.gui import helpers


@pytest.mark.parametrize(
    "monitor,expected",
    [
        ((0, 0, 1920, 1080), "+560+240"),
        ((-1920, 0, 1920, 1080), "+-1360+240"),
        ((1920, 0, 1600, 900), "+2320+150"),
        ((0, -1080, 1920, 1080), "+560+-840"),
        ((0, 120, 1920, 1080), "+560+360"),
    ],
)
def test_center_window_uses_primary_monitor_origin(monkeypatch, monitor, expected):
    monkeypatch.setattr(helpers, "primary_monitor_geometry", lambda _win: monitor)
    window = _Window()
    assert helpers.center_window(window)
    assert window.last_geometry == expected


def test_xrandr_primary_monitor_detection(monkeypatch):
    monkeypatch.setattr(helpers.os, "name", "posix")
    monkeypatch.setenv("DISPLAY", ":0")
    result = SimpleNamespace(
        returncode=0,
        stdout=("Monitors: 2\n 0: +DP-1 1920/509x1080/286+0+0\n"
                " 1: +*HDMI-1 2560/600x1440/340-2560-180\n"),
    )
    monkeypatch.setattr(helpers.subprocess, "run", lambda *a, **k: result)
    assert helpers.primary_monitor_geometry() == (-2560, -180, 2560, 1440)


def test_xrandr_fallback_uses_tk_screen_dimensions(monkeypatch):
    monkeypatch.setattr(helpers.os, "name", "posix")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(helpers.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert helpers.primary_monitor_geometry(_Window()) == (0, 0, 1600, 900)


class _Window:
    def __init__(self):
        self.last_geometry = None

    def winfo_exists(self):
        return True

    def update_idletasks(self):
        pass

    def winfo_width(self):
        return 800

    def winfo_height(self):
        return 600

    def winfo_reqwidth(self):
        return 800

    def winfo_reqheight(self):
        return 600

    def winfo_screenwidth(self):
        return 1600

    def winfo_screenheight(self):
        return 900

    def geometry(self, value):
        self.last_geometry = value


