"""
Due vie di crescita.

Ogni volta che COLTIVI ('cultivate') rafforzi le tue FONDAMENTA (corpo: vitalità e
difesa). Ogni volta che ALLENI un Dao ('comprehend') affini la tua INTUIZIONE
(attacco e spirito). A lungo andare chi pende verso i Dao diventa un
"Seguace del Dao", chi pende verso la coltivazione un "Coltivatore dell'Universo";
le due vie potenziano statistiche diverse.

Inoltre i Dao versano punti-statistica DIRETTI in base al livello raggiunto (vedi
dao_training.dao_stat_points): così chi allena Dao di alto livello è davvero più forte
di chi accumula solo coltivazione.
"""

from __future__ import annotations

import sqlite3

FOUNDATION_PER_CULT = 1.0     # fondamenta guadagnate per sessione di coltivazione
INSIGHT_PER_DAO = 1.0         # intuizione guadagnata per sessione di allenamento Dao

PATH_DAO = "Seguace del Dao"
PATH_CULT = "Coltivatore dell'Universo"
PATH_BAL = "Via Equilibrata"
PATH_NONE = "Viandante"


def _counters(conn: sqlite3.Connection, pid: int = 1) -> tuple[int, int]:
    r = conn.execute(
        "SELECT dao_sessions, cult_sessions FROM character_profiles "
        "WHERE character_type='player' AND character_id=?;", (pid,)).fetchone()
    if not r:
        return (0, 0)
    return (r["dao_sessions"] or 0, r["cult_sessions"] or 0)


def record_cultivation(conn: sqlite3.Connection, pid: int = 1) -> None:
    conn.execute("UPDATE character_profiles SET cult_sessions=COALESCE(cult_sessions,0)+1 "
                 "WHERE character_type='player' AND character_id=?;", (pid,))


def record_dao_training(conn: sqlite3.Connection, pid: int = 1) -> None:
    conn.execute("UPDATE character_profiles SET dao_sessions=COALESCE(dao_sessions,0)+1 "
                 "WHERE character_type='player' AND character_id=?;", (pid,))


def path(conn: sqlite3.Connection, pid: int = 1) -> tuple[str, str]:
    dao, cult = _counters(conn, pid)
    total = dao + cult
    if total < 10:
        return ("none", PATH_NONE)
    frac = dao / total
    if frac >= 0.6:
        return ("dao", PATH_DAO)
    if frac <= 0.4:
        return ("cult", PATH_CULT)
    return ("bal", PATH_BAL)


def path_label(conn: sqlite3.Connection, pid: int = 1) -> str:
    return path(conn, pid)[1]


def growth_bonuses(conn: sqlite3.Connection, ctype: str, cid: int) -> dict:
    """Bonus-statistica DIRETTI (flat) da sommare alla potenza:
    Dao (per tutti) + sessioni (solo player) con il moltiplicatore della via."""
    from engine.systems import dao_training
    pts = dao_training.dao_stat_points(conn, ctype, cid)   # attack/defense/vitality/spirit
    dao_attack = pts["attack"]
    dao_defense = pts["defense"]
    dao_vitality = pts["vitality"]
    foundation = 0.0
    if ctype == "player":
        dao_s, cult_s = _counters(conn, cid)
        dao_attack += dao_s * INSIGHT_PER_DAO * 0.5     # intuizione -> attacco
        foundation = cult_s * FOUNDATION_PER_CULT
        pkey = path(conn, cid)[0]
        dao_mult = 1.25 if pkey == "dao" else 1.0       # la Via del Dao amplifica i Dao
        cult_mult = 1.25 if pkey == "cult" else 1.0     # la Via dell'Universo le fondamenta
        dao_attack *= dao_mult
        dao_defense *= dao_mult
        dao_vitality *= dao_mult
        foundation *= cult_mult
    return {
        "attack": dao_attack,
        "defense": dao_defense + foundation * 0.25,
        "vitality": dao_vitality + foundation * 0.5,
    }


def spirit_bonus(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    """Punti di spirito (per la percezione) da Dao dell'Anima + intuizione."""
    from engine.systems import dao_training
    bonus = dao_training.dao_stat_points(conn, ctype, cid)["spirit"]
    if ctype == "player":
        dao_s, _ = _counters(conn, cid)
        bonus += dao_s * 0.5
        if path(conn, cid)[0] == "dao":
            bonus *= 1.25
    return bonus
