"""CF-LIBS uncertainty window (Monte Carlo propagation, most probable values, error budget, plots)."""

from __future__ import annotations

import base64
import csv
import io
import tkinter as tk
from tkinter import filedialog, ttk

from pylibs.core.cflibs_uncertainty import STAT_KEYS, SOURCES, fmt_pm, kde_mode, monte_carlo, parse_code_map, stat_value
from pylibs.gui.helpers import _showerror, center_window
from pylibs.gui.lte_dialog import ToolbarTooltip, session_kt_sigma, session_ne_sigma

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    Figure = FigureCanvasTkAgg = None

HELP = {
    "n": "Number of Monte Carlo draws (2000 gives ~3 % precision on σ; use 5000+ for smooth distributions).",
    "kt_sig": "σ of kT (eV). Filled from the Saha-Boltzmann regression or the T–Ne fit when available.",
    "ne_rel": "Relative σ of Ne. Ne enters only through the Saha balance (ionization ratio / missing stage).",
    "s_int": "Default relative σ of the line integral when the Voigt fit gives no error (error_inte).",
    "s_ga": "Relative σ of g·A for every line (NIST accuracy classes: AA ≤ 2 %, A ≤ 3 %, B ≤ 10 %, C ≤ 25 %, D ≤ 50 %).",
    "codemap": "Optional σ of gA per LIBS.db accuracy code, e.g. '0:0.25, 1:0.03, 2:0.07, 3:0.10'. Codes not listed use\n"
               "the global σ gA. The meaning of the LIBS.db codes is not documented in pyLIBS, so set them explicitly.",
    "weighted": "Intercepts at fixed kT weighted by 1/σ²(ln I) instead of the plain mean used by pyLIBS.\n"
                "The nominal values then differ slightly from the CF-LIBS table.",
    "mode": "Most probable value = maximum of the probability density of the Monte Carlo draws\n"
            "(Gaussian kernel density estimate, Silverman bandwidth). For skewed distributions it differs\n"
            "from the mean and the median.",
    "se": "± after each statistic = its Monte Carlo standard error (bootstrap: the draws are resampled with\n"
          "replacement B times and the statistic is recomputed). It says how precisely the statistic itself is\n"
          "known with N draws (it falls as 1/√N) — it is NOT the uncertainty of the concentration, which is σ\n"
          "and the 68 % / 95 % intervals. Increase N if a s.e. is too large for the digits you want to report.",
}
COLORS = {"bar68": "#1f77b4", "bar95": "#9ecae1", "mode": "#d62728", "mean": "#2ca02c", "median": "#ff7f0e",
          "nominal": "#555555"}


