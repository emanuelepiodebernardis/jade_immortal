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
    # la via marziale è permanente; parti con un'arma BASE (regno 1, rarità 1 = +0%)
    conn.execute(
        "UPDATE character_profiles SET weapon=?, weapon_tier=1, weapon_rarity=1 "
        "WHERE character_type='player' AND character_id=?;",
        (key, player_id))
    # sblocca il Dao d'arma: praticato, affinità di partenza, prima comprensione
    from engine.generators import dao_gen
    dao_gen._set_dao(conn, "player", player_id, dao_key, affinity=65, comprehension=10, practiced=1)
    return {"status": "chosen", "weapon": label, "dao": dao_name, "dao_key": dao_key}


# ============================================================
# ARMA-OGGETTO: regno (livello di coltivazione) × rarità (4 classi)
# ------------------------------------------------------------
# La VIA marziale (il tipo) si sceglie una volta in setta ed è permanente. L'arma
# vera e propria, invece, ha una QUALITÀ data dal regno per cui è forgiata e dalla
# rarità. Trovando un'arma migliore DELLO STESSO TIPO la si equipaggia in automatico;
# armi di tipo diverso non rientrano nella tua via e non si possono impugnare.
# Il bonus è una percentuale di attacco: cresce col regno e, di più, con la rarità.
# ============================================================

RARITY_NAMES = {1: "comune", 2: "raffinata", 3: "pregiata", 4: "divina"}
RARITY_MAX = 4

# peso di bonus: il regno dà una base, la rarità è il vero moltiplicatore di pregio
_TIER_STEP = 0.06      # +6% attacco per ogni regno oltre il 1°
_RARITY_STEP = 0.05    # +5% attacco per ogni classe di rarità oltre la 1ª


def rarity_name(rarity: int) -> str:
    return RARITY_NAMES.get(rarity, "comune")


def weapon_bonus(tier: int, rarity: int) -> float:
    """Frazione di bonus all'attacco data da un'arma (regno×rarità). Base (1,1) = 0."""
    if not tier or not rarity:
        return 0.0
    return round((tier - 1) * _TIER_STEP + (rarity - 1) * _RARITY_STEP, 3)


def weapon_score(tier: int, rarity: int) -> float:
    """Metro di confronto fra due armi (coerente col bonus: più alto = più forte)."""
    return weapon_bonus(tier, rarity)


def describe_weapon(wtype: str, tier: int, rarity: int) -> str:
    return f"{weapon_label(wtype)} {rarity_name(rarity)} (regno {tier})"


def get_equipped(conn, player_id: int = 1) -> dict | None:
    r = conn.execute(
        "SELECT weapon, weapon_tier, weapon_rarity FROM character_profiles "
        "WHERE character_type='player' AND character_id=?;", (player_id,)).fetchone()
    if not r or not r["weapon"]:
        return None
    tier = r["weapon_tier"] or 1
    rarity = r["weapon_rarity"] or 1
    return {"type": r["weapon"], "tier": tier, "rarity": rarity,
            "bonus": weapon_bonus(tier, rarity), "label": weapon_label(r["weapon"])}


def equipped_bonus(conn, player_id: int = 1) -> float:
    eq = get_equipped(conn, player_id)
    return eq["bonus"] if eq else 0.0


def _set_equipped(conn, player_id: int, tier: int, rarity: int) -> None:
    conn.execute(
        "UPDATE character_profiles SET weapon_tier=?, weapon_rarity=? "
        "WHERE character_type='player' AND character_id=?;", (tier, rarity, player_id))


def try_equip_drop(conn, player_id: int, wtype: str | None,
                   tier: int, rarity: int) -> dict:
    """Decide cosa fare di un'arma trovata. NON pesca nulla a caso: applica la regola
    'stesso tipo e più forte → equipaggia, altrimenti lascia'. Ritorna lo stato e i
    dati per comporre il messaggio."""
    wtype = normalize(wtype) if wtype else None
    if wtype is None:
        return {"status": "invalid"}
    found = describe_weapon(wtype, tier, rarity)
    eq = get_equipped(conn, player_id)
    if eq is None:
        return {"status": "no_path", "found": found}
    if wtype != eq["type"]:
        return {"status": "wrong_type", "found": found,
                "found_type": weapon_label(wtype), "mine": eq["label"]}
    mine = describe_weapon(eq["type"], eq["tier"], eq["rarity"])
    if weapon_score(tier, rarity) > weapon_score(eq["tier"], eq["rarity"]):
        _set_equipped(conn, player_id, tier, rarity)
        return {"status": "equipped", "found": found, "old": mine,
                "bonus": weapon_bonus(tier, rarity)}
    return {"status": "weaker", "found": found, "mine": mine}
