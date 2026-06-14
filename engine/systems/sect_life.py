"""
Vita di setta: il loop di competizione.

Quando ti iscrivi a una setta:
  - ti vengono assegnati 2-3 COMPAGNI DI CLASSE (rivali al tuo livello);
  - tra 10 giorni si tiene la SFIDA DI CLASSIFICA che fissa la graduatoria iniziale;
  - poi OGNI MESE un TORNEO aggiorna la classifica e premia i migliori;
  - quando superi il regno della tua classe, vieni PROMOSSO alla classe successiva
    (nuovi compagni, nuovo calendario).

I tornei sono sparring NON letali: l'esito dipende dalla potenza (regno + strato +
affinità), con varianza. Il narratore annuncia e racconta gli eventi.
"""

from __future__ import annotations

import random
import sqlite3

from engine.systems import training
from engine.simulation import cultivation, combat, event_system as ev

CLASS_SIZE = 3                         # compagni di classe (oltre al giocatore)
CHALLENGE_DELAY = 10 * training.DAY_TICKS    # 10 giorni
MONTH_TICKS = 30 * training.DAY_TICKS        # 1 mese
REWARDS = {1: 120, 2: 70, 3: 40, 4: 20}      # pietre spirituali per piazzamento


# ---------- setup classe / compagni ----------

def setup_class(conn: sqlite3.Connection, tick: int, rng: random.Random,
                player_id: int = 1) -> dict:
    """Crea i compagni di classe e programma la sfida di classifica. Usato all'iscrizione
    e a ogni promozione di classe."""
    from engine.systems import sects
    m = sects.get_membership(conn, player_id)
    if not m:
        return {"status": "not_member"}
    faction_id = m["faction_id"]
    tier = cultivation.realm_tier(conn, "player", player_id)

    _clear_class(conn, player_id)
    hq = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (faction_id,)).fetchone()
    loc = hq["home_location_id"] if hq else None

    mates = _spawn_classmates(conn, rng, faction_id, loc, tier, CLASS_SIZE)
    for nid in mates:
        conn.execute(
            "INSERT OR IGNORE INTO sect_cohort (player_id, npc_id, faction_id, class_tier) "
            "VALUES (?, ?, ?, ?);", (player_id, nid, faction_id, tier))

    conn.execute("UPDATE sect_memberships SET class_tier=?, class_rank=NULL WHERE player_id=?;",
                 (tier, player_id))
    schedule_event(conn, player_id, faction_id, "ranking_challenge", tick + CHALLENGE_DELAY)
    return {"status": "ok", "mates": mates, "challenge_tick": tick + CHALLENGE_DELAY}


def _clear_class(conn, player_id) -> None:
    conn.execute("DELETE FROM sect_cohort WHERE player_id=?;", (player_id,))
    conn.execute("DELETE FROM sect_events WHERE player_id=? AND resolved=0;", (player_id,))


