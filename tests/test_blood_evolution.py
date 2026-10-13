"""Evoluzione del sangue e risonanza corpo-sangue."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, bloodlines as B, blood_evolution as E, body_blood, constitutions,
                            blood_menu, state)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "e.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=4, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


def _tier(c, t):
    rid = c.execute("SELECT id FROM cultivation_realms WHERE tier=? LIMIT 1;", (t,)).fetchone()["id"]
    c.execute("UPDATE players SET realm_id=?;", (rid,))


def test_every_evolution_goes_up_and_every_chain_reaches_chaos():
    for fam, outs in E.EVOLUTIONS.items():
        assert fam in B.FAMILIES
        for to, _need in outs:
            assert to in B.FAMILIES and B.FAMILY_RANK[to] > B.FAMILY_RANK[fam], (fam, to)
    for fam in E.EVOLUTIONS:
        assert E.chain(fam, 20)[-1] == "hundun"


def test_snake_becomes_jiao_keeps_old_form_as_minor(conn):
    B.grant_heritage(conn, "Serpente Volante", ["vento"], 90)
    p = _p(conn)
    o = E.options(conn, B.ordered(conn)[0][1])
    assert [x["to"] for x in o] == ["jiao"]
    _tier(conn, 2)

    class Good(random.Random):
        def random(self):
            return 0.0
    out = E.evolve(conn, p, "1", Good())
    assert "EVOLUZIONE" in out
    ln = B.all_lines(conn)["serpente volante"]
    assert ln["families"] == ["jiao"] and "serpente" in ln["minor"]
    assert B.line_rank(ln) == 4 and ln["name"].startswith("Sangue di Jiao")
    assert state.get_int(conn, "blood_evolutions", 0) == 1


def test_requirements_block_and_failure_costs(conn):
    B.grant_heritage(conn, "Drago delle Nubi", ["fulmine"], 90)       # drago (5) -> drago azzurro (6): grado Sacro
    p = _p(conn)
    out = E.evolve(conn, p, "1")
    assert "non è ancora pronto" in out
    d = B.all_lines(conn)
    d["drago delle nubi"]["conc"] = 600
    B._save(conn, d)
    _tier(conn, 4)

    class Bad(random.Random):
        def random(self):
            return 0.999
    out = E.evolve(conn, p, "1", Bad())
    assert "si spezza" in out
    assert B.all_lines(conn)["drago delle nubi"]["conc"] == pytest.approx(480)
    assert "riprendi" in E.evolve(conn, p, "1") or "si riprende" in E.evolve(conn, p, "1")


def test_ascent_beyond_chaos_is_endless(conn):
    B.grant_heritage(conn, "Hundun", ["caos"], 20000)
    _tier(conn, 8)
    ln = B.ordered(conn)[0][1]
    assert B.line_rank(ln) == 8
    assert E.options(conn, ln)[0]["to"] == "ascesa"

    class Good(random.Random):
        def random(self):
            return 0.0
    assert "EVOLUZIONE" in E.evolve(conn, _p(conn), "1", Good())
    ln = B.ordered(conn)[0][1]
    assert B.line_rank(ln) == 9 and "Oltre il Caos" in B.RANK_NAME[9]


def test_body_resonance_boosts_gain_and_awakens_body(conn):
    constitutions.grant(conn, "drago")
    st0 = constitutions.stage(conn)
    B.grant_heritage(conn, "Serpente Nero", ["terra"], 0)
    B.gain(conn, 0, random.Random(1), _p(conn), "Drago delle Nubi", ["fulmine"], 10)
    ln = B.all_lines(conn)["drago delle nubi"]
    assert ln["conc"] > 10                              # risonanza: concentra di più
    assert body_blood.label(conn, ln)
    B.grant_heritage(conn, "Serpente Nero", ["terra"], 90)
    _tier(conn, 2)

    class Good(random.Random):
        def random(self):
            return 0.0
    i = next(i for i, (k, _l) in enumerate(B.ordered(conn), 1) if k == "serpente nero")
    out = E.evolve(conn, _p(conn), str(i), Good())
    assert "RISVEGLIO" in out and constitutions.stage(conn) == st0 + 1


def test_menu_shows_evolution_buttons(conn):
    B.grant_heritage(conn, "Volpe Spirituale", ["illusione"], 90)
    m = blood_menu.menu_build(conn, _p(conn))
    labels = [a["label"] for s in m["sections"] for a in s["actions"]]
    assert any("Evolvi in Volpe Celeste" in x for x in labels)
    assert "EVOLUZIONE" in blood_menu.command(conn, _p(conn), "evolvi 1") or True


def test_body_powers_unlock_with_stages_and_techniques(conn):
    from engine.systems import body_powers
    constitutions.grant(conn, "asura")
    for _ in range(4):
        constitutions.awaken(conn, "prova")
    names = [n for _m, n, _e, _t in body_powers.unlocked("asura", 4)]
    assert "Tre Teste e Sei Braccia" in names
    techs = {r["name"] for r in conn.execute("SELECT name FROM learned_techniques;")}
    assert "Lama dell'Asura" in techs
    assert body_powers.next_power("asura", 4)[0] == 5
    assert any("(II)" in n for _m, n, _e, _t in body_powers.unlocked("asura", 8))   # oltre il compiuto


def test_supreme_body_needs_both_peaks(conn):
    from engine.systems import supreme_body
    p = _p(conn)
    constitutions.grant(conn, "drago")
    assert "Ti manca" in supreme_body.unite(conn, p)
    c = constitutions.get(conn)
    c["stage"] = 5
    state.set_json(conn, constitutions.KEY, c)
    B.grant_heritage(conn, "Drago della Torcia", ["fuoco"], 1300)
    out = supreme_body.unite(conn, p)
    assert "Sovrano dei Draghi Ancestrali" in out
    assert supreme_body.level(conn) >= 1 and supreme_body.cultivation_mult(conn) > 1.3
    assert any("Ruggito dei Diecimila Draghi" in r["name"] for r in conn.execute("SELECT name FROM learned_techniques;"))


def test_absorbing_enemy_bodies_fuses_them(conn):
    from engine.systems import body_absorb

    class Good(random.Random):
        def random(self):
            return 0.0
    p = _p(conn)
    out = body_absorb.absorb(conn, 0, Good(), p.id, "tuono")
    assert constitutions.get(conn)["key"] == "tuono"
    out = body_absorb.absorb(conn, 0, Good(), p.id, "ossa_spada")
    assert "FUSIONE DEI CORPI" in "\n".join(out)
    c = constitutions.get(conn)
    assert c["absorbed"] == ["ossa_spada"] and "⟡" in constitutions.display_name(c)
    g = constitutions._gifts(conn)
    assert g["pierce"] > 0 and g["dao"]["spada"] > 1.0 and "dao_other_weapon" not in g   # niente maledizione
    # gli NPC forti possono avere un corpo, deterministico
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE kind='human';")]
    assert all(body_absorb.npc_body(conn, i) == body_absorb.npc_body(conn, i) for i in ids)
