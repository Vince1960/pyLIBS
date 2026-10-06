import math

from pylibs.utils.formatting import format_scientific_display_value


def test_scientific_display_keeps_small_area_visible():
    assert format_scientific_display_value(6.84e-5) == "6.840000e-05"


def test_scientific_display_preserves_empty_and_non_finite_values():
    assert format_scientific_display_value(None) == ""
    assert format_scientific_display_value("") == ""
    assert format_scientific_display_value(math.nan) == "nan"
