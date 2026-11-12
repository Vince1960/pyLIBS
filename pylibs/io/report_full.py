"""Complete-data sections of the CF-LIBS report (pyLIBS-dev)."""

from __future__ import annotations

import base64
import html
import io
import math
import tempfile
from pathlib import Path

CM1_TO_EV = 1.23985e-4
KT_TO_K = 11604.45


# ------------------------------------------------------------------------------------------ helpers
def _alive(win) -> bool:
    try:
        return win is not None and bool(win.winfo_exists())
    except Exception:
        return False


def _num(v, digits=6):
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(f):
        return str(f)
    if f == 0:
        return "0"
    return f"{f:.{digits}g}"


def fig_to_b64(fig, dpi=110) -> str:
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


class Section:
    def __init__(self, sid, title, intro=""):
        self.sid, self.title, self.intro = sid, title, intro
        self.blocks = []          # ("table", name, headers, rows) | ("img", b64, caption) | ("note", text)

    def table(self, name, headers, rows):
        self.blocks.append(("table", name, list(headers), [list(r) for r in rows]))

    def img(self, b64, caption=""):
        if b64:
            self.blocks.append(("img", b64, caption))

    def note(self, text):
        self.blocks.append(("note", text))


# ------------------------------------------------------------------------------------------ sections
def _sec_credits(app):
    from pylibs.utils import constants as K
    s = Section("credits", "Software, credits and session")
    rows = [
        ["Program", f"{getattr(K, 'APP_DEV_NAME', 'pyLIBS')} {getattr(K, 'APP_DEV_VERSION', '')}"],
        ["Based on", f"pyLIBS {K.APP_VERSION} — {getattr(K, 'ORIGINAL_COPYRIGHT', '')}"],
        ["Original authors", f"{getattr(K, 'ORIGINAL_AUTHOR', '')}, {getattr(K, 'ORIGINAL_LAB', '')}"],
        ["Citation", f"DOI {getattr(K, 'ORIGINAL_DOI', '')}"],
        ["Licence", getattr(K, "LICENSE_NAME", "")],
        ["Modified by", f"{getattr(K, 'MOD_AUTHORS', '')} ({getattr(K, 'MOD_YEAR', '')})"],
        ["Session file", getattr(app, "session_file", "") or "not saved as a session"],
    ]
    s.table("credits", ["Field", "Value"], rows)
    return s


def _sec_options(app):
    s = Section("options", "Analysis options")
    opts = getattr(app, "options", None)
    rows = []
    if opts is not None:
        for k, v in sorted(vars(opts).items()):
            if k.startswith("_") or k == "window_positions":
                continue
            rows.append([k, _num(v) if not isinstance(v, str) else v])
    def _sig(v):
        return _num(v[1]) if isinstance(v, (list, tuple)) and len(v) == 2 else _num(v)
    rows += [["session kT (eV)", _num(getattr(app, "session_temperature", None))],
             ["session σ kT (eV)", _sig(getattr(app, "session_temperature_sigma", None))],
             ["session kT source", getattr(app, "session_temperature_source", "") or ""],
             ["session Ne (cm-3)", _num(getattr(app, "session_ne", None))],
             ["session σ Ne (cm-3)", _sig(getattr(app, "session_ne_sigma", None))],
             ["session Ne source", getattr(app, "session_ne_source", "") or ""],
             ["self-absorption correction applied", "yes" if getattr(app, "apply_sac_correction", False) else "no"]]
    s.table("options", ["Option", "Value"], rows)
    return s


