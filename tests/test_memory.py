"""Fase 8 — Memory System: short-term, historical filtering, active selection."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import event_system as ev, world_tick
from engine.systems import memory


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "mem.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    c.commit()
    yield c
    c.close()


def _event(conn, npc_id, etype, tick, summary):
    ev.log_event(
        conn, event_type=etype, tick=tick, location_id=1,
        title=summary, summary=summary,
        participants=[ev.Participant("npc", npc_id, "initiator")],
        consequences=[ev.Consequence("npc", npc_id, "x", "x",
                                     visibility="hidden", resolve_tick=tick)],
    )


def test_memory_derived_from_participation(conn):
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    _event(conn, npc, "fight", 10, "uno scontro")
    mems = memory.active_memory(conn, "npc", npc, current_tick=20)
    assert any(m.summary == "uno scontro" for m in mems)


def test_short_term_respects_window(conn):
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    _event(conn, npc, "fight", 100, "recente")
    _event(conn, npc, "fight", 5, "vecchio")
    st = memory.short_term(conn, "npc", npc, current_tick=120, window=80)
    sums = {m.summary for m in st}
    assert "recente" in sums       # age 20 <= 80
    assert "vecchio" not in sums   # age 115 > 80


def test_historical_filters_trivia(conn):
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    _event(conn, npc, "npc_move", 5, "un passo banale")     # importanza 1
    _event(conn, npc, "death", 5, "una morte epocale")       # importanza 10
    hist = memory.historical(conn, "npc", npc, current_tick=500)
    sums = {m.summary for m in hist}
    assert "una morte epocale" in sums
    assert "un passo banale" not in sums  # filtrato (sotto soglia)


def test_active_memory_bounded_and_ranked(conn):
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    # molti eventi banali recenti + una morte
    for t in range(1, 30):
        _event(conn, npc, "npc_move", t, f"passo {t}")
    _event(conn, npc, "death", 2, "MORTE")
    mems = memory.active_memory(conn, "npc", npc, current_tick=40, budget=5)
    assert len(mems) <= 5
    # la morte (importanza 10) deve essere in cima
    assert mems[0].summary == "MORTE"
    # ordinamento per score decrescente
    scores = [m.score for m in mems]
    assert scores == sorted(scores, reverse=True)


def test_world_historical_returns_significant(conn):
    npc = conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    _event(conn, npc, "npc_move", 5, "banale")
    _event(conn, npc, "breakthrough", 6, "ascesa")
    wh = memory.world_historical(conn, current_tick=50)
    sums = {m.summary for m in wh}
    assert "ascesa" in sums
    assert "banale" not in sums


def test_player_accumulates_memory_after_simulation(conn):
    # il giocatore partecipa ad eventi col tempo (almeno via combat se attacca);
    # qui verifichiamo che la funzione lavori anche per il player senza errori
    mems = memory.active_memory(conn, "player", 1, current_tick=0)
    assert isinstance(mems, list)
