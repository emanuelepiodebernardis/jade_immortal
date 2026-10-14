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
  - La sua STORIA è un arco in quattro capitoli (soul_arcs.py, trame in intrigue_data3.py):
      liv. 3   il Legno Nutrianime: da allora ogni nucleo vale doppio
      liv. 6   il discepolo traditore: vendetta (la sua eredità) o perdono
      liv. 8   il Palazzo delle Anime lo strappa dall'anello: finché non lo liberi l'anello è muto
      liv. 10  un corpo nuovo: rinasce e cammina accanto a te come maestro, oppure, se lo lasci
               solo nella notte della rinascita, prova a prendersi il tuo corpo
  - Quando l'anello resta VUOTO (il maestro è rinato, perduto o spezzato) può accogliere un'altra
    anima: l'anima di un anziano o di un coltivatore forte che hai appena abbattuto
    ('anello accogli'). Con la nuova anima la storia ricomincia: ognuno ha un passato.

  anello                 consiglio del maestro e stato dell'anello
  anello nutri [n]       lo nutri con n nuclei di bestia (e pietre)
  anello forza           prende il controllo per il prossimo scontro
  anello accogli         un'anima appena liberata da un nemico caduto entra nell'anello vuoto
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


def _di(name: str) -> str:
    """«di» con l'articolo giusto: del Vecchio Mo, della Venerabile Lan, di Feng Ying."""
    low = name.lower()
    for art, prep in (("il ", "del "), ("la ", "della "), ("lo ", "dello "), ("l'", "dell'")):
        if low.startswith(art):
            return prep + name[len(art):]
    return "di " + name


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
    if d.get("gone"):
        return "L'anello è vuoto. ('anello accogli' dopo aver abbattuto un coltivatore forte)"
    if d.get("captive"):
        return "L'anello è freddo e muto: il Palazzo delle Anime ha portato via il tuo maestro."
    n = int(arg) if arg.strip().isdigit() else 1
    have = professions.material(conn, player.id, "nuclei")
    n = min(n, have)
    if n <= 0:
        return f"{_cap(d['name'])}: «Nuclei di bestia, ragazzo. Mi servono nuclei.» ('gather', caccia)"
    professions.spend(conn, player.id, {"nuclei": n})
    d["fed"] = d.get("fed", 0) + n * (2 if d.get("wood") else 1)
    out = [f"L'anello si scalda: {d['name']} beve l'essenza di {n} nuclei"
           + (" (il Legno Nutrianime la raddoppia)." if d.get("wood") else ".")]
    while d["fed"] >= feed_need(d["level"]):
        d["fed"] -= feed_need(d["level"])
        d["level"] += 1
        out.append(f"✦ {_cap(d['name'])} si risveglia di più: livello {d['level']}.")
        if d["level"] in _PAST and d.get("gen", 1) == 1:
            out.append(f"  {_PAST[d['level']]}")
    _save(conn, d)
    return "\n".join(out)


def _spawn_traitor(conn, player, d: dict) -> list[str]:  # (usato dal capitolo 2)
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
                "name": f"Eredità {_di(d['name'])}", "magnitude": round(0.12 + 0.02 * d["level"], 3),
                "tech_key": "anello:eredita"}, "dao_key": "anima", "dao_gain": 10 + 2 * d["level"]})
            state.grant_title(conn, "Vendicatore del Maestro")
    return out


def active(conn) -> bool:
    """L'anima c'è ed è nell'anello (non rapita, non partita)."""
    d = get(conn)
    return bool(d) and not d.get("gone") and not d.get("captive")


def cultivation_mult(conn) -> tuple[float, str]:
    lv = level(conn) if active(conn) else 0
    if not lv:
        return 1.0, ""
    return 1.0 + 0.04 * lv, "la guida del maestro nell'anello"


def craft_bonus(conn) -> float:
    return 0.02 * level(conn) if active(conn) else 0.0


