"""Template file loading and saving helpers for pyLIBS."""

from __future__ import annotations

import csv

from pylibs.core.models import TemplateLine
from pylibs.utils.formatting import safe_float, safe_int


TEMPLATE_COLUMNS = (
    "wavelen", "specie", "ion", "asswavelen", "inte", "ei", "ek", "aki",
    "gk", "gi", "acc", "wg", "wl", "fitwavelen",
)


def load_template_lines(filename: str, columns=TEMPLATE_COLUMNS) -> list[TemplateLine]:
    cols = list(columns)
    rows = []
    with open(filename, "r", encoding="utf-8", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ") if sample.strip() else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if reader.fieldnames and any(name in reader.fieldnames for name in cols):
            for r in reader:
                kw = {}
                for c in cols:
                    v = (r.get(c) or "").strip()
                    if c == "specie":
                        kw[c] = v
                    elif c in ("ion", "gk", "gi", "acc"):
                        kw[c] = safe_int(v, 0)
                    else:
                        kw[c] = safe_float(v, 0.0)
                if kw.get("wavelen", 0.0):
                    rows.append(TemplateLine(**kw))
        else:
            f.seek(0)
            for line in f:
                parts = line.replace(",", ".").split()
                if not parts:
                    continue
                try:
                    rows.append(TemplateLine(wavelen=float(parts[0])))
                except Exception:
                    pass
    return rows


def save_template_lines(filename: str, lines, columns=TEMPLATE_COLUMNS) -> None:
    cols = list(columns)
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for line in lines:
            writer.writerow([getattr(line, c) for c in cols])
