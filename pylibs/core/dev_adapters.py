"""Adapters from pyLIBS 1.2.1 state into the Brazilian diagnostic APIs.

Imports of the application module are deferred until a diagnostic is opened to
avoid a startup import cycle.
"""

from __future__ import annotations

import math
import time

from pylibs.utils.formatting import safe_float, safe_int


def _app_api():
    import pyLIBS
    return pyLIBS


def saha_points(app, elements=None):
    from pylibs.core.plasma_fit import SBPoint
    api = _app_api()
    groups, skipped = api.libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
    offset = math.log(6.04e21 / 1.0e17)
    points = []
    for element, rows in groups.items():
        if elements and element not in elements:
            continue
        for row in rows:
            if row.get("inactive"):
                continue
            line = row["line"]
            ion = safe_int(row.get("ion", getattr(line, "ion", 1)), 1)
            ek = safe_float(getattr(line, "ek", 0.0), 0.0) * 1.23985e-4
            eion = row["x"] - ek if ion == 2 else 0.0
            y = api._sac_corrected_fit_y(app, row) + (offset if ion == 2 else 0.0)
            points.append(SBPoint(element, ion, ek, eion, y,
                                  f"{element} {api._roman_ion(ion)} {row.get('center', 0.0):.2f}"))
    return points, skipped


def outlier_points(app):
    from pylibs.core.plasma_fit import SBPoint
    api = _app_api()
    groups, _ = api.libspp_saha_boltzmann_groups(app, 1.0e17, 1.0)
    offset = math.log(6.04e21 / 1.0e17)
    points, lines, active, centers = [], [], [], []
    for element, rows in sorted(groups.items()):
        for row in rows:
            line = row["line"]
            ion = safe_int(row.get("ion", getattr(line, "ion", 1)), 1)
            ek = safe_float(getattr(line, "ek", 0.0), 0.0) * 1.23985e-4
            eion = row["x"] - ek if ion == 2 else 0.0
            y = api._sac_corrected_fit_y(app, row) + (offset if ion == 2 else 0.0)
            center = safe_float(row.get("center", 0.0), 0.0)
            points.append(SBPoint(element, ion, ek, eion, y,
                                  f"{element} {api._roman_ion(ion)} {center:.2f}"))
            lines.append(line)
            active.append(not row.get("inactive"))
            centers.append(center)
    return points, lines, active, centers


def alternatives(app, center, tol, element, ion, limit=6):
    try:
        app.libs_db.connect()
        candidates = app.libs_db.search_lines(center, tol, table="Datalibs", limit=60)
    except Exception:
        return []
    present = {str(getattr(line, "specie", "")).strip().capitalize()
               for line in app.template_lines if getattr(line, "specie", "")}
    rows = []
    for candidate in candidates:
        el, stage = str(candidate.specie).strip().capitalize(), safe_int(candidate.ion, 0)
        if el == element and stage == ion and abs(candidate.wavelen - center) < 0.05:
            continue
        rows.append((el in present, el, stage, candidate.wavelen, safe_float(candidate.inte, 0.0)))
    rows.sort(key=lambda row: (not row[0], abs(row[3] - center), -row[4]))
    return rows[:limit]


def mc_inputs(app, sig_int_default=0.05, sig_ga_default=0.10, code_map=None, collect=None):
    from pylibs.core.cflibs_uncertainty import CFInputs, MCPoint, ZTable
    api = _app_api()
    groups, _ = api.libspp_boltzmann_groups_with_skips(app)
    out, all_elements = {}, set()
    for key, rows in groups.items():
        current = []
        for row in rows:
            line = row["line"]
            excluded = bool(row.get("inactive"))
            if excluded and collect is None:
                continue
            inte = api._template_line_intensity(line)
            err = safe_float(getattr(line, "error_inte", 0.0), 0.0)
            s_int = err / inte if err > 0 and inte > 0 and math.isfinite(err) else sig_int_default
            code = safe_int(getattr(line, "acc", 0), 0)
            s_ga = (code_map or {}).get(code, sig_ga_default)
            sac = safe_float(getattr(line, "sa_sac_rel", 0.0), 0.0) if app.apply_sac_correction else 0.0
            wl = safe_float(getattr(line, "asswavelen", 0.0), 0.0) or safe_float(getattr(line, "wavelen", 0.0), 0.0)
            point = MCPoint(row["x"], api._sac_corrected_fit_y(app, row), s_int, s_ga, sac,
                            f"{key[0]} {api._roman_ion(key[1])} {wl:.2f}")
            if collect is not None:
                collect.append((key, point, line, not excluded))
                all_elements.add(key[0])
            if not excluded:
                current.append(point)
        if current:
            out[key] = current
    db = app.libs_db
    db.connect()
    mass, eion, tables = {}, {}, {}
    for element in sorted({key[0] for key in out} | all_elements):
        try:
            meta = db.element_metadata(element)
        except Exception:
            meta = {}
        mass[element] = safe_float(meta.get("m_atomica"), 1.0) or 1.0
        eion[element] = safe_float(meta.get("en_ion"), 0.0) * 0.000123985
        for stage in (1, 2):
            try:
                rows = db.conn.execute(
                    "SELECT temperature, partfunct FROM partfunctPay "
                    "WHERE TRIM(element)=? AND ion=? ORDER BY temperature",
                    (element, stage),
                ).fetchall()
                tables[(element, stage)] = [(float(r[0]), float(r[1])) for r in rows]
            except Exception:
                tables[(element, stage)] = []
    return CFInputs(out, mass, eion, ZTable(tables))


