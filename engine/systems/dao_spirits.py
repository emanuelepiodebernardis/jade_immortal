"""
SPIRITI DEL DAO — quando un Dao diventa profondo, prende forma e cammina accanto a te.

Nelle storie di coltivazione chi comprende a fondo una legge ne vede nascere la forma: lo
spirito della fiamma, la dama dell'acqua, l'ombra della spada, il «法相» (la forma del Dharma)
che si erge alle spalle del coltivatore. Qui ogni Dao arrivato a «maestro» (100) genera uno
SPIRITO, che cresce con la comprensione:

    maestro → Scintilla · gran maestro → Spirito · dominatore → Incarnazione ·
    legislatore → Forma del Dharma · sovrano → Signore · origine → Primordiale ·
    antenato → Antenato, poi Antenato II, III… senza fine

Cosa fanno:
  · COMBATTONO con te: i più forti accorrono in ogni scontro (quanti dipende dalla tempra
    dell'anima: 1 + grado/3, fino a 6);
  · ALLENANO il loro Dao ogni giorno, anche mentre fai altro;
  · con `spiriti allena` (una volta al giorno, costa spirito) ti allenano tutti insieme.

  spiriti            i tuoi Spiriti del Dao
  spiriti allena     sessione con tutti gli spiriti
"""

from __future__ import annotations

import math

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "dao_spirits"
MIN_IDX = 4             # «maestro»
STAGES = ["", "", "", "", "Scintilla", "Spirito", "Incarnazione", "Forma del Dharma", "Signore", "Primordiale",
          "Antenato"]

# personificazioni: dao_key -> (nome, aspetto)
FORMS = {
    "fuoco": ("Salamandra di Fiamma", "una figura di brace con occhi d'oro fuso"),
    "acqua": ("Ondina", "una dama di acqua limpida che non bagna ciò che tocca"),
    "terra": ("Gigante di Pietra", "un colosso di roccia e radici, lento e inamovibile"),
    "vento": ("Silfide", "un turbine sottile con una risata di foglie"),
    "metallo": ("Guerriero d'Acciaio", "un'armatura vuota che si muove come un generale"),
    "legno": ("Driade", "una fanciulla di corteccia con capelli di germogli"),
    "fulmine": ("Drago del Tuono", "un serpente di folgore che si avvolge al tuo braccio"),
    "luce": ("Serafino di Luce", "sei ali di luce attorno a un volto che non si riesce a guardare"),
    "oscurita": ("Ombra Vivente", "la tua ombra, alzatasi da terra con occhi rossi"),
    "ghiaccio": ("Regina del Gelo", "una dama di cristallo che lascia brina sul suo passo"),
    "spada": ("Spirito della Spada", "una spada che cammina da sola, con la tua stessa postura"),
    "lancia": ("Spirito della Lancia", "un cavaliere fatto solo di una punta e di uno slancio"),
    "arco": ("Spirito dell'Arco", "un arciere di vento che non manca mai"),
    "pugno": ("Spirito del Pugno", "un monaco di bronzo con le nocche rotte e lo sguardo calmo"),
    "corpo": ("Gigante Dorato", "il tuo corpo, alto tre volte tanto, d'oro vivo"),
    "anima": ("Anima Gemella", "il tuo volto, trasparente, che pensa un attimo prima di te"),
    "spazio": ("Viandante del Vuoto", "una figura che appare dove non c'era nessuna porta"),
    "tempo": ("Custode delle Ore", "un vecchio e un bambino che sono la stessa persona"),
    "destino": ("Tessitrice del Fato", "una donna senza volto con mille fili tra le dita"),
    "karma": ("Giudice del Karma", "una bilancia d'avorio con due occhi sul giogo"),
    "massacro": ("Asura del Massacro", "un guerriero a sei braccia coperto di sangue antico"),
    "vita_morte": ("Signore del Confine", "metà fiore, metà teschio"),
    "samsara": ("Ruota Vivente", "una ruota di sei raggi con un volto per ogni vita"),
    "yinyang": ("Gemelli Yin-Yang", "un pesce nero e un pesce bianco che nuotano nell'aria"),
    "caos": ("Embrione del Caos", "un uovo grigio da cui ogni tanto esce un mondo"),
    "sangue": ("Signore del Sangue", "una nebbia rossa che prende la forma che vuole"),
    "illusione": ("Volpe dei Sogni", "una volpe bianca che non sai mai se è lì davvero"),
    "stelle": ("Pastore di Stelle", "un uomo vestito di notte con costellazioni al guinzaglio"),
    "vuoto": ("Nulla Vestito", "un mantello senza nessuno dentro"),
    "creazione": ("Artefice Primo", "un vasaio che plasma creta e la creta respira"),
    "veleno": ("Serpe dei Cento Veleni", "un serpente di giada che cambia colore a ogni respiro"),
}


