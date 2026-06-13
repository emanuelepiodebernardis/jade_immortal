"""Sette + economia dell'allenamento: test d'ingresso, rango/risorse, rendimento decrescente."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import sects, training, character
from engine.simulation import cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sect.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _move_player_to_a_sect(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    return sect


def test_joinable_sects_exist(conn):
    assert len(sects.joinable_sects(conn)) >= 1


def test_cannot_join_outside_hq(conn):
    # sposta il player lontano da ogni sede
    loc = conn.execute(
        "SELECT id FROM locations WHERE id NOT IN (SELECT home_location_id FROM factions) LIMIT 1;"
    ).fetchone()
    if loc:
        conn.execute("UPDATE players SET location_id=? WHERE id=1;", (loc["id"],))
        assert sects.join_sect(conn, 0)["status"] == "no_sect_here"


def test_join_runs_entrance_test_and_grants_resources(conn):
    sect = _move_player_to_a_sect(conn)
    res = sects.join_sect(conn, tick=10)
    assert res["status"] == "joined"
    assert res["sect"] == sect["name"]
    assert res["stones"] > 0
    # risorse e affiliazione registrate
    assert sects.get_resource(conn, "pietre_spirituali") == res["stones"]
    assert conn.execute("SELECT faction_id FROM players WHERE id=1;").fetchone()["faction_id"] == sect["id"]
    m = sects.get_membership(conn)
    assert m["rank"] == res["rank"]


def test_talent_test_reflects_affinities(conn):
    # un genio (alta affinità coltivazione) ottiene un rango migliore di radici torbide
    _move_player_to_a_sect(conn)
    res = sects.join_sect(conn, tick=10)
    assert res["rank_level"] >= 1   # almeno discepolo esterno, non servitore


def test_already_member_blocks_second_join(conn):
    _move_player_to_a_sect(conn)
    sects.join_sect(conn, tick=10)
    assert sects.join_sect(conn, tick=11)["status"] == "already_member"


def test_join_logs_event(conn):
    _move_player_to_a_sect(conn)
    sects.join_sect(conn, tick=10)
    n = conn.execute("SELECT COUNT(*) c FROM events WHERE event_type='sect_join';").fetchone()["c"]
    assert n == 1


def test_training_diminishing_returns(conn):
    # le sessioni successive della stessa giornata rendono meno
    y1 = training.session_yield(1)
    y3 = training.session_yield(3)
    y6 = training.session_yield(6)
    assert y1 > y3 > y6


def test_sessions_reset_next_day(conn):
    t_day0 = 0
    t_day1 = training.DAY_TICKS
    training.record_session(conn, t_day0)
    training.record_session(conn, t_day0)
    assert training.sessions_today(conn, t_day0) == 2
    assert training.sessions_today(conn, t_day1) == 0   # nuovo giorno


def test_cultivation_yields_less_after_many_sessions(conn):
    # prima sessione vs sesta: progresso minore per stanchezza
    conn.execute("UPDATE cultivation_records SET progress=0 WHERE character_type='player' AND character_id=1;")
    r1 = cultivation.cultivate(conn, "player", 1, 0, random.Random(5), multiplier=training.session_yield(1))
    conn.execute("UPDATE cultivation_records SET progress=0 WHERE character_type='player' AND character_id=1;")
    r6 = cultivation.cultivate(conn, "player", 1, 0, random.Random(5), multiplier=training.session_yield(6))
    assert r1["progress"] > r6["progress"]


def test_sect_hq_bonus_applies_when_member(conn):
    sect = _move_player_to_a_sect(conn)
    sects.join_sect(conn, tick=10)
    bonus = training.location_bonus(conn, 1, sect["home_location_id"])
    assert bonus > 0
    # lontano dalla sede: nessun bonus
    other = conn.execute(
        "SELECT id FROM locations WHERE id<>? LIMIT 1;", (sect["home_location_id"],)
    ).fetchone()["id"]
    assert training.location_bonus(conn, 1, other) == 0.0
