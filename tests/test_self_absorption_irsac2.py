"""Self-absorption: El Sherbini relation, IRSAC, Stark-method guards (pylibs.core.self_absorption)."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_data as S  # noqa: E402

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from pylibs.core.self_absorption_irsac2 import (SALine, StarkRef, assess, choose_reference, irsac_species,  # noqa: E402
                                         same_level_test, slope_check, stark_assessment, tau_proxy)
from pylibs.core.dev_adapters import self_absorption_lines  # noqa: E402
from pylibs.gui.sa_dialog import MODES  # noqa: E402
from pyLIBS import AppOptions, TemplateLine  # noqa: E402


def absorbed(tau0):
    """Exact area ratio and FWHM ratio of a self-absorbed Lorentzian (homogeneous slab)."""
    x = np.linspace(-300, 300, 300001)
    L = 1.0 / (1.0 + x ** 2)
    prof = 1.0 - np.exp(-tau0 * L)
    area = np.trapezoid(prof, x) if hasattr(np, "trapezoid") else np.trapz(prof, x)
    area0 = np.trapezoid(L, x) if hasattr(np, "trapezoid") else np.trapz(L, x)
    h = np.where(prof >= prof.max() / 2)[0]
    return area / (tau0 * area0), (x[h[-1]] - x[h[0]]) / 2.0


@unittest.skipUnless(HAS_NUMPY, "numpy not available")
class TestElSherbini(unittest.TestCase):
    def test_width_based_sac_matches_exact_curve_of_growth(self):
        for tau0 in (0.5, 2.0, 5.0):
            sa_area, wr = absorbed(tau0)
            sac_width = wr ** (0.46 / 0.54)
            self.assertLess(abs(sac_width * sa_area - 1.0), 0.06, f"tau0={tau0}")


class TestIRSAC(unittest.TestCase):
    def test_visible_modes_expose_irsac2_only(self):
        labels = tuple(MODES)

        self.assertIn("IRSAC2 (recommended)", labels)
        self.assertFalse(any("IRSAC1" in label for label in labels))

    def lines(self, attenuate=None, kt=0.9, noise=0.0, seed=1):
        rng = random.Random(seed)
        spec = [(4226.7, 0.0, 2.93, 3 * 2.18e8), (4302.5, 1.90, 4.78, 5 * 1.36e8), (6162.2, 1.90, 3.91, 3 * 3.5e7),
                (4454.8, 1.90, 4.68, 7 * 8.7e7), (5588.7, 2.53, 4.74, 7 * 4.9e7), (6439.1, 2.53, 4.45, 9 * 5.3e7)]
        out = []
        for i, (wl, ei, ek, ga) in enumerate(spec):
            inten = ga * math.exp(-ek / kt) * math.exp(rng.gauss(0, noise))
            if attenuate and i in attenuate:
                inten *= attenuate[i]
            out.append(SALine(i, "Ca", 1, wl, ei, ek, ga, inten, 0.1, label=f"Ca I {wl}"))
        return out

    def test_reference_is_least_optically_thick(self):
        ls = self.lines()
        ref = choose_reference(ls, 0.9)
        self.assertEqual(ref.key, min(ls, key=lambda l: tau_proxy(l, 0.9)).key)

    def test_detects_attenuated_line(self):
        ls = self.lines(attenuate={0: 0.5}, noise=0.02, seed=4)
        res = irsac_species(ls, 0.9, 0.0, 0.03)
        self.assertEqual(res[0]["irsac_status"], "self-absorbed")
        self.assertAlmostEqual(res[0]["irsac_sa"], 0.5, delta=0.06)
        self.assertAlmostEqual(res[0]["irsac_sac"], 2.0, delta=0.25)
        for k in range(1, 6):
            self.assertIn(res[k]["irsac_status"], ("thin", "reference") + tuple(
                s for s in [res[k]["irsac_status"]] if s.startswith("thin within")))

    def test_no_correction_for_thin_lines(self):
        res = irsac_species(self.lines(noise=0.01, seed=2), 0.9, 0.0, 0.05)
        self.assertTrue(all(v["irsac_sac"] == 1.0 for v in res.values()))


class TestIRSACAdapter(unittest.TestCase):
    @staticmethod
    def line(aki):
        return TemplateLine(
            wavelen=340.36521,
            specie="Cd",
            ion=1,
            asswavelen=340.36521,
            inte=1.0,
            ei=10000.0,
            ek=30000.0,
            aki=aki,
            gk=3,
            gi=1,
            fitwavelen=340.36,
            wg=0.05,
            wl=0.05,
            fit_profile="voigt",
        )

    @staticmethod
    def app(line):
        return SimpleNamespace(
            template_lines=[line],
            options=AppOptions(aki_threshold=1.0e5, apply_response=False),
            wavelength_unit="nm",
            current_wavelength_unit_label=lambda: "nm",
        )

    def test_adapter_applies_aki_threshold_and_converts_nm_to_angstrom(self):
        self.assertEqual(self_absorption_lines(self.app(self.line(9.0e4))), [])

        rows = self_absorption_lines(self.app(self.line(1.0e7)))

        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0].wavelength_A, 3403.6521, places=6)


class TestIRSACExtensions(unittest.TestCase):
    lines = TestIRSAC.lines

    def test_reference_absorption_is_estimated(self):
        ls = self.lines()
        ref = choose_reference(ls, 0.9)
        ls[ref.key].intensity *= 0.6
        res = irsac_species(ls, 0.9, 0.0, 0.03, reference=ls[ref.key])
        self.assertTrue(res[ref.key]["irsac_status"].startswith("reference, self-absorbed"))
        self.assertAlmostEqual(res[ref.key]["irsac_fref"], 0.6, delta=0.02)
        self.assertAlmostEqual(res[ref.key]["irsac_sac"], 1 / 0.6, delta=0.05)
        others = [v for k, v in res.items() if k != ref.key]
        self.assertTrue(all(v["irsac_sac"] == 1.0 for v in others))
        res0 = irsac_species(ls, 0.9, 0.0, 0.03, reference=ls[ref.key], ref_absorption=False)
        self.assertEqual(res0[ref.key]["irsac_sac"], 1.0)

    def test_single_stronger_line_does_not_rescale_reference(self):
        ls = self.lines(attenuate={4: 1.8})
        res = irsac_species(ls, 0.9, 0.0, 0.03)
        ref = [k for k, v in res.items() if v["irsac_status"].startswith("reference")][0]
        self.assertEqual(res[ref]["irsac_fref"], 1.0)
        self.assertIn("blend", res[ref]["irsac_status"])

    def test_factor_above_bound_is_not_applied(self):
        ls = self.lines(attenuate={0: 0.1})
        res = irsac_species(ls, 0.9, 0.0, 0.03)
        self.assertIsNone(res[0]["irsac_sac"])
        self.assertTrue(res[0]["irsac_status"].startswith("unsafe"))
        res = irsac_species(ls, 0.9, 0.0, 0.03, max_sac=0)
        self.assertAlmostEqual(res[0]["irsac_sac"], 10.0, delta=0.5)

    def test_poor_fit_is_not_corrected_nor_reference(self):
        ls = self.lines(attenuate={0: 0.5})
        best = choose_reference(ls, 0.9)
        best.fit_warning = "residual"
        self.assertNotEqual(choose_reference(ls, 0.9).key, best.key)
        ls[0].snr = 4.0
        res = irsac_species(ls, 0.9, 0.0, 0.03)
        self.assertIsNone(res[0]["irsac_sac"])

    def test_same_upper_level_mismatch(self):
        a = SALine(1, "Ca", 1, 4000.0, 0.0, 3.0, 1.0, 1.0, 0.1, label="a")
        b = SALine(2, "Ca", 1, 4100.0, 1.0, 3.0, 1.0, 0.5, 0.1, label="b")
        c = SALine(3, "Ca", 1, 4200.0, 1.0, 3.5, 1.0, 0.5, 0.1, label="c")
        out = same_level_test([a, b, c], sigma_y=0.05)
        self.assertTrue(out[2].startswith("weaker"))
        self.assertTrue(out[1].startswith("stronger"))
        self.assertNotIn(3, out)
        b.intensity = 0.98
        self.assertTrue(same_level_test([a, b], sigma_y=0.05)[2].startswith("agrees"))

    def test_slope_check_after_correction(self):
        ls = self.lines(attenuate={0: 0.5})
        res = assess(ls, None, 0.9, 1e17, sigma_y=0.03)
        sc = slope_check(res, "irsac", 0.9)
        self.assertTrue(sc[("Ca", 1)]["compatible"])
        self.assertAlmostEqual(sc[("Ca", 1)]["kt"], 0.9, delta=0.01)


class TestStarkGuards(unittest.TestCase):
    ref = StarkRef(w_1e17=0.10, rel_unc=0.15, n_exp=0.0, t_range=(1e4, 1e4), n_meas=1, kind="measured")

    def line(self, wl_lorentz):
        return SALine(1, "X", 1, 5000.0, 0.0, 3.0, 1.0, 1.0, wl_lorentz)

    def test_unresolved_when_w0_below_instrument(self):
        out = stark_assessment(self.line(0.5), self.ref, 1e17, 0.1, inst_fwhm=1.0, resolve_ratio=0.2)
        self.assertTrue(out["stark_status"].startswith("unresolved"))

    def test_thin_when_measured_width_below_w0(self):
        out = stark_assessment(self.line(0.08), self.ref, 1e17, 0.1, inst_fwhm=0.1)
        self.assertEqual(out["stark_sac"], 1.0)

    def test_correction_follows_el_sherbini(self):
        out = stark_assessment(self.line(0.40), self.ref, 1e17, 0.1, inst_fwhm=0.1)
        self.assertEqual(out["stark_status"], "self-absorbed")
        self.assertAlmostEqual(out["stark_sac"], 4.0 ** (0.46 / 0.54), places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
