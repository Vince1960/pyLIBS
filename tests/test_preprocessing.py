import json
import tempfile
import unittest
from pathlib import Path

from pylibs.core.preprocessing import subtract_dark
from pylibs.io.spectrum_io import read_ascii_metadata, read_ascii_spectrum_columns
from pyLIBS import AppOptions, discover_replicate_spectrum_files, load_spectrum_for_open


class PreprocessingTests(unittest.TestCase):
    def test_precorrected_averager_file_does_not_subtract_configured_dark_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "305.txt"
            path.write_text(
                "# pylibs_dark_corrected=1\n"
                "# pylibs_dark_source=median_of_auxiliary_detector_traces\n"
                "300\t1\n301\t2\n",
                encoding="utf-8",
            )
            options = AppOptions(dark_mode="constant", dark_constant=525.0)

            spectrum = load_spectrum_for_open(str(path), options)

            self.assertEqual(spectrum.y, [1.0, 2.0])
            self.assertTrue(spectrum.dark_corrected)
            self.assertEqual(
                spectrum.dark_source, "median of auxiliary detector traces"
            )
            self.assertEqual(
                read_ascii_metadata(str(path))["pylibs_dark_corrected"], "1"
            )

    def test_replicate_manifest_links_mean_spectrum_to_acquisitions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mean_path = root / "305.txt"
            mean_path.write_text("300 1\n301 2\n", encoding="utf-8")
            replicate_dir = root / "replicates"
            replicate_dir.mkdir()
            paths = []
            for index in range(1, 4):
                path = replicate_dir / f"305_{index}.txt"
                path.write_text(f"300 {index}\n301 {index + 1}\n", encoding="utf-8")
                paths.append(path)
            (root / "replicates.json").write_text(
                json.dumps({
                    "format": "pylibs-replicates-v1",
                    "windows": {
                        "305.txt": {
                            "replicates": [
                                str(path.relative_to(root)) for path in paths
                            ]
                        }
                    },
                }),
                encoding="utf-8",
            )

            discovered = discover_replicate_spectrum_files(str(mean_path))

            self.assertEqual(discovered, tuple(str(path.resolve()) for path in paths))

    def test_multicolumn_decimal_comma_and_pixel_dark(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spectrum.asc"
            path.write_text(
                "300,0\t10,0\t2,0\t4,0\n"
                "301,0\t20,0\t3,0\t5,0\n"
                "302,0\t40,0\t4,0\t6,0\n",
                encoding="utf-8",
            )
            wavelengths, columns = read_ascii_spectrum_columns(str(path))
        result = subtract_dark(wavelengths, columns, mode="auto_columns", signal_column=1)
        self.assertEqual(wavelengths, [300.0, 301.0, 302.0])
        self.assertEqual(result.dark_columns, (1, 2))
        self.assertEqual(result.dark, [3.0, 4.0, 5.0])
        self.assertEqual(result.intensity, [7.0, 16.0, 35.0])

    def test_signal_column_can_be_selected_automatically(self):
        wavelengths = [1.0, 2.0, 3.0, 4.0]
        columns = [[10.0, 10.0, 10.0, 10.0], [10.0, 11.0, 40.0, 10.0]]
        result = subtract_dark(wavelengths, columns, mode="auto_columns", signal_column=0)
        self.assertEqual(result.signal_column, 1)
        self.assertEqual(result.intensity, [0.0, 1.0, 30.0, 0.0])


if __name__ == "__main__":
    unittest.main()
