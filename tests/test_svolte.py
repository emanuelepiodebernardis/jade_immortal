"""Svolte: volo, incarnazioni del Dao, il tuo Dao, capolavori, pannello e annunci."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, svolte, state, qol, professions
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _tier(conn, t):
    rid = cultivation.ensure_realm(conn, t)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


def test_fly_needs_realm_and_known_place(conn):
    home = _p(conn).location_id
    name = conn.execute("SELECT name FROM locations WHERE id=?;", (home,)).fetchone()["name"]
    qol.note(conn, "luoghi", name)
    assert "regno" in svolte.fly(conn, _p(conn), name)
    _tier(conn, 2)
    other = conn.execute("SELECT to_location_id FROM location_connections WHERE from_location_id=? LIMIT 1;",
                         (home,)).fetchone()["to_location_id"]
    entities.move_player(conn, 1, other)
    out = loop.dispatch(conn, f"vola {name}", allow_nl=False)
    assert _p(conn).location_id == home and "cielo" in out
    assert "Non conosci" in svolte.fly(conn, _p(conn), "zzzz")


def test_incarnation_is_endless():
    assert svolte.incarnation(1999) == 0
    assert svolte.incarnation(2000) == 1 and svolte.incarnation(4000) == 2 and svolte.incarnation(64000) == 6


def test_create_own_dao(conn):
    assert "servono 3" in svolte.create_dao(conn, _p(conn), "Giada")
    for k in ("spada", "fuoco", "fulmine"):
        dao_gen._set_dao(conn, "player", 1, k, 60, 1200, 1)
    out = loop.dispatch(conn, "crea_dao Giada Eterna", allow_nl=False)
    assert "Dao di Giada Eterna" in out
    assert len(svolte.own_daos(conn, 1)) == 1 and svolte.own_dao_slots(conn, 1) == 0


def test_masterpiece_and_cultivation_bonus(conn):
    loop.dispatch(conn, "profession forgia", allow_nl=False)
    assert "livello 10" in svolte.masterpiece(conn, _p(conn), "Lama")
    state.set(conn, "profession_xp", str(professions.xp_for_level(10)))
    out = svolte.masterpiece(conn, _p(conn), "Lama dell'Alba")
    assert "compiuta" in out and svolte.cultivation_mult(conn)[0] == pytest.approx(1.05)


def test_panel_and_announcements(conn):
    assert "SVOLTE" in loop.dispatch(conn, "svolte", allow_nl=False)
    _tier(conn, 2)
    msgs = svolte.check_new(conn, _p(conn))
    assert any("Volo" in m for m in msgs)
    assert not any("Volo" in m for m in svolte.check_new(conn, _p(conn)))     # una volta sola