def _form(dao_key: str, dao_name: str) -> tuple[str, str]:
    if dao_key in FORMS:
        return FORMS[dao_key]
    short = dao_name.replace("Dao della ", "").replace("Dao del ", "").replace("Dao dello ", "") \
        .replace("Dao dell'", "").replace("Dao di ", "").replace("Dao ", "")
    return (f"Spirito di {short}", f"la forma viva del Dao di {short}")


def _roman(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s


def stage_of(conn, comprehension: int) -> tuple[int, str]:
    """(livello, nome dello stadio). Livello 1 = Scintilla; oltre l'Antenato continua senza fine."""
    from engine.systems import dao_training as dt
    i = dt._tier_index(comprehension or 0)
    if i < MIN_IDX:
        return 0, ""
    lvl = i - MIN_IDX + 1
    last = dt.DAO_THRESHOLDS[-1][0]
    if i >= len(STAGES) - 1 and comprehension >= 2 * last:
        extra = int(math.log2(comprehension / last))
        return lvl + extra, f"Antenato {_roman(extra + 1)}"
    return lvl, STAGES[min(i, len(STAGES) - 1)]


def spirits(conn, pid: int = 1) -> list[dict]:
    rows = conn.execute(
        "SELECT cd.dao_key, d.name, cd.comprehension FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? AND cd.comprehension>=100 "
        "ORDER BY cd.comprehension DESC;", (pid,)).fetchall()
    out = []
    for r in rows:
        lvl, stage = stage_of(conn, r["comprehension"])
        if lvl <= 0:
            continue
        name, look = _form(r["dao_key"], r["name"])
        out.append({"dao": r["dao_key"], "dao_name": r["name"], "comp": r["comprehension"], "level": lvl,
                    "stage": stage, "name": name, "look": look})
    return out


def slots(conn, pid: int = 1) -> int:
    from engine.systems import soul_temper
    try:
        g = soul_temper.grade(conn, pid)
    except Exception:
        g = 0
    return max(1, min(6, 1 + g // 3))


def _seen(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"known": {}, "train_day": -1}


def daily(conn, t: int, rng, player) -> list[str]:
    """Gli spiriti allenano il loro Dao; uno spirito nuovo o cresciuto si annuncia."""
    if player is None:
        return []
    d = _seen(conn)
    out = []
    for s in spirits(conn, player.id):
        old = d["known"].get(s["dao"], 0)
        if s["level"] > old:
            d["known"][s["dao"]] = s["level"]
            if old == 0:
                out.append(f"✺ Il Dao «{s['dao_name']}» prende forma: nasce {s['name']} — {s['look']}. "
                           "Combatterà al tuo fianco e allenerà il suo Dao anche quando tu riposi.")
                from engine.systems import chronicle
                chronicle.add(conn, "svolta", f"Nasce uno Spirito del Dao: {s['name']} ({s['dao_name']}).")
            else:
                out.append(f"✺ {s['name']} cresce: ora è {s['stage']}.")
        gain = 1 + s["level"] // 2
        conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='player' "
                     "AND character_id=? AND dao_key=?;", (gain, player.id, s["dao"]))
    state.set_json(conn, KEY, d)
    return out


def train(conn, player) -> str:
    sp = spirits(conn, player.id)
    if not sp:
        return "Non hai ancora Spiriti del Dao: porta un Dao a «maestro» (100) e prenderà forma."
    d = _seen(conn)
    day = tick_mod.get_tick(conn) // 120
    if d.get("train_day") == day:
        return "Gli spiriti hanno già combattuto con te oggi: riposano. Domani."
    from engine.systems import spirit
    cost = max(1, int(spirit.max_spirit(conn, player.id) * 0.25))
    if not spirit.can_afford(conn, cost, player.id):
        return f"Non hai abbastanza spirito per sostenerli tutti (servono {cost})."
    spirit.spend(conn, cost, player.id)
    d["train_day"] = day
    state.set_json(conn, KEY, d)
    lines = [f"✺ Chiami i tuoi Spiriti del Dao e combatti con ognuno, a turno (−{cost} spirito):"]
    for s in sp:
        gain = 3 + 2 * s["level"]
        conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='player' "
                     "AND character_id=? AND dao_key=?;", (gain, player.id, s["dao"]))
        lines.append(f"  · {s['name']} ({s['stage']}): Dao «{s['dao_name']}» +{gain}")
    from engine.simulation import world_tick
    world_tick.advance(conn, 12)
    return "\n".join(lines)


def combat_allies(conn, player_id: int) -> list[dict]:
    sp = spirits(conn, player_id)[:slots(conn, player_id)]
    if not sp:
        return []
    from engine.simulation import combat
    atk = combat.combat_power(conn, "player", player_id)["attack"]
    out = []
    for s in sp:
        out.append({"intro": f"✺ {s['name']} ({s['stage']}) si leva alle tue spalle.",
                    "attack": atk * min(0.6, 0.10 + 0.06 * s["level"]),
                    "line": f"{s['name']} colpisce con il Dao «{s['dao_name']}»."})
    return out


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import dao_training as dt
    sp = spirits(conn, player.id)
    n = slots(conn, player.id)
    secs = []
    if not sp:
        secs.append(section("Nessuno spirito, per ora", [
            "Quando un Dao arriva a «maestro» (100 di comprensione) prende forma accanto a te.",
            "Più spiriti combattono con te quanto più è temprata la tua anima (comando «tempra»)."],
            [act("Allenati (Qi, Dao e arte)", "train", main=True), act("Tempra lo spirito", "tempra")], icon="✺"))
    for i, s in enumerate(sp):
        nxt = dt.next_threshold(s["comp"])
        goal = nxt[0] if nxt else max(2000, 1 << s["comp"].bit_length())
        prev = max([t[0] for t in dt.DAO_THRESHOLDS if t[0] <= s["comp"]] or [0])
        pct = 100 * (s["comp"] - prev) / max(1, goal - prev)
        fights = "combatte con te" if i < n else "riposa (anima non abbastanza temprata)"
        secs.append(section(f"{s['name']} — {s['stage']}", [s["look"].capitalize() + ".",
                                                            f"Dao «{s['dao_name']}» · {fights} · allena +{1 + s['level'] // 2} al giorno"],
                            bars=[bar("Verso lo stadio successivo", pct, f"{s['comp']}/{goal}", tone="rare")], icon="✺"))
    acts = [act("Combatti con tutti gli spiriti (allena i loro Dao)", "spiriti allena", bool(sp), "nessuno spirito", main=True)]
    secs.insert(0, section("I tuoi spiriti", [f"Spiriti: {len(sp)} · in battaglia ne accorrono fino a {n}"], acts, icon="✺"))
    return menu("spiriti", "✺ SPIRITI DEL DAO", ["Ogni Dao profondo prende forma, combatte con te e si allena da solo."], secs)


def command(conn, player, arg: str) -> str:
    if (arg or "").strip().lower() in ("allena", "allenati", "train"):
        return train(conn, player)
    from engine.systems import menus
    return menus.show(conn, player, "spiriti")
