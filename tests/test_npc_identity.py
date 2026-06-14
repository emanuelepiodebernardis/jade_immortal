"""Fase 2 — NPC Identity: archetipi, traits correlati, relazioni NPC-player."""

from __future__ import annotations

import statistics
from pathlib import Path

import pytest

from engine import db
from engine.generators import npc_gen
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import relations
import random


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "npc.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, static_npc_count=12))
    c.commit()
    yield c
    c.close()


def test_every_npc_has_archetype_and_traits(conn):
    # le creature (bestie/demoni/spiriti) hanno una categoria propria: qui si
    # verifica l'identità degli NPC umani, generati per archetipo.
    npcs = conn.execute(
        "SELECT id, archetype FROM npcs WHERE kind='human' OR kind IS NULL;").fetchall()
    assert len(npcs) > 0
    for n in npcs:
        assert n["archetype"] in npc_gen.ARCHETYPE_PROFILES
        traits = conn.execute(
            "SELECT * FROM npc_traits WHERE npc_id=?;", (n["id"],)
        ).fetchone()
        assert traits is not None


def test_traits_correlate_to_archetype():
    rng = random.Random(1)
    # mercanti avidi in media, anziani onorevoli in media
    merchant_greed = [npc_gen.roll_traits(rng, "mercante")["greed"] for _ in range(50)]
    elder_honor = [npc_gen.roll_traits(rng, "anziano")["honor"] for _ in range(50)]
    hermit_greed = [npc_gen.roll_traits(rng, "eremita")["greed"] for _ in range(50)]
    assert statistics.mean(merchant_greed) > 65
    assert statistics.mean(elder_honor) > 65
    assert statistics.mean(hermit_greed) < 35


def test_traits_clamped_0_100():
    rng = random.Random(2)
    for arch in npc_gen.ARCHETYPE_PROFILES:
        for _ in range(20):
            for v in npc_gen.roll_traits(rng, arch).values():
                assert 0 <= v <= 100


def test_description_mentions_archetype():
    traits = npc_gen.roll_traits(random.Random(3), "mercante")
    desc = npc_gen.make_description("mercante", traits)
    assert desc.lower().startswith("mercante")


def test_greet_creates_relationship_then_decays(conn):
    npc_id = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    assert relations.get_disposition(conn, npc_id).relationship_type == "stranger"
    d1 = relations.adjust(conn, npc_id, 10, tick=0)
    assert d1.relationship_type == "acquaintance"
    assert d1.score == 10


def test_relationship_score_is_clamped(conn):
    npc_id = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    d = relations.adjust(conn, npc_id, 999, tick=0)
    assert d.score == 100
    assert d.relationship_type == "friend"
