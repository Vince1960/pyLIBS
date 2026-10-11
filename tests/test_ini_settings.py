import configparser
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyLIBS import AppOptions, apply_pending_scientific_settings
from pylibs.io.ini import load_pylibs_ini, save_pylibs_ini


class IniScientificSettingsTests(unittest.TestCase):
    def test_pending_scientific_settings_override_stale_open_instance_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "pending.json"
            ranges = '{"Cd:1:326.105480":[325.95,326.26]}'
            pending.write_text(
                json.dumps({
                    "delta_min": "0.5",
                    "voigt_baseline_mode": "origin_constant",
                    "voigt_fit_ranges": ranges,
                    "irsac_reference_lines": '{"Cd I":340.36521}',
                    "irsac_equation_mode": "excel_worksheet",
                    "cflibs_intercept_mode": "excel_free",
                    "cflibs_ionization_mode": "saha",
                    "cflibs_neutral_fractions": "",
                }),
                encoding="utf-8",
            )
            options = AppOptions()
            options.delta_min = 1.0
            options.voigt_fit_ranges = "{}"

            applied = apply_pending_scientific_settings(
                options,
                pending,
                persist=False,
                consume=True,
            )

            self.assertTrue(applied)
            self.assertEqual(options.delta_min, 0.5)
            self.assertEqual(options.voigt_fit_ranges, ranges)
            self.assertFalse(pending.exists())

    def test_missing_new_sections_keep_safe_scientific_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini_path = Path(tmp) / "pyLIBS.ini"
            ini_path.write_text(
                "[General]\nusername=test\ninput_dir=\n"
                "[SelfAbsorption]\nirsac_mode=irsac\n",
                encoding="utf-8",
            )
            options = AppOptions()
            with patch(
                "pylibs.io.ini.resource_path",
                side_effect=lambda filename: Path(tmp) / filename,
            ):
                self.assertTrue(load_pylibs_ini(options))

            self.assertEqual(options.irsac_thermometric_species, "")
            self.assertEqual(options.irsac_equation_mode, "staged")
            self.assertEqual(options.cflibs_intercept_mode, "fixed_temperature")
            self.assertEqual(options.cflibs_ionization_mode, "saha")
            self.assertEqual(options.voigt_baseline_mode, "local_linear")
            self.assertEqual(options.voigt_fit_ranges, "{}")
            self.assertEqual(options.voigt_fit_range_sources, "{}")
            self.assertEqual(options.delta_min, 0.5)
            self.assertEqual(options.cflibs_neutral_fractions, "")
            self.assertTrue(options.strict_quantitation)
            self.assertEqual(options.quality_min_temperature_lines, 4)
            self.assertEqual(options.quality_min_energy_span_ev, 1.5)
            self.assertEqual(options.quality_min_composition_lines, 3)
            self.assertEqual(
                options.quality_max_composition_loo_relative_change,
                0.20,
            )
            self.assertEqual(options.quality_max_replicate_composition_cv, 0.15)
            self.assertTrue(options.quality_require_replicate_composition)
            self.assertFalse(options.remember_ne_for_series)
            self.assertEqual(options.boltzmann_intensity_mode, "energy")

    def test_save_persists_irsac_and_cflibs_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            options = AppOptions()
            with patch(
                "pylibs.io.ini.resource_path",
                side_effect=lambda filename: Path(tmp) / filename,
            ):
                path = save_pylibs_ini(options)

            parser = configparser.ConfigParser(interpolation=None)
            parser.read(path, encoding="utf-8")
            self.assertEqual(
                parser.get("SelfAbsorption", "irsac_equation_mode"),
                "staged",
            )
            self.assertEqual(
                parser.get("CFLIBS", "cflibs_intercept_mode"),
                "fixed_temperature",
            )
            self.assertEqual(
                parser.get("CFLIBS", "cflibs_ionization_mode"),
                "saha",
            )
            self.assertEqual(parser.get("CFLIBS", "cflibs_neutral_fractions"), "")
            self.assertTrue(parser.getboolean("CFLIBS", "strict_quantitation"))
            self.assertEqual(
                parser.getint("CFLIBS", "quality_min_temperature_lines"),
                4,
            )
            self.assertEqual(
                parser.getfloat("CFLIBS", "quality_min_halpha_r2"),
                0.90,
            )
            self.assertEqual(
                parser.getfloat("CFLIBS", "quality_max_ne_relative_uncertainty"),
                0.20,
            )
            self.assertEqual(
                parser.getint("CFLIBS", "quality_min_composition_lines"),
                3,
            )
            self.assertEqual(
                parser.getfloat(
                    "CFLIBS",
                    "quality_max_composition_loo_relative_change",
                ),
                0.20,
            )
            self.assertEqual(
                parser.getfloat(
                    "CFLIBS",
                    "quality_max_replicate_composition_cv",
                ),
                0.15,
            )
            self.assertTrue(
                parser.getboolean(
                    "CFLIBS",
                    "quality_require_replicate_composition",
                )
            )
            self.assertEqual(
                parser.get("Fit", "voigt_baseline_mode"),
                "local_linear",
            )
            self.assertEqual(parser.get("Fit", "voigt_fit_ranges"), "{}")
            self.assertFalse(
                parser.getboolean("HAlpha", "remember_ne_for_series")
            )
            self.assertEqual(
                parser.get("Boltzmann", "boltzmann_intensity_mode"),
                "energy",
            )


if __name__ == "__main__":
    unittest.main()
