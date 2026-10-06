"""Spectrum file parsing and writing helpers for pyLIBS."""

from __future__ import annotations

import struct
from collections import Counter
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


def read_ascii_metadata(filename: str) -> dict[str, str]:
    """Read pyLIBS metadata comments placed before the numeric spectrum."""
    metadata: dict[str, str] = {}
    with open(filename, "r", encoding="utf-8-sig", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith("#"):
                break
            content = line[1:].strip()
            key, separator, value = content.partition("=")
            key = key.strip().lower()
            if separator and key.startswith("pylibs_"):
                metadata[key] = value.strip()
    return metadata


def _numeric_ascii_row(line: str) -> list[float]:
    """Parse whitespace/tab/semicolon data while preserving decimal commas."""
    text = line.strip()
    if not text or text.startswith("#"):
        return []
    if ";" in text:
        tokens = [token.strip().replace(",", ".") for token in text.split(";")]
    elif "\t" in text:
        tokens = [token.strip().replace(",", ".") for token in text.split("\t")]
    elif len(text.split()) > 1:
        tokens = [token.replace(",", ".") for token in text.split()]
    else:
        # A comma is treated as a delimiter only when no whitespace exists.
        # A lone decimal-comma value is not a valid spectrum row anyway.
        tokens = [token.strip() for token in text.split(",")]
    values = []
    for token in tokens:
        if token == "":
            continue
        try:
            values.append(float(token))
        except ValueError:
            # The repository OPC format appends element/species labels after
            # its two numeric columns. Preserve the numeric prefix exactly as
            # the original ASCII reader did.
            return values if len(values) >= 2 else []
    return values


def read_ascii_spectrum_columns(
    filename: str,
    convert_nm_to_a: bool = False,
) -> tuple[list[float], list[list[float]]]:
    """Read wavelength plus one or more intensity columns."""
    rows = []
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            values = _numeric_ascii_row(line)
            if len(values) >= 2:
                rows.append(values)
    if not rows:
        raise ValueError("Il file non contiene dati numerici a due colonne.")
    # Use the most common row width so an occasional footer cannot silently
    # change the number of detector traces.
    width = Counter(len(row) for row in rows).most_common(1)[0][0]
    rows = [row[:width] for row in rows if len(row) >= width]
    xs = []
    columns = [[] for _ in range(width - 1)]
    for row in rows:
        wave = row[0]
        if convert_nm_to_a and wave < 1500:
            wave *= 10.0
        xs.append(wave)
        for index, value in enumerate(row[1:]):
            columns[index].append(value)
    return xs, columns


def read_ascii_spectrum(filename: str, convert_nm_to_a: bool = False) -> tuple[list[float], list[float]]:
    xs, columns = read_ascii_spectrum_columns(filename, convert_nm_to_a)
    return xs, columns[0]


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
