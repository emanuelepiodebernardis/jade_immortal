"""
Generazione fazioni (Fase 4 — Step 6 della spec).

Crea le fazioni, assegna sede e territorio iniziale, genera un leader (NPC
archetipo 'patriarca') per ciascuna, e imposta le relazioni iniziali tra fazioni
(alcune alleate, alcune tese, alcune neutrali).
"""

from __future__ import annotations

import json
import random
import sqlite3

from engine.core import entities
from engine.generators import npc_gen

_PREFIX = ["Setta", "Clan", "Casata", "Ordine", "Palazzo", "Valle"]
_SUFFIX = ["della Spada di Giada", "del Loto Nero", "del Drago Cremisi",
           "della Nube Bianca", "del Gelo Eterno", "della Fiamma Vermiglia",
           "del Picco Celeste", "dell'Ombra Silente", "del Fiume Dorato",
           "della Montagna Sacra"]
_GOALS = ["expand", "dominate", "defend", "wealth", "ascend"]


def _faction_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(100):
        name = f"{rng.choice(_PREFIX)} {rng.choice(_SUFFIX)}"
        if name not in used:
            used.add(name)
            return name
    return f"{rng.choice(_PREFIX)} {rng.choice(_SUFFIX)} {rng.randint(2, 99)}"


def faction_relation_type(score: int) -> str:
    if score >= 40:
        return "ally"
    if score <= -40:
        return "enemy"
    if score <= -10:
        return "rival"
    return "neutral"


def generate_factions(conn: sqlite3.Connection, rng: random.Random,
                      count: int, all_locs: list[int]) -> list[int]:
    cities = [r["id"] for r in conn.execute(
        "SELECT id FROM locations WHERE location_type='city' ORDER BY id;")]
    rng.shuffle(cities)
    homes = cities[:count]
    if len(homes) < count:  # fallback: usa altre location
        extra = [l for l in all_locs if l not in homes]
        rng.shuffle(extra)
        homes += extra[: count - len(homes)]

    used_names: set[str] = set()
    used_npc_names: set[str] = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    faction_ids: list[int] = []

    for home in homes:
        name = _faction_name(rng, used_names)
        influence = rng.randint(35, 65)
        wealth = rng.randint(35, 65)
        goals = json.dumps(rng.sample(_GOALS, k=2))
        # tier/elemento da un RNG dedicato (NON tocca lo stream principale di world-gen,
        # così il posizionamento di NPC e il resto restano deterministici)
        aux = random.Random(home * 911 + 7)
        tier = aux.choices([1, 2, 3], weights=[4, 2, 1])[0]   # per lo più Regionali
        element = aux.choice(["corpo", "fulmine", "spada", "anima", None])
        cur = conn.execute(
            "INSERT INTO factions (name, home_location_id, influence, wealth, "
            "description, goals, tier, element, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active');",
            (name, home, influence, wealth,
             "Una potenza che contende il proprio posto nel mondo.", goals, tier, element),
        )
        fid = cur.lastrowid
        faction_ids.append(fid)

        # territorio: sede + (forse) una adiacente non rivendicata
        conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (fid, home))
        for ex in entities.get_exits_detailed(conn, home):
            if rng.random() < 0.5:
                owned = conn.execute(
                    "SELECT owner_faction_id FROM locations WHERE id=?;", (ex["dest_id"],)
                ).fetchone()["owner_faction_id"]
                if owned is None:
                    conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;",
                                 (fid, ex["dest_id"]))
                    break

        # leader
        traits = npc_gen.roll_traits(rng, "patriarca")
        lname = npc_gen._unique_name(rng, used_npc_names)
        ldesc = npc_gen.make_description("patriarca", traits)
        cur = conn.execute(
            "INSERT INTO npcs (name, location_id, status, description, archetype, "
            "faction_id, last_active_tick) VALUES (?, ?, 'alive', ?, 'patriarca', ?, 0);",
            (lname, home, ldesc, fid),
        )
        leader_id = cur.lastrowid
        conn.execute(
            "INSERT INTO npc_traits "
            "(npc_id, ambition, honor, greed, courage, loyalty, compassion, pride) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (leader_id, traits["ambition"], traits["honor"], traits["greed"],
             traits["courage"], traits["loyalty"], traits["compassion"], traits["pride"]),
        )
        conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (leader_id, fid))

    _generate_relations(conn, rng, faction_ids)
    return faction_ids


def _generate_relations(conn: sqlite3.Connection, rng: random.Random,
                        faction_ids: list[int]) -> None:
    for i in range(len(faction_ids)):
        for j in range(i + 1, len(faction_ids)):
            a, b = faction_ids[i], faction_ids[j]
            # mix: per lo più neutrale, qualche alleanza, qualche tensione
            bucket = rng.choices(
                ["conflict", "neutral", "ally"], weights=[3, 4, 2])[0]
            if bucket == "conflict":
                score = rng.randint(-80, -20)
                reason = "rivalità per territori e risorse"
            elif bucket == "ally":
                score = rng.randint(40, 80)
                reason = "patto di mutua difesa"
            else:
                score = rng.randint(-15, 25)
                reason = "rapporti formali"
            conn.execute(
                "INSERT OR IGNORE INTO faction_relations "
                "(faction_a, faction_b, relation_score, relation_type, reason, last_updated_tick) "
                "VALUES (?, ?, ?, ?, ?, 0);",
                (a, b, score, faction_relation_type(score), reason),
            )
