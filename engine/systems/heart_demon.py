"""
DEMONE INTERIORE (心魔) — la prova prima del breakthrough.

Quando tenti di salire di regno, a volte il tuo passato prende forma e ti sbarra la
strada: i volti di chi hai divorato, il peso del karma, il sangue versato, o anche solo
il tuo stesso dubbio. È una scena a scelta (motore degli incontri):

  - affrontarlo con l'anima  → se vinci, il breakthrough diventa più probabile;
  - accettarlo come parte di te → prova di karma, effetto più piccolo ma sicuro;
  - rimandare                → nessun tentativo, nessun rischio.

Se perdi lo scontro interiore il breakthrough parte svantaggiato e il demone si stacca
da te: diventa una NEMESI che ti darà la caccia nel mondo.
Appare al massimo una volta per regno.
"""

from __future__ import annotations

import random
import sqlite3

from engine.systems import state


def _face(conn, pid) -> tuple[str, int]:
    """Che forma prende il demone, e quanto è forte (difficoltà della prova)."""
    from engine.systems import character, karma
    prof = character.get_profile(conn, "player", pid)
    k = karma.get_karma(conn, "player", pid)
    devoured = (prof["abs_human"] or 0) if prof else 0
    kills = state.get_int(conn, "kills_human", 0)
    if devoured >= 5:
        return (f"Hanno i volti di chi hai divorato — {devoured} anime che ancora urlano dentro di te.",
                18 + min(25, devoured))
    if k <= -150:
        return ("È fatto del tuo debito karmico: ogni torto che hai commesso ha una voce.",
                15 + min(25, -k // 20))
    if kills >= 20:
        return (f"Ha il passo di un esercito: le {kills} vite che hai tolto camminano con lui.",
                12 + min(20, kills // 5))
    return ("Ha il tuo volto. Ti chiede, con la tua voce, se sei davvero degno di salire.", 5)


def should_trigger(conn: sqlite3.Connection, pid: int, tier: int, rng: random.Random) -> bool:
    if state.get_int(conn, "hd_seen_tier", 0) == tier:
        return False
    from engine.systems import destinies, karma
    p = 0.40
    if state.get_int(conn, "hd_seen_tier", 0) == tier - 1:
        p *= 0.5                       # appena affrontato al regno precedente: torna più di rado
    if karma.get_karma(conn, "player", pid) < -100:
        p += 0.25
    if destinies.flag_value(conn, "pure_heart", pid, False):
        p *= 0.5
    return rng.random() < p


def scene(conn: sqlite3.Connection, pid: int, tier: int) -> dict:
    face, diff = _face(conn, pid)
    state.set(conn, "hd_seen_tier", str(tier))
    from engine.systems import destinies
    if destinies.flag_value(conn, "pure_heart", pid, False):
        diff -= 15
    return {
        "key": "demone_interiore", "title": "Il Demone Interiore", "event_type": "story",
        "sticky": True,
        "text": ("Chiudi gli occhi per sfondare… e qualcosa ti aspetta dall'altra parte. "
                 + face),
        "choices": [
            {"label": "Lo affronti con tutta la tua anima",
             "check": {"stat": "anima", "dc": 70 + diff},
             "success": {"bt_bonus": 0.20, "aff_soul": 1,
                         "text": "Il demone si dissolve. La via davanti a te è sgombra.",
                         "command": "breakthrough !"},
             "failure": {"bt_bonus": -0.15, "inner_demon": True, "heart": -10,
                         "text": "Il demone ti travolge e si stacca da te, ridendo. Sfondi "
                                 "comunque, ma a fatica.",
                         "command": "breakthrough !"}},
            {"label": "Lo accetti come parte di te",
             "check": {"stat": "karma", "dc": 55 + diff // 2},
             "success": {"bt_bonus": 0.10, "text": "Il demone si placa: è tuo, e tu sei suo.",
                         "command": "breakthrough !"},
             "failure": {"bt_bonus": -0.05, "residue": 5,
                         "text": "Accettarlo ti sporca un poco. Ma vai avanti.",
                         "command": "breakthrough !"}},
            {"label": "Riapri gli occhi: non sei ancora pronto",
             "effects": {"text": "Rimandi. Il demone resta in attesa — al prossimo regno."}},
        ],
    }


def peek_bonus(conn: sqlite3.Connection) -> float:
    try:
        return float(state.get(conn, "bt_bonus") or 0.0)
    except ValueError:
        return 0.0


def take_bonus(conn: sqlite3.Connection) -> float:
    """Bonus/malus al breakthrough accumulato (demone, pillole). Si consuma."""
    raw = state.get(conn, "bt_bonus")
    if raw is None:
        return 0.0
    state.delete(conn, "bt_bonus")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def add_bonus(conn: sqlite3.Connection, v: float) -> None:
    cur = float(state.get(conn, "bt_bonus", "0") or 0)
    state.set(conn, "bt_bonus", str(round(cur + v, 3)))


def spawn_demon(conn: sqlite3.Connection, player, t: int) -> str | None:
    """Il demone sconfitto si stacca e diventa una nemesi."""
    from engine.systems import npc_factory, bonds
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, random.Random(t + 13), archetype="vagabondo", location_id=None,
                            tier=tier, stage=7, name=f"Demone del Cuore di {player.name}",
                            dao="oscurita", traits={"pride": 95, "ambition": 95, "compassion": 0})
    conn.execute("UPDATE npcs SET kind='demon', description=? WHERE id=?;",
                 ("Il tuo demone interiore, fatto carne.", nid))
    return bonds.add_bond(conn, player.id, nid, "nemesis", t, rng=random.Random(t),
                          reason="è nato dai tuoi rimorsi")
