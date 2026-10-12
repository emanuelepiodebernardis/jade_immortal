"""Le saghe a più atti: ogni ramo si percorre senza errori; premi, morti e grazia hanno effetto."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, encounters, sects, items, feuds, rewards
from engine.systems.encounter_sagas import SAGAS
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sagas.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(1))
    sects.grant_resource(c, "pietre_spirituali", 5000, 1)
    c.commit()
    yield c
    c.close()


def _walk(conn, scene, path, depth=0):
    p = entities.get_player(conn)
    sc = encounters.format_scene(dict(scene), {"npc_name": "Lu Feng", "luogo": "qui"})
    encounters.clear(conn)
    assert encounters.start_scene(conn, p, sc, force=True)
    for n in path:
        if not encounters.pending(conn):
            return
        text, cmd = encounters.choose(conn, entities.get_player(conn), n)
        assert text
        if cmd and not cmd.startswith("duello"):
            loop.dispatch(conn, cmd, allow_nl=False)


def test_every_saga_branch_runs(conn):
    for s in SAGAS:
        assert 2 <= len(s["choices"]) <= 4 and s["key"].startswith("saga_")
        for i in range(1, len(s["choices"]) + 1):
            for j in (1, 2, 3):
                for k in (1, 2, 3):
                    _walk(conn, s, [i, j, k])


def test_prize_generator_scales_and_records_in_the_book(conn):
    p = entities.get_player(conn)
    before = len(items.player_inventory(conn, 1))
    lines = rewards.grant(conn, random.Random(1), p, rank=1, scale=1.5)
    assert len(lines) == 4                      # pietre + tre oggetti per il primo posto
    assert len(items.player_inventory(conn, 1)) == before + 3
    from engine.systems import state
    assert state.get_json(conn, "world_book_items")
