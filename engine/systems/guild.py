"""
Gilde: zone di caccia, punti MERITO e TECNICHE segrete.

Uccidere mostri (bestie/demoni/spiriti) dà merito alla tua setta; nella zona di
caccia della tua setta il merito è maggiore. Col merito impari le tecniche segrete
della setta: più forti nelle sette di livello alto. Le tecniche restano tue per
sempre (anche se cambi setta); il merito invece è legato alla membership corrente
e riparte da zero quando ascendi a una nuova setta.

L'assorbimento funziona normalmente su questi mostri (vedi absorption): cacciare
e divorare nelle zone di caccia è una via di crescita parallela all'allenamento.
"""

from __future__ import annotations

import sqlite3

# suffisso del nome tecnica per elemento della setta
_TECH_SUFFIX = {
    "corpo": "del Corpo Indistruttibile",
    "fulmine": "del Fulmine Divino",
    "spada": "della Spada Celeste",
    "anima": "dell'Anima Eterna",
}
_RANK_NAME = {1: "Manuale", 2: "Arte", 3: "Legge"}


# ============================================================
# Merito
# ============================================================

def get_merit(conn: sqlite3.Connection, player_id: int = 1) -> int:
    r = conn.execute("SELECT merit FROM sect_memberships WHERE player_id=?;",
                     (player_id,)).fetchone()
    return (r["merit"] or 0) if r else 0


def add_merit(conn: sqlite3.Connection, amount: int, player_id: int = 1) -> int:
    conn.execute("UPDATE sect_memberships SET merit=COALESCE(merit,0)+? WHERE player_id=?;",
                 (amount, player_id))
    return get_merit(conn, player_id)


def merit_for_kill(conn: sqlite3.Connection, npc_id: int, in_hunt_zone: bool = False) -> int:
    """Merito per una creatura uccisa: scala col suo regno; +50% se nella zona di caccia."""
    row = conn.execute("SELECT kind, realm_id FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not row or row["kind"] in (None, "human"):
        return 0
    tr = conn.execute("SELECT tier FROM cultivation_realms WHERE id=?;",
                      (row["realm_id"],)).fetchone()
    ctier = tr["tier"] if tr else 1
    base = 4 + ctier * 3
    return int(base * 1.5) if in_hunt_zone else base


def on_creature_kill(conn: sqlite3.Connection, npc_id: int, player_id: int = 1) -> dict:
    """Accredita merito alla setta del giocatore per aver ucciso una creatura.
    Ritorna {'gained', 'merit', 'in_zone'}. gained=0 se umano o senza setta."""
    from engine.systems import sects
    m = sects.get_membership(conn, player_id)
    if not m:
        return {"gained": 0, "merit": 0, "in_zone": False}
    ploc = conn.execute("SELECT location_id FROM players WHERE id=?;",
                        (player_id,)).fetchone()["location_id"]
    hz = conn.execute("SELECT hunt_zone_id FROM factions WHERE id=?;",
                      (m["faction_id"],)).fetchone()
    in_zone = bool(hz and hz["hunt_zone_id"] == ploc)
    gained = merit_for_kill(conn, npc_id, in_zone)
    if gained <= 0:
        return {"gained": 0, "merit": get_merit(conn, player_id), "in_zone": in_zone}
    total = add_merit(conn, gained, player_id)
    return {"gained": gained, "merit": total, "in_zone": in_zone}


# ============================================================
# Tecniche segrete
# ============================================================

def sect_techniques(conn: sqlite3.Connection, faction_id: int) -> list[dict]:
    """Le 3 tecniche segrete della setta, scalate al suo livello (costo/potenza crescenti)."""
    f = conn.execute("SELECT tier, element FROM factions WHERE id=?;", (faction_id,)).fetchone()
    if not f:
        return []
    tier = f["tier"] or 1
    suffix = _TECH_SUFFIX.get(f["element"], "Segreta")
    techs = []
    for i in (1, 2, 3):
        cost = tier * 40 * i
        magnitude = round((0.05 + 0.03 * i) * (1 + 0.4 * (tier - 1)), 3)
        techs.append({
            "key": f"{faction_id}:{i}",
            "name": f"{_RANK_NAME[i]} {suffix}",
            "cost": cost,
            "magnitude": magnitude,
            "rank": i,
        })
    return techs


def is_learned(conn: sqlite3.Connection, tech_key: str, player_id: int = 1) -> bool:
    return conn.execute(
        "SELECT 1 FROM learned_techniques WHERE player_id=? AND tech_key=?;",
        (player_id, tech_key)).fetchone() is not None


def learned(conn: sqlite3.Connection, player_id: int = 1) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT tech_key, name, magnitude FROM learned_techniques WHERE player_id=?;",
        (player_id,)).fetchall()


def learn(conn: sqlite3.Connection, tick: int, rank: int, player_id: int = 1) -> dict:
    """Impara la tecnica n. <rank> (1..3) della tua setta, spendendo merito."""
    from engine.systems import sects
    m = sects.get_membership(conn, player_id)
    if not m:
        return {"status": "no_sect"}
    tech = next((t for t in sect_techniques(conn, m["faction_id"]) if t["rank"] == rank), None)
    if tech is None:
        return {"status": "no_such"}
    if is_learned(conn, tech["key"], player_id):
        return {"status": "already", "name": tech["name"]}
    merit = get_merit(conn, player_id)
    if merit < tech["cost"]:
        return {"status": "poor", "need": tech["cost"], "have": merit, "name": tech["name"]}
    add_merit(conn, -tech["cost"], player_id)
    conn.execute(
        "INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (player_id, m["faction_id"], tech["key"], tech["name"], tech["magnitude"], tick))
    return {"status": "learned", "name": tech["name"], "magnitude": tech["magnitude"],
            "merit": get_merit(conn, player_id)}


def technique_combat_factor(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    """Moltiplicatore di potenza dalle tecniche apprese (solo player)."""
    if ctype != "player":
        return 1.0
    rows = conn.execute(
        "SELECT magnitude FROM learned_techniques WHERE player_id=?;", (cid,)).fetchall()
    return 1.0 + sum((r["magnitude"] or 0) for r in rows)
