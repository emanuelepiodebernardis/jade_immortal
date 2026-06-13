"""Proprietà del generatore procedurale (Fase 1)."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def _make(tmp_path: Path, monkeypatch, seed=42, tag=""):
    p = tmp_path / f"w_{seed}{tag}.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=seed))
    c.commit()
    return c


def test_graph_is_fully_connected(tmp_path, monkeypatch):
    c = _make(tmp_path, monkeypatch)
    all_ids = {r["id"] for r in c.execute("SELECT id FROM locations;")}
    start = c.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    adj = {}
    for r in c.execute("SELECT from_location_id f, to_location_id t FROM location_connections;"):
        adj.setdefault(r["f"], []).append(r["t"])
    seen, q = {start}, deque([start])
    while q:
        for nb in adj.get(q.popleft(), []):
            if nb not in seen:
                seen.add(nb); q.append(nb)
    assert seen == all_ids, "ogni location deve essere raggiungibile dallo start"


def test_all_connections_are_reciprocal(tmp_path, monkeypatch):
    c = _make(tmp_path, monkeypatch)
    edges = {(r["f"], r["d"], r["t"]) for r in c.execute(
        "SELECT from_location_id f, direction d, to_location_id t FROM location_connections;")}
    for f, d, t in edges:
        assert (t, OPP[d], f) in edges, f"manca l'arco reciproco per {(f, d, t)}"


def test_no_duplicate_direction_per_location(tmp_path, monkeypatch):
    c = _make(tmp_path, monkeypatch)
    rows = c.execute(
        "SELECT from_location_id f, direction d, COUNT(*) n "
        "FROM location_connections GROUP BY f, d HAVING n > 1;").fetchall()
    assert rows == []


def test_deterministic_same_seed(tmp_path, monkeypatch):
    c1 = _make(tmp_path, monkeypatch, seed=7, tag="a")
    names1 = [r["name"] for r in c1.execute("SELECT name FROM locations ORDER BY id;")]
    c2 = _make(tmp_path, monkeypatch, seed=7, tag="b")
    names2 = [r["name"] for r in c2.execute("SELECT name FROM locations ORDER BY id;")]
    assert names1 == names2 and len(names1) > 0


def test_npcs_placed_in_valid_locations(tmp_path, monkeypatch):
    c = _make(tmp_path, monkeypatch)
    loc_ids = {r["id"] for r in c.execute("SELECT id FROM locations;")}
    npc_rows = c.execute("SELECT location_id FROM npcs;").fetchall()
    assert len(npc_rows) > 0
    for r in npc_rows:
        assert r["location_id"] in loc_ids
