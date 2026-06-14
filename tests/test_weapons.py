"""Arma principale: scelta in setta, sblocco del Dao d'arma, permanenza."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import sects, sect_life, character, weapons, dao_training
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "weap.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))


def test_all_weapon_daos_exist_in_seed(conn):
    keys = {r["dao_key"] for r in conn.execute("SELECT dao_key FROM daos;")}
    for _k, (dao_key, _label, _name) in weapons.WEAPONS.items():
        assert dao_key in keys


def test_weapon_daos_are_combat_daos():
    for _k, (dao_key, _l, _n) in weapons.WEAPONS.items():
        assert dao_key in dao_training.COMBAT_DAOS


def test_choosing_weapon_unlocks_trainable_dao(conn):
    _join(conn)
    res = weapons.choose_weapon(conn, "lancia", 1)
    assert res["status"] == "chosen"
    assert weapons.get_weapon(conn, 1) == "lancia"
    # il Dao della lancia è ora praticato e allenabile
    row = conn.execute("SELECT practiced, comprehension FROM character_daos "
                       "WHERE character_type='player' AND character_id=1 AND dao_key='lancia';").fetchone()
    assert row is not None and row["practiced"] == 1
    out = dao_training.comprehend(conn, 0, random.Random(3), "lancia")
    assert out["status"] == "ok" and out["gain"] > 0


def test_weapon_choice_is_permanent(conn):
    _join(conn)
    weapons.choose_weapon(conn, "spada", 1)
    again = weapons.choose_weapon(conn, "arco", 1)
    assert again["status"] == "already"
    assert weapons.get_weapon(conn, 1) == "spada"   # invariata


def test_weapon_accepts_number_and_aliases(conn):
    _join(conn)
    res = weapons.choose_weapon(conn, "pugni", 1)   # alias -> pugno
    assert res["status"] == "chosen" and weapons.get_weapon(conn, 1) == "pugno"


def test_weapon_dao_boosts_combat(conn):
    _join(conn)
    base = combat.combat_power(conn, "player", 1)["attack"]
    weapons.choose_weapon(conn, "spada", 1)
    # porta la comprensione della spada a una soglia con bonus
    conn.execute("UPDATE character_daos SET comprehension=100 "
                 "WHERE character_type='player' AND character_id=1 AND dao_key='spada';")
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base


def test_cmd_weapon_requires_sect(conn):
    from engine.cli import loop
    player = entities.get_player(conn)
    # senza setta: invita a unirsi
    out = loop.cmd_weapon(conn, player, "spada")
    assert "setta" in out.lower()
    assert weapons.get_weapon(conn, 1) is None
