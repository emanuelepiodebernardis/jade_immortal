"""
Tribolazioni dell'Abisso: resistenza e doni del fulmine.

Chi padroneggia il DAO DEL FULMINE doma il castigo del Cielo: più alta è la sua
comprensione, meno lo ferisce la tribolazione (il fulmine gli appartiene). E ogni
folgore che lo colpisce viene ASSORBITA, donandogli una capacità celeste permanente
e molto potente — che si accumula a ogni colpo. Così la tribolazione, da pericolo,
diventa la fonte di poteri straordinari.
"""

from __future__ import annotations

import random
import sqlite3

# benedizioni: chiave -> (nome, statistica, magnitudine per livello, descrizione)
BOONS = {
    "corpo_fulmine":   ("Corpo di Fulmine", "attack_mult", 0.06,
                        "i muscoli guizzano di scariche: attacco superiore"),
    "pelle_tuono":     ("Pelle di Tuono", "defense_mult", 0.06,
                        "la pelle si fa dura come tuono: difesa superiore"),
    "cuore_folgorato": ("Cuore Folgorato", "vitality_mult", 0.06,
                        "il cuore pompa folgore: vitalità superiore"),
    "anima_folgorata": ("Anima Folgorata", "spirit", 30.0,
                        "lo spirito risuona di tuono: presenza e percezione"),
    "furia_celeste":   ("Furia Celeste", "attack_flat", 10.0,
                        "ogni colpo è carico di folgore: attacco diretto"),
}


def _fulmine_comp(conn: sqlite3.Connection, player_id: int = 1) -> int:
    r = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key='fulmine';", (player_id,)).fetchone()
    return (r["comprehension"] if r and r["comprehension"] else 0)


def fulmine_resistance(conn: sqlite3.Connection, player_id: int = 1) -> float:
    """Punti di 'resistenza' alla tribolazione dati dal Dao del Fulmine (sommati alla
    capacità di reggere il castigo). Alta comprensione = il fulmine non ti scalfisce."""
    return _fulmine_comp(conn, player_id) * 0.6


def grant_boon(conn: sqlite3.Connection, rng: random.Random, player_id: int = 1) -> str:
    """Assorbi una folgore: ottieni (o potenzi) una benedizione celeste."""
    key = rng.choice(list(BOONS.keys()))
    cur = conn.execute(
        "SELECT level FROM tribulation_boons WHERE player_id=? AND boon_key=?;",
        (player_id, key)).fetchone()
    if cur:
        lvl = (cur["level"] or 0) + 1
        conn.execute("UPDATE tribulation_boons SET level=? WHERE player_id=? AND boon_key=?;",
                     (lvl, player_id, key))
    else:
        lvl = 1
        conn.execute("INSERT INTO tribulation_boons (player_id, boon_key, level) VALUES (?, ?, 1);",
                     (player_id, key))
    return f"{BOONS[key][0]} (livello {lvl})"


def boon_bonuses(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    """Bonus aggregati di tutte le benedizioni assorbite."""
    out = {"attack_mult": 1.0, "defense_mult": 1.0, "vitality_mult": 1.0,
           "spirit": 0.0, "attack_flat": 0.0}
    rows = conn.execute(
        "SELECT boon_key, level FROM tribulation_boons WHERE player_id=?;",
        (player_id,)).fetchall()
    for r in rows:
        b = BOONS.get(r["boon_key"])
        if not b:
            continue
        _name, stat, mag, _desc = b
        lvl = r["level"] or 1
        if stat.endswith("_mult"):
            out[stat] *= (1.0 + mag * lvl)
        else:
            out[stat] += mag * lvl
    return out


def boon_list(conn: sqlite3.Connection, player_id: int = 1) -> list[str]:
    rows = conn.execute(
        "SELECT boon_key, level FROM tribulation_boons WHERE player_id=? ORDER BY level DESC;",
        (player_id,)).fetchall()
    return [f"{BOONS[r['boon_key']][0]} (liv. {r['level']})"
            for r in rows if r["boon_key"] in BOONS]
