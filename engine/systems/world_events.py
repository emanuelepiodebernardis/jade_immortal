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

REINFORCE_INTERVAL = 8       # ogni quanti tick possono arrivare rinforzi se non respingi
REINFORCE_CAP = 9            # tetto di creature in campo contemporaneamente
LOCAL_DEFENSE_CHANCE = 0.35  # prob. per tick che i difensori locali abbattano un invasore
CHAMPION_FROM_THREAT = 4     # da questa minaccia in su l'ondata ha un CAMPIONE

KIND_LABEL = {"beast_tide": "Marea di Bestie", "demon_incursion": "Incursione Demoniaca",
              "spirit_incursion": "Marea Spettrale"}
_KIND_CREATURE = {"beast_tide": "beast", "demon_incursion": "demon",
                  "spirit_incursion": "spirit"}
_CHAMPION_NAME = {"beast_tide": "Bestia Alfa", "demon_incursion": "Generale Demoniaco",
                  "spirit_incursion": "Spettro Ancestrale"}


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
    retaliation = False
    # ESPANSIONE → RITORSIONE: più la tua setta conquista, più i nemici colpiscono i TUOI
    # territori. Con probabilità crescente l'invasione bersaglia una tua roccaforte.
    if player:
        from engine.systems import sect_invasion, sects
        nconq = sect_invasion.conquests(conn)
        m = sects.get_membership(conn, player.id)
        if m and nconq > 0 and rng.random() < min(0.75, 0.18 * nconq):
            mine = [r["id"] for r in conn.execute(
                "SELECT id FROM locations WHERE owner_faction_id=?;",
                (m["faction_id"],)).fetchall()]
            home = conn.execute("SELECT home_location_id FROM factions WHERE id=?;",
                                (m["faction_id"],)).fetchone()
            if home and home["home_location_id"]:
                mine.append(home["home_location_id"])
            mine = [x for x in mine if x in locs] or mine
            if mine:
                loc = rng.choice(mine)
                retaliation = True
    from engine.simulation import cultivation
    pr = cultivation.realm_tier(conn, "player", player.id) if player else 1
    threat = max(2, min(8, pr + rng.choice([-1, 0, 1])))
    kind = rng.choices(["beast_tide", "demon_incursion", "spirit_incursion"],
                       weights=[3, 2, 2])[0]
    wave = rng.randint(3, 5)
    cur = conn.execute(
        "INSERT INTO world_events (kind, location_id, threat, status, started_tick, "
        "deadline_tick, wave_total, wave_remaining, reinforce_tick) "
        "VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?);",
        (kind, loc, threat, tick, tick + DURATION, wave, wave, tick))
    eid = cur.lastrowid
    from engine.generators import creature_gen
    ck = _KIND_CREATURE[kind]
    for _ in range(wave):
        nid = creature_gen._spawn_one(conn, rng, ck, loc, max(1, threat - 1), min(8, threat + 1))
        conn.execute("UPDATE npcs SET event_id=? WHERE id=?;", (eid, nid))
    # le invasioni forti sono guidate da un CAMPIONE: più tosto, e va abbattuto per vincere
    champion_note = ""
    if threat >= CHAMPION_FROM_THREAT:
        cid = creature_gen._spawn_one(conn, rng, ck, loc, threat, min(9, threat + 2))
        cname = _CHAMPION_NAME[kind]
        conn.execute("UPDATE npcs SET event_id=?, name=? WHERE id=?;", (eid, cname, cid))
        conn.execute("UPDATE world_events SET champion_id=?, wave_total=wave_total+1, "
                     "wave_remaining=wave_remaining+1 WHERE id=?;", (cid, eid))
        champion_note = f" A guidarle c'è {cname}: abbattilo per spezzare l'ondata."
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
        prefix = ("⚔ RITORSIONE! La tua espansione provoca una controffensiva: "
                  if retaliation else "⚠ ")
        observations.append(
            f"{prefix}{KIND_LABEL[kind]} a {lname}! ({wave} creature, soglia {DURATION} tick).{champion_note} "
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
    champ_line = ""
    if ev["champion_id"] and npc_id == ev["champion_id"]:
        champ_line = "Hai abbattuto il campione dell'ondata! Le creature vacillano. "
    if rem > 0:
        return f"{champ_line}Invasore abbattuto: ne restano {rem}."
    return champ_line + _repel(conn, ev, tick, player)


def _repel(conn: sqlite3.Connection, ev: sqlite3.Row, tick: int, player) -> str:
    conn.execute("UPDATE world_events SET status='repelled', wave_remaining=0 WHERE id=?;",
                 (ev["id"],))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                         (ev["location_id"],)).fetchone()["name"]
    threat = ev["threat"] or 2
    waves = ev["wave_total"] or 4
    had_champion = bool(ev["champion_id"])
    fame = threat * 20 + waves * 3 + (threat * 10 if had_champion else 0)
    stones = threat * 50 + waves * 8 + (threat * 25 if had_champion else 0)
    from engine.systems import reputation, sects, items
    reputation.adjust(conn, player.id, fame=fame)
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    # i grandi assalti lasciano un bottino: un manuale o un tesoro per il difensore
    loot_line = ""
    if had_champion:
        iid = items.create_item(
            conn, f"Trofeo di {lname}", "tesoro", "prezioso",
            "Ricompensa per aver salvato un insediamento.",
            {"grow_strength": threat * 2, "grow_vitality": threat * 2, "stones": threat * 10})
        items.grant(conn, "player", player.id, iid, 1)
        loot_line = f" Ricevi un «Trofeo di {lname}» (nello zaino)."
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
            f"La gente ti acclama. Fama +{fame}, +{stones} pietre spirituali.{loot_line}")


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


