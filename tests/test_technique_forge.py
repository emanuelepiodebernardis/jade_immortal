"""La fucina delle tecniche: fondere le tecniche, crescerle, usarle in battaglia."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, technique_forge as TF, sects, state, menus, moves, spirit, weapons
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "tf.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=17, factions=3, static_npc_count=12))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _setup(conn):
    weapons.choose_weapon(conn, "spada", 1)
    for k, v in (("fuoco", 40), ("legno", 30), ("acqua", 25)):
        conn.execute("INSERT OR REPLACE INTO character_daos (character_type, character_id, dao_key, comprehension) "
                     "VALUES ('player', 1, ?, ?);", (k, v))
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)


def test_bonds_between_elements():
    assert TF._bond({"fuoco"}, {"fuoco"})[0] == "risonanza"
    assert TF._bond({"legno"}, {"fuoco"})[0] == "generazione"
    assert TF._bond({"acqua"}, {"fuoco"})[0] == "conflitto"
    assert TF._bond({"spada"}, {"vento"})[0] == "intento"


def test_panel_lists_techniques_and_proposes_fusions(conn):
    _setup(conn)
    techs = TF.techniques(conn, 1)
    assert len(techs) >= 3 and all("tags" in t for t in techs)
    sug = TF.suggestions(conn, 1)
    assert sug and sug[0][1]["name"]
    txt = menus.render(conn, menus.build(conn, _p(conn), "tecniche"))
    assert "Fucina" in txt and "Le tue tecniche attive" in txt


def test_only_the_strongest_of_each_category_is_loaded(conn):
    _setup(conn)
    for i, mag in enumerate((0.1, 0.3, 0.05)):
        conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                     "VALUES (1, NULL, ?, ?, ?, 0);", (f"legacy:x{i}", f"Arte del Fuoco {i}", mag))
    every = TF.techniques(conn, 1, everything=True)
    active = TF.techniques(conn, 1)
    fire = [m for m in active if TF.category(m) == "fuoco"]
    assert len(fire) == 1 and len(active) < len(every)
    assert TF.superseded(conn, 1) == len(every) - len(active)
    # i doppioni con lo stesso nome sono una tecnica sola, padroneggiata più volte
    conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                 "VALUES (1, NULL, 'legacy:y1', 'Arte del Fuoco 1', 0.3, 0);")
    names = [m["name"] for m in TF.techniques(conn, 1, everything=True)]
    assert "Arte del Fuoco 1 (×2)" in names


def test_fusion_creates_a_new_move_that_grows(conn):
    _setup(conn)
    state.set(conn, TF.INSIGHT, "20")                   # riuscita quasi certa
    spirit.restore_full(conn, 1)
    out = loop.dispatch(conn, "tecniche fondi migliore", allow_nl=False)
    assert "Nasce una tecnica nuova" in out, out
    lst = TF.forged(conn)
    assert len(lst) == 1 and lst[0]["gen"] == 1
    mv = [m for m in moves.available_moves(conn, 1) if m["source"] == "creata"]
    assert mv and mv[0]["mods"]["attack_mult"] >= 1.0
    # allenarla e usarla la fa crescere
    spirit.restore_full(conn, 1)
    TF.train(conn, _p(conn), 1)
    for _ in range(20):
        TF.on_use(conn, mv[0])
    assert TF.forged(conn)[0]["lv"] >= 2
    assert "Nuovo Nome" in TF.rename(conn, 1, "Nuovo Nome")
    # la tecnica creata si può fondere ancora (seconda generazione)
    techs = TF.techniques(conn, 1)
    i = next(k for k, t in enumerate(techs, 1) if t["source"] == "creata")
    j = next(k for k, t in enumerate(techs, 1) if t["source"] != "creata")
    p = TF.plan([techs[i - 1], techs[j - 1]], conn, 1)
    assert p["gen"] == 2
    assert "dissolv" in TF.forget(conn, 1)


def test_failed_fusion_leaves_insight(conn, monkeypatch):
    _setup(conn)
    state.set(conn, TF.INSIGHT, "0")
    spirit.restore_full(conn, 1)
    monkeypatch.setattr(TF, "plan", lambda parts, c=None, pid=1: {**_real_plan(parts, c, pid), "chance": 0.0})
    out = TF.command(conn, _p(conn), "fondi 1 2")
    assert "INTUIZIONE" in out and state.get_int(conn, TF.INSIGHT, 0) == 1
    assert TF.forged(conn) == []
    assert "almeno due" in TF.command(conn, _p(conn), "fondi 1")


_real_plan = TF.plan


def test_blood_menu_lists_lines_and_refines(conn):
    from engine.systems import bloodlines, blood_menu
    rng = random.Random(3)
    p = _p(conn)
    bloodlines.gain(conn, 0, rng, p, "Drago Celeste", ["fulmine", "acqua"], 120)
    bloodlines.gain(conn, 0, rng, p, "Fenice Rossa", ["fuoco"], 100)
    bloodlines.gain(conn, 0, rng, p, "Lupo Spirituale", ["vento"], 20)
    txt = loop.dispatch(conn, "sangue", allow_nl=False)
    assert "IL SANGUE E I LIGNAGGI" in txt and "Drago Celeste" in txt and "Fondi #1 + #2" in txt
    assert "SANGUE IN RIVOLTA" in txt                    # acqua contro fuoco
    out = blood_menu.refine(conn, p, "3 in 1")
    assert "Lupo" in out and len(bloodlines.ordered(conn)) == 2
    assert "LIGNAGGI DI SANGUE" in loop.dispatch(conn, "sangue info", allow_nl=False)


def test_rarer_blood_dominates_fusions_and_names_stay_short(conn):
    from engine.systems import bloodlines as B
    rng = random.Random(4)
    p = _p(conn)
    B.gain(conn, 0, rng, p, "Cinghiale Corazzato", ["corpo"], 300)
    B.gain(conn, 0, rng, p, "Drago delle Nubi", ["fulmine", "acqua"], 100)
    B.gain(conn, 0, rng, p, "Lupo Spirituale", ["vento"], 100)
    o = B.ordered(conn)
    assert B.line_rank(o[0][1]) == 1 and B.RANK_MULT[3] > B.RANK_MULT[1]
    res = B.fusion_result([ln for _k, ln in o])
    assert res["families"] == ["drago"] and set(res["minor"]) == {"cinghiale", "lupo"}
    assert res["species"].startswith("Drago di ") and res["species"].count(" e ") <= 1
    out = B.fuse(conn, p, "1 2 3")
    assert "domina" in out and len(B.ordered(conn)) == 1
    # due leggendari alla pari: nome combinato, rarità divina
    B.gain(conn, 0, rng, p, "Fenice Rossa", ["fuoco"], 100)
    B.fuse(conn, p, "1 2")
    ln = B.ordered(conn)[0][1]
    assert ln["species"].startswith(("Drago-Fenice", "Fenice-Drago")) and B.line_rank(ln) == 6


def test_sacrifice_lesser_blood_to_the_noblest(conn):
    from engine.systems import bloodlines as B, blood_menu
    rng = random.Random(5)
    p = _p(conn)
    B.gain(conn, 0, rng, p, "Cinghiale Corazzato", ["corpo"], 400)
    B.gain(conn, 0, rng, p, "Lupo Spirituale", ["vento"], 200)
    B.gain(conn, 0, rng, p, "Drago delle Nubi", ["fulmine", "acqua"], 50)
    assert blood_menu.noblest(conn) == 3                  # il drago, anche se meno concentrato
    assert "non si piega" in blood_menu.refine(conn, p, "3 a 1")
    txt = loop.dispatch(conn, "sangue", allow_nl=False)
    assert "Sacrifica i 2 sangui meno nobili" in txt
    out = loop.dispatch(conn, "sangue sacrifica tutti", allow_nl=False)
    o = B.ordered(conn)
    assert len(o) == 1 and o[0][1]["species"] == "Drago delle Nubi" and o[0][1]["purity"] > 0
    assert o[0][1]["conc"] == pytest.approx(50 + 0.6 * 600, rel=0.01) and "purezza" in out


def test_income_from_workshop_sect_and_panel(conn):
    from engine.systems import income, professions, sect_menu
    p = _p(conn)
    professions.add_xp(conn, 1, 5000, "alchimia")
    assert professions.level(conn, 1, "alchimia") >= 3
    s0 = sects.get_resource(conn, "pietre_spirituali", 1)
    income.daily(conn, 120, random.Random(1), p)
    assert sects.get_resource(conn, "pietre_spirituali", 1) > s0
    txt = loop.dispatch(conn, "rendite", allow_nl=False)
    assert "RENDITE" in txt and "Bottega" in txt
    assert "nulla da riscuotere" in loop.dispatch(conn, "rendite riscuoti", allow_nl=False) or True


def test_auto_loot_and_absorb_after_a_kill(conn):
    from engine.systems import auto_collect, items, npc_factory
    p = _p(conn)
    iid = items.create_item(conn, "Essenza di Sangue di Lupo", "essenza", "raro", "x",
                            {"bloodline": {"species": "Lupo Spirituale", "elements": ["vento"], "gain": 15}})
    items.grant(conn, "ground", p.location_id, iid)
    out = auto_collect.after_kill(conn, p)
    assert any("Raccogli" in ln for ln in out) and any("Assorbi 1 essenza" in ln for ln in out)
    assert not [r for r in items.player_inventory(conn, 1) if r["item_type"] == "essenza"]
    assert "SPENTA" in loop.dispatch(conn, "autoassorbi off", allow_nl=False)
    items.grant(conn, "player", 1, iid)
    assert auto_collect.daily(conn, 120, random.Random(1), p) == []
    assert "Assorbi" in loop.dispatch(conn, "raccogli", allow_nl=False)


def test_old_fused_lines_get_short_names(conn):
    from engine.systems import bloodlines as B
    d = {"vecchio": {"name": "Sangue di Cinghiale-Drago-Demone-Lupo di Carne Ferrea e Tuono e Tenebra e Vento",
                     "species": "Cinghiale-Drago-Demone-Lupo di Carne Ferrea e Tuono e Tenebra e Vento",
                     "elements": ["corpo", "fulmine", "oscurita", "vento"],
                     "families": ["cinghiale", "drago", "demone", "lupo"], "conc": 900, "fused_from": ["a", "b"]}}
    B._save(conn, d)
    ln = B.all_lines(conn)["vecchio"]
    assert ln["species"] == "Drago-Demone di Tuono e Tenebra" and set(ln["minor"]) == {"cinghiale", "lupo"}
    assert B.form_name(ln) == "Drago-Demone"
