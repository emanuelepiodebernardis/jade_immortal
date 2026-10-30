"""Aggiornamento 71: la squadra di bestie — livelli, evoluzioni, carte nel duello, lotte tra bestie."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, beast_team, bonds, classes, duel, npc_factory


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "bt.db"
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


def _beast(conn, p, name="Lupo Spirituale 12"):
    nid = npc_factory.spawn(conn, random.Random(len(name)), archetype="guardia", location_id=p.location_id, tier=4,
                            stage=3, name=name, tick=0)
    conn.execute("UPDATE npcs SET kind='beast' WHERE id=?;", (nid,))
    return nid


def test_team_size_grows_with_realm(conn):
    p = entities.get_player(conn)
    assert classes.max_beasts(conn, p.id) == 3


def test_levels_and_evolution(conn):
    p = entities.get_player(conn)
    nid = _beast(conn, p)
    bonds.add_bond(conn, p.id, nid, "beast", 0)
    out = []
    for _ in range(200):
        out += beast_team.gain(conn, nid, 40)
    assert beast_team.info(conn, nid)["lv"] >= beast_team.EVO_LV[1]
    assert any("EVOLUZIONE" in x for x in out)
    assert "Re" in beast_team.display_name(conn, nid)
    assert "SQUADRA" in beast_team.describe(conn, p)


def test_duel_card_and_strike(conn):
    p = entities.get_player(conn)
    nid = _beast(conn, p)
    bonds.add_bond(conn, p.id, nid, "beast", 0)
    foe = conn.execute("SELECT id, name FROM npcs WHERE status='alive' AND kind='human' LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (p.location_id, foe["id"]))
    duel.start(conn, p, foe["name"], arena=True)
    a = duel.arena(conn, p)
    cards = [c for c in a["carte"] if c["kind"] == "bestia"]
    assert cards and cards[0]["ok"]
    before = duel.get(conn)["hp_e"]
    duel.act(conn, p, cards[0]["cmd"].split(" ", 1)[1])
    d = duel.get(conn)
    assert d is None or d["hp_e"] < before or d.get("bcd")


def test_beast_battle(conn):
    p = entities.get_player(conn)
    mine = _beast(conn, p, "Aquila del Tuono 3")
    bonds.add_bond(conn, p.id, mine, "beast", 0)
    _beast(conn, p, "Serpente di Roccia 7")
    out = beast_team.battle(conn, p, "serpente")
    assert "LOTTA TRA BESTIE" in out
    assert "stremato" in beast_team.battle(conn, p, "serpente")
