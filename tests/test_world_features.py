"""Reami segreti, ritiro e illuminazioni, classifiche, grotta-dimora, discepoli e setta propria."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, encounters, state, secret_realms, seclusion, rankings,
                            cave_abode, own_sect, npc_factory, sects, relations, reputation, lifespan)
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "w.db"
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


def _wild(conn):
    return conn.execute("SELECT id FROM locations WHERE location_type='mountain' LIMIT 1;").fetchone()["id"]


def _stones(conn, n):
    sects.grant_resource(conn, "pietre_spirituali", n, 1)


# ---------- reami segreti ----------

def test_secret_realm_opens_and_runs_to_inheritance(conn):
    tick.advance_tick(conn, 120 * 5)
    msgs = secret_realms.daily(conn, tick.get_tick(conn), random.Random(1), _p(conn))
    r = secret_realms.current(conn)
    assert r and msgs
    assert "Nessun" not in secret_realms.describe(conn, _p(conn))
    assert "non è qui" in secret_realms.enter(conn, _p(conn)) or _p(conn).location_id == r["loc"]
    entities.move_player(conn, 1, r["loc"])
    assert "soglia" in secret_realms.enter(conn, _p(conn))
    for _ in range(r["floors"]):
        out = loop.dispatch(conn, "delve", allow_nl=False)
        assert "piano" in out or "Eredità" in out or "Prova" in out
        sc = encounters.pending(conn)
        if sc["key"].startswith("prova_cuore"):
            loop.dispatch(conn, "1", allow_nl=False)
            sc = encounters.pending(conn)
        last = len(sc["choices"])
        loop.dispatch(conn, str(last if "Eredità" not in sc["title"] else 3), allow_nl=False)
        if _p(conn).status != "alive":
            return
    assert secret_realms.run(conn) is None          # l'eredità chiude la discesa


def test_secret_realm_closes(conn):
    tick.advance_tick(conn, 120 * 5)
    secret_realms.daily(conn, tick.get_tick(conn), random.Random(1), _p(conn))
    tick.advance_tick(conn, 120 * 4)
    out = secret_realms.daily(conn, tick.get_tick(conn), random.Random(1), _p(conn))
    assert secret_realms.current(conn) is None and any("richius" in x for x in out)


# ---------- ritiro e illuminazione ----------

def test_retreat_needs_place_and_advances(conn):
    city = conn.execute("SELECT id FROM locations WHERE location_type='city' LIMIT 1;").fetchone()["id"]
    entities.move_player(conn, 1, city)
    assert "trambusto" in seclusion.retreat(conn, _p(conn), "5")
    entities.move_player(conn, 1, _wild(conn))
    age0 = lifespan.age_years(conn, 1)
    rec0 = cultivation.get_record(conn, "player", 1)
    t0 = tick.get_tick(conn)
    out = seclusion.retreat(conn, _p(conn), "10")
    assert "ritiro" in out
    assert tick.get_tick(conn) > t0
    rec = cultivation.get_record(conn, "player", 1)
    assert (rec["stage"], rec["progress"]) > (rec0["stage"], rec0["progress"])
    assert lifespan.age_years(conn, 1) > age0


def test_illumination_raises_dao(conn):
    from engine.systems import dao_training
    rows = dao_training.trainable_daos(conn, 1)
    if not rows:
        pytest.skip("nessun Dao")
    before = rows[0]["comprehension"]
    seclusion.illumination(conn, tick.get_tick(conn), random.Random(3), _p(conn), "test", rows[0]["dao_key"])
    after = dao_training.find_dao(conn, rows[0]["dao_key"], 1)["comprehension"]
    assert after > before and state.get_int(conn, "illuminations") == 1


def test_upset_win_gives_fame_and_title(conn):
    f0 = reputation.get(conn, 1)["fame"]
    seclusion.on_upset_win(conn, tick.get_tick(conn), random.Random(5), _p(conn), "Gigante", 0.5)
    assert reputation.get(conn, 1)["fame"] > f0
    assert "Sfidante dei Cieli" in state.titles(conn)


# ---------- classifiche ----------

def test_rankings_list_and_reward(conn):
    out = rankings.describe(conn, _p(conn))
    assert "CLASSIFICA DEL CIELO" in out and "◀ TU" in out
    assert "DRAGO NASCENTE" in rankings.describe(conn, _p(conn), "giovani")
    assert "SETTE" in rankings.describe(conn, _p(conn), "sette")
    _set_tier(conn, 9)
    s0 = sects.get_resource(conn, "pietre_spirituali", 1)
    msgs = rankings.daily(conn, tick.get_tick(conn), random.Random(1), _p(conn))
    rank, _ = rankings.player_rank(conn)
    assert rank >= 1
    _, total = rankings.player_rank(conn)
    if any(rank <= th and total >= max(12, th * 3) for th in rankings.THRESHOLDS):
        assert msgs and sects.get_resource(conn, "pietre_spirituali", 1) > s0
    # in un mondo affollato il primo posto vale
    for i in range(40):
        npc_factory.spawn(conn, random.Random(i), archetype="vagabondo", location_id=_wild(conn), tier=1, stage=1)
    state.delete(conn, "rank_best_cielo")
    msgs = rankings.daily(conn, tick.get_tick(conn), random.Random(1), _p(conn))
    if rankings.player_rank(conn)[0] <= 10:
        assert msgs


# ---------- grotta-dimora ----------

def test_cave_abode_claim_upgrade_produce(conn):
    entities.move_player(conn, 1, _wild(conn))
    assert "Servono" in cave_abode.claim(conn, _p(conn)) or cave_abode.get(conn)
    _stones(conn, 5000)
    assert "casa" in cave_abode.claim(conn, _p(conn)) or cave_abode.get(conn)
    assert cave_abode.is_home(conn, 1, _p(conn).location_id)
    assert "livello 1" in cave_abode.upgrade(conn, _p(conn), "erbe")
    assert "livello 1" in cave_abode.upgrade(conn, _p(conn), "qi")
    assert cave_abode.upgrade_cost("qi", 1) > cave_abode.upgrade_cost("qi", 0)
    m, _ = cave_abode.cultivation_mult(conn, 1, _p(conn).location_id)
    assert m > 1.2
    for d in range(3):
        cave_abode.daily(conn, 0, random.Random(d), _p(conn))
    assert "erbe" in cave_abode.collect(conn, _p(conn))
    other = conn.execute("SELECT id FROM locations WHERE location_type='city' LIMIT 1;").fetchone()["id"]
    entities.move_player(conn, 1, other)
    assert "dimora" in cave_abode.go_home(conn, _p(conn))
    assert cave_abode.is_home(conn, 1, _p(conn).location_id)


# ---------- discepoli e setta ----------

def _weak_npc(conn, loc, rng):
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=loc, tier=1, stage=2)
    relations.adjust(conn, nid, 60, tick.get_tick(conn), 1)
    return entities.get_npc(conn, nid)


def test_disciples_and_found_sect(conn):
    rng = random.Random(4)
    loc = _wild(conn)
    entities.move_player(conn, 1, loc)
    npc = _weak_npc(conn, loc, rng)
    assert "terzo regno" in own_sect.accept(conn, 0, _p(conn), npc)
    _set_tier(conn, 5)
    assert "DISCEPOLO" in own_sect.accept(conn, 0, _p(conn), npc)
    r0 = cultivation.stage_of(conn, "npc", npc.id) + 10 * cultivation.realm_tier(conn, "npc", npc.id)
    out = own_sect.teach(conn, tick.get_tick(conn), rng, _p(conn), npc)
    assert "Insegni" in out
    assert "già" in own_sect.teach(conn, tick.get_tick(conn), rng, _p(conn), npc)
    r1 = cultivation.stage_of(conn, "npc", npc.id) + 10 * cultivation.realm_tier(conn, "npc", npc.id)
    assert r1 > r0
    for _ in range(2):
        own_sect.accept(conn, 0, _p(conn), _weak_npc(conn, loc, rng))
    assert len(own_sect.disciples(conn, 1)) == 3
    assert "servono" in own_sect.found(conn, 0, _p(conn), "Giada").lower()
    _stones(conn, 10000)
    cave_abode.claim(conn, _p(conn))
    out = own_sect.found(conn, tick.get_tick(conn), _p(conn), "della Giada Celeste")
    assert "nasce una setta" in out
    s = own_sect.get(conn)
    assert s and len(own_sect.members(conn, s["fid"])) == 3
    # tributi e raid
    for d in range(25):
        own_sect.daily(conn, (tick.get_tick(conn) // 120 + d) * 120, random.Random(d), _p(conn))
    assert own_sect.get(conn)["treasury"] > 0
    assert "Ritiri" in own_sect.collect(conn, _p(conn))
    assert "entra nella" in own_sect.recruit(conn, 0, rng, _p(conn))
    # la setta del giocatore non compare tra quelle a cui ci si può iscrivere
    assert sects.sect_at_location(conn, loc) is None


def test_sect_raid_defend_scene(conn):
    rng = random.Random(9)
    loc = _wild(conn)
    entities.move_player(conn, 1, loc)
    _set_tier(conn, 5)
    _stones(conn, 10000)
    cave_abode.claim(conn, _p(conn))
    for _ in range(3):
        own_sect.accept(conn, 0, _p(conn), _weak_npc(conn, loc, rng))
    own_sect.found(conn, 0, _p(conn), "del Loto")
    s = own_sect.get(conn)
    s["next_raid_day"] = 0
    state.set_json(conn, own_sect.KEY, s)
    msgs = own_sect.daily(conn, 120, random.Random(1), _p(conn))
    assert any("difendi" in m for m in msgs)
    out = own_sect.defend(conn, 120, rng, _p(conn))
    assert "Assalto" in out and encounters.pending(conn)
