"""Il regista: budget settimanale, distanza tra scene dello stesso tipo, coda, passo della storia."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, director, encounters
from engine.simulation import world_tick


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "dr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=4, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _sc(key):
    return {"key": key, "title": key, "text": "…", "choices": [{"label": "ok", "effects": {}}]}


def _p(conn):
    return entities.get_player(conn)


def test_same_family_is_queued_then_released(conn):
    with director.ambient():
        assert encounters.start_scene(conn, _p(conn), _sc("famiglia_minacciata"))
    encounters.clear(conn)
    with director.ambient():
        assert encounters.start_scene(conn, _p(conn), _sc("famiglia_minacciata")) is None   # troppo presto
    assert director._get(conn)["queue"]
    assert director.release(conn, _p(conn)) is None                 # ancora troppo presto
    world_tick.advance(conn, 120 * director.FAMILY_GAP)
    assert director.release(conn, _p(conn))                         # ora arriva
    assert not director._get(conn)["queue"]


def test_week_budget(conn):
    shown = 0
    for k in ("a1", "a2", "a3", "a4", "a5", "a6"):
        encounters.clear(conn)
        with director.ambient():
            if encounters.start_scene(conn, _p(conn), _sc(k)):
                shown += 1
    assert shown == director.WEEK_BUDGET


def test_user_commands_and_exempt_pass(conn):
    assert encounters.start_scene(conn, _p(conn), _sc("famiglia_minacciata"))   # da un tuo comando
    encounters.clear(conn)
    for _ in range(3):
        with director.ambient():
            assert encounters.start_scene(conn, _p(conn), _sc("calamita"))       # urgente
        encounters.clear(conn)


def test_reactive_scenes_keep_distance(conn):
    assert encounters.start_scene(conn, _p(conn), _sc("battaglia_anima"))
    encounters.clear(conn)
    assert encounters.start_scene(conn, _p(conn), _sc("battaglia_anima")) is None


def test_story_gap_and_rotation(conn):
    assert director.story_ready(conn)
    director.story_shown(conn, 0)
    assert not director.story_ready(conn)
    assert director.story_order(conn, 4)[0] == 1
    world_tick.advance(conn, 120 * director.STORY_GAP)
    assert director.story_ready(conn)
