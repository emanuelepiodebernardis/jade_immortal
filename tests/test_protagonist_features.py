"""Maestro nell'anello, spazio interiore, cloni, elementi celesti, famiglia, senso divino, marionette e tesori,
retaggio spezzato, Gu, battaglie dell'anima e bandiera."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, mentor_ring, inner_space, clones, celestial_elements, family, divine_sense,
                            puppets, lost_legacy, gu, soul_war, state, professions, sects, encounters, npc_factory,
                            combat_states, rebirth, spirit as spmod)
from engine.simulation import cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "pf.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=7, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _set_tier(conn, tier):
    rid = cultivation.ensure_realm(conn, tier)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


def _fx(conn):
    e = npc_factory.spawn(conn, random.Random(9), archetype="vagabondo", location_id=_p(conn).location_id, tier=1)
    return combat_states.FightCtx(conn, 1, e, "Tu", "X", 100, 100, 10, 10)


def test_mentor_ring_feed_lend_and_traitor(conn):
    mentor_ring.awaken(conn, random.Random(1))
    assert mentor_ring.level(conn) == 1
    professions.give(conn, 1, "nuclei", 200)
    out = mentor_ring.feed(conn, _p(conn), "200")
    assert mentor_ring.level(conn) >= 6 and "traditore" in out
    assert mentor_ring.cultivation_mult(conn)[0] > 1.2
    assert "Lascia" in mentor_ring.lend(conn, _p(conn))
    fx = _fx(conn)
    assert any("prende il controllo" in x for x in fx.lines_intro)
    d = mentor_ring.get(conn)
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (d["traitor"],))
    out = mentor_ring.daily(conn, 0, random.Random(1), _p(conn))
    assert any("eredità" in x for x in out)


def test_inner_space_grows_herbs_and_world(conn):
    inner_space.grant(conn)
    professions.give(conn, 1, "erbe", 5)
    assert "Pianti" in inner_space.sow(conn, _p(conn), "5")
    tick.advance_tick(conn, 130)
    assert "Raccogli 15" in inner_space.harvest(conn, _p(conn))
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    for _ in range(5):
        inner_space.expand(conn, _p(conn))
    assert inner_space.level(conn) == 6 and inner_space.cultivation_mult(conn)[0] > 1.0


def test_clones_share_cultivation_and_save_life(conn):
    assert "quarto regno" in clones.create(conn, _p(conn))
    _set_tier(conn, 4)
    conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
                 "VALUES ('player', 1, 'anima', 60, 50, 1) ON CONFLICT(character_type, character_id, dao_key) "
                 "DO UPDATE SET comprehension=50;")
    assert "CLONE" in clones.create(conn, _p(conn))
    state.set(conn, "profession", "alchimia")
    x0 = professions.xp(conn, 1)
    clones.daily(conn, 0, random.Random(1), _p(conn))
    assert professions.xp(conn, 1) > x0
    clones.assign(conn, "esplora")
    s0 = sects.get_resource(conn, "pietre_spirituali", 1)
    clones.daily(conn, 120, random.Random(2), _p(conn))
    assert sects.get_resource(conn, "pietre_spirituali", 1) > s0
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    out = rebirth.try_phoenix(conn, _p(conn))
    assert out and "CLONE" in out and _p(conn).status == "alive" and not clones.clones(conn)


def test_celestial_element_event_and_absorb(conn):
    out = []
    for d in range(4, 200):
        out += celestial_elements.daily(conn, d * 120, random.Random(d), _p(conn))
        if celestial_elements.current_event(conn):
            break
    ev = celestial_elements.current_event(conn)
    assert ev and any("ELEMENTO CELESTE" in x for x in out)
    entities.move_player(conn, 1, ev["loc"])
    assert "guardiano" in celestial_elements.absorb(conn, _p(conn))
    celestial_elements.set_free(conn)
    msg = celestial_elements.absorb(conn, _p(conn))
    assert "Celeste" in msg
    d = celestial_elements.owned(conn)
    assert ev["el"] in d and d[ev["el"]]["power"] > 0
    fx = _fx(conn)
    assert any(src.startswith("celeste:") for _s, _c, _p2, src in fx.p.procs)


def test_family_threat_visit_and_growth(conn):
    family.create(conn, random.Random(1), _p(conn))
    d = family.get(conn)
    assert len(d["members"]) == 3
    assert "Ceni" in family.visit(conn, _p(conn))
    sects.grant_resource(conn, "pietre_spirituali", 10000, 1)
    out = family.donate(conn, _p(conn), "5000")
    assert family.get(conn)["level"] > 1
    d = family.get(conn)
    d["threat"] = {"enemy": "Qualcuno", "npc": None, "deadline": -1}
    family._save(conn, d)
    msgs = family.daily(conn, 240, random.Random(3), _p(conn))
    assert msgs


def test_divine_sense_and_concealment(conn):
    spmod.restore_full(conn, 1)
    out = divine_sense.scan(conn, _p(conn), "")
    assert "senso divino" in out
    divine_sense.toggle(conn, "on")
    assert divine_sense.concealed(conn)
    assert divine_sense.on_upset(conn, _p(conn), "Il Prepotente")


def test_puppets_and_treasures(conn):
    state.set(conn, "profession", "forgia")
    state.set(conn, "profession_xp", "100000")
    professions.give(conn, 1, "minerali", 100)
    professions.give(conn, 1, "nuclei", 20)
    professions.give(conn, 1, "nuclei_rari", 2)
    assert "Marionetta n.1" in puppets.create_puppet(conn, _p(conn))
    assert "livello 2" in puppets.upgrade_puppet(conn, _p(conn), "1")
    assert "legato" in puppets.forge_treasure(conn, _p(conn), "campana")
    sects.grant_resource(conn, "pietre_spirituali", 1000, 1)
    assert "livello 2" in puppets.feed(conn, _p(conn), "1")
    fx = _fx(conn)
    allies = puppets.combat_allies(conn, 1, fx)
    assert allies and any(src == "tesoro:campana" for _s, _c, _p2, src in fx.p.procs)


def test_lost_legacy_fragments_and_cycles(conn):
    lost_legacy.assign(conn, random.Random(4))
    assert lost_legacy.cultivation_mult(conn)[0] < 1.0
    _set_tier(conn, 2)
    out = lost_legacy.daily(conn, 0, random.Random(1), _p(conn))
    d = lost_legacy.get(conn)
    assert d["holder"] and out
    for _ in range(5):
        lost_legacy.recover(conn, 0, random.Random(1), _p(conn))
    d = lost_legacy.get(conn)
    assert d["cycle"] == 2 and lost_legacy.total(d) == 5
    assert lost_legacy.cultivation_mult(conn)[0] > 1.0


def test_gu_feed_refine_and_rewind(conn):
    gu.add(conn, 1, "luna")
    gu.add(conn, 1, "luna")
    random.seed(0)
    out = gu.refine(conn, _p(conn), "luna")
    assert "grado" in out
    sects.grant_resource(conn, "pietre_spirituali", 0, 1)
    for d in range(4):
        gu.daily(conn, d * 120, random.Random(d), _p(conn))
    assert gu.gus(conn) == []                      # morti di fame
    gu.add(conn, 1, "cicala")
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    assert "riavvolge" in rebirth.try_phoenix(conn, _p(conn))


def test_soul_flag_and_possession(conn):
    soul_war.grant_flag(conn)
    for _ in range(12):
        soul_war.on_kill(conn, 0, _p(conn), "human")
    assert soul_war.flag(conn)["souls"] == 12
    fx = _fx(conn)
    assert any("Bandiera" in x for x in fx.lines_intro)
    encounters.clear(conn)
    assert soul_war.possession_scene(conn, _p(conn), "un test", 3)
