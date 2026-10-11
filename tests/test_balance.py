"""Bilanciamento (Aggiornamento 23): regno come scala, crescita compressa, limiti anti-esplosione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, tribulation, dao_heart, state, archrival, perception, items
from engine.simulation import combat, cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "bl.db"
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


def _tier(conn, t):
    rid = cultivation.ensure_realm(conn, t)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=1 WHERE character_type='player' "
                 "AND character_id=1;", (rid,))


def test_compression_and_amplifier_are_endless_but_slow():
    assert combat.compress(1.0) == 1.0 and combat.compress(0.5) == 0.5
    assert 1.6 < combat.compress(10) < 1.7 and 2.9 < combat.compress(1000) < 3.1
    assert combat.compress(10 ** 9) > combat.compress(10 ** 6)          # senza tetto
    assert combat.dao_amplifier(0, 3) == 1.0
    assert combat.dao_amplifier(10 ** 7, 3) > combat.dao_amplifier(10 ** 5, 3) > 1.0


def test_realm_is_the_main_scale(conn):
    a = combat.combat_power(conn, "player", 1)["attack"]
    _tier(conn, 3)
    b = combat.combat_power(conn, "player", 1)["attack"]
    assert b / a == pytest.approx(combat.REALM_STEP ** 2, rel=0.15)


def test_tribulation_bolts_are_bounded(conn):
    out = tribulation.resolve_tribulation(conn, 0, random.Random(1), 10 ** 8, 1)
    assert out["bolts"] <= 120
    assert sum(len(x) for x in out["lines"]) < 5000


def test_pills_weaker_at_high_realms(conn):
    _tier(conn, 9)
    p0 = cultivation.get_record(conn, "player", 1)["progress"]
    items.apply_effects(conn, 0, random.Random(1), 1, {"cultivation_progress": 0.5})
    gain = cultivation.get_record(conn, "player", 1)["progress"] - p0
    assert 0.03 < gain < 0.15          # al primo regno sarebbe stato 0.5 (× affinità)


def test_dao_heart_recovers(conn):
    state.set(conn, dao_heart.HEART_KEY, "0")
    for d in range(5):
        dao_heart.daily(conn, d * 120, None, _p(conn))
    assert dao_heart.heart(conn) == 15


def test_archrival_starts_at_your_height(conn):
    _tier(conn, 4)
    archrival.create(conn, random.Random(3), _p(conn))
    r = perception.strength_ratio(conn, 1, archrival.get(conn)["npc"])
    assert 0.5 < r < 1.4


def test_maintenance_prunes_old_world_events_but_keeps_yours(conn):
    from engine.systems import maintenance
    from engine.simulation import event_system as ev
    ev.log_event(conn, event_type="encounter", tick=10, location_id=None, title="vecchio", summary="vecchio",
                 participants=[ev.Participant("npc", 1, "initiator")],
                 consequences=[ev.Consequence("npc", 1, "nota", "x", resolve_tick=10)])
    ev.log_event(conn, event_type="story", tick=10, location_id=None, title="mio", summary="mio",
                 participants=[ev.Participant("player", 1, "initiator")],
                 consequences=[ev.Consequence("player", 1, "nota", "x", resolve_tick=10)])
    n = maintenance.prune(conn, 400, force=True)
    assert n >= 1
    left = {r[0] for r in conn.execute("SELECT title FROM events WHERE tick=10;")}
    assert "mio" in left and "vecchio" not in left


def test_long_run_stays_bounded(conn):
    """Regressione: 30 giorni di pilota automatico non devono far esplodere nulla."""
    from engine.systems import autopilot, cult_mods
    from engine.cli import loop
    loop.dispatch(conn, "auto imposta sfonda si", allow_nl=False)
    from engine.core import tick as _tk
    from engine.systems import encounters, captivity, state
    for _ in range(60):
        if _tk.get_tick(conn) // 120 >= 30:
            break
        autopilot.run(conn, _p(conn), 10)
        encounters.clear(conn)
        state.delete(conn, captivity.KEY)
        if _p(conn).status != "alive":
            return
    assert _tk.get_tick(conn) // 120 >= 25
    tier = cultivation.realm_tier(conn, "player", 1) or 1
    atk = combat.combat_power(conn, "player", 1)["attack"]
    assert tier <= 4
    assert atk < 32 * combat.REALM_STEP ** tier * 60           # nessuna esplosione di potenza
    assert cult_mods.cultivation_mult(conn, 1, _p(conn).location_id)[0] < 20
    assert conn.execute("SELECT COALESCE(SUM(LENGTH(text)),0) FROM pending_reports;").fetchone()[0] < 2_000_000
