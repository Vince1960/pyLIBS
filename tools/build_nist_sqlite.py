#!/usr/bin/env python3
"""Convert a LIBS++-compatible NIST MDB into pyLIBS SQLite format."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROVIDERS = (
    "Microsoft.ACE.OLEDB.16.0",
    "Microsoft.ACE.OLEDB.12.0",
    "Microsoft.Jet.OLEDB.4.0",
)


def connect_mdb(path: Path):
    try:
        import adodbapi
    except ImportError as exc:
        raise RuntimeError(
            "Reading MDB requires adodbapi/pywin32 on Windows. "
            "The generated SQLite database itself has no such dependency."
        ) from exc
    errors = []
    for provider in PROVIDERS:
        try:
            connection = adodbapi.connect(f"Provider={provider};Data Source={path};")
            return connection, provider
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    raise RuntimeError("No Access provider could open the MDB:\n" + "\n".join(errors))


def fetch_rows(cursor, sql: str) -> list[tuple]:
    cursor.execute(sql)
    return [tuple(row) for row in cursor.fetchall()]


def quoted_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise ValueError(f"Unsafe table name in MDB: {name!r}")
    return f'"{name}"'


def build_database(
    source_mdb: Path,
    output_db: Path,
    metadata_path: Path | None = None,
    progress=None,
) -> dict:
    source_mdb = source_mdb.resolve()
    output_db = output_db.resolve()
    if not source_mdb.exists():
        raise FileNotFoundError(source_mdb)
    metadata = {}
    if metadata_path and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    temporary = output_db.with_suffix(output_db.suffix + ".building")
    if temporary.exists():
        temporary.unlink()
    if progress:
        progress(f"Opening {source_mdb.name}")
    access, provider = connect_mdb(source_mdb)
    source_cursor = access.cursor()
    target = sqlite3.connect(str(temporary))
    try:
        target.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE Elementi (
                specie TEXT, n_atomico INTEGER, m_atomica REAL,
                en_ion REAL, n_righe INTEGER
            );
            CREATE TABLE Datalibs (
                wavelen REAL, specie TEXT, inte REAL, ion REAL
            );
            CREATE TABLE Daticerti (
                wavelen REAL, specie TEXT, inte REAL, ion REAL
            );
            CREATE TABLE partfunctPay (
                element TEXT, temperature INTEGER, partfunct REAL, ion INTEGER
            );
            CREATE TABLE database_info (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        elements = fetch_rows(
            source_cursor,
            "SELECT specie, n_atomico, m_atomica, en_ion, n_righe FROM [Elementi]",
        )
        if progress:
            progress(f"Element metadata: {len(elements)}")
        target.executemany("INSERT INTO Elementi VALUES (?, ?, ?, ?, ?)", elements)

        datalibs = fetch_rows(source_cursor, "SELECT wavelen, specie, inte, ion FROM [Datalibs]")
        if progress:
            progress(f"Search lines: {len(datalibs)}")
        target.executemany("INSERT INTO Datalibs VALUES (?, ?, ?, ?)", datalibs)
        daticerti = fetch_rows(source_cursor, "SELECT wavelen, specie, inte, ion FROM [Daticerti]")
        target.executemany("INSERT INTO Daticerti VALUES (?, ?, ?, ?)", daticerti)
        partitions = fetch_rows(
            source_cursor,
            "SELECT element, temperature, partfunct, ion FROM [partfunctPay]",
        )
        if progress:
            progress(f"Partition functions: {len(partitions)}")
        target.executemany("INSERT INTO partfunctPay VALUES (?, ?, ?, ?)", partitions)

        line_count = 0
        for element_index, element_row in enumerate(elements, start=1):
            symbol = str(element_row[0]).strip()
            table = quoted_identifier(symbol)
            target.execute(
                f"CREATE TABLE {table} ("
                "specie TEXT, ion INTEGER, wavelen REAL, Ei REAL, Ek REAL, "
                "gi INTEGER, gk INTEGER, Aki REAL, acc INTEGER)"
            )
            source_rows = fetch_rows(
                source_cursor,
                f"SELECT specie, ion, wavelen, Ei, Ek, gi, gk, Aki FROM [{symbol}]",
            )
            rows = [row + (None,) for row in source_rows]
            target.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            target.execute(f"CREATE INDEX {quoted_identifier('idx_' + symbol + '_wave')} ON {table}(wavelen, ion)")
            line_count += len(rows)
            if progress and (element_index % 5 == 0 or element_index == len(elements)):
                progress(f"Element tables: {element_index}/{len(elements)}; lines: {line_count}")

        target.executescript(
            """
            CREATE INDEX idx_datalibs_wave ON Datalibs(wavelen);
            CREATE INDEX idx_datalibs_species ON Datalibs(specie, ion, wavelen);
            CREATE INDEX idx_daticerti_wave ON Daticerti(wavelen);
            CREATE INDEX idx_partition_species ON partfunctPay(element, ion, temperature);
            CREATE UNIQUE INDEX idx_element_symbol ON Elementi(specie);
            """
        )
        info = {
            "library": f"NIST ASD {metadata.get('nist_asd_version', 'offline')}",
            "source": "NIST Atomic Spectra Database",
            "version": str(metadata.get("nist_asd_version", "unknown")),
            "release_date": str(metadata.get("nist_release_date", "unknown")),
            "source_mdb": source_mdb.name,
            "wavelength_unit": "angstrom",
            "energy_unit": "cm^-1",
            "aki_unit": "1e8 s^-1",
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "legacy_symbol_aliases": "Aq=As; Iq=In",
        }
        target.executemany("INSERT INTO database_info(key, value) VALUES (?, ?)", info.items())
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        source_cursor.close()
        access.close()
        target.close()

    os.replace(temporary, output_db)
    return {
        "output": str(output_db),
        "provider": provider,
        "elements": len(elements),
        "line_count": line_count,
        "datalibs_count": len(datalibs),
        "partition_count": len(partitions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_mdb", type=Path)
    parser.add_argument("output_db", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    report = build_database(
        args.source_mdb,
        args.output_db,
        args.metadata,
        progress=lambda message: print(message, flush=True),
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
