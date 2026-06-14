"""
Arma principale — la via marziale del personaggio.

Quando entri in una setta scegli un'arma (spada, lancia, sciabola, arco, pugni,
bastone). La scelta è PERMANENTE e sblocca il Dao d'arma corrispondente, che è un
Dao da combattimento: allenandolo con 'comprehend' diventi più forte secondo la tua
via. Così due coltivatori dello stesso elemento (es. Fulmine) possono essere del
tutto diversi: uno Spada, uno Lancia, uno Arco...
"""

from __future__ import annotations

import sqlite3

# chiave -> (dao_key, etichetta, nome del Dao)
WEAPONS = {
    "spada":    ("spada",    "Spada",    "Dao della Spada"),
    "lancia":   ("lancia",   "Lancia",   "Dao della Lancia"),
    "sciabola": ("sciabola", "Sciabola", "Dao della Sciabola"),
    "arco":     ("arco",     "Arco",     "Dao dell'Arco"),
    "pugno":    ("pugno",    "Pugni",    "Dao del Pugno"),
    "bastone":  ("bastone",  "Bastone",  "Dao del Bastone"),
}

# alias accettati dal comando
_ALIASES = {
    "pugni": "pugno", "fists": "pugno", "fist": "pugno",
    "sword": "spada", "spear": "lancia", "saber": "sciabola",
    "sciabla": "sciabola", "bow": "arco", "staff": "bastone", "bastoni": "bastone",
}


def normalize(key: str) -> str | None:
    k = (key or "").strip().lower()
    k = _ALIASES.get(k, k)
    return k if k in WEAPONS else None


def get_weapon(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    r = conn.execute(
        "SELECT weapon FROM character_profiles WHERE character_type='player' AND character_id=?;",
        (player_id,)).fetchone()
    return (r["weapon"] if r and r["weapon"] else None)


def weapon_label(key: str | None) -> str | None:
    if not key or key not in WEAPONS:
        return None
    return WEAPONS[key][1]


def list_choices() -> list[str]:
    """Righe descrittive per il menu di scelta."""
    out = []
    for i, (k, (_dk, label, dao)) in enumerate(WEAPONS.items(), start=1):
        out.append(f"  {i}. {label} — sblocca il {dao}")
    return out


def _key_by_index(idx: int) -> str | None:
    keys = list(WEAPONS.keys())
    return keys[idx - 1] if 1 <= idx <= len(keys) else None


def choose_weapon(conn: sqlite3.Connection, raw: str, player_id: int = 1) -> dict:
    """Sceglie l'arma (per chiave, alias o numero 1..6) e sblocca il Dao d'arma.
    Scelta una volta sola: permanente."""
    if get_weapon(conn, player_id):
        return {"status": "already", "weapon": weapon_label(get_weapon(conn, player_id))}
    key = None
    raw = (raw or "").strip()
    if raw.isdigit():
        key = _key_by_index(int(raw))
    else:
        key = normalize(raw)
    if key is None:
        return {"status": "invalid"}
    dao_key, label, dao_name = WEAPONS[key]
    conn.execute(
        "UPDATE character_profiles SET weapon=? WHERE character_type='player' AND character_id=?;",
        (key, player_id))
    # sblocca il Dao d'arma: praticato, affinità di partenza, prima comprensione
    from engine.generators import dao_gen
    dao_gen._set_dao(conn, "player", player_id, dao_key, affinity=65, comprehension=10, practiced=1)
    return {"status": "chosen", "weapon": label, "dao": dao_name, "dao_key": dao_key}
