"""
MISSIONE QUOTIDIANA DEL SISTEMA e RANGO DEL CACCIATORE (ispirati a «Solo Leveling»).

In «Solo Leveling» il Sistema assegna ogni giorno la stessa missione di allenamento: se la
completi arriva una ricompensa (e i punti attributo), se la salti c'è la Zona di Penalità.
Qui ogni giorno il Sistema ti chiede tre cose, scalate sul tuo livello:

  ☸ Dao      — guadagna N di comprensione dei Dao (allenati, comprendi, spiriti del Dao)
  ⚔ Caccia   — abbatti N nemici
  🌀 Tempra   — tempra lo spirito almeno una volta

Ricompensa: 1 punto attributo, pietre, e ogni 7 giorni di fila altri 2 punti e un titolo.
Penalità (se la salti): la serie si azzera e il cuore del Dao si incrina (−2). Niente di
più crudele: è un gioco, non una prigione.

RANGO DEL CACCIATORE: E, D, C, B, A, S, poi SS, SSS, «Livello Nazionale», «Monarca»…
dipende dal tuo livello rispetto al tetto del mondo in cui vivi.

  missione   la missione del giorno (anche nel pannello Mete della dashboard)
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "system_daily"
RANKS = ["E", "D", "C", "B", "A", "S", "SS", "SSS", "Livello Nazionale", "Monarca"]


def hunter_rank(conn, pid: int = 1) -> str:
    """Il rango del cacciatore: quanto sei in alto nel tuo mondo (e oltre, nei mondi superiori)."""
    from engine.simulation import cultivation
    from engine.systems import ascension
    t = cultivation.realm_tier(conn, "player", pid) or 1
    st = cultivation.stage_of(conn, "player", pid) or 1
    layer = ascension.player_layer(conn, pid)
    lo, hi = ascension.plane_range(layer) if hasattr(ascension, "plane_range") else (1, 9)
    span = max(1, (hi - lo + 1) * 10)
    frac = max(0.0, min(1.0, ((t - lo) * 10 + st) / span))
    i = min(5, int(frac * 6))
    i += min(4, layer)                  # ogni mondo superiore alza il rango
    return RANKS[min(i, len(RANKS) - 1)] if i < len(RANKS) else f"Monarca {i - len(RANKS) + 2}"


def _snapshot(conn, pid: int) -> dict:
    from engine.systems import soul_temper
    dao = conn.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos WHERE character_type='player' "
                       "AND character_id=?;", (pid,)).fetchone()["s"]
    return {"dao": int(dao), "kills": state.get_int(conn, "kills_total", 0),
            "soul": float(soul_temper.get(conn).get("xp", 0.0))}


def _goals(conn, pid: int) -> dict:
    from engine.simulation import cultivation
    t = cultivation.realm_tier(conn, "player", pid) or 1
    return {"dao": 6 + 3 * t, "kills": 1 + t // 3, "soul": 1}


def get(conn, pid: int = 1) -> dict:
    """La missione di oggi (la crea se è un giorno nuovo). Non tocca il mondo oltre allo stato della missione."""
    day = tick_mod.get_tick(conn) // 120
    d = state.get_json(conn, KEY, None) or {}
    if d.get("day") != day:
        prev_done = d.get("done", True) if d else True
        streak = d.get("streak", 0) if prev_done else 0
        missed = bool(d) and not prev_done and d.get("day", day) == day - 1
        d = {"day": day, "base": _snapshot(conn, pid), "goals": _goals(conn, pid), "done": False,
             "streak": streak, "missed": missed, "bonus_points": d.get("bonus_points", 0) if d else 0}
        state.set_json(conn, KEY, d)
    return d


def progress(conn, pid: int = 1) -> list[dict]:
    d = get(conn, pid)
    now = _snapshot(conn, pid)
    out = []
    for k, label, icon in (("dao", "Comprensione dei Dao", "☸"), ("kills", "Nemici abbattuti", "⚔"),
                           ("soul", "Tempra dello spirito", "🌀")):
        have = now[k] - d["base"][k]
        need = d["goals"][k]
        if k == "soul":
            have = 1 if have > 0 else 0
        out.append({"k": k, "label": label, "icon": icon, "have": max(0, int(have)), "need": need,
                    "ok": have >= need})
    return out


def bonus_points(conn) -> int:
    d = state.get_json(conn, KEY, None) or {}
    return int(d.get("bonus_points", 0))


def check(conn, player) -> list[str]:
    """Dopo ogni comando: se la missione è completa, il Sistema paga."""
    if player is None or player.status != "alive":
        return []
    d = get(conn, player.id)
    out = []
    if d.get("missed"):
        d["missed"] = False
        from engine.systems import dao_heart
        try:
            dao_heart.adjust(conn, -2, "missione saltata")
        except Exception:
            pass
        state.set_json(conn, KEY, d)
        out.append("[Sistema] Ieri non hai completato la Missione Quotidiana. Penalità: la serie si azzera, "
                   "il cuore del Dao si incrina (−2).")
    if d["done"]:
        return out
    if not all(g["ok"] for g in progress(conn, player.id)):
        return out
    d["done"] = True
    d["streak"] = d.get("streak", 0) + 1
    pts = 1
    from engine.simulation import cultivation
    from engine.systems import sects
    t = cultivation.realm_tier(conn, "player", player.id) or 1
    stones = 40 * t
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    msg = (f"[Sistema] MISSIONE QUOTIDIANA COMPLETATA. Ricompense: +{pts} punto attributo, +{stones} pietre. "
           f"Serie: {d['streak']} giorni.")
    if d["streak"] % 7 == 0:
        pts += 2
        title = "Colui che Non Salta un Giorno" if d["streak"] == 7 else f"Disciplina di Ferro ({d['streak']} giorni)"
        state.grant_title(conn, title)
        msg += f" Bonus della settimana: +2 punti attributo, titolo «{title}»."
    d["bonus_points"] = d.get("bonus_points", 0) + pts
    state.set_json(conn, KEY, d)
    out.append(msg)
    from engine.systems import system_quest                 # il Trasmigratore: anche i punti del Sistema
    out += system_quest.on_daily_done(conn, player, d["streak"])
    return out


def data(conn, pid: int = 1) -> dict:
    d = get(conn, pid)
    return {"giorno": d["day"] + 1, "serie": d.get("streak", 0), "fatta": d["done"], "obiettivi": progress(conn, pid),
            "rango": hunter_rank(conn, pid)}


def describe(conn, player) -> str:
    x = data(conn, player.id)
    lines = [f"[Sistema] MISSIONE QUOTIDIANA — giorno {x['giorno']} · serie {x['serie']} · rango {x['rango']}"]
    for g in x["obiettivi"]:
        lines.append(f"  {'✔' if g['ok'] else '·'} {g['icon']} {g['label']}: {min(g['have'], g['need'])}/{g['need']}")
    lines.append("  Completata!" if x["fatta"] else
                 "  Ricompensa: 1 punto attributo e pietre (ogni 7 giorni di fila: +2 punti e un titolo).")
    return "\n".join(lines)
