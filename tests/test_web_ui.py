"""Aggiornamento 70: test automatici dell'interfaccia — il server risponde, le schede esistono, il JS è valido.

Non serve un browser: si avvia il server su un mondo di prova e si interrogano le API che la dashboard usa.
"""
from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import threading
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character

STATIC = Path(__file__).resolve().parent.parent / "engine" / "web" / "static"


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    from engine.web import game, server
    p = tmp_path_factory.mktemp("ui") / "ui.db"
    old_path, old_tx = db.DB_PATH, game.transaction
    db.DB_PATH = p
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 4)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    c.close()

    @contextmanager
    def tx(db_path=None):
        conn = db.connect(p)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    game.transaction = tx
    httpd = server.serve(port=0)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    db.DB_PATH, game.transaction = old_path, old_tx


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        assert r.status == 200
        return json.loads(r.read().decode())


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        assert r.status == 200
        return json.loads(r.read().decode())


@pytest.mark.parametrize("path", ["/api/stato", "/api/zaino", "/api/equip", "/api/gear", "/api/codex", "/api/scelte",
                                  "/api/mappa", "/api/immagini"])
def test_api_endpoints(base, path):
    _get(base + path)


def test_state_has_dashboard_fields(base):
    s = _get(base + "/api/stato")
    for k in ("todo", "badges", "luogo"):
        assert k in s
    assert any(t["icon"] == "🧭" for t in s["todo"])            # i primi passi


@pytest.mark.parametrize("menu", ["via:forza", "via:coltivazione", "stagione", "setta", "eventi"])
def test_menus_render(base, menu):
    m = _get(base + "/api/menu/" + menu)
    assert m.get("title") and isinstance(m.get("sections"), list)


def test_commands_round_trip(base):
    for cmd in ("equip", "guida", "stagione", "codex duello", "forza"):
        r = _post(base + "/api/comando", {"cmd": cmd})
        assert "log" in r and "Traceback" not in (r["log"] or "")


def test_every_menu_tab_exists():
    """Ogni scheda «m:<menu>» della dashboard ha un menu dietro."""
    from engine.systems import menus
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    keys = set(re.findall(r'"m:([a-z_]+)"', js))
    known = set(menus._builders().keys()) if hasattr(menus, "_builders") else None
    if known is None:
        pytest.skip("registro dei menu non introspezionabile")
    missing = {k for k in keys if k not in known and k != "via"}
    assert not missing, missing


@pytest.mark.skipif(shutil.which("node") is None, reason="node non installato")
@pytest.mark.parametrize("f", ["app.js", "viz.js"])
def test_js_syntax(f):
    r = subprocess.run(["node", "--check", str(STATIC / f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_export_import_round_trip(base):
    import base64
    with urllib.request.urlopen(base + "/api/esporta", timeout=30) as r:
        data = r.read()
        assert r.status == 200 and data.startswith(b"SQLite format 3")
        assert "attachment" in r.headers.get("Content-Disposition", "")
    res = _post(base + "/api/importa", {"dati": base64.b64encode(data).decode()})
    assert res["ok"], res
    bad = _post(base + "/api/importa", {"dati": base64.b64encode(b"ciao").decode()})
    assert not bad["ok"]
    assert "testo" in _get(base + "/api/ultimo_salvataggio")
    assert _get(base + "/api/album")["pagine"]
