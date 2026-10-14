"""Dashboard nel browser: il ponte col motore (engine/web/game.py) e il server HTTP."""
from __future__ import annotations

import json
import random
import threading
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest

from engine import db
from engine.core import tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.web import game, server


@pytest.fixture()
def world(tmp_path: Path, monkeypatch):
    p = tmp_path / "web.db"
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
    return p, tx


def test_new_game_turn_and_state(world):
    _p, tx = world
    assert game.phase() == "nuovo"
    opts = game.creation_options()
    assert opts["origini"] and opts["destini"] and opts["rivali"]
    out = game.create("mortale", opts["destini"][0]["key"], "Lin Feng", "normale")
    assert "Lin Feng" in out and game.phase() == "gioco"
    s = game.state_snapshot()
    assert s["nome"] == "Lin Feng" and s["luogo"]["name"] and s["uscite"]
    assert s["suggerimenti"]
    r = game.turn("train")
    assert r["log"] and "\x1b[" not in r["log"]
    assert game.state_snapshot()["esperienza"] > 0


def test_panels_never_change_the_world(world):
    _p, tx = world
    game.create("mortale", "", "A", "normale")
    with tx() as c:
        t0 = tick.get_tick(c)
    for name in game.PANELS:
        parts = game.panel(name)
        assert parts and all(isinstance(x["text"], str) for x in parts)
    with tx() as c:
        assert tick.get_tick(c) == t0


def test_map_dao_and_autopilot_day(world):
    game.create("mortale", "", "A", "normale")
    m = game.map_data()
    assert any(n["here"] for n in m["nodes"]) and m["edges"]
    assert isinstance(game.dao_data(), list)
    r = game.auto_day()
    assert "log" in r


def test_death_and_rebirth(world):
    _p, tx = world
    game.create("mortale", "", "A", "normale")
    with tx() as c:
        c.execute("UPDATE players SET status='dead';")
    assert game.phase() == "morto"
    info = game.death_info()
    if "salvato" in info:                       # una fenice o un clone può salvarti
        return
    assert info["epilogo"] and info["eredita"]
    assert game.death_info()["epilogo"] == info["epilogo"]      # registrata una volta sola
    out = game.reincarnate("mortale", "", "B", 0)
    assert "Rinasci" in out and game.phase() == "gioco"


def test_http_server_end_to_end(world):
    game.create("mortale", "", "A", "normale")
    httpd = server.serve(port=0)
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        html = urllib.request.urlopen(base + "/").read().decode()
        assert "Jade Immortal" in html
        assert urllib.request.urlopen(base + "/static/app.js").status == 200
        st = json.loads(urllib.request.urlopen(base + "/api/stato").read())
        assert st["fase"] == "gioco"
        req = urllib.request.Request(base + "/api/comando", data=json.dumps({"cmd": "look"}).encode(),
                                     headers={"Content-Type": "application/json"})
        assert json.loads(urllib.request.urlopen(req).read())["log"]
        ev = urllib.request.urlopen(base + "/api/auto?giorni=1").read().decode()
        assert '"fine": true' in ev
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/static/../../engine/db.py")
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_two_fragments_and_realm_memory(world):
    _p, tx = world
    from engine.systems import rebirth, cult_mods
    game.create("mortale", "", "A", "normale")
    with tx() as c:
        rebirth.remember_realm(c, 5)
        c.execute("UPDATE players SET status='dead';")
    info = game.death_info()
    if "salvato" in info:
        return
    n = len(info["eredita"])
    out = game.reincarnate("mortale", "", "B", [0, 1] if n > 2 else [0])
    assert "Rinasci" in out
    with tx() as c:
        m, labels = cult_mods.cultivation_mult(c, 1, None)
        assert any("memoria delle vite" in x for x in labels)
        assert rebirth.memory_bt_bonus(c, 1) > 0


def test_senza_ritorno_archives_and_starts_a_new_world(world, monkeypatch):
    p, tx = world
    from engine.systems import rebirth
    import engine.db as _db
    monkeypatch.setattr(_db, "DB_PATH", p)
    game.create("mortale", "", "A", "normale", hardcore=True)
    with tx() as c:
        assert rebirth.hardcore(c)
        c.execute("UPDATE players SET status='dead';")
    info = game.death_info()
    if "salvato" in info:
        return
    assert info["senza_ritorno"]
    monkeypatch.setattr("engine.generators.world_gen.transaction", tx, raising=False)
    msg = game.new_world()
    assert "archivio_" in msg and list((p.parent / "saves").glob("archivio_*.db"))
    assert game.phase() == "nuovo"


