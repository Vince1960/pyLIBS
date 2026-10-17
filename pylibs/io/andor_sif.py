"""Reader for calibrated, extracted one dimensional Andor SIF spectra.

Andor does not publish a complete stable SIF specification. This reader
implements the text-header / float32 payload layout used by Solis SIF files
with the ``Pixel number`` dimension record and rejects other layouts.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np


_MAGIC = b"Andor Technology Multi-Channel File"
_MAX_POINTS = 100_000_000


def _line_values(line: bytes, label: str) -> list[float]:
    """Return finite numeric values from a UTF-8/Latin-1 header line."""
    try:
        text = line.decode("ascii").strip()
        values = [float(token) for token in text.split()]
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"Andor SIF: invalid {label} record.") from exc
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError(f"Andor SIF: invalid {label} record.")
    return values


def read_andor_sif(filename: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a single extracted 1D SIF spectrum as wavelength and intensity.

    Wavelength coefficients are stored in ascending polynomial order and are
    evaluated at Andor's 1-based pixel coordinates, matching the SIF reader
    calibration convention. SIF pixel samples are little endian float32.
    """
    path = Path(filename)
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise ValueError(f"Could not open Andor SIF file: {exc}") from exc
    with handle:
        first_line = handle.readline()
        if not first_line.startswith(_MAGIC):
            raise ValueError("Not an Andor SIF file (missing Andor file signature).")

        # Read only the text header. Old SIF variants can include an earlier
        # short "Pixel number" label, so require a complete dimension record.
        header_lines = [first_line]
        header_bytes = len(first_line)
        record = None
        while True:
            line = handle.readline()
            if not line:
                break
            header_lines.append(line)
            header_bytes += len(line)
            if line.startswith(b"Pixel number"):
                tokens = line[len(b"Pixel number"):].strip().split()
                if len(tokens) >= 8:
                    record = tokens
                    break
            if header_bytes > 16 * 1024 * 1024:
                raise ValueError("Andor SIF header is unreasonably large.")
        if record is None:
            raise ValueError(
                "Unsupported Andor SIF variant: no extracted-spectrum Pixel number dimensions found."
            )
        coordinate_line = handle.readline()
        terminator_line = handle.readline()
        data_offset = handle.tell()
        file_size = path.stat().st_size

    if len(coordinate_line) == 0 or len(terminator_line) == 0:
        raise ValueError(
            "Andor SIF header is truncated after the Pixel number record."
        )

    # The first token is the record version; next five tokens are C, X, Y, Z,
    # T dimensions. The coordinate record stores start/end/binning for X/Y.
    try:
        version = int(record[0])
        size_c, _declared_x, _declared_y, size_z, size_t = map(int, record[1:6])
        coords = _line_values(coordinate_line.rstrip(b"\r\n"), "coordinate")
        terminator = terminator_line.strip()
    except (ValueError, IndexError) as exc:
        raise ValueError("Andor SIF contains malformed spectrum dimensions.") from exc
    if version < 65535 or any(v <= 0 for v in (size_c, _declared_x, _declared_y, size_z, size_t)):
        raise ValueError("Andor SIF contains invalid or unsupported dimensions.")
    if size_c != 1 or size_z != 1 or size_t != 1:
        raise ValueError(
            "Unsupported Andor SIF variant: only a single extracted 1D spectrum is supported."
        )
    if len(coords) < 7 or terminator != b"0":
        raise ValueError("Unsupported Andor SIF spectrum data layout.")
    # Coordinate tuples are version, x-start, y-start, x-end, y-end,
    # x-binning, y-binning in the Solis Pixel number layout.
    try:
        _, x_start, y_start, x_end, y_end, x_bin, y_bin = map(int, coords[:7])
    except ValueError as exc:
        raise ValueError("Andor SIF contains malformed spectrum dimensions.") from exc
    width = (abs(x_end - x_start) + x_bin)
    height = (abs(y_end - y_start) + y_bin)
    if height != 1:
        raise ValueError(
            "Unsupported Andor SIF variant: only a single extracted 1D spectrum is supported."
        )
    if x_bin <= 0 or y_bin <= 0 or width <= 0:
        raise ValueError("Andor SIF dimensions disagree with the spectrum coordinate record.")
    if width > _MAX_POINTS:
        raise ValueError("Andor SIF declares an unreasonable spectrum size.")

    coefficients = None
    for i, raw_line in enumerate(header_lines[:-1]):
        fields = raw_line.strip().split()
        if fields and fields[0] == b"65539":
            if i + 1 >= len(header_lines) - 1:
                break
            values = _line_values(header_lines[i + 1].rstrip(b"\r\n"), "wavelength calibration")
            if len(values) < 2 or len(values) > 8:
                raise ValueError("Andor SIF has an unsupported wavelength calibration order.")
            coefficients = values
    if coefficients is None:
        raise ValueError("Andor SIF wavelength calibration coefficients were not found.")

    payload_size = width * 4
    # Standard SIF files end with an 8 byte trailer. Permit no trailer too,
    # while rejecting unexplained bytes that could signal a different variant.
    remaining = file_size - data_offset
    if remaining < payload_size:
        raise ValueError("Andor SIF file is truncated: declared pixel data is incomplete.")
    if remaining - payload_size not in (0, 8):
        raise ValueError(
            "Unsupported Andor SIF variant: unexpected pixel type, payload size, or trailer."
        )
    with path.open("rb") as handle:
        handle.seek(data_offset)
        payload = handle.read(payload_size)
    if len(payload) != payload_size:
        raise ValueError("Andor SIF file is truncated: declared pixel data is incomplete.")
    intensities = np.frombuffer(payload, dtype="<f4", count=width).copy()
    if not np.all(np.isfinite(intensities)):
        raise ValueError("Andor SIF pixel data contains non-finite values.")
    nonzero = intensities != 0
    if np.any(nonzero) and np.all(np.abs(intensities[nonzero]) < np.finfo(np.float32).tiny):
        swapped = np.frombuffer(payload, dtype=">f4", count=width)
        if np.any(np.isfinite(swapped) & (np.abs(swapped) >= np.finfo(np.float32).tiny)):
            raise ValueError("Unsupported Andor SIF byte order: expected little endian float32 data.")
    pixels = np.arange(1, width + 1, dtype=np.float64)
    wavelengths = np.polynomial.polynomial.polyval(pixels, coefficients)
    return wavelengths, intensities


def convert_sif_batch(
    filenames: list[str | Path], output_directory: str | Path
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Convert each supported SIF to a headerless tab-separated XY file."""
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
        claimed.add(key)
        try:
            wavelength, intensity = read_andor_sif(source)
            with destination.open("w", encoding="ascii", newline="\n") as handle:
                for x_value, y_value in zip(wavelength, intensity):
                    handle.write(f"{float(x_value):.17g}\t{float(y_value):.17g}\n")
            converted.append(destination)
        except Exception as exc:
            failed.append((source, str(exc)))
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
    return converted, failed
