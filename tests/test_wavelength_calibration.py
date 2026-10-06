import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pyLIBS import WavelengthCalibrationWindow, load_template_lines
from pylibs.core.wavelength_calibration import (
    CalibrationAnchor,
    calibration_for_window,
    estimate_window_calibration,
    fit_wavelength_calibration,
    parse_calibrations,
    serialize_calibrations,
)


class WavelengthCalibrationTests(unittest.TestCase):
    def test_calibration_accepts_pasted_decimal_comma_wavelengths(self):
        references = WavelengthCalibrationWindow._parse_pasted_wavelengths(
            "313,411; 344.626 349,296\n356.637"
        )

        self.assertEqual(references, [313.411, 344.626, 349.296, 356.637])

    def test_plain_one_column_nist_list_loads_without_a_csv_header(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "nist-lines.txt"
            filename.write_text(
                "313.411\n344.626\n349.296\n356.637\n",
                encoding="utf-8",
            )

            lines = load_template_lines(filename)

        self.assertEqual(
            [line.wavelen for line in lines],
            [313.411, 344.626, 349.296, 356.637],
        )

    def test_plain_list_preserves_element_section_headings(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "selected-lines.txt"
            filename.write_text(
                "Ni:\n313,411\n344,626\nCd:\n326,10548\n340,36521\n",
                encoding="utf-8",
            )

            lines = load_template_lines(filename)

        self.assertEqual(
            [(line.specie, line.wavelen) for line in lines],
            [
                ("Ni", 313.411),
                ("Ni", 344.626),
                ("Cd", 326.10548),
                ("Cd", 340.36521),
            ],
        )
        self.assertEqual([line.ion for line in lines], [1, 1, 1, 1])

    def test_plain_list_accepts_explicit_ion_stage_in_section_heading(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "selected-ion-lines.txt"
            filename.write_text(
                "Cd I:\n340,36521\nCd II:\n340,42219\n",
                encoding="utf-8",
            )

            lines = load_template_lines(filename)

        self.assertEqual([line.specie for line in lines], ["Cd", "Cd"])
        self.assertEqual([line.ion for line in lines], [1, 2])

    def test_manual_multiline_windows_select_linear_model(self):
        anchors = [
            CalibrationAnchor(340.36521, 340.75802, 100.0),
            CalibrationAnchor(344.62600, 345.04567, 120.0),
            CalibrationAnchor(349.29600, 349.71624, 150.0),
            CalibrationAnchor(356.63700, 357.09409, 130.0),
        ]

        calibration = fit_wavelength_calibration(
            anchors,
            name="350",
            raw_min=329.8,
            raw_max=370.2,
            model="auto",
        )

        self.assertEqual(calibration.model, "linear")
        self.assertLess(calibration.rms, 0.01)
        self.assertAlmostEqual(calibration.correct(349.71624), 349.296, delta=0.015)

    def test_one_anchor_is_an_offset_even_when_linear_is_requested(self):
        calibration = fit_wavelength_calibration(
            [CalibrationAnchor(405.78067, 406.16523, 10.0)],
            name="400",
            raw_min=380.0,
            raw_max=420.0,
            model="linear",
        )

        self.assertEqual(calibration.model, "offset")
        self.assertAlmostEqual(calibration.slope, 1.0)
        self.assertAlmostEqual(calibration.intercept, -0.38456, places=6)

    def test_estimator_finds_real_peaks_and_recovers_affine_calibration(self):
        references = np.asarray([340.36521, 344.626, 349.296, 356.637])
        intercept = 1.25
        slope = 0.9975
        observed = (references - intercept) / slope
        x = np.linspace(329.8, 370.2, 4096)
        y = np.full_like(x, 525.0)
        for index, center in enumerate(observed):
            y += (200.0 + 80.0 * index) * np.exp(
                -0.5 * ((x - center) / 0.055) ** 2
            )
        rng = np.random.default_rng(42)
        y += rng.normal(0.0, 0.8, size=len(y))

        calibration = estimate_window_calibration(
            x,
            y,
            references,
            name="350",
            max_shift=0.8,
            model="auto",
        )

        self.assertEqual(calibration.model, "linear")
        self.assertEqual(calibration.used_anchor_count, 4)
        self.assertAlmostEqual(calibration.intercept, intercept, delta=0.08)
        self.assertAlmostEqual(calibration.slope, slope, delta=3.0e-4)
        self.assertLess(calibration.rms, 0.01)

    def test_profiles_round_trip_and_match_by_window_range(self):
        calibration = fit_wavelength_calibration(
            [
                CalibrationAnchor(357.27, 357.56234, 20.0),
                CalibrationAnchor(363.95677, 364.25019, 30.0),
                CalibrationAnchor(368.34625, 368.66055, 40.0),
                CalibrationAnchor(373.99353, 374.31791, 30.0),
            ],
            name="365.txt",
            raw_min=344.9,
            raw_max=385.2,
        )

        parsed = parse_calibrations(serialize_calibrations([calibration]))
        matched = calibration_for_window(
            parsed,
            np.linspace(344.91, 385.19, 100),
            "another_sample_365.txt",
        )

        self.assertIsNotNone(matched)
        self.assertTrue(math.isfinite(matched.intercept))
        self.assertAlmostEqual(matched.slope, calibration.slope)

    def test_disabled_anchor_is_not_used_by_the_fit(self):
        calibration = fit_wavelength_calibration(
            [
                CalibrationAnchor(340.0, 340.4, 10.0),
                CalibrationAnchor(350.0, 350.4, 10.0),
                CalibrationAnchor(360.0, 361.2, 10.0, used=False),
            ],
            model="auto",
        )

        self.assertEqual(calibration.used_anchor_count, 2)
        self.assertEqual(calibration.model, "offset")
        self.assertAlmostEqual(calibration.intercept, -0.4, places=6)
        self.assertFalse(calibration.anchors[2].used)


if __name__ == "__main__":
    unittest.main()
