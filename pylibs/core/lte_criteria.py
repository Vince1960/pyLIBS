"""LTE validity criteria (McWhirter, transient and diffusion; Cristoforetti et al. 2010)."""

from __future__ import annotations

import csv
import itertools
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# ---------------------------------------------------------------- constantes
K_B_EV = 8.617333262e-5          # eV / K
CM1_TO_EV = 1.239841984e-4       # eV por cm^-1   (hc)
OSC_CONST = 1.49919e-16          # f_ik = C λ²[Å] (g_k/g_i) A_ki, vacuum λ

MCWHIRTER_C = 1.6e12             # cm^-3 K^-1/2 eV^-3
TAU_C = 6.3e4
LAMBDA_C = 1.4e12
DEFAULT_GAUNT = 0.2
DEFAULT_SAFETY = 10.0            # "much smaller" = factor 10
LIBSDB_AKI_UNIT = 1e8            # LIBS.db stores A_ki in 1e8 s^-1

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}


def species_label(element: str, ion: int) -> str:
    return f"{element} {ROMAN.get(int(ion), str(ion))}"


# ---------------------------------------------------------------- formulas
def mcwhirter_ne_min(temperature_k: float, delta_e_ev: float) -> float:
    """McWhirter minimum electron density (cm^-3)."""
    if temperature_k <= 0 or delta_e_ev <= 0:
        raise ValueError("T and ΔE must be positive")
    return MCWHIRTER_C * math.sqrt(temperature_k) * delta_e_ev ** 3


def relaxation_time(ne: float, kt_ev: float, delta_e_ev: float, f12: float,
                    gaunt: float = DEFAULT_GAUNT) -> float:
    """Relaxation time to excitation equilibrium (s)."""
    if min(ne, kt_ev, delta_e_ev, f12, gaunt) <= 0:
        raise ValueError("all parameters must be positive")
    return TAU_C / (ne * f12 * gaunt) * delta_e_ev * math.sqrt(kt_ev) * math.exp(delta_e_ev / kt_ev)


def diffusion_length(ne: float, kt_ev: float, delta_e_ev: float, mass_amu: float,
                     f12: float, gaunt: float = DEFAULT_GAUNT) -> float:
    """Diffusion length during tau_rel (cm)."""
    if min(ne, kt_ev, delta_e_ev, mass_amu, f12, gaunt) <= 0:
        raise ValueError("all parameters must be positive")
    return (LAMBDA_C * kt_ev ** 0.75 / ne
            * math.sqrt(delta_e_ev / (mass_amu * f12 * gaunt))
            * math.exp(delta_e_ev / (2.0 * kt_ev)))


def oscillator_strength(wavelength_vac_A: float, aki: float, gi: float, gk: float) -> float:
    """Absorption oscillator strength from A_ki (vacuum λ in Å)."""
    if min(wavelength_vac_A, aki, gi, gk) <= 0:
        raise ValueError("parameters must be positive")
    return OSC_CONST * wavelength_vac_A ** 2 * (gk / gi) * aki


# --------------------------------------------------------- acesso ao LIBS.db
class AtomicData:
    """Leitura somente-leitura do LIBS.db do pyLIBS (tabelas livelli, Elementi"""

    def __init__(self, db_path: str | Path, aki_unit: float = LIBSDB_AKI_UNIT):
        self.aki_unit = aki_unit
        path = Path(db_path)
        if not path.exists():
            raise FileNotFoundError(f"LIBS.db not found: {path}")
        self.path = path
        self.conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        self._tables = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}

    def close(self):
        self.conn.close()

    def element_meta(self, element: str) -> dict:
        row = self.conn.execute(
            "SELECT m_atomica, en_ion FROM Elementi WHERE TRIM(specie)=? "
            "AND typeof(m_atomica) IN ('real','integer')", (element,)).fetchone()
        if not row:
            return {}
        return {"mass_amu": float(row[0]), "ionization_cm1": float(row[1])}

    def levels_cm1(self, element: str, ion: int) -> list[float]:
        """Sorted distinct level energies (cm^-1)."""
        if "livelli" not in self._tables:
            return []
        rows = self.conn.execute(
            "SELECT Ei FROM livelli WHERE TRIM(element)=? AND CAST(ion AS INTEGER)=? "
            "AND typeof(Ei) IN ('real','integer')", (element, int(ion))).fetchall()
        return _unique_sorted(float(r[0]) for r in rows)

    def transitions(self, element: str, ion: int) -> list[dict]:
        if element not in self._tables:
            return []
        rows = self.conn.execute(
            f'SELECT wavelen, Ei, Ek, gi, gk, Aki FROM "{element}" '
            "WHERE CAST(ion AS INTEGER)=? AND typeof(Ei) IN ('real','integer') "
            "AND typeof(Ek) IN ('real','integer') AND typeof(Aki) IN ('real','integer')",
            (int(ion),)).fetchall()
        out = []
        for wl, ei, ek, gi, gk, aki in rows:
            try:
                ei, ek, gi, gk, aki = float(ei), float(ek), float(gi), float(gk), float(aki)
            except (TypeError, ValueError):
                continue
            if ek > ei and gi > 0 and gk > 0 and aki > 0:
                out.append({"wavelen": float(wl), "ei": ei, "ek": ek, "gi": gi, "gk": gk,
                            "aki": aki * self.aki_unit})
        return out


