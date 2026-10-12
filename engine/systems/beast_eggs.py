"""
UOVA E ALLEVAMENTO DI BESTIE.

  - Le bestie rare (e a volte quelle forti) lasciano UOVA. Le uova si covano nella STALLA
    della tua grotta-dimora: 'use uovo' quando sei a casa. Più è rara la specie, più tempo
    serve; una stalla più grande accorcia l'attesa.
  - La bestia che nasce ti riconosce come genitore: talento più alto del normale, e ti
    segue se hai posto; altrimenti ti aspetta nella stalla (domarla sarà un attimo).
  - ALLEVAMENTO (arte del Domatore, livello 4): 'alleva <bestia> <bestia>' con due tue bestie
    nella stalla — nasce un uovo IBRIDO che ne unisce specie, elementi e doni, di rarità
    superiore. Il sangue di un ibrido nutre lignaggi ibridi.

  uova                     le uova in cova e quando si schiuderanno
  alleva <nome> <nome>     fai accoppiare due tue bestie (nella stalla della dimora)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "eggs"
RARITY_ORDER = ["comune", "rara", "leggendaria", "ibrida", "simbolo", "ancestrale", "caos"]
HATCH_DAYS = {"comune": 3, "rara": 6, "leggendaria": 10, "ibrida": 14, "simbolo": 20, "ancestrale": 30, "caos": 45}
BREED_LEVEL = 4
BREED_COOLDOWN = 10


def eggs(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def _save(conn, e: list[dict]) -> None:
    state.set_json(conn, KEY, e)


def drop_egg(conn, rng, player, npc_id: int) -> list[str]:
    """Dopo l'uccisione di una bestia: a volte un uovo."""
    from engine.systems import beasts, items
    tr = beasts.traits(conn, npc_id)
    rarity = tr["rarity"] or "comune"
    p = {"comune": 0.04, "rara": 0.25, "leggendaria": 0.3, "ibrida": 0.35, "simbolo": 0.3, "ancestrale": 0.25,
         "caos": 0.2}.get(rarity, 0.04)
    if rng.random() >= p:
        return []
    spec = {"species": tr["species"], "rarity": rarity, "elements": [e for e in (tr["elements"] or "").split(",") if e],
            "ability": tr["ability"]}
    nm = f"Uovo di {tr['species']}"
    iid = items.create_item(conn, nm, "uovo", "raro" if rarity != "comune" else "non_comune",
                            "Si schiude nella stalla della tua dimora ('use uovo' quando sei a casa).",
                            {"egg": spec})
    items.grant(conn, "player", player.id, iid)
    return [f"Tra le spoglie trovi un {nm}! Ancora caldo."]


def can_incubate(conn, pid: int) -> str | None:
    from engine.systems import cave_abode
    from engine.core import entities
    ab = cave_abode.get(conn, pid)
    if not ab:
        return "Per covare un uovo serve una dimora con una stalla ('dimora reclama', poi 'dimora potenzia stalla')."
    if cave_abode.level(conn, pid, "stalla") < 1:
        return "La tua dimora non ha ancora una stalla ('dimora potenzia stalla')."
    if entities.get_player(conn, pid).location_id != ab["loc"]:
        return "Le uova si covano nella stalla: torna alla tua dimora ('dimora torna')."
    return None


def incubate(conn, pid: int, spec: dict) -> list[str]:
    from engine.systems import cave_abode
    why = can_incubate(conn, pid)
    if why:
        return [why]
    day = tick_mod.get_tick(conn) // 120
    days = max(1, HATCH_DAYS.get(spec.get("rarity", "comune"), 5) - cave_abode.level(conn, pid, "stalla"))
    e = eggs(conn)
    e.append(dict(spec, hatch_day=day + days))
    _save(conn, e)
    return [f"Adagi l'uovo di {spec['species']} nella paglia tiepida della stalla. Si schiuderà tra {days} giorni."]


def _hatch(conn, rng, player, spec: dict) -> str:
    from engine.systems import beasts, npc_factory, bonds, cave_abode, classes
    from engine.simulation import cultivation
    ab = cave_abode.get(conn, player.id)
    loc = ab["loc"] if ab else player.location_id
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    rarity = spec.get("rarity", "comune")
    els = spec.get("elements") or ["corpo"]
    name = spec["species"]
    if conn.execute("SELECT 1 FROM npcs WHERE name=?;", (name,)).fetchone():
        name = f"{name} {rng.randint(2, 99)}"
    nid = npc_factory.spawn(conn, rng, archetype="vagabondo", location_id=loc, tier=max(1, ptier - 1), stage=1,
                            name=name, dao=els[0], dao_comp=10 + 5 * ptier, traits={"loyalty": 95})
    conn.execute("UPDATE npcs SET kind='beast', archetype='bestia', description=? WHERE id=?;",
                 (f"Una giovane creatura {rarity}, nata nella tua stalla.", nid))
    floor = min(len(beasts.TALENTS) - 1, beasts.RARITY_TALENT_FLOOR.get(rarity, 0) + 1)
    beasts.ensure_table(conn)
    conn.execute("INSERT OR REPLACE INTO beast_traits (npc_id, species, rarity, talent, elements, ability) "
                 "VALUES (?, ?, ?, ?, ?, ?);",
                 (nid, spec["species"], rarity, beasts._roll_talent(rng, floor), ",".join(els), spec.get("ability")))
    t = tick_mod.get_tick(conn)
    if len(beasts.pets(conn, player.id)) < classes.max_beasts(conn, player.id):
        bonds.add_bond(conn, player.id, nid, "beast", t, reason="nata dal tuo uovo")
        return f"🥚 L'uovo si schiude: nasce {name}! Ti guarda e ti riconosce come genitore. È tua."
    imp = state.get_json(conn, "imprinted", []) or []
    imp.append(nid)
    state.set_json(conn, "imprinted", imp)
    return (f"🥚 L'uovo si schiude: nasce {name}! Non hai posto per un'altra bestia al tuo fianco: ti aspetta "
            "nella stalla (domarla sarà facilissimo).")


