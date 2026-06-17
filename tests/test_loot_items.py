"""Eredità/bottino dei caduti importanti (5b) e oggetti speciali (11)."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen
from engine.systems import character, loot, items, sects
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "loot.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _ploc(conn):
    return entities.get_player(conn).location_id


def _kill_here(conn, npc_id):
    """Porta un NPC nel luogo del player e lo marca morto (come dopo un kill)."""
    loc = _ploc(conn)
    conn.execute("UPDATE npcs SET location_id=?, status='dead', death_tick=0 WHERE id=?;",
                 (loc, npc_id))
    conn.commit()


# ---------- 5b: drop dei patriarchi ----------

def test_patriarch_drops_legacy_on_kill(conn):
    pat = conn.execute("SELECT id, name FROM npcs WHERE archetype='patriarca' LIMIT 1;").fetchone()
    _kill_here(conn, pat["id"])
    player = entities.get_player(conn)
    lines = loot.on_player_kill(conn, 10, random.Random(7), player, entities.get_npc(conn, pat["id"]))
    assert lines and "eredità" in lines[0].lower()
    drops = loot.drops_in_location(conn, _ploc(conn))
    types = {d["item_type"] for d in drops}
    # un patriarca (tier>=4) lascia almeno il manuale e il tesoro di pietre
    assert "manuale" in types
    assert "tesoro" in types
    assert len(drops) >= 2


def test_loot_command_moves_drops_to_bag(conn):
    pat = conn.execute("SELECT id FROM npcs WHERE archetype='patriarca' LIMIT 1;").fetchone()
    _kill_here(conn, pat["id"])
    player = entities.get_player(conn)
    loot.on_player_kill(conn, 10, random.Random(7), player, entities.get_npc(conn, pat["id"]))
    out = loop.cmd_loot(conn, player, "")
    assert "Raccogli" in out
    # niente più a terra, tutto nello zaino
    assert loot.drops_in_location(conn, _ploc(conn)) == []
    assert len(items.player_inventory(conn, player.id)) >= 2


def test_weak_human_drops_nothing(conn):
    # un mercante di basso regno non è "importante"
    weak = conn.execute(
        "SELECT id FROM npcs WHERE archetype='mercante' AND kind='human' LIMIT 1;").fetchone()
    if weak is None:
        pytest.skip("nessun mercante generato")
    # assicura tier basso
    r1 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (r1, weak["id"]))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=1 WHERE character_type='npc' AND character_id=?;",
                 (r1, weak["id"]))
    _kill_here(conn, weak["id"])
    player = entities.get_player(conn)
    lines = loot.on_player_kill(conn, 10, random.Random(3), player, entities.get_npc(conn, weak["id"]))
    assert lines == []
    assert loot.drops_in_location(conn, _ploc(conn)) == []


def test_mythic_beast_drops_core(conn):
    loc = _ploc(conn)
    # bestia di alto regno (tier 6) = "mitica": lascia un nucleo (tratto permanente)
    bid = creature_gen._spawn_one(conn, random.Random(1), "beast", loc, 6, 6)
    conn.execute("UPDATE npcs SET status='dead', death_tick=0 WHERE id=?;", (bid,))
    conn.commit()
    player = entities.get_player(conn)
    # con tier 6 la probabilità di nucleo è 0.8; provo alcuni seed per determinismo del test
    dropped = False
    for s in range(20):
        # reset eventuali drop precedenti
        conn.execute("DELETE FROM inventories WHERE owner_type='ground';")
        loot.on_player_kill(conn, 10, random.Random(s), player, entities.get_npc(conn, bid))
        d = loot.drops_in_location(conn, loc)
        if d:
            assert d[0]["item_type"] == "nucleo"
            dropped = True
            break
    assert dropped


# ---------- 11: uso degli oggetti ----------

def test_use_pill_advances_cultivation(conn):
    player = entities.get_player(conn)
    iid = items.create_item(conn, "Pillola Test", "pillola", "raro",
                            "Avanza la coltivazione.", {"cultivation_progress": 0.5})
    items.grant(conn, "player", player.id, iid)
    before = cultivation.get_record(conn, "player", player.id)["progress"]
    out = loop.cmd_use(conn, player, "Pillola")
    after = cultivation.get_record(conn, "player", player.id)["progress"]
    assert "Pillola Test" in out
    assert after != before                       # la coltivazione è avanzata
    assert items.find_in_inventory(conn, player.id, "Pillola Test") is None   # consumata


def test_use_core_grants_permanent_trait(conn):
    player = entities.get_player(conn)
    prof0 = character.get_profile(conn, "player", player.id)
    s0 = prof0["grow_strength"] or 0
    iid = items.create_item(conn, "Nucleo Test", "nucleo", "prezioso",
                            "Innesta forza.", {"grow_strength": 12, "grow_vitality": 6})
    items.grant(conn, "player", player.id, iid)
    loop.cmd_use(conn, player, "Nucleo")
    prof1 = character.get_profile(conn, "player", player.id)
    assert (prof1["grow_strength"] or 0) == s0 + 12


def test_use_manual_learns_technique(conn):
    player = entities.get_player(conn)
    iid = items.create_item(conn, "Manuale: Arte Suprema della Spada", "manuale", "leggendario",
                            "Insegna una tecnica.",
                            {"learn_technique": {"name": "Arte Suprema della Spada",
                                                 "magnitude": 0.2, "tech_key": "legacy:test"}})
    items.grant(conn, "player", player.id, iid)
    loop.cmd_use(conn, player, "Manuale")
    row = conn.execute(
        "SELECT magnitude FROM learned_techniques WHERE player_id=? AND tech_key='legacy:test';",
        (player.id,)).fetchone()
    assert row is not None and abs(row["magnitude"] - 0.2) < 1e-6


def test_use_treasure_grants_stones(conn):
    player = entities.get_player(conn)
    before = sects.get_resource(conn, "pietre_spirituali", player.id)
    iid = items.create_item(conn, "Tesoro Test", "tesoro", "comune",
                            "Pietre.", {"stones": 250})
    items.grant(conn, "player", player.id, iid)
    loop.cmd_use(conn, player, "Tesoro")
    assert sects.get_resource(conn, "pietre_spirituali", player.id) == before + 250


def test_inventory_command_lists_items(conn):
    player = entities.get_player(conn)
    assert "vuoto" in loop.cmd_inventory(conn, player).lower()
    iid = items.create_item(conn, "Essenza Test", "essenza", "raro", "Dao.",
                            {"dao_key": "spada", "dao_gain": 5})
    items.grant(conn, "player", player.id, iid)
    out = loop.cmd_inventory(conn, player)
    assert "Essenza Test" in out
