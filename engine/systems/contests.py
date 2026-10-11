"""
GARE DEI MAESTRI D'ARTE — Torneo degli Alchimisti, Concorso dei Forgiatori, e gli altri.

Ogni ~30 giorni una città ospita una gara per una delle arti (alchimia, talismani, forgia,
formazioni, domatori). Se pratichi quell'arte puoi iscriverti: tre prove, ognuna contro un
maestro rivale. Conta il tuo livello, la tua dimora, il maestro nell'anello, gli elementi
celesti… e un po' di fortuna.

  gara                  la gara in corso (o la prossima)
  gara iscriviti        ti iscrivi (devi essere nella città che la ospita e praticare l'arte)
  gara prova            affronti la prova successiva

Chi vince diventa RE della sua arte («Re delle Pillole», «Gran Maestro della Forgia»…), e
ogni nuova vittoria aggiunge una corona: 2ª, 3ª, … senza fine.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "contest"
INTERVAL = 30
TITLES = {"alchimia": "Re delle Pillole", "talismani": "Sovrano dei Sigilli", "forgia": "Gran Maestro della Forgia",
          "formazioni": "Signore delle Formazioni", "domatore": "Re delle Bestie"}
NAMES = {"alchimia": "Torneo degli Alchimisti", "talismani": "Gara dei Maestri di Talismani",
         "forgia": "Concorso dei Forgiatori", "formazioni": "Sfida delle Formazioni", "domatore": "Raduno dei Domatori"}
STAGES = ["Prova del Fuoco", "Prova della Purezza", "Prova del Maestro"]


def current(conn) -> dict | None:
    c = state.get_json(conn, KEY)
    if c and tick_mod.get_tick(conn) // 120 <= c["end"]:
        return c
    return None


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import eras
    day = t // 120
    c = state.get_json(conn, KEY)
    if c and day > c["end"]:
        state.delete(conn, KEY)
        c = None
    interval = INTERVAL // 2 if eras.get(conn)["key"] == "scuole" else INTERVAL
    if c is None and day - state.get_int(conn, "contest_day", 5) >= interval:
        city = conn.execute("SELECT id, name FROM locations WHERE location_type='city' ORDER BY RANDOM() LIMIT 1;").fetchone()
        if not city:
            return []
        art = rng.choice(list(TITLES))
        state.set_json(conn, KEY, {"art": art, "loc": city["id"], "city": city["name"], "end": day + 4,
                                   "joined": False, "stage": 0, "done": False})
        state.set(conn, "contest_day", str(day))
        return [f"⚗ A {city['name']} si apre il {NAMES[art]}: quattro giorni di gare. ('gara')"]
    return []


def _score(conn, pid: int, rng) -> float:
    from engine.systems import professions, cave_abode, mentor_ring, celestial_elements
    from engine.core import entities
    c = current(conn)
    lv = professions.level(conn, pid, c["art"] if c else None)
    bonus = 1.0 + 0.05 * cave_abode.level(conn, pid, "alchimia") + mentor_ring.craft_bonus(conn) * 2 \
        + celestial_elements.craft_bonus(conn) * 2
    return lv * bonus * rng.uniform(0.8, 1.2)


def register(conn, player) -> str:
    from engine.systems import professions
    c = current(conn)
    if not c:
        return describe(conn, player)
    if player.location_id != c["loc"]:
        return f"Il {NAMES[c['art']]} si tiene a {c['city']}."
    if not professions.has(conn, c["art"]):
        return f"Per iscriverti devi conoscere l'arte: {c['art']} ('arti {c['art']}')."
    if c["joined"]:
        return "Sei già iscritto: 'gara prova'."
    c["joined"] = True
    state.set_json(conn, KEY, c)
    return f"Il tuo nome è sulla lista del {NAMES[c['art']]}. 'gara prova' per la {STAGES[0]}."


def trial(conn, player) -> str:
    from engine.systems import professions, sects, reputation
    from engine.simulation import world_tick
    c = current(conn)
    if not c or not c["joined"] or c["done"]:
        return describe(conn, player)
    if player.location_id != c["loc"]:
        return f"Le prove si tengono a {c['city']}."
    rng = random.Random(tick_mod.get_tick(conn) * 7 + c["stage"])
    lv = professions.level(conn, player.id, c["art"])
    opp = max(1, lv + c["stage"] + rng.randint(-2, 2)) * rng.uniform(0.85, 1.15)
    me = _score(conn, player.id, rng)
    world_tick.advance(conn, 24)
    st = STAGES[c["stage"]]
    professions.add_xp(conn, player.id, 3 + c["stage"] * 2, c["art"])
    if me < opp:
        c["done"] = True
        state.set_json(conn, KEY, c)
        reputation.adjust(conn, player.id, fame=1 + c["stage"])
        return f"{st}: il maestro rivale ti supera di un soffio. Esci dalla gara, ma hai imparato molto."
    c["stage"] += 1
    reward = 80 * c["stage"] * max(1, lv)
    sects.grant_resource(conn, "pietre_spirituali", reward, player.id)
    out = [f"{st}: superata! (+{reward} pietre)"]
    if c["stage"] >= len(STAGES):
        c["done"] = True
        n = state.get_int(conn, f"contest_wins_{c['art']}", 0) + 1
        state.set(conn, f"contest_wins_{c['art']}", str(n))
        title = TITLES[c["art"]] + (f" ({n}ª corona)" if n > 1 else "")
        state.grant_title(conn, title)
        reputation.adjust(conn, player.id, fame=20)
        professions.give(conn, player.id, "nuclei_rari", 1 + n // 2)
        out.append(f"✦ Hai vinto il {NAMES[c['art']]}! ✧ Nuovo titolo: «{title}» ✧")
    else:
        out.append(f"Prossima: {STAGES[c['stage']]} ('gara prova').")
    state.set_json(conn, KEY, c)
    return "\n".join(out)


def describe(conn, player) -> str:
    c = current(conn)
    if not c:
        nxt = max(1, INTERVAL - (tick_mod.get_tick(conn) // 120 - state.get_int(conn, "contest_day", 5)))
        return f"Nessuna gara d'arte in corso: la prossima tra circa {nxt} giorni."
    st = "concluso" if c["done"] else (f"prossima prova: {STAGES[c['stage']]}" if c["joined"] else "non iscritto")
    return f"⚗ {NAMES[c['art']]} a {c['city']} — {st}. ('gara iscriviti', 'gara prova')"


def command(conn, player, arg: str) -> str:
    a = arg.strip().lower()
    if a in ("iscriviti", "join"):
        return register(conn, player)
    if a in ("prova", "trial"):
        return trial(conn, player)
    return describe(conn, player)
