"""
TEMPRA DELLO SPIRITO (炼神) — la terza via di coltivazione, accanto al Qi e al Dao.

Il Qi è il corpo dell'energia, il Dao la comprensione; lo SPIRITO è chi li regge: la forza
dell'anima. Si tempra a parte, con sedute di contemplazione dell'anima:

  tempra              una seduta dedicata (rende di più se hai approfondito il Dao dell'Anima)
  train / allenati    l'allenamento d'insieme ora tempra anche lo spirito (con una quota minore)

Ogni grado dell'anima:
  · alza il PUNTEGGIO DI SPIRITO (quello che si confronta per sigillare un'anima, per
    intimidire, per leggere gli altri);
  · allarga la riserva di Spirito per le tecniche Dao;
  · allunga il senso divino.

Gradi (senza fine): Anima Mortale · Scintilla · Fiamma · Lago · Mare della Coscienza ·
Senso Divino Compiuto · Anima di Giada · Anima d'Oro · Anima Sovrana · Anima Eterna ·
e oltre, Anima del N° Cielo.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "soul_temper"
SHARE = 0.6                       # quota nell'allenamento d'insieme

GRADES = ["Anima Mortale", "Scintilla dell'Anima", "Fiamma dell'Anima", "Lago dell'Anima",
          "Mare della Coscienza", "Senso Divino Compiuto", "Anima di Giada", "Anima d'Oro Immortale",
          "Anima Sovrana", "Anima Eterna"]

_LINES = ["Chiudi gli occhi e scendi nel mare della coscienza: le onde si placano, una a una.",
          "Contempli la fiamma della tua anima finché non smette di tremare.",
          "Respingi i pensieri estranei come foglie sull'acqua: resta solo chi sei.",
          "Il tuo senso divino si allunga nel buio e torna indietro più denso.",
          "Ascolti il silenzio sotto il silenzio: lì l'anima si indurisce come giada."]


def grade_name(g: int) -> str:
    if g < len(GRADES):
        return GRADES[g]
    return f"Anima del {g - len(GRADES) + 1}° Cielo"


def need(g: int) -> int:
    """Esperienza totale per raggiungere il grado g."""
    return int(20 * g ** 1.8)


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"xp": 0.0, "g": 0}


def grade(conn, pid: int = 1) -> int:
    return int(get(conn).get("g", 0))


def progress(conn) -> tuple[int, float, int, int]:
    d = get(conn)
    g = int(d.get("g", 0))
    lo, hi = need(g), need(g + 1)
    return g, float(d.get("xp", 0.0)), lo, hi


def score_bonus(conn, pid: int = 1) -> float:
    """Punti di spirito dati dalla tempra (per perception.spirit_score)."""
    g = grade(conn, pid)
    bonus = 6 * g + 0.6 * g * g
    try:
        from engine.systems import character
        prof = character.get_profile(conn, "player", pid)
        bonus += (prof["grow_soul"] or 0) * 0.5 if prof else 0
    except Exception:
        pass
    return bonus


def spirit_pool_bonus(conn, pid: int = 1) -> int:
    return 20 * grade(conn, pid)


def add_xp(conn, amount: float) -> list[str]:
    d = get(conn)
    d["xp"] = round(float(d.get("xp", 0.0)) + amount, 3)
    out = []
    while d["xp"] >= need(int(d["g"]) + 1):
        d["g"] = int(d["g"]) + 1
        out.append(f"🌀 La tua anima si tempra: ora è {grade_name(d['g'])} (grado {d['g']}).")
        from engine.systems import chronicle
        chronicle.add(conn, "crescita", f"L'anima raggiunge il grado {grade_name(d['g'])}.")
    state.set_json(conn, KEY, d)
    return out


def _gain(conn, pid: int, y: float) -> float:
    from engine.simulation import cultivation
    from engine.systems import perception
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    anima = perception._anima(conn, "player", pid)
    from engine.systems import constitutions
    return 12.0 * y * (1 + anima / 100) * (1 + 0.2 * (tier - 1)) * constitutions.soul_mult(conn)


def session(conn, player, share: float = 1.0, advance: bool = True) -> str:
    """Una seduta di tempra. share<1 quando fa parte dell'allenamento d'insieme."""
    from engine.systems import training
    t = tick_mod.get_tick(conn)
    if share >= 1.0:
        n = training.record_session(conn, t, "player", player.id)
    else:
        n = max(1, training.sessions_today(conn, t, "player", player.id))
    y = training.session_yield(n)
    gain = round(_gain(conn, player.id, y) * share, 2)
    ups = add_xp(conn, gain)
    g, xp, lo, hi = progress(conn)
    pct = int(100 * (xp - lo) / max(1, hi - lo))
    rng = random.Random(t * 13 + player.id)
    if share >= 1.0:
        lines = [rng.choice(_LINES),
                 f"Spirito +{gain:g} — {grade_name(g)} ({pct}% verso il grado successivo). "
                 f"[{training.yield_label(y)}]"]
        if advance:
            from engine.simulation import world_tick
            world_tick.advance(conn, tick_mod.cost_of("cultivate"))
            from engine.systems import spirit
            spirit.restore_fraction(conn, 0.3, player.id)
    else:
        lines = [f"Spirito: +{gain:.0f} ({grade_name(g)}, {pct}%)."]
    return "\n".join(lines + ups)


def describe(conn, player) -> str:
    from engine.systems import perception
    g, xp, lo, hi = progress(conn)
    sc = perception.spirit_score(conn, "player", player.id)
    return (f"🌀 Tempra dello Spirito: {grade_name(g)} (grado {g}) — {int(xp - lo)}/{hi - lo} verso il prossimo.\n"
            f"Punteggio di spirito: {sc:.0f} (Dao dell'Anima + regno + tempra). "
            f"È ciò che si confronta quando sigilli un'anima ('sigilla <nome>').\n"
            f"Si allena con 'tempra' (seduta dedicata) o con 'train' (insieme a Qi, Dao e arti).")
