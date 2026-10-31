"""
«DOVE ERAVAMO» (Aggiornamento 79) — tornando al gioco dopo qualche ora, un riassunto breve per riprendere il filo.

Il mondo resta fermo tra una sessione e l'altra (solo la meditazione d'assenza continua): il riassunto quindi
racconta cosa è successo nell'ultima sessione e cosa ti aspetta adesso.
  · dove sei, in che regno, che giorno è;
  · i fatti più importanti dell'ultima sessione (dalla cronaca);
  · l'obiettivo e il prossimo passo; le scene o i duelli in sospeso; i rivali che ti hanno superato;
  · il laboratorio con la cassa piena.
Si mostra dopo almeno RECAP_HOURS ore di assenza; 'riassunto' lo mostra quando vuoi.
"""

from __future__ import annotations

import time

from engine.systems import state

KEY = "recap_session"
RECAP_HOURS = 4


def mark_session(conn) -> None:
    """Inizio di una sessione: da qui contano i fatti «dell'ultima volta»."""
    from engine.systems import chronicle
    try:
        chronicle.ensure_table(conn)
        last = conn.execute("SELECT COALESCE(MAX(id), 0) m FROM chronicle_entries;").fetchone()["m"]
    except Exception:                                    # noqa: BLE001
        last = 0
    prev = state.get_json(conn, KEY, None) or {}
    state.set_json(conn, KEY, {"from_id": prev.get("now_id", last), "now_id": last, "at": int(time.time())})


def build(conn, player) -> list[str]:
    from engine.core import entities, tick
    from engine.simulation import cultivation
    from engine.systems import goals, chronicle, encounters, duel, prodigies, workshop
    if player is None or player.status != "alive":
        return []
    loc = entities.get_location(conn, player.location_id)
    day = tick.get_tick(conn) // 120 + 1
    out = [f"📖 DOVE ERAVAMO — giorno {day}, " + (f"a {loc.name}, " if loc else "")
           + f"{cultivation.realm_label(conn, 'player', player.id)}."]
    rec = state.get_json(conn, KEY, None) or {}
    try:
        chronicle.ensure_table(conn)
        rows = conn.execute("SELECT * FROM chronicle_entries WHERE id>? ORDER BY id DESC LIMIT 5;",
                            (rec.get("from_id", 0),)).fetchall()
        if rows:
            out.append("L'ultima volta:")
            out += [f"  {chronicle.ICON.get(r['kind'], '·')} {r['text']}" for r in reversed(rows)]
    except Exception:                                    # noqa: BLE001
        pass
    sc = encounters.pending(conn)
    if sc:
        out.append(f"⏸ In sospeso: «{sc.get('title', 'una scena')}» aspetta una tua scelta.")
    if duel.get(conn):
        out.append("⚔ Sei a metà di un duello.")
    g = goals.plan(conn, player.id)
    if g and not g["complete"]:
        out.append(f"🎯 Obiettivo: {g['title']} ({g['done']}/{g['total']}) — ora: {g['next']['text']}"
                   + (f" ('{g['next']['cmd']}')" if g["next"]["cmd"] else ""))
    above = state.get_json(conn, "prodigies_above", []) or []
    above = [i for i in above if i in prodigies.roster(conn)]
    if above:
        names = [conn.execute("SELECT name FROM npcs WHERE id=?;", (i,)).fetchone()["name"] for i in above[:3]]
        out.append(f"⚠ Più forti di te: {', '.join(names)}" + ("…" if len(above) > 3 else "") + " ('prodigi').")
    lab = workshop.lab(conn)
    if lab and lab.get("cassa", 0) > 0:
        out.append(f"⚒ Il laboratorio a {lab['dove']} ha {lab['cassa']} pietre in cassa ('laboratorio riscuoti').")
    return out


def on_open(conn, player) -> list[str]:
    """All'apertura: il riassunto se sei stato via abbastanza; poi segna l'inizio della sessione."""
    rec = state.get_json(conn, KEY, None) or {}
    seen = state.get_int(conn, "idle_seen", 0)           # l'ultimo comando dato (vedi idle_cultivation.touch)
    away = (time.time() - seen) / 3600.0 if seen else 0.0
    out = build(conn, player) if rec and away >= RECAP_HOURS else []
    mark_session(conn)
    return out
