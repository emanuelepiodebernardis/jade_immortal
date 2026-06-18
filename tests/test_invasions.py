"""Invasioni mondiali 'vive': terzo tipo (spiriti), campione, rinforzi, difensori locali,
ricompense scalate con bottino."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, world_events as we, sects, items


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "inv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=11, factions=3, static_npc_count=25))
    character.apply_origin(c, "genio", random.Random(1))
    # tier alto → minaccia alta → campione garantito
    r6 = c.execute("SELECT id FROM cultivation_realms WHERE tier=6;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (r6,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=5 WHERE character_type='player' AND character_id=1;", (r6,))
    c.commit()
    yield c
    c.close()


def test_spirit_kind_exists():
    assert "spirit_incursion" in we.KIND_LABEL
    assert we._KIND_CREATURE["spirit_incursion"] == "spirit"


def test_strong_invasion_has_champion(conn):
    player = entities.get_player(conn)
    we.maybe_spawn(conn, 0, random.Random(7), player, [])
    ev = we.active_event(conn)
    assert ev["champion_id"] is not None
    champ = conn.execute("SELECT name, kind FROM npcs WHERE id=?;", (ev["champion_id"],)).fetchone()
    assert champ["name"] in we._CHAMPION_NAME.values()


def test_reinforcements_grow_the_wave(conn):
    player = entities.get_player(conn)
    we.maybe_spawn(conn, 0, random.Random(7), player, [])
    ev = we.active_event(conn)
    before = ev["wave_total"]
    obs = []
    we.escalate(conn, we.REINFORCE_INTERVAL + 1, random.Random(1), obs)
    after = we.active_event(conn)["wave_total"]
    assert after > before
    assert any("Rinforzi" in o for o in obs)


def test_local_defenders_kill_but_not_champion(conn):
    player = entities.get_player(conn)
    we.maybe_spawn(conn, 0, random.Random(7), player, [])
    ev = we.active_event(conn)
    champ = ev["champion_id"]
    # sopprimi i rinforzi (reinforce_tick alto) e chiama escalate con tick basso molte volte
    conn.execute("UPDATE world_events SET reinforce_tick=9999 WHERE id=?;", (ev["id"],))
    start = len(we._alive_invaders(conn, ev["id"]))
    for _ in range(40):
        we.escalate(conn, 1, random.Random(random.randint(1, 10**6)), [])
        if conn.execute("SELECT status FROM world_events WHERE id=?;", (ev["id"],)).fetchone()["status"] != "active":
            break
    # il campione non viene mai abbattuto dai locali
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (champ,)).fetchone()["status"] == "alive"
    # ma qualche invasore comune sì
    assert len(we._alive_invaders(conn, ev["id"])) < start


def test_repel_scales_and_drops_trophy(conn):
    player = entities.get_player(conn)
    we.maybe_spawn(conn, 0, random.Random(7), player, [])
    ev = we.active_event(conn)
    s0 = sects.get_resource(conn, "pietre_spirituali", 1)
    invaders = we._alive_invaders(conn, ev["id"])
    msg = None
    for nid in invaders:
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (nid,))
        msg = we.on_creature_killed(conn, nid, 5, player)
    assert msg and "respinto" in msg.lower()
    assert sects.get_resource(conn, "pietre_spirituali", 1) - s0 > 0
    assert any("Trofeo" in r["name"] for r in items.player_inventory(conn, 1))


def test_champion_kill_special_line(conn):
    player = entities.get_player(conn)
    we.maybe_spawn(conn, 0, random.Random(7), player, [])
    ev = we.active_event(conn)
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (ev["champion_id"],))
    msg = we.on_creature_killed(conn, ev["champion_id"], 5, player)
    assert "campione" in (msg or "").lower()
