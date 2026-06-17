"""
Oggetti speciali — l'EREDITÀ materiale del mondo.

Un oggetto è un dono concreto che si può tenere nello zaino e usare: una pillola
che fa avanzare la coltivazione, un'essenza che approfondisce un Dao, il nucleo di
una bestia mitica che innesta un tratto permanente, un manuale che insegna una
tecnica segreta, un tesoro di pietre spirituali.

Coerente col resto del gioco: gli effetti sono PERMANENTI e si SENTONO (il progresso
si deve sentire), i numeri grezzi restano in gran parte nascosti, a schermo prevalgono
le etichette qualitative. Gli oggetti arrivano soprattutto come BOTTINO (vedi loot.py:
i patriarchi e gli anziani lasciano la loro eredità quando cadono), ma il sistema è
generale e riusabile.

Tabelle usate: items (definizione) + inventories (possesso). effects è un JSON.
"""

from __future__ import annotations

import json
import random
import sqlite3

# rarità: ordine crescente di pregio (per ordinamento e colore narrativo)
RARITY_ORDER = ["comune", "non_comune", "raro", "prezioso", "leggendario"]

_RARITY_WORD = {
    "comune": "comune",
    "non_comune": "non comune",
    "raro": "raro",
    "prezioso": "prezioso",
    "leggendario": "leggendario",
}


# ============================================================
# Creazione e possesso
# ============================================================

def create_item(conn: sqlite3.Connection, name: str, item_type: str,
                rarity: str, description: str, effects: dict) -> int:
    cur = conn.execute(
        "INSERT INTO items (name, item_type, rarity, description, effects) "
        "VALUES (?, ?, ?, ?, ?);",
        (name, item_type, rarity, description, json.dumps(effects, ensure_ascii=False)))
    return cur.lastrowid


def grant(conn: sqlite3.Connection, owner_type: str, owner_id: int,
          item_id: int, quantity: int = 1) -> None:
    """Aggiunge un oggetto a un inventario. Gli oggetti unici (ogni create_item è un id
    distinto) non si impilano: una riga di inventario per id."""
    row = conn.execute(
        "SELECT id, quantity FROM inventories WHERE owner_type=? AND owner_id=? AND item_id=?;",
        (owner_type, owner_id, item_id)).fetchone()
    if row:
        conn.execute("UPDATE inventories SET quantity=quantity+? WHERE id=?;",
                     (quantity, row["id"]))
    else:
        conn.execute(
            "INSERT INTO inventories (owner_type, owner_id, item_id, quantity) "
            "VALUES (?, ?, ?, ?);", (owner_type, owner_id, item_id, quantity))


def player_inventory(conn: sqlite3.Connection, player_id: int = 1) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT inv.id AS inv_id, inv.quantity, i.id AS item_id, i.name, i.item_type, "
        "i.rarity, i.description, i.effects "
        "FROM inventories inv JOIN items i ON i.id=inv.item_id "
        "WHERE inv.owner_type='player' AND inv.owner_id=? AND inv.quantity>0 "
        "ORDER BY i.id;", (player_id,)).fetchall()


def find_in_inventory(conn: sqlite3.Connection, player_id: int,
                      frag: str) -> sqlite3.Row | None:
    frag = (frag or "").strip().lower()
    if not frag:
        return None
    for r in player_inventory(conn, player_id):
        if frag in r["name"].lower():
            return r
    return None


def _consume_one(conn: sqlite3.Connection, inv_id: int) -> None:
    conn.execute("UPDATE inventories SET quantity=quantity-1 WHERE id=?;", (inv_id,))
    conn.execute("DELETE FROM inventories WHERE id=? AND quantity<=0;", (inv_id,))


# ============================================================
# Uso / applicazione degli effetti
# ============================================================

def _grow(conn, player_id, col, amount) -> None:
    conn.execute(
        f"UPDATE character_profiles SET {col}={col}+? "
        "WHERE character_type='player' AND character_id=?;", (amount, player_id))


