"""
IL MAESTRO NELL'ANELLO — l'anima di un antico coltivatore che vive in un anello.

Una volta per vita, frugando tra rovine o zone proibite, puoi trovare un anello arrugginito.
Se lo indossi, dentro c'è qualcuno: l'anima di un grande maestro caduto, debolissima.
  - Ti CONSIGLIA ('anello'): quanto sei pronto allo sfondamento, quale Dao allenare, chi hai
    davanti, dove sono le occasioni.
  - Lo NUTRI ('anello nutri'): nuclei di bestia e pietre lo fanno risvegliare di livello —
    senza fine. Ogni livello aiuta la tua coltivazione e le tue arti.
  - Ti PRESTA LA SUA FORZA ('anello forza'): nello scontro successivo combatte con te.
    Poi deve riposare (meno a ogni livello).
  - La sua STORIA si svela a poco a poco: al livello 6 colui che lo tradì viene a cercarlo.
    Vendicarlo (abbattere il traditore) gli permette di consegnarti la sua eredità.

  anello                 consiglio del maestro e stato dell'anello
  anello nutri [n]       lo nutri con n nuclei di bestia (e pietre)
  anello forza           prende il controllo per il prossimo scontro
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "mentor_ring"
_NAMES = ["il Vecchio Mo", "la Venerabile Lan", "il Patriarca Senza Volto", "il Vecchio Yu della Fiamma",
          "la Signora delle Mille Pillole", "il Santo Caduto Han"]
_PAST = {3: "«Un tempo ero il più grande alchimista delle Nove Province. Poi qualcuno di cui mi fidavo…» Tace.",
         6: "«Il mio discepolo mi avvelenò per il mio Dao. È ancora vivo, e sente che sono tornato.»",
         9: "«Ho atteso diecimila anni per qualcuno come te. Ora capisco perché il Cielo ti ha messo sul mio cammino.»"}


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def level(conn) -> int:
    d = get(conn)
    return int(d.get("level", 0)) if d else 0


def feed_need(lv: int) -> int:
    return 2 + lv * 2


def offer_scene(conn, rng, player) -> str | None:
    """Una volta per vita, in rovine o zone proibite: l'anello."""
    from engine.systems import encounters
    if get(conn) or state.flag(conn, "ring_seen", False) or encounters.pending(conn):
        return None
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    if not lt or lt["location_type"] not in ("ruin", "forbidden_zone"):
        return None
    if tick_mod.get_tick(conn) // 120 < 2 or rng.random() > 0.08:
        return None
    state.set(conn, "ring_seen", "1")
    sc = {"key": "anello_antico", "title": "Un anello nella polvere", "event_type": "fortune",
          "text": ("Tra le pietre crollate, un anello nero, arrugginito, senza alcun valore apparente. Eppure, "
                   "quando lo sfiori, senti un brivido — come se qualcuno ti avesse guardato."),
          "choices": [{"label": "Lo infili al dito", "effects": {"mentor_ring": True}},
                      {"label": "Lo lasci dov'è", "effects": {"text": "Lo lasci. Ti sembra di sentire un sospiro."}}]}
    return encounters.start_scene(conn, player, sc)


def awaken(conn, rng) -> list[str]:
    if get(conn):
        return []
    name = rng.choice(_NAMES)
    _save(conn, {"name": name, "level": 1, "fed": 0, "rest_until": 0, "traitor": None, "avenged": False})
    state.grant_title(conn, "Portatore dell'Anello")
    return [f"Una voce roca, nella tua testa: «Finalmente… un corpo caldo.» Nell'anello vive {name}, "
            f"un maestro di un'altra era. È debolissimo. ('anello' per parlargli)"]


def feed(conn, player, arg: str) -> str:
    from engine.systems import professions, sects
    d = get(conn)
    if not d:
        return "Non porti nessun anello."
    n = int(arg) if arg.strip().isdigit() else 1
    have = professions.material(conn, player.id, "nuclei")
    n = min(n, have)
    if n <= 0:
        return f"{_cap(d['name'])}: «Nuclei di bestia, ragazzo. Mi servono nuclei.» ('gather', caccia)"
    professions.spend(conn, player.id, {"nuclei": n})
    d["fed"] = d.get("fed", 0) + n
    out = [f"L'anello si scalda: {d['name']} beve l'essenza di {n} nuclei."]
    while d["fed"] >= feed_need(d["level"]):
        d["fed"] -= feed_need(d["level"])
        d["level"] += 1
        out.append(f"✦ {_cap(d['name'])} si risveglia di più: livello {d['level']}.")
        if d["level"] in _PAST:
            out.append(f"  {_PAST[d['level']]}")
        if d["level"] == 6 and not d.get("traitor"):
            out += _spawn_traitor(conn, player, d)
    _save(conn, d)
    return "\n".join(out)