class UncertaintyWindow(tk.Toplevel):
    def __init__(self, master, inputs_provider):
        super().__init__(master)
        self.master_app = master
        self.inputs_provider = inputs_provider
        self.title("CF-LIBS uncertainty (Monte Carlo)")
        self.geometry("1320x780")
        self.minsize(1000, 600)
        self.result = None
        self._tips = []

        top = ttk.Frame(self, padding=(6, 5))
        top.pack(fill="x")
        ttk.Button(top, text="Run", command=self.run).pack(side="left")
        ttk.Button(top, text="Use session kT / Ne", command=self.load_session).pack(side="left", padx=4)
        ttk.Button(top, text="Save CSV...", command=self.save_csv).pack(side="left")
        ttk.Button(top, text="Save plot...", command=self.save_plot).pack(side="left", padx=4)
        self.status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=10)

        par = ttk.Frame(self, padding=(6, 0))
        par.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("n", "kt", "kt_sig", "ne", "ne_rel", "s_int", "s_ga", "codemap")}
        self.weighted = tk.BooleanVar(value=False)
        self.src = {s: tk.BooleanVar(value=True) for s in SOURCES}
        c = 0
        for label, key, w in (("draws", "n", 6), ("kT eV", "kt", 8), ("±σ kT", "kt_sig", 6), ("Ne cm⁻³", "ne", 10),
                              ("σ Ne (rel)", "ne_rel", 5), ("σ I default", "s_int", 5), ("σ gA", "s_ga", 5)):
            lab = ttk.Label(par, text=label)
            lab.grid(row=0, column=c, padx=(8, 2)); c += 1
            ent = ttk.Entry(par, textvariable=self.v[key], width=w)
            ent.grid(row=0, column=c); c += 1
            if key in HELP:
                self._tips += [ToolbarTooltip(lab, HELP[key]), ToolbarTooltip(ent, HELP[key])]
        cb = ttk.Checkbutton(par, text="weighted intercepts", variable=self.weighted)
        cb.grid(row=0, column=c, padx=10); c += 1
        self._tips.append(ToolbarTooltip(cb, HELP["weighted"]))
        self.show_se = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(par, text="± s.e. of each value", variable=self.show_se, command=self._refresh)
        cb.grid(row=0, column=c, padx=4)
        self._tips.append(ToolbarTooltip(cb, HELP["se"]))
        par2 = ttk.Frame(self, padding=(6, 3))
        par2.pack(fill="x")
        lab = ttk.Label(par2, text="σ gA per accuracy code")
        lab.pack(side="left", padx=(8, 2))
        ent = ttk.Entry(par2, textvariable=self.v["codemap"], width=34)
        ent.pack(side="left")
        self._tips += [ToolbarTooltip(lab, HELP["codemap"]), ToolbarTooltip(ent, HELP["codemap"])]
        ttk.Label(par2, text="   sources:").pack(side="left")
        for s in SOURCES:
            ttk.Checkbutton(par2, text=s, variable=self.src[s]).pack(side="left", padx=3)

        mid = ttk.PanedWindow(self, orient="horizontal")
        mid.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(mid)
        cols = ("Element", "Most probable", "Mean", "Median", "σ", "Skewness", "68 % (HDI)", "95 %", "CF-LIBS",
                "Mass % mode", "Mass % σ")
        self.table_label = tk.StringVar(value="Molar % (number of atoms) — Monte Carlo statistics")
        ttk.Label(left, textvariable=self.table_label, padding=(0, 0, 0, 2)).pack(anchor="w")
        tfr = ttk.Frame(left)
        tfr.pack(fill="x")
        self.tree = ttk.Treeview(tfr, columns=cols, show="headings", height=8)
        for col, w in zip(cols, (55, 105, 105, 105, 95, 90, 190, 190, 60, 100, 85)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=40, anchor="center", stretch=False)
        xsb = ttk.Scrollbar(tfr, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=xsb.set)
        self.tree.pack(fill="x")
        xsb.pack(fill="x")
        self._tips.append(ToolbarTooltip(self.tree, HELP["mode"] + "\n\n" + HELP["se"]))
        ttk.Label(left, text="Error budget: σ of molar % from each source alone", padding=(0, 6, 0, 2)).pack(anchor="w")
        bcols = ("Element",) + SOURCES + ("quadrature", "total MC")
        self.btree = ttk.Treeview(left, columns=bcols, show="headings", height=7)
        for col in bcols:
            self.btree.heading(col, text=col)
            self.btree.column(col, width=66, anchor="center")
        self.btree.pack(fill="x")
        self.text = tk.Text(left, height=7, wrap="word", font=("Consolas", 9))
        self.text.pack(fill="both", expand=True, pady=(6, 0))
        mid.add(left, weight=3)

        right = ttk.Frame(mid)
        ctl = ttk.Frame(right)
        ctl.pack(fill="x")
        self.view = tk.StringVar(value="Summary")
        self.unit = tk.StringVar(value="molar %")
        self.logx = tk.BooleanVar(value=False)
        ttk.Label(ctl, text="Plot").pack(side="left")
        self.view_cb = ttk.Combobox(ctl, textvariable=self.view, values=["Summary"], width=16, state="readonly")
        self.view_cb.pack(side="left", padx=3)
        self.view_cb.bind("<<ComboboxSelected>>", lambda _e: self.redraw())
        ttk.Combobox(ctl, textvariable=self.unit, values=["molar %", "mass %"], width=8, state="readonly").pack(side="left")
        ttk.Checkbutton(ctl, text="log x", variable=self.logx, command=self.redraw).pack(side="left", padx=6)
        self.unit.trace_add("write", lambda *_: self.redraw())
        if Figure is not None:
            self.fig = Figure(figsize=(6.4, 5.6), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=right)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            self.fig = self.canvas = None
        mid.add(right, weight=3)

        self.v["n"].set("3000")
        self.v["s_int"].set("0.05")
        self.v["s_ga"].set("0.10")
        self.load_session()
        center_window(self, master)

    # ------------------------------------------------------------------
    def load_session(self):
        app = self.master_app
        cw = getattr(app, "cflibs_window", None)
        kt = ne = None
        try:
            if cw is not None and cw.winfo_exists():
                kt, ne = float(cw.last_kt), float(cw.last_ne)
        except Exception:
            pass
        kt = kt or getattr(app, "session_temperature", None) or 1.0
        ne = ne or getattr(app, "session_ne", None) or 1e17
        sk = session_kt_sigma(app, kt)
        sn = session_ne_sigma(app, ne)
        self.v["kt"].set(f"{kt:.6g}")
        self.v["ne"].set(f"{ne:.6g}")
        self.v["kt_sig"].set(f"{sk:.3g}" if sk else "0.05")
        self.v["ne_rel"].set(f"{sn / ne:.3g}" if sn else "0.15")
        self.status_var.set("kT, Ne from the CF-LIBS window" + (" (σ kT from fit)" if sk else " (σ kT default 0.05 eV)")
                            + (", σ Ne from fit" if sn else ", σ Ne default 15 %"))

    def _f(self, k):
        return float(self.v[k].get().strip().replace(",", "."))

    def run(self):
        try:
            code_map = parse_code_map(self.v["codemap"].get()) if self.v["codemap"].get().strip() else None
            inp = self.inputs_provider(self.master_app, self._f("s_int"), self._f("s_ga"), code_map)
            if not inp.groups:
                raise ValueError("No CF-LIBS points: fit the template lines and run CF-LIBS first.")
            sources = tuple(s for s in SOURCES if self.src[s].get())
            self.result = monte_carlo(inp, self._f("kt"), self._f("ne"), self._f("kt_sig"), self._f("ne_rel"),
                                      n=int(self._f("n")), sources=sources, weighted=self.weighted.get())
            self.result.params.update(s_int=self._f("s_int"), s_ga=self._f("s_ga"),
                                      code_map=self.v["codemap"].get().strip(), n_lines=sum(len(v) for v in inp.groups.values()))
        except Exception as e:  # noqa: BLE001
            _showerror(self, "CF-LIBS uncertainty", str(e))
            return
        r = self.result
        self.order = sorted(r.nominal, key=lambda el: -r.nominal[el][0])
        self.view_cb.configure(values=["Summary"] + [f"Distribution: {el}" for el in self.order])
        r.summary_png = summary_png(r)          # embedded in the CF-LIBS report
        self.master_app.last_cflibs_uncertainty = r
        self._show()
        self._update_cflibs_table()

    def _refresh(self):
        if self.result is not None:
            self._show()

    def _show(self):
        r = self.result
        se_on = self.show_se.get()
        nb = r.params.get("n_boot", 0)
        self.table_label.set("Molar % (number of atoms) — Monte Carlo statistics"
                             + (f";  ± = Monte Carlo standard error of each value (bootstrap, B = {nb})"
                                if se_on and nb else ""))
        self.tree.delete(*self.tree.get_children())
        for el in self.order:
            nu, ma = r.number[el], r.mass[el]
            f = (lambda st, k: fmt_pm(stat_value(st, k), st.se.get(k))) if se_on else \
                (lambda st, k: f"{stat_value(st, k):.3g}" if k != "skew" else f"{st.skew:+.2f}")
            self.tree.insert("", "end", values=(
                el, f(nu, "mode"), f(nu, "mean"), f(nu, "p50"), f(nu, "sd"), f(nu, "skew"),
                f"{f(nu, 'hdi_lo')} – {f(nu, 'hdi_hi')}", f"{f(nu, 'p2_5')} – {f(nu, 'p97_5')}",
                f"{r.nominal[el][0]:.3g}", f(ma, "mode"), f(ma, "sd")))
        self.btree.delete(*self.btree.get_children())
        for el in self.order:
            parts = [r.budget_number.get(s, {}).get(el) for s in r.sources]
            quad = sum(p * p for p in parts if p is not None) ** 0.5
            row = [el] + [("—" if s not in r.sources else _fmt_sd(r.budget_number[s].get(el, 0))) for s in SOURCES]
            self.btree.insert("", "end", values=row + [f"{quad:.2g}", f"{r.number[el].sd:.2g}"])
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(summary_lines(r)))
        self.status_var.set(f"{r.n_draws} draws, {r.params.get('n_lines')} lines, sources: {', '.join(r.sources)}"
                            + (f", {r.failed} failed draws" if r.failed else ""))
        self.redraw()

    def redraw(self):
        if self.fig is None or self.result is None:
            return
        mass = self.unit.get() == "mass %"
        self.fig.clear()
        view = self.view.get()
        if view.startswith("Distribution: "):
            draw_distribution(self.fig, self.result, view.split(": ", 1)[1], mass=mass, logx=self.logx.get(),
                              show_se=self.show_se.get())
        else:
            draw_summary(self.fig, self.result, mass=mass, logx=self.logx.get())
        self.canvas.draw_idle()

    def _update_cflibs_table(self):
        cw = getattr(self.master_app, "cflibs_window", None)
        r = self.result
        try:
            if cw is None or not cw.winfo_exists():
                return
            if abs(cw.last_kt - r.params["kt"]) > 1e-4 * r.params["kt"] or abs(cw.last_ne - r.params["ne"]) > 1e-4 * r.params["ne"]:
                return
            for iid in cw.tree.get_children():
                vals = list(cw.tree.item(iid, "values"))
                el = vals[0]
                if el in r.mass:
                    base2 = str(vals[2]).split(" ±")[0]
                    base3 = str(vals[3]).split(" ±")[0]
                    vals[2] = f"{base2} ± {r.number[el].sd:.2g} (mode {r.number[el].mode:.3g})"
                    vals[3] = f"{base3} ± {r.mass[el].sd:.2g}"
                    cw.tree.item(iid, values=vals)
        except Exception:
            pass

    def save_plot(self):
        if self.fig is None or self.result is None:
            return
        fn = filedialog.asksaveasfilename(parent=self, defaultextension=".png",
                                          filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if fn:
            self.fig.savefig(fn, dpi=300, bbox_inches="tight")

    def save_csv(self):
        if not self.result:
            return
        fn = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fn:
            return
        r = self.result
        with open(fn, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            head = ["element", "molar_nominal", "mass_nominal"]
            for unit in ("molar", "mass"):
                for k in STAT_KEYS:
                    head += [f"{unit}_{k}", f"{unit}_{k}_se"]
            w.writerow(head + [f"molar_sd_{s}" for s in r.sources])
            for el in r.nominal:
                row = [el, r.nominal[el][0], r.nominal[el][1]]
                for st in (r.number[el], r.mass[el]):
                    for k in STAT_KEYS:
                        row += [stat_value(st, k), st.se.get(k)]
                w.writerow(row + [r.budget_number.get(s, {}).get(el) for s in r.sources])
            w.writerow([])
            w.writerow([f"# N = {r.n_draws} draws; *_se = Monte Carlo standard error of the statistic "
                        f"(bootstrap, B = {r.params.get('n_boot', 0)}); sd = uncertainty of the concentration"])


def _fmt_sd(x, ref: float = 1.0) -> str:
    """σ formatting that shows round-off noise (< 1e-9) as 0."""
    return "0" if x is None or abs(x) < 1e-9 else f"{x:.2g}"


# ---------------------------------------------------------------------- plotting (also used by the report)
def _stats_for(r, el, mass):
    return (r.mass if mass else r.number)[el], r.nominal[el][1 if mass else 0], \
        (r.samples_mass if mass else r.samples_number)[el]


def draw_summary(fig, r, mass=False, logx=False):
    order = sorted(r.nominal, key=lambda el: -r.nominal[el][1 if mass else 0])
    ax = fig.add_subplot(111)
    unit = "mass %" if mass else "molar %"
    stats = [_stats_for(r, el, mass) for el in order]
    lo = min(s[0].p2_5 for s in stats)
    hi = max(s[0].p97_5 for s in stats)
    if not logx and lo > 0 and hi / max(lo, 1e-12) > 50:
        logx = True
    for i, (st, nom, _v) in enumerate(stats):
        ax.plot([st.p2_5, st.p97_5], [i, i], color=COLORS["bar95"], lw=3, solid_capstyle="butt", zorder=1)
        ax.plot([st.hdi68[0], st.hdi68[1]], [i, i], color=COLORS["bar68"], lw=7, solid_capstyle="butt", zorder=2)
        ax.plot(st.mode, i, marker="D", color=COLORS["mode"], ms=8, zorder=4)
        ax.plot(st.mean, i, marker="o", mfc="white", mec=COLORS["mean"], ms=7, zorder=3)
        ax.plot(st.p50, i, marker="|", color=COLORS["median"], ms=14, mew=2, zorder=3)
        ax.plot(nom, i, marker="x", color=COLORS["nominal"], ms=7, zorder=3)
        txt = (f"{st.mode:.3g}  (+{st.hdi68[1] - st.mode:.2g} / −{st.mode - st.hdi68[0]:.2g})\n"
               f"x̄ = {st.mean:.3g},  σ = {st.sd:.2g},  Md = {st.p50:.3g}")
        ax.annotate(txt, xy=(1.01, i), xycoords=("axes fraction", "data"), va="center", fontsize=7.5)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=10)
    ax.invert_yaxis()
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(f"Concentration ({unit})")
    ax.grid(True, axis="x", ls="--", lw=0.5, alpha=0.6)
    fig.suptitle(f"CF-LIBS — most probable value and Monte Carlo intervals (N = {r.n_draws})",
                 x=0.01, ha="left", fontsize=10)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=COLORS["mode"], marker="D", ls="", label="most probable (mode)"),
               Line2D([], [], color=COLORS["mean"], marker="o", mfc="white", ls="", label="mean"),
               Line2D([], [], color=COLORS["median"], marker="|", ms=12, mew=2, ls="", label="median"),
               Line2D([], [], color=COLORS["nominal"], marker="x", ls="", label="CF-LIBS nominal"),
               Line2D([], [], color=COLORS["bar68"], lw=7, label="68 % HDI"),
               Line2D([], [], color=COLORS["bar95"], lw=3, label="95 % interval")]
    ax.legend(handles=handles, fontsize=7, loc="upper left", bbox_to_anchor=(0.0, -0.19), ncol=3, frameon=False)
    ax.set_ylim(len(order) - 0.5, -0.5)
    p = r.params
    fig.text(0.01, 0.01, f"kT = {p['kt']:.3g} ± {p['sig_kt']:.2g} eV;  Ne = {p['ne']:.2e} cm⁻³ (±{100 * p['sig_ne_rel']:.0f} %);  "
             f"sources: {', '.join(r.sources)}", fontsize=7, color="#444")
    fig.subplots_adjust(left=0.10, right=0.64, top=0.92, bottom=0.30)


