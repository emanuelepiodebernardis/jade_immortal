"""Aggiornamento 66: la calibrazione — arene non mortali, faide della vita passata, tossine, doni, pietre."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import (character, state, sects, duel, deification_tower as tower, dao_heart, power_budget,
                            stone_qi, income, autopilot, feuds, rebirth)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a66.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(4))
    rid = cultivation.ensure_realm(c, 5)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


def test_arena_duel_loss_is_not_lethal(conn):
    p = _p(conn)
    tower.challenge(conn, p)
    d = duel.get(conn)
    assert d and d["arena"] is True
    for _ in range(200):                          # il giocatore crolla: in arena non muore
        d = duel.get(conn)
        if not d:
            break
        d["hp_p"] = 0.01
        d["hp_e"] = 1e9
        duel._save(conn, d)
        duel.act(conn, _p(conn), "1")
    assert duel.get(conn) is None
    assert _p(conn).status == "alive"
    assert tower.get(conn)["guardian"] is None


def test_past_life_feuds_fall_asleep(conn):
    feuds.ensure_table(conn)
    nid = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(feuds);")]
    vals = {"kind": "faida", "npc_id": nid, "status": "giurata", "ready_day": 0}
    vals = {k: v for k, v in vals.items() if k in cols}
    conn.execute(f"INSERT INTO feuds ({', '.join(vals)}) VALUES ({', '.join('?' * len(vals))});", tuple(vals.values()))
    p = _p(conn)
    rebirth.record_death(conn, p)
    rebirth.reincarnate(conn, random.Random(1), "mortale", None, None)
    st = conn.execute("SELECT status FROM feuds WHERE npc_id=?;", (nid,)).fetchone()["status"]
    assert st == "sopita"
    assert not feuds.feuds(conn)


def test_toxin_floor_and_cap(conn):
    state.set(conn, dao_heart.TOXIN_KEY, "1195")               # un vecchio salvataggio
    assert dao_heart.toxin(conn) == dao_heart.TOXIN_MAX
    m, _ = dao_heart.cultivation_mult(conn)
    assert m == pytest.approx(dao_heart.TOXIN_FLOOR)
    dao_heart._set_toxin(conn, 5000)
    assert float(state.get(conn, dao_heart.TOXIN_KEY)) <= dao_heart.TOXIN_MAX


def test_gifts_tail_is_continuous_and_growing(conn):
    vals = [power_budget.gifts(x) for x in (1.0, 2.0, 2.99, 3.0, 3.01, 6.0, 12.0, 24.0, 100.0)]
    assert all(b >= a for a, b in zip(vals, vals[1:]))
    assert power_budget.gifts(3.01) - power_budget.gifts(2.99) < 0.02
    assert power_budget.gifts(24.0) > power_budget.gifts(12.0) + 0.1    # un dono nuovo conta ancora
    assert power_budget.gifts(100.0) < 5.0


def test_stone_qi_absorb_costs_grow_and_progress(conn):
    p = _p(conn)
    sects.grant_resource(conn, "pietre_spirituali", 5000, p.id)
    c0 = stone_qi.cost(conn, p.id)
    assert c0 == stone_qi.BASE_COST * 5
    r0 = cultivation.get_record(conn, "player", p.id)
    before = (r0["stage"], r0["progress"])
    out = stone_qi.absorb(conn, p, 2)
    assert "sessioni" in out
    r1 = cultivation.get_record(conn, "player", p.id)
    assert (r1["stage"], r1["progress"]) > before
    assert stone_qi.done_today(conn) == 2
    assert stone_qi.cost(conn, p.id) > c0
    assert sects.get_resource(conn, "pietre_spirituali", p.id) == 5000 - c0 - stone_qi.cost(conn, p.id, 1)


def test_stone_qi_autopilot_keeps_reserve(conn):
    p = _p(conn)
    reserve = stone_qi.RESERVE_PER_TIER * 5
    sects.grant_resource(conn, "pietre_spirituali", reserve + 100, p.id)
    assert stone_qi.auto_spend(conn, p) == []                  # sopra la riserva non basta per una sessione
    sects.grant_resource(conn, "pietre_spirituali", 5000, p.id)
    out = stone_qi.auto_spend(conn, p)
    assert out and stone_qi.done_today(conn) <= stone_qi.AUTO_SESSIONS
    assert sects.get_resource(conn, "pietre_spirituali", p.id) >= reserve
    assert autopilot.config(conn)["pietre"] is False      # le pietre restano tue




def test_stone_qi_at_peak_feeds_the_dao(conn):
    from engine.systems import dao_training
    p = _p(conn)
    conn.execute("UPDATE cultivation_records SET stage=?, progress=1.0 WHERE character_type='player' AND character_id=1;",
                 (cultivation.STAGES_PER_REALM,))
    if not dao_training.trainable_daos(conn, p.id):
        conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, comprehension) "
                     "VALUES ('player', 1, 'spada', 10);")
    before = max(r["comprehension"] for r in dao_training.trainable_daos(conn, p.id))
    sects.grant_resource(conn, "pietre_spirituali", 2000, p.id)
    out = stone_qi.absorb(conn, p, 2)
    assert "Dao" in out
    after = max(r["comprehension"] for r in dao_training.trainable_daos(conn, p.id))
    assert after > before


def test_rebirth_grace_blocks_ambush_and_death(conn):
    from engine.systems import calibration as cal
    from engine.core import tick as tick_mod
    p = _p(conn)
    assert not cal.in_grace(conn)
    rebirth.record_death(conn, p)
    lines = rebirth.reincarnate(conn, random.Random(2), "mortale", None, None)
    assert any("Samsara" in ln for ln in lines)
    assert cal.in_grace(conn)
    assert not cal.ambush_ok(conn, 1, tick_mod.get_tick(conn))
    conn.execute("UPDATE game_state SET value=? WHERE key=?;", (str(-100), cal.REBIRTH_KEY))
    assert not cal.in_grace(conn)
