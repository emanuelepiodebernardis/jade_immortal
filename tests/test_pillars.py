"""Aggiornamento 73: i sei pilastri — punteggi, armonia, consigli, schede della Via."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import combat
from engine.systems import character, menus, pillars, state, via_menu


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "pil.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def test_scores_cover_six_pillars(conn):
    d = pillars.compute(conn)
    assert list(d["scores"]) == pillars.ORDER
    assert all(0 <= v <= 100 for v in d["scores"].values())
    assert d["weakest"] in pillars.ORDER and 0.0 <= d["harmony"] <= 1.0
    for k in pillars.ORDER:
        assert d["parts"][k], k                               # ogni pilastro ha almeno una fonte attiva
        assert pillars.CMD[k] and pillars.ROLE[k]


def test_harmony_rewards_balance_and_never_penalizes():
    flat = pillars._harmony({k: 60 for k in pillars.ORDER})
    assert flat["harmony"] == 1.0
    lop = pillars._harmony({**{k: 80 for k in pillars.ORDER}, "legami": 5})
    assert lop["harmony"] == 0.0 and lop["weakest"] == "legami"
    tiny = pillars._harmony({k: 5 for k in pillars.ORDER})
    assert tiny["harmony"] == 0.0                              # serve almeno un pilastro costruito


def test_harmony_multiplies_power_and_cultivation(conn):
    p = entities.get_player(conn)
    pillars.refresh(conn)
    d = state.get_json(conn, pillars.KEY)
    d["harmony"] = 0.0
    state.set_json(conn, pillars.KEY, d)
    base = combat.combat_power(conn, "player", p.id)["attack"]
    d["harmony"] = 1.0
    state.set_json(conn, pillars.KEY, d)
    up = combat.combat_power(conn, "player", p.id)["attack"]
    assert up == pytest.approx(base * (1 + pillars.HARMONY_ATK), rel=1e-6)
    m, lbl = pillars.cultivation_mult(conn)
    assert m == pytest.approx(1 + pillars.HARMONY_CULT) and lbl
    from engine.systems import cult_mods
    assert any(lb == "Armonia dei pilastri" for _m, lb in cult_mods._parts_cult(conn, p.id, None, False))


def test_daily_announces_only_a_step_up(conn):
    p = entities.get_player(conn)
    pillars.refresh(conn)
    assert pillars.daily(conn, 0, None, p) == []
    d = state.get_json(conn, pillars.KEY)
    d["harmony"] = 0.0
    state.set_json(conn, pillars.KEY, d)
    import engine.systems.pillars as mod
    orig = mod.compute
    mod.compute = lambda c: {**orig(c), "harmony": 0.6}
    try:
        out = pillars.daily(conn, 0, None, p)
    finally:
        mod.compute = orig
    assert out and "armonia 60%" in out[0]


def test_forza_tab_starts_with_the_pillars_and_advice(conn):
    p = entities.get_player(conn)
    m = menus.build(conn, p, "via:forza")
    titles = [s["title"] for s in m["sections"]]
    assert titles[0] == "I sei pilastri"
    assert any(t.startswith("Il pilastro da alzare") for t in titles)
    assert len(m["sections"][0]["bars"]) == 6
    a = pillars.advice(conn)
    assert a is None or (a[0] and a[1])
    assert "Pilastri:" in pillars.summary(conn)


def test_via_tabs_are_the_pillars(conn):
    p = entities.get_player(conn)
    assert set(via_menu.GROUPS) == {"coltivazione", "corpo", "profondi", "anime", "forza"}
    members = [m for ms in via_menu.GROUPS.values() for m in ms]
    assert sorted(members) == sorted(via_menu.KEYS)            # ogni sistema sta in un solo pilastro
    m = menus.build(conn, p, "via:meridiani")
    assert m["tab"] == "corpo"
    divs = [s.get("divider") for s in m["sections"] if s.get("divider")]
    assert divs                                                # gli altri sistemi del pilastro, con il loro nome


@pytest.mark.parametrize("k", pillars.ORDER)
def test_pillar_commands_are_understood(conn, k):
    from engine.cli import loop
    for _n, _v, cmd in pillars.compute(conn)["parts"][k]:
        out = loop.dispatch(conn, cmd, allow_nl=False) or ""
        assert "non capisco" not in out.lower() and "comando sconosciuto" not in out.lower(), (cmd, out[:80])
    out = loop.dispatch(conn, pillars.CMD[k], allow_nl=False) or ""
    assert "non capisco" not in out.lower(), (pillars.CMD[k], out[:80])
