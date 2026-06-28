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
    ("show_progress", bool),
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


def load_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Load pyLIBS.ini using the same positional layout as the original libs++.ini."""
    path = resource_path(filename)
    if not path.exists():
        old = resource_path("libs++.ini")
        if old.exists():
            path = old
        else:
            return False
    values = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        clean = parse_legacy_ini_value(line)
        values.append(clean)
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
    options.ini_file = str(path)
    return True


def save_pylibs_ini(options, filename: str = "pyLIBS.ini"):
    """Save pyLIBS.ini in legacy positional format, with English comments."""
    comments = [
        "Username", "Limit Low", "Limit High", "Ha Lines", "Ha Range",
        "First wavelength", "Second wavelength", "First width", "Second width",
        "KappaT", "Thresh.", "Delta min.", "Range", "Apply normalization",
        "Apply before", "Apply after", "Normalization", "Echelle", "Single file",
        "Instr. width", "Fix wg", "Fixed wg", "Fix wl", "Fixed wl", "Aki thres.",
        "Ne low", "Ne high", "kT low", "kT high", "Show progress", "Fix wavel.",
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
    out = resource_path(filename)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    options.ini_file = str(out)
    return out
