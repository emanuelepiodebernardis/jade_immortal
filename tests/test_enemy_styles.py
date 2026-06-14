"""Punto 1: i nemici combattono con lo stile della loro CLASSE (Guerriero Dao, Corpo, ...)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, power, zones
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "enemystyle.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _player_loc(conn):
    return conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]


def test_spawned_dao_enemy_is_classified_dao(conn):
    nid = zones._spawn_classed_npc(conn, random.Random(2), _player_loc(conn), "dao", 600, 1)
    conn.commit()
    assert power.class_of(conn, "npc", nid) == "dao"


def test_corpo_enemy_is_tankier(conn):
    loc = _player_loc(conn)
    corpo = zones._spawn_classed_npc(conn, random.Random(3), loc, "corpo", 600, 1)
    qi = zones._spawn_classed_npc(conn, random.Random(4), loc, "qi", 600, 1)
    conn.commit()
    vp_corpo = combat.combat_power(conn, "npc", corpo)["vitality"]
    vp_qi = combat.combat_power(conn, "npc", qi)["vitality"]
    assert vp_corpo > vp_qi      # il Cultivatore del Corpo è più resistente


def test_dao_enemy_intro_in_combat(conn):
    from engine.cli import loop
    loc = _player_loc(conn)
    nid = zones._spawn_classed_npc(conn, random.Random(5), loc, "dao", 500, 1)
    conn.execute("UPDATE npcs SET name='Spadaccino Errante' WHERE id=?;", (nid,))
    conn.commit()
    out = loop.cmd_attack(conn, entities.get_player(conn), "Spadaccino")
    # l'intro di stile del Guerriero Dao compare (a meno che non sia paralizzato)
    assert "intento del Dao" in out or "intento" in out.lower()


def test_enemy_class_profiles_have_distinct_effects():
    from engine.cli.loop import _ENEMY_CLASS
    assert _ENEMY_CLASS["dao"]["pierce"] > 0          # i Guerrieri Dao perforano la difesa
    assert _ENEMY_CLASS["corpo"]["dmg_mult"] > 1.0    # i Cultivatori del Corpo colpiscono forte
    assert "verbs" in _ENEMY_CLASS["anima"]           # i Maestri dell'Anima hanno un linguaggio proprio
