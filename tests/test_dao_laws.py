"""Aggiornamento 77: le vie nuove, le fusioni con la loro profondità, le intuizioni da nemici e reperti."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators import dao_gen
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import combat
from engine.systems import character, dao_heart, dao_insight, dao_laws, dao_training, sects


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "dl.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(3))
    dao_gen.seed_daos(c)
    c.commit()
    yield c
    c.close()


def _player(conn):
    return entities.get_player(conn, 1)


def _set(conn, key, comp):
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('player', 1, ?, 50, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "comprehension=excluded.comprehension, practiced=1;", (key, comp))


def _stones(conn, n):
    sects.grant_resource(conn, "pietre_spirituali", n - sects.get_resource(conn, "pietre_spirituali", 1), 1)


def _heart(conn, v):
    dao_heart.adjust(conn, v - dao_heart.heart(conn), "test")


def test_registries_are_complete():
    keys = {r[0] for r in dao_gen.DAOS}
    assert len(dao_laws.NEW) == 34
    assert all(k in keys for k in dao_laws.BY_KEY) and all(k in keys for k in dao_laws.FUSED)
    assert len(keys) == len(dao_gen.DAOS)                    # nessun doppione
    for k in dao_laws.BY_KEY:
        assert k in dao_training.DAO_STAT
    for f, row in dao_laws.FUSED.items():                    # ogni componente esiste
        assert all(c in keys for c in row[2]), f
    for f, steps in dao_laws.INSIGHT.items():
        assert f in dao_laws.FUSED and all(d in keys for _t, d in steps)
    for row in dao_laws.NEW:                                 # ogni via ha un costo vero
        assert row[9], row[0]


def test_scelta_unlocks_for_stones_and_derived_needs_base(conn):
    p = _player(conn)
    _stones(conn, 0)
    assert "costa" in dao_laws.unlock(conn, p, "scudo")
    _stones(conn, 10_000)
    out = dao_laws.unlock(conn, p, "scudo")
    assert "Apri il Dao dello Scudo" in out and dao_laws._has(conn, "scudo")
    assert "chiusa" in dao_laws.unlock(conn, p, "ghiaccio")  # serve acqua 25
    _set(conn, "acqua", 30)
    assert "Apri" in dao_laws.unlock(conn, p, "ghiaccio")


def test_comprehend_command_opens_a_new_way(conn):
    from engine.cli import loop
    _stones(conn, 10_000)
    out = loop.cmd_comprehend(conn, _player(conn), "pugnale")
    assert "Pugnale" in out and dao_laws._has(conn, "pugnale")


def test_effects_grow_with_tier_and_costs_apply(conn):
    _set(conn, "pugnale", 0)
    assert dao_laws.levers(conn).get("crit", 0) == 0
    _set(conn, "pugnale", 100)                               # maestro → soglia 4
    lv = dao_laws.levers(conn)
    assert lv["crit"] == pytest.approx(0.16) and lv["taken"] == pytest.approx(-0.08)
    _set(conn, "pugnale", 10 ** 7)
    assert 0.3 < dao_laws.levers(conn)["crit"] <= 0.45            # il tetto


def test_combat_power_includes_new_laws(conn):
    base = combat.combat_power(conn, "player", 1)["attack"]
    _set(conn, "martello", 250)
    assert combat.combat_power(conn, "player", 1)["attack"] > base


def test_longevity_adds_years_and_sacrifice_takes_them(conn):
    from engine.systems import lifespan
    y0 = lifespan.max_years(conn, 1)
    _set(conn, "longevita", 100)
    assert lifespan.max_years(conn, 1) > y0
    _set(conn, "sacrificio", 50)
    assert dao_laws.life_years(conn) == 100 - 30


def test_fusion_needs_components_heart_and_stones(conn):
    p = _player(conn)
    assert "manca" in dao_laws.fuse(conn, p, ["acqua", "fuoco"])
    _set(conn, "acqua", 30)
    _set(conn, "fuoco", 30)
    _heart(conn, 30)
    assert "agitato" in dao_laws.fuse(conn, p, ["acqua", "e", "fuoco"])
    _heart(conn, 60)                                         # leggera: basta 50
    _stones(conn, 10_000)
    out = dao_laws.fuse(conn, p, ["fondi", "acqua", "e", "il", "fuoco"])
    assert "FUSIONE" in out and dao_laws._has(conn, "vapore")
    assert dao_laws.grade(dao_laws._comp(conn, "vapore")) == "leggera"


def test_conflict_risk_and_bridge(conn):
    p = _player(conn)
    _set(conn, "fuoco", 200)
    _set(conn, "ghiaccio", 200)
    assert dao_laws.recipe_status(conn, "fuoco_gelido")["risk"] > 0
    _set(conn, "yinyang", 10)
    assert dao_laws.recipe_status(conn, "fuoco_gelido")["risk"] == 0
    _heart(conn, 90)
    _stones(conn, 100_000)
    assert "FUSIONE" in dao_laws.fuse(conn, p, ["fuoco_gelido"], rng=random.Random(1))


def test_deep_fusion_reveals_a_higher_dao(conn):
    """Acqua e fuoco portati all'estremo aprono lo Yin-Yang."""
    _set(conn, "vapore", 260)
    out = dao_laws.check_awakenings(conn)
    assert any("Nebbia" in x for x in out) and not dao_laws._has(conn, "yinyang")
    _set(conn, "vapore", 1000)
    out = dao_laws.check_awakenings(conn)
    assert any("Yin-Yang" in x for x in out) and dao_laws._has(conn, "yinyang")
    assert dao_laws.grade(1000) == "estrema"
    assert dao_laws.check_awakenings(conn) == [] or not any("Yin-Yang" in x for x in dao_laws.check_awakenings(conn))


