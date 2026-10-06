"""CF-LIBS report generation and export helpers for pyLIBS."""

from __future__ import annotations

import base64
import html
import os
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional
import math

from pylibs.utils.constants import APP_VERSION
from pylibs.utils.formatting import format_template_display_value, safe_float


def _fmt(value):
    if value is None or value == "":
        return "N/A"
    try:
        number = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(number):
        return str(value)
    return f"{number:.8g}"


def _fmt3(value):
    try:
        number = float(value)
    except Exception:
        number = None
    if number is not None and math.isfinite(number) and number != 0.0 and abs(number) < 1.0e-3:
        return f"{number:.3e}"
    text = format_template_display_value(value)
    return text if text != "" else "N/A"


def _temperature_source(owner, kt):
    source = getattr(owner.master_app, "session_temperature_source", None)
    session_kt = safe_float(getattr(owner.master_app, "session_temperature", 0.0), 0.0)
    if source and session_kt and abs(session_kt - kt) <= max(abs(kt) * 1e-6, 1e-9):
        return source
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    rep = safe_float(saha.get("representative_temperature", 0.0), 0.0)
    if rep and abs(rep - kt) <= max(abs(kt) * 1e-6, 1e-9):
        mode = saha.get("representative_mode", "")
        return "selected element" if mode == "selected element" else "Saha-Boltzmann mean"
    if abs(kt - 1.0) <= 1e-9:
        return "default"
    return "manually entered"


def _ne_source(owner, ne):
    source = getattr(owner.master_app, "session_ne_source", None)
    session_ne = safe_float(getattr(owner.master_app, "session_ne", 0.0), 0.0)
    if source and session_ne and abs(session_ne - ne) <= max(abs(ne) * 1e-6, 1e-6):
        return source
    halpha = getattr(owner.master_app, "last_halpha_result", None) or {}
    h_ne = safe_float(halpha.get("ne", 0.0), 0.0)
    if h_ne and abs(h_ne - ne) <= max(abs(ne) * 1e-6, 1e-6):
        return "H-alpha"
    return "manual CF-LIBS entry"


def _finite_values(values):
    out = []
    for value in values or []:
        try:
            number = float(value)
        except Exception:
            continue
        if math.isfinite(number):
            out.append(number)
    return out


def spectrum_info(owner):
    spectra = getattr(owner.master_app, "spectra", []) or []
    sp = spectra[0] if spectra else None
    if not sp:
        return {
            "Spectrum file name": "N/A",
            "Full file path": "N/A",
            "Spectrum format / extension": "N/A",
            "Number of spectrum points": "0",
            "Wavelength range": "N/A",
            "Intensity range": "N/A",
        }
    filename = getattr(sp, "filename", "") or ""
    path = Path(filename) if filename else None
    xs = _finite_values(getattr(sp, "x", []))
    ys = _finite_values(getattr(sp, "y", []))
    return {
        "Spectrum file name": path.name if path else getattr(sp, "name", "Spectrum"),
        "Full file path": str(path) if path else "N/A",
        "Spectrum format / extension": path.suffix if path and path.suffix else "N/A",
        "Number of spectrum points": str(len(getattr(sp, "x", []) or [])),
        "Wavelength range": f"{_fmt(min(xs))} - {_fmt(max(xs))}" if xs else "N/A",
        "Intensity range": f"{_fmt(min(ys))} - {_fmt(max(ys))}" if ys else "N/A",
        "Dark correction": getattr(sp, "dark_source", "disabled") or "disabled",
        "Signal intensity column": str(getattr(sp, "signal_column", 1)),
        "Dark intensity columns": ", ".join(str(value) for value in getattr(sp, "dark_columns", ()) or ()) or "N/A",
    }


