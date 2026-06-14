"""Gilde: zone di caccia, merito da uccisioni, tecniche segrete e loro effetto."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen
from engine.systems import sects, sect_life, character, guild
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "guild.db"
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


def test_every_sect_has_a_hunt_zone(conn):
    for f in conn.execute("SELECT id, hunt_zone_id FROM factions WHERE status='active';"):
        assert f["hunt_zone_id"] is not None


def test_hunt_zone_has_creatures(conn):
    f = conn.execute("SELECT hunt_zone_id FROM factions WHERE status='active' LIMIT 1;").fetchone()
    n = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind<>'human' AND status='alive';",
                     (f["hunt_zone_id"],)).fetchone()["c"]
    assert n >= 1


def test_killing_creature_grants_merit(conn):
    _join_first_sect(conn)
    before = guild.get_merit(conn)
    # piazza una creatura nella location del player e "uccidila" (registrazione merito)
    ploc = entities.get_player(conn).location_id
    beast = conn.execute("SELECT id FROM npcs WHERE kind='beast' AND status='alive' LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=?, status='dead' WHERE id=?;", (ploc, beast["id"]))
    res = guild.on_creature_kill(conn, beast["id"], 1)
    assert res["gained"] > 0
    assert guild.get_merit(conn) == before + res["gained"]


def test_killing_human_grants_no_merit(conn):
    _join_first_sect(conn)
    human = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()
    assert guild.merit_for_kill(conn, human["id"]) == 0


def test_hunt_zone_bonus_merit(conn):
    _join_first_sect(conn)
    f = conn.execute("SELECT hunt_zone_id FROM factions WHERE id=(SELECT faction_id FROM sect_memberships WHERE player_id=1);").fetchone()
    beast = conn.execute("SELECT id, realm_id FROM npcs WHERE kind='beast' AND status='alive' LIMIT 1;").fetchone()
    normal = guild.merit_for_kill(conn, beast["id"], in_hunt_zone=False)
    inzone = guild.merit_for_kill(conn, beast["id"], in_hunt_zone=True)
    assert inzone > normal


def test_learn_technique_spends_merit_and_boosts_power(conn):
    _join_first_sect(conn)
    m = sects.get_membership(conn)
    tech = guild.sect_techniques(conn, m["faction_id"])[0]
    guild.add_merit(conn, tech["cost"], 1)        # merito sufficiente
    base = combat.combat_power(conn, "player", 1)["attack"]
    res = guild.learn(conn, 0, 1, 1)
    assert res["status"] == "learned"
    assert guild.get_merit(conn) == 0             # speso
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base                          # la tecnica aumenta la potenza


def test_cannot_learn_without_merit(conn):
    _join_first_sect(conn)
    res = guild.learn(conn, 0, 3, 1)               # la più costosa, merito 0
    assert res["status"] == "poor"


def test_higher_tier_sect_has_stronger_techniques(conn):
    _join_first_sect(conn)
    fid = sects._create_greater_sect(conn, random.Random(5), "Trono Celeste", tier=6, element="fulmine", tick=0)
    low = guild.sect_techniques(conn, sects.get_membership(conn)["faction_id"])[0]["magnitude"]
    high = guild.sect_techniques(conn, fid)[0]["magnitude"]
    assert high > low                              # tecniche più forti nelle sette alte


def test_techniques_persist_through_ascension(conn):
    _join_first_sect(conn)
    m = sects.get_membership(conn)
    tech = guild.sect_techniques(conn, m["faction_id"])[0]
    guild.add_merit(conn, tech["cost"], 1)
    guild.learn(conn, 0, 1, 1)
    learned_before = len(guild.learned(conn, 1))
    # ascendi a una nuova setta
    conn.execute("INSERT INTO sect_invitations (player_id, slot, name, tier, element, hint, created_tick, resolved) "
                 "VALUES (1, 1, 'Setta Superiore', 4, 'spada', 'x', 0, 0);")
    sects.accept_invitation(conn, tick=5, rng=random.Random(2), slot=1)
    # le tecniche apprese restano; il merito riparte da zero
    assert len(guild.learned(conn, 1)) == learned_before
    assert guild.get_merit(conn) == 0
