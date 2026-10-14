"""
LA FRONTIERA — la mappa di ogni mondo si allarga man mano che sali.

Ogni mondo comincia piccolo: il cuore abitato dove arrivi. Ogni volta che la tua coltivazione
supera una soglia, si apre un nuovo ANELLO di terre più lontane:
  · nemici più forti (bestie, demoni, spiriti e coltivatori del regno di quell'anello);
  · bottini più rari (chi cade lì lascia oggetti di qualità più alta);
  · più risorse (raccogliere rende di più a ogni anello);
  · INCONTRI MISTERIOSI: tombe antiche, sorgenti spirituali, eremiti, rovine di sette perdute,
    alberi dai frutti spirituali, frammenti di reami — ognuno si apre una volta sola.
Al tetto del mondo (la Grande Perfezione del suo regno più alto) la mappa è completa.
Quando ascendi, quel mondo scompare dalla mappa e ne comincia uno nuovo, piccolo, che si
allarga con le stesse regole — senza fine.

Gli anelli di un mondo sono max(6, numero dei suoi regni): nel Mondo Mortale (9 regni) uno a
regno; nei mondi superiori (3 regni) uno ogni mezzo regno.

  frontiera        a che punto è la mappa di questo mondo, e quando si apre il prossimo anello
"""

from __future__ import annotations

import math
import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "frontier"              # {layer: {"rings": n, "loc_ring": {loc: ring}, "mysteries": {loc: {...}}}}
COORDS = "map_coords"         # {loc_id: [x, y]}  (nord = y-1, come la mappa)
D = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}

MYSTERIES = {
    "tomba": ("Tomba Antica", "Una porta di pietra senza maniglia, coperta di sigilli sbiaditi."),
    "sorgente": ("Sorgente Spirituale", "Acqua che sale invece di scendere, e fuma di Qi."),
    "eremita": ("Eremita Misterioso", "Un vecchio pesca in uno stagno dove non ci sono pesci."),
    "setta_perduta": ("Rovine di una Setta Perduta", "Padiglioni crollati, e una biblioteca ancora asciutta."),
    "albero": ("Albero dei Frutti Spirituali", "Un albero solo, e frutti che brillano come lanterne."),
    "frammento": ("Frammento di Reame", "Uno squarcio nell'aria da cui soffia il vento di un altro mondo."),
    "campo": ("Antico Campo di Battaglia", "Armi conficcate a migliaia, e lo spirito di una guerra che non è finita."),
}


def _get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def world(conn, layer: int) -> dict:
    d = _get(conn)
    w = d.get(str(layer)) or {"rings": 0, "loc_ring": {}, "mysteries": {}}
    return w


def _put_world(conn, layer: int, w: dict) -> None:
    d = _get(conn)
    d[str(layer)] = w
    _save(conn, d)


def ring_count(layer: int) -> int:
    from engine.systems import ascension
    lo, hi = ascension.plane_range(layer)
    return max(6, hi - lo + 1)


def _level(tier: int, stage: int) -> int:
    return (tier - 1) * 10 + stage


def unlocked_rings(conn, layer: int, pid: int = 1) -> int:
    """Quanti anelli spettano al giocatore, in questo mondo, per la sua coltivazione."""
    from engine.simulation import cultivation
    from engine.systems import ascension
    lo, hi = ascension.plane_range(layer)
    t = cultivation.realm_tier(conn, "player", pid) or 1
    st = cultivation.stage_of(conn, "player", pid) or 1
    a, b = _level(lo, 1), _level(hi, 1)
    frac = (_level(t, st) - a) / max(1, b - a)
    r = ring_count(layer)
    return max(0, min(r, int(math.floor(frac * r + 1e-9))))


def next_ring_at(layer: int, ring: int) -> tuple[int, int]:
    """(regno, strato) a cui si apre l'anello `ring` (1..R)."""
    from engine.systems import ascension
    lo, hi = ascension.plane_range(layer)
    a, b = _level(lo, 1), _level(hi, 1)
    lvl = a + math.ceil(ring / ring_count(layer) * (b - a))
    return (lvl - 1) // 10 + 1, (lvl - 1) % 10 + 1


