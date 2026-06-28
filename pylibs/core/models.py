"""Passive core data models for pyLIBS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TemplateLine:
    wavelen: float
    specie: str = ""
    ion: int = 0
    asswavelen: float = 0.0
    inte: float = 0.0
    ei: float = 0.0
    wg: float = 0.0
    wl: float = 0.0
    ek: float = 0.0
    aki: float = 0.0
    gk: int = 0
    gi: int = 0
    fitwavelen: float = 0.0
    templint: float = 0.0
    error_inte: float = 0.0
    acc: int = 0


@dataclass
class AtomicLine:
    wavelen: float
    specie: str
    ion: int
    inte: float = 0.0
    ei: float = 0.0
    ek: float = 0.0
    gi: int = 0
    gk: int = 0
    aki: float = 0.0
    acc: int = 0
