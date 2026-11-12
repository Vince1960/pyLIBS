"""Session files (pylibs.io.session_io): complete round trip without the GUI."""
import math
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pylibs.core.models import TemplateLine  # noqa: E402
from pylibs.io.session_io import apply_state, collect_state, load_session, save_session, summary  # noqa: E402


@dataclass
class Spec:
    x: list = field(default_factory=list)
    y: list = field(default_factory=list)
    name: str = "Spectrum"
    filename: str = ""
    visible: bool = True
    color: str = None
    response_corrected: bool = False


@dataclass
class Resp:
    x: list
    y: list
    filename: str = ""


def make_app():
    t = TemplateLine(3933.66, "Ca", 2, 3933.66, 1234.5, 0.0, 0.05, 0.12, 25414.4, -1.47, 4, 2, 3933.7, 1200.0, 12.3, 1)
    t.sa_use, t.sa_sac, t.sa_sac_rel = True, 1.37, 0.08
    opts = SimpleNamespace(kt_low=0.6, instrumental_width=0.37, libs_db_file="C:/x/LIBS.db", input_dir="C:/data")
    return SimpleNamespace(spectra=[Spec([1.0, 2.0, 3.0], [4.0, float("nan"), 6.0], "a", "C:/a.asc", color="#123456")],
                           template_lines=[t], session_temperature=0.85, session_ne=6e16, session_ne_source="H-alpha",
                           apply_sac_correction=True, options=opts, response=Resp([1.0, 2.0], [0.5, 0.7], "r.txt"))


class TestSession(unittest.TestCase):
    def test_round_trip(self):
        app = make_app()
        with tempfile.TemporaryDirectory() as d:
            path = save_session(Path(d) / "s", collect_state(app, "test"))
            self.assertEqual(path.suffix, ".plibs")
            state = load_session(path)
        new = SimpleNamespace(spectra=[], template_lines=[], session_temperature=None, session_ne=None,
                              options=SimpleNamespace(kt_low=0.5, instrumental_width=0.5, libs_db_file="D:/LIBS.db",
                                                      input_dir="D:/"), response=None)
        apply_state(new, state, Spec, TemplateLine, Resp)
        self.assertEqual(new.spectra[0].x, [1.0, 2.0, 3.0])
        self.assertTrue(math.isnan(new.spectra[0].y[1]))
        self.assertEqual(new.spectra[0].color, "#123456")
        t = new.template_lines[0]
        self.assertIsInstance(t, TemplateLine)
        self.assertEqual((t.aki, t.gk, t.error_inte), (-1.47, 4, 12.3))      # exclusion kept (negative Aki)
        self.assertEqual((t.sa_use, t.sa_sac, t.sa_sac_rel), (True, 1.37, 0.08))
        self.assertEqual((new.session_temperature, new.session_ne, new.apply_sac_correction), (0.85, 6e16, False))
        self.assertEqual(new.irsac_algorithm, "IRSAC2")
        self.assertIn("results_snapshot", state)
        self.assertFalse(new.session_result_validity["restored_as_authoritative"])
        self.assertEqual((new.options.kt_low, new.options.instrumental_width), (0.6, 0.37))
        self.assertEqual(new.options.libs_db_file, "D:/LIBS.db")             # paths are never overwritten
        self.assertEqual(new.response.y, [0.5, 0.7])
        self.assertIn("1 excluded", summary(state))

    def test_historical_algorithm_selection_is_migrated_to_irsac2(self):
        app = SimpleNamespace(
            spectra=[],
            template_lines=[],
            options=SimpleNamespace(),
            apply_sac_correction=True,
            irsac_algorithm="IRSAC1",
        )
        state = {
            "spectra": [],
            "template": [],
            "session": {"irsac_algorithm": "IRSAC1"},
            "options": {},
        }

        apply_state(app, state, Spec, TemplateLine)

        self.assertEqual(app.irsac_algorithm, "IRSAC2")
        self.assertFalse(app.apply_sac_correction)

    def test_rejects_other_files(self):
        import gzip
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.plibs"
            with gzip.open(p, "wt") as fh:
                fh.write('{"magic": "something else"}')
            with self.assertRaises(ValueError):
                load_session(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
