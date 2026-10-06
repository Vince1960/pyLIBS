"""Instrument-response curves and per-window matching for pyLIBS."""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable, Optional, Sequence

from pylibs.io.spectrum_io import read_ascii_spectrum


def parse_response_paths(value) -> list[str]:
    """Decode the persisted response-file list, including the legacy scalar."""
    if isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        text = str(value or "").strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, list):
            raw = parsed
        elif "|" in text:
            raw = text.split("|")
        else:
            raw = [text]
    paths = []
    seen = set()
    for item in raw:
        path = str(item or "").strip()
        key = path.casefold()
        if path and key not in seen:
            paths.append(path)
            seen.add(key)
    return paths


def serialize_response_paths(paths: Iterable[str]) -> str:
    return json.dumps(parse_response_paths(list(paths)), ensure_ascii=True)


def parse_lsf_widths(value) -> dict[str, float]:
    """Decode persisted per-response Gaussian FWHM values."""
    if isinstance(value, dict):
        raw = value
    else:
        try:
            raw = json.loads(str(value or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = {}
    result = {}
    if isinstance(raw, dict):
        for key, width in raw.items():
            try:
                width = float(width)
            except (TypeError, ValueError):
                continue
            if str(key).strip() and math.isfinite(width) and width > 0.0:
                result[str(key).strip()] = width
    return result


def serialize_lsf_widths(values) -> str:
    return json.dumps(parse_lsf_widths(values), ensure_ascii=True, sort_keys=True)


def extract_window_tag(path_or_name: str) -> str:
    name = Path(str(path_or_name or "")).name
    match = re.search(r"(\d{3,4})\s*nm", name, re.IGNORECASE)
    if match:
        return match.group(1)
    numbers = re.findall(r"(\d{3,4})", name)
    return numbers[-1] if numbers else Path(name).stem.casefold()


def _read_response_workbook(
    filename: str,
    convert_nm_to_a: bool = False,
) -> list[tuple[list[float], list[float], str]]:
    """Read the calibrated multi-window response workbook used by pyLIBS.

    Deuterium sheets (for example ``fs305d``) use columns A:B. Tungsten
    sheets use the D/W cross-scaled response in column C when available.
    When both sources exist for one window, the deuterium sheet is preferred;
    the tungsten copy of the overlap window is used only for cross-scaling.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise ValueError(
            "Reading an .xlsx instrument response requires the openpyxl package."
        ) from exc

    workbook = openpyxl.load_workbook(filename, read_only=True, data_only=True)
    candidates: dict[str, list[tuple[int, list[float], list[float], str]]] = {}
    try:
        for sheet in workbook.worksheets:
            match = re.fullmatch(r"fs\s*[_-]?(\d{3,4})\s*([dw])?", sheet.title.strip(), re.IGNORECASE)
            if not match:
                continue
            window = match.group(1)
            source = (match.group(2) or "").casefold()
            rows = list(sheet.iter_rows(values_only=True))
            response_column = 2 if source == "w" and any(
                len(row) > 2 and isinstance(row[2], (int, float))
                for row in rows
            ) else 1
            x_values, y_values = [], []
            for row in rows:
                if len(row) <= response_column:
                    continue
                wavelength, response = row[0], row[response_column]
                if not isinstance(wavelength, (int, float)) or not isinstance(response, (int, float)):
                    continue
                wavelength = float(wavelength)
                response = float(response)
                if not math.isfinite(wavelength) or not math.isfinite(response):
                    continue
                if convert_nm_to_a and wavelength < 1500.0:
                    wavelength *= 10.0
                x_values.append(wavelength)
                y_values.append(response)
            if len(x_values) < 2:
                continue
            priority = 2 if source == "d" else 1
            candidates.setdefault(window, []).append(
                (priority, x_values, y_values, sheet.title)
            )
    finally:
        workbook.close()

    curves = []
    for window in sorted(candidates, key=lambda value: int(value)):
        _priority, x_values, y_values, sheet_name = max(
            candidates[window], key=lambda item: item[0]
        )
        curves.append((x_values, y_values, sheet_name))
    if not curves:
        raise ValueError(
            "No instrument-response sheets were found. Expected names such as "
            "fs305d, fs365w or fs475w."
        )
    return curves


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return math.nan
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(100.0, percentile)) * (len(ordered) - 1) / 100.0
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] + fraction * (ordered[high] - ordered[low])


def _largest_true_block(mask: Sequence[bool]) -> Optional[tuple[int, int]]:
    best = None
    start = None
    for index, value in enumerate(list(mask) + [False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            end = index - 1
            if best is None or end - start > best[1] - best[0]:
                best = (start, end)
            start = None
    return best


@dataclass
class ResponseCurve:
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    filename: str = ""
    lsf_fwhm: Optional[float] = None

    def __post_init__(self):
        cleaned = []
        for xx, yy in zip(self.x, self.y):
            try:
                xx = float(xx)
                yy = float(yy)
            except (TypeError, ValueError):
                continue
            if math.isfinite(xx) and math.isfinite(yy):
                cleaned.append((xx, yy))
        cleaned.sort(key=lambda point: point[0])
        unique = []
        for xx, yy in cleaned:
            if unique and xx == unique[-1][0]:
                unique[-1] = (xx, yy)
            else:
                unique.append((xx, yy))
        self.x = [point[0] for point in unique]
        self.y = [point[1] for point in unique]
        if len(self.x) < 2:
            raise ValueError("An instrument response needs at least two finite points.")
        if sum(1 for value in self.y if value > 0.0) < 2:
            raise ValueError("An instrument response needs positive finite values.")

    @classmethod
    def from_ascii(cls, filename: str, convert_nm_to_a: bool = False, lsf_fwhm: Optional[float] = None):
        xs, ys = read_ascii_spectrum(filename, convert_nm_to_a)
        return cls(list(xs), list(ys), str(filename), lsf_fwhm)

    @property
    def name(self) -> str:
        return Path(self.filename).name or "Response"

    @property
    def minimum(self) -> float:
        return self.x[0]

    @property
    def maximum(self) -> float:
        return self.x[-1]

    @property
    def center(self) -> float:
        return 0.5 * (self.minimum + self.maximum)

    def _endpoint_tolerance(self, wavelength: float) -> float:
        """Allow only the rounding introduced by ASCII response files.

        OPC files historically used eight significant digits.  A NIST value
        reloaded from the database can therefore lie a few 1e-6 nm beyond an
        endpoint that represents the same analytical line.  This tolerance is
        far below the spectral sampling/resolution and must not become general
        response-curve extrapolation.
        """
        scale = max(
            abs(float(wavelength)),
            abs(self.minimum),
            abs(self.maximum),
            1.0,
        )
        return max(1.0e-9, 5.0e-8 * scale)

    def covers(self, wavelength: float) -> bool:
        wavelength = float(wavelength)
        tolerance = self._endpoint_tolerance(wavelength)
        return self.minimum - tolerance <= wavelength <= self.maximum + tolerance

    def value_at(self, wavelength: float) -> Optional[float]:
        wavelength = float(wavelength)
        if not self.covers(wavelength):
            return None
        if wavelength <= self.minimum:
            return self.y[0]
        if wavelength >= self.maximum:
            return self.y[-1]
        index = bisect_right(self.x, wavelength)
        if index <= 0:
            return self.y[0]
        if index >= len(self.x):
            return self.y[-1]
        x0, x1 = self.x[index - 1], self.x[index]
        y0, y1 = self.y[index - 1], self.y[index]
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (wavelength - x0) / (x1 - x0)

    def values_at(self, wavelengths: Sequence[float]) -> list[Optional[float]]:
        return [self.value_at(wavelength) for wavelength in wavelengths]

    def overlap_fraction(self, wavelengths: Sequence[float]) -> float:
        values = [float(value) for value in wavelengths if math.isfinite(float(value))]
        if not values:
            return 0.0
        low, high = min(values), max(values)
        span = max(high - low, math.ulp(1.0))
        overlap = max(0.0, min(high, self.maximum) - max(low, self.minimum))
        if high == low:
            return 1.0 if self.covers(low) else 0.0
        return overlap / span

    def correct(
        self,
        wavelengths: Sequence[float],
        intensities: Sequence[float],
        minimum_coverage: float = 0.15,
        edge_fraction: float = 0.05,
    ) -> tuple[list[float], list[float], str]:
        """Divide by the response on its reliable contiguous wavelength block."""
        if len(wavelengths) != len(intensities):
            raise ValueError("Spectrum and response axes have incompatible lengths.")
        if len(wavelengths) < 3:
            raise ValueError("The spectrum has too few points for response correction.")
        covered = [
            index for index, wavelength in enumerate(wavelengths)
            if self.covers(float(wavelength))
        ]
        minimum_points = max(3, min(20, int(math.ceil(minimum_coverage * len(wavelengths)))))
        if len(covered) < minimum_points:
            low = min(float(value) for value in wavelengths)
            high = max(float(value) for value in wavelengths)
            raise ValueError(
                f"Response {self.name} does not sufficiently cover the spectral window "
                f"({low:.3f}-{high:.3f})."
            )
        covered_x = [float(wavelengths[index]) for index in covered]
        response = [self.value_at(value) for value in covered_x]
        positive = [
            float(value) for value in response
            if value is not None and math.isfinite(float(value)) and float(value) > 0.0
        ]
        if len(positive) < minimum_points:
            raise ValueError(f"Response {self.name} has too few positive values in this window.")
        reference = _percentile(positive, 95.0)
        threshold = max(1e-12, edge_fraction * reference)
        valid = [
            value is not None and math.isfinite(float(value)) and float(value) > threshold
            for value in response
        ]
        block = _largest_true_block(valid)
        if block is None or block[1] - block[0] + 1 < minimum_points:
            raise ValueError(f"Response {self.name} has no reliable contiguous block in this window.")
        start, end = block
        selected = covered[start:end + 1]
        selected_response = response[start:end + 1]
        corrected_x = [float(wavelengths[index]) for index in selected]
        corrected_y = [
            float(intensities[index]) / float(factor)
            for index, factor in zip(selected, selected_response)
        ]
        info = (
            f"{self.name}: {corrected_x[0]:.3f}-{corrected_x[-1]:.3f}; "
            f"edge threshold {threshold:.3g}"
        )
        return corrected_x, corrected_y, info


class InstrumentResponseLibrary:
    def __init__(self, curves: Optional[Iterable[ResponseCurve]] = None):
        self.curves = list(curves or [])

    @classmethod
    def from_files(
        cls,
        paths: Iterable[str],
        convert_nm_to_a: bool = False,
        lsf_widths=None,
    ):
        widths = parse_lsf_widths(lsf_widths)
        curves = []
        for path in parse_response_paths(paths):
            width = widths.get(path)
            if width is None:
                width = widths.get(Path(path).name)
            if Path(path).suffix.lower() in {".xlsx", ".xlsm"}:
                for xs, ys, sheet_name in _read_response_workbook(path, convert_nm_to_a):
                    sheet_width = widths.get(sheet_name, width)
                    curves.append(
                        ResponseCurve(
                            xs,
                            ys,
                            f"{path} [{sheet_name}]",
                            sheet_width,
                        )
                    )
            else:
                curves.append(ResponseCurve.from_ascii(path, convert_nm_to_a, width))
        return cls(curves)

    @property
    def paths(self) -> list[str]:
        return [curve.filename for curve in self.curves]

    def best_for(self, spectrum_name: str, wavelengths: Sequence[float]) -> Optional[ResponseCurve]:
        values = [float(value) for value in wavelengths]
        if not values:
            return None
        spectrum_center = 0.5 * (min(values) + max(values))
        spectrum_tag = extract_window_tag(spectrum_name)
        candidates = []
        for index, curve in enumerate(self.curves):
            coverage = curve.overlap_fraction(values)
            if coverage <= 0.0:
                continue
            tag_match = extract_window_tag(curve.name) == spectrum_tag
            candidates.append((tag_match, coverage, -abs(curve.center - spectrum_center), -index, curve))
        return max(candidates, key=lambda item: item[:-1])[-1] if candidates else None

    def assign_windows(
        self,
        windows: Sequence[tuple[str, Sequence[float]]],
    ) -> dict[int, ResponseCurve]:
        """Match distinct source windows one-to-one when enough curves exist."""
        candidates = []
        for window_index, (name, wavelengths) in enumerate(windows):
            values = [float(value) for value in wavelengths]
            if not values:
                continue
            center = 0.5 * (min(values) + max(values))
            tag = extract_window_tag(name)
            for curve_index, curve in enumerate(self.curves):
                coverage = curve.overlap_fraction(values)
                if coverage <= 0.0:
                    continue
                candidates.append((
                    extract_window_tag(curve.name) == tag,
                    coverage,
                    -abs(curve.center - center),
                    -curve_index,
                    window_index,
                    curve_index,
                ))
        assignments = {}
        used_curves = set()
        enforce_unique = len(self.curves) >= len(windows)
        for candidate in sorted(candidates, reverse=True):
            window_index, curve_index = candidate[-2], candidate[-1]
            if window_index in assignments:
                continue
            if enforce_unique and curve_index in used_curves:
                continue
            assignments[window_index] = self.curves[curve_index]
            used_curves.add(curve_index)
        if not enforce_unique:
            for window_index, (name, wavelengths) in enumerate(windows):
                if window_index not in assignments:
                    curve = self.best_for(name, wavelengths)
                    if curve is not None:
                        assignments[window_index] = curve
        return assignments

    def for_wavelength(self, wavelength: float) -> Optional[ResponseCurve]:
        candidates = [curve for curve in self.curves if curve.covers(float(wavelength))]
        if not candidates:
            return None
        return min(candidates, key=lambda curve: abs(curve.center - float(wavelength)))

    def value_at(self, wavelength: float) -> Optional[float]:
        curve = self.for_wavelength(wavelength)
        return curve.value_at(wavelength) if curve is not None else None

    def lsf_fwhm_at(self, wavelength: float, default: float) -> float:
        curve = self.for_wavelength(wavelength)
        if curve is not None and curve.lsf_fwhm is not None and curve.lsf_fwhm > 0.0:
            return float(curve.lsf_fwhm)
        return float(default)