def outlier_cf_data(app, lines):
    collect = []
    inputs = mc_inputs(app, collect=collect)
    by_id = {id(line): (key, point) for key, point, line, _active in collect}
    cf = [by_id.get(id(line)) for line in lines]
    kt = ne = None
    source = "session"
    window = getattr(app, "cflibs_window", None)
    try:
        if window is not None and window.winfo_exists() and window.last_kt:
            kt, ne, source = float(window.last_kt), float(window.last_ne), "CF-LIBS window"
    except Exception:
        pass
    return (cf, inputs, kt or getattr(app, "session_temperature", None) or 1.0,
            ne or getattr(app, "session_ne", None) or 1.0e17, source)


def self_absorption_lines(app):
    from pylibs.core.self_absorption_irsac2 import SALine
    api = _app_api()
    result = []
    for line in app.template_lines:
        if api._template_line_has_fit_error(line):
            continue
        element = str(getattr(line, "specie", "") or "").strip().capitalize()
        ion = safe_int(getattr(line, "ion", 0), 0)
        aki = safe_float(getattr(line, "aki", 0.0), 0.0)
        gk = safe_float(getattr(line, "gk", 0.0), 0.0)
        ek = safe_float(getattr(line, "ek", 0.0), 0.0)
        ei = safe_float(getattr(line, "ei", 0.0), 0.0)
        wavelength = api._template_line_nist_wavelength(line)
        center = abs(safe_float(getattr(line, "fitwavelen", 0.0), 0.0)) or wavelength
        intensity = api._template_line_intensity(line)
        if not element or ion not in (1, 2) or aki <= 0 or gk <= 0 or ek <= 0 or intensity <= 0 or wavelength <= 0:
            continue
        if not api._aki_passes_threshold(app, aki):
            continue
        corrected = intensity / api._response_factor(app, center)
        ordinate = api._boltzmann_ordinate(app, corrected, wavelength, aki, gk)
        factor = 1.0 if api._wavelength_unit_is_angstrom(app) else 10.0
        row = SALine(id(line), element, ion, wavelength * factor, ei * 1.23985e-4,
                     ek * 1.23985e-4, abs(aki * gk), math.exp(ordinate) * abs(aki * gk),
                     abs(safe_float(getattr(line, "wl", 0.0), 0.0)) * factor,
                     abs(safe_float(getattr(line, "wg", 0.0), 0.0)) * factor,
                     f"{element} {api._roman_ion(ion)} {wavelength:.2f}")
        err = safe_float(getattr(line, "error_inte", 0.0), 0.0)
        row.rel_int_err = err / intensity if err > 0 and math.isfinite(err) else None
        row.template_line = line
        result.append(row)
    return result


def mean_kt(app, ne, kt0, elements=None):
    api = _app_api()
    kt = kt0 if kt0 > 0 else 1.0
    for _ in range(50):
        groups, _ = api.libspp_saha_boltzmann_groups(app, ne, kt)
        if elements:
            groups = {element: rows for element, rows in groups.items() if element in elements}
        fits = api.libspp_fit_saha_boltzmann(app, groups)
        updated = api.libspp_weighted_temperature(fits, app.options.kt_low, app.options.kt_high)
        if updated <= 0:
            updated = api.libspp_weighted_temperature(fits, 0.0, float("inf"))
        if updated <= 0:
            return None
        if abs(updated - kt) / updated <= 1e-5:
            return updated
        kt = updated
    return kt


