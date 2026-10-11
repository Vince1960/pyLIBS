import math
import unittest
from types import SimpleNamespace

from pyLIBS import (
    AppOptions,
    CFLibsWindow,
    SACWindow,
    Spectrum,
    _active_irsac_reference_lines,
    _cflibs_intercept_mode_is_quantitative,
    _cflibs_visible_groups,
    _irsac_configuration_mismatch,
    _locked_post_irsac_saha_element,
    _saha_plot_fit_results,
    _saha_merge_display_groups,
    _saha_visible_groups,
    _saha_temperature_for_irsac_reference,
    _sac_factor_for_line,
    _self_absorption_quantification_blocker,
    _worksheet_irsac_temperature_ev,
    _worksheet_irsac_temperature_source,
    cflibs_quantitation_quality,
    format_cflibs_quality_report,
    libspp_boltzmann_groups_with_skips,
    libspp_fit_boltzmann,
    libspp_fit_boltzmann_excel_intercepts,
    libspp_fit_boltzmann_fixed_temperature,
    libspp_cflibs_line_audit,
    libspp_cflibs_robustness,
    libspp_fit_saha_boltzmann,
    libspp_saha_cflibs,
    libspp_saha_boltzmann_groups,
    libspp_saha_boltzmann_diagnostic_groups,
    merge_spectra_by_wavelength,
    remove_traced_elements,
    select_most_reliable_saha_element,
    saha_no_fit_message,
    saha_fit_quality,
    saha_template_line_diagnostics,
    validated_cflibs_rows,
)
from pylibs.core.boltzmann import (
    PHOTONS_PER_JOULE_NM,
    radiometric_boltzmann_ordinate,
    radiometric_line_intensity_from_ordinate,
    wavelength_in_nm,
)
from pylibs.core.models import TemplateLine


EV_PER_CM = 1.23985e-4


class FakeDatabase:
    def __init__(self, ionization_cm=60000.0):
        self.ionization_cm = ionization_cm

    def element_metadata(self, _element):
        return {"en_ion": self.ionization_cm, "m_atomica": 1.0}

    def partition_function(self, _element, _ion, _temperature_k):
        return 1.0


def quantitative_quality_app(*, temperature_quality=None, halpha_ne=1.0e17):
    options = AppOptions()
    options.apply_response = True
    options.apply_before = True
    options.apply_after = False
    app = SimpleNamespace(
        options=options,
        response_library=SimpleNamespace(curves=[object()]),
        spectra=[SimpleNamespace(response_corrected=True, halpha_response_bypassed=False)],
        apply_sac_correction=False,
        last_self_absorption_result={
            "assessment_status": "No significant evidence",
            "assessment_can_apply": False,
        },
        last_halpha_result={
            "available": True,
            "ne": halpha_ne,
            "kt": 1.0,
            "ne_evaluation_kt": 1.0,
            "corrected_lorentzian_width_angstrom": 1.0,
            "corrected_lorentzian_width": 0.12,
            "r_squared": 0.99,
            "peak_identification_quality": "compatible",
            "peak_prominence_to_noise": 12.0,
            "ne_relative_uncertainty": 0.05,
        },
        libs_db=FakeDatabase(),
        template_lines=[],
    )
    quality = temperature_quality or {
        "quantitative_eligible": True,
        "quantitative_failures": [],
        "nlines": 4,
        "distinct_levels": 4,
        "energy_span_ev": 2.0,
        "r2": 0.995,
        "relative_slope_error": 0.04,
        "loo_relative_span": 0.08,
    }
    app.last_saha_boltzmann = {
        "selected_element": "Cu",
        "representative_temperature": 1.0,
        "representative_mode": "most reliable element",
        "elements": [{"element": "Cu", "included": True, "quality": quality}],
    }
    return app


def fake_app(lines, *, apply_sac=False, wavelength_unit="nm", ionization_cm=60000.0):
    return SimpleNamespace(
        template_lines=lines,
        apply_sac_correction=apply_sac,
        spectra=[],
        response_library=SimpleNamespace(curves=[]),
        options=SimpleNamespace(
            apply_response=False,
            apply_after=False,
            ne_low=1.0e17,
            aki_threshold=1.0e5,
            kt_low=0.5,
            kt_high=3.0,
        ),
        libs_db=FakeDatabase(ionization_cm),
        current_wavelength_unit_label=lambda: wavelength_unit,
    )


def line_from_ordinate(species, ion, wavelength_nm, energy_cm, ordinate, aki=2.0e7, gk=3):
    intensity = radiometric_line_intensity_from_ordinate(ordinate, wavelength_nm, aki, gk)
    return TemplateLine(
        wavelen=wavelength_nm,
        asswavelen=wavelength_nm,
        fitwavelen=wavelength_nm,
        specie=species,
        ion=ion,
        inte=intensity,
        ek=energy_cm,
        aki=aki,
        gk=gk,
        wg=0.08,
        wl=0.04,
    )


