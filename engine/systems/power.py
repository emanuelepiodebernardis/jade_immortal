"""
Potenza Effettiva Totale e CLASSI di combattimento.

Personaggi molto diversi (un coltivatore del Qi, un guerriero Dao, un cultivatore del
Corpo, un maestro dell'Anima) possono avere forza COMPLESSIVA simile pur distribuita in
modo diverso. Per confrontarli — e per popolare le zone con archetipi vari ma equilibrati
— il motore calcola:

  - un PROFILO a 4 assi: Qi, Corpo, Anima, Dao;
  - un RATING (potenza effettiva) scalare, derivato dalle statistiche reali di combattimento;
  - una CLASSE, dall'asse dominante del profilo.

In più, un piccolo vantaggio di STILE (morra cinese): Dao>Qi>Corpo>Anima>Dao.
"""

from __future__ import annotations

import sqlite3

CLASS_LABEL = {
    "qi": "Coltivatore del Qi",
    "corpo": "Cultivatore del Corpo",
    "anima": "Maestro dell'Anima",
    "dao": "Guerriero Dao",
    "equilibrato": "Coltivatore Equilibrato",
}

# morra cinese: la chiave BATTE il valore (piccolo vantaggio di stile)
_BEATS = {"dao": "qi", "qi": "corpo", "corpo": "anima", "anima": "dao"}


def power_profile(conn: sqlite3.Connection, ctype: str, cid: int) -> dict:
    """I quattro assi di potenza del personaggio."""
    from engine.simulation import cultivation
    from engine.systems import dao_training as dt
    rec = cultivation.get_record(conn, ctype, cid)
    tier = cultivation.realm_tier(conn, ctype, cid) or 1
    stage = (rec["stage"] if rec and rec["stage"] else 1)
    qi_lv = (rec["qi_level"] if rec else 0) or 0
    body_lv = (rec["body_level"] if rec else 0) or 0
    soul_lv = (rec["soul_level"] if rec else 0) or 0

    daos = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type=? AND character_id=?;", (ctype, cid)).fetchall()
    # asse DAO = Dao d'arma/intento (spada, lancia, ..., fulmine, tempo, spazio, destino);
    # il Dao del CORPO nutre l'asse Corpo, il Dao dell'ANIMA l'asse Anima.
    dao_axis_keys = {"spada", "lancia", "sciabola", "arco", "pugno", "bastone",
                     "fulmine", "tempo", "spazio", "destino"}
    dao_power = sum((d["comprehension"] or 0) for d in daos if d["dao_key"] in dao_axis_keys)
    corpo_dao = sum((d["comprehension"] or 0) for d in daos if d["dao_key"] == "corpo")
    anima_dao = sum((d["comprehension"] or 0) for d in daos if d["dao_key"] == "anima")

    qi = tier * 40 + stage * 6 + qi_lv
    corpo = body_lv + tier * 10 + corpo_dao
    anima = soul_lv + anima_dao + tier * 6
    dao = dao_power

    if ctype == "player":
        from engine.systems import character
        p = character.get_profile(conn, "player", cid)
        if p is not None:
            corpo += (p["grow_strength"] or 0) + (p["grow_vitality"] or 0) + (p["grow_resistance"] or 0)
            anima += (p["grow_soul"] or 0)
    return {"qi": float(qi), "corpo": float(corpo), "anima": float(anima), "dao": float(dao)}


def combat_rating(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    """Potenza effettiva scalare, dalle statistiche REALI di combattimento (chi vince)."""
    from engine.simulation import combat
    cp = combat.combat_power(conn, ctype, cid)
    return int(cp["attack"] * 0.5 + cp["defense"] * 0.3 + cp["vitality"] * 0.2
               + cp.get("spirit", 0) * 0.1)


def classify(conn: sqlite3.Connection, ctype: str, cid: int) -> tuple[str, str]:
    """(chiave_classe, etichetta) dall'asse dominante. Senza dominanza chiara: equilibrato."""
    pr = power_profile(conn, ctype, cid)
    total = sum(pr.values()) or 1.0
    key = max(pr, key=pr.get)
    if pr[key] / total < 0.40:
        return ("equilibrato", CLASS_LABEL["equilibrato"])
    return (key, CLASS_LABEL[key])


def class_of(conn: sqlite3.Connection, ctype: str, cid: int) -> str:
    return classify(conn, ctype, cid)[0]


def matchup_bonus(attacker_class: str, defender_class: str) -> float:
    """Vantaggio/svantaggio di stile (piccolo): +0.12 se batti, -0.10 se sei battuto."""
    if _BEATS.get(attacker_class) == defender_class:
        return 0.12
    if _BEATS.get(defender_class) == attacker_class:
        return -0.10
    return 0.0


def matchup_note(attacker_class: str, defender_class: str) -> str | None:
    b = matchup_bonus(attacker_class, defender_class)
    if b > 0:
        return f"Il tuo stile ({CLASS_LABEL.get(attacker_class,'?')}) sovrasta il suo: vantaggio."
    if b < 0:
        return f"Il suo stile ({CLASS_LABEL.get(defender_class,'?')}) contrasta il tuo: svantaggio."
    return None
