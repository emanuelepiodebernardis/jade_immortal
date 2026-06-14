"""
Mosse attive in combattimento.

Oltre all'attacco normale, puoi scatenare MOSSE attive con effetti tattici diversi,
ognuna con un COOLDOWN (non spammabile: usarla è una scelta). Le fonti:

  - MOSSA FIRMA dell'arma scelta (spada, lancia, sciabola, arco, pugni, bastone):
    è ciò che rende ogni arma diversa in battaglia.
  - TECNICHE SEGRETE apprese dalla setta: diventano burst attivabili (più forti
    nelle sette alte).
  - MORSO DELL'ABISSO (solo Divoratore): se uccide, assorbe all'istante.

Effetti possibili (modificatori passati a resolve_combat):
  attack_mult, pierce, extra_strikes, taken_mult, death_bonus, devour_on_kill.

Uso: 'attack <bersaglio> <mossa>' oppure 'use <mossa> <bersaglio>'. 'moves' le elenca.
"""

from __future__ import annotations

import sqlite3

# mosse firma per Dao d'arma: (key, nome, cooldown, qi_cost, mods, desc)
_WEAPON_MOVES = {
    "spada":    ("fendente", "Fendente Mortale", 12, 32,
                 {"attack_mult": 1.5, "death_bonus": 0.28},
                 "un colpo che cerca la fine"),
    "lancia":   ("affondo", "Affondo Penetrante", 12, 30,
                 {"attack_mult": 1.3, "pierce": 0.6},
                 "trapassa le difese nemiche"),
    "sciabola": ("danza", "Danza delle Lame", 12, 28,
                 {"attack_mult": 1.2, "extra_strikes": 1},
                 "fendenti ampi e a raffica"),
    "arco":     ("tiro", "Tiro Preciso", 12, 38,
                 {"attack_mult": 1.8},
                 "un dardo letale che apre lo scontro"),
    "pugno":    ("pioggia", "Pioggia di Colpi", 12, 26,
                 {"attack_mult": 1.12, "extra_strikes": 2},
                 "una tempesta di colpi ravvicinati"),
    "bastone":  ("guardia", "Guardia del Bastone", 10, 22,
                 {"taken_mult": 0.4, "attack_mult": 1.1},
                 "difesa imperscrutabile: subisci molto meno"),
}

_ABYSS_MOVE = ("morso", "Morso dell'Abisso", 16, 45,
               {"attack_mult": 1.35, "death_bonus": 0.2, "devour_on_kill": True},
               "se uccide, divora all'istante i resti")

TECH_COOLDOWN = 20


def _state_key(player_id: int, move_key: str) -> str:
    return f"cd:{player_id}:{move_key}"


def _ready_tick(conn: sqlite3.Connection, player_id: int, move_key: str) -> int:
    r = conn.execute("SELECT value FROM game_state WHERE key=?;",
                     (_state_key(player_id, move_key),)).fetchone()
    return int(r["value"]) if r and r["value"] is not None else 0


def _set_cooldown(conn: sqlite3.Connection, player_id: int, move_key: str,
                  ready_tick: int) -> None:
    conn.execute(
        "INSERT INTO game_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value;",
        (_state_key(player_id, move_key), str(ready_tick)))


def available_moves(conn: sqlite3.Connection, player_id: int = 1) -> list[dict]:
    """Tutte le mosse che il giocatore possiede ora, con stato del cooldown."""
    out: list[dict] = []
    from engine.core import tick as tickmod
    now_tick = tickmod.get_tick(conn)

    from engine.systems import weapons, guild
    wkey = weapons.get_weapon(conn, player_id)
    if wkey and wkey in _WEAPON_MOVES:
        k, name, cd, qi_cost, mods, desc = _WEAPON_MOVES[wkey]
        out.append({"key": k, "name": name, "cooldown": cd, "qi_cost": qi_cost,
                    "spirit_cost": 0, "fuel": "qi",
                    "mods": mods, "desc": desc, "source": "arma"})

    # tecniche segrete apprese -> burst attivabili (forza e costo dalla magnitude)
    for t in guild.learned(conn, player_id):
        mag = t["magnitude"] or 0
        key = f"tec{t['tech_key'].replace(':', '_')}"
        out.append({"key": key, "name": t["name"], "cooldown": TECH_COOLDOWN,
                    "qi_cost": int(40 + mag * 200), "spirit_cost": 0, "fuel": "qi",
                    "mods": {"attack_mult": 1.0 + mag * 4, "death_bonus": 0.15},
                    "desc": "tecnica segreta scatenata", "source": "tecnica"})

    # Morso dell'Abisso (Divoratore)
    from engine.systems import absorption
    if absorption.can_absorb(conn, player_id):
        k, name, cd, qi_cost, mods, desc = _ABYSS_MOVE
        out.append({"key": k, "name": name, "cooldown": cd, "qi_cost": qi_cost,
                    "spirit_cost": 0, "fuel": "qi",
                    "mods": mods, "desc": desc, "source": "abisso"})

    # TECNICHE DAO (Guerriero Dao): nascono dai Dao e affaticano lo Spirito, non il Qi
    from engine.systems import dao_techniques
    out.extend(dao_techniques.dao_techniques(conn, player_id))

    from engine.systems import qi as qimod, spirit as spmod
    cur_qi = qimod.get_qi(conn, player_id)
    cur_sp = spmod.get_spirit(conn, player_id)
    for m in out:
        rt = _ready_tick(conn, player_id, m["key"])
        m["ready"] = now_tick >= rt
        m["ready_in"] = max(0, rt - now_tick)
        if m.get("fuel") == "spirit":
            m["affordable"] = cur_sp >= m["spirit_cost"]
        else:
            m["affordable"] = cur_qi >= m["qi_cost"]
    return out


def find_move(conn: sqlite3.Connection, token: str, player_id: int = 1) -> dict | None:
    token = (token or "").strip().lower()
    if not token:
        return None
    for m in available_moves(conn, player_id):
        if m["key"] == token or token in m["name"].lower():
            return m
    return None


def use_cost(conn: sqlite3.Connection, move: dict, tick: int, player_id: int = 1) -> None:
    """Mette la mossa in cooldown a partire da 'tick'."""
    _set_cooldown(conn, player_id, move["key"], tick + move["cooldown"])
