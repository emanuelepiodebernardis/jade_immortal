"""Tecniche generate dai Dao + Guerriero Dao: generazione a soglie, combinazione, Spirito."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen, creature_gen
from engine.systems import character, dao_techniques, spirit as spmod, moves
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "daotech.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_no_technique_below_threshold(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 5, 1)   # < 10
    assert dao_techniques.dao_techniques(conn, 1) == []


def test_technique_appears_at_threshold_10(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 12, 1)
    techs = dao_techniques.dao_techniques(conn, 1)
    assert len(techs) == 1
    t = techs[0]
    assert t["main"] == "spada" and t["fuel"] == "spirit" and t["spirit_cost"] > 0
    assert t["source"] == "dao"


def test_technique_evolves_with_dao(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 12, 1)
    name_low = dao_techniques.dao_techniques(conn, 1)[0]["name"]
    pw_low = dao_techniques.dao_techniques(conn, 1)[0]["mods"]["attack_mult"]
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 600, 1)   # soglia molto più alta
    t_high = dao_techniques.dao_techniques(conn, 1)[0]
    assert t_high["name"] != name_low                  # il nome è evoluto
    assert t_high["mods"]["attack_mult"] > pw_low      # più potente


def test_secondary_dao_modifies_name(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 120, 1)
    base = dao_techniques.dao_techniques(conn, 1)[0]["name"]
    dao_gen._set_dao(conn, "player", 1, "fulmine", 70, 40, 1)  # secondario
    combo = next(t for t in dao_techniques.dao_techniques(conn, 1) if t["main"] == "spada")
    assert combo["mod"] == "fulmine"
    assert combo["name"] != base                       # la combinazione cambia il nome


def test_spirit_pool_scales_with_anima(conn):
    base = spmod.max_spirit(conn, 1)
    dao_gen._set_dao(conn, "player", 1, "anima", 70, 200, 1)
    assert spmod.max_spirit(conn, 1) > base            # investire nell'Anima allarga lo Spirito


def test_dao_techniques_appear_in_move_pool_with_spirit_fuel(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 120, 1)
    pool = moves.available_moves(conn, 1)
    dao_moves = [m for m in pool if m.get("fuel") == "spirit"]
    assert dao_moves and all(m["spirit_cost"] > 0 for m in dao_moves)


def test_using_dao_technique_spends_spirit(conn):
    from engine.cli import loop
    dao_gen._set_dao(conn, "player", 1, "spada", 70, 250, 1)
    dao_gen._set_dao(conn, "player", 1, "anima", 70, 200, 1)   # ampia riserva di Spirito
    # regno modesto: è la via del Guerriero Dao
    r2 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=2;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (r2,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (r2,))
    loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    # un avversario robusto perché lo scontro duri abbastanza da usare una tecnica
    bid = creature_gen._spawn_one(conn, random.Random(3), "beast", loc, 4, 4)
    conn.execute("UPDATE npcs SET name='Orsaccio' WHERE id=?;", (bid,))
    conn.commit()
    sp0 = spmod.get_spirit(conn, 1)
    out = loop.cmd_attack(conn, entities.get_player(conn), "Orsaccio")
    # se ha scatenato una tecnica Dao, lo Spirito è calato e la narrazione è propria
    if "◈" in out:
        assert spmod.get_spirit(conn, 1) < sp0


def test_dao_warrior_low_realm_high_dao_is_strong(conn):
    """Un Guerriero Dao di regno modesto ma Dao mostruoso supera un coltivatore di regno alto."""
    # guerriero Dao: regno 2, spada 1000
    r2 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=2;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (r2,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=3 WHERE character_type='player' AND character_id=1;", (r2,))
    dao_gen._set_dao(conn, "player", 1, "spada", 90, 1000, 1)
    warrior_atk = combat.combat_power(conn, "player", 1)["attack"]
    # coltivatore classico di regno alto ma Dao scarso (npc), per confronto
    npc = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()["id"]
    r5 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=5;").fetchone()["id"]
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=3 WHERE character_type='npc' AND character_id=?;", (r5, npc))
    conn.execute("UPDATE character_daos SET comprehension=20 WHERE character_type='npc' AND character_id=?;", (npc,))
    classic_atk = combat.combat_power(conn, "npc", npc)["attack"]
    assert warrior_atk > classic_atk
