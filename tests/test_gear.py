"""Aggiornamento 69: l'equipaggiamento — sei posti, rarità, set, forgia, effetti in combattimento."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation, combat
from engine.systems import character, gear, sects, rewards


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "g.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 4)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def test_make_scales_with_tier_and_rarity():
    r = random.Random(1)
    lo = gear.make(r, 1, "anello", "comune")["stats"]["atk"]
    hi = gear.make(r, 9, "anello", "divina")["stats"]["atk"]
    assert hi > lo * 4
    assert len(gear.make(r, 3, "veste", "divina")["stats"]) == 4
    assert gear.make(r, 3, "veste", "comune")["set"] == ""


def test_add_equips_empty_slot_then_bags(conn):
    r = random.Random(2)
    assert "Indossi" in gear.add(conn, gear.make(r, 4, "anello", "comune"))
    assert "Trovi" in gear.add(conn, gear.make(r, 4, "anello", "divina"))
    d = gear.get(conn)
    assert "anello" in d["eq"] and len(d["bag"]) == 1
    gear.auto(conn)
    assert gear.get(conn)["eq"]["anello"]["rar"] == "divina"


def test_bonus_sets_and_combat(conn):
    p = entities.get_player(conn)
    before = combat.combat_power(conn, "player", p.id)["attack"]
    r = random.Random(3)
    for s in gear.ORDER:
        it = gear.make(r, 4, s, "pregiata")
        it["set"] = "drago"
        gear.add(conn, it)
    b = gear.bonus(conn)
    assert b["atk"] >= 0.05 + 0.08                      # set del Drago, 2 e 4 pezzi
    assert gear.sets_active(conn)
    assert combat.combat_power(conn, "player", p.id)["attack"] > before
    assert gear.cultivation_mult(conn)[0] > 1.0


def test_forge_scrap_and_commands(conn):
    p = entities.get_player(conn)
    cost = gear.forge_cost(4)
    sects.grant_resource(conn, "pietre_spirituali", cost * 3, p.id)
    out = gear.command(conn, p, "forgia anello")
    assert "forgia" in out.lower() and "anello" in gear.get(conn)["eq"]
    assert sects.get_resource(conn, "pietre_spirituali", p.id) == cost * 2
    gear.command(conn, p, "forgia anello")
    n = gear.get(conn)["bag"][0]["id"]
    assert "Scomponi" in gear.command(conn, p, f"scomponi {n}")
    assert "togli" in gear.command(conn, p, "zzz") or "equip" in gear.command(conn, p, "zzz")
    v = gear.view(conn)
    assert len(v["posti"]) == 6 and v["costo_forgia"] == cost


def test_rewards_can_drop_gear(conn):
    p = entities.get_player(conn)
    got = 0
    for i in range(30):
        lines = rewards.grant(conn, random.Random(i), p, rank=1)
        got += sum("🧥" in x for x in lines)
    assert got >= 3
