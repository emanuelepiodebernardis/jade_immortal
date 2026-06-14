"""Potenza Effettiva: profilo a 4 assi, classi, matchup di stile, zone tematiche."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, power, zones


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "power.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _npc(conn):
    return conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()["id"]


def test_profile_axes_present(conn):
    pr = power.power_profile(conn, "player", 1)
    assert set(pr) == {"qi", "corpo", "anima", "dao"}


def test_dao_warrior_classified_as_dao(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 90, 1000, 1)
    assert power.class_of(conn, "player", 1) == "dao"
    assert "Guerriero Dao" in power.classify(conn, "player", 1)[1]


def test_soul_master_classified_as_anima(conn):
    dao_gen._set_dao(conn, "player", 1, "anima", 90, 1000, 1)
    assert power.class_of(conn, "player", 1) == "anima"


def test_matchup_rock_paper_scissors(conn):
    assert power.matchup_bonus("dao", "qi") > 0      # Dao batte Qi
    assert power.matchup_bonus("qi", "dao") < 0      # e ne è battuto
    assert power.matchup_bonus("qi", "corpo") > 0
    assert power.matchup_bonus("corpo", "anima") > 0
    assert power.matchup_bonus("anima", "dao") > 0
    assert power.matchup_bonus("dao", "dao") == 0    # stesso stile: neutro


def test_rating_is_scalar_and_grows(conn):
    r0 = power.combat_rating(conn, "player", 1)
    dao_gen._set_dao(conn, "player", 1, "spada", 90, 500, 1)
    assert power.combat_rating(conn, "player", 1) > r0


def test_zone_themes_assigned(conn):
    rows = conn.execute("SELECT location_id, theme, rating FROM zone_themes;").fetchall()
    assert len(rows) >= 1
    for r in rows:
        assert r["theme"] in zones.THEMES
        assert r["rating"] > 0


def test_populate_zone_spawns_classed_inhabitants(conn):
    z = conn.execute("SELECT location_id, theme FROM zone_themes LIMIT 1;").fetchone()
    loc = z["location_id"]
    before = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive';", (loc,)).fetchone()["c"]
    n = zones.populate_zone(conn, random.Random(7), loc, 100, force=True)
    assert n >= 1
    after = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive';", (loc,)).fetchone()["c"]
    assert after > before


def test_themed_zone_has_dominant_class(conn):
    # popola una Valle delle Mille Lame (tema dao) e verifica la prevalenza di Guerrieri Dao
    # forziamo il tema su una location pulita
    loc = conn.execute("SELECT id FROM locations ORDER BY id DESC LIMIT 1;").fetchone()["id"]
    conn.execute("INSERT OR REPLACE INTO zone_themes (location_id, theme, rating, populated_tick) "
                 "VALUES (?, 'mille_lame', 600, -1);", (loc,))
    conn.commit()
    # popola molte volte e conta le classi
    for s in range(6):
        zones.populate_zone(conn, random.Random(s), loc, 100 + s, force=True)
    classes = [power.class_of(conn, "npc", r["id"])
               for r in conn.execute("SELECT id FROM npcs WHERE location_id=? AND kind='human' AND status='alive';", (loc,))]
    assert classes.count("dao") >= 1     # ci sono Guerrieri Dao nella Valle delle Mille Lame


def test_examine_shows_style(conn):
    from engine.systems import perception
    dao_gen._set_dao(conn, "player", 1, "anima", 90, 200, 1)   # per percepire bene
    npc = _npc(conn)
    lines = perception.describe(conn, 1, entities.get_npc(conn, npc))
    assert any("Stile:" in ln for ln in lines)
