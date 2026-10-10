"""La tribolazione del Cielo parte DA SOLA col tempo; la sfida di rango promuove se vinci."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, sects, dao_powers, reports
from engine.simulation import world_tick
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "tc.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=3, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


# ---------- tribolazione del Cielo automatica ----------

def test_high_defiance_triggers_tribulation_over_time(conn):
    for k, comp in [("spazio", 400), ("tempo", 400), ("destino", 339)]:
        dao_gen._set_dao(conn, "player", 1, k, 60, comp, 1)
    assert dao_powers.heaven_defiance(conn, 1) > 800
    assert dao_powers.tribulation_due(conn, 1) > 0
    world_tick.advance(conn, 12, rng=random.Random(5))    # basta che passi il tempo
    reps = reports.drain(conn, 1)
    assert any("Cielo" in r for r in reps)
    # registrata: non si ri-scatena subito
    assert dao_powers.tribulation_due(conn, 1) == 0


# ---------- sfida di rango ----------

def _join(conn, strong):
    conn.execute("DELETE FROM sect_memberships;")
    conn.execute("DELETE FROM game_state WHERE key='challenge_day';")
    val = 9000 if strong else 0
    conn.execute("UPDATE character_profiles SET grow_strength=?, grow_vitality=?, grow_resistance=? "
                 "WHERE character_type='player' AND character_id=1;", (val, val, val))
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    conn.commit()


def test_strong_player_wins_and_ranks_up(conn):
    _join(conn, strong=True)
    before = sects.get_membership(conn, 1)["rank"]
    out = loop.cmd_challenge(conn, entities.get_player(conn), "")
    after = sects.get_membership(conn, 1)["rank"]
    assert "SCONFITTO" in out and after != before


def test_weak_player_loses_rank_unchanged(conn):
    _join(conn, strong=False)
    before = sects.get_membership(conn, 1)["rank"]
    out = loop.cmd_challenge(conn, entities.get_player(conn), "")
    assert "respinto" in out.lower()
    assert sects.get_membership(conn, 1)["rank"] == before


def test_challenge_daily_cooldown(conn):
    _join(conn, strong=True)
    loop.cmd_challenge(conn, entities.get_player(conn), "")
    again = loop.cmd_challenge(conn, entities.get_player(conn), "")
    assert "oggi" in again.lower()


def test_no_sect_cannot_challenge(conn):
    conn.execute("DELETE FROM sect_memberships;")
    conn.commit()
    out = loop.cmd_challenge(conn, entities.get_player(conn), "")
    assert "setta" in out.lower()
