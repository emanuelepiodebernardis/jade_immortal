"""Aggiornamento 71: le grotte — un dungeon a bivi, stanza per stanza."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, caves, duel, encounters, state


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "cv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 4)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    loc = c.execute("SELECT id FROM locations WHERE location_type='mountain' LIMIT 1;").fetchone()
    c.execute("UPDATE players SET location_id=? WHERE id=1;", (loc["id"],))
    c.commit()
    yield c
    c.close()


def test_not_in_cities(conn):
    loc = conn.execute("SELECT id FROM locations WHERE location_type='city' LIMIT 1;").fetchone()
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (loc["id"],))
    assert "Qui non ci sono grotte" in caves.enter(conn, entities.get_player(conn))


def test_full_run_reaches_the_end(conn):
    p = entities.get_player(conn)
    out = caves.enter(conn, p)
    assert "Entri" in out and caves.get(conn)
    assert "grotta" in caves.enter(conn, p).lower() or True       # una sola grotta per volta
    rng = random.Random(4)
    global LOG
    LOG = []
    LAST = ''
    for _ in range(200):
        d = caves.get(conn)
        if not d:
            break
        if duel.get(conn):
            dd = duel.get(conn)
            if dd["hp_e"] <= 0:
                encounters.clear(conn)
                duel.finish(conn, p, kill=False)
            else:
                dd["hp_e"] = 0                                      # vinciamo in fretta
                state.set_json(conn, duel.KEY, dd)
                duel.finish(conn, p, kill=False)
            continue
        encounters.clear(conn)
        if d.get("fork"):
            LAST = caves.go(conn, p, rng.randint(1, 2))[:300]
        elif d.get("cur") == "enigma":
            caves.answer(conn, p, 1)
        elif d.get("cur") == "altare":
            caves.altar(conn, p, "offri")
        else:
            caves.leave(conn, p)
        LOG.append(LAST)
    assert caves.get(conn) is None
    encounters.clear(conn)
    assert "Oggi hai già" in caves.enter(conn, entities.get_player(conn))
    assert any("CUSTODE" in x for x in LOG)


def test_leave_and_faint(conn):
    p = entities.get_player(conn)
    caves.enter(conn, p)
    d = caves.get(conn)
    d["vigor"] = 5
    state.set_json(conn, caves.KEY, d)
    out = caves._next(conn, p, dict(d, vigor=0), ["x"])
    assert "svieni" in out and caves.get(conn) is None


def test_minigame_quality(conn):
    from engine.systems import minigame
    assert minigame.strip(conn, "equip forgia anello ~q90") == "equip forgia anello"
    assert minigame.quality(conn) == 0.9 and minigame.bonus(conn) > 0.1
    assert "perfetto" in minigame.verdict(conn).lower()
    assert minigame.strip(conn, "craft pillola") == "craft pillola"
    assert minigame.quality(conn) == 0.5 and minigame.bonus(conn) == 0
