"""Palleschi/Stark and internal-reference IRSAC correction helpers."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from pylibs.core.boltzmann import (
    ENERGY_INTENSITY_MODE,
    PHOTON_INTENSITY_MODE,
    normalize_intensity_mode,
)


CM_PER_K = 0.69503476


@dataclass(frozen=True)
class LineObservation:
    line: object
    species: str
    ion: int
    wavelength: float
    intensity: float
    ei_cm: float
    ek_cm: float
    aki: float
    gk: float
    accuracy_percent: float = 0.0
    snr: float = 0.0
    fit_warning: str = ""
    deconvolved_interference: bool = False
    transition_wavelength: float = 0.0
    intensity_mode: str = ENERGY_INTENSITY_MODE

    @property
    def key(self) -> tuple[str, int]:
        return self.species, self.ion

    @property
    def ag(self) -> float:
        return abs(self.aki * self.gk)

    @property
    def radiometric_wavelength(self) -> float:
        """Use the assigned transition wavelength in intensity equations."""
        assigned = abs(float(self.transition_wavelength))
        return assigned if assigned > 0.0 else abs(float(self.wavelength))

    def population_intensity(self, intensity: Optional[float] = None) -> float:
        """Return I for photon data or lambda*I for energy-domain data."""
        value = self.intensity if intensity is None else float(intensity)
        mode = normalize_intensity_mode(self.intensity_mode)
        if mode == PHOTON_INTENSITY_MODE:
            return value
        return self.radiometric_wavelength * value


@dataclass(frozen=True)
class LineCorrection:
    multiplier: float
    method: str
    reference_wavelength: float = 0.0
    yang_factor: float = 1.0
    flagged: bool = False


@dataclass(frozen=True)
class HybridCorrectionResult:
    corrections: dict[int, LineCorrection]
    temperature_k: float
    thermometric_key: Optional[tuple[str, int]]
    iterations: int
    converged: bool
    reference_absorption: dict[tuple[str, int], float] = field(default_factory=dict)
    rmse: float = math.nan
    temperature_history: tuple[float, ...] = ()
    selected_line_ids: tuple[int, ...] = ()
    max_log_factor_change: float = math.inf
    relative_temperature_change: float = math.inf
    decisions_stable: bool = False
    species_slope_validation: dict[tuple[str, int], dict] = field(default_factory=dict)
    slope_rejected_keys: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class LineAssessment:
    status: str
    reason: str
    recommended_use: bool = False
    is_reference: bool = False


@dataclass(frozen=True)
class SpeciesAssessment:
    key: tuple[str, int]
    status: str
    message: str
    equivalent_level_checks: int
    failed_checks: int
    reference_quality: str
    recommended_lines: int


@dataclass(frozen=True)
class SelfAbsorptionAssessment:
    lines: dict[int, LineAssessment]
    species: dict[tuple[str, int], SpeciesAssessment]
    status: str
    message: str
    can_apply: bool


def palleschi_sac_multiplier(measured_lorentzian_fwhm: float, stark_fwhm: float) -> Optional[float]:
    """Return the original Show-SA intensity multiplier from the width ratio."""
    measured = abs(float(measured_lorentzian_fwhm))
    stark = abs(float(stark_fwhm))
    if measured <= 0.0 or stark <= 0.0:
        return None
    ratio = measured / stark
    sa = ratio ** -1.85 if ratio >= 1.0 else 1.0
    multiplier = sa ** -0.46
    return multiplier if math.isfinite(multiplier) and multiplier >= 1.0 else None


def _rank(values: list[float], value: float, ascending: bool) -> float:
    ordered = sorted(set(values), reverse=not ascending)
    return float(ordered.index(value) + 1)


def select_yang_reference(observations: Iterable[LineObservation]) -> Optional[LineObservation]:
    """Apply Yang et al. Eq. (7) to the most accurate candidate lines."""
    candidates = [
        obs for obs in observations
        if obs.intensity > 0.0 and obs.aki > 0.0 and obs.gk > 0.0 and obs.ek_cm > 0.0
        and (obs.accuracy_percent <= 0.0 or obs.accuracy_percent <= 50.0)
    ]
    if not candidates:
        return None
    reported_accuracies = [
        obs.accuracy_percent for obs in candidates if obs.accuracy_percent > 0.0
    ]
    if reported_accuracies:
        best_accuracy = min(reported_accuracies)
        candidates = [
            obs for obs in candidates
            if obs.accuracy_percent > 0.0
            and abs(obs.accuracy_percent - best_accuracy) <= 1.0e-12
        ]
    energies = [obs.ei_cm for obs in candidates]
    probabilities = [obs.aki for obs in candidates]

    def score(obs: LineObservation):
        energy_rank = _rank(energies, obs.ei_cm, ascending=True)
        aki_rank = _rank(probabilities, obs.aki, ascending=False)
        return 0.5 * energy_rank + 0.5 * aki_rank

    # Python's max() keeps the first item when scores are tied. This matches
    # the Yang worksheet rule instead of introducing an undocumented
    # wavelength/Aki tie-breaker.
    return max(candidates, key=score)


def select_yang_reference_at_wavelength(
    observations: Iterable[LineObservation],
    wavelength: float,
) -> Optional[LineObservation]:
    """Return the usable observation nearest a configured reference wavelength."""
    try:
        target = abs(float(wavelength))
    except (TypeError, ValueError):
        return None
    candidates = [
        obs for obs in observations
        if obs.intensity > 0.0 and obs.aki > 0.0 and obs.gk > 0.0
        and obs.ek_cm > 0.0 and obs.radiometric_wavelength > 0.0
    ]
    if not candidates or target <= 0.0:
        return None
    return min(candidates, key=lambda obs: abs(obs.radiometric_wavelength - target))


def yang_aslam_factor(
    observation: LineObservation,
    reference: LineObservation,
    temperature_k: float,
    *,
    include_wavelength_ratio: bool = False,
    wavelength_reference: Optional[float] = None,
) -> Optional[float]:
    """Return the Yang/Aslam Eq. (6) self-absorption factor.

    Wavelength belongs to the Boltzmann ordinate, not to Eq. (6):
        f_k = I_k (A_ref g_ref) / [I_ref (A_k g_k)]
              * exp[-(E_ref - E_k)/(0.69503476 T)]
    """
    if temperature_k <= 0.0:
        return None
    if min(
        observation.intensity,
        reference.intensity,
        observation.ag,
        reference.ag,
    ) <= 0.0:
        return None
    exponent = -(reference.ek_cm - observation.ek_cm) / (CM_PER_K * temperature_k)
    try:
        factor = (
            observation.intensity
            * reference.ag
            / (reference.intensity * observation.ag)
            * math.exp(exponent)
        )
        if include_wavelength_ratio:
            denominator_wavelength = (
                abs(float(wavelength_reference))
                if wavelength_reference is not None
                else reference.wavelength
            )
            if min(observation.wavelength, denominator_wavelength) <= 0.0:
                return None
            factor *= observation.wavelength / denominator_wavelength
    except (OverflowError, ZeroDivisionError):
        return None
    return factor if math.isfinite(factor) and factor > 0.0 else None


def _linear_temperature(observations: list[LineObservation], corrections: dict[int, LineCorrection]) -> float:
    points = []
    for obs in observations:
        correction = corrections.get(id(obs.line))
        multiplier = correction.multiplier if correction is not None else 1.0
        corrected = obs.intensity * multiplier
        population_intensity = obs.population_intensity(corrected)
        if corrected <= 0.0 or obs.ag <= 0.0 or population_intensity <= 0.0:
            continue
        points.append((obs.ek_cm, math.log(population_intensity / obs.ag)))
    if len(points) < 2:
        return 0.0
    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)
    denominator = sum((point[0] - mean_x) ** 2 for point in points)
    if denominator <= 0.0:
        return 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    return -1.0 / (CM_PER_K * slope) if slope < 0.0 else 0.0


def _radiometric_ordinate(observation: LineObservation, intensity: float) -> float:
    population_intensity = observation.population_intensity(intensity)
    if min(population_intensity, intensity, observation.ag) <= 0.0:
        return math.nan
    return math.log(population_intensity / observation.ag)


def _yang_absorption_ratio(
    observation: LineObservation,
    reference: LineObservation,
    temperature_k: float,
) -> Optional[float]:
    """Return f_k/f_ref from Yang et al. Eq. (9) in the selected domain."""
    if temperature_k <= 0.0:
        return None
    wavelength = observation.radiometric_wavelength
    reference_wavelength = reference.radiometric_wavelength
    if min(
        observation.intensity,
        reference.intensity,
        observation.ag,
        reference.ag,
        wavelength,
        reference_wavelength,
    ) <= 0.0:
        return None
    exponent = (observation.ek_cm - reference.ek_cm) / (
        CM_PER_K * temperature_k
    )
    try:
        ratio = (
            observation.population_intensity()
            * reference.ag
            / (
                reference.population_intensity()
                * observation.ag
            )
            * math.exp(exponent)
        )
    except (OverflowError, ZeroDivisionError):
        return None
    return ratio if math.isfinite(ratio) and ratio > 0.0 else None


def _yang_reference_absorption(
    observations: list[LineObservation],
    reference: LineObservation,
    initial_temperature_k: float,
) -> Optional[float]:
    """Search f_ref=1.00..0.01 as specified by Yang et al. (2018)."""
    ratios = []
    for observation in observations:
        if observation.line is reference.line:
            continue
        ratio = _yang_absorption_ratio(
            observation,
            reference,
            initial_temperature_k,
        )
        if ratio is None:
            return None
        ratios.append(ratio)
    if not ratios:
        return 1.0
    for step in range(100, 0, -1):
        reference_absorption = step / 100.0
        if max(reference_absorption * ratio for ratio in ratios) < 1.0:
            return reference_absorption
    return None


def _yang_corrected_intensity(
    observation: LineObservation,
    reference: LineObservation,
    reference_absorption: float,
    temperature_k: float,
) -> Optional[float]:
    """Return the optically thin intensity from Yang et al. Eq. (10)."""
    wavelength = observation.radiometric_wavelength
    reference_wavelength = reference.radiometric_wavelength
    if temperature_k <= 0.0 or reference_absorption <= 0.0:
        return None
    if min(
        reference.intensity,
        reference.ag,
        observation.ag,
        wavelength,
        reference_wavelength,
    ) <= 0.0:
        return None
    exponent = (reference.ek_cm - observation.ek_cm) / (
        CM_PER_K * temperature_k
    )
    try:
        observation_factor = (
            1.0
            if normalize_intensity_mode(observation.intensity_mode) == PHOTON_INTENSITY_MODE
            else wavelength
        )
        reference_factor = (
            1.0
            if normalize_intensity_mode(reference.intensity_mode) == PHOTON_INTENSITY_MODE
            else reference_wavelength
        )
        corrected = (
            reference.intensity
            / reference_absorption
            * observation.ag
            / reference.ag
            * reference_factor
            / observation_factor
            * math.exp(exponent)
        )
    except (OverflowError, ZeroDivisionError):
        return None
    return corrected if math.isfinite(corrected) and corrected > 0.0 else None


def _yang_global_rmse(
    temperature_k: float,
    stage_points: dict[tuple[str, int], list[tuple[float, float]]],
    reference_points: dict[tuple[str, int], tuple[float, float]],
) -> float:
    if temperature_k <= 0.0:
        return math.inf
    slope = -1.0 / (CM_PER_K * temperature_k)
    residuals = []
    for key, points in stage_points.items():
        reference_point = reference_points.get(key)
        if reference_point is None:
            continue
        reference_x, reference_y = reference_point
        intercept = reference_y - slope * reference_x
        residuals.extend(
            (y_value - (slope * x_value + intercept)) ** 2
            for x_value, y_value in points
        )
    return (
        math.sqrt(sum(residuals) / len(residuals))
        if residuals
        else math.inf
    )


def _pso_temperature(
    lower_k: float,
    upper_k: float,
    objective: Callable[[float], float],
    max_iterations: int,
    relative_tolerance: float,
) -> tuple[float, float, int, bool, tuple[float, ...]]:
    """Run the one-dimensional PSO configuration reported by Yang et al."""
    lower = min(float(lower_k), float(upper_k))
    upper = max(float(lower_k), float(upper_k))
    if lower <= 0.0 or not all(math.isfinite(value) for value in (lower, upper)):
        return 0.0, math.inf, 0, False, ()
    if abs(upper - lower) <= 1.0e-12:
        fitness = objective(lower)
        return lower, fitness, 0, math.isfinite(fitness), (lower,)

    particle_count = 20
    iterations = max(1, int(max_iterations))
    rng = random.Random(201801)
    positions = [rng.uniform(lower, upper) for _ in range(particle_count)]
    positions[0] = lower
    positions[1] = upper
    positions[2] = 0.5 * (lower + upper)
    velocities = [rng.uniform(-50.0, 50.0) for _ in range(particle_count)]
    personal_positions = list(positions)
    personal_fitness = [objective(position) for position in positions]
    best_index = min(range(particle_count), key=personal_fitness.__getitem__)
    global_position = personal_positions[best_index]
    global_fitness = personal_fitness[best_index]
    history = [global_position]
    stable_iterations = 0

    for _iteration in range(1, iterations + 1):
        previous_fitness = global_fitness
        for index in range(particle_count):
            r1 = rng.random()
            r2 = rng.random()
            velocity = (
                0.5 * velocities[index]
                + 2.0 * r1 * (personal_positions[index] - positions[index])
                + 1.5 * r2 * (global_position - positions[index])
            )
            velocities[index] = max(-50.0, min(50.0, velocity))
            positions[index] = max(
                lower,
                min(upper, positions[index] + velocities[index]),
            )
            fitness = objective(positions[index])
            if fitness < personal_fitness[index]:
                personal_fitness[index] = fitness
                personal_positions[index] = positions[index]
            if fitness < global_fitness:
                global_fitness = fitness
                global_position = positions[index]
        history.append(global_position)
        scale = max(abs(previous_fitness), abs(global_fitness), 1.0e-12)
        if abs(previous_fitness - global_fitness) / scale <= max(
            relative_tolerance,
            1.0e-12,
        ):
            stable_iterations += 1
        else:
            stable_iterations = 0

    return (
        global_position,
        global_fitness,
        iterations,
        math.isfinite(global_fitness) and stable_iterations >= 10,
        tuple(history),
    )


def _iterative_yang_irsac(
    observations: list[LineObservation],
    initial_temperature_k: float,
    references: dict[tuple[str, int], Optional[LineObservation]],
    thermometric_key: Optional[tuple[str, int]],
    max_iterations: int,
    relative_tolerance: float,
) -> HybridCorrectionResult:
    """Implement Yang et al. (2018), Eqs. (7)-(11), including PSO."""
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for observation in observations:
        groups[observation.key].append(observation)

    reference_absorption: dict[tuple[str, int], float] = {}
    stage_points: dict[tuple[str, int], list[tuple[float, float]]] = {}
    reference_points: dict[tuple[str, int], tuple[float, float]] = {}
    raw_temperatures: dict[tuple[str, int], float] = {}
    species_temperatures: dict[tuple[str, int], float] = {}

    for key, group in groups.items():
        reference = references.get(key)
        if reference is None:
            continue
        raw_temperature = _linear_temperature(group, {})
        if raw_temperature <= 0.0:
            raw_temperature = max(float(initial_temperature_k), 1.0)
        raw_temperatures[key] = raw_temperature
        f_reference = _yang_reference_absorption(
            group,
            reference,
            raw_temperature,
        )
        if f_reference is None:
            continue
        reference_absorption[key] = f_reference
        points = []
        reference_point = None
        for observation in group:
            intensity = observation.intensity
            if observation.line is reference.line:
                intensity /= f_reference
            ordinate = _radiometric_ordinate(observation, intensity)
            if math.isfinite(ordinate):
                points.append((observation.ek_cm, ordinate))
                if observation.line is reference.line:
                    reference_point = (observation.ek_cm, ordinate)
        if len(points) < 2 or reference_point is None:
            continue
        reference_correction = {
            id(reference.line): LineCorrection(
                1.0 / f_reference,
                "IRSAC Yang 2018 reference",
                reference.radiometric_wavelength,
                f_reference,
            )
        }
        corrected_temperature = _linear_temperature(group, reference_correction)
        if corrected_temperature > 0.0 and math.isfinite(corrected_temperature):
            stage_points[key] = points
            reference_points[key] = reference_point
            species_temperatures[key] = corrected_temperature

    if not species_temperatures:
        return HybridCorrectionResult(
            {},
            max(float(initial_temperature_k), 1.0),
            thermometric_key,
            0,
            False,
            reference_absorption,
            math.inf,
            (),
        )

    # The thermometric species is the temperature anchor.  Other species keep
    # their own internal references and correction factors, but they must not
    # silently move the plasma temperature selected from the widest/reliable
    # Boltzmann energy interval.
    objective_keys = (
        {thermometric_key}
        if thermometric_key in stage_points
        else set(stage_points)
    )
    objective_stage_points = {
        key: stage_points[key]
        for key in objective_keys
    }
    objective_reference_points = {
        key: reference_points[key]
        for key in objective_keys
    }
    objective = lambda candidate: _yang_global_rmse(
        candidate,
        objective_stage_points,
        objective_reference_points,
    )
    if thermometric_key in species_temperatures:
        temperature_bounds = [
            raw_temperatures.get(
                thermometric_key,
                species_temperatures[thermometric_key],
            ),
            species_temperatures[thermometric_key],
        ]
    else:
        temperature_bounds = list(species_temperatures.values())
    temperature, rmse, iterations, converged, history = _pso_temperature(
        min(temperature_bounds),
        max(temperature_bounds),
        objective,
        max_iterations,
        relative_tolerance,
    )
    corrections: dict[int, LineCorrection] = {}
    for key, group in groups.items():
        reference = references.get(key)
        f_reference = reference_absorption.get(key)
        if reference is None or f_reference is None:
            continue
        for observation in group:
            corrected_intensity = _yang_corrected_intensity(
                observation,
                reference,
                f_reference,
                temperature,
            )
            if corrected_intensity is None or observation.intensity <= 0.0:
                continue
            multiplier = corrected_intensity / observation.intensity
            absorption = 1.0 / multiplier
            corrections[id(observation.line)] = LineCorrection(
                multiplier,
                "IRSAC Yang 2018 (PSO)",
                reference.radiometric_wavelength,
                absorption,
                multiplier < 0.98 or multiplier > (1.0 / 0.3),
            )
    return HybridCorrectionResult(
        corrections,
        temperature,
        thermometric_key,
        iterations,
        converged,
        reference_absorption,
        rmse,
        history,
    )


def _irsac_candidates_at_temperature(
    observations: list[LineObservation],
    temperature_k: float,
    references: dict[tuple[str, int], Optional[LineObservation]],
    *,
    mode: str,
    palleschi_factor: Optional[
        Callable[[LineObservation, float], Optional[float]]
    ] = None,
) -> tuple[
    dict[int, LineCorrection],
    dict[tuple[str, int], float],
]:
    """Calculate per-species candidate factors at one fixed temperature."""
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for observation in observations:
        groups[observation.key].append(observation)

    corrections: dict[int, LineCorrection] = {}
    reference_absorption: dict[tuple[str, int], float] = {}
    if mode in ("hybrid", "irsac", "yang", "yang/aslam"):
        for key, group in groups.items():
            reference = references.get(key)
            if reference is None:
                continue
            absorption = _yang_reference_absorption(
                group,
                reference,
                temperature_k,
            )
            if absorption is None:
                continue
            reference_absorption[key] = absorption
            for observation in group:
                corrected_intensity = _yang_corrected_intensity(
                    observation,
                    reference,
                    absorption,
                    temperature_k,
                )
                if corrected_intensity is None or observation.intensity <= 0.0:
                    continue
                multiplier = corrected_intensity / observation.intensity
                corrections[id(observation.line)] = LineCorrection(
                    multiplier,
                    "IRSAC internal reference (iterative)",
                    reference.radiometric_wavelength,
                    1.0 / multiplier,
                    multiplier < 0.98 or multiplier > (1.0 / 0.3),
                )

    if mode in ("hybrid", "palleschi") and palleschi_factor is not None:
        for observation in observations:
            multiplier = palleschi_factor(observation, temperature_k)
            if (
                multiplier is not None
                and math.isfinite(multiplier)
                and multiplier >= 1.0
            ):
                corrections[id(observation.line)] = LineCorrection(
                    multiplier,
                    "Palleschi/Stark",
                )
    return corrections, reference_absorption


def _correction_factor_change(
    previous: dict[int, LineCorrection],
    current: dict[int, LineCorrection],
) -> float:
    if not previous or set(previous) != set(current):
        return math.inf
    changes = []
    for line_id, correction in current.items():
        old = previous[line_id].multiplier
        new = correction.multiplier
        if min(old, new) <= 0.0 or not all(math.isfinite(v) for v in (old, new)):
            return math.inf
        changes.append(abs(math.log(new / old)))
    return max(changes, default=0.0)


def _species_slope_checks(
    observations: list[LineObservation],
    corrections: dict[int, LineCorrection],
    temperature_k: float,
) -> dict[tuple[str, int], dict]:
    """Compare independent species slopes with the final common temperature."""
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for observation in observations:
        groups[observation.key].append(observation)
    expected_slope = (
        -1.0 / (CM_PER_K * temperature_k)
        if temperature_k > 0.0
        else math.nan
    )
    results: dict[tuple[str, int], dict] = {}
    for key, group in groups.items():
        points = []
        for observation in group:
            correction = corrections.get(id(observation.line))
            multiplier = correction.multiplier if correction is not None else 1.0
            ordinate = _radiometric_ordinate(
                observation,
                observation.intensity * multiplier,
            )
            if math.isfinite(ordinate) and math.isfinite(observation.ek_cm):
                points.append((observation.ek_cm, ordinate))
        npoints = len(points)
        distinct_levels = len({round(point[0], 6) for point in points})
        result = {
            "nlines": npoints,
            "distinct_levels": distinct_levels,
            "slope": math.nan,
            "slope_standard_error": math.inf,
            "expected_slope": expected_slope,
            "temperature_k": 0.0,
            "compatible": None,
            "reason": "At least three independent upper levels are required.",
            "rmse": math.inf,
        }
        if npoints < 3 or distinct_levels < 3:
            results[key] = result
            continue
        mean_x = sum(point[0] for point in points) / npoints
        mean_y = sum(point[1] for point in points) / npoints
        sxx = sum((point[0] - mean_x) ** 2 for point in points)
        if sxx <= 0.0:
            results[key] = result
            continue
        slope = sum(
            (x_value - mean_x) * (y_value - mean_y)
            for x_value, y_value in points
        ) / sxx
        intercept = mean_y - slope * mean_x
        residuals = [
            y_value - (slope * x_value + intercept)
            for x_value, y_value in points
        ]
        rmse = math.sqrt(sum(value * value for value in residuals) / npoints)
        slope_error = math.sqrt(
            sum(value * value for value in residuals)
            / max(npoints - 2, 1)
            / sxx
        )
        tolerance = max(2.0 * slope_error, 1.0e-12)
        compatible = (
            math.isfinite(expected_slope)
            and slope < 0.0
            and abs(slope - expected_slope) <= tolerance
        )
        result.update({
            "slope": slope,
            "slope_standard_error": slope_error,
            "temperature_k": (
                -1.0 / (CM_PER_K * slope)
                if slope < 0.0
                else 0.0
            ),
            "compatible": compatible,
            "reason": (
                "Independent slope agrees with the thermometric temperature."
                if compatible
                else "Independent slope is incompatible with the thermometric temperature."
            ),
            "rmse": rmse,
        })
        results[key] = result
    return results


def _selective_iterative_irsac(
    observations: list[LineObservation],
    initial_temperature_k: float,
    references: dict[tuple[str, int], Optional[LineObservation]],
    thermometric_key: Optional[tuple[str, int]],
    *,
    mode: str,
    palleschi_factor: Optional[
        Callable[[LineObservation, float], Optional[float]]
    ],
    max_iterations: int,
    relative_tolerance: float,
) -> HybridCorrectionResult:
    """Iterate factors, diagnostics and thermometric T until all are stable."""
    thermometric_key = thermometric_key or most_reliable_thermometric_key(
        observations
    )
    raw_temperature = thermometric_temperature(
        observations,
        {},
        thermometric_key,
    )
    temperature = (
        raw_temperature
        if raw_temperature > 0.0 and math.isfinite(raw_temperature)
        else max(float(initial_temperature_k), 1.0)
    )
    temperature_history = [temperature]
    previous_candidates: dict[int, LineCorrection] = {}
    previous_decisions: Optional[tuple[int, ...]] = None
    final_candidates: dict[int, LineCorrection] = {}
    final_selected: dict[int, LineCorrection] = {}
    final_reference_absorption: dict[tuple[str, int], float] = {}
    final_slope_checks: dict[tuple[str, int], dict] = {}
    final_rejected_keys: set[tuple[str, int]] = set()
    factor_change = math.inf
    temperature_change = math.inf
    decisions_stable = False
    converged = False
    iterations = 0
    line_keys = {
        id(observation.line): observation.key
        for observation in observations
    }

    for iteration in range(1, max(1, int(max_iterations)) + 1):
        iterations = iteration
        candidates, reference_absorption = _irsac_candidates_at_temperature(
            observations,
            temperature,
            references,
            mode=mode,
            palleschi_factor=palleschi_factor,
        )
        assessment = assess_self_absorption(observations, candidates)
        selected = {
            line_id: correction
            for line_id, correction in candidates.items()
            if (
                line_id in assessment.lines
                and assessment.lines[line_id].recommended_use
            )
        }
        updated_temperature = thermometric_temperature(
            observations,
            selected,
            thermometric_key,
        )
        if updated_temperature <= 0.0 or not math.isfinite(updated_temperature):
            updated_temperature = temperature

        slope_checks = _species_slope_checks(
            observations,
            selected,
            updated_temperature,
        )
        corrected_keys = {
            observation.key
            for observation in observations
            if id(observation.line) in selected
        }
        rejected_keys = {
            key
            for key in corrected_keys
            if key != thermometric_key
            and slope_checks.get(key, {}).get("compatible") is False
        }
        if rejected_keys:
            selected = {
                line_id: correction
                for line_id, correction in selected.items()
                if line_keys.get(line_id) not in rejected_keys
            }
            updated_temperature = thermometric_temperature(
                observations,
                selected,
                thermometric_key,
            )
            if updated_temperature <= 0.0 or not math.isfinite(updated_temperature):
                updated_temperature = temperature
            raw_slope_checks = _species_slope_checks(
                observations,
                selected,
                updated_temperature,
            )
            for key, raw_check in raw_slope_checks.items():
                if key in rejected_keys:
                    slope_checks[key]["raw_after_rejection_slope"] = raw_check.get(
                        "slope",
                        math.nan,
                    )
                    slope_checks[key]["raw_after_rejection_temperature_k"] = (
                        raw_check.get("temperature_k", 0.0)
                    )
                else:
                    slope_checks[key] = raw_check

        decision_signature = tuple(sorted(selected))
        decisions_stable = (
            previous_decisions is not None
            and decision_signature == previous_decisions
        )
        factor_change = _correction_factor_change(
            previous_candidates,
            candidates,
        )
        temperature_change = abs(updated_temperature - temperature) / max(
            abs(updated_temperature),
            1.0,
        )

        final_candidates = candidates
        final_selected = selected
        final_reference_absorption = reference_absorption
        final_slope_checks = slope_checks
        final_rejected_keys = rejected_keys
        temperature = updated_temperature
        temperature_history.append(temperature)

        if (
            decisions_stable
            and temperature_change <= max(relative_tolerance, 1.0e-12)
            and factor_change <= max(relative_tolerance, 1.0e-12)
        ):
            converged = True
            break
        previous_candidates = candidates
        previous_decisions = decision_signature

    thermometric_check = final_slope_checks.get(thermometric_key, {})
    rmse = float(thermometric_check.get("rmse", math.inf))
    return HybridCorrectionResult(
        final_candidates,
        temperature,
        thermometric_key,
        iterations,
        converged,
        final_reference_absorption,
        rmse,
        tuple(temperature_history),
        tuple(sorted(final_selected)),
        factor_change,
        temperature_change,
        decisions_stable,
        final_slope_checks,
        tuple(sorted(final_rejected_keys)),
    )


def most_reliable_thermometric_key(observations: Iterable[LineObservation]) -> Optional[tuple[str, int]]:
    """Choose the eligible species with the widest upper-energy interval."""
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for obs in observations:
        groups[obs.key].append(obs)
    best = None
    for key, group in groups.items():
        usable = [
            obs for obs in group
            if obs.ek_cm > 0.0 and obs.intensity > 0.0 and obs.ag > 0.0
        ]
        energies = [obs.ek_cm for obs in usable]
        if len(usable) < 3 or len({round(value, 6) for value in energies}) < 3:
            continue
        leave_one_out = []
        for omitted in range(len(usable)):
            subset = usable[:omitted] + usable[omitted + 1:]
            if len({round(obs.ek_cm, 6) for obs in subset}) < 2:
                continue
            temperature = _linear_temperature(subset, {})
            if temperature > 0.0:
                leave_one_out.append(temperature)
        if len(leave_one_out) < 2:
            continue
        ordered = sorted(leave_one_out)
        middle = len(ordered) // 2
        median = (
            ordered[middle]
            if len(ordered) % 2
            else 0.5 * (ordered[middle - 1] + ordered[middle])
        )
        if median <= 0.0:
            continue
        relative_span = (ordered[-1] - ordered[0]) / median
        rank = (
            max(energies) - min(energies),
            len({round(value, 6) for value in energies}),
            -relative_span,
            len(usable),
        )
        if best is None or rank > best[0]:
            best = (rank, key)
    return best[1] if best else None


def thermometric_temperature(
    observations: Iterable[LineObservation],
    corrections: dict[int, LineCorrection],
    thermometric_key: Optional[tuple[str, int]],
) -> float:
    """Fit T from one thermometric species using only accepted corrections.

    Corrections belonging to other species deliberately have no influence on
    this temperature.  Passing an empty correction map gives the raw
    optically-thin temperature of the selected species.
    """
    observations = list(observations)
    key = thermometric_key or most_reliable_thermometric_key(observations)
    if key is None:
        return 0.0
    group = [observation for observation in observations if observation.key == key]
    return _linear_temperature(group, corrections)


def assess_self_absorption(
    observations: Iterable[LineObservation],
    corrections: dict[int, LineCorrection],
) -> SelfAbsorptionAssessment:
    """Assess correction support using only the currently loaded spectrum.

    IRSAC can always produce a numerical factor once a reference is chosen.
    That factor is not itself evidence of self-absorption. This assessment
    therefore uses the checks that can be supported by a single acquisition:

    * agreement of response-corrected integrated intensities from transitions
      sharing the same upper level;
    * fitted Voigt quality for every IRSAC reference and target line;
    * the Palleschi/Stark width test, when Stark data are available.

    For an equivalent-upper-level pair, ``I/(Aki*gk)`` in photon mode or
    ``I*lambda/(Aki*gk)`` in energy mode must agree in an optically thin plasma.
    Atomic-data accuracy and fitted peak S/N are used as
    an uncertainty estimate when available. A mismatch is compatible with
    self-absorption, but it can also be caused by blends, response-calibration
    error, atomic-data uncertainty or a poor fit. IRSAC is therefore
    recommended only when the mismatch is accompanied by clean Voigt fits
    (S/N >= 10), a valid reference and physical correction factors.

    This function deliberately does not infer a curve of growth or a temporal
    trend: neither can be reconstructed from one spectrum without additional
    acquisitions and plasma/geometry information. An Aslam internal-reference
    multiplier may be below one because it is a relative normalization to the
    selected reference, not an absolute optical-depth measurement. Only
    non-positive, non-finite or extreme relative factors are rejected here.
    """
    observations = list(observations)
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for observation in observations:
        groups[observation.key].append(observation)

    line_state = {
        id(observation.line): {
            "status": "Not assessed",
            "reasons": [],
            "recommended": False,
            "reference": False,
        }
        for observation in observations
    }
    species_results: dict[tuple[str, int], SpeciesAssessment] = {}

    def add_reason(observation: LineObservation, status: str, reason: str):
        state = line_state[id(observation.line)]
        priority = {
            "Not assessed": 0,
            "Reference fit OK": 1,
            "No mismatch": 1,
            "Evidence": 2,
            "Recommended": 3,
            "Unsafe": 4,
        }
        if priority.get(status, 0) >= priority.get(state["status"], 0):
            state["status"] = status
        if reason and reason not in state["reasons"]:
            state["reasons"].append(reason)

    for key, group in groups.items():
        group_corrections = {
            id(observation.line): corrections.get(id(observation.line))
            for observation in group
        }
        irsac_rows = [
            observation for observation in group
            if (
                group_corrections[id(observation.line)] is not None
                and group_corrections[id(observation.line)].method.startswith("IRSAC")
            )
        ]
        palleschi_rows = [
            observation for observation in group
            if (
                group_corrections[id(observation.line)] is not None
                and group_corrections[id(observation.line)].method.startswith("Palleschi")
            )
        ]

        reference = None
        if irsac_rows:
            reference_wavelength = group_corrections[
                id(irsac_rows[0].line)
            ].reference_wavelength
            reference = min(
                group,
                key=lambda observation: abs(
                    observation.wavelength - reference_wavelength
                ),
            )
            line_state[id(reference.line)]["reference"] = True

        reference_quality = "not required"
        if reference is not None:
            snr = reference.snr if math.isfinite(reference.snr) else 0.0
            warning = str(reference.fit_warning or "").strip()
            if snr > 0.0 and snr < 10.0:
                reference_quality = "invalid"
                add_reason(
                    reference,
                    "Unsafe",
                    f"IRSAC reference S/N={snr:.3g} is below 10",
                )
            elif warning:
                reference_quality = "invalid"
                add_reason(reference, "Unsafe", f"IRSAC reference fit: {warning}")
            elif reference.deconvolved_interference:
                reference_quality = "invalid"
                add_reason(
                    reference,
                    "Unsafe",
                    "IRSAC reference required deconvolution of an interfering peak",
                )
            elif snr >= 10.0:
                reference_quality = "valid"
                add_reason(
                    reference,
                    "Reference fit OK",
                    f"IRSAC reference fit passed available checks, S/N={snr:.3g}",
                )
            else:
                reference_quality = "unknown"
                add_reason(
                    reference,
                    "Not assessed",
                    "IRSAC reference S/N/profile quality not available; refit Voigt first",
                )

        equivalent_checks = 0
        failed_checks = 0
        conclusive_passes = 0
        sorted_group = sorted(group, key=lambda observation: observation.ek_cm)
        upper_level_groups: list[list[LineObservation]] = []
        for observation in sorted_group:
            if not upper_level_groups:
                upper_level_groups.append([observation])
                continue
            current = upper_level_groups[-1]
            tolerance = max(0.5, abs(observation.ek_cm) * 1.0e-6)
            if abs(observation.ek_cm - current[0].ek_cm) <= tolerance:
                current.append(observation)
            else:
                upper_level_groups.append([observation])

        for upper_group in upper_level_groups:
            if len(upper_group) < 2:
                continue
            for first_index in range(len(upper_group) - 1):
                for second_index in range(first_index + 1, len(upper_group)):
                    first = upper_group[first_index]
                    second = upper_group[second_index]
                    first_normalized = (
                        first.population_intensity() / first.ag
                        if min(first.intensity, first.radiometric_wavelength, first.ag) > 0.0
                        else 0.0
                    )
                    second_normalized = (
                        second.population_intensity() / second.ag
                        if min(second.intensity, second.radiometric_wavelength, second.ag) > 0.0
                        else 0.0
                    )
                    if min(first_normalized, second_normalized) <= 0.0:
                        continue
                    equivalent_checks += 1
                    log_deviation = abs(math.log(first_normalized / second_normalized))
                    uncertainty_terms = []
                    for observation in (first, second):
                        if observation.snr > 0.0 and math.isfinite(observation.snr):
                            uncertainty_terms.append(1.0 / observation.snr)
                        accuracy = abs(observation.accuracy_percent) / 100.0
                        if accuracy > 0.0 and math.isfinite(accuracy):
                            uncertainty_terms.append(accuracy)
                    if uncertainty_terms:
                        combined = math.sqrt(
                            sum(value * value for value in uncertainty_terms)
                        )
                        threshold = max(math.log(1.15), 3.0 * combined)
                        conclusive = True
                    else:
                        # Without an uncertainty estimate, only a mismatch of
                        # at least 50% is treated as evidence; a smaller
                        # difference remains explicitly inconclusive.
                        threshold = math.log(1.5)
                        conclusive = False
                    ratio = math.exp(log_deviation)
                    if log_deviation > threshold:
                        failed_checks += 1
                        message = (
                            f"same-upper-level ratio differs by a factor {ratio:.3g}"
                        )
                        if not conclusive:
                            message += " (uncertainty unavailable)"
                        add_reason(first, "Evidence", message)
                        add_reason(second, "Evidence", message)
                    elif conclusive:
                        conclusive_passes += 1
                        message = (
                            f"same-upper-level ratio agrees within uncertainty "
                            f"(factor {ratio:.3g})"
                        )
                        add_reason(first, "No mismatch", message)
                        add_reason(second, "No mismatch", message)

        unsafe_conditions = 0
        for observation in group:
            correction = group_corrections[id(observation.line)]
            if correction is None:
                continue
            multiplier = correction.multiplier
            if (
                not math.isfinite(multiplier)
                or multiplier <= 0.0
                or multiplier < 0.3
                or multiplier > (1.0 / 0.3)
            ):
                unsafe_conditions += 1
                reason = (
                    f"relative correction multiplier {multiplier:.3g} is "
                    "outside the configured 0.3 to 3.333 safety interval"
                )
                add_reason(observation, "Unsafe", reason)

        irsac_profile_quality: dict[int, str] = {}
        for observation in irsac_rows:
            if observation is reference:
                irsac_profile_quality[id(observation.line)] = reference_quality
                continue
            snr = observation.snr if math.isfinite(observation.snr) else 0.0
            warning = str(observation.fit_warning or "").strip()
            if snr > 0.0 and snr < 10.0:
                quality = "invalid"
                add_reason(
                    observation,
                    "Unsafe",
                    f"IRSAC target S/N={snr:.3g} is below 10",
                )
            elif warning:
                quality = "invalid"
                add_reason(
                    observation,
                    "Unsafe",
                    f"IRSAC target fit: {warning}",
                )
            elif observation.deconvolved_interference:
                quality = "invalid"
                add_reason(
                    observation,
                    "Unsafe",
                    "IRSAC target required deconvolution of an interfering peak",
                )
            elif snr >= 10.0:
                quality = "valid"
            else:
                quality = "unknown"
                add_reason(
                    observation,
                    "Not assessed",
                    "IRSAC target S/N/profile quality not available; refit Voigt first",
                )
            irsac_profile_quality[id(observation.line)] = quality
            if quality == "invalid":
                unsafe_conditions += 1

        for observation in palleschi_rows:
            correction = group_corrections[id(observation.line)]
            if (
                correction is not None
                and 1.02 < correction.multiplier <= (1.0 / 0.3)
            ):
                line_state[id(observation.line)]["recommended"] = True
                add_reason(
                    observation,
                    "Recommended",
                    "Palleschi/Stark width test indicates broadening by self-absorption",
                )

        irsac_supported = (
            failed_checks > 0
            and reference_quality == "valid"
            and unsafe_conditions == 0
        )
        if irsac_supported:
            for observation in irsac_rows:
                correction = group_corrections[id(observation.line)]
                if (
                    correction is not None
                    and irsac_profile_quality.get(id(observation.line)) == "valid"
                    and 0.3 <= correction.multiplier <= (1.0 / 0.3)
                    and abs(math.log(correction.multiplier)) > math.log(1.02)
                ):
                    line_state[id(observation.line)]["recommended"] = True
                    add_reason(
                        observation,
                        "Recommended",
                        "same-upper-level mismatch, clean Voigt fits and a "
                        "physical factor are compatible with IRSAC",
                    )

        recommended_lines = sum(
            1
            for observation in group
            if line_state[id(observation.line)]["recommended"]
        )
        if unsafe_conditions or reference_quality == "invalid":
            status = "Correction unsafe"
            message = (
                "Do not apply IRSAC automatically: a reference or calculated "
                "factor failed the physical/fit-quality checks."
            )
        elif recommended_lines:
            status = "Self-absorption compatible"
            message = (
                f"{failed_checks} equivalent-level mismatch(es), clean Voigt "
                "fits and/or a Palleschi/Stark width test support the selected "
                "corrections. This is evidence, not a unique proof."
            )
        elif equivalent_checks > 0 and failed_checks == 0 and conclusive_passes > 0:
            status = "No significant evidence"
            message = (
                "Available equivalent-upper-level ratios agree within their "
                "estimated uncertainty; IRSAC is not preselected."
            )
        else:
            status = "Not assessable"
            if reference_quality == "unknown":
                message = (
                    "The IRSAC reference has no stored S/N/profile-quality data. "
                    "Repeat the spectral fit explicitly, then recalculate IRSAC."
                )
            else:
                message = (
                    "No independent equivalent-level or Palleschi/Stark test "
                    "is available; a numerical IRSAC factor alone is not proof."
                )
        species_results[key] = SpeciesAssessment(
            key=key,
            status=status,
            message=message,
            equivalent_level_checks=equivalent_checks,
            failed_checks=failed_checks,
            reference_quality=reference_quality,
            recommended_lines=recommended_lines,
        )

    line_results = {
        line_id: LineAssessment(
            status=state["status"],
            reason="; ".join(state["reasons"]) or "No independent check available",
            recommended_use=bool(state["recommended"]),
            is_reference=bool(state["reference"]),
        )
        for line_id, state in line_state.items()
    }
    statuses = {assessment.status for assessment in species_results.values()}
    can_apply = any(
        assessment.recommended_use for assessment in line_results.values()
    )
    supported_species = [
        assessment
        for assessment in species_results.values()
        if assessment.recommended_lines > 0
    ]
    unsafe_species = [
        assessment
        for assessment in species_results.values()
        if assessment.status == "Correction unsafe"
    ]
    if supported_species and unsafe_species:
        status = "Selective correction available"
        message = (
            "Self-absorption is supported for at least one species. Only its "
            "validated rows are preselected; species with unsafe IRSAC factors "
            "remain uncorrected and are reported separately."
        )
    elif "Correction unsafe" in statuses:
        status = "Correction unsafe"
        message = (
            "At least one species failed the reference or physical-factor "
            "checks. Unsafe rows are disabled."
        )
    elif "Self-absorption compatible" in statuses:
        status = "Self-absorption compatible"
        message = (
            "The current-spectrum line-ratio/profile or Stark-width evidence "
            "is compatible with self-absorption; only supported rows are "
            "preselected."
        )
    elif "No significant evidence" in statuses:
        status = "No significant evidence"
        message = (
            "The available independent checks do not justify an automatic "
            "self-absorption correction."
        )
    else:
        status = "Not assessable"
        message = (
            "Independent optical-thinness evidence is insufficient. Refit "
            "Voigt profiles or provide suitable equivalent-level lines. No "
            "curve of growth or temporal trend is inferred from one spectrum."
        )
    return SelfAbsorptionAssessment(
        lines=line_results,
        species=species_results,
        status=status,
        message=message,
        can_apply=can_apply,
    )


def hybrid_self_absorption(
    observations: Iterable[LineObservation],
    initial_temperature_k: float,
    *,
    mode: str = "hybrid",
    thermometric_key: Optional[tuple[str, int]] = None,
    reference_wavelengths: Optional[dict[tuple[str, int], float]] = None,
    equation_mode: str = "staged",
    palleschi_factor: Optional[Callable[[LineObservation, float], Optional[float]]] = None,
    max_iterations: int = 100,
    relative_tolerance: float = 1.0e-3,
) -> HybridCorrectionResult:
    """Apply Palleschi/Stark or a selected IRSAC implementation.

    ``staged`` is the quantitative Aslam workflow used by pyLIBS. It derives
    the raw temperature from the selected thermometric species, corrects that
    species once with Eq. (6), freezes its corrected temperature, and then
    evaluates every other species at that temperature with its own internal
    reference. IRSAC changes integrated line intensities only: it neither
    refits peaks nor forces the independent species slopes to be parallel.

    ``iterative`` and ``excel_worksheet`` remain available only for explicit
    reproduction of earlier project calculations.
    """
    observations = list(observations)
    groups: dict[tuple[str, int], list[LineObservation]] = defaultdict(list)
    for obs in observations:
        groups[obs.key].append(obs)
    thermometric_key = thermometric_key or most_reliable_thermometric_key(observations)
    temperature = max(float(initial_temperature_k), 1.0)
    mode = str(mode or "hybrid").strip().lower()
    equation_mode = str(equation_mode or "staged").strip().lower()
    worksheet_equation = equation_mode in (
        "excel",
        "excel_worksheet",
        "worksheet",
    )
    iterative_equation = equation_mode in (
        "iterative",
        "pso",
        "yang2018",
        "yang_2018",
    )
    staged_equation = equation_mode in (
        "aslam",
        "aslam_staged",
        "internal_reference",
        "staged",
        "strict",
    )
    configured_references = reference_wavelengths or {}
    references = {
        key: (
            select_yang_reference_at_wavelength(group, configured_references[key])
            if key in configured_references
            else select_yang_reference(group)
        )
        for key, group in groups.items()
    }
    last_corrections: dict[int, LineCorrection] = {}
    converged = False
    iterations = 0

    def corrections_at(
        current_temperature: float,
        *,
        include_wavelength_ratio: Optional[bool] = None,
    ) -> dict[int, LineCorrection]:
        if include_wavelength_ratio is None:
            include_wavelength_ratio = worksheet_equation
        corrections: dict[int, LineCorrection] = {}
        for obs in observations:
            multiplier = None
            if mode in ("hybrid", "palleschi") and palleschi_factor is not None:
                multiplier = palleschi_factor(obs, current_temperature)
            if multiplier is not None and math.isfinite(multiplier) and multiplier >= 1.0:
                corrections[id(obs.line)] = LineCorrection(multiplier, "Palleschi/Stark")
                continue
            if mode in ("hybrid", "irsac", "yang", "yang/aslam"):
                reference = references.get(obs.key)
                factor = (
                    yang_aslam_factor(
                        obs,
                        reference,
                        current_temperature,
                        include_wavelength_ratio=include_wavelength_ratio,
                        wavelength_reference=(
                            configured_references.get(obs.key)
                            if include_wavelength_ratio
                            else None
                        ),
                    )
                    if reference is not None
                    else None
                )
                if factor is not None:
                    if staged_equation:
                        method = "IRSAC Aslam (staged)"
                    elif worksheet_equation:
                        method = "IRSAC legacy worksheet"
                    else:
                        method = "IRSAC Yang/Aslam"
                    corrections[id(obs.line)] = LineCorrection(
                        1.0 / factor,
                        method,
                        configured_references.get(obs.key, reference.wavelength),
                        factor,
                        factor < 0.3 or factor > 3.0,
                    )
        return corrections

    uses_irsac = mode in ("hybrid", "irsac", "yang", "yang/aslam")
    if uses_irsac:
        if iterative_equation:
            return _selective_iterative_irsac(
                observations,
                temperature,
                references,
                thermometric_key,
                mode=mode,
                palleschi_factor=palleschi_factor,
                max_iterations=max_iterations,
                relative_tolerance=relative_tolerance,
            )

        if staged_equation:
            raw_temperature = thermometric_temperature(
                observations,
                {},
                thermometric_key,
            )
            if raw_temperature <= 0.0 or not math.isfinite(raw_temperature):
                raw_temperature = temperature

            thermo = (
                groups.get(thermometric_key, [])
                if thermometric_key is not None
                else []
            )
            first_stage = corrections_at(
                raw_temperature,
                include_wavelength_ratio=False,
            )
            thermometric_corrections = {
                id(observation.line): first_stage[id(observation.line)]
                for observation in thermo
                if id(observation.line) in first_stage
            }
            corrected_temperature = _linear_temperature(
                thermo,
                thermometric_corrections,
            )
            converged = (
                corrected_temperature > 0.0
                and math.isfinite(corrected_temperature)
            )
            if not converged:
                corrected_temperature = raw_temperature

            last_corrections = corrections_at(
                corrected_temperature,
                include_wavelength_ratio=False,
            )
            # The thermometric correction is evaluated at its raw temperature.
            # Other species use the corrected and frozen thermometric T.
            for observation in thermo:
                line_id = id(observation.line)
                if line_id in thermometric_corrections:
                    last_corrections[line_id] = thermometric_corrections[line_id]
                else:
                    last_corrections.pop(line_id, None)

            slope_checks = _species_slope_checks(
                observations,
                last_corrections,
                corrected_temperature,
            )
            thermometric_check = slope_checks.get(thermometric_key, {})
            return HybridCorrectionResult(
                last_corrections,
                corrected_temperature,
                thermometric_key,
                1,
                converged,
                {},
                float(thermometric_check.get("rmse", math.inf)),
                (raw_temperature, corrected_temperature),
                tuple(sorted(last_corrections)),
                0.0,
                abs(corrected_temperature - raw_temperature)
                / max(abs(corrected_temperature), 1.0),
                True,
                slope_checks,
                (),
            )

        # Historical radiometric worksheet calculations remain available for
        # comparison, but are not the program's quantitative IRSAC mode.
        iterations = 1
        thermometric_corrections = corrections_at(temperature)
        last_corrections = thermometric_corrections
        thermo = groups.get(thermometric_key, []) if thermometric_key is not None else []
        temperature_corrections = (
            corrections_at(temperature, include_wavelength_ratio=False)
            if worksheet_equation
            else thermometric_corrections
        )
        updated = _linear_temperature(thermo, temperature_corrections)
        if updated > 0.0:
            temperature = updated
            converged = True
            other_corrections = corrections_at(temperature)
            last_corrections = dict(other_corrections)
            # The thermometric species remains corrected with the input
            # temperature, exactly as in the worksheet's first IRSAC stage.
            for obs in thermo:
                line_id = id(obs.line)
                if line_id in thermometric_corrections:
                    last_corrections[line_id] = thermometric_corrections[line_id]
                else:
                    last_corrections.pop(line_id, None)
        return HybridCorrectionResult(
            last_corrections,
            temperature,
            thermometric_key,
            iterations,
            converged,
        )

    # Palleschi-only mode retains its temperature-dependent width iteration.
    for iteration in range(1, max(1, int(max_iterations)) + 1):
        iterations = iteration
        corrections = corrections_at(temperature)
        last_corrections = corrections
        thermo = groups.get(thermometric_key, []) if thermometric_key is not None else []
        updated = _linear_temperature(thermo, corrections)
        if updated <= 0.0:
            break
        if abs(updated - temperature) / updated <= max(relative_tolerance, 1.0e-9):
            temperature = updated
            converged = True
            break
        temperature = updated

    last_corrections = corrections_at(temperature)
    return HybridCorrectionResult(last_corrections, temperature, thermometric_key, iterations, converged)
