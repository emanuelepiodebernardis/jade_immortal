"""
PRIGIONIA E FUGA — quando la forza non basta, serve l'astuzia.

A volte la storia ti fa cadere in mano ai nemici: un clan, una setta demoniaca, una prigione
sotterranea. Finché sei prigioniero non puoi viaggiare (né col pilota automatico). Per
fuggire servono tre passi, ognuno una scena:
  1. studiare le guardie      (istinto)
  2. trovare un alleato        (un altro prigioniero: se fuggite insieme, viaggerà con te)
  3. evadere                   (combatti il carceriere, o sgattaiola via)
Ogni giorno di prigionia pesa sul cuore del Dao; ogni fuga riuscita ti lascia più forte.

  evadi        il passo successivo della fuga
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "captivity"


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def active(conn) -> bool:
    return bool(get(conn))


def imprison(conn, player, captor: str) -> str:
    loc = conn.execute("SELECT id, name FROM locations WHERE location_type IN ('forbidden_zone','ruin') AND id<>? "
                       "ORDER BY RANDOM() LIMIT 1;", (player.location_id,)).fetchone()
    if not loc:
        return ""
    conn.execute("UPDATE players SET location_id=? WHERE id=?;", (loc["id"], player.id))
    state.set_json(conn, KEY, {"captor": captor, "loc": loc["id"], "step": 0, "ally": None,
                               "since": tick_mod.get_tick(conn) // 120})
    return (f"⛓ Ti risvegli in catene, in una prigione sotto {loc['name']}. Ti hanno preso: {captor}. "
            "Le guardie ridono. ('evadi' per cominciare a pianificare la fuga)")


def blocked_msg() -> str:
    return "Sei prigioniero: non puoi andartene così. ('evadi')"


def escape_step(conn, player) -> str:
    from engine.systems import encounters, npc_factory
    c = get(conn)
    if not c:
        return "Non sei prigioniero."
    if encounters.pending(conn):
        return encounters.render(conn, player)
    rng = random.Random(tick_mod.get_tick(conn) + c["step"])
    step = c["step"]
    if step == 0:
        sc = {"key": "fuga_guardie", "title": "Prigionia — le guardie", "event_type": "story",
              "text": "Per giorni osservi i turni delle guardie dalla fessura della cella.",
              "choices": [{"label": "Memorizzi ogni passo e ogni cambio", "check": {"stat": "istinto", "dc": 55},
                           "success": {"escape_step": 1, "text": "Hai trovato la falla: un'ora senza sorveglianza."},
                           "failure": {"heart": -2, "text": "Ti scoprono a spiare: ti spostano in una cella più buia."}}]}
    elif step == 1:
        sc = {"key": "fuga_alleato", "title": "Prigionia — un alleato", "event_type": "story",
              "text": "Nella cella accanto qualcuno bussa, piano: {npc}, prigioniero da anni.",
              "spawn": {"archetype": "vagabondo", "tier_offset": 0, "traits": {"loyalty": 90}},
              "choices": [{"label": "Gli proponi di fuggire insieme", "check": {"stat": "anima", "dc": 50},
                           "success": {"escape_step": 2, "escape_ally": True, "relation": 50,
                                       "text": "Accetta: «Ho aspettato qualcuno come te per dieci anni.»"},
                           "failure": {"escape_step": 2, "text": "Non si fida, ma ti indica il punto debole del muro."}},
                          {"label": "Fai da solo", "effects": {"escape_step": 2}}]}
    else:
        sc = {"key": "fuga_evasione", "title": "Prigionia — l'evasione", "event_type": "story",
              "text": "Notte. Il muro cede. Solo il carceriere, {npc}, si frappone tra te e la libertà.",
              "spawn": {"archetype": "guardia", "tier_offset": 0, "stage": 6},
              "choices": [{"label": "Lo affronti", "effects": {"escape_free": True}, "command": "attack {npc}"},
                          {"label": "Lo eviti strisciando nell'ombra", "check": {"stat": "istinto", "dc": 62},
                           "success": {"escape_free": True, "npc_leaves": True},
                           "failure": {"escape_free": True, "injury": 3, "command": "attack {npc}",
                                       "text": "Ti vede!"}}]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    return encounters.start_scene(conn, player, sc, force=True) or ""


def set_step(conn, n: int) -> None:
    c = get(conn)
    if c:
        c["step"] = max(c["step"], n)
        state.set_json(conn, KEY, c)


def set_ally(conn, npc_id) -> None:
    c = get(conn)
    if c and npc_id:
        c["ally"] = npc_id
        state.set_json(conn, KEY, c)


def free(conn, player) -> list[str]:
    from engine.systems import bonds, items, dao_heart
    c = get(conn)
    if not c:
        return []
    state.delete(conn, KEY)
    out = ["✦ Sei LIBERO. L'aria della notte non è mai stata così dolce."]
    t = tick_mod.get_tick(conn)
    if c.get("ally"):
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, c["ally"]))
        msg = bonds.add_bond(conn, player.id, c["ally"], "companion", t, reason="fuggiti insieme")
        if msg:
            out.append(msg)
    out += items.apply_effects(conn, t, random.Random(t), player.id, {"grow_soul": 2, "grow_strength": 2})
    out += dao_heart.adjust(conn, 8)
    n = state.get_int(conn, "escapes", 0) + 1
    state.set(conn, "escapes", str(n))
    title = "Evaso" if n == 1 else f"Nessuna Prigione lo Trattiene ({n})"
    state.grant_title(conn, title)
    out.append(f"✧ Nuovo titolo: «{title}» ✧")
    return out


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import dao_heart
    if not active(conn):
        return []
    return ["⛓ Un altro giorno in catene."] + dao_heart.adjust(conn, -1)
