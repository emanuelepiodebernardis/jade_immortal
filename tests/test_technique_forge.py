"""La fucina delle tecniche: fondere le tecniche, crescerle, usarle in battaglia."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, technique_forge as TF, sects, state, menus, moves, spirit, weapons
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "tf.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=17, factions=3, static_npc_count=12))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _setup(conn):
    weapons.choose_weapon(conn, "spada", 1)
    for k, v in (("fuoco", 40), ("legno", 30), ("acqua", 25)):
        conn.execute("INSERT OR REPLACE INTO character_daos (character_type, character_id, dao_key, comprehension) "
                     "VALUES ('player', 1, ?, ?);", (k, v))
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)


def test_bonds_between_elements():
    assert TF._bond({"fuoco"}, {"fuoco"})[0] == "risonanza"
    assert TF._bond({"legno"}, {"fuoco"})[0] == "generazione"
    assert TF._bond({"acqua"}, {"fuoco"})[0] == "conflitto"
    assert TF._bond({"spada"}, {"vento"})[0] == "intento"


def test_panel_lists_techniques_and_proposes_fusions(conn):
    _setup(conn)
    techs = TF.techniques(conn, 1)
    assert len(techs) >= 3 and all("tags" in t for t in techs)
    sug = TF.suggestions(conn, 1)
    assert sug and sug[0][1]["name"]
    txt = menus.render(conn, menus.build(conn, _p(conn), "tecniche"))
    assert "Fucina" in txt and "Le tue tecniche attive" in txt


def test_only_the_strongest_of_each_category_is_loaded(conn):
    _setup(conn)
    for i, mag in enumerate((0.1, 0.3, 0.05)):
        conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                     "VALUES (1, NULL, ?, ?, ?, 0);", (f"legacy:x{i}", f"Arte del Fuoco {i}", mag))
    every = TF.techniques(conn, 1, everything=True)
    active = TF.techniques(conn, 1)
    fire = [m for m in active if TF.category(m) == "fuoco"]
    assert len(fire) == 1 and len(active) < len(every)
    assert TF.superseded(conn, 1) == len(every) - len(active)
    # i doppioni con lo stesso nome sono una tecnica sola, padroneggiata più volte
    conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                 "VALUES (1, NULL, 'legacy:y1', 'Arte del Fuoco 1', 0.3, 0);")
    names = [m["name"] for m in TF.techniques(conn, 1, everything=True)]
    assert "Arte del Fuoco 1 (×2)" in names


def test_fusion_creates_a_new_move_that_grows(conn):
    _setup(conn)
    state.set(conn, TF.INSIGHT, "20")                   # riuscita quasi certa
    spirit.restore_full(conn, 1)
    out = loop.dispatch(conn, "tecniche fondi migliore", allow_nl=False)
    assert "Nasce una tecnica nuova" in out, out
    lst = TF.forged(conn)
    assert len(lst) == 1 and lst[0]["gen"] == 1
    mv = [m for m in moves.available_moves(conn, 1) if m["source"] == "creata"]
    assert mv and mv[0]["mods"]["attack_mult"] >= 1.0
    # allenarla e usarla la fa crescere
    spirit.restore_full(conn, 1)
    TF.train(conn, _p(conn), 1)
    for _ in range(20):
        TF.on_use(conn, mv[0])
    assert TF.forged(conn)[0]["lv"] >= 2
    assert "Nuovo Nome" in TF.rename(conn, 1, "Nuovo Nome")
    # la tecnica creata si può fondere ancora (seconda generazione)
    techs = TF.techniques(conn, 1)
    i = next(k for k, t in enumerate(techs, 1) if t["source"] == "creata")
    j = next(k for k, t in enumerate(techs, 1) if t["source"] != "creata")
    p = TF.plan([techs[i - 1], techs[j - 1]], conn, 1)
    assert p["gen"] == 2
    assert "dissolv" in TF.forget(conn, 1)


def test_failed_fusion_leaves_insight(conn, monkeypatch):
    _setup(conn)
    state.set(conn, TF.INSIGHT, "0")
    spirit.restore_full(conn, 1)
    monkeypatch.setattr(TF, "plan", lambda parts, c=None, pid=1: {**_real_plan(parts, c, pid), "chance": 0.0})
    out = TF.command(conn, _p(conn), "fondi 1 2")
    assert "INTUIZIONE" in out and state.get_int(conn, TF.INSIGHT, 0) == 1
    assert TF.forged(conn) == []
    assert "almeno due" in TF.command(conn, _p(conn), "fondi 1")


_real_plan = TF.plan
