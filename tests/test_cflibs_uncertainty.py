"""CF-LIBS model and Monte Carlo uncertainty (pylibs.core.cflibs_uncertainty)."""
import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_data as S  # noqa: E402

try:
    import numpy  # noqa: F401
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from pylibs.core.cflibs_uncertainty import (STAT_KEYS, CFInputs, MCPoint, cflibs_concentrations, fmt_pm,  # noqa: E402
                                            hdi, kde_mode, monte_carlo, stat_value)

TRUTH = {"Ca": 0.50, "Fe": 0.45, "Mg": 0.05}


def inputs(noise=0.0, seed=1, s_int=0.05):
    p = S.lte_plasma(0.85, 6e16, TRUTH, noise, seed)
    groups = {k: [MCPoint(ek, y, s_int, 0.0, 0.0, f"{k[0]} {k[1]} {wl:.2f}") for ek, y, wl, ei, ga in v]
              for k, v in p["points"].items()}
    return CFInputs(groups, p["mass"], p["eion"], p["z"]), p


@unittest.skipUnless(S.LIBS_DB.exists(), "LIBS.db not found")
class TestModel(unittest.TestCase):
    def test_exact_recovery_of_composition(self):
        inp, p = inputs()
        res = cflibs_concentrations(inp, p["kt"], p["ne"])
        for el, frac in TRUTH.items():
            self.assertAlmostEqual(res[el][0], 100 * frac, places=8)

    def test_mass_percent_consistent(self):
        inp, p = inputs()
        res = cflibs_concentrations(inp, p["kt"], p["ne"])
        tot = sum(TRUTH[e] * p["mass"][e] for e in TRUTH)
        for el in TRUTH:
            self.assertAlmostEqual(res[el][1], 100 * TRUTH[el] * p["mass"][el] / tot, places=8)


@unittest.skipUnless(S.LIBS_DB.exists() and HAS_NUMPY, "LIBS.db or numpy not available")
class TestMonteCarlo(unittest.TestCase):
    def test_sigma_matches_repeated_experiments(self):
        """σ predicted from one noisy spectrum ≈ scatter over independent noisy spectra (5 % noise)."""
        inp, p = inputs(noise=0.05, seed=3)
        mc = monte_carlo(inp, p["kt"], p["ne"], 0.0, 0.0, n=1500, sources=("intensity",), budget=False, seed=7)
        clean, _ = inputs()
        rng = random.Random(11)
        reps = {el: [] for el in TRUTH}
        for _ in range(200):
            ys = {k: [pt.y + rng.gauss(0, 0.05) for pt in v] for k, v in clean.groups.items()}
            out = cflibs_concentrations(clean, p["kt"], p["ne"], ys)
            for el in TRUTH:
                reps[el].append(out[el][0])
        for el in TRUTH:
            emp = statistics.stdev(reps[el])
            self.assertLess(abs(mc.number[el].sd / emp - 1.0), 0.25, f"{el}: MC {mc.number[el].sd} vs {emp}")

    def test_budget_sources_and_quadrature(self):
        inp, p = inputs(noise=0.03, seed=5)
        for pts in inp.groups.values():
            for pt in pts:
                pt.s_gA = 0.10
        mc = monte_carlo(inp, p["kt"], p["ne"], 0.03, 0.15, n=1500, seed=2)
        for el in TRUTH:
            quad = math.sqrt(sum(mc.budget_number[s][el] ** 2 for s in mc.sources))
            self.assertLess(abs(quad / mc.number[el].sd - 1.0), 0.35)
            self.assertGreater(mc.budget_number["kT"][el], 0.0)

    def test_mode_of_lognormal(self):
        rng = random.Random(1)
        for mu, s in ((3.0, 0.3), (1.0, 0.6)):
            v = [math.exp(rng.gauss(mu, s)) for _ in range(4000)]
            mode, _bw, _x, _d = kde_mode(v)
            self.assertLess(abs(mode / math.exp(mu - s * s) - 1.0), 0.05)

    def test_hdi_contains_68_percent(self):
        rng = random.Random(2)
        v = [rng.gauss(0, 1) for _ in range(5000)]
        lo, hi = hdi(v, 0.68)
        frac = sum(lo <= x <= hi for x in v) / len(v)
        self.assertAlmostEqual(frac, 0.68, delta=0.01)
        self.assertAlmostEqual(hi - lo, 2 * 0.994, delta=0.08)   # ±0.994σ for a Gaussian


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestFormatting(unittest.TestCase):
    def test_fmt_pm(self):
        self.assertEqual(fmt_pm(1.10834, 0.0204), "1.108 ± 0.020")
        self.assertEqual(fmt_pm(52.98, 2.61), "53.0 ± 2.6")
        self.assertEqual(fmt_pm(-0.1372, 0.0327), "-0.137 ± 0.033")
        self.assertEqual(fmt_pm(4.5, None), "4.5")


@unittest.skipUnless(S.LIBS_DB.exists() and HAS_NUMPY, "LIBS.db or numpy not available")
class TestStandardErrors(unittest.TestCase):
    def test_bootstrap_se_matches_seed_to_seed_scatter(self):
        """Bootstrap s.e. of each statistic ≈ scatter of that statistic over independent Monte Carlo runs."""
        p = S.lte_plasma(0.85, 6e16, TRUTH)
        groups = {k: [MCPoint(ek, y, 0.05, 0.10, 0.0, "") for ek, y, wl, ei, ga in v] for k, v in p["points"].items()}
        inp = CFInputs(groups, p["mass"], p["eion"], p["z"])
        r = monte_carlo(inp, 0.85, 6e16, 0.05, 0.15, n=2000, budget=False, seed=1, n_boot=150)
        reps = [monte_carlo(inp, 0.85, 6e16, 0.05, 0.15, n=2000, budget=False, seed=s, n_boot=0)
                for s in range(2, 32)]
        st = r.number["Ca"]
        self.assertEqual(set(st.se), set(STAT_KEYS))
        # mean: analytic σ/√N
        self.assertAlmostEqual(st.se["mean"] / (st.sd / math.sqrt(2000)), 1.0, delta=0.2)
        for k in ("mean", "p50", "sd", "hdi_lo", "hdi_hi", "mode"):
            emp = statistics.stdev([stat_value(x.number["Ca"], k) for x in reps])
            ratio = st.se[k] / emp
            self.assertTrue(0.5 < ratio < 2.0, f"{k}: bootstrap {st.se[k]:.3g} vs runs {emp:.3g}")
