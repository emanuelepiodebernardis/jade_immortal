"""Loop di competizione della setta: compagni, sfida programmata, tornei, promozione."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import sects, sect_life, training, character
from engine.simulation import world_tick, cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sl.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join_first_sect(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    return sect


def test_join_creates_classmates(conn):
    _join_first_sect(conn)
    mates = sect_life.classmates(conn)
    assert len(mates) == sect_life.CLASS_SIZE


def test_challenge_is_scheduled_ten_days_out(conn):
    _join_first_sect(conn)
    nxt = sect_life.next_event(conn, 0)
    assert nxt["kind"] == "ranking_challenge"
    assert nxt["fire_tick"] == sect_life.CHALLENGE_DELAY


def test_agenda_line_counts_down(conn):
    _join_first_sect(conn)
    line = sect_life.agenda_line(conn, 0)
    assert "Sfida di Classifica" in line and "giorni" in line


def test_tournament_fires_and_ranks_player(conn):
    _join_first_sect(conn)
    player = entities.get_player(conn)
    obs = []
    # fai scattare l'evento al suo tick
    sect_life.resolve_sect_events(conn, sect_life.CHALLENGE_DELAY, random.Random(2),
                                  player, player.location_id, obs)
    m = sects.get_membership(conn)
    assert m["class_rank"] is not None
    assert 1 <= m["class_rank"] <= sect_life.CLASS_SIZE + 1
    # evento tracciato + osservazione prodotta
    assert conn.execute("SELECT COUNT(*) c FROM events WHERE event_type='sect_tournament';").fetchone()["c"] == 1
    assert any("Classifica" in o for o in obs)


def test_tournament_grants_stones(conn):
    _join_first_sect(conn)
    before = sects.get_resource(conn, "pietre_spirituali")
    player = entities.get_player(conn)
    sect_life.resolve_sect_events(conn, sect_life.CHALLENGE_DELAY, random.Random(2),
                                  player, player.location_id, [])
    assert sects.get_resource(conn, "pietre_spirituali") > before


def test_monthly_tournament_rescheduled_after_firing(conn):
    _join_first_sect(conn)
    player = entities.get_player(conn)
    sect_life.resolve_sect_events(conn, sect_life.CHALLENGE_DELAY, random.Random(2),
                                  player, player.location_id, [])
    nxt = sect_life.next_event(conn, sect_life.CHALLENGE_DELAY)
    assert nxt["kind"] == "monthly_tournament"
    assert nxt["fire_tick"] == sect_life.CHALLENGE_DELAY + sect_life.MONTH_TICKS


def test_promotion_creates_new_class(conn):
    _join_first_sect(conn)
    old_mates = {m["id"] for m in sect_life.classmates(conn)}
    # simula breakthrough di regno e promozione
    conn.execute("UPDATE cultivation_records SET stage=10, progress=2.0, dao_understanding=90 "
                 "WHERE character_type='player' AND character_id=1;")
    for seed in range(60):
        r = cultivation.attempt_breakthrough(conn, "player", 1, 5, random.Random(seed))
        if r["status"] == "success":
            break
    sect_life.promote_class(conn, 5, random.Random(3))
    new_mates = {m["id"] for m in sect_life.classmates(conn)}
    m = sects.get_membership(conn)
    assert m["class_tier"] == cultivation.realm_tier(conn, "player", 1)
    assert new_mates and new_mates != old_mates   # nuova classe, nuovi rivali
