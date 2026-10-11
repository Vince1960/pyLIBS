"""SQLite access wrapper for the pyLIBS spectral database."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Optional

from pylibs.core.models import AtomicLine
from pylibs.utils.formatting import safe_float, safe_int
from pylibs.utils.paths import app_base_dir


class LibsDatabase:
    """Accesso al nuovo database SQLite LIBS.db.

    Schema osservato:
    - Datalibs(wavelen, specie, inte, ion): tabella compatta per ricerca rapida.
    - Daticerti(wavelen, specie, inte, ion): righe certificate.
    - Elementi(specie, n_atomico, m_atomica, en_ion, n_righe).
    - partfunctPay(element, temperature, partfunct, ion).
    - una tabella per elemento, ad esempio Fe, Cu, H, con:
      specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc.

    Alcune tabelle contengono una prima riga testuale con i nomi dei campi:
    i metodi sotto la scartano automaticamente.
    """

    def __init__(self, filename: str = "LIBS.db"):
        self.filename = filename
        self.conn: Optional[sqlite3.Connection] = None
        self._tables_cache: Optional[list[str]] = None
        self._aki_scale_cache: Optional[float] = None
        self._level_cache: dict[tuple[str, int], tuple[tuple[float, float], ...]] = {}

    def connect(self):
        if not self.filename:
            raise ValueError("Percorso LIBS.db non impostato.")
        path = Path(self.filename)
        if not path.exists():
            # fallback: directory corrente dello script
            alt = app_base_dir() / path.name
            if alt.exists():
                path = alt
        if not path.exists():
            raise FileNotFoundError(f"Database LIBS.db non trovato: {self.filename}")
        if self.conn is not None:
            self.close()
        connection = sqlite3.connect(str(path))
        connection.row_factory = sqlite3.Row
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
        }
        required = {"Datalibs", "Elementi", "partfunctPay"}
        missing = sorted(required - tables)
        if missing:
            connection.close()
            raise ValueError(
                f"Database LIBS non compatibile ({path.name}); tabelle mancanti: "
                + ", ".join(missing)
            )
        self.conn = connection
        self._tables_cache = sorted(tables)
        self.filename = str(path.resolve())
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        self._tables_cache = None
        self._aki_scale_cache = None
        self._level_cache = {}

    def switch(self, filename: str):
        """Validate and activate another pyLIBS-compatible SQLite library."""
        previous = self.filename
        self.close()
        self.filename = str(filename)
        try:
            return self.connect()
        except Exception:
            self.filename = previous
            raise

    def _ensure(self):
        if self.conn is None:
            self.connect()
        return self.conn

    def tables(self) -> list[str]:
        if self._tables_cache is None:
            conn = self._ensure()
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
            ).fetchall()
            self._tables_cache = [r[0] for r in rows]
        return list(self._tables_cache)

    def database_info(self) -> dict[str, str]:
        conn = self._ensure()
        if "database_info" in self.tables():
            rows = conn.execute('SELECT key, value FROM "database_info"').fetchall()
            return {str(row["key"]): str(row["value"]) for row in rows}
        return {
            "library": "LIBS++ historical",
            "source": "LIBS.db",
            "version": "legacy",
        }

    def display_name(self) -> str:
        info = self.database_info()
        return info.get("library") or info.get("source") or Path(self.filename).name

    @staticmethod
    def _normalize_wavelength_unit(unit: str) -> str:
        text = str(unit or "").strip().lower()
        if text in ("nm", "nanometer", "nanometers", "nanometre", "nanometres"):
            return "nm"
        if text in ("a", "aa", "angstrom", "angstroms"):
            return "angstrom"
        return "database"

    def database_wavelength_unit(self) -> str:
        try:
            unit = self._normalize_wavelength_unit(
                self.database_info().get("wavelength_unit", "")
            )
        except Exception:
            unit = "database"
        # Historical LIBS++ databases use Angstrom even though they do not
        # carry an explicit database_info table.
        return "angstrom" if unit == "database" else unit

    def wavelength_scale_to_database(self, unit: str = "database") -> float:
        source = self._normalize_wavelength_unit(unit)
        target = self.database_wavelength_unit()
        if source == "database" or source == target:
            return 1.0
        if source == "nm" and target == "angstrom":
            return 10.0
        if source == "angstrom" and target == "nm":
            return 0.1
        return 1.0

    def aki_scale_to_si(self) -> float:
        """Multiplier that converts stored Aki values to physical s^-1.

        LIBS++ stores Aki in units of 10^8 s^-1.  The rebuilt NIST library
        declares that convention explicitly; historical libraries use the
        same layout but have no metadata table.
        """
        if self._aki_scale_cache is not None:
            return self._aki_scale_cache
        info = self.database_info()
        unit = str(info.get("aki_unit", "") or "").strip().lower().replace(" ", "")
        if not unit:
            scale = 1.0e8
        elif "1e8" in unit or "10^8" in unit or "10**8" in unit:
            scale = 1.0e8
        else:
            scale = 1.0
        self._aki_scale_cache = scale
        return scale

    def _aki_to_si(self, value, default: float = 0.0) -> float:
        raw = safe_float(value, default)
        return raw * self.aki_scale_to_si() if raw else raw

    @staticmethod
    def _copy_atomic_line_with_wavelength(
        atomic: AtomicLine, wavelength: float
    ) -> AtomicLine:
        return AtomicLine(
            wavelen=float(wavelength),
            specie=atomic.specie,
            ion=atomic.ion,
            inte=atomic.inte,
            ei=atomic.ei,
            ek=atomic.ek,
            gi=atomic.gi,
            gk=atomic.gk,
            aki=atomic.aki,
            acc=atomic.acc,
        )

    def element_tables(self) -> list[str]:
        return [t for t in self.tables() if len(t) <= 2 and t[:1].isalpha() and t[0].isupper()]

    def search_lines(
        self,
        wavelength: float,
        search_range: float = 1.0,
        table: str = "Datalibs",
        element: str = "",
        ion: Optional[int] = None,
        limit: int = 500,
        prefer_full_element_table: bool = False,
        wavelength_unit: str = "database",
    ) -> list[AtomicLine]:
        conn = self._ensure()
        wavelength_scale = self.wavelength_scale_to_database(wavelength_unit)
        database_wavelength = wavelength * wavelength_scale
        database_range = abs(search_range * wavelength_scale)
        lo = database_wavelength - database_range
        hi = database_wavelength + database_range
        rows = []

        table_name = table
        if prefer_full_element_table and element:
            cand = element.strip().capitalize()
            if cand in self.tables():
                table_name = cand

        if table_name not in self.tables():
            table_name = "Datalibs"

        if table_name in ("Datalibs", "Daticerti"):
            sql = f'SELECT wavelen, specie, ion, inte, 0 AS Ei, 0 AS Ek, 0 AS gi, 0 AS gk, 0 AS Aki, 0 AS acc FROM "{table_name}" WHERE wavelen BETWEEN ? AND ?'
            params: list[object] = [lo, hi]
            if element:
                sql += " AND TRIM(specie)=?"
                params.append(element.strip().capitalize())
            if ion is not None:
                sql += " AND CAST(ion AS INTEGER)=?"
                params.append(int(ion))
            sql += " ORDER BY ABS(wavelen-?) LIMIT ?"
            params.extend([database_wavelength, limit])
            rows = conn.execute(sql, params).fetchall()
        else:
            # tabella elemento-specifica
            sql = f'SELECT wavelen, specie, ion, 0 AS inte, Ei, Ek, gi, gk, Aki, acc FROM "{table_name}" WHERE typeof(wavelen) IN ("real","integer") AND wavelen BETWEEN ? AND ?'
            params = [lo, hi]
            if ion is not None:
                sql += " AND CAST(ion AS INTEGER)=?"
                params.append(int(ion))
            sql += " ORDER BY ABS(wavelen-?) LIMIT ?"
            params.extend([database_wavelength, limit])
            rows = conn.execute(sql, params).fetchall()

        out: list[AtomicLine] = []
        for r in rows:
            try:
                wav = float(r["wavelen"])
            except Exception:
                continue
            sp = str(r["specie"]).strip() if r["specie"] is not None else (element or "")
            try:
                iz = int(float(r["ion"]))
            except Exception:
                iz = 0
            try:
                inte = float(r["inte"])
            except Exception:
                inte = 0.0
            out.append(AtomicLine(
                wavelen=wav / wavelength_scale, specie=sp, ion=iz, inte=inte,
                ei=safe_float(r["Ei"]), ek=safe_float(r["Ek"]),
                gi=safe_int(r["gi"]), gk=safe_int(r["gk"]),
                aki=self._aki_to_si(r["Aki"]), acc=safe_int(r["acc"])
            ))
        return out

    def enrich_line_from_element_table(
        self,
        atomic: AtomicLine,
        tolerance: float = 0.02,
        wavelength_unit: str = "database",
    ) -> AtomicLine:
        """Return the same line enriched with Ei/Ek/gi/gk/Aki/acc from the
        element-specific table in LIBS.db, when available.  Datalibs/Daticerti
        are fast lookup tables and often do not contain these spectroscopic
        parameters; LIBS++ copies them from the element table when the user
        assigns an identification.
        """
        if not atomic or not atomic.specie:
            return atomic
        conn = self._ensure()
        table = atomic.specie.strip().capitalize()
        if table not in self.tables():
            return atomic
        wavelength_scale = self.wavelength_scale_to_database(wavelength_unit)
        database_wavelength = atomic.wavelen * wavelength_scale
        database_tolerance = abs(tolerance * wavelength_scale)
        requested_ion = safe_int(atomic.ion, 0)
        rows = []
        if requested_ion in (1, 2):
            rows = conn.execute(
                f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc FROM "{table}" '
                'WHERE typeof(wavelen) IN ("real","integer") AND CAST(ion AS INTEGER)=? '
                'AND wavelen BETWEEN ? AND ? ORDER BY ABS(wavelen-?) LIMIT 1',
                (
                    requested_ion,
                    database_wavelength - database_tolerance,
                    database_wavelength + database_tolerance,
                    database_wavelength,
                )
            ).fetchall()
        else:
            rows = conn.execute(
                f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc FROM "{table}" '
                'WHERE typeof(wavelen) IN ("real","integer") AND wavelen BETWEEN ? AND ? '
                'ORDER BY ABS(wavelen-?) LIMIT 1',
                (
                    database_wavelength - database_tolerance,
                    database_wavelength + database_tolerance,
                    database_wavelength,
                )
            ).fetchall()
        if not rows:
            return atomic
        r = rows[0]
        return AtomicLine(
            wavelen=safe_float(r["wavelen"], database_wavelength) / wavelength_scale,
            specie=(str(r["specie"]).strip() or atomic.specie),
            ion=safe_int(r["ion"], atomic.ion),
            inte=atomic.inte,
            ei=safe_float(r["Ei"], atomic.ei),
            ek=safe_float(r["Ek"], atomic.ek),
            gi=safe_int(r["gi"], atomic.gi),
            gk=safe_int(r["gk"], atomic.gk),
            aki=self._aki_to_si(r["Aki"], atomic.aki / self.aki_scale_to_si()),
            acc=safe_int(r["acc"], atomic.acc),
        )

    def trace_lines(
        self,
        element: str,
        xmin: float,
        xmax: float,
        ions: Optional[list[int]] = None,
        max_lines: int = 20,
        table: str = "Datalibs",
        wavelength_unit: str = "database",
    ) -> list[AtomicLine]:
        """Return the strongest database lines for an element/species in the
        currently displayed spectral interval, as required by Analyse > Trace
        Lines.  Ion values follow LIBS.db convention: 1 = neutral (I),
        2 = singly ionized (II).
        """
        conn = self._ensure()
        element = (element or "").strip().capitalize()
        if not element:
            return []
        if xmin > xmax:
            xmin, xmax = xmax, xmin
        wavelength_scale = self.wavelength_scale_to_database(wavelength_unit)
        xmin *= wavelength_scale
        xmax *= wavelength_scale
        ions = ions or [1]
        max_lines = max(1, int(max_lines or 20))
        if table not in self.tables():
            table = "Datalibs"
        placeholders = ",".join("?" for _ in ions)
        rows = []
        if table in ("Datalibs", "Daticerti"):
            sql = (f'SELECT wavelen, specie, ion, inte, 0 AS Ei, 0 AS Ek, 0 AS gi, 0 AS gk, 0 AS Aki, 0 AS acc '
                   f'FROM "{table}" WHERE typeof(wavelen) IN ("real","integer") '
                   f'AND wavelen BETWEEN ? AND ? AND TRIM(specie)=? '
                   f'AND CAST(ion AS INTEGER) IN ({placeholders}) '
                   f'ORDER BY CAST(inte AS REAL) DESC LIMIT ?')
            params = [xmin, xmax, element] + [int(i) for i in ions] + [max_lines]
            rows = conn.execute(sql, params).fetchall()
        else:
            elem_table = element if element in self.tables() else table
            sql = (f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc, 0 AS inte '
                   f'FROM "{elem_table}" WHERE typeof(wavelen) IN ("real","integer") '
                   f'AND wavelen BETWEEN ? AND ? AND CAST(ion AS INTEGER) IN ({placeholders}) '
                   f'ORDER BY CAST(Aki AS REAL) DESC LIMIT ?')
            params = [xmin, xmax] + [int(i) for i in ions] + [max_lines]
            rows = conn.execute(sql, params).fetchall()

        def row_to_atomic(r) -> Optional[AtomicLine]:
            try:
                wav = float(r["wavelen"])
            except Exception:
                return None
            sp = str(r["specie"]).strip() if r["specie"] is not None else element
            try:
                iz = int(float(r["ion"]))
            except Exception:
                iz = 1
            return AtomicLine(
                wavelen=wav / wavelength_scale,
                specie=sp or element,
                ion=iz,
                inte=safe_float(r["inte"]),
                ei=safe_float(r["Ei"]), ek=safe_float(r["Ek"]),
                gi=safe_int(r["gi"]), gk=safe_int(r["gk"]),
                aki=self._aki_to_si(r["Aki"]), acc=safe_int(r["acc"])
            )

        def is_duplicate(candidate: AtomicLine, existing: list[AtomicLine]) -> bool:
            tolerance = 0.05 / wavelength_scale
            return any(
                abs(candidate.wavelen - line.wavelen) <= tolerance
                and candidate.specie == line.specie
                and candidate.ion == line.ion
                for line in existing
            )

        out: list[AtomicLine] = []
        for r in rows:
            line = row_to_atomic(r)
            if line and not is_duplicate(line, out):
                out.append(line)

        if table in ("Datalibs", "Daticerti") and len(out) < max_lines and element in self.tables():
            fallback_sql = (f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc, 0 AS inte '
                            f'FROM "{element}" WHERE typeof(wavelen) IN ("real","integer") '
                            f'AND wavelen BETWEEN ? AND ? AND CAST(ion AS INTEGER) IN ({placeholders}) '
                            f'ORDER BY CAST(Aki AS REAL) DESC LIMIT ?')
            fallback_params = [xmin, xmax] + [int(i) for i in ions] + [max_lines]
            for r in conn.execute(fallback_sql, fallback_params).fetchall():
                line = row_to_atomic(r)
                if line and not is_duplicate(line, out):
                    out.append(line)
                if len(out) >= max_lines:
                    break
        return out

    def match_selected_lines(
        self,
        element: str,
        wavelengths: list[float],
        tolerance: float,
        ions: Optional[list[int]] = None,
        wavelength_unit: str = "database",
    ) -> list[AtomicLine]:
        """Match one comprehensive element-table transition to each selected
        observed wavelength and ionization stage.

        Unlike trace_lines(), this does not return unrelated strong database
        lines from the rest of the visible interval.
        """
        element = (element or "").strip().capitalize()
        if not element or element not in self.tables():
            return []
        ions = ions or [1]
        tolerance = max(0.0, float(tolerance))
        wavelength_scale = self.wavelength_scale_to_database(wavelength_unit)
        duplicate_tolerance = 0.05 / wavelength_scale
        matches: list[AtomicLine] = []
        for wavelength in wavelengths:
            wavelength_matches: list[AtomicLine] = []
            for ion in ions:
                candidates = self.search_lines(
                    float(wavelength),
                    tolerance,
                    table=element,
                    element=element,
                    ion=int(ion),
                    limit=1,
                    prefer_full_element_table=True,
                    wavelength_unit=wavelength_unit,
                )
                if not candidates:
                    continue
                wavelength_matches.append(candidates[0])
            if not wavelength_matches:
                continue
            candidate = min(
                wavelength_matches,
                key=lambda line: (
                    abs(line.wavelen - float(wavelength)),
                    -abs(line.aki),
                    line.ion,
                ),
            )
            if any(
                abs(candidate.wavelen - existing.wavelen)
                <= duplicate_tolerance
                and candidate.specie == existing.specie
                and candidate.ion == existing.ion
                for existing in matches
            ):
                continue
            matches.append(candidate)
        return sorted(matches, key=lambda line: (line.wavelen, line.ion))

    def load_all_atomic_lines(self, table: str = "Datalibs", limit: int = 200000) -> list[AtomicLine]:
        conn = self._ensure()
        if table not in self.tables():
            table = "Datalibs"
        rows = conn.execute(
            f'SELECT wavelen, specie, ion, inte FROM "{table}" '
            'WHERE typeof(wavelen) IN ("real","integer") LIMIT ?', (limit,)
        ).fetchall()
        out = []
        for r in rows:
            out.append(AtomicLine(
                wavelen=safe_float(r["wavelen"]),
                specie=str(r["specie"]).strip(),
                ion=safe_int(r["ion"]),
                inte=safe_float(r["inte"])
            ))
        return [l for l in out if l.wavelen]

    def element_metadata(self, element: str) -> dict:
        conn = self._ensure()
        row = conn.execute(
            'SELECT * FROM Elementi WHERE TRIM(specie)=?',
            (element.strip().capitalize(),)
        ).fetchone()
        return dict(row) if row else {}

    def partition_function(self, element: str, ion: int, temperature: float) -> float:
        conn = self._ensure()
        temperature = float(temperature)
        if not math.isfinite(temperature) or temperature <= 0.0:
            raise ValueError("Partition-function temperature must be positive and finite.")
        symbol = element.strip().capitalize()
        key = (symbol, int(ion))
        if "livelli" in self.tables():
            if key not in self._level_cache:
                level_rows = conn.execute(
                    'SELECT Ei, gi FROM livelli '
                    'WHERE TRIM(element)=? AND CAST(ion AS INTEGER)=? '
                    'ORDER BY Ei',
                    key,
                ).fetchall()
                self._level_cache[key] = tuple(
                    (float(row["Ei"]), float(row["gi"]))
                    for row in level_rows
                    if safe_float(row["Ei"], -1.0) >= 0.0
                    and safe_float(row["gi"], 0.0) > 0.0
                )
            levels = self._level_cache[key]
            if levels:
                # hc/k expressed in cm K. The bundled NIST level energies are
                # in cm^-1, so this evaluates U(T) at the actual plasma T.
                return math.fsum(
                    degeneracy
                    * math.exp(-1.4387768775039338 * energy_cm1 / temperature)
                    for energy_cm1, degeneracy in levels
                )
        rows = conn.execute(
            'SELECT temperature, partfunct FROM partfunctPay WHERE TRIM(element)=? AND ion=? ORDER BY temperature',
            key,
        ).fetchall()
        if not rows:
            return 1.0
        pts = [(float(r["temperature"]), float(r["partfunct"])) for r in rows]
        if temperature <= pts[0][0]:
            return pts[0][1]
        if temperature >= pts[-1][0]:
            return pts[-1][1]
        for (t0, z0), (t1, z1) in zip(pts, pts[1:]):
            if t0 <= temperature <= t1:
                return z0 + (z1 - z0) * (temperature - t0) / (t1 - t0)
        return 1.0
