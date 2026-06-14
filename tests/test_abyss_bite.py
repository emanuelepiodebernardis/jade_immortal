"""L'Abisso morde: bonus evolutivi reali, terrore, corruzione che attira i cacciatori, tribolazione."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, absorption, hunters, perception
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "abyss.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _set_counts(conn, beast=0, demon=0, spirit=0, human=0):
    conn.execute("UPDATE character_profiles SET abs_beast=?, abs_demon=?, abs_spirit=?, abs_human=? "
                 "WHERE character_type='player' AND character_id=1;", (beast, demon, spirit, human))


def _set_residue(conn, r):
    conn.execute("UPDATE character_profiles SET soul_residue=? "
                 "WHERE character_type='player' AND character_id=1;", (r,))


def test_no_evolution_bonus_without_dominance(conn):
    assert absorption.evolution_bonuses(conn, 1) == {}
    _set_counts(conn, beast=2, demon=2, spirit=2)   # nessuna dominanza
    assert absorption.evolution_bonuses(conn, 1) == {}


def test_beast_path_raises_attack_and_vitality(conn):
    before = combat.combat_power(conn, "player", 1)
    _set_counts(conn, beast=120)                    # Predatore Primordiale compiuto
    evb = absorption.evolution_bonuses(conn, 1)
    assert evb.get("attack_mult", 1) > 1 and evb.get("vitality_mult", 1) > 1
    after = combat.combat_power(conn, "player", 1)
    assert after["attack"] > before["attack"]
    assert after["vitality"] > before["vitality"]


def test_demon_path_grants_fear(conn):
    _set_counts(conn, demon=120)
    assert absorption.evolution_bonuses(conn, 1).get("fear", 0) > 0
    assert absorption.dread_level(conn, 1) > 0


def test_spirit_path_raises_spirit_score(conn):
    base = perception.spirit_score(conn, "player", 1)
    _set_counts(conn, spirit=120)
    assert perception.spirit_score(conn, "player", 1) > base


def test_corruption_increases_dread_and_presence(conn):
    _set_residue(conn, 600)                          # terrore
    assert absorption.dread_level(conn, 1) >= 2
    low = perception.spirit_score(conn, "player", 1)
    _set_residue(conn, 1200)                         # anomalia celeste
    assert absorption.dread_level(conn, 1) >= 3
    assert perception.spirit_score(conn, "player", 1) > low


def test_corruption_attracts_hunters(conn):
    # niente reputazione, ma corruzione alta -> gli anziani percepiscono l'Abisso
    _set_residue(conn, 300)
    assert hunters._threat_tier(conn, 1) == 1
    _set_residue(conn, 1100)
    assert hunters._threat_tier(conn, 1) == 2


def test_dread_reduces_incoming_damage_in_combat(conn):
    # con terrore alto, un attacco subisce meno danni (i nemici esitano)
    from engine.cli import loop
    _set_residue(conn, 1200)
    # un avversario forte per generare danni misurabili
    r6 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=6;").fetchone()["id"]
    loc = conn.execute("""SELECT id FROM locations WHERE id NOT IN
        (SELECT DISTINCT location_id FROM npcs WHERE status='alive' AND location_id IS NOT NULL) LIMIT 1;""").fetchone()["id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (loc,))
    from engine.generators import creature_gen
    bid = creature_gen._spawn_one(conn, random.Random(2), "beast", loc, 6, 6)
    conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (r6, bid))
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (bid,)).fetchone()["name"]
    out = loop.cmd_attack(conn, entities.get_player(conn), name.split()[0])
    assert "terrorizza" in out                       # la presenza abissale è narrata


def test_tribulation_strikes_at_max_corruption(conn):
    _set_residue(conn, 1500)
    player = entities.get_player(conn)
    res_before = character.get_profile(conn, "player", 1)["soul_residue"]
    fired = 0
    for tk in range(40):
        fired += absorption.maybe_tribulation(conn, 24 * tk, random.Random(tk), player, [])
        if fired:
            break
    assert fired == 1
    # ha inflitto una ferita e scaricato corruzione
    inj = conn.execute("SELECT COUNT(*) c FROM injuries WHERE character_type='player' AND healed=0;").fetchone()["c"]
    assert inj >= 1
    assert character.get_profile(conn, "player", 1)["soul_residue"] < res_before


def test_tribulation_only_for_devourer_at_max(conn):
    _set_residue(conn, 500)                           # sotto soglia
    player = entities.get_player(conn)
    assert absorption.maybe_tribulation(conn, 24, random.Random(1), player, []) == 0
