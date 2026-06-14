"""
Entità base e funzioni di accesso (repository).

In Fase 0 esistono solo Location, NPC, Player come oggetti read-only +
poche query. Niente logica di simulazione: solo lettura coerente dal DB.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    id: int
    name: str
    location_type: str | None
    danger_level: int
    description: str | None


@dataclass(frozen=True)
class NPC:
    id: int
    name: str
    location_id: int | None
    status: str
    description: str | None
    archetype: str | None = None


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    location_id: int | None
    status: str


# ---------- Location ----------

def get_location(conn: sqlite3.Connection, location_id: int) -> Location | None:
    row = conn.execute(
        "SELECT id, name, location_type, danger_level, description "
        "FROM locations WHERE id = ?;",
        (location_id,),
    ).fetchone()
    if row is None:
        return None
    return Location(
        id=row["id"],
        name=row["name"],
        location_type=row["location_type"],
        danger_level=row["danger_level"],
        description=row["description"],
    )


def get_exits(conn: sqlite3.Connection, location_id: int) -> dict[str, int]:
    """direction -> to_location_id per la location data."""
    rows = conn.execute(
        "SELECT direction, to_location_id FROM location_connections "
        "WHERE from_location_id = ?;",
        (location_id,),
    ).fetchall()
    return {r["direction"]: r["to_location_id"] for r in rows}


def get_exits_detailed(conn: sqlite3.Connection, location_id: int) -> list[dict]:
    """Uscite con nome e danger della destinazione (per look/map)."""
    rows = conn.execute(
        "SELECT lc.direction, l.id AS dest_id, l.name AS dest_name, l.danger_level "
        "FROM location_connections lc JOIN locations l ON l.id = lc.to_location_id "
        "WHERE lc.from_location_id = ? ORDER BY lc.direction;",
        (location_id,),
    ).fetchall()
    return [
        {
            "direction": r["direction"],
            "dest_id": r["dest_id"],
            "dest_name": r["dest_name"],
            "danger": r["danger_level"],
        }
        for r in rows
    ]


# ---------- NPC ----------

def npcs_in_location(conn: sqlite3.Connection, location_id: int) -> list[NPC]:
    rows = conn.execute(
        "SELECT id, name, location_id, status, description, archetype FROM npcs "
        "WHERE location_id = ? AND status = 'alive' ORDER BY id;",
        (location_id,),
    ).fetchall()
    return [_npc_from_row(r) for r in rows]


def _npc_from_row(r: sqlite3.Row) -> NPC:
    return NPC(
        id=r["id"],
        name=r["name"],
        location_id=r["location_id"],
        status=r["status"],
        description=r["description"],
        archetype=r["archetype"],
    )


def get_npc(conn: sqlite3.Connection, npc_id: int) -> NPC | None:
    """Recupera un NPC per id (qualsiasi stato)."""
    row = conn.execute(
        "SELECT id, name, location_id, status, description, archetype FROM npcs WHERE id = ?;",
        (npc_id,),
    ).fetchone()
    return _npc_from_row(row) if row else None


def find_npc_in_location(conn: sqlite3.Connection, location_id: int,
                         name_fragment: str) -> NPC | None:
    """Trova un NPC vivo nella location per sottostringa del nome (case-insensitive)."""
    frag = f"%{name_fragment.strip().lower()}%"
    row = conn.execute(
        "SELECT id, name, location_id, status, description, archetype FROM npcs "
        "WHERE location_id = ? AND status = 'alive' AND LOWER(name) LIKE ? "
        "ORDER BY id LIMIT 1;",
        (location_id, frag),
    ).fetchone()
    return _npc_from_row(row) if row else None


def dead_npcs_in_location(conn: sqlite3.Connection, location_id: int) -> list[NPC]:
    rows = conn.execute(
        "SELECT id, name, location_id, status, description, archetype FROM npcs "
        "WHERE location_id = ? AND status = 'dead' ORDER BY id;",
        (location_id,),
    ).fetchall()
    return [_npc_from_row(r) for r in rows]


def find_dead_npc_in_location(conn: sqlite3.Connection, location_id: int,
                              name_fragment: str) -> NPC | None:
    frag = f"%{name_fragment.strip().lower()}%"
    row = conn.execute(
        "SELECT id, name, location_id, status, description, archetype FROM npcs "
        "WHERE location_id = ? AND status = 'dead' AND LOWER(name) LIKE ? "
        "ORDER BY id LIMIT 1;",
        (location_id, frag),
    ).fetchone()
    return _npc_from_row(row) if row else None


def get_npc_traits(conn: sqlite3.Connection, npc_id: int) -> dict[str, int]:
    row = conn.execute(
        "SELECT ambition, honor, greed, courage, loyalty, compassion, pride "
        "FROM npc_traits WHERE npc_id = ?;",
        (npc_id,),
    ).fetchone()
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}


# ---------- Player ----------

def get_player(conn: sqlite3.Connection, player_id: int = 1) -> Player | None:
    row = conn.execute(
        "SELECT id, name, location_id, status FROM players WHERE id = ?;",
        (player_id,),
    ).fetchone()
    if row is None:
        return None
    return Player(
        id=row["id"],
        name=row["name"],
        location_id=row["location_id"],
        status=row["status"],
    )


def move_player(conn: sqlite3.Connection, player_id: int, new_location_id: int) -> None:
    conn.execute(
        "UPDATE players SET location_id = ? WHERE id = ?;",
        (new_location_id, player_id),
    )


# ---------- Fazioni ----------

def location_owner_name(conn: sqlite3.Connection, location_id: int) -> str | None:
    row = conn.execute(
        "SELECT f.name FROM locations l JOIN factions f ON f.id = l.owner_faction_id "
        "WHERE l.id = ?;",
        (location_id,),
    ).fetchone()
    return row["name"] if row else None


def list_factions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT f.id, f.name, f.influence, f.wealth, "
        "(SELECT COUNT(*) FROM locations WHERE owner_faction_id=f.id) AS territories, "
        "(SELECT name FROM npcs WHERE id=f.leader_id) AS leader "
        "FROM factions f WHERE f.status='active' ORDER BY f.influence DESC;"
    ).fetchall()
    return [dict(r) for r in rows]


def faction_detail(conn: sqlite3.Connection, name_fragment: str) -> dict | None:
    frag = f"%{name_fragment.strip().lower()}%"
    f = conn.execute(
        "SELECT id, name, influence, wealth, goals, leader_id FROM factions "
        "WHERE status='active' AND LOWER(name) LIKE ? LIMIT 1;",
        (frag,),
    ).fetchone()
    if f is None:
        return None
    territories = [r["name"] for r in conn.execute(
        "SELECT name FROM locations WHERE owner_faction_id=? ORDER BY name;", (f["id"],))]
    leader = conn.execute(
        "SELECT name FROM npcs WHERE id=?;", (f["leader_id"],)).fetchone()
    relations = conn.execute(
        "SELECT CASE WHEN faction_a=? THEN faction_b ELSE faction_a END AS other, "
        "relation_type, relation_score FROM faction_relations "
        "WHERE faction_a=? OR faction_b=?;", (f["id"], f["id"], f["id"])).fetchall()
    rel_named = []
    for r in relations:
        on = conn.execute("SELECT name FROM factions WHERE id=?;", (r["other"],)).fetchone()
        if on:
            rel_named.append((on["name"], r["relation_type"], r["relation_score"]))
    return {
        "name": f["name"], "influence": f["influence"], "wealth": f["wealth"],
        "goals": f["goals"], "leader": leader["name"] if leader else None,
        "territories": territories, "relations": rel_named,
    }


# ---------- Cronaca / log eventi ----------

def recent_events(conn: sqlite3.Connection, limit: int = 8,
                  only_public: bool = True) -> list[dict]:
    """Eventi recenti. Con only_public=True mostra solo ciò che il giocatore
    potrebbe sapere (eventi con almeno una conseguenza pubblica)."""
    if only_public:
        rows = conn.execute(
            "SELECT DISTINCT e.tick, e.event_type, e.summary FROM events e "
            "JOIN consequences c ON c.event_id=e.id AND c.visibility='public' "
            "ORDER BY e.tick DESC, e.id DESC LIMIT ?;",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT tick, event_type, summary FROM events "
            "ORDER BY tick DESC, id DESC LIMIT ?;",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
