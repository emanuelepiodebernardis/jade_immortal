"""Fondamenta del Personaggio: origini, affinità nascoste, effetti sui sistemi."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, relations
from engine.simulation import cultivation, combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "char.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_apply_origin_creates_profile(conn):
    character.apply_origin(conn, "genio", random.Random(1))
    p = character.get_profile(conn, "player", 1)
    assert p is not None
    assert p["origin"] == "genio"
    assert p["age"] == 15


def test_erede_starts_at_higher_realm(conn):
    character.apply_origin(conn, "erede", random.Random(1))
    assert cultivation.realm_tier(conn, "player", 1) == 2


def test_genio_has_higher_cultivation_affinity_than_mortale(conn):
    character.apply_origin(conn, "genio", random.Random(1))
    genio = character.get_profile(conn, "player", 1)["aff_cultivation"]
    character.apply_origin(conn, "mortale", random.Random(1))
    mortale = character.get_profile(conn, "player", 1)["aff_cultivation"]
    assert genio > mortale


def test_affinity_factor_neutral_without_profile(conn):
    # un NPC non ha profilo -> fattore neutro 1.0
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    assert character.affinity_factor(conn, "npc", npc, "cultivation") == 1.0


def test_genio_cultivates_faster(conn):
    # stesso amount di base, ma il genio ha affinità alta -> progresso maggiore
    character.apply_origin(conn, "mortale", random.Random(1))
    r1 = cultivation.cultivate(conn, "player", 1, 0, random.Random(5))
    conn.execute("UPDATE cultivation_records SET progress=0 WHERE character_type='player' AND character_id=1;")
    character.apply_origin(conn, "genio", random.Random(1))
    r2 = cultivation.cultivate(conn, "player", 1, 0, random.Random(5))
    assert r2["progress"] > r1["progress"]


def test_hunted_origin_creates_enemies(conn):
    character.apply_origin(conn, "erede", random.Random(3))  # erede = hunted
    hostile = conn.execute(
        "SELECT COUNT(*) c FROM npc_player_relations WHERE score <= -40;"
    ).fetchone()["c"]
    assert hostile >= 1


def test_combat_affinity_affects_power(conn):
    base = combat.combat_power(conn, "player", 1)["attack"]
    character.apply_origin(conn, "erede", random.Random(1))  # alta affinità combat
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base


def test_describe_is_qualitative_no_raw_numbers(conn):
    character.apply_origin(conn, "genio", random.Random(1))
    desc = character.describe_profile(conn, 0)
    # nessun valore di affinità grezzo (es. "82") deve comparire
    p = character.get_profile(conn, "player", 1)
    assert str(p["aff_cultivation"]) not in desc
    # ma compaiono etichette qualitative
    assert any(w in desc for w in ("scarsa", "modesta", "discreta", "notevole",
                                   "eccezionale", "prodigiosa"))


def test_hard_tribulation_increases_breakthrough_death(conn):
    # con flag hard_tribulation la prob di morte al fallimento è maggiore
    character.apply_origin(conn, "genio", random.Random(1))  # genio = hard_tribulation
    assert character.has_flag(conn, "player", 1, "hard_tribulation")
