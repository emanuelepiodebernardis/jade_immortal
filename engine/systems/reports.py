"""
Coda di report differiti.

Alcuni eventi (su tutti i TORNEI di setta) scattano dentro l'avanzamento del tempo,
che a seconda del comando usato (cultivate/sleep/...) potrebbe non mostrare le sue
osservazioni. Per non perderli mai, li accodiamo qui e il loop principale li svuota
SEMPRE dopo ogni comando.
"""

from __future__ import annotations

import sqlite3


def push(conn: sqlite3.Connection, player_id: int, tick: int, text: str) -> None:
    conn.execute(
        "INSERT INTO pending_reports (player_id, tick, text, shown) VALUES (?, ?, ?, 0);",
        (player_id, tick, text))


def drain(conn: sqlite3.Connection, player_id: int = 1) -> list[str]:
    rows = conn.execute(
        "SELECT id, text FROM pending_reports WHERE player_id=? AND shown=0 ORDER BY id;",
        (player_id,)).fetchall()
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    conn.execute(
        f"UPDATE pending_reports SET shown=1 WHERE id IN ({','.join('?' * len(ids))});",
        tuple(ids))
    return [r["text"] for r in rows]
