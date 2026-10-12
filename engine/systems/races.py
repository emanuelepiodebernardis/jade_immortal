"""
LE RAZZE ANTICHE — popoli, non mostri.

Cinque razze antiche vivono ai margini del mondo umano, ciascuna nelle sue terre. Con ognuna
hai un RAPPORTO (−100…+100) e un ONORE che cresce senza fine:
  Draghi          (montagne)        ti rispettano se hai sangue di drago; doni: sangue, domare
  Demoni Celesti  (zone proibite)   rispettano la forza e l'infamia; doni: arti demoniache
  Spiriti dei Boschi (montagne)     amano chi rispetta la vita; doni: erbe e longevità
  Giganti         (rovine)          rispettano chi li batte; doni: tempra del corpo
  Popolo delle Maree (ovunque ci sia acqua) mercanti nati; doni: pietre e perle

  razze                         rapporti con le razze e le loro terre
  ambasciata <razza> dona <n>   doni pietre ai loro emissari (nelle loro terre)
  ambasciata <razza> prova      affronti il loro campione: vincere vale molto onore
A +60 si diventa ALLEATI: ogni tanto mandano doni, e nelle grandi calamità combattono con te.
A −60 è GUERRA: le loro razzie colpiscono le terre umane. L'onore sale all'infinito: Amico,
Alleato, Fratello di Sangue, Signore Onorario… e oltre.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "races"
RACES = {
    "draghi": ("Draghi", "mountain", "drago"),
    "demoni": ("Demoni Celesti", "forbidden_zone", None),
    "spiriti": ("Spiriti dei Boschi", "mountain", None),
    "giganti": ("Giganti", "ruin", None),
    "maree": ("Popolo delle Maree", "city", None),
}
_HONOR = [(0, "Straniero"), (50, "Amico"), (200, "Alleato"), (600, "Fratello di Sangue"), (1500, "Signore Onorario")]


def all_r(conn) -> dict:
    d = state.get_json(conn, KEY)
    if d:
        return d
    d = {}
    for k, (_n, ltype, _b) in RACES.items():
        loc = conn.execute("SELECT id FROM locations WHERE location_type=? ORDER BY id DESC LIMIT 1;", (ltype,)).fetchone()
        d[k] = {"rel": 0, "honor": 0, "land": loc["id"] if loc else None, "met": False}
    state.set_json(conn, KEY, d)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def honor_rank(h: int) -> str:
    nm = "Straniero"
    for th, n in _HONOR:
        if h >= th:
            nm = n
    if h >= 5000:
        nm = f"Antenato Onorario ({h // 5000}°)"
    return nm


def _find(arg: str) -> str | None:
    a = arg.strip().lower()
    for k, (n, _l, _b) in RACES.items():
        if a and (a in k or a in n.lower()):
            return k
    return None


def adjust(conn, key: str, rel: int = 0, honor: int = 0) -> list[str]:
    d = all_r(conn)
    r = d[key]
    before_rel, before_h = r["rel"], honor_rank(r["honor"])
    r["rel"] = max(-100, min(100, r["rel"] + rel))
    r["honor"] = max(0, r["honor"] + honor)
    _save(conn, d)
    out = []
    nm = RACES[key][0]
    if before_rel < 60 <= r["rel"]:
        out.append(f"✦ I {nm} ti riconoscono come ALLEATO.")
        from engine.systems import master_plot
        master_plot.record_choice(conn, f"razza_{key}", "alleata")
    if before_rel > -60 >= r["rel"]:
        out.append(f"⚠ I {nm} ti dichiarano GUERRA.")
    if honor_rank(r["honor"]) != before_h:
        t = f"{honor_rank(r['honor'])} dei {nm}"
        state.grant_title(conn, t)
        out.append(f"✧ Nuovo titolo: «{t}» ✧")
    return out


def allies(conn) -> list[str]:
    return [k for k, r in all_r(conn).items() if r["rel"] >= 60]


def intro(conn, player) -> list[str]:
    from engine.systems import bloodlines
    d = all_r(conn)
    out = ["Le razze antiche hanno notato la tua ascesa: i loro emissari ti osservano. ('razze')"]
    for ln in bloodlines.all_lines(conn).values():
        if "drago" in ln.get("families", []):
            out += adjust(conn, "draghi", 30)
            out.append("I Draghi sentono il loro sangue nelle tue vene: ti chiamano «piccolo parente».")
            break
    d = all_r(conn)
    for k in d:
        d[k]["met"] = True
    _save(conn, d)
    return out


def embassy(conn, player, arg: str) -> str:
    from engine.systems import sects, encounters, npc_factory, reputation
    from engine.simulation import cultivation
    parts = arg.split()
    key = _find(parts[0]) if parts else None
    if not key:
        return "Quale razza? " + ", ".join(v[0] for v in RACES.values())
    d = all_r(conn)
    r = d[key]
    nm = RACES[key][0]
    if r["land"] and player.location_id != r["land"] and key != "maree":
        ln = conn.execute("SELECT name FROM locations WHERE id=?;", (r["land"],)).fetchone()["name"]
        return f"Gli emissari dei {nm} si trovano nelle loro terre, a {ln}."
    if r["rel"] <= -60:
        return f"I {nm} sono in guerra con te: non c'è ambasciata, solo battaglia."
    sub = parts[1].lower() if len(parts) > 1 else ""
    if sub in ("dona", "dono"):
        n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 100
        if sects.get_resource(conn, "pietre_spirituali", player.id) < n:
            return "Non hai abbastanza pietre."
        sects.grant_resource(conn, "pietre_spirituali", -n, player.id)
        mult = 2 if key == "maree" else 1
        return "\n".join([f"I {nm} accettano il dono."] + adjust(conn, key, rel=max(1, n // 50) * mult, honor=n // 20))
    if sub in ("prova", "sfida"):                 # ora la prova è il campione della razza (race_realms)
        from engine.systems import race_realms
        if key in race_realms.BLOOD:
            return race_realms.challenge(conn, player, key)
        day = tick_mod.get_tick(conn) // 120
        if day - state.get_int(conn, f"race_trial_{key}", -99) < 7:
            return f"I {nm} ti hanno messo alla prova da poco."
        state.set(conn, f"race_trial_{key}", str(day))
        rng = random.Random(tick_mod.get_tick(conn) + 5)
        sc = {"key": "prova_razza", "title": f"La prova dei {nm}", "event_type": "combat",
              "text": f"Il campione dei {nm}, {{npc}}, ti attende nel cerchio di pietre.",
              "spawn": {"archetype": "guardia", "tier_offset": 0, "stage": 8},
              "choices": [{"label": "Combatti", "effects": {"race_honor": [key, 60, 15]}, "command": "attack {npc}"},
                          {"label": "Rinunci con un inchino", "effects": {"race_honor": [key, 5, 0]}}]}
        sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
        return encounters.start_scene(conn, player, sc, force=True) or ""
    return describe(conn, player)


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import sects, professions, items, reputation, master_plot
    if not master_plot.flag(conn, "razze"):
        return []
    d = all_r(conn)
    out = []
    for k, r in d.items():
        nm = RACES[k][0]
        if r["rel"] >= 60 and rng.random() < 0.08:
            if k == "draghi":
                out += items.apply_effects(conn, t, rng, player.id, {"bloodline": {"species": "Drago Azzurro",
                                                                                   "elements": ["fulmine", "acqua"], "gain": 5}})
            elif k == "spiriti":
                professions.give(conn, player.id, "erbe", 10)
            elif k == "giganti":
                out += items.apply_effects(conn, t, rng, player.id, {"grow_strength": 1, "grow_vitality": 1})
            elif k == "demoni":
                out += items.apply_effects(conn, t, rng, player.id, {"dao_key": "random", "dao_gain": 3})
            else:
                sects.grant_resource(conn, "pietre_spirituali", 150, player.id)
            out.append(f"I {nm}, tuoi alleati, ti mandano un dono.")
        elif r["rel"] <= -60 and rng.random() < 0.05:
            reputation.adjust(conn, player.id, fame=-2)
            out.append(f"⚠ I {nm} razziano le terre umane in nome della guerra con te.")
        # gli umori cambiano con le tue azioni
        if k == "demoni":
            rep = reputation.get(conn, player.id)
            if rep["infamy"] > rep["fame"] and rng.random() < 0.1:
                adjust(conn, k, rel=1)
    return out


def describe(conn, player) -> str:
    d = all_r(conn)
    lines = ["🐉 LE RAZZE ANTICHE"]
    for k, r in d.items():
        nm = RACES[k][0]
        ln = conn.execute("SELECT name FROM locations WHERE id=?;", (r["land"],)).fetchone()["name"] if r["land"] else "?"
        st = "ALLEATI" if r["rel"] >= 60 else ("IN GUERRA" if r["rel"] <= -60 else f"rapporto {r['rel']:+d}")
        lines.append(f"  · {nm} — terre: {ln} — {st} — onore {r['honor']} ({honor_rank(r['honor'])})")
    lines.append("'ambasciata <razza> dona <pietre>' o 'ambasciata <razza> prova' nelle loro terre.")
    return "\n".join(lines)
