import sqlite3
import math
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace

from pyLIBS import MainWindow
from pylibs.core.models import AtomicLine, TemplateLine
from pylibs.db.libs_database import LibsDatabase


ROOT = Path(__file__).resolve().parents[1]


class DatabaseLibraryTests(unittest.TestCase):
    def test_historical_library_remains_available(self):
        database = LibsDatabase(str(ROOT / "LIBS.db")).connect()
        try:
            self.assertEqual(database.display_name(), "LIBS++ historical")
            self.assertIn("Cu", database.element_tables())
        finally:
            database.close()

    def test_nist_library_metadata_and_counts(self):
        path = ROOT / "LIBS_NIST_5_12.db"
        database = LibsDatabase(str(path)).connect()
        try:
            info = database.database_info()
            self.assertEqual(info["version"], "5.12")
            self.assertEqual(info["wavelength_unit"], "angstrom")
            line = database.search_lines(
                3247.54, search_range=0.2, table="Cu", element="Cu", ion=1, limit=1
            )[0]
            self.assertAlmostEqual(line.wavelen, 3247.54, places=2)
            self.assertGreater(line.aki, 0.0)
            self.assertGreater(database.partition_function("Cu", 1, 10000), 0.0)
        finally:
            database.close()
        connection = sqlite3.connect(path)
        try:
            total = sum(
                connection.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]
                for row in connection.execute("SELECT specie FROM Elementi")
            )
            self.assertEqual(total, 40858)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM Datalibs").fetchone()[0], 24662)
        finally:
            connection.close()

    def test_nist_partition_function_uses_levels_above_legacy_grid(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            self.assertIn("livelli", database.tables())
            cu_i_19000 = database.partition_function("Cu", 1, 19000.0)
            cu_ii_19000 = database.partition_function("Cu", 2, 19000.0)
            self.assertAlmostEqual(cu_i_19000, 20.0712, places=3)
            self.assertAlmostEqual(cu_ii_19000, 4.9055, places=3)
            self.assertGreater(
                database.partition_function("Cu", 1, 21000.0),
                cu_i_19000,
            )
        finally:
            database.close()

    def test_partition_function_matches_direct_level_sum(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            temperature = 20722.0
            rows = database.conn.execute(
                "SELECT Ei, gi FROM livelli WHERE element='Al' AND CAST(ion AS INTEGER)=1"
            ).fetchall()
            expected = math.fsum(
                float(row["gi"])
                * math.exp(-1.4387768775039338 * float(row["Ei"]) / temperature)
                for row in rows
            )
            self.assertAlmostEqual(
                database.partition_function("Al", 1, temperature),
                expected,
                places=12,
            )
        finally:
            database.close()

    def test_nist_trace_accepts_nanometers_and_returns_nanometers(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            lines = database.trace_lines(
                "Pb",
                290.0,
                487.0,
                ions=[1],
                max_lines=20,
                wavelength_unit="nm",
            )
        finally:
            database.close()

        wavelengths = [line.wavelen for line in lines]
        self.assertTrue(any(abs(value - 368.34624) < 0.001 for value in wavelengths))
        self.assertTrue(all(290.0 <= value <= 487.0 for value in wavelengths))

    def test_nist_nm_search_enriches_the_same_lead_transition(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            line = database.search_lines(
                368.34624,
                search_range=0.01,
                table="Datalibs",
                element="Pb",
                ion=1,
                limit=1,
                wavelength_unit="nm",
            )[0]
            enriched = database.enrich_line_from_element_table(
                line,
                tolerance=0.005,
                wavelength_unit="nm",
            )
        finally:
            database.close()

        self.assertAlmostEqual(enriched.wavelen, 368.34624, places=3)
        self.assertEqual(enriched.specie, "Pb")
        self.assertEqual(enriched.ion, 1)
        self.assertGreater(enriched.aki, 0.0)
        self.assertGreater(enriched.ek, 0.0)

    def test_nist_aki_is_returned_in_physical_inverse_seconds(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            line = database.search_lines(
                313.411,
                search_range=0.01,
                table="Ni",
                element="Ni",
                ion=1,
                limit=1,
                wavelength_unit="nm",
            )[0]
        finally:
            database.close()

        self.assertAlmostEqual(line.wavelen, 313.4107, places=3)
        self.assertAlmostEqual(line.aki, 7.3e7, delta=1.0e5)
        self.assertAlmostEqual(line.aki * line.gk, 3.65e8, delta=1.0e6)

    def test_historical_aki_uses_the_same_libs_plus_scale(self):
        database = LibsDatabase(str(ROOT / "LIBS.db")).connect()
        try:
            line = database.search_lines(
                3247.54,
                search_range=0.2,
                table="Cu",
                element="Cu",
                ion=1,
                limit=1,
            )[0]
        finally:
            database.close()

        self.assertGreater(line.aki, 1.0e5)

    def test_selected_line_matching_does_not_add_unselected_lead_lines(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            lines = database.match_selected_lines(
                "Pb",
                [313.411, 368.34625, 405.78067],
                tolerance=0.02,
                ions=[1, 2],
                wavelength_unit="nm",
            )
        finally:
            database.close()

        wavelengths = [line.wavelen for line in lines]
        self.assertEqual(len(wavelengths), 2)
        self.assertTrue(any(abs(value - 368.34624) < 0.001 for value in wavelengths))
        self.assertTrue(any(abs(value - 405.78066) < 0.001 for value in wavelengths))
        self.assertFalse(any(abs(value - 363.95676) < 0.001 for value in wavelengths))

    def test_selected_cadmium_wavelength_matches_only_the_nearest_ion_stage(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            lines = database.match_selected_lines(
                "Cd",
                [340.36521],
                tolerance=0.1,
                ions=[1, 2],
                wavelength_unit="nm",
            )
        finally:
            database.close()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].ion, 1)
        self.assertAlmostEqual(lines[0].wavelen, 340.36521, places=4)

    def test_enrichment_never_changes_an_already_known_ion_stage(self):
        database = LibsDatabase(str(ROOT / "LIBS_NIST_5_12.db")).connect()
        try:
            original = AtomicLine(340.4221924, "Cd", 1)
            enriched = database.enrich_line_from_element_table(
                original,
                tolerance=0.001,
                wavelength_unit="nm",
            )
        finally:
            database.close()

        self.assertIs(enriched, original)
        self.assertEqual(enriched.ion, 1)

    def test_template_enrichment_uses_selected_nist_wavelength_before_fit_center(self):
        database_path = ROOT / "LIBS_NIST_5_12.db"
        database = LibsDatabase(str(database_path)).connect()
        app = SimpleNamespace(
            libs_db=database,
            options=SimpleNamespace(
                libs_db_file=str(database_path),
                search_range=1.0,
            ),
            wavelength_unit="nm",
            current_wavelength_unit_label=lambda: "nm",
        )
        app.copy_atomic_line_to_template_line = MethodType(
            MainWindow.copy_atomic_line_to_template_line,
            app,
        )
        line = TemplateLine(
            wavelen=340.36521,
            fitwavelen=340.4221924,
            specie="Cd",
            ion=1,
        )
        try:
            enriched = MainWindow.enrich_identified_template_line(
                app,
                line,
                tolerance=1.0,
            )
        finally:
            database.close()

        self.assertTrue(enriched)
        self.assertEqual(line.ion, 1)
        self.assertAlmostEqual(line.asswavelen, 340.36521, places=4)


if __name__ == "__main__":
    unittest.main()
