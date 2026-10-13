"""Corpi leggendari: storia, doni, stadi, e la scelta di affidarsi al Cielo alla nascita e alla rinascita."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, constitutions as C, spirit, lifespan
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "c.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=3, factions=3, static_npc_count=10))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_every_body_has_story_and_gifts():
    assert len(C.BODIES) >= 22
    for k in C.BODIES:
        assert k in C.LORE and len(C.LORE[k][0]) > 60 and C.LORE[k][1]
    assert C.stage_name(0) == "Sigillato" and "Oltre" in C.stage_name(9)


def test_forced_body_at_birth_and_its_gifts(conn):
    out = C.roll_at_birth(conn, random.Random(5), "mortale", forced=True)
    assert out and "corpo leggendario" in out[0] and "Doni:" in out[0]
    C.grant(conn, "doppie_pupille")
    base = spirit.max_spirit(conn, 1)
    C.awaken(conn, "prova")
    assert spirit.max_spirit(conn, 1) > base
    txt = loop.dispatch(conn, "costituzione", allow_nl=False)
    assert "Doppie Pupille" in txt and "Primo Risveglio" in txt
    y0 = lifespan.age_years(conn, 1)
    C.grant(conn, "immortale")
    assert "Corpo Immortale" in loop.dispatch(conn, "corpo", allow_nl=False)
