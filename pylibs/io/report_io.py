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
    if abs(ne - 1.0e17) <= 1.0:
        return "default"
    return "user input"


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
    return {
        "Response normalization used": "Yes" if already_corrected or owner.last_response_used else "No",
        "Normalization mode": mode,
        "Response file": str(getattr(opts, "response_file", "") or "N/A"),
        "Correction convention": "divide by response",
        "CF-LIBS intensity correction state": cf_state,
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
    return [
        ["Temperature used", f"{_fmt(owner.last_kt)} eV"],
        ["Temperature source", owner.last_temperature_source],
        ["Electron density used", f"{_fmt(owner.last_ne)} e/cm3"],
        ["Electron density source", owner.last_ne_source],
    ]


def result_rows(rows):
    return [
        [
            r.get("element", ""),
            _fmt3(r.get("ionized_neutral_ratio")),
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
        ["H-alpha Gaussian width", _fmt(result.get("gaussian_width"))],
        ["H-alpha intensity", _fmt(result.get("intensity"))],
        ["H-alpha integral", _fmt(result.get("integral"))],
        ["Electron density from H-alpha", f"{_fmt(result.get('ne'))} e/cm3"],
    ]
    return html_table(["Field", "Value"], rows)


def saha_section_html(owner):
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    low, high = saha.get("temperature_range", ("N/A", "N/A"))
    rows = [
        ["Allowed temperature range", f"{_fmt(low)} - {_fmt(high)} eV"],
        ["Mean temperature", f"{_fmt(saha.get('mean_temperature'))} eV"],
        ["Selected representative temperature mode", saha.get("representative_mode", "default value")],
        ["Selected element", saha.get("selected_element") or "N/A"],
        ["Representative temperature used for CF-LIBS", f"{_fmt(owner.last_kt)} eV"],
    ]
    return html_table(["Field", "Value"], rows) + html_table(
        ["Element", "Temperature (eV)", "Valid lines", "Included in mean"],
        saha_rows(owner),
    )


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
     "gi", "Assigned wavelength", "Template intensity", "Intensity error", "Accuracy"],
    template_rows(owner),
)}

<h2>Hydrogen Stark broadening</h2>
{halpha_section_html(owner)}

<h2>Saha-Boltzmann temperatures</h2>
{saha_section_html(owner)}

<h2>Plasma parameters used for CF-LIBS</h2>
{html_table(["Parameter", "Value"], plasma_parameter_rows(owner))}

<h2>CF-LIBS results</h2>
<p>Skipped/incomplete template lines: {html.escape(str(owner.last_skipped))}</p>
{html_table(["Element", "Ionized / Neutral ratio", "Number %", "Mass %"], result_rows(rows))}
<p class="muted">Atomic masses are read from LIBS.db table Elementi, field m_atomica. Incomplete template lines are skipped before concentration calculation.</p>
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
    data.append("Index\tWavelength\tSpecies\tFitted center\tFitted intensity\tLorentzian width\tGaussian width\tIntegral\tAki\tgki\tEk\tEi\tgi\tAssigned wavelength\tTemplate intensity\tIntensity error\tAccuracy")
    for row in template_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Hydrogen Stark broadening"])
    halpha = getattr(owner.master_app, "last_halpha_result", None) or {}
    if halpha and halpha.get("available"):
        for key in ("center", "corrected_lorentzian_width", "lorentzian_width", "gaussian_width", "intensity", "integral", "ne"):
            data.append(f"{key}: {_fmt(halpha.get(key))}")
    else:
        data.append("Not available")
    data.extend(["", "Saha-Boltzmann temperatures"])
    saha = getattr(owner.master_app, "last_saha_boltzmann", None) or {}
    low, high = saha.get("temperature_range", ("N/A", "N/A"))
    data.append(f"Allowed temperature range: {_fmt(low)} - {_fmt(high)} eV")
    data.append(f"Mean temperature: {_fmt(saha.get('mean_temperature'))} eV")
    data.append(f"Selected representative temperature mode: {saha.get('representative_mode', 'default value')}")
    data.append(f"Representative temperature used for CF-LIBS: {_fmt(owner.last_kt)} eV")
    data.append("Element\tTemperature (eV)\tValid lines\tIncluded in mean")
    for row in saha_rows(owner):
        data.append("\t".join(str(v) for v in row))
    data.extend(["", "Plasma parameters used for CF-LIBS"])
    for row in plasma_parameter_rows(owner):
        data.append(f"{row[0]}: {row[1]}")
    data.extend(["", "CF-LIBS results"])
    data.append(f"Skipped/incomplete template lines: {owner.last_skipped}")
    data.append("Element\tIonized / Neutral ratio\tNumber %\tMass %")
    for row in result_rows(rows):
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
    return bool(getattr(app, "fit_values_already_response_corrected", False))


def _roman_ion(ion: int) -> str:
    return "I" if ion == 1 else "II" if ion == 2 else str(ion)


def _template_line_intensity(line):
    return line.inte if getattr(line, "inte", 0.0) > 0.0 else getattr(line, "templint", 0.0)
