import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from pyLIBS import (
    CFLibsOPCWindow,
    MainWindow,
    OPC_MASS_PERCENT_BASIS,
    OPC_NUMBER_PERCENT_BASIS,
    Spectrum,
    _response_factor,
    _response_paths_kind,
    opc_nominal_number_percent,
    opc_number_percent_to_nominal,
    validate_opc_nominal_number_percent,
)
from pylibs.core.boltzmann import (
    ENERGY_INTENSITY_MODE,
    PHOTON_INTENSITY_MODE,
    radiometric_line_intensity_from_ordinate,
)
from pylibs.core.instrument_response import (
    InstrumentResponseLibrary,
    ResponseCurve,
    parse_response_paths,
)


class OnePointCalibrationTests(unittest.TestCase):
    def test_mass_nominal_composition_is_converted_to_number_percent(self):
        rows = [
            {"element": "Cd", "atomic_mass": 112.414},
            {"element": "Ni", "atomic_mass": 58.6934},
            {"element": "Pb", "atomic_mass": 207.2},
        ]
        mass_percent = {"Cd": 29.72, "Ni": 15.51, "Pb": 54.77}

        converted = opc_nominal_number_percent(
            rows,
            mass_percent,
            OPC_MASS_PERCENT_BASIS,
        )

        self.assertAlmostEqual(sum(converted.values()), 100.0)
        self.assertAlmostEqual(converted["Cd"], 33.34053, places=4)
        self.assertAlmostEqual(converted["Ni"], 33.32473, places=4)
        self.assertAlmostEqual(converted["Pb"], 33.33474, places=4)

    def test_number_nominal_composition_is_not_modified(self):
        rows = [
            {"element": "Cd", "atomic_mass": 112.414},
            {"element": "Ni", "atomic_mass": 58.6934},
            {"element": "Pb", "atomic_mass": 207.2},
        ]
        number_percent = {"Cd": 20.0, "Ni": 30.0, "Pb": 50.0}

        converted = opc_nominal_number_percent(
            rows,
            number_percent,
            OPC_NUMBER_PERCENT_BASIS,
        )

        self.assertEqual(converted, number_percent)

    def test_nominal_basis_round_trip_preserves_composition(self):
        rows = [
            {"element": "Cd", "atomic_mass": 112.414},
            {"element": "Ni", "atomic_mass": 58.6934},
            {"element": "Pb", "atomic_mass": 207.2},
        ]
        number_percent = {"Cd": 33.34, "Ni": 33.32, "Pb": 33.34}

        mass_percent = opc_number_percent_to_nominal(
            rows,
            number_percent,
            OPC_MASS_PERCENT_BASIS,
        )
        restored = opc_nominal_number_percent(
            rows,
            mass_percent,
            OPC_MASS_PERCENT_BASIS,
        )

        for element, expected in number_percent.items():
            self.assertAlmostEqual(restored[element], expected, places=10)

    def test_opc_nominal_composition_must_be_complete_and_total_100_percent(self):
        rows = [
            {"element": "Cd", "number_percent": 40.0},
            {"element": "Ni", "number_percent": 60.0},
        ]

        with self.assertRaisesRegex(ValueError, "missing: Ni"):
            validate_opc_nominal_number_percent(rows, {"Cd": 100.0})
        with self.assertRaisesRegex(ValueError, "expected 100%"):
            validate_opc_nominal_number_percent(
                rows,
                {"Cd": 20.0, "Ni": 60.0},
            )

        validated = validate_opc_nominal_number_percent(
            rows,
            {"Cd": 40.0, "Ni": 60.0},
        )
        self.assertEqual(validated, {"Cd": 40.0, "Ni": 60.0})

        thirds = [
            {"element": "Cd", "number_percent": 33.0},
            {"element": "Ni", "number_percent": 33.0},
            {"element": "Pb", "number_percent": 34.0},
        ]
        rounded = validate_opc_nominal_number_percent(
            thirds,
            {"Cd": 33.0, "Ni": 33.0, "Pb": 33.0},
        )
        self.assertAlmostEqual(sum(rounded.values()), 100.0)
        self.assertAlmostEqual(rounded["Cd"], 100.0 / 3.0)

    def _window(self, intensity_mode, nominal=10.0, calculated=10.0):
        aki = 2.0
        gk = 3.0
        wavelength_nm = 500.0
        x_value = 1.5
        slope = -0.5
        intercept = 2.0
        sac = 4.0
        target_ordinate = slope * x_value + intercept
        current_corrected = radiometric_line_intensity_from_ordinate(
            target_ordinate,
            wavelength_nm,
            aki,
            gk,
            intensity_mode,
        )
        line = SimpleNamespace(
            inte=current_corrected,
            fitwavelen=500.25,
            asswavelen=wavelength_nm,
            wavelen=wavelength_nm,
            wg=0.1,
            wl=0.1,
            fit_profile="voigt",
            aki=aki,
            gk=gk,
            sa_use=True,
            sa_sac=sac,
        )
        point = {
            "line": line,
            "x": x_value,
            "icorr": current_corrected,
            "nist_wavelength": wavelength_nm,
            "wavelength_nm": wavelength_nm,
        }
        owner = SimpleNamespace(
            last_rows=[{
                "element": "Cd",
                "number_percent": calculated,
                "mass_percent": 77.0,
            }],
            last_groups={("Cd", 1): [point]},
            last_fits={("Cd", 1): {"slope": slope, "q_at_t": intercept}},
        )
        app = SimpleNamespace(
            opc_nominal_percent={"Cd": nominal},
            standard_refs={"Cd": 99.0},
            spectra=[],
            response_library=InstrumentResponseLibrary(),
            options=SimpleNamespace(
                boltzmann_intensity_mode=intensity_mode,
                apply_response=False,
                apply_before=False,
                apply_after=False,
            ),
            current_wavelength_unit_label=lambda: "nm",
        )
        window = SimpleNamespace(
            owner=owner,
            master_app=app,
            factors={"Cd": nominal / calculated},
            compute=lambda: True,
        )
        window._current_rows = lambda: owner.last_rows
        return window

    def _two_element_round_trip_window(self):
        intensity_mode = ENERGY_INTENSITY_MODE
        slope = -1.0
        intercept = 2.0
        groups = {}
        fits = {}
        rows = []
        for element, wavelength, calculated in (
            ("Cd", 400.0, 50.0),
            ("Ni", 600.0, 50.0),
        ):
            x_value = 1.0
            aki = 2.0
            gk = 3.0
            ordinate = slope * x_value + intercept
            intensity = radiometric_line_intensity_from_ordinate(
                ordinate,
                wavelength,
                aki,
                gk,
                intensity_mode,
            )
            line = SimpleNamespace(
                specie=element,
                ion=1,
                inte=intensity,
                fitwavelen=wavelength,
                asswavelen=wavelength,
                wavelen=wavelength,
                wg=0.1,
                wl=0.1,
                fit_profile="voigt",
                aki=aki,
                gk=gk,
            )
            point = {
                "line": line,
                "x": x_value,
                "y": ordinate,
                "icorr": intensity,
                "eff": 1.0,
                "nist_wavelength": wavelength,
                "wavelength_nm": wavelength,
            }
            key = (element, 1)
            groups[key] = [point]
            fits[key] = {
                "slope": slope,
                "q": intercept,
                "q_at_t": intercept,
                "points": [point],
            }
            rows.append({
                "element": element,
                "number_percent": calculated,
                "mass_percent": calculated,
                "atomic_mass": 1.0,
            })

        class DummyDatabase:
            @staticmethod
            def partition_function(_element, _ion, _temperature):
                return 1.0

            @staticmethod
            def element_metadata(_element):
                return {"m_atomica": 1.0, "en_ion": 50000.0}

        owner = SimpleNamespace(
            last_rows=rows,
            last_groups=groups,
            last_fits=fits,
            last_kt=1.0,
            last_ne=1.0e17,
        )
        app = SimpleNamespace(
            opc_nominal_percent={"Cd": 40.0, "Ni": 60.0},
            opc_nominal_basis=OPC_NUMBER_PERCENT_BASIS,
            spectra=[],
            response_library=InstrumentResponseLibrary(),
            options=SimpleNamespace(
                boltzmann_intensity_mode=intensity_mode,
                apply_response=False,
                apply_before=False,
                apply_after=False,
            ),
            libs_db=DummyDatabase(),
            apply_sac_correction=False,
            current_wavelength_unit_label=lambda: "nm",
        )
        window = SimpleNamespace(
            owner=owner,
            master_app=app,
            factors={"Cd": 0.8, "Ni": 1.2},
            compute=lambda: True,
        )
        window._current_rows = lambda: owner.last_rows
        return window

    def test_candidate_opc_must_reproduce_its_nominal_standard(self):
        window = self._two_element_round_trip_window()
        calibration_rows = CFLibsOPCWindow._calibration_rows(window)

        validation = CFLibsOPCWindow._round_trip_validation(
            window,
            calibration_rows,
        )

        self.assertTrue(validation["passed"])
        self.assertAlmostEqual(
            validation["observed_number_percent"]["Cd"],
            40.0,
            places=10,
        )
        self.assertAlmostEqual(
            validation["observed_number_percent"]["Ni"],
            60.0,
            places=10,
        )

        bad_rows = list(calibration_rows)
        wavelength, factor, element, species = bad_rows[0]
        bad_rows[0] = (wavelength, factor * 2.0, element, species)
        failed = CFLibsOPCWindow._round_trip_validation(window, bad_rows)
        self.assertFalse(failed["passed"])

    def test_identity_opc_is_one_in_both_intensity_conventions(self):
        for mode in (ENERGY_INTENSITY_MODE, PHOTON_INTENSITY_MODE):
            with self.subTest(mode=mode):
                rows = CFLibsOPCWindow._calibration_rows(self._window(mode))
                self.assertEqual(len(rows), 1)
                wavelength, factor, element, species = rows[0]
                self.assertAlmostEqual(wavelength, 500.0)
                self.assertAlmostEqual(factor, 1.0)
                self.assertEqual(element, "Cd")
                self.assertEqual(species, "Cd I")

    def test_opc_uses_nist_wavelength_and_inverse_number_ratio(self):
        rows = CFLibsOPCWindow._calibration_rows(
            self._window(ENERGY_INTENSITY_MODE, nominal=20.0, calculated=10.0)
        )
        self.assertEqual(len(rows), 1)
        wavelength, factor, _element, _species = rows[0]
        self.assertAlmostEqual(wavelength, 500.0)
        self.assertAlmostEqual(factor, 0.5)

    def test_opc_factor_ignores_mass_percent_and_standard_mass_reference(self):
        window = self._window(
            ENERGY_INTENSITY_MODE,
            nominal=30.0,
            calculated=20.0,
        )
        window.owner.last_rows[0]["mass_percent"] = 5.0
        window.master_app.standard_refs["Cd"] = 90.0

        factors = CFLibsOPCWindow._compute_factors_from_entries(window)

        self.assertAlmostEqual(factors["Cd"], 1.5)

    def test_apply_before_generation_is_rejected(self):
        window = self._window(ENERGY_INTENSITY_MODE)
        curve = ResponseCurve([400.0, 600.0], [3.0, 3.0], "physical.txt")
        window.master_app.options.apply_response = True
        window.master_app.options.apply_before = True
        window.master_app.options.apply_after = False
        window.master_app.response_library = InstrumentResponseLibrary([curve])
        window.master_app.spectra = [SimpleNamespace(response_corrected=True)]
        line = window.owner.last_groups[("Cd", 1)][0]["line"]
        line.fit_response_source = "physical.txt"
        line.fit_calibration_intercept = 0.25
        line.fit_calibration_slope = 1.0

        with self.assertRaisesRegex(ValueError, "Apply After"):
            CFLibsOPCWindow._calibration_rows(window)

    def test_apply_after_opc_contains_the_active_instrument_response(self):
        window = self._window(ENERGY_INTENSITY_MODE)
        curve = ResponseCurve([400.0, 600.0], [3.0, 3.0], "physical.txt")
        window.master_app.options.apply_response = True
        window.master_app.options.apply_before = False
        window.master_app.options.apply_after = True
        window.master_app.response_library = InstrumentResponseLibrary([curve])
        window.master_app.spectra = [SimpleNamespace(response_corrected=False)]
        window.owner.last_groups[("Cd", 1)][0]["eff"] = 3.0

        rows = CFLibsOPCWindow._calibration_rows(window)

        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0], 500.0)
        self.assertAlmostEqual(rows[0][1], 3.0)

    def test_opc_files_are_distinct_from_physical_response_files(self):
        self.assertEqual(_response_paths_kind(["standard.opc"]), "opc")
        self.assertEqual(_response_paths_kind(["305.txt", "325.txt"]), "instrument")
        self.assertEqual(_response_paths_kind(["305.txt", "standard.opc"]), "mixed")

    def test_repository_opc_file_is_loadable_as_a_response_curve(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "standard.opc"
            path.write_text(
                "# pyLIBS One Point Calibration\n"
                "400.0 2.0 Cd Cd I\n"
                "600.0 4.0 Pb Pb I\n",
                encoding="utf-8",
            )
            curve = ResponseCurve.from_ascii(str(path))
            self.assertAlmostEqual(curve.value_at(500.0), 3.0)

    def test_loading_opc_selects_apply_after_without_modifying_spectrum(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "standard.opc"
            path.write_text("400 2\n600 4\n", encoding="ascii")
            options = SimpleNamespace(
                response_files="",
                response_file="",
                apply_response=False,
                apply_before=True,
                apply_after=False,
                convert_to_angstrom=False,
                lsf_widths="{}",
            )
            spectrum = Spectrum([400.0, 500.0, 600.0], [1.0, 5.0, 1.0])
            app = SimpleNamespace(
                options=options,
                spectra=[spectrum],
                response_library=InstrumentResponseLibrary(),
                response=None,
                response_window=None,
                template_lines=[],
                theoretical_window=None,
                last_cflibs_rows=[],
                last_cflibs_quality=None,
                last_cflibs_robustness=None,
                apply_sac_correction=False,
                status_messages=[],
            )
            app.configured_response_paths = lambda: parse_response_paths(
                options.response_files or options.response_file
            )
            app.load_configured_responses = lambda silent=False: MainWindow.load_configured_responses(
                app, silent=silent
            )
            app.invalidate_cflibs_results = lambda: None
            app.status = app.status_messages.append

            original_y = list(spectrum.y)
            with patch("pyLIBS.save_pylibs_ini"), patch(
                "pyLIBS.invalidate_self_absorption_analysis"
            ):
                loaded = MainWindow.load_response_files(app, [str(path)])

            self.assertTrue(loaded)
            self.assertTrue(options.apply_response)
            self.assertFalse(options.apply_before)
            self.assertTrue(options.apply_after)
            self.assertIs(app.spectra[0], spectrum)
            self.assertEqual(app.spectra[0].y, original_y)
            self.assertFalse(app.spectra[0].response_corrected)

    def test_loading_opc_restores_raw_spectrum_and_clears_apply_before_fit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "standard.opc"
            path.write_text("400 2\n600 4\n", encoding="ascii")
            options = SimpleNamespace(
                response_files="physical.txt",
                response_file="physical.txt",
                apply_response=True,
                apply_before=True,
                apply_after=False,
                convert_to_angstrom=False,
                lsf_widths="{}",
            )
            raw_y = [1.0, 5.0, 1.0]
            spectrum = Spectrum([400.0, 500.0, 600.0], raw_y)
            spectrum.apply_response(
                ResponseCurve([400.0, 600.0], [2.0, 2.0], "physical.txt")
            )
            line = SimpleNamespace(
                inte=3.0,
                wl=0.1,
                wg=0.1,
                fitwavelen=500.0,
                error_inte=0.1,
                fit_profile="voigt",
            )
            messages = []
            app = SimpleNamespace(
                options=options,
                spectra=[spectrum],
                template_lines=[line],
                response_library=InstrumentResponseLibrary(),
                response=None,
                response_window=None,
                active_window=None,
                theoretical_window=None,
                last_cflibs_rows=[],
                last_cflibs_quality=None,
                last_cflibs_robustness=None,
                apply_sac_correction=False,
                clear_fit_artists=lambda: None,
                redraw=lambda: None,
                invalidate_cflibs_results=lambda: None,
                status=messages.append,
            )
            app.configured_response_paths = lambda: parse_response_paths(
                options.response_files or options.response_file
            )
            app.load_configured_responses = lambda silent=False: MainWindow.load_configured_responses(
                app, silent=silent
            )

            with patch("pyLIBS.save_pylibs_ini"), patch(
                "pyLIBS.invalidate_self_absorption_analysis"
            ), patch("pyLIBS._showinfo"):
                loaded = MainWindow.load_response_files(app, [str(path)])

            self.assertTrue(loaded)
            self.assertFalse(options.apply_before)
            self.assertTrue(options.apply_after)
            self.assertFalse(app.spectra[0].response_corrected)
            self.assertEqual(app.spectra[0].y, raw_y)
            self.assertIsNone(line.inte)
            self.assertIsNone(line.fitwavelen)

    def test_analytical_divisor_uses_only_instrument_response(self):
        physical = ResponseCurve([400.0, 600.0], [2.0, 2.0], "physical.txt")
        opc = ResponseCurve([400.0, 600.0], [3.0, 3.0], "standard.opc")
        app = SimpleNamespace(
            options=SimpleNamespace(
                apply_response=True,
                apply_after=True,
                apply_opc=True,
            ),
            response_library=InstrumentResponseLibrary([physical]),
            opc_response=opc,
            spectra=[],
        )
        self.assertAlmostEqual(_response_factor(app, 500.0), 2.0)
        app.options.apply_after = False
        self.assertAlmostEqual(_response_factor(app, 500.0), 1.0)


if __name__ == "__main__":
    unittest.main()
