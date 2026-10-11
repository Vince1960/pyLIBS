import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyLIBS import (
    AppOptions,
    MainWindow,
    Spectrum,
    TemplateLine,
    active_electron_density,
    clear_all_spectra,
    load_template_lines,
    merge_analytical_line_libraries,
    save_analytical_line_library,
    set_session_electron_density,
    spectrum_contains_halpha,
)


class AnalyticalLineLibraryTests(unittest.TestCase):
    @staticmethod
    def _clear_graph_app(*, remember_ne=False):
        library = [
            TemplateLine(340.36521, "Cd", 1),
            TemplateLine(405.78067, "Pb", 1),
        ]
        app = SimpleNamespace(
            spectra=[Spectrum([300.0, 301.0], [1.0, 2.0])],
            analytical_line_library=library,
            template_lines=[
                TemplateLine(
                    340.36521,
                    "Cd",
                    1,
                    inte=123.0,
                    fitwavelen=340.41,
                )
            ],
            analysis_elements={"Cd", "Pb"},
            options=AppOptions(remember_ne_for_series=remember_ne),
            session_ne=1.0589e16,
            session_ne_source="H-alpha fit",
            last_known_ne=None,
            last_known_ne_source=None,
            last_halpha_result={"available": True},
            last_saha_boltzmann={"representative_temperature": 1.0},
            last_cflibs_rows=[{"element": "Cd"}],
            last_cflibs_quality={"approved": True},
            session_temperature=1.0,
            session_temperature_source="Saha-Boltzmann",
            active_window=None,
        )
        app.clear_plot_annotations = lambda: None
        app.notify_template_changed = lambda redraw=False: None
        app.redraw = lambda: None
        app.status_messages = []
        app.status = app.status_messages.append
        app._replace_analysis_lines_from_library = lambda **kwargs: (
            MainWindow._replace_analysis_lines_from_library(app, **kwargs)
        )
        return app

    def test_included_library_contains_the_current_multielement_list(self):
        path = Path(__file__).resolve().parents[1] / "analytical_line_library.default.txt"
        lines = load_template_lines(path)
        counts = {}
        for line in lines:
            counts[(line.specie, line.ion)] = counts.get((line.specie, line.ion), 0) + 1

        self.assertEqual(len(lines), 23)
        self.assertEqual(
            counts,
            {
                ("Ni", 1): 4,
                ("Cd", 1): 4,
                ("Pb", 1): 5,
                ("Zn", 1): 2,
                ("Cu", 1): 4,
                ("Sn", 1): 4,
            },
        )

    def test_secondary_lists_are_merged_without_duplicate_lines(self):
        existing = [
            TemplateLine(340.36521, "Cd", 1),
            TemplateLine(405.78067, "Pb", 1),
        ]
        additions = [
            TemplateLine(340.3652101, "cd", 1),
            TemplateLine(326.10548, "Cd", 1),
            TemplateLine(0.0, "", 0),
        ]

        merged, added, skipped = merge_analytical_line_libraries(
            existing,
            additions,
        )

        self.assertEqual(len(merged), 3)
        self.assertEqual(added, 1)
        self.assertEqual(skipped, 1)
        self.assertTrue(
            any(
                line.specie == "Cd" and abs(line.wavelen - 326.10548) < 1.0e-9
                for line in merged
            )
        )

    def test_saved_library_contains_no_fit_or_intensity_results(self):
        line = TemplateLine(
            340.36521,
            "Cd",
            1,
            inte=123.0,
            fitwavelen=340.41,
            wl=0.2,
            wg=0.1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.txt"
            count, skipped = save_analytical_line_library(path, [line])
            loaded = load_template_lines(path)

        self.assertEqual(count, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].specie, "Cd")
        self.assertEqual(loaded[0].ion, 1)
        self.assertEqual(loaded[0].wavelen, 340.36521)
        self.assertEqual(loaded[0].inte, 0.0)
        self.assertEqual(loaded[0].fitwavelen, 0.0)

    def test_halpha_window_is_recognized_in_nm_and_angstrom(self):
        nm = Spectrum([637.892, 656.28, 673.903], [0.0, 1.0, 0.0])
        angstrom = Spectrum([6378.92, 6562.8, 6739.03], [0.0, 1.0, 0.0])
        unrelated = Spectrum([300.0, 320.0, 340.0], [0.0, 1.0, 0.0])

        self.assertTrue(spectrum_contains_halpha(nm))
        self.assertTrue(spectrum_contains_halpha(angstrom))
        self.assertFalse(spectrum_contains_halpha(unrelated))

    def test_missing_response_for_halpha_is_routed_to_ne_workflow(self):
        calls = []
        window = SimpleNamespace(
            load_halpha_spectrum_path=lambda filename: calls.append(filename) or True
        )
        app = SimpleNamespace(
            options=AppOptions(),
            show_ne_halpha=lambda: window,
        )
        error = ValueError(
            "No response curve matches 656.txt (637.892-673.903)."
        )
        probe = Spectrum([637.892, 656.28, 673.903], [0.0, 1.0, 0.0])

        with patch("pyLIBS.load_spectrum_for_open", return_value=probe), patch(
            "pyLIBS._askyesno",
            return_value=True,
        ):
            routed = MainWindow._offer_halpha_ne_import(
                app,
                "656.txt",
                error,
            )

        self.assertTrue(routed)
        self.assertEqual(calls, ["656.txt"])

    def test_clear_graph_restores_persistent_list_and_clears_active_ne_by_default(self):
        app = self._clear_graph_app(remember_ne=False)

        with patch("pyLIBS._askyesno", return_value=True):
            clear_all_spectra(app)

        self.assertEqual(app.spectra, [])
        self.assertEqual(len(app.template_lines), 2)
        self.assertEqual(app.analysis_elements, {"Cd", "Pb"})
        self.assertTrue(all(line.inte == 0.0 for line in app.template_lines))
        self.assertTrue(all(line.fitwavelen == 0.0 for line in app.template_lines))
        self.assertIsNone(app.session_ne)
        self.assertEqual(app.last_known_ne, 1.0589e16)
        self.assertIsNone(app.last_halpha_result)
        self.assertIn("analytical list restored (2 lines)", app.status_messages[-1])

    def test_clear_graph_can_retain_ne_explicitly_for_measurement_series(self):
        app = self._clear_graph_app(remember_ne=True)

        with patch("pyLIBS._askyesno", return_value=True):
            clear_all_spectra(app)

        self.assertEqual(app.session_ne, 1.0589e16)
        self.assertEqual(
            app.session_ne_source,
            "series carry-over from H-alpha fit",
        )
        self.assertIn("Ne retained for series", app.status_messages[-1])

    def test_active_electron_density_has_no_implicit_default(self):
        app = SimpleNamespace(
            session_ne=None,
            session_ne_source=None,
            last_known_ne=None,
            last_known_ne_source=None,
        )

        self.assertEqual(active_electron_density(app), (None, "not set"))
        set_session_electron_density(app, 2.5e16, "H-alpha test")
        self.assertEqual(active_electron_density(app), (2.5e16, "H-alpha test"))
        self.assertEqual(app.last_known_ne, 2.5e16)


if __name__ == "__main__":
    unittest.main()
