"""
Piccolo accesso tipizzato alla tabella chiave/valore `game_state`.

Serve ai sistemi "di presentazione" (azioni suggerite, incontri in sospeso, titoli,
impostazioni dell'interfaccia) per salvare stato senza nuove tabelle. Il DB resta
l'unica fonte di verità.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def get(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM game_state WHERE key=?;", (key,)).fetchone()
    return row["value"] if row else default


def set(conn: sqlite3.Connection, key: str, value: str) -> None:  # noqa: A001
    conn.execute(
        "INSERT INTO game_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (key, value))


def delete(conn: sqlite3.Connection, key: str) -> None:
    conn.execute("DELETE FROM game_state WHERE key=?;", (key,))


def get_json(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    raw = get(conn, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def set_json(conn: sqlite3.Connection, key: str, value: Any) -> None:
    set(conn, key, json.dumps(value, ensure_ascii=False))


def get_int(conn: sqlite3.Connection, key: str, default: int = 0) -> int:
    raw = get(conn, key)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


def flag(conn: sqlite3.Connection, key: str, default: bool = True) -> bool:
    """Impostazione on/off (es. 'ui_hud'). Assente = default."""
    raw = get(conn, key)
    if raw is None:
        return default
    return raw == "1"


# ---------- titoli (traguardi) ----------

def titles(conn: sqlite3.Connection) -> list[str]:
    return list(get_json(conn, "player_titles", []) or [])


def grant_title(conn: sqlite3.Connection, title: str) -> bool:
    """Aggiunge un titolo. True se è nuovo."""
    cur = titles(conn)
    if title in cur:
        return False
    cur.append(title)
    set_json(conn, "player_titles", cur)
    return True
