"""Self-consistent kT / Ne determination (pylibs.core.plasma_fit)."""
import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_brazil as S  # noqa: E402

try:
    import scipy  # noqa: F401
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from pylibs.core.plasma_fit import SBPoint, stark_boltzmann_loop  # noqa: E402


def sb_points(noise=0.0, seed=1, only_neutral=False):
    p = S.lte_plasma(0.85, 6e16, {"Ca": 0.5, "Fe": 0.45, "Mg": 0.05}, noise, seed)
    out = []
    for (el, ion), v in p["points"].items():
        if only_neutral and ion == 2:
            continue
        for ek, y, wl, ei, ga in v:
            out.append(SBPoint(el, ion, ek, p["eion"][el], y, f"{el} {ion} {wl:.2f}"))
    return out


@unittest.skipUnless(S.LIBS_DB.exists() and HAS_SCIPY, "LIBS.db or scipy not available")
class TestGlobalFit(unittest.TestCase):
    def test_exact_recovery(self):
        from pylibs.core.plasma_fit import global_fit
        f = global_fit(sb_points(), 1.3, 1e17)
        self.assertAlmostEqual(f.kt, 0.85, places=6)
        self.assertAlmostEqual(f.ne / 6e16, 1.0, places=5)
        self.assertEqual(f.ne_elements, ["Ca", "Mg"])

    def test_covariance_sigma_is_calibrated(self):
        from pylibs.core.plasma_fit import global_fit
        kts, sig = [], []
        for seed in range(120):
            f = global_fit(sb_points(0.10, seed), 1.2, 2e17)
            kts.append(f.kt)
            sig.append(f.sigma_kt)
        self.assertLess(abs(statistics.mean(kts) - 0.85), 0.01)
        self.assertLess(abs(statistics.mean(sig) / statistics.stdev(kts) - 1.0), 0.25)

    def test_ne_not_identifiable_with_neutrals_only(self):
        from pylibs.core.plasma_fit import global_fit
        f = global_fit(sb_points(0.02, 4, only_neutral=True), 1.0, 1e17)
        self.assertFalse(f.ne_fitted)
        self.assertAlmostEqual(f.kt, 0.85, delta=0.03)


class TestLoop(unittest.TestCase):
    def test_stark_boltzmann_loop_converges(self):
        steps, ok = stark_boltzmann_loop(1.0, 1e17, lambda kt: 5e16 * (kt / 0.9) ** 0.3,
                                         lambda ne, kt: 0.9 * (ne / 5e16) ** 0.05)
        self.assertTrue(ok)
        self.assertAlmostEqual(steps[-1].kt, 0.9, places=4)
        self.assertAlmostEqual(steps[-1].ne / 5e16, 1.0, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
