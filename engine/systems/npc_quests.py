"""
INCARICHI A CATENA — le richieste delle persone che incontri.

Molti NPC hanno qualcosa da chiederti. Un incarico riuscito ne apre un altro, più grande:
una CATENA (3-5 passi) che finisce con un grande dono — una tecnica, un compagno, un
tesoro — e cambia per sempre il vostro rapporto.

Tipi di incarico:
  vendetta     abbatti chi ha fatto un torto al committente (lo trovi in un luogo vicino)
  scorta       accompagna il committente fino a un luogo (ti segue mentre viaggi)
  recupero     recupera un oggetto in un luogo selvaggio, sorvegliato da un guardiano
  guarigione   porta erbe spirituali o una pillola curativa al committente ('consegna')
  consegna     porta un messaggio a qualcuno in un'altra città

  richieste           chi, qui, ha un incarico per te
  incarico <n>        accetti la richiesta n (al massimo 3 incarichi insieme)
  incarichi           i tuoi incarichi in corso e dove andare
  consegna            consegni erbe/pillole per un incarico di guarigione
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "npc_quests"
MAX_ACTIVE = 3
_TYPES = ["vendetta", "scorta", "recupero", "guarigione", "consegna"]
_INTRO = {
    "vendetta": "«{target} mi ha rovinato. Fagli pagare il conto: lo trovi a {dest}.»",
    "scorta": "«Devo arrivare a {dest} vivo. Le strade non sono sicure: accompagnami.»",
    "recupero": "«A {dest} c'è un oggetto che mi appartiene. Ma qualcosa lo sorveglia.»",
    "guarigione": "«Mio fratello è malato. Mi servono {n} erbe spirituali (o una Pillola Curativa).»",
    "consegna": "«Porta questa lettera a {target}, a {dest}. Nessun altro deve leggerla.»",
}


def active(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def _save(conn, q: list[dict]) -> None:
    state.set_json(conn, KEY, q)


def _name(conn, nid) -> str:
    r = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()
    return r["name"] if r else "qualcuno"


def _loc_name(conn, lid) -> str:
    r = conn.execute("SELECT name FROM locations WHERE id=?;", (lid,)).fetchone()
    return r["name"] if r else "un luogo lontano"


def _nearby(conn, start: int, rng, hops: int, types: tuple | None = None) -> int:
    loc = start
    for _ in range(hops):
        ex = entities.get_exits(conn, loc)
        if not ex:
            break
        opts = sorted(ex.values())
        if types:
            pref = [x for x in opts if conn.execute("SELECT location_type FROM locations WHERE id=?;",
                                                    (x,)).fetchone()["location_type"] in types]
            opts = pref or opts
        loc = rng.choice(opts)
    if loc == start:
        ex = entities.get_exits(conn, start)
        if ex:
            loc = rng.choice(sorted(ex.values()))
    return loc


def _offers_here(conn, player) -> list[int]:
    day = tick_mod.get_tick(conn) // 120
    taken = {q["giver"] for q in active(conn)}
    out = []
    for r in conn.execute("SELECT id FROM npcs WHERE location_id=? AND status='alive' AND "
                          "COALESCE(kind,'human')='human' ORDER BY id;", (player.location_id,)):
        nid = r["id"]
        if nid in taken or state.get_int(conn, f"quest_cd_{nid}", -999) > day:
            continue
        from engine.systems import relations
        if relations.get_disposition(conn, nid, player.id).score < -10:
            continue
        if (nid * 7 + day // 7) % 3 == 0 or relations.get_disposition(conn, nid, player.id).score >= 25:
            out.append(nid)
    return out[:4]


def _make(conn, rng, player, giver: int, step: int, chain_len: int) -> dict:
    from engine.systems import npc_factory
    from engine.simulation import cultivation
    kind = rng.choice(_TYPES)
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    q = {"id": rng.randint(10 ** 5, 10 ** 6), "giver": giver, "kind": kind, "step": step,
         "chain": chain_len, "target": None, "dest": None, "need": 0, "done": False, "scene": False}
    base = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (giver,)).fetchone()["location_id"] \
        or player.location_id
    if kind == "vendetta":
        q["dest"] = _nearby(conn, base, rng, rng.randint(1, 3))
        q["target"] = npc_factory.spawn(conn, rng, archetype="vagabondo", location_id=q["dest"],
                                        tier=max(1, ptier + (1 if step >= 3 else 0)), stage=rng.randint(2, 6 + step),
                                        traits={"compassion": 10, "honor": 20})
    elif kind == "scorta":
        q["dest"] = _nearby(conn, base, rng, rng.randint(2, 3))
    elif kind == "recupero":
        q["dest"] = _nearby(conn, base, rng, rng.randint(1, 3), ("mountain", "ruin", "forbidden_zone"))
    elif kind == "guarigione":
        q["need"] = 3 + 2 * step
    else:
        city = conn.execute("SELECT id FROM locations WHERE location_type='city' AND id<>? ORDER BY RANDOM() LIMIT 1;",
                            (base,)).fetchone()
        q["dest"] = city["id"] if city else _nearby(conn, base, rng, 2)
        q["target"] = npc_factory.spawn(conn, rng, archetype="mercante", location_id=q["dest"], tier=max(1, ptier - 1))
    return q


def _text(conn, q: dict) -> str:
    return _INTRO[q["kind"]].format(target=_name(conn, q["target"]) if q["target"] else "",
                                    dest=_loc_name(conn, q["dest"]) if q["dest"] else "", n=q["need"])


def describe_offers(conn, player) -> str:
    offers = _offers_here(conn, player)
    if not offers:
        return "Nessuno qui sembra avere bisogno di te, per ora. (Le richieste cambiano con i giorni e i rapporti.)"
    lines = ["Chi, qui, ha qualcosa da chiederti:"]
    for i, nid in enumerate(offers, 1):
        lines.append(f"  {i}. {_name(conn, nid)} — ti fa cenno di avvicinarti.")
    lines.append("'incarico <n>' per ascoltarlo e accettare.")
    return "\n".join(lines)


def accept(conn, player, n: int) -> str:
    offers = _offers_here(conn, player)
    if not (1 <= n <= len(offers)):
        return describe_offers(conn, player)
    qs = active(conn)
    if len(qs) >= MAX_ACTIVE:
        return f"Hai già {MAX_ACTIVE} incarichi in corso ('incarichi')."
    giver = offers[n - 1]
    rng = random.Random(tick_mod.get_tick(conn) * 11 + giver)
    q = _make(conn, rng, player, giver, 1, rng.randint(3, 5))
    qs.append(q)
    _save(conn, qs)
    return f"{_name(conn, giver)}: {_text(conn, q)}\nAccetti l'incarico (passo 1). 'incarichi' per rivederlo."


def describe(conn, player) -> str:
    from engine.cli.loop import _first_step_toward
    qs = active(conn)
    if not qs:
        return "Nessun incarico in corso. 'richieste' per sentire chi, qui, ha bisogno di te."
    lines = ["INCARICHI IN CORSO"]
    for q in qs:
        where = ""
        if q["dest"]:
            step = _first_step_toward(conn, player.location_id, q["dest"])
            where = f" → {_loc_name(conn, q['dest'])}" + (f" (vai verso {step})" if step else " (sei qui)")
        lines.append(f"  · per {_name(conn, q['giver'])} — {q['kind']} (passo {q['step']}/{q['chain']}){where}")
        lines.append(f"      {_text(conn, q)}")
    return "\n".join(lines)


def _reward(conn, rng, player, q: dict) -> list[str]:
    from engine.systems import sects, relations, reputation, items
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    t = tick_mod.get_tick(conn)
    stones = 40 * tier * q["step"]
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    relations.adjust(conn, q["giver"], 12 * q["step"], t, player.id)
    reputation.adjust(conn, player.id, fame=q["step"])
    out = [f"✔ Incarico compiuto per {_name(conn, q['giver'])}: +{stones} pietre, la sua gratitudine cresce."]
    if q["step"] >= q["chain"]:
        gift = rng.choice(["tecnica", "pillola", "vita"])
        nm = _name(conn, q["giver"])
        if gift == "tecnica":
            out += items.apply_effects(conn, t, rng, player.id, {"learn_technique": {
                "name": f"Arte segreta di {nm}", "magnitude": round(0.06 + 0.02 * tier, 3),
                "tech_key": f"incarico:{q['giver']}"}})
        elif gift == "pillola":
            out += items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": round(0.6 + 0.1 * tier, 2)})
        else:
            out += items.apply_effects(conn, t, rng, player.id, {"lifespan_years": 20 + 10 * tier})
        relations.adjust(conn, q["giver"], 30, t, player.id)
        out.append(f"✦ La catena è conclusa: {nm} ti considera di famiglia, e ti ha dato ciò che di più prezioso "
                   "aveva. (Ora potresti chiedergli di seguirti, o giurare fratellanza.)")
        n = state.get_int(conn, "chains_done", 0) + 1
        state.set(conn, "chains_done", str(n))
        if n in (1, 10, 50) and state.grant_title(conn, {1: "Uomo di Parola", 10: "Benefattore",
                                                          50: "Colui a cui Tutti Chiedono"}[n]):
            out.append("✧ Nuovo titolo! ✧")
        state.set(conn, f"quest_cd_{q['giver']}", str(t // 120 + 10))
    return out


def _complete(conn, rng, player, q: dict) -> list[str]:
    qs = [x for x in active(conn) if x["id"] != q["id"]]
    _save(conn, qs)
    out = _reward(conn, rng, player, q)
    if q["step"] < q["chain"]:
        nq = _make(conn, rng, player, q["giver"], q["step"] + 1, q["chain"])
        qs.append(nq)
        _save(conn, qs)
        out.append(f"{_name(conn, q['giver'])} ti manda a dire: {_text(conn, nq)} (passo {nq['step']}/{nq['chain']})")
    return out


def check(conn, player) -> list[str]:
    """Verifica gli incarichi: bersagli abbattuti, destinazioni raggiunte."""
    out = []
    rng = random.Random(tick_mod.get_tick(conn) * 3 + 17)
    for q in list(active(conn)):
        if q["kind"] == "vendetta" and q["target"]:
            r = conn.execute("SELECT status FROM npcs WHERE id=?;", (q["target"],)).fetchone()
            if not r or r["status"] != "alive":
                out += _complete(conn, rng, player, q)
        elif q["kind"] in ("scorta", "consegna") and q["dest"] == player.location_id:
            if q["kind"] == "scorta":
                conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (q["dest"], q["giver"]))
            out += _complete(conn, rng, player, q)
        elif q["kind"] == "recupero":
            dead = False
            if q.get("target"):
                r = conn.execute("SELECT status FROM npcs WHERE id=?;", (q["target"],)).fetchone()
                dead = not r or r["status"] != "alive"
            if q.get("done") or dead:
                out += _complete(conn, rng, player, q)
    return out


def on_arrival(conn, player) -> str | None:
    from engine.systems import encounters, npc_factory
    lines = check(conn, player)
    # scorta: il committente ti segue
    for q in active(conn):
        if q["kind"] == "scorta":
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, q["giver"]))
    for q in active(conn):
        if q["kind"] == "recupero" and q["dest"] == player.location_id and not q.get("scene") \
                and not encounters.pending(conn):
            qs = active(conn)
            for x in qs:
                if x["id"] == q["id"]:
                    x["scene"] = True
            _save(conn, qs)
            rng = random.Random(q["id"])
            sc = {"key": "incarico_recupero", "title": "L'oggetto sorvegliato", "event_type": "quest",
                  "text": "Lo trovi: è lì, in un anfratto. Ma {npc} ci si è accampato sopra, e non sembra disposto a cederlo.",
                  "spawn": {"archetype": "guardia", "tier_offset": 0, "stage": 4 + 2 * q["step"]},
                  "choices": [
                      {"label": "Lo affronti", "effects": {"quest_target": q["id"]}, "command": "attack {npc}"},
                      {"label": "Lo sottrai di nascosto", "check": {"stat": "istinto", "dc": 55 + 4 * q["step"]},
                       "success": {"quest_done": q["id"], "text": "Ti allontani con l'oggetto prima che se ne accorga."},
                       "failure": {"text": "Ti scopre!", "command": "attack {npc}", "quest_target": q["id"]}}]}
            sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
            txt = encounters.start_scene(conn, player, sc)
            if txt:
                lines.append(txt)
            break
    return "\n".join(lines) if lines else None


def set_target(conn, qid: int, npc_id) -> None:
    qs = active(conn)
    for q in qs:
        if q["id"] == qid:
            q["target"] = npc_id
    _save(conn, qs)


def mark_done(conn, qid: int) -> None:
    qs = active(conn)
    for q in qs:
        if q["id"] == qid:
            q["done"] = True
    _save(conn, qs)


def deliver(conn, player) -> str:
    from engine.systems import professions, items
    rng = random.Random(tick_mod.get_tick(conn) + 5)
    for q in active(conn):
        if q["kind"] != "guarigione":
            continue
        g = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (q["giver"],)).fetchone()
        if not g or g["location_id"] != player.location_id:
            continue
        pill = items.find_in_inventory(conn, player.id, "curativa")
        if pill:
            conn.execute("UPDATE inventories SET quantity=quantity-1 WHERE id=?;", (pill["inv_id"],))
        elif not professions.spend(conn, player.id, {"erbe": q["need"]}):
            return f"Ti servono {q['need']} erbe spirituali (o una Pillola Curativa). ('gather' nelle zone selvagge)"
        return "\n".join(["Consegni ciò che serviva. Il malato riprende colore."] + _complete(conn, rng, player, q))
    return "Nessun committente qui aspetta una consegna."
