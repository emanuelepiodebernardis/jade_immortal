"""Qi come risorsa per le mosse: pool dal regno, consumo, niente recupero combattendo."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, sects, sect_life, weapons, qi, moves


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "qi.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _set_realm(conn, tier):
    rid = conn.execute("SELECT id FROM cultivation_realms WHERE tier=?;", (tier,)).fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


def test_max_qi_grows_with_realm(conn):
    _set_realm(conn, 1)
    low = qi.max_qi(conn)
    _set_realm(conn, 6)
    high = qi.max_qi(conn)
    assert high > low                       # regni più alti -> più Qi


def test_qi_starts_full(conn):
    assert qi.get_qi(conn) == qi.max_qi(conn)


def test_spending_qi_depletes_pool(conn):
    full = qi.get_qi(conn)
    assert qi.spend(conn, 30) is True
    assert qi.get_qi(conn) == full - 30


def test_cannot_spend_more_than_have(conn):
    _set_realm(conn, 1)
    qi._set(conn, 1, 10)
    assert qi.can_afford(conn, 40) is False
    assert qi.spend(conn, 40) is False
    assert qi.get_qi(conn) == 10            # invariato


def test_move_blocked_when_qi_exhausted(conn):
    from engine.cli import loop
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0); sect_life.setup_class(conn, 0, random.Random(1))
    weapons.choose_weapon(conn, "spada", 1)
    # svuota il Qi: la mossa è in cooldown-ready ma non affordable
    qi._set(conn, 1, 0)
    mv = moves.find_move(conn, "fendente", 1)
    assert mv["ready"] is True and mv["affordable"] is False
    # un NPC qualunque presente per tentare l'attacco
    npc = conn.execute("SELECT name, location_id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (npc["location_id"],))
    player = entities.get_player(conn)
    out = loop.cmd_attack(conn, player, f"{npc['name'].split()[0]} fendente")
    assert "Qi insufficiente" in out


def test_attacking_does_not_restore_qi_but_resting_does(conn):
    qi._set(conn, 1, 20)
    before = qi.get_qi(conn)
    # un attacco normale non ripristina il Qi
    from engine.cli import loop
    npc = conn.execute("SELECT name, location_id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (npc["location_id"],))
    player = entities.get_player(conn)
    loop.cmd_attack(conn, player, npc["name"].split()[0])     # attacco normale (nessuna mossa)
    assert qi.get_qi(conn) <= before + 0          # non aumenta combattendo
    # riposare invece recupera
    loop.cmd_wait(conn, entities.get_player(conn))
    assert qi.get_qi(conn) > before
