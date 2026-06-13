"""Taglie & criminali: ricercati, twist karmico (giustizia), ricompense, assorbimento corruttivo."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import bounties, karma, character, absorption, sects


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "bty.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=25))
    c.commit()
    yield c
    c.close()


def test_outlaws_seeded(conn):
    assert len(bounties.active_bounties(conn)) >= 3


def test_outlaws_have_negative_karma(conn):
    nid = bounties.active_bounties(conn)[0]["npc_id"]
    assert karma.get_karma(conn, "npc", nid) < 0


def test_killing_outlaw_is_righteous(conn):
    nid = bounties.active_bounties(conn)[0]["npc_id"]
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    before = karma.get_karma(conn, "player", 1)
    karma.on_kill(conn, 5, ("player", 1, "Tu"), ("npc", nid, name))
    after = karma.get_karma(conn, "player", 1)
    assert after > before          # giustizia = karma positivo


def test_killing_innocent_is_negative(conn):
    # un NPC non ricercato
    outlaw_ids = {b["npc_id"] for b in bounties.active_bounties(conn)}
    innocent = conn.execute(
        "SELECT id, name FROM npcs WHERE status='alive' AND id NOT IN ({}) LIMIT 1;".format(
            ",".join(str(i) for i in outlaw_ids) or "0")).fetchone()
    before = karma.get_karma(conn, "player", 1)
    karma.on_kill(conn, 5, ("player", 1, "Tu"), ("npc", innocent["id"], innocent["name"]))
    assert karma.get_karma(conn, "player", 1) < before


def test_claim_bounty_grants_reward_and_resolves(conn):
    b = bounties.active_bounties(conn)[0]
    nid, reward = b["npc_id"], b["reward"]
    conn.execute("UPDATE players SET location_id=(SELECT location_id FROM npcs WHERE id=?) WHERE id=1;", (nid,))
    before = sects.get_resource(conn, "pietre_spirituali")
    res = bounties.claim(conn, 5, nid, 1)
    assert res["status"] == "claimed"
    assert res["reward"] == reward
    assert sects.get_resource(conn, "pietre_spirituali") == before + reward
    assert not bounties.is_outlaw(conn, nid)        # taglia risolta
    assert conn.execute("SELECT COUNT(*) c FROM events WHERE event_type='bounty_claimed';").fetchone()["c"] == 1


def test_absorbing_outlaw_still_corrupts(conn):
    # giustizia (kill) è positiva, ma divorare un criminale eredita i suoi peccati
    character.apply_origin(conn, "divoratore", random.Random(1))
    b = bounties.active_bounties(conn)[0]
    nid = b["npc_id"]
    ploc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;", (ploc, nid))
    before = karma.get_karma(conn, "player", 1)
    absorption.absorb(conn, tick=5, rng=random.Random(3), target_id=nid)
    after = karma.get_karma(conn, "player", 1)
    assert after < before          # divorare un peccatore corrompe (eredità karmica)


def test_replenish_keeps_minimum(conn):
    # risolvi tutte le taglie, poi ricostituisci
    for b in bounties.active_bounties(conn):
        conn.execute("UPDATE outlaws SET resolved=1 WHERE npc_id=?;", (b["npc_id"],))
    assert len(bounties.active_bounties(conn)) == 0
    bounties.replenish(conn, random.Random(1))
    assert len(bounties.active_bounties(conn)) >= bounties.MIN_OUTLAWS
