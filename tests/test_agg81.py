"""Aggiornamento 81: azioni a schermo (tessere del luogo, menu delle persone), avvisi a tre livelli."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import attention, character, npc_crafts, place_actions


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a81.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=9, factions=3, static_npc_count=25))
    character.apply_origin(c, "divoratore", random.Random(7))
    c.commit()
    yield c
    c.close()


def _labels(conn):
    return [t["label"] for t in place_actions.tiles(conn, entities.get_player(conn, 1))]


def test_devour_tile_when_bodies_lie_here(conn):
    p = entities.get_player(conn, 1)
    assert not any("Divora" in x for x in _labels(conn))
    nid = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET status='dead', location_id=?, death_tick=0 WHERE id=?;", (p.location_id, nid))
    tiles = place_actions.tiles(conn, p)
    t = next(t for t in tiles if "Divora" in t["label"])
    assert t["cmd"] == "absorb all"


def test_relics_tile_in_ruins(conn):
    ruin = conn.execute("SELECT id FROM locations WHERE location_type='ruin' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (ruin,))
    assert any(t["cmd"] == "reperti" for t in place_actions.tiles(conn, entities.get_player(conn, 1)))


def test_master_tile_and_npc_menu_extras(conn, monkeypatch):
    from contextlib import contextmanager
    from engine.web import game
    p = entities.get_player(conn, 1)
    for r in conn.execute("SELECT id FROM npcs WHERE status='alive' AND (kind='human' OR kind IS NULL);"):
        conn.execute("UPDATE npcs SET archetype='patriarca', location_id=? WHERE id=?;", (p.location_id, r["id"]))
        if npc_crafts.of_npc(conn, r["id"]):
            break
    conn.commit()
    assert any(t["cmd"].startswith("bottega ") for t in place_actions.tiles(conn, p))

    @contextmanager
    def tx(db_path=None):
        yield conn
    monkeypatch.setattr(game, "transaction", tx)
    snap = game.state_snapshot()
    extras = [x[1] for n in snap["presenti"] for x in n.get("extra", [])]
    assert "Bottega" in extras and "Saluta" in extras
    assert "livelli" in snap


def test_three_levels():
    lst = [{"palace": "via", "tab": "dao", "hot": True, "prio": 1},
           {"palace": "oggi", "tab": "", "hot": False, "prio": 3},
           {"palace": "mondo", "tab": "mappa", "hot": False, "prio": 7}]
    lv = attention.levels(lst)
    assert lv["via"] == 2 and lv["via:dao"] == 2 and lv["oggi"] == 1 and lv.get("mondo", 0) == 0
    assert "_livelli" not in attention.badges(lst)
