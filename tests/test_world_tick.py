"""Fase 3 — World Tick: evoluzione autonoma, active scope (P1), vincolo 26."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick as tick_mod
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import world_tick


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "wt.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, static_npc_count=15))
    c.commit()
    yield c
    c.close()


def _player_loc(conn):
    return entities.get_player(conn).location_id


def test_world_advances_and_logs_ticks(conn):
    start = tick_mod.get_tick(conn)
    world_tick.advance(conn, 10, rng=random.Random(1))
    assert tick_mod.get_tick(conn) == start + 10
    assert conn.execute("SELECT COUNT(*) c FROM simulation_ticks;").fetchone()["c"] == 10


def test_npcs_in_scope_move_over_time(conn):
    # forza movimento per rendere il test deterministico
    before = {r["id"]: r["location_id"]
              for r in conn.execute("SELECT id, location_id FROM npcs;")}
    world_tick.advance(conn, 5, rng=random.Random(1), move_probability=1.0)
    after = {r["id"]: r["location_id"]
             for r in conn.execute("SELECT id, location_id FROM npcs;")}
    changed = [i for i in before if before[i] != after[i]]
    assert changed, "almeno un NPC nello scope deve essersi spostato"


def test_active_scope_limits_simulation(conn):
    """Gli NPC fuori dallo scope non vengono simulati (last_active_tick fermo)."""
    ploc = _player_loc(conn)
    scope = world_tick.compute_active_scope(conn, ploc)
    # un NPC chiaramente fuori scope, se esiste
    outside = conn.execute(
        "SELECT id, last_active_tick FROM npcs WHERE location_id NOT IN ({}) LIMIT 1;"
        .format(",".join(str(s) for s in scope))
    ).fetchone()
    world_tick.advance(conn, 8, rng=random.Random(2), move_probability=1.0)
    if outside is not None:
        now = conn.execute(
            "SELECT last_active_tick FROM npcs WHERE id=?;", (outside["id"],)
        ).fetchone()["last_active_tick"]
        assert now == outside["last_active_tick"], "NPC fuori scope non deve essere simulato"


def test_in_scope_npc_last_active_tick_updates(conn):
    ploc = _player_loc(conn)
    scope = world_tick.compute_active_scope(conn, ploc)
    inside = conn.execute(
        "SELECT id FROM npcs WHERE location_id IN ({}) LIMIT 1;"
        .format(",".join(str(s) for s in scope))
    ).fetchone()
    world_tick.advance(conn, 5, rng=random.Random(3), move_probability=0.0)
    if inside is not None:
        lat = conn.execute(
            "SELECT last_active_tick FROM npcs WHERE id=?;", (inside["id"],)
        ).fetchone()["last_active_tick"]
        assert lat == 5


def test_every_event_has_participant_and_consequence(conn):
    world_tick.advance(conn, 20, rng=random.Random(4), move_probability=1.0)
    events = conn.execute("SELECT id FROM events;").fetchall()
    assert len(events) > 0
    for e in events:
        np = conn.execute(
            "SELECT COUNT(*) c FROM event_participants WHERE event_id=?;", (e["id"],)
        ).fetchone()["c"]
        nc = conn.execute(
            "SELECT COUNT(*) c FROM consequences WHERE event_id=?;", (e["id"],)
        ).fetchone()["c"]
        assert np >= 1 and nc >= 1, "vincolo 26: ogni evento ha partecipante+conseguenza"


def test_deterministic_evolution(conn, tmp_path, monkeypatch):
    # stesso seed di generazione + stesso rng di simulazione -> stessa evoluzione
    world_tick.advance(conn, 12, rng=random.Random(99), move_probability=0.5)
    snap1 = sorted((r["id"], r["location_id"]) for r in
                   conn.execute("SELECT id, location_id FROM npcs;"))

    p2 = tmp_path / "wt2.db"
    monkeypatch.setattr(db, "DB_PATH", p2)
    db.init_db(p2)
    c2 = db.connect(p2)
    generate(c2, WorldGenConfig(seed=42, static_npc_count=15))
    c2.commit()
    world_tick.advance(c2, 12, rng=random.Random(99), move_probability=0.5)
    snap2 = sorted((r["id"], r["location_id"]) for r in
                   c2.execute("SELECT id, location_id FROM npcs;"))
    c2.close()
    assert snap1 == snap2