def _sec_lines(app):
    s = Section("lines", "All template lines (status, atomic data, fit, self-absorption)")
    rows = []
    for i, t in enumerate(getattr(app, "template_lines", []) or [], start=1):
        aki = getattr(t, "aki", 0.0) or 0.0
        try:
            aki = float(aki)
        except (TypeError, ValueError):
            aki = 0.0
        gk = getattr(t, "gk", 0) or 0
        rows.append([
            i, f"{getattr(t, 'specie', '')} {'I' * int(getattr(t, 'ion', 0) or 0)}".strip(),
            _num(getattr(t, "asswavelen", "")), _num(getattr(t, "fitwavelen", "")),
            "excluded" if aki < 0 else ("active" if aki > 0 else "no Aki"),
            _num(getattr(t, "ei", 0) and float(getattr(t, "ei", 0)) * CM1_TO_EV),
            _num(getattr(t, "ek", 0) and float(getattr(t, "ek", 0)) * CM1_TO_EV),
            _num(getattr(t, "gi", "")), _num(gk), _num(abs(aki)), _num(abs(aki) * float(gk or 0)),
            _num(getattr(t, "acc", "")), _num(getattr(t, "inte", "")), _num(getattr(t, "error_inte", "")),
            _num(getattr(t, "wl", "")), _num(getattr(t, "wg", "")),
            _num(getattr(t, "sa_value", "")), _num(getattr(t, "sa_sac", "")),
            "yes" if getattr(t, "sa_use", False) else "no", _num(getattr(t, "sa_sac_rel", "")),
        ])
    s.note("Energies in eV (LIBS.db stores cm⁻¹; ×1.23985×10⁻⁴). A_ki in the LIBS.db unit (10⁸ s⁻¹). "
           "Excluded lines have negative A_ki in the template (Shift-click / Outliers window).")
    s.table("lines", ["#", "Species", "λ assigned (Å)", "λ fitted (Å)", "Status", "Ei (eV)", "Ek (eV)", "gi", "gk",
                      "Aki", "gA", "acc", "Integral", "σ integral", "Lorentz w (Å)", "Gauss w (Å)",
                      "SA", "SAC", "SAC used", "σ SAC (rel)"], rows)
    return s


def _tables_from(provider):
    try:
        return provider()
    except Exception:
        return None


def _sec_saha(app):
    s = Section("saha", "Saha-Boltzmann plot — all points and fits")
    win = getattr(app, "saha_window", None)
    if not _alive(win) or not getattr(win, "saha_groups", None):
        s.note("The Saha-Boltzmann window is not open/computed: open Analyse → Saha Boltzmann plot and generate "
               "the report again to include its points, fits and plot.")
        return s
    if getattr(win, "fig", None) is not None:
        s.img(fig_to_b64(win.fig), "Saha-Boltzmann plot as shown in the program")
    tabs = _tables_from(win.export_tables) or {}
    for key, title in (("fits", "saha_fits"), ("points", "saha_points"), ("info", "saha_info")):
        if key in tabs:
            h, rows = tabs[key]
            s.table(title, h, [[_num(c) if not isinstance(c, str) else c for c in r] for r in rows])
    return s


def _sec_cflibs(owner):
    s = Section("cflibs", "CF-LIBS Boltzmann plots at fixed kT — all points, intercepts and results")
    if getattr(owner, "fig", None) is not None:
        s.img(fig_to_b64(owner.fig), "CF-LIBS plot as shown in the program")
    tabs = _tables_from(owner.export_tables) or {}
    for key, title in (("fits", "cflibs_fits"), ("points", "cflibs_points"), ("results", "cflibs_results"),
                       ("info", "cflibs_info")):
        if key in tabs:
            h, rows = tabs[key]
            s.table(title, h, [[_num(c) if not isinstance(c, str) else c for c in r] for r in rows])
    return s


