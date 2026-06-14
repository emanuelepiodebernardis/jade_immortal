"""
Guerre tra sette.

Ogni tanto una setta rivale dichiara guerra alla TUA. Si apre un FRONTE (un luogo) dove
si affrontano i discepoli. Puoi raggiungerlo e, per ogni nemico che sconfiggi, scegliere:

  - UCCIDI ('attack')  → merito di setta, poca infamia (è guerra, è sanzionato);
  - RISPARMIA ('spare') → onore e reputazione (e forse un alleato futuro);
  - ASSORBI ('absorb')  → Dao/talento del nemico, ma infamia e sospetto.

Sul campo cadono anche i TUOI compagni: i loro resti restano a terra. Divorarli dà
potere, ma è un tradimento — la setta inizia a sospettare di te (infamia e sospetto enormi).

Alla scadenza la guerra si risolve: il tuo contributo, sommato alla forza della setta,
decide chi vince. Vincere dà merito, reputazione e influenza; ignorare la guerra indebolisce
la tua setta.
"""

from __future__ import annotations

import random
import sqlite3

DECLARE_INTERVAL = 60
DECLARE_CHANCE = 0.5
DURATION = 48


def active_war(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sect_wars WHERE status='active' ORDER BY id DESC LIMIT 1;").fetchone()


def _combatants(conn, war_id, faction_id):
    return conn.execute(
        "SELECT id, name, location_id FROM npcs WHERE war_id=? AND faction_id=? "
        "AND status='alive' ORDER BY id;", (war_id, faction_id)).fetchall()


def enemy_disciples(conn, war):
    return _combatants(conn, war["id"], war["enemy_faction_id"])


def ally_disciples(conn, war):
    return _combatants(conn, war["id"], war["player_faction_id"])


def _spawn_disciple(conn, tick, rng, faction_id, loc, tier, kind_word):
    from engine.generators import npc_gen, dao_gen
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    realm_id = by_tier.get(max(1, min(8, tier)), by_tier.get(1))
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    name = npc_gen._unique_name(rng, used)
    cur = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, kind, "
        "faction_id, realm_id, last_active_tick) "
        "VALUES (?, ?, 'alive', ?, 'discepolo', 'human', ?, ?, ?);",
        (name, loc, f"Un discepolo {kind_word}.", faction_id, realm_id, tick))
    nid = cur.lastrowid
    stage = rng.randint(3, 8)
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, 0.3, ?, ?, ?, ?, ?);",
        (nid, realm_id, stage, tier * 8 + stage, tier * 7 + stage, tier * 7, tier * 5))
    dao_gen._set_dao(conn, "npc", nid, "spada", 55, tier * 8 + stage, 1)
    return nid


