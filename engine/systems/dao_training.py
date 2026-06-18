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

COMBAT_DAOS = {"corpo", "fulmine", "spada", "lancia", "sciabola", "arco", "pugno", "bastone",
               "fuoco", "acqua", "terra", "vento", "metallo", "legno", "luce", "oscurita"}

# Progressione SENZA TETTO a soglie. Ogni soglia raggiunta dà:
#   - un'etichetta di maestria
#   - un bonus di combattimento (solo per i Dao da combattimento), cumulativo per Dao
#   - eventualmente una TECNICA che si sblocca (nome flavor per Dao)
# (min_comprensione, etichetta, bonus_combat, tecnica_base|None)
DAO_THRESHOLDS = [
    (0,    "principiante",  0.00, None),
    (10,   "iniziato",      0.05, None),
    (25,   "adepto",        0.10, None),
    (50,   "esperto",       0.20, None),
    (100,  "maestro",       0.35, "Tecnica"),
    (250,  "gran maestro",  0.55, "Tecnica Suprema"),
    (500,  "dominatore",    0.80, "Dominio"),
    (1000, "legislatore",   1.20, "Legge"),
]


def _threshold_for(c: int) -> tuple[int, str, float, str | None]:
    cur = DAO_THRESHOLDS[0]
    for t in DAO_THRESHOLDS:
        if c >= t[0]:
            cur = t
    return cur


def _dao_suffix(dao_name: str) -> str:
    """'Dao del Fulmine' -> 'del Fulmine' (per comporre i nomi delle tecniche)."""
    return dao_name[4:] if dao_name.lower().startswith("dao ") else dao_name


def dao_combat_bonus(comprehension: int) -> float:
    """Bonus di combattimento di UN singolo Dao, dalla soglia raggiunta."""
    return _threshold_for(comprehension)[2]


def unlocked_technique(dao_name: str, comprehension: int) -> str | None:
    """Tecnica sbloccata alla soglia attuale, es. 'Dominio del Fulmine'. None se nessuna."""
    base = _threshold_for(comprehension)[3]
    return f"{base} {_dao_suffix(dao_name)}" if base else None


def next_threshold(comprehension: int) -> tuple[int, str, float, str | None] | None:
    """La prossima soglia da raggiungere (per il display 'manca poco'). None se al massimo."""
    for t in DAO_THRESHOLDS:
        if comprehension < t[0]:
            return t
    return None


def combat_dao_factor(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    """Moltiplicatore di potenza dato dai Dao da combattimento (soglie cumulative, SENZA tetto)."""
    rows = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type=? AND character_id=?;", (ctype, cid)).fetchall()
    total = sum(dao_combat_bonus(r["comprehension"])
                for r in rows if r["dao_key"] in COMBAT_DAOS)
    return 1.0 + total


# --- Punti-statistica DIRETTI dai livelli di Dao -------------------------------
# Oltre alle percentuali, ogni soglia raggiunta versa punti DIRETTI in una statistica.
# Cumulativi e indicizzati come DAO_THRESHOLDS (principiante..legislatore).
DAO_TIER_POINTS = [0, 2, 5, 10, 20, 35, 55, 85]

# Ogni Dao alimenta una statistica precisa.
DAO_STAT = {
    "corpo": "vitality",
    "fulmine": "attack",      # "velocità": offensiva fulminea
    "spada": "attack", "lancia": "attack", "sciabola": "attack",
    "arco": "attack", "pugno": "attack", "tempo": "attack",
    "bastone": "defense", "destino": "defense", "spazio": "defense",
    "anima": "spirit",
    # elementi: offensivi (fuoco/metallo/luce/oscurità/vento), difensivi/vitali (acqua/terra/legno)
    "fuoco": "attack", "metallo": "attack", "luce": "attack", "oscurita": "attack",
    "vento": "attack", "acqua": "defense", "terra": "vitality", "legno": "vitality",
}


def _tier_index(c: int) -> int:
    idx = 0
    for i, t in enumerate(DAO_THRESHOLDS):
        if c >= t[0]:
            idx = i
    return idx


def dao_tier_points(comprehension: int) -> int:
    """Punti diretti versati da UN Dao alla soglia raggiunta (cumulativi)."""
    return DAO_TIER_POINTS[_tier_index(comprehension or 0)]


def dao_stat_points(conn: sqlite3.Connection, ctype: str, cid: int) -> dict:
    """Somma dei punti DIRETTI versati da tutti i Dao del personaggio, per statistica."""
    out = {"attack": 0.0, "defense": 0.0, "vitality": 0.0, "spirit": 0.0}
    rows = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type=? AND character_id=?;", (ctype, cid)).fetchall()
    for r in rows:
        stat = DAO_STAT.get(r["dao_key"], "attack")
        out[stat] += dao_tier_points(r["comprehension"] or 0)
    return out


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
    """Affina la comprensione di un Dao (SENZA tetto). multiplier = rendimento giornaliero."""
    row = conn.execute(
        "SELECT affinity, comprehension, practiced FROM character_daos "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (player_id, dao_key)).fetchone()
    if row is None or (not row["practiced"] and row["comprehension"] == 0):
        return {"status": "locked"}        # Dao latente non ancora risvegliato

    attention = 1 + 0.3 * (_practiced_count(conn, player_id) - 1)
    raw = (row["affinity"] / 50.0) * rng.uniform(1.0, 2.0) * multiplier / attention
    gain = int(round(raw))
    if gain <= 0:
        return {"status": "exhausted", "comprehension": row["comprehension"]}

    before = row["comprehension"]
    new = before + gain                    # nessun tetto: progressione infinita
    conn.execute(
        "UPDATE character_daos SET comprehension=? "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (new, player_id, dao_key))

    # soglia / tecnica appena superata?
    dn = conn.execute("SELECT name FROM daos WHERE dao_key=?;", (dao_key,)).fetchone()
    dao_name = dn["name"] if dn else dao_key
    tier_up = _threshold_for(before)[1] != _threshold_for(new)[1]
    tech_before = _threshold_for(before)[3]
    tech_after = _threshold_for(new)[3]
    unlocked = (f"{tech_after} {_dao_suffix(dao_name)}"
                if tech_after and tech_after != tech_before else None)

    return {"status": "ok", "gain": new - before, "comprehension": new,
            "combat": dao_key in COMBAT_DAOS, "tier_up": tier_up,
            "label": _threshold_for(new)[1], "unlocked": unlocked}


def comprehension_label(c: int) -> str:
    if c <= 0:
        return "appena intuito"
    return _threshold_for(c)[1]
