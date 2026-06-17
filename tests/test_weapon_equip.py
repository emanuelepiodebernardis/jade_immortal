"""Armi equipaggiabili: regno×rarità, auto-equip solo se stesso tipo e più forte,
bonus di attacco, drop dai caduti."""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import sects, sect_life, character, weapons, items, loot
from engine.simulation import combat
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "wequip.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join_and_pick(conn, wtype="spada"):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    weapons.choose_weapon(conn, wtype, 1)


# ---------- modello regno×rarità ----------

def test_bonus_scales_with_tier_and_rarity():
    assert weapons.weapon_bonus(1, 1) == 0.0
    # rarità superiore = bonus maggiore a parità di regno
    assert weapons.weapon_bonus(3, 4) > weapons.weapon_bonus(3, 1)
    # regno superiore = bonus maggiore a parità di rarità
    assert weapons.weapon_bonus(5, 2) > weapons.weapon_bonus(2, 2)


def test_starter_weapon_is_base(conn):
    _join_and_pick(conn, "spada")
    eq = weapons.get_equipped(conn, 1)
    assert eq["type"] == "spada" and eq["tier"] == 1 and eq["rarity"] == 1
    assert weapons.equipped_bonus(conn, 1) == 0.0


# ---------- regola di auto-equip ----------

def test_no_path_without_weapon(conn):
    res = weapons.try_equip_drop(conn, 1, "spada", 4, 3)
    assert res["status"] == "no_path"     # non hai ancora una via marziale


def test_wrong_type_cannot_equip(conn):
    _join_and_pick(conn, "spada")
    res = weapons.try_equip_drop(conn, 1, "arco", 6, 4)   # un arco, tu sei spada
    assert res["status"] == "wrong_type"
    assert weapons.get_equipped(conn, 1)["type"] == "spada"   # invariata


def test_same_type_weaker_is_left(conn):
    _join_and_pick(conn, "spada")
    # equipaggia una spada decente
    weapons.try_equip_drop(conn, 1, "spada", 4, 3)
    before = weapons.equipped_bonus(conn, 1)
    res = weapons.try_equip_drop(conn, 1, "spada", 2, 1)   # peggiore
    assert res["status"] == "weaker"
    assert weapons.equipped_bonus(conn, 1) == before        # invariata


def test_same_type_stronger_auto_equips(conn):
    _join_and_pick(conn, "spada")
    res = weapons.try_equip_drop(conn, 1, "spada", 5, 4)
    assert res["status"] == "equipped"
    eq = weapons.get_equipped(conn, 1)
    assert eq["tier"] == 5 and eq["rarity"] == 4
    assert weapons.equipped_bonus(conn, 1) > 0


def test_better_weapon_raises_combat_attack(conn):
    _join_and_pick(conn, "spada")
    base = combat.combat_power(conn, "player", 1)["attack"]
    weapons.try_equip_drop(conn, 1, "spada", 6, 4)
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base


# ---------- integrazione: loot di un'arma ----------

def _drop_weapon_on_ground(conn, wtype, tier, rarity):
    ploc = entities.get_player(conn).location_id
    iid = items.create_item(conn, weapons.describe_weapon(wtype, tier, rarity), "arma",
                            "raro", "Arma del caduto.",
                            {"weapon_type": wtype, "tier": tier, "rarity": rarity})
    items.grant(conn, loot.GROUND, ploc, iid)


def test_loot_auto_equips_better_same_type(conn):
    _join_and_pick(conn, "spada")
    _drop_weapon_on_ground(conn, "spada", 5, 3)
    out = loop.cmd_loot(conn, entities.get_player(conn), "")
    assert "Impugni" in out and "superiore" in out
    assert weapons.get_equipped(conn, 1)["tier"] == 5
    # niente più armi a terra
    assert loot.drops_in_location(conn, entities.get_player(conn).location_id) == []


def test_loot_wrong_type_message(conn):
    _join_and_pick(conn, "spada")
    _drop_weapon_on_ground(conn, "arco", 6, 4)
    out = loop.cmd_loot(conn, entities.get_player(conn), "")
    assert "non puoi usarla" in out.lower()
    assert weapons.get_equipped(conn, 1)["type"] == "spada"


def test_loot_weaker_same_type_message(conn):
    _join_and_pick(conn, "spada")
    weapons.try_equip_drop(conn, 1, "spada", 5, 4)     # già forte
    _drop_weapon_on_ground(conn, "spada", 2, 1)
    out = loop.cmd_loot(conn, entities.get_player(conn), "")
    assert "non è all'altezza" in out.lower()
    assert weapons.get_equipped(conn, 1)["tier"] == 5  # invariata
