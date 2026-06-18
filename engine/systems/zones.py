"""
Zone tematiche.

Alcune zone pericolose acquistano un'IDENTITÀ: invece di incontrare sempre gli stessi
archetipi, ogni zona è popolata da CLASSI diverse ma di forza equivalente (stesso rating,
distribuzione diversa). Una Valle delle Mille Lame brulica di Guerrieri Dao; un Mare
Spirituale di Maestri dell'Anima; una Catena delle Ossa Celesti di Cultivatori del Corpo.

Così il mondo non è piatto: due zone dello stesso rating offrono sfide completamente diverse.
"""

from __future__ import annotations

import random
import sqlite3

# tema -> (etichetta, prefisso-nome, pesi {classe/creatura: peso})
# classi: qi, corpo, anima, dao ; creature: beast, demon, spirit
THEMES = {
    "mille_lame": ("Dominio delle Mille Lame", "Valle",
                   {"dao": 0.6, "qi": 0.25, "beast": 0.15}),
    "mare_spirituale": ("Mare Spirituale", "Mare",
                        {"anima": 0.6, "spirit": 0.25, "demon": 0.15}),
    "ossa_celesti": ("Catena delle Ossa Celesti", "Catena",
                     {"corpo": 0.6, "beast": 0.25, "demon": 0.15}),
    "fornace_qi": ("Fornace del Qi", "Fornace",
                   {"qi": 0.6, "dao": 0.25, "beast": 0.15}),
}

_ARCHETYPE = {"qi": "coltivatore del qi", "corpo": "monaco del corpo",
              "anima": "maestro dell'anima", "dao": "guerriero dao"}


def assign_zone_themes(conn: sqlite3.Connection, rng: random.Random) -> int:
    """Assegna un tema a un pugno di zone pericolose (idempotente)."""
    if conn.execute("SELECT COUNT(*) c FROM zone_themes;").fetchone()["c"] > 0:
        return 0
    locs = conn.execute(
        "SELECT id, danger_level FROM locations WHERE danger_level>=3 "
        "ORDER BY danger_level DESC, id;").fetchall()
    if not locs:
        locs = conn.execute("SELECT id, danger_level FROM locations ORDER BY danger_level DESC, id LIMIT 4;").fetchall()
    themes = list(THEMES.keys())
    rng.shuffle(themes)
    n = 0
    for i, loc in enumerate(locs[:len(themes)]):
        theme = themes[i % len(themes)]
        rating = 200 + (loc["danger_level"] or 1) * 120
        conn.execute(
            "INSERT OR IGNORE INTO zone_themes (location_id, theme, rating, populated_tick) "
            "VALUES (?, ?, ?, -1);", (loc["id"], theme, rating))
        n += 1
    return n


def zone_of(conn: sqlite3.Connection, location_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM zone_themes WHERE location_id=?;",
                        (location_id,)).fetchone()


def theme_label(theme: str) -> str:
    return THEMES.get(theme, (theme, "", {}))[0]


