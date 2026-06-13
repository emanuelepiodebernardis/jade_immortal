"""
Generazione NPC (Fase 2 — NPC Identity).

I traits sono correlati all'archetipo: un anziano è onorevole e poco ambizioso,
un mercante è avido, un eremita compassionevole, ecc. Ogni tratto è un valore
base dell'archetipo + jitter casuale (deterministico via rng), clampato 0-100.

La descrizione e il "tag" inline sono generati dai traits, senza LLM.
"""

from __future__ import annotations

import random
import sqlite3

# Pool nomi (deterministici via rng)
_SURNAMES = ["Han", "Liu", "Zhao", "Mei", "Gao", "Wu", "Lin", "Shen",
             "Bai", "Tang", "Yun", "Xu"]
_GIVEN = ["Wei", "Feng", "Lan", "Jian", "Yan", "Ruo", "Tian", "Cheng",
          "Min", "Hua", "Zhi", "Bo"]

TRAIT_NAMES = ["ambition", "honor", "greed", "courage", "loyalty",
               "compassion", "pride"]

# Profili base per archetipo (valori 0-100). +/- jitter al roll.
ARCHETYPE_PROFILES: dict[str, dict[str, int]] = {
    "anziano":   {"ambition": 30, "honor": 75, "greed": 25, "courage": 55,
                  "loyalty": 70, "compassion": 60, "pride": 70},
    "mercante":  {"ambition": 55, "honor": 35, "greed": 80, "courage": 35,
                  "loyalty": 40, "compassion": 35, "pride": 45},
    "vagabondo": {"ambition": 45, "honor": 45, "greed": 45, "courage": 65,
                  "loyalty": 30, "compassion": 45, "pride": 40},
    "discepolo": {"ambition": 75, "honor": 55, "greed": 40, "courage": 60,
                  "loyalty": 70, "compassion": 45, "pride": 55},
    "eremita":   {"ambition": 20, "honor": 70, "greed": 20, "courage": 50,
                  "loyalty": 35, "compassion": 70, "pride": 50},
    "guardia":   {"ambition": 40, "honor": 60, "greed": 35, "courage": 75,
                  "loyalty": 75, "compassion": 45, "pride": 50},
    "patriarca": {"ambition": 80, "honor": 60, "greed": 45, "courage": 70,
                  "loyalty": 65, "compassion": 40, "pride": 80},
}

# Archetipi plausibili per tipo di location (pesati)
_ARCHETYPES_BY_LOC = {
    "city":           (["mercante", "guardia", "anziano", "discepolo"], [4, 3, 2, 2]),
    "mountain":       (["eremita", "vagabondo", "discepolo"], [3, 2, 2]),
    "ruin":           (["vagabondo", "eremita"], [3, 1]),
    "forbidden_zone": (["vagabondo", "eremita"], [2, 1]),
}

_JITTER = 15

# tratto -> (aggettivo se alto, aggettivo se basso)  [forma maschile di default]
_TRAIT_ADJ = {
    "ambition":   ("ambizioso", "pacato"),
    "honor":      ("onorevole", "infido"),
    "greed":      ("avido", "disinteressato"),
    "courage":    ("coraggioso", "timoroso"),
    "loyalty":    ("leale", "voltagabbana"),
    "compassion": ("compassionevole", "spietato"),
    "pride":      ("fiero", "umile"),
}


def pick_archetype(rng: random.Random, location_type: str) -> str:
    pool, weights = _ARCHETYPES_BY_LOC.get(location_type, (list(ARCHETYPE_PROFILES), None))
    return rng.choices(pool, weights=weights)[0]


def roll_traits(rng: random.Random, archetype: str) -> dict[str, int]:
    base = ARCHETYPE_PROFILES[archetype]
    return {
        t: max(0, min(100, base[t] + rng.randint(-_JITTER, _JITTER)))
        for t in TRAIT_NAMES
    }


def _salient_traits(traits: dict[str, int], n: int = 2) -> list[tuple[str, int]]:
    """I tratti più caratterizzanti = quelli più lontani da 50."""
    return sorted(traits.items(), key=lambda kv: abs(kv[1] - 50), reverse=True)[:n]


def _adj_for(trait: str, value: int) -> str:
    high, low = _TRAIT_ADJ[trait]
    return high if value >= 50 else low


def dominant_descriptor(traits: dict[str, int]) -> str:
    """Aggettivo singolo per il tag inline (es. 'avido')."""
    t, v = _salient_traits(traits, 1)[0]
    return _adj_for(t, v)


def make_description(archetype: str, traits: dict[str, int]) -> str:
    top = _salient_traits(traits, 2)
    adjs = [_adj_for(t, v) for t, v in top]
    return f"{archetype.capitalize()}, {adjs[0]} e {adjs[1]} d'animo."


def _unique_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(100):
        n = f"{rng.choice(_SURNAMES)} {rng.choice(_GIVEN)}"
        if n not in used:
            used.add(n)
            return n
    return f"{rng.choice(_SURNAMES)} {rng.choice(_GIVEN)}{rng.randint(2, 99)}"


def generate_static_npcs(conn: sqlite3.Connection, rng: random.Random,
                         count: int, all_locs: list[int]) -> None:
    """Crea `count` NPC con archetipo, traits correlati, descrizione e (se nel
    territorio di una fazione) membership."""
    loc_info = {
        r["id"]: (r["location_type"], r["owner_faction_id"])
        for r in conn.execute("SELECT id, location_type, owner_faction_id FROM locations;")
    }
    weights = [5 if loc_info[lid][0] == "city" else 1 for lid in all_locs]
    used_names: set[str] = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}

    # archetipi che tendono ad affiliarsi vs neutrali
    _AFFILIATE = {"discepolo": 0.85, "guardia": 0.85, "anziano": 0.6, "mercante": 0.3}

    for _ in range(count):
        lid = rng.choices(all_locs, weights=weights)[0]
        loc_type, owner_faction = loc_info[lid]
        archetype = pick_archetype(rng, loc_type)
        name = _unique_name(rng, used_names)
        traits = roll_traits(rng, archetype)
        desc = make_description(archetype, traits)

        faction_id = None
        if owner_faction is not None:
            if rng.random() < _AFFILIATE.get(archetype, 0.0):
                faction_id = owner_faction

        cur = conn.execute(
            "INSERT INTO npcs (name, location_id, status, description, archetype, "
            "faction_id, last_active_tick) VALUES (?, ?, 'alive', ?, ?, ?, 0);",
            (name, lid, desc, archetype, faction_id),
        )
        npc_id = cur.lastrowid
        conn.execute(
            "INSERT INTO npc_traits "
            "(npc_id, ambition, honor, greed, courage, loyalty, compassion, pride) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (npc_id, traits["ambition"], traits["honor"], traits["greed"],
             traits["courage"], traits["loyalty"], traits["compassion"], traits["pride"]),
        )
