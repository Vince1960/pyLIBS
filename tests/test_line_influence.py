"""Influence of each line on the CF-LIBS concentrations (pylibs.core.line_influence) and restoration shifts."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_data as S  # noqa: E402

try:
    import scipy  # noqa: F401
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

TRUTH = {"Ca": 0.50, "Fe": 0.45, "Mg": 0.05}


def plasma(noise=0.03, seed=4, bad_factor=3.5):
    """Aligned Saha-Boltzmann points and CF-LIBS lines; Fe I 4045.8 made 3.5× too strong (misassignment)."""
    from pylibs.core.cflibs_uncertainty import CFInputs, MCPoint
    from pylibs.core.plasma_fit import SBPoint
    p = S.lte_plasma(0.85, 6e16, TRUTH, noise, seed)
    pts, cf, bad = [], [], None
    for (el, ion), v in p["points"].items():
        for ek, y, wl, ei, ga in v:
            if el == "Fe" and ion == 1 and abs(wl - 4045.8) < 0.5:
                y += math.log(bad_factor)
                bad = len(pts)
            pts.append(SBPoint(el, ion, ek, p["eion"][el], y, f"{el} {ion} {wl:.2f}"))
            cf.append(((el, ion), MCPoint(ek, y)))
    inp = CFInputs({}, p["mass"], p["eion"], p["z"])
    return pts, cf, inp, bad


@unittest.skipUnless(S.LIBS_DB.exists() and HAS_SCIPY, "LIBS.db or scipy not available")
class TestLineInfluence(unittest.TestCase):
    def setUp(self):
        from pylibs.core.line_influence import compose
        from pylibs.core.outliers import analyse
        self.pts, self.cf, self.inp, self.bad = plasma()
        self.active = [True] * len(self.pts)
        self.fit, self.rows, _s = analyse(self.pts, self.active, 0.9, 6e16, plasma_shifts=True)
        self.kt, self.ne = self.fit.kt, self.fit.ne
        self.base = compose(self.cf, self.active, self.inp, self.kt, self.ne)

    def infl(self, i, active=None, rows=None, base=None, plasma=True):
        from pylibs.core.line_influence import line_influence
        r = (rows or self.rows)[i]
        return line_influence(self.cf, active or self.active, i, self.inp, self.kt, self.ne, base or self.base,
                              r.dkt if plasma else None, r.dlnne if plasma else None)

    def test_molar_changes_sum_to_zero(self):
        for i in range(len(self.pts)):
            inf = self.infl(i)
            self.assertAlmostEqual(sum(d[0] for d in inf.total.values()), 0.0, places=9)
            self.assertAlmostEqual(sum(d[1] for d in inf.total.values()), 0.0, places=9)

    def test_misassigned_line_raises_its_element(self):
        """Excluding the too-strong Fe line lowers Fe (direct effect) and is the largest Fe influence."""
        inf = self.infl(self.bad)
        self.assertLess(inf.direct["Fe"][0], -1.0)
        self.assertGreater(inf.direct["Ca"][0], 0.0)
        others = [abs(self.infl(i, plasma=False).direct["Fe"][0]) for i in range(len(self.pts)) if i != self.bad]
        self.assertGreater(abs(inf.direct["Fe"][0]), max(others))

    def test_excluding_bad_line_moves_towards_truth(self):
        inf = self.infl(self.bad)
        for el, frac in TRUTH.items():
            self.assertLess(abs(inf.new[el][0] - 100 * frac), abs(self.base[el][0] - 100 * frac) + 1e-9)

    def test_restore_is_inverse_of_exclusion(self):
        from pylibs.core.line_influence import compose
        from pylibs.core.outliers import analyse
        ex = self.infl(self.bad)
        act2 = list(self.active)
        act2[self.bad] = False
        fit2, rows2, _s = analyse(self.pts, act2, 0.9, 6e16, plasma_shifts=True)
        self.assertAlmostEqual(rows2[self.bad].dkt, -self.rows[self.bad].dkt, places=6)
        kt2 = self.kt + self.rows[self.bad].dkt
        ne2 = self.ne * math.exp(self.rows[self.bad].dlnne)
        base2 = compose(self.cf, act2, self.inp, kt2, ne2)
        from pylibs.core.line_influence import line_influence
        re = line_influence(self.cf, act2, self.bad, self.inp, kt2, ne2, base2, rows2[self.bad].dkt,
                            rows2[self.bad].dlnne)
        self.assertTrue(re.restore)
        for el in TRUTH:
            self.assertAlmostEqual(re.total[el][0], -ex.total[el][0], places=5)

    def test_combined_change_equals_single_change(self):
        from pylibs.core.line_influence import combined_change
        from pylibs.core.outliers import mask_shift
        mask = list(self.active)
        mask[self.bad] = False
        dkt, dln = mask_shift(self.pts, self.active, mask, self.kt, self.ne)
        new, d, _kt, _ne = combined_change(self.cf, self.active, mask, self.inp, self.kt, self.ne, dkt, dln)
        inf = self.infl(self.bad)
        for el in TRUTH:
            self.assertAlmostEqual(d[el][0], inf.total[el][0], places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
