"""Chi ti insegue cresce con te (Aggiornamento 44)."""
import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character
from engine.core import entities
from engine.systems import pursuers, hunters, npc_factory, feuds


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "pur.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_hunter_is_never_a_wall(conn):
    p = entities.get_player(conn)
    rng = random.Random(3)
    nid, _msg = hunters._spawn_hunter(conn, 0, rng, p, 3)
    r = pursuers.ratio(conn, p.id, nid)
    lo, hi = pursuers.BANDS["cacciatore"]
    assert lo * 0.95 <= r <= hi * 1.05


def test_pursuer_keeps_pace_and_seniors_are_not_weakened(conn):
    p = entities.get_player(conn)
    rng = random.Random(5)
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=p.location_id, tier=9, stage=9)
    assert pursuers.ratio(conn, p.id, nid) > 3          # un muro...
    pursuers.fit(conn, p.id, nid, "nemesi")
    assert pursuers.ratio(conn, p.id, nid) <= pursuers.BANDS["nemesi"][1] * 1.05   # ...non più
    # gli anziani della faida non vengono indeboliti
    old = npc_factory.spawn(conn, rng, archetype="anziano", location_id=p.location_id, tier=9, stage=9)
    before = pursuers.ratio(conn, p.id, old)
    pursuers.fit(conn, p.id, old, "anziano")
    assert abs(pursuers.ratio(conn, p.id, old) - before) < 1e-6
