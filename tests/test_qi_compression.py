"""Aggiornamento 75: comprimere il qi allo Strato 10 colmo prima di sfondare."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import combat, cultivation
from engine.systems import character, qi as qimod, qi_compression as qc, state


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "qc.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=4, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(2))
    c.execute("UPDATE cultivation_records SET stage=10, progress=1.0 WHERE character_type='player' AND character_id=1;")
    c.commit()
    yield c
    c.close()


def _set_talent(conn, v):
    conn.execute("UPDATE character_profiles SET aff_cultivation=? WHERE character_type='player' AND character_id=1;", (v,))


def test_training_at_full_compresses_instead_of_wasting(conn):
    _set_talent(conn, 90)
    for i in range(6):
        cultivation.cultivate(conn, "player", 1, i, random.Random(i), amount=0.3)
    s = qc.status(conn)
    assert s["ready"] and s["over"] > 0.5 and s["grade"] >= 3
    rec = cultivation.get_record(conn, "player", 1)
    assert rec["progress"] == 1.0                                    # la barra resta piena: il resto è compresso


def test_talent_sets_the_threshold_and_practice_raises_it(conn):
    _set_talent(conn, 90)
    hi = qc.cap(conn)
    _set_talent(conn, 25)
    lo = qc.cap(conn)
    assert hi >= 4.9 and lo < 1.0
    d = qc.get(conn)
    d["mastery"] = 2.0
    state.set_json(conn, qc.KEY, d)
    assert qc.cap(conn) == pytest.approx(lo + 2.0)


def test_compressing_gets_slower_and_erupts_past_the_threshold(conn):
    _set_talent(conn, 25)                                            # un mortale: soglia bassa
    gains = []
    for i in range(40):
        before = qc.get(conn)["over"]
        qc.feed(conn, 0.2)
        gains.append(qc.get(conn)["over"] - before)
        if qc.eruption_pending(conn):
            break
    assert gains[-1] < gains[0]
    assert qc.eruption_pending(conn)                                 # oltre la soglia il qi erompe


def test_breakthrough_consolidates_gifts_and_brings_the_tribulation(conn, monkeypatch):
    p = entities.get_player(conn)
    d = qc.get(conn)
    d["over"] = 1.2
    state.set_json(conn, qc.KEY, d)
    atk0 = combat.combat_power(conn, "player", 1)["attack"]
    qmax0 = qimod.max_qi(conn, 1)
    lines = qc.on_breakthrough(conn, 100, p, True)
    text = "\n".join(lines)
    assert "Qi Cristallino" in text and "TRIBOLAZIONE DELLA COMPRESSIONE" in text and "Doni permanenti" in text
    b = qc.bonus(conn)
    assert b["atk"] > 0 and b["cult"] > 0 and b["qi"] > 0
    assert combat.combat_power(conn, "player", 1)["attack"] > atk0
    assert qimod.max_qi(conn, 1) > qmax0
    d = qc.get(conn)
    assert d["over"] == 0 and d["mastery"] > 0 and d["log"]
    from engine.systems import cult_mods
    assert any(lb == "Fondamenta compresse" for _m, lb in cult_mods._parts_cult(conn, 1, None, False))


def test_failure_scatters_half_and_odds_improve(conn):
    p = entities.get_player(conn)
    base = cultivation.breakthrough_odds(conn, "player", 1)["success"]
    d = qc.get(conn)
    d["over"] = 2.0
    state.set_json(conn, qc.KEY, d)
    assert cultivation.breakthrough_odds(conn, "player", 1)["success"] >= base
    qc.on_breakthrough(conn, 5, p, False)
    assert qc.get(conn)["over"] == pytest.approx(1.0)


def test_eruption_forces_the_breakthrough_from_training(conn):
    from engine.cli import loop
    p = entities.get_player(conn)
    d = qc.get(conn)
    d["erupt"] = True
    state.set_json(conn, qc.KEY, d)
    out = loop.cmd_cultivate(conn, p)
    assert "DA SOLO" in out
    assert not qc.eruption_pending(conn)


def test_menu_and_command(conn):
    from engine.systems import menus
    p = entities.get_player(conn)
    m = menus.build(conn, p, "via:coltivazione")
    assert any("Compressione del Qi" in s["title"] for s in m["sections"])
    from engine.cli import loop
    assert "COMPRESSIONE DEL QI" in loop.dispatch(conn, "compressione", allow_nl=False)


def test_full_breakthrough_command_with_compressed_qi(conn, monkeypatch):
    from engine.cli import loop
    from engine.systems import heart_demon
    monkeypatch.setattr(heart_demon, "should_trigger", lambda *a, **k: False)
    monkeypatch.setattr(cultivation, "_bt_success", lambda *a, **k: (1.0, 1.0))
    d = qc.get(conn)
    d["over"] = 0.6
    state.set_json(conn, qc.KEY, d)
    out = loop.cmd_breakthrough(conn, entities.get_player(conn))
    assert "ora sei" in out and "Qi Liquido" in out and "Doni permanenti" in out
    assert qc.get(conn)["over"] == 0
