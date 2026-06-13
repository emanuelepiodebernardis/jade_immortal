"""
Faction engine (Fase 4) — drift autonomo delle fazioni.

Periodicamente (cadenza in world_tick) ogni fazione attiva tenta UNA azione su
un confine del proprio territorio:
  - se la location adiacente è libera -> ESPANSIONE (prob. legata all'influenza);
  - se è di un'altra fazione -> possibile CONFLITTO (prob. legata alla relazione:
    più la relazione è negativa, più è probabile; le alleanze evitano il conflitto).

Ogni azione è un evento tracciabile (vincolo 26): partecipanti = fazioni coinvolte,
conseguenze = cambi di controllo territoriale e/o di influenza.

Il drift è globale (poche fazioni): P1 riguarda il costo O(N^2) degli NPC, non le fazioni.
"""

from __future__ import annotations

import random
import sqlite3

from engine.simulation import event_system as ev


# ---------- influenza ----------

def get_influence(conn: sqlite3.Connection, fid: int) -> int:
    return conn.execute("SELECT influence FROM factions WHERE id=?;", (fid,)).fetchone()["influence"]


def _adjust_influence(conn: sqlite3.Connection, fid: int, delta: int) -> int:
    new = max(0, min(100, get_influence(conn, fid) + delta))
    conn.execute("UPDATE factions SET influence=? WHERE id=?;", (new, fid))
    return new


# ---------- relazioni (coppia normalizzata a<b) ----------

def get_relation(conn: sqlite3.Connection, x: int, y: int) -> int:
    a, b = (x, y) if x < y else (y, x)
    row = conn.execute(
        "SELECT relation_score FROM faction_relations WHERE faction_a=? AND faction_b=?;",
        (a, b),
    ).fetchone()
    return row["relation_score"] if row else 0


def _set_relation(conn: sqlite3.Connection, x: int, y: int, score: int, tick: int) -> None:
    from engine.generators.faction_gen import faction_relation_type
    a, b = (x, y) if x < y else (y, x)
    score = max(-100, min(100, score))
    conn.execute(
        "INSERT INTO faction_relations (faction_a, faction_b, relation_score, "
        "relation_type, reason, last_updated_tick) VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(faction_a, faction_b) DO UPDATE SET "
        "relation_score=excluded.relation_score, relation_type=excluded.relation_type, "
        "last_updated_tick=excluded.last_updated_tick;",
        (a, b, score, faction_relation_type(score), "evoluzione del conflitto", tick),
    )


# ---------- territorio ----------

def _owned(conn: sqlite3.Connection, fid: int) -> list[int]:
    return [r["id"] for r in conn.execute(
        "SELECT id FROM locations WHERE owner_faction_id=?;", (fid,))]


def _border_targets(conn: sqlite3.Connection, fid: int) -> list[tuple[int, int | None]]:
    """Location adiacenti al territorio di fid: (target_loc_id, owner_faction_id_or_None)."""
    targets: dict[int, int | None] = {}
    for loc in _owned(conn, fid):
        for r in conn.execute(
            "SELECT lc.to_location_id t, l.owner_faction_id o "
            "FROM location_connections lc JOIN locations l ON l.id=lc.to_location_id "
            "WHERE lc.from_location_id=?;", (loc,),
        ):
            if r["o"] != fid:
                targets[r["t"]] = r["o"]
    return list(targets.items())


def _fname(conn: sqlite3.Connection, fid: int) -> str:
    return conn.execute("SELECT name FROM factions WHERE id=?;", (fid,)).fetchone()["name"]


# ---------- drift ----------

def faction_drift(conn: sqlite3.Connection, tick: int, rng: random.Random,
                  observer_location_id: int | None = None,
                  observations: list[str] | None = None) -> int:
    events = 0
    faction_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM factions WHERE status='active' ORDER BY id;")]

    for fid in faction_ids:
        targets = _border_targets(conn, fid)
        if not targets:
            continue
        target_loc, owner = rng.choice(targets)

        if owner is None:
            events += _try_expand(conn, tick, rng, fid, target_loc,
                                  observer_location_id, observations)
        else:
            events += _try_conflict(conn, tick, rng, fid, owner, target_loc,
                                    observer_location_id, observations)
    return events


def _try_expand(conn, tick, rng, fid, target_loc, obs_loc, obs) -> int:
    infl = get_influence(conn, fid)
    if rng.random() >= max(0.2, infl / 100):
        return 0
    conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (fid, target_loc))
    gain = rng.randint(2, 6)
    _adjust_influence(conn, fid, gain)
    name = _fname(conn, fid)
    ev.log_event(
        conn, event_type="faction_expand", tick=tick, location_id=target_loc,
        title=f"{name} si espande",
        summary=f"{name} estende il proprio controllo su un nuovo territorio.",
        participants=[ev.Participant("faction", fid, "initiator")],
        consequences=[
            ev.Consequence("location", target_loc, "territory_claim",
                           f"controllo -> fazione {fid}",
                           visibility="public" if target_loc == obs_loc else "hidden",
                           resolve_tick=tick),
            ev.Consequence("faction", fid, "influence_change", f"+{gain} influenza",
                           visibility="hidden", resolve_tick=tick),
        ],
    )
    if obs is not None and target_loc == obs_loc:
        obs.append(f"La {name} ora controlla questa zona.")
    return 1


def _try_conflict(conn, tick, rng, fid, owner, target_loc, obs_loc, obs) -> int:
    rel = get_relation(conn, fid, owner)
    p_conflict = max(0.0, min(0.8, (10 - rel) / 120 + 0.05))
    if rng.random() >= p_conflict:
        return 0

    atk = get_influence(conn, fid) + rng.randint(0, 20)
    dfn = get_influence(conn, owner) + rng.randint(0, 20)
    name_a, name_d = _fname(conn, fid), _fname(conn, owner)
    consequences = []

    if atk >= dfn:  # attaccante vince: prende il territorio
        conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (fid, target_loc))
        _adjust_influence(conn, fid, rng.randint(1, 4))
        _adjust_influence(conn, owner, -rng.randint(2, 6))
        summary = f"{name_a} strappa un territorio a {name_d}."
        consequences.append(ev.Consequence(
            "location", target_loc, "territory_capture", f"controllo -> fazione {fid}",
            visibility="public" if target_loc == obs_loc else "hidden", resolve_tick=tick))
        winner_obs = f"La {name_a} conquista questa zona a {name_d}."
    else:  # difensore respinge
        _adjust_influence(conn, owner, rng.randint(1, 4))
        _adjust_influence(conn, fid, -rng.randint(2, 6))
        summary = f"{name_d} respinge l'assalto di {name_a}."
        winner_obs = f"La {name_d} respinge un assalto della {name_a}."

    _set_relation(conn, fid, owner, rel - rng.randint(5, 15), tick)

    ev.log_event(
        conn, event_type="faction_conflict", tick=tick, location_id=target_loc,
        title=f"Conflitto: {name_a} vs {name_d}",
        summary=summary,
        participants=[ev.Participant("faction", fid, "initiator"),
                      ev.Participant("faction", owner, "target")],
        consequences=consequences + [
            ev.Consequence("faction", fid, "relation_change",
                           f"relazione con {owner} peggiora", visibility="hidden",
                           resolve_tick=tick)],
    )
    if obs is not None and target_loc == obs_loc:
        obs.append(winner_obs)
    return 1
