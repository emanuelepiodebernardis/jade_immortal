"""Azioni multiple: 'attack all' (creature) e 'absorb all' (resti)."""
from __future__ import annotations
import random
from pathlib import Path
import pytest
from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen
from engine.systems import character
from engine.cli import loop
@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "multi.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "divoratore", random.Random(1))
    # giocatore forte: abbatte tutto
    r8 = c.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=8 WHERE character_type='player' AND character_id=1;", (r8,))
    c.commit()
    yield c
    c.close()
def _loc(conn):
    return conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
def test_attack_all_hits_every_creature(conn):
    loc = _loc(conn)
    for i in range(4):
        bid = creature_gen._spawn_one(conn, random.Random(i), "beast", loc, 1, 1)
        conn.execute("UPDATE npcs SET name=? WHERE id=?;", (f"Lupo{i}", bid))
    conn.commit()
    n_before = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='beast' AND status='alive';", (loc,)).fetchone()["c"]
    out = loop.cmd_attack(conn, entities.get_player(conn), "all")
    assert "creature presenti" in out.lower() or "Creature abbattute" in out
    n_after = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='beast' AND status='alive';", (loc,)).fetchone()["c"]
    assert n_after < n_before
def test_attack_all_no_creatures(conn):
    loc = conn.execute("""SELECT id FROM locations WHERE id NOT IN
        (SELECT DISTINCT location_id FROM npcs WHERE status='alive' AND location_id IS NOT NULL AND kind!='human') LIMIT 1;""").fetchone()["id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (loc,))
    conn.commit()
    out = loop.cmd_attack(conn, entities.get_player(conn), "all")
    assert "nessuna creatura" in out.lower()
def test_absorb_all_consumes_every_corpse(conn):
    loc = _loc(conn)
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 3;")]
    for i in ids:
        conn.execute("UPDATE npcs SET status='dead', death_tick=5, location_id=? WHERE id=?;", (loc, i))
    conn.execute("UPDATE npcs SET location_id=location_id+10000 WHERE location_id=? AND status='alive' AND id NOT IN (SELECT id FROM players);", (loc,))
    conn.commit()
    out = loop.cmd_absorb(conn, entities.get_player(conn), "all")
    assert "Resti assorbiti" in out
    left = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='dead';", (loc,)).fetchone()["c"]
    assert left == 0
def test_absorb_all_warns_on_witnesses(conn):
    loc = _loc(conn)
    ids = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 2;").fetchall()
    dead, witness = ids[0]["id"], ids[1]["id"]
    conn.execute("UPDATE npcs SET status='dead', death_tick=5, location_id=? WHERE id=?;", (loc, dead))
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (loc, witness))
    conn.commit()
    out = loop.cmd_absorb(conn, entities.get_player(conn), "all")
    assert "testimoni" in out.lower() and "confirm" in out.lower()
