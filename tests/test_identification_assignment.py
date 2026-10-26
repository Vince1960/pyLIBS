import unittest
from types import SimpleNamespace

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from pyLIBS import LineIdentificationWindow, MainWindow, Spectrum
from pylibs.core.models import AtomicLine, TemplateLine


class FakeTree:
    def identify_row(self, _y):
        return "1"

    def focus(self):
        return "0"


class FakeIdentificationDialog:
    assign = LineIdentificationWindow.assign

    def __init__(self, master_app, atomic):
        self.master_app = master_app
        self.results = [AtomicLine(0, "X", 1), atomic]
        self.tree = FakeTree()
        self.wave_var = SimpleNamespace(get=lambda: "500.125")


class FakeDatabase:
    def enrich_line_from_element_table(self, atomic, **_kwargs):
        return atomic


class FakeMainApp:
    assign_atomic_line_to_nearest_template = MainWindow.assign_atomic_line_to_nearest_template

    def __init__(self, template_line):
        self.template_lines = [template_line]
        self.current_identification_wavelength = 123.0
        self.libs_db = FakeDatabase()
        self.options = SimpleNamespace(search_range=0.2)
        self.redraw_calls = []

    def copy_atomic_line_to_template_line(self, template, atomic):
        template.specie = atomic.specie
        template.ion = atomic.ion
        template.asswavelen = atomic.wavelen
        template.aki = atomic.aki
        template.ek = atomic.ek
        template.gk = atomic.gk
        template.gi = atomic.gi

    def notify_template_changed(self, redraw=False):
        pass

    def redraw(self, preserve_view=False):
        self.redraw_calls.append(preserve_view)

    def status(self, _message):
        pass

    def current_wavelength_unit_label(self):
        return "Å"


class FakePlotDatabase(FakeDatabase):
    pass


class PlotAssignmentApp:
    redraw = MainWindow.redraw
    _active_spectrum_y_at = MainWindow._active_spectrum_y_at
    assign_atomic_line_to_nearest_template = MainWindow.assign_atomic_line_to_nearest_template
    copy_atomic_line_to_template_line = MainWindow.copy_atomic_line_to_template_line

    def __init__(self):
        figure = Figure()
        self.canvas = FigureCanvasAgg(figure)
        self.ax = figure.add_subplot(111)
        self.spectra = [Spectrum([499.0, 500.0, 501.0], [0.0, 25.0, 0.0], "sample")]
        self.template_lines = [TemplateLine(wavelen=500.0, templint=25.0)]
        self.analysis_elements = set()
        self.independent_window_mode = False
        self.active_window = None
        self.view_log_x = self.view_log_y = False
        self.view_grid_x = self.view_grid_y = False
        self.plot_background = "#ffffff"
        self.plot_legend = None
        self.trace_markers = []
        self.element_markers = []
        self.fit_overlay = None
        self.fit_baseline_overlay = None
        self.fit_component_overlays = []
        self.fit_integration_bounds = []
        self.libs_db = FakePlotDatabase()
        self.options = SimpleNamespace(search_range=0.2)
        self.current_identification_wavelength = 500.0
        self.update_axis_labels = lambda: None
        self._update_xscroll = lambda: None
        self.notify_template_changed = lambda redraw=False: None
        self.status = lambda _message: None

    def current_wavelength_unit_label(self):
        return "Å"


class IdentificationAssignmentTests(unittest.TestCase):
    def test_double_click_targets_search_wavelength_and_selected_row(self):
        template = TemplateLine(wavelen=500.12)
        app = FakeMainApp(template)
        atomic = AtomicLine(500.13, "Fe", 1, ek=3.0, aki=1.2)
        dialog = FakeIdentificationDialog(app, atomic)

        dialog.assign(SimpleNamespace(y=40))

        self.assertEqual(app.current_identification_wavelength, 500.125)
        self.assertEqual(template.specie, "Fe")
        self.assertEqual(template.asswavelen, 500.13)
        self.assertIs(app.template_lines[0], template)
        self.assertEqual(app.redraw_calls, [True])

    def test_multiple_element_assignments_preserve_each_marked_wavelength(self):
        cases = ((400.12, "Fe", 1), (500.31, "Ca", 2), (600.45, "Mg", 1))
        for wavelength, element, ion in cases:
            with self.subTest(element=element, wavelength=wavelength):
                template = TemplateLine(wavelen=wavelength)
                app = FakeMainApp(template)
                atomic = AtomicLine(wavelength + 0.01, element, ion, ek=2.0, aki=0.5)
                dialog = FakeIdentificationDialog(app, atomic)
                dialog.wave_var = SimpleNamespace(get=lambda w=wavelength: str(w))

                dialog.assign(SimpleNamespace(y=10))

                self.assertEqual(template.wavelen, wavelength)
                self.assertEqual(template.specie, element)
                self.assertEqual(template.ion, ion)
                self.assertEqual(app.redraw_calls, [True])

    def test_blue_marker_becomes_persistent_gold_marker_and_label(self):
        app = PlotAssignmentApp()
        app.redraw()
        self.assertEqual(len(app.ax.collections), 1)
        self.assertEqual(app.ax.collections[0].get_colors()[0][:3].tolist(), [0.0, 0.0, 1.0])

        dialog = FakeIdentificationDialog(app, AtomicLine(500.0, "Fe", 1, ek=2.0, aki=1.0))
        dialog.assign(SimpleNamespace(y=10))

        self.assertEqual(len(app.template_lines), 1)
        self.assertEqual(app.template_lines[0].specie, "Fe")
        self.assertEqual(app.template_lines[0].wavelen, 500.0)
        self.assertEqual(len(app.ax.collections), 1)
        marker = app.ax.collections[0]
        self.assertEqual(marker.get_colors()[0][:3].tolist(), [1.0, 0.8431372549019608, 0.0])
        self.assertEqual(marker.get_linewidths()[0], 2.8)
        self.assertEqual(marker.get_zorder(), 10)
        self.assertTrue(any("Fe I 500.00" in text.get_text() for text in app.ax.texts))

        dialog.assign(SimpleNamespace(y=10))
        self.assertEqual(len(app.template_lines), 1)
        self.assertEqual(len(app.ax.collections), 1)
        self.assertEqual(sum("Fe I 500.00" in text.get_text() for text in app.ax.texts), 1)

        app.ax.set_xlim(499.5, 500.5)
        app.redraw(preserve_view=True)
        self.assertEqual(len(app.ax.collections), 1)
        self.assertEqual(app.ax.collections[0].get_colors()[0][:3].tolist(), [1.0, 0.8431372549019608, 0.0])
        self.assertTrue(any("Fe I 500.00" in text.get_text() for text in app.ax.texts))


if __name__ == "__main__":
    unittest.main()