def ring_tier(layer: int, ring: int) -> int:
    t, _st = next_ring_at(layer, max(1, ring))
    return t


# ---------------------------------------------------------------- coordinate della mappa

def coords(conn) -> dict[int, tuple[int, int]]:
    return {int(k): tuple(v) for k, v in (state.get_json(conn, COORDS, None) or {}).items()}


def _origin(conn, layer: int) -> int | None:
    from engine.systems import ascension
    if layer > 0:
        g = (state.get_json(conn, "world_layer_gates", {}) or {}).get(str(layer))
        if g:
            return int(g)
    locs = ascension.plane_locations(conn, layer)
    if not locs:
        return None
    r = conn.execute("SELECT id FROM locations WHERE id IN (%s) AND location_type='city' ORDER BY danger_level, id LIMIT 1;"
                     % ",".join("?" * len(locs)), locs).fetchone()
    return r["id"] if r else locs[0]


def ensure_coords(conn, layer: int) -> dict[int, tuple[int, int]]:
    """Coordinate di griglia per ogni luogo del mondo (calcolate una volta, poi fisse)."""
    from engine.systems import ascension
    allc = coords(conn)
    locs = set(ascension.plane_locations(conn, layer))
    if locs and locs <= set(allc):
        return {k: v for k, v in allc.items() if k in locs}
    start = _origin(conn, layer)
    if start is None:
        return {}
    taken = {v for k, v in allc.items() if k in locs}
    if start not in allc:
        allc[start] = (0, 0)
        taken.add((0, 0))
    from collections import deque
    q = deque([l for l in locs if l in allc])
    while q:
        cur = q.popleft()
        x, y = allc[cur]
        for d, nxt in entities.get_exits(conn, cur).items():
            if d not in D or nxt in allc or nxt not in locs:
                continue
            c = (x + D[d][0], y + D[d][1])
            if c in taken:
                continue
            allc[nxt] = c
            taken.add(c)
            q.append(nxt)
    # luoghi isolati (vecchi salvataggi): accanto a qualcosa, dove c'è posto
    for l in locs:
        if l in allc:
            continue
        for k in list(allc):
            if k not in locs:
                continue
            x, y = allc[k]
            spot = next(((x + dx, y + dy) for dx, dy in D.values() if (x + dx, y + dy) not in taken), None)
            if spot:
                allc[l] = spot
                taken.add(spot)
                break
    state.set_json(conn, COORDS, {str(k): list(v) for k, v in allc.items()})
    return {k: v for k, v in allc.items() if k in locs}


# ---------------------------------------------------------------- espansione

def _ring_size(ring: int) -> int:
    return min(10, 4 + ring)


# forme dei luoghi con il genere (m, f, fp) e nomi già con l'articolo: niente errori di grammatica
_FORMS = {
    "city": [("Borgo", "m"), ("Città", "f"), ("Avamposto", "m"), ("Villaggio", "m"), ("Porto", "m"), ("Fortezza", "f")],
    "mountain": [("Picco", "m"), ("Monte", "m"), ("Cresta", "f"), ("Valle", "f"), ("Gola", "f"), ("Altopiano", "m"),
                 ("Cascata", "f"), ("Foresta", "f")],
    "ruin": [("Rovine", "fp"), ("Tempio", "m"), ("Mausoleo", "m"), ("Torre", "f"), ("Santuario", "m"), ("Necropoli", "f")],
    "forbidden_zone": [("Abisso", "m"), ("Landa", "f"), ("Palude", "f"), ("Deserto", "m"), ("Selva", "f"), ("Voragine", "f")],
}
_OF = ["della Giada", "delle Nubi", "del Drago", "del Loto", "della Cenere", "del Ferro", "della Bruma", "del Vento",
       "del Gelo", "dell'Aurora", "della Luna", "dei Pini", "della Fenice", "della Tigre", "delle Gru", "del Serpente",
       "del Tuono", "dell'Ombra", "delle Stelle", "del Sole", "delle Ossa", "delle Lacrime", "del Sale", "della Brina",
       "dell'Ambra", "dei Salici", "del Bambù", "dei Cipressi", "delle Orchidee", "delle Peonie", "della Spada",
       "della Lancia", "della Campana", "dello Specchio", "delle Lanterne", "dell'Incenso", "dell'Inchiostro",
       "della Seta", "delle Perle", "dell'Ossidiana", "dei Mille Anni", "dei Nove Draghi", "delle Sette Stelle",
       "dei Cento Fiori", "dei Tre Soli", "del Vento Nero", "della Nebbia Rossa", "dell'Eremita", "dei Re Caduti"]
