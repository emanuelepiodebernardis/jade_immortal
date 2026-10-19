"""
I MERIDIANI (Aggiornamento 67) — aprirli uno a uno, poi temprarli senza fine.

Lo spunto viene da Immortal Celestial Fate (la «tempra dei meridiani») e dalla medicina cinese: dodici
meridiani principali e otto vasi straordinari. Prima qui i meridiani erano solo parole nelle descrizioni
del corpo; ora sono una via di crescita.

  · APRIRE: i meridiani si aprono in ordine. I dodici principali si aprono un po' a ogni regno (tre al
    primo, poi tre ogni regno); gli otto straordinari dal 5° regno, uno per regno. Aprire costa pietre e
    un giorno di lavoro, e può fallire (un po' di pietre perse e una ferita leggera); ogni fallimento
    rende più facile il tentativo dopo.
  · TEMPRARE: ogni meridiano aperto si tempra all'infinito (+1 livello alla volta; ogni livello costa il
    30% in più e vale +30% del valore base). Ogni meridiano rafforza una cosa sola: attacco, difesa,
    vitalità, critici, schivata, coltivazione, comprensione o le tossine delle pillole. Difesa, critici,
    schivata e tossine hanno un tetto; il resto passa dai tetti morbidi dei doni e della coltivazione.
  · I CIRCOLI: il Vaso Governatore e il Vaso Concezione aperti insieme chiudono il PICCOLO CIRCOLO
    CELESTE (coltivazione +10%); tutti e venti aperti, il GRANDE CIRCOLO (+15% a tutto, e un titolo).

  meridiani                       il pannello
  meridiani apri                  apri il prossimo meridiano
  meridiani tempra <n> [volte]    tempri il meridiano n
  meridiani tempra tutto          spendi le pietre temprando sempre il meridiano più economico
"""

from __future__ import annotations

import math
import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "meridians"
# (nome, effetto, peso). Gli effetti: atk, def (danni subiti), vit, crit, evade, cult, dao, tox
MERIDIANS = [
    ("Meridiano del Polmone", "vit", 1.0), ("Meridiano del Grosso Intestino", "atk", 1.0),
    ("Meridiano dello Stomaco", "vit", 1.0), ("Meridiano della Milza", "tox", 1.0),
    ("Meridiano del Cuore", "crit", 1.0), ("Meridiano dell'Intestino Tenue", "atk", 1.0),
    ("Meridiano della Vescica", "def", 1.0), ("Meridiano del Rene", "cult", 1.0),
    ("Meridiano del Pericardio", "def", 1.0), ("Meridiano del Triplice Riscaldatore", "cult", 1.0),
    ("Meridiano della Vescica Biliare", "evade", 1.0), ("Meridiano del Fegato", "dao", 1.0),
    # gli otto vasi straordinari
    ("Vaso Governatore", "atk", 1.6), ("Vaso Concezione", "cult", 1.6), ("Vaso Penetrante", "vit", 1.6),
    ("Vaso della Cintura", "def", 1.6), ("Vaso Yin del Tallone", "evade", 1.6), ("Vaso Yang del Tallone", "crit", 1.6),
    ("Vaso Yin di Collegamento", "dao", 1.6), ("Vaso Yang di Collegamento", "atk", 1.6),
]
EFFECT_LABEL = {"atk": "attacco", "def": "danni subiti", "vit": "vitalità", "crit": "critici", "evade": "schivata",
                "cult": "coltivazione", "dao": "comprensione del Dao", "tox": "tossine delle pillole"}
# quanto vale un «punto» di tempra (peso × log2(1+livello)), per effetto
PER_POINT = {"atk": 0.035, "def": 0.012, "vit": 0.04, "crit": 0.012, "evade": 0.008, "cult": 0.03, "dao": 0.03,
             "tox": 0.05}
CAPS = {"def": 0.25, "crit": 0.25, "evade": 0.15, "tox": 0.6}
OPEN_BASE = 80
TEMPER_BASE = 40
TEMPER_GROWTH = 1.3
PRINCIPAL = 12


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"open": 0, "lv": [], "fails": 0}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


def openable(conn) -> int:
    """Quanti meridiani il tuo regno permette di aprire."""
    t = _tier(conn)
    return min(PRINCIPAL, 3 * t) + max(0, min(8, t - 4))


def open_cost(conn, i: int) -> int:
    return int(OPEN_BASE * (i + 1) * (1 + 0.5 * _tier(conn)))


def temper_cost(conn, i: int, lv: int) -> int:
    return int(TEMPER_BASE * MERIDIANS[i][2] * (1 + 0.25 * _tier(conn)) * TEMPER_GROWTH ** lv)


