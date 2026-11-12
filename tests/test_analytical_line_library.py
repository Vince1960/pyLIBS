import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyLIBS import (
    AtomicLine,
    AppOptions,
    MainWindow,
    Spectrum,
    TemplateLine,
    acquired_wavelength_intervals,
    active_electron_density,
    automatic_trace_peak_match,
    clear_all_spectra,
    clear_current_line_analysis,
    load_template_lines,
    measured_peak_near_wavelength,
    merge_analytical_line_libraries,
    save_analytical_line_library,
    selected_observed_peak_wavelengths,
    set_session_electron_density,
    spectrum_contains_halpha,
    template_line_marker_is_visible,
    trace_lines_from_analytical_library,
)


class AnalyticalLineLibraryTests(unittest.TestCase):
    def test_complete_trace_scope_uses_all_acquired_intervals(self):
        spectrum = Spectrum(
            [300.0, 301.0, 400.0, 401.0],
            [1.0, 2.0, 3.0, 4.0],
        )
        app = SimpleNamespace(
            spectra=[spectrum],
            independent_window_mode=False,
        )

        self.assertEqual(
            acquired_wavelength_intervals(app),
            [(300.0, 301.0), (400.0, 401.0)],
        )

    def test_complete_trace_uses_only_real_peaks_and_allows_reidentification(self):
        app = SimpleNamespace(
            template_lines=[
                TemplateLine(340.36521, "Cd", 1),
                TemplateLine(341.0, templint=12.0),
                TemplateLine(
                    344.626,
                    "Ni",
                    1,
                    inte=3.2e-4,
                    fitwavelen=344.71,
                    fit_profile="voigt",
                ),
                TemplateLine(
                    326.10548,
                    "Cd",
                    1,
                    inte=2.1e-4,
                    fitwavelen=326.12,
                    fit_profile="voigt",
                ),
            ]
        )

        complete = selected_observed_peak_wavelengths(
            app,
            "Cd",
            allow_alternative_assignments=True,
        )
        curated = selected_observed_peak_wavelengths(
            app,
            "Cd",
            allow_alternative_assignments=False,
        )

        self.assertEqual(complete, [326.12, 341.0, 344.71])
        self.assertEqual(curated, [326.12, 341.0])

    def test_trace_assign_uses_shifted_fitted_center(self):
        selected = TemplateLine(
            340.70,
            templint=10.0,
            fitwavelen=340.365,
            fit_profile="voigt",
        )
        atomic = AtomicLine(340.365, "Cd", 1, aki=1.0)

        class Database:
            @staticmethod
            def enrich_line_from_element_table(line, **_kwargs):
                return line

        app = SimpleNamespace(
            template_lines=[selected],
            trace_markers=[atomic],
            options=SimpleNamespace(search_range=0.10),
            libs_db=Database(),
            wavelength_unit="nm",
            analysis_elements=set(),
            last_saha_boltzmann=None,
        )
        app.copy_atomic_line_to_template_line = (
            lambda template, line: MainWindow.copy_atomic_line_to_template_line(
                app, template, line
            )
        )
        app.notify_template_changed = lambda redraw=False: None
        app.redraw = lambda preserve_view=False: None
        app.status = lambda _message: None

        assigned = MainWindow.assign_traced_lines(app)

        self.assertEqual(assigned, 1)
        self.assertEqual(selected.specie, "Cd")
        self.assertAlmostEqual(selected.asswavelen, 340.365)

    def test_complete_trace_locates_a_real_peak_after_wavelength_shift(self):
        spectrum = Spectrum(
            [
                340.15,
                340.19,
                340.23,
                340.27,
                340.31,
                340.35,
                340.39,
                340.43,
                340.47,
            ],
            [1.0, 1.0, 2.0, 5.0, 10.0, 7.0, 3.0, 1.0, 1.0],
        )
        app = SimpleNamespace(
            spectra=[spectrum],
            independent_window_mode=False,
            active_window=None,
        )

        match = measured_peak_near_wavelength(app, 340.365, 0.10)

        self.assertIsNotNone(match)
        self.assertAlmostEqual(match["wavelength"], 340.31)
        self.assertEqual(match["intensity"], 10.0)

    def test_complete_trace_rejects_a_tiny_noise_maximum_near_a_line(self):
        x_values = [390.0 + 0.01 * index for index in range(1001)]
        y_values = [1.0 + (0.002 if index % 2 else 0.0) for index in range(1001)]
        y_values[336] = 50.0
        y_values[337] = 100.0
        y_values[338] = 45.0
        app = SimpleNamespace(
            spectra=[Spectrum(x_values, y_values)],
            independent_window_mode=False,
            active_window=None,
        )

        self.assertIsNone(measured_peak_near_wavelength(app, 391.005, 0.02))
        strong = measured_peak_near_wavelength(app, 393.37, 0.02)
        self.assertIsNotNone(strong)
        self.assertAlmostEqual(strong["wavelength"], 393.37)

    def test_strong_transition_recovers_a_small_residual_wavelength_offset(self):
        x_values = [392.8 + 0.01 * index for index in range(121)]
        y_values = [1.0 for _ in x_values]
        peak_index = min(
            range(len(x_values)),
            key=lambda index: abs(x_values[index] - 393.25),
        )
        y_values[peak_index - 1:peak_index + 2] = [25.0, 100.0, 30.0]
        app = SimpleNamespace(
            spectra=[Spectrum(x_values, y_values)],
            independent_window_mode=False,
            active_window=None,
        )
        line = AtomicLine(393.365991, "Ca", 2, inte=230.0)

        self.assertIsNone(
            automatic_trace_peak_match(
                app, line, 0.10, strong_transition=False
            )
        )
        recovered = automatic_trace_peak_match(
            app, line, 0.10, strong_transition=True
        )

        self.assertIsNotNone(recovered)
        self.assertAlmostEqual(recovered["wavelength"], 393.25)
        self.assertTrue(recovered["recovered_strong_transition"])
        self.assertAlmostEqual(recovered["recovery_tolerance"], 0.15)

    def test_trace_assign_creates_a_fittable_row_for_an_element_not_in_list(self):
        spectrum = Spectrum(
            [
                340.15,
                340.19,
                340.23,
                340.27,
                340.31,
                340.35,
                340.39,
                340.43,
                340.47,
            ],
            [1.0, 1.0, 2.0, 5.0, 10.0, 7.0, 3.0, 1.0, 1.0],
        )
        atomic = AtomicLine(340.365, "Cd", 1, aki=1.0)

        class Database:
            @staticmethod
            def enrich_line_from_element_table(line, **_kwargs):
                return line

        app = SimpleNamespace(
            spectra=[spectrum],
            independent_window_mode=False,
            active_window=None,
            template_lines=[],
            trace_markers=[atomic],
            options=SimpleNamespace(search_range=0.10),
            libs_db=Database(),
            wavelength_unit="nm",
            analysis_elements=set(),
        )
        app.copy_atomic_line_to_template_line = (
            lambda template, line: MainWindow.copy_atomic_line_to_template_line(
                app, template, line
            )
        )
        app.notify_template_changed = lambda redraw=False: None
        app.redraw = lambda preserve_view=False: None
        app.status = lambda _message: None

        assigned = MainWindow.assign_traced_lines(
            app,
            [atomic],
            tolerance=0.10,
        )

        self.assertEqual(assigned, 1)
        self.assertEqual(len(app.template_lines), 1)
        self.assertAlmostEqual(app.template_lines[0].wavelen, 340.31)
        self.assertAlmostEqual(app.template_lines[0].asswavelen, 340.365)
        self.assertEqual(app.template_lines[0].specie, "Cd")
        self.assertGreater(app.template_lines[0].templint, 0.0)

    def test_trace_assign_moves_existing_library_row_to_measured_peak(self):
        spectrum = Spectrum(
            [340.20, 340.25, 340.30, 340.35, 340.40],
            [1.0, 4.0, 12.0, 5.0, 1.0],
        )
        atomic = AtomicLine(340.365, "Cd", 1, aki=1.0)
        template = TemplateLine(340.365, "Cd", 1)

        class Database:
            @staticmethod
            def enrich_line_from_element_table(line, **_kwargs):
                return line

        class FitWindow:
            _fit_running = False

            def __init__(self):
                self.refreshes = 0

            @staticmethod
            def winfo_exists():
                return True

            def refresh_content(self):
                self.refreshes += 1

        fit_window = FitWindow()
        app = SimpleNamespace(
            spectra=[spectrum],
            independent_window_mode=False,
            active_window=None,
            template_lines=[template],
            trace_markers=[atomic],
            options=SimpleNamespace(search_range=0.10),
            libs_db=Database(),
            wavelength_unit="nm",
            analysis_elements=set(),
            auto_fit_window=fit_window,
        )
        app.copy_atomic_line_to_template_line = (
            lambda target, line: MainWindow.copy_atomic_line_to_template_line(
                app, target, line
            )
        )
        app.notify_template_changed = lambda redraw=False: None
        app.redraw = lambda preserve_view=False: None
        app.status = lambda _message: None
        match = {
            "wavelength": 340.30,
            "intensity": 12.0,
            "prominence": 11.0,
            "spectrum": spectrum,
        }

        assigned = MainWindow.assign_traced_lines(
            app,
            [atomic],
            peak_matches={id(atomic): match},
            tolerance=0.10,
        )

        self.assertEqual(assigned, 1)
        self.assertAlmostEqual(template.wavelen, 340.30)
        self.assertAlmostEqual(template.asswavelen, 340.365)
        self.assertEqual(template.templint, 12.0)
        self.assertTrue(template.trace_selected)
        self.assertEqual(app.analysis_elements, {"Cd"})
        self.assertEqual(app.last_trace_fit_ready_count, 1)
        self.assertEqual(fit_window.refreshes, 1)

    def test_trace_lines_can_use_only_the_persistent_main_list(self):
        library = [
            TemplateLine(326.10548, "Cd", 1),
            TemplateLine(340.36521, "Cd", 1),
            TemplateLine(214.438, "Cd", 2),
            TemplateLine(349.296, "Ni", 1),
        ]

        lines = trace_lines_from_analytical_library(
            library,
            "cd",
            [1],
            300.0,
            350.0,
            wavelength_unit="nm",
            selected_wavelengths=[340.40],
            tolerance=0.05,
        )

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].specie, "Cd")
        self.assertEqual(lines[0].ion, 1)
        self.assertAlmostEqual(lines[0].wavelen, 340.36521)

    def test_trace_lines_converts_the_persistent_list_to_angstrom(self):
        lines = trace_lines_from_analytical_library(
            [TemplateLine(340.36521, "Cd", 1)],
            "Cd",
            [1],
            3400.0,
            3410.0,
            wavelength_unit="angstrom",
        )

        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(lines[0].wavelen, 3403.6521)

    def test_trace_lines_all_includes_every_ion_stage_in_main_list(self):
        library = [
            TemplateLine(340.36521, "Cd", 1),
            TemplateLine(214.438, "Cd", 2),
            TemplateLine(155.0, "Cd", 3),
        ]

        lines = trace_lines_from_analytical_library(
            library,
            "Cd",
            None,
            100.0,
            400.0,
            wavelength_unit="nm",
        )

        self.assertEqual({line.ion for line in lines}, {1, 2, 3})

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

    def test_persistent_library_markers_require_explicit_element_selection(self):
        app = SimpleNamespace(
            analysis_elements=set(),
            last_saha_boltzmann=None,
        )
        cadmium = TemplateLine(340.36521, "Cd", 1)
        manual = TemplateLine(340.4)

        self.assertFalse(template_line_marker_is_visible(app, cadmium))
        self.assertTrue(template_line_marker_is_visible(app, manual))

        app.analysis_elements.add("Cd")
        self.assertTrue(template_line_marker_is_visible(app, cadmium))

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

    def test_clear_graph_restores_clean_library_and_clears_previous_analysis(self):
        app = self._clear_graph_app(remember_ne=False)

        with patch("pyLIBS._askyesno", return_value=True):
            clear_all_spectra(app)

        self.assertEqual(app.spectra, [])
        self.assertEqual(len(app.template_lines), 2)
        self.assertEqual(app.analysis_elements, set())
        self.assertTrue(all(line.inte == 0.0 for line in app.template_lines))
        self.assertTrue(all(line.fitwavelen == 0.0 for line in app.template_lines))
        self.assertIsNone(app.session_ne)
        self.assertEqual(app.last_known_ne, 1.0589e16)
        self.assertIsNone(app.last_halpha_result)
        self.assertIn("analytical list restored (2 clean lines)", app.status_messages[-1])

    def test_trace_clear_removes_dynamic_fits_and_saha_state(self):
        library = [TemplateLine(340.36521, "Cd", 1)]
        app = SimpleNamespace(
            analytical_line_library=library,
            template_lines=[
                TemplateLine(
                    340.36521,
                    "Cd",
                    1,
                    inte=2.0e-4,
                    fitwavelen=340.41,
                    fit_profile="voigt",
                ),
                TemplateLine(
                    393.25,
                    "Ca",
                    2,
                    inte=8.0e-4,
                    fitwavelen=393.25,
                    asswavelen=393.365991,
                    fit_profile="voigt",
                ),
            ],
            atomic_lines=[AtomicLine(393.365991, "Ca", 2)],
            element_markers=[AtomicLine(393.365991, "Ca", 2)],
            trace_markers=[AtomicLine(393.365991, "Ca", 2)],
            analysis_elements={"Cd", "Ca"},
            fit_overlay=([1.0], [2.0]),
            fit_baseline_overlay=([1.0], [0.0]),
            fit_component_overlays=[([1.0], [2.0])],
            fit_integration_bounds=[(339.0, 341.0)],
            last_saha_boltzmann={"selected_element": "Ca"},
            session_temperature=1.0,
            session_temperature_source="Saha-Boltzmann",
            post_irsac_temperature=0.9,
            post_irsac_temperature_source="IRSAC",
            saha_window=None,
        )
        app.notify_template_changed = lambda redraw=False: None

        removed, restored = clear_current_line_analysis(app)

        self.assertEqual((removed, restored), (2, 1))
        self.assertEqual(len(app.template_lines), 1)
        self.assertEqual(app.template_lines[0].specie, "Cd")
        self.assertEqual(app.template_lines[0].inte, 0.0)
        self.assertEqual(app.template_lines[0].fitwavelen, 0.0)
        self.assertEqual(app.atomic_lines, [])
        self.assertEqual(app.element_markers, [])
        self.assertEqual(app.trace_markers, [])
        self.assertEqual(app.analysis_elements, set())
        self.assertIsNone(app.last_saha_boltzmann)
        self.assertIsNone(app.session_temperature)
        self.assertIsNone(app.fit_overlay)
        self.assertEqual(app.fit_component_overlays, [])

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
