"""Vie delle sette, Grande Assemblea, giuramenti, radici spirituali, metodi, aste, archi del mondo."""
from __future__ import annotations

import random
from itertools import combinations
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, encounters, state, alignment, assembly, oaths, spirit_roots,
                            gongfa, auction, world_arcs, npc_factory, sects, relations, reputation,
                            bonds, karma, cult_mods)
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "w2.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=3, static_npc_count=20))
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


def _friend(conn, score, tier=1):
    rng = random.Random(score)
    nid = npc_factory.spawn(conn, rng, archetype="vagabondo", location_id=_p(conn).location_id, tier=tier)
    relations.adjust(conn, nid, score, tick.get_tick(conn), 1)
    return entities.get_npc(conn, nid)


# ---------- vie delle sette ----------

def test_alignments_assigned_and_orthodox_refuses_infamous(conn):
    alignment.ensure(conn)
    als = [r["alignment"] for r in conn.execute("SELECT alignment FROM factions;")]
    assert set(als) >= {"ortodossa", "demoniaca"}
    fid = conn.execute("SELECT id FROM factions WHERE alignment='ortodossa' LIMIT 1;").fetchone()["id"]
    assert alignment.can_join(conn, 1, fid)[0]
    reputation.adjust(conn, 1, infamy=200)
    assert not alignment.can_join(conn, 1, fid)[0]
    dem = conn.execute("SELECT id FROM factions WHERE alignment='demoniaca' LIMIT 1;").fetchone()["id"]
    assert alignment.can_join(conn, 1, dem)[0]


def test_demon_envoy_scene(conn):
    alignment.ensure(conn)
    reputation.adjust(conn, 1, infamy=80)
    out = alignment.daily(conn, 120 * 40, random.Random(1), _p(conn))
    assert out and encounters.pending(conn)["key"] == "emissario_demoniaco"


# ---------- Grande Assemblea ----------

def test_assembly_full_run(conn):
    out = assembly.daily(conn, 120 * 60, random.Random(1), _p(conn))
    a = assembly.current(conn) or state.get_json(conn, "assembly")
    assert out and a
    tick.advance_tick(conn, 120 * 60 - tick.get_tick(conn))
    entities.move_player(conn, 1, a["loc"])
    _set_tier(conn, 6)
    assert "registro" in assembly.register(conn, _p(conn))
    for _ in range(3):
        if assembly.current(conn)["done"]:
            break
        assembly.fight(conn, _p(conn), 2)
    a = assembly.current(conn)
    assert a["done"] and a.get("result")


# ---------- giuramenti ----------

def test_sworn_brotherhood_and_betrayal(conn):
    weak = _friend(conn, 20)
    assert "rapporto" in oaths.swear(conn, 0, _p(conn), weak)
    bro = _friend(conn, 90)
    assert "FRATELLO GIURATO" in oaths.swear(conn, 0, _p(conn), bro)
    assert any(a["intro"] for a in oaths.combat_allies(conn, 1, -1))
    k0 = karma.get_karma(conn, "player", 1)
    lines = oaths.on_kill(conn, 0, _p(conn), bro.id)
    assert lines and karma.get_karma(conn, "player", 1) < k0
    assert "Spergiuro" in state.titles(conn)


def test_sworn_call_and_request(conn):
    bro = _friend(conn, 90)
    oaths.swear(conn, 0, _p(conn), bro)
    other = conn.execute("SELECT id FROM locations WHERE id!=? LIMIT 1;", (_p(conn).location_id,)).fetchone()["id"]
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (other, bro.id))
    assert "accanto a te" in oaths.call(conn, 0, _p(conn), bro.name)
    assert "da poco" in oaths.call(conn, 0, _p(conn), bro.name)
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (other, bro.id))
    msgs = []
    for d in range(30, 200):
        msgs = oaths.daily(conn, d * 120, random.Random(d), _p(conn))
        if state.get_json(conn, "sworn_request"):
            break
    req = state.get_json(conn, "sworn_request")
    assert req
    entities.move_player(conn, 1, req["loc"])
    assert "giuramento" in (oaths.on_arrival(conn, _p(conn)) or "")


def test_dao_partner_dual_cultivation(conn):
    p = _friend(conn, 95)
    assert "COMPAGNI DEL DAO" in oaths.propose(conn, 0, _p(conn), p)
    m, lbl = bonds.dao_partner_mult(conn, 1, _p(conn).location_id)
    assert m > 1.2 and "doppia" in lbl
    total, labels = cult_mods.cultivation_mult(conn, 1, _p(conn).location_id)
    assert any("doppia" in x for x in labels)


# ---------- radici spirituali ----------

def test_every_root_combination_has_effects():
    els = spirit_roots.ELEMENTS
    n = 0
    for k in range(2, len(els) + 1):
        for combo in combinations(els, k):
            roots = {e: 60.0 for e in combo}
            cs = spirit_roots.combinations_of(roots)
            assert cs, combo
            n += 1
    assert n == 2 ** 9 - 1 - 9
    # le combinazioni crescono con i punteggi, senza tetto
    lo = spirit_roots._totals({e: 50.0 for e in spirit_roots.CYCLE})["cult"]
    hi = spirit_roots._totals({e: 5000.0 for e in spirit_roots.CYCLE})["cult"]
    assert hi > lo * 2
    assert spirit_roots.grade_index(10 ** 6) > spirit_roots.grade_index(10 ** 4) > 6


