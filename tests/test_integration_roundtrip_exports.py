"""Regression coverage for session adapters and tabular exports."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pyLIBS
from pylibs.core.instrument_response import InstrumentResponseLibrary, ResponseCurve
from pylibs.gui.plot_export import write_csv, write_xlsx
from pylibs.io.session_io import apply_state, collect_state


class IntegrationRoundTripTests(unittest.TestCase):
    def test_session_preserves_nested_spectrum_source_and_response_library(self):
        source = pyLIBS.SpectrumSourceWindow(
            x=(390.0, 391.0), y=(2.0, 3.0), name="original", filename="/machine/raw.asc",
            dark_corrected=True, dark_source="dark.asc", signal_column=2, dark_columns=(3,),
            raw_x=(389.9, 390.9), calibration_intercept=0.1, calibration_slope=1.001,
            calibration_model="linear", calibration_rms=0.02, replicate_files=("rep1.asc",),
        )
        spectrum = pyLIBS.Spectrum([390.1, 391.1], [4.0, 5.0], "sample", "sample.asc",
                                   source_windows=(source,))
        app = SimpleNamespace(
            spectra=[spectrum], template_lines=[], options=SimpleNamespace(kt_low=0.6),
            response=ResponseCurve([390, 391], [0.8, 0.9], "resp.asc", 0.04),
            response_library=InstrumentResponseLibrary([
                ResponseCurve([390, 391], [0.7, 0.95], "lib.asc", 0.05)
            ]),
            session_temperature=0.7, session_ne=1e17, apply_sac_correction=True,
        )
        state = collect_state(app, "1.2.1")
        restored = SimpleNamespace(spectra=[], template_lines=[], options=SimpleNamespace(kt_low=0.5))
        apply_state(restored, state, pyLIBS.Spectrum, pyLIBS.TemplateLine,
                    ResponseCurve, pyLIBS.SpectrumSourceWindow)
        out = restored.spectra[0]
        self.assertEqual(out.source_windows[0].raw_x, (389.9, 390.9))
        self.assertEqual(out.source_windows[0].dark_columns, (3,))
        self.assertEqual(restored.response.lsf_fwhm, 0.04)
        self.assertEqual(restored.response_library.curves[0].filename, "lib.asc")
        self.assertFalse(restored.apply_sac_correction)

    def test_csv_and_xlsx_writers_emit_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "results.csv"
            xlsx_path = Path(directory) / "results.xlsx"
            write_csv(csv_path, ["Element", "Value"], [["Fe", 1.25]])
            write_xlsx(xlsx_path, {"results": (["Element", "Value"], [["Fe", 1.25]])})
            self.assertIn("Fe,1.25", csv_path.read_text(encoding="utf-8"))
            from openpyxl import load_workbook
            workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
            sheet = workbook["results"]
            self.assertEqual(tuple(cell.value for cell in sheet[2]), ("Fe", 1.25))
            workbook.close()


if __name__ == "__main__":
    unittest.main()
