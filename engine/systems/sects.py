"""
Sette (strato "agenzia del giocatore").

Una setta è una fazione con una sede. Il giocatore può recarsi alla sede e
iscriversi: un TEST D'INGRESSO misura il suo talento (riusando le affinità
nascoste già presenti nel profilo) e gli assegna un rango e delle risorse.

Niente garanzie di build dominante: il test riflette ciò che sei, e il rango
dà vantaggi (risorse, allenamento agevolato) ma non potere gratuito.
"""

from __future__ import annotations

import sqlite3

# soglie del talento -> grado di "radici spirituali" + rango + risorse
GRADES = [
    (85, "Radici Celesti", "Discepolo del Nucleo", 3, 300),
    (70, "Radici Superiori", "Discepolo Interno", 2, 150),
    (52, "Radici Comuni", "Discepolo Esterno", 1, 60),
    (0,  "Radici Torbide", "Servitore", 0, 20),
]


def joinable_sects(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fazioni con una sede: sette a cui ci si può iscrivere."""
    return conn.execute(
        "SELECT f.id, f.name, f.home_location_id, l.name AS hq_name "
        "FROM factions f JOIN locations l ON l.id=f.home_location_id "
        "WHERE f.status='active' ORDER BY f.influence DESC;"
    ).fetchall()


def sect_at_location(conn: sqlite3.Connection, location_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, home_location_id FROM factions "
        "WHERE home_location_id=? AND status='active' LIMIT 1;", (location_id,)
    ).fetchone()


def get_membership(conn: sqlite3.Connection, player_id: int = 1) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT m.player_id, m.faction_id, m.rank, m.rank_level, m.grade, "
        "m.class_tier, m.class_rank, f.name AS sect_name "
        "FROM sect_memberships m JOIN factions f ON f.id=m.faction_id "
        "WHERE m.player_id=?;", (player_id,)
    ).fetchone()


def _talent_score(conn: sqlite3.Connection, player_id: int) -> int:
    """Talento dal profilo (numeri nascosti): coltivazione + qi + anima + miglior Dao."""
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    if p is None:
        return 50
    best_dao = conn.execute(
        "SELECT MAX(affinity) m FROM character_daos "
        "WHERE character_type='player' AND character_id=?;", (player_id,)
    ).fetchone()
    bd = best_dao["m"] if best_dao and best_dao["m"] is not None else 50
    score = (p["aff_cultivation"] * 0.5 + p["aff_qi"] * 0.2
             + p["aff_soul"] * 0.15 + bd * 0.15)
    return int(round(score))


def _grade_for(score: int):
    for threshold, grade, rank, level, stones in GRADES:
        if score >= threshold:
            return grade, rank, level, stones
    return GRADES[-1][1:]


def get_resource(conn: sqlite3.Connection, resource: str, player_id: int = 1) -> int:
    row = conn.execute(
        "SELECT amount FROM player_resources WHERE player_id=? AND resource=?;",
        (player_id, resource)).fetchone()
    return row["amount"] if row else 0


def grant_resource(conn: sqlite3.Connection, resource: str, amount: int,
                   player_id: int = 1) -> int:
    cur = get_resource(conn, resource, player_id)
    new = max(0, cur + amount)
    conn.execute(
        "INSERT INTO player_resources (player_id, resource, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(player_id, resource) DO UPDATE SET amount=excluded.amount;",
        (player_id, resource, new))
    return new


def join_sect(conn: sqlite3.Connection, tick: int, player_id: int = 1) -> dict:
    """Iscrizione alla setta nella location corrente del giocatore (test d'ingresso)."""
    player = conn.execute(
        "SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()
    if get_membership(conn, player_id):
        m = get_membership(conn, player_id)
        return {"status": "already_member", "sect": m["sect_name"]}
    sect = sect_at_location(conn, player["location_id"])
    if sect is None:
        return {"status": "no_sect_here"}

    score = _talent_score(conn, player_id)
    grade, rank, level, stones = _grade_for(score)

    conn.execute(
        "INSERT INTO sect_memberships (player_id, faction_id, rank, rank_level, grade, joined_tick) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (player_id, sect["id"], rank, level, grade, tick))
    conn.execute("UPDATE players SET faction_id=? WHERE id=?;", (sect["id"], player_id))
    grant_resource(conn, "pietre_spirituali", stones, player_id)

    # la setta ora ti vede di buon occhio
    from engine.systems import relations
    from engine.simulation import event_system as ev
    # registra l'evento (vincolo 26)
    ev.log_event(
        conn, event_type="sect_join", tick=tick, location_id=player["location_id"],
        title=f"Ammissione a {sect['name']}",
        summary=f"Superi il test d'ingresso di {sect['name']} come {rank} ({grade}).",
        participants=[ev.Participant("player", player_id, "initiator")],
        consequences=[ev.Consequence("player", player_id, "sect_membership",
                                     f"{rank} di {sect['name']}", visibility="public",
                                     resolve_tick=tick)],
    )
    return {"status": "joined", "sect": sect["name"], "grade": grade,
            "rank": rank, "rank_level": level, "stones": stones}


def leave_sect(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    m = get_membership(conn, player_id)
    if not m:
        return {"status": "not_member"}
    conn.execute("DELETE FROM sect_memberships WHERE player_id=?;", (player_id,))
    conn.execute("UPDATE players SET faction_id=NULL WHERE id=?;", (player_id,))
    return {"status": "left", "sect": m["sect_name"]}
