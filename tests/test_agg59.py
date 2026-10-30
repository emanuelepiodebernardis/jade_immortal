"""Aggiornamento 59: difficoltà, «La tua Via», varianti di testo delle trame."""
import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import calibration, pursuers, intrigue_variants, intrigue_data, state, character


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a59.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    c.commit()
    yield c
    c.close()


def test_presets_apply_in_place():
    try:
        calibration.apply("spietato")
        assert calibration.THREAT_CHANCE == calibration.PRESETS["spietato"]["THREAT_CHANCE"]
        assert pursuers.BANDS["nemesi"] == calibration.PRESETS["spietato"]["PURSUER_BANDS"]["nemesi"]          # il dict importato altrove cambia con lui
        calibration.apply("sereno")
        assert pursuers.BANDS["nemesi"] == (0.8, 1.1)
        assert calibration.AMBUSH_GAP_DAYS["A"] == 4
    finally:
        calibration.apply(calibration.DEFAULT)


def test_presets_get_harder():
    P = calibration.PRESETS
    for a, b in (("sereno", "normale"), ("normale", "spietato")):
        assert P[a]["THREAT_CHANCE"] < P[b]["THREAT_CHANCE"]
        assert P[a]["LOSS_DEATH_CHANCE"] <= P[b]["LOSS_DEATH_CHANCE"]
        assert P[a]["PURSUER_BANDS"]["nemesi"][1] < P[b]["PURSUER_BANDS"]["nemesi"][1]
        assert set(P[a]) == set(P[b])


def test_difficulty_command_and_state(conn):
    from engine.cli import loop
    try:
        out = loop.dispatch(conn, "difficolta", allow_nl=False)
        assert "Normale" in out and "Spietato" in out
        loop.dispatch(conn, "difficolta spietato", allow_nl=False)
        assert state.get(conn, "difficolta") == "spietato"
        assert calibration.THREAT_CHANCE == calibration.PRESETS["spietato"]["THREAT_CHANCE"]
        loop.dispatch(conn, "difficolta facile", allow_nl=False)        # alias
        assert calibration.current(conn) == "sereno"
    finally:
        calibration.apply(calibration.DEFAULT)


def test_difficulty_survives_rebirth():
    from engine.systems import rebirth
    assert "difficolta" in rebirth._WORLD_KEYS


def test_via_tabs(conn):
    from engine.core import entities
    from engine.systems import menus, via_menu
    p = entities.get_player(conn)
    for k in via_menu.KEYS:
        m = menus.build(conn, p, "via:" + k)
        assert m["tab"] == via_menu.GROUP_OF.get(k, k) and m["key"] == "via:" + k   # (Agg. 72) schede accorpate
        assert sum(t["on"] for t in m["tabs"]) == 1
    assert via_menu.tab_of("lignaggi") == "sangue" and via_menu.tab_of("boh") == via_menu.DEFAULT
    from engine.cli import loop
    out = loop.dispatch(conn, "via sangue", allow_nl=False)
    assert "Schede:" in out and "[🩸 Corpo]" in out   # (Agg. 73) le schede sono i pilastri


def test_variants_point_to_real_acts():
    tpls = {t["key"]: t for t in intrigue_data.TEMPLATES}
    assert len(intrigue_variants.VARIANTS) >= 12
    for k, acts in intrigue_variants.VARIANTS.items():
        assert k in tpls, k
        for i, texts in acts.items():
            assert 0 <= i < len(tpls[k]["acts"]) and len(texts) >= 2


def test_variant_pick_is_stable_and_varies():
    from engine.systems import intrigues
    opts = ["a", "b", "c"]
    assert intrigues._pick(opts, "5:0") == intrigues._pick(opts, "5:0")
    assert len({intrigues._pick(opts, f"{i}:0") for i in range(30)}) == 3
    assert intrigues._pick("solo", "x") == "solo"


def test_plot_scene_has_atmosphere_and_no_placeholders(conn):
    from engine.core import entities
    from engine.systems import intrigues
    p = entities.get_player(conn)
    out = intrigues.start(conn, p, "grotta_maestro", random.Random(3)) or ""
    assert "{" not in out and "volpe bianca" in out


# ---------------------------------------------------------------- tossine e Giudizio (Aggiornamento 60)

def test_purify_command(conn):
    from engine.core import entities
    from engine.systems import dao_heart, sects
    p = entities.get_player(conn)
    dao_heart._set_toxin(conn, 500)
    sects.grant_resource(conn, "pietre_spirituali", 1000, p.id)
    out = dao_heart.purify_command(conn, p)
    assert "Bagno di Qi" in out and dao_heart.toxin(conn) < 500 * 0.7
    again = dao_heart.purify_command(conn, p)
    assert "già fatto oggi" in again


def test_toxin_decays_faster_when_high(conn):
    from engine.systems import dao_heart
    dao_heart._set_toxin(conn, 1000)
    dao_heart.daily(conn, 0, random.Random(1), None)
    assert dao_heart.toxin(conn) < 1000 - 25
    dao_heart._set_toxin(conn, 200)
    dao_heart.on_breakthrough(conn)
    assert abs(dao_heart.toxin(conn) - 100) < 0.5


def test_use_all_keeps_cult_pills_when_blocked(conn):
    from engine.core import entities
    from engine.systems import dao_heart, items
    from engine.cli import loop
    p = entities.get_player(conn)
    iid = items.create_item(conn, "Pillola di Prova", "pillola", "comune", "test", {"cultivation_progress": 0.2})
    items.grant(conn, "player", p.id, iid, 3)
    dao_heart._set_toxin(conn, 200)
    out = loop.cmd_use_all(conn, p)
    assert "Lasci nello zaino 3" in out
    assert any(r["name"] == "Pillola di Prova" for r in items.player_inventory(conn, p.id))


def test_provoke_heaven(conn):
    from engine.core import entities
    from engine.systems import deep_dao
    p = entities.get_player(conn)
    d = deep_dao.get(conn)
    ok, why = deep_dao.provoke_status(conn, d, 100)
    assert not ok and "600" in why
    ok, _ = deep_dao.provoke_status(conn, d, 1000)
    assert ok
    out = deep_dao._provoke(conn, p, d, 1000)
    assert "Volontà" in out
    d = deep_dao.get(conn)
    assert d["will_npc"] and not deep_dao.provoke_status(conn, d, 1000)[0]
