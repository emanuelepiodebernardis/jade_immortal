"""
DESTINI ALLA NASCITA + TALENTO DEI RIVALI.

All'inizio di ogni vita, insieme all'origine, scegli UN destino da una mano estratta
(con rarità, come i tratti di Tale of Immortal o le benedizioni/penalità della Dice of
Fate di OOC). Ogni destino ha pregi e spesso un prezzo. I destini LEGGENDARI compaiono
solo dalla seconda vita in poi: si sbloccano con le vite passate.

Sempre all'inizio scegli quanto sono TALENTUOSI I RIVALI (compagni di setta e nemesi):
è la difficoltà del mondo, e resta valida anche dopo una reincarnazione.
"""

from __future__ import annotations

import json
import random
import sqlite3

from engine.systems import state

RARITY_WEIGHT = {"comune": 40, "non_comune": 28, "raro": 18, "epico": 10, "leggendario": 4}
RARITY_LABEL = {"comune": "comune", "non_comune": "non comune", "raro": "raro",
                "epico": "epico", "leggendario": "LEGGENDARIO"}

# effetti: aff_<x> (delta affinità), lifespan (anni), illness (True = malattia),
# karma, daos {dao: comprensione}, latent [dao], stones, flags {chiave: valore}
DESTINIES: dict[str, dict] = {
    "tenace": {"name": "Tempra d'Acciaio", "rarity": "comune",
               "desc": "Corpo robusto fin dall'infanzia.", "eff": {"aff_body": 8}},
    "sveglio": {"name": "Mente Sveglia", "rarity": "comune",
                "desc": "Impari in fretta le arti di combattimento.", "eff": {"aff_combat": 8}},
    "fortunato": {"name": "Nato con la Camicia", "rarity": "comune",
                  "desc": "La fortuna ti sorride negli incontri.",
                  "eff": {"flags": {"fortune": 15}}},
    "ricco": {"name": "Borsa Piena", "rarity": "comune",
              "desc": "Parti con 150 pietre spirituali.", "eff": {"stones": 150}},
    "longevo": {"name": "Sangue Longevo", "rarity": "non_comune",
                "desc": "La tua famiglia vive a lungo: +40 anni di vita.", "eff": {"lifespan": 40}},
    "cuore_puro": {"name": "Cuore Puro", "rarity": "non_comune",
                   "desc": "Karma limpido; i demoni interiori hanno poca presa su di te.",
                   "eff": {"karma": 120, "flags": {"pure_heart": True}}},
    "genio_malato": {"name": "Genio Malato", "rarity": "non_comune",
                     "desc": "Talento enorme, salute fragile: −20 anni di vita (malattia).",
                     "eff": {"aff_cultivation": 12, "lifespan": -20, "illness": True}},
    "domatore": {"name": "Amico delle Bestie", "rarity": "non_comune",
                 "desc": "Le creature ti riconoscono: domarle è molto più facile.",
                 "eff": {"flags": {"tamer": 25}}},
    "mano_alchimista": {"name": "Mani d'Artigiano", "rarity": "non_comune",
                        "desc": "Nato per l'alchimia, i talismani e la forgia.",
                        "eff": {"flags": {"crafter": 2}}},
    "cuore_spada": {"name": "Cuore di Spada", "rarity": "raro",
                    "desc": "Nasci con l'intento della spada già sveglio.",
                    "eff": {"daos": {"spada": 25}}},
    "figlio_tempesta": {"name": "Figlio della Tempesta", "rarity": "raro",
                        "desc": "Nato durante un temporale: il Fulmine ti appartiene.",
                        "eff": {"daos": {"fulmine": 25}, "aff_qi": 4}},
    "anima_antica": {"name": "Anima Antica", "rarity": "raro",
                     "desc": "Un'anima vasta e quieta.", "eff": {"aff_soul": 12}},
    "stella_cadente": {"name": "Stella Cadente", "rarity": "raro",
                       "desc": "Brilli fortissimo, ma per poco: −40 anni di vita.",
                       "eff": {"aff_cultivation": 18, "lifespan": -40}},
    "stella_nera": {"name": "Nato sotto la Stella Nera", "rarity": "raro",
                    "desc": "Sventura e potenza: karma pesante, ma la furia è tua.",
                    "eff": {"karma": -150, "aff_combat": 12}},
    "radici_caotiche": {"name": "Radici Caotiche", "rarity": "epico",
                        "desc": "Affinità latente con tutti e cinque gli elementi.",
                        "eff": {"latent": ["legno", "fuoco", "terra", "metallo", "acqua"]}},
    "occhi_cielo": {"name": "Occhi del Cielo", "rarity": "epico",
                    "desc": "Vedi le probabilità esatte di ogni prova.",
                    "eff": {"flags": {"heaven_eyes": True}, "aff_soul": 4}},
    "sangue_drago": {"name": "Sangue di Drago", "rarity": "epico",
                     "desc": "Corpo da drago; i draghi ti riconoscono come parente.",
                     "eff": {"aff_body": 10, "flags": {"dragon_blood": True, "tamer": 10}}},
    "fenice": {"name": "Corpo della Fenice", "rarity": "leggendario",
               "desc": "Una volta in questa vita, risorgi dalle tue ceneri.",
               "eff": {"flags": {"phoenix": True}}},
    "prescelto": {"name": "Prescelto dei Cieli", "rarity": "leggendario",
                  "desc": "Il Destino stesso ti accompagna.",
                  "eff": {"daos": {"destino": 25}, "aff_cultivation": 8, "flags": {"fortune": 20}}},
    "erede_ere": {"name": "Erede delle Ere", "rarity": "leggendario",
                  "desc": "Ricordi frammenti di tutte le tue vite: +10 a ogni affinità.",
                  "eff": {"aff_cultivation": 10, "aff_body": 10, "aff_qi": 10,
                          "aff_soul": 10, "aff_combat": 10}},
}