def apply_effects(conn: sqlite3.Connection, tick: int, rng: random.Random,
                  player_id: int, effects: dict) -> list[str]:
    """Applica gli effetti di un oggetto. Ritorna righe descrittive (qualitative)."""
    lines: list[str] = []

    # tratti fisici permanenti (nuclei di bestia, tesori del corpo)
    grow_map = {"grow_strength": "forza", "grow_vitality": "vitalità",
                "grow_resistance": "resistenza", "grow_aura": "aura",
                "grow_soul": "anima"}
    bits = []
    for col, word in grow_map.items():
        v = int(effects.get(col, 0) or 0)
        if v:
            _grow(conn, player_id, col, v)
            bits.append(f"+{v} {word}")
    if bits:
        lines.append("Il tuo corpo muta: " + ", ".join(bits) + ".")

    # avanzamento della coltivazione (pillole)
    cp = float(effects.get("cultivation_progress", 0) or 0)
    if cp:
        from engine.simulation import cultivation
        res = cultivation.cultivate(conn, "player", player_id, tick, rng, amount=cp)
        label = cultivation.realm_label(conn, "player", player_id)
        msg = f"L'energia dilaga nei meridiani: {label} — esperienza {res['progress']*100:.0f}%."
        if res.get("stage_up"):
            msg += f" Avanzi allo Strato {res['stage']}!"
        if res.get("ready"):
            msg += " Sei al colmo: tenta un 'breakthrough'."
        lines.append(msg)

    # affinamento di un Dao (essenze, intuizioni)
    dao_key = effects.get("dao_key")
    dao_gain = int(effects.get("dao_gain", 0) or 0)
    if dao_key and dao_gain:
        from engine.systems import absorption
        absorption._raise_comprehension(conn, dao_key, dao_gain, player_id)
        from engine.systems import dao_training
        try:
            label = dao_training.comprehension_label(_dao_comp(conn, player_id, dao_key))
        except Exception:
            label = "più profonda"
        lines.append(f"Una folgorazione: la tua comprensione del Dao «{dao_key}» è ora {label}.")

    # radici spirituali (affinità di coltivazione)
    aff = int(effects.get("aff_cultivation", 0) or 0)
    if aff:
        conn.execute(
            "UPDATE character_profiles SET aff_cultivation=MIN(100, aff_cultivation+?) "
            "WHERE character_type='player' AND character_id=?;", (aff, player_id))
        lines.append("Le tue radici spirituali si affinano.")

    # tecnica segreta insegnata da un manuale/eredità (bonus di potenza permanente)
    learn = effects.get("learn_technique")
    if learn:
        name = learn.get("name", "Tecnica Misteriosa")
        magnitude = float(learn.get("magnitude", 0.08))
        tech_key = learn.get("tech_key", f"legacy:{name}")
        existing = conn.execute(
            "SELECT 1 FROM learned_techniques WHERE player_id=? AND tech_key=?;",
            (player_id, tech_key)).fetchone()
        if existing:
            lines.append(f"Conosci già {name}: il manuale non ti insegna nulla di nuovo.")
        else:
            conn.execute(
                "INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, "
                "magnitude, learned_tick) VALUES (?, NULL, ?, ?, ?, ?);",
                (player_id, tech_key, name, magnitude, tick))
            lines.append(f"Apprendi {name}! La tua potenza cresce (+{int(magnitude*100)}%).")

    # pietre spirituali (tesori)
    stones = int(effects.get("stones", 0) or 0)
    if stones:
        from engine.systems import sects
        total = sects.grant_resource(conn, "pietre_spirituali", stones, player_id)
        lines.append(f"+{stones} pietre spirituali (totale: {total}).")

    if not lines:
        lines.append("Lo osservi a lungo, ma non ne ricavi nulla di tangibile.")
    return lines


def _dao_comp(conn, player_id, dao_key) -> int:
    r = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key=?;", (player_id, dao_key)).fetchone()
    return r["comprehension"] if r else 0


def use_item(conn: sqlite3.Connection, tick: int, rng: random.Random,
             player_id: int, frag: str) -> dict:
    """Usa (consuma) un oggetto dall'inventario per frammento di nome."""
    row = find_in_inventory(conn, player_id, frag)
    if row is None:
        return {"status": "not_found"}
    try:
        effects = json.loads(row["effects"]) if row["effects"] else {}
    except Exception:
        effects = {}
    lines = apply_effects(conn, tick, rng, player_id, effects)
    _consume_one(conn, row["inv_id"])
    return {"status": "used", "name": row["name"], "lines": lines}


# ============================================================
# Display
# ============================================================

def rarity_word(rarity: str) -> str:
    return _RARITY_WORD.get(rarity, rarity or "comune")


def describe_item(row: sqlite3.Row) -> str:
    qty = f" ×{row['quantity']}" if row["quantity"] and row["quantity"] > 1 else ""
    return f"{row['name']}{qty} [{rarity_word(row['rarity'])}] — {row['description']}"
