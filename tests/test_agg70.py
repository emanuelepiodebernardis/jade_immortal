"""Aggiornamento 70: forza per fonte, élite e boss, il nemico che pensa."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation, combat
from engine.systems import character, duel, elites, power_report, pursuers, power_budget


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a70.db"
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


def _npc_here(conn, p):
    r = conn.execute("SELECT id FROM npcs WHERE status='alive' AND kind='human' ORDER BY id LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (p.location_id, r["id"]))
    return entities.get_npc(conn, r["id"])


def test_trace_matches_result(conn):
    p = entities.get_player(conn)
    t: dict = {}
    r = combat.combat_power(conn, "player", p.id, t)
    assert r == combat.combat_power(conn, "player", p.id)
    assert {"base", "fattori", "regno", "dao"} <= set(t)


def test_power_report_sections(conn):
    p = entities.get_player(conn)
    titles = [s["title"] for s in power_report.sections(conn, p)]
    assert "Cosa potenziare adesso" in titles
    assert any(c == "equip forgia veste" for _a, c in power_report.advice(conn, p))


def test_elites_stable_and_boss(conn, monkeypatch):
    p = entities.get_player(conn)
    n = _npc_here(conn, p)
    conn.execute("UPDATE npcs SET archetype='patriarca' WHERE id=?;", (n.id,))
    monkeypatch.setattr(elites, "_dominant", lambda c, pl: True)
    elites.touch(conn, p, [n.id])
    assert elites.rank(conn, n.id) == "boss"
    assert pursuers.ratio(conn, p.id, n.id) >= elites.BANDS["boss"][0] * 0.95 or pursuers.factor(conn, n.id) >= 49
    assert elites.reward_rank(conn, n.id) == 1
    ranks = [elites._decide(i, "guardia") for i in range(2000)]
    assert 0.08 < ranks.count("elite") / 2000 < 0.17
    assert elites._decide(5, "guardia") == elites._decide(5, "guardia")


def test_technique_soft_cap():
    assert power_budget.soft(5.3, duel.TECH_CAP) < duel.TECH_CAP
    assert power_budget.soft(1.4, duel.TECH_CAP) > 1.3


def test_enemy_decisions_and_boss_phases():
    rng = random.Random(1)
    d = {"hp_e": 10.0, "emax": 100.0, "round": 5, "style": "prudente", "charge_e": False, "guard_e": False,
         "heals": 0, "ecd": 0, "el_e": "fuoco", "name": "X"}
    seen = {duel._decide_enemy(dict(d), random.Random(i)) for i in range(200)}
    assert {"cura", "fuga", "tecnica"} <= seen
    b = {"boss": True, "phase": 1, "hp_e": 45.0, "emax": 100.0, "name": "B", "st_e": {"ustione": 2}}
    lines: list[str] = []
    duel._boss_phase(b, lines)
    assert b["phase"] == 2 and b["hp_e"] == 60.0 and b["st_e"] == {}
    b["hp_e"] = 10.0
    duel._boss_phase(b, lines)
    assert b["phase"] == 3
    b.update(charge_e=False, guard_e=False, round=3)
    assert duel._decide_enemy(b, rng) == "carica"


def test_full_duels_run(conn):
    p = entities.get_player(conn)
    n = _npc_here(conn, p)
    for k in range(3):
        if not duel.get(conn):
            duel.start(conn, p, n.name, arena=True)
        for _ in range(40):
            if not duel.get(conn) or duel.get(conn)["hp_e"] <= 0:
                break
            duel.act(conn, p, random.Random(k).choice(["colpisci", "difendi", "concentrati"]))
            a = duel.arena(conn, p)
            if a:
                assert a["intento"]["tipo"] in ("attacco", "carica", "guardia", "tecnica", "cura", "fuga")
        if duel.get(conn):
            from engine.systems import state
            state.delete(conn, duel.KEY)


def test_guide_steps_and_rewards(conn):
    from engine.systems import guide, gear, sects
    p = entities.get_player(conn)
    it = guide.attention_item(conn, p)
    assert it and it["title"].startswith("Primi passi 1/")
    before = sects.get_resource(conn, "pietre_spirituali", p.id)
    gear.add(conn, gear.make(random.Random(1), 5, "anello", "comune"))
    out = guide.check(conn, p)
    assert any("Indossa" in x for x in out)
    assert sects.get_resource(conn, "pietre_spirituali", p.id) > before
    guide.flag(conn, "duello")
    assert any("duello" in x.lower() for x in guide.check(conn, p))
    assert "salta" in guide.command(conn, p, "")
    guide.command(conn, p, "salta")
    assert guide.attention_item(conn, p) is None


def test_codex_entries():
    from engine.systems import guide
    keys = {c["key"] for c in guide.codex()}
    assert {"coltivazione", "duello", "zaino", "mappa", "meridiani"} <= keys
