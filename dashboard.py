"""
Jade Immortal — DASHBOARD (si gioca nel browser).

  python dashboard.py            apre il gioco su http://127.0.0.1:8765 nel tuo browser
  python dashboard.py --porta N  usa un'altra porta
  python dashboard.py --no-browser
  python dashboard.py --rete     anche dagli altri dispositivi di casa (telefono sulla stessa Wi-Fi)

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
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nA presto, coltivatore.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
