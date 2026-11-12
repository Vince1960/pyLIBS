"""Save / restore a complete pyLIBS-dev analysis session (*.plibs)."""

from __future__ import annotations

import dataclasses
import gzip
import json
import math
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

MAGIC = "pyLIBS session"
LEGACY_MAGIC = "pyLIBS-dev session"
FORMAT_VERSION = 2
SESSION_EXT = ".plibs"
SESSION_FILETYPES = [("pyLIBS session", "*.plibs"), ("All files", "*.*")]

SESSION_ATTRS = ("session_temperature", "session_temperature_sigma", "session_temperature_source",
                 "session_ne", "session_ne_sigma", "session_ne_source", "apply_sac_correction",
                 "last_known_ne", "last_known_ne_source", "wavelength_unit", "view_grid_x",
                 "view_grid_y", "view_log_x", "view_log_y", "plot_background", "irsac_algorithm")
# options that describe files, folders or the screen are never taken from a session
OPTION_SKIP = {"username", "response_file", "response_files", "libs_db_file", "single_file_path", "input_dir", "ini_file", "dark_file",
               "window_positions", "view_grid_x", "view_grid_y", "view_log_x", "view_log_y", "background_color"}
ANALYSIS_WINDOWS = ("saha_window", "cflibs_window")


def _plain(v):
    """JSON-friendly copy of simple values (numbers, strings, bools, lists/dicts of them); None otherwise."""
    if v is None or isinstance(v, (bool, str)):
        return v
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return _object_attrs(v)
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float):
        return v                          # NaN / inf are written as NaN / Infinity (Python json)
    try:                                   # numpy scalars
        import numpy as np
        if isinstance(v, np.generic):
            return _plain(v.item())
    except Exception:
        pass
    if isinstance(v, (list, tuple, set)):
        out = [_plain(x) for x in v]
        return [item for item in out if item is not _SKIP]
    if isinstance(v, Mapping):
        out = {str(k): _plain(x) for k, x in v.items()}
        return {key: item for key, item in out.items() if item is not _SKIP}
    return _SKIP


_SKIP = object()


def _restore_float(v):
    if isinstance(v, str) and v in ("nan", "inf", "-inf"):
        return float(v)
    return v


def _object_attrs(obj) -> dict:
    """All simple attributes of a dataclass instance (declared fields + attributes added at run time)."""
    out = {}
    for k, v in vars(obj).items():
        if k.startswith("_"):
            continue
        p = _plain(v)
        if p is not _SKIP:
            out[k] = p
    return out


def _alive(win) -> bool:
    try:
        return win is not None and bool(win.winfo_exists())
    except Exception:
        return False


# --------------------------------------------------------------------------------------------- collect
def collect_state(app, program_version: str = "") -> dict:
    st = {"magic": MAGIC, "format_version": FORMAT_VERSION, "program": program_version,
          "saved": datetime.now().isoformat(timespec="seconds")}
    st["spectra"] = [_object_attrs(sp) for sp in getattr(app, "spectra", [])]
    st["template"] = [_object_attrs(t) for t in getattr(app, "template_lines", [])]
    st["session"] = {k: _plain(getattr(app, k)) for k in SESSION_ATTRS
                     if hasattr(app, k) and _plain(getattr(app, k)) is not _SKIP}
    opts = getattr(app, "options", None)
    if opts is not None:
        st["options"] = {k: _plain(v) for k, v in vars(opts).items()
                         if k not in OPTION_SKIP and not k.startswith("_") and _plain(v) is not _SKIP}
    resp = getattr(app, "response", None)
    if resp is not None and getattr(resp, "x", None):
        st["response"] = {"x": list(resp.x), "y": list(resp.y), "filename": getattr(resp, "filename", "")}
        st["response"]["lsf_fwhm"] = getattr(resp, "lsf_fwhm", None)
    library = getattr(app, "response_library", None)
    curves = getattr(library, "curves", []) if library is not None else []
    if curves:
        st["response_library"] = [
            {"x": list(curve.x), "y": list(curve.y), "filename": curve.filename,
             "lsf_fwhm": curve.lsf_fwhm}
            for curve in curves
        ]
    try:
        ax = app.ax
        st["view"] = {"xlim": list(ax.get_xlim()), "ylim": list(ax.get_ylim())}
    except Exception:
        st["view"] = {}
    st["open_windows"] = [w for w in ANALYSIS_WINDOWS if _alive(getattr(app, w, None))]
    st["results_snapshot"] = results_snapshot(app)
    st["result_validity"] = {
        "restored_as_authoritative": False,
        "reason": "Saved result summaries are documentary; analysis is invalidated on restore and must be recomputed.",
        "cflibs": bool(getattr(app, "last_cflibs_rows", None)),
        "saha_boltzmann": bool(getattr(app, "last_saha_boltzmann", None)),
        "irsac2": bool(getattr(app, "last_irsac2_result", None)),
        "monte_carlo": getattr(app, "last_cflibs_uncertainty", None) is not None,
    }
    return st


