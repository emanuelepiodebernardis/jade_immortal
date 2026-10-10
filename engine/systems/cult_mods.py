"""
Moltiplicatori di coltivazione e comprensione raccolti da tutti i sistemi (un solo punto
da cui li leggono 'cultivate', 'ritiro' e 'comprehend'):

  - grotta-dimora (formazione di raccolta del Qi, stanza del ritiro)
  - radici spirituali (punteggi per elemento e combinazioni)
  - metodo di coltivazione (gongfa) praticato
  - compagno del Dao (doppia coltivazione)

Ogni voce ritorna (moltiplicatore, etichetta). Tutto è facoltativo: se un sistema non è
attivo per il giocatore, il suo contributo è 1.0.
"""

from __future__ import annotations

import sqlite3


def _parts_cult(conn: sqlite3.Connection, pid: int, location_id: int | None,
                seclusion: bool = False) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    from engine.systems import cave_abode, spirit_roots, gongfa, bonds
    m, lbl = cave_abode.cultivation_mult(conn, pid, location_id, seclusion)
    if m != 1.0:
        out.append((m, lbl))
    m, lbl = spirit_roots.cultivation_mult(conn, "player", pid)
    if m != 1.0:
        out.append((m, lbl))
    m, lbl = gongfa.cultivation_mult(conn, pid)
    if m != 1.0:
        out.append((m, lbl))
    m, lbl = bonds.dao_partner_mult(conn, pid, location_id)
    if m != 1.0:
        out.append((m, lbl))
    from engine.systems import formations
    m, lbl = formations.cultivation_mult(conn, location_id)
    if m != 1.0:
        out.append((m, lbl))
    from engine.systems import ascension
    m, lbl = ascension.cultivation_mult(conn, location_id)
    if m != 1.0:
        out.append((m, lbl))
    return out


def cultivation_mult(conn: sqlite3.Connection, pid: int, location_id: int | None = None,
                     seclusion: bool = False) -> tuple[float, list[str]]:
    total, labels = 1.0, []
    for m, lbl in _parts_cult(conn, pid, location_id, seclusion):
        total *= m
        labels.append(lbl)
    return total, labels


def dao_mult(conn: sqlite3.Connection, pid: int, dao_key: str) -> float:
    from engine.systems import spirit_roots, bloodlines
    return spirit_roots.dao_mult(conn, "player", pid, dao_key) * bloodlines.dao_mult(conn, dao_key)