def _unique_sorted(values: Iterable[float], tol: float = 0.01) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


# ----------------------------------------------------------- template pyLIBS
@dataclass
class TemplateLine:
    element: str
    ion: int
    wavelength_A: float
    ei_cm1: float
    ek_cm1: float


def read_pylibs_template(path: str | Path) -> list[TemplateLine]:
    """Read a pyLIBS template CSV."""
    lines = []
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
        for r in csv.DictReader(f, dialect=dialect):
            el = (r.get("specie") or "").strip().capitalize()
            if not el or el == "Empty":
                continue
            try:
                ion = int(float(r.get("ion") or 0))
                ek = float(r.get("ek") or 0)
                ei = float(r.get("ei") or 0)
                aki = float(r.get("aki") or 0)
                wl = float(r.get("asswavelen") or 0) or float(r.get("wavelen") or 0)
            except ValueError:
                continue
            if ion <= 0 or ek <= 0 or aki < 0:
                continue
            lines.append(TemplateLine(el, ion, wl, ei, ek))
    return lines


# ---------------------------------------------------------------- species
@dataclass
class SpeciesGaps:
    element: str
    ion: int
    mass_amu: Optional[float] = None
    # largest gap between adjacent levels
    de_adjacent_ev: Optional[float] = None
    gap_lo_cm1: Optional[float] = None
    gap_hi_cm1: Optional[float] = None
    # strongest allowed transition bridging the gap
    de_bridge_ev: Optional[float] = None
    f12: Optional[float] = None
    bridge_wavelength_A: Optional[float] = None
    # largest ΔE of the lines used
    de_lines_ev: Optional[float] = None
    lines_wavelength_A: Optional[float] = None
    n_lines: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return species_label(self.element, self.ion)


@dataclass
class BridgeOverride:
    """User-supplied bridging transition (e.g. vacuum-UV resonance lines)."""
    wavelength_nm: float
    f12: float


def analyse_species(db: AtomicData, element: str, ion: int,
                    lines: Optional[list[TemplateLine]] = None,
                    override: Optional[BridgeOverride] = None) -> SpeciesGaps:
    """Relevant ΔE values of a species."""
    g = SpeciesGaps(element, ion)
    meta = db.element_meta(element)
    g.mass_amu = meta.get("mass_amu")
    if g.mass_amu is None:
        g.notes.append("atomic mass missing in LIBS.db")

    lines = [l for l in (lines or []) if l.element == element and l.ion == ion]
    g.n_lines = len(lines)
    if lines:
        best = max(lines, key=lambda l: l.ek_cm1 - l.ei_cm1)
        g.de_lines_ev = (best.ek_cm1 - best.ei_cm1) * CM1_TO_EV
        g.lines_wavelength_A = best.wavelength_A
        e_max = max(l.ek_cm1 for l in lines) + 0.5
    elif ion == 1 and meta.get("ionization_cm1"):
        e_max = meta["ionization_cm1"]
    else:
        e_max = math.inf

    levels = [e for e in db.levels_cm1(element, ion) if e <= e_max]
    if len(levels) < 2:
        g.notes.append("fewer than 2 levels in table 'livelli'")
        return g
    if levels[0] > 1.0:
        g.notes.append(f"lowest level at {levels[0]:.1f} cm-1 (ground state missing?)")
    lo, hi = max(zip(levels, levels[1:]), key=lambda p: p[1] - p[0])
    g.gap_lo_cm1, g.gap_hi_cm1 = lo, hi
    g.de_adjacent_ev = (hi - lo) * CM1_TO_EV

    # allowed transitions with Ei <= lo and Ek >= hi
    best_f, best = 0.0, None
    for t in db.transitions(element, ion):
        if t["ei"] <= lo + 0.5 and t["ek"] >= hi - 0.5:
            lam_vac = 1e8 / (t["ek"] - t["ei"])
            f = oscillator_strength(lam_vac, t["aki"], t["gi"], t["gk"])
            if f > best_f:
                best_f, best = f, t
    if override is not None:
        g.f12 = override.f12
        g.de_bridge_ev = 1239.841984 / override.wavelength_nm
        g.bridge_wavelength_A = override.wavelength_nm * 10.0
        g.notes.append(f"bridge transition given by the user: {override.wavelength_nm} nm, f12 = {override.f12}")
    elif best is None:
        g.notes.append("no transition with A_ki bridges the largest gap; f12 unavailable "
                       "(enter it as a manual bridge)")
    else:
        g.f12 = best_f
        g.de_bridge_ev = (best["ek"] - best["ei"]) * CM1_TO_EV
        g.bridge_wavelength_A = best["wavelen"]
    return g