_ADJ = [("Eterno", "Eterna", "Eterne"), ("Antico", "Antica", "Antiche"), ("Silenzioso", "Silenziosa", "Silenziose"),
        ("Velato", "Velata", "Velate"), ("Ardente", "Ardente", "Ardenti"), ("Gelido", "Gelida", "Gelide"),
        ("Infranto", "Infranta", "Infrante"), ("Celeste", "Celeste", "Celesti"), ("Oscuro", "Oscura", "Oscure"),
        ("Sacro", "Sacra", "Sacre"), ("Dimenticato", "Dimenticata", "Dimenticate"), ("Sospeso", "Sospesa", "Sospese"),
        ("Cremisi", "Cremisi", "Cremisi"), ("Proibito", "Proibita", "Proibite"), ("Sepolto", "Sepolta", "Sepolte")]


def _frontier_name(rng, ltype: str, used: set[str]) -> str:
    for _ in range(80):
        form, g = rng.choice(_FORMS[ltype])
        adj = rng.choice(_ADJ)[{"m": 0, "f": 1, "fp": 2}[g]] + " " if rng.random() < 0.4 else ""
        name = f"{form} {adj}{rng.choice(_OF)}"
        if name not in used:
            used.add(name)
            return name
    from engine.systems import names
    return names.place(rng, f"{rng.choice(_FORMS[ltype])[0]} {rng.choice(_OF)}", used)


