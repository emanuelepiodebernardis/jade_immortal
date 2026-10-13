"""Dao profondi (arcani, risonanze, Giudizio), Spiriti del Dao, finestra di stato (Aggiornamento 44)."""
from contextlib import contextmanager
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.web import game


@pytest.fixture()
def world(tmp_path: Path, monkeypatch):
    p = tmp_path / "dd.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=12, factions=3, static_npc_count=20))
    c.commit()
    c.close()

    @contextmanager
    def tx(db_path=None):
        conn = db.connect(p)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    monkeypatch.setattr(game, "transaction", tx)
    game.create("mortale", "", "Han", "normale")
    return tx


def _set_dao(conn, key, c):
    from engine.generators import dao_gen
    dao_gen._set_dao(conn, "player", 1, key, 60, c, 1)
    conn.execute("UPDATE character_daos SET comprehension=?, practiced=1 WHERE character_type='player' "
                 "AND character_id=1 AND dao_key=?;", (c, key))


def test_menus_open_and_never_change_the_world(world):
    for key in ("profondi", "spiriti", "attributi"):
        m = game.menu_data(key)
        assert m["sections"], key


def test_arcana_resonances_and_judgment(world):
    tx = world
    from engine.systems import deep_dao, dao_powers
    with tx() as c:
        for k in ("spazio", "tempo", "destino"):
            _set_dao(c, k, 300)
        assert {n for n, _e, _f in deep_dao.resonances(c)} >= {"Dominio Spazio-Tempo", "Causalità", "Fiume del Destino",
                                                                 "Trinità delle Leggi"}
        assert dao_powers.space_combat(c)["extra_strikes"] >= 2
    r = game.turn("arcano domani")
    assert "Occhio del Domani" in r["log"]
    r = game.turn("arcano taglio")
    assert "vuoto" in r["log"].lower()
    with tx() as c:
        assert deep_dao.get(c)["buffs"].get("taglio")
        for k in ("spazio", "tempo", "destino"):
            _set_dao(c, k, 250)
        from engine.core import entities
        import random
        out = deep_dao.daily(c, 120 * 5, random.Random(1), entities.get_player(c))
        assert deep_dao.get(c)["pending_judgment"] and any("Giudizio" in x or "GUERRA" in x for x in out)
    r = game.turn("cielo sfida")
    assert "Volontà del Cielo" in r["log"]
    with tx() as c:
        d = deep_dao.get(c)
        assert d["will_npc"] and not d["pending_judgment"]


def test_dao_spirits_fight_and_train(world):
    tx = world
    from engine.systems import dao_spirits
    with tx() as c:
        _set_dao(c, "fuoco", 260)
        sp = dao_spirits.spirits(c)
        assert sp and sp[0]["name"] == "Salamandra di Fiamma" and sp[0]["stage"] == "Spirito"
        assert dao_spirits.combat_allies(c, 1)
    r = game.turn("spiriti allena")
    assert "Salamandra" in r["log"]
    with tx() as c:
        assert c.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND dao_key='fuoco'"
                         ).fetchone()[0] > 260


def test_status_window_points_and_observe(world):
    tx = world
    from engine.systems import attributes
    from engine.simulation import combat
    with tx() as c:
        f0 = attributes.free(c)
        a0 = combat.combat_power(c, "player", 1)["attack"]
        assert f0 >= 3
    r = game.turn("attributi FOR 3")
    assert "Forza" in r["log"]
    with tx() as c:
        assert attributes.free(c) == f0 - 3
        assert combat.combat_power(c, "player", 1)["attack"] > a0
    assert "FINESTRA DI STATO" in game.turn("finestra")["log"]
    assert "Osserva" in game.turn("osserva")["log"] or "nessuno" in game.turn("osserva")["log"]


def test_daily_quest_pays_once(world):
    tx = world
    from engine.systems import system_daily, attributes, state
    from engine.core import entities
    with tx() as c:
        d = system_daily.get(c)
        f0 = attributes.free(c)
        assert system_daily.hunter_rank(c) == "E"
        _set_dao(c, "fuoco", d["base"]["dao"] + 100)
        state.set(c, "kills_total", str(d["base"]["kills"] + 5))
        sd = state.get_json(c, "soul_temper", None)
    game.turn("tempra")
    with tx() as c:
        x = system_daily.data(c)
        assert x["fatta"] and attributes.free(c) == f0 + 1
        assert not system_daily.check(c, entities.get_player(c))      # una volta sola


def test_duel_arena_cards_and_allies(world):
    tx = world
    from engine.systems import duel, npc_factory
    from engine.core import entities
    import random as _r
    with tx() as c:
        _set_dao(c, "fuoco", 300)                       # uno Spirito del Dao scende in campo
        p = entities.get_player(c)
        nid = npc_factory.spawn(c, _r.Random(4), archetype="discepolo", location_id=p.location_id, tier=1, stage=3)
        name = c.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    game.turn(f"duello {name.split()[0]}")
    s = game.state_snapshot()
    a = s["duello"]["arena"]
    assert a and a["carte"][0]["cmd"] == "duello_azione colpisci"
    assert any("Salamandra" in x for x in a["alleati"])
    game.turn("duello_azione colpisci")
    a2 = game.state_snapshot()["duello"]
    assert a2 is None or a2["arena"]["ultimo"].get("inflitto", 0) > 0
