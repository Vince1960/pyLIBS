"""Generic formatting and safe conversion helpers for pyLIBS."""

import math


def safe_float(value, default=0.0):
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(float(str(value).strip().replace(",", ".")))
    except Exception:
        return default


def format_template_display_value(value):
    """Format Template-window display values without changing stored data."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return ""
        try:
            number = float(text.replace(",", "."))
        except Exception:
            return value
    else:
        try:
            number = float(value)
        except Exception:
            return value
    if not math.isfinite(number):
        return str(value)
    return f"{number:.3f}".rstrip("0").rstrip(".")
