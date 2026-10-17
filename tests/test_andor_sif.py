import tempfile
import unittest
from pathlib import Path

import numpy as np

from pylibs.io.andor_sif import convert_sif_batch, read_andor_sif
from pylibs.io.spectrum_io import SPECTRUM_FILETYPES, load_spectrum_for_open


FIXTURE = Path(__file__).parent / "fixtures" / "spectrum.sif"


def synthetic_sif(*, dimensions="65538 1 1 4 1 1 1 4 4", coords="65538 1 1 4 1 1 1 0", calibration="700 0.25 0 0", pixels=None):
    pixels = np.asarray([1.25, 2.5, 3.75, 5.0] if pixels is None else pixels, dtype="<f4")
    header = (
        "Andor Technology Multi-Channel File\n"
        "65539 2 0 1 0 1\n"
        f"{calibration}\n"
        f"Pixel number{dimensions}\n"
        f"{coords}\n"
        "0\n"
    ).encode("ascii")
    return header + pixels.tobytes() + b"END!\x00\x00\x00\x00"


class AndorSifReaderTests(unittest.TestCase):
    def test_mechelle_fixture_calibration_and_pixel_values(self):
        wavelength, intensity = read_andor_sif(FIXTURE)
        self.assertEqual(len(wavelength), 8000)
        self.assertAlmostEqual(wavelength[0], 753.6400379, places=9)
        self.assertAlmostEqual(wavelength[1], 753.6830758, places=9)
        self.assertAlmostEqual(wavelength[-1], 1097.9002, places=7)
        np.testing.assert_array_equal(
            intensity[:5], np.array([1918.0, 813.1772, 395.268, 380.36926, 436.70627], dtype=np.float32)
        )

    def test_ascii_andor_load_path_and_shared_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short.SIF"
            path.write_bytes(synthetic_sif())
            spectrum = load_spectrum_for_open(str(path), type("Options", (), {"convert_to_angstrom": False})(), type("Spectrum", (), {"__init__": lambda self, x, y, name, filename: self.__dict__.update(x=x, y=y, name=name, filename=filename)}))
        self.assertEqual(spectrum.x, [700.25, 700.5, 700.75, 701.0])
        self.assertEqual(spectrum.y, [1.25, 2.5, 3.75, 5.0])
        self.assertIn("*.sif *.SIF", SPECTRUM_FILETYPES[0][1])

    def test_malformed_header_and_truncated_payload_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.sif"
            path.write_bytes(b"not an Andor file")
            with self.assertRaisesRegex(ValueError, "signature"):
                read_andor_sif(path)
            path.write_bytes(synthetic_sif()[:-12])
            with self.assertRaisesRegex(ValueError, "truncated"):
                read_andor_sif(path)

    def test_invalid_dimensions_and_unsupported_sif_variants_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variant.sif"
            path.write_bytes(synthetic_sif(dimensions="65538 0 1 4 1 1 1 4 4"))
            with self.assertRaisesRegex(ValueError, "invalid or unsupported dimensions"):
                read_andor_sif(path)
            path.write_bytes(synthetic_sif(coords="65538 1 1 4 2 1 1 0"))
            with self.assertRaisesRegex(ValueError, "single extracted 1D"):
                read_andor_sif(path)
            path.write_bytes(synthetic_sif(dimensions="65538 2 1 4 1 1 1 4 4"))
            with self.assertRaisesRegex(ValueError, "single extracted 1D"):
                read_andor_sif(path)

    def test_missing_calibration_and_malformed_dimension_record_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.sif"
            path.write_bytes(synthetic_sif(calibration="not calibration"))
            with self.assertRaisesRegex(ValueError, "invalid wavelength calibration"):
                read_andor_sif(path)
            path.write_bytes(synthetic_sif(dimensions="65538 x 1 4 1 1 1 4 4"))
            with self.assertRaisesRegex(ValueError, "malformed spectrum dimensions"):
                read_andor_sif(path)

    def test_big_endian_payload_is_not_silently_interpreted_as_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "byte-order.sif"
            header = (
                "Andor Technology Multi-Channel File\n65539 2 0 1 0 1\n"
                "700 0.25 0 0\nPixel number65538 1 1 4 1 1 1 4 4\n"
                "65538 1 1 4 1 1 1 0\n0\n"
            ).encode("ascii")
            path.write_bytes(header + np.array([1, 2, 3, 4], dtype=">f4").tobytes() + b"END!\x00\x00\x00\x00")
            with self.assertRaisesRegex(ValueError, "byte order"):
                read_andor_sif(path)

    def test_batch_conversion_has_two_exact_numeric_columns_and_isolates_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "sample.sif"
            bad = root / "broken.sif"
            out = root / "out"
            good.write_bytes(synthetic_sif())
            bad.write_bytes(b"broken")
            converted, failed = convert_sif_batch([good, bad], out)
            self.assertEqual([p.name for p in converted], ["sample.txt"])
            self.assertEqual([p.name for p, _ in failed], ["broken.sif"])
            lines = converted[0].read_text(encoding="ascii").splitlines()
            self.assertEqual(len(lines), 4)
            for line in lines:
                fields = line.split("\t")
                self.assertEqual(len(fields), 2)
                self.assertTrue(all(float(value) == float(value) for value in fields))
            self.assertEqual([float(line.split("\t")[1]) for line in lines], [1.25, 2.5, 3.75, 5.0])


if __name__ == "__main__":
    unittest.main()
