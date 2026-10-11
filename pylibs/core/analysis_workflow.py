"""Explicit ordering rules for the self-absorption analysis workflow."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class TheoreticalSpectrumReadiness:
    ready: bool
    message: str
    temperature_ev: Optional[float] = None
    temperature_source: str = ""


def irsac_correction_status(result: Optional[Mapping], applied: bool) -> tuple[bool, str]:
    """Return whether an IRSAC-capable correction has been calculated and applied."""
    if not result:
        return False, "Calculate IRSAC before the theoretical spectrum."
    if not bool(result.get("irsac_completed", False)):
        return False, "The selected correction did not run IRSAC; use hybrid or IRSAC mode."
    equation_mode = str(result.get("equation_mode", "") or "").strip().lower()
    if (
        equation_mode in ("iterative", "pso", "yang2018", "yang_2018")
        and not bool(result.get("converged", False))
    ):
        return False, "The iterative IRSAC temperature optimization did not converge."
    if int(result.get("corrected_lines", 0) or 0) <= 0:
        return False, "IRSAC did not produce any valid line correction."
    if not applied or not bool(result.get("applied", False)):
        return False, "Apply the IRSAC correction before continuing."
    if int(result.get("enabled_lines", 0) or 0) <= 0:
        return False, "Enable at least one valid corrected line in the IRSAC table."
    return True, "IRSAC correction applied."


def theoretical_spectrum_readiness(
    result: Optional[Mapping],
    applied: bool,
    post_irsac_temperature_ev,
    post_irsac_temperature_source: str = "",
) -> TheoreticalSpectrumReadiness:
    """Gate theory behind a self-absorption decision and reliable temperature."""
    assessment_status = str(
        (result or {}).get("assessment_status", "") if result else ""
    ).strip().lower()
    correction_not_required = (
        assessment_status == "no significant evidence" and not applied
    )
    if not correction_not_required:
        correction_ready, message = irsac_correction_status(result, applied)
        if not correction_ready:
            return TheoreticalSpectrumReadiness(False, message)
    try:
        temperature = float(post_irsac_temperature_ev)
    except (TypeError, ValueError):
        temperature = 0.0
    if not math.isfinite(temperature) or temperature <= 0.0:
        return TheoreticalSpectrumReadiness(
            False,
            "Recalculate Saha-Boltzmann after IRSAC using Most reliable element.",
        )
    source = str(post_irsac_temperature_source or "").strip()
    if not source:
        return TheoreticalSpectrumReadiness(
            False,
            "The analysis temperature has no reliable thermometric provenance.",
        )
    if correction_not_required:
        return TheoreticalSpectrumReadiness(
            True,
            (
                "Independent line checks found no significant self-absorption; "
                "the pre-correction temperature is ready for diagnostic theory."
            ),
            temperature,
            source,
        )
    return TheoreticalSpectrumReadiness(
        True,
        "IRSAC and the post-IRSAC temperature are ready; theory is diagnostic only.",
        temperature,
        source,
    )
