"""Il bilancio della potenza: tetti morbidi, amplificatore dei Dao limitato, schermata delle fonti."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, power_budget as pb, calibration, menus, combat_states
from engine.simulation import combat


def test_soft_cap_is_monotone_and_bounded():
    vals = [pb.soft(x, 3.0) for x in (1.0, 1.2, 2.0, 5.0, 25.0, 1000.0)]
    assert vals == sorted(vals) and vals[-1] < 3.0 and abs(vals[1] - 1.2) < 0.03
    assert pb.soft(0.5, 3.0) == 0.5


def test_dao_amp_grows_forever_but_below_the_ceiling():
    v = combat.dao_vessel(5)
    amps = [pb.dao_amp(v * r, v) for r in (0, 1, 7, 1000, 10 ** 9)]
    assert amps[0] == 1.0 and amps == sorted(amps) and amps[-1] < calibration.DAO_AMP_MAX


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "pb.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=3, factions=3, static_npc_count=15))
    character.apply_origin(c, "genio", random.Random(2))
    c.commit()
    yield c
    c.close()


def test_fight_gifts_are_capped_and_recorded(conn):
    p = entities.get_player(conn)
    nid = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    from engine.systems import bloodlines
    bloodlines.grant_heritage(conn, "Drago delle Nubi", ["fulmine"], 50000)      # un sangue esagerato
    pa, pd = combat.combat_power(conn, "player", 1), combat.combat_power(conn, "npc", nid)
    fx = combat_states.FightCtx(conn, 1, nid, "Tu", "x", pa["vitality"], pd["vitality"], pa["attack"], pd["attack"])
    assert fx.p.atk_mult <= calibration.GIFTS_ATK_CAP
    assert fx.p.prof.get("extra_strikes", 0) <= calibration.MAX_EXTRA_STRIKES
    m = menus.build(conn, p, "forza")
    titles = [s["title"] for s in m["sections"]]
    assert "Da dove viene la tua forza" in titles and any("ultimo scontro" in t for t in titles)


def test_mortal_tenacity_grows_with_days_of_toil(tmp_path, monkeypatch):
    p = tmp_path / "m.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=4, factions=3, static_npc_count=10))
    character.apply_origin(c, "mortale", random.Random(1))
    from engine.systems import tenacity, cult_mods
    assert tenacity.active(c)
    m0 = tenacity.cultivation_mult(c)[0]
    for d in range(30):
        tenacity.mark(c, d * 120)
        tenacity.mark(c, d * 120 + 5)                   # un giorno conta una volta sola
    assert tenacity.days(c) == 30
    assert abs(tenacity.cultivation_mult(c)[0] - (m0 + 0.36)) < 1e-6
    labels = cult_mods.cultivation_mult(c, 1, entities.get_player(c).location_id)[1]
    assert any("volontà del mortale" in x for x in labels)