def response_info(owner):
    opts = owner.master_app.options
    apply_response = bool(getattr(opts, "apply_response", False))
    apply_before = bool(getattr(opts, "apply_before", False))
    apply_after = bool(getattr(opts, "apply_after", False))
    already_corrected = _fit_values_already_response_corrected(owner.master_app)
    if not apply_response:
        mode = "None"
    elif apply_before:
        mode = "Apply Before"
    elif apply_after:
        mode = "Apply After"
    else:
        mode = "None"
    if already_corrected:
        cf_state = "Already corrected before fitting"
    elif owner.last_response_used:
        cf_state = "Corrected during CF-LIBS analysis"
    else:
        cf_state = "Uncorrected"
    response_paths = []
    library = getattr(owner.master_app, "response_library", None)
    if library is not None:
        response_paths = list(getattr(library, "paths", []) or [])
    if not response_paths:
        legacy_path = str(getattr(opts, "response_file", "") or "").strip()
        if legacy_path:
            response_paths = [legacy_path]
    try:
        database_name = owner.master_app.libs_db.display_name()
    except Exception:
        database_name = "Unknown"
    return {
        "Response normalization used": "Yes" if already_corrected or owner.last_response_used else "No",
        "Normalization mode": mode,
        "Response file(s)": "; ".join(response_paths) or "N/A",
        "Correction convention": "divide by response",
        "Instrumental FWHM (global, reference H-alpha 656 nm)": (
            _fmt(getattr(opts, "instrumental_width", ""))
            if float(getattr(opts, "instrumental_width", 0.0) or 0.0) > 0.0
            else "Not configured; no width deconvolution"
        ),
        "CF-LIBS intensity correction state": cf_state,
        "Atomic library": database_name,
        "Atomic library file": str(getattr(opts, "libs_db_file", "") or "N/A"),
    }


def template_rows(owner):
    rows = []
    for idx, line in enumerate(getattr(owner.master_app, "template_lines", []) or [], start=1):
        rows.append([
            idx,
            _fmt3(getattr(line, "wavelen", "")),
            f"{getattr(line, 'specie', '')} {_roman_ion(getattr(line, 'ion', 0)) if getattr(line, 'ion', 0) else ''}".strip() or "N/A",
            _fmt3(getattr(line, "fitwavelen", "")),
            _fmt3(_template_line_intensity(line)),
            _fmt3(getattr(line, "wl", "")),
            _fmt3(getattr(line, "wg", "")),
            _fmt3(getattr(line, "inte", "")),
            _fmt3(getattr(line, "aki", "")),
            _fmt3(getattr(line, "gk", "")),
            _fmt3(getattr(line, "ek", "")),
            _fmt3(getattr(line, "ei", "")),
            _fmt3(getattr(line, "gi", "")),
            _fmt3(getattr(line, "asswavelen", "")),
            _fmt3(getattr(line, "templint", "")),
            _fmt3(getattr(line, "error_inte", "")),
            _fmt3(getattr(line, "acc", "")),
            str(getattr(line, "sa_method", "") or ""),
            _fmt3(getattr(line, "sa_sac", "")),
            _fmt3(getattr(line, "sa_reference", "")),
            _fmt3(getattr(line, "fit_snr", "")),
            str(getattr(line, "sa_diagnostic_status", "") or ""),
            str(getattr(line, "sa_diagnostic_reason", "") or ""),
            "Yes" if bool(getattr(line, "sa_use", False)) else "No",
        ])
    return rows


def saha_rows(owner):
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    return [
        [
            item.get("element", "N/A"),
            _fmt(item.get("temperature")),
            _fmt(item.get("nlines")),
            "Yes" if item.get("included") else "No",
        ]
        for item in saha.get("elements", []) or []
    ]


def plasma_parameter_rows(owner):
    rows = [
        ["Temperature used", f"{_fmt(owner.last_kt)} eV"],
        ["Temperature source", owner.last_temperature_source],
        ["Electron density used", f"{_fmt(owner.last_ne)} e/cm3"],
        ["Electron density source", owner.last_ne_source],
    ]
    workflow = getattr(owner.master_app, "last_self_absorption_result", None)
    if isinstance(workflow, dict):
        rows.extend([
            [
                "Self-absorption assessment",
                workflow.get("assessment_status", "Not assessed"),
            ],
            [
                "Self-absorption decision",
                workflow.get("assessment_message", ""),
            ],
            [
                "Correction applied",
                "Yes" if workflow.get("applied") else "No",
            ],
        ])
    return rows


def result_rows(rows):
    return [
        [
            r.get("element", ""),
            _fmt3(r.get("ionized_neutral_ratio")),
            _fmt3(r.get("neutral_ratio")),
            _fmt3(r.get("number_percent")),
            _fmt3(r.get("mass_percent")),
        ]
        for r in rows
    ]


