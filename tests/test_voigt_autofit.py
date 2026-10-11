import unittest
from copy import deepcopy
from types import SimpleNamespace

import numpy as np

from pyLIBS import (
    AppOptions,
    MultiGaussianFitWindow,
    RetroFitManagerWindow,
    Spectrum,
    SpectrumSourceWindow,
    TemplateLine,
    _irsac_stable_voigt_result,
    _multifit_fit_group,
    _voigt_baseline_reaching_limits,
    _voigt_fit_visualization,
    _voigt_fit_range_key,
    _voigt_integral_to_baseline,
    _voigt_quality_assessment,
    _voigt_saved_fit_range,
    _session_voigt_saved_fit_range,
    measurement_spectrum_signature,
    _zoom_limits_around_cursor,
    multigaussian_model,
    multivoigt_model,
    palleschi_gaussian_area,
)


class VoigtAutoFitTests(unittest.TestCase):
    def test_palleschi_gaussian_area_matches_the_analytical_integral(self):
        amplitude = 7.5
        sigma = 0.08
        self.assertAlmostEqual(
            palleschi_gaussian_area(amplitude, sigma),
            amplitude * sigma * np.sqrt(np.pi),
            places=14,
        )
        x = np.linspace(-1.0, 1.0, 200001)
        y = multigaussian_model(x, 0.0, 0.0, amplitude, 0.0, sigma)
        self.assertAlmostEqual(
            float(np.trapz(y, x)),
            palleschi_gaussian_area(amplitude, sigma),
            places=10,
        )

    def test_wheel_zoom_keeps_cursor_stationary(self):
        lo, hi = _zoom_limits_around_cursor((0.0, 10.0), 2.0, 0.8)
        self.assertAlmostEqual(lo, 0.4)
        self.assertAlmostEqual(hi, 8.4)
        self.assertAlmostEqual((2.0 - lo) / (hi - lo), 0.2)

    def test_manual_palleschi_gaussian_fit_stores_integrated_area(self):
        x = np.linspace(99.7, 100.3, 601)
        amplitude = 4.0
        sigma = 0.035
        y = multigaussian_model(x, 0.2, 0.0, amplitude, 100.0, sigma)
        line = TemplateLine(wavelen=100.0, fitwavelen=100.0, wg=2.0 * sigma)
        messages = []
        app = SimpleNamespace(
            spectra=[Spectrum(x.tolist(), y.tolist(), name="100.txt")],
            independent_window_mode=False,
            options=SimpleNamespace(search_range=0.1, iterations=20),
            current_plot_view=lambda: ((99.7, 100.3), (0.0, 5.0)),
            notify_template_changed=lambda redraw=False: None,
            redraw=lambda preserve_view=False: None,
            restore_plot_view=lambda xlim, ylim: None,
            status=messages.append,
            fit_overlay=None,
            fit_baseline_overlay=None,
            fit_component_overlays=[],
            fit_integration_bounds=[],
        )
        window = object.__new__(MultiGaussianFitWindow)
        window.master_app = app
        window.sigma_var = SimpleNamespace(get=lambda: str(2.0 * sigma))

        ok, _message, results = window.fit_gaussian_lines(
            [line],
            show_messages=False,
        )

        self.assertTrue(ok)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(line.fitwavelen, 100.0, places=7)
        self.assertAlmostEqual(
            line.inte,
            palleschi_gaussian_area(amplitude, sigma),
            places=7,
        )
        self.assertEqual(line.wl, 0.0)
        self.assertEqual(line.fit_profile, "gaussian")
        self.assertEqual(app.fit_overlay_label, "Gaussian sum")

    @staticmethod
    def _replicate_fit_snapshot(areas, max_cv=0.25):
        x = np.linspace(99.7, 100.3, 1201)
        sigma = 0.010
        gamma = 0.006
        traces = [
            multivoigt_model(
                x,
                2.0e-5,
                0.0,
                area,
                100.0,
                sigma,
                gamma,
            )
            for area in areas
        ]
        mean_y = np.mean(np.asarray(traces), axis=0)
        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        return line, {
            "spectrum": {
                "x": x.tolist(),
                "y": mean_y.tolist(),
                "name": "100.txt",
            },
            "replicates": [
                {
                    "x": x.tolist(),
                    "y": trace.tolist(),
                    "name": f"100_{index}.txt",
                }
                for index, trace in enumerate(traces, start=1)
            ],
            "xlim": (99.7, 100.3),
            "ylim": (0.0, float(np.max(mean_y) * 1.1)),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
                "ion": 1,
            }],
            "options": {
                "voigt_baseline_mode": "origin_constant",
                "fixed_wg": 2.354820045 * sigma,
                "fixed_wl": 2.0 * gamma,
                "fix_wg": True,
                "fix_wl": True,
                "fix_wavelength": True,
                "iterations": 20,
                "quality_max_replicate_area_cv": max_cv,
            },
        }

    def test_replicates_are_fitted_individually_and_mean_area_is_used(self):
        line, snapshot = self._replicate_fit_snapshot(
            [1.9e-3, 2.0e-3, 2.1e-3]
        )
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        fitted = result["payload"]["fit_values"][0]
        self.assertTrue(fitted["quality_ok"], fitted["quality_message"])
        self.assertEqual(fitted["replicate_area_count"], 3)
        self.assertEqual(fitted["replicate_area_total"], 3)
        self.assertAlmostEqual(
            fitted["integrated_area"],
            fitted["replicate_area_mean"],
            places=12,
        )
        self.assertAlmostEqual(fitted["replicate_area_cv"], 0.05, delta=0.005)

    def test_unstable_replicate_voigt_areas_warn_but_keep_mean_fit(self):
        _line, snapshot = self._replicate_fit_snapshot(
            [0.5e-3, 2.0e-3, 3.5e-3]
        )
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        fitted = result["payload"]["fit_values"][0]
        self.assertTrue(fitted["quality_ok"], fitted["quality_message"])
        self.assertGreater(fitted["replicate_area_cv"], 0.25)
        self.assertFalse(fitted["replicate_precision_ok"])
        self.assertIn("replicate Voigt-area CV", fitted["quality_warning"])
        self.assertAlmostEqual(
            fitted["integrated_area"],
            fitted["mean_spectrum_area"],
            places=12,
        )

    def test_replicate_statistics_never_replace_mean_spectrum_area(self):
        runner = object.__new__(RetroFitManagerWindow)
        replicate_areas = {
            "replicate_1": 1.0,
            "replicate_2": 2.0,
            "replicate_3": 6.0,
        }

        def fake_replicate_fit(snapshot, _stop_requested):
            area = replicate_areas[snapshot["spectrum"]["name"]]
            return {
                "status": "success",
                "payload": {
                    "fit_values": [{
                        "key": "line",
                        "integrated_area": area,
                        "quality_ok": True,
                    }],
                },
            }

        runner._run_voigt_fit_snapshot = fake_replicate_fit
        snapshot = {
            "replicates": [
                {"name": name}
                for name in replicate_areas
            ],
            "lines": [{"key": "line"}],
            "options": {"quality_max_replicate_area_cv": 0.25},
        }
        payload = {
            "fit_values": [{
                "key": "line",
                "integrated_area": 10.0,
                "quality_ok": True,
                "quality_message": "",
            }],
        }

        runner._attach_replicate_voigt_statistics(
            snapshot,
            payload,
            lambda: False,
        )

        fitted = payload["fit_values"][0]
        self.assertEqual(fitted["integrated_area"], 10.0)
        self.assertEqual(fitted["mean_spectrum_area"], 10.0)
        self.assertEqual(fitted["replicate_area_mean"], 3.0)
        self.assertTrue(fitted["quality_ok"])
        self.assertFalse(fitted["replicate_precision_ok"])

    def test_quality_rejects_center_bound_and_roi_filling_profile(self):
        quality = _voigt_quality_assessment(
            center=328.15345,
            bound_center=328.20345,
            bound_half_window=0.05,
            dx=0.04,
            fit_span=0.949,
            gaussian_width=1.01053,
            lorentzian_width=0.17715,
            peak_snr=7.53,
        )

        self.assertFalse(quality["quality_ok"])
        self.assertTrue(quality["at_center_bound"])
        self.assertGreater(quality["fwhm_roi_fraction"], 1.0)
        self.assertIn("search boundary", quality["quality_message"])
        self.assertIn("not constrained", quality["quality_message"])

    def test_quality_accepts_contained_high_snr_profile(self):
        quality = _voigt_quality_assessment(
            center=334.521,
            bound_center=334.52,
            bound_half_window=0.05,
            dx=0.04,
            fit_span=0.987,
            gaussian_width=0.109,
            lorentzian_width=0.1295,
            peak_snr=23.6,
        )

        self.assertTrue(quality["quality_ok"], quality["quality_message"])
        self.assertFalse(quality["at_center_bound"])
        self.assertLess(quality["fwhm_roi_fraction"], 0.80)

    def test_quality_retains_area_when_only_center_bound_is_reached(self):
        quality = _voigt_quality_assessment(
            center=100.05,
            bound_center=100.0,
            bound_half_window=0.05,
            dx=0.001,
            fit_span=1.0,
            gaussian_width=0.020,
            lorentzian_width=0.010,
            peak_snr=25.0,
        )

        self.assertTrue(quality["quality_ok"], quality["quality_message"])
        self.assertTrue(quality["at_center_bound"])
        self.assertIn("area retained", quality["quality_warning"])

    def test_irsac_refit_uses_first_stable_three_roi_sequence(self):
        key = 123

        def result(area):
            return {
                "status": "success",
                "payload": {
                    "fit_values": [{
                        "key": key,
                        "integrated_area": area,
                        "quality_ok": True,
                    }]
                },
            }

        candidates = [
            result(1.00),
            result(1.20),
            result(1.21),
            result(1.19),
            result(1.45),
        ]

        chosen = _irsac_stable_voigt_result(candidates, tolerance=0.075)

        self.assertIs(chosen, candidates[2])

    def test_overlapping_fit_uses_nearest_named_detector_window(self):
        target = TemplateLine(wavelen=357.27, specie="Pb", ion=1)
        x = tuple(np.linspace(344.0, 370.0, 100))
        source_350 = SpectrumSourceWindow(
            x=x,
            y=tuple(np.full(len(x), 350.0)),
            name="350.txt",
        )
        source_365 = SpectrumSourceWindow(
            x=x,
            y=tuple(np.full(len(x), 365.0)),
            name="365.txt",
        )
        merged = Spectrum(
            list(x),
            list(source_350.y),
            name="merged",
            source_windows=(source_350, source_365),
        )

        def raw_copy(holder):
            source = holder.source_windows[0]
            return Spectrum(
                list(source.x),
                list(source.y),
                name=source.name,
                source_windows=(source,),
            )

        runner = object.__new__(RetroFitManagerWindow)
        runner.master_app = SimpleNamespace(
            active_window=None,
            spectra=[merged],
            _raw_spectrum_copy=raw_copy,
        )

        snapshot = runner._active_spectrum_snapshot([target])

        self.assertEqual(snapshot["name"], "350.txt")
        self.assertEqual(snapshot["y"][0], 350.0)

    def test_automatic_fit_uses_only_traced_analysis_elements(self):
        runner = object.__new__(RetroFitManagerWindow)
        runner.automatic = True
        runner.master_app = SimpleNamespace(
            analysis_elements={"Cd", "Ni", "Pb"},
            template_lines=[
                TemplateLine(wavelen=326.1, specie="Cd", ion=1),
                TemplateLine(wavelen=328.2, specie="Zn", ion=1),
                TemplateLine(wavelen=344.6, specie="Ni", ion=1),
                TemplateLine(wavelen=405.8, specie="Pb", ion=1),
            ],
        )

        self.assertEqual(
            [line.specie for line in runner._eligible_template_lines()],
            ["Cd", "Ni", "Pb"],
        )

    def test_baseline_limits_crop_a_broad_view_to_the_peak_foot(self):
        x = np.linspace(99.0, 101.0, 4001)
        y = multivoigt_model(
            x,
            2.0e-5,
            0.0,
            2.0e-3,
            100.0,
            0.020,
            0.012,
        )
        limits = _voigt_baseline_reaching_limits(
            x,
            y,
            [{"key": 1, "wavelen": 100.0, "fitwavelen": 0.0}],
        )

        self.assertIsNotNone(limits)
        left, right = limits
        self.assertLess(left, 100.0)
        self.assertGreater(right, 100.0)
        self.assertLess(right - left, 1.5)

    def test_voigt_integral_stops_when_profile_returns_to_baseline(self):
        x = np.linspace(99.5, 100.5, 4001)
        integrated, left, right = _voigt_integral_to_baseline(
            x,
            2.0e-3,
            100.0,
            0.020,
            0.012,
        )

        self.assertLess(integrated, 2.0e-3)
        self.assertGreater(integrated, 0.95 * 2.0e-3)
        self.assertGreater(left, 99.5)
        self.assertLess(right, 100.5)

    def test_diagnostic_voigt_display_reaches_baseline_without_changing_area(self):
        source_x = np.linspace(98.0, 102.0, 4001)
        fit_x = source_x[(source_x >= 99.85) & (source_x <= 100.15)]
        area = 2.0e-3
        popt = np.asarray([
            2.0e-5,
            0.0,
            area,
            100.0,
            0.020,
            0.012,
        ])

        display = _voigt_fit_visualization(
            source_x,
            fit_x,
            popt,
            1,
        )

        self.assertIsNotNone(display)
        curve = np.asarray(display["components"][0], dtype=float)
        self.assertLessEqual(curve[0], 0.005 * np.max(curve))
        self.assertLessEqual(curve[-1], 0.005 * np.max(curve))
        self.assertLess(display["x"][0], float(np.min(fit_x)))
        self.assertGreater(display["x"][-1], float(np.max(fit_x)))
        self.assertEqual(float(popt[2]), area)

    def test_saved_fit_range_is_shared_by_all_lines_in_a_group(self):
        options = SimpleNamespace(
            voigt_fit_ranges=(
                '{"Cd:1:326.105480":[325.9,326.3],'
                '"Cd:1:326.200000":[325.9,326.3]}'
            )
        )
        lines = [
            TemplateLine(wavelen=326.10548, specie="Cd", ion=1),
            TemplateLine(wavelen=326.2, specie="Cd", ion=1),
        ]
        self.assertEqual(
            _voigt_saved_fit_range(options, lines),
            (325.9, 326.3),
        )

    def test_saved_fit_range_is_not_applied_to_partially_configured_group(self):
        options = SimpleNamespace(
            voigt_fit_ranges='{"Cd:1:326.105480":[325.9,326.3]}'
        )
        lines = [
            TemplateLine(wavelen=326.10548, specie="Cd", ion=1),
            TemplateLine(wavelen=326.2, specie="Cd", ion=1),
        ]
        self.assertIsNone(
            _voigt_saved_fit_range(options, lines)
        )

    def test_saved_fit_range_is_not_reused_in_a_new_spectrum_session(self):
        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        key = _voigt_fit_range_key(line)
        app = SimpleNamespace(
            options=SimpleNamespace(
                voigt_fit_ranges=f'{{"{key}":[99.8,100.3]}}'
            ),
            session_voigt_fit_range_keys=set(),
        )

        self.assertIsNone(_session_voigt_saved_fit_range(app, [line]))

        app.session_voigt_fit_range_keys.add(key)
        self.assertEqual(
            _session_voigt_saved_fit_range(app, [line]),
            (99.8, 100.3),
        )

    def test_saved_fit_range_is_restored_for_identical_spectrum_after_restart(self):
        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        key = _voigt_fit_range_key(line)
        spectrum = Spectrum(
            [99.8, 100.0, 100.3],
            [1.0, 4.0, 1.2],
            name="same",
        )
        app = SimpleNamespace(
            spectra=[spectrum],
            independent_window_mode=False,
            options=SimpleNamespace(
                voigt_fit_ranges=f'{{"{key}":[99.8,100.3]}}',
                voigt_fit_range_sources="{}",
            ),
            session_voigt_fit_range_keys=set(),
        )
        signature = measurement_spectrum_signature(app)
        app.options.voigt_fit_range_sources = (
            f'{{"{key}":"{signature}"}}'
        )

        self.assertEqual(
            _session_voigt_saved_fit_range(app, [line]),
            (99.8, 100.3),
        )
        self.assertIn(key, app.session_voigt_fit_range_keys)

    def test_saved_fit_range_is_rejected_when_spectrum_values_change(self):
        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        key = _voigt_fit_range_key(line)
        original = Spectrum(
            [99.8, 100.0, 100.3],
            [1.0, 4.0, 1.2],
            name="sample",
        )
        app = SimpleNamespace(
            spectra=[original],
            independent_window_mode=False,
            options=SimpleNamespace(
                voigt_fit_ranges=f'{{"{key}":[99.8,100.3]}}',
                voigt_fit_range_sources="{}",
            ),
            session_voigt_fit_range_keys=set(),
        )
        signature = measurement_spectrum_signature(app)
        app.options.voigt_fit_range_sources = (
            f'{{"{key}":"{signature}"}}'
        )
        app.spectra = [
            Spectrum(
                [99.8, 100.0, 100.3],
                [1.0, 5.0, 1.2],
                name="sample",
            )
        ]

        self.assertIsNone(_session_voigt_saved_fit_range(app, [line]))

    @staticmethod
    def _double_peak():
        x = np.linspace(99.5, 100.6, 441)
        y = multivoigt_model(
            x,
            2.0e-5,
            3.0e-6,
            2.0e-3,
            100.0,
            0.030,
            0.018,
            3.5e-3,
            100.14,
            0.035,
            0.022,
        )
        rng = np.random.default_rng(1234)
        y += rng.normal(0.0, 2.0e-6, size=x.size)
        return x, y

    def test_selected_doublet_is_deconvolved_without_hidden_components(self):
        x, y = self._double_peak()
        line = TemplateLine(wavelen=100.0)
        neighbor = TemplateLine(wavelen=100.14)
        snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "synthetic"},
            "xlim": (99.5, 100.6),
            "ylim": (0.0, 1.0),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
            }, {
                "key": id(neighbor),
                "wavelen": 100.14,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "Y",
            }],
            "options": {
                "fixed_wg": 0.1,
                "fixed_wl": 0.1,
                "fix_wg": False,
                "fix_wl": False,
                "fix_wavelength": False,
                "iterations": 20,
            },
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["payload"]["nuisance_components"], 0)
        fitted = {
            item["key"]: item
            for item in result["payload"]["fit_values"]
        }
        self.assertAlmostEqual(fitted[id(line)]["fit_center"], 100.0, delta=0.01)
        self.assertAlmostEqual(
            fitted[id(line)]["integrated_area"],
            2.0e-3,
            delta=2.5e-4,
        )
        self.assertAlmostEqual(
            fitted[id(neighbor)]["integrated_area"],
            3.5e-3,
            delta=3.5e-4,
        )

    def test_selected_voigt_bounds_follow_compatible_observed_maximum(self):
        x = np.linspace(99.8, 100.2, 4001)
        expected_center = 100.0
        observed_center = 100.0199
        expected_area = 2.0e-3
        y = multivoigt_model(
            x,
            2.0e-5,
            0.0,
            expected_area,
            observed_center,
            0.008,
            0.005,
        )
        line = TemplateLine(wavelen=expected_center)
        snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "shifted"},
            "xlim": (99.8, 100.2),
            "ylim": (0.0, 1.0),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": expected_center,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
            }],
            "options": {
                "fixed_wg": 0.1,
                "fixed_wl": 0.1,
                "fix_wg": False,
                "fix_wl": False,
                "fix_wavelength": False,
                "iterations": 20,
            },
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        fitted = result["payload"]["fit_values"][0]
        self.assertTrue(fitted["quality_ok"], fitted["quality_message"])
        self.assertFalse(fitted["at_center_bound"])
        self.assertAlmostEqual(fitted["fit_center"], observed_center, delta=5.0e-4)
        self.assertAlmostEqual(fitted["profile_area"], expected_area, delta=1.0e-5)
        self.assertGreater(fitted["integrated_area"], 0.95 * expected_area)
        self.assertLess(fitted["integrated_area"], expected_area)
        self.assertEqual(result["payload"]["fit_range_mode"], "visible ROI")

    def test_truncated_saved_roi_is_expanded_to_measured_baselines(self):
        x = np.linspace(99.5, 100.5, 4001)
        expected_area = 2.0e-3
        y = multivoigt_model(
            x,
            2.0e-5,
            0.0,
            expected_area,
            100.0,
            0.045,
            0.018,
        )
        line = TemplateLine(wavelen=100.0, specie="Cd", ion=1)
        snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "truncated"},
            "xlim": (99.95, 100.05),
            "ylim": (0.0, 1.0),
            "fit_range_locked": True,
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "Cd",
                "ion": 1,
            }],
            "options": {
                "voigt_baseline_mode": "origin_constant",
                "fixed_wg": 0.1,
                "fixed_wl": 0.1,
                "fix_wg": False,
                "fix_wl": False,
                "fix_wavelength": False,
                "search_range": 0.5,
                "iterations": 20,
            },
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        payload = result["payload"]
        fitted = payload["fit_values"][0]
        self.assertTrue(fitted["quality_ok"], fitted["quality_message"])
        self.assertTrue(payload["saved_roi_auto_expanded"])
        self.assertEqual(payload["original_fit_range"], (99.95, 100.05))
        self.assertGreater(payload["fit_range"][1] - payload["fit_range"][0], 0.1)
        self.assertAlmostEqual(fitted["fit_center"], 100.0, delta=5.0e-4)
        self.assertAlmostEqual(fitted["profile_area"], expected_area, delta=1.0e-5)

    def test_two_click_roi_is_saved_for_the_current_line(self):
        class Value:
            def __init__(self):
                self.value = ""

            def set(self, value):
                self.value = value

        class Axis:
            def __init__(self):
                self.xlim = None

            def set_xlim(self, low, high):
                self.xlim = (low, high)

        class Canvas:
            def draw_idle(self):
                return None

        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        status_messages = []
        runner = object.__new__(RetroFitManagerWindow)
        runner.msg_var = Value()
        runner.displayed_lines = [line]
        runner._visible_template_lines = lambda: [line]
        runner.master_app = SimpleNamespace(
            fit_roi_capture_window=None,
            options=SimpleNamespace(voigt_fit_ranges="{}"),
            clear_fit_artists=lambda: None,
            ax=Axis(),
            full_y_main_visible_x=lambda: None,
            canvas=Canvas(),
            _update_xscroll=lambda: None,
            status=status_messages.append,
        )
        saved = {}
        runner._persist_fit_ranges = lambda ranges: saved.update(ranges)

        runner.select_fit_range_from_graph()
        runner.add_fit_range_point_from_graph(99.8)
        runner.add_fit_range_point_from_graph(100.3)

        self.assertIsNone(runner.master_app.fit_roi_capture_window)
        self.assertEqual(
            saved[_voigt_fit_range_key(line)],
            [99.8, 100.3],
        )
        self.assertIn(
            _voigt_fit_range_key(line),
            runner.master_app.session_voigt_fit_range_keys,
        )
        self.assertEqual(runner.master_app.ax.xlim, (99.8, 100.3))
        self.assertIn("Origin-compatible ROI saved", runner.msg_var.value)

    def test_libs_auto_changes_only_the_reported_integration_limits(self):
        x = np.linspace(99.5, 100.5, 2001)
        y = multivoigt_model(
            x,
            2.0e-5,
            0.0,
            2.0e-3,
            100.0,
            0.020,
            0.012,
        )
        line = TemplateLine(wavelen=100.0)
        base_snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "mode-check"},
            "xlim": (99.5, 100.5),
            "ylim": (0.0, 1.0),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
            }],
        }
        common_options = {
            "fixed_wg": 0.1,
            "fixed_wl": 0.1,
            "fix_wg": False,
            "fix_wl": False,
            "fix_wavelength": False,
            "iterations": 20,
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        origin_snapshot = dict(base_snapshot)
        origin_snapshot["options"] = dict(
            common_options,
            voigt_baseline_mode="origin_constant",
        )
        libs_snapshot = dict(base_snapshot)
        libs_snapshot["options"] = dict(
            common_options,
            voigt_baseline_mode="libs_auto",
        )
        origin = runner._run_voigt_fit_snapshot(origin_snapshot, lambda: False)
        libs_auto = runner._run_voigt_fit_snapshot(libs_snapshot, lambda: False)

        self.assertEqual(origin["status"], "success")
        self.assertEqual(libs_auto["status"], "success")
        origin_fit = origin["payload"]["fit_values"][0]
        libs_fit = libs_auto["payload"]["fit_values"][0]
        for key in ("fit_center", "profile_area", "sigma", "gamma"):
            self.assertAlmostEqual(origin_fit[key], libs_fit[key], places=12)
        self.assertAlmostEqual(
            origin_fit["integrated_area"],
            origin_fit["profile_area"],
            places=12,
        )
        self.assertIn("baseline_overlay", origin["payload"])
        self.assertEqual(len(origin["payload"]["component_overlays"]), 1)
        self.assertEqual(len(origin["payload"]["integration_bounds"]), 1)
        self.assertLess(
            libs_fit["integrated_area"],
            libs_fit["profile_area"],
        )
        self.assertGreater(
            libs_fit["integrated_area"],
            0.95 * libs_fit["profile_area"],
        )
        self.assertIn(
            "baseline-reaching",
            libs_auto["payload"]["integration_method"],
        )

    def test_explicit_deconvolution_keeps_component_nearest_nist_transition(self):
        x = np.linspace(99.5, 100.5, 2001)
        y = multivoigt_model(
            x,
            1.0e-5,
            0.0,
            8.0e-4,
            100.0,
            0.010,
            0.006,
            2.5e-3,
            100.04,
            0.012,
            0.007,
        )
        line = TemplateLine(wavelen=100.0)
        neighbor = TemplateLine(wavelen=100.04)
        snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "two-compatible"},
            "xlim": (99.5, 100.5),
            "ylim": (0.0, 1.0),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
            }, {
                "key": id(neighbor),
                "wavelen": 100.04,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "Y",
            }],
            "options": {
                "fixed_wg": 0.1,
                "fixed_wl": 0.1,
                "fix_wg": False,
                "fix_wl": False,
                "fix_wavelength": False,
                "iterations": 20,
            },
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        fitted = {
            item["key"]: item
            for item in result["payload"]["fit_values"]
        }[id(line)]
        self.assertAlmostEqual(fitted["fit_center"], 100.0, delta=0.005)
        self.assertEqual(result["payload"]["nuisance_components"], 0)

    def test_component_identity_does_not_follow_optimizer_array_order(self):
        runner = object.__new__(RetroFitManagerWindow)
        lines = [
            {"wavelen": 100.0, "_target_center": 100.0},
            {"wavelen": 100.2, "_target_center": 100.2},
        ]
        fit_lines = lines + [{"wavelen": 100.04, "_nuisance": True}]
        popt = np.asarray([
            0.0,
            0.0,
            1.0, 100.04, 0.01, 0.01,
            1.0, 100.20, 0.01, 0.01,
            1.0, 100.00, 0.01, 0.01,
        ])

        assignments = runner._voigt_selected_component_indices(
            lines,
            fit_lines,
            popt,
        )

        self.assertEqual(assignments, [2, 1])

    def test_multifit_uses_structured_voigt_result(self):
        x, y = self._double_peak()
        spectrum = Spectrum(x.tolist(), y.tolist(), name="synthetic")
        line = TemplateLine(wavelen=100.0)
        neighbor = TemplateLine(wavelen=100.14)
        options = AppOptions()
        options.delta_min = 0.5
        options.iterations = 20

        ok, message, results = _multifit_fit_group(
            spectrum,
            [(0, 100.0, line), (1, 100.14, neighbor)],
            options,
        )

        self.assertTrue(ok, message)
        self.assertIn(0, results)
        self.assertIn(1, results)
        self.assertAlmostEqual(results[0]["Inte"], 2.0e-3, delta=2.5e-4)
        self.assertAlmostEqual(results[1]["Inte"], 3.5e-3, delta=3.5e-4)

    def test_origin_baseline_keeps_slope_fixed_at_zero(self):
        x = np.linspace(99.5, 100.5, 1001)
        y = multivoigt_model(
            x,
            2.0e-5,
            0.0,
            2.0e-3,
            100.0,
            0.020,
            0.012,
        )
        line = TemplateLine(wavelen=100.0)
        snapshot = {
            "spectrum": {"x": x.tolist(), "y": y.tolist(), "name": "origin"},
            "xlim": (99.5, 100.5),
            "ylim": (0.0, 1.0),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 0.0,
                "wl": 0.0,
                "specie": "X",
            }],
            "options": {
                "voigt_baseline_mode": "origin_constant",
                "fixed_wg": 0.1,
                "fixed_wl": 0.1,
                "fix_wg": False,
                "fix_wl": False,
                "fix_wavelength": False,
                "iterations": 20,
            },
        }
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["payload"]["baseline_mode"], "origin_constant")
        self.assertEqual(result["payload"]["baseline_slope"], 0.0)
        self.assertAlmostEqual(
            result["payload"]["fit_values"][0]["profile_area"],
            2.0e-3,
            delta=1.0e-5,
        )
        self.assertAlmostEqual(
            result["payload"]["fit_values"][0]["integrated_area"],
            2.0e-3,
            delta=1.0e-5,
        )

    @staticmethod
    def _auto_baseline_snapshot(slope):
        x = np.linspace(99.5, 100.5, 1001)
        sigma = 0.020
        gamma = 0.012
        area = 2.0e-3
        y = multivoigt_model(
            x,
            2.0e-4,
            slope,
            area,
            100.0,
            sigma,
            gamma,
        )
        rng = np.random.default_rng(4815)
        y += rng.normal(0.0, 1.0e-6, size=x.size)
        line = TemplateLine(wavelen=100.0, specie="X", ion=1)
        return area, slope, {
            "spectrum": {
                "x": x.tolist(),
                "y": y.tolist(),
                "name": "baseline-selection",
            },
            "xlim": (99.5, 100.5),
            "ylim": (float(np.min(y)), float(np.max(y))),
            "line_overrides": {},
            "lines": [{
                "key": id(line),
                "wavelen": 100.0,
                "fitwavelen": 0.0,
                "wg": 2.354820045 * sigma,
                "wl": 2.0 * gamma,
                "specie": "X",
                "ion": 1,
            }],
            "options": {
                "voigt_baseline_mode": "palleschi_bic_diagnostic",
                "fixed_wg": 2.354820045 * sigma,
                "fixed_wl": 2.0 * gamma,
                "fix_wg": True,
                "fix_wl": True,
                "fix_wavelength": True,
                "iterations": 20,
            },
        }

    def test_bic_diagnostic_never_replaces_palleschi_flat_fit(self):
        expected_area, _slope, snapshot = self._auto_baseline_snapshot(0.0)
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)
        palleschi_snapshot = deepcopy(snapshot)
        palleschi_snapshot["options"]["voigt_baseline_mode"] = "local_linear"
        palleschi = runner._run_voigt_fit_snapshot(
            palleschi_snapshot,
            lambda: False,
        )

        self.assertEqual(result["status"], "success")
        payload = result["payload"]
        self.assertEqual(
            payload["baseline_mode_requested"],
            "palleschi_bic_diagnostic",
        )
        self.assertEqual(payload["baseline_mode_selected"], "local_linear")
        self.assertEqual(payload["baseline_mode"], "local_linear")
        self.assertTrue(payload["baseline_bic_comparable"])
        self.assertEqual(
            payload["baseline_bic_recommendation"],
            "constant baseline would be statistically sufficient",
        )
        self.assertEqual(palleschi["status"], "success")
        self.assertAlmostEqual(
            payload["fit_values"][0]["profile_area"],
            palleschi["payload"]["fit_values"][0]["profile_area"],
            delta=1.0e-15,
        )
        self.assertAlmostEqual(
            payload["fit_values"][0]["profile_area"],
            expected_area,
            delta=2.0e-6,
        )

    def test_bic_diagnostic_reports_support_for_palleschi_sloped_fit(self):
        expected_area, expected_slope, snapshot = self._auto_baseline_snapshot(
            8.0e-4
        )
        runner = object.__new__(RetroFitManagerWindow)
        runner.last_fit_result = None

        result = runner._run_voigt_fit_snapshot(snapshot, lambda: False)

        self.assertEqual(result["status"], "success")
        payload = result["payload"]
        self.assertEqual(
            payload["baseline_mode_requested"],
            "palleschi_bic_diagnostic",
        )
        self.assertEqual(payload["baseline_mode_selected"], "local_linear")
        self.assertEqual(payload["baseline_mode"], "local_linear")
        self.assertEqual(
            payload["baseline_bic_recommendation"],
            "linear baseline strongly supported",
        )
        self.assertGreaterEqual(
            payload["baseline_bic"]["origin_constant"]
            - payload["baseline_bic"]["local_linear"],
            6.0,
        )
        self.assertAlmostEqual(
            payload["baseline_slope"],
            expected_slope,
            delta=1.0e-5,
        )
        self.assertAlmostEqual(
            payload["fit_values"][0]["profile_area"],
            expected_area,
            delta=2.0e-6,
        )


if __name__ == "__main__":
    unittest.main()
