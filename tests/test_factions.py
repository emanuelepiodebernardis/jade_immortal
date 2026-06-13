"""Fase 4 — Factions: generazione, membership, relazioni, drift autonomo."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import faction_engine


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "fac.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_factions_created_with_home_and_leader(conn):
    facs = conn.execute("SELECT id, home_location_id, leader_id FROM factions;").fetchall()
    assert len(facs) == 4
    for f in facs:
        assert f["home_location_id"] is not None
        assert f["leader_id"] is not None
        leader = conn.execute(
            "SELECT faction_id, archetype FROM npcs WHERE id=?;", (f["leader_id"],)
        ).fetchone()
        assert leader["faction_id"] == f["id"]
        assert leader["archetype"] == "patriarca"


def test_each_faction_controls_at_least_home(conn):
    for f in conn.execute("SELECT id FROM factions;"):
        owned = conn.execute(
            "SELECT COUNT(*) c FROM locations WHERE owner_faction_id=?;", (f["id"],)
        ).fetchone()["c"]
        assert owned >= 1


def test_relations_exist_for_all_pairs(conn):
    n = conn.execute("SELECT COUNT(*) c FROM factions;").fetchone()["c"]
    rels = conn.execute("SELECT COUNT(*) c FROM faction_relations;").fetchone()["c"]
    assert rels == n * (n - 1) // 2


def test_some_npcs_are_members(conn):
    members = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE faction_id IS NOT NULL;"
    ).fetchone()["c"]
    assert members >= 4  # almeno i leader


def test_relation_normalization(conn):
    fids = [r["id"] for r in conn.execute("SELECT id FROM factions ORDER BY id;")]
    a, b = fids[0], fids[1]
    # get_relation deve dare lo stesso valore in entrambi i versi
    assert faction_engine.get_relation(conn, a, b) == faction_engine.get_relation(conn, b, a)


def test_drift_produces_traceable_events_and_change(conn):
    rng = random.Random(7)
    before_owners = {r["id"]: r["owner_faction_id"]
                     for r in conn.execute("SELECT id, owner_faction_id FROM locations;")}
    before_infl = {r["id"]: r["influence"]
                   for r in conn.execute("SELECT id, influence FROM factions;")}
    total = 0
    for cycle in range(15):
        total += faction_engine.faction_drift(conn, tick=cycle, rng=rng)
    assert total > 0, "il drift deve produrre azioni in 15 cicli"

    # qualcosa è cambiato (territori o influenza)
    after_owners = {r["id"]: r["owner_faction_id"]
                    for r in conn.execute("SELECT id, owner_faction_id FROM locations;")}
    after_infl = {r["id"]: r["influence"]
                  for r in conn.execute("SELECT id, influence FROM factions;")}
    assert before_owners != after_owners or before_infl != after_infl

    # vincolo 26 su tutti gli eventi di fazione
    fac_events = conn.execute(
        "SELECT id FROM events WHERE event_type IN ('faction_expand','faction_conflict');"
    ).fetchall()
    assert len(fac_events) > 0
    for e in fac_events:
        np = conn.execute("SELECT COUNT(*) c FROM event_participants WHERE event_id=?;",
                          (e["id"],)).fetchone()["c"]
        nc = conn.execute("SELECT COUNT(*) c FROM consequences WHERE event_id=?;",
                          (e["id"],)).fetchone()["c"]
        assert np >= 1 and nc >= 1


def test_conflict_has_two_faction_participants(conn):
    rng = random.Random(3)
    for cycle in range(40):
        faction_engine.faction_drift(conn, tick=cycle, rng=rng)
    conflicts = conn.execute(
        "SELECT id FROM events WHERE event_type='faction_conflict';").fetchall()
    if conflicts:  # se almeno un conflitto è avvenuto
        for e in conflicts:
            parts = conn.execute(
                "SELECT COUNT(*) c FROM event_participants "
                "WHERE event_id=? AND participant_type='faction';", (e["id"],)
            ).fetchone()["c"]
            assert parts == 2
