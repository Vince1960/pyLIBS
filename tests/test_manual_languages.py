import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pylibs.gui.simple_dialogs import show_manual
from pylibs.utils.paths import manual_path


class ManualLanguageTests(unittest.TestCase):
    def test_manual_paths_are_distinct_and_stable(self):
        self.assertEqual(manual_path("it").name, "pyLIBS_Manual.pdf")
        self.assertEqual(manual_path("en").name, "pyLIBS_Manual_EN.pdf")
        self.assertNotEqual(manual_path("it"), manual_path("en"))

    def test_unsupported_manual_language_is_rejected(self):
        with self.assertRaises(ValueError):
            manual_path("fr")

    def test_show_manual_opens_the_requested_language(self):
        with tempfile.TemporaryDirectory() as directory:
            english_manual = Path(directory) / "pyLIBS_Manual_EN.pdf"
            english_manual.touch()
            with (
                patch("pylibs.gui.simple_dialogs.manual_path", return_value=english_manual) as path_mock,
                patch("pylibs.gui.simple_dialogs._open_manual_with_qt", return_value=True) as open_mock,
            ):
                show_manual(object(), "en")

            path_mock.assert_called_once_with("en")
            open_mock.assert_called_once_with(english_manual)


if __name__ == "__main__":
    unittest.main()
