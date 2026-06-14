"""Verifica dei 4 fix: ricarica giornaliera Qi, uccisione decisiva, paralisi, assorbimento umano."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, qi as qimod, absorption


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "bugs.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def _strong_player(conn, tier=8):
    rid = conn.execute("SELECT id FROM cultivation_realms WHERE tier=?;", (tier,)).fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=8 "
                 "WHERE character_type='player' AND character_id=1;", (rid,))
    conn.commit()


def test_new_day_restores_qi(conn):
    from engine.cli import loop
    character.apply_origin(conn, "mortale", random.Random(1))
    # inizializza il Qi (prima lettura = pieno) poi spendine una parte
    qimod.get_qi(conn, 1)
    qimod.spend(conn, max(1, qimod.max_qi(conn, 1) - 5), 1)
    conn.commit()
    assert qimod.get_qi(conn, 1) < qimod.max_qi(conn, 1)
    # avanza il tempo oltre il giorno e mostra il banner (che ricarica)
    from engine.systems import training
    conn.execute("UPDATE worlds SET current_tick=?;", (training.DAY_TICKS + 2,))
    conn.execute("DELETE FROM game_state WHERE key='last_day';")
    conn.commit()
    banner = loop._day_banner(conn, entities.get_player(conn))
    assert banner is not None
    assert qimod.get_qi(conn, 1) == qimod.max_qi(conn, 1)


def test_decisive_victory_kills(conn):
    from engine.cli import loop
    from engine.generators import creature_gen
    _strong_player(conn, 8)
    loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    # una bestia debolissima: divario schiacciante
    kills = 0
    for i in range(6):
        bid = creature_gen._spawn_one(conn, random.Random(i), "beast", loc, 1, 1)
        conn.execute("UPDATE npcs SET name=? WHERE id=?;", (f"Bersaglio{i}", bid))
        conn.commit()
        loop.cmd_attack(conn, entities.get_player(conn), f"Bersaglio{i}")
        st = conn.execute("SELECT status FROM npcs WHERE id=?;", (bid,)).fetchone()["status"]
        if st in ("dead", "absorbed"):
            kills += 1
    assert kills == 6        # ogni vittoria schiacciante deve uccidere


def test_intimidated_enemy_is_paralyzed_not_fleeing(conn):
    from engine.cli import loop
    from engine.systems import perception
    from engine.generators import dao_gen
    _strong_player(conn, 8)
    # spirito altissimo = comprensione del Dao dell'Anima (non aff_soul)
    dao_gen._set_dao(conn, "player", 1, "anima", 90, 300, 1)
    loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    npc = conn.execute("SELECT id, name FROM npcs WHERE kind='human' AND status='alive' "
                       "AND location_id IS NOT NULL LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (loc, npc["id"]))
    # azzera lo spirito del bersaglio per garantire l'intimidazione
    conn.execute("UPDATE character_daos SET comprehension=0 WHERE character_type='npc' AND character_id=?;", (npc["id"],))
    conn.execute("UPDATE cultivation_records SET realm_id=(SELECT id FROM cultivation_realms WHERE tier=1) "
                 "WHERE character_type='npc' AND character_id=?;", (npc["id"],))
    conn.commit()
    assert perception.intimidates(conn, 1, entities.get_npc(conn, npc["id"])) is True
    p = entities.get_player(conn)
    out = loop.cmd_attack(conn, p, npc["name"].split()[0])
    assert "paralizzato" in out.lower()
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (npc["id"],)).fetchone()["status"] != "alive"


def test_absorbing_plain_human_gives_stats(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    # un umano SENZA Dao (mortale per strada): prima dava 0 statistiche
    npc = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("DELETE FROM character_daos WHERE character_type='npc' AND character_id=?;", (npc,))
    conn.execute("UPDATE npcs SET status='dead', death_tick=5, location_id=? WHERE id=?;", (loc, npc))
    conn.commit()
    prof0 = character.get_profile(conn, "player", 1)
    g0 = (prof0["grow_strength"], prof0["grow_vitality"], prof0["grow_soul"])
    res = absorption.absorb(conn, tick=6, rng=random.Random(2), target_id=npc)
    assert res["status"] == "human"
    assert res["strength"] >= 1 and res["vitality"] >= 1 and res["soul"] >= 1
    prof1 = character.get_profile(conn, "player", 1)
    g1 = (prof1["grow_strength"], prof1["grow_vitality"], prof1["grow_soul"])
    assert g1[0] > g0[0] and g1[1] > g0[1] and g1[2] > g0[2]


def test_absorbing_higher_level_human_gives_more(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 2;")]
    low, high = ids[0], ids[1]
    t1 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=1;").fetchone()["id"]
    t6 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=6;").fetchone()["id"]
    for i in ids:
        conn.execute("DELETE FROM character_daos WHERE character_type='npc' AND character_id=?;", (i,))
        conn.execute("UPDATE npcs SET status='dead', death_tick=5, location_id=? WHERE id=?;", (loc, i))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='npc' AND character_id=?;", (t1, low))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='npc' AND character_id=?;", (t6, high))
    conn.commit()
    r_low = absorption.absorb(conn, tick=6, rng=random.Random(5), target_id=low)
    r_high = absorption.absorb(conn, tick=6, rng=random.Random(5), target_id=high)
    assert r_high["strength"] >= r_low["strength"]
    assert r_high["soul"] >= r_low["soul"]