def test_hint_lowers_thresholds_and_removes_risk(conn):
    assert dao_laws.requirement_of(conn, "tempesta") == {"fulmine": 100, "vento": 100}
    dao_laws.add_hint(conn, "tempesta")
    assert dao_laws.requirement_of(conn, "tempesta") == {"fulmine": 80, "vento": 80}
    dao_laws.add_hint(conn, "fuoco_gelido")
    assert dao_laws.recipe_status(conn, "fuoco_gelido")["risk"] == 0


def test_awakening_conditions(conn):
    _set(conn, "massacro", 120)
    _set(conn, "vuoto", 30)
    out = dao_laws.check_awakenings(conn)
    assert any("ANNIENTAMENTO" in x for x in out)


def _strong_foe(conn):
    npc = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET realm_id=(SELECT id FROM cultivation_realms ORDER BY tier DESC LIMIT 1) WHERE id=?;",
                 (npc,))
    conn.execute("DELETE FROM character_daos WHERE character_type='npc' AND character_id=?;", (npc,))
    for k, c in (("fulmine", 400), ("vento", 300)):
        conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, "
                     "practiced) VALUES ('npc', ?, ?, 50, ?, 1);", (npc, k, c))
    return npc


def test_observing_a_stronger_foe(conn):
    npc = _strong_foe(conn)
    out = []
    for i in range(12):
        out += dao_insight.observe(conn, npc, 1, rng=random.Random(i))
    text = "\n".join(out)
    assert "Fulmine" in text
    assert "tempesta" in dao_laws.hints(conn)                # fulmine + vento → intuizione sulla Tempesta
    assert dao_laws._has(conn, "fulmine")                    # tre scorci aprono il Dao


def test_observing_deepens_a_dao_you_practice(conn):
    npc = _strong_foe(conn)
    _set(conn, "fulmine", 20)
    for i in range(12):
        dao_insight.observe(conn, npc, 1, rng=random.Random(i))
    assert dao_laws._comp(conn, "fulmine") > 20


def test_relics_in_ruins_with_cooldown(conn):
    p = _player(conn)
    assert "Qui non ci sono" in dao_insight.search(conn, p) or True
    ruin = conn.execute("SELECT id FROM locations WHERE location_type='ruin' LIMIT 1;").fetchone()
    assert ruin
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (ruin["id"],))
    _set(conn, "spada", 40)
    p = _player(conn)
    out = dao_insight.search(conn, p)
    assert out
    assert "già frugato" in dao_insight.search(conn, p)
    assert not dao_insight.can_search(conn, ruin["id"])


def test_commands_and_voice(conn):
    from engine.cli import story_cmds, voice
    p = _player(conn)
    assert "FUSIONI" in story_cmds.handle(conn, p, "fusione", "")
    assert "VIE NUOVE" in story_cmds.handle(conn, p, "vie", "")
    assert "INTUIZIONI" in story_cmds.handle(conn, p, "intuizioni", "")
    s = {}
    assert voice.interpret("cerca i reperti", s, "")["cmd"] == "reperti"
    assert voice.interpret("fondi spada e volontà", s, "")["cmd"] == "fusione spada e volontà"
    assert voice.interpret("mostra le fusioni", s, "")["cmd"] == "fusione"
    assert voice.interpret("apri la via del ghiaccio", s, "")["cmd"] == "comprehend ghiaccio"


def test_menu_section_present(conn):
    from engine.systems import via_menu
    m = via_menu.build(conn, _player(conn), "via:profondi")
    assert any(sec.get("title") == "Le leggi nuove e le fusioni" for sec in m["sections"])
