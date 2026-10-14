"""
LA VOLONTÀ DEL MORTALE — chi nasce senza talento sale con la fatica.

Nelle grandi storie il mortale senza doni (il ragazzo di campagna, lo «spazzatura» del clan) non vince
con il talento: vince perché non smette mai. Così qui: il Mortale comune accumula GIORNI DI FATICA
(un giorno conta se quel giorno ti sei allenato) e ognuno gli dà un poco di più:

  · coltivazione +1,2% per giorno di fatica, fino a +90% (dopo 75 giorni: alla pari con un genio);
  · sfondamenti +8% (la testardaggine di chi ha fallito mille volte);
  · alla rinascita metà della fatica resta: la volontà non muore col corpo.
"""

from __future__ import annotations

from engine.systems import state

KEY = "tenacity_days"
PER_DAY = 0.012
CAP = 0.9
BT = 0.08


def active(conn, pid: int = 1) -> bool:
    from engine.systems import character
    p = character.get_profile(conn, "player", pid)
    return bool(p and (p["origin"] if "origin" in p.keys() else "") == "mortale")


def days(conn) -> int:
    return state.get_int(conn, KEY, 0)


def mark(conn, t: int, pid: int = 1) -> None:
    """Un giorno di fatica (al primo allenamento della giornata)."""
    if not active(conn, pid):
        return
    day = t // 120
    if state.get_int(conn, "tenacity_last", -1) == day:
        return
    state.set(conn, "tenacity_last", str(day))
    state.set(conn, KEY, str(days(conn) + 1))


def cultivation_mult(conn, pid: int = 1) -> tuple[float, str]:
    if not active(conn, pid):
        return 1.0, ""
    m = 1.0 + min(CAP, PER_DAY * days(conn))
    return m, f"la volontà del mortale ({days(conn)} giorni di fatica)"


def bt_bonus(conn, pid: int = 1) -> float:
    return BT if active(conn, pid) else 0.0


def on_rebirth(conn) -> None:
    state.set(conn, KEY, str(days(conn) // 2))
