"""
Server HTTP della dashboard — solo libreria standard (nessuna dipendenza da installare).

Ascolta su 127.0.0.1 (solo il tuo PC). Rotte:
  GET  /                    la pagina
  GET  /static/<file>       stile e script
  GET  /api/stato           istantanea JSON (barra in alto, luogo, scena, suggerimenti, mete)
  POST /api/comando         {"cmd": "..."} → esegue un comando come nel terminale
  GET  /api/pannello/<n>    personaggio | tesori | storia | mondo | aiuto
  GET  /api/menu/<n>        setta | arti | coltivazione | eventi | regni | famiglia | menu (sezioni e azioni)
  GET  /api/mappa           grafo dei luoghi intorno a te
  GET  /api/nuovo           opzioni per creare il personaggio
  POST /api/nuovo           {"origine","destino","nome","rivali"}
  GET  /api/morte           epilogo ed eredità
  POST /api/rinasci         {"origine","destino","nome","eredita"}
  GET  /api/auto?giorni=N   pilota automatico dal vivo (Server-Sent Events, un giorno alla volta)
  POST /api/auto/stop       interrompe il pilota
"""

from __future__ import annotations

import json
import mimetypes
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from engine.web import game

STATIC = Path(__file__).parent / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "JadeImmortal/1.0"

    def log_message(self, fmt, *args):          # silenzioso: il terminale resta pulito
        pass

    # ---------- utilità ----------
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _error(self, e: Exception) -> None:
        traceback.print_exc()
        self._json({"errore": f"{type(e).__name__}: {e}"}, 500)

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        try:
            if path in ("/", "/index.html"):
                return self._file(STATIC / "index.html")
            if path.startswith("/static/"):
                f = (STATIC / path[len("/static/"):]).resolve()
                if STATIC.resolve() in f.parents and f.is_file():
                    return self._file(f)
                return self._send(404, b"non trovato", "text/plain")
            if path == "/api/stato":
                ph = game.phase()
                return self._json(game.state_snapshot() if ph == "gioco" else {"fase": ph})
            if path.startswith("/api/menu/"):
                return self._json(game.menu_data(path.rsplit("/", 1)[-1]))
            if path.startswith("/api/pannello/"):
                return self._json(game.panel(path.rsplit("/", 1)[-1]))
            if path == "/api/obiettivi":
                return self._json(game.objectives_data())
            if path == "/api/persone":
                return self._json(game.people_data())
            if path == "/api/merito":
                return self._json(game.merit_preview())
            if path == "/api/legami":
                return self._json(game.bonds_data())
            if path == "/api/mondo":
                return self._json(game.world_data())
            if path == "/api/zaino":
                return self._json(game.items_data())
            if path == "/api/cronaca":
                return self._json(game.chronicle_data("tutte" in url.query))
            if path == "/api/salvataggi":
                return self._json(game.saves())
            if path == "/api/dao":
                return self._json(game.dao_data())
            if path == "/api/mappa":
                return self._json(game.map_data())
            if path == "/api/nuovo":
                return self._json(game.creation_options())
            if path == "/api/morte":
                info = game.death_info()
                if "vita" in info:
                    info.update(game.creation_options(info["vita"]))
                return self._json(info)
            if path == "/api/auto":
                days = int((parse_qs(url.query).get("giorni") or ["7"])[0])
                return self._auto(max(1, min(60, days)))
            return self._send(404, b"non trovato", "text/plain")
        except Exception as e:
            return self._error(e)

    def _file(self, f: Path) -> None:
        # tipi espliciti: su Windows il registro a volte associa .js a text/plain
        ctype = {".html": "text/html", ".js": "application/javascript", ".css": "text/css",
                 ".svg": "image/svg+xml", ".png": "image/png"}.get(f.suffix.lower()) \
            or mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._send(200, f.read_bytes(), ctype)

    def _auto(self, days: int) -> None:
        """Server-Sent Events: un messaggio per giorno, finché il pilota non si ferma."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        game.STOP.clear()

        def emit(obj):
            self.wfile.write(("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()

        try:
            for i in range(days):
                if game.STOP.is_set():
                    emit({"fine": True, "stop": "interrotto da te"})
                    return
                r = game.auto_day()
                emit({"giorno": i + 1, "di": days, "log": r["log"]})
                if r["stop"]:
                    emit({"fine": True, "stop": r["stop"]})
                    return
            emit({"fine": True, "stop": None})
        except (BrokenPipeError, ConnectionResetError):
            game.STOP.set()

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        b = self._body()
        try:
            if path == "/api/comando":
                return self._json(game.turn(str(b.get("cmd", ""))[:300]))
            if path == "/api/nuovo":
                return self._json({"log": game.create(b.get("origine", "mortale"), b.get("destino", ""),
                                                      b.get("nome", ""), b.get("rivali", "normale"),
                                                      bool(b.get("senza_ritorno")))})
            if path == "/api/reincarnati":
                return self._json(game.voluntary())
            if path == "/api/nuovo_mondo":
                return self._json({"log": game.new_world()})
            if path == "/api/rinasci":
                return self._json({"log": game.reincarnate(b.get("origine", "mortale"), b.get("destino", ""),
                                                           b.get("nome", ""), b.get("eredita", [0]))})
            if path == "/api/intro":
                return self._json({"log": game.intro()})
            if path == "/api/auto/stop":
                game.STOP.set()
                return self._json({"ok": True})
            return self._send(404, b"non trovato", "text/plain")
        except Exception as e:
            return self._error(e)


def serve(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd
