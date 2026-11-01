"""Monte Carlo uncertainty propagation for the pyLIBS CF-LIBS concentrations."""

from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

KT_TO_K = 11604.45
SAHA_C = 6.04e21
SOURCES = ("intensity", "gA", "SAC", "kT", "Ne")


@dataclass
class MCPoint:
    x: float                 # E_k (eV)
    y: float                 # ln(I/gA), response- and SAC-corrected exactly as in CF-LIBS
    s_int: float = 0.0       # σ ln I
    s_gA: float = 0.0        # σ ln gA
    s_sac: float = 0.0       # σ ln SAC
    label: str = ""


class ZTable:
    """Partition function Z(T) with the same linear interpolation and end clamping as LibsDatabase."""

    def __init__(self, tables: dict):
        self.t = {k: (sorted(v)) for k, v in tables.items() if v}

    def __call__(self, element: str, ion: int, temperature: float) -> float:
        pts = self.t.get((element, ion))
        if not pts:
            return 1.0
        Ts = [p[0] for p in pts]
        if temperature <= Ts[0]:
            return pts[0][1]
        if temperature >= Ts[-1]:
            return pts[-1][1]
        i = bisect.bisect_right(Ts, temperature)
        (t0, z0), (t1, z1) = pts[i - 1], pts[i]
        return z0 + (z1 - z0) * (temperature - t0) / (t1 - t0)


@dataclass
class CFInputs:
    groups: dict             # (element, ion) -> list[MCPoint]
    mass: dict               # element -> amu
    eion: dict               # element -> eV
    z: Callable              # z(element, ion, T_K)


def cflibs_concentrations(inp: CFInputs, kt: float, ne: float, ys: Optional[dict] = None,
                          weighted: bool = False) -> dict:
    """Deterministic CF-LIBS; ys optionally overrides the y values {(el, ion): [y...]}. Returns"""
    T = kt * KT_TO_K
    q = {}
    for key, pts in inp.groups.items():
        yv = ys[key] if ys is not None else [p.y for p in pts]
        if weighted:
            w = [1.0 / max(p.s_int ** 2 + p.s_gA ** 2 + p.s_sac ** 2, 1e-6) for p in pts]
            q[key] = sum(wi * (yi + p.x / kt) for wi, yi, p in zip(w, yv, pts)) / sum(w)
        else:
            q[key] = sum(yi + p.x / kt for yi, p in zip(yv, pts)) / len(pts)
    conc, massr, ratio = {}, {}, {}
    for el in sorted({k[0] for k in inp.groups}):
        z1 = inp.z(el, 1, T)
        z2 = inp.z(el, 2, T)
        n1 = math.exp(q[(el, 1)]) * z1 if (el, 1) in q else 0.0
        n2 = math.exp(q[(el, 2)]) * z2 if (el, 2) in q else 0.0
        eion = inp.eion.get(el, 0.0)
        saha = SAHA_C / ne * kt ** 1.5 * (z2 / z1 if z1 else 1.0) * math.exp(-eion / kt) if ne else 0.0
        if n1 > 0 and n2 <= 0:
            n2 = n1 * saha
        elif n2 > 0 and n1 <= 0 and saha > 0:
            n1 = n2 / saha
        conc[el] = n1 + n2
        massr[el] = inp.mass.get(el, 1.0) * conc[el]
        ratio[el] = n2 / n1 if n1 > 0 else float("inf")
    tn = sum(conc.values()) or 1.0
    tm = sum(massr.values()) or 1.0
    return {el: (100.0 * conc[el] / tn, 100.0 * massr[el] / tm, ratio[el]) for el in conc}


@dataclass
class Stats:
    mean: float
    sd: float
    p16: float
    p50: float
    p84: float
    p2_5: float
    p97_5: float
    mode: float = float("nan")       # most probable value (peak of the kernel density estimate)
    skew: float = 0.0                # sample skewness
    hdi68: tuple = ()                # shortest interval containing 68 % of the draws
    bandwidth: float = 0.0
    se: dict = field(default_factory=dict)   # Monte Carlo standard error of each statistic (bootstrap), see STAT_KEYS


# statistics that receive a bootstrap standard error
STAT_KEYS = ("mode", "mean", "p50", "sd", "skew", "hdi_lo", "hdi_hi", "p2_5", "p97_5")
STAT_NAMES = {"mode": "most probable", "mean": "mean", "p50": "median", "sd": "σ", "skew": "skewness",
              "hdi_lo": "68 % HDI low", "hdi_hi": "68 % HDI high", "p2_5": "2.5 % percentile",
              "p97_5": "97.5 % percentile"}


