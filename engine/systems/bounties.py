"""
Taglie & criminali (avventure in città).

Alcuni NPC sono RICERCATI: tormentano la gente, depredano, praticano arti
demoniache. Hanno karma negativo (sono peccatori) e una taglia.

Cacciarli dà uno scopo concreto e ricompense. Il twist morale:
  - GIUSTIZIARE un ricercato è un atto giusto -> karma positivo (non negativo);
  - DIVORARLO resta corruttivo: erediti i suoi debiti karmici (i suoi peccati
    diventano tuoi). Quindi: esecutore giusto, oppure predatore di potere.
"""

from __future__ import annotations

import random
import sqlite3

CRIMES = [
    ("deprime le carovane sulle vie di montagna", 2),
    ("tormenta i contadini dei villaggi vicini", 2),
    ("ha ucciso un discepolo di setta a tradimento", 3),
    ("pratica arti demoniache divorando il qi altrui", 4),
    ("ha massacrato una famiglia di mortali", 4),
    ("razzia erbe spirituali e uccide chi protesta", 3),
]
MIN_OUTLAWS = 3


def seed_outlaws(conn: sqlite3.Connection, rng: random.Random, n: int = 5) -> None:
    from engine.systems import karma
    from engine.simulation import cultivation
    # candidati: NPC vivi che non guidano una fazione
    leaders = {r["leader_id"] for r in conn.execute("SELECT leader_id FROM factions;")}
    cands = [r["id"] for r in conn.execute(
        "SELECT id FROM npcs WHERE status='alive';") if r["id"] not in leaders]
    rng.shuffle(cands)
    for nid in cands[:n]:
        crime, sev = rng.choice(CRIMES)
        tier = cultivation.realm_tier(conn, "npc", nid)
        reward = 40 + tier * 20 + sev * 15
        conn.execute(
            "INSERT OR IGNORE INTO outlaws (npc_id, crime, reward, notoriety) "
            "VALUES (?, ?, ?, ?);", (nid, crime, reward, sev))
        # i ricercati portano un debito karmico (sono peccatori)
        karma.adjust_karma(conn, "npc", nid, -(30 + sev * 25), "crimini", 0)


def is_outlaw(conn: sqlite3.Connection, npc_id: int) -> bool:
    r = conn.execute(
        "SELECT 1 FROM outlaws WHERE npc_id=? AND resolved=0;", (npc_id,)).fetchone()
    return r is not None


def get_outlaw(conn: sqlite3.Connection, npc_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM outlaws WHERE npc_id=? AND resolved=0;", (npc_id,)).fetchone()


def active_bounties(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT o.npc_id, o.crime, o.reward, o.notoriety, n.name, l.name AS loc_name "
        "FROM outlaws o JOIN npcs n ON n.id=o.npc_id "
        "LEFT JOIN locations l ON l.id=n.location_id "
        "WHERE o.resolved=0 AND n.status='alive' ORDER BY o.reward DESC;"
    ).fetchall()


def claim(conn: sqlite3.Connection, tick: int, npc_id: int, player_id: int = 1) -> dict:
    """Riscuote la taglia se il ricercato è stato ucciso dal giocatore."""
    o = get_outlaw(conn, npc_id)
    if o is None:
        return {"status": "no_bounty"}
    conn.execute("UPDATE outlaws SET resolved=1 WHERE npc_id=?;", (npc_id,))
    from engine.systems import sects
    from engine.simulation import event_system as ev
    sects.grant_resource(conn, "pietre_spirituali", o["reward"], player_id)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    loc = conn.execute("SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()["location_id"]
    ev.log_event(
        conn, event_type="bounty_claimed", tick=tick, location_id=loc,
        title=f"Taglia riscossa: {name}",
        summary=f"Hai posto fine ai crimini di {name}. Taglia: {o['reward']} pietre spirituali.",
        participants=[ev.Participant("player", player_id, "initiator"),
                      ev.Participant("npc", npc_id, "target")],
        consequences=[ev.Consequence("player", player_id, "bounty_reward",
                                     f"+{o['reward']} pietre spirituali",
                                     visibility="public", resolve_tick=tick)],
    )
    return {"status": "claimed", "reward": o["reward"], "name": name}


def replenish(conn: sqlite3.Connection, rng: random.Random) -> None:
    """Mantiene sempre qualche ricercato in circolazione."""
    n = conn.execute(
        "SELECT COUNT(*) c FROM outlaws o JOIN npcs n ON n.id=o.npc_id "
        "WHERE o.resolved=0 AND n.status='alive';").fetchone()["c"]
    if n < MIN_OUTLAWS:
        seed_outlaws(conn, rng, MIN_OUTLAWS - n)


def outlaw_crime_tick(conn, tick, rng, player, scope, observer, observations) -> int:
    """Ogni tanto un ricercato nello scope commette un crimine (flavor + lo tiene saliente)."""
    if player is None or rng.random() > 0.04:
        return 0
    here = conn.execute(
        "SELECT o.npc_id, n.name FROM outlaws o JOIN npcs n ON n.id=o.npc_id "
        "WHERE o.resolved=0 AND n.status='alive' AND n.location_id=? LIMIT 1;",
        (player.location_id,)).fetchone()
    if not here:
        return 0
    crime = conn.execute("SELECT crime FROM outlaws WHERE npc_id=?;", (here["npc_id"],)).fetchone()["crime"]
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="crime", tick=tick, location_id=player.location_id,
        title=f"Crimine di {here['name']}",
        summary=f"{here['name']} {crime}: la gente trema.",
        participants=[ev.Participant("npc", here["npc_id"], "initiator")],
        consequences=[ev.Consequence("npc", here["npc_id"], "terror",
                                     "il terrore si diffonde", visibility="public",
                                     resolve_tick=tick)],
    )
    if observations is not None:
        observations.append(f"{here['name']} semina il terrore: {crime}.")
    return 1
