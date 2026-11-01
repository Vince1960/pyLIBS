"""Influence of each line on the CF-LIBS concentrations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from pylibs.core.cflibs_uncertainty import CFInputs, cflibs_concentrations


@dataclass
class Influence:
    index: int
    restore: bool                       # True: effect of restoring an excluded line
    kt: float                           # kT after the change (eV)
    ne: float                           # Ne after the change (cm^-3)
    total: dict = field(default_factory=dict)    # element -> (Δ molar %, Δ mass %)
    direct: dict = field(default_factory=dict)   # element -> (Δ molar %, Δ mass %) at unchanged kT, Ne
    new: dict = field(default_factory=dict)      # element -> (molar %, mass %) after the change
    plasma_shift: bool = True           # False if the kT/Ne shift could not be computed
    in_cflibs: bool = True              # False if the line is not used by CF-LIBS (only acts via kT/Ne)


def compose(cf: list, mask: list, inp: CFInputs, kt: float, ne: float) -> dict:
    """CF-LIBS composition {element: (molar %, mass %)} using the lines where mask is True."""
    groups = {}
    for c, m in zip(cf, mask):
        if c is not None and m:
            groups.setdefault(c[0], []).append(c[1])
    if not groups or kt <= 0 or ne <= 0:
        return {}
    res = cflibs_concentrations(CFInputs(groups, inp.mass, inp.eion, inp.z), kt, ne)
    return {el: (v[0], v[1]) for el, v in res.items()}


def delta(new: dict, base: dict) -> dict:
    out = {}
    for el in set(new) | set(base):
        n = new.get(el, (0.0, 0.0))
        b = base.get(el, (0.0, 0.0))
        out[el] = (n[0] - b[0], n[1] - b[1])
    return out


def line_influence(cf: list, active: list, i: int, inp: CFInputs, kt: float, ne: float, base: dict,
                   dkt: Optional[float] = None, dlnne: Optional[float] = None) -> Influence:
    """Change of the composition when line i is toggled (dkt / dlnne from the global Saha-Boltzmann fit)."""
    mask = list(active)
    mask[i] = not mask[i]
    shift = dkt is not None
    kt2 = kt + (dkt or 0.0)
    ne2 = ne * math.exp(dlnne or 0.0)
    if kt2 <= 0.05:
        kt2, shift = kt, False
    direct_new = compose(cf, mask, inp, kt, ne)
    total_new = compose(cf, mask, inp, kt2, ne2) if shift else direct_new
    return Influence(i, not active[i], kt2, ne2, delta(total_new, base), delta(direct_new, base), total_new,
                     shift, cf[i] is not None)


def combined_change(cf: list, active: list, new_mask: list, inp: CFInputs, kt: float, ne: float,
                    dkt: Optional[float] = None, dlnne: Optional[float] = None):
    """Composition after several exclusions / restorations at once. Returns (new composition, Δ, kT', Ne')."""
    base = compose(cf, active, inp, kt, ne)
    kt2 = kt + (dkt or 0.0)
    ne2 = ne * math.exp(dlnne or 0.0)
    if kt2 <= 0.05:
        kt2 = kt
    new = compose(cf, new_mask, inp, kt2, ne2)
    return new, delta(new, base), kt2, ne2


def ranking(influences: list, element: str, unit: int = 0) -> list:
    """Lines ordered by their effect on one element (largest increase first). unit 0 = molar %, 1 = mass %."""
    rows = [(inf.total.get(element, (0.0, 0.0))[unit], inf) for inf in influences]
    return sorted(rows, key=lambda r: -r[0])