def _sec_atomic(owner):
    app = owner.master_app
    s = Section("atomic", "Atomic data used (per element, at the CF-LIBS temperature)")
    kt = float(getattr(owner, "last_kt", 0) or 0)
    T = kt * KT_TO_K
    rows = []
    for r in getattr(owner, "last_rows", []) or []:
        el = r.get("element", "")
        try:
            meta = app.libs_db.element_metadata(el)
        except Exception:
            meta = {}
        try:
            z1 = app.libs_db.partition_function(el, 1, T)
            z2 = app.libs_db.partition_function(el, 2, T)
        except Exception:
            z1 = z2 = None
        eion = meta.get("en_ion")
        try:
            eion_ev = float(eion) * CM1_TO_EV
        except (TypeError, ValueError):
            eion_ev = None
        rows.append([el, _num(meta.get("m_atomica", r.get("atomic_mass"))), _num(eion), _num(eion_ev),
                     _num(z1), _num(z2), _num(r.get("ionized_neutral_ratio"))])
    s.note(f"T = {kt:.5g} eV = {T:.6g} K. Partition functions from LIBS.db table partfunctPay (linear "
           "interpolation in T); masses and ionization energies from table Elementi.")
    s.table("atomic_data", ["Element", "Atomic mass (u)", "E_ion (cm-1)", "E_ion (eV)", "Z_I(T)", "Z_II(T)",
                            "N_II / N_I"], rows)
    return s


def _sec_mc(owner):
    app = owner.master_app
    s = Section("mc_full", "Monte Carlo — complete statistics (molar and mass %)")
    r = getattr(app, "last_cflibs_uncertainty", None)
    try:
        ok = r is not None and abs(r.params["kt"] - float(owner.last_kt)) <= 1e-4 * r.params["kt"] and \
            abs(r.params["ne"] - float(owner.last_ne)) <= 1e-4 * r.params["ne"]
    except Exception:
        ok = False
    if not ok:
        s.note("Monte Carlo not computed for these kT / Ne (CF-LIBS → Uncertainty (MC)).")
        return s
    from pylibs.core.cflibs_uncertainty import STAT_KEYS, STAT_NAMES, fmt_pm, stat_value
    p = r.params
    s.table("mc_parameters", ["Parameter", "Value"], [
        ["draws N (valid / failed)", f"{r.n_draws} / {r.failed}"], ["sources", ", ".join(r.sources)],
        ["kT ± σ (eV)", f"{_num(p.get('kt'))} ± {_num(p.get('sig_kt'))}"],
        ["Ne (cm-3), σ rel", f"{_num(p.get('ne'))}, {_num(p.get('sig_ne_rel'))}"],
        ["σ intensity default / σ gA", f"{p.get('s_int')} / {p.get('s_ga')}"],
        ["σ gA per accuracy code", p.get("code_map") or "—"],
        ["intercepts", "weighted" if p.get("weighted") else "plain mean (as pyLIBS)"],
        ["bootstrap replicates for s.e.", str(p.get("n_boot", 0))]])
    order = sorted(r.nominal, key=lambda el: -r.nominal[el][0])
    for unit, stats, col in (("molar", r.number, 0), ("mass", r.mass, 1)):
        rows = []
        for el in order:
            st = stats[el]
            rows.append([el, _num(r.nominal[el][col])] +
                        [fmt_pm(stat_value(st, k), getattr(st, "se", {}).get(k)) for k in STAT_KEYS] +
                        [_num(100 * st.sd / st.mean if st.mean else None, 4), _num(st.bandwidth, 4)])
        s.table(f"mc_{unit}", ["Element", f"CF-LIBS nominal ({unit} %)"] + [STAT_NAMES[k] for k in STAT_KEYS] +
                ["σ rel (%)", "KDE bandwidth"], rows)
    for unit, bud in (("molar", r.budget_number), ("mass", r.budget_mass)):
        if bud:
            rows = [[el] + [_num(bud.get(src, {}).get(el), 3) for src in r.sources] +
                    [_num(math.sqrt(sum((bud.get(src, {}).get(el) or 0) ** 2 for src in r.sources)), 3),
                     _num((r.number if unit == "molar" else r.mass)[el].sd, 3)] for el in order]
            s.table(f"mc_budget_{unit}", ["Element"] + list(r.sources) + ["quadrature", "total MC"], rows)
    s.note("± after each statistic = Monte Carlo standard error (bootstrap); σ and the intervals are the "
           "uncertainty of the concentration. Error budget: σ of the concentration with one source at a time.")
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from pylibs.gui.uncertainty_dialog import draw_distribution
        for el in order:
            for mass in (False, True):
                fig = Figure(figsize=(7.2, 4.4), dpi=100)
                FigureCanvasAgg(fig)
                draw_distribution(fig, r, el, mass=mass)
                s.img(fig_to_b64(fig, 100), f"{el}: distribution of {'mass' if mass else 'molar'} %")
    except Exception:
        pass
    return s


