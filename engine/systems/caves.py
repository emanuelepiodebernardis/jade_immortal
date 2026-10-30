"""
LE GROTTE (Aggiornamento 71) — un piccolo dungeon da percorrere stanza per stanza.

'grotta' in un luogo selvaggio (montagna, rovine, zona proibita, foresta, grotta…) apre l'ingresso. Ogni
grotta ha 5-7 stanze; a ogni passo scegli tra due passaggi, con un indizio di cosa c'è oltre:

  ⚔ guardiano   un duello (le stesse carte: tipi, stati, intento) — vinci e prosegui
  ⚠ trappola    una prova di agilità o di intelletto: fallisci e perdi VIGORE
  ❓ enigma     una domanda della tradizione dei coltivatori: la risposta giusta apre un premio
  ✦ tesoro      un forziere
  💧 sorgente   recuperi vigore, qi e spirito
  ☯ altare      offri qi in cambio di una benedizione per il resto della grotta (o rischi)
  ♛ custode     l'ultima stanza: un boss, con tre fasi — il tesoro più grande, spesso equipaggiamento

Il VIGORE (100) è la tua tenuta dentro la grotta: se arriva a zero, svieni e vieni trascinato fuori ferito.
Puoi uscire quando vuoi ('grotta esci') tenendo ciò che hai trovato. Una grotta al giorno per luogo.
Tutto passa per le scene (scelte cliccabili) e per il duello: nessun sistema nuovo da imparare.
Per aggiungere un tipo di stanza: una riga in ROOMS e una funzione _room_<tipo>.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "cave"
WILD = {"mountain", "ruin", "forbidden_zone", "forest", "cave", "wilderness", "lake"}
ROOMS = {"guardiano": ("⚔", "senti un respiro pesante, e il clangore del metallo"),
         "trappola": ("⚠", "il pavimento è segnato da rune sbiadite"),
         "enigma": ("❓", "una voce antica sussurra una domanda"),
         "tesoro": ("✦", "un bagliore dorato filtra dalle crepe"),
         "sorgente": ("💧", "senti scorrere acqua fresca"),
         "altare": ("☯", "un odore di incenso, e un silenzio sacro")}
WEIGHTS = {"guardiano": 30, "trappola": 18, "enigma": 14, "tesoro": 14, "sorgente": 12, "altare": 12}
NAMES = ["Grotta del Drago Addormentato", "Caverna delle Mille Ossa", "Antro della Luna Spezzata",
         "Grotta dell'Eremita Perduto", "Caverna del Qi Gelido", "Antro delle Rune Rosse",
         "Grotta della Fenice Spenta", "Labirinto del Serpente di Giada"]
# domanda, risposte, indice giusto
RIDDLES = [
    ("Quale elemento genera il fuoco, nel ciclo dei Cinque?", ["Il metallo", "Il legno", "L'acqua"], 1),
    ("Quale elemento spegne il fuoco?", ["La terra", "L'acqua", "Il vento"], 1),
    ("Cosa viene prima: la Fondazione o il Nucleo d'Oro?", ["La Fondazione", "Il Nucleo d'Oro", "Nascono insieme"], 0),
    ("Dove si raccoglie il qi nel corpo del coltivatore?", ["Nel cuore", "Nel dantian", "Nelle ossa"], 1),
    ("Il metallo taglia il legno. Cosa taglia il metallo?", ["Il fuoco", "La terra", "L'acqua"], 0),
    ("Cosa teme più di tutto chi attraversa una tribolazione?", ["Il fulmine", "Il demone interiore", "La fame"], 1),
    ("«Il Dao che si può dire non è l'eterno Dao.» Chi lo dice?", ["Laozi", "Un mercante", "Il Re dei Demoni"], 0),
    ("Cosa nutre il legno, nel ciclo dei Cinque?", ["L'acqua", "Il fuoco", "Il metallo"], 0),
    ("Quanti sono i meridiani principali del corpo?", ["Otto", "Dodici", "Venti"], 1),
    ("Una pillola troppo forte per il tuo regno…", ["ti fa sfondare subito", "può spezzarti i meridiani", "non fa nulla"], 1),
]


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict | None) -> None:
    if d is None:
        state.delete(conn, KEY)
    else:
        state.set_json(conn, KEY, d)


def _tier(conn, pid: int) -> int:
    from engine.simulation import cultivation
    return max(1, cultivation.realm_tier(conn, "player", pid) or 1)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _pick(rng: random.Random) -> str:
    return rng.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]


def enter(conn, player) -> str:
    from engine.systems import encounters, duel
    if get(conn):
        return show(conn, player)
    if encounters.pending(conn) or duel.get(conn):
        return "Prima risolvi ciò che hai davanti."
    loc = entities.get_location(conn, player.location_id)
    if not loc or (loc.location_type or "") not in WILD:
        return "Qui non ci sono grotte: cercale in montagna, tra le rovine, nelle foreste o nelle zone proibite."
    done = state.get_json(conn, KEY + "_done") or {}
    if done.get(str(player.location_id)) == _day(conn):
        return "Oggi hai già esplorato la grotta di questo luogo. Torna domani: le pietre si spostano."
    rng = random.Random(tick_mod.get_tick(conn) * 37 + player.location_id)
    depth = rng.randint(5, 7)
    d = {"name": rng.choice(NAMES), "loc": player.location_id, "depth": depth, "room": 0, "vigor": 100,
         "found": [], "bless": 0.0, "fork": None, "cur": None, "guard": None, "seed": rng.randint(1, 10 ** 6)}
    done[str(player.location_id)] = _day(conn)
    state.set_json(conn, KEY + "_done", done)
    _save(conn, d)
    return (f"🕳 Entri nella {d['name']}. Il buio ti avvolge; la torcia illumina {depth} stanze di pietra antica.\n"
            + _fork(conn, player, d))


def _fork(conn, player, d: dict) -> str:
    """Il bivio: due passaggi, ognuno con il suo indizio. L'ultima stanza è il custode."""
    from engine.systems import encounters
    rng = random.Random(d["seed"] + d["room"] * 17)
    if d["room"] >= d["depth"] - 1:
        d["fork"] = ["custode", "custode"]
        _save(conn, d)
        sc = {"key": "grotta", "title": f"{d['name']} — l'ultima sala", "event_type": "fortune", "sticky": True,
              "text": f"Vigore {d['vigor']}/100. Davanti a te una porta di bronzo coperta di sigilli: dietro, il CUSTODE "
                      f"della grotta.", "choices": [
                  {"label": "♛ Affronti il custode", "effects": {}, "command": "grotta vai 1"},
                  {"label": "Esci con ciò che hai trovato", "effects": {}, "command": "grotta esci"}]}
        return encounters.start_scene(conn, player, sc, force=True) or ""
    a, b = _pick(rng), _pick(rng)
    while b == a and rng.random() < 0.7:
        b = _pick(rng)
    d["fork"] = [a, b]
    _save(conn, d)
    sc = {"key": "grotta", "title": f"{d['name']} — stanza {d['room'] + 1}/{d['depth']}", "event_type": "fortune",
          "sticky": True, "text": f"Vigore {d['vigor']}/100" + (f" · benedizione +{int(d['bless'] * 100)}%" if d["bless"] else "")
          + ". Il passaggio si divide.",
          "choices": [
              {"label": f"Sinistra: {ROOMS[a][1]}", "effects": {}, "command": "grotta vai 1"},
              {"label": f"Destra: {ROOMS[b][1]}", "effects": {}, "command": "grotta vai 2"},
              {"label": "Esci dalla grotta con ciò che hai trovato", "effects": {}, "command": "grotta esci"}]}
    return encounters.start_scene(conn, player, sc, force=True) or ""


