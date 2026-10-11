"""
Jade Immortal — DASHBOARD (si gioca nel browser).

  python dashboard.py            apre il gioco su http://127.0.0.1:8765 nel tuo browser
  python dashboard.py --porta N  usa un'altra porta
  python dashboard.py --no-browser

Il terminale (main.py) continua a funzionare: è la stessa partita, lo stesso salvataggio.
Non usarli entrambi nello stesso momento.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

from engine.db import init_db
from engine.generators.world_gen import generate_if_empty
from engine.web.server import serve


def main() -> None:
    ap = argparse.ArgumentParser(description="Jade Immortal — dashboard nel browser")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    init_db()
    if generate_if_empty():
        print("[Nuovo mondo generato]")
    httpd = serve(port=a.porta)
    url = f"http://127.0.0.1:{a.porta}/"
    print(f"Jade Immortal è in esecuzione su {url}  (Ctrl+C per chiudere)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nA presto, coltivatore.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
