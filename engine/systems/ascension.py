"""
ASCENSIONE AI MONDI SUPERIORI (飞升) — infiniti strati di mondo.

Questo mondo è solo il primo gradino. Dal 9° regno puoi aprire la PORTA CELESTE e
salire a un Mondo Superiore: un nuovo continente, generato al momento, con sette più
antiche, coltivatori del tuo livello e oltre, Qi più denso (si coltiva più in fretta).
Da lì, ogni 3 regni, un'altra porta: non c'è un ultimo mondo.

  ascendi_mondo       apri la Porta Celeste dal punto in cui ti trovi (regno ≥ 9, poi 12, 15…)
  mondi               gli strati di mondo che hai raggiunto
  up / down           attraversi le porte già aperte (su / giù)
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "world_layer"                  # sopravvive alla reincarnazione: il mondo resta
REGIONS_KEY = "world_layer_regions"  # {region_id: strato}
_LAYER_NAMES = ["Mondo Mortale", "Mondo Spirituale", "Mondo Immortale", "Mondo Celeste", "Mondo Divino",
                "Mondo Primordiale", "Mondo del Caos"]


def layer_name(n: int) -> str:
    if n < len(_LAYER_NAMES):
        return _LAYER_NAMES[n]
    return f"Mondo Oltre il Caos ({n - len(_LAYER_NAMES) + 1}° strato)"


def reached(conn) -> int:
    return state.get_int(conn, KEY, 0)


def required_tier(layer: int) -> int:
    return 9 + 3 * layer


def layer_of_location(conn, location_id: int | None) -> int:
    if not location_id:
        return 0
    r = conn.execute("SELECT region_id FROM locations WHERE id=?;", (location_id,)).fetchone()
    if not r:
        return 0
    m = state.get_json(conn, REGIONS_KEY, {}) or {}
    return int(m.get(str(r["region_id"]), 0))


def cultivation_mult(conn, location_id: int | None) -> tuple[float, str]:
    lay = layer_of_location(conn, location_id)
    if lay <= 0:
        return 1.0, ""
    return 1.0 + 0.3 * lay, f"il Qi denso del {layer_name(lay)}"


def _generate_layer(conn, rng: random.Random, layer: int, ptier: int) -> int:
    """Crea il nuovo continente: luoghi, sette, abitanti. Ritorna l'id della città d'arrivo."""
    from engine.generators import world_gen
    from engine.systems import npc_factory
    cur = conn.execute("INSERT INTO regions (world_id, name, region_type) VALUES (1, ?, 'continent');",
                       (layer_name(layer),))
    region = cur.lastrowid
    m = state.get_json(conn, REGIONS_KEY, {}) or {}
    m[str(region)] = layer
    state.set_json(conn, REGIONS_KEY, m)
    used = {r["name"].split(" ", 1)[-1] for r in conn.execute("SELECT name FROM locations;")}
    cells = world_gen._carve_cluster(rng, 8)
    ids: dict = {}
    for cell in sorted(cells):
        ltype = "city" if cell == (0, 0) else rng.choices(["city", "mountain", "ruin", "forbidden_zone"],
                                                         weights=[3, 3, 2, 2])[0]
        name = world_gen._location_name(rng, ltype, used)
        cur = conn.execute("INSERT INTO locations (region_id, name, location_type, danger_level, description) "
                           "VALUES (?, ?, ?, ?, ?);",
                           (region, name, ltype, min(10, 5 + layer + rng.randint(0, 2)),
                            world_gen._location_desc(ltype) + f" Il Qi del {layer_name(layer)} è denso come nebbia."))
        ids[cell] = cur.lastrowid
    for a, d, b in world_gen._edges_for_cluster(cells):
        conn.execute("INSERT OR IGNORE INTO location_connections (from_location_id, to_location_id, direction) "
                     "VALUES (?, ?, ?);", (ids[a], ids[b], d))
    locs = list(ids.values())
    start = ids[(0, 0)]
    # sette antiche del nuovo mondo
    from engine.generators import faction_gen
    used_f = {r["name"] for r in conn.execute("SELECT name FROM factions;")}
    cities = [l for l in locs if conn.execute("SELECT location_type FROM locations WHERE id=?;",
                                              (l,)).fetchone()["location_type"] == "city"]
    for home in (cities or [start])[:2]:
        fname = faction_gen._faction_name(rng, used_f)
        cur = conn.execute("INSERT INTO factions (name, home_location_id, influence, wealth, description, goals, "
                           "tier, element, status, alignment) VALUES (?, ?, ?, ?, ?, '[]', ?, ?, 'active', ?);",
                           (fname, home, 60 + 10 * layer, 60, f"Una setta antica del {layer_name(layer)}.",
                            3 + 2 * layer, rng.choice(["spada", "fulmine", "anima", "corpo", None]),
                            rng.choice(["ortodossa", "ortodossa", "eterodossa", "demoniaca"])))
        fid = cur.lastrowid
        conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (fid, home))
        lid = npc_factory.spawn(conn, rng, archetype="patriarca", location_id=home, tier=ptier + 2,
                                faction_id=fid, tick=tick_mod.get_tick(conn))
        conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (lid, fid))
        for _ in range(4):
            npc_factory.spawn(conn, rng, archetype=rng.choice(["discepolo", "anziano", "guardia"]),
                              location_id=home, tier=max(1, ptier + rng.randint(-1, 1)), faction_id=fid,
                              tick=tick_mod.get_tick(conn))
    for _ in range(8):
        npc_factory.spawn(conn, rng, archetype=rng.choice(["vagabondo", "eremita", "mercante", "discepolo"]),
                          location_id=rng.choice(locs), tier=max(1, ptier + rng.randint(-2, 1)),
                          tick=tick_mod.get_tick(conn))
    return start


def ascend(conn, player) -> str:
    from engine.simulation import cultivation, world_tick
    from engine.systems import encounters, reputation, lifespan
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    here = layer_of_location(conn, player.location_id)
    target = here + 1
    if "up" in entities.get_exits(conn, player.location_id):
        return "Qui la Porta Celeste è già aperta: 'up' per attraversarla."
    if tier < required_tier(here):
        return (f"La Porta Celeste non si apre per te: per lasciare il {layer_name(here)} serve "
                f"almeno il regno {required_tier(here)}.")
    if target <= reached(conn):
        # strato già esistente: apri una nuova porta verso la sua città d'arrivo
        dest = state.get_json(conn, "world_layer_gates", {}).get(str(target))
        if dest:
            _link(conn, player.location_id, dest)
            entities.move_player(conn, player.id, dest)
            return f"Riapri la Porta Celeste e risali al {layer_name(target)}."
    rng = random.Random(tick_mod.get_tick(conn) * 997 + target)
    dest = _generate_layer(conn, rng, target, tier)
    _link(conn, player.location_id, dest)
    gates = state.get_json(conn, "world_layer_gates", {}) or {}
    gates[str(target)] = dest
    state.set_json(conn, "world_layer_gates", gates)
    state.set(conn, KEY, str(max(reached(conn), target)))
    entities.move_player(conn, player.id, dest)
    reputation.adjust(conn, player.id, fame=50)
    lifespan.add_bonus_years(conn, 100 * target)
    world_tick.advance(conn, 120)
    title = f"Asceso al {layer_name(target)}"
    state.grant_title(conn, title)
    return (f"✦ Il cielo si squarcia. Una scala di luce ti solleva oltre le nuvole, oltre le stelle… ✦\n"
            f"Sei giunto nel {layer_name(target)}. Il Qi qui è così denso che respirarlo è già coltivare "
            f"(coltivazione ×{1 + 0.3 * target:.1f}). Qui, però, sei di nuovo uno tra tanti.\n"
            f"La vita ti si allunga di {100 * target} anni. ✧ Nuovo titolo: «{title}» ✧\n"
            "('down' per tornare indietro attraverso la porta)")


def _link(conn, a: int, b: int) -> None:
    conn.execute("INSERT OR REPLACE INTO location_connections (from_location_id, to_location_id, direction) "
                 "VALUES (?, ?, 'up');", (a, b))
    conn.execute("INSERT OR REPLACE INTO location_connections (from_location_id, to_location_id, direction) "
                 "VALUES (?, ?, 'down');", (b, a))


def describe(conn, player) -> str:
    n = reached(conn)
    here = layer_of_location(conn, player.location_id)
    lines = [f"Sei nel {layer_name(here)}."]
    for i in range(n + 1):
        lines.append(f"  {'◆' if i == here else '◇'} {layer_name(i)}")
    lines.append(f"Prossima Porta Celeste: regno {required_tier(here)} ('ascendi_mondo').")
    return "\n".join(lines)
