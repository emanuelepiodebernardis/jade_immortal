"""
Karma System (Fase 10).

Peso morale PERSISTENTE e INVISIBILE (numero nascosto, display qualitativo).
Le azioni lo muovono; il karma a sua volta agisce sul mondo:
  - uccidere genera karma negativo (di più se uccidi i più deboli; meno per legittima difesa);
  - risparmiare un avversario dà un piccolo karma positivo;
  - assorbire genera karma negativo E fa EREDITARE parte del karma della vittima
    (i debiti dei caduti diventano tuoi — il "nemico karmico" del design);
  - karma molto negativo rende i breakthrough più letali (tribolazione karmica);
  - karma molto negativo attira sventura/cacciatori (effetti su NPC e world events).

Vale anche per gli NPC: i loro karma influenzano i loro breakthrough e l'eredità
che lasciano quando vengono assorbiti.
"""

from __future__ import annotations

import json
import random
import sqlite3

KARMA_CAP = 1000
HUNTED_THRESHOLD = -60       # sotto questo, la sventura inizia a cercarti


def get_karma(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    row = conn.execute(
        "SELECT karma_score FROM karma_records WHERE character_type=? AND character_id=?;",
        (ctype, cid),
    ).fetchone()
    return row["karma_score"] if row else 0


def adjust_karma(conn: sqlite3.Connection, ctype: str, cid: int, delta: int,
                 source: str, tick: int) -> int:
    if delta == 0:
        return get_karma(conn, ctype, cid)
    cur = get_karma(conn, ctype, cid)
    new = max(-KARMA_CAP, min(KARMA_CAP, cur + delta))
    row = conn.execute(
        "SELECT positive_sources, negative_sources FROM karma_records "
        "WHERE character_type=? AND character_id=?;", (ctype, cid)).fetchone()
    pos = json.loads(row["positive_sources"]) if row and row["positive_sources"] else []
    neg = json.loads(row["negative_sources"]) if row and row["negative_sources"] else []
    (pos if delta > 0 else neg).append(source)
    pos, neg = pos[-20:], neg[-20:]
    conn.execute(
        "INSERT INTO karma_records "
        "(character_type, character_id, karma_score, positive_sources, negative_sources, last_updated_tick) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(character_type, character_id) DO UPDATE SET "
        "karma_score=excluded.karma_score, positive_sources=excluded.positive_sources, "
        "negative_sources=excluded.negative_sources, last_updated_tick=excluded.last_updated_tick;",
        (ctype, cid, new, json.dumps(pos), json.dumps(neg), tick),
    )
    return new


# karma_records non ha UNIQUE nel vecchio schema: garantiamolo a runtime
def _ensure_unique(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_karma "
        "ON karma_records(character_type, character_id);")


def breakthrough_factor(score: int) -> float:
    """Moltiplicatore sulla probabilità di morte nel breakthrough (>=1)."""
    if score >= 0:
        return 1.0
    return 1.0 + min(0.8, -score / 300.0)


def karma_hint(score: int) -> str:
    """Indizio qualitativo (mai il numero). '' se il karma è quasi neutro."""
    if score <= -300:
        return "Un fiume di sangue ti segue: il cielo stesso ti ha segnato."
    if score <= -120:
        return "Un pesante debito karmico grava su di te."
    if score <= -40:
        return "Un debito karmico sottile sembra seguirti."
    if score >= 120:
        return "Un'aura di virtù ti accompagna."
    if score >= 40:
        return "Una traccia di buona sorte ti accompagna."
    return ""


# ---------- generatori di karma (chiamati dai sistemi) ----------

def on_kill(conn, tick, killer, victim) -> None:
    """killer/victim = (type, id, name). Uccidere genera karma negativo —
    ma GIUSTIZIARE un ricercato è un atto giusto (karma positivo)."""
    from engine.simulation import cultivation
    # giustizia: la vittima è un criminale ricercato?
    if victim[0] == "npc":
        from engine.systems import bounties
        ol = bounties.get_outlaw(conn, victim[1])
        if ol is not None:
            adjust_karma(conn, killer[0], killer[1], 2 + ol["notoriety"],
                         f"giustizia su {victim[2]}", tick)
            return
    ktier = cultivation.realm_tier(conn, killer[0], killer[1])
    vtier = cultivation.realm_tier(conn, victim[0], victim[1])
    # uccidere i più deboli pesa di più; affrontare i più forti pesa meno
    base = 6 + max(0, ktier - vtier) * 2
    # legittima difesa: se la vittima era ostile verso il killer, dimezza
    if _was_hostile(conn, victim, killer):
        base = base // 2
    adjust_karma(conn, killer[0], killer[1], -base, f"morte di {victim[2]}", tick)


def on_spare(conn, tick, winner) -> None:
    """Vincere senza uccidere (clemenza) dà un piccolo karma positivo."""
    adjust_karma(conn, winner[0], winner[1], 1, "clemenza", tick)


def on_absorb(conn, tick, player_id, target_id, target_name) -> int:
    """Assorbire: karma negativo per l'atto + eredità di parte del karma della vittima."""
    victim_karma = get_karma(conn, "npc", target_id)
    inherited = int(victim_karma * 0.3)        # erediti i debiti (e i meriti) dei caduti
    delta = -6 + inherited                      # l'atto in sé è negativo
    new = adjust_karma(conn, "player", player_id, delta, f"assorbimento di {target_name}", tick)
    return new


# ---------- effetti sul mondo ----------

def karmic_pressure(conn, tick, rng, player, scope, observer, observations) -> int:
    """Karma molto negativo: la sventura ti cerca. Un presente può voltarti contro."""
    if player is None:
        return 0
    score = get_karma(conn, "player", player.id)
    if score > HUNTED_THRESHOLD:
        return 0
    # probabilità crescente col debito
    p = min(0.15, (-score - (-HUNTED_THRESHOLD)) / 2000.0 + 0.01)
    if rng.random() >= p:
        return 0
    from engine.systems import relations
    from engine.core import entities
    candidates = [n for n in entities.npcs_in_location(conn, player.location_id)
                  if relations.get_disposition(conn, n.id).score > -40]
    if not candidates:
        return 0
    target = rng.choice(candidates)
    relations.adjust(conn, target.id, -50, tick, player.id)
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="karmic_pressure", tick=tick, location_id=player.location_id,
        title=f"{target.name} percepisce il tuo karma",
        summary=f"{target.name} fiuta il sangue che ti segue e ti guarda con ostilità.",
        participants=[ev.Participant("npc", target.id, "initiator"),
                      ev.Participant("player", player.id, "target")],
        consequences=[ev.Consequence("player", player.id, "karmic_hostility",
                                     "un nemico in più per il tuo debito",
                                     visibility="public", resolve_tick=tick)],
    )
    if observations is not None:
        observations.append(f"{target.name} ti scruta con improvvisa ostilità.")
    return 1


def _was_hostile(conn, victim, aggressor) -> bool:
    """True se la vittima era ostile verso l'uccisore (legittima difesa)."""
    from engine.systems import relations
    if aggressor[0] == "player":
        return relations.get_disposition(conn, victim[1], aggressor[1]).score <= -20
    if victim[0] == "npc" and aggressor[0] == "npc":
        return relations.get_npc_relation(conn, victim[1], aggressor[1]) <= -20
    return False
