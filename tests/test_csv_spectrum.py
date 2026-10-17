import tempfile
import unittest
from pathlib import Path

from pylibs.io.spectrum_io import (
    SPECTRUM_FILETYPES,
    convert_csv_batch,
    read_ascii_spectrum,
    read_ascii_spectrum_columns,
    read_csv_spectrum,
)
from pyLIBS import AppOptions, load_spectrum_for_open as load_pylibs_spectrum


class CsvSpectrumReaderTests(unittest.TestCase):
    def write_csv(self, folder, contents, name="spectrum.csv"):
        path = Path(folder) / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_detects_comma_semicolon_and_tab_delimiters(self):
        with tempfile.TemporaryDirectory() as folder:
            comma = self.write_csv(folder, "400.125,12.5\n401.25,13.75\n", "comma.csv")
            semicolon = self.write_csv(folder, "400.125;12.5\n401.25;13.75\n", "semi.csv")
            tab = self.write_csv(folder, "400.125\t12.5\n401.25\t13.75\n", "tab.csv")
            expected = ([400.125, 401.25], [12.5, 13.75])
            for path in (comma, semicolon, tab):
                self.assertEqual(read_csv_spectrum(str(path)), expected)

    def test_headers_empty_lines_bom_and_decimal_comma(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "locale.csv"
            path.write_text(
                "\ufeffWavelength (nm);Intensity\n\n400,125;12,5\n401,250;13,75\n",
                encoding="utf-8",
            )
            self.assertEqual(read_csv_spectrum(str(path)), ([400.125, 401.25], [12.5, 13.75]))
            tab_path = self.write_csv(folder, "lambda\tcounts\n400,125\t2,5\n")
            self.assertEqual(read_csv_spectrum(str(tab_path)), ([400.125], [2.5]))

    def test_headerless_and_quoted_comma_decimal_rows_are_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            comma_decimal = self.write_csv(folder, '"400,125","12,5"\n"401,25","13,75"\n')
            self.assertEqual(read_csv_spectrum(str(comma_decimal)), ([400.125, 401.25], [12.5, 13.75]))
            self.assertEqual(read_ascii_spectrum(str(comma_decimal)), ([400.125, 401.25], [12.5, 13.75]))

    def test_angstrom_conversion_and_column_api_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_csv(folder, "Wavelength,Intensity\n400,10\n401,20\n")
            xs, columns = read_ascii_spectrum_columns(str(path), convert_nm_to_a=True)
            self.assertEqual(xs, [4000.0, 4010.0])
            self.assertEqual(columns, [[10.0, 20.0]])

    def test_normal_pylibs_loader_uses_csv_reader_and_existing_processing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_csv(folder, "Wavelength;Intensity\n400,5;20,25\n401,5;30,75\n")
            spectrum = load_pylibs_spectrum(str(path), AppOptions(dark_mode="none"))
        self.assertEqual(spectrum.x, [400.5, 401.5])
        self.assertEqual(spectrum.y, [20.25, 30.75])

    def test_malformed_rows_and_invalid_csv_are_rejected_clearly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_csv(folder, "wavelength,intensity\n400,10\n401,not-a-number\n")
            with self.assertRaisesRegex(ValueError, "Invalid CSV spectrum"):
                read_csv_spectrum(str(path))
            path.write_text("wavelength,intensity\n400,10,extra\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid CSV spectrum"):
                read_csv_spectrum(str(path))
            path.write_text('400,"12\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid CSV spectrum"):
                read_csv_spectrum(str(path))

    def test_bare_comma_decimal_values_are_reported_as_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_csv(folder, "400,125,12,5\n401,25,13,75\n")
            with self.assertRaisesRegex(ValueError, "Ambiguous CSV spectrum"):
                read_csv_spectrum(str(path))

    def test_batch_conversion_keeps_precision_and_continues_after_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            good = self.write_csv(
                folder,
                "lambda;signal\n400.12345678901234;1.2345678901234567\n",
                "sample.CSV",
            )
            bad = self.write_csv(folder, "x,y\ninvalid\n", "broken.csv")
            output = root / "out"
            converted, failed = convert_csv_batch([good, bad], output)
            self.assertEqual([path.name for path in converted], ["sample.txt"])
            self.assertEqual([path.name for path, _ in failed], ["broken.csv"])
            lines = converted[0].read_text(encoding="ascii").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(len(lines[0].split("\t")), 2)
            self.assertEqual(float(lines[0].split("\t")[0]), 400.12345678901234)
            self.assertEqual(float(lines[0].split("\t")[1]), 1.2345678901234567)

    def test_shared_spectrum_file_filter_includes_csv(self):
        self.assertIn("*.csv *.CSV", SPECTRUM_FILETYPES[0][1])
        self.assertEqual(SPECTRUM_FILETYPES[9][0], "CSV Files (*.csv *.CSV)")


if __name__ == "__main__":
    unittest.main()
