"""Self-consistent determination of plasma temperature and electron density."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

SAHA_C = 6.04e21  # cm^-3 eV^-3/2


@dataclass
class SBPoint:
    element: str
    ion: int            # 1 or 2
    ek_ev: float        # upper level energy (eV)
    eion_ev: float      # ionization energy of the neutral (eV); used for ion == 2
    y: float            # ln(I / gA), not shifted
    label: str = ""

    @property
    def s(self) -> int:
        return 1 if self.ion == 2 else 0

    @property
    def x_raw(self) -> float:
        return self.ek_ev + (self.eion_ev if self.ion == 2 else 0.0)


def sb_coordinates(p: SBPoint, kt: float, ne: float) -> tuple[float, float]:
    """Saha-Boltzmann plot coordinates (x*, y*) as in pyLIBS (Unit27)."""
    if p.ion == 2:
        return p.x_raw, p.y - math.log(SAHA_C / ne * kt ** 1.5)
    return p.x_raw, p.y


def ne_constraining_elements(points: list[SBPoint]) -> list[str]:
    stages: dict[str, set] = {}
    for p in points:
        stages.setdefault(p.element, set()).add(p.ion)
    return sorted(e for e, s in stages.items() if {1, 2} <= s)


@dataclass
class GlobalFit:
    kt: float
    sigma_kt: Optional[float]
    ne: float
    sigma_ne: Optional[float]
    ne_fitted: bool
    corr_kt_ne: Optional[float]
    intercepts: dict
    rms: float
    n_points: int
    n_params: int
    elements: list
    ne_elements: list
    residuals: list = field(default_factory=list)
    message: str = ""


def global_fit(points: list[SBPoint], kt0: float, ne0: float, fit_ne: bool = True) -> GlobalFit:
    """Joint fit of kT, Ne and element intercepts to all Saha-Boltzmann points."""
    import numpy as np
    from scipy.optimize import least_squares

    if kt0 <= 0 or ne0 <= 0:
        raise ValueError("initial kT and Ne must be positive")
    elements = sorted({p.element for p in points})
    ne_elems = ne_constraining_elements(points)
    fit_ne = fit_ne and bool(ne_elems)
    n_q = len(elements)
    n_par = 1 + (1 if fit_ne else 0) + n_q
    if len(points) <= n_par:
        raise ValueError(f"{len(points)} points for {n_par} parameters: not enough lines")
    eidx = {e: i for i, e in enumerate(elements)}
    X = np.array([p.x_raw for p in points])
    Y = np.array([p.y for p in points])
    S = np.array([p.s for p in points], dtype=float)
    E = np.array([eidx[p.element] for p in points])
    u_fixed = math.log(ne0)
    lnC = math.log(SAHA_C)

    def unpack(par):
        beta = par[0]
        u = par[1] if fit_ne else u_fixed
        q = par[2:] if fit_ne else par[1:]
        return beta, u, q

    def resid(par):
        beta, u, q = unpack(par)
        model = q[E] - beta * X + S * (lnC - 1.5 * np.log(beta) - u)
        return Y - model

    def jac(par):
        beta, _u, _q = unpack(par)
        J = np.zeros((len(points), n_par))
        J[:, 0] = X + 1.5 * S / beta
        off = 1
        if fit_ne:
            J[:, 1] = S
            off = 2
        J[np.arange(len(points)), off + E] = -1.0
        return J

    beta0 = 1.0 / kt0
    q0 = []
    for e in elements:
        ys = [p.y + beta0 * p.x_raw - p.s * (lnC - 1.5 * math.log(beta0) - u_fixed) for p in points if p.element == e]
        q0.append(sum(ys) / len(ys))
    p0 = [beta0] + ([u_fixed] if fit_ne else []) + q0
    lb = [1.0 / 20.0] + ([math.log(1e12)] if fit_ne else []) + [-np.inf] * n_q
    ub = [1.0 / 0.1] + ([math.log(1e21)] if fit_ne else []) + [np.inf] * n_q
    p0 = [min(max(v, lo + 1e-12 if np.isfinite(lo) else v), hi - 1e-12 if np.isfinite(hi) else v)
          for v, lo, hi in zip(p0, lb, ub)]
    sol = least_squares(resid, p0, jac=jac, bounds=(lb, ub), x_scale="jac", xtol=1e-12, ftol=1e-12)
    beta, u, q = unpack(sol.x)
    r = resid(sol.x)
    dof = len(points) - n_par
    s2 = float(r @ r) / dof
    J = jac(sol.x)
    try:
        cov = np.linalg.inv(J.T @ J) * s2
    except np.linalg.LinAlgError:
        cov = None
    kt = 1.0 / beta
    ne = math.exp(u)
    sig_kt = sig_ne = corr = None
    if cov is not None:
        sig_beta = math.sqrt(max(cov[0, 0], 0.0))
        sig_kt = sig_beta / beta ** 2
        if fit_ne:
            sig_u = math.sqrt(max(cov[1, 1], 0.0))
            sig_ne = ne * sig_u
            if sig_beta > 0 and sig_u > 0:
                # corr(kT, Ne) = -corr(beta, u)
                corr = -cov[0, 1] / (sig_beta * sig_u)
    msg = "" if fit_ne else ("Ne not fitted: no element has lines of both ionization stages; "
                             "Ne kept at its starting value")
    kt = float(kt)
    sig_kt = None if sig_kt is None else float(sig_kt)
    sig_ne = None if sig_ne is None else float(sig_ne)
    corr = None if corr is None else float(corr)
    return GlobalFit(kt=kt, sigma_kt=sig_kt, ne=ne, sigma_ne=sig_ne, ne_fitted=fit_ne, corr_kt_ne=corr,
                     intercepts={e: float(q[i]) for e, i in eidx.items()},
                     rms=math.sqrt(float(r @ r) / len(points)), n_points=len(points), n_params=n_par,
                     elements=elements, ne_elements=ne_elems, residuals=[float(v) for v in r], message=msg)


@dataclass
class LoopStep:
    phase: str
    iteration: int
    kt: float
    ne: float
    ne_stark: Optional[float]
    rel_change: float


def stark_boltzmann_loop(kt0: float, ne0: float,
                         ne_from_kt: Optional[Callable[[float], float]],
                         kt_from_ne: Callable[[float, float], float],
                         tol: float = 1e-3, max_iter: int = 50) -> tuple[list[LoopStep], bool]:
    """Phase 1: alternate Ne = Ne_Stark(kT) and kT = T_SB(Ne)."""
    kt, ne = kt0, ne0
    steps = []
    for k in range(1, max_iter + 1):
        ne_new = ne_from_kt(kt) if ne_from_kt else ne
        kt_new = kt_from_ne(ne_new, kt)
        if not kt_new or kt_new <= 0:
            raise ValueError("Saha-Boltzmann temperature could not be computed")
        change = max(abs(kt_new - kt) / kt_new, abs(ne_new - ne) / ne_new)
        steps.append(LoopStep("Stark ⇄ Saha-Boltzmann", k, kt_new, ne_new,
                              ne_new if ne_from_kt else None, change))
        kt, ne = kt_new, ne_new
        if change <= tol:
            return steps, True
    return steps, False