def test_objectives_people_and_voluntary_rebirth(world):
    _p, tx = world
    game.create("mortale", "", "A", "normale")
    for _ in range(3):
        game.turn("train")
    o = game.objectives_data()
    assert set(o) == {"primari", "secondari", "missioni", "indagini"} and o["primari"]
    pp = game.people_data()
    assert pp["io"]["potenza"] > 0 and pp["alleati"]                  # la famiglia
    assert all("potenza" in c and "confronto" in c for c in pp["alleati"])
    m = game.merit_preview()
    assert m["punti"] > 0 and m["pietre"] == m["punti"] * 10
    r = game.voluntary()
    assert r["morto"] and game.phase() == "morto"
    info = game.death_info()
    assert "salvato" not in info                                     # una scelta, non una disgrazia da evitare
    assert info["volontaria"] and info["frammenti"] >= len(info["eredita"]) - 1
    assert "Scelse la Ruota" in info["epilogo"]
    out = game.reincarnate("mortale", "", "B", list(range(len(info["eredita"]) - 1)))
    assert "pietre" in out and game.phase() == "gioco"
    from engine.systems import rebirth, sects
    with tx() as c:
        assert sects.get_resource(c, "pietre_spirituali", 1) >= m["pietre"]
        assert rebirth.samsara_cult_mult(c)[0] > 1.0
        assert not rebirth.voluntary_pending(c)


def test_restart_command_sets_flag(world):
    _p, tx = world
    game.create("mortale", "", "A", "normale")
    game.turn("ricomincia")
    from engine.systems import rebirth, state
    with tx() as c:
        assert state.get(c, rebirth.RESTART_KEY) != "1"              # senza conferma non succede nulla
    game.turn("ricomincia conferma")
    with tx() as c:
        assert state.get(c, rebirth.RESTART_KEY) == "1"


def test_charts_graph_book_and_autopilot_summary(world):
    import random as _r
    _p, tx = world
    game.create("mortale", "", "Lin Feng", "normale")
    game.turn("train")
    game.turn("sleep")
    ch = game.charts_data()
    assert ch["storia"] and set(ch["radar"]) >= {"Attacco", "Difesa", "Dao"}
    from engine.systems import feuds, npc_factory, rewards
    from engine.core import entities as ents
    with tx() as conn:
        p = ents.get_player(conn)
        nid = npc_factory.spawn(conn, _r.Random(1), archetype="anziano", location_id=p.location_id, tier=2)
        for s in range(8):
            if feuds.on_kill(conn, 0, _r.Random(s), p, ents.get_npc(conn, nid)):
                break
        rewards.grant(conn, _r.Random(2), p, rank=1)
    g = game.graph_data()
    groups = {n["group"] for n in g["nodi"]}
    assert "io" in groups and ("faida" in groups or "famiglia" in groups)
    b = game.book_data()
    assert any(pg["cat"] == "tesori" for pg in b["pagine"])
    a = game.summary_snapshot()
    game.turn("sleep")
    d = game.summary_diff(a, game.summary_snapshot())
    assert d["giorni"] >= 1 and "regno_a" in d


def test_creation_with_a_legendary_body(world):
    out = game.create("mortale", "", "Prova", "normale", False, True)
    assert "corpo leggendario" in out


def test_hero_data_and_rich_map(world):
    game.create("mortale", "", "Han", "normale")
    h = game.hero_data()
    assert h["finestra"]["livello"] >= 1 and len(h["finestra"]["attributi"]) == 6
    assert len(h["radici"]) == 9 and len(h["talento"]) == 5 and len(h["profondi"]["dao"]) == 3
    m = game.map_data(9)
    assert all({"people", "beasts", "threats", "sect"} <= set(n) for n in m["nodes"])
    s = game.state_snapshot()
    assert "livello" in s and "punti" in s


def test_click_menus_market_auction_recipes_board(world):
    game.create("mortale", "", "Han", "normale")
    for key in ("mercato", "asta", "ricette", "bacheca"):
        m = game.menu_data(key)
        assert m["title"] and m["sections"], key


def test_place_tiles_are_actions(world):
    game.create("mortale", "", "Han", "normale")
    s = game.state_snapshot()
    cmds = {t["cmd"] for t in s["azioni_luogo"]}
    assert not cmds & {"train", "sleep", "tempra", "breakthrough"}      # quelli stanno solo in alto a sinistra
    assert all(t["ok"] or t["why"] for t in s["azioni_luogo"])
    assert {"breakthrough", "raccogli", "tempra"} <= set(s["rapidi"])
