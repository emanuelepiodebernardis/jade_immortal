"""Eventi mondiali: comparsa invasione, difesa (respinta) e scadenza (conseguenze)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick as tickmod
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, world_events, reputation, sects


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "we.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=25))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _spawn_event(conn):
    player = entities.get_player(conn)
    obs = []
    # forza la comparsa
    n = world_events.maybe_spawn(conn, 10, random.Random(3), player, obs)
    return n, obs


def test_invasion_spawns_with_wave(conn):
    n, obs = _spawn_event(conn)
    assert n == 1
    ev = world_events.active_event(conn)
    assert ev is not None
    creatures = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE event_id=? AND status='alive' AND kind<>'human';",
        (ev["id"],)).fetchone()["c"]
    assert creatures == ev["wave_total"] >= 3
    assert any("Usa 'events'" in o for o in obs)


def test_only_one_active_event(conn):
    _spawn_event(conn)
    player = entities.get_player(conn)
    again = world_events.maybe_spawn(conn, 11, random.Random(4), player, [])
    assert again == 0


def test_defending_repels_and_grants_fame(conn):
    _spawn_event(conn)
    ev = world_events.active_event(conn)
    player = entities.get_player(conn)
    fame_before = reputation.get(conn)["fame"]
    # "uccidi" tutta l'ondata, segnalando ogni morte
    invaders = conn.execute("SELECT id FROM npcs WHERE event_id=? AND status='alive';", (ev["id"],)).fetchall()
    last = None
    for inv in invaders:
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (inv["id"],))
        last = world_events.on_creature_killed(conn, inv["id"], 12, player)
    assert world_events.active_event(conn) is None        # non più attiva
    assert conn.execute("SELECT status FROM world_events WHERE id=?;", (ev["id"],)).fetchone()["status"] == "repelled"
    assert "respinto" in (last or "").lower()
    assert reputation.get(conn)["fame"] > fame_before     # eroismo pubblico


def test_ignoring_invasion_has_consequences(conn):
    _spawn_event(conn)
    ev = world_events.active_event(conn)
    loc = ev["location_id"]
    alive_before = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='human' AND status='alive';",
        (loc,)).fetchone()["c"]
    danger_before = conn.execute("SELECT danger_level FROM locations WHERE id=?;", (loc,)).fetchone()["danger_level"]
    # supera la scadenza senza difendere
    obs = []
    world_events.resolve_overdue(conn, ev["deadline_tick"] + 1, random.Random(5), obs)
    assert conn.execute("SELECT status FROM world_events WHERE id=?;", (ev["id"],)).fetchone()["status"] == "lost"
    alive_after = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind='human' AND status='alive';",
        (loc,)).fetchone()["c"]
    danger_after = conn.execute("SELECT danger_level FROM locations WHERE id=?;", (loc,)).fetchone()["danger_level"]
    assert alive_after < alive_before          # alcuni abitanti periti
    assert danger_after >= danger_before        # luogo più pericoloso
    assert any("non è stata respinta" in o for o in obs)


def test_invaders_are_absorbable_creatures(conn):
    _spawn_event(conn)
    ev = world_events.active_event(conn)
    # gli invasori sono creature (kind != human) -> assorbibili come le altre
    kinds = {r["kind"] for r in conn.execute(
        "SELECT DISTINCT kind FROM npcs WHERE event_id=?;", (ev["id"],))}
    assert kinds and "human" not in kinds


def test_killing_invaders_gives_no_infamy(conn):
    from engine.cli import loop
    _spawn_event(conn)
    ev = world_events.active_event(conn)
    loc = ev["location_id"]
    # porta il player sul posto e rendilo forte
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (loc,))
    t8 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (t8,))
    inf_before = reputation.get(conn)["infamy"]
    for _ in range(20):
        loop.dispatch(conn, "defend")
        if world_events.active_event(conn) is None:
            break
    # respingere un'invasione è eroico: nessuna infamia per le creature abbattute
    assert reputation.get(conn)["infamy"] == inf_before
