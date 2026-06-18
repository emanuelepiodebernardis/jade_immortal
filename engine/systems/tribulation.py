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


# ============================================================
# TRIBOLAZIONE DIVINA — il prezzo della sfida al Cielo (heaven_defiance)
# ------------------------------------------------------------
# Quando padroneggi Spazio/Tempo/Destino il Cielo scaglia il castigo. Chi ha
# affinità col FULMINE lo doma: ogni folgore assorbita dona benedizioni e, soprattutto,
# RISVEGLIA poteri SPAZIALI; e l'intera prova PURIFICA l'Abisso, azzerando la corruzione.
# Chi non regge resta scottato (ferite + arretramento), ma — di norma — non muore.
# ============================================================

def _ensure_dao(conn, dao_key, player_id) -> None:
    row = conn.execute(
        "SELECT 1 FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND dao_key=?;", (player_id, dao_key)).fetchone()
    if row is None:
        # affinità di base se il Dao non era nemmeno latente
        conn.execute(
            "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, "
            "comprehension, practiced) VALUES ('player', ?, ?, 60, 0, 1);",
            (player_id, dao_key))
    else:
        conn.execute(
            "UPDATE character_daos SET practiced=1 WHERE character_type='player' "
            "AND character_id=? AND dao_key=?;", (player_id, dao_key))


def _raise_space(conn, amount, player_id) -> int:
    _ensure_dao(conn, "spazio", player_id)
    conn.execute(
        "UPDATE character_daos SET comprehension=comprehension+? "
        "WHERE character_type='player' AND character_id=? AND dao_key='spazio';",
        (amount, player_id))
    r = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key='spazio';", (player_id,)).fetchone()
    return r["comprehension"] if r else amount


def resolve_tribulation(conn: sqlite3.Connection, tick: int, rng: random.Random,
                        power: int, player_id: int = 1) -> dict:
    """Affronta una tribolazione divina di potenza `power`. Ritorna un esito narrativo."""
    from engine.simulation import combat
    from engine.systems import dao_powers, character
    cp = combat.combat_power(conn, "player", player_id)
    fulmine = _fulmine_comp(conn, player_id)
    resist = fulmine_resistance(conn, player_id) + cp["defense"] * 0.5 + cp["vitality"] * 0.3
    bolts = max(1, power // 25)
    per_bolt = power / bolts
    absorbed = 0
    lines = []
    boons = []
    for _ in range(bolts):
        if resist * rng.uniform(0.75, 1.25) >= per_bolt:
            absorbed += 1
            if fulmine > 0:
                boons.append(grant_boon(conn, rng, player_id))   # il Fulmine ti appartiene
    survived = absorbed >= (bolts + 1) // 2          # reggi almeno metà delle folgori

    head = (f"⚡ TRIBOLAZIONE DIVINA (potenza {power}): {bolts} folgori si abbattono su di te. "
            f"Ne assorbi {absorbed}.")
    lines.append(head)

    if survived:
        space_line = ""
        if fulmine > 0:
            # affinità col Fulmine → la folgore RISVEGLIA poteri SPAZIALI
            gain = 8 + power // 20
            newc = _raise_space(conn, gain, player_id)
            space_line = (f" Le folgori risvegliano in te il Dao dello Spazio "
                          f"(+{gain}, ora comprensione {newc}).")
        # PURIFICA l'Abisso: la corruzione da assorbimento torna a zero
        prof = character.get_profile(conn, "player", player_id)
        had_residue = (prof["soul_residue"] or 0) if prof else 0
        conn.execute(
            "UPDATE character_profiles SET soul_residue=0 "
            "WHERE character_type='player' AND character_id=?;", (player_id,))
        purge = (" Il tuono incenerisce la corruzione dell'Abisso: la tua anima torna limpida."
                 if had_residue else "")
        if boons:
            lines.append("Folgori domate → benedizioni: " + ", ".join(boons) + ".")
        lines.append("Hai DOMATO la tribolazione." + space_line + purge)
        conn.execute(
            "UPDATE character_profiles SET last_tribulation_defiance=? "
            "WHERE character_type='player' AND character_id=?;",
            (dao_powers.heaven_defiance(conn, player_id), player_id))
        return {"status": "survived", "absorbed": absorbed, "bolts": bolts,
                "boons": boons, "purified": bool(had_residue), "lines": lines}

    # non hai retto: ferite + arretramento della coltivazione (ma niente morte di norma)
    severity = max(2, min(10, int((per_bolt - resist) / max(1.0, per_bolt) * 10) + 3))
    heal_tick = tick + severity * 15
    conn.execute(
        "INSERT INTO injuries (character_type, character_id, severity, description, "
        "inflicted_tick, healed, heal_tick) VALUES ('player', ?, ?, ?, ?, 0, ?);",
        (player_id, severity, "ustioni della tribolazione", tick, heal_tick))
    conn.execute(
        "UPDATE cultivation_records SET progress=MAX(0, progress-0.4) "
        "WHERE character_type='player' AND character_id=?;", (player_id,))
    if boons:
        lines.append("Folgori parzialmente domate → benedizioni: " + ", ".join(boons) + ".")
    lines.append(f"Il castigo ti travolge: ustioni gravi (gravità {severity}) e coltivazione "
                 f"arretrata. Sopravvivi, ma il Cielo ti ha segnato.")
    conn.execute(
        "UPDATE character_profiles SET last_tribulation_defiance=? "
        "WHERE character_type='player' AND character_id=?;",
        (dao_powers.heaven_defiance(conn, player_id), player_id))
    return {"status": "scorched", "absorbed": absorbed, "bolts": bolts,
            "boons": boons, "severity": severity, "lines": lines}
