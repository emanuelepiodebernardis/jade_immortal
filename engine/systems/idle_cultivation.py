"""
LA COLTIVAZIONE MENTRE SEI VIA (Aggiornamento 67) — il cuore idle del genere, in piccolo.

Lo spunto viene da Immortal Celestial Fate e dagli idle del genere: il personaggio coltiva anche quando
il gioco è chiuso. Qui, quando riapri la partita dopo almeno un'ora di tempo VERO, trovi un resoconto:
per ogni ora d'assenza una sessione di meditazione leggera (fino a 12 ore), con i tuoi moltiplicatori.

  · il MONDO NON AVANZA: nessun giorno passa, nessun nemico si muove, nessun rischio. È solo il tuo
    personaggio seduto a gambe incrociate nell'ultima pagina che hai lasciato;
  · allo strato più alto del regno la meditazione si deposita nel Dao (come le pietre assorbite);
  · si spegne dalle impostazioni del pilota ('auto imposta assente no').
"""

from __future__ import annotations

import random
import time

from engine.systems import state

KEY = "idle_seen"
MAX_HOURS = 12
YIELD = 0.35


def now() -> int:
    return int(time.time())


def touch(conn) -> None:
    try:
        state.set(conn, KEY, str(now()))
    except Exception:                                   # noqa: BLE001 — mai bloccare un comando per questo
        pass


def enabled(conn) -> bool:
    from engine.systems import autopilot
    return bool(autopilot.config(conn).get("assente", True))


def on_open(conn, player, at: int | None = None) -> list[str]:
    """All'apertura della partita: quanto sei stato via, e cosa hai coltivato nel frattempo."""
    at = now() if at is None else at
    seen = state.get_int(conn, KEY, 0)
    state.set(conn, KEY, str(at))
    if not seen or player is None or player.status != "alive" or not enabled(conn):
        return []
    hours = (at - seen) / 3600.0
    if hours < 1.0:
        return []
    n = min(MAX_HOURS, int(hours))
    from engine.simulation import cultivation
    from engine.systems import cult_mods
    from engine.core import tick as tick_mod
    rec0 = cultivation.get_record(conn, "player", player.id)
    if rec0 is None:
        return []
    mult, _l = cult_mods.cultivation_mult(conn, player.id, player.location_id)
    rng = random.Random(at)
    t = tick_mod.get_tick(conn)
    stage0, prog0 = rec0["stage"] or 1, rec0["progress"]
    peak = False
    dao_gain = 0
    for _ in range(n):
        rec = cultivation.get_record(conn, "player", player.id)
        if (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM and rec["progress"] >= 1.0:
            peak = True
            dao_gain += 1 + (cultivation.realm_tier(conn, "player", player.id) or 1) // 4
            continue
        cultivation.cultivate(conn, "player", player.id, t, rng, multiplier=mult * YIELD)
    lines = []
    if dao_gain:
        from engine.systems import dao_training, items
        rows = dao_training.trainable_daos(conn, player.id)
        if rows:
            best = max(rows, key=lambda r: r["comprehension"])
            items.apply_effects(conn, t, rng, player.id, {"dao_key": best["dao_key"], "dao_gain": dao_gain})
    rec1 = cultivation.get_record(conn, "player", player.id)
    gain = (rec1["stage"] - stage0) * 100 + int((rec1["progress"] - prog0) * 100)
    hh = f"{int(hours)} ore" if hours < 48 else f"{int(hours // 24)} giorni"
    lines.append(f"🧘 Mentre eri via ({hh}) il tuo personaggio ha meditato: {n} sessioni"
                 + (f" (il massimo è {MAX_HOURS})" if hours > MAX_HOURS else "") + ". "
                 + (f"Coltivazione +{gain}% di strato." if gain > 0 else "")
                 + (f" Il regno è colmo: il Qi è sceso nel Dao (+{dao_gain})." if peak and dao_gain else "")
                 + " Il mondo, intanto, è rimasto fermo.")
    return lines
