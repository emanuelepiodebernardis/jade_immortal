"""
Eventi mondiali — invasioni.

Ogni tanto una MAREA DI BESTIE o un'INCURSIONE DEMONIACA colpisce un insediamento.
Il giocatore può:
  - DIFENDERE: raggiungere il luogo e abbattere l'ondata ('defend' / 'attack').
    Ogni mostro ucciso dà merito (se in setta) e si può ASSORBIRE; respingere
    l'ondata dà fama e ricompense.
  - IGNORARE: alla scadenza il luogo subisce conseguenze — alcuni abitanti periscono,
    l'influenza della fazione locale cala, il pericolo cresce. I caduti restano come
    resti a terra (assorbibili).

Una sola invasione attiva alla volta, per chiarezza.
"""

from __future__ import annotations

import sqlite3

SPAWN_INTERVAL = 48          # finestra per una possibile nuova invasione (~2 giorni)
SPAWN_CHANCE = 0.5
DURATION = 36                # tick a disposizione per difendere prima della scadenza

KIND_LABEL = {"beast_tide": "Marea di Bestie", "demon_incursion": "Incursione Demoniaca"}
_KIND_CREATURE = {"beast_tide": "beast", "demon_incursion": "demon"}


def active_event(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM world_events WHERE status='active' ORDER BY id DESC LIMIT 1;").fetchone()


def _populated_locations(conn: sqlite3.Connection) -> list[int]:
    return [r["location_id"] for r in conn.execute(
        "SELECT location_id, COUNT(*) c FROM npcs WHERE status='alive' AND kind='human' "
        "AND location_id IS NOT NULL GROUP BY location_id HAVING c>=2;")]


def maybe_spawn(conn: sqlite3.Connection, tick: int, rng, player, observations) -> int:
    """Fa nascere una nuova invasione (se non ce n'è già una). Ritorna 1 se creata."""
    if active_event(conn):
        return 0
    locs = _populated_locations(conn)
    if not locs:
        return 0
    loc = rng.choice(locs)
    from engine.simulation import cultivation
    pr = cultivation.realm_tier(conn, "player", player.id) if player else 1
    threat = max(2, min(8, pr + rng.choice([-1, 0, 1])))
    kind = rng.choices(["beast_tide", "demon_incursion"], weights=[3, 2])[0]
    wave = rng.randint(3, 5)
    cur = conn.execute(
        "INSERT INTO world_events (kind, location_id, threat, status, started_tick, "
        "deadline_tick, wave_total, wave_remaining) VALUES (?, ?, ?, 'active', ?, ?, ?, ?);",
        (kind, loc, threat, tick, tick + DURATION, wave, wave))
    eid = cur.lastrowid
    from engine.generators import creature_gen
    ck = _KIND_CREATURE[kind]
    for _ in range(wave):
        nid = creature_gen._spawn_one(conn, rng, ck, loc, max(1, threat - 1), min(8, threat + 1))
        conn.execute("UPDATE npcs SET event_id=? WHERE id=?;", (eid, nid))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="world_event", tick=tick, location_id=loc,
        title=f"{KIND_LABEL[kind]} a {lname}",
        summary=f"Una {KIND_LABEL[kind].lower()} si abbatte su {lname}.",
        participants=[ev.Participant("location", loc, "target")],
        consequences=[ev.Consequence("location", loc, "under_attack",
                                     f"{lname} è sotto attacco", visibility="public",
                                     resolve_tick=tick)])
    if observations is not None:
        observations.append(
            f"⚠ {KIND_LABEL[kind]} a {lname}! ({wave} creature, soglia {DURATION} tick). "
            f"Usa 'events' per i dettagli; raggiungi il luogo e 'defend' per difenderlo.")
    return 1


def on_creature_killed(conn: sqlite3.Connection, npc_id: int, tick: int, player) -> str | None:
    """Da chiamare quando il player uccide una creatura: se è un invasore dell'evento
    attivo, fa avanzare la difesa; respinta l'ondata, assegna le ricompense."""
    ev = active_event(conn)
    if not ev:
        return None
    row = conn.execute("SELECT event_id FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not row or row["event_id"] != ev["id"]:
        return None
    rem = max(0, (ev["wave_remaining"] or 0) - 1)
    conn.execute("UPDATE world_events SET wave_remaining=? WHERE id=?;", (rem, ev["id"]))
    if rem > 0:
        return f"Invasore abbattuto: ne restano {rem}."
    return _repel(conn, ev, tick, player)


def _repel(conn: sqlite3.Connection, ev: sqlite3.Row, tick: int, player) -> str:
    conn.execute("UPDATE world_events SET status='repelled', wave_remaining=0 WHERE id=?;",
                 (ev["id"],))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                         (ev["location_id"],)).fetchone()["name"]
    threat = ev["threat"] or 2
    fame = threat * 20
    stones = threat * 50
    from engine.systems import reputation, sects
    reputation.adjust(conn, player.id, fame=fame)
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    from engine.simulation import event_system as ev2
    ev2.log_event(
        conn, event_type="world_event_repelled", tick=tick, location_id=ev["location_id"],
        title=f"{lname} difesa",
        summary=f"L'ondata su {lname} è stata respinta.",
        participants=[ev2.Participant("player", player.id, "initiator"),
                      ev2.Participant("location", ev["location_id"], "target")],
        consequences=[ev2.Consequence("player", player.id, "hero",
                                      f"Difensore di {lname}", visibility="public",
                                      resolve_tick=tick)])
    return (f"★ Hai respinto la {KIND_LABEL[ev['kind']].lower()} su {lname}! "
            f"La gente ti acclama. Fama +{fame}, +{stones} pietre spirituali.")


