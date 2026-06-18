"""Correzioni: breakthrough che converge (no morte-trappola), use all, Dao d'assorbimento
scalato per setta, e rating che cresce con la coltivazione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, items, sects, sect_life
from engine.simulation import cultivation, combat
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "fix.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _make_ready(conn, tier=3, fails=0):
    rid = conn.execute("SELECT id FROM cultivation_realms WHERE tier=?;", (tier,)).fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=?, status='alive' WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=10, progress=1.0, "
                 "bt_failures=? WHERE character_type='player' AND character_id=1;", (rid, fails))


# ---------- breakthrough rework ----------

def test_guarantee_forces_success_after_many_failures(conn):
    _make_ready(conn, tier=3, fails=cultivation.BT_GUARANTEE)
    # con abbastanza fallimenti accumulati lo sfondamento è garantito, qualunque sia il seed
    res = cultivation.attempt_breakthrough(conn, "player", 1, tick=0, rng=random.Random(999))
    assert res["status"] == "success"
    # e i fallimenti si azzerano dopo il successo
    rec = cultivation.get_record(conn, "player", 1)
    assert (rec["bt_failures"] or 0) == 0


def test_failure_fortifies_body(conn):
    _make_ready(conn, tier=3, fails=0)
    rec = cultivation.get_record(conn, "player", 1)
    s0 = character.get_profile(conn, "player", 1)["grow_strength"] or 0
    res = cultivation._breakthrough_setback(conn, "player", 1, rec, 3, 0, "Tu", None, None, None)
    assert res["status"] == "failure" and res["bt_failures"] == 1
    s1 = character.get_profile(conn, "player", 1)["grow_strength"] or 0
    assert s1 > s0                      # il corpo si è rinforzato
    rec2 = cultivation.get_record(conn, "player", 1)
    assert (rec2["bt_failures"] or 0) == 1 and rec2["body_level"] > (rec["body_level"] or 0)


def test_absorption_does_not_raise_death_anymore(conn):
    # con residuo altissimo il breakthrough è più ARDUO (meno successo) ma non più letale:
    # su molti tentativi deve riuscire, non solo morire
    conn.execute("UPDATE character_profiles SET soul_residue=400 "
                 "WHERE character_type='player' AND character_id=1;")
    succeeded = False
    for seed in range(60):
        _make_ready(conn, tier=2, fails=0)
        conn.execute("UPDATE players SET status='alive' WHERE id=1;")
        res = cultivation.attempt_breakthrough(conn, "player", 1, tick=seed, rng=random.Random(seed))
        if res["status"] == "success":
            succeeded = True
            break
    assert succeeded


# ---------- use all ----------

def test_use_all_consumes_inventory(conn):
    player = entities.get_player(conn)
    i1 = items.create_item(conn, "Pillola A", "pillola", "raro", "x", {"cultivation_progress": 0.2})
    i2 = items.create_item(conn, "Tesoro B", "tesoro", "comune", "y", {"stones": 100})
    items.grant(conn, "player", player.id, i1)
    items.grant(conn, "player", player.id, i2)
    out = loop.cmd_use(conn, player, "all")
    assert "Pillola A" in out and "Tesoro B" in out
    assert items.player_inventory(conn, player.id) == []     # zaino svuotato


# ---------- Dao d'assorbimento scalato per setta ----------

def _dead_human_with_dao(conn, comp=60):
    ploc = entities.get_player(conn).location_id
    other = conn.execute("SELECT id FROM locations WHERE id<>? LIMIT 1;", (ploc,)).fetchone()["id"]
    npc = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' "
                       "AND id NOT IN (SELECT id FROM players) LIMIT 1;").fetchone()
    from engine.generators import dao_gen
    dao_gen._set_dao(conn, "npc", npc["id"], "spada", comp, 50, 1)
    # isola: sposta i possibili testimoni in un'altra location valida
    conn.execute("UPDATE npcs SET location_id=? WHERE location_id=? "
                 "AND status='alive' AND id NOT IN (SELECT id FROM players);", (other, ploc))
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;",
                 (ploc, npc["id"]))
    conn.commit()
    return npc["id"]


def test_absorbed_dao_scales_with_sect_tier(conn):
    import random as R
    # setta di tier 1
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    fac = sects.get_membership(conn, 1)["faction_id"]
    conn.execute("UPDATE factions SET tier=1 WHERE id=?;", (fac,))
    from engine.systems import absorption
    tid = _dead_human_with_dao(conn, comp=60)
    low = absorption.absorb(conn, 0, R.Random(1), tid, 1).get("dao_gain", 0)
    # stessa identica preda, ma ora la setta è tier 3
    conn.execute("UPDATE factions SET tier=3 WHERE id=?;", (fac,))
    tid2 = _dead_human_with_dao(conn, comp=60)
    high = absorption.absorb(conn, 0, R.Random(1), tid2, 1).get("dao_gain", 0)
    assert high > low                    # in setta superiore si assorbe più Dao


# ---------- rating cresce con la coltivazione ----------

def test_cultivation_levels_raise_rating(conn):
    from engine.systems import power
    before = power.combat_rating(conn, "player", 1)
    conn.execute("UPDATE cultivation_records SET qi_level=qi_level+200, body_level=body_level+200, "
                 "soul_level=soul_level+200, dao_understanding=dao_understanding+200 "
                 "WHERE character_type='player' AND character_id=1;")
    after = power.combat_rating(conn, "player", 1)
    assert after > before                # salire i livelli non può abbassare il rating