def maybe_declare(conn, tick, rng, player, observations) -> int:
    if active_war(conn):
        return 0
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if m is None:
        return 0
    pfac = m["faction_id"]
    rivals = conn.execute(
        "SELECT id, name, tier, home_location_id FROM factions "
        "WHERE id<>? AND status='active' AND leader_id IS NOT NULL ORDER BY tier DESC;",
        (pfac,)).fetchall()
    if not rivals:
        return 0
    enemy = rng.choice(rivals[: max(1, len(rivals) // 2 + 1)])
    pfac_row = conn.execute("SELECT name, home_location_id, tier FROM factions WHERE id=?;",
                            (pfac,)).fetchone()
    front = pfac_row["home_location_id"]
    if front is None:
        return 0
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    dtier = max(2, min(8, max(ptier, enemy["tier"] or 2)))
    n_enemy = rng.randint(4, 6)
    n_ally = rng.randint(2, 3)
    cur = conn.execute(
        "INSERT INTO sect_wars (player_faction_id, enemy_faction_id, battle_location_id, "
        "status, started_tick, deadline_tick, wave_total) VALUES (?, ?, ?, 'active', ?, ?, ?);",
        (pfac, enemy["id"], front, tick, tick + DURATION, n_enemy))
    war_id = cur.lastrowid
    for _ in range(n_enemy):
        nid = _spawn_disciple(conn, tick, rng, enemy["id"], front, dtier, f"di {enemy['name']}")
        conn.execute("UPDATE npcs SET war_id=? WHERE id=?;", (war_id, nid))
    for _ in range(n_ally):
        nid = _spawn_disciple(conn, tick, rng, pfac, front, dtier, f"di {pfac_row['name']}")
        conn.execute("UPDATE npcs SET war_id=? WHERE id=?;", (war_id, nid))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (front,)).fetchone()["name"]
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="sect_war_declared", tick=tick, location_id=front,
        title=f"{enemy['name']} dichiara guerra a {pfac_row['name']}",
        summary=f"Scoppia la guerra tra {pfac_row['name']} e {enemy['name']} a {lname}.",
        participants=[ev.Participant("faction", enemy["id"], "attacker"),
                      ev.Participant("faction", pfac, "defender")],
        consequences=[ev.Consequence("location", front, "battlefield",
                                     f"{lname} è un campo di battaglia", visibility="public",
                                     resolve_tick=tick)])
    if observations is not None:
        observations.append(
            f"⚔ GUERRA TRA SETTE: {enemy['name']} attacca la tua setta {pfac_row['name']} "
            f"a {lname}! Raggiungi il fronte e usa 'war' per i dettagli "
            f"(combatti, 'spare' o 'absorb' i nemici).")
    return 1


def on_enemy_defeated(conn, tick, player, npc_id, mode) -> str | None:
    """mode: 'kill' | 'spare' | 'absorb'. Avanza la guerra e applica le conseguenze."""
    war = active_war(conn)
    if not war:
        return None
    row = conn.execute("SELECT war_id, faction_id, name FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not row or row["war_id"] != war["id"]:
        return None
    is_enemy = row["faction_id"] == war["enemy_faction_id"]
    is_ally = row["faction_id"] == war["player_faction_id"]
    from engine.systems import reputation, guild, karma
    if is_enemy:
        conn.execute("UPDATE sect_wars SET score_player=score_player+1 WHERE id=?;", (war["id"],))
        if mode == "kill":
            guild.add_merit(conn, 12, player.id)
            reputation.adjust(conn, player.id, infamy=4)
            return "Un nemico cade in battaglia: +12 merito di setta."
        if mode == "spare":
            conn.execute("UPDATE npcs SET war_id=NULL WHERE id=?;", (npc_id,))
            reputation.adjust(conn, player.id, fame=10)
            karma.adjust_karma(conn, "player", player.id, 6,
                               "ha risparmiato un nemico in guerra", tick)
            return "Risparmi il nemico sconfitto: la tua magnanimità è notata (+fama)."
        if mode == "absorb":
            reputation.adjust(conn, player.id, infamy=10)
            return "Divori un nemico caduto in guerra: ne carpisci il Dao, ma l'infamia cresce."
    elif is_ally:
        # divorare un compagno è tradimento: la setta lo nota (gestito anche in cmd_absorb)
        conn.execute("UPDATE sect_wars SET score_enemy=score_enemy+1 WHERE id=?;", (war["id"],))
        return "Hai divorato un compagno caduto: la tua setta inizia a sospettare di te."
    return None


def _background_skirmish(conn, tick, rng, war, observations) -> None:
    """Mentre la guerra infuria, ogni tanto cade un combattente da una parte o dall'altra."""
    if rng.random() < 0.5:
        allies = ally_disciples(conn, war)
        if allies and rng.random() < 0.5:
            victim = rng.choice(allies)
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;",
                         (tick, victim["id"]))
            conn.execute("UPDATE sect_wars SET score_enemy=score_enemy+1 WHERE id=?;", (war["id"],))
            if observations is not None:
                observations.append(f"Al fronte cade {victim['name']}, uno dei tuoi: "
                                    f"i suoi resti giacciono sul campo.")
        enemies = enemy_disciples(conn, war)
        if enemies and rng.random() < 0.35:
            victim = rng.choice(enemies)
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;",
                         (tick, victim["id"]))
            conn.execute("UPDATE sect_wars SET score_enemy=score_enemy+1 WHERE id=?;", (war["id"],))


