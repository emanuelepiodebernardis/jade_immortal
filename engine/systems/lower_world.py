"""
IL MONDO DI SOTTO TI PREGA (Aggiornamento 63).

Quando ascendi, il mondo che hai lasciato continua a vivere, e si ricorda di te. Nei villaggi
qualcuno accende incensi al tuo nome: nasce un TEMPIO, e salgono le PREGHIERE.

  · Esaudisci una preghiera (costa pietre o spirito): la FEDE cresce, il karma anche.
  · Predica ai mortali (una volta al giorno): fede e merito.
  · Metti alla prova un mortale: se è degno, diventa il tuo EREDE nel mondo di sotto e ogni giorno
    porta fede al tempio; se non lo è, lo spaventi e il tuo nome si macchia un poco.
  · Il TEMPIO sale di livello con la fede: coltivazione +2% per livello, e il cuore si quieta.
  · Dal mondo di sotto arrivano anche NOTIZIE: la tua vecchia setta, la tua famiglia, i tuoi nemici.

(Lo spunto viene da Immortal Taoists: dal Cielo si predica ai mortali, si rispondono le preghiere e
si mettono alla prova.)

  preghiere            il tempio, la fede, le preghiere in attesa
  esaudisci <n>        rispondi a una preghiera
  ignora <n>           la lasci cadere
  predica              predichi ai mortali (una volta al giorno)
  metti_alla_prova     cerchi un erede tra i mortali (una volta ogni 5 giorni)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "lower_world"
TEMPLE_STEPS = (10, 30, 60, 100, 160, 240, 350, 500, 700, 1000)
PRAYERS = [
    ("siccita", "Il villaggio di {luogo} non vede pioggia da tre mesi: «Immortale {nome}, salva il raccolto.»",
     {"stones": 60}, 4, 3),
    ("malato", "Una madre prega per il figlio malato: «Un solo filo del tuo Qi, Immortale.»",
     {"spirit": 0.08}, 3, 4),
    ("demone", "Un demone divora le greggi vicino a {luogo}. I mortali si inginocchiano al tuo altare.",
     {"spirit": 0.15}, 6, 6),
    ("setta", "La tua vecchia setta è assediata: un discepolo, piangendo, brucia l'incenso al tuo nome.",
     {"stones": 150}, 8, 8),
    ("sposa", "Due giovani chiedono la tua benedizione per sposarsi: le loro famiglie si odiano.",
     {"spirit": 0.05}, 2, 5),
    ("tiranno", "Un signore della guerra opprime {luogo}: «Se esiste un Cielo giusto, che ci ascolti.»",
     {"spirit": 0.2}, 7, 10),
    ("famiglia", "Un tuo discendente, nel mondo di sotto, chiede aiuto: la casata sta per cadere.",
     {"stones": 100}, 6, 6),
]
NEWS = [
    "Nel mondo di sotto, la tua vecchia setta ha inciso il tuo nome sulla stele degli antenati.",
    "Nel mondo di sotto raccontano storie su di te ai bambini, la sera. Non tutte sono vere.",
    "Nel mondo di sotto un giovane coltivatore giura di raggiungerti in Cielo.",
    "Nel mondo di sotto qualcuno ha costruito una statua di te. Il naso è sbagliato.",
    "Nel mondo di sotto i tuoi vecchi nemici dicono che sei fuggito in Cielo per paura.",
    "Nel mondo di sotto la tua dimora è diventata meta di pellegrini.",
]


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"faith": 0, "prayers": [], "heir": None, "answered": 0,
                                               "sermon_day": -1, "test_day": -99, "seq": 0}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def active(conn, pid: int = 1) -> bool:
    from engine.systems import ascension
    return ascension.reached(conn) >= 1


def temple_level(d: dict) -> int:
    return sum(1 for s in TEMPLE_STEPS if d["faith"] >= s)


def _faith(conn, d: dict, n: int, out: list) -> None:
    before = temple_level(d)
    d["faith"] = max(0, d["faith"] + n)
    after = temple_level(d)
    if after > before:
        out.append(f"⛩ Il tuo tempio nel mondo di sotto cresce: livello {after}. Coltivazione +{2 * after}%.")
        if after >= 5:
            state.grant_title(conn, "Venerato nel Mondo di Sotto")


def daily(conn, t: int, rng, player) -> list[str]:
    if player is None or not active(conn):
        return []
    d = get(conn)
    out = []
    if len(d["prayers"]) < 3 and rng.random() < 0.45:
        key, txt, cost, faith, karma = rng.choice(PRAYERS)
        loc = conn.execute("SELECT name FROM locations ORDER BY RANDOM() LIMIT 1;").fetchone()
        d["seq"] += 1
        d["prayers"].append({"id": d["seq"], "key": key, "text": txt.format(luogo=loc["name"] if loc else "un villaggio",
                                                                             nome=player.name),
                             "cost": cost, "faith": faith, "karma": karma, "day": t // 120})
        out.append("🙏 Una preghiera sale dal mondo di sotto. ('preghiere')")
    d["prayers"] = [p for p in d["prayers"] if t // 120 - p["day"] <= 6]      # le preghiere non esaudite si spengono
    if d.get("heir"):
        _faith(conn, d, 1, out)
    if rng.random() < 0.05:
        out.append("📜 " + rng.choice(NEWS))
    _save(conn, d)
    return out


def answer(conn, player, arg: str) -> str:
    from engine.systems import sects, deep_dao, karma
    d = get(conn)
    p = next((x for x in d["prayers"] if arg.strip() and str(x["id"]) == arg.strip()), None) or \
        (d["prayers"][int(arg) - 1] if arg.strip().isdigit() and 0 < int(arg) <= len(d["prayers"]) else None)
    if not p:
        return "Nessuna preghiera con quel numero. ('preghiere')"
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    c = p["cost"]
    if c.get("stones"):
        need = c["stones"] * tier
        if sects.get_resource(conn, "pietre_spirituali", player.id) < need:
            return f"Servono {need} pietre spirituali per esaudirla."
        sects.grant_resource(conn, "pietre_spirituali", -need, player.id)
        paid = f"{need} pietre"
    else:
        ok, why = deep_dao._pay(conn, player.id, c.get("spirit", 0.05))
        if not ok:
            return why
        paid = why.strip("() ")
    d["prayers"].remove(p)
    d["answered"] += 1
    out = [f"Tendi la mano verso il mondo di sotto ({paid}). Laggiù, qualcuno vede un miracolo."]
    _faith(conn, d, p["faith"], out)
    karma.adjust_karma(conn, "player", player.id, p["karma"], "preghiera esaudita", tick_mod.get_tick(conn))
    out.append(f"Fede +{p['faith']} (ora {d['faith']}), karma +{p['karma']}.")
    if d["answered"] in (10, 50):
        state.grant_title(conn, "Colui che Ascolta" if d["answered"] == 10 else "Divinità del Mondo di Sotto")
    _save(conn, d)
    return "\n".join(out)


def ignore(conn, player, arg: str) -> str:
    d = get(conn)
    if arg.strip().isdigit() and 0 < int(arg) <= len(d["prayers"]):
        p = d["prayers"].pop(int(arg) - 1)
        _save(conn, d)
        return f"Lasci cadere la preghiera. ({p['text'][:60]}…)"
    return "Nessuna preghiera con quel numero."


def sermon(conn, player) -> str:
    from engine.systems import guild
    if not active(conn):
        return "Predicherai ai mortali quando sarai asceso a un mondo superiore."
    d = get(conn)
    day = _day(conn)
    if d["sermon_day"] == day:
        return "Hai già predicato oggi."
    d["sermon_day"] = day
    out = ["La tua voce scende tra le nuvole come pioggia. Nel mondo di sotto, mille mortali chiudono gli occhi."]
    _faith(conn, d, 2, out)
    guild.add_merit(conn, 10, player.id)
    _save(conn, d)
    return "\n".join(out + ["Fede +2, merito +10."])


def test_mortal(conn, player) -> str:
    from engine.systems import karma
    if not active(conn):
        return "Dal Cielo potrai mettere alla prova i mortali, quando ci sarai salito."
    d = get(conn)
    day = _day(conn)
    if day - d["test_day"] < 5:
        return f"I mortali vanno messi alla prova di rado (ancora {5 - (day - d['test_day'])} giorni)."
    d["test_day"] = day
    rng = random.Random(tick_mod.get_tick(conn) * 3 + 11)
    out = []
    if rng.random() < 0.35:
        from engine.systems import npc_factory
        nm = npc_factory.unique_name(rng, conn=conn)
        d["heir"] = nm
        out.append(f"Scendi in sogno come un mendicante e chiedi l'ultima ciotola di riso. {nm} te la dà, e ti "
                   "copre col suo mantello. È degno: d'ora in poi è il tuo EREDE nel mondo di sotto, e ogni giorno "
                   "porta fede al tuo tempio.")
        state.grant_title(conn, "Colui che Scelse un Erede")
        _faith(conn, d, 5, out)
    else:
        out.append("Scendi come un vecchio affamato. Ti cacciano a bastonate. Nessuno, oggi, è degno.")
        karma.adjust_karma(conn, "player", player.id, -1, "prova ai mortali", tick_mod.get_tick(conn))
    _save(conn, d)
    return "\n".join(out)


def cultivation_mult(conn) -> tuple[float, str]:
    if not active(conn):
        return 1.0, ""
    lv = temple_level(get(conn))
    return (1.0 + 0.02 * lv, "il tuo tempio nel mondo di sotto") if lv else (1.0, "")


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    if not active(conn):
        return menu("sotto", "🙏 IL MONDO DI SOTTO", ["Quando ascenderai, il mondo che lasci si ricorderà di te."],
                    [section("Non ancora", ["Ascendi a un mondo superiore: il mondo di sotto costruirà un tempio al "
                                            "tuo nome, e ti pregherà."], icon="🙏")])
    d = get(conn)
    lv = temple_level(d)
    nxt = next((s for s in TEMPLE_STEPS if s > d["faith"]), None)
    day = _day(conn)
    secs = [section("Il tempio", [f"Livello {lv} — coltivazione +{2 * lv}%. Preghiere esaudite: {d['answered']}.",
                                  f"Erede nel mondo di sotto: {d['heir']}" if d.get("heir") else "Nessun erede, per ora."],
                    [act("Predica ai mortali", "predica", d["sermon_day"] != day, "già fatto oggi"),
                     act("Metti alla prova un mortale", "metti_alla_prova", day - d["test_day"] >= 5,
                         f"ancora {5 - (day - d['test_day'])} giorni")],
                    [bar("Fede", 100 if nxt is None else 100 * d["faith"] / nxt, f"{d['faith']}/{nxt or '∞'}", tone="rare")],
                    icon="⛩")]
    for i, p in enumerate(d["prayers"], 1):
        c = p["cost"]
        cost = (f"{c['stones']}× regno pietre" if c.get("stones") else f"{int(c.get('spirit', 0) * 100)}% dello spirito")
        secs.append(section(f"Preghiera {i}", [p["text"], f"Costo: {cost}. Fede +{p['faith']}, karma +{p['karma']}."],
                            [act("Esaudisci", f"esaudisci {i}", main=True), act("Ignora", f"ignora {i}")], icon="🙏"))
    return menu("sotto", "🙏 IL MONDO DI SOTTO", ["Laggiù si ricordano di te."], secs)


def command(conn, player, cmd: str, arg: str) -> str:
    from engine.systems import menus
    if cmd in ("esaudisci", "esaudire"):
        return answer(conn, player, arg)
    if cmd in ("ignora_preghiera", "ignora"):
        return ignore(conn, player, arg)
    if cmd in ("predica", "sermone"):
        return sermon(conn, player)
    if cmd in ("metti_alla_prova", "prova_mortale"):
        return test_mortal(conn, player)
    return menus.render(conn, menu_build(conn, player))
