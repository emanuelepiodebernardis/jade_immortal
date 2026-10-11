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
        # una pillola vale meno a ogni regno, come la meditazione (prima a regni alti valeva
        # quanto decine di sessioni e faceva salire di cinque regni in ottanta giorni)
        tier = cultivation.realm_tier(conn, "player", player_id) or 1
        res = cultivation.cultivate(conn, "player", player_id, tick, rng, amount=cp / (1 + (tier - 1) * 0.5))
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
        from engine.systems import spirit_roots
        spirit_roots.refine_all(conn, player_id, 0.01 * aff)

    rg = effects.get("root_gain")
    if rg:
        from engine.systems import spirit_roots
        el, amt = rg.get("element", "all"), float(rg.get("amount", 5))
        if el == "all":
            spirit_roots.refine_all(conn, player_id, amt / 100.0)
            lines.append(f"Tutte le tue radici spirituali si affinano (+{amt:g}%).")
        else:
            if el == "random":
                el = rng.choice(spirit_roots.ELEMENTS)
            sc = spirit_roots.add(conn, "player", player_id, el, amt)
            lines.append(f"La tua radice di {spirit_roots.LABEL[el]} cresce (+{amt:g}, ora {sc:.0f}: "
                         f"{spirit_roots.grade_name(sc)}).")

    pf = effects.get("place_formation")
    if pf:
        from engine.systems import formations
        lines.append(formations.place(conn, player_id, pf["kind"], int(pf.get("level", 1))))
    if effects.get("purify"):
        from engine.systems import dao_heart
        lines.append(dao_heart.purify(conn, float(effects["purify"])))
    if effects.get("bloodline"):
        from engine.systems import bloodlines
        lines.append("Raffini l'essenza e la lasci scorrere nelle vene…")
        lines += bloodlines.use_essence(conn, tick, rng, player_id, effects["bloodline"])
    if effects.get("beast_lure"):
        from engine.systems import beasts
        from engine.core import entities as _ent
        nid, lname = beasts.spawn_rare(conn, rng, _ent.get_player(conn, player_id))
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        lines.append(f"L'odore dell'esca si spande nel vento… {nm} è stato avvistato a {lname}.")
    if effects.get("beast_stages") or effects.get("beast_talent") or effects.get("beast_element"):
        from engine.systems import beasts, npc_factory, classes
        pts = beasts.pets(conn, player_id)
        if not pts:
            lines.append("Non hai bestie su cui usarlo: l'effetto si disperde.")
        for pt in pts:
            if effects.get("beast_stages"):
                npc_factory.raise_npc(conn, pt["npc_id"], int(effects["beast_stages"]))
                lines.append(f"{pt['name']} cresce di {int(effects['beast_stages'])} strati.")
            if effects.get("beast_talent"):
                tr = beasts.traits(conn, pt["npc_id"])
                names = [x[0] for x in beasts.TALENTS]
                new = names[min(len(names) - 1, names.index(tr["talent"]) + int(effects["beast_talent"]))]
                conn.execute("UPDATE beast_traits SET talent=? WHERE npc_id=?;", (new, pt["npc_id"]))
                lines.append(f"{pt['name']} risveglia la sua stirpe: talento «{new}».")
            if effects.get("beast_element"):
                tr = beasts.traits(conn, pt["npc_id"])
                els = [e for e in (tr["elements"] or "").split(",") if e]
                for e in classes.attunement(conn, player_id):
                    if e not in els:
                        els.append(e)
                conn.execute("UPDATE beast_traits SET elements=? WHERE npc_id=?;", (",".join(els), pt["npc_id"]))
                lines.append(f"{pt['name']} ora porta in sé: {', '.join(els)}.")

    gf = effects.get("gongfa")
    if gf:
        from engine.systems import gongfa
        m = gf if gf.get("name") else gongfa.generate(rng, int(gf.get("grade", 1)), gf.get("element"))
        lines.append(gongfa.learn(conn, player_id, m))

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

    # --- effetti degli oggetti ARTIGIANALI (alchimia, talismani) ---
    if effects.get("heal_injuries"):
        n = conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' "
                         "AND character_id=? AND healed=0;", (player_id,)).rowcount
        lines.append("Le tue ferite si richiudono." if n else "Non hai ferite da curare.")
    if effects.get("bt_bonus"):
        from engine.systems import heart_demon
        heart_demon.add_bonus(conn, float(effects["bt_bonus"]))
        lines.append("Le tue fondamenta si consolidano: il prossimo breakthrough sarà più sicuro.")
    if effects.get("lifespan_years"):
        from engine.systems import lifespan
        lifespan.add_bonus_years(conn, int(effects["lifespan_years"]))
        lines.append(f"Il tempo rallenta nelle tue vene: +{int(effects['lifespan_years'])} anni di vita.")
    if effects.get("combat_buff"):
        from engine.systems import state
        buffs = state.get_json(conn, "combat_buffs", []) or []
        buffs.append(effects["combat_buff"])
        state.set_json(conn, "combat_buffs", buffs)
        lines.append(f"Prepari il talismano: si attiverà all'inizio del prossimo scontro "
                     f"({effects['combat_buff'].get('name', 'talismano')}).")

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
    if effects.get("egg"):
        from engine.systems import beast_eggs
        why = beast_eggs.can_incubate(conn, player_id)
        if why:
            return {"status": "used", "name": row["name"], "lines": [why + " (l'uovo resta nello zaino)"]}
        lines = beast_eggs.incubate(conn, player_id, effects["egg"])
        _consume_one(conn, row["inv_id"])
        return {"status": "used", "name": row["name"], "lines": lines}
    lines = apply_effects(conn, tick, rng, player_id, effects)
    if row["item_type"] == "pillola" and effects.get("cultivation_progress"):
        from engine.systems import dao_heart
        lines += dao_heart.on_pill(conn, player_id, float(effects["cultivation_progress"]))
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
