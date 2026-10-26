import tempfile
import unittest
from pathlib import Path

from pylibs.core.time_resolved import (
    pair_spectra,
    process_time_resolved_pairs,
    subtract_spectra,
    time_resolved_output_path,
    validate_output_prototype,
)
from pylibs.io.spectrum_io import read_ascii_spectrum, write_ascii_spectrum


class TimeResolvedTests(unittest.TestCase):
    def test_subtract_clips_and_preserves_axis(self):
        x, y = subtract_spectra([400.0, 401.0], [10, 2], [400.0, 401.0], [3, 5])
        self.assertEqual(x, [400.0, 401.0])
        self.assertEqual(y, [7, 0])

    def test_rejects_length_and_axis_mismatch(self):
        with self.assertRaisesRegex(ValueError, "point counts"):
            subtract_spectra([1, 2], [1, 2], [1], [1])
        with self.assertRaisesRegex(ValueError, "point 2"):
            subtract_spectra([1, 2], [1, 2], [1, 2.01], [1, 2])

    def test_natural_sort_pairing_and_output_name(self):
        with tempfile.TemporaryDirectory() as folder:
            a = [Path(folder) / "spectrum10.txt", Path(folder) / "spectrum2.txt"]
            b = [Path(folder) / "spectrum10.csv", Path(folder) / "spectrum2.csv"]
            self.assertEqual([p[0].name for p in pair_spectra(a, b)], ["spectrum2.txt", "spectrum10.txt"])
            self.assertEqual(time_resolved_output_path("spectrum_05.csv", folder, 500, 1000, "Sample", 1, 3).name, "Sample--d500-g500-001.csv")
            self.assertEqual(time_resolved_output_path("sample.txt", folder, 260, 468, "Sample", 3, 3).name, "Sample--d260-g208-003.txt")
            self.assertEqual(time_resolved_output_path("sample.txt", folder, 1.25, 2.5, "Sample", 1000, 1000).name, "Sample--d1p25-g1p25-1000.txt")
            self.assertEqual(time_resolved_output_path("sample.TXT", folder, 260, 468, "Sample", 1, 1).name, "Sample--d260-g208-001.TXT")

    def test_prototype_validation(self):
        self.assertEqual(validate_output_prototype(" Sample "), "Sample")
        for invalid in ("", "bad/name", "bad:name", "name.txt", "..", "trailing."):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_output_prototype(invalid)

    def test_unequal_counts_and_delay_order_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "different numbers"):
            pair_spectra(["a.txt"], [])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "greater"):
                process_time_resolved_pairs([], [], 2, 1, folder, "Sample")

    def test_multiple_pairs_csv_txt_roundtrip_and_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            out = root / "out"
            a1, b1 = root / "spectrum2.txt", root / "spectrum2_late.txt"
            a2, b2 = root / "spectrum10.csv", root / "spectrum10_late.csv"
            write_ascii_spectrum(str(a1), [400, 401], [10, 2])
            write_ascii_spectrum(str(b1), [400, 401], [3, 5])
            a2.write_text("400,20\n401,30\n", encoding="utf-8")
            b2.write_text("400,2\n401,10\n", encoding="utf-8")
            out.mkdir()
            pairs, saved, failed = process_time_resolved_pairs([a2, a1], [b2, b1], 260, 468, out, "Sample")
            self.assertEqual(len(pairs), 2)
            self.assertEqual(len(saved), 2)
            self.assertFalse(failed)
            self.assertEqual(read_ascii_spectrum(str(out / "Sample--d260-g208-001.txt")), ([400.0, 401.0], [7.0, 0.0]))
            self.assertEqual(read_ascii_spectrum(str(out / "Sample--d260-g208-002.csv")), ([400.0, 401.0], [18.0, 20.0]))
            _, saved_again, failed_again = process_time_resolved_pairs([a1], [b1], 260, 468, out, "Sample")
            self.assertFalse(saved_again)
            self.assertIn("already exists", failed_again[0][2])
            _, overwritten, overwrite_errors = process_time_resolved_pairs([a1], [b1], 260, 468, out, "Sample", overwrite=True)
            self.assertEqual(len(overwritten), 1)
            self.assertFalse(overwrite_errors)

    def test_missing_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "does not exist"):
                process_time_resolved_pairs([], [], 0, 1, Path(folder) / "missing", "Sample")


if __name__ == "__main__":
    unittest.main()
