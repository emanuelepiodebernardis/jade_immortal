"""Aggiornamento 69: il duello alla Pokémon — tipi, stati, intento del nemico."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, duel, duel_types as dt, deification_tower


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a69.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 5)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def test_type_chart():
    assert dt.effectiveness("fuoco", "metallo") == (dt.SUPER, "super")
    assert dt.effectiveness("fuoco", "acqua") == (dt.WEAK, "poco")
    assert dt.effectiveness("fuoco", "fuoco")[1] == "poco"
    assert dt.effectiveness(None, "acqua") == (1.0, "")
    m, tag = dt.effectiveness("fuoco", "luce", "fuoco")
    assert tag == "" and m == pytest.approx(dt.STAB)


def test_status_apply_tick_and_expire():
    d = {"name": "X", "hp_e": 100.0, "emax": 100.0, "hp_p": 2.0, "pmax": 100.0, "st_e": {}, "st_p": {}}
    dt.apply(d, "e", "ustione")
    dt.apply(d, "p", "emorragia")
    assert dt.mod(d["st_e"], "dot") == pytest.approx(0.05)
    dt.tick(d)
    assert d["hp_e"] == pytest.approx(95.0)
    assert d["hp_p"] >= 1.0                      # gli stati non uccidono il giocatore
    for _ in range(5):
        dt.tick(d)
    assert d["st_e"] == {} and d["st_p"] == {}


def test_mod_combines():
    assert dt.mod({"gelo": 2, "slancio": 1}, "dmg") == pytest.approx(0.75 * 1.2)
    assert dt.mod({"paralisi": 1, "stordito": 1}, "skip") == pytest.approx(0.85)
    assert dt.mod({"gelo": 0}, "dmg") == 1.0


def test_card_info_and_arena(conn):
    info = dt.card_info("Fiamma Nera dell'Abisso", "metallo", None)
    assert info["el"] == "fuoco" and info["eff"] == "super" and "ustione" in info["stato"]
    p = entities.get_player(conn)
    deification_tower.challenge(conn, p)
    a = duel.arena(conn, p)
    assert a and a["intento"]["tipo"] in ("attacco", "carica", "guardia")
    assert a["intento"]["danno"][1] >= a["intento"]["danno"][0] >= 0
    assert "stati_tu" in a and "elementi" in a
    for _ in range(12):
        if not duel.get(conn):
            break
        duel.act(conn, p, "colpisci")
    d = duel.get(conn)
    if d:
        assert "eff" in d["last"] and "stato" in d["last"]
