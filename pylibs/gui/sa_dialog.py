"""Self-absorption window: Stark-width method + internal reference line (IRSAC)."""

from __future__ import annotations

import csv
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from pylibs.core.self_absorption_irsac2 import MAX_SAC, StarkDatabase, assess, choose_reference, chosen_sac, slope_check
from pylibs.gui.helpers import _showerror, _showinfo, center_window
from pylibs.gui.lte_dialog import ToolbarTooltip, session_kt_sigma, session_ne_sigma

MODES = {
    "IRSAC (recommended)": "irsac",
    "Stark where available, else IRSAC": "stark_then_irsac",
    "Stark only": "stark",
}
AUTO = "auto (least optically thick)"

HELP = {
    "kt": "Plasma temperature kT (eV) used in the Boltzmann factor of IRSAC and in the Stark width T-scaling.",
    "kt_sig": "σ of kT (eV); propagated into the IRSAC significance test.",
    "ne": "Electron density (cm⁻³); the thin-line Stark width is w0 = w(1e17)·Ne/1e17.",
    "ne_rel": "Relative σ of Ne (e.g. 0.15 = 15 %). w0 ∝ Ne, so this enters the Stark SAC directly.",
    "inst": "Instrumental FWHM (Å, from Options). Stark is used only if w0 ≥ resolve × instrumental FWHM.",
    "inst_l": "Lorentzian part of the instrument function (Å), subtracted from the fitted Lorentzian width.\n"
              "0 if the instrument profile is Gaussian (it is then absorbed in the Gaussian width of the Voigt fit).",
    "resolve": "Minimum w0 / instrumental FWHM for the Stark method (default 0.2).",
    "aki": "Relative uncertainty of g·A (and of other line-to-line factors) for IRSAC, combined with the\n"
           "intensity fit error of each line when available.",
    "nsig": "Significance threshold: a line is corrected only if SA differs from 1 by more than nsig·σ.",
    "maxsac": "Largest admissible correction factor (default 3.33, i.e. SA ≥ 0.3, Yang et al. 2018). Larger factors\n"
              "are flagged 'unsafe' and not applied: they usually indicate a blend, a wrong assignment, wrong Ne\n"
              "or Stark data, rather than a measurable self-absorption. 0 = no limit.",
    "fref": "Estimate the self-absorption of the IRSAC reference line itself (Yang et al. 2018): if other lines of\n"
            "the species appear significantly less absorbed than the reference, the reference is scaled so that the\n"
            "least absorbed line is optically thin. This changes the species intercept and therefore the concentration.",
}