# ---------------------------------------------------------------- evaluation
DE_BASES = ("conservative", "adjacent", "bridge", "lines")
BASIS_LABELS = {
    "conservative": "largest (recommended)",
    "adjacent": "adjacent levels",
    "bridge": "resonance (bridge)",
    "lines": "lines used",
}
BASIS_SHORT = {"adjacent": "adjacent", "bridge": "resonance", "lines": "lines"}
BASIS_HELP = (
    "ΔE used in the McWhirter criterion (Ne,min ∝ ΔE³):\n"
    "• largest (recommended): the largest of the three values below; an OK here is OK for any definition.\n"
    "• adjacent levels: largest gap between consecutive energy levels, from the ground state up to the\n"
    "   highest upper level used (original McWhirter definition).\n"
    "• resonance (bridge): ΔE of the strongest allowed transition (max f12) crossing that gap,\n"
    "   usually the resonance line; also used for τ_rel and λ.\n"
    "• lines used: largest ΔE = hc/λ among the template lines (least strict)."
)


@dataclass
class PlasmaState:
    temperature_k: float
    ne: float
    sigma_t_k: float = 0.0
    sigma_ne: float = 0.0
    t_var_s: Optional[float] = None      # characteristic variation time
    d_var_cm: Optional[float] = None     # characteristic variation length
    gaunt: float = DEFAULT_GAUNT
    safety: float = DEFAULT_SAFETY

    @property
    def kt_ev(self) -> float:
        return self.temperature_k * K_B_EV

    def corners(self):
        """(T, n_e) at the ±σ corners (worst case)."""
        ts = {self.temperature_k} | ({self.temperature_k - self.sigma_t_k, self.temperature_k + self.sigma_t_k}
                                     if self.sigma_t_k > 0 else set())
        ns = {self.ne} | ({self.ne - self.sigma_ne, self.ne + self.sigma_ne} if self.sigma_ne > 0 else set())
        return [(t, n) for t, n in itertools.product(ts, ns) if t > 0 and n > 0]


@dataclass
class SpeciesVerdict:
    gaps: SpeciesGaps
    de_used_ev: Optional[float] = None
    de_basis: str = ""
    ne_min: Optional[float] = None
    ne_min_worst: Optional[float] = None
    ratio: Optional[float] = None          # n_e / n_e,min (nominal)
    ratio_worst: Optional[float] = None
    mcwhirter_ok: Optional[bool] = None
    tau_rel_s: Optional[float] = None
    tau_rel_worst_s: Optional[float] = None
    temporal_ok: Optional[bool] = None
    lambda_cm: Optional[float] = None
    lambda_worst_cm: Optional[float] = None
    spatial_ok: Optional[bool] = None


def choose_delta_e(g: SpeciesGaps, basis: str = "conservative") -> tuple[Optional[float], str]:
    cand = {"adjacent": g.de_adjacent_ev, "bridge": g.de_bridge_ev, "lines": g.de_lines_ev}
    if basis == "conservative":
        avail = {k: v for k, v in cand.items() if v}
        if not avail:
            return None, ""
        k = max(avail, key=avail.get)
        return avail[k], k
    return cand.get(basis), basis