def _spawn_classmates(conn, rng, faction_id, location_id, tier, n) -> list[int]:
    from engine.generators import npc_gen, dao_gen
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    realm_id = by_tier.get(tier, by_tier.get(1))
    # le sette di livello alto hanno discepoli più affilati (stesso regno, più maestria)
    srow = conn.execute("SELECT tier FROM factions WHERE id=?;", (faction_id,)).fetchone()
    sect_tier = (srow["tier"] if srow and srow["tier"] else 1)
    stage_lo = min(9, 2 + sect_tier)
    stage_hi = min(10, 6 + sect_tier)
    ids = []
    for _ in range(n):
        name = npc_gen._unique_name(rng, used)
        traits = npc_gen.roll_traits(rng, "discepolo")
        desc = npc_gen.make_description("discepolo", traits)
        cur = conn.execute(
            "INSERT INTO npcs (name, location_id, status, description, archetype, "
            "faction_id, realm_id, last_active_tick) VALUES (?, ?, 'alive', ?, 'discepolo', ?, ?, 0);",
            (name, location_id, desc, faction_id, realm_id))
        nid = cur.lastrowid
        conn.execute(
            "INSERT INTO npc_traits (npc_id, ambition, honor, greed, courage, loyalty, "
            "compassion, pride) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (nid, traits["ambition"], traits["honor"], traits["greed"], traits["courage"],
             traits["loyalty"], traits["compassion"], traits["pride"]))
        # coltivazione: stesso regno, strato vicino al giocatore (rivali credibili)
        stage = max(1, min(10, rng.randint(stage_lo, stage_hi)))
        conn.execute(
            "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
            "stage, qi_level, body_level, soul_level, dao_understanding) "
            "VALUES (?, 'npc', ?, ?, ?, ?, ?, ?, ?);",
            (nid, realm_id, round(rng.uniform(0, 0.5), 2), stage,
             tier * 10 + stage * 2, tier * 8 + stage, tier * 8 + stage, tier * 5))
        # un Dao primario, così sono assorbibili / esaminabili; più forte nelle sette alte
        pool = ["spada", "corpo", "fulmine", "anima"]
        conn.execute(
            "INSERT OR IGNORE INTO character_daos (character_type, character_id, dao_key, "
            "affinity, comprehension, practiced) VALUES ('npc', ?, ?, ?, ?, 1);",
            (nid, rng.choice(pool), rng.randint(45, 65), tier * 9 + stage + sect_tier * 8))
        ids.append(nid)
    return ids


# ---------- scheduler ----------

def schedule_event(conn, player_id, faction_id, kind, fire_tick) -> None:
    conn.execute(
        "INSERT INTO sect_events (player_id, faction_id, kind, fire_tick, resolved) "
        "VALUES (?, ?, ?, ?, 0);", (player_id, faction_id, kind, fire_tick))


def next_event(conn, tick, player_id=1) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT kind, fire_tick, faction_id FROM sect_events "
        "WHERE player_id=? AND resolved=0 ORDER BY fire_tick LIMIT 1;", (player_id,)
    ).fetchone()


def resolve_sect_events(conn, tick, rng, player, observer, observations) -> int:
    """Chiamata a ogni tick: fa scattare le sfide/tornei maturi."""
    if player is None:
        return 0
    due = conn.execute(
        "SELECT id, faction_id, kind FROM sect_events "
        "WHERE player_id=? AND resolved=0 AND fire_tick<=?;", (player.id, tick)
    ).fetchall()
    fired = 0
    for e in due:
        conn.execute("UPDATE sect_events SET resolved=1 WHERE id=?;", (e["id"],))
        _run_tournament(conn, tick, rng, player.id, e["faction_id"], e["kind"],
                        observer, observations)
        # programma il prossimo torneo mensile
        schedule_event(conn, player.id, e["faction_id"], "monthly_tournament", tick + MONTH_TICKS)
        fired += 1
    return fired


# ---------- tornei ----------

def _rating(conn, ctype, cid, rng) -> float:
    p = combat.combat_power(conn, ctype, cid)
    base = p["attack"] * 1.2 + p["defense"] + p["vitality"] * 0.5
    return base * rng.uniform(0.82, 1.18)      # varianza: il favorito non vince sempre