class RadiometricBoltzmannTests(unittest.TestCase):
    def test_blocked_quality_never_publishes_cflibs_percentages(self):
        rows = [{"element": "Cd", "number_percent": 57.0, "mass_percent": 60.0}]
        self.assertEqual(validated_cflibs_rows(rows, {"approved": False}), [])
        self.assertEqual(validated_cflibs_rows(rows, None), [])
        self.assertEqual(
            validated_cflibs_rows(
                rows,
                {"approved": True, "status": "LEGACY OVERRIDE"},
            ),
            [],
        )
        self.assertEqual(
            validated_cflibs_rows(rows, {"approved": True, "status": "PASS"}),
            rows,
        )

    def test_sac_uses_current_result_but_never_invents_equal_percentages(self):
        window = object.__new__(SACWindow)
        window.master_app = SimpleNamespace(
            last_cflibs_rows=[],
            last_cflibs_quality={"approved": False},
            template_lines=[SimpleNamespace(specie="Cd"), SimpleNamespace(specie="Ni")],
        )
        self.assertEqual(window._element_percentages(), {})

        window.master_app.last_cflibs_rows = [
            {"element": "Cd", "number_percent": 41.0},
            {"element": "Ni", "number_percent": 59.0},
        ]
        self.assertEqual(
            window._element_percentages(),
            {"Cd": 41.0, "Ni": 59.0},
        )

    def test_saha_ordinate_uses_nist_wavelength_not_fitted_center(self):
        nist_wavelength = 340.36521
        fitted_center = 340.742
        line = line_from_ordinate(
            "Cd",
            1,
            nist_wavelength,
            45000.0,
            17.0,
        )
        line.fitwavelen = fitted_center
        calls = []

        class ResponseLibrary:
            curves = [object()]

            @staticmethod
            def value_at(wavelength):
                calls.append(wavelength)
                return 2.0

        app = fake_app([line])
        app.options.apply_response = True
        app.options.apply_after = True
        app.response_library = ResponseLibrary()
        app.spectra = [
            Spectrum(
                [340.0, 340.5, 341.0],
                [0.0, 1.0, 0.0],
                response_corrected=False,
            )
        ]

        groups, skipped = libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
        point = groups["Cd"][0]
        expected = radiometric_boltzmann_ordinate(
            line.inte / 2.0,
            nist_wavelength,
            line.aki,
            line.gk,
        )

        self.assertEqual(skipped, 0)
        self.assertAlmostEqual(point["center"], fitted_center, places=12)
        self.assertAlmostEqual(point["nist_wavelength"], nist_wavelength, places=12)
        self.assertAlmostEqual(point["wavelength_nm"], nist_wavelength, places=12)
        self.assertAlmostEqual(point["y"], expected, places=12)
        self.assertEqual(calls, [nist_wavelength])

    def test_diagnostic_saha_ordinate_uses_nist_wavelength(self):
        nist_wavelength = 405.78067
        line = line_from_ordinate("Pb", 1, nist_wavelength, 35287.2, 18.0)
        line.fitwavelen = 406.12
        line.fit_mean_spectrum_area = line.inte
        line.fit_mean_quality_ok = True
        line.error_inte = "ERROR"
        app = fake_app([line])

        groups = libspp_saha_boltzmann_diagnostic_groups(app, 1.0e17, 1.0)
        point = groups["Pb"][0]

        self.assertAlmostEqual(point["center"], 406.12, places=12)
        self.assertAlmostEqual(point["nist_wavelength"], nist_wavelength, places=12)
        self.assertAlmostEqual(point["wavelength_nm"], nist_wavelength, places=12)

    def test_high_replicate_cv_mean_fit_remains_quantitative(self):
        line = line_from_ordinate(
            "Sn",
            1,
            317.50348,
            30000.0,
            12.0,
        )
        mean_area = line.inte
        line.fit_mean_spectrum_area = mean_area
        line.fit_mean_quality_ok = True
        line.fit_quality_warning = "replicate Voigt-area CV 0.607 > 0.250"
        line.fit_replicate_area_cv = 0.607
        app = fake_app([line])

        quantitative, _skipped = libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
        diagnostic = libspp_saha_boltzmann_diagnostic_groups(
            app,
            1.0e17,
            1.0,
        )
        display = _saha_merge_display_groups(quantitative, diagnostic)

        self.assertEqual(len(quantitative["Sn"]), 1)
        self.assertEqual(len(display["Sn"]), 1)
        self.assertFalse(display["Sn"][0].get("diagnostic_only", False))
        self.assertEqual(diagnostic, {})

    def test_unconstrained_mean_voigt_is_not_plotted_as_diagnostic(self):
        line = line_from_ordinate(
            "Sn",
            1,
            300.91335,
            35000.0,
            12.0,
        )
        line.fit_mean_spectrum_area = line.inte
        line.inte = "ERROR"
        line.wg = "ERROR"
        line.wl = "ERROR"
        line.fit_mean_quality_ok = False
        app = fake_app([line])

        self.assertEqual(
            libspp_saha_boltzmann_diagnostic_groups(app, 1.0e17, 1.0),
            {},
        )

    def test_energy_to_photon_constant_and_inverse(self):
        self.assertAlmostEqual(PHOTONS_PER_JOULE_NM / 5.0341165675e15, 1.0, places=10)
        y = radiometric_boltzmann_ordinate(2.5e-3, 324.754, 1.39e8, 4)
        recovered = radiometric_line_intensity_from_ordinate(y, 324.754, 1.39e8, 4)
        self.assertAlmostEqual(recovered, 2.5e-3, places=14)

    def test_photon_counting_mode_omits_energy_conversion_and_is_invertible(self):
        intensity = 2.5e-3
        wavelength = 324.754
        aki = 1.39e8
        gk = 4
        y = radiometric_boltzmann_ordinate(
            intensity,
            wavelength,
            aki,
            gk,
            "photon",
        )
        self.assertAlmostEqual(y, math.log(intensity / abs(aki * gk)), places=14)
        recovered = radiometric_line_intensity_from_ordinate(
            y,
            wavelength,
            aki,
            gk,
            "photon",
        )
        self.assertAlmostEqual(recovered, intensity, places=14)

    def test_wavelength_unit_conversion(self):
        self.assertAlmostEqual(wavelength_in_nm(3247.54, "angstrom"), 324.754)
        self.assertAlmostEqual(wavelength_in_nm(3247.54, "Å"), 324.754)
        self.assertAlmostEqual(wavelength_in_nm(324.754, "nm"), 324.754)

    def test_boltzmann_fit_recovers_known_temperature(self):
        kt = 0.82
        intercept = 24.0
        specifications = [
            (296.1165, 32000.0),
            (324.7540, 40000.0),
            (465.1124, 52000.0),
            (510.5540, 61000.0),
        ]
        lines = [
            line_from_ordinate("Cu", 1, wavelength, energy, intercept - energy * EV_PER_CM / kt)
            for wavelength, energy in specifications
        ]
        app = fake_app(lines)
        groups, skipped = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann(app, groups)
        self.assertEqual(skipped, 0)
        self.assertAlmostEqual(fits[("Cu", 1)]["kt"], kt, places=10)
        self.assertAlmostEqual(fits[("Cu", 1)]["q"], intercept, places=10)

    def test_applied_irsac_multipliers_restore_temperature(self):
        kt = 0.95
        intercept = 21.0
        lines = []
        for wavelength, energy, sac in (
            (300.0, 25000.0, 1.5),
            (330.0, 39000.0, 2.0),
            (470.0, 57000.0, 3.5),
        ):
            line = line_from_ordinate("Fe", 1, wavelength, energy, intercept - energy * EV_PER_CM / kt)
            line.inte /= sac
            line.sa_use = True
            line.sa_sac = sac
            line.sa_method = "IRSAC Yang/Aslam"
            lines.append(line)
        app = fake_app(lines, apply_sac=True)
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann(app, groups)
        self.assertAlmostEqual(fits[("Fe", 1)]["kt"], kt, places=10)
        self.assertAlmostEqual(fits[("Fe", 1)]["q"], intercept, places=10)

    def test_saha_boltzmann_fit_recovers_known_temperature(self):
        kt = 0.90
        ne = 1.0e17
        intercept = 22.0
        ionization_cm = 62000.0
        ionization_ev = ionization_cm * EV_PER_CM
        saha_shift = math.log(6.04e21 / ne * kt ** 1.5)
        lines = []
        for wavelength, energy in ((310.0, 30000.0), (360.0, 47000.0)):
            y = intercept - energy * EV_PER_CM / kt
            lines.append(line_from_ordinate("Zn", 1, wavelength, energy, y))
        for wavelength, energy in ((330.0, 41000.0), (480.0, 55000.0)):
            shifted_y = intercept - (ionization_ev + energy * EV_PER_CM) / kt
            lines.append(line_from_ordinate("Zn", 2, wavelength, energy, shifted_y + saha_shift))
        app = fake_app(lines, ionization_cm=ionization_cm)
        groups, skipped = libspp_saha_boltzmann_groups(app, ne, kt)
        fits = libspp_fit_saha_boltzmann(app, groups)
        self.assertEqual(skipped, 0)
        self.assertAlmostEqual(fits["Zn"]["kt"], kt, places=10)
        self.assertAlmostEqual(fits["Zn"]["q"], intercept, places=10)

    def test_saha_requires_integrated_voigt_result_not_peak_height(self):
        line = TemplateLine(
            wavelen=405.78,
            fitwavelen=405.79,
            specie="Pb",
            ion=1,
            inte=1500.0,
            templint=1500.0,
            ek=35287.2,
            aki=9.1e7,
            gk=3,
        )
        app = fake_app([line])
        groups, skipped = libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
        diagnostics = saha_template_line_diagnostics(app, ne=1.0e17, kt=1.0)
        self.assertEqual(groups, {})
        self.assertEqual(skipped, 1)
        self.assertFalse(diagnostics[0]["usable"])
        self.assertIn("missing Gaussian Voigt width", diagnostics[0]["blockers"])
        self.assertIn("missing Lorentzian Voigt width", diagnostics[0]["blockers"])

    def test_saha_diagnostics_explain_missing_voigt_fit(self):
        line = TemplateLine(
            wavelen=405.78,
            specie="Pb",
            ion=1,
            templint=1500.0,
            ek=35287.2,
            aki=9.1e7,
            gk=3,
        )
        app = fake_app([line])
        diagnostics = saha_template_line_diagnostics(app, ne=1.0e17, kt=1.0)
        message = saha_no_fit_message(diagnostics, {})
        self.assertIn("missing positive Voigt area", diagnostics[0]["blockers"])
        self.assertIn("0/1", message)
        self.assertIn("Auto Fit", message)

    def test_saha_diagnostics_marks_complete_line_ready(self):
        line = line_from_ordinate("Ni", 1, 344.626, 30000.0, 18.0)
        app = fake_app([line])
        diagnostics = saha_template_line_diagnostics(app, ne=1.0e17, kt=1.0)
        self.assertTrue(diagnostics[0]["usable"])
        self.assertEqual(diagnostics[0]["status"], "Ready")

    def test_aki_threshold_excludes_weak_lines_from_both_plots(self):
        weak = line_from_ordinate("Cd", 1, 326.1, 30000.0, 18.0, aki=9.0e4)
        strong = line_from_ordinate("Cd", 1, 340.3, 45000.0, 17.0, aki=1.0e5)
        app = fake_app([weak, strong])
        boltzmann, skipped = libspp_boltzmann_groups_with_skips(app)
        saha, saha_skipped = libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
        diagnostics = saha_template_line_diagnostics(app, ne=1.0e17, kt=1.0)
        self.assertEqual(len(boltzmann[("Cd", 1)]), 1)
        self.assertEqual(len(saha["Cd"]), 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(saha_skipped, 1)
        self.assertFalse(diagnostics[0]["usable"])
        self.assertIn("Aki below threshold", diagnostics[0]["status"])
        self.assertTrue(diagnostics[1]["usable"])

    def test_cflibs_refreshes_stale_temperature_from_current_analysis(self):
        class Variable:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        window = object.__new__(CFLibsWindow)
        window.master_app = SimpleNamespace(
            session_temperature=1.06272,
            session_ne=1.0589e16,
            session_temperature_source="post-IRSAC most reliable element: Pb",
        )
        window.kt_var = Variable("0.3")
        window.ne_var = Variable("1e17")
        window.status_var = Variable()
        self.assertTrue(window.sync_session_inputs())
        self.assertAlmostEqual(float(window.kt_var.get()), 1.06272)
        self.assertAlmostEqual(float(window.ne_var.get()), 1.0589e16)
        self.assertIn("Pb", window.status_var.get())

    def test_reliable_temperature_rejects_two_points_and_prefers_widest_ek_span(self):
        app = fake_app([])

        def result(element, xs, ys):
            n = len(xs)
            mean_x = sum(xs) / n
            mean_y = sum(ys) / n
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
            slope /= sum((x - mean_x) ** 2 for x in xs)
            intercept = mean_y - slope * mean_x
            return {
                "species": element,
                "nlines": n,
                "kt": -1.0 / slope,
                "q": intercept,
                "slope": slope,
                "points": [
                    {"x": x, "y": y, "inactive": False}
                    for x, y in zip(xs, ys)
                ],
            }

        two_point = result("Ni", [3.0, 7.0], [18.0, 14.0])
        cd = result(
            "Cd",
            [3.8008950571, 7.3753431353, 6.3832413184, 6.3832413184],
            [17.0372262734, 12.5275026396, 14.1217916327, 14.1321464708],
        )
        pb = result(
            "Pb",
            [6.1297709370, 4.3750863010, 4.3345044607, 5.9746671549, 4.3750863010],
            [13.9366547758, 15.3563688901, 15.4686463210, 13.7462671193, 15.5107018804],
        )
        fits = {"Ni": two_point, "Cd": cd, "Pb": pb}
        self.assertFalse(saha_fit_quality(app, two_point)["eligible"])
        self.assertEqual(select_most_reliable_saha_element(app, fits, 0.5, 3.0), "Cd")

    def test_temperature_quality_gate_exposes_strict_failures(self):
        app = fake_app([])
        result = {
            "species": "Cu",
            "nlines": 4,
            "kt": 1.0,
            "q": 20.0,
            "slope": -1.0,
            "points": [
                {"x": 3.5, "y": 16.7, "inactive": False},
                {"x": 4.0, "y": 15.8, "inactive": False},
                {"x": 6.0, "y": 14.6, "inactive": False},
                {"x": 7.5, "y": 11.9, "inactive": False},
            ],
        }

        quality = saha_fit_quality(app, result)

        self.assertTrue(quality["eligible"])
        self.assertFalse(quality["quantitative_eligible"])
        self.assertTrue(quality["quantitative_failures"])

    def test_quantitative_quality_passes_supported_chain(self):
        app = quantitative_quality_app()
        fits = {("Cu", 1): {"points": []}}
        rows = [{
            "element": "Cu",
            "distinct_levels": 3,
            "neutral_ratio": 0.25,
            "ionized_neutral_ratio": 3.0,
        }]
        line_audit = {"Cu": {
            "active_count": 3,
            "population_factor": 1.2,
        }}

        quality = cflibs_quantitation_quality(
            app, fits, rows, line_audit, 1.0, 1.0e17
        )

        self.assertTrue(quality["approved"])
        self.assertEqual(quality["status"], "PASS")
        self.assertIn("CF-LIBS quantitative quality: PASS", format_cflibs_quality_report(quality))

    def test_quantitative_quality_blocks_unstable_temperature_and_manual_ne(self):
        bad_temperature = {
            "quantitative_eligible": False,
            "quantitative_failures": ["LOO dT/T=0.9 > 0.25"],
            "nlines": 4,
            "distinct_levels": 4,
            "energy_span_ev": 3.9,
            "r2": 0.94,
            "relative_slope_error": 0.18,
            "loo_relative_span": 0.9,
        }
        app = quantitative_quality_app(
            temperature_quality=bad_temperature,
            halpha_ne=2.0e17,
        )
        fits = {("Cu", 1): {"points": []}}
        rows = [{
            "element": "Cu",
            "distinct_levels": 3,
            "neutral_ratio": 0.25,
            "ionized_neutral_ratio": 3.0,
        }]
        line_audit = {"Cu": {
            "active_count": 3,
            "population_factor": 1.2,
        }}

        quality = cflibs_quantitation_quality(
            app, fits, rows, line_audit, 1.0, 1.0e17
        )

        self.assertFalse(quality["approved"])
        self.assertTrue(any("Thermometric fit" in item for item in quality["blockers"]))
        self.assertTrue(any("Electron density from H-alpha" in item for item in quality["blockers"]))

    def test_quantitative_quality_blocks_dominant_unobserved_stage(self):
        app = quantitative_quality_app()
        fits = {("Cu", 1): {"points": []}}
        rows = [{
            "element": "Cu",
            "distinct_levels": 3,
            "neutral_ratio": 0.001,
            "ionized_neutral_ratio": 999.0,
        }]
        line_audit = {"Cu": {
            "active_count": 3,
            "population_factor": 1.2,
        }}

        quality = cflibs_quantitation_quality(
            app, fits, rows, line_audit, 1.0, 1.0e17
        )

        self.assertFalse(quality["approved"])
        self.assertTrue(any("Observed ionization stage Cu" in item for item in quality["blockers"]))

    def test_quantitative_quality_blocks_unresolved_features(self):
        app = quantitative_quality_app()
        fits = {("Cu", 1): {"points": []}}
        rows = [{
            "element": "Cu",
            "distinct_levels": 3,
            "neutral_ratio": 0.25,
            "ionized_neutral_ratio": 3.0,
        }]
        line_audit = {"Cu": {
            "active_count": 3,
            "clean_feature_count": 1,
            "population_factor": 1.2,
            "branching_factor": 1.0,
            "unresolved_interferences": [{"line": "Cu I 300 nm"}],
        }}

        quality = cflibs_quantitation_quality(
            app, fits, rows, line_audit, 1.0, 1.0e17
        )

        self.assertFalse(quality["approved"])
        self.assertTrue(any("Analytical lines Cu" in item for item in quality["blockers"]))

    def test_line_audit_checks_same_upper_level_branching(self):
        kt = 1.0
        ek = 40000.0
        first = line_from_ordinate("Sn", 1, 300.0, ek, 15.0)
        second = line_from_ordinate("Sn", 1, 317.0, ek, 15.0 + math.log(3.0))
        app = fake_app([first, second])
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)

        audit = libspp_cflibs_line_audit(app, fits, kt)["Sn"]

        self.assertAlmostEqual(audit["branching_factor"], 3.0, places=9)
        self.assertEqual(len(audit["branching_groups"]), 1)
        self.assertEqual(audit["status"], "Poor")

    def test_fixed_temperature_intercepts_feed_cflibs_concentrations(self):
        kt = 0.88
        q_cu = 23.0
        q_zn = q_cu - math.log(3.0)
        lines = []
        for species, intercept, wavelengths in (
            ("Cu", q_cu, (296.1, 324.7, 465.1)),
            ("Zn", q_zn, (307.5, 330.2, 481.0)),
        ):
            for wavelength, energy in zip(wavelengths, (30000.0, 43000.0, 57000.0)):
                y = intercept - energy * EV_PER_CM / kt
                lines.append(line_from_ordinate(species, 1, wavelength, energy, y))
        app = fake_app(lines)
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = {row["element"]: row for row in libspp_saha_cflibs(app, fits, kt, 1.0e17)}
        self.assertAlmostEqual(fits[("Cu", 1)]["q"], q_cu, places=10)
        self.assertAlmostEqual(fits[("Zn", 1)]["q"], q_zn, places=10)
        self.assertAlmostEqual(rows["Cu"]["number_percent"], 75.0, places=9)
        self.assertAlmostEqual(rows["Zn"]["number_percent"], 25.0, places=9)
        self.assertEqual(rows["Cu"]["nlines"], 3)
        self.assertEqual(rows["Cu"]["distinct_levels"], 3)

    def test_four_element_fixed_temperature_pipeline_closes_exactly(self):
        kt = 0.93
        expected = {"Cu": 0.64, "Al": 0.21, "Zn": 0.10, "Sn": 0.05}
        lines = []
        for offset, (species, fraction) in enumerate(expected.items()):
            intercept = 24.0 + math.log(fraction)
            wavelengths = (295.0 + offset, 335.0 + offset, 470.0 + offset)
            for wavelength, energy in zip(wavelengths, (30000.0, 43000.0, 57000.0)):
                ordinate = intercept - energy * EV_PER_CM / kt
                lines.append(line_from_ordinate(species, 1, wavelength, energy, ordinate))

        app = fake_app(lines)
        app.analysis_elements = set(expected)
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = {
            row["element"]: row
            for row in libspp_saha_cflibs(app, fits, kt, 1.0e17)
        }

        self.assertEqual(set(rows), set(expected))
        for element, fraction in expected.items():
            self.assertAlmostEqual(
                rows[element]["number_percent"],
                100.0 * fraction,
                places=8,
            )
        self.assertAlmostEqual(
            sum(row["number_percent"] for row in rows.values()),
            100.0,
            places=10,
        )

    def test_four_element_robustness_uses_line_omission_and_replicates(self):
        kt = 0.93
        lines = []
        for offset, (species, fraction) in enumerate(
            {"Cu": 0.64, "Al": 0.21, "Zn": 0.10, "Sn": 0.05}.items()
        ):
            intercept = 24.0 + math.log(fraction)
            for index, (wavelength, energy) in enumerate(
                zip(
                    (295.0 + offset, 335.0 + offset, 410.0 + offset, 470.0 + offset),
                    (30000.0, 39000.0, 48000.0, 57000.0),
                )
            ):
                line = line_from_ordinate(
                    species,
                    1,
                    wavelength,
                    energy,
                    intercept - energy * EV_PER_CM / kt,
                )
                line.fit_replicate_areas = (
                    line.inte * 0.98,
                    line.inte,
                    line.inte * 1.02,
                )
                line.fit_replicate_area_mean = line.inte
                line.fit_replicate_area_total = 3
                line.fit_replicate_area_count = 3
                lines.append(line)

        app = fake_app(lines)
        app.analysis_elements = {"Cu", "Al", "Zn", "Sn"}
        app.last_saha_boltzmann = {
            "selected_element": "Cu",
            "elements": [{
                "element": "Cu",
                "quality": {
                    "relative_slope_error": 0.02,
                    "loo_relative_span": 0.03,
                },
            }],
        }
        app.last_halpha_result = {"ne_relative_uncertainty": 0.05}
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = libspp_saha_cflibs(app, fits, kt, 1.0e17)

        robustness = libspp_cflibs_robustness(
            app, groups, fits, rows, kt, 1.0e17
        )

        self.assertEqual(robustness["replicate_total"], 3)
        self.assertTrue(robustness["line_trials_complete"])
        self.assertTrue(robustness["replicate_trials_complete"])
        self.assertTrue(robustness["parameter_trials_complete"])
        self.assertEqual(len(robustness["parameter_trials"]), 4)
        self.assertLess(robustness["line_loo_max_relative_change"], 1.0e-9)
        self.assertLess(robustness["replicate_max_composition_cv"], 1.0e-9)
        self.assertLess(robustness["parameter_max_relative_change"], 1.0e-9)
        self.assertEqual(
            {item["active_lines"] for item in robustness["elements"].values()},
            {4},
        )

    def test_robustness_detects_an_influential_multielement_line(self):
        kt = 0.93
        lines = []
        for offset, (species, fraction) in enumerate(
            {"Cu": 0.64, "Al": 0.21, "Zn": 0.10, "Sn": 0.05}.items()
        ):
            intercept = 24.0 + math.log(fraction)
            for index, (wavelength, energy) in enumerate(
                zip(
                    (295.0 + offset, 335.0 + offset, 410.0 + offset, 470.0 + offset),
                    (30000.0, 39000.0, 48000.0, 57000.0),
                )
            ):
                ordinate = intercept - energy * EV_PER_CM / kt
                if species == "Zn" and index == 0:
                    ordinate += math.log(4.0)
                lines.append(
                    line_from_ordinate(species, 1, wavelength, energy, ordinate)
                )

        app = fake_app(lines)
        app.analysis_elements = {"Cu", "Al", "Zn", "Sn"}
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = libspp_saha_cflibs(app, fits, kt, 1.0e17)

        robustness = libspp_cflibs_robustness(
            app, groups, fits, rows, kt, 1.0e17
        )

        self.assertGreater(
            robustness["elements"]["Zn"]["loo_max_relative_change"],
            0.20,
        )
        self.assertIn("Zn I", robustness["elements"]["Zn"]["loo_worst_line"])

    def test_quality_gate_blocks_fragile_multielement_robustness(self):
        app = quantitative_quality_app()
        app.analysis_elements = {"Cu"}
        fits = {("Cu", 1): {"points": []}}
        rows = [{
            "element": "Cu",
            "distinct_levels": 3,
            "neutral_ratio": 0.25,
            "ionized_neutral_ratio": 3.0,
        }]
        line_audit = {"Cu": {
            "active_count": 3,
            "clean_feature_count": 3,
            "population_factor": 1.2,
            "branching_factor": 1.0,
        }}
        robustness = {
            "line_counts": {"Cu": 2},
            "line_trials": [{}, {}],
            "line_trials_complete": True,
            "line_loo_max_relative_change": 0.35,
            "replicate_total": 3,
            "replicate_trials": [{}, {}, {}],
            "replicate_trials_complete": True,
            "replicate_max_composition_cv": 0.25,
            "missing_replicate_lines": [],
            "parameter_trials": [{}, {}, {}, {}],
            "parameter_trials_complete": True,
            "parameter_max_relative_change": 0.30,
            "temperature_relative_uncertainty": 0.05,
            "ne_relative_uncertainty": 0.05,
        }

        quality = cflibs_quantitation_quality(
            app,
            fits,
            rows,
            line_audit,
            1.0,
            1.0e17,
            robustness,
        )

        self.assertFalse(quality["approved"])
        self.assertTrue(any("Multielement line redundancy" in item for item in quality["blockers"]))
        self.assertTrue(any("Leave-one-line-out" in item for item in quality["blockers"]))
        self.assertTrue(any("Replicate composition" in item for item in quality["blockers"]))
        self.assertTrue(any("T/Ne composition" in item for item in quality["blockers"]))

    def test_quality_gate_blocks_incomplete_selected_element_closure(self):
        app = quantitative_quality_app()
        app.analysis_elements = {"Cu", "Al", "Zn", "Sn"}
        fits = {("Cu", 1): {}, ("Al", 1): {}, ("Zn", 1): {}}
        rows = [
            {
                "element": element,
                "distinct_levels": 3,
                "neutral_ratio": 0.5,
            }
            for element in ("Cu", "Al", "Zn")
        ]
        line_audit = {
            element: {
                "active_count": 3,
                "clean_feature_count": 3,
                "population_factor": 1.0,
                "branching_factor": 1.0,
                "unresolved_interferences": [],
            }
            for element in ("Cu", "Al", "Zn")
        }

        quality = cflibs_quantitation_quality(
            app, fits, rows, line_audit, 1.0, 1.0e17
        )

        self.assertFalse(quality["approved"])
        coverage = next(
            check
            for check in quality["checks"]
            if check["name"] == "Selected-element coverage"
        )
        self.assertFalse(coverage["passed"])
        self.assertIn("missing=Sn", coverage["detail"])

    def test_cflibs_uses_only_elements_admitted_by_saha(self):
        kt = 0.88
        lines = []
        for species, intercept in (("Cu", 23.0), ("Zn", 22.0)):
            for wavelength, energy in zip((300.0, 340.0, 470.0), (30000.0, 43000.0, 57000.0)):
                lines.append(
                    line_from_ordinate(
                        species,
                        1,
                        wavelength,
                        energy,
                        intercept - energy * EV_PER_CM / kt,
                    )
                )
        app = fake_app(lines)
        app.last_saha_boltzmann = {
            "elements": [
                {"element": "Cu", "included": True},
                {"element": "Zn", "included": False},
            ]
        }
        groups, _ = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = libspp_saha_cflibs(app, fits, kt, 1.0e17)
        self.assertEqual(set(fits), {("Cu", 1)})
        self.assertEqual([row["element"] for row in rows], ["Cu"])
        self.assertAlmostEqual(rows[0]["number_percent"], 100.0)

    def test_analysis_and_irsac_ignore_lines_outside_acquired_windows(self):
        lines = [
            line_from_ordinate("Sn", 1, 300.913, 30000.0, 20.0),
            line_from_ordinate("Pb", 1, 405.781, 40000.0, 18.0),
            line_from_ordinate("Cd", 1, 479.991, 50000.0, 17.0),
        ]
        app = fake_app(lines)
        app.spectra = [
            merge_spectra_by_wavelength(
                Spectrum([290.0, 300.0, 330.0], [1.0, 2.0, 1.0]),
                Spectrum([350.0, 405.781, 410.0], [1.0, 2.0, 1.0]),
            )
        ]
        app.analysis_elements = {"Sn", "Pb", "Cd"}
        app.options.irsac_reference_lines = (
            '{"Sn I":300.913,"Pb I":405.781,"Cd I":479.991}'
        )

        groups, _skipped = libspp_boltzmann_groups_with_skips(app)
        references = _active_irsac_reference_lines(app)

        self.assertEqual(set(groups), {("Sn", 1), ("Pb", 1)})
        self.assertEqual(set(references), {("Sn", 1), ("Pb", 1)})

    def test_cflibs_plot_hides_elements_excluded_from_the_calculation(self):
        cd_key = ("Cd", 1)
        zn_key = ("Zn", 1)
        groups = {
            cd_key: [{"x": 4.0, "y": 12.0}],
            zn_key: [{"x": 7.5, "y": 13.5}],
        }
        fits = {
            cd_key: {
                "slope": -1.0,
                "q_at_t": 16.0,
            }
        }

        self.assertEqual(
            _cflibs_visible_groups(groups, fits),
            {cd_key: groups[cd_key]},
        )

    def test_saha_plot_hides_excluded_zinc_instead_of_fading_it(self):
        groups = {
            "Cd": [{"x": 4.0, "y": 12.0}],
            "Ni": [{"x": 5.0, "y": 11.0}],
            "Zn": [{"x": 7.5, "y": 13.5}],
        }

        self.assertEqual(
            _saha_visible_groups(groups, {"Cd", "Ni"}),
            {"Cd": groups["Cd"], "Ni": groups["Ni"]},
        )

    def test_excel_intercepts_and_manual_neutral_fractions_reproduce_sheet(self):
        corrected_points = {
            "Cd": (
                (30656.087, 17.500735072586718),
                (59485.768, 13.288445322245904),
                (51483.98, 14.4575824201139),
                (51483.98, 14.4575824201139),
            ),
            "Ni": (
                (33610.89, 13.497967292149513),
                (29888.477, 14.018431938799411),
                (29500.674, 14.072654227235642),
                (31441.635, 13.801270696975502),
            ),
            "Pb": (
                (49439.6165, 13.591134985434408),
                (35287.2244, 15.569910514527319),
                (34959.9084, 15.615675561630598),
                (48188.6296, 13.766046918869025),
                (35287.2244, 15.569910514527319),
            ),
        }
        groups = {
            (element, 1): [
                {
                    "x": energy * EV_PER_CM,
                    "y": ordinate,
                    "line": None,
                    "inactive": False,
                }
                for energy, ordinate in points
            ]
            for element, points in corrected_points.items()
        }
        partition_functions = {"Cd": 1.16, "Ni": 42.51, "Pb": 3.69}

        class ExcelDatabase(FakeDatabase):
            def partition_function(self, element, _ion, _temperature_k):
                return partition_functions[element]

        app = fake_app([])
        app.libs_db = ExcelDatabase()
        app.options.cflibs_ionization_mode = "manual"
        app.options.cflibs_neutral_fractions = "Cd=0.03; Ni=0.024; Pb=0.013"
        kt = 10290.270625232668 / 11604.45
        fits = libspp_fit_boltzmann_excel_intercepts(app, groups, kt)
        rows = {
            row["element"]: row
            for row in libspp_saha_cflibs(
                app,
                fits,
                kt,
                1.0589e16,
                ionization_mode="manual",
            )
        }

        self.assertAlmostEqual(fits[("Cd", 1)]["q"], 21.979880057078788, places=8)
        self.assertAlmostEqual(fits[("Ni", 1)]["q"], 18.197413588795968, places=8)
        self.assertAlmostEqual(fits[("Pb", 1)]["q"], 20.503740473374364, places=8)
        self.assertAlmostEqual(rows["Cd"]["number_percent"], 26.87877222031957, places=7)
        self.assertAlmostEqual(rows["Ni"]["number_percent"], 28.03162279873725, places=7)
        self.assertAlmostEqual(rows["Pb"]["number_percent"], 45.089604980943164, places=7)

    def test_post_irsac_keeps_pre_correction_reference_element(self):
        app = fake_app([])
        app.apply_sac_correction = True
        app.last_self_absorption_result = {
            "irsac_completed": True,
            "corrected_lines": 4,
            "applied": True,
            "enabled_lines": 4,
        }
        app.last_saha_boltzmann = {
            "representative_mode": "most reliable element",
            "selected_element": "Pb",
            "elements": [
                {"element": "Cd", "included": True},
                {"element": "Pb", "included": True},
                {"element": "Zn", "included": False},
            ],
        }
        fits = {"Cd": {"kt": 1.06}, "Pb": {"kt": 1.06}, "Zn": {"kt": 0.01}}
        self.assertEqual(
            _locked_post_irsac_saha_element(app, fits, {"Cd", "Pb"}),
            "Pb",
        )

    def test_manual_irsac_reference_overrides_pre_correction_auto_reference(self):
        app = fake_app([])
        app.apply_sac_correction = True
        app.last_self_absorption_result = {
            "irsac_completed": True,
            "corrected_lines": 4,
            "applied": True,
            "enabled_lines": 4,
            "thermometric_species": ("Cd", 1),
        }
        app.last_saha_boltzmann = {
            "representative_mode": "most reliable element",
            "selected_element": "Pb",
            "elements": [
                {"element": "Cd", "temperature": 0.82, "included": True},
                {"element": "Pb", "temperature": 1.06, "included": True},
            ],
        }
        fits = {"Cd": {"kt": 0.82}, "Pb": {"kt": 1.06}}
        self.assertEqual(
            _locked_post_irsac_saha_element(app, fits, {"Cd", "Pb"}),
            "Cd",
        )
        self.assertAlmostEqual(
            _saha_temperature_for_irsac_reference(app, ("Cd", 1)),
            0.82 * 11604.45,
            places=6,
        )

    def test_excel_irsac_temperature_is_authoritative_and_identified(self):
        app = SimpleNamespace(
            apply_sac_correction=True,
            last_self_absorption_result={
                "irsac_completed": True,
                "corrected_lines": 4,
                "applied": True,
                "enabled_lines": 4,
                "equation_mode": "excel_worksheet",
                "temperature_k": 10290.270625232668,
                "thermometric_species": ("Cd", 1),
            },
        )
        self.assertAlmostEqual(
            _worksheet_irsac_temperature_ev(app),
            10290.270625232668 / 11604.45,
            places=12,
        )
        self.assertEqual(
            _worksheet_irsac_temperature_source(app),
            "legacy IRSAC worksheet T (Cd I)",
        )

    def test_app_defaults_use_common_temperature_slope_and_saha(self):
        options = AppOptions()
        self.assertEqual(options.irsac_equation_mode, "staged")
        self.assertEqual(options.cflibs_intercept_mode, "fixed_temperature")
        self.assertEqual(options.cflibs_ionization_mode, "saha")

    def test_staged_irsac_applies_positive_multiplier_below_one(self):
        line = SimpleNamespace(sa_use=True, sa_sac=0.544923452807984)
        self.assertAlmostEqual(
            _sac_factor_for_line(line),
            0.544923452807984,
            places=15,
        )

        app = SimpleNamespace(
            apply_sac_correction=True,
            template_lines=[line],
            last_self_absorption_result={
                "mode": "irsac",
                "equation_mode": "staged",
                "converged": True,
                "assessment_status": "Not assessable",
                "assessment_can_apply": True,
            },
        )
        self.assertEqual(_self_absorption_quantification_blocker(app), "")

    def test_only_common_temperature_mode_is_quantitative(self):
        self.assertTrue(
            _cflibs_intercept_mode_is_quantitative("fixed_temperature")
        )
        self.assertFalse(
            _cflibs_intercept_mode_is_quantitative("excel_free")
        )

    def test_trace_delete_removes_whole_element_but_preserves_voigt_fit(self):
        sn = line_from_ordinate("Sn", 1, 300.913, 34914.282, 13.5)
        pb = line_from_ordinate("Pb", 1, 405.781, 35287.224, 12.6)
        sn.asswavelen = 300.91335
        sn.ei = 1691.806
        sn.gi = 3
        sn.acc = 2
        original_fit = (sn.wavelen, sn.fitwavelen, sn.inte, sn.wg, sn.wl)
        app = SimpleNamespace(
            trace_markers=[
                SimpleNamespace(specie="Sn"),
                SimpleNamespace(specie="Sn"),
                SimpleNamespace(specie="Pb"),
            ],
            analysis_elements={"Sn", "Pb"},
            template_lines=[sn, pb],
        )

        removed, cleared = remove_traced_elements(app, {"Sn"})

        self.assertEqual((removed, cleared), (2, 1))
        self.assertEqual(app.analysis_elements, {"Pb"})
        self.assertEqual([marker.specie for marker in app.trace_markers], ["Pb"])
        self.assertEqual(sn.specie, "")
        self.assertEqual(sn.ion, 0)
        self.assertEqual(sn.asswavelen, 0.0)
        self.assertEqual(sn.ek, 0.0)
        self.assertEqual(sn.aki, 0.0)
        self.assertEqual(
            (sn.wavelen, sn.fitwavelen, sn.inte, sn.wg, sn.wl),
            original_fit,
        )
        self.assertEqual(pb.specie, "Pb")

    def test_sn_pb_workbook_data_use_fixed_common_slope(self):
        workbook_rows = {
            "Sn": (
                (301.25272, 34914.282, 1.10e8, 0.0000537223, 3),
                (314.53632, 48981.934, 5.70e7, 0.0000076256, 3),
                (317.86517, 34914.282, 3.00e8, 0.0000620232, 3),
                (326.63855, 39257.053, 8.10e8, 0.0000748498, 3),
            ),
            "Pb": (
                (357.56234, 49439.6165, 3.00e8, 0.000013363, 3),
                (364.25019, 35287.2244, 9.60e7, 0.0000211905, 3),
                (368.66055, 34959.9084, 1.37e8, 0.0000202677, 1),
                (374.31791, 48188.6296, 3.60e8, 0.00000887324, 5),
                (406.16523, 35287.2244, 2.70e8, 0.0000411881, 3),
            ),
        }
        lines = []
        for element, rows in workbook_rows.items():
            for wavelength, energy, akgk, area, gk in rows:
                lines.append(
                    TemplateLine(
                        wavelen=wavelength,
                        fitwavelen=wavelength,
                        asswavelen=wavelength,
                        specie=element,
                        ion=1,
                        inte=area,
                        ek=energy,
                        aki=akgk / gk,
                        gk=gk,
                        wg=0.05,
                        wl=0.05,
                    )
                )

        class WorkbookDatabase(FakeDatabase):
            partition_functions = {
                ("Sn", 1): 10.038800454884962,
                ("Sn", 2): 4.441725912057888,
                ("Pb", 1): 4.763930061232743,
                ("Pb", 2): 2.741542106515942,
            }
            ionization = {"Sn": 59232.69140625, "Pb": 59819.55859375}

            def element_metadata(self, element):
                return {
                    "en_ion": self.ionization[element],
                    "m_atomica": 1.0,
                }

            def partition_function(self, element, ion, _temperature_k):
                return self.partition_functions[(element, ion)]

        app = fake_app(lines)
        app.analysis_elements = {"Sn", "Pb"}
        app.libs_db = WorkbookDatabase()
        kt = 11925.801001532618 / 11604.45
        groups, skipped = libspp_boltzmann_groups_with_skips(app)
        fits = libspp_fit_boltzmann_fixed_temperature(app, groups, kt)
        rows = {
            row["element"]: row
            for row in libspp_saha_cflibs(app, fits, kt, 1.0589e16)
        }

        self.assertEqual(skipped, 0)
        self.assertAlmostEqual(fits[("Sn", 1)]["q"], 17.372351706954763)
        self.assertAlmostEqual(fits[("Pb", 1)]["q"], 16.92657100533557)
        self.assertAlmostEqual(rows["Sn"]["number_percent"], 73.10477572088877)
        self.assertAlmostEqual(rows["Pb"]["number_percent"], 26.895224279111236)

    def test_cflibs_rejects_factors_computed_with_a_different_irsac_equation(self):
        options = SimpleNamespace(
            irsac_equation_mode="excel_worksheet",
            irsac_mode="irsac",
            irsac_reference_lines='{"Cd I": 340.36521}',
            irsac_thermometric_species="Cd I",
        )
        app = SimpleNamespace(
            options=options,
            apply_sac_correction=True,
            last_self_absorption_result={
                "mode": "irsac",
                "equation_mode": "strict",
                "reference_lines": {"Cd I": 340.36521},
                "requested_thermometric_species": ("Cd", 1),
            },
        )
        self.assertIn("staged", _irsac_configuration_mismatch(app))
        app.last_self_absorption_result["equation_mode"] = "excel_worksheet"
        self.assertEqual(_irsac_configuration_mismatch(app), "")

    def test_cflibs_blocks_unsafe_manual_irsac_override(self):
        line = SimpleNamespace(
            specie="Si",
            ion=1,
            asswavelen=298.7645,
            sa_use=True,
            sa_sac=1.5,
            sa_recommended=False,
        )
        app = SimpleNamespace(
            apply_sac_correction=True,
            template_lines=[line],
            last_self_absorption_result={
                "assessment_status": "Correction unsafe",
                "assessment_can_apply": False,
            },
        )

        reason = _self_absorption_quantification_blocker(app)

        self.assertIn("Correction unsafe", reason)

    def test_cflibs_allows_only_independently_supported_corrections(self):
        line = SimpleNamespace(
            specie="Sn",
            ion=1,
            asswavelen=317.504,
            sa_use=True,
            sa_sac=2.0,
            sa_recommended=True,
        )
        app = SimpleNamespace(
            apply_sac_correction=True,
            template_lines=[line],
            last_self_absorption_result={
                "assessment_status": "Self-absorption compatible",
                "assessment_can_apply": True,
            },
        )

        self.assertEqual(_self_absorption_quantification_blocker(app), "")

    def test_cflibs_without_self_absorption_correction_is_not_blocked(self):
        app = SimpleNamespace(
            apply_sac_correction=False,
            template_lines=[],
            last_self_absorption_result={
                "assessment_status": "Correction unsafe",
                "assessment_can_apply": False,
            },
        )

        self.assertEqual(_self_absorption_quantification_blocker(app), "")

    def test_trace_selection_excludes_unrequested_elements_from_all_groups(self):
        lines = [
            line_from_ordinate("Cd", 1, 326.1, 30000.0, 20.0),
            line_from_ordinate("Cd", 1, 340.3, 40000.0, 18.0),
            line_from_ordinate("Zn", 1, 328.2, 30000.0, 21.0),
            line_from_ordinate("Zn", 1, 334.5, 40000.0, 19.0),
        ]
        app = fake_app(lines)
        app.analysis_elements = {"Cd"}
        boltzmann, _skipped = libspp_boltzmann_groups_with_skips(app)
        saha, _skipped = libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
        self.assertEqual(set(boltzmann), {("Cd", 1)})
        self.assertEqual(set(saha), {"Cd"})

    def test_saha_plot_uses_free_slopes_before_irsac_only(self):
        groups = {
            "Cd": [{"x": 1.0, "y": 4.0}, {"x": 2.0, "y": 2.0}],
            "Ni": [{"x": 1.0, "y": 5.0}, {"x": 2.0, "y": 4.0}],
        }
        fits = {
            "Cd": {"slope": -2.0, "q": 6.0},
            "Ni": {"slope": -1.0, "q": 6.0},
        }
        app = fake_app([])
        app.last_self_absorption_result = None
        plot_fits, common = _saha_plot_fit_results(app, groups, fits, 0.8)
        self.assertFalse(common)
        self.assertIs(plot_fits, fits)

        app.apply_sac_correction = True
        app.last_self_absorption_result = {
            "irsac_completed": True,
            "corrected_lines": 2,
            "applied": True,
            "enabled_lines": 2,
        }
        plot_fits, common = _saha_plot_fit_results(app, groups, fits, 0.8)
        self.assertTrue(common)
        self.assertAlmostEqual(plot_fits["Cd"]["slope"], -1.25)
        self.assertAlmostEqual(plot_fits["Ni"]["slope"], -1.25)


if __name__ == "__main__":
    unittest.main()
