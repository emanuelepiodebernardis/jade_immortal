"""
ELEMENTI CELESTI (天地灵物) — l'essenza viva di ogni elemento, nata tra cielo e terra.

Per ogni elemento esiste una classifica di Elementi Celesti: dalla «Fiamma del Loto Rosso»
alla «Fiamma dell'Origine», dal «Ghiaccio delle Nove Profondità» al «Mare del Nulla»…
Ogni tanto uno di essi NASCE in un luogo selvaggio (lo annunciano le cronache) e resta
qualche giorno, sorvegliato da una bestia. Chi lo raggiunge e lo ASSORBE ne guadagna i poteri.

  - Ogni elemento assorbito dà un VANTAGGIO proprio (il Fuoco rafforza l'alchimia, l'Acqua
    rigenera, la Terra protegge, il Metallo perfora, il Legno allunga la vita, il Fulmine fa
    bere più folgori alle tribolazioni, il Vento fa schivare, la Luce acceca e purifica,
    l'Oscurità drena), il suo STATO in battaglia, la crescita della radice e del Dao affini.
  - Più ne assorbi dello stesso elemento, più quell'elemento diventa forte (senza fine):
    gli elementi celesti si fondono tra loro e salgono di grado.
  - Elementi DIVERSI si armonizzano: due danno una Fusione Celeste, cinque del ciclo il
    «Corpo dei Cinque Elementi Celesti», tutti e nove il «Caos Celeste».
  - Assorbirli è rischioso se la tua radice di quell'elemento è debole e il cuore instabile.

  elementi               i tuoi elementi celesti e quello nato ora nel mondo
  elementi assorbi       assorbi l'elemento celeste qui (dopo averne vinto il guardiano)
"""

from __future__ import annotations

import math
import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "celestial"
EV_KEY = "celestial_event"
_NAMES = {
    "fuoco": ["Fiamma del Loto Rosso", "Fiamma Ossea Fredda", "Fiamma del Cuore Viola", "Fiamma della Fenice Primordiale",
              "Fiamma del Vuoto Bianco", "Fiamma dell'Origine"],
    "acqua": ["Rugiada delle Nove Profondità", "Ghiaccio dell'Abisso Nero", "Marea della Luna", "Ghiaccio Eterno del Polo",
              "Fonte della Vita Celeste", "Mare del Nulla"],
    "terra": ["Terra Gialla del Cuore", "Pietra Madre dei Monti", "Sabbia del Tempo", "Terra Primordiale Xirang",
              "Montagna che Regge il Cielo", "Terra dell'Origine"],
    "metallo": ["Oro Bianco Affilato", "Ferro Stellare", "Metallo del Gengjin", "Lama Nata dal Cielo",
                "Oro del Sole Infinito", "Metallo dell'Origine"],
    "legno": ["Germoglio della Vita", "Radice del Gelso Antico", "Legno di Fusang", "Linfa dell'Albero del Mondo",
              "Seme della Creazione", "Legno dell'Origine"],
    "fulmine": ["Fulmine Viola del Cielo", "Tuono delle Nove Ondate", "Fulmine della Distruzione", "Tuono del Caos",
                "Fulmine del Giudizio Celeste", "Fulmine dell'Origine"],
    "vento": ["Brezza delle Vette", "Vento Nero Tagliente", "Vento delle Nove Direzioni", "Tempesta del Peng",
              "Respiro del Cielo", "Vento dell'Origine"],
    "luce": ["Luce dell'Alba Pura", "Raggio del Sole Dorato", "Luce del Buddha", "Splendore Stellare",
             "Luce della Prima Creazione", "Luce dell'Origine"],
    "oscurita": ["Ombra della Luna Nuova", "Tenebra degli Inferi", "Notte Senza Stelle", "Ombra del Re Demone",
                 "Oscurità prima del Tempo", "Oscurità dell'Origine"],
}
EL_LABEL = {"fuoco": "Fuoco", "acqua": "Acqua", "terra": "Terra", "metallo": "Metallo", "legno": "Legno",
            "fulmine": "Fulmine", "vento": "Vento", "luce": "Luce", "oscurita": "Oscurità"}
_STATE = {"fuoco": "ustione", "acqua": "gelo", "terra": "scudo", "metallo": "emorragia", "legno": "rigenerazione",
          "fulmine": "stordimento", "vento": "velocita", "luce": "accecamento", "oscurita": "drenaggio"}
_GRADES = ["Germoglio", "Fiore", "Frutto", "Anima", "Sovrano", "Celeste"]
_CYCLE = {"legno", "fuoco", "terra", "metallo", "acqua"}


def owned(conn) -> dict:
    """{elemento: {"power": float, "names": [..]}}"""
    return state.get_json(conn, KEY, {}) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def strength(power: float) -> float:
    return math.log2(1 + power / 10.0)


def grade(power: float) -> str:
    i = int(strength(power))
    return _GRADES[i] if i < len(_GRADES) else f"Origine {i - len(_GRADES) + 1}"


