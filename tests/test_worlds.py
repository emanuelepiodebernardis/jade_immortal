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


def test_ascending_makes_the_whole_plane_new_sects_included(conn):
    p = entities.get_player(conn)
    hq = conn.execute("SELECT id, home_location_id FROM factions WHERE home_location_id IS NOT NULL LIMIT 1;").fetchone()
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (hq["home_location_id"],))
    loop.dispatch(conn, "join", allow_nl=False)
    conn.execute("INSERT OR IGNORE INTO sect_memberships (player_id, faction_id, rank, joined_tick) VALUES (1, ?, "
                 "'Discepolo Esterno', 0);", (hq["id"],)) if not sects.get_membership(conn, 1) else None
    assert sects.get_membership(conn, 1)
    _set_tier(conn, 9)
    out = ascension.ascend(conn, entities.get_player(conn), "conferma")
    assert ascension.player_layer(conn) == 1
    assert sects.get_membership(conn, 1) is None and "resta nel mondo inferiore" in out
    plane = ascension.plane_faction_ids(conn, 1)
    assert len(plane) == ascension.PLANE_SECTS
    lo, hi = ascension.plane_range(1)
    for r in conn.execute("SELECT id FROM npcs WHERE status='alive' AND location_id IN (%s);"
                          % ",".join("?" * len(ascension.plane_locations(conn, 1))), ascension.plane_locations(conn, 1)):
        assert lo <= (cultivation.realm_tier(conn, "npc", r["id"]) or 1) <= hi
    txt = loop.dispatch(conn, "sects", allow_nl=False)
    names = [r["name"] for r in conn.execute("SELECT name, id FROM factions;") if r["id"] in plane]
    others = [r["name"] for r in conn.execute("SELECT name, id FROM factions;") if r["id"] not in plane]
    assert all(n in txt for n in names) and not any(n in txt for n in others)


def test_upper_world_has_its_own_beasts_and_race_ladders(conn):
    from engine.systems import beasts, race_realms, bloodlines
    pool0 = {s[1] for s in beasts.plane_pool(0, 20)}
    pool1 = {s[1] for s in beasts.plane_pool(1, 20)}
    assert "rara" in pool0 and "ancestrale" not in pool0
    assert "rara" not in pool1 and "ancestrale" in pool1
    assert "caos" in {s[1] for s in beasts.plane_pool(2, 20)}
    p = entities.get_player(conn)
    bloodlines.gain(conn, 0, random.Random(1), p, "Drago delle Nubi", ["fulmine"], 40)
    d0 = race_realms.get(conn)
    d0["draghi"]["standing"], d0["draghi"]["beaten"] = 5, 6
    race_realms._save(conn, d0)
    _set_tier(conn, 9)
    out = ascension.ascend(conn, entities.get_player(conn), "conferma")
    d1 = race_realms.get(conn)
    assert d1["draghi"]["standing"] == 1 and d1["draghi"]["beaten"] == 0     # si riparte, da Discepolo
    assert d1["demoni"]["standing"] == 0
    assert "Discepolo" in out
    land = race_realms._land(conn, "draghi")
    assert land in ascension.plane_locations(conn, 1)


def test_never_ascend_into_a_weaker_world(conn):
    _set_tier(conn, 13)                        # salvataggio vecchio: oltre il tetto del Mondo Mortale
    out = ascension.ascend(conn, entities.get_player(conn), "conferma")
    layer = ascension.player_layer(conn)
    assert ascension.world_cap(layer) > 13 and layer == 2, out
