"""
Tecniche generate dai Dao (la via del Guerriero Dao).

Non serve scrivere centinaia di abilità a mano: le tecniche NASCONO dai Dao.
- Il Dao DOMINANTE dà l'identità della tecnica (Spada -> "Lama/Taglio/Intento...").
- Un Dao SECONDARIO la modifica (Fulmine -> "del Tuono"), cambiandone nome ed effetto.
- Crescendo il Dao, la tecnica EVOLVE a soglie (10/25/50/100/250/500/1000): stesso seme,
  nome e potenza che scalano all'infinito.

Queste tecniche derivano dal Dao: NON consumano Qi, ma affaticano lo SPIRITO.
"""

from __future__ import annotations

import sqlite3

from engine.systems import dao_training as dt

# Nomi del Dao DOMINANTE, per soglia (indice 0..7 = principiante..legislatore).
# L'indice 0 non genera tecnica (serve >=10). Le liste scalano col Dao.
_MAIN_NAMES = {
    "spada":    ["Taglio", "Primo Taglio", "Intento della Spada", "Dominio della Lama",
                 "Spada Celeste", "Spada dell'Eternità", "Legge della Spada", "Dao Vivente della Spada"],
    "sciabola": ["Fendente", "Mezzaluna", "Danza di Sciabole", "Tempesta di Lame",
                 "Sciabola Celeste", "Marea di Acciaio", "Legge della Sciabola", "Dao della Sciabola"],
    "lancia":   ["Affondo", "Punta Trafiggente", "Intento della Lancia", "Dominio dell'Asta",
                 "Lancia Celeste", "Lancia dell'Eternità", "Legge della Lancia", "Dao della Lancia"],
    "arco":     ["Tiro", "Freccia Certa", "Intento dell'Arco", "Pioggia di Strali",
                 "Arco Celeste", "Stella Cadente", "Legge dell'Arco", "Dao dell'Arco"],
    "pugno":    ["Colpo", "Pugno di Ferro", "Intento del Pugno", "Dominio del Corpo a Corpo",
                 "Pugno Celeste", "Montagna che Crolla", "Legge del Pugno", "Dao del Pugno"],
    "bastone":  ["Parata", "Guardia Rotante", "Intento del Bastone", "Dominio del Bastone",
                 "Bastone Celeste", "Pilastro del Cielo", "Legge del Bastone", "Dao del Bastone"],
    "corpo":    ["Pelle Dura", "Corpo di Ferro", "Corpo Diamantino", "Dominio del Corpo",
                 "Corpo Celeste", "Corpo Indistruttibile", "Legge del Corpo", "Dao del Corpo"],
    "fulmine":  ["Scarica", "Saetta", "Intento del Fulmine", "Dominio del Tuono",
                 "Fulmine Celeste", "Tribolazione Domata", "Legge del Fulmine", "Dao del Fulmine"],
    "tempo":    ["Istante", "Attimo Rubato", "Intento del Tempo", "Dominio dell'Istante",
                 "Tempo Celeste", "Eternità in un Battito", "Legge del Tempo", "Dao del Tempo"],
    "spazio":   ["Passo", "Passo Vuoto", "Intento dello Spazio", "Dominio della Distanza",
                 "Spazio Celeste", "Mondo Tascabile", "Legge dello Spazio", "Dao dello Spazio"],
    "destino":  ["Presagio", "Filo del Fato", "Intento del Destino", "Dominio del Fato",
                 "Destino Celeste", "Sentenza", "Legge del Destino", "Dao del Destino"],
    "anima":    ["Eco", "Pressione Spirituale", "Intento dell'Anima", "Dominio dello Spirito",
                 "Anima Celeste", "Sovrano dello Spirito", "Legge dell'Anima", "Dao dell'Anima"],
    "fuoco":    ["Fiammata", "Lingua di Fuoco", "Intento del Fuoco", "Inferno Vivente",
                 "Fuoco Celeste", "Sole Caduto", "Legge del Fuoco", "Dao del Fuoco"],
    "acqua":    ["Ondata", "Flusso", "Intento dell'Acqua", "Marea Inarrestabile",
                 "Acqua Celeste", "Oceano Senza Sponde", "Legge dell'Acqua", "Dao dell'Acqua"],
    "terra":    ["Zolla", "Muro di Roccia", "Intento della Terra", "Montagna Vivente",
                 "Terra Celeste", "Continente Immoto", "Legge della Terra", "Dao della Terra"],
    "vento":    ["Folata", "Lama di Vento", "Intento del Vento", "Tempesta Danzante",
                 "Vento Celeste", "Uragano Eterno", "Legge del Vento", "Dao del Vento"],
    "metallo":  ["Scheggia", "Lama d'Acciaio", "Intento del Metallo", "Mille Spade",
                 "Metallo Celeste", "Distruzione Affilata", "Legge del Metallo", "Dao del Metallo"],
    "legno":    ["Germoglio", "Radice Avvolgente", "Intento del Legno", "Foresta Vivente",
                 "Legno Celeste", "Albero del Mondo", "Legge del Legno", "Dao del Legno"],
    "luce":     ["Bagliore", "Raggio", "Intento della Luce", "Aurora Folgorante",
                 "Luce Celeste", "Alba della Creazione", "Legge della Luce", "Dao della Luce"],
    "oscurita": ["Ombra", "Tenebra", "Intento dell'Oscurità", "Notte Divorante",
                 "Oscurità Celeste", "Vuoto Senza Stelle", "Legge dell'Oscurità", "Dao dell'Oscurità"],
}

