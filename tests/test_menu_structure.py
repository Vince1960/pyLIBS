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
            "show_spectrum_offset", "show_baseline_removal", "smooth_main_spectrum", "convert_nm_to_angstrom",
            "load_template_from_menu", "show_template_manager", "template_info_from_menu",
            "close_template_from_menu", "show_batch_statistics", "show_statistics",
            "show_goto_dialog", "find_peaks_basic", "show_trace_lines",
            "show_retro_fit_manager", "show_auto_fit_manager", "show_ne_halpha",
            "show_saha_boltzmann", "show_sac_check", "show_sac_window",
            "show_self_absorption",
            "show_cf_libs", "show_theoretical_spectrum", "show_standard_correction",
            "show_manual", "show_about",
        }
        owner = SimpleNamespace(
            view_grid_x=True,
            view_grid_y=True,
            view_log_x=False,
            view_log_y=False,
            actions=[],
            bound_events={},
            bind_counts={},
        )
        for name in command_names:
            setattr(owner, name, lambda *args, _name=name, **kwargs: owner.actions.append(_name))
        owner.focus_get = lambda: None
        def bind(sequence, callback):
            owner.bind_counts[sequence] = owner.bind_counts.get(sequence, 0) + 1
            owner.bound_events[sequence] = callback
        owner.bind = bind
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
        processing = cascade(utilities, "Signal Processing")
        self.assertIn("Baseline Removal...", labels(processing, "command"))
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
        self.assertIn(
            "Self-absorption compensation...",
            labels(plasma, "command"),
        )
        self.assertIn("SAC Factors...", labels(plasma, "command"))
        self.assertNotIn("Self-Absorption / IRSAC...", labels(plasma, "command"))
        self.assertNotIn("Self-Absorption IRSAC2...", labels(plasma, "command"))
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

    def test_batch_layout_aligns_baseline_button_with_multifit(self):
        class Widget:
            def __init__(self, x=0, width=0):
                self.x = x
                self.width = width
                self.configured_width = None

            def winfo_rootx(self):
                return self.x

            def winfo_width(self):
                return self.width

            def configure(self, **kwargs):
                self.configured_width = kwargs["width"]

        window = SimpleNamespace(
            multifit_button=Widget(150),
            baseline_correction_button=Widget(80),
            time_resolved_spacer=Widget(width=10),
            update_idletasks=lambda: None,
            winfo_rootx=lambda: 50,
            winfo_reqwidth=lambda: 900,
            winfo_reqheight=lambda: 500,
            minsize=lambda width, height: setattr(window, "minimum", (width, height)),
        )
        pyLIBS.BatchStatisticsWindow._fit_batch_layout(window)
        self.assertEqual(window.time_resolved_spacer.configured_width, 80)
        self.assertEqual(window.minimum, (900, 500))

    def test_signal_processing_and_following_shortcuts_bind_exact_commands(self):
        owner = self.build_menu()
        expected = {
            "<Control-F2>": ("Ctrl+F2", "Intensity Offset...", "show_spectrum_offset"),
            "<Control-F3>": ("Ctrl+F3", "Smooth Spectrum", "smooth_main_spectrum"),
            "<Control-F4>": ("Ctrl+F4", "Baseline Removal...", "show_baseline_removal"),
            "<Control-F5>": ("Ctrl+F5", "Convert nm to Å", "convert_nm_to_angstrom"),
            "<Control-F6>": ("Ctrl+F6", "Import Lines for Current Analysis...", "load_template_from_menu"),
            "<Control-F7>": ("Ctrl+F7", "Main Analytical-Line Library...", "show_template_manager"),
            "<Control-F8>": ("Ctrl+F8", "Selected-Line Summary", "template_info_from_menu"),
        }
        shortcuts = {
            item["event"]: item
            for item in owner.menu_shortcuts
            if item.get("event") in expected
        }
        self.assertEqual(set(shortcuts), set(expected))
        utilities = cascade(owner.root_menu, "Utilities")
        menu_entries = []
        for submenu_name in ("Signal Processing", "Analytical Line Lists"):
            menu_entries.extend(cascade(utilities, submenu_name).entries)
        displayed = {
            entry["label"]: entry["accelerator"]
            for entry in menu_entries
            if entry.get("type") == "command" and entry.get("accelerator")
        }
        for sequence, (accelerator, label, action) in expected.items():
            with self.subTest(sequence=sequence):
                item = shortcuts[sequence]
                self.assertEqual((item["accelerator"], item["label"]), (accelerator, label))
                self.assertEqual(displayed[label], accelerator)
                self.assertEqual(owner.bind_counts[sequence], 1)
                owner.bound_events[sequence]()
                self.assertEqual(owner.actions[-1], action)


if __name__ == "__main__":
    unittest.main()
