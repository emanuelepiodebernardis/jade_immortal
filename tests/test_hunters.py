"""Cacciatori dell'Eretico: comparsa per notorietà, inseguimento, maschera = fuga, sconfitta."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, reputation, hunters


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "hunt.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_no_hunters_when_reputation_clean(conn):
    player = entities.get_player(conn)
    assert hunters._threat_tier(conn, 1) == 0
    n = hunters.maybe_spawn(conn, 30, random.Random(1), player, [])
    assert n == 0
    assert hunters.active_hunters(conn) == []


def test_high_suspicion_spawns_a_hunter(conn):
    reputation.adjust(conn, 1, suspicion=700)
    player = entities.get_player(conn)
    obs = []
    n = hunters.maybe_spawn(conn, 30, random.Random(2), player, obs)
    assert n == 1
    hs = hunters.active_hunters(conn)
    assert len(hs) == 1
    assert any("tracce" in o for o in obs)


def test_hunter_cap_scales_with_tier(conn):
    player = entities.get_player(conn)
    # tier 1: massimo 1 cacciatore
    reputation.adjust(conn, 1, suspicion=600)
    hunters.maybe_spawn(conn, 30, random.Random(3), player, [])
    assert hunters.maybe_spawn(conn, 60, random.Random(4), player, []) == 0
    assert len(hunters.active_hunters(conn)) == 1


def test_hunter_pursues_toward_player(conn):
    reputation.adjust(conn, 1, suspicion=1200)
    player = entities.get_player(conn)
    hunters.maybe_spawn(conn, 30, random.Random(5), player, [])
    h = hunters.active_hunters(conn)[0]
    start = h["location_id"]
    # se non è già co-locato, dopo un inseguimento deve avvicinarsi/raggiungere
    for tk in range(40):
        hunters.pursue(conn, 100 + tk, random.Random(tk), entities.get_player(conn), [])
        cur = conn.execute("SELECT location_id, status FROM npcs WHERE id=?;", (h["id"],)).fetchone()
        if cur["location_id"] == player.location_id or cur["status"] != "alive":
            break
    # ha raggiunto il giocatore (o lo scontro è già avvenuto)
    reached = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (h["id"],)).fetchone()
    assert reached is None or reached["location_id"] == player.location_id or \
        conn.execute("SELECT status FROM players WHERE id=1;").fetchone()["status"] != "alive"


def test_mask_lets_you_lose_hunters(conn):
    reputation.adjust(conn, 1, suspicion=1200)
    player = entities.get_player(conn)
    hunters.maybe_spawn(conn, 30, random.Random(6), player, [])
    reputation.set_disguise(conn, 1, True)        # mask on
    # con la maschera, prima o poi perdono le tracce (rinunciano)
    lost = False
    for tk in range(60):
        hunters.pursue(conn, 200 + tk, random.Random(tk + 1), entities.get_player(conn), [])
        if not hunters.active_hunters(conn):
            lost = True
            break
    assert lost


def test_defeating_hunter_reduces_suspicion(conn):
    reputation.adjust(conn, 1, suspicion=1200)
    player = entities.get_player(conn)
    hunters.maybe_spawn(conn, 30, random.Random(7), player, [])
    h = hunters.active_hunters(conn)[0]
    before = reputation.get(conn)["suspicion"]
    msg = hunters.on_hunter_defeated(conn, h["id"], player)
    assert msg is not None
    assert reputation.get(conn)["suspicion"] < before


def test_hunter_is_renowned_for_perception(conn):
    from engine.systems import perception
    reputation.adjust(conn, 1, suspicion=1200)
    player = entities.get_player(conn)
    hunters.maybe_spawn(conn, 30, random.Random(8), player, [])
    h = hunters.active_hunters(conn)[0]
    assert perception.is_renowned(conn, h["id"]) is True
