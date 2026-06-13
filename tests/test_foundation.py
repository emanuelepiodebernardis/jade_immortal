"""Test di fondazione (tick, entità, movimento) su mondo generato."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch) -> sqlite3.Connection:
    test_db = tmp_path / "test_world.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db(test_db)
    c = db.connect(test_db)
    generate(c, WorldGenConfig(seed=42))
    c.commit()
    yield c
    c.close()


def test_schema_has_core_tables(conn):
    names = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';").fetchall()}
    for required in {"worlds", "locations", "npcs", "players",
                     "location_connections", "simulation_ticks"}:
        assert required in names


def test_world_starts_at_tick_zero(conn):
    assert tick.get_tick(conn) == 0


def test_advance_tick_logs_each_tick(conn):
    tick.advance_tick(conn, 3)
    assert tick.get_tick(conn) == 3
    assert conn.execute("SELECT COUNT(*) c FROM simulation_ticks;").fetchone()["c"] == 3


def test_zero_cost_action_does_not_advance(conn):
    assert tick.cost_of("look") == 0
    tick.advance_tick(conn, tick.cost_of("look"))
    assert tick.get_tick(conn) == 0


def test_player_starts_in_safe_city(conn):
    p = entities.get_player(conn)
    loc = entities.get_location(conn, p.location_id)
    assert loc.location_type == "city"
    assert loc.danger_level == 1


def test_move_changes_location_and_advances_tick(conn):
    p = entities.get_player(conn)
    exits = entities.get_exits(conn, p.location_id)
    assert exits, "la location iniziale deve avere almeno un'uscita"
    direction, dest = next(iter(exits.items()))
    entities.move_player(conn, p.id, dest)
    tick.advance_tick(conn, tick.cost_of("move"))
    p2 = entities.get_player(conn)
    assert p2.location_id == dest
    assert tick.get_tick(conn) == 1
