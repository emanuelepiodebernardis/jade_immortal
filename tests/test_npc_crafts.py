"""Aggiornamento 78: assorbire qualcuno dà anche l'esperienza del suo mestiere."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, npc_crafts, professions


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "nc.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=3, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(4))
    c.commit()
    yield c
    c.close()


def _crafter(conn, archetype="anziano"):
    for r in conn.execute("SELECT id FROM npcs WHERE kind='human' OR kind IS NULL;"):
        conn.execute("UPDATE npcs SET archetype=? WHERE id=?;", (archetype, r["id"]))
        if npc_crafts.of_npc(conn, r["id"]):
            return r["id"]
    raise AssertionError("nessun artigiano")


def test_crafts_are_stable_and_shown(conn):
    nid = _crafter(conn)
    a = npc_crafts.of_npc(conn, nid)
    assert a == npc_crafts.of_npc(conn, nid)
    assert all(k in professions.PROFESSIONS and lv >= 1 for k, lv in a)
    assert "Mestiere:" in npc_crafts.describe_npc(conn, nid)


def test_unknown_art_gives_fragments_then_learns(conn):
    nid = _crafter(conn)
    key, lv = npc_crafts.of_npc(conn, nid)[0]
    assert not professions.has(conn, key)
    out = []
    for _ in range(8):
        out += npc_crafts.on_absorb(conn, 1, nid, "human", 1.0, True)
        if professions.has(conn, key):
            break
    assert professions.has(conn, key), out
    assert any("conosci l'arte" in x for x in out)


def test_known_art_grows_but_never_past_the_victim(conn):
    nid = _crafter(conn, "patriarca")
    key, lv = npc_crafts.of_npc(conn, nid)[0]
    professions.add_xp(conn, 1, 0, key)
    for _ in range(30):
        npc_crafts.on_absorb(conn, 1, nid, "human", 1.0, True)
    assert professions.xp(conn, 1, key) == professions.xp_for_level(lv)
    assert "nulla da imparare" in npc_crafts.on_absorb(conn, 1, nid, "human", 1.0, True)[0]


def test_beasts_teach_taming(conn):
    out = npc_crafts.on_absorb(conn, 1, conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"],
                               "beast", 1.0, True)
    assert "Addomesticamento" in out[0]