def halpha_ne(app, kt):
    result = getattr(app, "last_halpha_result", None) or {}
    width = safe_float(result.get("corrected_width", result.get("width", 0.0)), 0.0)
    if width <= 0:
        return None
    return _app_api().libspp_halpha_ne(width, kt)


def compare_irsac(app, dialog):
    """Run IRSAC1 and IRSAC2 on the same current fitted-line observations."""
    from pylibs.core.cflibs_uncertainty import cflibs_concentrations
    from pylibs.core.self_absorption import hybrid_self_absorption
    from pylibs.core.self_absorption_irsac2 import assess as assess_irsac2, chosen_sac

    api = _app_api()
    observations = api._self_absorption_observations(app)
    lines = list(dialog.lines_provider(app))
    if not observations or not lines:
        raise ValueError("Both IRSAC methods require assigned lines with fitted intensities.")
    kt = safe_float(getattr(app, "session_temperature", 0.0), 0.0) or dialog._num("kt")
    ne = safe_float(getattr(app, "session_ne", 0.0), 0.0) or dialog._num("ne")
    temperature_k = kt * 11604.518

    t0 = time.perf_counter()
    original = hybrid_self_absorption(
        observations, temperature_k, mode="irsac",
        thermometric_key=api._saha_thermometric_key(app, observations),
        reference_wavelengths=api._active_irsac_reference_lines(app, observations),
        equation_mode="staged",
        max_iterations=max(1, safe_int(getattr(app.options, "irsac_iterations", 100), 100)),
        relative_tolerance=max(1.0e-9, safe_float(getattr(app.options, "irsac_tolerance", 0.001), 0.001)),
    )
    seconds1 = time.perf_counter() - t0
    factors1 = {key: corr.multiplier for key, corr in original.corrections.items()}

    try:
        params = dict(dialog.params)
    except Exception:
        params = {}
    params = {
        "kt_sigma": safe_float(params.get("kt_sigma"), 0.0),
        "ne_rel": safe_float(params.get("ne_rel"), 0.15),
        "inst_fwhm": safe_float(params.get("inst_fwhm"), 0.0),
        "inst_lorentz": safe_float(params.get("inst_lorentz"), 0.0),
        "resolve_ratio": safe_float(params.get("resolve_ratio"), 0.2),
        "sigma_y": safe_float(params.get("sigma_y"), 0.1),
        "references": dialog._references(),
        "nsig": safe_float(params.get("nsig"), 2.0),
        "ref_absorption": bool(params.get("ref_absorption", True)),
        "max_sac": safe_float(params.get("max_sac"), 1.0 / 0.3),
    }
    t0 = time.perf_counter()
    result2 = assess_irsac2(lines, None, kt, ne, **params)
    seconds2 = time.perf_counter() - t0
    factors2 = {}
    for result in result2:
        factor, _method = chosen_sac(result, "irsac")
        if factor is not None and result.line.template_line is not None:
            factors2[id(result.line.template_line)] = factor

    collect = []
    inputs = mc_inputs(app, collect=collect)
    point_for_line = {id(line): point for _key, point, line, active in collect if active}
    def composition(factors):
        y_values = {}
        for key, points in inputs.groups.items():
            values = []
            by_point = {id(point): line for _k, point, line, active in collect if active and _k == key}
            for point in points:
                line = by_point.get(id(point))
                factor = factors.get(id(line), 1.0) if line is not None else 1.0
                values.append(point.y + math.log(factor) if factor > 0.0 else point.y)
            y_values[key] = values
        result = cflibs_concentrations(inputs, kt, ne, ys=y_values)
        return {element: (row[0], row[1]) for element, row in result.items()}

    composition1, composition2 = composition(factors1), composition(factors2)
    labels = {id(line): line.label for line in lines}
    return {
        "irsac1_seconds": seconds1, "irsac2_seconds": seconds2,
        "irsac1_converged": original.converged, "irsac1_iterations": original.iterations,
        "irsac1_temperature_k": original.temperature_k, "irsac1_rmse": original.rmse,
        "irsac2_method": "per-species internal-reference fit at fixed input kT; no iterative temperature solver",
        "irsac1_factors": factors1, "irsac2_factors": factors2,
        "line_labels": labels, "composition1": composition1, "composition2": composition2,
    }
