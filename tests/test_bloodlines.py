"""Lignaggi di sangue: fonti, gradi, manifestazioni, fusione, trasformazione, eredità."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, bloodlines, beasts, items, state, npc_factory, combat_states,
                            destinies, secret_masters)
from engine.simulation import cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "b.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=4, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _rare_beast(conn, species):
    sp = next(s for s in beasts.RARE_SPECIES if s[0] == species)
    nid, _ = beasts.spawn_rare(conn, random.Random(1), _p(conn), sp)
    return nid


def test_grades_are_infinite():
    assert bloodlines.grade_name(0) == "Tracce"
    assert bloodlines.grade_name(80) == "Puro"
    assert bloodlines.grade_name(500) == "Sacro"
    assert "Caos" in bloodlines.grade_name(1200 * 2.5 ** 3)
    assert bloodlines.grade_index(10 ** 9) > bloodlines.grade_index(10 ** 6)


def test_rare_beast_drops_essence_and_absorbing_it_creates_lineage(conn):
    nid = _rare_beast(conn, "Fenice")
    out = bloodlines.on_beast_kill(conn, 0, random.Random(1), _p(conn), nid)
    assert any("Essenza di Sangue" in x for x in out)
    res = items.use_item(conn, 0, random.Random(2), 1, "essenza")
    assert res["status"] == "used"
    lines = bloodlines.all_lines(conn)
    assert "fenice" in lines and lines["fenice"]["conc"] > 0


def test_weak_common_beasts_give_no_blood(conn):
    nid = npc_factory.spawn(conn, random.Random(3), archetype="vagabondo", location_id=_p(conn).location_id,
                            tier=1, stage=1, name="Lupo Spirituale")
    conn.execute("UPDATE npcs SET kind='beast' WHERE id=?;", (nid,))
    assert bloodlines.beast_blood(conn, nid) is None


def test_manifestations_and_combat_effects(conn):
    p = _p(conn)
    bloodlines.gain(conn, 0, random.Random(1), p, "Fenice", ["fuoco"], 600)    # Sacro
    ln = bloodlines.all_lines(conn)["fenice"]
    mf = [k for k, _n in bloodlines.manifestations(ln)]
    assert mf == ["occhi", "artigli", "pelle", "ali", "corno"]
    enemy = npc_factory.spawn(conn, random.Random(5), archetype="vagabondo", location_id=p.location_id, tier=1)
    fx = combat_states.FightCtx(conn, 1, enemy, "Tu", "X", 100, 100, 10, 10)
    assert fx.p.prof.get("crit", 0) > 0 and fx.p.prof.get("evade", 0) > 0
    assert fx.p.lethal_saves >= 1                       # dono della Fenice
    assert any(src.startswith("sangue:") for _s, _c, _p2, src in fx.p.procs)


def test_transformation(conn):
    p = _p(conn)
    assert "Sacro" in bloodlines.transform(conn, p, "")
    bloodlines.gain(conn, 0, random.Random(1), p, "Drago Azzurro", ["fulmine", "acqua"], 700)
    out = bloodlines.transform(conn, p, "")
    assert "Drago" in out
    enemy = npc_factory.spawn(conn, random.Random(5), archetype="vagabondo", location_id=p.location_id, tier=1)
    fx = combat_states.FightCtx(conn, 1, enemy, "Tu", "X", 100, 100, 10, 10)
    assert any("TRASFORMAZIONE" in x for x in fx.lines_intro)
    assert "riposa" in bloodlines.transform(conn, p, "")


def test_fusion_of_dragon_and_ice_phoenix(conn):
    p = _p(conn)
    bloodlines.gain(conn, 0, random.Random(1), p, "Drago di Fuoco", ["fuoco"], 100)
    bloodlines.gain(conn, 0, random.Random(1), p, "Fenice di Ghiaccio", ["acqua"], 100)
    assert "fondi_sangue" in bloodlines.describe(conn, p)
    out = bloodlines.fuse(conn, p, "1 2")
    assert "Drago-Fenice di Fuoco e Ghiaccio" in out
    d = bloodlines.all_lines(conn)
    assert len(d) == 1
    ln = list(d.values())[0]
    assert set(ln["elements"]) == {"fuoco", "acqua"} and ln["conc"] == pytest.approx(180)
    # altro sangue di Fenice di Ghiaccio confluisce nel lignaggio fuso
    bloodlines.gain(conn, 0, random.Random(1), p, "Fenice di Ghiaccio", ["acqua"], 10)
    assert len(bloodlines.all_lines(conn)) == 1


def test_fusion_requires_pure(conn):
    p = _p(conn)
    bloodlines.gain(conn, 0, random.Random(1), p, "Qilin", ["luce"], 20)
    bloodlines.gain(conn, 0, random.Random(1), p, "Tigre Bianca", ["metallo"], 100)
    assert "diluiti" in bloodlines.fuse(conn, p, "1 2")


def test_rebellion_can_happen_with_conflicting_lines(conn):
    p = _p(conn)
    bloodlines.gain(conn, 0, random.Random(1), p, "Fenice", ["fuoco"], 20)
    bloodlines.gain(conn, 0, random.Random(1), p, "Tartaruga Nera", ["acqua", "terra"], 20)
    assert bloodlines._conflicts(bloodlines.all_lines(conn)) >= 1
    hit = any(bloodlines._rebellion(conn, 0, random.Random(s), p, "fenice", 30) for s in range(60))
    assert hit


def test_devourer_drinks_blood(conn):
    character.apply_origin(conn, "divoratore", random.Random(3))
    nid = _rare_beast(conn, "Tigre Bianca")
    out = bloodlines.on_devour_beast(conn, 0, random.Random(1), _p(conn), nid)
    assert out and "tigre bianca" in bloodlines.all_lines(conn)


def test_heritage_destiny_and_rebirth(conn):
    destinies.apply(conn, "sangue_drago")
    assert "drago azzurro" in bloodlines.all_lines(conn)
    from engine.systems import rebirth
    bloodlines.gain(conn, 0, random.Random(1), _p(conn), "Drago Azzurro", ["fulmine", "acqua"], 200)
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    row = rebirth.record_death(conn, _p(conn))
    lines = rebirth.reincarnate(conn, random.Random(1), "mortale", "Nuovo", {"key": "none"})
    assert any("sangue non dimentica" in x for x in lines)
    assert bloodlines.all_lines(conn)["drago azzurro"]["conc"] > 40


def test_blood_masters_path(conn):
    m = secret_masters.master_for("Sangue Antico", 5)
    assert any(r[0] == "blood" for r in m["req"])
    ok, txt = secret_masters._progress(conn, 1, ("blood", 30))
    assert not ok and "lignaggio" in txt