def evaluate_species(g: SpeciesGaps, p: PlasmaState, basis: str = "conservative") -> SpeciesVerdict:
    v = SpeciesVerdict(g)
    v.de_used_ev, v.de_basis = choose_delta_e(g, basis)
    corners = p.corners()
    if v.de_used_ev:
        v.ne_min = mcwhirter_ne_min(p.temperature_k, v.de_used_ev)
        v.ratio = p.ne / v.ne_min
        v.ratio_worst = min(n / mcwhirter_ne_min(t, v.de_used_ev) for t, n in corners)
        v.ne_min_worst = max(mcwhirter_ne_min(t, v.de_used_ev) for t, _ in corners)
        v.mcwhirter_ok = v.ratio_worst >= 1.0

    # tau_rel and lambda use the bridging transition
    if g.f12 and g.de_bridge_ev:
        de, f = g.de_bridge_ev, g.f12
        v.tau_rel_s = relaxation_time(p.ne, p.kt_ev, de, f, p.gaunt)
        v.tau_rel_worst_s = max(relaxation_time(n, t * K_B_EV, de, f, p.gaunt) for t, n in corners)
        if p.t_var_s:
            v.temporal_ok = p.safety * v.tau_rel_worst_s <= p.t_var_s
        if g.mass_amu:
            v.lambda_cm = diffusion_length(p.ne, p.kt_ev, de, g.mass_amu, f, p.gaunt)
            v.lambda_worst_cm = max(diffusion_length(n, t * K_B_EV, de, g.mass_amu, f, p.gaunt)
                                    for t, n in corners)
            if p.d_var_cm:
                v.spatial_ok = p.safety * v.lambda_worst_cm <= p.d_var_cm
    return v


def check_lte(db: AtomicData, plasma: PlasmaState,
              species: Optional[Iterable[tuple[str, int]]] = None,
              lines: Optional[list[TemplateLine]] = None,
              basis: str = "conservative",
              overrides: Optional[dict[tuple[str, int], BridgeOverride]] = None) -> list[SpeciesVerdict]:
    """Evaluate the LTE criteria for every species."""
    if basis not in DE_BASES:
        raise ValueError(f"basis must be one of {DE_BASES}")
    keys = set(species or [])
    keys |= {(l.element, l.ion) for l in (lines or [])}
    out = []
    for el, ion in sorted(keys, key=lambda k: (k[0], k[1])):
        out.append(evaluate_species(analyse_species(db, el, ion, lines, (overrides or {}).get((el, ion))),
                                   plasma, basis))
    return out


def parse_species(text: str) -> list[tuple[str, int]]:
    """'Fe I, Ca II, Mg 1' -> [('Fe',1), ('Ca',2), ('Mg',1)]"""
    inv = {v: k for k, v in ROMAN.items()}
    out = []
    for tok in text.replace(";", ",").split(","):
        parts = tok.split()
        if not parts:
            continue
        el = parts[0].capitalize()
        st = parts[1].upper() if len(parts) > 1 else "I"
        ion = inv.get(st) or int(st)
        out.append((el, ion))
    return out


def parse_bridges(text: str) -> dict[tuple[str, int], BridgeOverride]:
    """'H I=121.567:0.4164; O I=130.217:0.052' -> {('H',1): BridgeOverride(...), ...}"""
    out = {}
    for tok in text.split(";"):
        if not tok.strip():
            continue
        sp, val = tok.split("=")
        wl, f = val.split(":")
        out[parse_species(sp)[0]] = BridgeOverride(float(wl), float(f))
    return out


# ---------------------------------------------------------------- report
def _fmt(x, spec=".3g"):
    return "—" if x is None else format(x, spec)


def _ok(b):
    return "—" if b is None else ("OK" if b else "FAIL")


