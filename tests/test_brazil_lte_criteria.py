import math
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pylibs.core.lte_criteria as L  # noqa: E402

REAL_DB = HERE.parent / "LIBS.db"


class TestFormulas(unittest.TestCase):
    def test_mcwhirter_value(self):
        # 1.6e12 * sqrt(10000) * 2^3 = 1.28e15
        self.assertAlmostEqual(L.mcwhirter_ne_min(1e4, 2.0) / 1.28e15, 1.0, places=12)

    def test_oscillator_strength_na_d2(self):
        # Na I 589.158 nm (vacuum), A = 6.16e7 s-1, gi = 2, gk = 4 -> f = 0.641 (NIST)
        f = L.oscillator_strength(5891.58, 6.16e7, 2, 4)
        self.assertAlmostEqual(f, 0.641, delta=0.003)

    def test_diffusion_consistency(self):
        # λ² / τ_rel must give D = (1.4e12)²/6.3e4 * kT / (ne M_A), independent of ΔE, f, g
        ne, kt, de, m, f, g = 1e17, 1.0, 3.0, 40.0, 1.0, 0.2
        lam = L.diffusion_length(ne, kt, de, m, f, g)
        tau = L.relaxation_time(ne, kt, de, f, g)
        d_expected = L.LAMBDA_C ** 2 / L.TAU_C * kt / (ne * m)
        self.assertAlmostEqual(lam ** 2 / tau / d_expected, 1.0, places=10)

    def test_scaling(self):
        # τ_rel ∝ 1/ne ; ne_min ∝ ΔE^3
        self.assertAlmostEqual(L.relaxation_time(1e16, 1, 3, 1) / L.relaxation_time(1e17, 1, 3, 1), 10.0)
        self.assertAlmostEqual(L.mcwhirter_ne_min(1e4, 4) / L.mcwhirter_ne_min(1e4, 2), 8.0)

    def test_parse_species(self):
        self.assertEqual(L.parse_species("Fe I, ca II; Mg 1"), [("Fe", 1), ("Ca", 2), ("Mg", 1)])


def _synthetic_db(path):
    """Fictitious atom 'Xx': levels 0, 100, 20000, 25000, 30000 cm-1.
    Largest gap: 100 -> 20000 (19900 cm-1). Two transitions bridge it;
    the one with the largest f must be chosen."""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE Elementi (specie, n_atomico, m_atomica, en_ion, n_righe)")
    c.execute("INSERT INTO Elementi VALUES ('specie','n_atomico','m_atomica','en_ion','n_righe')")
    c.execute("INSERT INTO Elementi VALUES ('Xx', 99, 50.0, 70000.0, 3)")
    c.execute("CREATE TABLE livelli (element, ion, Ei, gi)")
    c.execute("INSERT INTO livelli VALUES ('element','ion','Ei','gi')")
    for e in (0.0, 100.0, 20000.0, 25000.0, 30000.0, 60000.0):
        c.execute("INSERT INTO livelli VALUES ('Xx','1',?,1)", (e,))
    c.execute("CREATE TABLE Xx (specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc)")
    c.execute("INSERT INTO Xx VALUES ('specie','ion','wavelen','Ei','Ek','gi','gk','Aki','acc')")
    c.execute("INSERT INTO Xx VALUES ('Xx',1,5000.0,0.0,20000.0,1,3,0.01,0)")      # fraca
    c.execute("INSERT INTO Xx VALUES ('Xx',1,4000.0,0.0,25000.0,1,3,1.0,0)")      # forte
    c.execute("INSERT INTO Xx VALUES ('Xx',1,20000.0,25000.0,30000.0,3,3,0.1,0)") # does not bridge
    c.commit()
    c.close()


class TestParsers(unittest.TestCase):
    def test_parse_bridges(self):
        d = L.parse_bridges("H I=121.567:0.4164; O I=130.217:0.052")
        self.assertEqual(d[("O", 1)].f12, 0.052)
        self.assertEqual(d[("H", 1)].wavelength_nm, 121.567)


class TestSynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "syn.db"
        _synthetic_db(cls.path)
        cls.db = L.AtomicData(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    LINE = L.TemplateLine("Xx", 1, 4000.0, 0.0, 25000.0)

    def test_gap_and_bridge(self):
        g = L.analyse_species(self.db, "Xx", 1, [self.LINE])
        self.assertAlmostEqual(g.gap_lo_cm1, 100.0)
        self.assertAlmostEqual(g.gap_hi_cm1, 20000.0)
        self.assertAlmostEqual(g.de_adjacent_ev, 19900 * L.CM1_TO_EV)
        self.assertAlmostEqual(g.de_bridge_ev, 25000 * L.CM1_TO_EV)    # escolheu a forte
        self.assertAlmostEqual(g.f12, L.oscillator_strength(4000.0, 1e8, 1, 3), places=8)
        self.assertEqual(g.mass_amu, 50.0)

    def test_levels_limited_by_lines(self):
        # with a line whose upper level is 25000, level 60000 (gap 30000) is not used
        line = L.TemplateLine("Xx", 1, 4000.0, 0.0, 25000.0)
        g = L.analyse_species(self.db, "Xx", 1, [line])
        self.assertAlmostEqual(g.gap_hi_cm1, 20000.0)
        g2 = L.analyse_species(self.db, "Xx", 1)  # no lines: up to the ionization limit (70000)
        self.assertAlmostEqual(g2.gap_hi_cm1, 60000.0)

    def test_verdict_and_worst_case(self):
        g = L.analyse_species(self.db, "Xx", 1, [self.LINE])
        de = g.de_bridge_ev  # conservative = largest available ΔE
        nmin = L.mcwhirter_ne_min(10000, de)
        p = L.PlasmaState(10000, 2 * nmin)
        v = L.evaluate_species(g, p)
        self.assertEqual(v.de_basis, "bridge")
        self.assertTrue(v.mcwhirter_ok)
        self.assertAlmostEqual(v.ratio, 2.0)
        # with σ_ne = 1.5 nmin the worst case drops below 1
        p2 = L.PlasmaState(10000, 2 * nmin, sigma_ne=1.5 * nmin)
        v2 = L.evaluate_species(g, p2)
        self.assertFalse(v2.mcwhirter_ok)
        self.assertGreater(v2.ratio, 1.0)

    def test_temporal_spatial(self):
        g = L.analyse_species(self.db, "Xx", 1, [self.LINE])
        p = L.PlasmaState(11604.5, 1e17, t_var_s=1e-3, d_var_cm=10.0)
        v = L.evaluate_species(g, p)
        self.assertTrue(v.temporal_ok)
        self.assertTrue(v.spatial_ok)
        p = L.PlasmaState(11604.5, 1e17, t_var_s=1e-15, d_var_cm=1e-12)
        v = L.evaluate_species(g, p)
        self.assertFalse(v.temporal_ok)
        self.assertFalse(v.spatial_ok)

    def test_template_reader(self):
        csvp = Path(self.tmp.name) / "t.csv"
        csvp.write_text(
            "wavelen,specie,ion,asswavelen,inte,ei,ek,aki,gk,gi,acc,wg,wl,fitwavelen\n"
            "4000,Xx,1,4000,10,0,25000,1e8,3,1,0,0,0,4000\n"
            "4100,Xx,1,4100,10,0,24000,-1e8,3,1,0,0,0,4100\n"     # excluded (Aki<0)
            "4200,Empty,0,0,0,0,0,0,0,0,0,0,0,0\n", encoding="utf-8")
        lines = L.read_pylibs_template(csvp)
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0].element, lines[0].ion), ("Xx", 1))


@unittest.skipUnless(REAL_DB.exists(), "real LIBS.db not found")
class TestRealDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = L.AtomicData(REAL_DB)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_hydrogen(self):
        # H I: maior intervalo 1s -> n=2 = 82259 cm-1 = 10.20 eV
        g = L.analyse_species(self.db, "H", 1)
        self.assertAlmostEqual(g.de_adjacent_ev, 10.20, delta=0.02)

    def test_hydrogen_override(self):
        ov = {("H", 1): L.BridgeOverride(121.567, 0.4164)}
        p = L.PlasmaState(11000, 1e17)
        v = L.check_lte(self.db, p, species=[("H", 1)], overrides=ov)[0]
        self.assertAlmostEqual(v.gaps.de_bridge_ev, 10.199, delta=0.002)
        self.assertIsNotNone(v.tau_rel_s)

    def test_calcium_resonance(self):
        # Ca I: the bridging transition must be the 422.67 nm resonance line (f ≈ 1.75)
        g = L.analyse_species(self.db, "Ca", 1)
        self.assertAlmostEqual(g.bridge_wavelength_A / 10, 422.67, delta=0.05)
        self.assertAlmostEqual(g.f12, 1.75, delta=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
