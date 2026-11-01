"""Stark_extended.db: unit convention of the original Stark.db and data sanity."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import _synthetic_data as S  # noqa: E402
from pylibs.core.self_absorption_irsac2 import StarkDatabase  # noqa: E402

ORIG = S.ROOT / "Stark.db"


@unittest.skipUnless(S.STARK_DB.exists() and ORIG.exists(), "Stark databases not found")
class TestStarkDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ext = sqlite3.connect(f"file:{S.STARK_DB.resolve().as_posix()}?mode=ro", uri=True)
        cls.orig = sqlite3.connect(f"file:{ORIG.resolve().as_posix()}?mode=ro", uri=True)

    @classmethod
    def tearDownClass(cls):
        cls.ext.close()
        cls.orig.close()

    def test_original_stark_db_is_hwhm_in_nm(self):
        """Original value x 20 (HWHM nm -> FWHM A) equals the NIST critical-review FWHM normalized to 1e17."""
        cases = {("Sr", 2, 4215.52): 0.32, ("Ni", 1, 3414.76): 0.0763, ("Ba", 2, 4934.09): 0.434,
                 ("Cu", 1, 5105.54): 0.43, ("Al", 2, 2816.19): 0.424}
        for (el, ion, wl), fwhm in cases.items():
            w = self.orig.execute("SELECT \"w-T10000\" FROM Stark WHERE TRIM(Element)=? AND Ion=? "
                                  "AND ABS(Wavelength-?)<0.1", (el, ion, wl)).fetchone()[0]
            self.assertAlmostEqual(w * 20.0, fwhm, delta=0.01 * fwhm + 1e-4, msg=f"{el} {ion} {wl}")

    def test_known_bad_entry_is_excluded(self):
        row = self.ext.execute("SELECT status, note FROM measurements WHERE element='Fe' AND ion=1 "
                               "AND ABS(wavelength_A-4260.47)<0.1 AND extraction='original'").fetchone()
        self.assertEqual(row[0], "excluded")
        self.assertIn("10x", row[1])

    def test_all_values_positive_and_normalized(self):
        bad = self.ext.execute("SELECT COUNT(*) FROM measurements WHERE fwhm_A<=0 OR ne_cm3<=0 OR T_K<=0 "
                               "OR ABS(fwhm_A_1e17 - fwhm_A*1e17/ne_cm3) > 1e-9*fwhm_A_1e17").fetchone()[0]
        self.assertEqual(bad, 0)

    def test_reference_width(self):
        db = StarkDatabase(S.STARK_DB)
        try:
            r = db.reference("Si", 2, 6347.1, 11000)
            self.assertGreater(r.w_1e17, 1.5)
            self.assertLess(r.w_1e17, 3.5)
            self.assertLess(r.n_exp, 0)          # ionic line: width decreases with T
            self.assertIsNone(db.reference("Xx", 1, 5000.0, 10000))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