def _sec_outliers(app):
    s = Section("outliers", "Outlier screening and influence of each line on the concentrations")
    win = getattr(app, "outlier_window", None)
    if not _alive(win) or not getattr(win, "rows", None):
        s.note("The Outliers window is not open: open it (Analyse → Outlier lines) and generate the report again "
               "to include the residuals and the influence of every line.")
        return s
    els = list(getattr(win, "elements", []) or [])
    rows = []
    for r in sorted(win.rows, key=lambda r: (not r.active, r.ek_ev)):
        inf = getattr(win, "influence", {}).get(r.index)
        d = [(_num(inf.total.get(el, (0, 0))[0], 3) if inf else "") for el in els]
        rows.append([r.label, "active" if r.active else "excluded", _num(r.ek_ev, 4), _num(r.residual, 3),
                     _num(r.z, 3), _num(r.dkt, 3), f"#{r.order}" if r.order else ""] + d)
    s.note(f"Global Saha-Boltzmann fit: kT = {win.base.kt:.5g} eV, Ne = {win.base.ne:.4g} cm-3, robust σ = "
           f"{win.scale:.4g}. Δ = change of the molar % if the line is excluded (active) or restored (excluded), "
           "including the kT/Ne shift." if getattr(win, "base", None) else "")
    s.table("outliers_influence", ["Line", "Status", "Ek (eV)", "deleted residual", "z", "ΔkT if toggled (eV)",
                                   "suggested"] + [f"Δ{el} (molar %)" for el in els], rows)
    if getattr(win, "fig", None) is not None:
        s.img(fig_to_b64(win.fig), "Outlier window plot (as currently selected)")
    return s


def _sec_new_diagnostics(app):
    s = Section("diagnostics", "Plasma diagnostics and self-absorption method comparison")
    lte = getattr(app, "lte_window", None)
    if _alive(lte) and getattr(lte, "results", None):
        rows = []
        for r in lte.results:
            rows.append([getattr(getattr(r, "gaps", None), "label", ""),
                         _num(getattr(r, "de_used_ev", None)),
                         _num(getattr(r, "ne_min", None)),
                         _num(getattr(r, "ratio", None)),
                         getattr(r, "mcwhirter_ok", None), getattr(r, "temporal_ok", None),
                         getattr(r, "spatial_ok", None), _num(getattr(r, "ratio_worst", None))])
        s.table("lte_criteria", ["Species", "ΔE used (eV)", "Ne minimum", "Ne/Ne minimum",
                                  "McWhirter", "Temporal", "Spatial", "Worst case"], rows)
    else:
        s.note("LTE criteria have not been calculated in this session.")

    fit = getattr(app, "last_selfconsistent", None)
    if isinstance(fit, dict):
        try:
            f = fit.get("fit")
            if f is not None:
                s.table("self_consistent_fit", ["Parameter", "Value"], [
                    ["kT (eV)", _num(getattr(f, "kt", None))], ["σ kT (eV)", _num(getattr(f, "sigma_kt", None))],
                    ["Ne (cm-3)", _num(getattr(f, "ne", None))], ["σ Ne (cm-3)", _num(getattr(f, "sigma_ne", None))],
                    ["RMS", _num(getattr(f, "rms", None))], ["converged/applied", _num(fit.get("applied"))],
                ])
        except Exception:
            s.note("A self-consistent fit result is available but could not be rendered.")
    else:
        s.note("No self-consistent T–Ne fit has been applied.")

    sa2 = getattr(app, "last_irsac2_result", None)
    if isinstance(sa2, dict):
        results = sa2.get("results", [])
        rows = []
        for r in results:
            line = getattr(r, "line", None)
            rows.append([getattr(line, "label", ""), _num(getattr(r, "stark_sac", None)),
                         _num(getattr(r, "irsac_sa", None)), _num(getattr(r, "irsac_sac", None)),
                         getattr(r, "irsac_status", ""), getattr(r, "level_test", "")])
        s.note("Applied correction algorithm: IRSAC2.")
        s.table("irsac2_lines", ["Line", "Stark SAC", "IRSAC SA", "IRSAC SAC", "IRSAC status", "Same-level test"], rows)
    return s


