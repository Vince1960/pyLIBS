"""Spectrum file parsing and writing helpers for pyLIBS."""

from __future__ import annotations

import csv
import io
import math
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Optional

from pylibs.utils.formatting import safe_int
from pylibs.io.andor_sif import read_andor_sif
from pylibs.io.aryelle import read_aryelle


SPECTRUM_FILETYPES = [
    (
        "All Supported Spectrum Files",
        "*.txt *.TXT *.dat *.DAT *.roh *.ROH *.trt *.TRT *.mch *.MCH *.jnd *.JND *.asc *.ASC *.csv *.CSV *.sif *.SIF *.ary *.ARY",
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
    ("Andor SIF Files (*.sif *.SIF)", "*.sif *.SIF"),
    ("LTB ARYELLE Files (*.ary *.ARY)", "*.ary *.ARY"),
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
    if Path(filename).suffix.lower() == ".csv":
        xs, ys = read_csv_spectrum(filename, convert_nm_to_a)
        return xs, [ys]
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


_CSV_HEADER_WORDS = {
    "x", "y", "wavelength", "wavelength_nm", "lambda", "nm", "intensity",
    "signal", "counts", "count", "ordinate", "pixel", "frequency",
}


def _csv_number(value: str, delimiter: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError("empty numeric field")
    if "," in value and "." in value:
        raise ValueError("a numeric field mixes decimal comma and decimal point")
    if "," in value:
        # With comma delimiters, commas inside a field can only have come from
        # a quoted CSV field; this supports unambiguous quoted decimal commas.
        if delimiter != "," and value.count(",") == 1:
            value = value.replace(",", ".")
        elif delimiter == "," and value.count(",") == 1:
            value = value.replace(",", ".")
        else:
            raise ValueError("ambiguous decimal-comma number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite numeric value")
    return number


def _csv_header_row(row: list[str]) -> bool:
    if len(row) != 2:
        return False
    normalized = [re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") for value in row]
    if all(value in _CSV_HEADER_WORDS for value in normalized):
        return True
    # Permit ordinary descriptive labels, but never discard a row containing
    # a numeric-looking field as a supposed header.
    return all(value and re.search(r"[A-Za-z]", value) for value in row)


def read_csv_spectrum(
    filename: str,
    convert_nm_to_a: bool = False,
) -> tuple[list[float], list[float]]:
    """Read a two-column CSV spectrum with strict delimiter inference.

    Comma, semicolon and tab delimiters are supported. Decimal commas are
    accepted inside semicolon/tab separated fields and quoted comma-delimited
    fields. Bare comma-delimited decimal-comma data is rejected as ambiguous.
    """
    try:
        text = Path(filename).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV spectrum must be UTF-8 text (an optional BOM is supported).") from exc
    if not text.strip():
        raise ValueError("CSV spectrum is empty.")

    candidates: list[tuple[str, list[float], list[float]]] = []
    failures: list[str] = []
    ambiguous_decimal_comma = False
    for delimiter in (",", ";", "\t"):
        try:
            rows = [
                [cell.strip() for cell in row]
                for row in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
                if any(cell.strip() for cell in row)
            ]
        except csv.Error as exc:
            failures.append(f"{delimiter!r} delimiter: malformed quoting ({exc})")
            continue
        if not rows:
            continue
        has_header = len(rows[0]) == 2 and _csv_header_row(rows[0])
        data_rows = rows[1:] if has_header else rows
        if not data_rows:
            failures.append(f"{delimiter!r} delimiter: no numeric rows")
            continue
        xs: list[float] = []
        ys: list[float] = []
        problem = None
        for row_number, row in enumerate(data_rows, start=2 if has_header else 1):
            if len(row) != 2:
                if delimiter == "," and len(row) > 2 and all(
                    _is_plain_numeric_cell(cell) for cell in row
                ):
                    ambiguous_decimal_comma = True
                problem = f"row {row_number} has {len(row)} fields; expected exactly 2"
                break
            try:
                x_value = _csv_number(row[0], delimiter)
                y_value = _csv_number(row[1], delimiter)
            except ValueError as exc:
                problem = f"row {row_number}: {exc}"
                break
            xs.append(x_value)
            ys.append(y_value)
        if problem:
            failures.append(f"{delimiter!r} delimiter: {problem}")
        elif xs:
            candidates.append((delimiter, xs, ys))
    if len(candidates) > 1:
        names = ", ".join("tab" if delim == "\t" else delim for delim, _, _ in candidates)
        raise ValueError(f"Ambiguous CSV spectrum: multiple delimiters are valid ({names}).")
    if not candidates:
        if ambiguous_decimal_comma:
            raise ValueError(
                "Ambiguous CSV spectrum: comma-separated fields may be decimal-comma values; "
                "use semicolons or tabs between columns."
            )
        detail = failures[0] if failures else "no two-column numeric data found"
        raise ValueError(f"Invalid CSV spectrum: {detail}.")
    _, xs, ys = candidates[0]
    if convert_nm_to_a:
        xs = [wave * 10.0 if wave < 1500 else wave for wave in xs]
    return xs, ys


def _is_plain_numeric_cell(value: str) -> bool:
    """Return whether a comma-delimited cell is a numeric decimal-point value."""
    try:
        return math.isfinite(float(value.strip()))
    except ValueError:
        return False


def convert_csv_batch(
    filenames: list[str | Path], output_directory: str | Path
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Convert CSV spectra to headerless tab-separated ASCII XY files."""
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    converted: list[Path] = []
    failed: list[tuple[Path, str]] = []
    claimed: set[str] = set()
    for source_value in filenames:
        source = Path(source_value)
        destination = output_dir / f"{source.stem}.txt"
        key = destination.name.casefold()
        if key in claimed or destination.exists():
            failed.append((source, f"Output already exists: {destination.name}"))
            continue
        try:
            wavelength, intensity = read_csv_spectrum(str(source))
            with destination.open("w", encoding="ascii", newline="\n") as handle:
                for x_value, y_value in zip(wavelength, intensity):
                    handle.write(f"{x_value:.17g}\t{y_value:.17g}\n")
            claimed.add(key)
            converted.append(destination)
        except Exception as exc:
            failed.append((source, str(exc)))
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
    return converted, failed


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
    if Path(filename).suffix.lower() == ".ary":
        xs, ys = read_aryelle(filename)
        if getattr(options, "convert_to_angstrom", False):
            xs = xs * 10.0
        return spectrum_cls(xs.tolist(), ys.tolist(), Path(filename).name, filename)
    if Path(filename).suffix.lower() == ".sif":
        xs, ys = read_andor_sif(filename)
        if getattr(options, "convert_to_angstrom", False):
            xs = xs * 10.0
        return spectrum_cls(xs.tolist(), ys.tolist(), Path(filename).name, filename)
    if is_roh_spectrum_file(filename):
        return spectrum_cls.from_roh(
            filename,
            getattr(options, "convert_to_angstrom", False),
            getattr(options, "limit_low", None),
            getattr(options, "limit_high", None),
        )
    return spectrum_cls.from_ascii(filename, getattr(options, "convert_to_angstrom", False))
