"""Spectrum file parsing and writing helpers for pyLIBS."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional

from pylibs.utils.formatting import safe_int


SPECTRUM_FILETYPES = [
    (
        "All Supported Spectrum Files",
        "*.txt *.TXT *.dat *.DAT *.roh *.ROH *.trt *.TRT *.mch *.MCH *.jnd *.JND *.asc *.ASC *.csv *.CSV",
    ),
    ("ASCII Files (*.txt *.TXT)", "*.txt *.TXT"),
    ("Data Files (*.dat *.DAT)", "*.dat *.DAT"),
    ("ROH Files (*.roh *.ROH)", "*.roh *.ROH"),
    ("Avantes ROH (*.roh *.ROH)", "*.roh *.ROH"),
    ("TRT Files (*.trt *.TRT)", "*.trt *.TRT"),
    ("Mechelle Files (*.mch *.MCH)", "*.mch *.MCH"),
    ("Joined Files (*.jnd *.JND)", "*.jnd *.JND"),
    ("ASC Files (*.asc *.ASC)", "*.asc *.ASC"),
    ("CSV Files (*.csv *.CSV)", "*.csv *.CSV"),
    ("All", "*.*"),
]


def read_ascii_spectrum(filename: str, convert_nm_to_a: bool = False) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip().replace(",", ".")
            if not line or line.startswith("#"):
                continue
            p = line.split()
            if len(p) < 2:
                continue
            try:
                wave = float(p[0])
                inten = float(p[1])
            except Exception:
                continue
            if convert_nm_to_a and wave < 1500:
                wave *= 10.0
            xs.append(wave)
            ys.append(inten)
    if not xs:
        raise ValueError("Il file non contiene dati numerici a due colonne.")
    return xs, ys


def read_roh_spectrum(
    filename: str,
    convert_nm_to_a: bool = False,
    limit_low: Optional[float] = None,
    limit_high: Optional[float] = None,
) -> tuple[list[float], list[float]]:
    data = Path(filename).read_bytes()
    if len(data) < 4:
        raise ValueError(".ROH file is too short or corrupted.")
    total = len(data) // 4
    offset = 0

    def read_float(label: str) -> float:
        nonlocal offset
        if offset >= total:
            raise ValueError(f".ROH file is too short while reading {label}.")
        value = struct.unpack_from("<f", data, offset * 4)[0]
        offset += 1
        return value

    def skip(count: int, label: str):
        nonlocal offset
        if offset + count > total:
            raise ValueError(f".ROH file is too short while skipping {label}.")
        offset += count

    version = read_float("version")
    if version < 70:
        start_w = read_float("start_w")
        res_w = read_float("res_w")
        quadr = read_float("quadr")
        cub = read_float("cub")
        skip(11, "header")
        npoints = safe_int(read_float("npoints"), 0)
        skip(3, "header")
        start_index, end_index = 0, npoints
    else:
        skip(73, "header")
        start_w = read_float("start_w")
        res_w = read_float("res_w")
        quadr = read_float("quadr")
        cub = read_float("cub")
        read_float("quart")
        start_index = safe_int(read_float("startt"), 0)
        end_index = safe_int(read_float("endd"), 0)
        skip(19, "header")

    if end_index <= start_index:
        raise ValueError(".ROH file contains no valid spectrum points.")
    needed = end_index - start_index
    if offset + needed > total:
        raise ValueError(".ROH file is too short while reading intensities.")

    lo = min(limit_low, limit_high) if limit_low is not None and limit_high is not None else None
    hi = max(limit_low, limit_high) if limit_low is not None and limit_high is not None else None
    xs, ys = [], []
    for nq in range(start_index, end_index):
        wave = start_w + nq * res_w + quadr * nq * nq + cub * nq * nq * nq
        inten = read_float("intensity")
        if convert_nm_to_a and wave < 1500:
            wave *= 10.0
        if lo is not None and hi is not None and not (lo <= wave <= hi):
            continue
        xs.append(wave)
        ys.append(inten)
    if not xs:
        raise ValueError(".ROH file contains no points in the configured wavelength range.")
    return xs, ys


def write_ascii_spectrum(filename: str, x_values, y_values) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        for x, y in zip(x_values, y_values):
            f.write(f"{x:.8g} {y:.8g}\n")


def is_roh_spectrum_file(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".roh"


def load_spectrum_for_open(filename: str, options, spectrum_cls):
    if is_roh_spectrum_file(filename):
        return spectrum_cls.from_roh(
            filename,
            getattr(options, "convert_to_angstrom", False),
            getattr(options, "limit_low", None),
            getattr(options, "limit_high", None),
        )
    return spectrum_cls.from_ascii(filename, getattr(options, "convert_to_angstrom", False))
