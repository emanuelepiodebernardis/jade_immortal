"""
Qi — l'energia per le MOSSE attive in combattimento.

Il massimo dipende dal REGNO (livello): più alto il regno, più Qi. Le mosse lo
consumano (quelle più forti di più). NON si rigenera mentre combatti (gli 'attack'
non lo recuperano): solo riposando (wait/sleep), meditando (cultivate/comprehend) o
spostandoti. Così, anche col cooldown scaduto, una volta esaurito il Qi non puoi più
scatenare mosse: ti restano gli attacchi normali o devi ritirarti a recuperare.

(È distinto dal 'qi_level' della coltivazione: questo è la riserva di energia da spendere.)
"""

from __future__ import annotations

import sqlite3


def max_qi(conn: sqlite3.Connection, player_id: int = 1) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player_id) or 1
    rec = cultivation.get_record(conn, "player", player_id)
    stage = (rec["stage"] if rec and rec["stage"] else 1)
    return tier * 60 + stage * 5


def _set(conn: sqlite3.Connection, player_id: int, value: int) -> None:
    conn.execute(
        "UPDATE character_profiles SET qi_current=? WHERE character_type='player' AND character_id=?;",
        (max(0, int(value)), player_id))


def get_qi(conn: sqlite3.Connection, player_id: int = 1) -> int:
    r = conn.execute(
        "SELECT qi_current FROM character_profiles WHERE character_type='player' AND character_id=?;",
        (player_id,)).fetchone()
    mx = max_qi(conn, player_id)
    if r is None:
        return mx
    cur = r["qi_current"]
    if cur is None or cur < 0:        # non inizializzato: parte pieno
        _set(conn, player_id, mx)
        return mx
    return min(cur, mx)


def can_afford(conn: sqlite3.Connection, cost: int, player_id: int = 1) -> bool:
    return get_qi(conn, player_id) >= cost


def spend(conn: sqlite3.Connection, cost: int, player_id: int = 1) -> bool:
    cur = get_qi(conn, player_id)
    if cur < cost:
        return False
    _set(conn, player_id, cur - cost)
    return True


def restore(conn: sqlite3.Connection, amount: int, player_id: int = 1) -> int:
    _set(conn, player_id, min(max_qi(conn, player_id), get_qi(conn, player_id) + amount))
    return get_qi(conn, player_id)


def restore_fraction(conn: sqlite3.Connection, frac: float, player_id: int = 1) -> int:
    return restore(conn, int(max_qi(conn, player_id) * frac), player_id)


def restore_full(conn: sqlite3.Connection, player_id: int = 1) -> int:
    _set(conn, player_id, max_qi(conn, player_id))
    return get_qi(conn, player_id)


def qi_label(conn: sqlite3.Connection, player_id: int = 1) -> str:
    return f"{get_qi(conn, player_id)}/{max_qi(conn, player_id)}"
