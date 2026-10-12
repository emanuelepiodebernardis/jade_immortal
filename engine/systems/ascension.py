"""
ASCENSIONE AI MONDI SUPERIORI (飞升) — infiniti strati di mondo, ognuno col suo TETTO.

Ogni mondo regge solo fino a un certo regno: il Mondo Mortale fino al 9° (Superamento della
Tribolazione), ogni mondo superiore tre regni in più (12, 15, 18…). Nessuno, in quel mondo, può
andare oltre: né tu né chi ci vive. Arrivato alla GRANDE PERFEZIONE del regno più alto, lo
sfondamento non è più possibile: resta solo l'ASCENSIONE.

Ascendere è rinascere in un cielo più alto:
  · attraversi la Porta Celeste e diventi subito il primo regno del nuovo mondo
    (dal Mondo Mortale: Immortale di Giada);
  · NON puoi portare nulla del mondo inferiore: oggetti, pillole, materiali si dissolvono nel
    passaggio, e le pietre spirituali valgono un decimo (il Qi del cielo superiore è di un altro
    ordine). Restano tuoi solo ciò che è legato all'anima: arma, tecniche, Dao, bestia, legami;
  · il nuovo mondo ha sette più antiche, Qi più denso e coltivatori che ti superano.

  ascendi_mondo [conferma]  apri la Porta Celeste (prima ti dice cosa lascerai indietro)
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


def world_cap(layer: int) -> int:
    """Il regno più alto che un mondo può reggere (Mondo Mortale: 9; poi 12, 15, 18…)."""
    return 9 + 3 * layer


def cap_at(conn, location_id: int | None) -> int:
    return world_cap(layer_of_location(conn, location_id))


def clamp_tier(conn, location_id: int | None, tier: int) -> int:
    """Nessuno nasce, in un mondo, più forte di quanto quel mondo possa reggere."""
    return max(1, min(int(tier), cap_at(conn, location_id)))


def at_world_peak(conn, pid: int = 1) -> bool:
    from engine.simulation import cultivation
    p = entities.get_player(conn, pid)
    return (cultivation.realm_tier(conn, "player", pid) or 1) >= cap_at(conn, p.location_id)


def baggage(conn, pid: int = 1) -> dict:
    """Ciò che si perde salendo: oggetti, materiali e i nove decimi delle pietre."""
    from engine.systems import items, sects, professions
    inv = items.player_inventory(conn, pid)
    mats = {k: professions.material(conn, pid, k) for k in professions.MATERIALS}
    stones = sects.get_resource(conn, "pietre_spirituali", pid)
    return {"items": sum(r["quantity"] for r in inv), "names": [r["name"] for r in inv][:8],
            "mats": {k: v for k, v in mats.items() if v}, "stones": stones, "stones_after": stones // 10}


def _leave_behind(conn, pid: int = 1) -> list[str]:
    from engine.systems import sects, professions
    b = baggage(conn, pid)
    conn.execute("DELETE FROM inventories WHERE owner_type='player' AND owner_id=?;", (pid,))
    for k in professions.MATERIALS:
        sects.grant_resource(conn, k, -professions.material(conn, pid, k), pid)
    sects.grant_resource(conn, "pietre_spirituali", b["stones_after"] - b["stones"], pid)
    out = []
    if b["items"]:
        out.append(f"I {b['items']} oggetti del mondo inferiore si sfaldano come cenere nel passaggio.")
    if b["mats"]:
        out.append("Erbe, minerali e nuclei si dissolvono: la loro essenza qui non vale nulla.")
    if b["stones"]:
        out.append(f"Le tue {b['stones']} pietre spirituali, al cospetto del Qi superiore, ne valgono "
                   f"{b['stones_after']}.")
    from engine.systems import dominion
    out += dominion.leave_behind(conn, pid)
    return out


def describe_baggage(conn, pid: int = 1) -> str:
    b = baggage(conn, pid)
    lines = []
    if b["items"]:
        lines.append(f"  · {b['items']} oggetti dello zaino (" + ", ".join(b["names"]) +
                     ("…" if b["items"] > len(b["names"]) else "") + ")")
    if b["mats"]:
        lines.append("  · i materiali: " + ", ".join(f"{v} {k}" for k, v in b["mats"].items()))
    if b["stones"]:
        lines.append(f"  · le pietre: da {b['stones']} a {b['stones_after']}")
    return "\n".join(lines)


def layer_of_location(conn, location_id: int | None) -> int:
    if not location_id:
        return 0
    r = conn.execute("SELECT region_id FROM locations WHERE id=?;", (location_id,)).fetchone()
    if not r:
        return 0
    m = state.get_json(conn, REGIONS_KEY, {}) or {}
    return int(m.get(str(r["region_id"]), 0))


def player_layer(conn, pid: int = 1) -> int:
    r = conn.execute("SELECT location_id FROM players WHERE id=?;", (pid,)).fetchone()
    return layer_of_location(conn, r["location_id"] if r else None)


def faction_layer(conn, fid: int) -> int:
    r = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (fid,)).fetchone()
    return layer_of_location(conn, r["home_location_id"] if r else None)


def plane_locations(conn, layer: int) -> list[int]:
    m = {int(k): v for k, v in (state.get_json(conn, REGIONS_KEY, {}) or {}).items()}
    return [r["id"] for r in conn.execute("SELECT id, region_id FROM locations ORDER BY id;")
            if m.get(r["region_id"], 0) == layer]


def plane_faction_ids(conn, layer: int) -> set[int]:
    locs = set(plane_locations(conn, layer))
    return {r["id"] for r in conn.execute("SELECT id, home_location_id FROM factions WHERE status='active';")
            if r["home_location_id"] in locs}


def plane_range(layer: int) -> tuple[int, int]:
    """I regni di chi è nato in quel mondo: dal primo sopra il mondo inferiore al tetto."""
    return (1 if layer <= 0 else world_cap(layer - 1) + 1), world_cap(layer)


PLANE_SECTS = 4


def populate_plane(conn, rng: random.Random, layer: int, ptier: int) -> list[str]:
    """Riempie un mondo superiore: le sue sette (dalla più piccola alla più alta che quel mondo regga) e i
    suoi abitanti, tutti nati per QUEL mondo e in linea con la tua forza. Non tocca il Mondo Mortale."""
    if layer <= 0:
        return []
    from engine.systems import npc_factory
    from engine.generators import faction_gen
    locs = plane_locations(conn, layer)
    if not locs:
        return []
    lo, hi = plane_range(layer)
    t = tick_mod.get_tick(conn)
    out = []
    have = plane_faction_ids(conn, layer)
    lo_t, hi_t = world_cap(layer - 1) - 1, world_cap(layer) - 2      # livelli delle sette di questo mondo
    tiers = sorted(max(1, lo_t + round(i * (hi_t - lo_t) / max(1, PLANE_SECTS - 1))) for i in range(PLANE_SECTS))
    rows = {r["id"]: r for r in conn.execute("SELECT id, location_type, owner_faction_id FROM locations WHERE id IN (%s);"
                                             % ",".join("?" * len(locs)), locs)}
    homes = [l for l in locs if rows[l]["location_type"] == "city" and not rows[l]["owner_faction_id"]]
    homes += [l for l in locs if rows[l]["location_type"] in ("mountain", "ruin") and not rows[l]["owner_faction_id"]]
    wild = [l for l in locs if rows[l]["location_type"] != "city"] or locs
    used_f = {r["name"] for r in conn.execute("SELECT name FROM factions;")}
    new_names = []
    for tier in tiers[len(have):]:
        if not homes:
            break
        home = homes.pop(0)
        fname = faction_gen._faction_name(rng, used_f)
        used_f.add(fname)
        cur = conn.execute("INSERT INTO factions (name, home_location_id, influence, wealth, description, goals, tier, "
                           "element, status, alignment, hunt_zone_id) VALUES (?, ?, ?, ?, ?, '[]', ?, ?, 'active', ?, ?);",
                           (fname, home, 50 + 8 * tier, 50 + 8 * tier, f"Una setta del {layer_name(layer)}.", tier,
                            rng.choice(["spada", "fulmine", "anima", "corpo", "fuoco", "acqua", "spazio", "tempo", None]),
                            rng.choice(["ortodossa", "ortodossa", "eterodossa", "demoniaca"]), rng.choice(wild)))
        fid = cur.lastrowid
        conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (fid, home))
        top = min(hi, 2 + tier)
        lid = npc_factory.spawn(conn, rng, archetype="patriarca", location_id=home, tier=top, faction_id=fid, tick=t)
        conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (lid, fid))
        for _ in range(2):
            npc_factory.spawn(conn, rng, archetype="anziano", location_id=home, tier=max(lo, top - 1), faction_id=fid, tick=t)
        for _ in range(4):
            npc_factory.spawn(conn, rng, archetype=rng.choice(["discepolo", "guardia"]), location_id=home,
                              tier=max(lo, min(top - 1, ptier + rng.randint(-1, 1))), faction_id=fid, tick=t)
        new_names.append(f"{fname} ({tier})")
    # abitanti: se il mondo si è svuotato, ne nascono di nuovi, in linea con la tua forza
    alive = conn.execute("SELECT COUNT(*) c FROM npcs WHERE status='alive' AND location_id IN (%s);"
                         % ",".join("?" * len(locs)), locs).fetchone()["c"]
    target = 12 + 7 * len(plane_faction_ids(conn, layer))
    for _ in range(max(0, min(12, target - alive))):
        npc_factory.spawn(conn, rng, archetype=rng.choice(["vagabondo", "eremita", "mercante", "discepolo", "guardia"]),
                          location_id=rng.choice(locs), tier=max(lo, min(hi, ptier + rng.randint(-1, 1))), tick=t)
    # chi è rimasto indietro rispetto al proprio mondo (salvataggi vecchi) viene riportato al suo livello
    from engine.simulation import cultivation
    for r in conn.execute("SELECT id FROM npcs WHERE status='alive' AND location_id IN (%s);"
                          % ",".join("?" * len(locs)), locs).fetchall():
        if (cultivation.realm_tier(conn, "npc", r["id"]) or 1) < lo:
            rid = cultivation.ensure_realm(conn, lo)
            conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='npc' AND character_id=?;",
                         (rid, r["id"]))
            conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (rid, r["id"]))
    if new_names:
        out.append(f"Le sette del {layer_name(layer)}: " + ", ".join(new_names) + ". ('sette')")
    return out


def arrive(conn, player, layer: int) -> list[str]:
    """Arrivi in un mondo superiore: tutto, qui, è di questo mondo — anche le sette."""
    from engine.systems import sects, chronicle
    from engine.simulation import cultivation
    out = []
    m = sects.get_membership(conn, player.id)
    if m and faction_layer(conn, m["faction_id"]) < layer:
        conn.execute("DELETE FROM sect_memberships WHERE player_id=?;", (player.id,))
        conn.execute("UPDATE sect_invitations SET resolved=1 WHERE player_id=? AND resolved=0;", (player.id,))
        out.append(f"Il tuo posto in {m['sect_name']} resta nel mondo inferiore: qui nessuno sa chi eri. "
                   f"Le sette del {layer_name(layer)} ti osservano — cercane una ('sette').")
        chronicle.add(conn, "scelta", f"Lascia {m['sect_name']} nel mondo inferiore.")
    rng = random.Random(tick_mod.get_tick(conn) * 31 + layer)
    out += populate_plane(conn, rng, layer, cultivation.realm_tier(conn, "player", player.id) or 1)
    from engine.systems import race_realms
    if not state.get(conn, race_realms._key(layer)):
        out += race_realms.on_arrive(conn, player, layer)
    return out


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    """Nei mondi superiori, chi muore viene rimpiazzato da nuovi coltivatori di quel mondo."""
    layer = player_layer(conn, player.id)
    if layer <= 0 or (t // 120) % 5:
        return []
    from engine.simulation import cultivation
    populate_plane(conn, rng, layer, cultivation.realm_tier(conn, "player", player.id) or 1)
    return []


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
    cells = world_gen._carve_cluster(rng, 12)
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
    start = ids[(0, 0)]
    populate_plane(conn, rng, layer, ptier)
    return start


def ascend(conn, player, arg: str = "") -> str:
    from engine.simulation import cultivation, world_tick
    from engine.systems import encounters, reputation, lifespan
    from engine.generators.cultivation_gen import realm_name_for_tier
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    here = layer_of_location(conn, player.location_id)
    target = here + 1
    while world_cap(target) <= tier:          # mai in un mondo che non regge la tua coltivazione: si salta oltre
        target += 1
    cap = world_cap(here)
    rec = cultivation.get_record(conn, "player", player.id)
    perfect = tier > cap or (tier == cap and rec and (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM
                             and rec["progress"] >= 1.0)
    if tier < cap or not perfect:
        return (f"La Porta Celeste non si apre per te. Il {layer_name(here)} regge fino al regno "
                f"{cap} ({realm_name_for_tier(cap)}): raggiungine la GRANDE PERFEZIONE (strato 10, "
                f"esperienza piena), poi potrai ascendere.")
    if arg.strip().lower() not in ("conferma", "si", "sì", "ok"):
        bag = describe_baggage(conn, player.id)
        return (f"☁ Sei alla Grande Perfezione del {layer_name(here)}. Sopra di te, il {layer_name(target)}"
                f" (regge fino al regno {world_cap(target)}).\n"
                + (f"Ascendendo lascerai indietro tutto ciò che appartiene a questo mondo:\n{bag}\n"
                   "(Prima puoi usarli: 'use all', 'use essenze'.)\n" if bag else "")
                + "Resteranno tuoi l'arma, le tecniche, i Dao, la bestia e i legami.\n"
                "Scrivi 'ascendi_mondo conferma' quando sei pronto.")
    lost = _leave_behind(conn, player.id)
    rise = []
    if tier == cap and tier + 1 <= world_cap(target):   # la Porta stessa è lo sfondamento al regno successivo
        r = cultivation._breakthrough_success(conn, "player", player.id, tier, tick_mod.get_tick(conn),
                                              player.name, player.location_id, None, [])
        rise.append(f"Il Qi del cielo superiore ti attraversa: sei ora {realm_name_for_tier(tier + 1)}!")
    if target <= reached(conn):
        # strato già esistente: apri una nuova porta verso la sua città d'arrivo
        dest = state.get_json(conn, "world_layer_gates", {}).get(str(target))
        if dest:
            _link(conn, player.location_id, dest)
            entities.move_player(conn, player.id, dest)
            return "\n".join([f"Riapri la Porta Celeste e risali al {layer_name(target)}."] + lost + rise
                              + arrive(conn, entities.get_player(conn, player.id), target))
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
    plane = arrive(conn, entities.get_player(conn, player.id), target)
    return (f"✦ Il cielo si squarcia. Una scala di luce ti solleva oltre le nuvole, oltre le stelle… ✦\n"
            + "\n".join(lost + rise) + ("\n" if lost or rise else "") +
            f"Sei giunto nel {layer_name(target)}. Il Qi qui è così denso che respirarlo è già coltivare "
            f"(coltivazione ×{1 + 0.3 * target:.1f}). Qui, però, sei di nuovo uno tra tanti: questo mondo "
            f"regge fino al regno {world_cap(target)} ({realm_name_for_tier(world_cap(target))}).\n"
            f"La vita ti si allunga di {100 * target} anni. ✧ Nuovo titolo: «{title}» ✧\n"
            + ("\n".join(plane) + "\n" if plane else "")
            + "('down' per tornare indietro attraverso la porta)")


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
