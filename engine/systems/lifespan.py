"""
DURATA DELLA VITA (寿元).

Un mortale sano vive 80 anni. Ogni volta che arrivi allo Strato 10 di un regno e lo
SUPERI (breakthrough riuscito), la tua durata massima di vita RADDOPPIA:
  regno 1 → 80 anni, regno 2 → 160, regno 3 → 320, …
I destini la modificano (malattie: Genio Malato −20, Stella Cadente −40; Sangue Longevo +40)
e gli Elisir di Longevità la allungano. Se l'età raggiunge il limite, muori di vecchiaia:
la tua vita riceve l'epilogo e puoi reincarnarti.
"""

from __future__ import annotations

import sqlite3

from engine.core import tick as tick_mod
from engine.systems import state

BASE_YEARS = 80


def base_years(conn: sqlite3.Connection, pid: int = 1) -> int:
    from engine.systems import destinies
    return max(20, BASE_YEARS + int(destinies.flag_value(conn, "lifespan_mod", pid, 0)))


def max_years(conn: sqlite3.Connection, pid: int = 1) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    return int(base_years(conn, pid) * (2 ** (tier - 1))) + state.get_int(conn, "life_bonus_years", 0)


def age_years(conn: sqlite3.Connection, pid: int = 1) -> float:
    from engine.systems import character, storyline
    p = character.get_profile(conn, "player", pid)
    start_age = (p["age"] or 16) if p else 16
    lived = tick_mod.get_tick(conn) - storyline.life_start(conn)
    return start_age + max(0, lived) / character.YEAR_TICKS


def add_bonus_years(conn: sqlite3.Connection, years: int) -> None:
    state.set(conn, "life_bonus_years", str(state.get_int(conn, "life_bonus_years", 0) + years))


def label(conn: sqlite3.Connection, pid: int = 1) -> str:
    return f"{int(age_years(conn, pid))}/{max_years(conn, pid)} anni"


def daily_check(conn: sqlite3.Connection, player, t: int) -> list[str]:
    """Avvisi di vecchiaia e morte naturale. Ritorna righe da mostrare."""
    age, mx = age_years(conn, player.id), max_years(conn, player.id)
    if age >= mx:
        from engine.simulation import event_system as ev
        conn.execute("UPDATE players SET status='dead' WHERE id=?;", (player.id,))
        ev.log_event(conn, event_type="death", tick=t, location_id=player.location_id,
                     title=f"La fine naturale di {player.name}",
                     summary=f"{player.name} si spegne di vecchiaia a {int(age)} anni.",
                     participants=[ev.Participant("player", player.id, "victim")],
                     consequences=[ev.Consequence("player", player.id, "death",
                                                  "vecchiaia", visibility="public", resolve_tick=t)])
        return [f"Il tuo tempo è finito: a {int(age)} anni il cuore si ferma, sereno."]
    left = mx - age
    warned = state.get_int(conn, "life_warned", 0)
    if left <= mx * 0.05 and warned < 2:
        state.set(conn, "life_warned", "2")
        return [f"⌛ Ti restano pochi anni ({int(left)}). Solo un nuovo regno può allungare la tua vita."]
    if left <= mx * 0.2 and warned < 1:
        state.set(conn, "life_warned", "1")
        return [f"⌛ Senti il peso degli anni: ne hai {int(age)} su {mx}. "
                f"Sfondare al regno successivo raddoppierebbe la tua vita."]
    return []


def on_realm_up(conn: sqlite3.Connection, pid: int = 1) -> str:
    state.set(conn, "life_warned", "0")
    return f"La tua durata di vita raddoppia: ora puoi vivere fino a {max_years(conn, pid)} anni."