def draw_distribution(fig, r, el, mass=False, logx=False, show_se=True):
    import numpy as np
    st, nom, v = _stats_for(r, el, mass)
    unit = "mass %" if mass else "molar %"
    ax = fig.add_subplot(111)
    a = np.asarray(v)
    bins = np.logspace(np.log10(max(a.min(), 1e-6)), np.log10(a.max()), 50) if logx else 50
    ax.hist(a, bins=bins, density=True, color="#c6dbef", edgecolor="white", label="Monte Carlo draws")
    mode, bw, xs, dens = kde_mode(list(a))
    ax.plot(xs, dens, color="#08519c", lw=1.6, label="kernel density")
    ax.axvspan(st.hdi68[0], st.hdi68[1], color=COLORS["bar68"], alpha=0.12, label="68 % HDI")
    for x in (st.p2_5, st.p97_5):
        ax.axvline(x, color=COLORS["bar95"], lw=1.2, ls="--")
    ax.axvline(st.mode, color=COLORS["mode"], lw=2, label=f"most probable = {st.mode:.3g}")
    ax.axvline(st.mean, color=COLORS["mean"], lw=1.4, ls="--", label=f"mean = {st.mean:.3g}")
    ax.axvline(st.p50, color=COLORS["median"], lw=1.4, ls=":", label=f"median = {st.p50:.3g}")
    ax.axvline(nom, color=COLORS["nominal"], lw=1.2, ls="-.", label=f"CF-LIBS nominal = {nom:.3g}")
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(f"{el} ({unit})")
    ax.set_ylabel("probability density")
    ax.set_title(f"{el}: distribution of {unit} (N = {len(a)})", fontsize=10)
    ax.legend(fontsize=7, loc="upper left")
    if show_se and st.se:
        g = lambda k: fmt_pm(stat_value(st, k), st.se.get(k))  # noqa: E731
        box = (f"N = {len(a)}\n"
               f"most probable = {g('mode')}\n"
               f"mean          = {g('mean')}\n"
               f"median        = {g('p50')}\n"
               f"sd (σ)        = {g('sd')}  ({100 * st.sd / st.mean:.1f} %)\n"
               f"skewness      = {g('skew')}\n"
               f"68 % HDI      = [{g('hdi_lo')}, {g('hdi_hi')}]\n"
               f"95 %          = [{g('p2_5')}, {g('p97_5')}]\n"
               f"KDE bandwidth = {bw:.3g}\n"
               f"± = MC standard error (bootstrap, B = {r.params.get('n_boot', 0)})")
    else:
        box = (f"N = {len(a)}\n"
               f"most probable = {st.mode:.4g}\n"
               f"mean = {st.mean:.4g}\n"
               f"median = {st.p50:.4g}\n"
               f"σ = {st.sd:.3g}  ({100 * st.sd / st.mean:.1f} %)\n"
               f"skewness = {st.skew:+.2f}\n"
               f"68 % HDI = [{st.hdi68[0]:.4g}, {st.hdi68[1]:.4g}]\n"
               f"95 % = [{st.p2_5:.4g}, {st.p97_5:.4g}]\n"
               f"KDE bandwidth = {bw:.3g}")
    ax.text(0.98, 0.97, box, transform=ax.transAxes, ha="right", va="top", fontsize=8, family="monospace",
            multialignment="left",
            bbox=dict(boxstyle="round", fc="white", ec="#999", alpha=0.92))
    ax.grid(True, ls="--", lw=0.5, alpha=0.5)
    fig.tight_layout()