def _run_tournament(conn, tick, rng, player_id, faction_id, kind, observer, observations):
    cohort = [r["npc_id"] for r in conn.execute(
        "SELECT npc_id FROM sect_cohort WHERE player_id=? AND faction_id=?;",
        (player_id, faction_id)).fetchall()]
    # solo compagni ancora vivi
    cohort = [n for n in cohort if conn.execute(
        "SELECT status FROM npcs WHERE id=?;", (n,)).fetchone()["status"] == "alive"]

    contenders = [("player", player_id)] + [("npc", n) for n in cohort]
    scored = sorted(contenders, key=lambda c: _rating(conn, c[0], c[1], rng), reverse=True)
    placement = {c: i + 1 for i, c in enumerate(scored)}
    player_rank = placement[("player", player_id)]
    total = len(scored)

    # racconta gli incontri del giocatore contro ogni compagno
    from engine.systems import combat_narration as cn
    match_lines = []
    for n in cohort:
        opp_name = conn.execute("SELECT name FROM npcs WHERE id=?;", (n,)).fetchone()["name"]
        _, line = cn.match_line(conn, "Tu", opp_name, ("player", player_id), ("npc", n), rng)
        match_lines.append("  " + line)

    conn.execute("UPDATE sect_memberships SET class_rank=? WHERE player_id=?;",
                 (player_rank, player_id))
    stones = REWARDS.get(player_rank, 10)
    from engine.systems import sects
    sects.grant_resource(conn, "pietre_spirituali", stones, player_id)

    # gloria pubblica: il piazzamento accresce la fama (reputazione sociale)
    from engine.systems import reputation
    fame_gain = {1: 30, 2: 15, 3: 6}.get(player_rank, 0)
    if fame_gain:
        reputation.adjust(conn, player_id, fame=fame_gain)

    sect = conn.execute("SELECT name FROM factions WHERE id=?;", (faction_id,)).fetchone()["name"]
    label = "Sfida di Classifica" if kind == "ranking_challenge" else "Torneo Mensile"
    ordinal = {1: "1°", 2: "2°", 3: "3°", 4: "4°"}.get(player_rank, f"{player_rank}°")
    summary = (f"{label} di {sect}: ti classifichi {ordinal} su {total}. "
               f"Ricevi {stones} pietre spirituali.")
    detail = summary + ("\n" + "\n".join(match_lines) if match_lines else "")

    loc = conn.execute("SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()["location_id"]
    ev.log_event(
        conn, event_type="sect_tournament", tick=tick, location_id=loc,
        title=f"{label} — {sect}",
        summary=summary,
        participants=[ev.Participant("player", player_id, "competitor")]
                     + [ev.Participant("npc", n, "competitor") for n in cohort],
        consequences=[ev.Consequence("player", player_id, "class_rank",
                                     f"piazzamento {player_rank}/{total}",
                                     visibility="public", resolve_tick=tick)],
    )
    if observations is not None:
        observations.append(detail)

    # vincere il torneo richiama i 7 rappresentanti delle sette superiori
    if player_rank == 1:
        invs = sects.generate_invitations(conn, tick, rng, player_id)
        if invs and observations is not None:
            observations.append(
                "I tuoi exploit hanno richiamato i RAPPRESENTANTI di sette superiori: "
                "usa 'invitations' per vederli e 'accept <numero>' per ascendere.")


# ---------- promozione di classe ----------

def promote_class(conn, tick, rng, player_id=1) -> dict:
    """Dopo un breakthrough di regno, se sei in una setta avanzi di classe."""
    from engine.systems import sects
    m = sects.get_membership(conn, player_id)
    if not m:
        return {"status": "not_member"}
    new = setup_class(conn, tick, rng, player_id)
    return {"status": "promoted", **new}


# ---------- agenda (cosa mi aspetta) ----------

def agenda_line(conn, tick, player_id=1) -> str | None:
    nxt = next_event(conn, tick, player_id)
    if not nxt:
        return None
    days = max(0, (nxt["fire_tick"] - tick + training.DAY_TICKS - 1) // training.DAY_TICKS)
    label = "Sfida di Classifica" if nxt["kind"] == "ranking_challenge" else "Torneo Mensile"
    when = "oggi" if days == 0 else f"tra {days} giorni"
    return f"{label}: {when}."


def classmates(conn, player_id=1) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT n.id, n.name FROM sect_cohort c JOIN npcs n ON n.id=c.npc_id "
        "WHERE c.player_id=? AND n.status='alive';", (player_id,)
    ).fetchall()
