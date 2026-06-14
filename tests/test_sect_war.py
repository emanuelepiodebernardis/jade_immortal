"""Guerre tra sette: dichiarazione, scelte uccidi/risparmia/assorbi, tradimento, risoluzione."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, sect_war, sects, guild, reputation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "war.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=25))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _enroll(conn):
    """Iscrive il giocatore d'ufficio alla prima setta con sede, per i test."""
    fac = conn.execute("SELECT id, home_location_id FROM factions WHERE home_location_id IS NOT NULL "
                       "AND leader_id IS NOT NULL LIMIT 1;").fetchone()
    conn.execute("INSERT INTO sect_memberships (player_id, faction_id, rank, joined_tick) "
                 "VALUES (1, ?, 'discepolo esterno', 0) "
                 "ON CONFLICT(player_id) DO UPDATE SET faction_id=excluded.faction_id;",
                 (fac["id"],))
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (fac["home_location_id"],))
    conn.commit()
    return fac["id"]


def test_no_war_without_sect(conn):
    player = entities.get_player(conn)
    assert sect_war.maybe_declare(conn, 60, random.Random(1), player, []) == 0


def test_war_declares_and_spawns_combatants(conn):
    pfac = _enroll(conn)
    player = entities.get_player(conn)
    n = sect_war.maybe_declare(conn, 60, random.Random(2), player, [])
    assert n == 1
    war = sect_war.active_war(conn)
    assert war is not None and war["player_faction_id"] == pfac
    assert len(sect_war.enemy_disciples(conn, war)) >= 4
    assert len(sect_war.ally_disciples(conn, war)) >= 2


def test_kill_enemy_gives_merit(conn):
    _enroll(conn)
    player = entities.get_player(conn)
    sect_war.maybe_declare(conn, 60, random.Random(3), player, [])
    war = sect_war.active_war(conn)
    enemy = sect_war.enemy_disciples(conn, war)[0]
    merit0 = guild.get_merit(conn, 1)
    msg = sect_war.on_enemy_defeated(conn, 61, player, enemy["id"], "kill")
    assert msg and guild.get_merit(conn, 1) > merit0
    assert sect_war.active_war(conn)["score_player"] == 1


def test_spare_enemy_gives_fame_and_removes_from_war(conn):
    _enroll(conn)
    player = entities.get_player(conn)
    sect_war.maybe_declare(conn, 60, random.Random(4), player, [])
    war = sect_war.active_war(conn)
    enemy = sect_war.enemy_disciples(conn, war)[0]
    fame0 = reputation.get(conn, 1)["fame"]
    sect_war.on_enemy_defeated(conn, 61, player, enemy["id"], "spare")
    assert reputation.get(conn, 1)["fame"] > fame0
    # risparmiato: non è più un combattente della guerra
    assert conn.execute("SELECT war_id FROM npcs WHERE id=?;", (enemy["id"],)).fetchone()["war_id"] is None


def test_absorbing_ally_makes_sect_suspect_you(conn):
    _enroll(conn)
    player = entities.get_player(conn)
    sect_war.maybe_declare(conn, 60, random.Random(5), player, [])
    war = sect_war.active_war(conn)
    ally = sect_war.ally_disciples(conn, war)[0]
    score_enemy0 = war["score_enemy"]
    msg = sect_war.on_enemy_defeated(conn, 61, player, ally["id"], "absorb")
    assert msg is not None and "sospett" in msg.lower()
    assert sect_war.active_war(conn)["score_enemy"] == score_enemy0 + 1


def test_resolution_win_rewards_contribution(conn):
    _enroll(conn)
    player = entities.get_player(conn)
    sect_war.maybe_declare(conn, 60, random.Random(6), player, [])
    war = sect_war.active_war(conn)
    # vinci abbattendo tutti i nemici
    for e in sect_war.enemy_disciples(conn, war):
        conn.execute("UPDATE npcs SET status='dead', death_tick=61 WHERE id=?;", (e["id"],))
        sect_war.on_enemy_defeated(conn, 61, player, e["id"], "kill")
    merit0 = guild.get_merit(conn, 1)
    fired = sect_war.resolve(conn, 200, random.Random(6), player, [])
    assert fired == 1
    w = conn.execute("SELECT status FROM sect_wars ORDER BY id DESC LIMIT 1;").fetchone()
    assert w["status"] == "won"
    assert guild.get_merit(conn, 1) > merit0


def test_resolution_ignored_war_weakens_sect(conn):
    pfac = _enroll(conn)
    player = entities.get_player(conn)
    sect_war.maybe_declare(conn, 60, random.Random(7), player, [])
    inf0 = conn.execute("SELECT influence FROM factions WHERE id=?;", (pfac,)).fetchone()["influence"]
    # ignori del tutto: forza il punteggio nemico in modo che la tua setta perda
    war = sect_war.active_war(conn)
    conn.execute("UPDATE sect_wars SET score_enemy=50 WHERE id=?;", (war["id"],))
    sect_war.resolve(conn, 200, random.Random(7), player, [])
    inf1 = conn.execute("SELECT influence FROM factions WHERE id=?;", (pfac,)).fetchone()["influence"]
    assert inf1 < inf0
    assert conn.execute("SELECT status FROM sect_wars ORDER BY id DESC LIMIT 1;").fetchone()["status"] == "lost"