def summary_png(r, mass=False) -> str:
    """Summary plot as base64 PNG (for the HTML report)."""
    try:
        from matplotlib.figure import Figure as F
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        fig = F(figsize=(9, 2.6 + 0.6 * len(r.nominal)), dpi=110)
        FigureCanvasAgg(fig)
        draw_summary(fig, r, mass=mass)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def summary_lines(r) -> list[str]:
    p = r.params
    out = [
        f"Monte Carlo: {r.n_draws} draws; kT = {p['kt']:.4g} ± {p['sig_kt']:.2g} eV; Ne = {p['ne']:.3e} cm-3 "
        f"(σ {100 * p['sig_ne_rel']:.0f} %); σ I default {p.get('s_int')}, σ gA {p.get('s_ga')}"
        + (f", per code: {p['code_map']}" if p.get("code_map") else "")
        + ("; weighted intercepts" if p.get("weighted") else "; plain-mean intercepts (as pyLIBS)"),
        "Molar % = number of atoms of the element / total number of atoms (×100). Most probable value = mode of the "
        "Monte Carlo distribution (Gaussian KDE). 68 % HDI = shortest interval containing 68 % of the draws; "
        "95 % = 2.5–97.5 percentiles. '±' after a statistic = its Monte Carlo standard error (bootstrap); it "
        "decreases as 1/√N and is not the uncertainty of the concentration (σ and the intervals). Distributions are skewed because concentrations depend exponentially on the "
        "Boltzmann intercepts and are normalized to 100 %.",
    ]
    if r.budget_number:
        dom = {}
        for el in r.nominal:
            best = max(r.sources, key=lambda s: r.budget_number.get(s, {}).get(el, 0) or 0)
            dom.setdefault(best, []).append(el)
        out.append("Dominant source per element: " + "; ".join(f"{s}: {', '.join(v)}" for s, v in dom.items()))
    out.append("Not included: partition-function and atomic-mass uncertainties, departures from LTE, and spectral "
               "interferences; the normalization to 100 % assumes that all major elements are measured.")
    return out
