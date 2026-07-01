"""pyLIBS.ini loading and saving helpers."""

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

# Legacy pyLIBS.ini files may still contain the removed positional slot.
# Skip that value so the remaining parameters keep their original alignment.
_LEGACY_SHOW_PROGRESS_INDEX = 29


WINDOW_POSITION_SECTION = "WindowPositions"
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


def load_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Load pyLIBS.ini using the same positional layout as the original libs++.ini."""
    path = resource_path(filename)
    if not path.exists():
        old = resource_path("libs++.ini")
        if old.exists():
            path = old
        else:
            return False
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
    _values, _comments, window_positions = _read_pylibs_ini(path)
    return window_positions


def save_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Save pyLIBS.ini in legacy positional format, with English comments."""
    comments = [
        "Username", "Limit Low", "Limit High", "Ha Lines", "Ha Range",
        "First wavelength", "Second wavelength", "First width", "Second width",
        "KappaT", "Thresh.", "Delta min.", "Range", "Apply normalization",
        "Apply before", "Apply after", "Normalization", "Echelle", "Single file",
        "Instr. width", "Fix wg", "Fixed wg", "Fix wl", "Fixed wl", "Aki thres.",
        "Ne low", "Ne high", "kT low", "kT high", "Fix wavel.",
        "Convert to A", "Iterations", "Auto Offset", "Auto Shift", "Main",
        "Template", "Fit", "CF", "Options", "Ident", "InDir",
        "GridX", "GridY", "LogX", "LogY", "BackgroundColor",
    ]
    def fmt(v):
        if isinstance(v, bool):
            return "1" if v else "0"
        return str(v)
    lines = []
    # Persist the last working directory under the legacy InDir slot.
    if hasattr(options, "input_directory") and not getattr(options, "input_dir", ""):
        options.input_dir = getattr(options, "input_directory", "")
    for i, (attr, typ) in enumerate(PYLIBS_INI_ORDER):
        value = getattr(options, attr, "")
        lines.append(f"{fmt(value)} // {comments[i]}")
    window_positions = getattr(options, "window_positions", {}) or {}
    if window_positions:
        lines.append("")
        lines.append(f"[{WINDOW_POSITION_SECTION}]")
        for key in WINDOW_POSITION_ORDER:
            for suffix in ("X", "Y", "W", "H"):
                full_key = f"{key}_{suffix}"
                if full_key not in window_positions:
                    continue
                value = window_positions.get(full_key, "")
                if value is None:
                    value = ""
                lines.append(f"{full_key}={value}")
        for full_key in sorted(k for k in window_positions if k.split("_", 1)[0] not in WINDOW_POSITION_ORDER):
            value = window_positions.get(full_key, "")
            if value is None:
                value = ""
            lines.append(f"{full_key}={value}")
    out = resource_path(filename)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    options.ini_file = str(out)
    return out
