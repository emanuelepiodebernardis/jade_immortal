"""Duello a turni: azioni, colpo pesante annunciato, fine con scelta, fuga."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, duel, encounters, npc_factory
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "du.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=14, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _foe(conn, tier=1, stage=1):
    nid = npc_factory.spawn(conn, random.Random(5), archetype="discepolo", location_id=_p(conn).location_id,
                            tier=tier, stage=stage)
    return nid, conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"].split()[0]


def test_duel_turns_until_decision(conn):
    nid, first = _foe(conn)
    out = loop.dispatch(conn, f"duello {first}", allow_nl=False)
    assert "Turno 1" in out
    labels = [c["label"] for c in encounters.pending(conn)["choices"]]
    assert labels[0] == "Colpisci" and any(l.startswith("Difendi") for l in labels)
    for _ in range(80):
        sc = encounters.pending(conn)
        if not sc or not duel.get(conn):
            break
        if sc["title"].endswith("è a terra"):
            out = loop.dispatch(conn, "2", allow_nl=False)          # lo risparmi
            assert entities.get_npc(conn, nid).status == "alive"
            break
        loop.dispatch(conn, "1", allow_nl=False)                    # colpisci
    assert duel.get(conn) is None or _p(conn).status != "alive"


def test_heavy_blow_is_announced_and_defend_parries(conn):
    nid, first = _foe(conn)
    duel.start(conn, _p(conn), first)
    d = duel.get(conn)
    d["charge_e"] = True
    duel._save(conn, d)
    hp0 = d["hp_p"]
    duel.act(conn, _p(conn), "difendi")
    d2 = duel.get(conn)
    if d2:
        assert hp0 - d2["hp_p"] < d["pmax"] * 0.5


def test_flee_and_kill(conn):
    nid, first = _foe(conn)
    duel.start(conn, _p(conn), first)
    d = duel.get(conn)
    d["hp_e"] = 0
    duel._save(conn, d)
    out = duel.finish(conn, _p(conn), True)
    assert entities.get_npc(conn, nid).status == "dead" and "★" in out
    nid2, first2 = _foe(conn)
    duel.start(conn, _p(conn), first2)
    for _ in range(30):
        r = duel.act(conn, _p(conn), "fuggi")
        if "dilegui" in r or not duel.get(conn):
            break
    assert duel.get(conn) is None or _p(conn).status != "alive"
