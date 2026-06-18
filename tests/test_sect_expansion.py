"""Livelli di setta infiniti, promozione di categoria, zone per affinità, caccia ai mostri,
e razzie alle sette."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen
from engine.systems import character, sects, sect_life, reputation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "exp.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    return sects.get_membership(conn, 1)["faction_id"]


def _strong(conn):
    r8 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=8 WHERE character_type='player' AND character_id=1;", (r8,))
    conn.execute("UPDATE character_profiles SET grow_strength=8000, grow_vitality=8000, grow_resistance=8000 WHERE character_type='player' AND character_id=1;")
    conn.commit()


# ---------- #1 livelli di setta infiniti ----------

def test_sect_tier_names_infinite():
    assert sects.tier_name(6) == "Setta Celeste"
    assert sects.tier_name(7) == "Setta Trascendente"
    assert sects.tier_name(15) == "Setta Trascendente II"   # ciclo con numerale


def test_invitations_not_capped(conn):
    fac = _join(conn)
    conn.execute("UPDATE factions SET tier=6 WHERE id=?;", (fac,))    # già all'apice "tabellato"
    invs = sects.generate_invitations(conn, 0, random.Random(2), 1)
    assert invs                                                       # niente più tetto
    assert any(i["tier"] > 6 for i in invs)


# ---------- #5 promozione di categoria ----------

def test_promote_rank_climbs_ladder(conn):
    _join(conn)
    start = sects.get_membership(conn, 1)["rank"]
    res = sects.promote_rank(conn, 1)
    assert res["promoted"]
    assert sects.RANK_LADDER.index(res["rank"]) > sects.RANK_LADDER.index(start)


def test_tournament_win_promotes_category(conn):
    fac = _join(conn)
    # nessun compagno → sei 1° e vinci
    conn.execute("DELETE FROM sect_cohort WHERE player_id=1;")
    before = sects.get_membership(conn, 1)["rank"]
    from engine.systems import reports
    sect_life._run_tournament(conn, 100, random.Random(1), 1, fac, "monthly_tournament", None, [])
    after = sects.get_membership(conn, 1)["rank"]
    rep = "\n".join(reports.drain(conn, 1))
    assert after != before and "PROMOZIONE" in rep


# ---------- #4 zone per affinità ----------

def test_zone_spawns_carry_zone_element(conn):
    from engine.systems import zones
    z = conn.execute("SELECT location_id FROM zone_themes LIMIT 1;").fetchone()
    if z is None:
        pytest.skip("nessuna zona generata")
    loc = z["location_id"]
    elem = zones._zone_element(conn, loc)
    # svuota e ripopola la zona forzatamente
    conn.execute("UPDATE npcs SET location_id=location_id WHERE 1=0;")
    n = zones.populate_zone(conn, random.Random(5), loc, 10, force=True)
    assert n > 0
    with_elem = conn.execute(
        "SELECT COUNT(DISTINCT cd.character_id) c FROM character_daos cd "
        "JOIN npcs n ON n.id=cd.character_id "
        "WHERE n.location_id=? AND cd.character_type='npc' AND cd.dao_key=?;",
        (loc, elem)).fetchone()["c"]
    assert with_elem >= 1            # la zona porta il proprio elemento


# ---------- #2 caccia ai mostri ----------

def test_creature_kill_cleanses_negative_status(conn):
    loc = entities.get_player(conn).location_id
    reputation.adjust(conn, 1, infamy=50, suspicion=50)
    bid = creature_gen._spawn_one(conn, random.Random(1), "beast", loc, 2, 2)
    before = reputation.get(conn, 1)
    npc = entities.get_npc(conn, bid)
    loop._kill_reputation(conn, entities.get_player(conn), npc, was_outlaw=False)
    after = reputation.get(conn, 1)
    assert after["infamy"] < before["infamy"]
    assert after["suspicion"] < before["suspicion"]
    assert after["fame"] > before["fame"]


# ---------- #3 razzie alle sette ----------

def test_raid_sacks_rival_sect(conn):
    _strong(conn)
    # una setta rivale (diversa dalla mia, qui non sono iscritto)
    rival = sects.joinable_sects(conn)[1]
    rhome = rival["home_location_id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (rhome,))
    # garantisci un paio di membri DEBOLI presenti alla sede
    r1 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=1;").fetchone()["id"]
    weak = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 2;").fetchall()
    for w in weak:
        conn.execute("UPDATE npcs SET faction_id=?, location_id=?, realm_id=? WHERE id=?;",
                     (rival["id"], rhome, r1, w["id"]))
        conn.execute("UPDATE cultivation_records SET realm_id=?, stage=1 WHERE character_type='npc' AND character_id=?;", (r1, w["id"]))
    conn.commit()
    before = sects.get_resource(conn, "pietre_spirituali", 1)
    out = loop.cmd_raid(conn, entities.get_player(conn), "")
    assert "RAZZIA" in out
    # con un giocatore schiacciante, la sede cade e saccheggi
    assert "SACCHEGGIO" in out
    assert sects.get_resource(conn, "pietre_spirituali", 1) > before
