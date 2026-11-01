"""Outlier lines window: leave-one-out screening of Saha-Boltzmann points, influence of each line on the"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pylibs.core.line_influence import combined_change, compose, line_influence
from pylibs.core.outliers import analyse, interpretation, mask_shift, sequential
from pylibs.gui.helpers import _showerror, center_window
from pylibs.gui.lte_dialog import ToolbarTooltip

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    Figure = FigureCanvasTkAgg = None

HELP = (
    "Each line is compared with the global Saha-Boltzmann fit (common kT and Ne, one intercept per element)\n"
    "refitted WITHOUT that line. z = deleted residual / robust σ (1.4826·MAD).\n"
    "Suggested exclusions come from sequential screening: remove the worst |z| > threshold, refit, repeat.\n"
    "Nothing is changed until you press 'Apply changes'. Exclusion = negative Aki, as with Shift-click in the plots."
)
HELP_INFLUENCE = (
    "Δ columns: change of the CF-LIBS concentration of each element if the line is toggled —\n"
    "EXCLUDED when it is active, RESTORED when it is already excluded (rows marked ✕ / ↺).\n"
    "Positive = the element increases, negative = it decreases.\n"
    "• direct (via intercept): the line changes the Boltzmann intercept of its own species; through the\n"
    "  normalization to 100 % all the other elements move in the opposite direction.\n"
    "• via kT / Ne: the line also shifts the plasma temperature and Ne (global Saha-Boltzmann fit with and\n"
    "  without the line); this acts on every element. Untick 'include kT/Ne shift' to see the direct part only.\n"
    "The CF-LIBS model is the same as the CF-LIBS window, at its kT and Ne."
)
HELP_MARK = ("Double-click a row (or click a point / bar) to mark it.\n"
             "☐ → ☑ : active line, mark to EXCLUDE.\n"
             "✕ → ↺ : excluded line, mark to RESTORE.")
UNITS = ("Δ molar % (points)", "Δ relative (%)", "Δ mass % (points)")
BASE_COLS = ("Mark", "Line", "Ek eV", "residual", "z", "ΔkT if toggled", "status")
TAIL_COLS = ("interpretation", "possible alternatives")


class OutlierWindow(tk.Toplevel):
    def __init__(self, master, backend):
        super().__init__(master)
        self.master_app = master
        self.backend = backend
        self.title("Outlier lines — misassignments and influence on the concentrations")
        self.geometry("1400x860")
        self.minsize(1050, 640)
        self.rows = []
        self.choice = {}           # index -> bool (exclude an active line / restore an excluded one)
        self.influence = {}        # index -> Influence
        self.cf = None
        self.cf_msg = ""
        self.cf_base = {}
        self.elements = []
        self._tips = []
        self._pick_map = {}

        top = ttk.Frame(self, padding=(6, 5))
        top.pack(fill="x")
        b = ttk.Button(top, text="Check", command=self.run)
        b.pack(side="left")
        self._tips.append(ToolbarTooltip(b, HELP))
        b = ttk.Button(top, text="Apply changes", command=self.apply)
        b.pack(side="left", padx=4)
        self._tips.append(ToolbarTooltip(b, "Exclude the lines marked ☑ and restore the lines marked ↺."))
        ttk.Button(top, text="Restore all excluded", command=self.restore_all).pack(side="left")
        ttk.Label(top, text="z threshold").pack(side="left", padx=(14, 2))
        self.zthr = tk.StringVar(value="3.0")
        ttk.Entry(top, textvariable=self.zthr, width=5).pack(side="left")
        ttk.Label(top, text="search ± Å").pack(side="left", padx=(10, 2))
        self.tol = tk.StringVar(value="0.3")
        ttk.Entry(top, textvariable=self.tol, width=5).pack(side="left")
        ttk.Label(top, text="min. lines/element").pack(side="left", padx=(10, 2))
        self.minpe = tk.StringVar(value="3")
        ttk.Entry(top, textvariable=self.minpe, width=3).pack(side="left")
        self.status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=12)

        inf = ttk.Frame(self, padding=(6, 0))
        inf.pack(fill="x")
        lab = ttk.Label(inf, text="Influence on the concentrations:")
        lab.pack(side="left")
        self._tips.append(ToolbarTooltip(lab, HELP_INFLUENCE))
        self.unit = tk.StringVar(value=UNITS[0])
        cb = ttk.Combobox(inf, textvariable=self.unit, values=UNITS, width=18, state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._show())
        self.with_plasma = tk.BooleanVar(value=True)
        c = ttk.Checkbutton(inf, text="include kT/Ne shift", variable=self.with_plasma,
                            command=self._recompute_influence)
        c.pack(side="left", padx=6)
        self._tips.append(ToolbarTooltip(c, HELP_INFLUENCE))
        ttk.Label(inf, text="   Plot").pack(side="left")
        self.plot_mode = tk.StringVar(value="z vs E_k")
        self.plot_cb = ttk.Combobox(inf, textvariable=self.plot_mode, values=["z vs E_k"], width=20, state="readonly")
        self.plot_cb.pack(side="left", padx=4)
        self.plot_cb.bind("<<ComboboxSelected>>", lambda _e: self._plot())

        self.preview_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.preview_var, padding=(8, 4), foreground="#1a4d8f",
                  wraplength=1350, justify="left").pack(anchor="w", fill="x")

        mid = ttk.PanedWindow(self, orient="vertical")
        mid.pack(fill="both", expand=True, padx=6, pady=2)
        tf = ttk.Frame(mid)
        tbl = ttk.Frame(tf)
        tbl.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tbl, columns=BASE_COLS + TAIL_COLS, show="headings", height=11)
        ysb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="left", fill="y")
        xsb.pack(fill="x")
        self.tree.tag_configure("sugg", background="#fde2c8")
        self.tree.tag_configure("excl", foreground="#888888")
        self.tree.tag_configure("chk", background="#f8d7da")
        self.tree.tag_configure("rest", background="#d4edda", foreground="#1e5631")
        self.tree.bind("<Double-1>", self._toggle_row)
        self.tree.bind("<space>", self._toggle_row)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._detail())
        self._tips.append(ToolbarTooltip(self.tree, HELP_MARK + "\n\n" + HELP_INFLUENCE))
        self.detail = tk.Text(tf, height=7, wrap="none", font=("Consolas", 9))
        self.detail.pack(fill="x", pady=(4, 0))
        mid.add(tf, weight=3)
        pf = ttk.Frame(mid)
        if Figure is not None:
            self.fig = Figure(figsize=(9, 3.4), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=pf)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvas.mpl_connect("pick_event", self._on_pick)
        else:
            self.fig = self.canvas = None
        mid.add(pf, weight=2)
        ttk.Label(self, text="Double-click a row (or click a point/bar) to mark it.  ☑ = exclude (red row),  "
                  "↺ = restore an excluded line (green row),  orange = suggested by the screening,  grey ✕ = excluded.",
                  padding=(8, 0, 8, 6), foreground="#555").pack(anchor="w")
        center_window(self, master)
        self.after(150, self.run)

    # ------------------------------------------------------------------ analysis
    def run(self):
        try:
            self.points, self.lines, self.active, self.centers = self.backend.points(self.master_app)
            if sum(self.active) < 4:
                raise ValueError("Too few active Saha-Boltzmann points.")
            app = self.master_app
            kt0 = getattr(app, "session_temperature", None) or 1.0
            ne0 = getattr(app, "session_ne", None) or 1e17
            zthr, minpe = float(self.zthr.get()), int(float(self.minpe.get()))
            self.base, self.rows, self.scale = analyse(self.points, self.active, kt0, ne0, minpe, plasma_shifts=True)
            self.order = sequential(self.points, self.active, self.base.kt, self.base.ne, zthr, min_per_element=minpe)
            tol = float(self.tol.get())
            for r in self.rows:
                r.order = self.order.index(r.index) + 1 if r.index in self.order else None
                if r.order or (r.z is not None and abs(r.z) > zthr) or not r.active:
                    r.alternatives = self.backend.alternatives(app, self.centers[r.index], tol, r.element, r.ion)
            self.choice = {r.index: (r.order is not None) if r.active else False for r in self.rows}
        except Exception as e:  # noqa: BLE001
            _showerror(self, "Outlier lines", str(e))
            return
        self._load_cf()
        self._recompute_influence()

    def _load_cf(self):
        self.cf = None
        self.cf_msg = ""
        self.cf_base = {}
        cf_data = getattr(self.backend, "cf_data", None)
        if cf_data is None:
            self.cf_msg = "Influence on the concentrations not available (no CF-LIBS backend)."
            return
        try:
            self.cf, self.cf_inp, self.cf_kt, self.cf_ne, self.cf_source = cf_data(self.master_app, self.lines)
            self.cf_base = compose(self.cf, self.active, self.cf_inp, self.cf_kt, self.cf_ne)
            if not self.cf_base:
                raise ValueError("no CF-LIBS lines")
        except Exception as e:  # noqa: BLE001
            self.cf = None
            self.cf_base = {}
            self.cf_msg = f"Influence on the concentrations not available: {e}"

    def _recompute_influence(self):
        self.influence = {}
        if self.cf is not None:
            plasma = self.with_plasma.get()
            for r in self.rows:
                try:
                    self.influence[r.index] = line_influence(
                        self.cf, self.active, r.index, self.cf_inp, self.cf_kt, self.cf_ne, self.cf_base,
                        r.dkt if plasma else None, r.dlnne if plasma else None)
                except Exception:  # noqa: BLE001
                    pass
            self.elements = sorted(self.cf_base, key=lambda el: -self.cf_base[el][0])
        else:
            self.elements = []
        values = ["z vs E_k"] + [f"Influence on {el}" for el in self.elements]
        self.plot_cb.configure(values=values)
        if self.plot_mode.get() not in values:
            self.plot_mode.set("z vs E_k")
        self._show()

    # ------------------------------------------------------------------ formatting
    def _unit_index(self):
        return UNITS.index(self.unit.get()) if self.unit.get() in UNITS else 0

    def _dval(self, el, d):
        """Δ in the selected unit (None if not defined)."""
        u = self._unit_index()
        if u == 1:
            b = self.cf_base.get(el, (0.0, 0.0))[0]
            return 100.0 * d[0] / b if b > 0 else None
        return d[1] if u == 2 else d[0]

    def _fmt_delta(self, el, d):
        v = self._dval(el, d)
        if v is None:
            return "new" if d[0] > 0 else "—"
        if abs(v) < 5e-4:
            return "0"
        return f"{v:+.1f} %" if self._unit_index() == 1 else f"{v:+.3g}"

    def _new_mask(self):
        return [a != bool(self.choice.get(i, False)) for i, a in enumerate(self.active)]

    # ------------------------------------------------------------------ table
    def _show(self):
        if not self.rows:
            return
        zthr = float(self.zthr.get())
        dcols = tuple(f"Δ{el}" for el in self.elements)
        cols = BASE_COLS + dcols + TAIL_COLS
        self.tree.configure(columns=cols)
        widths = dict(zip(BASE_COLS, (48, 120, 52, 66, 52, 98, 92)))
        widths.update({c: 74 for c in dcols})
        widths.update({"interpretation": 290, "possible alternatives": 400})
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], minwidth=40, stretch=False,
                             anchor="w" if col in TAIL_COLS else "center")
        self.tree.delete(*self.tree.get_children())
        rows = sorted(self.rows, key=lambda r: (not r.active, r.order is None, -(abs(r.z) if r.z is not None else -1)))
        for r in rows:
            alt = "; ".join(f"{'*' if a[0] else ''}{a[1]} {'I' * a[2] if a[2] in (1, 2) else a[2]} {a[3]:.2f} ({a[4]:g})"
                            for a in r.alternatives) if r.alternatives else ""
            marked = bool(self.choice.get(r.index))
            if r.active:
                status = f"suggested #{r.order}" if r.order else ("|z| > thr" if r.z is not None and abs(r.z) > zthr
                                                                   else ("not testable" if not r.testable else "ok"))
                mark = "☑" if marked else "☐"
                tag = "chk" if marked else ("sugg" if r.order else "")
            else:
                status = "to restore" if marked else "excluded"
                mark = "↺" if marked else "✕"
                tag = "rest" if marked else "excl"
            inf = self.influence.get(r.index)
            dvals = tuple(self._fmt_delta(el, inf.total.get(el, (0.0, 0.0))) if inf else "" for el in self.elements)
            self.tree.insert("", "end", iid=str(r.index), values=(
                mark, r.label, f"{r.ek_ev:.2f}",
                "—" if r.residual is None else f"{r.residual:+.2f}",
                "—" if r.z is None else f"{r.z:+.1f}",
                "—" if r.dkt is None else f"{r.dkt:+.4f} eV",
                status) + dvals + (self._interp(r, zthr), alt), tags=(tag,))
        n_sugg = len(self.order)
        n_ex = sum(1 for r in self.rows if not r.active)
        self.status_var.set(f"kT = {self.base.kt:.4f} eV, Ne = {self.base.ne:.2e} cm⁻³ (global fit), robust σ = "
                            f"{self.scale:.3f}; {n_sugg} suggested exclusion(s), {n_ex} excluded line(s). "
                            "* = element present in the template.")
        self._preview()
        self._plot()
        self._detail()

    @staticmethod
    def _interp(r, zthr):
        if not r.testable and r.active:
            return r.note
        if r.residual is None:
            return ""
        if not r.active or r.order or (r.z is not None and abs(r.z) > zthr):
            return interpretation(r.residual)
        return ""

    # ------------------------------------------------------------------ combined preview
    def preview_text(self) -> str:
        if self.cf is None:
            return self.cf_msg
        unit = 1 if self._unit_index() == 2 else 0
        uname = "mass %" if unit else "molar %"
        now = "  ·  ".join(f"{el} {self.cf_base[el][unit]:.3g}" for el in self.elements)
        txt = (f"CF-LIBS now ({uname}; kT = {self.cf_kt:.4g} eV, Ne = {self.cf_ne:.3g} cm⁻³, {self.cf_source}):  "
               f"{now}")
        new_mask = self._new_mask()
        n_ex = sum(1 for a, m in zip(self.active, new_mask) if a and not m)
        n_re = sum(1 for a, m in zip(self.active, new_mask) if not a and m)
        if not (n_ex or n_re):
            return txt + "\nNo line marked: double-click rows to see the combined effect of excluding / restoring them."
        dkt = dln = None
        if self.with_plasma.get():
            try:
                dkt, dln = mask_shift(self.points, self.active, new_mask, self.base.kt, self.base.ne)
            except Exception:  # noqa: BLE001
                dkt = dln = None
        try:
            new, d, kt2, ne2 = combined_change(self.cf, self.active, new_mask, self.cf_inp, self.cf_kt, self.cf_ne,
                                               dkt, dln)
        except Exception as e:  # noqa: BLE001
            return txt + f"\nAfter the marked changes: not computable ({e})"
        after = "  ·  ".join(f"{el} {new.get(el, (0.0, 0.0))[unit]:.3g} ({d.get(el, (0.0, 0.0))[unit]:+.2g})"
                             for el in self.elements)
        return txt + (f"\nAfter the marked changes ({n_ex} to exclude, {n_re} to restore; kT ≈ {kt2:.4g} eV, "
                      f"Ne ≈ {ne2:.3g} cm⁻³):  {after}")

    def _preview(self):
        self.preview_var.set(self.preview_text())

    # ------------------------------------------------------------------ detail of the selected line
    def detail_text(self, idx: int) -> str:
        r = next((x for x in self.rows if x.index == idx), None)
        inf = self.influence.get(idx)
        if r is None or inf is None:
            return self.cf_msg or ""
        action = "RESTORING this excluded line" if inf.restore else "EXCLUDING this line"
        head = f"{r.label}: effect of {action}"
        if inf.plasma_shift and self.with_plasma.get():
            head += f"   (kT {self.cf_kt:.4f} → {inf.kt:.4f} eV, Ne {self.cf_ne:.3g} → {inf.ne:.3g} cm⁻³)"
        elif self.with_plasma.get():
            head += "   (kT/Ne shift not computable: direct effect only)"
        if not inf.in_cflibs:
            head += "\n  The line is not used by CF-LIBS: it acts only through kT / Ne."
        unit = 1 if self._unit_index() == 2 else 0
        un = "mass %" if unit else "molar %"
        out = [head, f"  {'element':8s}{'now':>10s}{'after':>10s}{'Δ total':>10s}{'Δ rel.':>9s}"
                     f"{'via intercept':>15s}{'via kT/Ne':>11s}   ({un})"]
        for el in self.elements:
            b = self.cf_base.get(el, (0.0, 0.0))[unit]
            n = inf.new.get(el, (0.0, 0.0))[unit]
            t = inf.total.get(el, (0.0, 0.0))[unit]
            dr = inf.direct.get(el, (0.0, 0.0))[unit]
            rel = f"{100 * t / b:+.1f}%" if b > 0 else "new"
            out.append(f"  {el:8s}{b:10.4g}{n:10.4g}{t:+10.3g}{rel:>9s}{dr:+15.3g}{t - dr:+11.3g}")
        return "\n".join(out)

    def _detail(self):
        self.detail.delete("1.0", "end")
        sel = self.tree.focus() or (self.tree.selection()[0] if self.tree.selection() else "")
        if not sel:
            self.detail.insert("1.0", self.cf_msg or "Select a line to see how much it raises or lowers each "
                               "concentration (and how much of it comes from the intercept and from kT / Ne).")
            return
        self.detail.insert("1.0", self.detail_text(int(sel)))

    # ------------------------------------------------------------------ plots
    def _plot(self):
        if self.fig is None or not self.rows:
            return
        self.fig.clear()
        self._pick_map = {}
        mode = self.plot_mode.get()
        if mode.startswith("Influence on ") and self.influence:
            self._plot_influence(mode.split("Influence on ", 1)[1])
        else:
            self._plot_z()
        self.canvas.draw_idle()

    def _plot_z(self):
        ax = self.fig.add_subplot(111)
        zthr = float(self.zthr.get())
        for r in self.rows:
            if r.z is None:
                continue
            marked = self.choice.get(r.index)
            if not r.active:
                st = dict(marker="P", color="#2ca02c", s=60, edgecolors="k") if marked else \
                    dict(marker="x", color="#999999", s=40)
            elif marked:
                st = dict(marker="o", color="#d62728", s=60, edgecolors="k")
            elif r.order:
                st = dict(marker="o", color="#ff7f0e", s=50)
            else:
                st = dict(marker="o", color="#1f77b4", s=30)
            art = ax.scatter([r.ek_ev], [r.z], picker=6, **st)
            self._pick_map[art] = r.index
            if r.order or not r.active or abs(r.z) > zthr:
                ax.annotate(r.label, (r.ek_ev, r.z), fontsize=7, xytext=(4, 3), textcoords="offset points")
        ax.axhline(zthr, color="#d62728", ls="--", lw=1)
        ax.axhline(-zthr, color="#d62728", ls="--", lw=1)
        ax.axhline(0, color="#444", lw=0.8)
        ax.set_xlabel("E_k (eV)")
        ax.set_ylabel("z (deleted residual / robust σ)")
        ax.set_title("Leave-one-out residuals of the global Saha-Boltzmann fit  (green + = marked to restore)",
                     fontsize=9)
        ax.grid(True, ls="--", lw=0.5, alpha=0.5)
        self.fig.tight_layout()

    def _plot_influence(self, el, top: int = 30):
        draw_influence(self.fig, self.rows, self.influence, el, self._dval, self.choice, self.unit.get(),
                       self.with_plasma.get(), self._pick_map, top)

    # ------------------------------------------------------------------ marking
    def _toggle(self, idx):
        r = next((x for x in self.rows if x.index == idx), None)
        if r is None:
            return
        self.choice[idx] = not self.choice.get(idx, False)
        self._show()
        try:
            self.tree.selection_set(str(idx))
            self.tree.focus(str(idx))
            self.tree.see(str(idx))
        except Exception:
            pass
        self._detail()

    def _toggle_row(self, _e=None):
        sel = self.tree.focus()
        if sel:
            self._toggle(int(sel))
        return "break"

    def _on_pick(self, event):
        idx = self._pick_map.get(event.artist)
        if idx is not None:
            self._toggle(idx)

    # ------------------------------------------------------------------ apply
    def apply(self):
        n_ex = n_re = 0
        for idx, flag in self.choice.items():
            if not flag:
                continue
            if self.active[idx]:
                self.backend.set_active(self.lines[idx], False)
                n_ex += 1
            else:
                self.backend.set_active(self.lines[idx], True)
                n_re += 1
        self._after_change(f"{n_ex} line(s) excluded, {n_re} restored")

    def restore_all(self):
        n = 0
        for t, a in zip(self.lines, self.active):
            if not a:
                self.backend.set_active(t, True)
                n += 1
        self._after_change(f"{n} line(s) restored")

    def _after_change(self, msg):
        app = self.master_app
        try:
            app.notify_template_changed(redraw=True)
        except Exception:
            pass
        for attr in ("saha_window", "cflibs_window"):
            win = getattr(app, attr, None)
            try:
                if win is not None and win.winfo_exists():
                    win.compute()
            except Exception:
                pass
        self.run()
        self.status_var.set(msg + " — " + self.status_var.get())
        try:
            app.status(msg)
        except Exception:
            pass


def draw_influence(fig, rows, influence, el, dval, choice, unit_label, with_plasma, pick_map=None, top=30):
    """Horizontal bars: change of element `el` when each line is excluded (or, hatched, restored)."""
    ax = fig.add_subplot(111)
    items = []
    for r in rows:
        inf = influence.get(r.index)
        if inf is None:
            continue
        v = dval(el, inf.total.get(el, (0.0, 0.0)))
        if v is None:
            continue
        items.append((v, r))
    items.sort(key=lambda t: -abs(t[0]))
    shown = sorted(items[:top], key=lambda t: t[0])
    for k, (v, r) in enumerate(shown):
        marked = choice.get(r.index)
        color = "#d62728" if v > 0 else "#1f77b4"
        bars = ax.barh(k, v, color=color, alpha=0.85 if r.active else 0.45, hatch=None if r.active else "//",
                       edgecolor="k" if marked else color, linewidth=1.6 if marked else 0.5, picker=True)
        if pick_map is not None:
            for patch in bars.patches:
                pick_map[patch] = r.index
    ax.set_yticks(range(len(shown)))
    ax.set_yticklabels([("↺ " if not r.active else "") + r.label + (" ☑" if choice.get(r.index) and r.active else "")
                        for _v, r in shown], fontsize=7)
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_xlabel(f"change of {el} ({unit_label.replace('Δ ', '')})")
    part = "incl. kT/Ne shift" if with_plasma else "intercept only"
    ax.set_title(f"How each line moves {el}: change if the line is excluded (hatched: if restored); "
                 f"red = {el} rises, blue = falls; {part}", fontsize=8.5)
    ax.grid(True, axis="x", ls="--", lw=0.5, alpha=0.5)
    if len(items) > top:
        ax.text(0.99, 0.01, f"{top} largest of {len(items)} lines", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=7, color="#555")
    fig.tight_layout()
