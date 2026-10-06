import unittest

from pyLIBS import (
    _DARK_SUBTRACTION_LABELS,
    _SELF_ABSORPTION_MODE_LABELS,
    _VOIGT_BASELINE_LABELS,
    _option_key_from_label,
)


class ProfessionalOptionLabelTests(unittest.TestCase):
    def test_legacy_keys_round_trip_from_professional_labels(self):
        mappings = (
            (_DARK_SUBTRACTION_LABELS, "auto_columns"),
            (_VOIGT_BASELINE_LABELS, "local_linear"),
            (_SELF_ABSORPTION_MODE_LABELS, "palleschi"),
        )
        for labels, key in mappings:
            with self.subTest(key=key):
                self.assertEqual(_option_key_from_label(labels, key, key), key)
                self.assertEqual(
                    _option_key_from_label(labels, labels[key], key),
                    key,
                )

    def test_self_absorption_labels_do_not_expose_person_names(self):
        visible_text = " ".join(_SELF_ABSORPTION_MODE_LABELS.values()).casefold()
        self.assertNotIn("palleschi", visible_text)

    def test_raw_internal_tokens_are_not_used_as_visible_labels(self):
        for labels in (
            _DARK_SUBTRACTION_LABELS,
            _VOIGT_BASELINE_LABELS,
            _SELF_ABSORPTION_MODE_LABELS,
        ):
            for key, label in labels.items():
                with self.subTest(key=key):
                    self.assertNotEqual(key.casefold(), label.casefold())


if __name__ == "__main__":
    unittest.main()
