"""Boltzmann-plot intensity conventions.

An energy-domain response requires conversion from radiant energy to photon
number through ``lambda/(h*c)``.  A photon-counting response has already made
that conversion and must not receive the wavelength factor a second time.
"""

from __future__ import annotations

import math


PLANCK_CONSTANT_J_S = 6.62607015e-34
SPEED_OF_LIGHT_M_S = 299792458.0
NM_TO_M = 1.0e-9
PHOTONS_PER_JOULE_NM = NM_TO_M / (PLANCK_CONSTANT_J_S * SPEED_OF_LIGHT_M_S)
ENERGY_INTENSITY_MODE = "energy"
PHOTON_INTENSITY_MODE = "photon"
SUPPORTED_INTENSITY_MODES = (ENERGY_INTENSITY_MODE, PHOTON_INTENSITY_MODE)


def normalize_intensity_mode(value: str) -> str:
    """Return a stable intensity-convention key."""
    mode = str(value or ENERGY_INTENSITY_MODE).strip().lower()
    aliases = {
        "radiometric": ENERGY_INTENSITY_MODE,
        "energy_calibrated": ENERGY_INTENSITY_MODE,
        "photon_counting": PHOTON_INTENSITY_MODE,
        "counts": PHOTON_INTENSITY_MODE,
    }
    mode = aliases.get(mode, mode)
    if mode not in SUPPORTED_INTENSITY_MODES:
        raise ValueError(f"Unsupported Boltzmann intensity mode: {value}")
    return mode


def wavelength_in_nm(wavelength: float, unit_label: str = "nm") -> float:
    """Return a positive wavelength in nm from an nm or angstrom value."""
    value = abs(float(wavelength))
    if value <= 0.0 or not math.isfinite(value):
        raise ValueError("Wavelength must be positive and finite.")
    unit = str(unit_label or "nm").strip().lower()
    if unit in ("a", "aa", "angstrom", "angstroms", "angstroem", "angstroems", "å"):
        return value / 10.0
    if unit == "nm" or unit.startswith("nanomet"):
        return value
    raise ValueError(f"Unsupported wavelength unit: {unit_label}")


def photon_equivalent_line_intensity(energy_intensity: float, wavelength_nm: float) -> float:
    """Convert radiant line intensity to the corresponding photon intensity."""
    intensity = float(energy_intensity)
    wavelength = wavelength_in_nm(wavelength_nm, "nm")
    if intensity <= 0.0 or not math.isfinite(intensity):
        raise ValueError("Radiometric line intensity must be positive and finite.")
    return PHOTONS_PER_JOULE_NM * intensity * wavelength


def boltzmann_population_intensity(
    intensity: float,
    wavelength_nm: float,
    intensity_mode: str = ENERGY_INTENSITY_MODE,
) -> float:
    """Return the photon-domain intensity used in the Boltzmann ordinate."""
    value = float(intensity)
    if value <= 0.0 or not math.isfinite(value):
        raise ValueError("Line intensity must be positive and finite.")
    mode = normalize_intensity_mode(intensity_mode)
    if mode == PHOTON_INTENSITY_MODE:
        return value
    return photon_equivalent_line_intensity(value, wavelength_nm)


def radiometric_boltzmann_ordinate(
    energy_intensity: float,
    wavelength_nm: float,
    aki: float,
    gk: float,
    intensity_mode: str = ENERGY_INTENSITY_MODE,
) -> float:
    """Return the Boltzmann ordinate for the selected intensity convention."""
    ag = abs(float(aki) * float(gk))
    if ag <= 0.0 or not math.isfinite(ag):
        raise ValueError("Aki*gk must be non-zero and finite.")
    population_intensity = boltzmann_population_intensity(
        energy_intensity,
        wavelength_nm,
        intensity_mode,
    )
    return math.log(population_intensity / ag)


def radiometric_line_intensity_from_ordinate(
    ordinate: float,
    wavelength_nm: float,
    aki: float,
    gk: float,
    intensity_mode: str = ENERGY_INTENSITY_MODE,
) -> float:
    """Invert :func:`radiometric_boltzmann_ordinate`."""
    ag = abs(float(aki) * float(gk))
    wavelength = wavelength_in_nm(wavelength_nm, "nm")
    if ag <= 0.0 or not math.isfinite(ag):
        raise ValueError("Aki*gk must be non-zero and finite.")
    population_intensity = math.exp(float(ordinate)) * ag
    mode = normalize_intensity_mode(intensity_mode)
    if mode == PHOTON_INTENSITY_MODE:
        return population_intensity
    return population_intensity / (PHOTONS_PER_JOULE_NM * wavelength)
