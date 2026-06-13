"""
Allenamento dei Dao.

Puoi affinare la COMPRENSIONE di un Dao che pratichi (o che hai risvegliato
assorbendo). L'affinità (talento nascosto) accelera l'apprendimento; più Dao
insegui, più lento ognuno (l'attenzione si divide). Tetto: 100.

I Dao da combattimento (Corpo, Fulmine, Spada) aumentano la potenza fino a +20%
complessivo: allenarli ti rende davvero più forte, ma regno e strato restano il
fattore principale. I Dao profondi (Destino/Tempo/Spazio) si possono affinare ma
i loro effetti meccanici (informazione/utilità) restano per una fase futura.

L'allenamento dei Dao condivide l'economia giornaliera con la coltivazione: ogni
giorno scegli come spendere le poche sessioni utili.
"""

from __future__ import annotations

import random
import sqlite3

COMBAT_DAOS = {"corpo", "fulmine", "spada"}
COMBAT_PER_POINT = 0.0012        # potenza per punto di comprensione (combat dao)
COMBAT_CAP = 0.20                # tetto al bonus da Dao in combattimento
COMP_CAP = 100


def combat_dao_factor(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    """Moltiplicatore di potenza dato dalla comprensione dei Dao da combattimento."""
    rows = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type=? AND character_id=?;", (ctype, cid)).fetchall()
    total = sum(r["comprehension"] for r in rows if r["dao_key"] in COMBAT_DAOS)
    return 1.0 + min(COMBAT_CAP, total * COMBAT_PER_POINT)


def trainable_daos(conn: sqlite3.Connection, player_id: int = 1) -> list[sqlite3.Row]:
    """Dao che puoi allenare: praticati o già risvegliati (comprensione > 0)."""
    return conn.execute(
        "SELECT cd.dao_key, cd.affinity, cd.comprehension, cd.practiced, d.name, d.level "
        "FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? "
        "AND (cd.practiced=1 OR cd.comprehension>0) ORDER BY cd.comprehension DESC;",
        (player_id,)).fetchall()


def _practiced_count(conn, player_id) -> int:
    n = conn.execute(
        "SELECT COUNT(*) c FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND (practiced=1 OR comprehension>0);", (player_id,)
    ).fetchone()["c"]
    return max(1, n)


def find_dao(conn: sqlite3.Connection, fragment: str, player_id: int = 1) -> sqlite3.Row | None:
    frag = f"%{fragment.strip().lower()}%"
    return conn.execute(
        "SELECT cd.dao_key, cd.affinity, cd.comprehension, cd.practiced, d.name "
        "FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? "
        "AND (LOWER(cd.dao_key) LIKE ? OR LOWER(d.name) LIKE ?) LIMIT 1;",
        (player_id, frag, frag)).fetchone()


def comprehend(conn: sqlite3.Connection, tick: int, rng: random.Random,
               dao_key: str, multiplier: float = 1.0, player_id: int = 1) -> dict:
    """Affina la comprensione di un Dao. multiplier = rendimento giornaliero."""
    row = conn.execute(
        "SELECT affinity, comprehension, practiced FROM character_daos "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (player_id, dao_key)).fetchone()
    if row is None or (not row["practiced"] and row["comprehension"] == 0):
        return {"status": "locked"}        # Dao latente non ancora risvegliato
    if row["comprehension"] >= COMP_CAP:
        return {"status": "maxed", "comprehension": COMP_CAP}

    attention = 1 + 0.3 * (_practiced_count(conn, player_id) - 1)
    raw = (row["affinity"] / 50.0) * rng.uniform(1.0, 2.0) * multiplier / attention
    gain = int(round(raw))
    if gain <= 0:
        return {"status": "exhausted", "comprehension": row["comprehension"]}
    new = min(COMP_CAP, row["comprehension"] + gain)
    conn.execute(
        "UPDATE character_daos SET comprehension=? "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (new, player_id, dao_key))
    return {"status": "ok", "gain": new - row["comprehension"], "comprehension": new,
            "combat": dao_key in COMBAT_DAOS}


def comprehension_label(c: int) -> str:
    if c == 0:
        return "appena intuito"
    if c < 20:
        return "principiante"
    if c < 45:
        return "discreto"
    if c < 70:
        return "esperto"
    if c < 90:
        return "maestro"
    return "sublime"
