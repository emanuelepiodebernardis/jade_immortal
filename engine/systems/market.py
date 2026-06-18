"""
Il MERCATO delle pietre spirituali.

Nelle CITTÀ trovi un mercato dove spendere le pietre spirituali in oggetti che ti
potenziano (pillole, essenze di Dao, nuclei, manuali). L'assortimento è più ricco,
più potente e più costoso quanto più è ALTA la tua setta: un errante trova cianfrusaglie,
un discepolo di una setta suprema trova tesori. Lo stock si rinnova ogni giorno.

Riusa gli effetti di items.py: ciò che compri finisce nello zaino e si usa con 'use'.
"""

from __future__ import annotations

import json
import random
import sqlite3

from engine.systems import items, sects, training
from engine.core import tick as tickmod
from engine.simulation import cultivation

_RARITY = ["comune", "non_comune", "raro", "prezioso", "leggendario"]

# (tipo, prezzo_base)
_TYPES = [
    ("pillola", 80),
    ("essenza", 120),
    ("nucleo", 100),
    ("manuale", 220),
]

_DAO_POOL = ["spada", "lancia", "sciabola", "arco", "pugno", "bastone",
             "corpo", "fulmine", "anima", "tempo", "spazio", "destino",
             "fuoco", "acqua", "terra", "vento", "metallo", "legno", "luce", "oscurita"]


def is_market_here(conn: sqlite3.Connection, location_id: int) -> bool:
    r = conn.execute("SELECT location_type FROM locations WHERE id=?;", (location_id,)).fetchone()
    return bool(r and r["location_type"] == "city")


def _sect_tier(conn, player_id) -> int:
    m = sects.get_membership(conn, player_id)
    return (m["sect_tier"] if m and m["sect_tier"] else 1)


def _rarity_for(rng, sect_tier) -> int:
    """Indice di rarità 0..4, pesato verso l'alto nelle sette potenti."""
    if sect_tier >= 5:
        w = [1, 2, 3, 4, 3]
    elif sect_tier >= 3:
        w = [2, 3, 3, 2, 1]
    elif sect_tier >= 2:
        w = [4, 3, 2, 1, 0]
    else:
        w = [6, 3, 1, 0, 0]
    return rng.choices([0, 1, 2, 3, 4], weights=w)[0]


def _make_offer(rng, sect_tier, realm_tier, player_daos) -> dict:
    itype, base = rng.choice(_TYPES)
    ridx = _rarity_for(rng, sect_tier)
    rarity = _RARITY[ridx]
    tier = max(sect_tier, realm_tier)
    price = int(base * (1 + ridx * 0.9) * (1 + (sect_tier - 1) * 0.7) * (1 + realm_tier * 0.15))

    if itype == "pillola":
        prog = round(0.18 + 0.05 * tier + ridx * 0.06, 2)
        name = f"Pillola del {_RARITY[ridx].replace('_', ' ').title()} Progresso"
        eff = {"cultivation_progress": prog}
        desc = "Fa avanzare la coltivazione."
    elif itype == "essenza":
        dao = rng.choice(player_daos) if player_daos else rng.choice(_DAO_POOL)
        gain = max(2, int((4 + tier * 2 + ridx * 3)))
        name = f"Essenza del Dao «{dao}»"
        eff = {"dao_key": dao, "dao_gain": gain}
        desc = f"Approfondisce la tua comprensione del Dao «{dao}»."
    elif itype == "nucleo":
        stat = rng.choice(["grow_strength", "grow_vitality", "grow_resistance", "grow_soul"])
        amt = max(2, int((2 + tier) * (1 + ridx)))
        word = {"grow_strength": "Forza", "grow_vitality": "Vitalità",
                "grow_resistance": "Resistenza", "grow_soul": "Anima"}[stat]
        name = f"Nucleo di {word}"
        eff = {stat: amt}
        desc = f"Innesta {word.lower()} permanente."
    else:  # manuale
        mag = round(0.06 + 0.02 * tier + ridx * 0.03, 3)
        name = f"Manuale Segreto ({rarity.replace('_', ' ')})"
        eff = {"learn_technique": {"name": name, "magnitude": mag,
                                   "tech_key": f"market:{rng.randint(1, 10**9)}"}}
        desc = f"Insegna una tecnica (+{int(mag*100)}% potenza)."

    return {"name": name, "item_type": itype, "rarity": rarity,
            "price": max(10, price), "effects": eff, "desc": desc}


def ensure_stock(conn: sqlite3.Connection, player_id: int, location_id: int) -> None:
    day = training.current_day(tickmod.get_tick(conn))
    existing = conn.execute(
        "SELECT COUNT(*) c FROM market_offers WHERE player_id=? AND location_id=? AND day=?;",
        (player_id, location_id, day)).fetchone()["c"]
    if existing:
        return
    sect_tier = _sect_tier(conn, player_id)
    realm_tier = cultivation.realm_tier(conn, "player", player_id) or 1
    rng = random.Random(location_id * 7919 + day * 31 + sect_tier)
    pdaos = [r["dao_key"] for r in conn.execute(
        "SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND (practiced=1 OR comprehension>0);", (player_id,)).fetchall()]
    count = 4 + sect_tier
    for _ in range(count):
        o = _make_offer(rng, sect_tier, realm_tier, pdaos)
        conn.execute(
            "INSERT INTO market_offers (player_id, location_id, day, name, item_type, rarity, "
            "price, effects, sold) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0);",
            (player_id, location_id, day, o["name"], o["item_type"], o["rarity"],
             o["price"], json.dumps(o["effects"], ensure_ascii=False)))


def offers(conn: sqlite3.Connection, player_id: int, location_id: int) -> list[sqlite3.Row]:
    day = training.current_day(tickmod.get_tick(conn))
    return conn.execute(
        "SELECT id, name, item_type, rarity, price, effects FROM market_offers "
        "WHERE player_id=? AND location_id=? AND day=? AND sold=0 ORDER BY id;",
        (player_id, location_id, day)).fetchall()


def buy(conn: sqlite3.Connection, player_id: int, location_id: int, slot: int) -> dict:
    rows = offers(conn, player_id, location_id)
    if slot < 1 or slot > len(rows):
        return {"status": "no_such"}
    o = rows[slot - 1]
    stones = sects.get_resource(conn, "pietre_spirituali", player_id)
    if stones < o["price"]:
        return {"status": "poor", "need": o["price"], "have": stones}
    sects.grant_resource(conn, "pietre_spirituali", -o["price"], player_id)
    try:
        eff = json.loads(o["effects"]) if o["effects"] else {}
    except Exception:
        eff = {}
    iid = items.create_item(conn, o["name"], o["item_type"], o["rarity"],
                            "Acquistato al mercato.", eff)
    items.grant(conn, "player", player_id, iid, 1)
    conn.execute("UPDATE market_offers SET sold=1 WHERE id=?;", (o["id"],))
    return {"status": "bought", "name": o["name"], "price": o["price"],
            "left": sects.get_resource(conn, "pietre_spirituali", player_id)}
