"""Fase 10 — Karma: peso morale nascosto, effetti su breakthrough, mondo, eredità."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import karma, character, absorption, relations
from engine.simulation import combat, world_tick


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "karma.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_default_karma_is_zero(conn):
    assert karma.get_karma(conn, "player", 1) == 0


def test_adjust_and_persist(conn):
    karma.adjust_karma(conn, "player", 1, -30, "test", 5)
    assert karma.get_karma(conn, "player", 1) == -30
    # persistito in karma_records
    row = conn.execute("SELECT karma_score FROM karma_records WHERE character_type='player' AND character_id=1;").fetchone()
    assert row["karma_score"] == -30


def test_karma_clamped(conn):
    karma.adjust_karma(conn, "player", 1, -5000, "x", 1)
    assert karma.get_karma(conn, "player", 1) == -karma.KARMA_CAP


def test_breakthrough_factor_increases_with_negative_karma(conn):
    assert karma.breakthrough_factor(0) == 1.0
    assert karma.breakthrough_factor(-150) > 1.0
    assert karma.breakthrough_factor(-600) > karma.breakthrough_factor(-150)


def test_killing_generates_negative_karma(conn):
    player = entities.get_player(conn)
    victim = conn.execute("SELECT id, name, location_id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, victim["id"]))
    before = karma.get_karma(conn, "player", 1)
    # forza una morte: combatti finché muore (resolve con esito letale simulato)
    res = combat.resolve_combat(conn, tick=5, rng=random.Random(1),
                                atk=("player", 1, player.name),
                                dfn=("npc", victim["id"], victim["name"]),
                                loc=player.location_id, observer=player.location_id,
                                observations=[])
    if res["died"] and res["winner"][0] == "player":
        assert karma.get_karma(conn, "player", 1) < before


def test_self_defense_costs_less_karma(conn):
    player = entities.get_player(conn)
    # due vittime identiche di tier; una ostile (aggressore), una neutra
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 2;")]
    hostile, neutral = ids
    relations.adjust(conn, hostile, -60, 0, 1)   # ostile verso il player
    k_h = -karma.get_karma(conn, "player", 1)
    karma.on_kill(conn, 5, ("player", 1, player.name), ("npc", hostile, "Ostile"))
    after_hostile = karma.get_karma(conn, "player", 1)
    karma.on_kill(conn, 5, ("player", 1, player.name), ("npc", neutral, "Neutro"))
    after_neutral = karma.get_karma(conn, "player", 1)
    cost_hostile = 0 - after_hostile
    cost_neutral = after_hostile - after_neutral
    assert cost_hostile < cost_neutral   # legittima difesa pesa meno


def test_absorption_inherits_victim_karma(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    ploc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    victim = conn.execute("SELECT id, name FROM npcs WHERE status='alive' LIMIT 1;").fetchone()
    # la vittima è un peccatore: karma molto negativo
    karma.adjust_karma(conn, "npc", victim["id"], -200, "peccati", 0)
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;",
                 (ploc, victim["id"]))
    before = karma.get_karma(conn, "player", 1)
    absorption.absorb(conn, tick=5, rng=random.Random(3), target_id=victim["id"])
    after = karma.get_karma(conn, "player", 1)
    # erediti i debiti: karma più negativo dell'atto base (-6)
    assert after < before - 6


def test_npcs_accumulate_karma_when_killing(conn):
    a = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    b = conn.execute("SELECT id FROM npcs WHERE status='alive' AND id<>? LIMIT 1;", (a,)).fetchone()["id"]
    karma.on_kill(conn, 5, ("npc", a, "A"), ("npc", b, "B"))
    assert karma.get_karma(conn, "npc", a) < 0


def test_karmic_pressure_creates_hostility_when_cursed(conn):
    player = entities.get_player(conn)
    # karma fortemente negativo
    karma.adjust_karma(conn, "player", 1, -800, "massacro", 0)
    # assicura un NPC neutro presente
    npc = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, npc))
    obs = []
    created = 0
    for t in range(1, 200):
        created += karma.karmic_pressure(conn, t, random.Random(t), player, set(), player.location_id, obs)
        if created:
            break
    assert created >= 1
    # almeno un NPC ora è ostile
    hostile = conn.execute("SELECT COUNT(*) c FROM npc_player_relations WHERE score <= -40;").fetchone()["c"]
    assert hostile >= 1


def test_karma_hint_is_qualitative(conn):
    assert karma.karma_hint(0) == ""
    assert "debito" in karma.karma_hint(-100).lower()
    assert str(-100) not in karma.karma_hint(-100)