def format_report(results: list[SpeciesVerdict], p: PlasmaState, basis: str) -> str:
    lines = [
        "LTE validity check",
        f"T = {p.temperature_k:.0f} K (kT = {p.kt_ev:.4g} eV)"
        + (f" ± {p.sigma_t_k:.0f} K" if p.sigma_t_k else ""),
        f"n_e = {p.ne:.3e} cm^-3" + (f" ± {p.sigma_ne:.2e}" if p.sigma_ne else ""),
        f"ΔE basis (McWhirter): {BASIS_LABELS.get(basis, basis)};  <g> = {p.gaunt};  safety factor = {p.safety:g}",
        "",
        f"{'Species':<9}{'ΔE adj':>8}{'ΔE brdg':>8}{'ΔE lns':>8}{'ΔE used':>8} {'basis':<9}"
        f"{'n_e,min':>10}{'n_e/n_min':>11}{'worst':>8} {'McW':<6}"
        f"{'f12':>8}{'τ_rel(ns)':>11}{'λ(µm)':>9} {'temp':<6}{'spat':<6}",
    ]
    for v in results:
        g = v.gaps
        lines.append(
            f"{g.label:<9}{_fmt(g.de_adjacent_ev, '.3f'):>8}{_fmt(g.de_bridge_ev, '.3f'):>8}"
            f"{_fmt(g.de_lines_ev, '.3f'):>8}{_fmt(v.de_used_ev, '.3f'):>8} {BASIS_SHORT.get(v.de_basis, v.de_basis):<9}"
            f"{_fmt(v.ne_min, '.2e'):>10}{_fmt(v.ratio, '.3g'):>11}{_fmt(v.ratio_worst, '.3g'):>8} "
            f"{_ok(v.mcwhirter_ok):<6}{_fmt(g.f12, '.3g'):>8}"
            f"{_fmt(None if v.tau_rel_worst_s is None else v.tau_rel_worst_s * 1e9, '.3g'):>11}"
            f"{_fmt(None if v.lambda_worst_cm is None else v.lambda_worst_cm * 1e4, '.3g'):>9} "
            f"{_ok(v.temporal_ok):<6}{_ok(v.spatial_ok):<6}")
    lines.append("")
    mc = [v for v in results if v.mcwhirter_ok is not None]
    if mc:
        worst = min(mc, key=lambda v: v.ratio_worst)
        lines.append(
            f"McWhirter: {sum(v.mcwhirter_ok for v in mc)}/{len(mc)} species satisfied. "
            f"Most restrictive: {worst.gaps.label} (ΔE = {worst.de_used_ev:.3f} eV, "
            f"n_e,min = {worst.ne_min_worst:.2e} cm^-3).")
    lines.append("τ_rel and λ are worst-case values (T, n_e at ±σ extremes); ΔE and f12 of the bridge transition.")
    lines.append("Note: the McWhirter criterion is necessary but not sufficient "
                 "(Cristoforetti et al., 2010). For transient and inhomogeneous plasmas "
                 "τ_rel and λ must also be checked.")
    for v in results:
        for n in v.gaps.notes:
            lines.append(f"  [{v.gaps.label}] {n}")
        g = v.gaps
        if g.bridge_wavelength_A and g.gap_lo_cm1 is not None:
            lines.append(f"  [{g.label}] largest gap {g.gap_lo_cm1:.1f} → {g.gap_hi_cm1:.1f} cm-1; "
                         f"bridge transition {g.bridge_wavelength_A / 10:.3f} nm (f12 = {g.f12:.3g})")
    return "\n".join(lines)


CSV_HEADER = ["species", "n_lines", "mass_amu", "dE_adjacent_eV", "gap_lo_cm1", "gap_hi_cm1",
              "dE_bridge_eV", "bridge_wavelength_nm", "f12", "dE_lines_eV", "dE_used_eV", "dE_basis",
              "ne_min_cm3", "ne_min_worst_cm3", "ne_over_nemin", "ne_over_nemin_worst", "mcwhirter_ok",
              "tau_rel_s", "tau_rel_worst_s", "temporal_ok", "lambda_cm", "lambda_worst_cm", "spatial_ok",
              "notes"]


def write_csv(path: str | Path, results: list[SpeciesVerdict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for v in results:
            g = v.gaps
            w.writerow([g.label, g.n_lines, g.mass_amu, g.de_adjacent_ev, g.gap_lo_cm1, g.gap_hi_cm1,
                        g.de_bridge_ev, None if g.bridge_wavelength_A is None else g.bridge_wavelength_A / 10,
                        g.f12, g.de_lines_ev, v.de_used_ev, v.de_basis, v.ne_min, v.ne_min_worst,
                        v.ratio, v.ratio_worst, v.mcwhirter_ok, v.tau_rel_s, v.tau_rel_worst_s,
                        v.temporal_ok, v.lambda_cm, v.lambda_worst_cm, v.spatial_ok, "; ".join(g.notes)])