def collect_sections(owner):
    app = owner.master_app
    secs = []
    for fn, arg in ((_sec_credits, app), (_sec_options, app), (_sec_lines, app), (_sec_saha, app),
                    (_sec_cflibs, owner), (_sec_atomic, owner), (_sec_mc, owner), (_sec_outliers, app)):
        try:
            secs.append(fn(arg))
        except Exception as e:  # noqa: BLE001
            sec = Section(fn.__name__, fn.__name__.replace("_sec_", "").title())
            sec.note(f"Not available: {e}")
            secs.append(sec)
    try:
        secs.append(_sec_new_diagnostics(app))
    except Exception as e:  # noqa: BLE001
        sec = Section("diagnostics", "Plasma diagnostics and self-absorption")
        sec.note(f"Not available: {e}")
        secs.append(sec)
    return secs


# ------------------------------------------------------------------------------------------ renderers
def xlsx_data_uri(sections) -> str:
    try:
        from pylibs.gui.plot_export import write_xlsx
    except Exception:
        return ""
    tables = {}
    for s in sections:
        for b in s.blocks:
            if b[0] == "table" and b[3]:
                name = b[1][:31]
                tables[name] = (b[2], b[3])
    if not tables:
        return ""
    try:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "report_data.xlsx"
            write_xlsx(p, tables)
            data = p.read_bytes()
        return ("data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"
                + base64.b64encode(data).decode("ascii"))
    except Exception:
        return ""


def _html_table(headers, rows):
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    if rows:
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    else:
        body = f'<tr><td colspan="{len(headers)}">Not available</td></tr>'
    return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_html(sections) -> str:
    out = []
    for s in sections:
        out.append(f'<h2 id="{s.sid}">{html.escape(s.title)}</h2>')
        if s.intro:
            out.append(f"<p>{html.escape(s.intro)}</p>")
        for b in s.blocks:
            if b[0] == "table":
                out.append(f'<p class="tname">{html.escape(b[1])}</p>' + _html_table(b[2], b[3]))
            elif b[0] == "img":
                out.append(f'<figure><img src="data:image/png;base64,{b[1]}" alt="{html.escape(b[2])}">'
                           f"<figcaption>{html.escape(b[2])}</figcaption></figure>")
            elif b[0] == "note" and b[1]:
                out.append(f'<p class="muted">{html.escape(b[1])}</p>')
    return "\n".join(out)


def render_text(sections) -> list:
    lines = []
    for s in sections:
        lines += ["", s.title.upper()]
        for b in s.blocks:
            if b[0] == "table":
                lines.append(f"[{b[1]}]")
                lines.append("\t".join(str(h) for h in b[2]))
                lines += ["\t".join(str(c) for c in r) for r in b[3]]
            elif b[0] == "note" and b[1]:
                lines.append(b[1])
            elif b[0] == "img":
                lines.append(f"(figure in the HTML report: {b[2]})")
    return lines


def toc_html(sections, extra=()) -> str:
    items = [f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t in extra]
    items += [f'<a href="#{s.sid}">{html.escape(s.title)}</a>' for s in sections]
    return '<nav class="toc"><b>Contents</b><br>' + " · ".join(items) + "</nav>"
