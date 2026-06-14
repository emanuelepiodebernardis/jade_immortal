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
}

# Frase modificatrice quando un Dao è SECONDARIO.
_MODIFIERS = {
    "fulmine": "del Tuono", "spada": "Tagliente", "sciabola": "Lacerante",
    "lancia": "Trafiggente", "arco": "Fulmineo", "pugno": "Frantumante",
    "bastone": "Inarrestabile", "corpo": "Corporeo", "tempo": "Istantaneo",
    "spazio": "Senza Distanza", "destino": "Ineluttabile", "anima": "Spirituale",
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
    if idx >= 5 and "extra_strikes" not in mods:
        mods["extra_strikes"] = 1
    return mods


def dao_techniques(conn: sqlite3.Connection, player_id: int = 1) -> list[dict]:
    """Tecniche Dao attualmente possedute dal giocatore (>= soglia 10 in un Dao).
    Una tecnica-firma per Dao, che evolve di nome e potenza; il Dao secondario la modifica."""
    rows = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type='player' AND character_id=? AND comprehension>=10 "
        "ORDER BY comprehension DESC;", (player_id,)).fetchall()
    if not rows:
        return []
    out: list[dict] = []
    for r in rows:
        main = r["dao_key"]
        comp = r["comprehension"] or 0
        idx = dt._tier_index(comp)            # 1..7 (>=10)
        # Dao secondario = il più alto OltreA questo, con una frase modificatrice
        sec = next((s for s in rows if s["dao_key"] != main
                    and s["dao_key"] in _MODIFIERS and (s["comprehension"] or 0) >= 10), None)
        sec_key = sec["dao_key"] if sec else None
        sec_comp = (sec["comprehension"] or 0) if sec else 0
        name = _main_name(main, idx)
        if sec_key:
            name = f"{name} {_MODIFIERS[sec_key]}"
        mods = _profile_mods(main, idx, dt.dao_combat_bonus(comp), dt.dao_combat_bonus(sec_comp))
        spirit_cost = 18 + idx * 9 + (8 if sec_key else 0)
        out.append({
            "key": f"dao_{main}", "name": name, "cooldown": 2,
            "spirit_cost": spirit_cost, "qi_cost": 0, "mods": mods,
            "desc": "tecnica del Dao (affatica lo Spirito)", "source": "dao",
            "fuel": "spirit", "main": main, "mod": sec_key,
            "grade": _GRADE[min(idx, 7)]})
    return out


def technique_list(conn: sqlite3.Connection, player_id: int = 1) -> list[str]:
    techs = dao_techniques(conn, player_id)
    lines = []
    for t in techs:
        mod = f" + {_dao_label(t['mod'])}" if t["mod"] else ""
        lines.append(f"{t['name']} [{_dao_label(t['main'])}{mod}] "
                     f"— costa {t['spirit_cost']} Spirito")
    return lines
