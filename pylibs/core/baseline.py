"""Sparse baseline estimation for LIBS spectra."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


def _inputs(wavelengths: Sequence[float], intensities: Sequence[float]):
    x = np.asarray(wavelengths, dtype=float)
    y = np.asarray(intensities, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size:
        raise ValueError("Wavelength and intensity arrays must be one-dimensional and equal in length.")
    if x.size < 3:
        raise ValueError("Baseline removal requires at least three data points.")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Spectrum contains NaN or infinite values.")
    dx = np.diff(x)
    if np.any(dx == 0) or not (np.all(dx > 0) or np.all(dx < 0)):
        raise ValueError("Wavelengths must be strictly monotonic with no duplicates.")
    return x, y


def _penalty(x: np.ndarray) -> sparse.csc_matrix:
    """Second derivative penalty on the actual, possibly nonuniform grid."""
    h = np.abs(np.diff(x))
    # Divide local slope change by the mean adjacent spacing, giving a
    # dimensionally consistent second derivative on irregular pixel grids.
    d = sparse.diags(
        [1.0 / h[:-1], -(1.0 / h[:-1] + 1.0 / h[1:]), 1.0 / h[1:]],
        [0, 1, 2], shape=(x.size - 2, x.size), format="csc",
    )
    scale = (0.5 * (h[:-1] + h[1:]))[:, None]
    return (d.multiply(scale).T @ d.multiply(scale)).tocsc()


def estimate_baseline(
    wavelengths: Sequence[float], intensities: Sequence[float], *,
    algorithm: str = "AsLS", lam: float = 1e6, p: float = 0.01,
    max_iter: int = 50, tolerance: float = 1e-3,
) -> np.ndarray:
    """Estimate a baseline using AsLS or adaptive iteratively reweighted PLS.

    Defaults are conservative starting values for LIBS spectra. ``lam`` is
    scaled to the wavelength unit through the local-spacing penalty.
    """
    x, y = _inputs(wavelengths, intensities)
    lam = float(lam)
    if not math.isfinite(lam) or lam <= 0:
        raise ValueError("Smoothing parameter λ must be a finite positive number.")
    max_iter = int(max_iter)
    if max_iter < 1 or max_iter > 500:
        raise ValueError("Maximum iterations must be between 1 and 500.")
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Convergence tolerance must be finite and positive.")
    method = str(algorithm).strip().lower()
    penalty = _penalty(x) * lam
    weights = np.ones(y.size, dtype=float)
    baseline = y.copy()
    for iteration in range(max_iter):
        matrix = sparse.diags(weights, format="csc") + penalty
        try:
            updated = np.asarray(spsolve(matrix, weights * y), dtype=float)
        except Exception as exc:
            raise ValueError(f"Baseline solver failed: {exc}") from exc
        if updated.shape != y.shape or not np.isfinite(updated).all():
            raise ValueError("Baseline solver produced non-finite values.")
        delta = np.linalg.norm(updated - baseline) / max(np.linalg.norm(baseline), np.linalg.norm(y), 1.0)
        baseline = updated
        residual = y - baseline
        if method in ("asls", "als"):
            asymmetry = float(p)
            if not math.isfinite(asymmetry) or not 0 < asymmetry < 1:
                raise ValueError("AsLS asymmetry p must be between 0 and 1.")
            weights = np.where(residual > 0, asymmetry, 1.0 - asymmetry)
            if delta <= tolerance:
                break
        elif method in ("airpls", "air-pls"):
            negative = residual < 0
            if not negative.any():
                break
            # airPLS weights are driven by negative residuals. Scale by their
            # robust magnitude to avoid overflow on high-count spectra.
            magnitude = np.abs(residual[negative])
            total = float(np.sum(magnitude))
            if total <= np.finfo(float).eps * max(float(np.max(np.abs(y))), 1.0):
                break
            weights = np.zeros_like(y)
            weights[negative] = np.exp(np.clip((iteration + 1) * magnitude / total, -50.0, 50.0))
            endpoint_weight = math.exp(min(50.0, (iteration + 1) * float(np.max(magnitude)) / total))
            weights[[0, -1]] = endpoint_weight
            if delta <= tolerance:
                break
        else:
            raise ValueError("Unknown baseline algorithm. Choose AsLS or airPLS.")
        weights = np.maximum(weights, 1e-12)
    return baseline


def remove_baseline(
    wavelengths: Sequence[float], intensities: Sequence[float], *,
    algorithm: str = "AsLS", lam: float = 1e6, p: float = 0.01,
    max_iter: int = 50, tolerance: float = 1e-3, clip_negative: bool = False,
) -> tuple[list[float], list[float]]:
    """Return (estimated baseline, corrected intensity) without changing inputs."""
    _, y = _inputs(wavelengths, intensities)
    baseline = estimate_baseline(
        wavelengths, intensities, algorithm=algorithm, lam=lam, p=p,
        max_iter=max_iter, tolerance=tolerance,
    )
    corrected = y - baseline
    if clip_negative:
        corrected = np.maximum(corrected, 0.0)
    return baseline.tolist(), corrected.tolist()
