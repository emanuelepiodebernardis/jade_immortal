"""Invasioni guidate dal giocatore (rango alto → conquista) e ritorsioni da espansione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, sects, sect_invasion, world_events as we, items


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "lead.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=4, static_npc_count=30))
    character.apply_origin(c, "genio", random.Random(1))
    sect = sects.joinable_sects(c)[0]
    c.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(c, tick=0)
    r8 = c.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=8 WHERE character_type='player' AND character_id=1;", (r8,))
    c.execute("UPDATE character_profiles SET grow_strength=9000, grow_vitality=9000, grow_resistance=9000 WHERE character_type='player' AND character_id=1;")
    c.commit()
    yield c
    c.close()


def _go_to_rival(conn):
    myfac = sects.get_membership(conn, 1)["faction_id"]
    rival = conn.execute(
        "SELECT id, home_location_id, name FROM factions WHERE id<>? AND home_location_id IS NOT NULL "
        "AND status='active' LIMIT 1;", (myfac,)).fetchone()
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (rival["home_location_id"],))
    # alcuni difensori presenti
    defs_ = [r["id"] for r in conn.execute(
        "SELECT id FROM npcs WHERE faction_id=? AND kind='human' AND status='alive' LIMIT 3;",
        (rival["id"],)).fetchall()]
    for d in defs_:
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (rival["home_location_id"], d))
    conn.commit()
    return rival


def test_low_rank_cannot_lead(conn):
    conn.execute("UPDATE sect_memberships SET rank='Discepolo Esterno' WHERE player_id=1;")
    conn.commit()
    ok, why = sect_invasion.can_lead(conn, 1)
    assert not ok and "rango" in why.lower()


def test_top_rank_can_conquer(conn):
    conn.execute("UPDATE sect_memberships SET rank='Giovane Patriarca', rank_level=8 WHERE player_id=1;")
    rival = _go_to_rival(conn)
    myfac = sects.get_membership(conn, 1)["faction_id"]
    infl0 = conn.execute("SELECT influence FROM factions WHERE id=?;", (rival["id"],)).fetchone()["influence"]
    res = sect_invasion.lead_invasion(conn, 10, random.Random(2), entities.get_player(conn))
    assert res["status"] == "conquered"
    # la sede è passata alla mia setta
    owner = conn.execute("SELECT owner_faction_id FROM locations WHERE id=?;",
                         (rival["home_location_id"],)).fetchone()["owner_faction_id"]
    assert owner == myfac
    # influenza rivale ridotta, conquiste +1, bottino nello zaino
    infl1 = conn.execute("SELECT influence FROM factions WHERE id=?;", (rival["id"],)).fetchone()["influence"]
    assert infl1 < infl0
    assert sect_invasion.conquests(conn) == 1
    assert any("Tesoro" in r["name"] for r in items.player_inventory(conn, 1))


def test_expansion_triggers_retaliation_targeting(conn):
    myfac = sects.get_membership(conn, 1)["faction_id"]
    # simulo conquiste e territorio controllato
    conn.execute("INSERT INTO game_state (key, value) VALUES (?, '5') "
                 "ON CONFLICT(key) DO UPDATE SET value='5';", (sect_invasion.CONQUEST_KEY,))
    # rendo "mia" una location popolata
    pop = we._populated_locations(conn)
    assert pop
    mineloc = pop[0]
    conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (myfac, mineloc))
    conn.commit()
    # con 5 conquiste, su più tentativi almeno un'invasione bersaglia il mio territorio
    targeted_mine = 0
    for s in range(20):
        conn.execute("UPDATE world_events SET status='lost' WHERE status='active';")  # libera lo slot
        we.maybe_spawn(conn, s, random.Random(s * 13 + 1), entities.get_player(conn), [])
        ev = we.active_event(conn)
        if ev and ev["location_id"] == mineloc:
            targeted_mine += 1
    assert targeted_mine >= 1