def _spawn_traitor(conn, player, d: dict) -> list[str]:
    from engine.systems import npc_factory, bonds
    from engine.simulation import cultivation
    rng = random.Random(tick_mod.get_tick(conn) + 99)
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=None, tier=ptier + 1, stage=5,
                            traits={"honor": 5, "ambition": 95})
    d["traitor"] = nid
    bonds.add_bond(conn, player.id, nid, "nemesis", tick_mod.get_tick(conn), rng=rng,
                   reason="vuole l'anima del tuo maestro")
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    return [f"☠ Lontano, {nm} — il discepolo traditore — apre gli occhi: ha sentito il suo vecchio maestro. "
            "Verrà a cercarvi."]


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import items
    d = get(conn)
    if not d:
        return []
    out = []
    if d.get("traitor") and not d.get("avenged"):
        r = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["traitor"],)).fetchone()
        if r and r["status"] != "alive":
            d["avenged"] = True
            _save(conn, d)
            out.append(f"✦ {_cap(d['name'])}: «È finita. Grazie, ragazzo.» E ti consegna la sua eredità.")
            out += items.apply_effects(conn, t, rng, player.id, {"learn_technique": {
                "name": f"Eredità di {d['name']}", "magnitude": round(0.12 + 0.02 * d["level"], 3),
                "tech_key": "anello:eredita"}, "dao_key": "anima", "dao_gain": 10 + 2 * d["level"]})
            state.grant_title(conn, "Vendicatore del Maestro")
    return out


def cultivation_mult(conn) -> tuple[float, str]:
    lv = level(conn)
    if not lv:
        return 1.0, ""
    return 1.0 + 0.04 * lv, "la guida del maestro nell'anello"


def craft_bonus(conn) -> float:
    return 0.02 * level(conn)


def lend(conn, player) -> str:
    d = get(conn)
    if not d:
        return "Non porti nessun anello."
    day = tick_mod.get_tick(conn) // 120
    if day < d.get("rest_until", 0):
        return f"{_cap(d['name'])} riposa ancora: ha dato troppo l'ultima volta."
    state.set(conn, "ring_loan", "1")
    d["rest_until"] = day + max(1, 7 - d["level"] // 2)
    _save(conn, d)
    return f"{_cap(d['name'])}: «Lascia fare a me.» Nello scontro successivo, la sua anima guiderà le tue mani."


def combat(conn, fx) -> list[str]:
    d = get(conn)
    if not d or not state.get(conn, "ring_loan"):
        return []
    state.delete(conn, "ring_loan")
    fx.p.atk_mult *= 2.0 + 0.4 * d["level"]
    fx.p.prof["crit"] = fx.p.prof.get("crit", 0.0) + 0.1
    return [f"✦ {_cap(d['name'])} prende il controllo: per un istante combatte un maestro di diecimila anni fa!"]


def advise(conn, player) -> str:
    from engine.simulation import cultivation
    from engine.systems import dao_training, secret_realms, beasts, perception
    d = get(conn)
    if not d:
        return "Non porti nessun anello."
    lines = [f"💍 {_cap(d['name'])} (livello {d['level']}, nutrimento {d.get('fed', 0)}/{feed_need(d['level'])} nuclei)"]
    rec = cultivation.get_record(conn, "player", player.id)
    if rec:
        st = rec["stage"] or 1
        lines.append(f"  «Sei allo strato {st}: " + ("tenta lo sfondamento, sei pronto." if st >= 10 and rec["progress"] >= 1
                                                    else f"ti manca ancora {int((1 - rec['progress']) * 100)}% di questo strato.»"))
    rows = dao_training.trainable_daos(conn, player.id)
    if rows:
        weakest = min(rows, key=lambda r: r["comprehension"])
        lines.append(f"  «Il tuo Dao più debole è {weakest['name']}: è lì che c'è più da guadagnare.»")
    here = conn.execute("SELECT id, name FROM npcs WHERE location_id=? AND status='alive' LIMIT 3;",
                        (player.location_id,)).fetchall()
    for r in here:
        lines.append(f"  «{r['name']}? {perception.relative_strength(conn, player.id, r['id'])}.»")
    if d["level"] >= 3:
        rr = secret_realms.current(conn)
        if rr:
            lines.append(f"  «Sento un reame segreto aperto: {rr['name']}. Vai.»")
        for b in beasts.active_rare(conn)[:1]:
            lines.append(f"  «C'è una bestia rara in giro: {b['name']}.»")
    if not d.get("avenged") and d["level"] >= 6:
        lines.append("  «Il traditore ci cerca. Diventa forte, poi trovalo.»")
    lines.append("  ('anello nutri [n]' per risvegliarlo; 'anello forza' per il suo aiuto in battaglia)")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    if sub in ("nutri", "feed"):
        return feed(conn, player, parts[1] if len(parts) > 1 else "1")
    if sub in ("forza", "aiuto", "help"):
        return lend(conn, player)
    return advise(conn, player)
