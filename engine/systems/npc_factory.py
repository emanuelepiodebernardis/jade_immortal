"""
Creazione di NPC "di storia" (compagni, maestri, nemesi, personaggi degli incontri).

Stessa struttura degli NPC generati dal mondo (riga npcs + traits + record di
coltivazione + un Dao primario), così tutti i sistemi esistenti — combattimento,
esame, assorbimento, bottino — li trattano come chiunque altro.
"""

from __future__ import annotations

import random
import sqlite3

from engine.generators import npc_gen

_DAO_POOL = ["spada", "corpo", "fulmine", "anima", "lancia", "fuoco", "vento", "acqua"]


# nomi più vari per i personaggi "di storia" (il pool del mondo è piccolo e finisce presto)
_SURNAMES = ["Han", "Liu", "Zhao", "Mei", "Gao", "Wu", "Lin", "Shen", "Bai", "Tang", "Yun", "Xu",
             "Qin", "Su", "Long", "Feng", "Ye", "Mo", "Lu", "Jiang", "Song", "Hua", "Luo", "Qiao",
             "Shi", "Wen", "Yan", "Zhou", "Ling", "Xiao"]
_GIVEN = ["Wei", "Feng", "Lan", "Jian", "Yan", "Ruo", "Tian", "Cheng", "Min", "Hua", "Zhi", "Bo",
          "Xue", "Yu", "Chen", "Hao", "Rong", "Qing", "Shan", "Ling", "Xin", "Kai", "Ming", "Yue",
          "Lian", "Fei", "Heng", "Jun", "Ying", "Zhen", "Wuji", "Changge", "Moran", "Xiaoyu"]


# nomi femminili (per le donne del mondo: fidanzate, compagne del Dao, sorelle, madri…)
_GIVEN_F = ["Mei", "Lan", "Xue", "Ling", "Yue", "Ying", "Qing", "Rou", "Xiu", "Yan", "Zhen", "Fei", "Lian",
            "Shuang", "Yao", "Ning", "Wan", "Xiaoyu", "Ruoxi", "Qingxue", "Yuyan", "Lingyun", "Hua", "Xin"]


def gender_of(conn: sqlite3.Connection, npc_id: int) -> str:
    """'m' o 'f'. Nei mondi creati prima del genere (NULL) lo si deduce in modo stabile dall'id."""
    r = conn.execute("SELECT gender, kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if r is None:
        return "m"
    if r["gender"] in ("m", "f"):
        return r["gender"]
    return "f" if (r["kind"] or "human") == "human" and npc_id % 5 in (1, 3) else "m"


def is_female(conn: sqlite3.Connection, npc_id: int) -> bool:
    return gender_of(conn, npc_id) == "f"


def unique_name(rng: random.Random, used: set[str] | None = None,
                conn: sqlite3.Connection | None = None, female: bool = False) -> str:
    if used is None:
        used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")} if conn else set()
    pool = _GIVEN_F if female else _GIVEN
    for _ in range(200):
        n = f"{rng.choice(_SURNAMES)} {rng.choice(pool)}"
        if n not in used:
            used.add(n)
            return n
    return npc_gen._unique_name(rng, used)


def realm_id_for(conn: sqlite3.Connection, tier: int) -> int:
    from engine.simulation import cultivation
    return cultivation.ensure_realm(conn, max(1, int(tier)))


def spawn(conn: sqlite3.Connection, rng: random.Random, *, archetype: str,
          location_id: int | None, tier: int, stage: int | None = None,
          name: str | None = None, faction_id: int | None = None,
          dao: str | None = None, dao_comp: int | None = None,
          traits: dict[str, int] | None = None, tick: int = 0, gender: str | None = None) -> int:
    """Crea un NPC umano e ritorna il suo id. gender: 'm' | 'f' (None = a caso)."""
    if archetype not in npc_gen.ARCHETYPE_PROFILES:
        archetype = "vagabondo"
    gender = gender if gender in ("m", "f") else None      # None: deciso in modo stabile dall'id
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    name = name or unique_name(rng, used, female=gender == "f")
    tr = dict(npc_gen.roll_traits(rng, archetype))
    if traits:
        tr.update({k: max(0, min(100, v)) for k, v in traits.items()})
    desc = npc_gen.make_description(archetype, tr)
    realm_id = realm_id_for(conn, tier)
    stage = stage if stage is not None else rng.randint(2, 8)
    stage = max(1, min(10, stage))
    cur = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, faction_id, "
        "realm_id, kind, birth_tick, last_active_tick, gender) "
        "VALUES (?, ?, 'alive', ?, ?, ?, ?, 'human', ?, ?, ?);",
        (name, location_id, desc, archetype, faction_id, realm_id, tick, tick, gender))
    nid = cur.lastrowid
    if gender is None:
        conn.execute("UPDATE npcs SET gender=? WHERE id=?;", (gender_of(conn, nid), nid))
    conn.execute(
        "INSERT INTO npc_traits (npc_id, ambition, honor, greed, courage, loyalty, "
        "compassion, pride) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (nid, tr["ambition"], tr["honor"], tr["greed"], tr["courage"],
         tr["loyalty"], tr["compassion"], tr["pride"]))
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, ?, ?, ?, ?, ?, ?);",
        (nid, realm_id, round(rng.uniform(0, 0.4), 2), stage,
         tier * 10 + stage * 2, tier * 8 + stage, tier * 8 + stage, tier * 5))
    dkey = dao or rng.choice(_DAO_POOL)
    comp = dao_comp if dao_comp is not None else tier * 10 + stage + rng.randint(0, 8)
    conn.execute(
        "INSERT OR IGNORE INTO character_daos (character_type, character_id, dao_key, "
        "affinity, comprehension, practiced) VALUES ('npc', ?, ?, ?, ?, 1);",
        (nid, dkey, rng.randint(50, 70), comp))
    return nid


def raise_npc(conn: sqlite3.Connection, npc_id: int, stages: int) -> dict:
    """Fa crescere un NPC di `stages` strati (oltre il 10 sale di regno). Ritorna tier/stage."""
    rec = conn.execute(
        "SELECT cr.stage, r.tier FROM cultivation_records cr "
        "JOIN cultivation_realms r ON r.id=cr.realm_id "
        "WHERE cr.character_type='npc' AND cr.character_id=?;", (npc_id,)).fetchone()
    if not rec:
        return {"tier": 1, "stage": 1}
    tier, stage = rec["tier"], rec["stage"] + max(0, stages)
    while stage > 10:
        stage -= 10
        tier += 1
    rid = realm_id_for(conn, tier)
    conn.execute(
        "UPDATE cultivation_records SET realm_id=?, stage=?, qi_level=?, body_level=?, "
        "soul_level=?, dao_understanding=? WHERE character_type='npc' AND character_id=?;",
        (rid, stage, tier * 10 + stage * 2, tier * 8 + stage, tier * 8 + stage, tier * 5, npc_id))
    conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (rid, npc_id))
    conn.execute(
        "UPDATE character_daos SET comprehension = comprehension + ? "
        "WHERE character_type='npc' AND character_id=?;", (max(0, stages) * 2, npc_id))
    return {"tier": tier, "stage": stage}


def npc_tier(conn: sqlite3.Connection, npc_id: int) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "npc", npc_id) or 1
