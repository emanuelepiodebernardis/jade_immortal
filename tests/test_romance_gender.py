"""Il protagonista è un uomo: fidanzata e compagna del Dao sono donne."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, master_plot, npc_factory, oaths, relations, family


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "rg.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=9, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def test_fiancee_is_a_woman(conn):
    sc = master_plot._b_engagement(conn, _p(conn))
    fid = master_plot.get(conn)["fiancee"]
    assert npc_factory.is_female(conn, fid)
    assert "promessa sposa" in sc["text"] and "discepola" in sc["text"]


def test_dao_partner_must_be_a_woman(conn):
    r = random.Random(3)
    loc = _p(conn).location_id
    him = npc_factory.spawn(conn, r, archetype="discepolo", location_id=loc, tier=1, gender="m")
    her = npc_factory.spawn(conn, r, archetype="discepolo", location_id=loc, tier=1, gender="f")
    for nid in (him, her):
        relations.adjust(conn, nid, 95, 0)
    t = tick.get_tick(conn)
    out = oaths.propose(conn, t, _p(conn), entities.get_npc(conn, him))
    assert "sarà una donna" in out
    out = oaths.propose(conn, t, _p(conn), entities.get_npc(conn, her))
    assert "COMPAGNA DEL DAO" in out


def test_family_women_and_old_worlds(conn):
    family.create(conn, random.Random(4), _p(conn))
    rows = conn.execute("SELECT b.reason, n.id FROM bonds b JOIN npcs n ON n.id=b.npc_id "
                        "WHERE b.kind='family';").fetchall()
    for r in rows:
        assert npc_factory.is_female(conn, r["id"]) == (r["reason"] in ("madre", "sorella minore"))
    # nei mondi vecchi (genere NULL) il genere è dedotto in modo stabile
    nid = conn.execute("SELECT id FROM npcs WHERE kind='human' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET gender=NULL WHERE id=?;", (nid,))
    assert npc_factory.gender_of(conn, nid) == npc_factory.gender_of(conn, nid)