# Frase modificatrice quando un Dao è SECONDARIO.
_MODIFIERS = {
    "fulmine": "del Tuono", "spada": "Tagliente", "sciabola": "Lacerante",
    "lancia": "Trafiggente", "arco": "Fulmineo", "pugno": "Frantumante",
    "bastone": "Inarrestabile", "corpo": "Corporeo", "tempo": "Istantaneo",
    "spazio": "Senza Distanza", "destino": "Ineluttabile", "anima": "Spirituale",
    "fuoco": "Ardente", "acqua": "Travolgente", "terra": "Incrollabile",
    "vento": "del Vento", "metallo": "d'Acciaio", "legno": "Vivente",
    "luce": "Radiante", "oscurita": "Tenebroso",
}

_GRADE = ["", "iniziato", "adepto", "esperto", "maestro", "gran maestro", "dominatore", "legislatore"]


def _main_name(dao_key: str, idx: int) -> str:
    names = _MAIN_NAMES.get(dao_key)
    if names:
        return names[min(idx, len(names) - 1)]
    suffix = dt._dao_suffix(_dao_label(dao_key))
    return f"Intento {suffix}"


def _dao_label(dao_key: str) -> str:
    from engine.generators import dao_gen
    for k, name, *_ in dao_gen.DAOS:
        if k == dao_key:
            return name
    return dao_key.capitalize()


def _profile_mods(dao_key: str, idx: int, main_bonus: float, sec_bonus: float) -> dict:
    """Effetti scalati per identità del Dao dominante (linguaggio meccanico distinto)."""
    base_atk = 1.0 + 0.22 * idx + main_bonus * 0.6 + sec_bonus * 0.4
    death = min(0.45, 0.04 * idx + sec_bonus * 0.12)
    mods: dict = {"attack_mult": base_atk, "death_bonus": death}
    if dao_key in ("spada", "lancia", "arco"):
        mods["pierce"] = min(0.6, 0.08 * idx)
    if dao_key in ("sciabola", "pugno"):
        mods["extra_strikes"] = 1 + (1 if idx >= 5 else 0)
    if dao_key in ("bastone", "corpo"):
        mods["attack_mult"] = 1.0 + 0.14 * idx + main_bonus * 0.4
        mods["taken_mult"] = max(0.5, 1.0 - 0.06 * idx)     # difensiva: subisci meno
    if dao_key == "fulmine":
        mods["attack_mult"] += 0.15
        mods["death_bonus"] = min(0.5, death + 0.08)
    # elementi offensivi
    if dao_key in ("fuoco", "luce", "metallo", "oscurita", "vento"):
        mods["attack_mult"] += 0.10
        if dao_key in ("metallo", "oscurita"):
            mods["pierce"] = max(mods.get("pierce", 0.0), min(0.6, 0.07 * idx))
        if dao_key in ("fuoco", "luce"):
            mods["death_bonus"] = min(0.55, death + 0.06)
        if dao_key == "vento":
            mods["extra_strikes"] = mods.get("extra_strikes", 0) + (1 if idx >= 4 else 0)
    # elementi difensivi/vitali
    if dao_key in ("acqua", "terra", "legno"):
        mods["taken_mult"] = min(mods.get("taken_mult", 1.0), max(0.45, 1.0 - 0.05 * idx))
    if idx >= 5 and "extra_strikes" not in mods:
        mods["extra_strikes"] = 1
    return mods


