"""pyLIBS.ini loading and saving helpers."""

import configparser

from pylibs.utils.formatting import safe_float, safe_int
from pylibs.utils.paths import resource_path


PYLIBS_INI_ORDER = [
    ("username", str),
    ("limit_low", float),
    ("limit_high", float),
    ("ha_lines", int),
    ("ha_range", float),
    ("ha_wl1", float),
    ("ha_wl2", float),
    ("ha_dl1", float),
    ("ha_dl2", float),
    ("ha_kt", float),
    ("threshold", float),
    ("delta_min", float),
    ("search_range", float),
    ("apply_response", bool),
    ("apply_before", bool),
    ("apply_after", bool),
    ("response_file", str),
    ("echelle", bool),
    ("single_file_path", str),
    ("instrumental_width", float),
    ("fix_wg", bool),
    ("fixed_wg", float),
    ("fix_wl", bool),
    ("fixed_wl", float),
    ("aki_threshold", float),
    ("ne_low", float),
    ("ne_high", float),
    ("kt_low", float),
    ("kt_high", float),
    ("fix_wavelength", bool),
    ("convert_to_angstrom", bool),
    ("iterations", int),
    ("auto_offset", bool),
    ("auto_shift", float),
    ("main_geometry", str),
    ("template_geometry", str),
    ("fit_geometry", str),
    ("cf_geometry", str),
    ("options_geometry", str),
    ("ident_geometry", str),
    ("input_dir", str),
    ("view_grid_x", bool),
    ("view_grid_y", bool),
    ("view_log_x", bool),
    ("view_log_y", bool),
    ("background_color", str),
]

PYLIBS_INI_SECTIONED_ORDER = [
    ("General", ("username", "input_dir")),
    ("Limits", ("limit_low", "limit_high", "threshold", "delta_min", "search_range")),
    ("HAlpha", ("ha_lines", "ha_range", "ha_wl1", "ha_wl2", "ha_dl1", "ha_dl2", "ha_kt")),
    ("Response", ("apply_response", "apply_before", "apply_after", "response_file")),
    ("Acquisition", ("echelle", "single_file_path", "instrumental_width")),
    ("Fit", ("fix_wg", "fixed_wg", "fix_wl", "fixed_wl", "aki_threshold", "ne_low", "ne_high", "kt_low", "kt_high", "fix_wavelength", "convert_to_angstrom", "iterations", "auto_offset", "auto_shift")),
    ("Windows", ("main_geometry", "template_geometry", "fit_geometry", "cf_geometry", "options_geometry", "ident_geometry")),
    ("View", ("view_grid_x", "view_grid_y", "view_log_x", "view_log_y", "background_color")),
]

# Legacy pyLIBS.ini files may still contain the removed positional slot.
# Skip that value so the remaining parameters keep their original alignment.
_LEGACY_SHOW_PROGRESS_INDEX = 29


WINDOW_POSITION_SECTION = "WindowPositions"
WINDOW_POSITION_SECTIONS = (WINDOW_POSITION_SECTION, "WindowsPositions")
WINDOW_POSITION_ORDER = [
    "Main",
    "ManualFit",
    "AutoFit",
    "Trace",
    "Template",
    "SahaBoltzmann",
    "ShowSA",
    "CFLIBS",
]


def parse_legacy_ini_value(line: str) -> str:
    return line.split("//", 1)[0].strip()


def _ini_cast(value: str, typ):
    if typ is bool:
        return bool(safe_int(value, 0))
    if typ is int:
        return safe_int(value, 0)
    if typ is float:
        return safe_float(value, 0.0)
    return value


def _is_sectioned_ini(path):
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        return stripped.startswith("[") and stripped.endswith("]")
    return False


def _read_pylibs_ini(path):
    legacy_values = []
    legacy_comments = []
    window_positions = {}
    in_window_positions = False
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_window_positions = stripped[1:-1].strip().lower() == WINDOW_POSITION_SECTION.lower()
            continue
        if in_window_positions:
            clean = parse_legacy_ini_value(raw_line)
            if "=" not in clean:
                continue
            key, value = clean.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                window_positions[key] = value
            continue
        legacy_values.append(parse_legacy_ini_value(raw_line))
        legacy_comments.append(raw_line.split("//", 1)[1].strip() if "//" in raw_line else "")
    return legacy_values, legacy_comments, window_positions


