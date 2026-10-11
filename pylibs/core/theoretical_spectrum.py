"""LTE line-list synthesis with Voigt profiles and instrument-domain handling."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency
    np = None


@dataclass(frozen=True)
class TheoreticalLine:
    wavelength: float
    area: float
    species: str
    ion: int
    lorentzian_fwhm: float = 0.0


def _trapezoid(values, coordinates) -> float:
    """Version-independent trapezoidal integration for NumPy 1.x and 2.x."""
    values = np.asarray(values, dtype=float)
    coordinates = np.asarray(coordinates, dtype=float)
    if values.size < 2 or coordinates.size < 2:
        return 0.0
    return float(
        np.sum(
            0.5
            * (values[:-1] + values[1:])
            * (coordinates[1:] - coordinates[:-1])
        )
    )


def _voigt_unit(x, center: float, gaussian_fwhm: float, lorentzian_fwhm: float):
    sigma = max(abs(float(gaussian_fwhm)) / 2.354820045, 1.0e-12)
    gamma = max(abs(float(lorentzian_fwhm)) / 2.0, 1.0e-12)
    try:
        from scipy.special import wofz

        z = ((x - center) + 1j * gamma) / (sigma * math.sqrt(2.0))
        return np.real(wofz(z)) / (sigma * math.sqrt(2.0 * math.pi))
    except Exception:
        gaussian = np.exp(-0.5 * ((x - center) / sigma) ** 2) / (sigma * math.sqrt(2.0 * math.pi))
        lorentzian = gamma / (math.pi * ((x - center) ** 2 + gamma * gamma))
        fraction = gamma / (gamma + sigma)
        return (1.0 - fraction) * gaussian + fraction * lorentzian


def synthesize_voigt_spectrum(
    wavelengths: Sequence[float],
    lines: Iterable[TheoreticalLine],
    *,
    lsf_fwhm: Callable[[float], float],
    response: Optional[Callable[[float], Optional[float]]] = None,
    detector_domain: bool = False,
) -> list[float]:
    """Sum area-normalized Voigts and optionally map them to detector counts."""
    if np is None:
        raise RuntimeError("numpy is required for theoretical spectrum synthesis.")
    x = np.asarray(wavelengths, dtype=float)
    y = np.zeros_like(x)
    if x.size == 0:
        return []
    for line in lines:
        center = float(line.wavelength)
        area = float(line.area)
        if not math.isfinite(center) or not math.isfinite(area) or area <= 0.0:
            continue
        gaussian = max(float(lsf_fwhm(center)), 1.0e-9)
        lorentzian = max(float(line.lorentzian_fwhm), 1.0e-9)
        half_span = max(8.0 * gaussian, 25.0 * lorentzian)
        mask = np.abs(x - center) <= half_span
        if not np.any(mask):
            continue
        profile = _voigt_unit(x[mask], center, gaussian, lorentzian)
        # Preserve the requested integrated area when the complete numerical
        # support is inside the acquired window.  Lines clipped by a detector
        # edge deliberately retain only their visible fraction.
        if center - half_span >= float(np.min(x)) and center + half_span <= float(np.max(x)):
            integral = _trapezoid(profile, x[mask]) if np.count_nonzero(mask) > 1 else 0.0
            if integral > 0.0 and math.isfinite(integral):
                profile = profile / integral
        y[mask] += area * profile
    if detector_domain:
        if response is None:
            raise ValueError("Detector-domain synthesis requires an instrumental-response curve.")
        factors = []
        for wavelength in x:
            factor = response(float(wavelength))
            factors.append(float(factor) if factor is not None and math.isfinite(float(factor)) and factor > 0.0 else 0.0)
        y *= np.asarray(factors, dtype=float)
    return y.tolist()


def rescale_model_to_observation(observed: Sequence[float], model: Sequence[float]) -> tuple[list[float], float]:
    """Least-squares non-negative scalar for visual comparison only."""
    if np is None:
        raise RuntimeError("numpy is required for theoretical spectrum synthesis.")
    obs = np.asarray(observed, dtype=float)
    mod = np.asarray(model, dtype=float)
    mask = np.isfinite(obs) & np.isfinite(mod)
    denominator = float(np.dot(mod[mask], mod[mask])) if np.any(mask) else 0.0
    scale = max(0.0, float(np.dot(obs[mask], mod[mask])) / denominator) if denominator > 0.0 else 1.0
    return (mod * scale).tolist(), scale
