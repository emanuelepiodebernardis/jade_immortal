"""
Spirito — l'energia per le TECNICHE DAO (la via del Guerriero Dao).

A differenza del Qi (che alimenta le mosse dei coltivatori classici), le tecniche che
nascono dai Dao non bruciano Qi: AFFATICANO lo spirito. Più alto è il tuo Spirito —
che cresce soprattutto con il Dao dell'Anima — più a lungo puoi scatenare Intenti del
Dao prima di doverti fermare. È il meccanismo di combattimento del Guerriero Dao:
un coltivatore di regno modesto ma dal Dao mostruoso può restare un avversario terribile.

Si rigenera come il Qi: riposando, meditando, spostandoti, e si ristabilisce a ogni
nuovo giorno.
"""

from __future__ import annotations

import sqlite3


def max_spirit(conn: sqlite3.Connection, player_id: int = 1) -> int:
    """Riserva massima: base + Dao dell'Anima + regno. Investire nell'Anima la allarga."""
    from engine.simulation import cultivation
    row = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key='anima';", (player_id,)).fetchone()
    anima = (row["comprehension"] if row and row["comprehension"] else 0)
    tier = cultivation.realm_tier(conn, "player", player_id) or 1
    return 30 + int(anima) + tier * 10


def _set(conn: sqlite3.Connection, player_id: int, value: int) -> None:
    conn.execute(
        "UPDATE character_profiles SET spirit_current=? "
        "WHERE character_type='player' AND character_id=?;", (max(0, int(value)), player_id))


def get_spirit(conn: sqlite3.Connection, player_id: int = 1) -> int:
    r = conn.execute(
        "SELECT spirit_current FROM character_profiles "
        "WHERE character_type='player' AND character_id=?;", (player_id,)).fetchone()
    mx = max_spirit(conn, player_id)
    if r is None:
        return mx
    cur = r["spirit_current"]
    if cur is None or cur < 0:        # non inizializzato: parte pieno
        _set(conn, player_id, mx)
        return mx
    return min(cur, mx)


def can_afford(conn: sqlite3.Connection, cost: int, player_id: int = 1) -> bool:
    return get_spirit(conn, player_id) >= cost


def spend(conn: sqlite3.Connection, cost: int, player_id: int = 1) -> bool:
    cur = get_spirit(conn, player_id)
    if cur < cost:
        return False
    _set(conn, player_id, cur - cost)
    return True


def restore(conn: sqlite3.Connection, amount: int, player_id: int = 1) -> int:
    _set(conn, player_id, min(max_spirit(conn, player_id), get_spirit(conn, player_id) + amount))
    return get_spirit(conn, player_id)


def restore_fraction(conn: sqlite3.Connection, frac: float, player_id: int = 1) -> int:
    return restore(conn, int(max_spirit(conn, player_id) * frac), player_id)


def restore_full(conn: sqlite3.Connection, player_id: int = 1) -> int:
    _set(conn, player_id, max_spirit(conn, player_id))
    return get_spirit(conn, player_id)


def spirit_label(conn: sqlite3.Connection, player_id: int = 1) -> str:
    cur, mx = get_spirit(conn, player_id), max_spirit(conn, player_id)
    frac = cur / mx if mx else 0
    word = ("colmo" if frac >= 0.95 else "lucido" if frac >= 0.6
            else "affaticato" if frac >= 0.3 else "esausto")
    return f"{cur}/{mx} ({word})"
