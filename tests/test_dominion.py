"""Dominio: sigillo dell'anima, servi, sette vassalle, salme e tempra dello spirito."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, dominion, npc_factory, sects, state, soul_temper, perception, items,
                            menus, feuds, bonds)
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "dom.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=11, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _strong_soul(conn, grade=12):
    xp = soul_temper.need(grade)
    state.set_json(conn, soul_temper.KEY, {"xp": xp, "g": grade})


def _npc(conn, archetype="vagabondo", seed=1, tier=1):
    nid = npc_factory.spawn(conn, random.Random(seed), archetype=archetype, location_id=_p(conn).location_id, tier=tier)
    return entities.get_npc(conn, nid)


def test_temper_raises_spirit_score_and_pool(conn):
    p = _p(conn)
    s0 = perception.spirit_score(conn, "player", p.id)
    out = soul_temper.session(conn, p)
    assert "Spirito +" in out
    _strong_soul(conn, 5)
    assert perception.spirit_score(conn, "player", p.id) > s0 + 30
    assert soul_temper.grade_name(5) == "Senso Divino Compiuto"
    assert "Cielo" in soul_temper.grade_name(14)
    tr = loop.dispatch(conn, "train", allow_nl=False)
    assert "Spirito:" in tr


def test_cannot_seal_a_stronger_soul(conn):
    v = _npc(conn, tier=4)
    ok, p, why = dominion.seal_odds(conn, _p(conn).id, v.id, True)
    assert not ok and "tempra" in why


def test_seal_a_beaten_foe_takes_goods_and_makes_a_servant(conn):
    _strong_soul(conn)
    v = _npc(conn, "anziano", 3, tier=2)
    dominion.note_defeated(conn, v.id)
    stones0 = sects.get_resource(conn, "pietre_spirituali", 1)
    out = ""
    for s in range(8):
        out = dominion.seal(conn, s, random.Random(s), _p(conn), v, True)
        if dominion.servant(conn, v.id):
            break
        state.set_json(conn, "seal_tried", {})
        from engine.systems import spirit
        spirit.restore_full(conn, 1)
        if entities.get_npc(conn, v.id).status != "alive":
            v = _npc(conn, "anziano", 30 + s, tier=2)
            dominion.note_defeated(conn, v.id)
    assert dominion.servant(conn, v.id), out
    assert sects.get_resource(conn, "pietre_spirituali", 1) > stones0
    assert "servo" in bonds.bond_kinds(conn, v.id, 1)
    # compiti, rinsaldo, menu
    first = v.name.split()[0]
    assert "scorta" in loop.dispatch(conn, f"servo {first} scorta", allow_nl=False)
    assert dominion.combat_allies(conn, 1, -1)
    txt = menus.render(conn, menus.build(conn, _p(conn), "dominio"))
    assert v.name in txt and "Sigillo" in txt
    # libero: o debito o nemesi, ma non più servo
    dominion.release(conn, _p(conn), dominion.servant(conn, v.id))
    assert not dominion.servant(conn, v.id)


def test_sealing_a_patriarch_makes_the_sect_a_vassal(conn):
    _strong_soul(conn, 30)
    f = conn.execute("SELECT id, name, leader_id FROM factions WHERE leader_id IS NOT NULL LIMIT 1;").fetchone()
    pat = entities.get_npc(conn, f["leader_id"])
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (_p(conn).location_id, pat.id))
    lines = dominion._bind(conn, 0, random.Random(1), _p(conn), pat, "sigillo", 90)
    assert f["id"] in dominion.vassal_ids(conn), lines
    assert any("VASSALLA" in ln for ln in lines)
    assert dominion.servant(conn, pat.id)["role"] == "reggente"
    for d in range(3):
        dominion.daily(conn, 120 * (d + 1), random.Random(d), _p(conn))
    assert "Riscuoti" in dominion.collect(conn, _p(conn))
    assert dominion.techniques(conn)
    s0 = sects.get_resource(conn, "pietre_spirituali", 1)
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    assert "apprendi" in dominion.learn_technique(conn, _p(conn), "1").lower()
    assert sects.get_resource(conn, "pietre_spirituali", 1) < s0 + 100000
    bonus, names = dominion.war_support(conn)
    assert bonus > 0 and f["name"] in names
    rival = dominion.targets(conn, _p(conn))[0]
    out = dominion.attack(conn, _p(conn), rival["name"])
    assert "marciano" in out
    assert "riposano" in dominion.attack(conn, _p(conn), rival["name"]) or "3 giorni" in dominion.attack(conn, _p(conn), rival["name"])
    # se il patriarca muore, il vassallaggio finisce
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (pat.id,))
    out = dominion.daily(conn, 600, random.Random(9), _p(conn))
    assert f["id"] not in dominion.vassal_ids(conn), out


def test_seal_breaks_when_the_servant_outgrows_you(conn):
    _strong_soul(conn, 3)
    v = _npc(conn, "vagabondo", 4, tier=1)
    dominion._bind(conn, 0, random.Random(1), _p(conn), v, "sigillo", 5)
    _strong_soul(conn, 0)
    npc_factory.raise_npc(conn, v.id, 40)
    out = []
    for d in range(10):
        out += dominion.daily(conn, 120 * (d + 1), random.Random(d), _p(conn))
        if not dominion.servant(conn, v.id):
            break
    assert not dominion.servant(conn, v.id)
    assert any("spezza" in ln for ln in out)


def test_salma_art_revives_the_dead_as_a_servant(conn):
    _strong_soul(conn, 6)
    v = _npc(conn, "vagabondo", 5, tier=1)
    assert "Non conosci" in dominion.revive_command(conn, _p(conn), v.name)
    iid = dominion.salma_manual(conn)
    out = items.apply_effects(conn, 0, random.Random(1), 1, {"learn_art": "salma"})
    assert dominion.art_level(conn) == 1 and out and iid
    conn.execute("UPDATE npcs SET status='dead', death_tick=0 WHERE id=?;", (v.id,))
    sects.grant_resource(conn, "pietre_spirituali", 1000, 1)
    out = dominion.revive_command(conn, _p(conn), v.name.split()[0])
    s = dominion.servant(conn, v.id)
    assert s and s["kind"] == "salma", out
    assert "salma" in dominion.set_role(conn, _p(conn), s, "lavoro").lower()
    assert "pace" in dominion.release(conn, _p(conn), s)
    assert entities.get_npc(conn, v.id).status == "dead"


def test_kin_swear_to_break_the_seal(conn):
    v = _npc(conn, "anziano", 6, tier=2)
    got = []
    for s in range(10):
        got = feuds.on_kill(conn, 0, random.Random(s), _p(conn), v, cause="sigillo")
        if got:
            break
    assert got and "sigillo" in got[0]
    f = feuds.feuds(conn)[0]
    assert f["note"] == "sigillo"
