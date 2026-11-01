"""LTE validity check window for pyLIBS (McWhirter + Cristoforetti 2010 criteria)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from pylibs.core.lte_criteria import (
    BASIS_HELP, BASIS_LABELS, BASIS_SHORT, DE_BASES, DEFAULT_GAUNT, DEFAULT_SAFETY, K_B_EV, AtomicData, PlasmaState, TemplateLine as LTELine,
    check_lte, format_report, parse_bridges, parse_species, write_csv,
)
from pylibs.gui.helpers import _showerror, _showinfo, center_window

# Vacuum-UV resonance transitions missing from LIBS.db (NIST ASD). Used only if the species is analysed.
DEFAULT_BRIDGES = "H I=121.567:0.4164; O I=130.217:0.0520"


def lte_lines_from_template(app) -> list[LTELine]:
    """Convert the current pyLIBS template lines (active, assigned, with Ek) to LTE lines."""
    has_error = getattr(app, "_lte_line_has_error", None)
    out = []
    for t in getattr(app, "template_lines", []) or []:
        try:
            if callable(has_error) and has_error(t):
                continue
            el = str(getattr(t, "specie", "") or "").strip().capitalize()
            ion = int(float(getattr(t, "ion", 0) or 0))
            ek = float(getattr(t, "ek", 0.0) or 0.0)
            ei = float(getattr(t, "ei", 0.0) or 0.0)
            aki = float(getattr(t, "aki", 0.0) or 0.0)
            wl = float(getattr(t, "asswavelen", 0.0) or 0.0) or float(getattr(t, "wavelen", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if not el or el == "Empty" or ion <= 0 or ek <= 0 or aki <= 0:   # Aki < 0 = excluded point
            continue
        out.append(LTELine(el, ion, wl, ei, ek))
    return out


FIELD_HELP = {
    "kt": "Plasma temperature kT (eV), normally from the Saha-Boltzmann plot.",
    "sigma_kt": "Uncertainty of kT (eV). Filled automatically from the Saha-Boltzmann regression:\n"
                "σ_kT = kT²·σ_slope for one element; for the mean, the larger of the propagated\n"
                "regression error and the scatter between elements. Used for the worst case (T ± σ).",
    "ne": "Electron density (cm⁻³), normally from the Stark broadening of H-alpha.",
    "sigma_ne": "Uncertainty of Ne (cm⁻³). Filled automatically from the H-alpha fit covariance or the T–Ne\n"
                "self-consistent fit. Used for the worst case (Ne ± σ).",
    "tvar": "Characteristic time of variation of T and Ne (ns): t_var ≈ T / |dT/dt|.\n"
            "Enables the transient-plasma criterion: safety·τ_rel ≤ t_var. Leave blank to skip.",
    "d": "Characteristic length of the T, Ne gradients (mm): d ≈ T / |dT/dx|.\n"
         "Enables the spatial (diffusion) criterion: safety·λ ≤ d. Leave blank to skip.",
    "gaunt": "Effective Gaunt factor <g> of the van Regemorter collision rate (≈ 0.2 for ΔE/kT ≳ 1).\n"
             "Affects τ_rel and λ only.",
    "safety": "Factor translating '<<' into a number for the temporal and spatial criteria (default 10).\n"
              "Not applied to McWhirter, whose constant already includes a factor of 10.",
    "basis": BASIS_HELP,
    "species": "Species present in the plasma but not in the template (matrix, air): e.g. O I, N I, H I.",
    "bridge": "f12 of resonance transitions missing from LIBS.db (vacuum UV), format species=λ nm:f12; ...",
}


class ToolbarTooltip:
    """Hover help that stays inside the screen (multi-line text)."""

    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        ttk.Label(self.tip, text=self.text, relief="solid", borderwidth=1, padding=(6, 4),
                  background="#ffffe0", justify="left").pack()
        self.tip.update_idletasks()
        w, h = self.tip.winfo_reqwidth(), self.tip.winfo_reqheight()
        sw, sh = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        x = max(0, min(x, sw - w - 8))
        if y + h > sh:
            y = max(0, self.widget.winfo_rooty() - h - 4)
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def session_kt_sigma(app, kt: float):
    """sigma(kT) from the last Saha-Boltzmann fit, if it refers to this kT."""
    pair = getattr(app, "session_temperature_sigma", None)
    if not pair or pair[1] is None or not kt:
        return None
    k0, sig = pair
    return sig if abs(k0 - kt) <= 1e-4 * max(abs(kt), 1e-12) else None


def session_ne_sigma(app, ne: float):
    """sigma(Ne) from the H-alpha fit or the T-Ne fit, if it refers to this Ne."""
    pair = getattr(app, "session_ne_sigma", None)
    if not pair or pair[1] is None or not ne:
        return None
    n0, sig = pair
    return sig if abs(n0 - ne) <= 1e-4 * max(abs(ne), 1.0) else None


def libs_db_path(app) -> str:
    db = app.libs_db
    db.filename = app.options.libs_db_file
    db.connect()
    return db.filename


def run_lte_check(app, kt_ev: float, ne: float, **kw):
    """Non-GUI helper used by the CF-LIBS window status line."""
    lines = lte_lines_from_template(app)
    if not lines or kt_ev <= 0 or ne <= 0:
        return [], None
    sig = session_kt_sigma(app, kt_ev) or 0.0
    plasma = PlasmaState(temperature_k=kt_ev / K_B_EV, ne=ne, sigma_t_k=sig / K_B_EV,
                         sigma_ne=session_ne_sigma(app, ne) or 0.0)
    db = AtomicData(libs_db_path(app))
    try:
        res = check_lte(db, plasma, lines=lines, overrides=parse_bridges(DEFAULT_BRIDGES), **kw)
    finally:
        db.close()
    return res, plasma


def lte_status_text(results) -> str:
    mc = [v for v in results if v.mcwhirter_ok is not None]
    if not mc:
        return "LTE: n/a"
    bad = [v.gaps.label for v in mc if not v.mcwhirter_ok]
    return f"LTE McWhirter {len(mc) - len(bad)}/{len(mc)}" + (f" (fails: {', '.join(bad)})" if bad else " OK")


class LTECheckWindow(tk.Toplevel):
    COLS = ("Species", "lines", "ΔE used (eV)", "basis", "Ne,min (cm⁻³)", "Ne/Ne,min", "worst",
            "McWhirter", "f12", "τ_rel (ns)", "λ (µm)", "Temporal", "Spatial")

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("LTE check (McWhirter / Cristoforetti)")
        self.geometry("1200x660")
        self.minsize(900, 500)
        self.results = []
        self.plasma = None

        self.v = {k: tk.StringVar() for k in (
            "kt", "sigma_kt", "ne", "sigma_ne", "tvar", "d", "gaunt", "safety", "species", "bridge")}
        self.v["gaunt"].set(str(DEFAULT_GAUNT))
        self.v["safety"].set(f"{DEFAULT_SAFETY:g}")
        self.v["bridge"].set(DEFAULT_BRIDGES)
        self.basis = tk.StringVar(value=BASIS_LABELS["conservative"])

        top = ttk.Frame(self, padding=(6, 5))
        top.pack(fill="x")
        ttk.Button(top, text="Check LTE", command=self.compute).pack(side="left")
        ttk.Button(top, text="Use session kT / Ne", command=self.load_session).pack(side="left", padx=4)
        ttk.Button(top, text="Save CSV...", command=self.save_csv).pack(side="left", padx=4)
        ttk.Button(top, text="Save Report...", command=self.save_txt).pack(side="left")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=12, fill="x", expand=True)

        par = ttk.Frame(self, padding=(6, 0))
        par.pack(fill="x")
        c = 0
        self._tips = []
        for label, key, w in (("kT eV", "kt", 8), ("±σ kT", "sigma_kt", 6), ("Ne cm⁻³", "ne", 11),
                              ("±σ Ne", "sigma_ne", 9), ("t_var ns", "tvar", 7), ("d mm", "d", 6),
                              ("<g>", "gaunt", 5), ("safety", "safety", 4)):
            lab = ttk.Label(par, text=label)
            lab.grid(row=0, column=c, padx=(8, 2)); c += 1
            ent = ttk.Entry(par, textvariable=self.v[key], width=w)
            ent.grid(row=0, column=c); c += 1
            self._tips += [ToolbarTooltip(lab, FIELD_HELP[key]), ToolbarTooltip(ent, FIELD_HELP[key])]
        lab = ttk.Label(par, text="ΔE basis ⓘ")
        lab.grid(row=0, column=c, padx=(8, 2)); c += 1
        cb = ttk.Combobox(par, textvariable=self.basis, values=[BASIS_LABELS[k] for k in DE_BASES],
                          width=20, state="readonly")
        cb.grid(row=0, column=c)
        self._tips += [ToolbarTooltip(lab, BASIS_HELP), ToolbarTooltip(cb, BASIS_HELP)]

        ext = ttk.Frame(self, padding=(6, 3))
        ext.pack(fill="x")
        ext.columnconfigure(1, weight=1)
        lab = ttk.Label(ext, text="Extra species")
        lab.grid(row=0, column=0, sticky="e", padx=3)
        self._tips.append(ToolbarTooltip(lab, FIELD_HELP["species"]))
        ttk.Entry(ext, textvariable=self.v["species"]).grid(row=0, column=1, sticky="we")
        ttk.Label(ext, text='e.g. "O I, H I" (template species are always included)').grid(row=0, column=2, sticky="w", padx=4)
        lab = ttk.Label(ext, text="Manual bridge")
        lab.grid(row=1, column=0, sticky="e", padx=3)
        self._tips.append(ToolbarTooltip(lab, FIELD_HELP["bridge"]))
        ttk.Entry(ext, textvariable=self.v["bridge"]).grid(row=1, column=1, sticky="we")
        ttk.Label(ext, text="species=λ nm:f12 ; ...  (VUV resonances not in LIBS.db)").grid(row=1, column=2, sticky="w", padx=4)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=10)
        for col in self.COLS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=88, anchor="center")
        self.tree.tag_configure("bad", background="#f8d7da")
        self.tree.tag_configure("good", background="#d4edda")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.text = tk.Text(self, height=11, wrap="none", font=("Consolas", 9))
        self.text.pack(fill="both", padx=6, pady=(0, 6))

        self.load_session()
        center_window(self, master)
        self.after(100, self.compute)

    # ------------------------------------------------------------------
    def basis_key(self) -> str:
        inv = {v: k for k, v in BASIS_LABELS.items()}
        return inv.get(self.basis.get(), "conservative")

    def load_session(self):
        app = self.master_app
        kt = getattr(app, "session_temperature", None)
        ne = getattr(app, "session_ne", None)
        self.v["kt"].set(f"{kt:.6g}" if kt else "")
        self.v["ne"].set(f"{ne:.6g}" if ne else "")
        sig = session_kt_sigma(app, kt) if kt else None
        self.v["sigma_kt"].set(f"{sig:.3g}" if sig else "")
        sig_ne = session_ne_sigma(app, ne) if ne else None
        self.v["sigma_ne"].set(f"{sig_ne:.3g}" if sig_ne else "")
        src = f"kT from {getattr(app, 'session_temperature_source', None) or '—'}" \
              + (" (σ from fit)" if sig else "") + \
              f", Ne from {getattr(app, 'session_ne_source', None) or '—'}" \
              + (" (σ from fit)" if sig_ne else "")
        self.status_var.set(src)

    def _num(self, key, name, optional=False):
        s = self.v[key].get().strip().replace(",", ".")
        if not s:
            if optional:
                return None
            raise ValueError(f"{name} is required (run Saha-Boltzmann / H-alpha or type a value).")
        return float(s)

    def compute(self):
        try:
            kt = self._num("kt", "kT")
            sig_kt = self._num("sigma_kt", "σ kT", True) or 0.0
            tvar = self._num("tvar", "t_var", True)
            d = self._num("d", "d", True)
            self.plasma = PlasmaState(
                temperature_k=kt / K_B_EV, ne=self._num("ne", "Ne"), sigma_t_k=sig_kt / K_B_EV,
                sigma_ne=self._num("sigma_ne", "σ Ne", True) or 0.0,
                t_var_s=tvar * 1e-9 if tvar else None, d_var_cm=d * 0.1 if d else None,
                gaunt=self._num("gaunt", "<g>"), safety=self._num("safety", "safety"))
            lines = lte_lines_from_template(self.master_app)
            species = parse_species(self.v["species"].get()) if self.v["species"].get().strip() else None
            if not lines and not species:
                raise ValueError("No template lines with species, ion and Ek, and no extra species given.")
            bridges = parse_bridges(self.v["bridge"].get()) if self.v["bridge"].get().strip() else None
            db = AtomicData(libs_db_path(self.master_app))
            try:
                self.results = check_lte(db, self.plasma, species=species, lines=lines,
                                         basis=self.basis_key(), overrides=bridges)
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001
            self.status_var.set(str(e))
            _showerror(self, "LTE check", str(e))
            return
        self._show()
        self.master_app.last_lte_check = {"results": self.results, "plasma": self.plasma, "basis": self.basis_key()}
        msg = lte_status_text(self.results)
        self.status_var.set(msg)
        try:
            self.master_app.status(msg)
        except Exception:
            pass

    def _show(self):
        self.tree.delete(*self.tree.get_children())
        f = lambda x, s: "—" if x is None else format(x, s)  # noqa: E731
        ok = lambda b: "—" if b is None else ("OK" if b else "FAIL")  # noqa: E731
        for v in self.results:
            g = v.gaps
            vals = (g.label, g.n_lines, f(v.de_used_ev, ".3f"), BASIS_SHORT.get(v.de_basis, v.de_basis), f(v.ne_min, ".2e"),
                    f(v.ratio, ".3g"), f(v.ratio_worst, ".3g"), ok(v.mcwhirter_ok), f(g.f12, ".3g"),
                    f(None if v.tau_rel_worst_s is None else v.tau_rel_worst_s * 1e9, ".3g"),
                    f(None if v.lambda_worst_cm is None else v.lambda_worst_cm * 1e4, ".3g"),
                    ok(v.temporal_ok), ok(v.spatial_ok))
            flags = [x for x in (v.mcwhirter_ok, v.temporal_ok, v.spatial_ok) if x is not None]
            tag = "bad" if False in flags else ("good" if flags else "")
            self.tree.insert("", "end", values=vals, tags=(tag,))
        self.text.delete("1.0", "end")
        self.text.insert("1.0", format_report(self.results, self.plasma, self.basis_key()))

    def save_csv(self):
        if not self.results:
            _showinfo(self, "LTE check", "Nothing to save yet.")
            return
        fn = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if fn:
            write_csv(fn, self.results)

    def save_txt(self):
        if not self.results:
            _showinfo(self, "LTE check", "Nothing to save yet.")
            return
        fn = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if fn:
            Path(fn).write_text(format_report(self.results, self.plasma, self.basis_key()), encoding="utf-8")