def go(conn, player, n: int) -> str:
    d = get(conn)
    if not d or not d.get("fork"):
        return "Non sei in una grotta. ('grotta' in un luogo selvaggio)"
    kind = d["fork"][0 if n == 1 else 1]
    d["fork"] = None
    d["cur"] = kind
    _save(conn, d)
    return {"guardiano": _room_guard, "custode": _room_boss, "trappola": _room_trap, "enigma": _room_riddle,
            "tesoro": _room_treasure, "sorgente": _room_spring, "altare": _room_altar}[kind](conn, player, d)


def _next(conn, player, d: dict, lines: list[str]) -> str:
    d["room"] += 1
    d["cur"] = None
    if d["vigor"] <= 0:
        return "\n".join(lines + _faint(conn, player, d))
    _save(conn, d)
    return "\n".join(lines) + "\n" + _fork(conn, player, d)


def _faint(conn, player, d: dict) -> list[str]:
    from engine.simulation import combat
    _save(conn, None)
    try:
        combat.apply_injury(conn, "player", player.id, "sfinimento", 0.15, tick_mod.get_tick(conn) + 240) \
            if hasattr(combat, "apply_injury") else None
    except Exception:                                  # noqa: BLE001
        pass
    return [f"Il vigore ti abbandona: svieni nel buio. Ti risvegli all'ingresso della {d['name']}, ammaccato. "
            f"Hai tenuto ciò che avevi trovato ({len(d['found'])} tesori)."]