def lend(conn, player) -> str:
    d = get(conn)
    if not d:
        return "Non porti nessun anello."
    if not active(conn):
        return "Nell'anello non c'è nessuno che possa combattere con te."
    day = tick_mod.get_tick(conn) // 120
    if day < d.get("rest_until", 0):
        return f"{_cap(d['name'])} riposa ancora: ha dato troppo l'ultima volta."
    state.set(conn, "ring_loan", "1")
    d["rest_until"] = day + max(1, 7 - d["level"] // 2)
    _save(conn, d)
    return f"{_cap(d['name'])}: «Lascia fare a me.» Nello scontro successivo, la sua anima guiderà le tue mani."


def combat(conn, fx) -> list[str]:
    d = get(conn)
    if not d or not state.get(conn, "ring_loan") or not active(conn):
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
    from engine.systems import soul_arcs
    if d.get("gone"):
        cand = soul_candidate(conn)
        return ("💍 L'anello è vuoto. " + {"rinato": f"{_cap(d['name'])} cammina ora nel mondo con un corpo suo.",
                                          "perduto": f"{_cap(d['name'])} è rimasto al Palazzo delle Anime.",
                                          "spezzato": f"{_cap(_di(d['name']))} restano solo i ricordi, dentro di te."}.get(d["gone"], "")
                + ("\n  Un'anima vaga ancora qui: " + cand["name"] + ". ('anello accogli')" if cand else
                   "\n  Può accogliere l'anima di un coltivatore forte appena abbattuto ('anello accogli')."))
    if d.get("captive"):
        return ("💍 L'anello è freddo. Il Palazzo delle Anime tiene prigioniero " + d["name"] + ". "
                + soul_arcs.status_line(conn, "anello"))
    lines = [f"💍 {_cap(d['name'])} (livello {d['level']}, nutrimento {d.get('fed', 0)}/{feed_need(d['level'])} nuclei"
             + (", Legno Nutrianime" if d.get("wood") else "") + ")",
             "  " + soul_arcs.status_line(conn, "anello")]
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
    lines.append("  ('anello nutri [n]' per risvegliarlo; 'anello forza' per il suo aiuto in battaglia)")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    if sub in ("nutri", "feed"):
        return feed(conn, player, parts[1] if len(parts) > 1 else "1")
    if sub in ("forza", "aiuto", "help"):
        return lend(conn, player)
    if sub in ("accogli", "anima", "ospita"):
        return host(conn, player)
    return advise(conn, player)


# ---------------------------------------------------------------- l'arco (soul_arcs) e le anime nuove

def arc_level(conn) -> int | None:
    d = get(conn)
    if not d or d.get("gone"):
        return None
    if d.get("captive"):
        return d["level"]                          # il capitolo del Palazzo continua anche ad anello muto
    return d["level"]


def names(conn) -> dict:
    d = get(conn) or {}
    nm = d.get("name", "il maestro")
    return {"maestro": nm, "Maestro": _cap(nm), "di_maestro": _di(nm)}


def branches(conn, plot: str) -> list:
    return []


def prepare(conn, player, plot: str):
    d = get(conn)
    if plot == "anello_traditore":
        if d.get("avenged"):
            return False                           # vecchi salvataggi: la vendetta c'è già stata
        alive = d.get("traitor") and conn.execute("SELECT 1 FROM npcs WHERE id=? AND status='alive';",
                                                  (d["traitor"],)).fetchone()
        if not alive:
            _spawn_traitor(conn, player, d)
            _save(conn, d)
        state.set(conn, "vaso_traditore", str(d["traitor"]))
    if plot == "anello_palazzo":
        d["captive"] = True                        # lo strappano dall'anello: l'anello tace
        _save(conn, d)
    return True


def _legacy(conn, player, d: dict, mag: float, dao: int, label: str) -> list[str]:
    from engine.systems import items
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + 4421)
    return items.apply_effects(conn, t, rng, player.id, {"learn_technique": {
        "name": f"{label} {_di(d['name'])}", "magnitude": round(mag, 3), "tech_key": f"anello:{label.lower()}"},
        "dao_key": "anima", "dao_gain": dao})


def on_chapter(conn, player, plot: str, outcome: str, closed: bool) -> list[str]:
    d = get(conn)
    if not d:
        return []
    out = []
    if plot == "anello_legno" and closed:
        d["wood"] = True
        d["level"] += 1
        out.append(f"✦ Il Legno Nutrianime avvolge l'anello. {_cap(d['name'])} sale al livello {d['level']}, "
                   "e d'ora in poi ogni nucleo vale doppio.")
    elif plot == "anello_traditore" and closed:
        d["avenged"] = True
        if outcome == "perdono":
            d["level"] += 1
            out.append(f"✦ {_cap(d['name'])} non porta più rancore: la sua anima si fa più leggera (livello {d['level']}).")
            out += _legacy(conn, player, d, 0.10 + 0.015 * d["level"], 8 + 2 * d["level"], "Perdono")
            state.grant_title(conn, "Colui che Sciolse un Rancore")
        else:
            out.append(f"✦ {_cap(d['name'])}: «È finita. Grazie, ragazzo.» E ti consegna la sua eredità.")
            out += _legacy(conn, player, d, 0.12 + 0.02 * d["level"], 10 + 2 * d["level"], "Eredità")
            state.grant_title(conn, "Vendicatore del Maestro")
    elif plot == "anello_palazzo":
        if outcome == "abbandonato":
            d["captive"] = False
            d["gone"] = "perduto"
            out.append(f"L'anello resta vuoto. Da qualche parte, sulla montagna, una lanterna si spegne.")
        elif closed:
            d["captive"] = False
            d["level"] += 2
            out.append(f"✦ {_cap(d['name'])} torna nell'anello. Nella prigione ha divorato le catene del Palazzo: "
                       f"ora è al livello {d['level']}.")
            state.grant_title(conn, "Colui che Sfidò il Palazzo delle Anime")
        else:
            out.append(f"{_cap(d['name'])} è ancora prigioniero. L'anello resta freddo.")
    elif plot == "anello_corpo" and closed:
        if outcome == "rinato":
            out += _reborn(conn, player, d)
        else:
            d["gone"] = "spezzato"
            out += _legacy(conn, player, d, 0.18 + 0.02 * d["level"], 20 + 2 * d["level"], "Ricordi")
            out.append("Nel tuo mare della coscienza galleggiano diecimila anni di ricordi non tuoi.")
    _save(conn, d)
    return out


