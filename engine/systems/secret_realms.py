"""
REAMI SEGRETI (秘境) — luoghi che si aprono per pochi giorni e poi si richiudono.

Il cuore di tanti romanzi xianxia: a intervalli regolari un reame nascosto si apre in un
luogo selvaggio. Dentro: guardiani, tesori, discepoli delle sette rivali che competono per
gli stessi premi e, in fondo, una SALA DELL'EREDITÀ.

  - Ogni ~12 giorni se ne apre uno (annunciato all'alba); resta aperto 3 giorni.
  - Raggiungilo ed entra con 'enter'; poi 'delve' per scendere di piano in piano.
  - Ogni piano è una scena a scelta: guardiani da abbattere, scrigni, rivali di altre sette,
    pozze di Qi. Puoi uscire quando vuoi ('leave realm') tenendo ciò che hai preso.
  - All'ultimo piano, l'eredità: una tecnica, un frammento di Dao, una fiala di vita…
  - Il reame è scalato al tuo regno: più sali, più ricco (e letale) diventa.
"""

from __future__ import annotations

import random
from engine.core import tick as tick_mod
from engine.systems import state

INTERVAL_DAYS = 12
OPEN_DAYS = 3
_NAMES = ["Reame della Luna Spezzata", "Valle delle Diecimila Erbe", "Palazzo Sommerso del Drago",
          "Tomba dell'Imperatore Celeste", "Foresta delle Spade Dormienti", "Grotta del Fuoco Antico",
          "Isola del Tuono Silente", "Abisso delle Stelle Cadute", "Giardino del Vecchio Immortale"]


def current(conn) -> dict | None:
    r = state.get_json(conn, "secret_realm")
    if not r:
        return None
    if tick_mod.get_tick(conn) > r["close_tick"]:
        return None
    return r