def _read_sectioned_pylibs_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    values = {}
    for section, attrs in PYLIBS_INI_SECTIONED_ORDER:
        if not parser.has_section(section):
            continue
        for attr in attrs:
            if parser.has_option(section, attr):
                values[attr] = parser.get(section, attr)
    window_positions = {}
    for section_name in WINDOW_POSITION_SECTIONS:
        if not parser.has_section(section_name):
            continue
        for key, value in parser.items(section_name):
            window_positions[key] = value
    return values, window_positions


def load_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Load pyLIBS.ini using the same positional layout as the original libs++.ini."""
    path = resource_path(filename)
    if not path.exists():
        old = resource_path("libs++.ini")
        if old.exists():
            path = old
        else:
            return False
    if _is_sectioned_ini(path):
        values, window_positions = _read_sectioned_pylibs_ini(path)
        for attr, typ in PYLIBS_INI_ORDER:
            if hasattr(options, attr) and attr in values:
                setattr(options, attr, _ini_cast(values[attr], typ))
    else:
        values, comments, window_positions = _read_pylibs_ini(path)
        legacy_index = next((i for i, comment in enumerate(comments) if comment.lower() == "show progress"), None)
        if legacy_index is not None and len(values) > legacy_index:
            values = values[:legacy_index] + values[legacy_index + 1:]
        elif len(values) == len(PYLIBS_INI_ORDER) + 1 and len(values) > _LEGACY_SHOW_PROGRESS_INDEX:
            values = values[:_LEGACY_SHOW_PROGRESS_INDEX] + values[_LEGACY_SHOW_PROGRESS_INDEX + 1:]
        for (attr, typ), value in zip(PYLIBS_INI_ORDER, values):
            if hasattr(options, attr):
                setattr(options, attr, _ini_cast(value, typ))
    # Keep old experimental name synchronized, if present in older builds.
    if hasattr(options, "input_directory") and not getattr(options, "input_dir", ""):
        options.input_dir = getattr(options, "input_directory", "")
    # v8.3 default: external database lives beside the program.
    dbp = resource_path("LIBS.db")
    if dbp.exists():
        options.libs_db_file = str(dbp)
    if hasattr(options, "window_positions"):
        options.window_positions = window_positions
    options.ini_file = str(path)
    return True


def load_window_positions(filename: str = "pyLIBS.ini"):
    """Load only the WindowPositions section from pyLIBS.ini."""
    path = resource_path(filename)
    if not path.exists():
        old = resource_path("libs++.ini")
        if old.exists():
            path = old
        else:
            return {}
    if _is_sectioned_ini(path):
        _values, window_positions = _read_sectioned_pylibs_ini(path)
    else:
        _values, _comments, window_positions = _read_pylibs_ini(path)
    return window_positions


def save_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Save pyLIBS.ini in sectioned INI format."""
    def fmt(v):
        if isinstance(v, bool):
            return "1" if v else "0"
        return str(v)
    # Persist the last working directory under the legacy InDir slot.
    if hasattr(options, "input_directory") and not getattr(options, "input_dir", ""):
        options.input_dir = getattr(options, "input_directory", "")
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    for section, attrs in PYLIBS_INI_SECTIONED_ORDER:
        parser.add_section(section)
        for attr in attrs:
            parser.set(section, attr, fmt(getattr(options, attr, "")))
    window_positions = getattr(options, "window_positions", {}) or {}
    if window_positions:
        parser.add_section(WINDOW_POSITION_SECTION)
        for key in WINDOW_POSITION_ORDER:
            for suffix in ("X", "Y", "W", "H"):
                full_key = f"{key}_{suffix}"
                if full_key not in window_positions:
                    continue
                value = window_positions.get(full_key, "")
                if value is None:
                    value = ""
                parser.set(WINDOW_POSITION_SECTION, full_key, str(value))
        for full_key in sorted(k for k in window_positions if k.split("_", 1)[0] not in WINDOW_POSITION_ORDER):
            value = window_positions.get(full_key, "")
            if value is None:
                value = ""
            parser.set(WINDOW_POSITION_SECTION, full_key, str(value))
    out = resource_path(filename)
    with out.open("w", encoding="utf-8", newline="") as fh:
        parser.write(fh, space_around_delimiters=False)
    options.ini_file = str(out)
    return out