def kde_mode(v: list[float], grid: int = 1024):
    """Peak of a Gaussian kernel density estimate (Silverman bandwidth). Returns (mode, bandwidth, xs, density)."""
    import numpy as np
    a = np.asarray(v, dtype=float)
    n = a.size
    sd = a.std(ddof=1) if n > 1 else 0.0
    iqr = np.subtract(*np.percentile(a, [75, 25])) if n > 3 else 0.0
    sig = min(sd, iqr / 1.349) if iqr > 0 else sd
    if sig <= 0:
        return float(a.mean()), 0.0, a, np.ones_like(a)
    h = 0.9 * sig * n ** (-0.2)
    lo, hi = a.min() - 3 * h, a.max() + 3 * h
    xs = np.linspace(lo, hi, grid)
    # binned KDE (fast): histogram on the grid convolved with the Gaussian kernel
    counts, edges = np.histogram(a, bins=grid, range=(lo, hi))
    dx = xs[1] - xs[0]
    k = np.arange(-int(4 * h / dx) - 1, int(4 * h / dx) + 2) * dx
    kern = np.exp(-0.5 * (k / h) ** 2)
    dens = np.convolve(counts, kern, mode="same")
    dens = dens / (dens.sum() * dx)
    return float(xs[int(np.argmax(dens))]), float(h), xs, dens


def hdi(v: list[float], mass: float = 0.68) -> tuple:
    """Shortest interval containing `mass` of the sorted draws."""
    v = sorted(v)
    n = len(v)
    k = max(1, int(math.floor(mass * n)))
    if k >= n:
        return (v[0], v[-1])
    widths = [v[i + k] - v[i] for i in range(n - k)]
    i = min(range(len(widths)), key=widths.__getitem__)
    return (v[i], v[i + k])


def _np_stats(a, mass: float = 0.68) -> dict:
    """Same statistics as _stats, vectorized (numpy array, any order). Used for the bootstrap replicates."""
    import numpy as np
    a = np.sort(np.asarray(a, dtype=float))
    n = a.size
    m = a.mean()
    sd = a.std(ddof=1) if n > 1 else 0.0
    q = lambda p: a[min(n - 1, max(0, int(round(p * (n - 1)))))]  # noqa: E731
    skew = float(np.mean((a - m) ** 3) / sd ** 3) if sd > 0 else 0.0
    k = max(1, int(math.floor(mass * n)))
    if k >= n:
        lo, hi = a[0], a[-1]
    else:
        i = int(np.argmin(a[k:] - a[:n - k]))
        lo, hi = a[i], a[i + k]
    mode = kde_mode(a)[0]
    return {"mode": mode, "mean": float(m), "p50": float(q(0.5)), "sd": float(sd), "skew": skew,
            "hdi_lo": float(lo), "hdi_hi": float(hi), "p2_5": float(q(0.025)), "p97_5": float(q(0.975))}


def bootstrap_se(v: list[float], n_boot: int = 200, seed: int = 2024) -> dict:
    """Monte Carlo (sampling) standard error of every statistic in STAT_KEYS."""
    import numpy as np
    a = np.asarray(v, dtype=float)
    if a.size < 10 or n_boot < 2:
        return {}
    rng = np.random.default_rng(seed)
    n = a.size
    m, s = a.mean(), a.std(ddof=1)
    h = kde_mode(a)[1]
    shrink = 1.0 / math.sqrt(1.0 + (h / s) ** 2) if s > 0 else 1.0
    smooth = ("mode", "hdi_lo", "hdi_hi")
    reps = {k: [] for k in STAT_KEYS}
    for _ in range(n_boot):
        x = a[rng.integers(0, n, n)]
        st = _np_stats(x)
        xs = m + (x - m + h * rng.standard_normal(n)) * shrink
        sm = _np_stats(xs)
        for k in STAT_KEYS:
            reps[k].append(sm[k] if k in smooth else st[k])
    return {k: float(np.std(reps[k], ddof=1)) for k in STAT_KEYS}


def stat_value(st: "Stats", key: str) -> float:
    if key == "hdi_lo":
        return st.hdi68[0]
    if key == "hdi_hi":
        return st.hdi68[1]
    return getattr(st, key)


def fmt_pm(x: float, se: Optional[float], digits: int = 2) -> str:
    """Value ± standard error, the value rounded to the decimal place of the error's 2nd significant digit."""
    if x is None or not math.isfinite(x):
        return "—"
    if se is None or not math.isfinite(se) or se <= 0:
        return f"{x:.4g}"
    dec = max(0, digits - 1 - int(math.floor(math.log10(se))))
    return f"{x:.{dec}f} ± {se:.{dec}f}"


