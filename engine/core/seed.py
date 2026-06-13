"""
Seed minimale per la Fase 0.

NON è il world generator definitivo (sez. 25 della spec, arriverà più avanti).
Serve solo a rendere il loop giocabile: 1 mondo, 3 location connesse, 1 player,
2 NPC statici. Idempotente: non seeda se esiste già un mondo.
"""

from __future__ import annotations

import sqlite3

from engine.db import is_initialized, transaction


def seed_if_empty() -> bool:
    """Seeda solo se il DB è vuoto. Ritorna True se ha seedato."""
    if is_initialized():
        return False
    with transaction() as conn:
        _seed(conn)
    return True


def _seed(conn: sqlite3.Connection) -> None:
    # Mondo (tick 0)
    conn.execute(
        "INSERT INTO worlds (id, name, description, current_year, current_tick) "
        "VALUES (1, 'Jade Realm', 'Un mondo di coltivatori.', 1, 0);"
    )

    # Una regione root e un territorio
    conn.execute(
        "INSERT INTO regions (id, world_id, name, region_type) "
        "VALUES (1, 1, 'Mondo Mortale', 'continent');"
    )

    # 3 location
    locations = [
        (1, "Villaggio di Pietra", "city", 1, "Un tranquillo villaggio ai piedi della montagna."),
        (2, "Sentiero del Bosco", "mountain", 2, "Un sentiero alberato che sale verso nord."),
        (3, "Mercato dell'Est", "city", 1, "Bancarelle rumorose e mercanti dagli occhi attenti."),
    ]
    conn.executemany(
        "INSERT INTO locations (id, region_id, name, location_type, danger_level, description) "
        "VALUES (?, 1, ?, ?, ?, ?);",
        locations,
    )

    # Connessioni (direzionali). Villaggio <-> Bosco (N/S), Villaggio <-> Mercato (E/W)
    connections = [
        (1, 2, "north"),
        (2, 1, "south"),
        (1, 3, "east"),
        (3, 1, "west"),
    ]
    conn.executemany(
        "INSERT INTO location_connections (from_location_id, to_location_id, direction) "
        "VALUES (?, ?, ?);",
        connections,
    )

    # Player nel villaggio
    conn.execute(
        "INSERT INTO players (id, name, location_id, status, created_tick) "
        "VALUES (1, 'Wanderer', 1, 'alive', 0);"
    )

    # 2 NPC statici (Fase 0: esistono ma non agiscono)
    npcs = [
        (1, "Anziano Han", 1, "alive", "Un vecchio dallo sguardo vigile."),
        (2, "Mercante Liu", 3, "alive", "Un mercante dall'aria nervosa."),
    ]
    conn.executemany(
        "INSERT INTO npcs (id, name, location_id, status, description) "
        "VALUES (?, ?, ?, ?, ?);",
        npcs,
    )
