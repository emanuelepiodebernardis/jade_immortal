"""
Creature selvagge: bestie, demoni, spiriti.

Coltivano come gli umani (hanno un regno) e popolano le zone pericolose. Si possono
cacciare e assorbire: ogni tipo dà una crescita diversa (vedi absorption).

Le zone selvagge si ripopolano: l'assorbitore ha così una via di crescita "fuori
dalla setta", non limitata dalle 4 sessioni di allenamento al giorno.
"""

from __future__ import annotations

import random
import sqlite3

# tipo -> (archetipi/nomi, range di tier indicativo)
BEASTS = ["Cinghiale Corazzato", "Orso di Ferro", "Lupo Spirituale", "Tigre di Giada",
          "Serpente di Roccia", "Aquila del Tuono"]
DEMONS = ["Demone del Sangue", "Spettro Cornuto", "Divoratore d'Ombra", "Stirpe Maligna"]
SPIRITS = ["Spirito Errante", "Anima Nebbiosa", "Eco Ancestrale", "Fiamma Fatua"]

WILD_TYPES = {"ruin", "forbidden_zone", "mountain"}     # dove vivono le creature
MIN_BEASTS = 6


def _realm_for(conn, rng, lo, hi):
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    tier = rng.randint(lo, hi)
    return by_tier.get(tier, by_tier.get(1)), tier


def _spawn_one(conn, rng, kind, location_id, lo, hi) -> int:
    pool = {"beast": BEASTS, "demon": DEMONS, "spirit": SPIRITS}[kind]
    name = rng.choice(pool)
    # nome unico-ish con un suffisso se serve
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    base = name
    i = 2
    while name in used:
        name = f"{base} {i}"; i += 1
    realm_id, tier = _realm_for(conn, rng, lo, hi)
    archetype = {"beast": "bestia", "demon": "demone", "spirit": "spirito"}[kind]
    desc = {"beast": "Una bestia selvaggia dagli occhi feroci.",
            "demon": "Una creatura demoniaca avvolta da un'aura malsana.",
            "spirit": "Un'entità spirituale dai contorni indistinti."}[kind]
    cur = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, kind, "
        "realm_id, last_active_tick) VALUES (?, ?, 'alive', ?, ?, ?, ?, 0);",
        (name, location_id, desc, archetype, kind, realm_id))
    nid = cur.lastrowid
    stage = rng.randint(1, 10)
    # le bestie sono fisiche (più vitalità/corpo); gli spiriti più "anima"
    qi = tier * 8 + stage
    body = tier * 11 + stage * 2 if kind == "beast" else tier * 7 + stage
    soul = tier * 11 + stage * 2 if kind == "spirit" else tier * 7 + stage
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, ?, ?, ?, ?, ?, ?);",
        (nid, realm_id, round(rng.uniform(0, 0.4), 2), stage, qi, body, soul, tier * 4))
    # tratti "ferini" così il loro combat_power è coerente (coraggio alto)
    conn.execute(
        "INSERT INTO npc_traits (npc_id, ambition, honor, greed, courage, loyalty, "
        "compassion, pride) VALUES (?, 40, 20, 60, ?, 10, 10, 55);",
        (nid, rng.randint(60, 90)))
    return nid


def seed_creatures(conn: sqlite3.Connection, rng: random.Random) -> None:
    wild = [r["id"] for r in conn.execute(
        "SELECT id FROM locations WHERE location_type IN (%s);" %
        ",".join("?" * len(WILD_TYPES)), tuple(WILD_TYPES)).fetchall()]
    if not wild:
        wild = [r["id"] for r in conn.execute(
            "SELECT id FROM locations ORDER BY danger_level DESC LIMIT 4;").fetchall()]
    for _ in range(8):
        loc = rng.choice(wild)
        danger = conn.execute("SELECT danger_level FROM locations WHERE id=?;", (loc,)).fetchone()["danger_level"]
        kind = rng.choices(["beast", "demon", "spirit"], weights=[5, 2, 2])[0]
        lo = max(1, danger - 1); hi = min(8, danger + 1)
        _spawn_one(conn, rng, kind, loc, lo, hi)


def replenish_wild(conn: sqlite3.Connection, rng: random.Random) -> int:
    """Mantiene viva la fauna delle zone selvagge."""
    n = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE kind<>'human' AND status='alive';").fetchone()["c"]
    if n >= MIN_BEASTS:
        return 0
    wild = [r["id"] for r in conn.execute(
        "SELECT id FROM locations ORDER BY danger_level DESC LIMIT 5;").fetchall()]
    spawned = 0
    for _ in range(MIN_BEASTS - n):
        loc = rng.choice(wild)
        danger = conn.execute("SELECT danger_level FROM locations WHERE id=?;", (loc,)).fetchone()["danger_level"]
        kind = rng.choices(["beast", "demon", "spirit"], weights=[5, 2, 2])[0]
        _spawn_one(conn, rng, kind, loc, max(1, danger - 1), min(8, danger + 1))
        spawned += 1
    return spawned


# ============================================================
# Zone di caccia delle sette (mostri scalati al livello della setta)
# ============================================================

def hunt_tier_range(sect_tier: int) -> tuple[int, int]:
    return max(1, sect_tier), min(8, sect_tier + 2)


def populate_hunt_zone(conn: sqlite3.Connection, rng: random.Random,
                       location_id: int, sect_tier: int, n: int = 4) -> None:
    lo, hi = hunt_tier_range(sect_tier)
    for _ in range(n):
        kind = rng.choices(["beast", "demon", "spirit"], weights=[5, 3, 2])[0]
        _spawn_one(conn, rng, kind, location_id, lo, hi)


def setup_hunt_zone(conn: sqlite3.Connection, rng: random.Random, faction_id: int) -> int | None:
    """Assegna alla setta una zona di caccia (location selvaggia) e la popola coi mostri
    scalati al suo livello. Idempotente sull'assegnazione: se già presente, ripopola."""
    f = conn.execute("SELECT hunt_zone_id, tier FROM factions WHERE id=?;", (faction_id,)).fetchone()
    if not f:
        return None
    tier = f["tier"] or 1
    zone = f["hunt_zone_id"]
    if zone is None:
        homes = {r["home_location_id"] for r in conn.execute(
            "SELECT home_location_id FROM factions WHERE home_location_id IS NOT NULL;")}
        cand = [r["id"] for r in conn.execute(
            "SELECT id FROM locations WHERE location_type IN ('ruin','forbidden_zone','mountain') "
            "ORDER BY danger_level DESC;").fetchall() if r["id"] not in homes]
        if not cand:
            cand = [r["id"] for r in conn.execute(
                "SELECT id FROM locations ORDER BY danger_level DESC LIMIT 5;").fetchall()]
        if not cand:
            return None
        zone = rng.choice(cand)
        conn.execute("UPDATE factions SET hunt_zone_id=? WHERE id=?;", (zone, faction_id))
    populate_hunt_zone(conn, rng, zone, tier)
    return zone


def assign_hunt_zones(conn: sqlite3.Connection, rng: random.Random) -> None:
    for f in conn.execute("SELECT id FROM factions WHERE status='active';").fetchall():
        setup_hunt_zone(conn, rng, f["id"])
