"""Interactive baseline removal preview for the main spectrum."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from pylibs.core.baseline import remove_baseline
from pylibs.gui.helpers import _showerror, center_window

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    FigureCanvasTkAgg = Figure = None


class BaselineRemovalDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.app = master
        self.title("Baseline Removal")
        self.geometry("820x610")
        self.minsize(640, 460)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.algorithm = tk.StringVar(value="AsLS")
        self.lam = tk.StringVar(value="1000000")
        self.p = tk.StringVar(value="0.01")
        self.iterations = tk.StringVar(value="50")
        self.tolerance = tk.StringVar(value="0.001")
        self.clip = tk.BooleanVar(value=False)
        controls = ttk.LabelFrame(self, text="Baseline parameters", padding=6)
        controls.pack(fill="x", padx=8, pady=6)
        ttk.Label(controls, text="Algorithm").grid(row=0, column=0, sticky="e", padx=3)
        combo = ttk.Combobox(controls, textvariable=self.algorithm, values=("AsLS", "airPLS"), state="readonly", width=10)
        combo.grid(row=0, column=1, sticky="w", padx=3)
        ttk.Label(controls, text="Smoothing λ").grid(row=0, column=2, sticky="e", padx=3)
        ttk.Entry(controls, textvariable=self.lam, width=12).grid(row=0, column=3, padx=3)
        ttk.Label(controls, text="Asymmetry p").grid(row=0, column=4, sticky="e", padx=3)
        self.p_entry = ttk.Entry(controls, textvariable=self.p, width=8)
        self.p_entry.grid(row=0, column=5, padx=3)
        ttk.Label(controls, text="Max iterations").grid(row=1, column=0, sticky="e", padx=3, pady=5)
        ttk.Entry(controls, textvariable=self.iterations, width=8).grid(row=1, column=1, sticky="w", padx=3)
        ttk.Label(controls, text="Tolerance").grid(row=1, column=2, sticky="e", padx=3)
        ttk.Entry(controls, textvariable=self.tolerance, width=12).grid(row=1, column=3, sticky="w", padx=3)
        ttk.Checkbutton(controls, text="Clip negative corrected intensities to zero", variable=self.clip).grid(row=1, column=4, columnspan=2, sticky="w", padx=4)
        combo.bind("<<ComboboxSelected>>", self._algorithm_changed)
        if Figure is not None and FigureCanvasTkAgg is not None:
            self.figure = Figure(figsize=(7.2, 4.2), dpi=90)
            self.axes = self.figure.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.figure, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=4)
        else:
            self.figure = self.axes = self.canvas = None
            ttk.Label(self, text="Matplotlib is required for graphical preview.").pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Preview is not applied until you select Apply.")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", padx=10)
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=8, pady=8)
        ttk.Button(buttons, text="Preview", command=self.preview).pack(side="left")
        ttk.Button(buttons, text="Apply", command=self.apply).pack(side="right", padx=3)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=3)
        for variable in (self.algorithm, self.lam, self.p, self.iterations, self.tolerance, self.clip):
            variable.trace_add("write", self._schedule_preview)
        self._preview_job = None
        center_window(self, master)
        self.after_idle(self.preview)

    def _algorithm_changed(self, _event=None):
        self.p_entry.configure(state="normal" if self.algorithm.get() == "AsLS" else "disabled")
        self.preview()

    def _schedule_preview(self, *_args):
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(250, self.preview)

    def _compute(self):
        if not self.app.spectra:
            raise ValueError("Load a spectrum before removing its baseline.")
        sp = self.app.spectra[0]
        return sp, remove_baseline(
            sp.x, sp.y, algorithm=self.algorithm.get(), lam=float(self.lam.get()),
            p=float(self.p.get()), max_iter=int(self.iterations.get()),
            tolerance=float(self.tolerance.get()), clip_negative=self.clip.get(),
        )

    def preview(self):
        self._preview_job = None
        try:
            sp, (baseline, corrected) = self._compute()
            if self.axes is not None:
                self.axes.clear()
                self.axes.plot(sp.x, sp.y, color="#222222", linewidth=0.9, label="Original spectrum")
                self.axes.plot(sp.x, baseline, color="#d95f02", linewidth=1.2, label="Estimated baseline")
                self.axes.plot(sp.x, corrected, color="#1b9e77", linewidth=0.9, label="Corrected spectrum")
                self.axes.set_xlabel("Wavelength")
                self.axes.set_ylabel("Intensity")
                self.axes.legend(loc="best")
                self.axes.grid(True, alpha=0.2)
                self.figure.tight_layout()
                self.canvas.draw_idle()
            self.status.set(f"Preview: {len(sp.x)} points; original spectrum remains unchanged.")
        except Exception as exc:
            self.status.set(str(exc))

    def apply(self):
        try:
            sp, (baseline, corrected) = self._compute()
        except Exception as exc:
            _showerror(self, "Baseline Removal", str(exc))
            return
        sp.y = corrected
        sp.baseline = baseline
        sp.baseline_algorithm = self.algorithm.get()
        sp.capture_source()
        self.app.invalidate_cflibs_results()
        self.app.invalidate_self_absorption_analysis()
        self.app.last_theoretical_spectrum = None
        self.app.redraw(preserve_view=True)
        if self.app.active_window and self.app.active_window.winfo_exists():
            self.app.active_window.refresh()
        self.app.status(f"Baseline removed from {sp.name} using {self.algorithm.get()}.")
        self.destroy()
