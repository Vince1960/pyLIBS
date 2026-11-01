"""Outlier screening of Saha-Boltzmann points (pylibs.core.outliers)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_data as S  # noqa: E402
from tests.test_plasma_fit import sb_points  # noqa: E402

try:
    import scipy  # noqa: F401
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@unittest.skipUnless(S.LIBS_DB.exists() and HAS_SCIPY, "LIBS.db or scipy not available")
class TestOutliers(unittest.TestCase):
    def test_injected_misassignments_are_found_first(self):
        from pylibs.core.outliers import sequential
        pts = sb_points(0.05, 3)
        bad = {}
        for i, p in enumerate(pts):
            if p.label.startswith("Fe 1 4045"):
                p.y += math.log(3.5)
                bad[i] = "strong"
            if p.label.startswith("Ca 1 6439"):
                p.y += math.log(0.3)
                bad[i] = "weak"
        order = sequential(pts, [True] * len(pts), 0.9, 6e16, 3.0)
        self.assertEqual(set(order[:2]), set(bad))

    def test_clean_data_gives_no_suggestion(self):
        from pylibs.core.outliers import sequential
        pts = sb_points(0.03, 8)
        self.assertEqual(sequential(pts, [True] * len(pts), 0.9, 6e16, 3.5), [])

    def test_elements_with_few_lines_are_not_tested(self):
        from pylibs.core.outliers import analyse
        pts = [p for p in sb_points(0.03, 1) if not (p.element == "Mg" and p.ion == 2)][:-1]
        mask = [True] * len(pts)
        _base, rows, _s = analyse(pts, mask, 0.9, 6e16, min_per_element=50)
        self.assertTrue(all(not r.testable for r in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
