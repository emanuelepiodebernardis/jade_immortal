"""
Event system — registrazione eventi con invariante di tracciabilità (vincolo 26).

Ogni evento DEVE nascere con almeno un partecipante e almeno una conseguenza.
`log_event` impone questa regola a livello di codice: è impossibile creare un
evento "orfano". Questo rende il vincolo 26 strutturale invece che opzionale.

A ogni evento/conseguenza si può sempre rispondere via SQL:
  chi c'era (event_participants), cosa è cambiato (consequences),
  quando (events.tick), visibilità (consequences.visibility).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Participant:
    type: str          # 'npc' | 'player' | 'faction'
    id: int
    role: str          # initiator | target | witness | victim


@dataclass
class Consequence:
    target_type: str   # 'npc' | 'player' | 'faction' | 'location' | 'world'
    target_id: int | None
    consequence_type: str
    description: str
    visibility: str = "hidden"   # public | private | hidden
    resolved: int = 1
    resolve_tick: int | None = None


def log_event(conn: sqlite3.Connection, *, event_type: str, tick: int,
              location_id: int | None, title: str, summary: str,
              participants: list[Participant], consequences: list[Consequence],
              status: str = "resolved") -> int:
    """Crea un evento + partecipanti + conseguenze in modo atomico e tracciabile."""
    if not participants:
        raise ValueError("Un evento deve avere almeno un partecipante (vincolo 26).")
    if not consequences:
        raise ValueError("Un evento deve avere almeno una conseguenza (vincolo 26).")

    cur = conn.execute(
        "INSERT INTO events (title, event_type, tick, location_id, status, summary) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (title, event_type, tick, location_id, status, summary),
    )
    event_id = cur.lastrowid

    for p in participants:
        conn.execute(
            "INSERT OR IGNORE INTO event_participants "
            "(event_id, participant_type, participant_id, role) VALUES (?, ?, ?, ?);",
            (event_id, p.type, p.id, p.role),
        )

    for c in consequences:
        conn.execute(
            "INSERT INTO consequences "
            "(event_id, target_type, target_id, consequence_type, visibility, "
            " description, resolved, resolve_tick) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (event_id, c.target_type, c.target_id, c.consequence_type,
             c.visibility, c.description, c.resolved, c.resolve_tick),
        )
    return event_id
