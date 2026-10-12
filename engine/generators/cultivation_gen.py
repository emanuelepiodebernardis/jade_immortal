"""
Generazione coltivazione (Fase 7).

seed_realms: inserisce gli 8 regni di riferimento (tier 1-8), fino a
"Immortale di Giada" (che dà il nome al gioco).
assign_cultivation: assegna a player e NPC un regno iniziale (per archetipo) e
crea il relativo cultivation_record che traccia il progresso entro il regno.
"""

from __future__ import annotations

import random
import sqlite3

# tier -> nome del regno. I nove regni del MONDO MORTALE (il nono è il suo tetto): la scala
# classica dei romanzi di coltivazione (练气 筑基 金丹 元婴 化神 炼虚 合体 大乘 渡劫).
REALMS = [
    (1, "Condensazione del Qi"),           # 练气 — si raccoglie il Qi del cielo e della terra
    (2, "Fondazione"),                     # 筑基 — il Qi diventa una base solida
    (3, "Nucleo d'Oro"),                   # 金丹 — il Qi si condensa in un nucleo
    (4, "Anima Nascente"),                 # 元婴 — dal nucleo nasce un'anima bambina
    (5, "Trasformazione dello Spirito"),   # 化神 — lo spirito tocca le leggi del mondo
    (6, "Raffinamento del Vuoto"),         # 炼虚 — si tempra il proprio vuoto interiore
    (7, "Unione del Corpo"),               # 合体 — corpo, anima e Dao diventano una cosa sola
    (8, "Grande Veicolo"),                 # 大乘 — il Mahayana: la vetta dei mortali
    (9, "Superamento della Tribolazione"), # 渡劫 — l'ultima prova del Cielo, prima di ascendere
]

# Oltre il Mondo Mortale (tre regni per ogni mondo superiore) i regni dell'immortalità, poi
# santi, signori del Dao e il caos primordiale; esauriti i nomi, si ricomincia con un numerale.
_ASCENDING_REALMS = [
    # Mondo degli Immortali (10-12)
    "Immortale di Giada", "Immortale Celeste", "Immortale Mistico",
    # Cielo d'Oro (13-15) — 金仙, 太乙金仙, 大罗金仙
    "Immortale d'Oro", "Immortale d'Oro dell'Unità Suprema", "Immortale d'Oro della Grande Rete",
    # Mondo dei Santi (16-18)
    "Mezzo Santo", "Santo", "Santo Supremo",
    # Reame del Dao (19-21)
    "Re del Dao", "Imperatore del Dao", "Antenato del Dao",
    # Mare del Caos (22-24) — 混元
    "Caos Primordiale", "Origine Senza Origine", "Oltre il Principio",
]

_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _roman(n: int) -> str:
    out = ""
    for val, sym in _ROMAN:
        while n >= val:
            out += sym
            n -= val
    return out


def realm_name_for_tier(tier: int) -> str:
    """Nome del regno per un tier qualsiasi: tabellato fino all'Immortale di Giada (8),
    poi generato all'infinito."""
    if tier <= len(REALMS):
        return REALMS[tier - 1][1]
    idx = tier - len(REALMS) - 1            # 0-based oltre i regni tabellati
    cycle = idx // len(_ASCENDING_REALMS)
    base = _ASCENDING_REALMS[idx % len(_ASCENDING_REALMS)]
    return base if cycle == 0 else f"{base} {_roman(cycle + 1)}"


def requirements_for(tier: int) -> tuple[int, int, int, int]:
    return (tier * 100, tier * 80, tier * 80, tier * 60)


# range di tier iniziale per archetipo
_ARCH_REALM = {
    "patriarca": (3, 5),
    "anziano": (2, 4),
    "eremita": (2, 4),
    "guardia": (1, 2),
    "discepolo": (1, 2),
    "vagabondo": (1, 2),
    "mercante": (1, 1),
}


def seed_realms(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) c FROM cultivation_realms;").fetchone()["c"] > 0:
        return
    for tier, name in REALMS:
        conn.execute(
            "INSERT INTO cultivation_realms "
            "(name, tier, qi_requirement, body_requirement, soul_requirement, dao_requirement) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            (name, tier, tier * 100, tier * 80, tier * 80, tier * 60),
        )


def _realm_id_by_tier(conn: sqlite3.Connection) -> dict[int, int]:
    return {r["tier"]: r["id"]
            for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}


def _make_record(conn, ctype, cid, realm_id, tier, progress, stage=1):
    conn.execute(
        "INSERT INTO cultivation_records "
        "(character_id, character_type, realm_id, progress, stage, qi_level, body_level, "
        " soul_level, dao_understanding) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
        (cid, ctype, realm_id, progress, stage,
         tier * 10 + stage * 2, tier * 8 + stage, tier * 8 + stage, tier * 5),
    )


def assign_cultivation(conn: sqlite3.Connection, rng: random.Random) -> None:
    by_tier = _realm_id_by_tier(conn)

    # player: parte da tier 1, Strato 1, progresso nullo
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (by_tier[1],))
    _make_record(conn, "player", 1, by_tier[1], 1, 0.0, stage=1)

    # npc: tier per archetipo, strato casuale (varietà di forza)
    for npc in conn.execute("SELECT id, archetype FROM npcs;").fetchall():
        lo, hi = _ARCH_REALM.get(npc["archetype"], (1, 1))
        tier = rng.randint(lo, hi)
        realm_id = by_tier[tier]
        stage = rng.randint(1, 10)
        conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (realm_id, npc["id"]))
        _make_record(conn, "npc", npc["id"], realm_id, tier,
                     round(rng.uniform(0.0, 0.6), 3), stage=stage)
