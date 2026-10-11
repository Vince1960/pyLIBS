"""Spectrum preprocessing shared by the GUI and scientific tests."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DarkCorrectionResult:
    intensity: list[float]
    dark: list[float]
    signal_column: int
    dark_columns: tuple[int, ...]
    source: str


def _finite(values: Iterable[float]) -> list[float]:
    return [float(value) for value in values if math.isfinite(float(value))]


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(_finite(values))
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] + weight * (ordered[high] - ordered[low])


def signal_score(values: Sequence[float]) -> float:
    """Robust peak score used only to choose among repeated detector traces."""
    finite = _finite(values)
    if not finite:
        return -math.inf
    return max(0.0, _percentile(finite, 0.995) - _percentile(finite, 0.50))


def choose_signal_column(columns: Sequence[Sequence[float]], configured: int = 0) -> int:
    """Return a zero-based intensity-column index; configured is one-based, 0=auto."""
    if not columns:
        raise ValueError("No intensity columns are available.")
    if configured > 0:
        index = configured - 1
        if index >= len(columns):
            raise ValueError(
                f"Signal column {configured} is not present; the file has {len(columns)} intensity column(s)."
            )
        return index
    return max(range(len(columns)), key=lambda index: signal_score(columns[index]))


def parse_column_selection(value: str, count: int, excluded: int | None = None) -> tuple[int, ...]:
    """Parse one-based comma/space separated intensity columns."""
    text = str(value or "").strip()
    if not text:
        return tuple(index for index in range(count) if index != excluded)
    selected = []
    for token in text.replace(";", ",").replace(" ", ",").split(","):
        if not token:
            continue
        try:
            index = int(token) - 1
        except ValueError as exc:
            raise ValueError(f"Invalid dark column: {token}") from exc
        if index < 0 or index >= count:
            raise ValueError(f"Dark column {index + 1} is not present; available columns: 1-{count}.")
        if index != excluded and index not in selected:
            selected.append(index)
    return tuple(selected)


def interpolate_trace(source_x: Sequence[float], source_y: Sequence[float], target_x: Sequence[float]) -> list[float]:
    points = sorted(
        (float(x), float(y))
        for x, y in zip(source_x, source_y)
        if math.isfinite(float(x)) and math.isfinite(float(y))
    )
    if len(points) < 2:
        raise ValueError("A dark file needs at least two finite points.")
    sx = [point[0] for point in points]
    sy = [point[1] for point in points]
    result = []
    for value in target_x:
        value = float(value)
        if value < sx[0] or value > sx[-1]:
            raise ValueError("The dark trace does not cover the entire spectral window.")
        right = bisect_right(sx, value)
        if right <= 0:
            result.append(sy[0])
        elif right >= len(sx):
            result.append(sy[-1])
        else:
            x0, x1 = sx[right - 1], sx[right]
            y0, y1 = sy[right - 1], sy[right]
            result.append(y1 if x1 == x0 else y0 + (y1 - y0) * (value - x0) / (x1 - x0))
    return result


def subtract_dark(
    wavelengths: Sequence[float],
    columns: Sequence[Sequence[float]],
    *,
    mode: str = "auto_columns",
    signal_column: int = 0,
    dark_columns: str = "",
    constant: float = 0.0,
    dark_trace: tuple[Sequence[float], Sequence[float]] | None = None,
) -> DarkCorrectionResult:
    """Select the signal trace and subtract a per-pixel or scalar dark."""
    if not columns:
        raise ValueError("No intensity columns are available.")
    lengths = {len(column) for column in columns}
    if lengths != {len(wavelengths)}:
        raise ValueError("Wavelength and intensity columns have incompatible lengths.")
    signal_index = choose_signal_column(columns, int(signal_column or 0))
    signal = [float(value) for value in columns[signal_index]]
    mode = str(mode or "none").strip().lower()
    selected: tuple[int, ...] = ()
    if mode in ("auto", "auto_columns", "columns"):
        selected = parse_column_selection(dark_columns, len(columns), signal_index)
        if not selected:
            dark = [0.0] * len(signal)
            source = "no additional columns"
        else:
            dark = [median(float(columns[index][row]) for index in selected) for row in range(len(signal))]
            source = "median of intensity columns " + ", ".join(str(index + 1) for index in selected)
    elif mode == "constant":
        dark = [float(constant)] * len(signal)
        source = f"constant {float(constant):.8g}"
    elif mode == "file":
        if dark_trace is None:
            raise ValueError("Dark mode is 'file', but no dark file is configured.")
        dark = interpolate_trace(dark_trace[0], dark_trace[1], wavelengths)
        source = "external dark trace"
    elif mode in ("none", "off"):
        dark = [0.0] * len(signal)
        source = "disabled"
    else:
        raise ValueError(f"Unknown dark correction mode: {mode}")
    corrected = [value - background for value, background in zip(signal, dark)]
    return DarkCorrectionResult(corrected, dark, signal_index, selected, source)
