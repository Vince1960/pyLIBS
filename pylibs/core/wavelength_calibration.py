"""Per-window wavelength calibration for multi-window LIBS spectra."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency
    np = None

try:
    from scipy.optimize import curve_fit
    from scipy.signal import find_peaks
    from scipy.special import wofz
except Exception:  # pragma: no cover - optional runtime dependency
    curve_fit = None
    find_peaks = None
    wofz = None


@dataclass(frozen=True)
class CalibrationAnchor:
    reference: float
    observed: float
    prominence: float = 1.0
    residual: float = 0.0
    used: bool = True


@dataclass(frozen=True)
class WindowCalibration:
    name: str
    raw_min: float
    raw_max: float
    intercept: float
    slope: float = 1.0
    model: str = "offset"
    rms: float = 0.0
    anchors: tuple[CalibrationAnchor, ...] = field(default_factory=tuple)

    def correct(self, wavelength: float) -> float:
        return self.intercept + self.slope * float(wavelength)

    def correction_at(self, wavelength: float) -> float:
        wavelength = float(wavelength)
        return self.correct(wavelength) - wavelength

    @property
    def center(self) -> float:
        return 0.5 * (self.raw_min + self.raw_max)

    @property
    def used_anchor_count(self) -> int:
        return sum(1 for anchor in self.anchors if anchor.used)


def _weighted_median(values, weights):
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cutoff = 0.5 * float(np.sum(sorted_weights))
    index = int(np.searchsorted(np.cumsum(sorted_weights), cutoff, side="left"))
    return float(sorted_values[min(index, len(sorted_values) - 1)])


def _calibration_parameters(observed, reference, weights, model):
    if model == "offset":
        return float(np.average(reference - observed, weights=weights)), 1.0
    design = np.column_stack((np.ones_like(observed), observed))
    weighted_design = design * np.sqrt(weights)[:, None]
    weighted_reference = reference * np.sqrt(weights)
    intercept, slope = np.linalg.lstsq(
        weighted_design, weighted_reference, rcond=None
    )[0]
    return float(intercept), float(slope)


def fit_wavelength_calibration(
    anchors: Sequence[CalibrationAnchor],
    *,
    name: str = "",
    raw_min: float | None = None,
    raw_max: float | None = None,
    model: str = "auto",
) -> WindowCalibration:
    """Fit ``reference = intercept + slope * observed`` robustly.

    Automatic mode uses a linear calibration only with at least three anchors
    spanning 5 nm, a physically plausible scale, and a clear RMS improvement
    over a pure offset. A one-line calibration is therefore always an offset.
    """
    if np is None:
        raise RuntimeError("NumPy is required for wavelength calibration.")
    clean = [
        anchor
        for anchor in anchors
        if math.isfinite(float(anchor.reference))
        and math.isfinite(float(anchor.observed))
    ]
    if not clean:
        raise ValueError("At least one valid calibration anchor is required.")

    observed = np.asarray([anchor.observed for anchor in clean], dtype=float)
    reference = np.asarray([anchor.reference for anchor in clean], dtype=float)
    enabled = np.asarray([bool(anchor.used) for anchor in clean], dtype=bool)
    if not np.any(enabled):
        raise ValueError("At least one calibration anchor must be enabled.")
    raw_weights = np.asarray(
        [max(float(anchor.prominence), 1.0e-12) for anchor in clean], dtype=float
    )
    weights = np.sqrt(raw_weights / max(float(np.median(raw_weights)), 1.0e-12))
    weights = np.clip(weights, 0.25, 4.0)

    requested = str(model or "auto").strip().lower()
    if requested not in {"auto", "offset", "linear"}:
        raise ValueError(f"Unsupported calibration model: {model}")

    offset_intercept, offset_slope = _calibration_parameters(
        observed[enabled], reference[enabled], weights[enabled], "offset"
    )
    offset_residuals = reference - (
        offset_intercept + offset_slope * observed
    )
    offset_rms = float(np.sqrt(np.mean(offset_residuals[enabled] ** 2)))

    can_fit_linear = (
        int(np.sum(enabled)) >= 2
        and float(np.ptp(observed[enabled])) >= 1.0e-6
    )
    use_linear = requested == "linear" and can_fit_linear
    linear_candidate = None
    if can_fit_linear:
        linear_intercept, linear_slope = _calibration_parameters(
            observed[enabled], reference[enabled], weights[enabled], "linear"
        )
        linear_residuals = reference - (
            linear_intercept + linear_slope * observed
        )
        linear_rms = float(np.sqrt(np.mean(linear_residuals[enabled] ** 2)))
        linear_candidate = (
            linear_intercept,
            linear_slope,
            linear_residuals,
            linear_rms,
        )
        if requested == "auto":
            improvement = (
                (offset_rms - linear_rms) / offset_rms
                if offset_rms > 1.0e-12
                else 0.0
            )
            use_linear = (
                int(np.sum(enabled)) >= 3
                and float(np.ptp(reference[enabled])) >= 5.0
                and 0.97 <= linear_slope <= 1.03
                and improvement >= 0.25
            )

    chosen_model = "linear" if use_linear else "offset"
    mask = enabled.copy()
    for _ in range(4):
        if int(np.sum(mask)) < (2 if chosen_model == "linear" else 1):
            break
        intercept, slope = _calibration_parameters(
            observed[mask], reference[mask], weights[mask], chosen_model
        )
        residuals = reference - (intercept + slope * observed)
        median = float(np.median(residuals[mask]))
        mad = float(np.median(np.abs(residuals[mask] - median)))
        rejection_limit = max(0.03, 3.0 * 1.4826 * mad)
        new_mask = np.abs(residuals - median) <= rejection_limit
        minimum = 2 if chosen_model == "linear" else 1
        if int(np.sum(new_mask)) < minimum or np.array_equal(mask, new_mask):
            break
        mask = new_mask

    intercept, slope = _calibration_parameters(
        observed[mask], reference[mask], weights[mask], chosen_model
    )
    if chosen_model == "linear" and not 0.97 <= slope <= 1.03:
        chosen_model = "offset"
        mask = enabled.copy()
        intercept, slope = _calibration_parameters(
            observed[mask], reference[mask], weights[mask], chosen_model
        )
    residuals = reference - (intercept + slope * observed)
    rms = float(np.sqrt(np.mean(residuals[mask] ** 2)))
    fitted_anchors = tuple(
        CalibrationAnchor(
            reference=float(anchor.reference),
            observed=float(anchor.observed),
            prominence=float(anchor.prominence),
            residual=float(residual),
            used=bool(used),
        )
        for anchor, residual, used in zip(clean, residuals, mask)
    )
    low = float(np.min(observed)) if raw_min is None else float(raw_min)
    high = float(np.max(observed)) if raw_max is None else float(raw_max)
    if low > high:
        low, high = high, low
    return WindowCalibration(
        name=str(name or ""),
        raw_min=low,
        raw_max=high,
        intercept=float(intercept),
        slope=float(slope),
        model=chosen_model,
        rms=rms,
        anchors=fitted_anchors,
    )


def _voigt_unit(x, center, sigma, gamma):
    sigma = max(abs(float(sigma)), 1.0e-12)
    gamma = max(abs(float(gamma)), 1.0e-12)
    z = ((x - center) + 1j * gamma) / (sigma * math.sqrt(2.0))
    return np.real(wofz(z)) / (sigma * math.sqrt(2.0 * math.pi))


def _refine_voigt_center(x, y, peak_index, median_step):
    peak_x = float(x[peak_index])
    if np is None:
        return peak_x
    if curve_fit is None or wofz is None:
        if 0 < peak_index < len(x) - 1:
            left, middle, right = (
                float(y[peak_index - 1]),
                float(y[peak_index]),
                float(y[peak_index + 1]),
            )
            denominator = left - 2.0 * middle + right
            if abs(denominator) > 1.0e-15:
                fraction = 0.5 * (left - right) / denominator
                if abs(fraction) <= 1.0:
                    return peak_x + fraction * median_step
        return peak_x
    half_width = max(0.16, 5.0 * median_step)
    mask = np.abs(x - peak_x) <= half_width
    local_x = x[mask]
    local_y = y[mask]
    if len(local_x) < 7:
        return peak_x
    origin = float(np.mean(local_x))
    fit_x = local_x - origin
    center0 = peak_x - origin
    edge_count = max(2, len(local_y) // 5)
    baseline0 = float(
        np.median(np.concatenate((local_y[:edge_count], local_y[-edge_count:])))
    )
    area0 = max(
        (float(np.max(local_y)) - baseline0) * max(4.0 * median_step, 0.05),
        1.0e-12,
    )

    def model(values, baseline, slope, area, center, sigma, gamma):
        return (
            baseline
            + slope * values
            + area * _voigt_unit(values, center, sigma, gamma)
        )

    center_bound = max(0.10, 2.5 * median_step)
    p0 = [
        baseline0,
        0.0,
        area0,
        center0,
        max(median_step, 0.02),
        max(median_step, 0.02),
    ]
    lower = [
        -math.inf,
        -math.inf,
        0.0,
        center0 - center_bound,
        max(median_step * 0.10, 1.0e-5),
        max(median_step * 0.10, 1.0e-5),
    ]
    upper = [
        math.inf,
        math.inf,
        math.inf,
        center0 + center_bound,
        max(0.5, 12.0 * median_step),
        max(0.5, 12.0 * median_step),
    ]
    try:
        fitted, _ = curve_fit(
            model,
            fit_x,
            local_y,
            p0=p0,
            bounds=(lower, upper),
            maxfev=6000,
        )
    except Exception:
        return peak_x
    center = float(fitted[3] + origin)
    return center if math.isfinite(center) else peak_x


def estimate_window_calibration(
    x_values: Sequence[float],
    y_values: Sequence[float],
    reference_wavelengths: Iterable[float],
    *,
    name: str = "",
    max_shift: float = 0.8,
    model: str = "auto",
) -> WindowCalibration:
    """Locate real peaks near NIST lines and fit a per-window calibration."""
    if np is None:
        raise RuntimeError("NumPy is required for automatic calibration.")
    points = sorted(
        (
            (float(x), float(y))
            for x, y in zip(x_values, y_values)
            if math.isfinite(float(x)) and math.isfinite(float(y))
        ),
        key=lambda point: point[0],
    )
    if len(points) < 7:
        raise ValueError("The spectral window has too few valid samples.")
    x = np.asarray([point[0] for point in points], dtype=float)
    y = np.asarray([point[1] for point in points], dtype=float)
    steps = np.diff(x)
    positive_steps = steps[steps > 0.0]
    median_step = float(np.median(positive_steps)) if len(positive_steps) else 1.0
    max_shift = max(abs(float(max_shift)), 4.0 * median_step)
    references = sorted(
        {
            float(value)
            for value in reference_wavelengths
            if value is not None
            and math.isfinite(float(value))
            and x[0] - max_shift <= float(value) <= x[-1] + max_shift
        }
    )
    if not references:
        raise ValueError("No reference wavelength falls in this spectral window.")

    differences = np.diff(y)
    median_difference = float(np.median(differences)) if len(differences) else 0.0
    mad_difference = (
        float(np.median(np.abs(differences - median_difference)))
        if len(differences)
        else 0.0
    )
    noise_sigma = 1.4826 * mad_difference / math.sqrt(2.0)
    prominence_floor = max(
        4.0 * noise_sigma,
        float(np.ptp(y)) * 1.0e-4,
        1.0e-12,
    )
    minimum_distance = max(2, int(round(0.06 / max(median_step, 1.0e-12))))
    if find_peaks is not None:
        peak_indices, properties = find_peaks(
            y,
            prominence=prominence_floor,
            distance=minimum_distance,
        )
    else:
        local_maxima = [
            index
            for index in range(1, len(y) - 1)
            if y[index] > y[index - 1] and y[index] >= y[index + 1]
        ]
        selected = []
        selected_prominences = []
        for index in sorted(local_maxima, key=lambda item: float(y[item]), reverse=True):
            if any(abs(index - previous) < minimum_distance for previous in selected):
                continue
            radius = max(3, minimum_distance * 2)
            low = max(0, index - radius)
            high = min(len(y), index + radius + 1)
            local_baseline = float(np.median(y[low:high]))
            prominence = float(y[index] - local_baseline)
            if prominence >= prominence_floor:
                selected.append(index)
                selected_prominences.append(prominence)
        order = np.argsort(selected)
        peak_indices = np.asarray(selected, dtype=int)[order]
        properties = {
            "prominences": np.asarray(selected_prominences, dtype=float)[order]
        }
    if not len(peak_indices):
        raise ValueError("No measured peak passed the automatic noise threshold.")
    peak_x = x[peak_indices]
    prominences = np.asarray(properties.get("prominences", []), dtype=float)
    if len(prominences) != len(peak_indices):
        prominences = np.ones(len(peak_indices), dtype=float)

    shift_candidates = []
    for reference in references:
        compatible = np.where(np.abs(peak_x - reference) <= max_shift)[0]
        for peak_pos in compatible:
            shift_candidates.append(float(peak_x[peak_pos] - reference))
    if not shift_candidates:
        raise ValueError(
            f"No measured peak was found within ±{max_shift:g} of the reference lines."
        )

    cluster_half_width = max(0.08, 3.0 * median_step)
    best = None
    for shift in shift_candidates:
        matched = 0
        score = 0.0
        local_shifts = []
        local_weights = []
        for reference in references:
            deltas = peak_x - reference
            compatible = np.where(np.abs(deltas - shift) <= cluster_half_width)[0]
            if not len(compatible):
                continue
            peak_pos = max(compatible, key=lambda pos: prominences[int(pos)])
            prominence = float(prominences[int(peak_pos)])
            matched += 1
            score += math.log1p(prominence / prominence_floor)
            local_shifts.append(float(deltas[int(peak_pos)]))
            local_weights.append(max(prominence, prominence_floor))
        candidate = (matched, score)
        if best is None or candidate > best[:2]:
            coarse_shift = _weighted_median(
                np.asarray(local_shifts, dtype=float),
                np.asarray(local_weights, dtype=float),
            )
            best = (matched, score, coarse_shift)
    coarse_shift = float(best[2])

    gate = max(0.14, 4.0 * median_step)
    anchors = []
    used_peak_positions = set()
    for reference in references:
        predicted = reference + coarse_shift
        compatible = [
            int(pos)
            for pos in np.where(np.abs(peak_x - predicted) <= gate)[0]
            if int(pos) not in used_peak_positions
        ]
        if not compatible:
            continue
        peak_pos = min(compatible, key=lambda pos: abs(float(peak_x[pos]) - predicted))
        data_index = int(peak_indices[peak_pos])
        observed = _refine_voigt_center(x, y, data_index, median_step)
        if abs(observed - predicted) > gate:
            continue
        anchors.append(
            CalibrationAnchor(
                reference=float(reference),
                observed=float(observed),
                prominence=float(prominences[peak_pos]),
            )
        )
        used_peak_positions.add(peak_pos)
    if not anchors:
        raise ValueError("The detected maxima could not be paired with the reference lines.")

    return fit_wavelength_calibration(
        anchors,
        name=name,
        raw_min=float(x[0]),
        raw_max=float(x[-1]),
        model=model,
    )


def serialize_calibrations(calibrations: Sequence[WindowCalibration]) -> str:
    payload = []
    for calibration in calibrations:
        item = asdict(calibration)
        item["anchors"] = [asdict(anchor) for anchor in calibration.anchors]
        payload.append(item)
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def parse_calibrations(value) -> list[WindowCalibration]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        payload = value
    else:
        try:
            payload = json.loads(str(value))
        except Exception:
            return []
    calibrations = []
    for item in payload if isinstance(payload, list) else []:
        try:
            anchors = tuple(
                CalibrationAnchor(
                    reference=float(anchor["reference"]),
                    observed=float(anchor["observed"]),
                    prominence=float(anchor.get("prominence", 1.0)),
                    residual=float(anchor.get("residual", 0.0)),
                    used=bool(anchor.get("used", True)),
                )
                for anchor in item.get("anchors", [])
            )
            calibrations.append(
                WindowCalibration(
                    name=str(item.get("name", "")),
                    raw_min=float(item["raw_min"]),
                    raw_max=float(item["raw_max"]),
                    intercept=float(item["intercept"]),
                    slope=float(item.get("slope", 1.0)),
                    model=str(item.get("model", "offset")),
                    rms=float(item.get("rms", 0.0)),
                    anchors=anchors,
                )
            )
        except Exception:
            continue
    return calibrations


def calibration_for_window(
    calibrations: Sequence[WindowCalibration],
    x_values: Sequence[float],
    name: str = "",
) -> WindowCalibration | None:
    finite = [
        float(value)
        for value in x_values
        if value is not None and math.isfinite(float(value))
    ]
    if not finite:
        return None
    low, high = min(finite), max(finite)
    span = max(high - low, 1.0e-9)
    center = 0.5 * (low + high)
    normalized_name = Path(str(name or "")).stem.lower()
    best = None
    for calibration in calibrations:
        profile_span = max(calibration.raw_max - calibration.raw_min, 1.0e-9)
        overlap = max(
            0.0,
            min(high, calibration.raw_max) - max(low, calibration.raw_min),
        )
        overlap_fraction = overlap / min(span, profile_span)
        center_distance = abs(center - calibration.center) / max(span, profile_span)
        name_match = bool(
            normalized_name
            and Path(str(calibration.name or "")).stem.lower() == normalized_name
        )
        if overlap_fraction < 0.70 and center_distance > 0.10 and not name_match:
            continue
        score = overlap_fraction - center_distance + (0.05 if name_match else 0.0)
        if best is None or score > best[0]:
            best = (score, calibration)
    return best[1] if best else None