def run(conn) -> dict | None:
    return state.get_json(conn, "realm_run")


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import training
    from engine.simulation import cultivation
    out = []
    r = state.get_json(conn, "secret_realm")
    day = training.current_day(t)
    if r and t > r["close_tick"]:
        state.delete(conn, "secret_realm")
        if run(conn):
            state.delete(conn, "realm_run")
            out.append(f"«{r['name']}» si richiude, e ti scaglia fuori con ciò che hai preso.")
        else:
            out.append(f"«{r['name']}» si è richiuso. Il prossimo si aprirà tra qualche giorno.")
        r = None
    last_open = state.get_int(conn, "secret_realm_day", -999)
    if r is None and day - last_open >= INTERVAL_DAYS and day >= 3:
        wild = [x["id"] for x in conn.execute(
            "SELECT id FROM locations WHERE location_type IN ('mountain','ruin','forbidden_zone');")]
        if not wild:
            return out
        loc = rng.choice(wild)
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        name = rng.choice(_NAMES)
        floors = 4 + min(4, tier // 2)
        state.set_json(conn, "secret_realm", {
            "name": name, "loc": loc, "tier": tier, "floors": floors,
            "close_tick": t + training.DAY_TICKS * OPEN_DAYS})
        state.set(conn, "secret_realm_day", str(day))
        lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
        out.append(f"✧ Il cielo si incrina sopra {lname}: si è aperto un reame segreto: «{name}»! Resterà aperto "
                   f"{OPEN_DAYS} giorni. ('realm' per i dettagli)")
    return out


def describe(conn, player) -> str:
    r = current(conn)
    if not r:
        nxt = INTERVAL_DAYS - ((tick_mod.get_tick(conn) // 120) - state.get_int(conn, "secret_realm_day", -999))
        return ("Nessun reame segreto è aperto ora." +
                (f" Il prossimo dovrebbe aprirsi tra circa {max(1, nxt)} giorn{'o' if max(1, nxt) == 1 else 'i'}."
                 if nxt < 99 else ""))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (r["loc"],)).fetchone()["name"]
    days = max(0, (r["close_tick"] - tick_mod.get_tick(conn)) // 120)
    ru = run(conn)
    lines = [f"✧ {r['name']} — aperto a {lname} (si chiude tra {days} giorni), {r['floors']} piani."]
    if ru:
        lines.append(f"Sei dentro: piano {ru['floor']}/{r['floors']}. 'delve' per scendere, 'leave realm' per uscire.")
    elif player.location_id == r["loc"]:
        lines.append("L'ingresso è davanti a te: 'enter' per entrare.")
    else:
        from engine.cli.loop import _first_step_toward
        step = _first_step_toward(conn, player.location_id, r["loc"])
        lines.append(f"Raggiungilo: {'muoviti verso ' + step if step else 'la via non è chiara'}.")
    return "\n".join(lines)


def enter(conn, player) -> str:
    r = current(conn)
    if not r:
        return "Non c'è nessun reame segreto aperto."
    if player.location_id != r["loc"]:
        return "L'ingresso del reame non è qui. ('realm' per sapere dov'è)"
    if run(conn):
        return "Sei già dentro il reame. 'delve' per proseguire."
    state.set_json(conn, "realm_run", {"floor": 0, "loot": 0})
    return (f"Varchi la soglia di «{r['name']}». L'aria è densa di Qi antico; da qualche parte, "
            f"altri passi echeggiano. 'delve' per scendere al primo piano.")


def leave(conn) -> str:
    if not run(conn):
        return "Non sei dentro un reame segreto."
    state.delete(conn, "realm_run")
    return "Risali alla luce del giorno con ciò che hai trovato."


def _floor_scene(conn, rng, player, r: dict, floor: int) -> dict:
    tier = r["tier"]
    last = floor >= r["floors"]
    if last:
        return {
            "key": "reame_eredita", "title": f"{r['name']} — La Sala dell'Eredità", "event_type": "fortune",
            "text": ("In fondo al reame, una sala intatta da diecimila anni. Su un altare, cinque doni: "
                     "solo uno potrà essere tuo."),
            "sticky": True,
            "choices": [
                {"label": "Il rotolo di una tecnica perduta",
                 "effects": {"learn_technique": {"name": f"Eredità di «{r['name']}»",
                                                 "magnitude": round(0.08 + 0.03 * tier, 3),
                                                 "tech_key": f"reame:{r['name']}:{tier}"},
                             "realm_done": True, "title": "Erede di un Reame Segreto"}},
                {"label": "Un frammento cristallizzato di Dao",
                 "effects": {"dao_key": "random", "dao_gain": 10 + 6 * tier, "realm_done": True}},
                {"label": "Il rotolo di un metodo di coltivazione",
                 "effects": {"gongfa": {"grade": tier + 1}, "realm_done": True}},
                {"label": "Il seme di una radice spirituale",
                 "effects": {"root_gain": {"element": "random", "amount": 15 + 10 * tier}, "realm_done": True}},
                {"label": "Una fiala di vita antica",
                 "effects": {"lifespan_years": 20 + 15 * tier, "cultivation_progress": 0.5,
                             "realm_done": True}},
                {"label": "Una bottiglietta di giada verde, piena di terra",
                 "effects": {"inner_space": True, "realm_done": True}},
            ]}
    kind = rng.choice(["guardiano", "scrigno", "rivali", "pozza", "guardiano", "scrigno"])
    base = {"title": f"{r['name']} — piano {floor}/{r['floors']}", "event_type": "fortune", "sticky": True}
    if kind == "guardiano":
        return dict(base, key="reame_guardiano",
                    text="Un guardiano di pietra e Qi si anima al tuo passaggio. Dietro di lui, una scala.",
                    spawn={"archetype": "guardia", "tier_offset": 0, "stage": 4 + floor},
                    choices=[{"label": "Lo abbatti", "effects": {}, "command": "attack {npc}"},
                             {"label": "Lo aggiri di soppiatto", "check": {"stat": "istinto", "dc": 60 + 4 * floor},
                              "success": {"text": "Scivoli oltre senza un rumore.", "npc_leaves": True},
                              "failure": {"injury": 3, "text": "Ti scorge e ti colpisce mentre passi."}}])
    if kind == "scrigno":
        return dict(base, key="reame_scrigno",
                    text="Uno scrigno coperto di sigilli. Le rune pulsano: forse è una trappola.",
                    choices=[{"label": "Lo apri con cautela", "check": {"stat": "fortuna", "dc": 55 + 3 * floor},
                              "success": {"stones": 40 + 30 * tier * floor, "text": "Pietre spirituali a manciate."},
                              "failure": {"injury": 3, "text": "Il sigillo esplode."}},
                             {"label": "Spezzi i sigilli con l'anima", "check": {"stat": "anima", "dc": 62 + 3 * floor},
                              "success": {"item": {"name": "Pillola del Reame Segreto", "item_type": "pillola",
                                                   "rarity": "raro", "desc": "Qi antico condensato.",
                                                   "effects": {"cultivation_progress": round(0.3 + 0.1 * tier, 2)}}},
                              "failure": {"aff_soul": -1, "text": "I sigilli ti mordono la mente."}},
                             {"label": "Lo lasci stare", "effects": {}}])
    if kind == "rivali":
        return dict(base, key="reame_rivali",
                    text="Discepoli di un'altra setta ti sbarrano la strada. Il loro capo, {npc}, sorride: "
                         "«Questo piano è nostro.»",
                    spawn={"archetype": "discepolo", "tier_offset": 0, "stage": 5 + floor,
                           "traits": {"pride": 85}},
                    choices=[{"label": "Combatti per il passaggio", "effects": {"fame": 3}, "command": "attack {npc}"},
                             {"label": "Proponi di dividere il bottino", "check": {"stat": "anima", "dc": 60},
                              "success": {"relation": 30, "stones": 20 * tier,
                                          "text": "Accetta: proseguite per un tratto insieme."},
                              "failure": {"text": "Rifiuta con disprezzo: si combatte!",
                                          "command": "attack {npc}"}},
                             {"label": "Torni indietro e cerchi un'altra via", "effects": {}}])
    return dict(base, key="reame_pozza",
                text="Una pozza di Qi liquido, immobile come uno specchio. Meditarci accanto è pericoloso, "
                     "e prezioso.",
                choices=[{"label": "Mediti nella pozza", "check": {"stat": "coltivazione", "dc": 58 + 3 * floor},
                          "success": {"cultivation_progress": round(0.25 + 0.05 * floor, 2), "qi_full": True},
                          "failure": {"injury": 2, "text": "Il Qi ti travolge."}},
                         {"label": "Raccogli il Qi in una fiala",
                          "effects": {"item": {"name": "Fiala di Qi Antico", "item_type": "pillola",
                                               "rarity": "non_comune", "desc": "Qi del reame.",
                                               "effects": {"cultivation_progress": 0.2}}}}])


def delve(conn, player) -> str:
    from engine.systems import encounters
    r = current(conn)
    ru = run(conn)
    if not r or not ru:
        return "Non sei dentro un reame segreto. ('realm' per vedere se ce n'è uno aperto)"
    if player.location_id != r["loc"]:
        state.delete(conn, "realm_run")
        return "Ti sei allontanato dall'ingresso: il reame ti ha richiuso fuori."
    if encounters.pending(conn):
        return encounters.render(conn, player)
    ru["floor"] += 1
    state.set_json(conn, "realm_run", ru)
    rng = random.Random(tick_mod.get_tick(conn) * 37 + ru["floor"])
    from engine.systems import npc_factory
    ctx = {"npc_name": npc_factory.unique_name(rng, conn=conn)}
    sc = encounters.format_scene(_floor_scene(conn, rng, player, r, ru["floor"]), ctx)
    from engine.simulation import world_tick
    world_tick.advance(conn, 2)
    return encounters.start_scene(conn, player, sc, force=True)


def on_done(conn) -> None:
    state.delete(conn, "realm_run")
