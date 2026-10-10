"""
Riga di stato compatta (HUD) mostrata dopo ogni comando.

Ispirata al pannello statistiche delle storie interattive: i pochi numeri che
contano sempre sotto gli occhi, senza dover digitare 'status'. Disattivabile con
'hud off'.
"""

from __future__ import annotations

import sqlite3

from engine.core import entities, tick
from engine.simulation import cultivation, combat
from engine.systems import state


def day_and_hour(t: int) -> tuple[int, int]:
    from engine.systems import training
    day = t // training.DAY_TICKS + 1
    hour = int((t % training.DAY_TICKS) / training.DAY_TICKS * 24)
    return day, hour


def hud_line(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import qi as qimod, spirit as spmod, sects, dao_techniques as dtk
    t = tick.get_tick(conn)
    day, hour = day_and_hour(t)
    rec = cultivation.get_record(conn, "player", player.id)
    prog = f" {rec['progress']*100:.0f}%" if rec else ""
    realm = cultivation.realm_label(conn, "player", player.id)
    parts = [f"Giorno {day}, ore {hour:02d}", f"{realm}{prog}",
             f"Qi {qimod.qi_label(conn, player.id).split(' ')[0]}"]
    if dtk.dao_techniques(conn, player.id):
        parts.append(f"Spirito {spmod.spirit_label(conn, player.id).split(' ')[0]}")
    wounds = combat.active_injuries(conn, "player", player.id)
    if wounds:
        worst = max(w["severity"] for w in wounds)
        parts.append(f"Ferite {len(wounds)} (gravità max {worst})")
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    if stones:
        parts.append(f"Pietre {stones}")
    from engine.systems import bonds
    comp = bonds.companion(conn, player.id)
    if comp:
        parts.append(f"Compagno: {comp['name']}")
    return "── " + " · ".join(parts) + " ──"


def enabled(conn: sqlite3.Connection) -> bool:
    return state.flag(conn, "ui_hud", True)
