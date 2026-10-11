import math
import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from pyLIBS import (
    _stark_row_map,
    _sync_self_absorption_temperature,
    calculate_hybrid_self_absorption,
)
from pylibs.core.models import TemplateLine
from pylibs.core.self_absorption import (
    CM_PER_K,
    LineCorrection,
    LineObservation,
    assess_self_absorption,
    hybrid_self_absorption,
    most_reliable_thermometric_key,
    palleschi_sac_multiplier,
    select_yang_reference,
    thermometric_temperature,
    yang_aslam_factor,
)


@dataclass
class DummyLine:
    name: str


def observation(name, wavelength, intensity, ei, ek, aki):
    return LineObservation(DummyLine(name), "Cu", 1, wavelength, intensity, ei, ek, aki, 2.0)


class SelfAbsorptionTests(unittest.TestCase):
    def test_photon_counting_thermometry_does_not_reapply_wavelength_factor(self):
        temperature = 10000.0
        intercept = 12.0
        rows = []
        for index, (wavelength, energy) in enumerate(
            ((300.0, 30000.0), (400.0, 50000.0), (600.0, 70000.0))
        ):
            intensity = math.exp(intercept - energy / (CM_PER_K * temperature))
            rows.append(LineObservation(
                DummyLine(f"line {index}"),
                "Cu",
                1,
                wavelength,
                intensity,
                0.0,
                energy,
                1.0,
                1.0,
                intensity_mode="photon",
            ))

        fitted = thermometric_temperature(rows, {}, ("Cu", 1))

        self.assertAlmostEqual(fitted, temperature, places=7)

    def test_independent_same_upper_level_mismatch_supports_irsac(self):
        reference = LineObservation(
            DummyLine("reference"),
            "Sn",
            1,
            300.0,
            100.0,
            1000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=100.0,
        )
        target = LineObservation(
            DummyLine("target"),
            "Sn",
            1,
            600.0,
            25.0,
            2000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=100.0,
        )
        corrections = {
            id(reference.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
            id(target.line): LineCorrection(
                2.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
        }

        assessment = assess_self_absorption(
            [reference, target],
            corrections,
        )

        self.assertEqual(assessment.status, "Self-absorption compatible")
        self.assertFalse(assessment.lines[id(reference.line)].recommended_use)
        self.assertTrue(assessment.lines[id(target.line)].recommended_use)
        self.assertEqual(
            assessment.species[("Sn", 1)].reference_quality,
            "valid",
        )

    def test_dirty_target_fit_cannot_support_irsac(self):
        reference = LineObservation(
            DummyLine("reference"),
            "Sn",
            1,
            300.0,
            100.0,
            1000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=100.0,
        )
        target = LineObservation(
            DummyLine("target"),
            "Sn",
            1,
            600.0,
            25.0,
            2000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=4.0,
        )
        corrections = {
            id(reference.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
            id(target.line): LineCorrection(
                2.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
        }

        assessment = assess_self_absorption([reference, target], corrections)

        self.assertEqual(assessment.status, "Correction unsafe")
        self.assertFalse(assessment.can_apply)
        self.assertEqual(assessment.lines[id(target.line)].status, "Unsafe")
        self.assertIn(
            "below 10",
            assessment.lines[id(target.line)].reason,
        )

    def test_supported_species_is_kept_when_another_species_is_not_assessable(self):
        sn_reference = LineObservation(
            DummyLine("Sn reference"), "Sn", 1, 300.0, 100.0,
            1000.0, 40000.0, 1.0, 1.0,
            accuracy_percent=5.0, snr=100.0,
        )
        sn_target = LineObservation(
            DummyLine("Sn target"), "Sn", 1, 600.0, 25.0,
            2000.0, 40000.0, 1.0, 1.0,
            accuracy_percent=5.0, snr=100.0,
        )
        pb_reference = LineObservation(
            DummyLine("Pb reference"), "Pb", 1, 400.0, 100.0,
            1000.0, 50000.0, 1.0, 1.0,
            accuracy_percent=5.0, snr=100.0,
        )
        pb_target = LineObservation(
            DummyLine("Pb target"), "Pb", 1, 410.0, 120.0,
            2000.0, 60000.0, 1.0, 1.0,
            accuracy_percent=5.0, snr=100.0,
        )
        corrections = {
            id(sn_reference.line): LineCorrection(
                1.0, "IRSAC Yang/Aslam", reference_wavelength=300.0,
            ),
            id(sn_target.line): LineCorrection(
                2.0, "IRSAC Yang/Aslam", reference_wavelength=300.0,
            ),
            id(pb_reference.line): LineCorrection(
                1.0, "IRSAC Yang/Aslam", reference_wavelength=400.0,
            ),
            id(pb_target.line): LineCorrection(
                0.7, "IRSAC Yang/Aslam", reference_wavelength=400.0,
            ),
        }

        assessment = assess_self_absorption(
            [sn_reference, sn_target, pb_reference, pb_target],
            corrections,
        )

        self.assertEqual(assessment.status, "Self-absorption compatible")
        self.assertTrue(assessment.can_apply)
        self.assertTrue(assessment.lines[id(sn_target.line)].recommended_use)
        self.assertFalse(assessment.lines[id(pb_target.line)].recommended_use)
        self.assertEqual(
            assessment.species[("Pb", 1)].status,
            "Not assessable",
        )

    def test_consistent_same_upper_level_pair_does_not_enable_irsac(self):
        reference = LineObservation(
            DummyLine("reference"),
            "Pb",
            1,
            300.0,
            100.0,
            1000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=100.0,
        )
        target = LineObservation(
            DummyLine("target"),
            "Pb",
            1,
            600.0,
            50.0,
            2000.0,
            40000.0,
            1.0,
            1.0,
            accuracy_percent=5.0,
            snr=100.0,
        )
        corrections = {
            id(reference.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
            id(target.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
        }

        assessment = assess_self_absorption(
            [reference, target],
            corrections,
        )

        self.assertEqual(assessment.status, "No significant evidence")
        self.assertFalse(assessment.can_apply)
        self.assertFalse(assessment.lines[id(target.line)].recommended_use)

    def test_relative_irsac_multiplier_below_one_is_allowed(self):
        reference = LineObservation(
            DummyLine("reference"),
            "Cd",
            1,
            300.0,
            100.0,
            1000.0,
            40000.0,
            1.0,
            1.0,
            snr=100.0,
        )
        target = LineObservation(
            DummyLine("target"),
            "Cd",
            1,
            310.0,
            120.0,
            2000.0,
            50000.0,
            1.0,
            1.0,
            snr=100.0,
        )
        corrections = {
            id(reference.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
            id(target.line): LineCorrection(
                0.7,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
        }

        assessment = assess_self_absorption(
            [reference, target],
            corrections,
        )

        self.assertEqual(assessment.status, "Not assessable")
        self.assertNotEqual(assessment.lines[id(target.line)].status, "Unsafe")
        self.assertFalse(assessment.lines[id(target.line)].recommended_use)

    def test_al_si_workbook_flags_only_extreme_relative_factors(self):
        rows = [
            LineObservation(DummyLine("Al 308"), "Al", 1, 308.21529, 0.00177, 0.0, 32435.453, 2.35e8, 1.0, snr=100.0),
            LineObservation(DummyLine("Al 394"), "Al", 1, 394.400585, 0.00109, 0.0, 25347.756, 9.98e7, 1.0, snr=100.0),
            LineObservation(DummyLine("Al 396"), "Al", 1, 396.152, 0.00183, 0.0, 25347.756, 1.97e8, 1.0, snr=100.0),
            LineObservation(DummyLine("Si 288"), "Si", 1, 288.15795, 1.24972e-4, 0.0, 40991.884, 6.51e8, 1.0, snr=100.0),
            LineObservation(DummyLine("Si 298"), "Si", 1, 298.7645, 1.24972e-4, 0.0, 39760.285, 7.98e6, 1.0, snr=100.0),
            LineObservation(DummyLine("Si 390"), "Si", 1, 390.55232, 1.48764e-5, 0.0, 40991.884, 3.99e7, 1.0, snr=100.0),
        ]
        factors = [1.18235, 1.0, 0.85053, 0.51488, 36.6311, 1.0]
        references = [394.400585] * 3 + [390.55232] * 3
        corrections = {
            id(row.line): LineCorrection(
                1.0 / factor,
                "IRSAC Yang/Aslam",
                reference_wavelength=reference,
            )
            for row, factor, reference in zip(rows, factors, references)
        }

        assessment = assess_self_absorption(rows, corrections)

        self.assertEqual(assessment.status, "Selective correction available")
        self.assertTrue(assessment.can_apply)
        self.assertEqual(
            assessment.lines[id(rows[4].line)].status,
            "Unsafe",
        )

    def test_sn_pb_workbook_factors_are_rejected_for_quantification(self):
        rows = [
            LineObservation(DummyLine("Pb 357"), "Pb", 1, 357.273, 1.0, 0.0, 50000.0, 1.0, 1.0, snr=100.0),
            LineObservation(DummyLine("Pb 374"), "Pb", 1, 373.994, 1.0, 0.0, 60000.0, 1.0, 1.0, snr=100.0),
            LineObservation(DummyLine("Sn 300"), "Sn", 1, 300.913, 1.0, 0.0, 50000.0, 1.0, 1.0, snr=100.0),
            LineObservation(DummyLine("Sn 314"), "Sn", 1, 314.183, 1.0, 0.0, 60000.0, 1.0, 1.0, snr=100.0),
            LineObservation(DummyLine("Sn 326"), "Sn", 1, 326.233, 1.0, 0.0, 70000.0, 1.0, 1.0, snr=100.0),
        ]
        factors = [2.1016, 1.0, 0.6437, 1.0, 0.2081]
        references = [373.994, 373.994, 314.183, 314.183, 314.183]
        corrections = {
            id(row.line): LineCorrection(
                1.0 / factor,
                "IRSAC Yang/Aslam",
                reference_wavelength=reference,
            )
            for row, factor, reference in zip(rows, factors, references)
        }

        assessment = assess_self_absorption(rows, corrections)

        self.assertEqual(assessment.status, "Correction unsafe")
        self.assertFalse(assessment.can_apply)

    def test_missing_reference_fit_quality_remains_not_assessable(self):
        reference = LineObservation(
            DummyLine("reference"),
            "Cu",
            1,
            300.0,
            100.0,
            1000.0,
            40000.0,
            1.0,
            1.0,
        )
        target = LineObservation(
            DummyLine("target"),
            "Cu",
            1,
            600.0,
            25.0,
            2000.0,
            40000.0,
            1.0,
            1.0,
        )
        corrections = {
            id(reference.line): LineCorrection(
                1.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
            id(target.line): LineCorrection(
                2.0,
                "IRSAC Yang/Aslam",
                reference_wavelength=300.0,
            ),
        }

        assessment = assess_self_absorption(
            [reference, target],
            corrections,
        )

        self.assertEqual(assessment.status, "Not assessable")
        self.assertFalse(assessment.can_apply)

    def test_yang_reference_prefers_high_lower_energy_and_low_aki(self):
        low = observation("low", 300.0, 10.0, 100.0, 10000.0, 1.0e8)
        reference = observation("reference", 310.0, 12.0, 5000.0, 12000.0, 1.0e5)
        self.assertIs(select_yang_reference([low, reference]), reference)
        self.assertAlmostEqual(yang_aslam_factor(reference, reference, 10000.0), 1.0)

    def test_yang_tie_keeps_first_available_line(self):
        first = observation("first", 300.0, 10.0, 100.0, 10000.0, 1.0e5)
        second = observation("second", 310.0, 10.0, 5000.0, 12000.0, 1.0e8)

        self.assertIs(select_yang_reference([first, second]), first)

    def test_manual_irsac_line_reference_overrides_automatic_ranking(self):
        automatic = observation("automatic", 326.1054, 10.0, 5000.0, 30000.0, 1.0e5)
        manual = observation("manual", 340.36521, 12.0, 100.0, 59000.0, 2.0e8)

        result = hybrid_self_absorption(
            [automatic, manual],
            10000.0,
            mode="irsac",
            thermometric_key=("Cu", 1),
            reference_wavelengths={("Cu", 1): 340.36521},
        )

        self.assertAlmostEqual(
            result.corrections[id(automatic.line)].reference_wavelength,
            340.36521,
            places=8,
        )
        self.assertAlmostEqual(
            result.corrections[id(manual.line)].multiplier,
            1.0,
            places=12,
        )

    def test_yang_aslam_equation_does_not_contain_wavelength_ratio(self):
        reference = observation("reference", 300.0, 5.0, 5000.0, 20000.0, 2.0e6)
        target = observation("target", 600.0, 7.0, 1000.0, 35000.0, 4.0e6)
        temperature = 10000.0
        expected = (
            target.intensity
            * reference.ag
            / (reference.intensity * target.ag)
            * math.exp(
                -(reference.ek_cm - target.ek_cm)
                / (CM_PER_K * temperature)
            )
        )

        self.assertAlmostEqual(
            yang_aslam_factor(target, reference, temperature),
            expected,
            places=12,
        )

    def test_irsac_matches_the_workbook_staged_cadmium_calculation(self):
        initial_temperature = 11110.057424870804
        wavelengths = (326.1054, 340.36521, 467.81493, 479.99123)
        lower_energies = (0.0, 30113.99, 30113.99, 30656.087)
        upper_energies = (30656.08791, 59485.76862, 51483.98051, 51483.98051)
        ag_values = (1220000.0, 230000000.0, 39000000.0, 120000000.0)
        intensities = (0.000247211, 0.00116, 0.000286609, 0.00108)
        cadmium = [
            LineObservation(
                DummyLine(f"Cd{index}"),
                "Cd",
                1,
                wavelength,
                intensity,
                lower,
                upper,
                ag,
                1.0,
            )
            for index, (wavelength, intensity, lower, upper, ag) in enumerate(
                zip(
                    wavelengths,
                    intensities,
                    lower_energies,
                    upper_energies,
                    ag_values,
                )
            )
        ]
        result = hybrid_self_absorption(
            cadmium,
            initial_temperature,
            mode="irsac",
            thermometric_key=("Cd", 1),
            equation_mode="strict",
        )

        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 1)
        raw_temperature = thermometric_temperature(cadmium, {}, ("Cd", 1))
        self.assertAlmostEqual(result.temperature_history[0], raw_temperature, places=12)
        self.assertAlmostEqual(result.temperature_k, 11678.689216950326, places=6)
        reference = cadmium[0]
        expected_factor = yang_aslam_factor(
            cadmium[1],
            reference,
            raw_temperature,
        )
        self.assertAlmostEqual(
            result.corrections[id(cadmium[1].line)].multiplier,
            1.0 / expected_factor,
            places=12,
        )

    def test_staged_aslam_matches_verified_cd_ni_pb_workbook(self):
        specifications = {
            ("Cd", 1): (
                (326.1054, 340.36521, 467.81493, 479.99123),
                (30656.087, 59485.768, 51483.98, 51483.98),
                (1.22e6, 2.30e8, 3.90e7, 1.20e8),
                (2.22704e-5, 7.4809e-5, 9.25003e-5, 1.22328e-4),
                326.1054,
            ),
            ("Ni", 1): (
                (313.411, 344.626, 349.296, 356.637),
                (33610.89, 29888.477, 29500.674, 31441.635),
                (3.6e8, 2.2e8, 2.9e8, 2.8e8),
                (1.49534e-4, 1.37126e-4, 1.9294e-4, 1.35235e-4),
                356.637,
            ),
            ("Pb", 1): (
                (357.27, 363.95677, 368.34625, 373.99353, 405.78067),
                (49439.6165, 35287.2244, 34959.9084, 48188.6296, 35287.2244),
                (3.0e8, 9.6e7, 1.37e8, 3.6e8, 2.7e8),
                (1.81407e-4, 2.64994e-4, 4.32669e-4, 1.8709e-4, 7.65594e-4),
                373.99353,
            ),
        }
        observations = []
        references = {}
        for key, (wavelengths, energies, ag_values, intensities, reference) in specifications.items():
            references[key] = reference
            for index, (wavelength, energy, ag, intensity) in enumerate(
                zip(wavelengths, energies, ag_values, intensities)
            ):
                observations.append(LineObservation(
                    DummyLine(f"{key[0]}{index}"),
                    key[0],
                    key[1],
                    wavelength,
                    intensity,
                    0.0,
                    energy,
                    ag,
                    1.0,
                    transition_wavelength=wavelength,
                ))

        result = hybrid_self_absorption(
            observations,
            9000.0,
            mode="irsac",
            thermometric_key=("Cd", 1),
            reference_wavelengths=references,
            equation_mode="staged",
        )

        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 1)
        self.assertEqual(len(result.corrections), 13)
        self.assertEqual(set(result.selected_line_ids), set(result.corrections))
        self.assertAlmostEqual(result.temperature_history[0], 11317.294003287836, places=6)
        self.assertAlmostEqual(result.temperature_k, 11907.157093431775, places=6)
        expected = {
            ("Cd", 1): (1.0, 1.4367842655769605, 0.544923452807984, 1.2678544659697852),
            ("Ni", 1): (0.8946588142719895, 0.9348440140420775, 0.9178311079892142, 1.0),
            ("Pb", 1): (0.7388684829526454, 0.8949760301664668, 0.8137998181642637, 1.0, 0.871247318765476),
        }
        for key, multipliers in expected.items():
            actual = [
                result.corrections[id(observation.line)].multiplier
                for observation in observations
                if observation.key == key
            ]
            for value, expected_value in zip(actual, multipliers):
                self.assertAlmostEqual(value, expected_value, places=12)

        cd_slope = result.species_slope_validation[("Cd", 1)]["slope"]
        ni_slope = result.species_slope_validation[("Ni", 1)]["slope"]
        pb_slope = result.species_slope_validation[("Pb", 1)]["slope"]
        self.assertAlmostEqual(cd_slope, -0.00012083295366171619, places=15)
        self.assertAlmostEqual(ni_slope, -0.00014454673984924535, places=15)
        self.assertAlmostEqual(pb_slope, -0.00012354394377507441, places=15)
        self.assertNotAlmostEqual(ni_slope, cd_slope, places=8)
        self.assertNotAlmostEqual(pb_slope, cd_slope, places=8)

    def test_excel_worksheet_mode_reproduces_22_july_irsac_sequence(self):
        rows = (
            (326.50626, 30656.087, 1220000.0, 0.0000383998),
            (340.75802, 59485.768, 230000000.0, 0.0000793073),
            (468.1731, 51483.98, 39000000.0, 0.0000868703),
            (480.41319, 51483.98, 120000000.0, 0.000142203),
        )
        cadmium = [
            LineObservation(
                DummyLine(f"Cd{index}"),
                "Cd",
                1,
                wavelength,
                intensity,
                0.0,
                energy,
                ag,
                1.0,
            )
            for index, (wavelength, energy, ag, intensity) in enumerate(rows)
        ]

        result = hybrid_self_absorption(
            cadmium,
            9847.252511881234,
            mode="irsac",
            thermometric_key=("Cd", 1),
            reference_wavelengths={("Cd", 1): 340.36521},
            equation_mode="excel_worksheet",
        )

        expected_multipliers = (
            0.7709816510582469,
            0.9988472465006106,
            0.36229897947553025,
            0.6636480863040962,
        )
        self.assertAlmostEqual(result.temperature_k, 10290.270625232668, places=3)
        for observation, expected in zip(cadmium, expected_multipliers):
            self.assertAlmostEqual(
                result.corrections[id(observation.line)].multiplier,
                expected,
                places=6,
            )

    def test_post_irsac_temperature_is_published_without_an_open_saha_window(self):
        app = SimpleNamespace(
            last_self_absorption_result={
                "input_temperature_k": 10000.0,
                "temperature_k": 11677.9737252994,
                "thermometric_species": ("Cd", 1),
                "enabled_lines": 4,
            },
            post_irsac_temperature=None,
            post_irsac_temperature_source=None,
            session_temperature=1.0,
            session_temperature_source="most reliable element",
        )

        self.assertTrue(_sync_self_absorption_temperature(app, True))
        self.assertAlmostEqual(
            app.session_temperature,
            11677.9737252994 / 11604.45,
            places=12,
        )
        self.assertIn("Cd I", app.session_temperature_source)
        self.assertEqual(app.session_temperature, app.post_irsac_temperature)

        self.assertFalse(_sync_self_absorption_temperature(app, False))
        self.assertAlmostEqual(
            app.session_temperature,
            10000.0 / 11604.45,
            places=12,
        )
        self.assertIsNone(app.post_irsac_temperature)

    def test_palleschi_is_prioritized_in_hybrid_mode(self):
        first = observation("first", 300.0, 10.0, 100.0, 10000.0, 1.0e6)
        second = observation("second", 310.0, 8.0, 5000.0, 20000.0, 2.0e6)

        def palleschi(obs, _temperature):
            return 2.0 if obs.line is first.line else None

        result = hybrid_self_absorption(
            [first, second], 10000.0, mode="hybrid", palleschi_factor=palleschi
        )
        self.assertEqual(result.corrections[id(first.line)].method, "Palleschi/Stark")
        self.assertEqual(result.corrections[id(first.line)].multiplier, 2.0)
        self.assertEqual(
            result.corrections[id(second.line)].method,
            "IRSAC Aslam (staged)",
        )

    def test_selective_iterative_irsac_converges_and_reconstructs_parallel_lines(self):
        target_temperature = 11000.0
        rows = []
        references = {}
        specifications = (
            ("A", 15.0, (0.42, 0.58, 0.75, 0.92), 0.0),
            ("B", 14.0, (0.30, 0.50, 0.72, 0.96), 20.0),
            ("C", 13.0, (0.55, 0.68, 0.82, 0.94), 40.0),
        )
        for species, intercept, absorptions, offset in specifications:
            for index, (energy, absorption) in enumerate(
                zip((10000.0, 20000.0, 30000.0, 40000.0), absorptions)
            ):
                wavelength = 300.0 + offset + index * 10.0
                ag = 1.0e6 * (index + 1)
                thin_intensity = (
                    math.exp(
                        intercept - energy / (CM_PER_K * target_temperature)
                    )
                    * ag
                    / wavelength
                )
                rows.append(LineObservation(
                    DummyLine(f"{species}{index}"),
                    species,
                    1,
                    wavelength + 0.4,
                    thin_intensity * absorption,
                    1000.0 + index * 1000.0,
                    energy,
                    ag,
                    1.0,
                    accuracy_percent=5.0,
                    transition_wavelength=wavelength,
                ))
            references[(species, 1)] = 330.0 + offset

        result = hybrid_self_absorption(
            rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            reference_wavelengths=references,
            max_iterations=100,
        )
        repeated = hybrid_self_absorption(
            rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            reference_wavelengths=references,
            max_iterations=100,
        )

        self.assertTrue(result.converged)
        self.assertGreaterEqual(result.iterations, 2)
        self.assertLessEqual(result.iterations, 100)
        self.assertEqual(len(result.temperature_history), result.iterations + 1)
        self.assertTrue(result.decisions_stable)
        self.assertLessEqual(result.relative_temperature_change, 1.0e-3)
        self.assertLessEqual(result.max_log_factor_change, 1.0e-3)
        self.assertEqual(result.temperature_k, repeated.temperature_k)
        self.assertEqual(result.rmse, repeated.rmse)
        self.assertEqual(set(result.reference_absorption), {
            ("A", 1), ("B", 1), ("C", 1),
        })
        self.assertTrue(all(
            0.0 < value <= 1.0
            for value in result.reference_absorption.values()
        ))
        expected_slope = -1.0 / (CM_PER_K * result.temperature_k)
        for species, _intercept, _absorptions, _offset in specifications:
            corrected_points = []
            for observation in rows:
                if observation.species != species:
                    continue
                correction = result.corrections[id(observation.line)]
                corrected_points.append((
                    observation.ek_cm,
                    math.log(
                        observation.radiometric_wavelength
                        * observation.intensity
                        * correction.multiplier
                        / observation.ag
                    ),
                ))
            for first, second in zip(corrected_points, corrected_points[1:]):
                slope = (second[1] - first[1]) / (second[0] - first[0])
                self.assertAlmostEqual(slope, expected_slope, places=12)

    def test_selective_iterative_irsac_recalculates_factors_until_stable(self):
        rows = []
        for index, (energy, absorption) in enumerate(zip(
            (10000.0, 20000.0, 20000.0, 40000.0),
            (0.50, 0.45, 0.80, 0.95),
        )):
            wavelength = 300.0 + index * 10.0
            ag = 1.0e6
            intensity = (
                math.exp(14.0 - energy / (CM_PER_K * 10000.0))
                * ag
                / wavelength
                * absorption
            )
            rows.append(LineObservation(
                DummyLine(f"Cd{index}"), "Cd", 1, wavelength, intensity,
                1000.0 + index, energy, ag, 1.0,
                accuracy_percent=5.0, snr=100.0,
                transition_wavelength=wavelength,
            ))

        first_cycle = hybrid_self_absorption(
            rows,
            9000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("Cd", 1),
            reference_wavelengths={("Cd", 1): 330.0},
            max_iterations=1,
            relative_tolerance=1.0e-4,
        )
        converged = hybrid_self_absorption(
            rows,
            9000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("Cd", 1),
            reference_wavelengths={("Cd", 1): 330.0},
            max_iterations=100,
            relative_tolerance=1.0e-4,
        )

        self.assertFalse(first_cycle.converged)
        self.assertTrue(converged.converged)
        self.assertGreater(converged.iterations, 2)
        self.assertTrue(converged.decisions_stable)
        self.assertTrue(converged.selected_line_ids)
        self.assertGreater(
            abs(converged.temperature_k - first_cycle.temperature_k),
            1.0,
        )
        self.assertTrue(any(
            abs(
                converged.corrections[id(row.line)].multiplier
                - first_cycle.corrections[id(row.line)].multiplier
            ) > 1.0e-4
            for row in rows
        ))

    def test_iterative_irsac_rejects_incompatible_nonthermometric_slope(self):
        def make_group(species, absorptions, offset):
            result = []
            for index, (energy, absorption) in enumerate(zip(
                (10000.0, 20000.0, 20000.0, 40000.0),
                absorptions,
            )):
                wavelength = 300.0 + offset + index * 10.0
                ag = 1.0e6 * (index + 1)
                intensity = (
                    math.exp(14.0 - energy / (CM_PER_K * 11000.0))
                    * ag
                    / wavelength
                    * absorption
                )
                result.append(LineObservation(
                    DummyLine(f"{species}{index}"), species, 1,
                    wavelength, intensity, 1000.0 + index * 1000.0,
                    energy, ag, 1.0, accuracy_percent=5.0, snr=100.0,
                    transition_wavelength=wavelength,
                ))
            return result

        cadmium = make_group("Cd", (0.50, 0.45, 0.80, 0.95), 0.0)
        nickel = make_group("Ni", (0.35, 0.35, 0.50, 0.80), 50.0)
        rows = cadmium + nickel
        result = hybrid_self_absorption(
            rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("Cd", 1),
            reference_wavelengths={("Cd", 1): 330.0, ("Ni", 1): 380.0},
            max_iterations=100,
            relative_tolerance=1.0e-4,
        )

        self.assertTrue(result.converged)
        self.assertIn(("Ni", 1), result.slope_rejected_keys)
        self.assertFalse(result.species_slope_validation[("Ni", 1)]["compatible"])
        self.assertTrue(any(
            id(row.line) in result.selected_line_ids for row in cadmium
        ))
        self.assertTrue(all(
            id(row.line) not in result.selected_line_ids for row in nickel
        ))

    def test_selected_thermometric_species_anchors_iterative_temperature(self):
        rows = []
        references = {}
        for species, source_temperature, offset in (
            ("A", 9000.0, 0.0),
            ("B", 14000.0, 50.0),
        ):
            for index, (energy, absorption) in enumerate(zip(
                (10000.0, 20000.0, 30000.0, 40000.0),
                (0.40, 0.60, 0.80, 0.95),
            )):
                wavelength = 300.0 + offset + index * 10.0
                ag = 1.0e6 * (index + 1)
                intensity = (
                    math.exp(
                        14.0 - energy / (CM_PER_K * source_temperature)
                    )
                    * ag
                    / wavelength
                    * absorption
                )
                rows.append(LineObservation(
                    DummyLine(f"{species}{index}"),
                    species,
                    1,
                    wavelength,
                    intensity,
                    0.0,
                    energy,
                    ag,
                    1.0,
                    accuracy_percent=5.0,
                    transition_wavelength=wavelength,
                ))
            references[(species, 1)] = 330.0 + offset

        anchored_a = hybrid_self_absorption(
            rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("A", 1),
            reference_wavelengths=references,
            max_iterations=100,
        )
        anchored_b = hybrid_self_absorption(
            rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("B", 1),
            reference_wavelengths=references,
            max_iterations=100,
        )
        a_rows = [row for row in rows if row.species == "A"]
        anchored_a_alone = hybrid_self_absorption(
            a_rows,
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            thermometric_key=("A", 1),
            reference_wavelengths={("A", 1): references[("A", 1)]},
            max_iterations=100,
        )

        self.assertTrue(anchored_a.converged)
        self.assertTrue(anchored_b.converged)
        self.assertAlmostEqual(
            anchored_a.temperature_k,
            anchored_a_alone.temperature_k,
            places=10,
        )
        self.assertGreater(
            abs(anchored_a.temperature_k - anchored_b.temperature_k),
            1000.0,
        )

    def test_other_species_corrections_do_not_move_thermometric_temperature(self):
        rows = []
        for species, offset in (("Cd", 0.0), ("Ni", 50.0)):
            for index, energy in enumerate((10000.0, 20000.0, 30000.0)):
                wavelength = 300.0 + offset + index * 10.0
                ag = 1.0e6
                intensity = (
                    math.exp(14.0 - energy / (CM_PER_K * 10000.0))
                    * ag
                    / wavelength
                )
                rows.append(LineObservation(
                    DummyLine(f"{species}{index}"), species, 1,
                    wavelength, intensity, 0.0, energy, ag, 1.0,
                ))
        raw_temperature = thermometric_temperature(rows, {}, ("Cd", 1))
        ni_only = {
            id(row.line): LineCorrection(2.0, "IRSAC test")
            for row in rows
            if row.species == "Ni"
        }
        self.assertAlmostEqual(
            thermometric_temperature(rows, ni_only, ("Cd", 1)),
            raw_temperature,
            places=12,
        )

    def test_iterative_yang_uses_transition_not_shifted_voigt_wavelength(self):
        def shifted_rows(shift):
            result = []
            for species, offset in (("A", 0.0), ("B", 40.0)):
                for index, energy in enumerate((10000.0, 20000.0, 30000.0)):
                    wavelength = 300.0 + offset + index * 10.0
                    ag = 1.0e6 * (index + 1)
                    intensity = (
                        math.exp(14.0 - energy / (CM_PER_K * 10000.0))
                        * ag
                        / wavelength
                        * (0.6 + 0.15 * index)
                    )
                    result.append(LineObservation(
                        DummyLine(f"{species}{index}-{shift}"),
                        species,
                        1,
                        wavelength + shift,
                        intensity,
                        1000.0 + index,
                        energy,
                        ag,
                        1.0,
                        transition_wavelength=wavelength,
                    ))
            return result

        references = {("A", 1): 320.0, ("B", 1): 360.0}
        unshifted = hybrid_self_absorption(
            shifted_rows(0.0),
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            reference_wavelengths=references,
        )
        shifted = hybrid_self_absorption(
            shifted_rows(0.4),
            10000.0,
            mode="irsac",
            equation_mode="iterative",
            reference_wavelengths=references,
        )
        self.assertAlmostEqual(unshifted.temperature_k, shifted.temperature_k, places=12)
        self.assertEqual(unshifted.reference_absorption, shifted.reference_absorption)

    def test_palleschi_width_formula_returns_intensity_multiplier(self):
        multiplier = palleschi_sac_multiplier(2.0, 1.0)
        self.assertIsNotNone(multiplier)
        self.assertGreater(multiplier, 1.0)

    def test_stark_database_matches_a_spectrum_expressed_in_nm(self):
        line = observation("cu324", 324.754, 10.0, 0.0, 30000.0, 1.0e6)
        rows = _stark_row_map([line], tolerance=0.02, wavelength_scale=10.0)
        self.assertIn(id(line.line), rows)

    def test_final_factors_are_recomputed_at_returned_temperature(self):
        target_temperature = 10000.0

        def at_temperature(name, wavelength, ek):
            aki = 1.0e6
            intensity = aki * 2.0 / wavelength * math.exp(-ek / (CM_PER_K * target_temperature))
            return observation(name, wavelength, intensity, 100.0, ek, aki)

        observations = [
            at_temperature("first", 300.0, 10000.0),
            at_temperature("second", 310.0, 20000.0),
        ]

        def temperature_dependent(_obs, temperature):
            return temperature / 5000.0

        result = hybrid_self_absorption(
            observations,
            5000.0,
            mode="palleschi",
            thermometric_key=("Cu", 1),
            palleschi_factor=temperature_dependent,
            max_iterations=1,
        )
        self.assertAlmostEqual(result.temperature_k, target_temperature, places=5)
        self.assertAlmostEqual(result.corrections[id(observations[0].line)].multiplier, 2.0, places=5)

    def test_automatic_thermometric_species_prefers_widest_ek_span(self):
        def group(species, rows):
            result = []
            for index, (energy, ordinate) in enumerate(rows):
                wavelength = 300.0 + index
                aki = 1.0e6
                gk = 2.0
                intensity = math.exp(ordinate) * aki * gk / wavelength
                result.append(LineObservation(
                    DummyLine(f"{species}{index}"),
                    species,
                    1,
                    wavelength,
                    intensity,
                    100.0,
                    energy,
                    aki,
                    gk,
                ))
            return result

        observations = group("Cd", [
            (30656.0879, 17.0372262734),
            (59485.7695, 12.5275026396),
            (51483.9805, 14.1217916327),
            (51483.9805, 14.1321464708),
        ])
        observations += group("Pb", [
            (49439.6172, 13.9366547758),
            (35287.2227, 15.3563688901),
            (34959.9102, 15.4686463210),
            (48188.6289, 13.7462671193),
            (35287.2227, 15.5107018804),
        ])
        self.assertEqual(most_reliable_thermometric_key(observations), ("Cd", 1))

    def test_manual_cadmium_reference_is_used_by_staged_irsac(self):
        lines = []
        for species, offset in (("Cd", 0.0), ("Pb", 0.3)):
            for index, energy in enumerate((30000.0, 45000.0, 60000.0)):
                wavelength = 300.0 + index * 10.0 + offset
                intensity = 2.0e6 * 3.0 / wavelength * math.exp(
                    -energy / (CM_PER_K * 10000.0)
                )
                lines.append(
                    TemplateLine(
                        wavelen=wavelength,
                        fitwavelen=wavelength,
                        asswavelen=wavelength,
                        specie=species,
                        ion=1,
                        inte=intensity,
                        ei=1000.0 * index,
                        ek=energy,
                        aki=2.0e6,
                        gk=3,
                        gi=1,
                        wg=0.1,
                        wl=0.1,
                    )
                )
        app = SimpleNamespace(
            template_lines=lines,
            options=SimpleNamespace(
                irsac_mode="irsac",
                irsac_thermometric_species="Cd I",
                irsac_iterations=10,
                irsac_tolerance=1.0e-4,
                irsac_equation_mode="iterative",
                search_range=0.2,
                apply_response=False,
                apply_after=False,
            ),
            response_library=SimpleNamespace(curves=[]),
            spectra=[],
            session_temperature=1.0,
            session_ne=0.0,
            apply_sac_correction=False,
            last_saha_boltzmann=None,
            last_self_absorption_result=None,
            last_theoretical_spectrum=None,
            post_irsac_temperature=None,
            post_irsac_temperature_source=None,
            theoretical_window=None,
            current_wavelength_unit_label=lambda: "nm",
        )

        fitted_areas = [line.inte for line in lines]
        result = calculate_hybrid_self_absorption(
            app,
            mode="irsac",
            thermometric_species="Cd I",
            temperature_k=9000.0,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.thermometric_key, ("Cd", 1))
        self.assertEqual(app.options.irsac_equation_mode, "staged")
        self.assertEqual(app.last_self_absorption_result["equation_mode"], "staged")
        self.assertEqual(app.last_self_absorption_result["thermometric_species"], ("Cd", 1))
        self.assertEqual([line.inte for line in lines], fitted_areas)


if __name__ == "__main__":
    unittest.main()
