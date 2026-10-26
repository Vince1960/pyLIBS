"""Reader for single-spectrum LTB ARYELLE ZIP containers."""

from __future__ import annotations

import math
import zipfile
from pathlib import Path

import numpy as np


_MAX_POINTS = 100_000_000


def read_aryelle(filename: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Read an ARYELLE ``.ary`` as ascending wavelength and original intensity.

    Only the member ending in ``.~tmp`` is read. Auxiliary and acquisition
    members are never opened or interpreted.
    """
    path = Path(filename)
    try:
        with zipfile.ZipFile(path, "r") as archive:
            candidates = [info for info in archive.infolist()
                          if not info.is_dir() and info.filename.lower().endswith(".~tmp")]
            if len(candidates) != 1:
                raise ValueError(
                    "ARYELLE file must contain exactly one spectral data member ending in .~tmp."
                )
            info = candidates[0]
            if info.file_size == 0 or info.file_size % 8:
                raise ValueError("ARYELLE spectral data is empty or has an incomplete float pair.")
            count = info.file_size // 8
            if count < 2 or count > _MAX_POINTS:
                raise ValueError("ARYELLE spectral data has an unsupported point count.")
            payload = archive.read(info)
    except ValueError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError) as exc:
        raise ValueError(f"Could not read ARYELLE ZIP container: {exc}") from exc

    if len(payload) != info.file_size:
        raise ValueError("ARYELLE spectral data is truncated.")
    pairs = np.frombuffer(payload, dtype="<f4")
    intensities = pairs[0::2]
    wavelengths = pairs[1::2]
    if not np.all(np.isfinite(pairs)):
        raise ValueError("ARYELLE spectral data contains non-finite values.")
    if np.any(wavelengths <= 0) or not np.all(np.diff(wavelengths) > 0) and not np.all(np.diff(wavelengths) < 0):
        raise ValueError("ARYELLE wavelengths must be positive and strictly monotonic.")
    if not all(math.isfinite(float(value)) for value in (wavelengths[0], wavelengths[-1])):
        raise ValueError("ARYELLE spectral data contains invalid wavelengths.")
    if wavelengths[0] > wavelengths[-1]:
        wavelengths = wavelengths[::-1]
        intensities = intensities[::-1]
    return wavelengths, intensities


def convert_aryelle_batch(
    filenames: list[str | Path], output_directory: str | Path, progress=None
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Convert ARYELLE files (or directories of them) to headerless XY text."""
    sources: list[Path] = []
    for value in filenames:
        source = Path(value)
        if source.is_dir():
            sources.extend(sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() == ".ary"))
        else:
            sources.append(source)
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    converted: list[Path] = []
    failed: list[tuple[Path, str]] = []
    claimed: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if progress:
            progress(index, len(sources), source)
        destination = output_dir / f"{source.stem}.txt"
        key = destination.name.casefold()
        if key in claimed or destination.exists():
            failed.append((source, f"Output already exists: {destination.name}"))
            continue
        created = False
        try:
            wavelength, intensity = read_aryelle(source)
            with destination.open("x", encoding="ascii", newline="\n") as handle:
                created = True
                for x_value, y_value in zip(wavelength, intensity):
                    handle.write(f"{float(x_value):.17g}\t{float(y_value):.17g}\n")
            claimed.add(key)
            converted.append(destination)
        except Exception as exc:
            failed.append((source, str(exc)))
            if created:
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    pass
    return converted, failed
