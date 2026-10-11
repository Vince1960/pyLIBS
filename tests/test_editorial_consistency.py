import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ITALIAN_MANUAL = ROOT / "docs" / "pyLIBS_Manual.md"
ENGLISH_MANUAL = ROOT / "docs" / "pyLIBS_Manual_EN.md"
PROGRAM = ROOT / "pyLIBS.py"


class EditorialConsistencyTests(unittest.TestCase):
    def test_italian_manual_uses_required_accents(self):
        text = ITALIAN_MANUAL.read_text(encoding="utf-8")
        unaccented = (
            "piu", "puo", "modalita", "unita", "qualita", "sensibilita",
            "stabilita", "densita", "compatibilita", "validita",
            "probabilita", "meta", "gia", "perche", "integrita",
            "intensita", "profondita", "ripetibilita", "parita",
        )
        self.assertIsNone(
            re.search(r"\b(?:" + "|".join(unaccented) + r")\b", text, re.IGNORECASE)
        )

    def test_manuals_use_current_menu_names(self):
        obsolete = (
            "Analytical Lines / Main Library...",
            "Calculate Ne from Ha",
            "Saha Boltzmann plot",
            "| CF LIBS |",
            "| Auto X / Auto Y |",
            "| Show All |",
            "| nm -> A |",
            "| Batch Ops. |",
            "| Manual > Italiano / English |",
            "`Autofit`",
        )
        for path in (ITALIAN_MANUAL, ENGLISH_MANUAL):
            text = path.read_text(encoding="utf-8")
            for old_label in obsolete:
                with self.subTest(path=path.name, label=old_label):
                    self.assertNotIn(old_label, text)

    def test_markdown_table_rows_are_well_formed(self):
        for path in (ITALIAN_MANUAL, ENGLISH_MANUAL):
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                if line.startswith("|"):
                    with self.subTest(path=path.name, line=number):
                        self.assertTrue(line.endswith("|"))
                        self.assertGreaterEqual(line.count("|"), 3)

    def test_user_facing_library_names_are_capitalized(self):
        source = PROGRAM.read_text(encoding="utf-8")
        for fragment in (
            "matplotlib not available",
            "numpy not available",
            "scipy.optimize not available",
            "Install scipy",
        ):
            self.assertNotIn(fragment, source)

    def test_window_titles_do_not_expose_legacy_unit_numbers(self):
        source = PROGRAM.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"self\.title\([^\n]*Unit\d+", source))
        self.assertNotIn('"Ha parameters"', source)
        self.assertNotIn('"electron density Range"', source)


if __name__ == "__main__":
    unittest.main()
