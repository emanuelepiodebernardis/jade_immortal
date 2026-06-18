"""
Bottino ed eredità — ciò che un caduto importante lascia sul campo.

Principio: i deboli non lasciano nulla di rilevante, ma quando cade un PATRIARCA,
un ANZIANO o un avversario di alto regno, la loro eredità resta da raccogliere:
il manuale di una tecnica segreta, l'essenza distillata del loro Dao, pillole di
coltivazione, un tesoro di pietre. Le bestie mitiche (creature di alto regno) lasciano
un NUCLEO che innesta un tratto permanente.

Il bottino cade a TERRA (inventario della location) e si raccoglie con 'loot'. È quindi
distinto dall'assorbimento (che divora l'essenza del cadavere): puoi fare entrambe le
cose, o solo una. Saccheggiare non sporca l'anima; divorare sì.
"""

from __future__ import annotations

import random
import sqlite3

from engine.systems import items
from engine.simulation import cultivation

GROUND = "ground"

# soglia di regno oltre la quale un avversario (anche non titolato) lascia eredità
_LEGACY_TIER = 4
# soglia di regno per cui una creatura lascia un nucleo (bestia "mitica")
_BEAST_CORE_TIER = 3

_DAO_NAME = {
    "spada": "della Spada", "lancia": "della Lancia", "sciabola": "della Sciabola",
    "arco": "dell'Arco", "pugno": "del Pugno", "bastone": "del Bastone",
    "corpo": "del Corpo", "fulmine": "del Fulmine", "anima": "dell'Anima",
    "destino": "del Destino", "tempo": "del Tempo", "spazio": "dello Spazio",
}

_KIND_CORE = {
    "beast":  ("Nucleo Bestiale", "grow_strength", "grow_vitality",
               "Il nucleo pulsante di una bestia: la sua potenza fisica può essere innestata."),
    "demon":  ("Cuore Demoniaco", "grow_aura", "grow_strength",
               "Un cuore demoniaco ancora caldo d'ira: innesta un'aura feroce."),
    "spirit": ("Essenza Spirituale", "grow_soul", "grow_soul",
               "L'essenza condensata di uno spirito: nutre l'anima."),
}


def _tier(conn, ctype, cid) -> int:
    try:
        return cultivation.realm_tier(conn, ctype, cid) or 1
    except Exception:
        return 1


def _strongest_dao(conn, npc_id: int):
    return conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type='npc' AND character_id=? ORDER BY comprehension DESC LIMIT 1;",
        (npc_id,)).fetchone()


def _rarity_for_tier(tier: int) -> str:
    if tier >= 7:
        return "leggendario"
    if tier >= 5:
        return "prezioso"
    if tier >= 4:
        return "raro"
    if tier >= 2:
        return "non_comune"
    return "comune"


