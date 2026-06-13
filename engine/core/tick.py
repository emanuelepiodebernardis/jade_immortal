"""
Sistema tick globale.

Modello temporale (vedi spec sez. 4): il tempo avanza ogni volta che il giocatore
agisce. Ogni azione costa N tick. In Fase 0 il tick è solo un contatore + log;
dalla Fase 3 world_tick.py aggancerà qui la simulazione vera.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

# Costo in tick per tipo di azione (spec sez. 4)
TICK_COST = {
    "move": 1,
    "look": 0,        # osservare non fa passare il tempo
    "status": 0,
    "short_rest": 6,
    "cultivate": 12,
    "long_rest": 24,
    "travel_far": 72,
}


def get_tick(conn: sqlite3.Connection, world_id: int = 1) -> int:
    row = conn.execute(
        "SELECT current_tick FROM worlds WHERE id = ?;", (world_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"World {world_id} non esiste.")
    return row["current_tick"]


def advance_tick(conn: sqlite3.Connection, n: int = 1, world_id: int = 1,
                 on_tick=None) -> int:
    """
    Avanza il mondo di n tick. Per ogni tick, se `on_tick` è fornito, lo chiama
    con (conn, tick_number) PRIMA di registrare il tick; deve ritornare
    (events_processed, npcs_acted). Aggiorna worlds.current_tick e logga
    simulation_ticks. Ritorna il nuovo current_tick.

    `on_tick` è il punto unico di aggancio per la simulazione (world_tick, Fase 3+).
    Senza callback (Fase 0/1) il tick è solo un contatore.
    """
    if n <= 0:
        return get_tick(conn, world_id)

    current = get_tick(conn, world_id)
    ts = datetime.now(timezone.utc).isoformat()
    for i in range(1, n + 1):
        tick_no = current + i
        events_processed, npcs_acted = (0, 0)
        if on_tick is not None:
            result = on_tick(conn, tick_no)
            if result:
                events_processed, npcs_acted = result
        conn.execute(
            "INSERT INTO simulation_ticks "
            "(world_id, tick_number, timestamp, events_processed, npcs_acted) "
            "VALUES (?, ?, ?, ?, ?);",
            (world_id, tick_no, ts, events_processed, npcs_acted),
        )
        conn.execute(
            "UPDATE worlds SET current_tick = ? WHERE id = ?;", (tick_no, world_id)
        )
    return current + n


def cost_of(action: str) -> int:
    """Costo in tick di un'azione; default 1 se non mappata."""
    return TICK_COST.get(action, 1)
