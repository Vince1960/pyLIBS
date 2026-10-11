import math
import unittest
from types import SimpleNamespace

from pyLIBS import (
    hydrogen_doppler_fwhm,
    identify_halpha_peak,
    recompute_halpha_ne_for_temperature,
)


class HAlphaWidthTests(unittest.TestCase):
    def test_hydrogen_doppler_width_at_one_ev(self):
        width_nm = hydrogen_doppler_fwhm(656.28, 1.0)
        self.assertAlmostEqual(width_nm, 0.05045, places=4)

    def test_doppler_width_preserves_wavelength_units(self):
        width_nm = hydrogen_doppler_fwhm(656.28, 1.0)
        width_angstrom = hydrogen_doppler_fwhm(6562.8, 1.0)
        self.assertAlmostEqual(width_angstrom, 10.0 * width_nm, places=10)

    def test_nonpositive_inputs_disable_doppler_width(self):
        self.assertEqual(hydrogen_doppler_fwhm(656.28, 0.0), 0.0)
        self.assertEqual(hydrogen_doppler_fwhm(0.0, 1.0), 0.0)

    def test_identification_uses_a_real_maximum_near_halpha(self):
        xs = [650.0 + index * 0.02 for index in range(601)]
        ys = [
            20.0
            + 200.0 * math.exp(-0.5 * ((x - 656.44) / 0.35) ** 2)
            + 1000.0 * math.exp(-0.5 * ((x - 660.0) / 0.08) ** 2)
            for x in xs
        ]

        result = identify_halpha_peak(xs, ys, 656.28, 1.5)

        self.assertAlmostEqual(result["observed_center"], 656.44, places=2)
        self.assertAlmostEqual(result["shift"], 0.16, places=2)
        self.assertEqual(result["quality"], "compatible")

    def test_two_comparable_nearby_maxima_are_flagged(self):
        xs = [654.0 + index * 0.01 for index in range(451)]
        ys = [
            10.0
            + 100.0 * math.exp(-0.5 * ((x - 655.9) / 0.08) ** 2)
            + 80.0 * math.exp(-0.5 * ((x - 656.65) / 0.08) ** 2)
            for x in xs
        ]

        result = identify_halpha_peak(xs, ys, 656.28, 1.5)

        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["quality"], "check")
        self.assertGreater(result["ambiguity_ratio"], 0.5)

    def test_large_wavelength_mismatch_requires_confirmation(self):
        xs = [654.0 + index * 0.01 for index in range(451)]
        ys = [
            10.0
            + 100.0 * math.exp(-0.5 * ((x - 657.2) / 0.12) ** 2)
            for x in xs
        ]

        result = identify_halpha_peak(xs, ys, 656.28, 1.5)

        self.assertTrue(result["large_shift"])
        self.assertEqual(result["quality"], "check")

    def test_identification_rejects_a_trace_without_a_peak(self):
        xs = [655.0 + index * 0.01 for index in range(251)]
        ys = [float(index) for index in range(len(xs))]

        with self.assertRaisesRegex(ValueError, "No real measured maximum"):
            identify_halpha_peak(xs, ys, 656.28, 1.5)

    def test_stored_halpha_width_is_recomputed_at_saha_temperature(self):
        app = SimpleNamespace(
            last_halpha_result={
                "available": True,
                "kt": 1.0,
                "corrected_lorentzian_width_angstrom": 1.2,
            },
            session_ne=None,
            session_ne_source="",
        )

        ne = recompute_halpha_ne_for_temperature(app, 1.4)

        self.assertGreater(ne, 0.0)
        self.assertAlmostEqual(app.last_halpha_result["ne_evaluation_kt"], 1.4)
        self.assertAlmostEqual(app.last_halpha_result["ne"], ne)
        self.assertAlmostEqual(app.session_ne, ne)
        self.assertIn("coupled", app.session_ne_source)


if __name__ == "__main__":
    unittest.main()
