"""
Fondamenta del Personaggio (prima passata).

Origini con vantaggi E trade-off (nessuna build dominante). Affinità come NUMERI
INTERNI (servono ai sistemi: coltivazione, breakthrough, combattimento) ma MAI
mostrati grezzi: il giocatore vede etichette qualitative ("discreta affinità...").

Le origini agganciano solo sistemi GIÀ esistenti (regno/età iniziali, velocità di
coltivazione, successo del breakthrough, potenza in combattimento, disposizione
degli NPC). Dao, tecniche e anomalie arriveranno dopo: qui si pongono le basi.
"""

from __future__ import annotations

import json
import random
import sqlite3

YEAR_TICKS = 2000   # conversione approssimativa tick -> anni (solo flavor)

AFFINITY_KEYS = ["cultivation", "body", "qi", "soul", "combat"]
AFF_LABELS_IT = {
    "cultivation": "coltivazione", "body": "corpo", "qi": "qi",
    "soul": "anima", "combat": "istinto di combattimento",
}

# Origini: ogni voce ha pregi e difetti. 'aff' sono valori base (con jitter).
ORIGINS = {
    "mortale": {
        "name": "Mortale comune",
        "desc": "Nessun privilegio, nessun fardello. Tutto è da conquistare.",
        "start_tier": 1, "age": 16,
        "aff": {"cultivation": 45, "body": 50, "qi": 48, "soul": 45, "combat": 50},
        "flags": {},
    },
    "clan": {
        "name": "Discendente di clan",
        "desc": "Risorse e un nome alle spalle — ma anche rivali che quel nome se lo ricordano.",
        "start_tier": 1, "age": 17,
        "aff": {"cultivation": 55, "body": 55, "qi": 55, "soul": 50, "combat": 55},
        "flags": {"resources": True, "more_enemies": True},
    },
    "genio": {
        "name": "Genio",
        "desc": "Comprensione fulminea. Ma il cielo invidia i geni: le tribolazioni saranno più dure.",
        "start_tier": 1, "age": 15,
        "aff": {"cultivation": 82, "body": 55, "qi": 70, "soul": 60, "combat": 55},
        "flags": {"hard_tribulation": True},
    },
    "reincarnato": {
        "name": "Reincarnato",
        "desc": "Porti memorie di un'altra vita. Ma due anime in un corpo possono incrinarsi.",
        "start_tier": 1, "age": 16,
        "aff": {"cultivation": 62, "body": 48, "qi": 58, "soul": 78, "combat": 52},
        "flags": {"mental_deviation": True},
    },
    "erede": {
        "name": "Erede di un immortale",
        "desc": "Inizi più avanti, con un'eredità rara. Mezzo mondo la vuole.",
        "start_tier": 2, "age": 18,
        "aff": {"cultivation": 60, "body": 58, "qi": 60, "soul": 55, "combat": 66},
        "flags": {"hunted": True},
        "daos": {"practiced": ["spada", "corpo"], "latent": []},
    },
    "divoratore": {
        "name": "Portatore dell'Abisso Divoratore",
        "desc": "Un'anomalia rarissima: puoi divorare l'eredità altrui. Ma mezzo mondo "
                "ti vuole morto, e ogni assorbimento lascia un segno nell'anima.",
        "start_tier": 1, "age": 17,
        "aff": {"cultivation": 55, "body": 60, "qi": 50, "soul": 82, "combat": 60},
        "flags": {"hunted": True, "anomaly": "abisso_divoratore"},
        "anomaly": "abisso_divoratore",
        # pratica Corpo/Anima/Fulmine; affinità LATENTI verso i Dao profondi
        "daos": {"practiced": ["corpo", "anima", "fulmine"],
                 "latent": ["destino", "tempo", "spazio"]},
    },
}


def label_for(value: int) -> str:
    if value < 30:
        return "scarsa"
    if value < 45:
        return "modesta"
    if value < 60:
        return "discreta"
    if value < 75:
        return "notevole"
    if value < 88:
        return "eccezionale"
    return "prodigiosa"


def load_default_origin() -> str | None:
    """Origine preimpostata da config (per non scegliere a ogni avvio). None = scelta manuale."""
    from engine.db import PROJECT_ROOT
    path = PROJECT_ROOT / "config" / "settings.yaml"
    if not path.exists():
        return None
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        val = (data.get("character", {}) or {}).get("default_origin")
        return val if val in ORIGINS else None
    except Exception:
        return None


def list_origins() -> list[tuple[str, dict]]:
    return list(ORIGINS.items())


def get_profile(conn: sqlite3.Connection, ctype: str, cid: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM character_profiles WHERE character_type=? AND character_id=?;",
        (ctype, cid),
    ).fetchone()


def has_profile(conn: sqlite3.Connection, ctype: str = "player", cid: int = 1) -> bool:
    return get_profile(conn, ctype, cid) is not None


def affinity_factor(conn: sqlite3.Connection, ctype: str, cid: int, which: str) -> float:
    """Moltiplicatore derivato dall'affinità (50 = neutro 1.0). 1.0 se senza profilo."""
    p = get_profile(conn, ctype, cid)
    if p is None:
        return 1.0
    val = p[f"aff_{which}"] if f"aff_{which}" in p.keys() else 50
    return max(0.4, min(1.8, val / 50.0))


def has_flag(conn: sqlite3.Connection, ctype: str, cid: int, flag: str) -> bool:
    p = get_profile(conn, ctype, cid)
    if p is None or not p["flags"]:
        return False
    try:
        return bool(json.loads(p["flags"]).get(flag))
    except Exception:
        return False


