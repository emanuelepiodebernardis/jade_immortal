"""Fix dal playtest: loot dopo attack all, attack all su tutti, qi+dao vari da assorbimento,
formula di potenza dei Dao, rigenerazione zone, tribolazione da assorbimento, comandi viaggio."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen, dao_gen
from engine.systems import character, loot, absorption, dao_training, zones, moves
from engine.simulation import combat
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "pf.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=25))
    character.apply_origin(c, "divoratore", random.Random(1))
    r8 = c.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=8 WHERE character_type='player' AND character_id=1;", (r8,))
    c.execute("UPDATE character_profiles SET grow_strength=6000, grow_vitality=6000, grow_resistance=6000 WHERE character_type='player' AND character_id=1;")
    c.commit()
    yield c
    c.close()


# ---------- bug del loot dopo attack all ----------

def test_loot_lands_at_player_location(conn):
    loc = entities.get_player(conn).location_id
    for i in range(8):
        creature_gen._spawn_one(conn, random.Random(100 + i), "beast", loc, 5, 5)
    conn.commit()
    loop._attack_all(conn, entities.get_player(conn))
    # tutto il bottino e i resti restano DOVE SONO (loc del giocatore)
    elsewhere = conn.execute(
        "SELECT COUNT(*) c FROM inventories WHERE owner_type='ground' AND owner_id<>?;",
        (loc,)).fetchone()["c"]
    assert elsewhere == 0
    assert len(loot.drops_in_location(conn, loc)) >= 1


# ---------- attack all colpisce tutti ----------

def test_attack_all_hits_humans_too(conn):
    loc = entities.get_player(conn).location_id
    # porta qualche umano sul posto
    humans = [r["id"] for r in conn.execute(
        "SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 3;").fetchall()]
    for h in humans:
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (loc, h))
    conn.commit()
    before = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='human' AND status='alive';", (loc,)).fetchone()["c"]
    loop._attack_all(conn, entities.get_player(conn))
    after = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='human' AND status='alive';", (loc,)).fetchone()["c"]
    assert after < before


# ---------- assorbimento: qi + più Dao ----------

def test_absorb_grants_qi_and_multiple_daos(conn):
    tid = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()["id"]
    # il bersaglio ha più Dao e del qi
    for k, comp in [("anima", 40), ("destino", 25), ("fuoco", 15)]:
        dao_gen._set_dao(conn, "npc", tid, k, 60, comp, 1)
    conn.execute("UPDATE cultivation_records SET qi_level=80 WHERE character_type='npc' AND character_id=?;", (tid,))
    loc = entities.get_player(conn).location_id
    conn.execute("UPDATE npcs SET status='dead', location_id=?, death_tick=0 WHERE id=?;", (loc, tid))
    conn.commit()
    qi0 = conn.execute("SELECT qi_level FROM cultivation_records WHERE character_type='player' AND character_id=1;").fetchone()["qi_level"]
    res = absorption.absorb(conn, 1, random.Random(2), tid, 1)
    qi1 = conn.execute("SELECT qi_level FROM cultivation_records WHERE character_type='player' AND character_id=1;").fetchone()["qi_level"]
    assert qi1 > qi0                                   # il qi del coltivatore ti rafforza
    got = {r["dao_key"] for r in conn.execute(
        "SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=1 AND comprehension>0;")}
    assert len({"anima", "destino", "fuoco"} & got) >= 2   # più Dao, non solo uno


# ---------- formula di potenza dei Dao ----------

def test_dao_power_formula_matches_spec(conn):
    def setp(levels):
        conn.execute("DELETE FROM character_daos WHERE character_type='player' AND character_id=1;")
        for i, l in enumerate(levels):
            dao_gen._set_dao(conn, "player", 1, ["spada", "anima", "fuoco"][i], 60, l, 1)
        conn.commit()
        return dao_training.dao_power(conn, "player", 1)
    assert round(setp([10, 10])) == 100
    assert round(setp([10, 10, 10])) == 150
    p1, p2, p3 = setp([100]), setp([100, 100]), setp([100, 100, 100])
    assert 950 <= p1 <= 1050 and 2900 <= p2 <= 3100 and 5500 <= p3 <= 6100


def test_more_daos_means_more_attack(conn):
    conn.execute("DELETE FROM character_daos WHERE character_type='player' AND character_id=1;")
    dao_gen._set_dao(conn, "player", 1, "spada", 60, 50, 1)
    conn.commit()
    a1 = combat.combat_power(conn, "player", 1)["attack"]
    dao_gen._set_dao(conn, "player", 1, "anima", 60, 50, 1)
    conn.commit()
    a2 = combat.combat_power(conn, "player", 1)["attack"]
    assert a2 > a1                                     # 2 Dao > 1 Dao


# ---------- rigenerazione zone di caccia ----------

def test_hunting_zone_respawns_after_cooldown(conn):
    z = conn.execute("SELECT location_id FROM zone_themes LIMIT 1;").fetchone()
    loc = z["location_id"]
    rng = random.Random(1)
    zones.populate_zone(conn, rng, loc, tick=0, force=True)
    # svuota la zona
    conn.execute("UPDATE npcs SET status='dead' WHERE location_id=? AND kind<>'human';", (loc,))
    conn.commit()
    # subito: niente respawn (cooldown non passato)
    zones.maybe_respawn(conn, rng, loc, tick=1)
    none_yet = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human';", (loc,)).fetchone()["c"]
    # dopo il cooldown: si ripopola
    zones.maybe_respawn(conn, rng, loc, tick=zones.ZONE_RESPAWN + 5)
    after = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human';", (loc,)).fetchone()["c"]
    assert after > none_yet


# ---------- tribolazione da assorbimento + colpo speciale ----------

def test_absorption_triggers_tribulation_and_unlocks_strike(conn):
    dao_gen._set_dao(conn, "player", 1, "fulmine", 60, 400, 1)
    loc = entities.get_player(conn).location_id
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 13;").fetchall()]
    for i in ids:
        conn.execute("UPDATE npcs SET status='dead', location_id=?, death_tick=0 WHERE id=?;", (loc, i))
    conn.commit()
    fired = False
    for i in ids:
        if absorption.absorb(conn, 1, random.Random(i), i, 1).get("tribulation"):
            fired = True
    assert fired
    assert any(m["name"] == "Folgore della Tribolazione" for m in moves.available_moves(conn, 1))


# ---------- comandi di viaggio ----------

def test_raidtarget_moves_to_rival_sect(conn):
    out = loop.cmd_to_raid(conn, entities.get_player(conn))
    assert "raid" in out.lower() or "sede" in out.lower()