def _new_location(conn, rng, region: int, layer: int, ring: int, used: set[str]) -> int:
    from engine.generators import world_gen
    w = {"city": max(1, 3 - ring // 3), "mountain": 3, "ruin": 2 + ring // 3, "forbidden_zone": 1 + ring // 2}
    ltype = rng.choices(list(w), weights=list(w.values()))[0]
    name = _frontier_name(rng, ltype, used)
    danger = min(10, 1 + ring + layer + rng.randint(0, 1))
    desc = world_gen._location_desc(ltype) + f" Terre di frontiera (anello {ring}): qui nessuno ti conosce."
    cur = conn.execute("INSERT INTO locations (region_id, name, location_type, danger_level, description) "
                       "VALUES (?, ?, ?, ?, ?);", (region, name, ltype, danger, desc))
    return cur.lastrowid


def _populate(conn, rng, loc: int, ltype: str, tier: int) -> None:
    from engine.generators import creature_gen
    from engine.systems import npc_factory
    t = tick_mod.get_tick(conn)
    if ltype != "city":
        for _ in range(rng.randint(1, 3)):
            kind = rng.choice(["beast", "beast", "demon", "spirit"])
            nid = creature_gen._spawn_one(conn, rng, kind, loc, tier, tier + 1)
            _fit_fauna(conn, rng, nid, tier)
    for _ in range(rng.randint(0, 2) + (2 if ltype == "city" else 0)):
        npc_factory.spawn(conn, rng, archetype=rng.choice(["vagabondo", "eremita", "mercante", "guardia", "discepolo"]),
                          location_id=loc, tier=tier, tick=t)


def expand(conn, player, layer: int | None = None) -> list[str]:
    """Apre gli anelli che spettano al giocatore. Ritorna i messaggi (vuoto se nulla cambia)."""
    from engine.systems import ascension
    if player is None:
        return []
    layer = ascension.player_layer(conn, player.id) if layer is None else layer
    w = world(conn, layer)
    want = unlocked_rings(conn, layer, player.id)
    if want <= w["rings"]:
        return []
    allc = coords(conn)
    cmap = ensure_coords(conn, layer)
    allc.update(cmap)
    taken_all = set(cmap.values())          # le coordinate di QUESTO mondo (gli altri sono altrove)
    region = conn.execute("SELECT region_id FROM locations WHERE id=?;", (next(iter(cmap)),)).fetchone()["region_id"]
    used = {r["name"] for r in conn.execute("SELECT name FROM locations;")}
    out = []
    rng = random.Random(tick_mod.get_tick(conn) * 131 + layer * 7 + want)
    from engine.systems import ascension as asc
    lo, hi = asc.plane_range(layer)
    while w["rings"] < want:
        ring = w["rings"] + 1
        tier = max(lo, min(hi, ring_tier(layer, ring)))
        created = []
        for _ in range(_ring_size(ring)):
            # crescita concentrica: la cella libera più vicina al centro, attaccata al mondo (anelli, non serpenti)
            mine = {l: c for l, c in allc.items() if l in cmap or str(l) in w["loc_ring"]}
            cands = {}
            for l, (x, y) in mine.items():
                for d, (dx, dy) in D.items():
                    c = (x + dx, y + dy)
                    if c not in taken_all and c not in cands:
                        cands[c] = (l, d)
            if not cands:
                break
            cell = min(cands, key=lambda c: max(abs(c[0]), abs(c[1])) + 0.35 * (abs(c[0]) + abs(c[1])) / 2
                       + rng.random() * 0.9)
            spot = (cands[cell][0], (cands[cell][1], cell))
            parent, (d, cell) = spot
            nid = _new_location(conn, rng, region, layer, ring, used)
            allc[nid] = cell
            cmap[nid] = cell
            taken_all.add(cell)
            # collegamenti con tutti i vicini già esistenti dello stesso mondo
            for dd, (dx, dy) in D.items():
                nb = next((k for k, c in cmap.items() if c == (cell[0] + dx, cell[1] + dy)), None)
                if nb is not None and nb != nid:
                    conn.execute("INSERT OR IGNORE INTO location_connections (from_location_id, to_location_id, direction) "
                                 "VALUES (?, ?, ?);", (nid, nb, dd))
                    conn.execute("INSERT OR IGNORE INTO location_connections (from_location_id, to_location_id, direction) "
                                 "VALUES (?, ?, ?);", (nb, nid, OPP[dd]))
            w["loc_ring"][str(nid)] = ring
            ltype = conn.execute("SELECT location_type FROM locations WHERE id=?;", (nid,)).fetchone()["location_type"]
            _populate(conn, rng, nid, ltype, tier)
            created.append(nid)
        # incontri misteriosi
        for nid in rng.sample(created, min(len(created), 1 + ring // 3)):
            kind = rng.choice(list(MYSTERIES))
            w["mysteries"][str(nid)] = {"kind": kind, "ring": ring, "done": False}
        w["rings"] = ring
        names = [conn.execute("SELECT name FROM locations WHERE id=?;", (n,)).fetchone()["name"] for n in created[:4]]
        out.append(f"🗺 La frontiera si allarga (anello {ring}/{ring_count(layer)}): {len(created)} nuove terre — "
                   + ", ".join(names) + ("…" if len(created) > 4 else "")
                   + f". Nemici del regno {tier}, bottini più rari, risorse più ricche"
                   + (" e qualcosa di misterioso." if any(str(n) in w["mysteries"] for n in created) else "."))
    state.set_json(conn, COORDS, {str(k): list(v) for k, v in allc.items()})
    _put_world(conn, layer, w)
    if len(out) > 1:                                  # più anelli in un colpo: una riga sola
        rings = [int(x.split("anello ")[1].split("/")[0]) for x in out]
        n = sum(int(x.split("): ")[1].split(" ")[0]) for x in out)
        out = [f"🗺 La frontiera si allarga di {len(out)} anelli (fino al {max(rings)}/{ring_count(layer)}): {n} nuove "
               f"terre: più ci si allontana, più i nemici sono forti e i bottini rari; alcuni luoghi nascondono misteri."]
    if w["rings"] >= ring_count(layer):
        out.append(f"🗺 Hai la mappa completa del {asc.layer_name(layer)}. Oltre, c'è solo il cielo.")
    return out


# ---------------------------------------------------------------- effetti degli anelli

def ring_of(conn, location_id: int | None) -> int:
    if not location_id:
        return 0
    from engine.systems import ascension
    w = world(conn, ascension.layer_of_location(conn, location_id))
    return int(w["loc_ring"].get(str(location_id), 0))


def gather_mult(conn, location_id: int | None) -> float:
    return 1.0 + 0.35 * ring_of(conn, location_id)


def loot_bonus(conn, location_id: int | None) -> int:
    """Classi di qualità in più per il bottino caduto in un anello lontano."""
    return ring_of(conn, location_id) // 2


# ---------------------------------------------------------------- incontri misteriosi

def mystery_here(conn, player) -> dict | None:
    from engine.systems import ascension
    w = world(conn, ascension.layer_of_location(conn, player.location_id))
    m = w["mysteries"].get(str(player.location_id))
    return m if m and not m["done"] else None


def repopulate(conn, loc: int) -> int:
    """Le terre di frontiera si ripopolano col tempo (Agg. 55): dopo che le hai ripulite, in qualche
    giorno tornano creature del loro anello. Prima restavano vuote e si cacciavano solo prede facili."""
    from engine.systems import ascension, calibration
    ring = ring_of(conn, loc)
    if not ring:
        return 0
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (loc,)).fetchone()
    if not lt or lt["location_type"] == "city":
        return 0
    alive = conn.execute("SELECT COUNT(*) n FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human';",
                         (loc,)).fetchone()["n"]
    if alive >= 2:
        return 0
    day = tick_mod.get_tick(conn) // 120
    marks = state.get_json(conn, "frontier_respawn", {}) or {}
    if day - int(marks.get(str(loc), -999)) < calibration.FRONTIER_RESPAWN_DAYS:
        return 0
    marks[str(loc)] = day
    state.set_json(conn, "frontier_respawn", marks)
    from engine.generators import creature_gen
    tier = ring_tier(ascension.layer_of_location(conn, loc), ring)
    rng = random.Random(day * 131 + loc)
    n = rng.randint(2, 3)
    for _ in range(n):
        nid = creature_gen._spawn_one(conn, rng, rng.choice(["beast", "beast", "demon", "spirit"]), loc, tier, tier + 1)
        _fit_fauna(conn, rng, nid, tier)
    return n


def _fit_fauna(conn, rng, nid: int, ring_t: int) -> None:
    """Le creature delle terre del TUO livello restano una sfida: forza tra FAUNA_BAND della tua
    (le terre più vicine, sotto il tuo livello, restano facili: lì si caccia per raccogliere)."""
    from engine.systems import calibration, pursuers
    from engine.simulation import cultivation
    pt = cultivation.realm_tier(conn, "player", 1) or 1
    if ring_t < pt - 1:
        return
    lo, hi = calibration.FAUNA_BAND
    try:
        pursuers.fit(conn, 1, nid, "fauna", target=rng.uniform(lo, hi))
    except Exception:  # noqa: BLE001
        pass


def on_arrival(conn, player) -> str | None:
    from engine.systems import encounters
    repopulate(conn, player.location_id)
    m = mystery_here(conn, player)
    if not m or encounters.pending(conn):
        return None
    return encounters.start_scene(conn, player, mystery_scene(conn, player, m))


def mystery_scene(conn, player, m: dict) -> dict:
    name, txt = MYSTERIES[m["kind"]]
    r = m["ring"]
    return {"key": f"mistero_{m['kind']}", "title": f"❖ {name}", "event_type": "story", "ctx": {}, "sticky": True,
            "text": txt + " Senti che qui c'è qualcosa che aspetta da molto tempo.",
            "choices": [{"label": "Esplori fino in fondo", "effects": {}, "command": "mistero esplora"},
                        {"label": "Lo osservi con prudenza, prendendo solo ciò che è sicuro", "effects": {},
                         "command": "mistero prudente"},
                        {"label": "Te ne vai: tornerai più forte", "effects": {"text": "Lo lasci com'è. Ti aspetterà."}}]}


def resolve(conn, player, arg: str) -> str:
    """Il premio dell'incontro misterioso: esplorare rende di più, ma può svegliare un guardiano."""
    from engine.systems import ascension, items, sects, encounters
    layer = ascension.layer_of_location(conn, player.location_id)
    w = world(conn, layer)
    m = w["mysteries"].get(str(player.location_id))
    if not m or m["done"]:
        return "Qui non c'è nessun mistero da sciogliere (o l'hai già sciolto)."
    bold = not (arg or "").lower().startswith("prud")
    r = m["ring"]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 17 + player.location_id)
    m["done"] = True
    _put_world(conn, layer, w)
    name = MYSTERIES[m["kind"]][0]
    mult = (1.6 if bold else 1.0) * (1 + 0.5 * r) * (1 + layer)
    out = [f"❖ {name}:"]
    kind = m["kind"]
    if kind in ("sorgente", "albero"):
        out += items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": round(0.15 * mult, 2)})
        if kind == "albero":
            from engine.systems import lifespan
            yrs = int(5 * mult)
            lifespan.add_bonus_years(conn, yrs)
            out.append(f"Un frutto spirituale: la tua vita si allunga di {yrs} anni.")
    elif kind in ("tomba", "setta_perduta", "campo"):
        out += items.apply_effects(conn, t, rng, player.id, {"dao_key": _best_dao(conn, player.id),
                                                             "dao_gain": int(4 * mult)})
        st = int(60 * mult * max(1, ring_tier(layer, r)))
        sects.grant_resource(conn, "pietre_spirituali", st, player.id)
        out.append(f"Tra la polvere: {st} pietre spirituali.")
    elif kind == "eremita":
        d = state.get_json(conn, "system_daily", None) or {}
        d["bonus_points"] = d.get("bonus_points", 0) + (2 if bold else 1)
        state.set_json(conn, "system_daily", d)
        out.append(f"L'eremita ti tocca la fronte: «Hai fretta. Bene.» +{2 if bold else 1} punti attributo.")
        out += items.apply_effects(conn, t, rng, player.id, {"aff_cultivation": 1}) if bold else []
    elif kind == "frammento":
        out += items.apply_effects(conn, t, rng, player.id, {"dao_key": rng.choice(["spazio", "tempo", "destino"]),
                                                             "dao_gain": int(3 * mult)})
    if bold and rng.random() < 0.45:
        from engine.systems import npc_factory, pursuers
        gid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=player.location_id,
                                tier=max(1, ring_tier(layer, r)), tick=t,
                                traits={"pride": 90, "courage": 95, "loyalty": 100})
        gname = f"Guardiano {conn.execute('SELECT name FROM npcs WHERE id=?;', (gid,)).fetchone()['name'].split()[-1]}"
        conn.execute("UPDATE npcs SET name=? WHERE id=?;", (gname, gid))
        pursuers.fit(conn, player.id, gid, "campione", target=1.1)
        out.append(f"⚠ Il tuo frugare sveglia il {gname}: «Chi osa?» — affrontalo ('duello {gname.split()[0]}') "
                   "o fuggi.")
    from engine.systems import chronicle
    chronicle.add(conn, "impresa", f"Scioglie il mistero: {name} (anello {r}).")
    return "\n".join(out)


def _best_dao(conn, pid: int) -> str:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
                     "ORDER BY comprehension DESC LIMIT 1;", (pid,)).fetchone()
    return r["dao_key"] if r else "corpo"


def describe(conn, player) -> str:
    from engine.systems import ascension
    layer = ascension.player_layer(conn, player.id)
    w = world(conn, layer)
    R = ring_count(layer)
    lines = [f"🗺 FRONTIERA del {ascension.layer_name(layer)}: anelli aperti {w['rings']}/{R}"]
    if w["rings"] < R:
        t, st = next_ring_at(layer, w["rings"] + 1)
        lines.append(f"  Il prossimo anello si apre al regno {t}, strato {st}.")
    else:
        lines.append("  La mappa di questo mondo è completa.")
    open_m = [(int(k), v) for k, v in w["mysteries"].items() if not v["done"]]
    for lid, v in open_m[:8]:
        nm = conn.execute("SELECT name FROM locations WHERE id=?;", (lid,)).fetchone()
        lines.append(f"  ❖ {MYSTERIES[v['kind']][0]} — a {nm['name'] if nm else '?'} (anello {v['ring']})")
    return "\n".join(lines)
