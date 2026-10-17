import inspect
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import pyLIBS
from pylibs.gui import simple_dialogs
from pylibs.io import report_io
from pylibs.utils.constants import APP_NAME, APP_TITLE, APP_VERSION


ROOT = Path(__file__).resolve().parents[1]


class ApplicationVersionConsistencyTests(unittest.TestCase):
    def test_application_version_is_centralized_and_at_current_release(self):
        self.assertEqual(APP_VERSION, "1.1.1")
        self.assertEqual(APP_TITLE, f"{APP_NAME} {APP_VERSION}")
        self.assertEqual(pyLIBS.APP_VERSION, APP_VERSION)
        self.assertEqual(simple_dialogs.APP_VERSION, APP_VERSION)
        self.assertEqual(report_io.APP_VERSION, APP_VERSION)
        self.assertIn("APP_VERSION", inspect.getsource(pyLIBS.show_startup_splash))
        self.assertIn("APP_VERSION", inspect.getsource(simple_dialogs.show_about))

    def test_main_window_title_uses_centralized_app_title(self):
        titles = []
        owner = SimpleNamespace(
            build_retro_menu=lambda: None,
            build_retro_toolbar=lambda: None,
            title=titles.append,
            status=lambda _message: None,
        )
        pyLIBS.install_retro_ui(owner)
        self.assertEqual(titles, [APP_TITLE])

    def test_documentation_and_citation_metadata_match_application_version(self):
        for manual in ("docs/pyLIBS_Manual.md", "docs/pyLIBS_Manual_EN.md"):
            content = (ROOT / manual).read_text(encoding="utf-8")
            self.assertIn(f"Software: pyLIBS {APP_VERSION}", content)

        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        match = re.search(r'^version:\s*["\']?([^"\'\s]+)', citation, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), APP_VERSION)

    def test_application_sources_do_not_keep_the_stale_version_literal(self):
        for filename in (
            "pyLIBS.py",
            "pylibs/utils/constants.py",
            "pylibs/gui/simple_dialogs.py",
            "pylibs/io/report_io.py",
        ):
            content = (ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn("1.0.3", content)


if __name__ == "__main__":
    unittest.main()
