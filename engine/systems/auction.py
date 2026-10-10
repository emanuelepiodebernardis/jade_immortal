"""
CASA D'ASTE (拍卖会).

Ogni ~10 giorni una grande casa d'aste apre i battenti in una città per 2 giorni.
Mette all'incanto tesori adatti al tuo livello: metodi di coltivazione, semi di radici
spirituali, pillole rare, rotoli di tecniche, elisir di lunga vita, talismani.

  asta                      il catalogo (lotti, offerta corrente, chi rilancia)
  asta offri <lotto> <pietre>   fai un'offerta. Gli altri offerenti hanno un limite che
                            non conosci: se lo superi, il lotto è tuo e paghi il loro
                            limite più un rilancio (mai più di quanto hai offerto).
                            Altrimenti rilanciano: puoi offrire di nuovo.

Attenzione: chi vince un tesoro molto ambito all'asta a volte viene seguito fuori città…
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

INTERVAL_DAYS = 10
OPEN_DAYS = 2
_BIDDERS = ["il Giovane Maestro del Clan Mu", "una dama velata dal palco", "un vecchio mercante di Jiangnan",
            "l'inviato di una setta demoniaca", "un anziano dalle maniche larghe", "un ricco erede annoiato"]


def _lots(rng: random.Random, tier: int) -> list[dict]:
    from engine.systems import gongfa, spirit_roots
    pool = [
        lambda: {"name": "", "kind": "gongfa", "value": 300 * (tier + 1),
                 "eff": {"gongfa": gongfa.generate(rng, tier + 1)}},
        lambda: (lambda el: {"name": f"Seme della Radice di {spirit_roots.LABEL[el]}", "kind": "radice",
                             "value": 250 * tier, "eff": {"root_gain": {"element": el, "amount": 10 + 8 * tier}}})(
            rng.choice(spirit_roots.ELEMENTS)),
        lambda: {"name": f"Pillola della Marea Celeste ({tier}° grado)", "kind": "pillola", "value": 120 * tier,
                 "eff": {"item": {"name": "Pillola della Marea Celeste", "item_type": "pillola", "rarity": "raro",
                                  "desc": "Qi purissimo.", "effects": {"cultivation_progress": round(0.4 + 0.1 * tier, 2)}}}},
        lambda: {"name": f"Rotolo dell'Arte Perduta di {rng.choice(['Han', 'Qin', 'Wei', 'Lan', 'Su'])}",
                 "kind": "tecnica", "value": 400 * tier,
                 "eff": {"learn_technique": {"name": "Arte Perduta dell'Asta", "magnitude": round(0.06 + 0.02 * tier, 3),
                                             "tech_key": f"asta:{tier}:{rng.randint(1, 10 ** 6)}"}}},
        lambda: {"name": "Elisir dei Mille Autunni", "kind": "vita", "value": 350 * tier,
                 "eff": {"lifespan_years": 30 + 20 * tier}},
        lambda: {"name": "Pillola di Fondazione Celeste", "kind": "sfondamento", "value": 200 * tier,
                 "eff": {"item": {"name": "Pillola di Fondazione Celeste", "item_type": "pillola",
                                  "rarity": "raro", "desc": "Rende più sicuro lo sfondamento.",
                                  "effects": {"bt_bonus": 0.15}}}},
    ]
    out = []
    for f in rng.sample(pool, 4):
        lot = f()
        if lot["kind"] == "gongfa":
            lot["name"] = f"Metodo: {lot['eff']['gongfa']['name']}"
        lot["value"] = int(lot["value"] * rng.uniform(0.8, 1.2))
        lot["current"] = lot["value"] // 2
        lot["max"] = int(lot["value"] * rng.uniform(0.8, 1.7))
        lot["rival"] = rng.choice(_BIDDERS)
        lot["sold"] = None
        out.append(lot)
    return out


def current(conn) -> dict | None:
    a = state.get_json(conn, "auction")
    if not a or tick_mod.get_tick(conn) // 120 > a["end_day"]:
        return None
    return a


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.simulation import cultivation
    day = t // 120
    a = state.get_json(conn, "auction")
    if a and day > a["end_day"]:
        state.delete(conn, "auction")
        a = None
    if a is None and day - state.get_int(conn, "auction_day", -999) >= INTERVAL_DAYS and day >= 2:
        city = conn.execute("SELECT id, name FROM locations WHERE location_type='city' "
                            "ORDER BY RANDOM() LIMIT 1;").fetchone()
        if not city:
            return []
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        state.set_json(conn, "auction", {"loc": city["id"], "city": city["name"], "end_day": day + OPEN_DAYS,
                                         "lots": _lots(rng, tier)})
        state.set(conn, "auction_day", str(day))
        return [f"⚖ La Casa d'Aste del Padiglione di Giada apre a {city['name']} per {OPEN_DAYS} giorni ('asta')."]
    return []


def describe(conn, player) -> str:
    a = current(conn)
    if not a:
        return "Nessuna asta in corso. Il Padiglione di Giada apre a turno nelle città, ogni dieci giorni circa."
    lines = [f"⚖ CASA D'ASTE — a {a['city']}" + (" (sei qui)" if player.location_id == a["loc"] else "")]
    for i, l in enumerate(a["lots"], 1):
        if l["sold"]:
            lines.append(f"  [{i}] {l['name']} — aggiudicato a {l['sold']}")
        else:
            lines.append(f"  [{i}] {l['name']} — offerta corrente {l['current']} pietre ({l['rival']})")
    lines.append("Offri: 'asta offri <lotto> <pietre>'.")
    return "\n".join(lines)


def bid(conn, player, n: int, amount: int) -> str:
    from engine.systems import sects, items
    a = current(conn)
    if not a:
        return "Nessuna asta in corso."
    if player.location_id != a["loc"]:
        return f"L'asta si tiene a {a['city']}."
    if not (1 <= n <= len(a["lots"])):
        return describe(conn, player)
    lot = a["lots"][n - 1]
    if lot["sold"]:
        return "Quel lotto è già stato aggiudicato."
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    if amount > have:
        return f"Non puoi offrire più di quanto possiedi ({have} pietre)."
    step = max(10, lot["value"] // 20)
    if amount < lot["current"] + step:
        return f"Il rilancio minimo è {lot['current'] + step} pietre."
    if amount > lot["max"]:
        price = min(amount, lot["max"] + step)
        sects.grant_resource(conn, "pietre_spirituali", -price, player.id)
        lot["sold"] = "te"
        state.set_json(conn, "auction", a)
        t = tick_mod.get_tick(conn)
        lines = [f"Il banditore batte il martelletto: «Aggiudicato!» {lot['rival'].capitalize()} si morde il labbro. "
                 f"Paghi {price} pietre."]
        lines += items.apply_effects(conn, t, random.Random(t + n), player.id, lot["eff"]) \
            if "item" not in lot["eff"] and "lifespan_years" not in lot["eff"] else []
        if "item" in lot["eff"]:
            it = lot["eff"]["item"]
            iid = items.create_item(conn, it["name"], it["item_type"], it["rarity"], it["desc"], it["effects"])
            items.grant(conn, "player", player.id, iid)
            lines.append(f"Ottieni: {it['name']} (nello zaino).")
        if "lifespan_years" in lot["eff"]:
            from engine.systems import lifespan
            lifespan.add_bonus_years(conn, int(lot["eff"]["lifespan_years"]))
            lines.append(f"Bevi l'elisir: la tua vita si allunga di {lot['eff']['lifespan_years']} anni.")
        if price >= 600 and random.Random(t * 3 + n).random() < 0.4:
            state.set_json(conn, "auction_ambush", {"by": lot["rival"], "tier_offset": 0})
            lines.append("Mentre esci, senti uno sguardo sulla schiena…")
        return "\n".join(lines)
    lot["current"] = min(lot["max"], amount + step)
    state.set_json(conn, "auction", a)
    return f"{lot['rival'].capitalize()} rilancia subito: {lot['current']} pietre. Offri di più?"


def on_arrival(conn, player) -> str | None:
    """Chi ti ha visto vincere all'asta può tenderti un agguato fuori città."""
    from engine.systems import encounters, npc_factory
    amb = state.get_json(conn, "auction_ambush")
    if not amb or encounters.pending(conn):
        return None
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    if lt and lt["location_type"] == "city":
        return None
    state.delete(conn, "auction_ambush")
    rng = random.Random(tick_mod.get_tick(conn) + 77)
    sc = {"key": "agguato_asta", "title": "Agguato dopo l'asta", "event_type": "combat",
          "text": f"Uomini mascherati ti circondano. Dietro di loro, {{npc}}, mandato da {amb['by']}: "
                  "«Quel tesoro era nostro.»",
          "spawn": {"archetype": "vagabondo", "tier_offset": 0, "stage": 8, "traits": {"greed": 90}},
          "choices": [{"label": "Combatti", "effects": {}, "command": "attack {npc}"},
                      {"label": "Fuggi a rotta di collo", "check": {"stat": "istinto", "dc": 62},
                       "success": {"npc_leaves": True, "text": "Li semini tra gli alberi."},
                       "failure": {"injury": 3, "text": "Ti raggiungono: devi combattere ferito.",
                                   "command": "attack {npc}"}}]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    return encounters.start_scene(conn, player, sc)


def command(conn, player, arg: str) -> str:
    p = arg.split()
    if p and p[0].lower() in ("offri", "bid", "punta") and len(p) >= 3 and p[1].isdigit() and p[2].isdigit():
        return bid(conn, player, int(p[1]), int(p[2]))
    return describe(conn, player)
