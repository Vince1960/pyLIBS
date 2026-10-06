import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pyLIBS


class FakeVariable:
    def __init__(self, value=False, **_kwargs):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeMenu:
    def __init__(self, parent=None, **_kwargs):
        self.parent = parent
        self.entries = []

    def add_command(self, **kwargs):
        self.entries.append({"type": "command", **kwargs})

    def add_checkbutton(self, **kwargs):
        self.entries.append({"type": "checkbutton", **kwargs})

    def add_cascade(self, **kwargs):
        self.entries.append({"type": "cascade", **kwargs})

    def add_separator(self):
        self.entries.append({"type": "separator"})


def cascade(menu, label):
    return next(
        entry["menu"]
        for entry in menu.entries
        if entry.get("type") == "cascade" and entry.get("label") == label
    )


def labels(menu, entry_type=None):
    return [
        entry.get("label")
        for entry in menu.entries
        if entry.get("label") is not None
        and (entry_type is None or entry.get("type") == entry_type)
    ]


class ProfessionalMenuStructureTests(unittest.TestCase):
    def build_menu(self):
        command_names = {
            "ask_open_spectrum", "compare_spectrum", "ask_import_multiple",
            "load_independent_windows", "ask_save_spectrum", "save_with_labels",
            "print_plot", "on_close", "copy_plot", "swap_spectra",
            "show_active_spectra", "clear_all_spectra", "show_options",
            "restore_factory_settings", "change_background", "toggle_grid",
            "toggle_log", "full_x", "full_y", "expand_x_50", "full_scale",
            "save_window_positions", "load_window_positions", "show_response_window",
            "apply_response_now", "show_wavelength_calibration", "show_spectrum_shift",
            "show_spectrum_offset", "smooth_main_spectrum", "convert_nm_to_angstrom",
            "load_template_from_menu", "show_template_manager", "template_info_from_menu",
            "close_template_from_menu", "show_batch_statistics", "show_statistics",
            "show_goto_dialog", "find_peaks_basic", "show_trace_lines",
            "show_retro_fit_manager", "show_auto_fit_manager", "show_ne_halpha",
            "show_saha_boltzmann", "show_sac_check", "show_sac_window",
            "show_cf_libs", "show_theoretical_spectrum", "show_standard_correction",
            "show_manual", "show_about",
        }
        owner = SimpleNamespace(
            view_grid_x=True,
            view_grid_y=True,
            view_log_x=False,
            view_log_y=False,
        )
        for name in command_names:
            setattr(owner, name, lambda *args, **kwargs: None)
        owner.bind = lambda *args, **kwargs: None
        owner.config = lambda **kwargs: setattr(owner, "root_menu", kwargs["menu"])
        with (
            patch.object(pyLIBS.tk, "Menu", FakeMenu),
            patch.object(pyLIBS.tk, "BooleanVar", FakeVariable),
            patch.object(pyLIBS, "get_menu_icon", return_value=None),
        ):
            pyLIBS.build_retro_menu(owner)
        return owner

    def test_original_top_level_menu_order_is_preserved(self):
        owner = self.build_menu()
        self.assertEqual(
            labels(owner.root_menu, "cascade"),
            ["File", "Edit", "View", "Utilities", "Analyse", "Help"],
        )

    def test_long_menus_are_grouped_by_workflow(self):
        owner = self.build_menu()
        view = cascade(owner.root_menu, "View")
        utilities = cascade(owner.root_menu, "Utilities")
        analysis = cascade(owner.root_menu, "Analyse")
        self.assertEqual(
            labels(view, "cascade"),
            ["Appearance", "Zoom and Scale", "Window Layout"],
        )
        self.assertEqual(
            labels(utilities, "cascade"),
            [
                "Instrument Calibration",
                "Signal Processing",
                "Analytical Line Lists",
                "Batch and Statistics",
            ],
        )
        self.assertEqual(
            labels(analysis, "cascade"),
            [
                "Peak and Line Detection",
                "Spectral Fitting",
                "Plasma Diagnostics",
                "Quantitative Analysis",
            ],
        )

    def test_professional_analysis_labels_replace_ambiguous_abbreviations(self):
        owner = self.build_menu()
        analysis = cascade(owner.root_menu, "Analyse")
        plasma = cascade(analysis, "Plasma Diagnostics")
        quantitative = cascade(analysis, "Quantitative Analysis")
        self.assertIn("Electron Density from Hα...", labels(plasma, "command"))
        self.assertIn("SAC Factors...", labels(plasma, "command"))
        self.assertIn("CF-LIBS...", labels(quantitative, "command"))
        self.assertNotIn("SAC", labels(plasma, "command"))
        self.assertNotIn("CF LIBS", labels(quantitative, "command"))

    def test_cascade_helper_uses_the_existing_icon_system(self):
        owner = SimpleNamespace()
        menu = FakeMenu()
        submenu = FakeMenu()
        icon = object()
        with patch.object(pyLIBS, "get_menu_icon", return_value=icon) as icon_loader:
            pyLIBS._add_menu_cascade(owner, menu, "Workflow", submenu, "fit.png")
        icon_loader.assert_called_once_with(owner, "fit.png")
        self.assertEqual(
            menu.entries,
            [{
                "type": "cascade",
                "label": "Workflow",
                "menu": submenu,
                "image": icon,
                "compound": "left",
            }],
        )


if __name__ == "__main__":
    unittest.main()
