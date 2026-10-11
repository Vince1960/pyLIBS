import unittest

import numpy as np

from pylibs.core.theoretical_spectrum import (
    TheoreticalLine,
    _trapezoid,
    synthesize_voigt_spectrum,
)


class TheoreticalSpectrumTests(unittest.TestCase):
    def test_voigt_is_area_normalized_and_response_is_forward_applied(self):
        x = np.linspace(495.0, 505.0, 20001)
        lines = [TheoreticalLine(500.0, 12.0, "Cu", 1, 0.05)]
        corrected = synthesize_voigt_spectrum(x, lines, lsf_fwhm=lambda _w: 0.1)
        detector = synthesize_voigt_spectrum(
            x,
            lines,
            lsf_fwhm=lambda _w: 0.1,
            response=lambda _w: 2.0,
            detector_domain=True,
        )
        self.assertAlmostEqual(_trapezoid(corrected, x), 12.0, places=2)
        self.assertAlmostEqual(_trapezoid(detector, x), 24.0, places=2)

    def test_close_lines_are_summed_without_peak_loss(self):
        x = np.linspace(499.0, 501.0, 4001)
        lines = [
            TheoreticalLine(499.95, 5.0, "Cu", 1),
            TheoreticalLine(500.05, 7.0, "Cu", 1),
        ]
        y = synthesize_voigt_spectrum(x, lines, lsf_fwhm=lambda _w: 0.08)
        self.assertAlmostEqual(_trapezoid(y, x), 12.0, places=2)


if __name__ == "__main__":
    unittest.main()