def html_table(headers, rows):
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = []
    if rows:
        for row in rows:
            body.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>")
    else:
        body.append(f"<tr><td colspan=\"{len(headers)}\">Not available</td></tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def definition_table(mapping):
    return html_table(["Field", "Value"], [[k, v] for k, v in mapping.items()])


def halpha_section_html(owner):
    result = getattr(owner.master_app, "last_halpha_result", None) or {}
    if not result or not result.get("available"):
        detail = result.get("error") if result else ""
        return "<p>Not available" + (f": {html.escape(str(detail))}" if detail else "") + ".</p>"
    rows = [
        ["H-alpha fitted center", _fmt(result.get("center"))],
        ["H-alpha Lorentzian/Stark width", _fmt(result.get("corrected_lorentzian_width"))],
        ["H-alpha measured Lorentzian width", _fmt(result.get("lorentzian_width"))],
        ["H-alpha width standard error", _fmt(result.get("lorentzian_width_std"))],
        ["H-alpha Gaussian width", _fmt(result.get("gaussian_width"))],
        ["H-alpha fit R2", _fmt(result.get("r_squared"))],
        ["H-alpha peak S/N", _fmt(result.get("peak_prominence_to_noise"))],
        ["H-alpha intensity", _fmt(result.get("intensity"))],
        ["H-alpha integral", _fmt(result.get("integral"))],
        ["Electron density from H-alpha", f"{_fmt(result.get('ne'))} e/cm3"],
        ["kT used to evaluate Ne", f"{_fmt(result.get('ne_evaluation_kt'))} eV"],
        ["Relative Ne uncertainty", _fmt(result.get("ne_relative_uncertainty"))],
    ]
    return html_table(["Field", "Value"], rows)


def saha_section_html(owner):
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    low, high = saha.get("temperature_range", ("N/A", "N/A"))
    rows = [
        ["Allowed temperature range", f"{_fmt(low)} - {_fmt(high)} eV"],
        ["Boltzmann intensity convention", saha.get("intensity_mode", "energy")],
        ["Boltzmann ordinate", saha.get("ordinate_formula", "N/A")],
        ["Mean temperature", f"{_fmt(saha.get('mean_temperature'))} eV"],
        ["Selected representative temperature mode", saha.get("representative_mode", "default value")],
        ["Selected element", saha.get("selected_element") or "N/A"],
        ["Representative temperature used for CF-LIBS", f"{_fmt(owner.last_kt)} eV"],
    ]
    return html_table(["Field", "Value"], rows) + html_table(
        ["Element", "Temperature (eV)", "Valid lines", "Included in mean"],
        saha_rows(owner),
    )


def cflibs_line_audit_rows(owner):
    rows = []
    for element, audit in sorted(
        (getattr(owner, "last_line_audit", {}) or {}).items()
    ):
        rows.append([
            element,
            audit.get("active_count", 0),
            ", ".join(audit.get("active_lines", [])) or "None",
            ", ".join(audit.get("excluded_lines", [])) or "None",
            ", ".join(audit.get("omitted_lines", [])) or "None",
            audit.get("q_display", ""),
            _fmt(audit.get("q_span")),
            _fmt(audit.get("population_factor")),
            audit.get("status", "Insufficient"),
        ])
    return rows


def cflibs_line_audit_detail_rows(owner):
    rows = []
    for element, audit in sorted(
        (getattr(owner, "last_line_audit", {}) or {}).items()
    ):
        for stage in audit.get("stages", []):
            for line in stage.get("lines", []):
                rows.append([
                    element,
                    line.get("ion"),
                    _fmt(line.get("wavelength")),
                    _fmt(line.get("upper_energy_cm")),
                    _fmt(line.get("q_contribution")),
                    _fmt(line.get("q_residual")),
                    _fmt(line.get("snr")),
                ])
    return rows


def cflibs_robustness_rows(owner):
    robustness = (
        getattr(owner, "last_robustness", None)
        or getattr(owner.master_app, "last_cflibs_robustness", None)
        or {}
    )
    rows = []
    for element, item in sorted((robustness.get("elements") or {}).items()):
        rows.append([
            element,
            item.get("active_lines", 0),
            _fmt(item.get("baseline_number_percent")),
            _fmt(item.get("baseline_mass_percent")),
            _fmt(item.get("loo_number_min")),
            _fmt(item.get("loo_number_max")),
            _fmt(item.get("loo_mass_min")),
            _fmt(item.get("loo_mass_max")),
            _fmt(item.get("loo_max_relative_change")),
            item.get("loo_worst_line", ""),
            _fmt(item.get("replicate_number_cv")),
            _fmt(item.get("replicate_mass_cv")),
            _fmt(item.get("parameter_max_relative_change")),
        ])
    return rows


def cflibs_quality_rows(owner):
    quality = (
        getattr(owner, "last_quality", None)
        or getattr(owner.master_app, "last_cflibs_quality", None)
        or {}
    )
    return [
        [
            "PASS" if check.get("passed") else "FAIL",
            check.get("name", ""),
            check.get("detail", ""),
        ]
        for check in quality.get("checks", []) or []
    ]


def cflibs_quality_status(owner):
    quality = (
        getattr(owner, "last_quality", None)
        or getattr(owner.master_app, "last_cflibs_quality", None)
        or {}
    )
    return str(quality.get("status", "Not run")), list(quality.get("warnings", []) or [])


def build_cflibs_report_html(owner, rows, image_info, report_path: Optional[Path] = None):
    spectrum_info_data = spectrum_info(owner)
    response_info_data = response_info(owner)
    image_path = image_info.get("path")
    image_block = "<p>Spectrum image export failed: " + html.escape(str(image_info.get("error"))) + "</p>"
    if image_path:
        src = image_info.get("data_uri") or str(image_path)
        if report_path and not image_info.get("data_uri"):
            try:
                src = os.path.relpath(str(image_path), str(report_path.parent))
            except Exception:
                src = str(image_path)
        image_block = f"<p>PNG file: {html.escape(str(image_path))}</p><img src=\"{html.escape(src)}\" alt=\"Current spectrum plot\">"
    template_note = "pyLIBS stores the fitted line integral in the template intensity field used for CF-LIBS."
    quality_status, quality_warnings = cflibs_quality_status(owner)
    quality_warning_html = (
        "<ul>" + "".join(
            f"<li>{html.escape(str(warning))}</li>"
            for warning in quality_warnings
        ) + "</ul>"
        if quality_warnings
        else "<p>None recorded.</p>"
    )
    style = """
body { font-family: Arial, sans-serif; margin: 24px; color: #222; }
h1 { margin-bottom: 0.2em; }
h2 { margin-top: 1.5em; border-bottom: 1px solid #bbb; padding-bottom: 0.2em; }
table { border-collapse: collapse; width: 100%; margin: 0.7em 0 1.2em; font-size: 13px; }
th, td { border: 1px solid #bbb; padding: 4px 6px; text-align: left; }
th { background: #efefef; }
img { max-width: 100%; border: 1px solid #bbb; }
.muted { color: #555; }
"""
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CF-LIBS Analysis Report</title>
<style>{style}</style>
</head>
<body>
<h1>CF-LIBS Analysis Report</h1>
<p>pyLIBS version: {html.escape(APP_VERSION)}<br>
Date/time: {html.escape(datetime.now().isoformat(timespec='seconds'))}</p>

<h2>Spectrum information</h2>
{definition_table(spectrum_info_data)}

<h2>Spectrum image</h2>
{image_block}

<h2>Instrument-response normalization</h2>
{definition_table(response_info_data)}

<h2>Template contents</h2>
<p class="muted">{html.escape(template_note)}</p>
{html_table(
    ["#", "Wavelength", "Identification / species", "Fitted center", "Fitted intensity",
     "Lorentzian width", "Gaussian width", "Integral", "Aki", "gki", "Ek", "Ei",
     "gi", "Assigned wavelength", "Template intensity", "Intensity error", "Accuracy",
     "SA method", "SA intensity factor", "IRSAC reference", "Voigt S/N",
     "Independent SA check", "SA diagnostic reason", "Use correction"],
    template_rows(owner),
)}

<h2>Hydrogen Stark broadening</h2>
{halpha_section_html(owner)}

<h2>Saha-Boltzmann temperatures</h2>
{saha_section_html(owner)}

<h2>Plasma parameters used for CF-LIBS</h2>
{html_table(["Parameter", "Value"], plasma_parameter_rows(owner))}

<h2>Quantitative quality gate</h2>
<p><strong>Status: {html.escape(quality_status)}</strong></p>
{html_table(["Check", "Criterion", "Detail"], cflibs_quality_rows(owner))}
<p class="muted">Explicit limitations that remain after the numerical checks:</p>
{quality_warning_html}

<h2>CF-LIBS results</h2>
<p>Skipped/incomplete template lines: {html.escape(str(owner.last_skipped))}</p>
{html_table(["Element", "Ionized / Neutral ratio", "Neutral fraction", "Number %", "Mass %"], result_rows(rows))}
<p class="muted">Atomic masses are read from LIBS.db table Elementi, field m_atomica. Incomplete template lines are skipped before concentration calculation.</p>

<h2>Multielement robustness</h2>
<p class="muted">LOO recomputes the complete composition after omitting each analytical line. Replicate CV uses the individually fitted Voigt areas at fixed T and Ne. T/Ne sensitivity uses the measured uncertainty intervals and does not use the nominal composition.</p>
{html_table(
    ["Element", "Lines", "Base number %", "Base mass %", "LOO number min", "LOO number max",
     "LOO mass min", "LOO mass max", "LOO max relative", "Worst omitted line",
     "Replicate number CV", "Replicate mass CV", "T/Ne max relative"],
    cflibs_robustness_rows(owner),
)}

<h2>Analytical-line audit</h2>
<p class="muted">This diagnostic reports the lines that actually determine each fixed-slope intercept. The q spread factor is exp(max(q line) - min(q line)); it is not an automatic outlier-removal rule. Stable is at most 1.5, Review is at most 3, and Poor is above 3.</p>
{html_table(
    ["Element", "Used", "Active lines", "Explicitly excluded", "Omitted", "q at T",
     "q span", "Population factor", "Check"],
    cflibs_line_audit_rows(owner),
)}
{html_table(
    ["Element", "Ion", "Wavelength (nm)", "Ek (cm-1)", "Line q",
     "q residual", "Voigt S/N"],
    cflibs_line_audit_detail_rows(owner),
)}
</body>
</html>
"""


def build_cflibs_report_text(owner, rows, image_info):
    data = [
        "CF-LIBS Analysis Report",
        f"pyLIBS version: {APP_VERSION}",
        f"Date/time: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Spectrum information",
    ]
    for key, value in spectrum_info(owner).items():
        data.append(f"{key}: {value}")
    data.extend(["", "Spectrum image"])
    if image_info.get("path"):
        data.append(f"PNG file: {image_info['path']}")
    else:
        data.append(f"PNG export failed: {image_info.get('error')}")
    data.extend(["", "Instrument-response normalization"])
    for key, value in response_info(owner).items():
        data.append(f"{key}: {value}")
    data.extend(["", "Template contents"])
    data.append("Index\tWavelength\tSpecies\tFitted center\tFitted intensity\tLorentzian width\tGaussian width\tIntegral\tAki\tgki\tEk\tEi\tgi\tAssigned wavelength\tTemplate intensity\tIntensity error\tAccuracy\tSA method\tSA intensity factor\tIRSAC reference\tVoigt S/N\tIndependent SA check\tSA diagnostic reason\tUse correction")
    for row in template_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Hydrogen Stark broadening"])
    halpha = getattr(owner.master_app, "last_halpha_result", None) or {}
    if halpha and halpha.get("available"):
        for key in (
            "center", "corrected_lorentzian_width", "lorentzian_width",
            "lorentzian_width_std", "gaussian_width", "r_squared",
            "peak_prominence_to_noise", "intensity", "integral", "ne",
            "ne_evaluation_kt", "ne_relative_uncertainty",
        ):
            data.append(f"{key}: {_fmt(halpha.get(key))}")
    else:
        data.append("Not available")
    data.extend(["", "Saha-Boltzmann temperatures"])
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    low, high = saha.get("temperature_range", ("N/A", "N/A"))
    data.append(f"Allowed temperature range: {_fmt(low)} - {_fmt(high)} eV")
    data.append(f"Boltzmann intensity convention: {saha.get('intensity_mode', 'energy')}")
    data.append(f"Boltzmann ordinate: {saha.get('ordinate_formula', 'N/A')}")
    data.append(f"Mean temperature: {_fmt(saha.get('mean_temperature'))} eV")
    data.append(f"Selected representative temperature mode: {saha.get('representative_mode', 'default value')}")
    data.append(f"Representative temperature used for CF-LIBS: {_fmt(owner.last_kt)} eV")
    data.append("Element\tTemperature (eV)\tValid lines\tIncluded in mean")
    for row in saha_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Plasma parameters used for CF-LIBS"])
    for row in plasma_parameter_rows(owner):
        data.append(f"{row[0]}: {row[1]}")
    quality_status, quality_warnings = cflibs_quality_status(owner)
    data.extend(["", "Quantitative quality gate", f"Status: {quality_status}"])
    data.append("Check\tCriterion\tDetail")
    for row in cflibs_quality_rows(owner):
        data.append("\t".join(str(value) for value in row))
    if quality_warnings:
        data.append("Explicit limitations:")
        data.extend(f"- {warning}" for warning in quality_warnings)
    data.extend(["", "CF-LIBS results"])
    data.append(f"Skipped/incomplete template lines: {owner.last_skipped}")
    data.append("Element\tIonized / Neutral ratio\tNeutral fraction\tNumber %\tMass %")
    for row in result_rows(rows):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Multielement robustness"])
    data.append(
        "Element\tLines\tBase number %\tBase mass %\tLOO number min\t"
        "LOO number max\tLOO mass min\tLOO mass max\tLOO max relative\t"
        "Worst omitted line\tReplicate number CV\tReplicate mass CV\t"
        "T/Ne max relative"
    )
    for row in cflibs_robustness_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Analytical-line audit"])
    data.append(
        "Element\tUsed\tActive lines\tExplicitly excluded\tOmitted\t"
        "q at T\tq span\tPopulation factor\tCheck"
    )
    for row in cflibs_line_audit_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.append("")
    data.append(
        "Element\tIon\tWavelength (nm)\tEk (cm-1)\tLine q\t"
        "q residual\tVoigt S/N"
    )
    for row in cflibs_line_audit_detail_rows(owner):
        data.append("\t".join(str(v) for v in row))
    return "\n".join(data) + "\n"


def ensure_report_temp_dir(owner) -> Path:
    if owner.report_temp_dir:
        path = Path(owner.report_temp_dir)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            pass
    path = Path(tempfile.mkdtemp(prefix="pylibs_cflibs_report_"))
    owner.report_temp_dir = str(path)
    return path


def report_temp_path(owner, filename: str) -> Path:
    return ensure_report_temp_dir(owner) / filename


def export_spectrum_png(owner, image_path: Path):
    try:
        if not getattr(owner.master_app, "fig", None):
            return {"path": None, "error": "Main spectrum plot is not available."}
        owner.master_app.fig.savefig(str(image_path), dpi=150)
        data_uri = None
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            data_uri = f"data:image/png;base64,{encoded}"
        except Exception:
            data_uri = None
        return {"path": image_path, "data_uri": data_uri, "error": None}
    except Exception as e:
        return {"path": None, "data_uri": None, "error": str(e)}


def write_temp_cflibs_report(owner, rows):
    report_path = report_temp_path(owner, "cflibs_report.html")
    image_path = report_temp_path(owner, "cflibs_report_spectrum.png")
    image_info = export_spectrum_png(owner, image_path)
    content = build_cflibs_report_html(owner, rows, image_info, report_path)
    report_path.write_text(content, encoding="utf-8")
    return report_path, content


def open_file_with_default_app(path: Path):
    path = Path(path)
    if os.name == "nt":
        os.startfile(str(path))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
        return
    try:
        subprocess.Popen(["xdg-open", str(path)])
        return
    except Exception:
        if webbrowser.open(path.resolve().as_uri()):
            return
        raise


def write_report_content(owner, filename: str, content: str):
    Path(filename).write_text(content, encoding="utf-8")


def _fit_values_already_response_corrected(app):
    spectra = list(getattr(app, "spectra", []) or [])
    return bool(spectra) and all(getattr(sp, "response_corrected", False) for sp in spectra)


def _roman_ion(ion: int) -> str:
    return "I" if ion == 1 else "II" if ion == 2 else str(ion)


def _template_line_intensity(line):
    return line.inte if getattr(line, "inte", 0.0) > 0.0 else getattr(line, "templint", 0.0)
