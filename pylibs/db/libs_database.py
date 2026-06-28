"""SQLite access wrapper for the pyLIBS spectral database."""

from __future__ import annotations

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
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.filename = str(path)
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _ensure(self):
        if self.conn is None:
            self.connect()
        return self.conn

    def tables(self) -> list[str]:
        conn = self._ensure()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

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
    ) -> list[AtomicLine]:
        conn = self._ensure()
        lo, hi = wavelength - search_range, wavelength + search_range
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
            params.extend([wavelength, limit])
            rows = conn.execute(sql, params).fetchall()
        else:
            # tabella elemento-specifica
            sql = f'SELECT wavelen, specie, ion, 0 AS inte, Ei, Ek, gi, gk, Aki, acc FROM "{table_name}" WHERE typeof(wavelen) IN ("real","integer") AND wavelen BETWEEN ? AND ?'
            params = [lo, hi]
            if ion is not None:
                sql += " AND CAST(ion AS INTEGER)=?"
                params.append(int(ion))
            sql += " ORDER BY ABS(wavelen-?) LIMIT ?"
            params.extend([wavelength, limit])
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
                wavelen=wav, specie=sp, ion=iz, inte=inte,
                ei=safe_float(r["Ei"]), ek=safe_float(r["Ek"]),
                gi=safe_int(r["gi"]), gk=safe_int(r["gk"]),
                aki=safe_float(r["Aki"]), acc=safe_int(r["acc"])
            ))
        return out

    def enrich_line_from_element_table(self, atomic: AtomicLine, tolerance: float = 0.02) -> AtomicLine:
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
        rows = conn.execute(
            f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc FROM "{table}" '
            'WHERE typeof(wavelen) IN ("real","integer") AND CAST(ion AS INTEGER)=? '
            'AND wavelen BETWEEN ? AND ? ORDER BY ABS(wavelen-?) LIMIT 1',
            (int(atomic.ion), atomic.wavelen - tolerance, atomic.wavelen + tolerance, atomic.wavelen)
        ).fetchall()
        if not rows:
            rows = conn.execute(
                f'SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki, acc FROM "{table}" '
                'WHERE typeof(wavelen) IN ("real","integer") AND wavelen BETWEEN ? AND ? '
                'ORDER BY ABS(wavelen-?) LIMIT 1',
                (atomic.wavelen - tolerance, atomic.wavelen + tolerance, atomic.wavelen)
            ).fetchall()
        if not rows:
            return atomic
        r = rows[0]
        return AtomicLine(
            wavelen=safe_float(r["wavelen"], atomic.wavelen),
            specie=(str(r["specie"]).strip() or atomic.specie),
            ion=safe_int(r["ion"], atomic.ion),
            inte=atomic.inte,
            ei=safe_float(r["Ei"], atomic.ei),
            ek=safe_float(r["Ek"], atomic.ek),
            gi=safe_int(r["gi"], atomic.gi),
            gk=safe_int(r["gk"], atomic.gk),
            aki=safe_float(r["Aki"], atomic.aki),
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
                wavelen=wav, specie=sp or element, ion=iz, inte=safe_float(r["inte"]),
                ei=safe_float(r["Ei"]), ek=safe_float(r["Ek"]),
                gi=safe_int(r["gi"]), gk=safe_int(r["gk"]),
                aki=safe_float(r["Aki"]), acc=safe_int(r["acc"])
            )

        def is_duplicate(candidate: AtomicLine, existing: list[AtomicLine]) -> bool:
            return any(
                abs(candidate.wavelen - line.wavelen) <= 0.05
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
        rows = conn.execute(
            'SELECT temperature, partfunct FROM partfunctPay WHERE TRIM(element)=? AND ion=? ORDER BY temperature',
            (element.strip().capitalize(), int(ion))
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
