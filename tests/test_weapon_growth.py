"""Arma viva: esperienza con tempo e uso, tempra automatica, risveglio, spirito senza tetto."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, weapons, weapon_spirit, combat_states, npc_factory
from engine.simulation import cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "w.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=3, factions=3, static_npc_count=10))
    character.apply_origin(c, "mortale", random.Random(2))
    c.execute("UPDATE character_profiles SET weapon='spada', weapon_tier=1, weapon_rarity=1 "
              "WHERE character_type='player' AND character_id=1;")
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _set_tier(conn, tier):
    rid = cultivation.ensure_realm(conn, tier)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


def test_weapon_tempers_itself_but_never_beyond_player(conn):
    out = weapon_spirit.add_xp(conn, _p(conn), 2000)
    eq = weapons.get_equipped(conn, 1)
    assert eq["rarity"] == 4 and eq["tier"] == 1          # regno 1: non può salire oltre
    assert any("tempra" in x for x in out)
    _set_tier(conn, 3)
    weapon_spirit.add_xp(conn, _p(conn), 5000)
    assert weapons.get_equipped(conn, 1)["tier"] == 3


def test_any_weapon_awakens_with_time(conn):
    _set_tier(conn, 9)                                     # la tempra non frena il risveglio
    conn.execute("UPDATE character_profiles SET weapon_tier=9 WHERE character_type='player' AND character_id=1;")
    msgs = []
    for _ in range(10):
        msgs += weapon_spirit.on_days(conn, _p(conn), 60)
    assert weapon_spirit.get(conn)["awakened"]
    assert weapon_spirit.get(conn)["days"] == 600
    assert weapon_spirit.bond_mult(weapon_spirit.get(conn)) > 1.5


def test_spirit_grows_without_cap_and_unlocks(conn):
    weapon_spirit.awaken(conn, random.Random(1), _p(conn), forced=True)
    out = weapon_spirit.add_xp(conn, _p(conn), 50000)
    d = weapon_spirit.get(conn)
    lv = weapon_spirit.level(d)
    assert lv > 21 and "Origine" in weapon_spirit.grade(lv)
    assert weapon_spirit.weapon_name(d)
    assert any("SENZIENTE" in x for x in out) and any("CELESTE" in x for x in out)
    assert "accetta" in weapon_spirit.rename(conn, _p(conn), "Lama del Mattino")
    assert weapon_spirit.weapon_name(weapon_spirit.get(conn)) == "Lama del Mattino"
    enemy = npc_factory.spawn(conn, random.Random(4), archetype="vagabondo", location_id=_p(conn).location_id, tier=1)
    fx = combat_states.FightCtx(conn, 1, enemy, "Tu", "X", 100, 100, 10, 10)
    ally = weapon_spirit.combat_ally(conn, 1, fx)
    assert ally["attack"] > 0 and fx.p.lethal_saves >= 1


def test_upset_victory_teaches_more_and_is_remembered(conn):
    weapon_spirit.on_fight(conn, random.Random(1), _p(conn), True, "Gigante di Ferro", 0.5)
    d = weapon_spirit.get(conn)
    assert d["xp"] >= 13 and "Gigante di Ferro" in d["feats"]
    assert "Gigante di Ferro" in weapon_spirit.full(conn, _p(conn))


def test_bonded_weapon_is_not_replaced_and_new_weapon_resets(conn):
    weapon_spirit.awaken(conn, random.Random(1), _p(conn), forced=True)
    res = weapons.try_equip_drop(conn, 1, "spada", 5, 4)
    assert res["status"] == "bonded"
    conn.execute("UPDATE game_state SET value='{}' WHERE key='weapon_spirit';")
    weapon_spirit.get(conn)
    res = weapons.try_equip_drop(conn, 1, "spada", 5, 4)
    assert res["status"] == "equipped"
    assert weapon_spirit.get(conn)["xp"] == 0