def on_player_kill(conn: sqlite3.Connection, tick: int, rng: random.Random,
                   player, npc) -> list[str]:
    """Genera l'eredità lasciata da un caduto importante e la depone a terra.
    Ritorna righe narrative (vuoto se il bersaglio non lascia nulla di rilevante)."""
    row = conn.execute(
        "SELECT archetype, kind, location_id, name FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if row is None:
        return []
    kind = row["kind"] or "human"
    archetype = row["archetype"]
    loc = row["location_id"]
    name = row["name"]
    tier = _tier(conn, "npc", npc.id)

    drops: list[tuple[str, str, str, str, dict]] = []  # (name, type, rarity, desc, effects)

    if kind in ("beast", "demon", "spirit"):
        # bestie mitiche: solo le creature di alto regno lasciano un nucleo
        if tier >= _BEAST_CORE_TIER and rng.random() < 0.5 + 0.1 * (tier - _BEAST_CORE_TIER):
            core_name, c1, c2, desc = _KIND_CORE[kind]
            amt = max(2, int(tier * 1.5))
            eff = {c1: amt}
            if c2 != c1:
                eff[c2] = max(1, amt // 2)
            drops.append((f"{core_name} di {name}", "nucleo",
                          _rarity_for_tier(tier), desc, eff))
        if not drops:
            return []
    else:
        important = archetype in ("patriarca", "anziano") or tier >= _LEGACY_TIER
        if not important:
            return []
        rarity = _rarity_for_tier(tier)
        # 1) manuale di tecnica (eredità marziale) — sempre per i patriarchi
        if archetype == "patriarca" or tier >= 5:
            magnitude = round(0.06 + 0.02 * tier, 3)
            tname = _legacy_technique_name(conn, npc.id, name)
            drops.append((
                f"Manuale: {tname}", "manuale", rarity,
                f"L'eredità marziale di {name}. Studiandolo apprendi la sua tecnica.",
                {"learn_technique": {"name": tname, "magnitude": magnitude,
                                     "tech_key": f"legacy:{npc.id}"}}))
        # 2) essenza del suo Dao più alto
        dao = _strongest_dao(conn, npc.id)
        if dao and dao["comprehension"] and rng.random() < 0.8:
            gain = max(2, int(dao["comprehension"] * 0.25))
            dname = _DAO_NAME.get(dao["dao_key"], f"«{dao['dao_key']}»")
            drops.append((
                f"Essenza del Dao {dname}", "essenza", rarity,
                f"L'intento distillato del Dao {dname}. Approfondisce la tua comprensione.",
                {"dao_key": dao["dao_key"], "dao_gain": gain}))
        # 3) pillola di coltivazione (a volte)
        if rng.random() < (0.7 if archetype == "patriarca" else 0.4):
            prog = round(0.25 + 0.05 * tier, 2)
            drops.append((
                "Pillola dell'Eredità", "pillola", rarity,
                "Una pillola intrisa dell'energia del caduto: fa avanzare la coltivazione.",
                {"cultivation_progress": prog}))
        # 4) tesoro di pietre spirituali
        stones = rng.randint(20, 60) * tier
        drops.append((
            "Borsa di Pietre Spirituali", "tesoro", rarity,
            "Le ricchezze accumulate dal caduto.", {"stones": stones}))
        # 5) la sua ARMA — droppa quasi sempre per i patriarchi, spesso per gli altri
        if archetype == "patriarca" or rng.random() < 0.6:
            wdrop = _weapon_drop(conn, rng, npc.id, tier)
            if wdrop:
                drops.append(wdrop)

    # deponi a terra DOVE SI TROVA IL GIOCATORE (il nemico potrebbe essersi spostato
    # tra un colpo e l'altro: il bottino deve restare dove combatti, raccoglibile con 'loot')
    deposit_loc = getattr(player, "location_id", None) or loc
    for nm, itype, rar, desc, eff in drops:
        iid = items.create_item(conn, nm, itype, rar, desc, eff)
        items.grant(conn, GROUND, deposit_loc, iid, 1)

    lines = [f"⚑ {name} lascia un'eredità sul terreno ({len(drops)} oggetti). "
             f"Usa 'loot' per raccoglierla."]
    return lines


def _weapon_drop(conn, rng, npc_id: int, tier: int):
    """Costruisce il drop dell'arma del caduto: tipo derivato dalla sua via (Dao d'arma)
    o casuale, regno = suo regno, rarità tirata (più alta a regni alti)."""
    from engine.systems import weapons
    wtype = None
    for r in conn.execute(
            "SELECT dao_key FROM character_daos WHERE character_type='npc' AND character_id=? "
            "ORDER BY comprehension DESC;", (npc_id,)).fetchall():
        if r["dao_key"] in weapons.WEAPONS:
            wtype = r["dao_key"]
            break
    if wtype is None:
        wtype = rng.choice(list(weapons.WEAPONS.keys()))
    rarity = _roll_rarity(rng, tier)
    # Dao del Destino: la fortuna può elevare la classe dell'arma trovata
    from engine.systems import dao_powers
    if rng.random() < dao_powers.fate_loot_bonus(conn, 1):
        rarity = min(weapons.RARITY_MAX, rarity + 1)
    label = weapons.describe_weapon(wtype, tier, rarity)
    return (label, "arma", _rarity_for_tier(tier),
            f"Un'arma da {weapons.weapon_label(wtype).lower()} forgiata per il suo regno.",
            {"weapon_type": wtype, "tier": tier, "rarity": rarity})


def _roll_rarity(rng, tier: int) -> int:
    """Rarità 1..4. I regni più alti pesano verso le classi superiori."""
    if tier >= 6:
        weights = [1, 2, 4, 4]
    elif tier >= 4:
        weights = [2, 3, 3, 2]
    elif tier >= 2:
        weights = [4, 3, 2, 1]
    else:
        weights = [6, 3, 1, 0]
    return rng.choices([1, 2, 3, 4], weights=weights)[0]


def _legacy_technique_name(conn, npc_id: int, npc_name: str) -> str:
    """Nome della tecnica eredità, ispirato all'elemento/Dao del caduto."""
    dao = _strongest_dao(conn, npc_id)
    suffix = _DAO_NAME.get(dao["dao_key"], "") if dao else ""
    if suffix:
        return f"Arte Suprema {suffix}"
    return "Arte Segreta del Patriarca"


# ============================================================
# Raccolta
# ============================================================

def drops_in_location(conn: sqlite3.Connection, location_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT inv.id AS inv_id, inv.quantity, i.id AS item_id, i.name, i.item_type, "
        "i.rarity, i.description "
        "FROM inventories inv JOIN items i ON i.id=inv.item_id "
        "WHERE inv.owner_type=? AND inv.owner_id=? AND inv.quantity>0 ORDER BY i.id;",
        (GROUND, location_id)).fetchall()


def take_all(conn: sqlite3.Connection, player_id: int, location_id: int) -> list[str]:
    """Raccoglie tutto il bottino a terra nello zaino del giocatore."""
    rows = drops_in_location(conn, location_id)
    if not rows:
        return []
    taken = []
    for r in rows:
        items.grant(conn, "player", player_id, r["item_id"], r["quantity"])
        conn.execute("DELETE FROM inventories WHERE id=?;", (r["inv_id"],))
        taken.append(r["name"])
    return taken
