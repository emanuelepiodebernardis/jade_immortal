"""Fase 9 — Narrative Engine: contesto fattuale, fallback, sink puro (P2), Factual Lock."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.narrative import context as ctx_mod, prompts, llm, renderer


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "narr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_context_collects_observable_facts(conn):
    player = entities.get_player(conn)
    ctx = ctx_mod.build_scene_context(conn, player, tick=0)
    assert ctx.location_name
    assert ctx.player_realm
    # gli NPC presenti nella location iniziale finiscono nel contesto
    here = entities.npcs_in_location(conn, player.location_id)
    assert len(ctx.present_npcs) == len(here)


def test_prompt_includes_facts_and_system_forbids_invention(conn):
    player = entities.get_player(conn)
    ctx = ctx_mod.build_scene_context(conn, player, tick=0)
    prompt = prompts.build_scene_prompt(ctx)
    assert ctx.location_name in prompt
    # il system prompt vieta esplicitamente di inventare
    assert "non inventare" in prompts.SYSTEM_PROMPT.lower()


def test_fallback_render_produces_prose(conn):
    player = entities.get_player(conn)
    # con LLM disabilitato (default), render usa il fallback
    assert not llm.is_enabled()
    text = renderer.render_scene(conn, player, tick=0)
    assert isinstance(text, str) and len(text) > 20
    assert player and entities.get_location(conn, player.location_id).name in text


def test_narrative_is_a_pure_sink(conn):
    """P2: rendere la scena NON deve modificare la simulazione."""
    def snapshot():
        return {
            t: conn.execute(f"SELECT COUNT(*) c FROM {t};").fetchone()["c"]
            for t in ("events", "consequences", "event_participants", "npcs",
                      "cultivation_records", "npc_relationships", "injuries")
        }
    player = entities.get_player(conn)
    before = snapshot()
    for _ in range(3):
        renderer.render_scene(conn, player, tick=0)
        renderer.render_chronicle(conn, tick=0)
    after = snapshot()
    assert before == after, "il narrative layer non deve scrivere nulla nel DB"


def test_validate_flags_foreign_entities(conn):
    player = entities.get_player(conn)
    ctx = ctx_mod.build_scene_context(conn, player, tick=0)
    allowed = ctx.allowed_names()
    # prendi un NPC che NON è nella scena
    here_ids = {n.name for n in ctx.present_npcs}
    foreign_npc = conn.execute(
        "SELECT name FROM npcs WHERE name NOT IN ({}) LIMIT 1;".format(
            ",".join("?" * len(here_ids)) or "''"),
        tuple(here_ids),
    ).fetchone()
    if foreign_npc:
        text = f"Nel vento appare {foreign_npc['name']}, giunto dal nulla."
        flagged = renderer.validate_no_foreign_entities(conn, text, allowed)
        assert foreign_npc["name"] in flagged
    # testo pulito (solo nomi ammessi) non genera flag
    clean = f"Ti trovi presso {ctx.location_name}."
    assert renderer.validate_no_foreign_entities(conn, clean, allowed) == []


def test_llm_disabled_returns_none(conn):
    # senza abilitazione, generate non chiama nulla e ritorna None
    cfg = {"provider": "ollama", "model": "x", "host": "http://localhost:11434", "enabled": False}
    assert llm.generate("sys", "prompt", cfg) is None