# ---------------- le stanze ----------------
def _spawn_guard(conn, player, d: dict, boss: bool) -> str:
    from engine.systems import npc_factory, pursuers, duel, elites
    rng = random.Random(d["seed"] + d["room"] * 101)
    t = tick_mod.get_tick(conn)
    beast = rng.random() < 0.5 and not boss
    nm = (f"Custode {d['name'].split(' ', 1)[1]}" if boss else
          rng.choice(["Guardiano di Pietra", "Serpente delle Caverne", "Spettro del Coltivatore", "Lupo d'Ombra",
                      "Golem di Giada", "Pipistrello Vampiro"]) + f" {rng.randint(10, 99)}")
    nid = npc_factory.spawn(conn, rng, archetype="patriarca" if boss else "guardia", location_id=player.location_id,
                            tier=_tier(conn, player.id), stage=5, name=nm, traits={"courage": 90, "honor": 50},
                            tick=t)
    target = (0.95 if boss else 0.6 + 0.04 * d["room"]) * (1 - d["bless"] * 0.5)
    pursuers.fit(conn, player.id, nid, "campione", target=target)
    if boss:
        rk = elites.get(conn)
        rk["rank"][str(nid)] = "boss"
        elites._save(conn, rk)
    d["guard"] = nid
    _save(conn, d)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    return duel.start(conn, player, name, arena=True) or ""


def _room_guard(conn, player, d):
    return "⚔ Un guardiano ti sbarra il passo!\n" + _spawn_guard(conn, player, d, boss=False)


def _room_boss(conn, player, d):
    return "♛ La porta di bronzo si apre. Il CUSTODE della grotta si alza dal suo trono di ossa.\n" + \
        _spawn_guard(conn, player, d, boss=True)


