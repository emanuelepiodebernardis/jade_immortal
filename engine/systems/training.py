"""
Economia dell'allenamento.

Introduce il concetto di GIORNO e il rendimento decrescente: le prime sessioni
di coltivazione della giornata rendono molto, poi cala (stanchezza, qi esaurito).
Così "quante volte al giorno posso allenarmi" ha una risposta reale, e salire di
regno torna una conquista invece di uno spam infinito.

Essere membro di una setta e allenarsi presso la SUA sede dà un bonus (formazioni
di raccolta del qi).
"""

from __future__ import annotations

import sqlite3

DAY_TICKS = 120                      # durata di un "giorno" in tick (~10 sessioni di tempo)
# rendimento per numero di sessioni già fatte oggi (0 = prima sessione)
SESSION_YIELD = [1.0, 0.8, 0.55, 0.30, 0.15]
EXHAUSTED_YIELD = 0.08               # oltre l'elenco: praticamente esausto
SECT_HQ_BONUS = 0.30                 # +30% se ti alleni nella sede della tua setta


def current_day(tick: int) -> int:
    return tick // DAY_TICKS


def sessions_today(conn: sqlite3.Connection, tick: int,
                   ctype: str = "player", cid: int = 1) -> int:
    day = current_day(tick)
    row = conn.execute(
        "SELECT cultivation_sessions FROM daily_activity "
        "WHERE character_type=? AND character_id=? AND day=?;",
        (ctype, cid, day)).fetchone()
    return row["cultivation_sessions"] if row else 0


def record_session(conn: sqlite3.Connection, tick: int,
                   ctype: str = "player", cid: int = 1) -> int:
    """Registra una sessione di allenamento per oggi. Ritorna il numero (1-based)."""
    day = current_day(tick)
    n = sessions_today(conn, tick, ctype, cid) + 1
    conn.execute(
        "INSERT INTO daily_activity (character_type, character_id, day, cultivation_sessions) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(character_type, character_id, day) DO UPDATE SET "
        "cultivation_sessions=excluded.cultivation_sessions;",
        (ctype, cid, day, n))
    return n


def session_yield(session_number: int) -> float:
    """Rendimento della N-esima sessione (1-based) della giornata."""
    idx = session_number - 1
    return SESSION_YIELD[idx] if 0 <= idx < len(SESSION_YIELD) else EXHAUSTED_YIELD


def location_bonus(conn: sqlite3.Connection, player_id: int, location_id: int) -> float:
    """Bonus di coltivazione se ti alleni nella sede della tua setta."""
    from engine.systems import sects
    m = sects.get_membership(conn, player_id)
    if not m:
        return 0.0
    hq = conn.execute(
        "SELECT home_location_id FROM factions WHERE id=?;", (m["faction_id"],)
    ).fetchone()
    if hq and hq["home_location_id"] == location_id:
        return SECT_HQ_BONUS
    return 0.0


def yield_label(y: float) -> str:
    if y >= 0.9:
        return "pieno"
    if y >= 0.5:
        return "buono"
    if y >= 0.25:
        return "calante"
    return "esiguo (sei sfinito)"
