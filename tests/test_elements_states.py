"""Scontri più lunghi, ciclo dei Cinque Elementi (catene 2-5), stati di combattimento,
fusioni leggendarie, domini e Dao superiori."""
from __future__ import annotations

import random
import re
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import (character, elements, combat_states, dao_superiori, npc_factory,
                            state, karma)
from engine.simulation import combat
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "el.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(3))
    c.commit()
    yield c
    c.close()


def _daos(conn, **kv):
    for k, v in kv.items():
        dao_gen._set_dao(conn, "player", 1, k, 60, v, 1)


# ---------- durata degli scontri ----------

def test_duel_scale_full_between_equals_and_none_for_huge_gap():
    even = {"attack": 100, "defense": 20, "vitality": 100}
    assert combat.duel_scale(even, dict(even)) == combat.DUEL_HP_SCALE
    weak = {"attack": 5, "defense": 1, "vitality": 10}
    strong = {"attack": 5000, "defense": 500, "vitality": 5000}
    assert combat.duel_scale(strong, weak) == 1.0


# ---------- ciclo dei Cinque Elementi ----------

def test_chains_of_three_four_five():
    assert elements.longest_chain({"legno", "fuoco", "terra"}) == ["legno", "fuoco", "terra"]
    assert len(elements.longest_chain({"acqua", "legno", "fuoco", "terra"})) == 4
    assert elements.longest_chain(set(elements.CYCLE)) == elements.CYCLE
    for n in (2, 3, 4):
        for i in range(5):
            chain = frozenset(elements.CYCLE[(i + j) % 5] for j in range(n))
            assert chain in elements.CHAIN_NAMES


def test_conflict_needs_bridge():
    assert elements.conflicts({"legno", "terra"}) == [("legno", "terra", "fuoco")]
    assert elements.conflicts({"legno", "fuoco", "terra"}) == []


def test_profile_reports_named_chain_and_legendary(conn):
    _daos(conn, legno=30, fuoco=30, terra=30, vento=30)
    pr = elements.profile(conn, "player", 1)
    assert pr["chain_name"] == "Vulcano Vivente"
    assert "Incendio Danzante" in pr["legendary"]
    assert pr["attack"] >= elements.CHAIN_BONUS[3][0]
    txt = "\n".join(elements.describe(conn, 1))
    assert "Vulcano Vivente" in txt


def test_full_cycle_turns_states(conn):
    _daos(conn, legno=30, fuoco=30, terra=30, metallo=30, acqua=30)
    pr = elements.profile(conn, "player", 1)
    assert pr["chain_name"] == "Ciclo Perfetto dei Cinque Elementi"
    assert "cycle_states" in pr["special"]


def test_elemental_matchup(conn):
    _daos(conn, acqua=40)
    p = entities.get_player(conn)
    nid = npc_factory.spawn(conn, random.Random(1), archetype="vagabondo",
                            location_id=p.location_id, tier=1, dao="fuoco", dao_comp=30)
    mp, me, phrase = elements.matchup(conn, 1, nid)
    assert mp > 1.0 and me == 1.0 and "sovrasta" in phrase


# ---------- stati ----------

def test_states_apply_and_tick():
    ctx = combat_states.FightCtx.__new__(combat_states.FightCtx)
    ctx.p = combat_states.Side("Tu", 100, 50)
    ctx.e = combat_states.Side("X", 100, 50)
    ctx.p.prof = {"special": set()}
    ctx.e.prof = {}
    ctx.p.domains = []
    ctx._apply(ctx.e, "ustione", 1.0)
    for _ in range(3):
        ctx._apply(ctx.e, "emorragia", 1.0)
    hp0 = ctx.e.hp
    ctx.round_start(random.Random(1))
    assert ctx.e.hp < hp0
    assert ctx.e.states["emorragia"]["stacks"] == 3
    ctx._apply(ctx.e, "stordimento", 1.0)
    assert ctx.blocked("e", random.Random(1))
    assert ctx.blocked("e", random.Random(1)) is None      # dura un solo turno
    ctx._apply(ctx.p, "scudo", 1.0)
    assert ctx.absorb("p", 10) < 10


def test_fight_with_elements_runs_and_shows_fusions(conn):
    _daos(conn, fuoco=60, vento=30, fulmine=30)
    p = entities.get_player(conn)
    nid = npc_factory.spawn(conn, random.Random(3), archetype="vagabondo",
                            location_id=p.location_id, tier=2, stage=5, dao="acqua", dao_comp=120)
    out = loop.dispatch(conn, f"attack {entities.get_npc(conn, nid).name}")
    assert "Fusioni leggendarie" in out
    assert re.search(r"\(\d+ round\)", out)


def test_domain_opens_at_dominator(conn):
    _daos(conn, fuoco=520)
    pr = elements.profile(conn, "player", 1)
    assert "fuoco" in pr["domains"]


def test_talisman_buff_is_consumed(conn):
    state.set_json(conn, "combat_buffs", [{"name": "Talismano del Tuono", "state": "stordimento"}])
    p = entities.get_player(conn)
    nid = npc_factory.spawn(conn, random.Random(3), archetype="vagabondo",
                            location_id=p.location_id, tier=1)
    fx = combat_states.FightCtx(conn, 1, nid, "Tu", "X", 100, 100, 10, 10)
    assert "stordimento" in fx.e.states
    assert state.get_json(conn, "combat_buffs") is None


# ---------- Dao superiori ----------

def test_superior_daos_awaken_by_deeds(conn):
    assert dao_superiori.check_awakenings(conn, 1) == []
    karma.adjust_karma(conn, "player", 1, 400, "test", 0)
    out = dao_superiori.check_awakenings(conn, 1)
    assert any("KARMA" in o for o in out)
    assert dao_superiori.has(conn, 1, "karma")
    _daos(conn, luce=50, oscurita=50)
    assert any("YIN-YANG" in o for o in dao_superiori.check_awakenings(conn, 1))
    for _ in range(3):
        dao_superiori.on_win(conn, 0.05)
    assert any("VITA E DELLA MORTE" in o for o in dao_superiori.check_awakenings(conn, 1))


def test_superior_daos_have_states_names_and_hints(conn):
    from engine.systems.dao_techniques import _main_name
    for k in dao_superiori.SUPERIOR:
        assert k in combat_states.STATE_OF_DAO
        assert not _main_name(k, 3).startswith("Intento ") or "Intento" in _main_name(k, 3)
    assert len(dao_superiori.sealed_hints(conn, 1)) == len(dao_superiori.SUPERIOR)
    assert "sigillati" in loop.dispatch(conn, "dao")
