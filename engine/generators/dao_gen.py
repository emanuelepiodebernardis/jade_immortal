"""
Generazione Dao (v1).

I Dao sono classificati su 3 livelli (il design del giocatore):
  - narrative: identità/stile;
  - systemic: effetti reali ma contenuti;
  - deep: i più potenti (Destino/Tempo/Spazio) — qui solo come AFFINITÀ latenti,
    i loro effetti meccanici sono slottati e verranno dopo.

Ogni personaggio ha, per Dao: un'affinità (talento latente, nascosto) e una
comprensione (padronanza reale). Gli NPC hanno un Dao primario, così l'assorbimento
può trasferirne frammenti.
"""

from __future__ import annotations

import random
import sqlite3

DAOS = [
    ("corpo", "Dao del Corpo", "systemic", "La via della forza e della sopravvivenza fisica."),
    ("anima", "Dao dell'Anima", "systemic", "La via dello spirito e della resistenza mentale."),
    ("fulmine", "Dao del Fulmine", "systemic", "La via che doma le tribolazioni celesti."),
    ("spada", "Dao della Spada", "narrative", "La via tagliente, identità del guerriero."),
    ("destino", "Dao del Destino", "deep", "La via che intravede ciò che sarà."),
    ("tempo", "Dao del Tempo", "deep", "La via che piega il fluire degli istanti."),
    ("spazio", "Dao dello Spazio", "deep", "La via che annulla le distanze."),
]

# Dao primario per archetipo NPC (pesato)
_ARCH_DAO = {
    "guardia": (["corpo", "spada", "fulmine"], [3, 2, 1]),
    "discepolo": (["spada", "corpo", "anima"], [3, 2, 1]),
    "patriarca": (["fulmine", "spada", "anima", "destino"], [3, 2, 2, 1]),
    "anziano": (["anima", "destino", "corpo"], [3, 2, 1]),
    "eremita": (["anima", "destino", "spazio"], [3, 2, 1]),
    "vagabondo": (["spada", "corpo", "spazio"], [2, 2, 1]),
    "mercante": (["corpo", "anima"], [2, 1]),
}


def seed_daos(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) c FROM daos;").fetchone()["c"] > 0:
        return
    for key, name, level, desc in DAOS:
        conn.execute(
            "INSERT INTO daos (dao_key, name, level, description) VALUES (?, ?, ?, ?);",
            (key, name, level, desc),
        )


def _set_dao(conn, ctype, cid, dao_key, affinity, comprehension, practiced):
    conn.execute(
        "INSERT INTO character_daos "
        "(character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "affinity=excluded.affinity, comprehension=excluded.comprehension, "
        "practiced=excluded.practiced;",
        (ctype, cid, dao_key, affinity, comprehension, practiced),
    )


def assign_npc_daos(conn: sqlite3.Connection, rng: random.Random) -> None:
    from engine.simulation import cultivation
    for npc in conn.execute("SELECT id, archetype FROM npcs;").fetchall():
        pool, weights = _ARCH_DAO.get(npc["archetype"], (["corpo"], [1]))
        dao = rng.choices(pool, weights=weights)[0]
        tier = cultivation.realm_tier(conn, "npc", npc["id"])
        comp = max(1, min(100, tier * 9 + rng.randint(-5, 5)))
        aff = max(1, min(100, 50 + rng.randint(-10, 15)))
        _set_dao(conn, "npc", npc["id"], dao, aff, comp, 1)


def assign_player_daos(conn: sqlite3.Connection, rng: random.Random,
                       practiced: list[str], latent: list[str],
                       player_id: int = 1) -> None:
    for dao in practiced:
        _set_dao(conn, "player", player_id, dao,
                 affinity=max(1, min(100, 65 + rng.randint(-5, 5))),
                 comprehension=rng.randint(8, 18), practiced=1)
    for dao in latent:
        # affinità latente ALTA, comprensione ZERO: potenziale, non potere
        _set_dao(conn, "player", player_id, dao,
                 affinity=max(1, min(100, 80 + rng.randint(-5, 8))),
                 comprehension=0, practiced=0)


def player_dao_affinity(conn, dao_key, player_id=1) -> int:
    row = conn.execute(
        "SELECT affinity FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key=?;", (player_id, dao_key),
    ).fetchone()
    return row["affinity"] if row else 30


def list_character_daos(conn, ctype, cid) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT cd.dao_key, cd.affinity, cd.comprehension, cd.practiced, d.name, d.level "
        "FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type=? AND cd.character_id=? ORDER BY cd.comprehension DESC;",
        (ctype, cid),
    ).fetchall()
