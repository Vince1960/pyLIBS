"""Synthetic LTE plasmas built from the real LIBS.db, shared by the tests (no GUI, no pyLIBS.py import)."""

from __future__ import annotations

import math
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBS_DB = ROOT / "LIBS.db"
STARK_DB = ROOT / "Stark_extended.db"
CM1 = 1.23985e-4
SAHA_C = 6.04e21

# lines used by the synthetic plasma (Å, approximate; the closest database line is taken)
LINES = {
    ("Ca", 1): [4226.7, 4302.5, 6162.2, 6439.1, 4454.8, 5588.7],
    ("Ca", 2): [3933.7, 3968.5, 3179.3, 3736.9],
    ("Mg", 1): [2852.1, 5183.6, 3832.3, 5528.4],
    ("Mg", 2): [2795.5, 2802.7, 2790.8, 2928.6],
    ("Fe", 1): [3719.9, 4045.8, 4383.5, 3581.2, 4404.8],
}


def connect():
    return sqlite3.connect(f"file:{LIBS_DB.resolve().as_posix()}?mode=ro", uri=True)


def line_data(conn, lines=LINES):
    """{(el, ion): [(wl, ei_cm1, ek_cm1, gi, gk, aki), ...]}"""
    out = {}
    for (el, ion), wls in lines.items():
        rows = []
        for w in wls:
            r = conn.execute(
                f'SELECT wavelen, Ei, Ek, gi, gk, Aki FROM "{el}" WHERE typeof(wavelen)="real" '
                "AND CAST(ion AS INTEGER)=? AND Aki>0 ORDER BY ABS(wavelen-?) LIMIT 1", (ion, w)).fetchone()
            rows.append(tuple(float(x) for x in r))
        out[(el, ion)] = rows
    return out


def element_meta(conn, el):
    m, e = conn.execute("SELECT m_atomica, en_ion FROM Elementi WHERE TRIM(specie)=? "
                        "AND typeof(m_atomica) IN ('real','integer')", (el,)).fetchone()
    return float(m), float(e) * CM1


def z_tables(conn, elements):
    t = {}
    for el in elements:
        for ion in (1, 2):
            pts = []
            for T, z in conn.execute("SELECT temperature, partfunct FROM partfunctPay WHERE TRIM(element)=? AND ion=? "
                                     "ORDER BY temperature", (el, ion)):
                try:
                    pts.append((float(T), float(z)))
                except (TypeError, ValueError):
                    pass
            t[(el, ion)] = pts
    return t


def lte_plasma(kt=0.85, ne=6e16, number_fraction=None, noise=0.0, seed=1, lines=LINES):
    """Saha-Boltzmann line intensities for a known composition.

    Returns dict with 'points' {(el, ion): [(ek_eV, y=ln(I/gA), wl, ei_eV, gA)]}, 'eion', 'mass', 'z', and the truth.
    """
    from pylibs.core.cflibs_uncertainty import ZTable
    rng = random.Random(seed)
    conn = connect()
    data = line_data(conn, lines)
    els = sorted({k[0] for k in data})
    meta = {el: element_meta(conn, el) for el in els}
    z = ZTable(z_tables(conn, els))
    conn.close()
    nf = number_fraction or {el: 1.0 / len(els) for el in els}
    T = kt * 11604.45
    pts = {}
    for (el, ion), rows in data.items():
        z1, z2 = z(el, 1, T), z(el, 2, T)
        r21 = SAHA_C / ne * kt ** 1.5 * (z2 / z1) * math.exp(-meta[el][1] / kt)
        n1 = nf[el] / (1.0 + r21)
        n_stage = n1 if ion == 1 else n1 * r21
        z_stage = z1 if ion == 1 else z2
        lst = []
        for wl, ei, ek, gi, gk, aki in rows:
            y = math.log(n_stage / z_stage) - ek * CM1 / kt + rng.gauss(0.0, noise)
            lst.append((ek * CM1, y, wl, ei * CM1, gk * aki))
        pts[(el, ion)] = lst
    return {"points": pts, "eion": {el: meta[el][1] for el in els}, "mass": {el: meta[el][0] for el in els},
            "z": z, "kt": kt, "ne": ne, "number_fraction": nf}