RIVAL_LEVELS = {
    "facile":      (0.7, "Rivali mediocri: crescono lentamente."),
    "normale":     (1.0, "Rivali come il mondo li ha fatti."),
    "difficile":   (1.3, "Rivali dotati: ti incalzano senza tregua."),
    "leggendario": (1.6, "Rivali geniali: ogni giorno perso è un passo che non recuperi."),
}


# ============================================================
# Talento dei rivali
# ============================================================

def rival_mult(conn: sqlite3.Connection) -> float:
    key = state.get(conn, "world_rival_talent", "normale")
    return RIVAL_LEVELS.get(key, RIVAL_LEVELS["normale"])[0]


def set_rival_level(conn: sqlite3.Connection, key: str) -> None:
    if key in RIVAL_LEVELS:
        state.set(conn, "world_rival_talent", key)


# ============================================================
# Destini
# ============================================================

def draw_hand(rng: random.Random, life_no: int = 1, n: int = 6) -> list[str]:
    pool = [k for k, d in DESTINIES.items() if d["rarity"] != "leggendario" or life_no >= 2]
    weights = [RARITY_WEIGHT[DESTINIES[k]["rarity"]] for k in pool]
    hand: list[str] = []
    while len(hand) < min(n, len(pool)):
        k = rng.choices(pool, weights=weights)[0]
        if k not in hand:
            hand.append(k)
    order = list(RARITY_WEIGHT)
    return sorted(hand, key=lambda k: order.index(DESTINIES[k]["rarity"]))


def label(key: str) -> str:
    d = DESTINIES[key]
    return f"{d['name']} [{RARITY_LABEL[d['rarity']]}] — {d['desc']}"


def apply(conn: sqlite3.Connection, key: str, player_id: int = 1) -> dict:
    d = DESTINIES[key]
    eff = d["eff"]
    for aff in ("cultivation", "body", "qi", "soul", "combat"):
        v = int(eff.get(f"aff_{aff}", 0))
        if v:
            conn.execute(f"UPDATE character_profiles SET aff_{aff}=MAX(1, MIN(100, aff_{aff}+?)) "
                         "WHERE character_type='player' AND character_id=?;", (v, player_id))
    row = conn.execute("SELECT flags FROM character_profiles WHERE character_type='player' "
                       "AND character_id=?;", (player_id,)).fetchone()
    flags = json.loads(row["flags"]) if row and row["flags"] else {}
    flags["destiny"] = key
    flags.update(eff.get("flags", {}))
    if eff.get("illness"):
        flags["illness"] = True
    if eff.get("lifespan"):
        flags["lifespan_mod"] = flags.get("lifespan_mod", 0) + int(eff["lifespan"])
    conn.execute("UPDATE character_profiles SET flags=? WHERE character_type='player' "
                 "AND character_id=?;", (json.dumps(flags), player_id))
    if eff.get("karma"):
        from engine.systems import karma
        karma.adjust_karma(conn, "player", player_id, int(eff["karma"]), d["name"], 0)
    for dk, comp in eff.get("daos", {}).items():
        conn.execute(
            "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, "
            "comprehension, practiced) VALUES ('player', ?, ?, 75, ?, 1) "
            "ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET practiced=1, "
            "comprehension=MAX(character_daos.comprehension, excluded.comprehension);",
            (player_id, dk, comp))
    for dk in eff.get("latent", []):
        conn.execute(
            "INSERT OR IGNORE INTO character_daos (character_type, character_id, dao_key, "
            "affinity, comprehension, practiced) VALUES ('player', ?, ?, 80, 0, 0);",
            (player_id, dk))
    if eff.get("stones"):
        from engine.systems import sects
        sects.grant_resource(conn, "pietre_spirituali", int(eff["stones"]), player_id)
    return d


def current(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    if not p or not p["flags"]:
        return None
    try:
        return json.loads(p["flags"]).get("destiny")
    except Exception:
        return None


def flag_value(conn: sqlite3.Connection, flag: str, player_id: int = 1, default=0):
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    if not p or not p["flags"]:
        return default
    try:
        return json.loads(p["flags"]).get(flag, default)
    except Exception:
        return default


def set_flag(conn: sqlite3.Connection, flag: str, value, player_id: int = 1) -> None:
    row = conn.execute("SELECT flags FROM character_profiles WHERE character_type='player' "
                       "AND character_id=?;", (player_id,)).fetchone()
    flags = json.loads(row["flags"]) if row and row["flags"] else {}
    flags[flag] = value
    conn.execute("UPDATE character_profiles SET flags=? WHERE character_type='player' "
                 "AND character_id=?;", (json.dumps(flags), player_id))
