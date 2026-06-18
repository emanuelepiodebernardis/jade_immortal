"""Regni infiniti con nomi auto-generati + tecniche Dao fuse a 3+ Dao e nuovi elementi."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.generators.cultivation_gen import realm_name_for_tier
from engine.simulation import cultivation
from engine.systems import character, dao_techniques, dao_training


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "inf.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=2, static_npc_count=10))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


# ---------- Parte A: regni infiniti ----------

def test_realm_name_generator_infinite():
    assert realm_name_for_tier(8) == "Immortale di Giada"
    assert realm_name_for_tier(9) == "Sovrano Celeste"
    # oltre i titoli si cicla con un numerale → mai esauribile
    assert realm_name_for_tier(19) == "Sovrano Celeste II"
    assert realm_name_for_tier(8 + 10 * 3 + 1).endswith("IV")


def test_ensure_realm_creates_new_tier(conn):
    rid = cultivation.ensure_realm(conn, 12)
    row = conn.execute("SELECT name, tier FROM cultivation_realms WHERE id=?;", (rid,)).fetchone()
    assert row["tier"] == 12 and row["name"]
    # idempotente
    assert cultivation.ensure_realm(conn, 12) == rid


def test_breakthrough_beyond_jade_immortal(conn):
    t8 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (t8,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=10, progress=1.0, bt_failures=? "
                 "WHERE character_type='player' AND character_id=1;", (t8, cultivation.BT_GUARANTEE))
    res = cultivation.attempt_breakthrough(conn, "player", 1, tick=0, rng=random.Random(1))
    assert res["status"] == "success"            # niente più 'peak': si sale oltre l'8
    assert cultivation.realm_tier(conn, "player", 1) == 9
    assert cultivation.realm_name(conn, "player", 1) == "Sovrano Celeste"


# ---------- Parte B: nuovi elementi + fusione ----------

def test_new_elemental_daos_seeded(conn):
    rows = {r["dao_key"] for r in conn.execute("SELECT dao_key FROM daos WHERE level='elemental';")}
    for k in ("fuoco", "acqua", "terra", "vento", "metallo", "legno", "luce", "oscurita"):
        assert k in rows


def test_elements_are_combat_daos():
    for k in ("fuoco", "metallo", "luce", "oscurita"):
        assert k in dao_training.COMBAT_DAOS


def _give(conn, pairs):
    for k, comp in pairs:
        dao_gen._set_dao(conn, "player", 1, k, 60, comp, 1)
    conn.commit()


def test_fusion_combines_three_or_more(conn):
    _give(conn, [("spada", 300), ("fuoco", 120), ("metallo", 60)])
    techs = dao_techniques.dao_techniques(conn, 1)
    fused = next(t for t in techs if len(t.get("fused", [])) > 1)
    assert len(fused["fused"]) == 3                 # tre Dao fusi in una sola tecnica
    assert "FUSIONE" in "\n".join(dao_techniques.technique_list(conn, 1))


def test_fusion_grows_with_each_added_dao(conn):
    _give(conn, [("spada", 300), ("fuoco", 120)])
    two = next(t for t in dao_techniques.dao_techniques(conn, 1) if t["main"] == "spada")
    atk2 = two["mods"]["attack_mult"]
    _give(conn, [("metallo", 120)])                 # aggiungo un terzo Dao oltre soglia
    three = next(t for t in dao_techniques.dao_techniques(conn, 1) if t["main"] == "spada")
    assert len(three["fused"]) == 3
    assert three["mods"]["attack_mult"] > atk2      # più Dao = tecnica più forte


def test_absorbing_awakens_new_element(conn):
    # un Dao elementale assorbito si risveglia anche se non lo possedevi
    from engine.systems import absorption
    absorption._raise_comprehension(conn, "oscurita", 7, 1)
    row = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' "
                       "AND character_id=1 AND dao_key='oscurita';").fetchone()
    assert row is not None and row["comprehension"] == 7
