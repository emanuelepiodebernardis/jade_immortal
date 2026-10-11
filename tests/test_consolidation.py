"""Pannello unico dei tesori, aiuto progressivo, varianti del testo."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, inner_space, mentor_ring, professions
from engine.cli import loop, help_text
from engine.narrative import varia


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "cs.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def test_treasury_panel_and_care(conn):
    assert "Non porti ancora tesori" in loop.dispatch(conn, "tesori", allow_nl=False)
    inner_space.grant(conn, "test")
    professions.give(conn, 1, "erbe", 5)
    out = loop.dispatch(conn, "tesori", allow_nl=False)
    assert "TESORI" in out and "campo vuoto" in out
    out = loop.dispatch(conn, "tesori cura", allow_nl=False)
    assert inner_space.get(conn)["planted"] > 0
    assert "spazio" in loop.dispatch(conn, "tesori spazio", allow_nl=False).lower()


def test_progressive_help(conn):
    h = help_text.help_for("", conn)
    assert "Ancora da scoprire" in h and "arti" in h.split("Ancora da scoprire")[1]
    loop.dispatch(conn, "profession forgia", allow_nl=False)
    h = help_text.help_for("", conn)
    assert "arti" not in h.split("Ancora da scoprire")[1] if "Ancora da scoprire" in h else True
    assert "Professioni" in help_text.help_for("tutto")           # 'help tutto' mostra sempre tutto


def test_varia_changes_with_world():
    assert varia.season(0) == "primavera" and varia.season(1500) == "inverno"
    assert varia.time_of_day(10) == "mattina" and varia.time_of_day(110) == "notte"
    lines = {varia.dawn(d * 120) for d in range(12)}
    assert len(lines) >= 10                                      # le albe non si ripetono
    rng = random.Random(1)
    outs = [varia.outcome(True, rng) for _ in range(6)]
    assert len(set(outs[:4])) >= 3                               # niente ripetizioni ravvicinate
