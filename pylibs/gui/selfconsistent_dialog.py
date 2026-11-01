"""Self-consistent plasma temperature and electron density (H-alpha Stark + Saha-Boltzmann)."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from pylibs.core.plasma_fit import global_fit, sb_coordinates, stark_boltzmann_loop
from pylibs.gui.helpers import _showerror, center_window

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    Figure = FigureCanvasTkAgg = None

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf"]

HELP = (
    "Phase 1 (Stark ⇄ Saha-Boltzmann): Ne from the H-alpha Stark width with α evaluated at the current T; "
    "T from the Saha-Boltzmann plot at that Ne; repeated until both change less than the tolerance.\n"
    "Phase 2 (global best fit): T, Ne and one intercept per element fitted together to all neutral and "
    "ionic lines (non-linear least squares). Ne is fitted only from elements with lines of both stages; "
    "σ from the covariance matrix. Ne(Saha) is then compared with Ne(Stark) at the fitted T."
)


class SelfConsistentWindow(tk.Toplevel):
    def __init__(self, master, backend):
        super().__init__(master)
        self.master_app = master
        self.backend = backend
        self.title("T–Ne self-consistent fit (H-alpha Stark + Saha-Boltzmann)")
        self.geometry("1150x760")
        self.minsize(950, 600)
        self.result = None

        top = ttk.Frame(self, padding=(6, 5))
        top.pack(fill="x")
        ttk.Button(top, text="Run", command=self.run).pack(side="left")
        self.apply_fit_btn = ttk.Button(top, text="Apply global fit", command=self.apply_global, state="disabled")
        self.apply_fit_btn.pack(side="left", padx=4)
        self.apply_stark_btn = ttk.Button(top, text="Apply Stark-consistent", command=self.apply_stark, state="disabled")
        self.apply_stark_btn.pack(side="left")
        self.status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=12)

        par = ttk.Frame(self, padding=(6, 0))
        par.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("kt0", "ne0", "tol", "maxit")}
        self.use_stark = tk.BooleanVar(value=True)
        c = 0
        for label, key, w in (("start kT eV", "kt0", 8), ("start Ne cm⁻³", "ne0", 11),
                              ("tolerance", "tol", 7), ("max iter", "maxit", 5)):
            ttk.Label(par, text=label).grid(row=0, column=c, padx=(8, 2)); c += 1
            ttk.Entry(par, textvariable=self.v[key], width=w).grid(row=0, column=c); c += 1
        self.stark_cb = ttk.Checkbutton(par, text="Phase 1 uses H-alpha Stark Ne(T)", variable=self.use_stark)
        self.stark_cb.grid(row=0, column=c, padx=12)
        self.info_var = tk.StringVar()
        ttk.Label(self, textvariable=self.info_var, padding=(10, 2), foreground="#444").pack(fill="x")
        ttk.Label(self, text=HELP, wraplength=1100, padding=(10, 0), foreground="#555", justify="left").pack(fill="x")

        mid = ttk.PanedWindow(self, orient="horizontal")
        mid.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(mid)
        cols = ("phase", "iter", "kT (eV)", "Ne (cm⁻³)", "Ne Stark(T)", "rel. change")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        for col, w in zip(cols, (150, 40, 90, 95, 95, 80)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.text = tk.Text(left, height=14, wrap="word", font=("Consolas", 9))
        self.text.pack(fill="both", expand=True, pady=(4, 0))
        mid.add(left, weight=1)
        right = ttk.Frame(mid)
        if Figure is not None:
            self.fig = Figure(figsize=(5.6, 4.6), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=right)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            self.fig = self.ax = self.canvas = None
        mid.add(right, weight=1)

        self._defaults()
        center_window(self, master)

    # ------------------------------------------------------------------
    def _halpha_width(self):
        res = getattr(self.master_app, "last_halpha_result", None) or {}
        if res.get("available") and (res.get("corrected_lorentzian_width") or 0) > 0:
            return float(res["corrected_lorentzian_width"]), res
        return None, res

    def _elements(self):
        sw = getattr(self.master_app, "saha_window", None)
        try:
            if sw is not None and sw.winfo_exists() and sw.included_elements:
                return set(sw.included_elements)
        except Exception:
            pass
        return None

    def _defaults(self):
        app = self.master_app
        kt0 = getattr(app, "session_temperature", None) or getattr(app.options, "ha_kt", 1.0) or 1.0
        width, res = self._halpha_width()
        ne0 = (res.get("ne") if width else None) or getattr(app, "session_ne", None) or 1.0e17
        self.v["kt0"].set(f"{kt0:.4g}")
        self.v["ne0"].set(f"{ne0:.4g}")
        self.v["tol"].set("1e-4")
        self.v["maxit"].set("50")
        if width:
            self.info_var.set(f"H-alpha: corrected Stark FWHM = {width:.4f} Å "
                              f"(Ne = {res.get('ne', 0):.3e} cm⁻³ at kT = {res.get('kt', 0):.3g} eV from Options)")
            self.use_stark.set(True)
            self.stark_cb.state(["!disabled"])
        else:
            self.info_var.set("No H-alpha fit in this session: Phase 1 iterates T only at the start Ne. "
                              "Run Analyse > Ne from H-alpha first to use the Stark width.")
            self.use_stark.set(False)
            self.stark_cb.state(["disabled"])
        els = self._elements()
        if els:
            self.info_var.set(self.info_var.get() + f"   |   elements included in Saha-Boltzmann: {', '.join(sorted(els))}")

    def _num(self, key):
        return float(self.v[key].get().strip().replace(",", "."))

    # ------------------------------------------------------------------
    def run(self):
        app = self.master_app
        try:
            kt0, ne0 = self._num("kt0"), self._num("ne0")
            tol, maxit = self._num("tol"), int(self._num("maxit"))
            elements = self._elements()
            points, skipped = self.backend.points(app, elements)
            if not points:
                raise ValueError("No valid Saha-Boltzmann points: fit the template lines first.")
            width, _res = self._halpha_width()
            use_stark = bool(width) and self.use_stark.get()
            ne_from_kt = (lambda kt: self.backend.halpha_ne(width, kt)[0]) if use_stark else None
            kt_from_ne = lambda ne, kt: self.backend.mean_kt(app, ne, kt, elements)  # noqa: E731
            steps, converged = stark_boltzmann_loop(kt0, ne0, ne_from_kt, kt_from_ne, tol, maxit)
            p1 = steps[-1]
            fit = global_fit(points, p1.kt, p1.ne, fit_ne=True)
            ne_stark_fit = self.backend.halpha_ne(width, fit.kt)[0] if width else None
        except Exception as e:  # noqa: BLE001
            self.status_var.set(str(e))
            _showerror(self, "T–Ne fit", str(e))
            return
        self.result = {"steps": steps, "converged": converged, "fit": fit, "points": points,
                       "skipped": skipped, "ne_stark_fit": ne_stark_fit, "use_stark": use_stark,
                       "halpha_sigma_rel": self._halpha_sigma_rel(), "elements": sorted({p.element for p in points})}
        app.last_selfconsistent = self.result
        self._show()
        self.apply_fit_btn.state(["!disabled"])
        self.apply_stark_btn.state(["!disabled"] if use_stark else ["disabled"])

    def _halpha_sigma_rel(self):
        res = getattr(self.master_app, "last_halpha_result", None) or {}
        ne, s = res.get("ne"), res.get("ne_sigma")
        return s / ne if ne and s else None

    def _show(self):
        r = self.result
        fit, steps = r["fit"], r["steps"]
        self.tree.delete(*self.tree.get_children())
        for st in steps:
            self.tree.insert("", "end", values=(
                "1: Stark ⇄ SB" if r["use_stark"] else "1: SB (fixed Ne)", st.iteration, f"{st.kt:.5f}",
                f"{st.ne:.4e}", "—" if st.ne_stark is None else f"{st.ne_stark:.4e}", f"{st.rel_change:.2e}"))
        self.tree.insert("", "end", values=(
            "2: global fit", "—", f"{fit.kt:.5f}", f"{fit.ne:.4e}",
            "—" if r["ne_stark_fit"] is None else f"{r['ne_stark_fit']:.4e}", "—"))
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(summary_lines(r)))
        self.status_var.set(f"kT = {fit.kt:.4g} ± {fit.sigma_kt or 0:.2g} eV, "
                            f"Ne = {fit.ne:.3e}" + (f" ± {fit.sigma_ne:.1e}" if fit.sigma_ne else "") + " cm⁻³")
        self._plot()

    def _plot(self):
        if self.ax is None:
            return
        r = self.result
        fit = r["fit"]
        self.ax.clear()
        by_el = {}
        for p in r["points"]:
            by_el.setdefault(p.element, []).append(p)
        for i, (el, pts) in enumerate(sorted(by_el.items())):
            color = COLORS[i % len(COLORS)]
            for ion, marker in ((1, "o"), (2, "s")):
                xy = [sb_coordinates(p, fit.kt, fit.ne) for p in pts if p.ion == ion]
                if xy:
                    self.ax.scatter([a for a, _ in xy], [b for _, b in xy], color=color, marker=marker, s=28,
                                    label=f"{el} {'I' if ion == 1 else 'II'}")
            xs = [sb_coordinates(p, fit.kt, fit.ne)[0] for p in pts]
            x0, x1 = min(xs) - 0.3, max(xs) + 0.3
            q = fit.intercepts[el]
            self.ax.plot([x0, x1], [q - x0 / fit.kt, q - x1 / fit.kt], color=color, lw=1)
        self.ax.set_title(f"Global Saha-Boltzmann fit: kT = {fit.kt:.3f} eV, Ne = {fit.ne:.2e} cm⁻³", fontsize=9)
        self.ax.set_xlabel("E_k (+ E_ion for ions)  (eV)")
        self.ax.set_ylabel("ln(I/gA)  (ions: − ln(6.04e21 kT^1.5/Ne))")
        self.ax.grid(True, ls="--", lw=0.5, alpha=0.6)
        self.ax.legend(fontsize=7, ncol=2)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    def _apply(self, kt, skt, ne, sne, source):
        app = self.master_app
        had_applied_sac = bool(getattr(app, "apply_sac_correction", False))
        app.session_ne, app.session_ne_source, app.session_ne_sigma = ne, source, (ne, sne)
        sw = getattr(app, "saha_window", None)
        try:
            if sw is not None and sw.winfo_exists():
                sw.compute()  # redraw the Saha-Boltzmann plot at the new Ne
        except Exception:
            pass
        # the global/self-consistent T is the session temperature (overrides the per-element mean)
        app.session_temperature, app.session_temperature_source = kt, source
        app.session_temperature_sigma = (kt, skt)
        app.last_selfconsistent = self.result
        try:
            app.invalidate_cflibs_results()
            if had_applied_sac:
                app.invalidate_self_absorption_analysis()
        except Exception:
            pass
        try:
            if sw is not None and sw.winfo_exists():
                sw.summary_var.set(f"Session set by T–Ne fit: kT={kt:.4g} eV, Ne={ne:.3e} cm-3 | " + sw.summary_var.get())
        except Exception:
            pass
        cw = getattr(app, "cflibs_window", None)
        try:
            if cw is not None and cw.winfo_exists():
                cw.kt_var.set(f"{kt:.6g}")
                cw.ne_var.set(f"{ne:.6g}")
        except Exception:
            pass
        if self.result is not None:
            self.result["applied"] = source
        msg = f"Applied ({source}): kT = {kt:.4g} eV, Ne = {ne:.3e} cm-3"
        self.status_var.set(msg)
        try:
            app.status(msg)
        except Exception:
            pass

    def apply_global(self):
        if not self.result:
            return
        f = self.result["fit"]
        src = "T–Ne global Saha-Boltzmann fit" if f.ne_fitted else "T global fit (Ne from Phase 1)"
        sne = f.sigma_ne if f.ne_fitted else None
        self._apply(f.kt, f.sigma_kt, f.ne, sne, src)

    def apply_stark(self):
        if not self.result:
            return
        st = self.result["steps"][-1]
        rel = self.result.get("halpha_sigma_rel")
        self._apply(st.kt, None, st.ne, st.ne * rel if rel else None, "Stark ⇄ Saha-Boltzmann self-consistent")


def summary_lines(r) -> list[str]:
    """Plain-text summary (also used by the CF-LIBS report)."""
    fit, steps = r["fit"], r["steps"]
    p1 = steps[-1]
    out = [
        f"Phase 1 ({'H-alpha Stark ⇄ Saha-Boltzmann' if r['use_stark'] else 'Saha-Boltzmann at fixed Ne'}): "
        f"{'converged' if r['converged'] else 'NOT converged'} after {len(steps)} iteration(s): "
        f"kT = {p1.kt:.5g} eV, Ne = {p1.ne:.4e} cm-3",
        "",
        f"Phase 2 (global fit, {fit.n_points} lines, {fit.n_params} parameters, elements: {', '.join(fit.elements)}):",
        f"  kT = {fit.kt:.5g} ± {_s(fit.sigma_kt)} eV   (T = {fit.kt * 11604.5:.0f} ± {_s(fit.sigma_kt and fit.sigma_kt * 11604.5, '.0f')} K)",
    ]
    if fit.ne_fitted:
        out.append(f"  Ne = {fit.ne:.4e} ± {_s(fit.sigma_ne, '.2e')} cm-3   (from Saha balance of: {', '.join(fit.ne_elements)})")
        if fit.corr_kt_ne is not None:
            out.append(f"  correlation(kT, Ne) = {fit.corr_kt_ne:+.2f}")
    else:
        out.append(f"  {fit.message}")
    out.append(f"  rms residual = {fit.rms:.3f} (in ln I; ≈ {100 * (math.exp(fit.rms) - 1):.0f} % intensity scatter)")
    if r.get("ne_stark_fit") and fit.ne_fitted:
        ratio = fit.ne / r["ne_stark_fit"]
        rel_s = (fit.sigma_ne / fit.ne) if fit.sigma_ne else None
        rel_h = r.get("halpha_sigma_rel")
        out += ["", f"Consistency: Ne(Stark, at fitted T) = {r['ne_stark_fit']:.4e} cm-3; Ne(Saha)/Ne(Stark) = {ratio:.3g}"]
        if rel_s:
            comb = math.sqrt(rel_s ** 2 + (rel_h or 0.0) ** 2)
            z = abs(math.log(ratio)) / comb if comb > 0 else float("inf")
            out.append(f"  z = |ln ratio| / σ = {z:.2f}" + ("" if rel_h else "  (H-alpha σ unknown: Saha σ only)"))
            if z > 2:
                out.append("  → Saha and Stark Ne disagree beyond 2σ: check LTE between ionization stages "
                           "(LTE check), self-absorption of strong lines, and the instrument response correction.")
            else:
                out.append("  → Saha and Stark Ne agree within 2σ (supports LTE between ionization stages).")
    if r.get("applied"):
        out += ["", f"Applied to session: {r['applied']}"]
    return out


def _s(v, spec=".2g"):
    return "N/A" if v is None else format(v, spec)
