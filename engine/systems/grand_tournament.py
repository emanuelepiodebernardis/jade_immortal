"""
IL GRAN TORNEO DELL'ASCESA (Aggiornamento 65) — ogni novanta giorni, i prodigi di tutto il mondo.

Lo spunto viene dall'Ascension Tournament di Tale of Immortal, la grande conferenza che torna a
intervalli regolari e mette in palio frutti del Dao. Qui: ogni 90 giorni il torneo resta aperto 7 giorni.
Quattro turni, quattro duelli contro prodigi sempre più forti (misurati su di te). Vinci e passi al
turno dopo; perdi e sei fuori fino al prossimo torneo.

Premi a ogni turno superato: pietre e un FRUTTO DEL DAO (comprensione del tuo Dao migliore). Al
campione: un tesoro, fama, e il titolo «Campione del Gran Torneo» (con il numero delle corone).

  torneo            il torneo: quando, a che turno sei
  torneo combatti   il duello del turno
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "grand_tournament"
EVERY, OPEN = 90, 7
RATIOS = (0.85, 1.0, 1.15, 1.3)
ROUND_NAME = ("Ottavi", "Quarti", "Semifinale", "Finale")


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def edition(day: int) -> int:
    return day // EVERY


def is_open(day: int) -> bool:
    return day >= EVERY and day % EVERY < OPEN


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"ed": -1, "round": 0, "out": False, "fighter": None, "crowns": 0}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _cur(conn) -> dict:
    d = get(conn)
    ed = edition(_day(conn))
    if d["ed"] != ed:
        d.update({"ed": ed, "round": 0, "out": False, "fighter": None})
    return d


def status_line(conn) -> str:
    day = _day(conn)
    if not is_open(day):
        nxt = (edition(day) + 1) * EVERY
        return f"Il prossimo Gran Torneo apre tra {nxt - day} giorni."
    d = _cur(conn)
    left = OPEN - day % EVERY
    if d["out"]:
        return f"Sei fuori da questo torneo (chiude tra {left} giorni)."
    if d["round"] >= len(RATIOS):
        return "Hai vinto questo Gran Torneo."
    return f"Il Gran Torneo è aperto ancora {left} giorni: ti aspetta {ROUND_NAME[d['round']]}."


def fight(conn, player) -> str:
    from engine.systems import npc_factory, pursuers, duel, encounters
    from engine.simulation import cultivation
    day = _day(conn)
    if not is_open(day):
        return status_line(conn)
    if encounters.pending(conn) or duel.get(conn):
        return "Prima risolvi ciò che hai davanti."
    d = _cur(conn)
    if d["out"] or d["round"] >= len(RATIOS):
        return status_line(conn)
    rng = random.Random(tick_mod.get_tick(conn) + d["round"] * 13)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=player.location_id, tier=tier, stage=6,
                            traits={"pride": 90, "courage": 90, "ambition": 90}, tick=tick_mod.get_tick(conn))
    pursuers.fit(conn, player.id, nid, "campione", target=RATIOS[d["round"]])
    d["fighter"] = nid
    _save(conn, d)
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    return (f"🏟 Gran Torneo dell'Ascesa — {ROUND_NAME[d['round']]}. Sull'arena sale {nm}, prodigio di un'altra "
            "regione. Il pubblico trattiene il fiato.\n" + (duel.start(conn, player, nm, arena=True) or ""))


def on_duel(conn, player, npc_id: int, outcome: str) -> list[str]:
    from engine.systems import items, sects, rewards, reputation, dao_training
    from engine.simulation import cultivation
    d = get(conn)
    if npc_id is None or d.get("fighter") != npc_id:
        return []
    d["fighter"] = None
    conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (npc_id,))       # torna alla sua regione
    if outcome not in ("ucciso", "risparmiato", "sigillato"):
        d["out"] = True
        _save(conn, d)
        return [f"🏟 Sei eliminato al turno «{ROUND_NAME[d['round']]}». Il prossimo Gran Torneo tra {EVERY} giorni."]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + npc_id)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    st = 80 * tier * (d["round"] + 1)
    sects.grant_resource(conn, "pietre_spirituali", st, player.id)
    out = [f"🏟 Vinci {ROUND_NAME[d['round']].lower()}! +{st} pietre e un Frutto del Dao:"]
    rows = dao_training.trainable_daos(conn, player.id)
    if rows:
        out += items.apply_effects(conn, t, rng, player.id, {"dao_key": rows[0]["dao_key"], "dao_gain": 4 + 2 * d["round"]})
    d["round"] += 1
    if d["round"] >= len(RATIOS):
        d["crowns"] = d.get("crowns", 0) + 1
        title = "Campione del Gran Torneo" + (f" ({d['crowns']}ª corona)" if d["crowns"] > 1 else "")
        state.grant_title(conn, title)
        reputation.adjust(conn, player.id, fame=40)
        out.append(f"✦ SEI IL CAMPIONE DEL GRAN TORNEO DELL'ASCESA. Titolo: «{title}». Il tesoro del campione:")
        out += rewards.grant(conn, rng, player, rank=1, kinds=["tesoro", "manuale"], n=2)
    else:
        out.append(f"Prossimo turno: {ROUND_NAME[d['round']]} ('torneo combatti').")
    _save(conn, d)
    return out


def menu_section(conn, player):
    from engine.systems.menus import act, section
    day = _day(conn)
    d = _cur(conn)
    ok = is_open(day) and not d["out"] and d["round"] < len(RATIOS)
    return section("Gran Torneo dell'Ascesa", [status_line(conn), "Ogni 90 giorni, per 7 giorni: quattro duelli, "
                                               f"frutti del Dao a ogni turno. Corone vinte: {d.get('crowns', 0)}."],
                   [act(f"Combatti: {ROUND_NAME[min(d['round'], 3)]}", "torneo combatti", ok,
                        "il torneo non è aperto" if not is_open(day) else "non sei più in gara", main=ok)], icon="🏟", img="scene/torneo")


def command(conn, player, arg: str) -> str:
    if (arg or "").strip().lower().startswith(("combatti", "duello", "sfida")):
        return fight(conn, player)
    return "🏟 " + status_line(conn)
