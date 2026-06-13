"""
Relazioni NPC <-> giocatore (Fase 2, base).

Il giocatore non è un NPC, quindi le relazioni vivono in `npc_player_relations`.
Assenza di riga = 'stranger' con score 0. Le interazioni (es. greet) creano o
aggiornano la riga. Gli effetti più ricchi (eventi, conseguenze) arrivano in Fase 5.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

_DEFAULT_TYPE = "stranger"


@dataclass(frozen=True)
class Disposition:
    score: int
    relationship_type: str


def get_disposition(conn: sqlite3.Connection, npc_id: int,
                    player_id: int = 1) -> Disposition:
    row = conn.execute(
        "SELECT score, relationship_type FROM npc_player_relations "
        "WHERE npc_id = ? AND player_id = ?;",
        (npc_id, player_id),
    ).fetchone()
    if row is None:
        return Disposition(0, _DEFAULT_TYPE)
    return Disposition(row["score"], row["relationship_type"])


def _classify(score: int) -> str:
    if score >= 60:
        return "friend"
    if score >= 10:
        return "acquaintance"
    if score <= -60:
        return "enemy"
    if score <= -10:
        return "rival"
    return "stranger"


def adjust(conn: sqlite3.Connection, npc_id: int, delta: int, tick: int,
          player_id: int = 1) -> Disposition:
    """Crea/aggiorna la disposizione di un NPC verso il player. Clampa -100..100."""
    current = get_disposition(conn, npc_id, player_id)
    new_score = max(-100, min(100, current.score + delta))
    new_type = _classify(new_score)
    conn.execute(
        "INSERT INTO npc_player_relations "
        "(npc_id, player_id, score, relationship_type, last_updated_tick) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(npc_id, player_id) DO UPDATE SET "
        "score = excluded.score, relationship_type = excluded.relationship_type, "
        "last_updated_tick = excluded.last_updated_tick;",
        (npc_id, player_id, new_score, new_type, tick),
    )
    return Disposition(new_score, new_type)


# ---------- relazioni NPC <-> NPC (direzionali: source verso target) ----------

def _classify_npc(score: int) -> str:
    if score >= 40:
        return "friend"
    if score >= 15:
        return "friendly"
    if score <= -40:
        return "enemy"
    if score <= -15:
        return "rival"
    return "neutral"


def get_npc_relation(conn: sqlite3.Connection, source: int, target: int) -> int:
    row = conn.execute(
        "SELECT score FROM npc_relationships WHERE source_npc=? AND target_npc=?;",
        (source, target),
    ).fetchone()
    return row["score"] if row else 0


def adjust_npc(conn: sqlite3.Connection, source: int, target: int,
               delta: int, tick: int) -> int:
    new_score = max(-100, min(100, get_npc_relation(conn, source, target) + delta))
    conn.execute(
        "INSERT INTO npc_relationships "
        "(source_npc, target_npc, score, relationship_type, last_updated_tick) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(source_npc, target_npc) DO UPDATE SET "
        "score=excluded.score, relationship_type=excluded.relationship_type, "
        "last_updated_tick=excluded.last_updated_tick;",
        (source, target, new_score, _classify_npc(new_score), tick),
    )
    return new_score
