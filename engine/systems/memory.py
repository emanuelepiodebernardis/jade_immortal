"""
Memory System (Fase 8).

PRINCIPIO: la memoria NON è un archivio separato. Gli `events` + `event_participants`
sono già la verità persistente del mondo (vincolo 26). I "livelli" di memoria sono
viste filtrate e pesate su quei dati. Niente doppia verità, niente desync.

Livelli:
  - short_term: eventi recenti che coinvolgono il personaggio (finestra di tick);
  - historical: eventi più vecchi ma SIGNIFICATIVI (filtrati per importanza);
  - active_memory: selezione limitata e ordinata per rilevanza (recency × importanza)
    — è ciò che la Fase 9 passerà all'LLM, già pronta contro il "context drift".

Una "memoria" = un evento a cui il personaggio ha partecipato (event_participants).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# importanza per tipo di evento (1 = banale, 10 = epocale)
IMPORTANCE = {
    "death": 10,
    "absorption": 9,
    "breakthrough": 8,
    "fight": 7,
    "bounty_claimed": 7,
    "sect_tournament": 7,
    "crime": 5,
    "karmic_pressure": 6,
    "sect_join": 5,
    "faction_conflict": 6,
    "breakthrough_failure": 5,
    "faction_expand": 4,
    "encounter": 3,
    "faction_capture": 6,
    "npc_move": 1,
}
DEFAULT_IMPORTANCE = 2

SHORT_TERM_WINDOW = 80      # tick entro cui un ricordo è "fresco"
RECENCY_SCALE = 250.0       # quanto lentamente sbiadiscono i ricordi
FRESH_BONUS = 1.6           # i ricordi freschi sono più vividi
MIN_HISTORICAL_IMPORTANCE = 4
ACTIVE_BUDGET = 10


@dataclass
class Memory:
    event_id: int
    tick: int
    event_type: str
    summary: str
    importance: int
    age: int
    score: float


def importance_of(event_type: str) -> int:
    return IMPORTANCE.get(event_type, DEFAULT_IMPORTANCE)


def _significant_types(min_importance: int) -> list[str]:
    """Tipi di evento con importanza >= soglia (per filtrare in SQL)."""
    return [t for t, imp in IMPORTANCE.items() if imp >= min_importance]


def _raw_memories(conn: sqlite3.Connection, ctype: str, cid: int,
                  limit: int = 300, min_importance: int | None = None) -> list[sqlite3.Row]:
    if min_importance is None:
        return conn.execute(
            "SELECT e.id, e.tick, e.event_type, e.summary "
            "FROM events e JOIN event_participants ep ON ep.event_id = e.id "
            "WHERE ep.participant_type=? AND ep.participant_id=? "
            "ORDER BY e.tick DESC LIMIT ?;",
            (ctype, cid, limit),
        ).fetchall()
    types = _significant_types(min_importance)
    if not types:
        return []
    ph = ",".join("?" * len(types))
    return conn.execute(
        f"SELECT e.id, e.tick, e.event_type, e.summary "
        f"FROM events e JOIN event_participants ep ON ep.event_id = e.id "
        f"WHERE ep.participant_type=? AND ep.participant_id=? "
        f"AND e.event_type IN ({ph}) ORDER BY e.tick DESC LIMIT ?;",
        (ctype, cid, *types, limit),
    ).fetchall()


def _score(event_type: str, age: int) -> float:
    imp = importance_of(event_type)
    recency = 1.0 / (1.0 + max(0, age) / RECENCY_SCALE)
    s = imp * recency
    if age <= SHORT_TERM_WINDOW:
        s *= FRESH_BONUS
    return s


def _to_memory(row: sqlite3.Row, current_tick: int) -> Memory:
    age = current_tick - row["tick"]
    return Memory(
        event_id=row["id"], tick=row["tick"], event_type=row["event_type"],
        summary=row["summary"], importance=importance_of(row["event_type"]),
        age=age, score=_score(row["event_type"], age),
    )


def short_term(conn, ctype, cid, current_tick, window=SHORT_TERM_WINDOW) -> list[Memory]:
    """Ricordi recenti (entro `window` tick), qualsiasi importanza."""
    mems = [_to_memory(r, current_tick) for r in _raw_memories(conn, ctype, cid)]
    return [m for m in mems if m.age <= window]


def historical(conn, ctype, cid, current_tick,
               min_importance=MIN_HISTORICAL_IMPORTANCE, limit=20) -> list[Memory]:
    """Ricordi più vecchi ma significativi (la banalità è filtrata via SQL)."""
    rows = _raw_memories(conn, ctype, cid, min_importance=min_importance)
    mems = [_to_memory(r, current_tick) for r in rows]
    sig = [m for m in mems if m.age > SHORT_TERM_WINDOW]
    sig.sort(key=lambda m: m.score, reverse=True)
    return sig[:limit]


def active_memory(conn, ctype, cid, current_tick, budget=ACTIVE_BUDGET) -> list[Memory]:
    """Selezione attiva: i ricordi più rilevanti adesso (recency × importanza),
    limitata a `budget`. La banalità (es. spostamenti) è esclusa: non è un ricordo
    degno di nota. Restano gli eventi significativi, recenti o memorabili."""
    rows = _raw_memories(conn, ctype, cid, min_importance=2)
    candidates = [_to_memory(r, current_tick) for r in rows]
    candidates.sort(key=lambda m: m.score, reverse=True)
    return candidates[:budget]


def world_historical(conn, current_tick, min_importance=MIN_HISTORICAL_IMPORTANCE,
                     limit=15) -> list[Memory]:
    """Eventi SIGNIFICATIVI del mondo (non legati a un personaggio) — per il
    contesto narrativo globale (Fase 9) e le cronache (Fase 14). Filtra in SQL."""
    types = _significant_types(min_importance)
    if not types:
        return []
    ph = ",".join("?" * len(types))
    rows = conn.execute(
        f"SELECT id, tick, event_type, summary FROM events "
        f"WHERE event_type IN ({ph}) ORDER BY tick DESC LIMIT ?;",
        (*types, limit * 3),
    ).fetchall()
    mems = [_to_memory(r, current_tick) for r in rows]
    mems.sort(key=lambda m: (m.tick, m.score), reverse=True)
    return mems[:limit]
