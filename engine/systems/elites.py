"""
ÉLITE E BOSS (Aggiornamento 70) — quando sei molto più forte del tuo regno, il mondo risponde.

Nel tardo gioco i bonus si sommano (tecniche, doni, Dao, attributi, equipaggiamento) e un coltivatore
dello stesso regno cade al primo colpo. Non indeboliamo te: «meglio averne più che meno». Invece alcune
persone del mondo restano al tuo passo:

  ★ ÉLITE  — circa una persona su otto (decisa una volta, stabile): tra 0,55 e 0,9 della tua forza.
  ♛ BOSS   — patriarchi e capi delle sette: tra 0,9 e 1,3 della tua forza. Nel duello hanno più fasi.

Gli altri restano come sono: puoi ancora spazzarli via, ed è giusto. Élite e boss si riconoscono nel luogo
(★ / ♛), danno premi migliori e, se li batti, il mondo lo racconta.

Vale solo quando sei davvero avanti (la persona media del luogo vale meno di DOMINANT della tua forza):
a inizio partita non cambia nulla. Il motore è lo stesso degli inseguitori (pursuers.fit): un fattore per
NPC che combat_power applica; il fattore sale soltanto, mai giù, così nessuno «si sgonfia» se perdi forza.
"""

from __future__ import annotations

import random

from engine.systems import state

KEY = "elites"
ELITE_CHANCE = 0.125
BANDS = {"elite": (0.55, 0.9), "boss": (0.9, 1.3)}
BOSS_ARCH = {"patriarca"}
DOMINANT = 0.35                      # sotto questo rapporto (lui/te) il mondo comincia a rispondere
ICON = {"elite": "★ élite", "boss": "♛ boss"}


def get(conn) -> dict:
    d = state.get_json(conn, KEY) or {}
    d.setdefault("rank", {})          # npc_id -> "elite" | "boss" | "" (deciso: nessuno)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def rank(conn, npc_id: int) -> str:
    return get(conn)["rank"].get(str(npc_id), "") or ""


def _decide(npc_id: int, archetype: str | None) -> str:
    if (archetype or "") in BOSS_ARCH:
        return "boss"
    return "elite" if random.Random(npc_id * 7919 + 13).random() < ELITE_CHANCE else ""


def touch(conn, player, npc_ids: list[int] | None = None) -> list[str]:
    """Decide (una volta) chi è élite o boss tra le persone del luogo e le porta al passo."""
    from engine.systems import pursuers
    d = get(conn)
    if npc_ids is None:
        npc_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM npcs WHERE location_id=? AND status='alive' AND id NOT IN "
            "(SELECT npc_id FROM bonds WHERE player_id=? AND kind IN ('servo','scorta','beast','companion') AND npc_id IS NOT NULL);",
            (player.location_id, player.id))]
    out: list[str] = []
    changed = False
    dom = None
    for nid in npc_ids:
        k = str(nid)
        if k not in d["rank"]:
            row = conn.execute("SELECT archetype FROM npcs WHERE id=?;", (nid,)).fetchone()
            d["rank"][k] = _decide(nid, row["archetype"] if row else "")
            changed = True
        r = d["rank"][k]
        if not r:
            continue
        lo, hi = BANDS[r]
        cur = pursuers.ratio(conn, player.id, nid)
        if cur < lo and (dom if dom is not None else (dom := _dominant(conn, player))):
            pursuers.fit(conn, player.id, nid, "vendicatore", target=random.Random(nid).uniform(lo, (lo + hi) / 2))
    if changed:
        _save(conn, d)
    return out


def _dominant(conn, player) -> bool:
    """Il mondo risponde solo se la persona media del tuo regno vale meno di DOMINANT della tua forza."""
    from engine.simulation import combat, cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    rows = conn.execute("SELECT id FROM npcs WHERE status='alive' AND kind='human' ORDER BY id LIMIT 400;").fetchall()
    peers = [r["id"] for r in rows if (cultivation.realm_tier(conn, "npc", r["id"]) or 0) == tier][:25]
    if len(peers) < 3:
        return False
    me = combat.combat_power(conn, "player", player.id)["attack"]
    vals = sorted(combat.combat_power(conn, "npc", n)["attack"] for n in peers)
    return vals[len(vals) // 2] / max(1.0, me) < DOMINANT


def daily(conn, t: int, rng, player) -> list[str]:
    try:
        return touch(conn, player)
    except Exception:                                  # noqa: BLE001
        return []


def tag(conn, npc_id: int) -> str:
    r = rank(conn, npc_id)
    return ICON.get(r, "")


def reward_rank(conn, npc_id: int) -> int | None:
    """Il rango dei premi per chi batte un élite (2) o un boss (1)."""
    r = rank(conn, npc_id)
    return 1 if r == "boss" else 2 if r == "elite" else None