def _secondary_contribution(dao_key: str, idx: int) -> dict:
    """Quanto un Dao SECONDARIO aggiunge a una tecnica FUSA (additivo, scalato col Dao)."""
    c = {"attack_mult": 0.05 + 0.02 * idx, "pierce": 0.0, "extra_strikes": 0,
         "death_bonus": 0.0, "taken_mult": 0.0}
    if dao_key in ("spada", "lancia", "arco", "metallo", "oscurita"):
        c["pierce"] += min(0.4, 0.05 * idx)
    if dao_key in ("sciabola", "pugno", "vento") and idx >= 4:
        c["extra_strikes"] += 1
    if dao_key in ("fulmine", "fuoco", "luce"):
        c["death_bonus"] += min(0.2, 0.04 * idx)
    if dao_key in ("corpo", "bastone", "acqua", "terra", "legno"):
        c["taken_mult"] += min(0.25, 0.04 * idx)
    return c


def dao_techniques(conn: sqlite3.Connection, player_id: int = 1) -> list[dict]:
    """Tecniche Dao del giocatore. La tecnica DOMINANTE è una FUSIONE: ogni Dao che supera
    la soglia (>=10) vi si unisce, aggiungendo nome ed effetto e rendendola più forte (3,
    4, … Dao). Gli altri Dao mantengono la propria tecnica singola."""
    rows = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type='player' AND character_id=? AND comprehension>=10 "
        "ORDER BY comprehension DESC;", (player_id,)).fetchall()
    if not rows:
        return []
    qualifying = [(r["dao_key"], r["comprehension"] or 0) for r in rows]
    main_key, main_comp = qualifying[0]
    main_idx = dt._tier_index(main_comp)
    secondaries = [(k, c) for k, c in qualifying[1:]]

    out: list[dict] = []

    # ---- TECNICA FUSA (dominante + tutti i secondari) ----
    sec_bonus0 = dt.dao_combat_bonus(secondaries[0][1]) if secondaries else 0.0
    mods = dict(_profile_mods(main_key, main_idx,
                              dt.dao_combat_bonus(main_comp), sec_bonus0))
    mod_names = []
    for k, c in secondaries:
        contr = _secondary_contribution(k, dt._tier_index(c))
        mods["attack_mult"] = mods.get("attack_mult", 1.0) + contr["attack_mult"]
        if contr["pierce"]:
            mods["pierce"] = min(0.9, mods.get("pierce", 0.0) + contr["pierce"])
        if contr["extra_strikes"]:
            mods["extra_strikes"] = mods.get("extra_strikes", 0) + contr["extra_strikes"]
        if contr["death_bonus"]:
            mods["death_bonus"] = min(0.7, mods.get("death_bonus", 0.0) + contr["death_bonus"])
        if contr["taken_mult"]:
            mods["taken_mult"] = max(0.3, mods.get("taken_mult", 1.0) - contr["taken_mult"])
        if k in _MODIFIERS:
            mod_names.append(_MODIFIERS[k])
    name = _main_name(main_key, main_idx)
    if mod_names:
        name = name + " " + " ".join(mod_names[:3]) + (" …" if len(mod_names) > 3 else "")
    fused_count = 1 + len(secondaries)
    spirit_cost = 18 + main_idx * 9 + 6 * len(secondaries)
    out.append({
        "key": f"dao_{main_key}", "name": name, "cooldown": 2,
        "spirit_cost": spirit_cost, "qi_cost": 0, "mods": mods,
        "desc": (f"tecnica FUSA di {fused_count} Dao (affatica lo Spirito)"
                 if fused_count > 1 else "tecnica del Dao (affatica lo Spirito)"),
        "source": "dao", "fuel": "spirit", "main": main_key,
        "mod": secondaries[0][0] if secondaries else None,
        "fused": [main_key] + [k for k, _ in secondaries],
        "grade": _GRADE[min(main_idx, 7)]})

    # ---- tecniche SINGOLE dei Dao secondari (varietà) ----
    for k, c in secondaries:
        idx = dt._tier_index(c)
        out.append({
            "key": f"dao_{k}", "name": _main_name(k, idx), "cooldown": 2,
            "spirit_cost": 18 + idx * 9, "qi_cost": 0,
            "mods": _profile_mods(k, idx, dt.dao_combat_bonus(c), 0.0),
            "desc": "tecnica del Dao (affatica lo Spirito)", "source": "dao",
            "fuel": "spirit", "main": k, "mod": None,
            "fused": [k], "grade": _GRADE[min(idx, 7)]})
    return out


def technique_list(conn: sqlite3.Connection, player_id: int = 1) -> list[str]:
    techs = dao_techniques(conn, player_id)
    lines = []
    for t in techs:
        fused = t.get("fused", [t["main"]])
        if len(fused) > 1:
            daos = " + ".join(_dao_label(k) for k in fused)
            lines.append(f"{t['name']} [FUSIONE: {daos}] — costa {t['spirit_cost']} Spirito")
        else:
            lines.append(f"{t['name']} [{_dao_label(t['main'])}] — costa {t['spirit_cost']} Spirito")
    return lines