def daily(conn, t: int, rng, player) -> list[str]:
    e = eggs(conn)
    if not e:
        return []
    day = t // 120
    out, keep = [], []
    for spec in e:
        if day >= spec["hatch_day"]:
            out.append(_hatch(conn, rng, player, spec))
        else:
            keep.append(spec)
    _save(conn, keep)
    return out


def tame_bonus(conn, npc_id: int) -> float:
    return 0.6 if npc_id in (state.get_json(conn, "imprinted", []) or []) else 0.0


def _hybrid_species(a: dict, b: dict) -> str:
    from engine.systems import bloodlines
    fams = []
    for sp in (a["species"], b["species"]):
        fs = bloodlines.families_of(sp)
        nouns = [bloodlines.FAMILIES[f][0] for f in fs] or [sp.split()[0]]
        for n in nouns:
            if n not in fams:
                fams.append(n)
    els = list(dict.fromkeys((a["elements"] or []) + (b["elements"] or [])))[:3]
    tail = " e ".join(bloodlines.EL_ADJ.get(e, e) for e in els[:2])
    return "-".join(fams[:3]) + (f" di {tail}" if tail else "")


def breed(conn, player, arg: str) -> str:
    from engine.systems import beasts, professions, cave_abode
    if professions.level(conn, player.id, "domatore") < BREED_LEVEL:
        return f"Solo un Domatore di Bestie esperto (livello {BREED_LEVEL}) sa far accoppiare le bestie spirituali."
    why = can_incubate(conn, player.id)
    if why:
        return why
    day = tick_mod.get_tick(conn) // 120
    if day - state.get_int(conn, "breed_day", -999) < BREED_COOLDOWN:
        return "Le tue bestie hanno bisogno di riposo dopo l'ultimo accoppiamento."
    parts = arg.split()
    ps = beasts.pets(conn, player.id)
    if len(parts) < 2 or len(ps) < 2:
        return "Usa: alleva <bestia> <bestia> (servono due tue bestie, nella stalla della dimora)."
    pick = []
    for frag in parts[:2]:
        r = next((p for p in ps if frag.lower() in p["name"].lower() and p not in pick), None)
        if r is None:
            return f"Non hai una bestia di nome '{frag}'."
        pick.append(r)
    ab = cave_abode.get(conn, player.id)
    if any(p["location_id"] != ab["loc"] for p in pick):
        return "Entrambe le bestie devono essere qui, nella stalla."
    ta, tb = beasts.traits(conn, pick[0]["npc_id"]), beasts.traits(conn, pick[1]["npc_id"])
    A = {"species": ta["species"], "elements": [e for e in (ta["elements"] or "").split(",") if e], "rarity": ta["rarity"]}
    B = {"species": tb["species"], "elements": [e for e in (tb["elements"] or "").split(",") if e], "rarity": tb["rarity"]}
    hi = max(RARITY_ORDER.index(A["rarity"] or "comune"), RARITY_ORDER.index(B["rarity"] or "comune"))
    rarity = RARITY_ORDER[hi + 1] if hi < RARITY_ORDER.index("ibrida") else RARITY_ORDER[hi]   # l'ibrido non supera il proprio sangue
    species = _hybrid_species(A, B) if A["species"] != B["species"] else A["species"]
    spec = {"species": species, "rarity": rarity,
            "elements": list(dict.fromkeys(A["elements"] + B["elements"]))[:3],
            "ability": ta["ability"] or tb["ability"]}
    state.set(conn, "breed_day", str(day))
    professions.add_xp(conn, player.id, 6, "domatore")
    lines = [f"{pick[0]['name']} e {pick[1]['name']} si accoppiano sotto la luna: nasce un uovo di {species}!"]
    lines += incubate(conn, player.id, spec)
    return "\n".join(lines)


def describe(conn, player) -> str:
    e = eggs(conn)
    if not e:
        return ("Nessun uovo in cova. Le bestie rare a volte lasciano uova; un Domatore esperto può far "
                "accoppiare le sue bestie ('alleva').")
    day = tick_mod.get_tick(conn) // 120
    lines = ["🥚 UOVA IN COVA"]
    for s in e:
        left = max(0, s["hatch_day"] - day)
        lines.append(f"  · {s['species']} ({s['rarity']}) — si schiude tra {left} giorn{'o' if left == 1 else 'i'}")
    return "\n".join(lines)