def resolve_overdue(conn: sqlite3.Connection, tick: int, rng, observations) -> int:
    """Se l'invasione attiva ha superato la scadenza senza essere respinta: il luogo
    paga il prezzo (morti, calo d'influenza, pericolo in aumento)."""
    ev = active_event(conn)
    if not ev or tick < (ev["deadline_tick"] or 0):
        return 0
    loc = ev["location_id"]
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    # alcuni abitanti periscono (i più deboli, non i leader): restano come resti
    leaders = {r["leader_id"] for r in conn.execute(
        "SELECT leader_id FROM factions WHERE leader_id IS NOT NULL;")}
    victims = [r["id"] for r in conn.execute(
        "SELECT n.id FROM npcs n LEFT JOIN cultivation_records cr "
        "ON cr.character_type='npc' AND cr.character_id=n.id "
        "LEFT JOIN cultivation_realms re ON re.id=cr.realm_id "
        "WHERE n.location_id=? AND n.status='alive' AND n.kind='human' "
        "ORDER BY COALESCE(re.tier,1) ASC, n.id ASC;", (loc,)).fetchall()
        if r["id"] not in leaders]
    n_dead = min(len(victims), max(1, (ev["wave_remaining"] or 1)))
    dead = victims[:n_dead]
    for vid in dead:
        conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (tick, vid))
    # influenza/ricchezza della fazione che controlla il luogo
    owner = conn.execute(
        "SELECT id FROM factions WHERE home_location_id=? AND status='active' LIMIT 1;",
        (loc,)).fetchone()
    if owner:
        conn.execute("UPDATE factions SET influence=MAX(0, influence-10), "
                     "wealth=MAX(0, wealth-8) WHERE id=?;", (owner["id"],))
    # il luogo diventa più pericoloso
    conn.execute("UPDATE locations SET danger_level=MIN(6, danger_level+1) WHERE id=?;", (loc,))
    # gli invasori superstiti si disperdono nelle terre selvagge (restano cacciabili)
    conn.execute("UPDATE npcs SET event_id=NULL WHERE event_id=?;", (ev["id"],))
    conn.execute("UPDATE world_events SET status='lost', wave_remaining=0 WHERE id=?;", (ev["id"],))
    from engine.simulation import event_system as ev2
    ev2.log_event(
        conn, event_type="world_event_lost", tick=tick, location_id=loc,
        title=f"{lname} devastata",
        summary=f"La {KIND_LABEL[ev['kind']].lower()} su {lname} non è stata respinta.",
        participants=[ev2.Participant("location", loc, "target")],
        consequences=[ev2.Consequence("location", loc, "devastation",
                                      f"{n_dead} abitanti periti a {lname}",
                                      visibility="public", resolve_tick=tick)])
    if observations is not None:
        observations.append(
            f"✖ La {KIND_LABEL[ev['kind']].lower()} su {lname} non è stata respinta: "
            f"{n_dead} abitanti sono periti e il luogo è più pericoloso.")
    return 1


def tick(conn: sqlite3.Connection, tick_no: int, rng, player, observations) -> int:
    """Da chiamare nel world_tick: gestisce comparsa (a cadenza) e risoluzione scadute."""
    events = resolve_overdue(conn, tick_no, rng, observations)
    if tick_no % SPAWN_INTERVAL == 0 and rng.random() < SPAWN_CHANCE:
        events += maybe_spawn(conn, tick_no, rng, player, observations)
    return events


def describe(conn: sqlite3.Connection, ev: sqlite3.Row, player_loc: int,
            step_fn) -> str:
    lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                         (ev["location_id"],)).fetchone()["name"]
    remaining = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE event_id=? AND status='alive';",
        (ev["id"],)).fetchone()["c"]
    lines = [f"{KIND_LABEL[ev['kind']]} a {lname} — minaccia di livello {ev['threat']}.",
             f"Creature ancora in campo: {remaining}."]
    from engine.core import tick as tickmod
    now = tickmod.get_tick(conn)
    left = (ev["deadline_tick"] or 0) - now
    lines.append(f"Tempo per difendere: ~{max(0, left)} tick." if left > 0
                 else "Il tempo sta per scadere!")
    if ev["location_id"] == player_loc:
        lines.append("Sei sul posto: usa 'defend' (o 'attack <nome>') per abbatterle.")
    else:
        step = step_fn(conn, player_loc, ev["location_id"])
        if step:
            lines.append(f"Muoviti verso '{step}' per raggiungere il luogo e difenderlo.")
    return "\n".join(lines)
