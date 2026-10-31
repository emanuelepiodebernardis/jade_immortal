"""
LE PROVE DEL CIELO (Aggiornamento 79) — sfide scelte da te, più forti di te, con premi alti.

  prova_cielo            le tre prove e quando puoi ritentarle
  prova_cielo 1|2|3      Bronzo (un avversario ~15% più forte), Argento (~40%), Oro (~80%)

Sono duelli d'arena: se perdi non muori, e la sconfitta ti insegna qualcosa (vedi dao_insight.after_defeat).
Se vinci: pietre, un Frutto del Dao, e con l'Oro uno scorcio di una via nuova e un titolo. Ogni prova si ritenta
dopo sette giorni. Una sfida vera anche quando il resto del mondo non ti tiene più testa.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "heaven_trials"
TRIALS = {1: ("Prova del Bronzo", 1.15, 1), 2: ("Prova d'Argento", 1.4, 2), 3: ("Prova d'Oro", 1.8, 4)}
COOLDOWN = 7


def _get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"last": {}, "fighter": None, "grade": 0, "wins": {}}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def describe(conn) -> str:
    d = _get(conn)
    day = _day(conn)
    lines = ["⛩ LE PROVE DEL CIELO — duelli d'arena contro chi è più forte di te (perdere non uccide)."]
    for g, (name, ratio, _m) in TRIALS.items():
        last = d["last"].get(str(g))
        wait = 0 if last is None else max(0, COOLDOWN - (day - int(last)))
        w = d["wins"].get(str(g), 0)
        lines.append(f"  {g}. {name} — avversario ~{int((ratio - 1) * 100)}% più forte · vinte {w}"
                     + (f" · ritenta tra {wait} giorni" if wait else " · pronta"))
    lines.append("Scrivi 'prova_cielo <1-3>'. Premi: pietre e Frutti del Dao; l'Oro dà anche uno scorcio di una via nuova.")
    return "\n".join(lines)


def start(conn, player, arg: str) -> str:
    from engine.systems import npc_factory, pursuers, duel, encounters
    from engine.simulation import cultivation
    a = (arg or "").strip()
    if not a.isdigit() or int(a) not in TRIALS:
        return describe(conn)
    g = int(a)
    d = _get(conn)
    day = _day(conn)
    last = d["last"].get(str(g))
    if last is not None and day - int(last) < COOLDOWN:
        return f"Il Cielo non ti riceve ancora: la {TRIALS[g][0]} si ritenta tra {COOLDOWN - (day - int(last))} giorni."
    if encounters.pending(conn) or duel.get(conn):
        return "Prima risolvi ciò che hai davanti."
    name, ratio, _m = TRIALS[g]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 31 + g)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, rng, archetype="patriarca" if g == 3 else "discepolo", location_id=player.location_id,
                            tier=tier, stage=8, traits={"pride": 80, "courage": 95}, tick=t)
    pursuers.fit(conn, player.id, nid, "campione", target=ratio)
    d["last"][str(g)] = day
    d["fighter"], d["grade"] = nid, g
    _save(conn, d)
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    return (f"⛩ {name.upper()}. Il cielo si apre in un cerchio di luce: ne scende {nm}, un'eco di qualcuno che un tempo "
            f"camminò sulla tua stessa via. Ti aspetta, immobile.\n" + (duel.start(conn, player, nm, arena=True) or ""))


def on_duel(conn, player, npc_id: int, outcome: str) -> list[str]:
    from engine.systems import items, sects, dao_training, dao_insight, dao_laws
    from engine.simulation import cultivation
    d = _get(conn)
    if npc_id is None or d.get("fighter") != npc_id:
        return []
    g = d.get("grade") or 1
    d["fighter"] = None
    conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (npc_id,))     # l'eco torna in cielo
    name, _r, mult = TRIALS[g]
    if outcome not in ("ucciso", "risparmiato", "sigillato"):
        _save(conn, d)
        return [f"⛩ La {name} ti respinge. L'eco svanisce senza una parola; tra {COOLDOWN} giorni potrai ritentare."]
    d["wins"][str(g)] = d["wins"].get(str(g), 0) + 1
    _save(conn, d)
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + npc_id)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    st = 150 * tier * mult
    sects.grant_resource(conn, "pietre_spirituali", st, player.id)
    out = [f"⛩ Superi la {name}! +{st} pietre e un Frutto del Dao:"]
    rows = dao_training.trainable_daos(conn, player.id)
    if rows:
        out += items.apply_effects(conn, t, rng, player.id, {"dao_key": rows[0]["dao_key"], "dao_gain": 5 * mult})
    if g == 3:
        cand = sorted(k for k in dao_laws.BY_KEY if not dao_laws._has(conn, k, player.id)
                      and dao_laws.BY_KEY[k][4][0] != "risveglio")
        if cand:
            dd = dao_insight._data(conn)
            out.append(dao_insight.glimpse(conn, rng.choice(cand), dd, player.id))
            dao_insight._save(conn, dd)
        if state.grant_title(conn, "Prescelto del Cielo"):
            out.append("✧ Nuovo titolo: «Prescelto del Cielo»")
    return out


def menu_section(conn, player):
    from engine.systems.menus import act, section
    d = _get(conn)
    day = _day(conn)
    acts = []
    for g, (name, _r, _m) in TRIALS.items():
        last = d["last"].get(str(g))
        ok = last is None or day - int(last) >= COOLDOWN
        acts.append(act(name, f"prova_cielo {g}", ok, "ritenta più avanti"))
    return section("Le Prove del Cielo", ["Duelli d'arena contro chi è più forte di te: perdere non uccide, vincere "
                                          "paga bene."], acts, icon="⛩", img="scene/giudizio")