def _stats(v: list[float], n_boot: int = 0, seed: int = 2024) -> Stats:
    v = sorted(v)
    n = len(v)
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / max(n - 1, 1))
    q = lambda p: v[min(n - 1, max(0, int(round(p * (n - 1)))))]  # noqa: E731
    skew = (sum((x - m) ** 3 for x in v) / n) / sd ** 3 if sd > 0 else 0.0
    try:
        mode, bw, _xs, _d = kde_mode(v)
    except Exception:  # numpy missing
        mode, bw = q(0.5), 0.0
    st = Stats(m, sd, q(0.16), q(0.5), q(0.84), q(0.025), q(0.975), mode, skew, hdi(v, 0.68), bw)
    if n_boot:
        try:
            st.se = bootstrap_se(v, n_boot, seed)
        except Exception:  # numpy missing
            st.se = {}
    return st


@dataclass
class MCResult:
    nominal: dict
    number: dict                      # element -> Stats
    mass: dict
    budget_number: dict = field(default_factory=dict)   # source -> {element: sd}
    budget_mass: dict = field(default_factory=dict)
    n_draws: int = 0
    sources: tuple = ()
    params: dict = field(default_factory=dict)
    failed: int = 0
    samples_number: dict = field(default_factory=dict)   # element -> list of molar % draws
    samples_mass: dict = field(default_factory=dict)


def _simulate(inp: CFInputs, kt: float, ne: float, sig_kt: float, sig_lnne: float, n: int,
              sources: tuple, weighted: bool, rng: random.Random):
    nums, masses = {}, {}
    failed = 0
    for _ in range(n):
        k = kt + (rng.gauss(0.0, sig_kt) if "kT" in sources and sig_kt > 0 else 0.0)
        if k <= 0.05:
            failed += 1
            continue
        e = ne * math.exp(rng.gauss(0.0, sig_lnne)) if "Ne" in sources and sig_lnne > 0 else ne
        ys = {}
        for key, pts in inp.groups.items():
            yl = []
            for p in pts:
                d = 0.0
                if "intensity" in sources and p.s_int > 0:
                    d += rng.gauss(0.0, p.s_int)
                if "gA" in sources and p.s_gA > 0:
                    d += rng.gauss(0.0, p.s_gA)
                if "SAC" in sources and p.s_sac > 0:
                    d += rng.gauss(0.0, p.s_sac)
                yl.append(p.y + d)
            ys[key] = yl
        try:
            res = cflibs_concentrations(inp, k, e, ys, weighted)
        except (OverflowError, ValueError, ZeroDivisionError):
            failed += 1
            continue
        for el, (nu, ma, _r) in res.items():
            nums.setdefault(el, []).append(nu)
            masses.setdefault(el, []).append(ma)
    return nums, masses, failed


def monte_carlo(inp: CFInputs, kt: float, ne: float, sig_kt: float = 0.0, sig_ne_rel: float = 0.0,
                n: int = 2000, sources: tuple = SOURCES, weighted: bool = False, budget: bool = True,
                seed: int = 12345, n_boot: int = 200) -> MCResult:
    rng = random.Random(seed)
    sig_lnne = math.log(1.0 + sig_ne_rel) if sig_ne_rel > 0 else 0.0
    nominal = cflibs_concentrations(inp, kt, ne, None, weighted)
    nums, masses, failed = _simulate(inp, kt, ne, sig_kt, sig_lnne, n, sources, weighted, rng)
    out = MCResult(nominal, {el: _stats(v, n_boot, seed) for el, v in nums.items()},
                   {el: _stats(v, n_boot, seed) for el, v in masses.items()},
                   n_draws=n, sources=tuple(sources), failed=failed,
                   params=dict(kt=kt, ne=ne, sig_kt=sig_kt, sig_ne_rel=sig_ne_rel, weighted=weighted, n_boot=n_boot),
                   samples_number=nums, samples_mass=masses)
    if budget:
        nb = max(300, n // 3)
        for src in sources:
            nu, ma, _f = _simulate(inp, kt, ne, sig_kt, sig_lnne, nb, (src,), weighted, rng)
            out.budget_number[src] = {el: _stats(v).sd for el, v in nu.items()}
            out.budget_mass[src] = {el: _stats(v).sd for el, v in ma.items()}
    return out


def parse_code_map(text: str) -> dict:
    """'0:0.25, 1:0.03, 3:0.10' -> {0: 0.25, 1: 0.03, 3: 0.10}"""
    out = {}
    for tok in text.replace(";", ",").split(","):
        if ":" in tok:
            k, v = tok.split(":", 1)
            out[int(k.strip())] = float(v.strip())
    return out
