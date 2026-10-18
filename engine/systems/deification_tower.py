"""
LA TORRE DELLA DEIFICAZIONE (Aggiornamento 63) — piano dopo piano, settimana dopo settimana.

Ogni piano ha un guardiano, sempre un po' più forte del precedente, misurato su di te. Tre tentativi
al giorno. Ogni cinque piani, un premio. La torre si azzera ogni settimana (7 giorni): conta il piano
più alto che raggiungi, e accanto al tuo nome sulla lavagna della torre ci sono quelli dei prodigi del
mondo. A fine settimana, chi è più in alto riceve di più. (Spunto: la Deification Tower di Immortal
Taoists, il torneo settimanale.)

  torre            la torre, la tua settimana, la classifica
  torre sfida      affronti il guardiano del piano successivo
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "deif_tower"
WEEK = 7
TRIES = 3


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def get(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {"week": -1, "floor": 0, "best": 0, "tries_day": -1, "tries": 0,
                                            "guardian": None, "wins": 0}
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def rivals(conn, pid: int, week: int) -> list[tuple[str, int]]:
    """I prodigi del mondo sulla lavagna della torre (i più giovani e forti, coi loro piani)."""
    rows = conn.execute("SELECT name FROM npcs WHERE status='alive' AND (kind IS NULL OR kind='human') "
                        "AND archetype IN ('discepolo','giovane_maestro','erede','vagabondo') ORDER BY id LIMIT 60;").fetchall()
    rng = random.Random(week * 7919 + 17)
    names = [r["name"] for r in rows if not r["name"].startswith(("Volontà", "Guardiano", "Messaggero"))] \
        or ["Un prodigio senza nome"]
    picks = rng.sample(names, min(9, len(names)))
    top = 6 + 2 * _tier(conn, pid)
    return sorted([(n, rng.randint(2, top)) for n in picks], key=lambda x: -x[1])


def _roll_week(conn, player, d: dict, out: list) -> None:
    week = _day(conn) // WEEK
    if d["week"] == week:
        return
    if d["week"] >= 0 and d["floor"] > 0:
        board = rivals(conn, player.id, d["week"])
        rank = 1 + sum(1 for _n, f in board if f > d["floor"])
        from engine.systems import sects
        st = int(max(0, 11 - rank) * 60 * _tier(conn, player.id))
        if st:
            sects.grant_resource(conn, "pietre_spirituali", st, player.id)
        out.append(f"🗼 La settimana della Torre si chiude: sei {rank}° con il {d['floor']}° piano. +{st} pietre.")
        if rank == 1:
            state.grant_title(conn, "Primo della Torre della Deificazione")
    d["week"], d["floor"], d["guardian"] = week, 0, None


def challenge(conn, player) -> str:
    from engine.systems import npc_factory, pursuers, duel, encounters
    if encounters.pending(conn) or duel.get(conn):
        return "Prima risolvi ciò che hai davanti."
    d = get(conn)
    out: list[str] = []
    _roll_week(conn, player, d, out)
    day = _day(conn)
    if d["tries_day"] != day:
        d["tries_day"], d["tries"] = day, 0
    if d["tries"] >= TRIES:
        _save(conn, d)
        return "\n".join(out + [f"Oggi hai già usato i tuoi {TRIES} tentativi alla Torre."])
    d["tries"] += 1
    floor = d["floor"] + 1
    rng = random.Random(tick_mod.get_tick(conn) + floor * 101)
    nid = npc_factory.spawn(conn, rng, archetype="guardia", location_id=player.location_id, tier=_tier(conn, player.id),
                            stage=5, name=f"Guardiano del {floor}° Piano {rng.randint(100, 999)}",
                            traits={"courage": 95, "honor": 80}, tick=tick_mod.get_tick(conn))
    pursuers.fit(conn, player.id, nid, "campione", target=min(1.6, 0.65 + 0.045 * floor))
    d["guardian"] = nid
    _save(conn, d)
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    out.append(f"🗼 Sali al {floor}° piano della Torre della Deificazione. Ti aspetta {nm}. "
               f"(tentativo {d['tries']}/{TRIES} di oggi)")
    return "\n".join(out) + "\n" + (duel.start(conn, player, nm, arena=True) or "")


def on_duel(conn, player, npc_id: int, outcome: str) -> list[str]:
    d = get(conn)
    if d.get("guardian") != npc_id:
        return []
    d["guardian"] = None
    conn.execute("UPDATE npcs SET status='dead', location_id=NULL WHERE id=?;", (npc_id,))   # il guardiano torna nella torre
    out = []
    if outcome in ("ucciso", "risparmiato", "sigillato"):
        d["floor"] += 1
        d["best"] = max(d["best"], d["floor"])
        d["wins"] += 1
        out.append(f"🗼 Il guardiano si dissolve in luce: hai conquistato il {d['floor']}° piano.")
        if d["floor"] % 5 == 0:
            from engine.systems import rewards
            out.append("Su questo piano c'è un forziere per chi arriva fin qui:")
            out += rewards.grant(conn, random.Random(npc_id), player, rank=2 if d["floor"] < 15 else 1,
                                 kinds=["tesoro", "manuale", "pillola"], n=1)
    else:
        out.append("🗼 Il guardiano ti respinge giù per le scale. Il piano resta da conquistare.")
    _save(conn, d)
    return out


def describe(conn, player) -> str:
    d = get(conn)
    out: list[str] = []
    _roll_week(conn, player, d, out)
    _save(conn, d)
    day = _day(conn)
    tries = d["tries"] if d["tries_day"] == day else 0
    left = WEEK - day % WEEK
    lines = out + [f"🗼 LA TORRE DELLA DEIFICAZIONE — settimana {d['week'] + 1} (si chiude tra {left} giorni)",
                   f"  Il tuo piano: {d['floor']} (record: {d['best']}). Tentativi di oggi: {tries}/{TRIES}.",
                   "  La lavagna della torre:"]
    board = rivals(conn, player.id, d["week"]) + [("TU", d["floor"])]
    for i, (n, f) in enumerate(sorted(board, key=lambda x: -x[1])[:10], 1):
        lines.append(f"   {i:>2}. {n} — {f}° piano" + (" ◀" if n == "TU" else ""))
    lines.append("  ('torre sfida' per affrontare il guardiano del piano successivo)")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    if a.startswith(("sfida", "sali", "combatti")):
        return challenge(conn, player)
    return describe(conn, player)
