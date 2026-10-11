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
