"""Fase 7 — Cultivation Core: regni, progresso, breakthrough (successo/fallimento/morte)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation, combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "cult.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_eight_realms_seeded(conn):
    rows = conn.execute("SELECT tier, name FROM cultivation_realms ORDER BY tier;").fetchall()
    assert [r["tier"] for r in rows] == list(range(1, 9))
    assert rows[-1]["name"] == "Immortale di Giada"


def test_player_starts_tier1_with_record(conn):
    assert cultivation.realm_tier(conn, "player", 1) == 1
    assert cultivation.get_record(conn, "player", 1) is not None


def test_npcs_have_realms_by_archetype(conn):
    # i patriarca in media a tier più alto delle guardie
    import statistics
    def avg_tier(arch):
        ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE archetype=?;", (arch,))]
        return statistics.mean(cultivation.realm_tier(conn, "npc", i) for i in ids) if ids else None
    pat = avg_tier("patriarca")
    gua = avg_tier("guardia")
    if pat is not None and gua is not None:
        assert pat > gua


def test_cultivate_increases_progress(conn):
    before = cultivation.get_record(conn, "player", 1)["progress"]
    cultivation.cultivate(conn, "player", 1, tick=0, rng=random.Random(1))
    after = cultivation.get_record(conn, "player", 1)["progress"]
    assert after > before


def test_breakthrough_not_ready_below_threshold(conn):
    res = cultivation.attempt_breakthrough(conn, "player", 1, tick=0, rng=random.Random(1))
    assert res["status"] == "not_ready"


def test_breakthrough_success_raises_tier(conn):
    # progresso abbondante -> alta probabilità di successo
    conn.execute("UPDATE cultivation_records SET progress=2.0, stage=10, dao_understanding=80 "
                 "WHERE character_type='player' AND character_id=1;")
    raised = False
    for seed in range(20):
        conn.execute("UPDATE cultivation_records SET progress=2.0, stage=10 "
                     "WHERE character_type='player' AND character_id=1;")
        # riporta al tier 1 per ogni prova
        t1 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=1;").fetchone()["id"]
        conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (t1,))
        conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (t1,))
        res = cultivation.attempt_breakthrough(conn, "player", 1, tick=seed, rng=random.Random(seed))
        if res["status"] == "success":
            assert cultivation.realm_tier(conn, "player", 1) == 2
            raised = True
            break
    assert raised


def test_breakthrough_can_kill(conn):
    """A tier alto, i fallimenti possono causare deviazione del qi e morte."""
    t7 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=7;").fetchone()["id"]
    died = False
    for seed in range(300):
        conn.execute("UPDATE players SET status='alive', realm_id=? WHERE id=1;", (t7,))
        conn.execute("UPDATE cultivation_records SET progress=1.0, stage=10, realm_id=?, dao_understanding=0 "
                     "WHERE character_type='player' AND character_id=1;", (t7,))
        res = cultivation.attempt_breakthrough(conn, "player", 1, tick=seed, rng=random.Random(seed))
        if res["status"] == "death":
            assert conn.execute("SELECT status FROM players WHERE id=1;").fetchone()["status"] == "dead"
            died = True
            break
    assert died, "a tier 7 una morte da breakthrough dovrebbe poter accadere"


def test_realm_boosts_combat_power(conn):
    base = combat.combat_power(conn, "player", 1)["attack"]
    t5 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=5;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (t5,))
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base * 2  # tier5 -> fattore 1+4*0.4 = 2.6


def test_breakthrough_events_are_traceable(conn):
    conn.execute("UPDATE cultivation_records SET progress=2.0, stage=10, dao_understanding=80 "
                 "WHERE character_type='player' AND character_id=1;")
    cultivation.attempt_breakthrough(conn, "player", 1, tick=1, rng=random.Random(0))
    evs = conn.execute(
        "SELECT id FROM events WHERE event_type IN "
        "('breakthrough','breakthrough_failure','death');").fetchall()
    assert len(evs) >= 1
    for e in evs:
        np = conn.execute("SELECT COUNT(*) c FROM event_participants WHERE event_id=?;", (e["id"],)).fetchone()["c"]
        nc = conn.execute("SELECT COUNT(*) c FROM consequences WHERE event_id=?;", (e["id"],)).fetchone()["c"]
        assert np >= 1 and nc >= 1


# ---- Sotto-livelli (10 strati per regno) ----

def test_cultivate_advances_stage_and_resets_experience(conn):
    conn.execute("UPDATE cultivation_records SET stage=1, progress=0.95 "
                 "WHERE character_type='player' AND character_id=1;")
    import random as _r
    res = cultivation.cultivate(conn, "player", 1, 0, _r.Random(1), amount=0.2)
    assert res["stage"] == 2           # ha superato lo strato
    assert res["progress"] < 1.0       # esperienza ripartita
    assert res["stage_up"] is True


def test_breakthrough_blocked_before_stage_ten(conn):
    conn.execute("UPDATE cultivation_records SET stage=5, progress=1.0 "
                 "WHERE character_type='player' AND character_id=1;")
    import random as _r
    res = cultivation.attempt_breakthrough(conn, "player", 1, 0, _r.Random(1))
    assert res["status"] == "not_ready"


def test_breakthrough_resets_to_stage_one(conn):
    conn.execute("UPDATE cultivation_records SET stage=10, progress=2.0, dao_understanding=80 "
                 "WHERE character_type='player' AND character_id=1;")
    import random as _r
    for seed in range(40):
        r = cultivation.attempt_breakthrough(conn, "player", 1, 0, _r.Random(seed))
        if r["status"] == "success":
            assert cultivation.stage_of(conn, "player", 1) == 1
            assert cultivation.realm_tier(conn, "player", 1) == 2
            return


def test_effective_level_and_combat_scale_with_stage(conn):
    from engine.simulation import combat
    conn.execute("UPDATE cultivation_records SET stage=3 WHERE character_type='player' AND character_id=1;")
    lvl3 = cultivation.effective_level(conn, "player", 1)
    p3 = combat.combat_power(conn, "player", 1)["attack"]
    conn.execute("UPDATE cultivation_records SET stage=4 WHERE character_type='player' AND character_id=1;")
    lvl4 = cultivation.effective_level(conn, "player", 1)
    p4 = combat.combat_power(conn, "player", 1)["attack"]
    assert lvl4 == lvl3 + 1
    assert p4 > p3                     # Strato 4 è più forte dello Strato 3