def on_duel(conn, player, npc_id: int, outcome: str) -> list[str]:
    d = get(conn)
    if not d or d.get("guard") != npc_id:
        return []
    conn.execute("UPDATE npcs SET status='dead', location_id=NULL WHERE id=?;", (npc_id,))   # torna nella pietra
    boss = d.get("cur") == "custode"
    d["guard"] = None
    if outcome not in ("ucciso", "risparmiato", "sigillato"):
        d["vigor"] -= 40
        if d["vigor"] <= 0:
            return _faint(conn, player, d)
        _save(conn, d)
        return [f"Il guardiano ti respinge: perdi vigore ({d['vigor']}/100). Puoi riprovare un'altra strada.",
                _next(conn, player, d, [])]
    from engine.systems import rewards
    lines = ["Il guardiano si sbriciola in polvere di pietra."]
    if boss:
        lines.append(f"♛ Hai vinto il custode della {d['name']}! Il suo tesoro è tuo:")
        lines += ["  " + x for x in rewards.grant(conn, random.Random(d["seed"]), player, rank=1)]
        from engine.systems import gear
        it = gear.make(random.Random(d["seed"] + 7), _tier(conn, player.id), rar=random.Random(d["seed"]).choice(
            ["pregiata", "pregiata", "divina"]))
        lines.append(gear.add(conn, it))
        d["found"].append("custode")
        from engine.systems import chronicle
        try:
            chronicle.add(conn, "impresa", f"Espugni la {d['name']} e ne sconfiggi il custode.")
        except Exception:                              # noqa: BLE001
            pass
        _save(conn, None)
        lines.append(f"La grotta è tua. Esci alla luce con {len(d['found'])} tesori.")
        return lines
    if random.Random(npc_id).random() < 0.5:
        lines += ["  " + x for x in rewards.grant(conn, random.Random(npc_id), player, rank=3, n=1, stones=False)]
        d["found"].append("guardiano")
    return [_next(conn, player, d, lines)]


def _room_trap(conn, player, d):
    from engine.systems import attributes
    rng = random.Random(d["seed"] + d["room"] * 7)
    try:
        agi, intel = attributes.mult(conn, "AGI"), attributes.mult(conn, "INT")
    except Exception:                                  # noqa: BLE001
        agi = intel = 1.0
    kind = rng.choice(["frecce", "rune", "crollo"])
    stat = intel if kind == "rune" else agi
    p = min(0.85, 0.45 + 0.3 * (stat - 1.0) + d["bless"])
    ok = rng.random() < p
    txt = {"frecce": ("Dalle pareti scattano frecce avvelenate.", "Le schivi tutte con un balzo.", "Una ti prende alla spalla."),
           "rune": ("Le rune del pavimento si accendono.", "Leggi lo schema e passi sulle pietre giuste.", "Sbagli pietra: un'esplosione di qi."),
           "crollo": ("Il soffitto trema.", "Ti lanci oltre prima del crollo.", "Le pietre ti travolgono.")}[kind]
    lines = [f"⚠ {txt[0]} {txt[1] if ok else txt[2]}"]
    if not ok:
        loss = rng.randint(20, 35)
        d["vigor"] -= loss
        lines.append(f"  Vigore −{loss} ({max(0, d['vigor'])}/100).")
    return _next(conn, player, d, lines)


def _room_riddle(conn, player, d):
    from engine.systems import encounters
    rng = random.Random(d["seed"] + d["room"] * 13)
    q, opts, right = rng.choice(RIDDLES)
    d["riddle"] = right
    _save(conn, d)
    sc = {"key": "grotta", "title": f"{d['name']} — l'enigma", "event_type": "fortune", "sticky": True,
          "text": f"❓ Una statua di pietra apre gli occhi: «{q}»",
          "choices": [{"label": o, "effects": {}, "command": f"grotta rispondi {i + 1}"} for i, o in enumerate(opts)]}
    return encounters.start_scene(conn, player, sc, force=True) or ""


def answer(conn, player, n: int) -> str:
    d = get(conn)
    if not d or d.get("cur") != "enigma":
        return "Nessun enigma davanti a te."
    from engine.systems import rewards
    right = d.pop("riddle", 0)
    if n - 1 == right:
        lines = ["La statua china il capo: «Giusto.» Una nicchia si apre."]
        lines += ["  " + x for x in rewards.grant(conn, random.Random(d["seed"] + d["room"]), player, rank=2, n=1)]
        d["found"].append("enigma")
    else:
        d["vigor"] -= 15
        lines = [f"La statua tace. Una folata gelida ti attraversa: vigore −15 ({max(0, d['vigor'])}/100)."]
    return _next(conn, player, d, lines)


