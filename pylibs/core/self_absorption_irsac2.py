"""Self-absorption assessment and correction for CF-LIBS."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CM1_TO_EV = 1.239841984e-4
SA_EXP = 0.54                  # w = w0 * SA^-0.54
AREA_EXP = 0.46 / 0.54         # SAC_area = (w/w0)^(0.46/0.54)
DEFAULT_N = {1: 0.0, 2: -0.5}  # assumed T exponent of the Stark width when only one temperature is known
SIGMA_N = {1: 0.5, 2: 0.3}     # uncertainty of that exponent


# ------------------------------------------------------------------ Stark database
@dataclass
class StarkRef:
    w_1e17: float              # FWHM (A) at Ne = 1e17 cm-3 and the requested T
    rel_unc: float             # relative 1-sigma
    n_exp: float               # T exponent used
    t_range: tuple             # (Tmin, Tmax) of the data used
    n_meas: int
    kind: str
    sources: list = field(default_factory=list)
    note: str = ""


class StarkDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Stark database not found: {self.path}")
        self.conn = sqlite3.connect(f"file:{self.path.resolve().as_posix()}?mode=ro", uri=True)

    def close(self):
        self.conn.close()

    def rows(self, element: str, ion: int, wavelength_A: float, tol: float = 0.15):
        return self.conn.execute(
            "SELECT T_K, fwhm_A_1e17, rel_unc, kind, source, wavelength_A FROM measurements "
            "WHERE status='ok' AND element=? AND ion=? AND wavelength_A BETWEEN ? AND ? "
            "ORDER BY ABS(wavelength_A-?)",
            (element, int(ion), wavelength_A - tol, wavelength_A + tol, wavelength_A)).fetchall()

    def reference(self, element: str, ion: int, wavelength_A: float, T: float, tol: float = 0.15) -> Optional[StarkRef]:
        rows = self.rows(element, ion, wavelength_A, tol)
        if not rows:
            return None
        good = [r for r in rows if r[3] != "extrapolated"]
        use = good or rows
        kind = "measured/theory" if good else "extrapolated"
        Ts = [r[0] for r in use]
        tmin, tmax = min(Ts), max(Ts)
        srcs = sorted({r[4] for r in use})
        # weighted log-log fit when the temperature span is large enough
        if len(use) >= 3 and tmax / tmin >= 1.3:
            w = [1.0 / max(r[2], 0.05) ** 2 for r in use]
            X = [math.log(r[0]) for r in use]
            Y = [math.log(r[1]) for r in use]
            W = sum(w)
            xm = sum(wi * xi for wi, xi in zip(w, X)) / W
            ym = sum(wi * yi for wi, yi in zip(w, Y)) / W
            sxx = sum(wi * (xi - xm) ** 2 for wi, xi in zip(w, X))
            n = sum(wi * (xi - xm) * (yi - ym) for wi, xi, yi in zip(w, X, Y)) / sxx
            n = max(min(n, 1.0), -1.5)                     # physically plausible range
            a = ym - n * xm
            lw = a + n * math.log(T)
            res = [yi - (a + n * xi) for xi, yi in zip(X, Y)]
            s2 = sum(wi * ri * ri for wi, ri in zip(w, res)) / max(W, 1e-12) * len(use) / max(len(use) - 2, 1)
            rel = math.sqrt(s2 / len(use) + s2 * (math.log(T) - xm) ** 2 * (W / sxx) / len(use))
            rel = max(rel, min(r[2] for r in use) / math.sqrt(len(use)), 0.08)
            note = f"log-log fit n = {n:+.2f}"
            if not (tmin / 1.5 <= T <= tmax * 1.5):
                rel = math.hypot(rel, 0.3)
                note += "; T outside data range"
            return StarkRef(math.exp(lw), rel, n, (tmin, tmax), len(use), kind, srcs, note)
        # few points / narrow T span: weighted mean at T_ref, scaled with a default exponent
        w = [1.0 / max(r[2], 0.05) ** 2 for r in use]
        W = sum(w)
        tref = math.exp(sum(wi * math.log(r[0]) for wi, r in zip(w, use)) / W)
        lwm = sum(wi * math.log(r[1]) for wi, r in zip(w, use)) / W
        n0 = DEFAULT_N.get(ion, 0.0)
        acc = 1.0 / math.sqrt(W)
        spread = 0.0
        if len(use) > 1:
            spread = math.sqrt(sum(wi * (math.log(r[1]) - lwm) ** 2 for wi, r in zip(w, use)) / W)
        rel = math.sqrt(acc ** 2 + spread ** 2 + (SIGMA_N.get(ion, 0.5) * math.log(T / tref)) ** 2)
        if kind == "extrapolated":
            rel = math.hypot(rel, 0.5)
        return StarkRef(math.exp(lwm) * (T / tref) ** n0, rel, n0, (tmin, tmax), len(use), kind, srcs,
                        f"single-T data scaled with assumed n = {n0:+.1f} ± {SIGMA_N.get(ion, 0.5)}")


# ------------------------------------------------------------------ line data
MAX_SAC = 1.0 / 0.3            # physical bound of a correction factor (Yang et al. 2018; pyLIBS 1.2.1)
MIN_SNR = 10.0                 # minimum peak S/N of an IRSAC reference / target
SAME_LEVEL_EV = 1.0e-4         # upper levels closer than this are the same level


@dataclass
class SALine:
    key: int
    element: str
    ion: int
    wavelength_A: float
    ei_ev: float
    ek_ev: float
    gA: float                  # |g_k A_ki| (any consistent unit within a species)
    intensity: float           # response-corrected integrated intensity
    w_lorentz_A: float         # fitted Lorentzian FWHM
    w_gauss_A: float = 0.0
    label: str = ""
    snr: float = 0.0           # fitted peak S/N (0 = unknown)
    fit_warning: str = ""

    @property
    def y(self) -> float:
        return math.log(self.intensity / self.gA)

    @property
    def fit_ok(self) -> Optional[bool]:
        if self.fit_warning:
            return False
        if self.snr > 0:
            return self.snr >= MIN_SNR
        return None


def tau_proxy(line: SALine, kt: float) -> float:
    """Relative optical depth at line centre (same species): g_i f_ik lambda e^(-E_i/kT) ∝ g_k A lambda^3 e^(-E_i/kT)."""
    return line.gA * line.wavelength_A ** 3 * math.exp(-line.ei_ev / kt)


def choose_reference(lines: list[SALine], kt: float, min_rel_intensity: float = 0.05) -> Optional[SALine]:
    """Least self-absorbed line among those with usable intensity and a clean fit."""
    if not lines:
        return None
    imax = max(l.intensity for l in lines)
    cand = [l for l in lines if l.intensity >= min_rel_intensity * imax] or lines
    clean = [l for l in cand if l.fit_ok is not False]
    return min(clean or cand, key=lambda l: tau_proxy(l, kt))


@dataclass
class SAResult:
    line: SALine
    # Stark
    stark_w0: Optional[float] = None
    stark_w0_rel: Optional[float] = None
    stark_status: str = "no data"
    stark_sa: Optional[float] = None
    stark_sac: Optional[float] = None
    stark_sac_rel: Optional[float] = None
    stark_note: str = ""
    # IRSAC
    irsac_ref: Optional[str] = None
    irsac_sa: Optional[float] = None
    irsac_sac: Optional[float] = None
    irsac_sac_rel: Optional[float] = None
    irsac_status: str = "n/a"
    irsac_fref: Optional[float] = None  # self-absorption of the reference line (1 = thin)
    tau_rel: Optional[float] = None     # optical-depth proxy relative to the reference
    # independent evidence
    level_test: str = "—"               # same-upper-level ratio test


def stark_assessment(line: SALine, ref: Optional[StarkRef], ne: float, ne_rel: float,
                     inst_fwhm: float, inst_lorentz: float = 0.0, resolve_ratio: float = 0.2,
                     w_fit_rel: float = 0.10, nsig: float = 2.0) -> dict:
    out = {"stark_status": "no data"}
    if ref is None:
        return out
    w0 = ref.w_1e17 * ne / 1e17
    out.update(stark_w0=w0, stark_w0_rel=math.hypot(ref.rel_unc, ne_rel), stark_note=ref.note)
    if inst_fwhm > 0 and w0 < resolve_ratio * inst_fwhm:
        out["stark_status"] = f"unresolved (w0 {w0:.3g} Å < {resolve_ratio:g}×instr. {inst_fwhm:g} Å)"
        return out
    wm = line.w_lorentz_A - inst_lorentz
    if wm <= 0:
        out["stark_status"] = "no Lorentzian width"
        return out
    ratio = wm / w0
    rel = math.sqrt(ref.rel_unc ** 2 + ne_rel ** 2 + w_fit_rel ** 2)
    if ratio <= 1.0:
        out.update(stark_status="thin" if ratio > 0.5 else "thin (w < 0.5 w0: check Ne / data)",
                   stark_sa=1.0, stark_sac=1.0, stark_sac_rel=0.0)
        return out
    sa = ratio ** (-1.0 / SA_EXP)
    sac = ratio ** AREA_EXP
    # if the ratio is compatible with 1 within 2 sigma, do not correct
    if math.log(ratio) < nsig * rel:
        out.update(stark_status=f"thin within {nsig:g}σ", stark_sa=sa, stark_sac=1.0, stark_sac_rel=AREA_EXP * rel)
    else:
        out.update(stark_status="self-absorbed", stark_sa=sa, stark_sac=sac, stark_sac_rel=AREA_EXP * rel)
    return out


def _sy(line: SALine, default: float) -> float:
    return getattr(line, "sigma_y", None) or default


def _bounded(sac: float, max_sac: float) -> bool:
    return max_sac <= 0 or sac <= max_sac


def irsac_species(lines: list[SALine], kt: float, kt_sigma: float = 0.0, sigma_y: float = 0.10,
                  reference: Optional[SALine] = None, nsig: float = 2.0, ref_absorption: bool = True,
                  max_sac: float = MAX_SAC) -> dict[int, dict]:
    """IRSAC for the lines of one species. Returns {line.key: fields}.

    With ref_absorption the self-absorption of the reference itself is estimated as in Yang et al. (2018), made
    robust against a single blended line: f_ref is set by the second most significant line that appears less
    absorbed than the reference.
    """
    out = {}
    if len(lines) < 2:
        for l in lines:
            out[l.key] = {"irsac_status": "single line"}
        return out
    ref = reference or choose_reference(lines, kt)
    tref = tau_proxy(ref, kt)
    rel = {}
    for l in lines:
        if l is ref:
            continue
        dE = l.ek_ev - ref.ek_ev
        d = l.y - ref.y + dE / kt
        sig = math.sqrt(_sy(l, sigma_y) ** 2 + _sy(ref, sigma_y) ** 2 + (dE / kt * (kt_sigma / kt)) ** 2)
        rel[l.key] = (d, sig)
    ln_fref, sig_fref, fref_note = 0.0, 0.0, ""
    if ref_absorption:
        excess = sorted(((d, sig) for d, sig in rel.values() if d > nsig * sig), key=lambda x: -x[0])
        if len(excess) >= 2:
            # second largest excess: one line above the reference can be a blend, two agreeing lines are evidence
            d_ref, sig_fref = excess[1]
            ln_fref = -d_ref
        elif excess:
            fref_note = "; one line above the reference only (blend?): f_ref not estimated"
    fref = math.exp(ln_fref)
    ref_note = "" if fref >= 1.0 else f" (f_ref={fref:.3g})"
    for l in lines:
        tr = tau_proxy(l, kt) / tref if tref > 0 else None
        base = {"irsac_ref": ref.label + ref_note, "irsac_fref": fref, "tau_rel": tr}
        if l is ref:
            if fref < 1.0:
                sac = 1.0 / fref
                ok = _bounded(sac, max_sac)
                base.update(irsac_sa=fref, irsac_sac=sac if ok else None, irsac_sac_rel=sig_fref,
                            irsac_status="reference, self-absorbed" if ok else f"reference, unsafe (SAC {sac:.3g} > {max_sac:.3g})")
            else:
                base.update(irsac_sa=1.0, irsac_sac=1.0, irsac_sac_rel=0.0, irsac_status="reference" + fref_note)
            if l.fit_ok is False:
                base["irsac_status"] += "; poor fit"
            out[l.key] = base
            continue
        d, sig = rel[l.key]
        ln_sa = d + ln_fref
        sig_t = math.hypot(sig, sig_fref)
        sa = math.exp(ln_sa)
        if ln_sa >= 0.0:
            status = "thin" if ln_sa < nsig * sig_t else "SA > 1 (reference absorbed? / noise)"
            base.update(irsac_sa=sa, irsac_sac=1.0, irsac_sac_rel=sig_t, irsac_status=status)
        elif -ln_sa < nsig * sig_t:
            base.update(irsac_sa=sa, irsac_sac=1.0, irsac_sac_rel=sig_t, irsac_status=f"thin within {nsig:g}σ")
        else:
            sac = 1.0 / sa
            if not _bounded(sac, max_sac):
                base.update(irsac_sa=sa, irsac_sac=None, irsac_sac_rel=sig_t,
                            irsac_status=f"unsafe (SAC {sac:.3g} > {max_sac:.3g})")
            elif l.fit_ok is False:
                base.update(irsac_sa=sa, irsac_sac=None, irsac_sac_rel=sig_t,
                            irsac_status="self-absorbed, poor fit (not applied)")
            else:
                base.update(irsac_sa=sa, irsac_sac=sac, irsac_sac_rel=sig_t, irsac_status="self-absorbed")
        out[l.key] = base
    return out


def same_level_test(lines: list[SALine], sigma_y: float = 0.10, nsig: float = 3.0) -> dict[int, str]:
    """Lines sharing the upper level must have equal I/(gA) (λI/(gA) in energy mode) if optically thin.

    A ratio outside nsig·σ (and > 15 %) is independent evidence of self-absorption, blending or response error.
    """
    out = {}
    groups: dict[tuple, list[SALine]] = {}
    for l in lines:
        groups.setdefault((l.element, l.ion), []).append(l)
    for ls in groups.values():
        ls = sorted(ls, key=lambda l: l.ek_ev)
        for i, a in enumerate(ls):
            for b in ls[i + 1:]:
                if abs(b.ek_ev - a.ek_ev) > SAME_LEVEL_EV:
                    break
                dev = a.y - b.y
                thr = max(math.log(1.15), nsig * math.hypot(_sy(a, sigma_y), _sy(b, sigma_y)))
                r = math.exp(abs(dev))
                weaker, stronger = (a, b) if dev < 0 else (b, a)
                if abs(dev) > thr:
                    out[weaker.key] = f"weaker ×{r:.2f} vs {stronger.label}"
                    out.setdefault(stronger.key, f"stronger ×{r:.2f} vs {weaker.label}")
                else:
                    out.setdefault(a.key, f"agrees with {b.label}")
                    out.setdefault(b.key, f"agrees with {a.label}")
    return out


def slope_check(results: list[SAResult], mode: str, kt: float) -> dict[tuple, dict]:
    """Slope of each species after the chosen correction compared with the common kT (2σ)."""
    groups: dict[tuple, list[tuple[float, float]]] = {}
    for r in results:
        sac, _m = chosen_sac(r, mode)
        y = r.line.y + math.log(sac if sac and sac > 0 else 1.0)
        groups.setdefault((r.line.element, r.line.ion), []).append((r.line.ek_ev, y))
    out = {}
    for sp, pts in groups.items():
        n = len(pts)
        if n < 3 or len({round(x, 4) for x, _ in pts}) < 3:
            continue
        mx = sum(x for x, _ in pts) / n
        my = sum(y for _, y in pts) / n
        sxx = sum((x - mx) ** 2 for x, _ in pts)
        if sxx <= 0:
            continue
        b = sum((x - mx) * (y - my) for x, y in pts) / sxx
        res = [y - (my + b * (x - mx)) for x, y in pts]
        se = math.sqrt(sum(e * e for e in res) / max(n - 2, 1) / sxx)
        expected = -1.0 / kt
        out[sp] = {"n": n, "kt": -1.0 / b if b < 0 else None, "slope": b, "se": se,
                   "compatible": b < 0 and abs(b - expected) <= max(2.0 * se, 1e-12)}
    return out


def assess(lines: list[SALine], stark_db: Optional[StarkDatabase], kt: float, ne: float, *,
           kt_sigma: float = 0.0, ne_rel: float = 0.15, inst_fwhm: float = 0.0, inst_lorentz: float = 0.0,
           resolve_ratio: float = 0.2, sigma_y: float = 0.10, references: Optional[dict] = None,
           nsig: float = 2.0, ref_absorption: bool = True, max_sac: float = MAX_SAC) -> list[SAResult]:
    """Run both methods on all lines; `references` maps (element, ion) -> line key chosen by the user."""
    T = kt * 11604.518
    results = {l.key: SAResult(l) for l in lines}
    for l in lines:
        ref = stark_db.reference(l.element, l.ion, l.wavelength_A, T) if stark_db else None
        fields = stark_assessment(l, ref, ne, ne_rel, inst_fwhm, inst_lorentz, resolve_ratio, nsig=nsig)
        sac = fields.get("stark_sac")
        if sac is not None and sac > 1.0 and not _bounded(sac, max_sac):
            fields["stark_status"] = f"unsafe (SAC {sac:.3g} > {max_sac:.3g}): check Ne / Stark data"
            fields["stark_sac"] = None
        for k, v in fields.items():
            setattr(results[l.key], k, v)
    groups: dict[tuple, list[SALine]] = {}
    for l in lines:
        groups.setdefault((l.element, l.ion), []).append(l)
    for sp, ls in groups.items():
        ref = None
        if references and references.get(sp) is not None:
            ref = next((l for l in ls if l.key == references[sp]), None)
        for key, fields in irsac_species(ls, kt, kt_sigma, sigma_y, ref, nsig, ref_absorption, max_sac).items():
            for k, v in fields.items():
                setattr(results[key], k, v)
    for key, text in same_level_test(lines, sigma_y).items():
        results[key].level_test = text
    return [results[l.key] for l in lines]


def chosen_sac(r: SAResult, mode: str) -> tuple[Optional[float], str]:
    """mode: 'irsac' | 'stark' | 'stark_then_irsac' -> (SAC, method used)."""
    stark_ok = r.stark_sac is not None
    irsac_ok = r.irsac_sac is not None
    if mode == "stark":
        return (r.stark_sac, "Stark") if stark_ok else (None, "")
    if mode == "stark_then_irsac":
        if stark_ok:
            return r.stark_sac, "Stark"
        return (r.irsac_sac, "IRSAC") if irsac_ok else (None, "")
    return (r.irsac_sac, "IRSAC") if irsac_ok else (None, "")