def results_snapshot(app) -> dict:
    """Last results, stored for documentation only (they are recomputed after loading)."""
    snap = {}
    rows = getattr(app, "last_cflibs_rows", None)
    if rows:
        snap["cflibs"] = [{k: _plain(v) for k, v in r.items() if _plain(v) is not _SKIP} for r in rows]
    saha = getattr(app, "last_saha_boltzmann", None)
    if isinstance(saha, dict):
        snap["saha_boltzmann"] = _plain(saha)
    for attr in ("last_cflibs_quality", "last_cflibs_robustness", "last_halpha_result"):
        value = getattr(app, attr, None)
        if value is not None:
            snap[attr] = _plain(value)
    for attr in ("last_self_absorption_result", "last_irsac2_result"):
        value = getattr(app, attr, None)
        if isinstance(value, dict):
            snap[attr] = _plain(value)
    if getattr(app, "last_selfconsistent", None) is not None:
        snap["self_consistent"] = _plain(getattr(app, "last_selfconsistent"))
    cw = getattr(app, "cflibs_window", None)
    if _alive(cw):
        snap["cflibs_kt"] = _plain(getattr(cw, "last_kt", None))
        snap["cflibs_ne"] = _plain(getattr(cw, "last_ne", None))
    mc = getattr(app, "last_cflibs_uncertainty", None)
    if mc is not None:
        try:
            snap["monte_carlo"] = {
                "params": {k: _plain(v) for k, v in mc.params.items() if _plain(v) is not _SKIP},
                "n_draws": mc.n_draws, "sources": list(mc.sources),
                "molar": {el: {"mode": s.mode, "mean": s.mean, "median": s.p50, "sd": s.sd,
                               "hdi68": list(s.hdi68), "p2_5": s.p2_5, "p97_5": s.p97_5}
                          for el, s in mc.number.items()},
            }
            snap["monte_carlo"] = _plain(snap["monte_carlo"])
        except Exception:
            pass
    return snap


# --------------------------------------------------------------------------------------------- file I/O
def save_session(path, state: dict) -> Path:
    path = Path(path)
    if path.suffix.lower() != SESSION_EXT:
        path = path.with_suffix(SESSION_EXT)
    data = json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wb", compresslevel=6) as fh:
        fh.write(data)
    tmp.replace(path)                       # never leaves a half-written session
    return path


def load_session(path) -> dict:
    with gzip.open(path, "rb") as fh:
        state = json.loads(fh.read().decode("utf-8"))
    if state.get("magic") not in (MAGIC, LEGACY_MAGIC):
        raise ValueError("Not a supported pyLIBS session file.")
    if int(state.get("format_version", 0)) > FORMAT_VERSION:
        raise ValueError("This session was written by a newer pyLIBS-dev; please update the program.")
    return state


