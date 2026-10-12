"""Costituzioni, cuore del Dao e tossine, prodigi, uova, incarichi, tribolazioni del fulmine, qualità di vita."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, constitutions, dao_heart, prodigies, beast_eggs, npc_quests, heaven_trib,
                            qol, state, items, cave_abode, sects, beasts, bonds, professions, lifespan,
                            encounters, npc_factory, combat_states, relations)
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "q.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=25))
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


def _wild(conn):
    return conn.execute("SELECT id FROM locations WHERE location_type='mountain' LIMIT 1;").fetchone()["id"]


# ---------- costituzioni ----------

def test_constitution_birth_awaken_and_effects(conn):
    assert constitutions.roll_at_birth(conn, random.Random(1), "mortale", forced=True)
    c = constitutions.get(conn)
    assert c and c["stage"] == 0
    constitutions.grant(conn, "caos")
    m0, _ = constitutions.cultivation_mult(conn)
    constitutions.awaken(conn, "test")
    m1, _ = constitutions.cultivation_mult(conn)
    assert m1 > m0 > 1.0 and constitutions.bt_bonus(conn) < 0


def test_yin_veins_curse_and_cure(conn):
    constitutions.grant(conn, "vene_yin")
    assert lifespan.max_years(conn, 1) == 20
    conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
                 "VALUES ('player', 1, 'fuoco', 60, 60, 1) ON CONFLICT(character_type, character_id, dao_key) "
                 "DO UPDATE SET comprehension=60;")
    out = constitutions.daily(conn, 0, random.Random(1), _p(conn))
    assert any("GUARITO" in x for x in out) and lifespan.max_years(conn, 1) > 20


def test_broken_meridians_trash_to_genius(conn):
    constitutions.grant(conn, "spezzati")
    assert constitutions.cultivation_mult(conn)[0] == 0.5
    constitutions.awaken(conn, "test")
    assert constitutions.cultivation_mult(conn)[0] >= 2.0


# ---------- cuore del Dao e tossine ----------

def test_heart_and_qi_deviation(conn):
    assert dao_heart.heart(conn) == 60
    dao_heart.adjust(conn, -60)
    hit = any(dao_heart.on_cultivate(conn, 0, random.Random(s), _p(conn)) for s in range(80))
    assert hit and state.get_int(conn, "qi_deviations") >= 1
    assert dao_heart.breakthrough_bonus(conn) < 0


def test_pill_toxins_slow_and_purify(conn):
    iid = items.create_item(conn, "Pillola X", "pillola", "comune", "", {"cultivation_progress": 1.0})
    for _ in range(4):
        items.grant(conn, "player", 1, iid)
        items.use_item(conn, 0, random.Random(1), 1, "Pillola X")
    assert dao_heart.toxin(conn) >= 60
    assert dao_heart.cultivation_mult(conn)[0] < 0.6
    dao_heart.purify(conn, 200)
    assert dao_heart.toxin(conn) == 0
    constitutions.grant(conn, "veleno")
    assert dao_heart.on_pill(conn, 1, 1.0) == [] and dao_heart.toxin(conn) == 0


# ---------- prodigi ----------

def test_prodigies_grow_and_report(conn):
    ids = prodigies.roster(conn)
    assert ids
    before = {i: cultivation.realm_tier(conn, "npc", i) * 10 + cultivation.stage_of(conn, "npc", i) for i in ids}
    out = []
    for d in range(60):
        out += prodigies.daily(conn, d * 120, random.Random(d), _p(conn))
    after = {i: cultivation.realm_tier(conn, "npc", i) * 10 + cultivation.stage_of(conn, "npc", i)
             for i in ids if prodigies._alive(conn, i)}
    assert any(after[i] > before[i] for i in after)
    assert any("Voci" in x or "superato" in x or "Cronache" in x for x in out)
    assert "PRODIGI" in prodigies.describe(conn, _p(conn))


# ---------- uova e allevamento ----------

def test_eggs_incubate_and_hatch(conn):
    entities.move_player(conn, 1, _wild(conn))
    spec = {"species": "Fenice", "rarity": "leggendaria", "elements": ["fuoco"], "ability": "rinascita"}
    assert "dimora" in beast_eggs.incubate(conn, 1, spec)[0]
    sects.grant_resource(conn, "pietre_spirituali", 5000, 1)
    cave_abode.claim(conn, _p(conn))
    cave_abode.upgrade(conn, _p(conn), "stalla")
    out = beast_eggs.incubate(conn, 1, spec)
    assert "schiuderà" in out[0]
    msgs = beast_eggs.daily(conn, 120 * 30, random.Random(1), _p(conn))
    assert any("schiude" in m for m in msgs)
    assert beasts.pets(conn, 1)


def test_breeding_makes_hybrid(conn):
    entities.move_player(conn, 1, _wild(conn))
    sects.grant_resource(conn, "pietre_spirituali", 5000, 1)
    cave_abode.claim(conn, _p(conn))
    cave_abode.upgrade(conn, _p(conn), "stalla")
    state.set(conn, "profession", "domatore")
    state.set(conn, "profession_xp", "100000")
    for sp in ("Fenice", "Drago delle Nubi"):
        s = next(x for x in beasts.RARE_SPECIES if x[0] == sp)
        nid, _ = beasts.spawn_rare(conn, random.Random(1), _p(conn), s)
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (_p(conn).location_id, nid))
        bonds.add_bond(conn, 1, nid, "beast", 0)
    out = beast_eggs.breed(conn, _p(conn), "Fenice Drago")
    assert "Fenice-Drago" in out or "Drago-Fenice" in out
    assert beast_eggs.eggs(conn)[0]["rarity"] == "ibrida"


# ---------- incarichi ----------

def test_quest_chain_vendetta(conn):
    p = _p(conn)
    nid = npc_factory.spawn(conn, random.Random(3), archetype="anziano", location_id=p.location_id, tier=1)
    relations.adjust(conn, nid, 40, 0, 1)
    assert "incarico" in npc_quests.describe_offers(conn, p)
    offers = npc_quests._offers_here(conn, p)
    out = npc_quests.accept(conn, p, offers.index(nid) + 1)
    assert "passo 1" in out
    q = npc_quests.active(conn)[0]
    steps = q["chain"]
    for _ in range(steps):
        q = npc_quests.active(conn)[0]
        if q["kind"] == "vendetta":
            conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (q["target"],))
        elif q["kind"] in ("scorta", "consegna"):
            entities.move_player(conn, 1, q["dest"])
        elif q["kind"] == "recupero":
            npc_quests.mark_done(conn, q["id"])
        else:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (_p(conn).location_id, q["giver"]))
            professions.give(conn, 1, "erbe", 50)
            npc_quests.deliver(conn, _p(conn))
            continue
        npc_quests.check(conn, _p(conn))
    assert state.get_int(conn, "chains_done") == 1
    assert not npc_quests.active(conn)


# ---------- tribolazioni del fulmine ----------

def test_heaven_tribulation_grows_and_absorbs(conn):
    p = _p(conn)
    assert heaven_trib.on_realm_up(conn, 0, random.Random(1), p, 2) == []
    out = heaven_trib.on_realm_up(conn, 0, random.Random(1), p, 3)
    assert "1ª" in out[0] and heaven_trib.count(conn) == 1
    b1, p1 = heaven_trib.preview(conn, 1, 4)
    conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
                 "VALUES ('player', 1, 'fulmine', 60, 400, 1) ON CONFLICT(character_type, character_id, dao_key) "
                 "DO UPDATE SET comprehension=400;")
    out = heaven_trib.on_realm_up(conn, 0, random.Random(2), p, 4)
    b2, p2 = heaven_trib.preview(conn, 1, 4)
    assert b2 > b1 and p2 > p1
    assert heaven_trib.charges(conn) > 0
    enemy = npc_factory.spawn(conn, random.Random(4), archetype="vagabondo", location_id=p.location_id, tier=1)
    c0 = heaven_trib.charges(conn)
    fx = combat_states.FightCtx(conn, 1, enemy, "Tu", "X", 100, 100, 10, 10)
    assert heaven_trib.charges(conn) == c0 - 1 and any("FULMINE" in x for x in fx.lines_intro)


# ---------- qualità di vita ----------

def test_save_load_map_codex_tutorial(conn):
    p = _p(conn)
    assert "salvata" in qol.save(conn, "prova")
    state.set(conn, "marcatore", "1")
    assert "ricaricato" in qol.load(conn, "prova")
    assert state.get(conn, "marcatore") is None
    assert "prova" in qol.list_saves()
    assert "@" in qol.map_text(conn, p)
    ex = entities.get_exits(conn, p.location_id)
    entities.move_player(conn, 1, list(ex.values())[0])
    assert "CODEX" in qol.codex(conn, _p(conn))
    assert "TUTORIAL" in qol.tutorial(conn, _p(conn))
    assert "\x1b[" in qol.colorize("⚠ attenzione")
