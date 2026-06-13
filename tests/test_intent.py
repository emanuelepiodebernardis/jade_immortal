"""Fase 9.1 — Linguaggio naturale: parsing intenti, validazione, graceful senza LLM."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.cli import intent, loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "int.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_parse_valid_json_command():
    assert intent.build_command_from_llm_text('{"command":"examine","arg":"Han"}') == "examine Han"


def test_parse_no_arg_command():
    assert intent.build_command_from_llm_text('{"command":"look","arg":""}') == "look"


def test_parse_strips_surrounding_text():
    out = 'Ecco il comando: {"command":"move","arg":"north"} spero vada bene'
    assert intent.build_command_from_llm_text(out) == "move north"


def test_parse_rejects_unknown_command():
    assert intent.build_command_from_llm_text('{"command":"teleport","arg":"x"}') is None


def test_parse_rejects_garbage():
    assert intent.build_command_from_llm_text("non è json") is None


def test_translate_returns_none_without_llm(conn):
    # LLM disabilitato (default) -> nessuna traduzione, restano i comandi fissi
    player = entities.get_player(conn)
    assert intent.translate(conn, player, "vai a nord") is None


def test_dispatch_unknown_without_llm_gives_hint(conn):
    # senza LLM, una frase naturale resta "comando sconosciuto"
    out = loop.dispatch(conn, "vai verso nord per favore")
    assert "sconosciuto" in out.lower()


def test_fixed_commands_still_work(conn):
    out = loop.dispatch(conn, "status")
    assert "Coltivazione:" in out