def apply_origin(conn: sqlite3.Connection, origin_key: str, rng: random.Random,
                 player_id: int = 1) -> dict:
    """Crea il profilo del giocatore dall'origine scelta e applica gli effetti."""
    origin = ORIGINS.get(origin_key, ORIGINS["mortale"])
    aff = {k: max(1, min(100, origin["aff"][k] + rng.randint(-6, 6))) for k in AFFINITY_KEYS}

    conn.execute(
        "INSERT INTO character_profiles "
        "(character_type, character_id, origin, age, aff_cultivation, aff_body, "
        " aff_qi, aff_soul, aff_combat, anomaly, soul_residue, flags, created_tick) "
        "VALUES ('player', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0) "
        "ON CONFLICT(character_type, character_id) DO UPDATE SET "
        "origin=excluded.origin, age=excluded.age, aff_cultivation=excluded.aff_cultivation, "
        "aff_body=excluded.aff_body, aff_qi=excluded.aff_qi, aff_soul=excluded.aff_soul, "
        "aff_combat=excluded.aff_combat, anomaly=excluded.anomaly, flags=excluded.flags;",
        (player_id, origin_key, origin["age"], aff["cultivation"], aff["body"],
         aff["qi"], aff["soul"], aff["combat"], origin.get("anomaly"),
         json.dumps(origin["flags"])),
    )

    # Dao praticati + affinità latenti (dall'origine)
    from engine.generators import dao_gen
    daos = origin.get("daos", {"practiced": ["corpo"], "latent": []})
    dao_gen.assign_player_daos(conn, rng, daos.get("practiced", []),
                               daos.get("latent", []), player_id)

    # regno iniziale dall'origine
    realm = conn.execute(
        "SELECT id FROM cultivation_realms WHERE tier=?;", (origin["start_tier"],)
    ).fetchone()
    if realm:
        conn.execute("UPDATE players SET realm_id=? WHERE id=?;", (realm["id"], player_id))
        conn.execute(
            "UPDATE cultivation_records SET realm_id=? "
            "WHERE character_type='player' AND character_id=?;",
            (realm["id"], player_id),
        )

    # trade-off: nemici iniziali
    _apply_enemy_flags(conn, origin["flags"], rng, player_id)
    return origin


def _apply_enemy_flags(conn, flags, rng, player_id) -> None:
    from engine.systems import relations
    if not (flags.get("hunted") or flags.get("more_enemies")):
        return
    n = 3 if flags.get("hunted") else 2
    delta = -50 if flags.get("hunted") else -25   # hunted = nemici; more_enemies = rivali
    npcs = [r["id"] for r in conn.execute(
        "SELECT id FROM npcs WHERE status='alive' ORDER BY id;")]
    rng.shuffle(npcs)
    for nid in npcs[:n]:
        relations.adjust(conn, nid, delta, tick=0, player_id=player_id)


def describe_profile(conn: sqlite3.Connection, current_tick: int = 0,
                     player_id: int = 1) -> str:
    p = get_profile(conn, "player", player_id)
    if p is None:
        return "Non hai ancora un'origine definita."
    origin = ORIGINS.get(p["origin"], ORIGINS["mortale"])
    age_now = (p["age"] or 16) + current_tick // YEAR_TICKS
    lines = [f"Origine: {origin['name']} — {origin['desc']}",
             f"Età: {age_now} anni"]
    affs = [f"{AFF_LABELS_IT[k]}: {label_for(p[f'aff_{k}'])}" for k in AFFINITY_KEYS]
    lines.append("Affinità — " + "; ".join(affs) + ".")
    notes = []
    if has_flag(conn, "player", player_id, "hunted"):
        notes.append("Sei braccato: qualcuno ti vuole morto.")
    if has_flag(conn, "player", player_id, "more_enemies"):
        notes.append("Il tuo nome attira rivalità.")
    if has_flag(conn, "player", player_id, "hard_tribulation"):
        notes.append("Il cielo ti osserva: le tribolazioni saranno più severe.")
    if has_flag(conn, "player", player_id, "mental_deviation"):
        notes.append("Echi di un'altra vita turbano la tua mente.")
    if notes:
        lines.append(" ".join(notes))
    # crescita fisica da assorbimento (qualitativa)
    body = []
    if (p["grow_strength"] or 0) > 0:
        body.append(f"forza {label_for(min(100, 30 + p['grow_strength']))}")
    if (p["grow_vitality"] or 0) > 0:
        body.append(f"vitalità {label_for(min(100, 30 + p['grow_vitality']))}")
    if (p["grow_resistance"] or 0) > 0:
        body.append(f"resistenza {label_for(min(100, 30 + p['grow_resistance']))}")
    if (p["grow_aura"] or 0) > 0:
        body.append(f"aura {label_for(min(100, 30 + p['grow_aura']))}")
    if (p["grow_soul"] or 0) > 0:
        body.append(f"anima forgiata {label_for(min(100, 30 + p['grow_soul']))}")
    if body:
        lines.append("Corpo forgiato dall'Abisso — " + "; ".join(body) + ".")
    # corruzione dell'Abisso (con effetti a soglia)
    if p["anomaly"] == "abisso_divoratore":
        from engine.systems import absorption
        res = p["soul_residue"] or 0
        clab = absorption.corruption_label(res)
        lines.append(f"Corruzione dell'Abisso: {clab}.")
        path = absorption.evolution_path(conn, player_id)
        if path:
            lines.append(f"Ciò che stai diventando: {path}.")
    return "\n".join(lines)
