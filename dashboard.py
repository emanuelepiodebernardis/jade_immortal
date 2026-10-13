"""
Jade Immortal — DASHBOARD (si gioca nel browser).

  python dashboard.py            apre il gioco su http://127.0.0.1:8765 nel tuo browser
  python dashboard.py --porta N  usa un'altra porta
  python dashboard.py --no-browser
  python dashboard.py --rete     anche dagli altri dispositivi di casa (telefono sulla stessa Wi-Fi)
  python dashboard.py --no-reload  non riavviarti da solo quando il codice del gioco cambia

Quando il codice del gioco cambia (un aggiornamento), la dashboard se ne accorge e si RIAVVIA DA SOLA
in un paio di secondi: basta ricaricare la pagina. La partita è salvata, non si perde nulla.

Il terminale (main.py) continua a funzionare: è la stessa partita, lo stesso salvataggio.
Non usarli entrambi nello stesso momento.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from engine.db import init_db
from engine.generators.world_gen import generate_if_empty
from engine.web.server import serve


ROOT = Path(__file__).resolve().parent


def _code_stamp() -> float:
    """L'ultima modifica a un file del gioco (codice e pagina)."""
    newest = 0.0
    for folder in (ROOT / "engine",):
        for f in folder.rglob("*"):
            if f.suffix in (".py", ".js", ".html", ".css") and "__pycache__" not in f.parts:
                try:
                    newest = max(newest, f.stat().st_mtime)
                except OSError:
                    pass
    return newest


_RESTART = threading.Event()


def _watch_and_restart(httpd) -> None:
    """Se il codice cambia, ferma il server: main() lo riavvia con il codice nuovo."""
    start = _code_stamp()
    while True:
        time.sleep(2)
        if _code_stamp() > start:
            time.sleep(1.5)                                    # lascia finire di scrivere tutti i file
            print("\n[Il gioco è stato aggiornato: la dashboard si riavvia con il codice nuovo…]", flush=True)
            _RESTART.set()
            httpd.shutdown()
            return


def _restart() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-browser"] + ["--no-browser"]
    if os.name == "nt":                                        # su Windows execv non sostituisce il processo
        import subprocess
        subprocess.Popen([sys.executable, str(ROOT / "dashboard.py")] + args)
        sys.exit(0)
    os.execv(sys.executable, [sys.executable, str(ROOT / "dashboard.py")] + args)


def main() -> None:
    ap = argparse.ArgumentParser(description="Jade Immortal — dashboard nel browser")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-reload", action="store_true", help="non riavviarti da solo quando il codice cambia")
    ap.add_argument("--rete", action="store_true",
                    help="ascolta sulla rete di casa (per il telefono): nessuna password, usalo solo in casa")
    a = ap.parse_args()
    init_db()
    if generate_if_empty():
        print("[Nuovo mondo generato]")
    httpd = serve(host="0.0.0.0" if a.rete else "127.0.0.1", port=a.porta)
    url = f"http://127.0.0.1:{a.porta}/"
    print(f"Jade Immortal è in esecuzione su {url}  (Ctrl+C per chiudere)")
    if a.rete:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
        except OSError:
            ip = "<indirizzo del PC>"
        print(f"Dal telefono (stessa Wi-Fi): http://{ip}:{a.porta}/  — nessuna password: usalo solo in casa.")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    if not a.no_reload:
        threading.Thread(target=_watch_and_restart, args=(httpd,), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nA presto, coltivatore.")
    finally:
        httpd.server_close()
    if _RESTART.is_set():
        _restart()


if __name__ == "__main__":
    main()
