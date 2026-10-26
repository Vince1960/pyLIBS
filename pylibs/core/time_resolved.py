"""Batch reconstruction of finite-window LIBS emission spectra."""

from __future__ import annotations

import math
import os
import re
import tempfile
from pathlib import Path

from pylibs.io.spectrum_io import read_ascii_spectrum, read_ascii_metadata, write_ascii_spectrum

WRITABLE_SUFFIXES = {".txt", ".dat", ".trt", ".mch", ".jnd", ".asc", ".csv"}


def natural_sort_key(value):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(value))]


def pair_spectra(group_a, group_b):
    """Return stable natural-sorted one-to-one pairs, rejecting unequal groups."""
    order = lambda p: (natural_sort_key(p.name), str(p).casefold())
    a = sorted((Path(p) for p in group_a), key=order)
    b = sorted((Path(p) for p in group_b), key=order)
    if len(a) != len(b):
        raise ValueError(f"Groups contain different numbers of files: Group A has {len(a)}, Group B has {len(b)}.")
    return list(zip(a, b))


def _delay_text(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Delay values must be finite numbers.")
    if value.is_integer():
        return str(int(value))
    return format(value, ".15g").replace("-", "m").replace(".", "p")


def validate_output_prototype(prototype):
    value = str(prototype).strip()
    if not value:
        raise ValueError("Enter an output filename prototype.")
    if value in {".", ".."} or any(ord(ch) < 32 or ch in '<>:"/\\|?*' for ch in value):
        raise ValueError("The prototype contains invalid filename characters or a path separator.")
    if value.endswith((".", " ")):
        raise ValueError("The prototype cannot end with a dot or space.")
    if Path(value).suffix:
        raise ValueError("Enter the prototype without a file extension.")
    return value


def time_resolved_output_path(source, output_directory, t1, t2, prototype="Spectrum", number=1, total=1):
    source = Path(source)
    prototype = validate_output_prototype(prototype)
    width = max(3, len(str(max(1, int(total)))))
    return Path(output_directory) / (
        f"{prototype}--d{_delay_text(t1)}-g{_delay_text(float(t2)-float(t1))}-{int(number):0{width}d}{source.suffix}"
    )


def subtract_spectra(wavelength_a, intensity_a, wavelength_b, intensity_b, *, atol=1e-7, rtol=1e-9):
    if len(wavelength_a) != len(wavelength_b):
        raise ValueError(f"Different wavelength point counts ({len(wavelength_a)} and {len(wavelength_b)}).")
    if len(intensity_a) != len(wavelength_a) or len(intensity_b) != len(wavelength_b):
        raise ValueError("Wavelength and intensity arrays have different lengths.")
    if not all(math.isfinite(float(v)) for v in (*wavelength_a, *wavelength_b, *intensity_a, *intensity_b)):
        raise ValueError("Spectrum contains non-finite wavelength or intensity values.")
    for index, (wa, wb) in enumerate(zip(wavelength_a, wavelength_b), 1):
        if not math.isclose(float(wa), float(wb), rel_tol=rtol, abs_tol=atol):
            raise ValueError(f"Wavelength mismatch at point {index}: {wa} vs {wb}.")
    return list(wavelength_a), [max(0.0, float(a) - float(b)) for a, b in zip(intensity_a, intensity_b)]


def _write_result(path, source, wavelengths, intensities):
    """Write via pyLIBS ASCII utility; CSV is emitted as conventional XY CSV."""
    metadata = read_ascii_metadata(str(source)) if source.suffix.lower() != ".csv" else {}
    if path.suffix.lower() == ".csv":
        import csv
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(zip(wavelengths, intensities))
    else:
        write_ascii_spectrum(str(path), wavelengths, intensities)
    if metadata and path.suffix.lower() != ".csv":
        body = path.read_text(encoding="utf-8")
        comments = "".join(f"# {key}={value}\n" for key, value in metadata.items())
        path.write_text(comments + body, encoding="utf-8")


def process_time_resolved_pairs(group_a, group_b, t1, t2, output_directory, prototype, *, overwrite=False):
    """Process file pairs independently; return output paths and pair errors."""
    try:
        t1, t2 = float(t1), float(t2)
    except (TypeError, ValueError) as exc:
        raise ValueError("Delays must be numeric values.") from exc
    if not (math.isfinite(t1) and math.isfinite(t2)) or t1 < 0 or t2 < 0:
        raise ValueError("Delays must be finite, nonnegative numbers.")
    if t2 <= t1:
        raise ValueError("The second delay must be greater than the first delay.")
    pairs = pair_spectra(group_a, group_b)
    prototype = validate_output_prototype(prototype)
    output_dir = Path(output_directory)
    if not output_dir.exists() or not output_dir.is_dir():
        raise ValueError(f"Output directory does not exist: {output_dir}")
    if not os.access(output_dir, os.W_OK | os.X_OK):
        raise ValueError(f"Output directory is not writable: {output_dir}")
    try:
        fd, probe = tempfile.mkstemp(prefix=".pylibs-write-check-", dir=output_dir)
        os.close(fd)
        Path(probe).unlink()
    except OSError as exc:
        raise ValueError(f"Output directory is not writable: {output_dir} ({exc})") from exc
    saved, failed = [], []
    claimed = set()
    for pair_index, (first, second) in enumerate(pairs, 1):
        destination = time_resolved_output_path(first, output_dir, t1, t2, prototype, pair_index, len(pairs))
        try:
            if first.suffix.lower() not in WRITABLE_SUFFIXES or second.suffix.lower() not in WRITABLE_SUFFIXES:
                raise ValueError("Unsupported format for reliable time-resolved output (SIF/ROH are read-only).")
            key = destination.name.casefold()
            if (destination.exists() and not overwrite) or key in claimed:
                raise FileExistsError(f"Output already exists: {destination.name}")
            xa, ya = read_ascii_spectrum(str(first))
            xb, yb = read_ascii_spectrum(str(second))
            x, y = subtract_spectra(xa, ya, xb, yb)
            fd, temporary = tempfile.mkstemp(prefix=".pylibs-time-resolved-", suffix=destination.suffix, dir=output_dir)
            os.close(fd)
            try:
                _write_result(Path(temporary), first, x, y)
                # Atomic install: never replace unless the caller explicitly confirmed it.
                if overwrite:
                    os.replace(temporary, destination)
                else:
                    os.link(temporary, destination)
            finally:
                Path(temporary).unlink(missing_ok=True)
            claimed.add(key)
            saved.append(destination)
        except Exception as exc:
            failed.append((first, second, str(exc)))
    return pairs, saved, failed
