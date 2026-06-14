"""Archetipi e punti diretti dai Dao: vie, crescita per sessione, impatto in combattimento."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, progression, dao_training
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "prog.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_dao_tier_points_scale_with_threshold():
    assert dao_training.dao_tier_points(0) == 0
    assert dao_training.dao_tier_points(10) > 0
    assert dao_training.dao_tier_points(100) > dao_training.dao_tier_points(25)
    assert dao_training.dao_tier_points(1000) == max(dao_training.DAO_TIER_POINTS)


def test_dao_points_go_to_mapped_stat(conn):
    # un Dao d'arma (spada) versa in ATTACCO; il Dao del Corpo in VITALITÀ
    dao_gen._set_dao(conn, "player", 1, "spada", affinity=80, comprehension=100, practiced=1)
    dao_gen._set_dao(conn, "player", 1, "corpo", affinity=80, comprehension=100, practiced=1)
    pts = dao_training.dao_stat_points(conn, "player", 1)
    assert pts["attack"] >= 20 and pts["vitality"] >= 20


def test_high_dao_raises_combat_power(conn):
    before = combat.combat_power(conn, "player", 1)["attack"]
    dao_gen._set_dao(conn, "player", 1, "spada", affinity=80, comprehension=250, practiced=1)
    after = combat.combat_power(conn, "player", 1)["attack"]
    assert after > before                      # i punti diretti aumentano la potenza


def test_path_starts_undecided_then_diverges(conn):
    assert progression.path(conn)[0] == "none"
    for _ in range(12):
        progression.record_dao_training(conn)
    assert progression.path(conn)[0] == "dao"
    # ribilancia verso la coltivazione
    for _ in range(40):
        progression.record_cultivation(conn)
    assert progression.path(conn)[0] == "cult"


def test_dao_path_amplifies_dao_points(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", affinity=80, comprehension=100, practiced=1)
    # baseline equilibrato
    for _ in range(5):
        progression.record_dao_training(conn)
    for _ in range(5):
        progression.record_cultivation(conn)
    bal = progression.growth_bonuses(conn, "player", 1)["attack"]
    # spingi forte sulla Via del Dao
    for _ in range(40):
        progression.record_dao_training(conn)
    assert progression.path(conn)[0] == "dao"
    dao = progression.growth_bonuses(conn, "player", 1)["attack"]
    assert dao > bal                           # la via amplifica i punti dei Dao


def test_cultivation_builds_foundation(conn):
    base_vit = combat.combat_power(conn, "player", 1)["vitality"]
    for _ in range(30):
        progression.record_cultivation(conn)
    after = combat.combat_power(conn, "player", 1)["vitality"]
    assert after > base_vit                     # coltivare rafforza le fondamenta (vitalità)


def test_npcs_get_dao_points_too(conn):
    npc = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()["id"]
    before = combat.combat_power(conn, "npc", npc)["attack"]
    dao_gen._set_dao(conn, "npc", npc, "spada", affinity=80, comprehension=250, practiced=1)
    after = combat.combat_power(conn, "npc", npc)["attack"]
    assert after > before                       # anche gli NPC con Dao alti sono più forti