# --------------------------------------------------------------------------------------------- apply
def _build(cls, attrs: dict, source_window_cls=None):
    """Instance of dataclass `cls` from saved attributes (unknown fields become plain attributes)."""
    names = {f.name for f in dataclasses.fields(cls) if f.init}
    kwargs = {k: _restore_float(v) for k, v in attrs.items() if k in names}
    if source_window_cls is not None and "source_windows" in kwargs:
        kwargs["source_windows"] = tuple(
            _build(source_window_cls, item) if isinstance(item, dict) else item
            for item in kwargs["source_windows"]
        )
    obj = cls(**kwargs)
    # JSON represents tuples as arrays. Restore tuple-valued dataclass fields
    # from their declared defaults (notably source windows and metadata).
    for f in dataclasses.fields(cls):
        if not isinstance(attrs.get(f.name), list):
            continue
        default = f.default
        if default is dataclasses.MISSING and f.default_factory is not dataclasses.MISSING:
            try:
                default = f.default_factory()
            except Exception:
                default = dataclasses.MISSING
        if isinstance(default, tuple):
            try:
                object.__setattr__(obj, f.name, tuple(getattr(obj, f.name)))
            except Exception:
                pass
    for k, v in attrs.items():
        if k not in names:
            try:
                setattr(obj, k, _restore_float(v))
            except Exception:
                pass
    return obj


def apply_state(app, state: dict, spectrum_cls, template_cls, response_cls=None,
                source_window_cls=None, restore_options: bool = True):
    """Put a loaded session into the running application (data only; the caller redraws)."""
    app.spectra = [_build(spectrum_cls, d, source_window_cls) for d in state.get("spectra", [])]
    app.template_lines = [_build(template_cls, d) for d in state.get("template", [])]
    for k in SESSION_ATTRS:                 # forget the plasma parameters of the previous analysis
        if k.startswith("session_"):
            setattr(app, k, None)
    app.apply_sac_correction = False
    for k, v in state.get("session", {}).items():
        setattr(app, k, _restore_float(v))
    # Historical sessions may store a superseded algorithm selection. Results
    # are invalidated below; every recomputation uses the supported IRSAC2 path.
    app.irsac_algorithm = "IRSAC2"
    if restore_options and getattr(app, "options", None) is not None:
        for k, v in state.get("options", {}).items():
            if k in OPTION_SKIP or not hasattr(app.options, k):
                continue
            try:
                setattr(app.options, k, _restore_float(v))
            except Exception:
                pass
    resp = state.get("response")
    if response_cls is not None:
        if resp:
            try:
                app.response = response_cls(
                    resp["x"], resp["y"], resp.get("filename", ""), resp.get("lsf_fwhm")
                )
            except TypeError:
                app.response = response_cls(resp["x"], resp["y"], resp.get("filename", ""))
    library_rows = state.get("response_library")
    if library_rows is not None:
        try:
            from pylibs.core.instrument_response import InstrumentResponseLibrary, ResponseCurve
            app.response_library = InstrumentResponseLibrary([
                ResponseCurve(row["x"], row["y"], row.get("filename", ""), row.get("lsf_fwhm"))
                for row in library_rows
            ])
        except Exception:
            pass
    app.session_results_snapshot = state.get("results_snapshot", {})
    app.session_result_validity = state.get("result_validity", {})
    # Runtime scientific results depend on current data and are not trusted
    # after a session restore. Keep only the report snapshot for reference.
    for attr in ("last_cflibs_rows", "last_cflibs_quality", "last_cflibs_robustness",
                 "last_saha_boltzmann", "last_halpha_result", "last_self_absorption_result",
                 "last_irsac2_result", "last_cflibs_uncertainty", "last_selfconsistent"):
        if hasattr(app, attr):
            setattr(app, attr, None if attr not in ("last_cflibs_rows",) else [])
    app.apply_sac_correction = False
    return app


def summary(state: dict) -> str:
    sp = state.get("spectra", [])
    tl = state.get("template", [])
    excl = sum(1 for t in tl if (t.get("aki") or 0) < 0)
    ses = state.get("session", {})
    parts = [f"{len(sp)} spectrum(a)", f"{len(tl)} template line(s)" + (f" ({excl} excluded)" if excl else "")]
    if ses.get("session_temperature"):
        parts.append(f"kT = {float(ses['session_temperature']):.4g} eV")
    if ses.get("session_ne"):
        parts.append(f"Ne = {float(ses['session_ne']):.3g} cm⁻³")
    if ses.get("apply_sac_correction"):
        parts.append("SAC on")
    return ", ".join(parts)