def bonus(conn) -> dict:
    """Il totale per effetto (frazioni: 0,12 = +12%)."""
    d = get(conn)
    out = {k: 0.0 for k in EFFECT_LABEL}
    for i, lv in enumerate(d.get("lv", [])[: d.get("open", 0)]):
        name, eff, w = MERIDIANS[i]
        out[eff] += PER_POINT[eff] * w * (1.0 + 0.3 * lv)               # aperto vale già un punto
    for k, cap in CAPS.items():
        out[k] = min(cap, out[k])
    n = d.get("open", 0)
    if n >= 14:                                            # Governatore + Concezione: il Piccolo Circolo
        out["cult"] += 0.10
    if n >= len(MERIDIANS):                                # il Grande Circolo
        for k in ("atk", "vit", "cult", "dao"):
            out[k] += 0.15
    return out


def circle(conn) -> str:
    n = get(conn).get("open", 0)
    return "Grande Circolo Celeste" if n >= len(MERIDIANS) else "Piccolo Circolo Celeste" if n >= 14 else ""


def open_next(conn, player) -> str:
    from engine.systems import sects
    from engine.simulation import world_tick
    d = get(conn)
    i = d.get("open", 0)
    if i >= len(MERIDIANS):
        return "Tutti i venti meridiani sono aperti: il Grande Circolo Celeste gira in te."
    if i >= openable(conn):
        nxt = "dal 5° regno" if i >= PRINCIPAL and _tier(conn) < 5 else "al prossimo regno"
        return f"Il {MERIDIANS[i][0]} non cede ancora: si apre {nxt}."
    cost = open_cost(conn, i)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Per aprire il {MERIDIANS[i][0]} servono {cost} pietre spirituali."
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 7 + i * 31)
    from engine.systems import character
    aff = character.affinity_factor(conn, "player", player.id, "body")
    p = min(0.95, 0.6 + 0.12 * d.get("fails", 0) + 0.1 * (aff - 1.0) - (0.08 if i >= PRINCIPAL else 0.0))
    world_tick.advance(conn, 60)
    if rng.random() > p:
        sects.grant_resource(conn, "pietre_spirituali", -(cost // 3), player.id)
        d["fails"] = d.get("fails", 0) + 1
        _save(conn, d)
        _hurt(conn, player)
        return (f"Il Qi sbatte contro il {MERIDIANS[i][0]} e torna indietro: sputi sangue (−{cost // 3} pietre). "
                f"Ogni fallimento lo indebolisce: il prossimo tentativo riuscirà più facilmente ({int(min(0.95, p + 0.12) * 100)}%).")
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    d["open"] = i + 1
    d["fails"] = 0
    lv = d.setdefault("lv", [])
    while len(lv) < d["open"]:
        lv.append(0)
    _save(conn, d)
    nm, eff, _w = MERIDIANS[i]
    lines = [f"⚡ Il {nm} si apre come una diga che cede: il Qi lo attraversa per la prima volta "
             f"(−{cost} pietre). Rafforza: {EFFECT_LABEL[eff]}."]
    if d["open"] == 14:
        lines.append("☯ Governatore e Concezione si toccano: il PICCOLO CIRCOLO CELESTE gira in te (coltivazione +10%).")
    if d["open"] == len(MERIDIANS):
        lines.append("☯ Venti meridiani aperti: il GRANDE CIRCOLO CELESTE. Ogni tuo respiro è un ciclo del Cielo.")
        state.grant_title(conn, "Signore del Grande Circolo")
    return "\n".join(lines)


def _hurt(conn, player) -> None:
    t = tick_mod.get_tick(conn)
    try:
        conn.execute("INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
                     "healed, heal_tick) VALUES ('player', ?, 1, 'meridiano lacerato', ?, 0, ?);", (player.id, t, t + 15))
    except Exception:                                   # noqa: BLE001
        pass


def temper(conn, player, i: int, times: int = 1) -> str:
    from engine.systems import sects
    d = get(conn)
    if not (0 <= i < d.get("open", 0)):
        return "Puoi temprare solo un meridiano aperto. ('meridiani' per l'elenco)"
    lv = d.setdefault("lv", [0] * d["open"])
    done = spent = 0
    for _ in range(max(1, min(50, times))):
        c = temper_cost(conn, i, lv[i])
        if sects.get_resource(conn, "pietre_spirituali", player.id) < c:
            break
        sects.grant_resource(conn, "pietre_spirituali", -c, player.id)
        lv[i] += 1
        done += 1
        spent += c
    _save(conn, d)
    nm, eff, _w = MERIDIANS[i]
    if not done:
        return f"Per temprare il {nm} servono {temper_cost(conn, i, lv[i])} pietre."
    return (f"🔥 Tempri il {nm}: livello {lv[i]} (+{done}, −{spent} pietre). "
            f"{EFFECT_LABEL[eff].capitalize()}: {_fmt(eff, bonus(conn)[eff])}.")


def temper_all(conn, player, budget: int | None = None) -> str:
    """Tempera sempre il meridiano più economico finché bastano le pietre (o il budget)."""
    from engine.systems import sects
    d = get(conn)
    n = d.get("open", 0)
    if not n:
        return "Prima apri almeno un meridiano. ('meridiani apri')"
    lv = d.setdefault("lv", [0] * n)
    while len(lv) < n:
        lv.append(0)
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    cap = have if budget is None else min(have, budget)
    spent = steps = 0
    while steps < 500:
        i = min(range(n), key=lambda k: temper_cost(conn, k, lv[k]))
        c = temper_cost(conn, i, lv[i])
        if spent + c > cap:
            break
        spent += c
        lv[i] += 1
        steps += 1
    if not steps:
        i = min(range(n), key=lambda k: temper_cost(conn, k, lv[k]))
        return f"La tempra più economica costa {temper_cost(conn, i, lv[i])} pietre."
    sects.grant_resource(conn, "pietre_spirituali", -spent, player.id)
    _save(conn, d)
    return f"🔥 Tempri i meridiani senza sosta: {steps} livelli (−{spent} pietre). " + summary(conn)


def _fmt(eff: str, v: float) -> str:
    if eff == "def":
        return f"−{v * 100:.1f}%"
    if eff == "tox":
        return f"−{v * 100:.0f}%"
    return f"+{v * 100:.1f}%"


def summary(conn) -> str:
    b = bonus(conn)
    return " · ".join(f"{EFFECT_LABEL[k]} {_fmt(k, v)}" for k, v in b.items() if v > 0) or "nessun effetto ancora"


# ---------------------------------------------------------------- effetti sugli altri sistemi

def combat(conn, fx) -> list[str]:
    b = bonus(conn)
    if b["atk"]:
        fx.p.atk_mult *= 1.0 + b["atk"]
    if b["vit"]:
        from engine.systems import power_budget
        m = power_budget.soft(1.0 + b["vit"], 2.5)        # la vitalità non passa dal bilancio dei doni: tetto suo
        fx.p.hp *= m
        fx.p.max *= m
    pr = fx.p.prof
    if b["def"]:
        pr["taken"] = pr.get("taken", 0.0) + b["def"]
    if b["crit"]:
        pr["crit"] = pr.get("crit", 0.0) + b["crit"]
    if b["evade"]:
        pr["evade"] = pr.get("evade", 0.0) + b["evade"]
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    b = bonus(conn)["cult"]
    return (1.0 + b, "i meridiani aperti" + (f" ({circle(conn)})" if circle(conn) else "")) if b else (1.0, "")


def dao_mult(conn) -> float:
    return 1.0 + bonus(conn)["dao"]


def toxin_factor(conn) -> float:
    return 1.0 - bonus(conn)["tox"]


# ---------------------------------------------------------------- pannello

def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import sects
    d = get(conn)
    n = d.get("open", 0)
    lv = d.get("lv", [])
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    secs = []
    can = openable(conn)
    head = [f"Aperti {n}/{len(MERIDIANS)} (il tuo regno ne permette {can}) · pietre {stones}",
            "Effetti: " + summary(conn)]
    if circle(conn):
        head.append(f"☯ {circle(conn)}")
    acts = []
    if n < len(MERIDIANS):
        c = open_cost(conn, n)
        ok = n < can and stones >= c
        why = "il tuo regno non lo permette ancora" if n >= can else f"servono {c} pietre"
        acts.append(act(f"Apri il {MERIDIANS[n][0]} ({c} pietre)", "meridiani apri", ok, why, main=ok))
    if n:
        i = min(range(n), key=lambda k: temper_cost(conn, k, lv[k] if k < len(lv) else 0))
        c = temper_cost(conn, i, lv[i] if i < len(lv) else 0)
        acts.append(act("Tempra tutto ciò che puoi", "meridiani tempra tutto", stones >= c, f"servono {c} pietre",
                        main=not acts or not acts[0].get("ok", True)))
    secs.append(section("I meridiani", head, acts, icon="⚡"))
    rows, bars = [], []
    for i, (nm, eff, w) in enumerate(MERIDIANS):
        if i < n:
            l = lv[i] if i < len(lv) else 0
            bars.append(bar(f"{i + 1}. {nm} · liv. {l}", min(100, 10 * math.log2(2 + l) * 2), EFFECT_LABEL[eff],
                            tone="rare" if i >= PRINCIPAL else ""))
        elif i < n + 3:
            rows.append(f"🔒 {i + 1}. {nm} — {EFFECT_LABEL[eff]}")
    tacts = [act(f"Tempra {i + 1}", f"meridiani tempra {i + 1}") for i in range(n)][-6:]
    secs.append(section("Tempra", rows or ["Ogni livello costa il 30% in più del precedente: non c'è un tetto."],
                        tacts, bars, icon="🔥"))
    return menu("meridiani", "⚡ I MERIDIANI", ["Aprili uno a uno; poi temprali senza fine."], secs)


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub in ("apri", "open"):
        return open_next(conn, player)
    if sub in ("tempra", "tempera", "temprare"):
        if len(p) > 1 and p[1].lower() in ("tutto", "tutti", "max"):
            return temper_all(conn, player)
        if len(p) > 1 and p[1].isdigit():
            return temper(conn, player, int(p[1]) - 1, int(p[2]) if len(p) > 2 and p[2].isdigit() else 1)
        return temper_all(conn, player)
    from engine.systems import menus
    return menus.render(conn, menu_build(conn, player))