def resolve(conn, tick, rng, player, observations) -> int:
    war = active_war(conn)
    if not war:
        return 0
    enemies_left = len(enemy_disciples(conn, war))
    if tick < (war["deadline_tick"] or 0) and enemies_left > 0:
        return 0
    from engine.systems import sects, guild, reputation
    pfac = war["player_faction_id"]
    pinf = conn.execute("SELECT influence FROM factions WHERE id=?;", (pfac,)).fetchone()
    einf = conn.execute("SELECT influence FROM factions WHERE id=?;",
                        (war["enemy_faction_id"],)).fetchone()
    p_strength = (pinf["influence"] if pinf else 30) + (war["score_player"] or 0) * 12
    e_strength = (einf["influence"] if einf else 30) + (war["score_enemy"] or 0) * 10 + enemies_left * 8
    won = p_strength >= e_strength
    lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                         (war["battle_location_id"],)).fetchone()["name"]
    if won:
        conn.execute("UPDATE sect_wars SET status='won' WHERE id=?;", (war["id"],))
        conn.execute("UPDATE factions SET influence=influence+12 WHERE id=?;", (pfac,))
        conn.execute("UPDATE factions SET influence=MAX(0, influence-10) WHERE id=?;",
                     (war["enemy_faction_id"],))
        if (war["score_player"] or 0) > 0:
            guild.add_merit(conn, 25 + (war["score_player"] or 0) * 5, player.id)
            reputation.adjust(conn, player.id, fame=20)
            sects.grant_resource(conn, "pietre_spirituali", 80, player.id)
            msg = (f"VITTORIA a {lname}! La tua setta respinge i rivali. "
                   f"Merito, fama e pietre per il tuo contributo.")
        else:
            msg = f"La tua setta vince a {lname}, ma non hai mosso un dito: nessun merito per te."
    else:
        conn.execute("UPDATE sect_wars SET status='lost' WHERE id=?;", (war["id"],))
        conn.execute("UPDATE factions SET influence=MAX(0, influence-15) WHERE id=?;", (pfac,))
        conn.execute("UPDATE factions SET influence=influence+8 WHERE id=?;",
                     (war["enemy_faction_id"],))
        msg = (f"SCONFITTA a {lname}: la tua setta è piegata e perde influenza."
               + ("" if (war["score_player"] or 0) else " La tua assenza è pesata."))
    conn.execute("UPDATE npcs SET war_id=NULL WHERE war_id=?;", (war["id"],))
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="sect_war_resolved", tick=tick, location_id=war["battle_location_id"],
        title=f"Guerra tra sette: {'vittoria' if won else 'sconfitta'}",
        summary=msg,
        participants=[ev.Participant("faction", pfac, "defender"),
                      ev.Participant("faction", war["enemy_faction_id"], "attacker")],
        consequences=[ev.Consequence("faction", pfac, "war_outcome", msg,
                                     visibility="public", resolve_tick=tick)])
    if observations is not None:
        observations.append("⚔ " + msg)
    return 1


def tick(conn, tick_no, rng, player, observations) -> int:
    if player is None:
        return 0
    events = 0
    war = active_war(conn)
    if war:
        _background_skirmish(conn, tick_no, rng, war, observations)
        events += resolve(conn, tick_no, rng, player, observations)
    elif tick_no % DECLARE_INTERVAL == 0 and rng.random() < DECLARE_CHANCE:
        events += maybe_declare(conn, tick_no, rng, player, observations)
    return events


def describe(conn, war, player_loc, step_fn) -> str:
    pf = conn.execute("SELECT name FROM factions WHERE id=?;", (war["player_faction_id"],)).fetchone()["name"]
    ef = conn.execute("SELECT name FROM factions WHERE id=?;", (war["enemy_faction_id"],)).fetchone()["name"]
    lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                         (war["battle_location_id"],)).fetchone()["name"]
    enemies = len(enemy_disciples(conn, war))
    allies = len(ally_disciples(conn, war))
    from engine.core import tick as tickmod
    left = (war["deadline_tick"] or 0) - tickmod.get_tick(conn)
    lines = [f"GUERRA: {pf} contro {ef}, fronte a {lname}.",
             f"Nemici in campo: {enemies} | tuoi compagni: {allies} | "
             f"tuo punteggio: {war['score_player']}.",
             f"Tempo rimasto: ~{max(0, left)} tick."]
    if war["battle_location_id"] == player_loc:
        lines.append("Sei al fronte: 'attack <nome>' (uccidi), 'spare <nome>' (risparmia), "
                     "'absorb <nome>' sui caduti.")
    else:
        step = step_fn(conn, player_loc, war["battle_location_id"])
        if step:
            lines.append(f"Muoviti verso '{step}' per raggiungere il fronte.")
    return "\n".join(lines)
