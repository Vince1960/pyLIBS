import unittest

import numpy as np

from pylibs.core.baseline import estimate_baseline, remove_baseline


class BaselineRemovalTests(unittest.TestCase):
    def spectrum(self, n=501, nonuniform=False):
        x = np.linspace(400, 600, n)
        if nonuniform:
            x = 400 + 200 * np.linspace(0, 1, n) ** 1.2
        baseline = 12 + 0.02 * (x - 400) + 2 * np.sin((x - 400) / 80)
        peaks = 30 * np.exp(-0.5 * ((x - 475) / 0.9) ** 2) + 8 * np.exp(-0.5 * ((x - 532) / 2.5) ** 2)
        return x, baseline + peaks, baseline, peaks

    def test_asls_recovers_smooth_baseline_and_preserves_peak(self):
        x, y, truth, peaks = self.spectrum()
        baseline, corrected = remove_baseline(x, y, lam=1e6, p=0.01)
        self.assertLess(np.median(np.abs(np.asarray(baseline)[peaks < 1] - truth[peaks < 1])), 0.2)
        self.assertAlmostEqual(max(corrected), max(peaks), delta=1.0)

    def test_constant_and_linear_baselines_are_preserved(self):
        x = np.linspace(0, 1, 300)
        for baseline in (np.full_like(x, -4.0), 3.0 + 2.5 * x):
            for algorithm in ("AsLS", "airPLS"):
                estimated = estimate_baseline(x, baseline, algorithm=algorithm, lam=1e5)
                self.assertLess(np.max(np.abs(estimated - baseline)), 1e-7)

    def test_dense_lines_remain_finite(self):
        x = np.linspace(200, 300, 2000)
        baseline = 5 + 0.2 * np.sin(x / 30)
        centers = np.linspace(202, 298, 55)
        y = baseline.copy()
        for center in centers:
            y += 3 * np.exp(-0.5 * ((x - center) / 0.12) ** 2)
        estimate = estimate_baseline(x, y, lam=1e6, max_iter=40)
        self.assertTrue(np.isfinite(estimate).all())

    def test_airpls_nonuniform_grid_and_negative_signal(self):
        x, y, _truth, _peaks = self.spectrum(nonuniform=True)
        y = y - 20
        baseline = estimate_baseline(x, y, algorithm="airPLS", lam=1e5, max_iter=30)
        self.assertEqual(len(baseline), len(x))
        self.assertTrue(np.isfinite(baseline).all())
        self.assertLess(np.median(np.abs(np.asarray(baseline)[20:-20] - (12 + .02 * (x[20:-20]-400) + 2*np.sin((x[20:-20]-400)/80) - 20))), 1.0)

    def test_clip_is_opt_in_and_wavelength_order_is_unchanged(self):
        x = [5, 4, 3, 2, 1]
        y = [-5, -4, -3, -4, -5]
        _base, preserved = remove_baseline(x, y, lam=1e4)
        _base, clipped = remove_baseline(x, y, lam=1e4, clip_negative=True)
        self.assertTrue(any(value < 0 for value in preserved))
        self.assertTrue(all(value >= 0 for value in clipped))

    def test_invalid_inputs_are_reported(self):
        for x, y in (([1, 2], [1, 2]), ([1, 2, 3], [1, float("nan"), 2]), ([1, 2, 2], [1, 2, 3])):
            with self.assertRaises(ValueError):
                estimate_baseline(x, y)


if __name__ == "__main__":
    unittest.main()
