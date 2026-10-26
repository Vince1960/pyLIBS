import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

from pylibs.io.aryelle import convert_aryelle_batch, read_aryelle
from pylibs.io.spectrum_io import SPECTRUM_FILETYPES, load_spectrum_for_open, read_ascii_spectrum


def make_ary(path: Path, internal_name="folder/unusual.~tmp", wavelengths=None, intensities=None):
    wavelengths = np.asarray([792.522, 334.427, 196.870] if wavelengths is None else wavelengths, dtype="<f4")
    intensities = np.asarray([2.25, 31684.0, 1.5] if intensities is None else intensities, dtype="<f4")
    # LTB sequence is intensity, wavelength, repeated.
    pairs = np.empty((len(wavelengths), 2), dtype="<f4")
    pairs[:, 0] = intensities
    pairs[:, 1] = wavelengths
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("notes/~aif", "must not be parsed")
        archive.writestr(internal_name, pairs.tobytes())
        archive.writestr("rep/~rep", "must not be parsed")


class AryelleTests(unittest.TestCase):
    def test_decode_interleaved_values_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.ary"
            make_ary(path)
            wavelength, intensity = read_aryelle(path)
        np.testing.assert_array_equal(wavelength, np.array([196.870, 334.427, 792.522], dtype=np.float32))
        np.testing.assert_array_equal(intensity, np.array([1.5, 31684.0, 2.25], dtype=np.float32))

    def test_member_name_is_not_fixed_and_bad_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "varied.ary"
            make_ary(path, "arbitrary-name.~TMP")
            self.assertEqual(len(read_aryelle(path)[0]), 3)
            path.write_bytes(b"not a zip")
            with self.assertRaisesRegex(ValueError, "ZIP container"):
                read_aryelle(path)
            path.write_bytes(b"")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("x.~tmp", b"1234567")
            with self.assertRaisesRegex(ValueError, "incomplete float pair"):
                read_aryelle(path)

    def test_shared_open_and_batch_ascii_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "sample.ary"
            make_ary(path, "different-base.~tmp")
            Spectrum = type("Spectrum", (), {"__init__": lambda self, x, y, name, filename: self.__dict__.update(x=x, y=y, name=name, filename=filename)})
            options = type("Options", (), {"convert_to_angstrom": False})()
            loaded = load_spectrum_for_open(str(path), options, Spectrum)
            self.assertEqual(len(loaded.x), 3)
            converted, failed = convert_aryelle_batch([path], root / "out")
            self.assertEqual(len(failed), 0)
            self.assertEqual(converted[0].name, "sample.txt")
            x, y = read_ascii_spectrum(str(converted[0]))
            np.testing.assert_allclose(x, loaded.x, rtol=0, atol=0)
            np.testing.assert_allclose(y, loaded.y, rtol=0, atol=0)
            again, failed = convert_aryelle_batch([path], root / "out")
            self.assertFalse(again)
            self.assertEqual(len(failed), 1)

    def test_filter_includes_ary(self):
        self.assertIn("*.ary *.ARY", SPECTRUM_FILETYPES[0][1])

    def test_supplied_sample_if_present(self):
        candidates = [Path("1,5.ary"), Path("tests/fixtures/1,5.ary")]
        sample = next((path for path in candidates if path.exists()), None)
        if sample is None:
            self.skipTest("The referenced 1,5.ary sample is not present in this workspace.")
        wavelength, intensity = read_aryelle(sample)
        self.assertEqual(len(wavelength), 40564)
        self.assertAlmostEqual(float(wavelength[0]), 196.870, places=2)
        self.assertAlmostEqual(float(wavelength[-1]), 792.522, places=2)
        index = int(np.argmax(intensity))
        self.assertAlmostEqual(float(intensity[index]), 31684, delta=2)
        self.assertAlmostEqual(float(wavelength[index]), 334.427, places=2)


if __name__ == "__main__":
    unittest.main()
