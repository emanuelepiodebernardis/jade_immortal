"""Il tetto di ogni mondo, l'ascensione che lascia indietro gli oggetti, i nomi dei regni."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators.cultivation_gen import realm_name_for_tier
from engine.systems import character, ascension, items, sects, professions, npc_factory
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "worlds.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=7, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _set_tier(conn, tier, stage=10, progress=1.0):
    rid = cultivation.ensure_realm(conn, tier)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=?, progress=? "
                 "WHERE character_type='player' AND character_id=1;", (rid, stage, progress))


def test_realm_names_and_phases():
    assert realm_name_for_tier(1) == "Condensazione del Qi"
    assert realm_name_for_tier(9) == "Superamento della Tribolazione"
    assert realm_name_for_tier(10) == "Immortale di Giada"
    assert realm_name_for_tier(14) == "Immortale d'Oro dell'Unità Suprema"
    assert cultivation.stage_phase(2) == "iniziale" and cultivation.stage_phase(10, 1.0) == "Grande Perfezione"


def test_mortal_world_caps_everyone(conn):
    p = entities.get_player(conn)
    nid = npc_factory.spawn(conn, random.Random(1), archetype="anziano", location_id=p.location_id, tier=15)
    assert cultivation.realm_tier(conn, "npc", nid) == 9               # nessuno nasce oltre il tetto
    npc_factory.raise_npc(conn, nid, 40)
    assert cultivation.realm_tier(conn, "npc", nid) == 9
    _set_tier(conn, 9)
    out = loop.dispatch(conn, "breakthrough", allow_nl=False)
    assert "ascendi_mondo" in out and cultivation.realm_tier(conn, "player", 1) == 9


def test_ascension_needs_perfection_and_leaves_items_behind(conn):
    _set_tier(conn, 9, stage=5, progress=0.2)
    assert "GRANDE PERFEZIONE" in ascension.ascend(conn, entities.get_player(conn))
    _set_tier(conn, 9)
    iid = items.create_item(conn, "Pillola di Prova", "pillola", "raro", "x", {"cultivation_progress": 0.1})
    items.grant(conn, "player", 1, iid, 3)
    professions.give(conn, 1, "erbe", 20)
    sects.grant_resource(conn, "pietre_spirituali", 1000, 1)
    warn = ascension.ascend(conn, entities.get_player(conn))
    assert "conferma" in warn and "Pillola di Prova" in warn
    out = ascension.ascend(conn, entities.get_player(conn), "conferma")
    assert "Immortale di Giada" in out
    assert cultivation.realm_tier(conn, "player", 1) == 10
    assert not items.player_inventory(conn, 1)
    assert professions.material(conn, 1, "erbe") == 0
    assert sects.get_resource(conn, "pietre_spirituali", 1) == 100
    p = entities.get_player(conn)
    assert ascension.layer_of_location(conn, p.location_id) == 1
    assert ascension.cap_at(conn, p.location_id) == 12
