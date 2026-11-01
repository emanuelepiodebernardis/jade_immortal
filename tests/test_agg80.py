"""Aggiornamento 80: anteprima, novità graduali, studio degli elementi, eredi del tuo stile, fusioni personali."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators import dao_gen
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, dao_heart, dao_laws, dao_preview, disciple_heirs, intro, personal_fusion,
                            sects, state)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a80.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=3, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(6))
    dao_gen.seed_daos(c)
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn, 1)


def _set(conn, key, comp, ctype="player", cid=1):
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES (?, ?, ?, 50, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "comprehension=excluded.comprehension, practiced=1;", (ctype, cid, key, comp))


def _stones(conn, n):
    sects.grant_resource(conn, "pietre_spirituali", n - sects.get_resource(conn, "pietre_spirituali", 1), 1)


def _set_day(conn, d):
    conn.execute("UPDATE worlds SET current_tick=? WHERE id=1;", (d * 120,))


def test_preview_changes_nothing(conn):
    _set(conn, "fulmine", 120)
    _set(conn, "vento", 110)
    n0 = conn.execute("SELECT COUNT(*) n FROM character_daos").fetchone()["n"]
    out = dao_preview.preview(conn, _p(conn), "tempesta")
    assert "ANTEPRIMA" in out and "attacco +" in out and "a 1000" in out
    assert conn.execute("SELECT COUNT(*) n FROM character_daos").fetchone()["n"] == n0
    assert not dao_laws._has(conn, "tempesta")
    assert "ANTEPRIMA" in dao_preview.preview(conn, _p(conn), "ghiaccio")
    assert "Non trovo" in dao_preview.preview(conn, _p(conn), "pippo")


def test_base_elements_can_be_studied(conn):
    p = _p(conn)
    conn.execute("DELETE FROM character_daos WHERE character_type='player' AND dao_key='acqua';")
    _stones(conn, 0)
    assert "costa" in dao_laws.unlock(conn, p, "acqua")
    _stones(conn, 10_000)
    assert "Studi le basi" in dao_laws.unlock(conn, p, "acqua") and dao_laws._has(conn, "acqua")


def test_intro_one_at_a_time_and_off(conn):
    p = _p(conn)
    _set_day(conn, 10)
    _stones(conn, 10_000)
    a = intro.check(conn, p)
    b = intro.check(conn, p)
    assert len(a) == 1 and "NOVITÀ" in a[0]
    assert b != a
    assert "NOVITÀ CHE HAI SCOPERTO" in intro.command(conn, p, "")
    intro.command(conn, p, "no")
    assert intro.check(conn, p) == []
    intro.command(conn, p, "si")
    assert len(intro.seen(conn)) >= 2


def test_heirs_learn_and_can_surpass(conn):
    from engine.systems import bonds, own_sect
    p = _p(conn)
    npc = conn.execute("SELECT id, name FROM npcs WHERE status='alive' AND (kind='human' OR kind IS NULL) LIMIT 1;"
                       ).fetchone()
    bonds.ensure_table(conn)
    bonds.add_bond(conn, p.id, npc["id"], "disciple", 0)
    assert own_sect.disciples(conn, p.id)
    _set(conn, "spada", 300)
    assert disciple_heirs.lesson_gain(conn, p.id, npc["id"], "spada") == 25
    _set(conn, "spada", 290, "npc", npc["id"])
    out = []
    for i in range(60):
        out += disciple_heirs.daily(conn, i * 120, random.Random(i), p)
        if out:
            break
    assert out and ("superato" in out[0])
    assert "EREDI" in disciple_heirs.describe(conn, p) or not own_sect.disciples(conn, p.id)


def test_personal_fusion_lifecycle(conn):
    p = _p(conn)
    _set(conn, "spada", 300)
    _set(conn, "anima", 280)
    out = []
    for i in range(400):
        out += personal_fusion.daily(conn, i * 120, random.Random(i), p)
        if out:
            break
    assert out and "MAI AVUTA" in out[0]
    dao_heart.adjust(conn, 80 - dao_heart.heart(conn), "t")
    _stones(conn, 100_000)
    res = personal_fusion.baptize(conn, p, "Fiamma del Lupo Bianco")
    assert "NASCE UNA VIA NUOVA" in res
    f = personal_fusion.all_(conn)[0]
    assert f["name"] == "Dao «Fiamma del Lupo Bianco»" and dao_laws._has(conn, f["key"])
    lv = dao_laws.levers(conn)
    assert any(v > 0 for v in lv.values())
    from engine.systems import dao_tree
    assert any(n["key"] == f["key"] for n in dao_tree.graph(conn)["nodes"])
    assert "Fiamma del Lupo Bianco" in dao_laws.describe_fusions(conn, p)
    assert "Non hai nessuna intuizione" in personal_fusion.baptize(conn, p, "Altro") or "Le tue fusioni" in \
        personal_fusion.baptize(conn, p, "Altro")


def test_commands(conn):
    from engine.cli import story_cmds, voice
    p = _p(conn)
    for c in ("novita", "eredi", "battezza", "anteprima"):
        assert story_cmds.handle(conn, p, c, "") is not None, c
    assert voice.interpret("prova fusione magma", {}, "")["cmd"] == "anteprima magma"
    assert voice.interpret("prova d'oro", {}, "")["cmd"] == "prova_cielo 3"
    assert state.get(conn, "x") is None