def _name(el: str, rank: int) -> str:
    ns = _NAMES[el]
    if rank <= len(ns):
        return ns[rank - 1]
    return f"{ns[-1]} (rinata {rank - len(ns)} volte)"


def current_event(conn) -> dict | None:
    ev = state.get_json(conn, EV_KEY)
    if ev and tick_mod.get_tick(conn) // 120 <= ev["until"]:
        return ev
    return None


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.simulation import cultivation
    day = t // 120
    ev = state.get_json(conn, EV_KEY)
    out = []
    if ev and day > ev["until"]:
        state.delete(conn, EV_KEY)
        if not ev.get("taken"):
            out.append(f"Lo spirito del {ev['name']} si dissolve nel cielo: qualcun altro, forse, l'ha preso.")
        ev = None
    if ev is None and day - state.get_int(conn, "celestial_day", -999) >= 18 and day >= 4 and rng.random() < 0.35:
        wild = [r["id"] for r in conn.execute("SELECT id FROM locations WHERE location_type IN "
                                               "('mountain','ruin','forbidden_zone');")]
        if not wild:
            return out
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        el = rng.choice(list(_NAMES))
        rank = max(1, min(len(_NAMES[el]) + tier // 3, rng.randint(1, 1 + tier // 2)))
        loc = rng.choice(wild)
        state.set_json(conn, EV_KEY, {"el": el, "rank": rank, "name": _name(el, rank), "loc": loc,
                                       "until": day + 4, "guard": None, "taken": False})
        state.set(conn, "celestial_day", str(day))
        lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
        out.append(f"✦ Il cielo cambia colore sopra {lname}: è nato un ELEMENTO CELESTE, il {_name(el, rank)}! "
                   "Resterà 4 giorni. ('elementi')")
    return out


def on_arrival(conn, player) -> str | None:
    from engine.systems import encounters, npc_factory
    ev = current_event(conn)
    if not ev or ev["loc"] != player.location_id or ev.get("guard") or ev.get("taken") or encounters.pending(conn):
        return None
    rng = random.Random(tick_mod.get_tick(conn) + 7)
    sc = {"key": "elemento_celeste", "title": f"Il {ev['name']}", "event_type": "fortune",
          "text": f"Lo vedi: il {ev['name']} danza a mezz'aria. Ma attorno a lui si arrotola {{npc}}, il suo guardiano.",
          "spawn": {"archetype": "guardia", "tier_offset": 1 if ev["rank"] >= 3 else 0, "stage": 3 + 2 * ev["rank"]},
          "sticky": True,
          "choices": [{"label": "Abbatti il guardiano", "effects": {"celestial_guard": True}, "command": "attack {npc}"},
                      {"label": "Lo distrai e afferri l'elemento", "check": {"stat": "istinto", "dc": 60 + 5 * ev["rank"]},
                       "success": {"celestial_free": True, "npc_leaves": True,
                                   "text": "Il guardiano si volta: è il tuo momento. ('elementi assorbi')"},
                       "failure": {"celestial_guard": True, "command": "attack {npc}",
                                   "text": "Il guardiano non abbocca!"}}]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    return encounters.start_scene(conn, player, sc)


def set_guard(conn, npc_id) -> None:
    ev = state.get_json(conn, EV_KEY)
    if ev:
        ev["guard"] = npc_id
        state.set_json(conn, EV_KEY, ev)


def set_free(conn) -> None:
    ev = state.get_json(conn, EV_KEY)
    if ev:
        ev["guard"] = -1
        state.set_json(conn, EV_KEY, ev)


def absorb(conn, player) -> str:
    from engine.systems import spirit_roots, dao_heart, items, lifespan
    ev = current_event(conn)
    if not ev or ev["loc"] != player.location_id or ev.get("taken"):
        return "Qui non c'è nessun Elemento Celeste da assorbire."
    g = ev.get("guard")
    if g is None:
        return "Il guardiano lo protegge ancora."
    if g not in (-1,):
        r = conn.execute("SELECT status FROM npcs WHERE id=?;", (g,)).fetchone()
        if r and r["status"] == "alive":
            return "Il guardiano è ancora vivo: abbattilo prima."
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + 3)
    el = ev["el"]
    gain = 10.0 * ev["rank"] ** 1.5
    lines = [f"Ti siedi e apri i meridiani: il {ev['name']} ti entra nel corpo come un fiume in piena."]
    root = spirit_roots.get(conn, "player", player.id).get(el, 0)
    if root < 20 and dao_heart.heart(conn) < 50 and rng.random() < 0.35:
        conn.execute("INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
                     "healed, heal_tick) VALUES ('player', ?, 4, 'elemento celeste indomito', ?, 0, ?);",
                     (player.id, t, t + 60))
        gain *= 0.5
        lines.append("⚠ Il tuo corpo non era pronto: l'elemento ti devasta i meridiani, e ne trattieni solo metà.")
    d = owned(conn)
    cur = d.setdefault(el, {"power": 0.0, "names": []})
    g0 = grade(cur["power"])
    cur["power"] = round(cur["power"] + gain, 1)
    cur["names"].append(ev["name"])
    _save(conn, d)
    ev["taken"] = True
    state.set_json(conn, EV_KEY, ev)
    spirit_roots.add(conn, "player", player.id, el, 5.0 + 2 * ev["rank"])
    lines += items.apply_effects(conn, t, rng, player.id, {"dao_key": el if el != "oscurita" else "oscurita",
                                                           "dao_gain": 4 + 2 * ev["rank"]})
    if el == "legno":
        lifespan.add_bonus_years(conn, 10 * ev["rank"])
        lines.append(f"La linfa celeste ti allunga la vita di {10 * ev['rank']} anni.")
    if el == "luce":
        lines.append(dao_heart.purify(conn, 40))
    lines.append(f"✦ {EL_LABEL[el]} Celeste: potenza {cur['power']:.0f}, grado {grade(cur['power'])}"
                 + (" (sale di grado!)" if grade(cur["power"]) != g0 else "") + ".")
    n = len(d)
    if n in (2, 5, 9):
        lines.append({2: "Due elementi celesti si armonizzano in te: FUSIONE CELESTE.",
                      5: "Cinque elementi celesti: nasce il tuo CORPO CELESTE DEI CINQUE ELEMENTI.",
                      9: "Tutti e nove: il CAOS CELESTE ti scorre nelle vene."}[n])
        state.grant_title(conn, {2: "Fusione Celeste", 5: "Corpo dei Cinque Elementi Celesti", 9: "Caos Celeste"}[n])
    return "\n".join(lines)


def _harmony(d: dict) -> float:
    els = set(d)
    bonus = 0.05 * max(0, len(els) - 1)
    if _CYCLE <= els:
        bonus += 0.2
    if len(els) >= 9:
        bonus += 0.3
    return bonus


def cultivation_mult(conn) -> tuple[float, str]:
    d = owned(conn)
    if not d:
        return 1.0, ""
    return 1.0 + 0.03 * sum(strength(v["power"]) for v in d.values()) + _harmony(d), "gli elementi celesti"


def dao_mult(conn, dao_key: str) -> float:
    v = owned(conn).get(dao_key)
    return 1.0 + 0.1 * strength(v["power"]) if v else 1.0


def craft_bonus(conn) -> float:
    v = owned(conn).get("fuoco")
    return 0.03 * strength(v["power"]) if v else 0.0


def tribulation_bonus(conn) -> float:
    v = owned(conn).get("fulmine")
    return 0.04 * strength(v["power"]) if v else 0.0


def combat(conn, fx) -> list[str]:
    d = owned(conn)
    if not d:
        return []
    pr = fx.p.prof
    h = _harmony(d)
    for el, v in d.items():
        s = strength(v["power"])
        fx.add_proc("p", _STATE[el], min(0.5, 0.12 + 0.04 * s), 1.2 + 0.2 * s, f"celeste:{el}")
        if el == "terra":
            pr["taken"] = pr.get("taken", 0.0) + min(0.2, 0.03 * s)
        elif el == "metallo":
            pr["pierce"] = pr.get("pierce", 0.0) + 0.04 * s
        elif el == "vento":
            pr["evade"] = min(0.4, pr.get("evade", 0.0) + 0.02 * s)
        elif el == "luce":
            pr["crit"] = pr.get("crit", 0.0) + 0.02 * s
    fx.p.atk_mult *= 1.0 + h
    names = ", ".join(EL_LABEL[e] for e in d)
    return [f"Gli elementi celesti ti avvolgono ({names})."]


def describe(conn, player) -> str:
    d = owned(conn)
    lines = ["✦ ELEMENTI CELESTI"]
    if d:
        for el, v in sorted(d.items(), key=lambda kv: -kv[1]["power"]):
            lines.append(f"  · {EL_LABEL[el]} Celeste — potenza {v['power']:.0f}, grado {grade(v['power'])} "
                         f"(assorbiti: {', '.join(v['names'][-3:])})")
        h = _harmony(d)
        if h:
            lines.append(f"  Armonia tra elementi: +{int(h * 100)}% di potenza in battaglia.")
    else:
        lines.append("  Non ne hai ancora assorbito nessuno.")
    ev = current_event(conn)
    if ev and not ev.get("taken"):
        lname = conn.execute("SELECT name FROM locations WHERE id=?;", (ev["loc"],)).fetchone()["name"]
        days = ev["until"] - tick_mod.get_tick(conn) // 120
        from engine.cli.loop import _first_step_toward
        step = _first_step_toward(conn, player.location_id, ev["loc"])
        lines.append(f"  Nel mondo: il {ev['name']} ({EL_LABEL[ev['el']]}) a {lname}, ancora {days} giorni"
                     + (f" — vai verso {step}." if step else " — è qui! ('elementi assorbi' dopo il guardiano)"))
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    if arg.strip().lower() in ("assorbi", "absorb", "prendi"):
        return absorb(conn, player)
    return describe(conn, player)
