"""Mete e comandi diretti: vai, iscriviti."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, travel, assembly, state, suggestions
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "tv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _far_city(conn):
    return conn.execute("SELECT id, name FROM locations WHERE location_type='city' AND id<>? ORDER BY id DESC LIMIT 1;",
                        (_p(conn).location_id,)).fetchone()


def test_go_to_a_place_by_name(conn):
    city = _far_city(conn)
    t0 = tick.get_tick(conn)
    out = loop.dispatch(conn, f"vai {city['name']}", allow_nl=False)
    assert _p(conn).location_id == city["id"] and "arrivi" in out
    assert tick.get_tick(conn) > t0                       # il viaggio costa tempo


def test_destinations_and_join(conn):
    city = _far_city(conn)
    day = tick.get_tick(conn) // 120
    state.set_json(conn, "assembly", {"loc": city["id"], "city": city["name"], "end_day": day + 5,
                                      "joined": False, "done": False, "round": 0})
    lst = loop.dispatch(conn, "mete", allow_nl=False)
    assert "Grande Assemblea" in lst
    assert any(c.startswith("iscriviti assemblea") for _l, c in suggestions.compute(conn, _p(conn)))
    out = loop.dispatch(conn, "iscriviti assemblea", allow_nl=False)
    assert _p(conn).location_id == city["id"]
    from engine.systems import encounters
    if encounters.pending(conn):                     # all'arrivo è successo qualcosa: lo risolvi, poi ti iscrivi
        assert "interrotto" in out
        encounters.clear(conn)
        out = loop.dispatch(conn, "iscriviti assemblea", allow_nl=False)
    assert assembly.current(conn)["joined"] or "Assemblea" in out


def test_plain_iscriviti_still_joins_sect(conn):
    # senza argomento resta il vecchio 'iscriviti' alla setta
    assert travel.join(conn, _p(conn), "") is None