def _reborn(conn, player, d: dict) -> list[str]:
    from engine.systems import npc_factory, bonds
    from engine.simulation import cultivation
    rng = random.Random(tick_mod.get_tick(conn) + 777)
    pt = cultivation.realm_tier(conn, "player", player.id) or 1
    nm = _cap(d["name"]).replace("Il ", "").replace("La ", "")
    if conn.execute("SELECT 1 FROM npcs WHERE name=?;", (nm,)).fetchone():
        nm = f"{nm} Rinato"
    nid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=player.location_id, tier=pt + 1, stage=3,
                            name=nm, traits={"honor": 85, "loyalty": 100, "compassion": 60},
                            tick=tick_mod.get_tick(conn))
    bonds.add_bond(conn, player.id, nid, "master", tick_mod.get_tick(conn), rng=rng, reason="gli hai ridato un corpo")
    d["gone"] = "rinato"
    d["reborn_npc"] = nid
    state.grant_title(conn, "Colui che Ridiede un Corpo al Maestro")
    out = [f"✦ {nm} è vivo, con un corpo suo. Ora è il tuo maestro nel mondo: puoi trovarlo, parlargli, "
           "combattere al suo fianco."]
    out += _legacy(conn, player, d, 0.20 + 0.02 * d["level"], 25 + 2 * d["level"], "Lascito")
    out.append("L'anello resta vuoto, ma caldo: potrà accogliere un'altra anima ('anello accogli').")
    return out


# --- le anime nuove: l'anello vuoto accoglie l'anima di chi hai appena abbattuto

SOUL_KEY = "ring_soul_candidate"


def on_kill(conn, t: int, rng, player, npc_id: int) -> list[str]:
    """Un coltivatore forte cade: per un giorno la sua anima vaga, e un anello vuoto può accoglierla."""
    d = get(conn)
    if not d or not d.get("gone"):
        return []
    from engine.simulation import cultivation
    r = conn.execute("SELECT name, archetype, kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not r or (r["kind"] not in (None, "human")):
        return []
    nt = cultivation.realm_tier(conn, "npc", npc_id) or 1
    pt = cultivation.realm_tier(conn, "player", player.id) or 1
    if nt < pt and r["archetype"] != "anziano":
        return []
    state.set_json(conn, SOUL_KEY, {"id": npc_id, "name": r["name"], "day": t // 120})
    return [f"💍 L'anello vuoto si scalda: l'anima di {r['name']} gli gira intorno. ('anello accogli')"]


def soul_candidate(conn) -> dict | None:
    c = state.get_json(conn, SOUL_KEY, None)
    if not c or tick_mod.get_tick(conn) // 120 - c.get("day", -99) > 1:
        return None
    return c


def host(conn, player) -> str:
    d = get(conn)
    if not d:
        return "Non porti nessun anello."
    if not d.get("gone"):
        return f"Nell'anello c'è già {d['name']}."
    c = soul_candidate(conn)
    if not c:
        return "Nessuna anima vaga qui. Abbatti un coltivatore forte, e il giorno stesso l'anello potrà accoglierlo."
    state.delete(conn, SOUL_KEY)
    gen = d.get("gen", 1) + 1
    nd = {"name": c["name"], "level": 1, "fed": 0, "rest_until": 0, "traitor": None, "avenged": False,
          "gen": gen, "wood": d.get("wood", False)}
    _save(conn, nd)
    from engine.systems import soul_arcs
    soul_arcs.reset(conn, "anello")
    return (f"💍 L'anima di {c['name']} entra nell'anello. All'inizio urla, poi tace, poi parla: «Va bene. Hai vinto tu. "
            "Ma anche io ho una storia, e qualcuno che mi cerca.» (una nuova anima: la sua storia ricomincia)")
