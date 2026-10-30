"""
I MINIGIOCHI DI MANO (Aggiornamento 71) — la forgia e il calderone non sono più solo un clic.

La dashboard, prima di mandare 'equip forgia …' o 'craft …', apre un piccolo gioco di tempismo (il fuoco del
calderone, il ritmo del martello) e aggiunge al comando la tua QUALITÀ: « ~q83 » (0-100). Qui la si legge:

  quality(conn)   0.0-1.0 per il comando in corso (0.5 se hai saltato il gioco o giochi da riga di comando)
  bonus(conn)     da −0.12 a +0.18: quanto sposta la riuscita (alchimia) o la rarità (forgia)

Dal terminale si può scrivere a mano, o semplicemente non scriverla: vale il caso, come prima.
"""

from __future__ import annotations

import re

from engine.systems import state

KEY = "minigame_q"
MARK = re.compile(r"\s+~q(\d{1,3})\s*$")


def strip(conn, raw: str) -> str:
    """Toglie il segno di qualità dal comando e lo ricorda per il comando in corso."""
    m = MARK.search(raw or "")
    if not m:
        state.delete(conn, KEY)
        return raw
    state.set(conn, KEY, str(max(0, min(100, int(m.group(1))))))
    return raw[: m.start()]


def quality(conn) -> float:
    v = state.get_int(conn, KEY, -1)
    return 0.5 if v < 0 else v / 100.0


def bonus(conn) -> float:
    q = quality(conn)
    return (q - 0.5) * (0.36 if q >= 0.5 else 0.24)


def verdict(conn) -> str:
    v = state.get_int(conn, KEY, -1)
    if v < 0:
        return ""
    return ("Un lavoro perfetto." if v >= 90 else "Mano sicura." if v >= 70 else "Fuoco incerto." if v >= 40
            else "Il fuoco ti sfugge di mano.") + f" (tempismo {v}/100)"
