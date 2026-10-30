"""Aggiornamento 72: l'album illustrato e i suoi premi."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, album, state, sects


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "al.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    c.commit()
    yield c
    c.close()


def test_pages_and_progress(conn):
    p = entities.get_player(conn)
    v = album.view(conn, p)
    assert [x["key"] for x in v["pagine"]] == [k for k, _t in album.PAGES]
    assert all(x["totale"] > 0 for x in v["pagine"])
    assert next(x for x in v["pagine"] if x["key"] == "dao")["totale"] >= 20


def test_discover_and_claim(conn):
    p = entities.get_player(conn)
    names = [r["name"] for r in conn.execute("SELECT name FROM locations;")]
    state.set_json(conn, "world_codex_luoghi", names)
    v = album.view(conn, p)
    lu = next(x for x in v["pagine"] if x["key"] == "luoghi")
    assert lu["pct"] == 100 and lu["premi"] == [25, 50, 75, 100]
    before = sects.get_resource(conn, "pietre_spirituali", p.id)
    out = album.claim(conn, p)
    assert "Custode dell'Album" in out and sects.get_resource(conn, "pietre_spirituali", p.id) > before
    assert "Nessun premio" in album.claim(conn, p)
    assert "ALBUM" in album.command(conn, p, "")