class SelfAbsorptionWindow(tk.Toplevel):
    COLS = ("Line", "Ei eV", "Ek eV", "τ/τref", "w_L Å", "w0 Å", "Stark", "SAC Stark", "IRSAC SA", "SAC IRSAC",
            "IRSAC", "Same-Ek test", "Applied")

    def __init__(self, master, lines_provider):
        super().__init__(master)
        self.master_app = master
        self.lines_provider = lines_provider
        self.title("Self-absorption correction (Stark width + internal reference line)")
        self.geometry("1260x700")
        self.minsize(1000, 560)
        self.results = []
        self.lines = []
        self.ref_vars = {}
        self._tips = []

        top = ttk.Frame(self, padding=(6, 5))
        top.pack(fill="x")
        ttk.Button(top, text="Compute", command=self.compute).pack(side="left")
        ttk.Button(top, text="Apply SAC", command=self.apply).pack(side="left", padx=4)
        ttk.Button(top, text="Remove SAC", command=self.remove).pack(side="left")
        ttk.Button(top, text="Compare IRSAC1 / IRSAC2", command=self.compare_methods).pack(side="left", padx=4)
        it_btn = ttk.Button(top, text="Iterate SAC ⇄ T–Ne", command=self.iterate_with_tne)
        it_btn.pack(side="left", padx=4)
        self._tips.append(ToolbarTooltip(it_btn,
            "Repeats: compute SA with the current kT, Ne → apply SAC → re-run the T–Ne fit → update kT, Ne,\n"
            "until kT changes < 0.1 %. Ne is taken from H-alpha (Stark ⇄ Saha-Boltzmann loop) when an H-alpha fit\n"
            "exists, because the Saha balance is biased by self-absorbed ionic resonance lines; otherwise from the\n"
            "global Saha-Boltzmann fit."))
        ttk.Button(top, text="Save CSV...", command=self.save_csv).pack(side="left")
        ttk.Label(top, text="Mode").pack(side="left", padx=(14, 2))
        self.mode = tk.StringVar(value="IRSAC (recommended)")
        ttk.Combobox(top, textvariable=self.mode, values=list(MODES), width=32, state="readonly").pack(side="left")
        self.status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=10)

        par = ttk.Frame(self, padding=(6, 0))
        par.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("kt", "kt_sig", "ne", "ne_rel", "inst", "inst_l", "resolve", "aki", "nsig",
                                              "maxsac")}
        c = 0
        for label, key, w in (("kT eV", "kt", 8), ("±σ kT", "kt_sig", 6), ("Ne cm⁻³", "ne", 10), ("σ Ne (rel)", "ne_rel", 5),
                              ("instr. FWHM Å", "inst", 6), ("instr. Lorentz Å", "inst_l", 5), ("resolve", "resolve", 4),
                              ("σ gA (rel)", "aki", 5), ("nσ", "nsig", 4), ("max SAC", "maxsac", 5)):
            lab = ttk.Label(par, text=label)
            lab.grid(row=0, column=c, padx=(8, 2)); c += 1
            ent = ttk.Entry(par, textvariable=self.v[key], width=w)
            ent.grid(row=0, column=c); c += 1
            self._tips += [ToolbarTooltip(lab, HELP[key]), ToolbarTooltip(ent, HELP[key])]
        self.fref = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(par, text="reference absorption (Yang)", variable=self.fref, command=self.compute)
        cb.grid(row=0, column=c, padx=(10, 2))
        self._tips.append(ToolbarTooltip(cb, HELP["fref"]))

        self.ref_frame = ttk.LabelFrame(self, text="IRSAC reference line per species (hover for the criterion)", padding=4)
        self.ref_frame.pack(fill="x", padx=6, pady=4)
        self._tips.append(ToolbarTooltip(self.ref_frame,
            "Automatic choice: among lines with ≥ 5 % of the strongest intensity of the species, the one with the\n"
            "smallest optical-depth proxy g_k A_ki λ³ exp(−E_i/kT) (high lower level, weak transition)."))

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=14)
        for col, w in zip(self.COLS, (130, 50, 50, 55, 55, 55, 170, 85, 65, 85, 170, 170, 90)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.tag_configure("abs", background="#fde2c8")
        self.tree.tag_configure("ref", background="#dbe9f8")
        self.tree.tag_configure("unsafe", background="#f8d7da")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.note = tk.Text(self, height=6, wrap="word", font=("Consolas", 9))
        self.note.pack(fill="x", padx=6, pady=(0, 6))

        self.load_session()
        center_window(self, master)
        self._initial_after = self.after(150, self.compute)

    # ------------------------------------------------------------------
    def _db_path(self) -> Path:
        here = Path(getattr(self.master_app.options, "libs_db_file", "") or "LIBS.db").resolve().parent
        for cand in (here / "Stark_extended.db", Path(__file__).resolve().parents[2] / "Stark_extended.db"):
            if cand.exists():
                return cand
        return Path(__file__).resolve().parents[2] / "Stark_extended.db"

    def load_session(self):
        app = self.master_app
        kt = getattr(app, "session_temperature", None)
        ne = getattr(app, "session_ne", None)
        sk = session_kt_sigma(app, kt) if kt else None
        sn = session_ne_sigma(app, ne) if ne else None
        self.v["kt"].set(f"{kt:.6g}" if kt else "1.0")
        self.v["kt_sig"].set(f"{sk:.3g}" if sk else "0")
        self.v["ne"].set(f"{ne:.6g}" if ne else "1e17")
        self.v["ne_rel"].set(f"{max(sn / ne, 0.10):.3g}" if sn and ne else "0.15")
        inst = float(getattr(app.options, "instrumental_width", 0.0) or 0.0)
        try:
            if app.current_wavelength_unit_label() == "nm":
                inst *= 10.0
        except Exception:
            pass
        self.v["inst"].set(f"{inst:g}")
        self.v["inst_l"].set(self.v["inst_l"].get() or "0")
        self.v["resolve"].set(self.v["resolve"].get() or "0.2")
        self.v["aki"].set(self.v["aki"].get() or "0.10")
        self.v["nsig"].set(self.v["nsig"].get() or "2")
        self.v["maxsac"].set(self.v["maxsac"].get() or f"{MAX_SAC:.3g}")

    def _num(self, key):
        return float(self.v[key].get().strip().replace(",", "."))

    def _build_ref_selectors(self, kt):
        for w in self.ref_frame.winfo_children():
            w.destroy()
        groups = {}
        for l in self.lines:
            groups.setdefault((l.element, l.ion), []).append(l)
        col = 0
        for sp, ls in sorted(groups.items()):
            if len(ls) < 2:
                continue
            name = f"{sp[0]} {'I' if sp[1] == 1 else 'II'}"
            var = self.ref_vars.get(sp) or tk.StringVar(value=AUTO)
            self.ref_vars[sp] = var
            auto = choose_reference(ls, kt)
            ttk.Label(self.ref_frame, text=name).grid(row=col // 4, column=2 * (col % 4), padx=(6, 2), sticky="e")
            cb = ttk.Combobox(self.ref_frame, textvariable=var, width=26, state="readonly",
                              values=[AUTO] + [l.label for l in sorted(ls, key=lambda x: x.wavelength_A)])
            cb.grid(row=col // 4, column=2 * (col % 4) + 1, padx=(0, 8))
            cb.bind("<<ComboboxSelected>>", lambda _e: self.compute())
            self._tips.append(ToolbarTooltip(cb, f"auto → {auto.label}"))
            col += 1
        if col == 0:
            ttk.Label(self.ref_frame, text="No species with ≥ 2 lines").grid(row=0, column=0)

    def _references(self):
        refs = {}
        for sp, var in self.ref_vars.items():
            if var.get() != AUTO:
                l = next((x for x in self.lines if x.label == var.get() and (x.element, x.ion) == sp), None)
                if l is not None:
                    refs[sp] = l.key
        return refs

    def compute(self):
        pending = getattr(self, "_initial_after", None)
        if pending is not None:
            try:
                self.after_cancel(pending)
            except Exception:
                pass
            self._initial_after = None
        try:
            kt, ne = self._num("kt"), self._num("ne")
            self.params = dict(kt=kt, kt_sigma=self._num("kt_sig"), ne=ne, ne_rel=self._num("ne_rel"),
                               inst_fwhm=self._num("inst"), inst_lorentz=self._num("inst_l"),
                               resolve_ratio=self._num("resolve"), sigma_y=self._num("aki"), nsig=self._num("nsig"),
                               max_sac=self._num("maxsac"), ref_absorption=bool(self.fref.get()))
            self.lines = self.lines_provider(self.master_app)
            if not self.lines:
                raise ValueError("No template lines with species, ion, Ek, gA and a fitted intensity.")
            for l in self.lines:
                rel = getattr(l, "rel_int_err", None)
                l.sigma_y = math.sqrt(self.params["sigma_y"] ** 2 + (rel or 0.0) ** 2)
            if not self.ref_frame.winfo_children() or set(self.ref_vars) != {(l.element, l.ion) for l in self.lines}:
                self._build_ref_selectors(kt)
            db = None
            try:
                db = StarkDatabase(self._db_path())
            except Exception as e:  # noqa: BLE001
                self.status_var.set(f"Stark database unavailable ({e}); IRSAC only")
            try:
                self.results = assess(self.lines, db, references=self._references(), **self.params)
            finally:
                if db is not None:
                    db.close()
        except Exception as e:  # noqa: BLE001
            _showerror(self, "Self-absorption", str(e))
            return
        self._show()

    def _show(self):
        mode = MODES[self.mode.get()]
        self.tree.delete(*self.tree.get_children())
        f = lambda x, s=".3g": "—" if x is None else format(x, s)  # noqa: E731
        n_abs = 0
        for r in self.results:
            l = r.line
            sac, meth = chosen_sac(r, mode)
            applied = f"{sac:.3g} ({meth})" if sac and sac > 1.0 else "1"
            n_abs += bool(sac and sac > 1.0)
            st_sac = "—" if r.stark_sac is None else f"{r.stark_sac:.3g} ±{100 * (r.stark_sac_rel or 0):.0f}%"
            ir_sac = "—" if r.irsac_sac is None else f"{r.irsac_sac:.3g} ±{100 * (r.irsac_sac_rel or 0):.0f}%"
            unsafe = "unsafe" in r.irsac_status or "unsafe" in r.stark_status or "poor fit" in r.irsac_status
            tag = ("ref" if r.irsac_status.startswith("reference") else "abs" if sac and sac > 1.0
                   else "unsafe" if unsafe else "")
            self.tree.insert("", "end", values=(
                l.label, f"{l.ei_ev:.2f}", f"{l.ek_ev:.2f}", f(r.tau_rel), f(l.w_lorentz_A), f(r.stark_w0),
                r.stark_status, st_sac, f(r.irsac_sa), ir_sac, r.irsac_status, r.level_test, applied), tags=(tag,))
        n_stark = sum(1 for r in self.results if r.stark_w0 is not None)
        self.status_var.set(f"{len(self.results)} lines; Stark data for {n_stark}; {n_abs} to correct ({self.mode.get()})")
        self.note.delete("1.0", "end")
        self.note.insert("1.0", "\n".join(self._notes()))

    def _notes(self):
        out = []
        both = [r for r in self.results if r.stark_sac is not None and r.irsac_sac is not None
                and r.irsac_status != "reference"]
        if both:
            out.append("Lines with both methods (Stark vs IRSAC SAC): " + "; ".join(
                f"{r.line.label}: {r.stark_sac:.2f} vs {r.irsac_sac:.2f}" for r in both[:8]))
        mode = MODES[self.mode.get()]
        fr = sorted({(r.line.element, r.line.ion, r.irsac_fref) for r in self.results
                     if r.irsac_status.startswith("reference") and r.irsac_fref is not None and r.irsac_fref < 1.0})
        if fr:
            out.append("Reference line self-absorbed (Yang f_ref): " + "; ".join(
                f"{e} {'I' if i == 1 else 'II'} f_ref = {v:.3g}" for e, i, v in fr))
        unsafe = [r.line.label for r in self.results if "unsafe" in r.irsac_status or "unsafe" in r.stark_status]
        if unsafe:
            out.append(f"Not applied, factor above max SAC ({self.params.get('max_sac', MAX_SAC):g}): " + ", ".join(unsafe[:12])
                       + (" ..." if len(unsafe) > 12 else "") + ". Check blends, assignment, Ne or remove the line.")
        mism = [f"{r.line.label} {r.level_test}" for r in self.results if r.level_test.startswith("weaker")]
        if mism:
            out.append("Same-upper-level test (independent evidence; also caused by blends or response error): "
                       + "; ".join(mism[:6]))
        try:
            sc = slope_check(self.results, mode, self.params["kt"])
        except Exception:  # noqa: BLE001
            sc = {}
        if sc:
            out.append("Slope after correction vs common kT = {:.4g} eV: ".format(self.params["kt"]) + "; ".join(
                f"{e} {'I' if i == 1 else 'II'} kT={v['kt']:.3g} eV {'✓' if v['compatible'] else '✗'}"
                if v["kt"] else f"{e} {'I' if i == 1 else 'II'} slope ≥ 0 ✗" for (e, i), v in sorted(sc.items())))
        res_refs = sorted({r.line.label for r in self.results if r.irsac_status.startswith("reference") and r.line.ei_ev < 0.05})
        if res_refs:
            out.append("Reference is a resonance line (E_i ≈ 0) for " + ", ".join(res_refs) + ": it is probably "
                       "self-absorbed itself, so IRSAC cannot correct that species reliably (choose a line with a higher "
                       "lower level if one is measurable).")
        bad = [r.line.label for r in self.results if r.irsac_status.startswith("SA > 1")]
        if bad:
            out.append("SA > 1 beyond noise for " + ", ".join(bad) + ": the reference line may itself be self-absorbed, "
                       "or kT is off — choose another reference or re-run the T–Ne fit.")
        unres = sum(1 for r in self.results if r.stark_status.startswith("unresolved"))
        if unres:
            out.append(f"{unres} line(s) have Stark widths below the resolvable limit: the Stark method is not applied to them.")
        out.append("IRSAC gives SA relative to the reference line; if the reference is slightly absorbed, all lines of the "
                   "species share that factor, which cancels in the Boltzmann slope (T) but not in absolute concentrations "
                   "between species.")
        out.append("Stark widths: Stark_extended.db (Konjević et al., J. Phys. Chem. Ref. Data 1984, 1990, 2002 and the "
                   "original pyLIBS Stark.db, units verified and corrected).")
        return out

    # ------------------------------------------------------------------
    def apply(self, quiet=False):
        if not self.results:
            return 0
        mode = MODES[self.mode.get()]
        n = 0
        for r in self.results:
            t = getattr(r.line, "template_line", None)
            if t is None:
                continue
            sac, meth = chosen_sac(r, mode)
            if sac and sac > 1.0 and math.isfinite(sac):
                t.sa_sac, t.sa_use, t.sa_method = sac, True, meth
                t.sa_sac_rel = (r.stark_sac_rel if meth == "Stark" else r.irsac_sac_rel) or 0.0
                n += 1
            else:
                t.sa_sac, t.sa_use, t.sa_method, t.sa_sac_rel = "", False, "", 0.0
        app = self.master_app
        app.apply_sac_correction = True
        app.last_self_absorption = {"results": self.results, "params": dict(self.params), "mode": self.mode.get(),
                                    "applied": n}
        app.irsac_algorithm = "IRSAC2"
        app.last_irsac2_result = app.last_self_absorption
        app.last_self_absorption_result = {
            "algorithm": "IRSAC2", "mode": "irsac", "equation_mode": "irsac2",
            "irsac_completed": True, "converged": True,
            "corrected_lines": sum(1 for r in self.results if r.irsac_sac is not None),
            "enabled_lines": n, "applied": n > 0,
            "temperature_k": self.params["kt"] * 11604.518,
            "assessment_status": "IRSAC2 assessment",
        }
        try:
            app.invalidate_cflibs_results()
        except Exception:
            pass
        self._recompute_windows()
        msg = f"SAC applied to {n} line(s) ({self.mode.get()})"
        self.status_var.set(msg)
        try:
            app.status(msg)
        except Exception:
            pass
        return n

    def remove(self):
        app = self.master_app
        app.apply_sac_correction = False
        if getattr(app, "last_self_absorption", None):
            app.last_self_absorption["applied"] = 0
        if isinstance(getattr(app, "last_self_absorption_result", None), dict) and app.last_self_absorption_result.get("algorithm") == "IRSAC2":
            app.last_self_absorption_result["applied"] = False
            app.last_self_absorption_result["enabled_lines"] = 0
        self._recompute_windows()
        self.status_var.set("SAC removed")

    def iterate_with_tne(self, max_iter: int = 10, tol: float = 1e-3):
        app = self.master_app
        try:
            app.show_selfconsistent()
            sc = getattr(app, "selfconsistent_window", None)
            if sc is None:
                raise RuntimeError("T–Ne window not available")
            history = []
            kt_prev = None
            for k in range(1, max_iter + 1):
                self.compute()
                n = self.apply()
                sc.run()
                if not sc.result:
                    raise RuntimeError("T–Ne fit failed")
                use_stark = sc.result.get("use_stark")
                if use_stark:
                    sc.apply_stark()
                    st = sc.result["steps"][-1]
                    kt, ne = st.kt, st.ne
                else:
                    sc.apply_global()
                    kt, ne = sc.result["fit"].kt, sc.result["fit"].ne
                history.append((k, kt, ne, n, "Stark ⇄ SB" if use_stark else "global Saha-Boltzmann"))
                self.load_session()
                if kt_prev and abs(kt - kt_prev) / kt < tol:
                    break
                kt_prev = kt
            self.compute()
            self.apply()
            app.last_self_absorption["history"] = history
            self.note.insert("end", "\n\nIteration SAC ⇄ T–Ne: " + " → ".join(
                f"[{h[0]}] kT={h[1]:.4f} eV, Ne={h[2]:.3e}, {h[3]} corrected" for h in history)
                + f"  (Ne from {history[-1][4]})")
            self.status_var.set(f"Converged after {len(history)} iteration(s): kT = {history[-1][1]:.4f} eV, "
                                f"Ne = {history[-1][2]:.3e} cm-3")
        except Exception as e:  # noqa: BLE001
            _showerror(self, "Self-absorption", str(e))

    def _recompute_windows(self):
        for attr in ("saha_window", "cflibs_window"):
            win = getattr(self.master_app, attr, None)
            try:
                if win is not None and win.winfo_exists():
                    win.compute()
            except Exception:
                pass

    def save_csv(self):
        if not self.results:
            return
        fn = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fn:
            return
        mode = MODES[self.mode.get()]
        with open(fn, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["line", "Ei_eV", "Ek_eV", "tau_rel", "wL_A", "w0_A", "w0_rel_unc", "stark_status", "stark_SA",
                        "stark_SAC", "stark_SAC_rel", "irsac_ref", "irsac_SA", "irsac_SAC", "irsac_SAC_rel",
                        "irsac_status", "irsac_f_ref", "same_level_test", "applied_SAC", "method"])
            for r in self.results:
                sac, meth = chosen_sac(r, mode)
                w.writerow([r.line.label, r.line.ei_ev, r.line.ek_ev, r.tau_rel, r.line.w_lorentz_A, r.stark_w0,
                            r.stark_w0_rel, r.stark_status, r.stark_sa, r.stark_sac, r.stark_sac_rel, r.irsac_ref,
                            r.irsac_sa, r.irsac_sac, r.irsac_sac_rel, r.irsac_status, r.irsac_fref, r.level_test,
                            sac, meth])

    def compare_methods(self):
        if not self.results:
            self.compute()
        try:
            from pylibs.core.dev_adapters import compare_irsac
            result = compare_irsac(self.master_app, self)
        except Exception as exc:  # noqa: BLE001
            _showerror(self, "IRSAC comparison", str(exc))
            return
        lines = [
            "IRSAC comparison on the current fitted line set", "",
            (f"IRSAC1: {result['irsac1_seconds']:.6g} s; converged={result['irsac1_converged']}; "
             f"iterations={result['irsac1_iterations']}; T={result['irsac1_temperature_k']:.7g} K; "
             f"RMSE={result['irsac1_rmse']:.6g}"),
            f"IRSAC2: {result['irsac2_seconds']:.6g} s; {result['irsac2_method']}",
            "", "Line correction factors:",
            f"{'Line':34} {'IRSAC1':>13} {'IRSAC2':>13}",
        ]
        for key, label in sorted(result["line_labels"].items(), key=lambda pair: pair[1]):
            a, b = result["irsac1_factors"].get(key), result["irsac2_factors"].get(key)
            lines.append(f"{label[:34]:34} {a if a is not None else '—':>13} {b if b is not None else '—':>13}")
        lines += ["", "CF-LIBS composition (molar % / mass %):",
                  f"{'Element':12} {'IRSAC1 molar/mass':>28} {'IRSAC2 molar/mass':>28}"]
        c1, c2 = result["composition1"], result["composition2"]
        for element in sorted(set(c1) | set(c2)):
            a, b = c1.get(element), c2.get(element)
            fa = f"{a[0]:.6g} / {a[1]:.6g}" if a else "—"
            fb = f"{b[0]:.6g} / {b[1]:.6g}" if b else "—"
            lines.append(f"{element:12} {fa:>28} {fb:>28}")
        self.master_app.last_irsac_comparison = result
        win = tk.Toplevel(self)
        win.title("IRSAC1 / IRSAC2 comparison")
        win.geometry("980x620")
        text = tk.Text(win, wrap="none", font=("TkFixedFont", 9))
        ybar = ttk.Scrollbar(win, orient="vertical", command=text.yview)
        xbar = ttk.Scrollbar(win, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        ybar.pack(side="right", fill="y")
        xbar.pack(side="bottom", fill="x")
        text.pack(fill="both", expand=True)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")


def report_rows(app):
    """Rows for the CF-LIBS report: (summary list, table rows)."""
    sa = getattr(app, "last_self_absorption", None)
    if not sa or not getattr(app, "apply_sac_correction", False) or not sa.get("applied"):
        return None
    p = sa["params"]
    mode = MODES.get(sa["mode"], "irsac")
    summary = [
        ["Mode", sa["mode"]],
        ["kT / σ kT used", f"{p['kt']:.4g} / {p['kt_sigma']:.2g} eV"],
        ["Ne / σ (rel)", f"{p['ne']:.3e} cm-3 / {100 * p['ne_rel']:.0f} %"],
        ["Instrumental FWHM / Lorentzian part / resolve ratio", f"{p['inst_fwhm']:g} / {p['inst_lorentz']:g} Å / {p['resolve_ratio']:g}"],
        ["σ gA (rel) / significance", f"{p['sigma_y']:g} / {p['nsig']:g}σ"],
        ["Max SAC / reference absorption (Yang)", f"{p.get('max_sac', MAX_SAC):.3g} / {'yes' if p.get('ref_absorption', True) else 'no'}"],
        ["Lines corrected", str(sa["applied"])],
    ]
    if sa.get("history"):
        h = sa["history"]
        summary.append(["Iteration SAC ⇄ T–Ne (Ne from " + h[-1][4] + ")",
                        " → ".join(f"kT={x[1]:.4f} eV, Ne={x[2]:.3e}" for x in h)])
    rows = []
    for r in sa["results"]:
        sac, meth = chosen_sac(r, mode)
        rows.append([r.line.label, f"{r.tau_rel:.3g}" if r.tau_rel is not None else "N/A",
                     "N/A" if r.stark_w0 is None else f"{r.stark_w0:.3g}", r.stark_status,
                     "N/A" if r.stark_sac is None else f"{r.stark_sac:.3g}",
                     "N/A" if r.irsac_sa is None else f"{r.irsac_sa:.3g}", r.irsac_status, r.level_test,
                     f"{sac:.3g} ({meth})" if sac and sac > 1 else "1"])
    return summary, rows