def _rating_to_tier(rating: int) -> int:
    return max(1, min(8, 1 + rating // 150))


def _spawn_classed_npc(conn, rng, loc, klass, rating, tick) -> int:
    """Crea un NPC di una CLASSE, con regno/Dao/corpo/anima sbilanciati su quell'asse,
    puntando a un rating simile (distribuzione diversa)."""
    from engine.generators import npc_gen, dao_gen
    tier = _rating_to_tier(rating)
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    name = npc_gen._unique_name(rng, used)
    # i Guerrieri Dao hanno regno PIÙ BASSO ma Dao altissimo; i coltivatori Qi il contrario
    if klass == "dao":
        rtier = max(1, tier - 2)
    elif klass == "qi":
        rtier = min(8, tier + 1)
    else:
        rtier = tier
    realm_id = by_tier.get(rtier, by_tier.get(1))
    cur = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, kind, "
        "realm_id, last_active_tick) VALUES (?, ?, 'alive', ?, ?, 'human', ?, ?);",
        (name, loc, f"Un {_ARCHETYPE[klass]}.", _ARCHETYPE[klass], realm_id, tick))
    nid = cur.lastrowid
    stage = rng.randint(3, 9)
    body = soul = qi = tier * 6
    if klass == "corpo":
        body = tier * 14 + stage * 3
    elif klass == "anima":
        soul = tier * 14 + stage * 3
    elif klass == "qi":
        qi = tier * 16 + stage * 4
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, 0.3, ?, ?, ?, ?, ?);",
        (nid, realm_id, stage, qi, body, soul, tier * 6))
    # Dao sbilanciati per classe
    if klass == "dao":
        dao_gen._set_dao(conn, "npc", nid, rng.choice(["spada", "lancia", "sciabola"]),
                         70, rating + rng.randint(-40, 60), 1)
        dao_gen._set_dao(conn, "npc", nid, "anima", 50, rating // 4, 1)
    elif klass == "corpo":
        dao_gen._set_dao(conn, "npc", nid, "corpo", 70, rating // 2, 1)
    elif klass == "anima":
        dao_gen._set_dao(conn, "npc", nid, "anima", 70, rating // 2 + rating // 4, 1)
    else:  # qi: poco Dao
        dao_gen._set_dao(conn, "npc", nid, "spada", 50, rating // 6, 1)
    return nid


_ZONE_ELEMENT_POOL = ["fuoco", "acqua", "terra", "vento", "metallo", "legno",
                      "spada", "corpo", "fulmine", "anima", "luce", "oscurita"]


def _zone_element(conn, location_id) -> str:
    """Elemento affine della zona: quello della setta che vi caccia, o uno stabile per zona."""
    r = conn.execute(
        "SELECT element FROM factions WHERE hunt_zone_id=? AND element IS NOT NULL LIMIT 1;",
        (location_id,)).fetchone()
    if r and r["element"]:
        return r["element"]
    return _ZONE_ELEMENT_POOL[location_id % len(_ZONE_ELEMENT_POOL)]


ZONE_RESPAWN = 24    # tick (~1 giorno): dopo aver ripulito una zona, si ripopola nel tempo


def maybe_respawn(conn, rng, location_id, tick) -> int:
    """Ripopola una zona di caccia: la prima volta sempre, poi RIGENERA nel tempo se è
    stata ripulita (così puoi tornare a cacciare e accumulare punti per la setta)."""
    z = zone_of(conn, location_id)
    if not z:
        return 0
    here = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human';",
        (location_id,)).fetchone()["c"]
    last = z["populated_tick"] if z["populated_tick"] is not None else -1
    if last < 0:
        return populate_zone(conn, rng, location_id, tick)
    if here < 3 and (tick - last) >= ZONE_RESPAWN:
        return populate_zone(conn, rng, location_id, tick, force=True)
    return 0


def populate_zone(conn, rng, location_id, tick, force=False) -> int:
    """Popola una zona tematica con un mix di classi/creature al suo rating (se serve)."""
    z = zone_of(conn, location_id)
    if not z:
        return 0
    # non sovraffollare: ripopola solo se ci sono pochi abitanti 'a tema'
    here = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive';",
        (location_id,)).fetchone()["c"]
    if here >= 5 and not force:
        return 0
    weights = THEMES[z["theme"]][2]
    rating = z["rating"] or 300
    spawned = 0
    keys = list(weights.keys())
    wts = [weights[k] for k in keys]
    elem = _zone_element(conn, location_id)
    for _ in range(rng.randint(3, 5)):
        pick = rng.choices(keys, weights=wts, k=1)[0]
        if pick in ("beast", "demon", "spirit"):
            from engine.generators import creature_gen
            tier = _rating_to_tier(rating)
            nid = creature_gen._spawn_one(conn, rng, pick, location_id, max(1, tier - 1), tier)
        else:
            nid = _spawn_classed_npc(conn, rng, location_id, pick, rating, tick)
        # affinità di zona: la maggior parte degli abitanti porta il Dao della zona
        if elem and nid and rng.random() < 0.7:
            from engine.generators import dao_gen
            dao_gen.bias_dominant(conn, "npc", nid, elem, rng)
        spawned += 1
    conn.execute("UPDATE zone_themes SET populated_tick=? WHERE location_id=?;",
                 (tick, location_id))
    return spawned


def describe(conn, location_id) -> str | None:
    z = zone_of(conn, location_id)
    if not z:
        return None
    return (f"⟡ {theme_label(z['theme'])} — zona di rating ~{z['rating']}: "
            f"qui prosperano combattenti di stili diversi ma di pari forza.")