def test_roots_shown_and_used(conn):
    out = spirit_roots.describe(conn, _p(conn))
    assert "RADICI" in out
    roots = spirit_roots.get(conn, "player", 1)
    assert roots
    spirit_roots.add(conn, "player", 1, "fuoco", 500)
    assert "Sangue della Fenice" in " ".join(spirit_roots.talents_of(spirit_roots.get(conn, "player", 1)))
    assert spirit_roots.dao_mult(conn, "player", 1, "fuoco") > 3
    prof = spirit_roots.combat_profile(conn, "player", 1)
    assert any(p[0] == "ustione" for p in prof["procs"])


def test_devourer_feeds_on_victim_roots(tmp_path, monkeypatch):
    p = tmp_path / "dv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(2))
    before = dict(spirit_roots.get(c, "player", 1))
    rng = random.Random(3)
    for i in range(5):
        nid = npc_factory.spawn(c, rng, archetype="discepolo", location_id=entities.get_player(c).location_id,
                                tier=3)
        line = spirit_roots.devour(c, 1, nid)
        assert line and "radici" in line
    after = spirit_roots.get(c, "player", 1)
    assert sum(after.values()) > sum(before.values())
    c.close()


# ---------- metodi di coltivazione ----------

def test_gongfa_learn_and_multiplier(conn):
    m = gongfa.generate(random.Random(1), 2, "fuoco")
    assert "Impari" in gongfa.learn(conn, 1, m)
    assert gongfa.active(conn, 1)["name"] == m["name"]
    mult, lbl = gongfa.cultivation_mult(conn, 1)
    assert mult > 1.0 and lbl
    big = gongfa.generate(random.Random(2), 40)
    gongfa.learn(conn, 1, big)
    assert "regge" in gongfa.command(conn, _p(conn), "pratica 2")


# ---------- aste ----------

def test_auction_bidding(conn):
    from engine.systems import sects as _s
    msgs = auction.daily(conn, 120 * 20, random.Random(4), _p(conn))
    a = auction.current(conn) or state.get_json(conn, "auction")
    assert msgs and len(a["lots"]) == 4
    tick.advance_tick(conn, 120 * 20 - tick.get_tick(conn))
    entities.move_player(conn, 1, a["loc"])
    _s.grant_resource(conn, "pietre_spirituali", 100000, 1)
    low = a["lots"][0]["current"] + max(10, a["lots"][0]["value"] // 20)
    out = auction.bid(conn, _p(conn), 1, low)
    assert "rilancia" in out or "Aggiudicato" in out
    if "rilancia" in out:
        out = auction.bid(conn, _p(conn), 1, 50000)
    assert "Aggiudicato" in out
    assert auction.current(conn)["lots"][0]["sold"] == "te"


# ---------- archi del mondo ----------

def test_world_arc_triggers_at_tier(conn):
    state.set(conn, "story_chapter", "99")     # storia d'origine conclusa
    assert world_arcs.maybe_advance(conn, _p(conn)) is None
    _set_tier(conn, 3)
    out = world_arcs.maybe_advance(conn, _p(conn))
    assert out and "Guerra" in out
    loop.dispatch(conn, "1", allow_nl=False)
    assert world_arcs.progress(conn)["guerra"] == 1
    assert any("Guerra" in g for g in world_arcs.goals(conn))


# ---------- Trasmigratore col Sistema ----------

def test_system_transmigrator(tmp_path, monkeypatch):
    import random as _r
    from engine import db as _db
    from engine.generators.world_gen import generate as _gen, WorldGenConfig as _W
    from engine.systems import character as _ch, system_quest, storyline
    from engine.core import entities as _e
    p = tmp_path / "s.db"
    monkeypatch.setattr(_db, "DB_PATH", p)
    _db.init_db(p)
    c = _db.connect(p)
    _gen(c, _W(seed=3, factions=3, static_npc_count=10))
    _ch.apply_origin(c, "trasmigratore", _r.Random(1))
    pl = _e.get_player(c)
    assert system_quest.active(c)
    assert "PANNELLO" in system_quest.describe(c, pl)
    d = system_quest.today(c, 1)
    assert len(d["quests"]) == 3
    # completa artificialmente le missioni spostando la base
    for q in d["quests"]:
        q["start"] -= q["need"]
    from engine.systems import state as _s
    _s.set_json(c, "sys_day", d)
    out = system_quest.claim(c, pl)
    assert "+" in out and system_quest.points(c) > 0
    _s.set(c, "sys_points", "1000")
    assert "Acquisto" in system_quest.buy(c, pl, 1)
    assert "Acquisto" in system_quest.buy(c, pl, 5)
    assert storyline.ARCS["trasmigratore"]["chapters"]
    c.close()


def test_system_inactive_for_other_origins(conn):
    from engine.systems import system_quest
    assert not system_quest.active(conn)
