import unittest
from types import SimpleNamespace

from pyLIBS import _release


class FakeAxis:
    def __init__(self):
        self.xlim = (0.0, 100.0)
        self.ylim = (0.0, 100.0)

    def get_xlim(self):
        return self.xlim

    def get_ylim(self):
        return self.ylim

    def set_xlim(self, *values):
        self.xlim = tuple(values)

    def set_ylim(self, *values):
        self.ylim = tuple(values)


class FakeCanvas:
    def __init__(self):
        self.draws = 0

    def draw_idle(self):
        self.draws += 1


class DirectionalZoomTests(unittest.TestCase):
    def make_app(self, button=1, x0=80, y0=80):
        app = SimpleNamespace()
        app.ax = FakeAxis()
        app.canvas = FakeCanvas()
        app._nav_press = (button, 20.0, 20.0, x0, y0, app.ax.get_xlim(), app.ax.get_ylim())
        app._zoom_rectangle = None
        app._update_xscroll = lambda: None
        app.clear_fit_artists = lambda: None
        app.full_scale = lambda: (app.ax.set_xlim(0.0, 100.0), app.ax.set_ylim(0.0, 100.0), app.canvas.draw_idle(), app._update_xscroll())
        return app

    def release(self, app, x, y, xdata, ydata, button=1):
        event = SimpleNamespace(
            x=x, y=y, xdata=xdata, ydata=ydata, button=button,
            inaxes=app.ax,
        )
        _release(app, event)

    def test_upper_left_to_lower_right_keeps_box_zoom(self):
        # Screen down corresponds to a smaller Matplotlib display y.
        app = self.make_app(x0=10, y0=90)
        app._nav_press = (1, 20.0, 80.0, 10, 90, app.ax.get_xlim(), app.ax.get_ylim())
        self.release(app, 80, 20, 80.0, 20.0)
        self.assertEqual(app.ax.get_xlim(), (20.0, 80.0))
        self.assertEqual(app.ax.get_ylim(), (20.0, 80.0))

    def test_lower_right_to_upper_left_resets_both_axes(self):
        app = self.make_app(x0=90, y0=10)
        app.ax.set_xlim(40.0, 50.0)
        app.ax.set_ylim(45.0, 55.0)
        self.release(app, 20, 80, 20.0, 80.0)
        self.assertEqual(app.ax.get_xlim(), (0.0, 100.0))
        self.assertEqual(app.ax.get_ylim(), (0.0, 100.0))

    def test_repeated_zoom_then_reverse_drag_resets(self):
        app = self.make_app(x0=10, y0=90)
        self.release(app, 80, 20, 80.0, 20.0)
        app._nav_press = (1, 30.0, 30.0, 10, 90, app.ax.get_xlim(), app.ax.get_ylim())
        self.release(app, 70, 40, 70.0, 40.0)
        app._nav_press = (1, 70.0, 40.0, 90, 10, app.ax.get_xlim(), app.ax.get_ylim())
        self.release(app, 20, 80, 20.0, 80.0)
        self.assertEqual(app.ax.get_xlim(), (0.0, 100.0))
        self.assertEqual(app.ax.get_ylim(), (0.0, 100.0))

    def test_small_drag_does_not_change_limits(self):
        app = self.make_app(x0=20, y0=20)
        self.release(app, 24, 24, 24.0, 24.0)
        self.assertEqual(app.ax.get_xlim(), (0.0, 100.0))
        self.assertEqual(app.ax.get_ylim(), (0.0, 100.0))

    def test_other_left_drag_direction_keeps_existing_box_zoom(self):
        app = self.make_app(x0=10, y0=20)
        app._nav_press = (1, 20.0, 20.0, 10, 20, app.ax.get_xlim(), app.ax.get_ylim())
        self.release(app, 80, 90, 80.0, 90.0)
        self.assertEqual(app.ax.get_xlim(), (20.0, 80.0))
        self.assertEqual(app.ax.get_ylim(), (20.0, 90.0))

    def test_right_button_pan_is_unchanged(self):
        app = self.make_app(button=3, x0=20, y0=20)
        app.ax.set_xlim(20.0, 80.0)
        app.ax.set_ylim(10.0, 70.0)
        app._nav_press = (3, 20.0, 20.0, 20, 20, app.ax.get_xlim(), app.ax.get_ylim())
        self.release(app, 50, 50, 30.0, 40.0, button=3)
        self.assertEqual(app.ax.get_xlim(), (10.0, 70.0))
        self.assertEqual(app.ax.get_ylim(), (-10.0, 50.0))


if __name__ == "__main__":
    unittest.main()
