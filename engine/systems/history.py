"""
STORIA IN NUMERI — un'istantanea al giorno, per i grafici della dashboard.

Ogni alba si registrano potenza, regno e strato, Dao, pietre, fama, karma. Le serie lunghe si
diradano da sole (oltre 400 punti si tiene un giorno su due dei più vecchi), così il grafico
racconta anni di vita senza appesantire il salvataggio.
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "history"
MAX = 400


def snapshot(conn, pid: int = 1) -> dict:
    from engine.simulation import cultivation
    from engine.systems import power, sects, reputation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    rec = cultivation.get_record(conn, "player", pid)
    stage = (rec["stage"] or 1) if rec else 1
    dao = conn.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos WHERE character_type='player' "
                       "AND character_id=?;", (pid,)).fetchone()["s"]
    try:
        rep = reputation.get(conn, pid)
        fame = rep["fame"]
    except Exception:
        fame = 0
    from engine.systems import karma
    k = karma.get_karma(conn, "player", pid)
    return {"d": tick_mod.get_tick(conn) // 120 + 1, "tier": tier, "stage": stage,
            "lvl": round(tier + (stage - 1) / 10 + (rec["progress"] if rec else 0) / 10, 2),
            "power": round(power.combat_rating(conn, "player", pid)),
            "dao": int(dao), "stones": sects.get_resource(conn, "pietre_spirituali", pid),
            "fame": int(fame), "karma": int(k or 0)}


def record(conn, pid: int = 1) -> None:
    h = state.get_json(conn, KEY, []) or []
    s = snapshot(conn, pid)
    if h and h[-1]["d"] == s["d"]:
        h[-1] = s
    else:
        h.append(s)
    if len(h) > MAX:                                  # dirada la metà più vecchia
        half = len(h) // 2
        h = h[:half:2] + h[half:]
    state.set_json(conn, KEY, h)


def series(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []
