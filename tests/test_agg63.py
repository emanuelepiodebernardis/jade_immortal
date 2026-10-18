"""Aggiornamento 63: destini dello sfondamento, discepoli vivi, legami in Cielo, mondo di sotto,
viaggio dell'anima e meditazioni, cavalcature, Torre della Deificazione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import (character, encounters, state, sects, breakthrough_fates as bf, disciple_life as dl,
                            heaven_bonds, lower_world, soul_roam, mounts, deification_tower as tower, npc_factory,
                            bonds, menus)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a63.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 5)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.execute("UPDATE worlds SET current_tick=current_tick+1200;")
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


def test_breakthrough_fates_offer_and_take(conn):
    p = _p(conn)
    assert bf.on_realm_up(conn, p, 5)
    out = bf.after_command(conn, p)
    assert out and "tre fili" in out[0]
    sc = encounters.pending(conn)
    assert len(sc["choices"]) == 3
    encounters.choose(conn, p, 1)
    assert len(bf.chosen(conn)) == 1
    k = bf.chosen(conn)[0]
    assert k in bf.BY_KEY
    assert not encounters.pending(conn) and not bf.after_command(conn, p)


def test_fates_effects(conn):
    state.set_json(conn, bf.KEY, ["respiro_lungo", "corpo_immortale", "sangue_bollente"])
    assert abs(bf.cultivation_mult(conn)[0] - 1.06) < 1e-9
    assert bf.total(conn, "lethal") == 1 and abs(bf.total(conn, "taken") + 0.05) < 1e-9


def _disciple(conn, p):
    nid = npc_factory.spawn(conn, random.Random(1), archetype="discepolo", location_id=p.location_id, tier=2)
    bonds.add_bond(conn, p.id, nid, "disciple", tick.get_tick(conn), reason="test")
    return nid


def test_disciples_traits_tasks_lecture(conn):
    p = _p(conn)
    nid = _disciple(conn, p)
    inf = dl.info(conn, nid)
    assert len(inf["traits"]) == 2 and inf["task"] == "allena"
    assert "incarichi" in dl.assign(conn, p, "missioni", "1")
    out = dl.daily(conn, tick.get_tick(conn), random.Random(1), p)
    assert out and "📋" in out[0]
    assert "Lezione aperta" in dl.lecture(conn, p)
    assert "già tenuta" in dl.lecture(conn, p)
    m = menus.build(conn, p, "discepoli")
    assert len(m["sections"]) == 2


def test_disciple_demon_and_redemption(conn):
    p = _p(conn)
    nid = _disciple(conn, p)
    inf = dl.info(conn, nid)
    inf["demon"] = True
    dl._set(conn, nid, inf)
    assert "è nel demone" in dl.daily(conn, tick.get_tick(conn), random.Random(1), p)[0]
    dl.face(conn, p, "1")
    assert state.get_int(conn, "disciple_demon_duel", 0) == nid
    out = dl.on_duel(conn, p, nid, "risparmiato")
    assert out and not dl.info(conn, nid)["demon"]


def test_bonds_follow_to_heaven(conn):
    from engine.systems import ascension
    p = _p(conn)
    nid = npc_factory.spawn(conn, random.Random(2), archetype="vagabondo", location_id=p.location_id, tier=2)
    bonds.add_bond(conn, p.id, nid, "companion", tick.get_tick(conn), reason="test")
    rng = random.Random(1)
    dest = ascension._generate_layer(conn, rng, 1, 5)
    state.set(conn, ascension.KEY, "1")
    old = p.location_id
    entities.move_player(conn, p.id, dest)
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (old, nid))     # è rimasto nel mondo di sotto
    out = heaven_bonds.on_ascend(conn, _p(conn), 1)
    assert out and heaven_bonds.get(conn)["queue"]
    conn.execute("UPDATE worlds SET current_tick=current_tick+120*10;")
    out = heaven_bonds.daily(conn, tick.get_tick(conn), random.Random(3), _p(conn))
    assert out and "Ti ho seguito" in out[0]
    assert conn.execute("SELECT location_id FROM npcs WHERE id=?;", (nid,)).fetchone()["location_id"] == dest


def test_lower_world_prayers(conn):
    p = _p(conn)
    assert not lower_world.active(conn)
    state.set(conn, "world_layer", "1")
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    for d in range(10):
        lower_world.daily(conn, (20 + d) * 120, random.Random(d), p)
    g = lower_world.get(conn)
    assert g["prayers"]
    n = len(g["prayers"])
    out = lower_world.answer(conn, p, "1")
    assert "Fede" in out or "spirito" in out
    assert "Fede +2" in lower_world.sermon(conn, p)
    m = menus.build(conn, p, "sotto")
    assert m["sections"]


def test_soul_roam_and_meditation(conn):
    p = _p(conn)
    from engine.systems import spirit
    spirit.restore_full(conn, p.id)
    out = soul_roam.roam(conn, p)
    assert "L'anima" in out or "anima" in out
    assert "Meditazione della mente" in soul_roam.meditate(conn, p, "mente")
    assert "già fatta" in soul_roam.meditate(conn, p, "mente")
    d = soul_roam.get(conn)
    d["mind"], d["mind_day"] = 9, -1
    soul_roam._save(conn, d)
    out = soul_roam.meditate(conn, p, "mente")
    assert "NOTA DEL TAO" in out and "Il Primo Respiro" in soul_roam.notes_text(conn)
    d = soul_roam.get(conn); d["body"] = 9; soul_roam._save(conn, d)
    from engine.systems import attributes
    e0 = attributes.earned(conn, p.id)
    soul_roam.meditate(conn, p, "corpo")
    assert attributes.earned(conn, p.id) == e0 + 1


def test_mount(conn):
    from engine.systems import beasts
    p = _p(conn)
    assert "Non hai bestie" in mounts.mount(conn, p, "")
    nid = npc_factory.spawn(conn, random.Random(4), archetype="vagabondo", location_id=p.location_id, tier=4)
    conn.execute("UPDATE npcs SET kind='beast' WHERE id=?;", (nid,))
    beasts.ensure_table(conn)
    beasts.traits(conn, nid, random.Random(1))
    bonds.add_bond(conn, p.id, nid, "beast", tick.get_tick(conn), reason="test")
    out = mounts.mount(conn, p, "")
    assert "Monti" in out and mounts.mounted(conn, p.id)
    assert mounts.bonus(conn, p.id)["atk"] > 0
    assert "Scendi" in mounts.dismount(conn, p)


def test_tower(conn):
    p = _p(conn)
    out = tower.challenge(conn, p)
    assert "1° piano" in out
    g = tower.get(conn)["guardian"]
    assert g
    res = tower.on_duel(conn, p, g, "risparmiato")
    assert "conquistato il 1° piano" in res[0] and tower.get(conn)["floor"] == 1
    assert "lavagna" in tower.describe(conn, p)
