"""Outlier diagnostics for Saha-Boltzmann / CF-LIBS points (possible misassigned or blended lines)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from pylibs.core.plasma_fit import SBPoint, global_fit


@dataclass
class OutlierRow:
    index: int
    label: str
    element: str
    ion: int
    ek_ev: float
    active: bool
    residual: Optional[float] = None       # deleted residual (ln I)
    z: Optional[float] = None
    dkt: Optional[float] = None            # kT(line toggled) - kT(current): exclusion if active, restoration if not
    dlnne: Optional[float] = None          # ln Ne(line toggled) - ln Ne(current)
    testable: bool = True
    note: str = ""
    order: Optional[int] = None            # rank in the sequential suggestion (1 = first to remove)
    alternatives: list = field(default_factory=list)


def _counts(points, mask):
    c = {}
    for p, m in zip(points, mask):
        if m:
            c[p.element] = c.get(p.element, 0) + 1
    return c


def _fit(points, mask, kt0, ne0):
    sub = [p for p, m in zip(points, mask) if m]
    return global_fit(sub, kt0, ne0, fit_ne=True)


def _model(fit, p: SBPoint) -> float:
    q = fit.intercepts.get(p.element)
    if q is None:
        return float("nan")
    return q - p.x_raw / fit.kt + p.s * (math.log(6.04e21) + 1.5 * math.log(fit.kt) - math.log(fit.ne))


def _shift(points, mask, base):
    """(ΔkT, Δln Ne) of the global fit with `mask` relative to `base`; (None, None) if the fit fails."""
    try:
        f = _fit(points, mask, base.kt, base.ne)
    except Exception:  # noqa: BLE001
        return None, None
    return f.kt - base.kt, (math.log(f.ne) - math.log(base.ne)) if f.ne_fitted else 0.0


def analyse(points: list[SBPoint], active: list[bool], kt0: float, ne0: float, min_per_element: int = 3,
            plasma_shifts: bool = False):
    """Leave-one-out residuals for all lines (inactive lines are evaluated against the active fit)."""
    base = _fit(points, active, kt0, ne0)
    counts = _counts(points, active)
    rows = []
    for i, (p, a) in enumerate(zip(points, active)):
        row = OutlierRow(i, p.label, p.element, p.ion, p.ek_ev, a)
        if not a:
            row.residual = p.y - _model(base, p)
            row.note = "excluded"
            if plasma_shifts:
                m = list(active)
                m[i] = True
                row.dkt, row.dlnne = _shift(points, m, base)
        elif counts.get(p.element, 0) < min_per_element:
            row.testable = False
            row.residual = p.y - _model(base, p)
            row.note = f"only {counts.get(p.element, 0)} line(s) of {p.element}: cannot be tested"
            if plasma_shifts:
                m = list(active)
                m[i] = False
                row.dkt, row.dlnne = _shift(points, m, base)
        else:
            m = list(active)
            m[i] = False
            try:
                f = _fit(points, m, base.kt, base.ne)
                row.residual = p.y - _model(f, p)
                row.dkt = f.kt - base.kt
                row.dlnne = (math.log(f.ne) - math.log(base.ne)) if f.ne_fitted else 0.0
            except Exception as e:  # noqa: BLE001
                row.testable = False
                row.note = f"refit failed: {e}"
        rows.append(row)
    test = [abs(r.residual) for r in rows if r.active and r.testable and r.residual is not None]
    s = 1.4826 * sorted(test)[len(test) // 2] if test else 0.0
    s = max(s, 0.02)
    for r in rows:
        if r.residual is not None and (r.testable or not r.active):
            r.z = r.residual / s
    return base, rows, s


def sequential(points: list[SBPoint], active: list[bool], kt0: float, ne0: float, z_thr: float = 3.0,
               max_remove: int = 10, min_per_element: int = 3):
    """Remove the worst |z| > z_thr line, refit, repeat. Returns ordered list of point indices."""
    mask = list(active)
    order = []
    kt, ne = kt0, ne0
    for _ in range(max_remove):
        base, rows, _s = analyse(points, mask, kt, ne, min_per_element)
        kt, ne = base.kt, base.ne
        cand = [r for r in rows if r.active and r.testable and r.z is not None and abs(r.z) > z_thr]
        if not cand:
            break
        worst = max(cand, key=lambda r: abs(r.z))
        order.append(worst.index)
        mask[worst.index] = False
    return order


def mask_shift(points: list[SBPoint], active: list[bool], new_mask: list[bool], kt0: float, ne0: float):
    """(ΔkT, Δln Ne) between the global fits with new_mask and with active (several changes at once)."""
    base = _fit(points, active, kt0, ne0)
    if list(new_mask) == list(active):
        return 0.0, 0.0
    return _shift(points, new_mask, base)


def interpretation(residual: float) -> str:
    f = math.exp(residual)
    if residual > 0:
        return f"{f:.2g}× stronger than the trend: blend or misassignment?"
    return f"{1 / f:.2g}× weaker than the trend: self-absorption, gA or misassignment?"