def _alive_invaders(conn, eid, exclude_champion=None):
    q = "SELECT id FROM npcs WHERE event_id=? AND status='alive'"
    params = [eid]
    if exclude_champion:
        q += " AND id<>?"
        params.append(exclude_champion)
    return [r["id"] for r in conn.execute(q + ";", params).fetchall()]


def escalate(conn: sqlite3.Connection, tick: int, rng, observations) -> int:
    """Dà VITA all'invasione attiva: se tardi arrivano RINFORZI, e intanto i DIFENSORI
    locali combattono per conto loro (ma non riescono ad abbattere il campione)."""
    ev = active_event(conn)
    if not ev or ev["status"] != "active":
        return 0
    loc = ev["location_id"]
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    n = 0

    # 1) RINFORZI: a intervalli, se non hai ancora respinto, l'ondata si ingrossa
    if tick - (ev["reinforce_tick"] or ev["started_tick"]) >= REINFORCE_INTERVAL:
        alive = len(_alive_invaders(conn, ev["id"]))
        if alive and alive < REINFORCE_CAP:
            from engine.generators import creature_gen
            ck = _KIND_CREATURE[ev["kind"]]
            threat = ev["threat"] or 2
            add = rng.randint(1, 2)
            for _ in range(add):
                nid = creature_gen._spawn_one(conn, rng, ck, loc,
                                              max(1, threat - 1), min(8, threat + 1))
                conn.execute("UPDATE npcs SET event_id=? WHERE id=?;", (ev["id"], nid))
            conn.execute("UPDATE world_events SET wave_total=wave_total+?, "
                         "wave_remaining=wave_remaining+? WHERE id=?;", (add, add, ev["id"]))
            if observations is not None:
                msg = (f"⚠ Rinforzi! Un'altra creatura si unisce all'assalto su {lname}."
                       if add == 1 else
                       f"⚠ Rinforzi! Altre {add} creature si uniscono all'assalto su {lname}.")
                observations.append(msg)
            n += 1
        conn.execute("UPDATE world_events SET reinforce_tick=? WHERE id=?;", (tick, ev["id"]))

    # 2) DIFENSORI LOCALI: il mondo reagisce: gli abitanti abbattono qualche invasore
    #    (ma il CAMPIONE è troppo forte per loro: serve il giocatore)
    if rng.random() < LOCAL_DEFENSE_CHANCE:
        targets = _alive_invaders(conn, ev["id"], exclude_champion=ev["champion_id"])
        if targets:
            victim = rng.choice(targets)
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (tick, victim))
            rem = max(0, (ev["wave_remaining"] or 1) - 1)
            conn.execute("UPDATE world_events SET wave_remaining=? WHERE id=?;", (rem, ev["id"]))
            if observations is not None and rng.random() < 0.5:
                observations.append(
                    f"I difensori di {lname} resistono e abbattono un invasore "
                    f"(ne restano {rem}).")
            # se i locali ripuliscono tutto (senza campione), il luogo si salva da solo
            still = _alive_invaders(conn, ev["id"])
            if not still:
                conn.execute("UPDATE world_events SET status='repelled', wave_remaining=0 "
                             "WHERE id=?;", (ev["id"],))
                if observations is not None:
                    observations.append(
                        f"✓ Senza il tuo aiuto, i difensori di {lname} hanno respinto l'ondata. "
                        f"La gloria (e il bottino) va a loro.")
            n += 1
    return n


def tick(conn: sqlite3.Connection, tick_no: int, rng, player, observations) -> int:
    """Da chiamare nel world_tick: gestisce comparsa, escalation e risoluzione scadute."""
    events = resolve_overdue(conn, tick_no, rng, observations)
    events += escalate(conn, tick_no, rng, observations)
    if tick_no % SPAWN_INTERVAL == 0 and rng.random() < SPAWN_CHANCE:
        events += maybe_spawn(conn, tick_no, rng, player, observations)
    # più la tua setta si espande, più spesso sei sotto attacco (controffensive)
    elif player is not None:
        from engine.systems import sect_invasion
        nconq = sect_invasion.conquests(conn)
        if nconq > 0 and tick_no % (SPAWN_INTERVAL // 2) == 0 \
                and rng.random() < min(0.5, 0.12 * nconq):
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
    if ev["champion_id"]:
        champ = conn.execute("SELECT name, status FROM npcs WHERE id=?;",
                             (ev["champion_id"],)).fetchone()
        if champ and champ["status"] == "alive":
            lines.append(f"⚔ Campione in campo: {champ['name']} — abbattilo per spezzare l'ondata.")
        else:
            lines.append("Il campione dell'ondata è già caduto.")
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
