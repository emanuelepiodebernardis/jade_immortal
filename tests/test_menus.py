"""Menu a sezioni (setta, arti, coltivazione, eventi, regni, famiglia), arti multiple e ascesa di setta."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, sects, state, guild, sect_menu, menus, professions, encounters,
                            suggestions)
from engine.cli import loop, story_cmds


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "menus.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=11, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _join(conn):
    hq = conn.execute("SELECT home_location_id FROM factions WHERE status='active' AND home_location_id "
                      "IS NOT NULL LIMIT 1;").fetchone()["home_location_id"]
    entities.move_player(conn, 1, hq)
    res = sects.join_sect(conn, 0, 1)
    assert res["status"] == "joined"
    return res


# ---------------- arti ----------------

def test_several_arts_grow_together_and_none_is_allowed(conn):
    loop.dispatch(conn, "arti alchimia", allow_nl=False)
    loop.dispatch(conn, "arti forgia", allow_nl=False)
    assert professions.practiced(conn) == ["alchimia", "forgia"]
    assert professions.profession(conn) == "alchimia"            # la prima diventa principale
    for _ in range(4):
        loop.dispatch(conn, "train", allow_nl=False)
    assert professions.xp(conn, 1, "alchimia") > 0 and professions.xp(conn, 1, "forgia") > 0
    loop.dispatch(conn, "arti nessuna", allow_nl=False)
    assert professions.practiced(conn) == []
    assert professions.has(conn, "forgia")                        # ciò che hai imparato resta tuo
    out = loop.dispatch(conn, "arti tutte", allow_nl=False)
    assert "tutte" in out and len(professions.practiced(conn)) == len(professions.PROFESSIONS)


def test_switching_main_art_loses_nothing_and_craft_by_name(conn):
    professions.choose(conn, 1, "alchimia")
    professions.add_xp(conn, 1, 40)
    lv = professions.level(conn, 1, "alchimia")
    professions.choose(conn, 1, "talismani")
    assert professions.profession(conn) == "talismani"
    assert professions.level(conn, 1, "alchimia") == lv          # niente esperienza perduta
    professions.give(conn, 1, "erbe", 20)
    out = professions.craft(conn, 0, random.Random(1), _p(conn), "alchimia 1")
    assert "Crei" in out or "fallisce" in out


def test_legacy_single_art_save_is_migrated(conn):
    state.set(conn, "profession", "forgia")
    state.set(conn, "profession_xp", "60")
    assert professions.practiced(conn) == ["forgia"]
    assert professions.xp(conn, 1, "forgia") == 60


# ---------------- menu ----------------

def test_every_menu_builds_and_numbers_run_its_actions(conn):
    for key in menus.NAMES:
        m = menus.build(conn, _p(conn), key)
        assert m["title"] and isinstance(m["sections"], list)
    _join(conn)
    for key in menus.NAMES:
        m = menus.build(conn, _p(conn), key)
        for s in m["sections"]:
            for a in s["actions"]:
                assert a["ok"] or a["why"]                   # chi non può, dice perché
    txt = loop.dispatch(conn, "setta", allow_nl=False)
    assert "Ascesa" in txt and "[1]" in txt
    # dopo un menu i numeri restano i suoi (niente azioni suggerite al loro posto)
    tail = story_cmds.after_command(conn, _p(conn))
    assert "Azioni suggerite" not in tail
    first = suggestions.stored(conn)[0]
    out = loop.dispatch(conn, "1", allow_nl=False)
    assert out.startswith(f"(→ {first})")


def test_merit_shop_promotion_and_stipend(conn):
    _join(conn)
    guild.add_merit(conn, 300, 1)
    out = loop.dispatch(conn, "setta compra 2", allow_nl=False)
    assert "Spendi" in out
    out = loop.dispatch(conn, "setta stipendio", allow_nl=False)
    assert "stipendio" in out
    assert "già" in loop.dispatch(conn, "setta stipendio", allow_nl=False)
    before = sects.get_membership(conn)["rank"]
    out = loop.dispatch(conn, "setta promozione", allow_nl=False)
    assert sects.get_membership(conn)["rank"] != before, out


# ---------------- ascesa ----------------

def test_merit_threshold_brings_emissaries_and_loyalty_raises_the_bar(conn):
    _join(conn)
    need = sect_menu.requirements(conn, 1)["need_merit"]
    guild.add_merit(conn, need, 1)
    lines = sect_menu.daily(conn, 500, random.Random(2), _p(conn))
    assert lines
    sc = encounters.pending(conn)
    assert sc and sc["key"] == sect_menu.SCENE_KEY and len(sc["choices"]) == 5
    out = loop.dispatch(conn, "setta rifiuta", allow_nl=False)
    assert "lealtà" in out or "Rimandi" in out
    assert not sect_menu.offers(conn, 1) and not encounters.pending(conn)
    assert sect_menu.requirements(conn, 1)["need_merit"] > need


def test_accepting_an_offer_moves_you_and_resets_merit(conn):
    _join(conn)
    old = sects.get_membership(conn)
    guild.add_merit(conn, 2000, 1)
    sect_menu.daily(conn, 500, random.Random(2), _p(conn))
    out = loop.dispatch(conn, "1", allow_nl=False)              # la scena: prima offerta
    new = sects.get_membership(conn)
    assert new["faction_id"] != old["faction_id"] and (new["sect_tier"] or 1) > (old["sect_tier"] or 1), out
    assert sect_menu.requirements(conn, 1)["earned"] == 0
    assert guild.get_merit(conn, 1) == 0


def test_dashboard_menu_endpoint(conn, monkeypatch):
    from contextlib import contextmanager
    from engine.web import game

    @contextmanager
    def tx(db_path=None):
        yield conn
    monkeypatch.setattr(game, "transaction", tx)
    _join(conn)
    conn.commit()
    m = game.menu_data("setta")
    assert m["key"] == "setta" and any(s["title"].startswith("Ascesa") for s in m["sections"])
    assert "errore" in game.menu_data("nulla")


def test_abode_upgrade_max_spends_what_it_can_and_menu_offers_it(conn):
    from engine.systems import cave_abode
    loc = conn.execute("SELECT id FROM locations WHERE location_type='mountain' LIMIT 1;").fetchone()["id"]
    entities.move_player(conn, 1, loc)
    sects.grant_resource(conn, "pietre_spirituali", 3000, 1)
    loop.dispatch(conn, "dimora reclama", allow_nl=False)
    m = menus.build(conn, _p(conn), "dimora")
    top = m["sections"][0]["actions"][0]
    assert top["cmd"] == "dimora potenzia max" and top["ok"]
    stones = sects.get_resource(conn, "pietre_spirituali", 1)
    steps, cost = cave_abode.plan_max(cave_abode.get(conn), stones)
    out = loop.dispatch(conn, "dimora potenzia max", allow_nl=False)
    assert "potenziament" in out
    left = sects.get_resource(conn, "pietre_spirituali", 1)
    assert left == stones - cost
    ab = cave_abode.get(conn)
    nxt = min(cave_abode.upgrade_cost(k, int(ab["wings"].get(k, 0))) for k in cave_abode.WINGS)
    assert nxt > left                                   # non resta nulla che si possa ancora pagare
    out = loop.dispatch(conn, "dimora potenzia qi max", allow_nl=False)
    assert "Non hai abbastanza pietre" in out or "potenziament" in out


def test_one_command_absorbs_every_essence(conn):
    from engine.systems import items
    for i in range(3):
        iid = items.create_item(conn, f"Essenza di Sangue {i}", "essenza", "raro", "x", {"grow_strength": 1})
        items.grant(conn, "player", 1, iid)
    iid = items.create_item(conn, "Essenza del Dao «spada»", "essenza", "raro", "x", {"dao_key": "spada", "dao_gain": 2})
    items.grant(conn, "player", 1, iid, 2)
    out = loop.dispatch(conn, "use essenze", allow_nl=False)
    assert "Assorbi" in out
    left = [r for r in items.player_inventory(conn, 1) if r["item_type"] == "essenza"]
    assert not left, out