def _room_treasure(conn, player, d):
    from engine.systems import rewards
    lines = ["✦ Un forziere coperto di muschio. Dentro:"]
    lines += ["  " + x for x in rewards.grant(conn, random.Random(d["seed"] + d["room"] * 3), player,
                                             rank=2 if d["room"] >= 3 else 3, n=1)]
    d["found"].append("tesoro")
    return _next(conn, player, d, lines)


def _room_spring(conn, player, d):
    from engine.systems import qi as qimod, spirit as spmod
    d["vigor"] = min(100, d["vigor"] + 40)
    try:
        qimod.restore_fraction(conn, 0.5, player.id)
        spmod.restore_fraction(conn, 0.5, player.id) if hasattr(spmod, "restore_fraction") else None
    except Exception:                                  # noqa: BLE001
        pass
    return _next(conn, player, d, [f"💧 Una sorgente limpida. Bevi: vigore {d['vigor']}/100, qi e spirito ritornano."])


def _room_altar(conn, player, d):
    from engine.systems import encounters
    sc = {"key": "grotta", "title": f"{d['name']} — l'altare", "event_type": "fortune", "sticky": True,
          "text": "☯ Un altare di giada nera, con un incensiere ancora acceso. Qualcuno, un tempo, pregava qui.",
          "choices": [{"label": "Offri metà del tuo qi (benedizione: guardiani più deboli, trappole più facili)",
                       "effects": {}, "command": "grotta altare offri"},
                      {"label": "Prendi l'incensiere (forse un tesoro, forse una maledizione)", "effects": {},
                       "command": "grotta altare prendi"},
                      {"label": "Passi oltre in silenzio", "effects": {}, "command": "grotta altare passa"}]}
    return encounters.start_scene(conn, player, sc, force=True) or ""


def altar(conn, player, what: str) -> str:
    d = get(conn)
    if not d or d.get("cur") != "altare":
        return "Nessun altare davanti a te."
    from engine.systems import qi as qimod, rewards
    rng = random.Random(d["seed"] + d["room"] * 5)
    if what == "offri":
        try:
            qimod.spend(conn, qimod.get_qi(conn, player.id) // 2, player.id)
        except Exception:                              # noqa: BLE001
            pass
        d["bless"] = min(0.3, d["bless"] + 0.15)
        lines = [f"Il fumo sale dritto: l'altare accetta. Benedizione +{int(d['bless'] * 100)}%."]
    elif what == "prendi":
        if rng.random() < 0.55:
            lines = ["L'incensiere è d'oro antico."] + ["  " + x for x in rewards.grant(conn, rng, player, rank=2, n=1)]
            d["found"].append("altare")
        else:
            d["vigor"] -= 30
            lines = [f"Una maledizione ti morde le ossa: vigore −30 ({max(0, d['vigor'])}/100)."]
    else:
        lines = ["Chini il capo e passi oltre."]
    return _next(conn, player, d, lines)


def leave(conn, player) -> str:
    from engine.systems import encounters
    d = get(conn)
    if not d:
        return "Non sei in una grotta."
    _save(conn, None)
    encounters.clear(conn) if hasattr(encounters, "clear") else None
    return f"Risali verso la luce. Lasci la {d['name']} con {len(d['found'])} tesori."


def show(conn, player) -> str:
    d = get(conn)
    if not d:
        return enter(conn, player)
    if d.get("fork"):
        return _fork(conn, player, d)
    return f"Sei nella {d['name']}, stanza {d['room'] + 1}/{d['depth']}, vigore {d['vigor']}/100."


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub in ("", "entra", "esplora"):
        return enter(conn, player) if not get(conn) else show(conn, player)
    if sub == "vai" and len(p) > 1 and p[1].isdigit():
        return go(conn, player, int(p[1]))
    if sub == "rispondi" and len(p) > 1 and p[1].isdigit():
        return answer(conn, player, int(p[1]))
    if sub == "altare" and len(p) > 1:
        return altar(conn, player, p[1].lower())
    if sub in ("esci", "fuori"):
        return leave(conn, player)
    return "grotta — entra · grotta vai 1|2 · grotta esci"
