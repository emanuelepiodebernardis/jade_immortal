"""Fase 5 — Events System: incontri, scontri, morte differita, resolver, vincolo 26."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import event_generator, world_tick
from engine.systems import relations


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "ev.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=25))
    c.commit()
    yield c
    c.close()


def _two_hostile_colocated(conn):
    """Forza due NPC vivi nella stessa location con relazione ostile e coraggio alto."""
    npcs = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 2;").fetchall()
    a, b = npcs[0]["id"], npcs[1]["id"]
    loc = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (a,)).fetchone()["location_id"]
    conn.execute("UPDATE npcs SET location_id=? WHERE id IN (?,?);", (loc, a, b))
    for nid in (a, b):
        conn.execute("UPDATE npc_traits SET courage=80 WHERE npc_id=?;", (nid,))
    relations.adjust_npc(conn, a, b, -90, 0)
    relations.adjust_npc(conn, b, a, -90, 0)
    return a, b, loc


def test_encounters_create_npc_relationships(conn):
    world_tick.advance(conn, 60, rng=random.Random(1))
    rels = conn.execute("SELECT COUNT(*) c FROM npc_relationships;").fetchone()["c"]
    assert rels > 0


def test_deferred_death_check_mechanism(conn):
    """Il meccanismo delle conseguenze differite: una death_check programmata
    nel futuro viene applicata dal resolver quando matura."""
    from engine.simulation import event_system as ev
    npc = conn.execute("SELECT id, location_id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()
    # registra un evento con una conseguenza differita (resolved=0, tick futuro)
    ev.log_event(
        conn, event_type="fight", tick=5, location_id=npc["location_id"],
        title="ferita di prova", summary="ferita di prova",
        participants=[ev.Participant("npc", npc["id"], "target")],
        consequences=[ev.Consequence("npc", npc["id"], "death_check",
                                     "ferita grave", visibility="hidden",
                                     resolved=0, resolve_tick=12)],
    )
    # prima della maturazione: non si applica
    event_generator.resolve_due_consequences(conn, tick=8, rng=random.Random(0),
                                             observer=None, observations=[], death_prob=1.0)
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (npc["id"],)).fetchone()["status"] == "alive"
    # dopo la maturazione, con death_prob=1.0: muore e la conseguenza è risolta
    event_generator.resolve_due_consequences(conn, tick=12, rng=random.Random(0),
                                             observer=None, observations=[], death_prob=1.0)
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (npc["id"],)).fetchone()["status"] == "dead"
    unresolved = conn.execute(
        "SELECT COUNT(*) c FROM consequences WHERE consequence_type='death_check' AND resolved=0;"
    ).fetchone()["c"]
    assert unresolved == 0
    assert conn.execute("SELECT COUNT(*) c FROM events WHERE event_type='death';").fetchone()["c"] == 1


def test_leader_death_triggers_succession(conn):
    # prendi una fazione con un leader e dei membri
    f = conn.execute(
        "SELECT id, leader_id FROM factions WHERE leader_id IS NOT NULL "
        "AND (SELECT COUNT(*) FROM npcs WHERE faction_id=factions.id AND status='alive')>=2 "
        "LIMIT 1;").fetchone()
    if f is None:
        pytest.skip("nessuna fazione con leader e membri")
    leader = conn.execute(
        "SELECT id,name,location_id,status,faction_id FROM npcs WHERE id=?;", (f["leader_id"],)
    ).fetchone()
    event_generator._kill_npc(conn, tick=10, rng=random.Random(0), npc=leader,
                              observer=None, observations=[])
    new_leader = conn.execute("SELECT leader_id FROM factions WHERE id=?;", (f["id"],)).fetchone()["leader_id"]
    assert new_leader != f["leader_id"]  # cambiato (nuovo leader o NULL)


def test_all_event_types_respect_traceability(conn):
    world_tick.advance(conn, 200, rng=random.Random(4), move_probability=0.6)
    types = conn.execute("SELECT DISTINCT event_type FROM events;").fetchall()
    assert len(types) >= 2
    for e in conn.execute("SELECT id FROM events;").fetchall():
        np = conn.execute("SELECT COUNT(*) c FROM event_participants WHERE event_id=?;",
                          (e["id"],)).fetchone()["c"]
        nc = conn.execute("SELECT COUNT(*) c FROM consequences WHERE event_id=?;",
                          (e["id"],)).fetchone()["c"]
        assert np >= 1 and nc >= 1
