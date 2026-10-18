"""Aggiornamento 65: dantian, eredi, feng shui e giardino, Immortale, filtro ricette, Gran Torneo."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import (character, state, dantian, heirs, fengshui, calibration, grand_tournament as gt,
                            cave_abode, npc_factory, bonds, sects)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a65.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 6)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


def test_dantian_shapes_score_and_auto(conn):
    assert dantian.size(conn) == 5
    a = {"key": "a", "name": "A", "tags": ["fuoco"], "cells": [(0, 0), (0, 1)]}
    b = {"key": "b", "name": "B", "tags": ["fuoco"], "cells": [(1, 0)]}
    c = {"key": "c", "name": "C", "tags": ["terra"], "cells": [(1, 1)]}
    s = dantian.score([a, b, c])
    assert s["cells"] == 4 and s["same"] == 1 and s["cycle"] >= 1 and s["atk"] > 0
    assert dantian._rotate([(0, 0), (0, 1)], 1) == [(0, 0), (1, 0)]
    out = dantian.auto(conn, 1)
    assert "dantian" in out
    assert "IL DANTIAN" in dantian.describe(conn, _p(conn))


def test_heir_candidates_and_become(conn):
    p = _p(conn)
    nid = npc_factory.spawn(conn, random.Random(1), archetype="discepolo", location_id=p.location_id, tier=4)
    bonds.add_bond(conn, p.id, nid, "disciple", tick.get_tick(conn), reason="test")
    cs = heirs.remember(conn, p)
    assert any(c["id"] == nid for c in cs)
    h = next(c for c in cs if c["id"] == nid)
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    lines = heirs.become(conn, random.Random(2), h, "Vecchio Io", "mortale", None, [{"key": "none"}])
    assert lines and "la Via continua" in lines[0]
    assert entities.get_player(conn).name == nm
    assert cultivation.realm_tier(conn, "player", 1) == 4
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()["status"] == "dead"


def test_fengshui_and_garden(conn):
    p = _p(conn)
    assert fengshui.harmony(conn, 1)["label"] == "nessuna dimora"
    state.set_json(conn, cave_abode.KEY, {"name": "Grotta", "loc": p.location_id, "wings":
                                          {"erbe": 3, "alchimia": 3, "difesa": 3, "qi": 3, "ritiro": 3}})
    h = fengshui.harmony(conn, 1)
    assert h["score"] >= 0.9 and h["mult"] > 1.15
    assert fengshui.cultivation_mult(conn, 1, p.location_id)[0] > 1.0
    assert "Semini 3" in fengshui.plant(conn, p, "erba")
    assert "non c'è ancora" in fengshui.harvest(conn, p)
    conn.execute("UPDATE worlds SET current_tick=current_tick+120*3;")
    assert fengshui.ready_count(conn) == 3
    out = fengshui.harvest(conn, p)
    assert "Raccogli 3" in out and len(fengshui.garden(conn)["plots"]) == 3       # ripiantati


def test_immortale_hides_and_blocks_saves(conn):
    from engine.cli import loop
    try:
        calibration.set_difficulty(conn, "immortale")
        assert calibration.THREAT_CHANCE == calibration.PRESETS["spietato"]["THREAT_CHANCE"]
        assert "Immortale" in loop.dispatch(conn, "salva", allow_nl=False)
    finally:
        calibration.apply(calibration.DEFAULT)


def test_recipes_filter(conn):
    from engine.systems import shops, professions
    p = _p(conn)
    state.set(conn, "profession", "alchimia")
    m1 = shops.recipes_menu(conn, p)
    state.set(conn, "recipes_only_ready", "1")
    m2 = shops.recipes_menu(conn, p)
    n1 = sum(len(s["actions"]) for s in m1["sections"])
    n2 = sum(len(s["actions"]) for s in m2["sections"])
    assert n2 <= n1


def test_grand_tournament(conn):
    p = _p(conn)
    assert "prossimo Gran Torneo" in gt.status_line(conn)
    conn.execute("UPDATE worlds SET current_tick=?;", (120 * 90 + 10,))
    assert gt.is_open(90)
    out = gt.fight(conn, p)
    assert "Ottavi" in out
    nid = gt.get(conn)["fighter"]
    res = gt.on_duel(conn, p, nid, "risparmiato")
    assert "Vinci" in res[0] and gt.get(conn)["round"] == 1
    from engine.systems import duel
    for _ in range(3):
        state.delete(conn, duel.KEY)                      # (il duello precedente si è chiuso)
        from engine.systems import encounters
        encounters.clear(conn)
        gt.fight(conn, entities.get_player(conn))
        res = gt.on_duel(conn, p, gt.get(conn)["fighter"], "ucciso")
    assert any("CAMPIONE" in x for x in res) and gt.get(conn)["crowns"] == 1
