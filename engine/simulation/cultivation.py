"""
Cultivation system (Fase 7).

Progressione xianxia reale e NON garantita:
  - `cultivate` accumula progresso entro il regno corrente;
  - al colmo (progress >= 1.0) si può tentare un BREAKTHROUGH;
  - il breakthrough può RIUSCIRE (sali di regno), FALLIRE (contraccolpo) o, raro,
    causare DEVIAZIONE DEL QI e morte. Più alto è il regno, più è rischioso.

Il fattore di regno alimenta il combattimento (combat._realm_factor): coltivare
rende davvero più forti.
"""

from __future__ import annotations

import random
import sqlite3

from engine.simulation import event_system as ev

MAX_TIER = 8
REALM_FACTOR_PER_TIER = 0.4
STAGES_PER_REALM = 10
# dopo questo numero di fallimenti accumulati, il corpo è così temprato da SFONDARE comunque
BT_GUARANTEE = 8
PER_STAGE_FACTOR = REALM_FACTOR_PER_TIER / STAGES_PER_REALM   # scaling fluido entro il regno


def ensure_realm(conn: sqlite3.Connection, tier: int) -> int:
    """Ritorna l'id del regno di un certo tier, creandolo (con nome auto-generato) se non
    esiste ancora: i regni salgono all'infinito oltre l'Immortale di Giada."""
    row = conn.execute("SELECT id FROM cultivation_realms WHERE tier=?;", (tier,)).fetchone()
    if row:
        return row["id"]
    from engine.generators import cultivation_gen
    name = cultivation_gen.realm_name_for_tier(tier)
    qi, body, soul, dao = cultivation_gen.requirements_for(tier)
    cur = conn.execute(
        "INSERT INTO cultivation_realms (name, tier, qi_requirement, body_requirement, "
        "soul_requirement, dao_requirement) VALUES (?, ?, ?, ?, ?, ?);",
        (name, tier, qi, body, soul, dao))
    return cur.lastrowid


def realm_tier(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    table = "players" if ctype == "player" else "npcs"
    row = conn.execute(
        f"SELECT r.tier FROM {table} c JOIN cultivation_realms r ON r.id=c.realm_id "
        "WHERE c.id=?;", (cid,),
    ).fetchone()
    return row["tier"] if row and row["tier"] else 1


def stage_of(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    rec = get_record(conn, ctype, cid)
    s = rec["stage"] if rec and "stage" in rec.keys() and rec["stage"] else 1
    return max(1, min(STAGES_PER_REALM, s))


def effective_level(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    """Livello assoluto: (tier-1)*10 + stage. Usato dal combattimento."""
    return (realm_tier(conn, ctype, cid) - 1) * STAGES_PER_REALM + stage_of(conn, ctype, cid)


def realm_label(conn: sqlite3.Connection, ctype: str, cid: int) -> str:
    """Es. 'Condensazione del Qi · Strato 4/10'."""
    return f"{realm_name(conn, ctype, cid)} · Strato {stage_of(conn, ctype, cid)}/{STAGES_PER_REALM}"


def realm_name(conn: sqlite3.Connection, ctype: str, cid: int) -> str:
    table = "players" if ctype == "player" else "npcs"
    row = conn.execute(
        f"SELECT r.name FROM {table} c JOIN cultivation_realms r ON r.id=c.realm_id "
        "WHERE c.id=?;", (cid,),
    ).fetchone()
    return row["name"] if row and row["name"] else "Mortale"


def get_record(conn: sqlite3.Connection, ctype: str, cid: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM cultivation_records WHERE character_type=? AND character_id=?;",
        (ctype, cid),
    ).fetchone()


def _add_progress(conn, ctype, cid, amount: float) -> float:
    rec = get_record(conn, ctype, cid)
    if rec is None:
        return 0.0
    new = min(1.5, rec["progress"] + amount)
    conn.execute(
        "UPDATE cultivation_records SET progress=?, qi_level=qi_level+1 "
        "WHERE id=?;", (new, rec["id"]),
    )
    return new


def cultivate(conn, ctype, cid, tick: int, rng: random.Random,
              amount: float | None = None, multiplier: float = 1.0) -> dict:
    """Sessione di coltivazione. L'esperienza riempie lo STRATO corrente; quando si
    colma, avanzi automaticamente di strato (le statistiche salgono) e l'esperienza
    riparte da zero. Allo Strato 10 colmo, serve un BREAKTHROUGH (rischioso) per
    salire di REGNO."""
    tier = realm_tier(conn, ctype, cid)
    if amount is None:
        amount = rng.uniform(0.08, 0.15) / (1 + (tier - 1) * 0.5)
    from engine.systems import character
    amount *= character.affinity_factor(conn, ctype, cid, "cultivation") * multiplier

    rec = get_record(conn, ctype, cid)
    if rec is None:
        return {"progress": 0.0, "tier": tier, "stage": 1, "ready": False, "stage_up": False}
    stage = max(1, min(STAGES_PER_REALM, rec["stage"] if rec["stage"] else 1))
    progress = rec["progress"] + amount
    stage_up = False

    # avanzamento automatico degli strati entro il regno
    while progress >= 1.0 and stage < STAGES_PER_REALM:
        progress -= 1.0
        stage += 1
        stage_up = True
        # ogni strato rende un po' più forti (statistiche su)
        conn.execute(
            "UPDATE cultivation_records SET qi_level=qi_level+2, body_level=body_level+1, "
            "soul_level=soul_level+1 WHERE id=?;", (rec["id"],))

    ready = False
    if stage >= STAGES_PER_REALM and progress >= 1.0:
        progress = 1.0          # allo strato massimo l'esperienza si ferma: serve il breakthrough
        ready = True

    conn.execute(
        "UPDATE cultivation_records SET progress=?, stage=?, qi_level=qi_level+1 WHERE id=?;",
        (progress, stage, rec["id"]))
    return {"progress": progress, "tier": tier, "stage": stage,
            "ready": ready, "stage_up": stage_up}


def attempt_breakthrough(conn, ctype, cid, tick: int, rng: random.Random,
                         observer: int | None = None,
                         observations: list | None = None) -> dict:
    rec = get_record(conn, ctype, cid)
    tier = realm_tier(conn, ctype, cid)
    if rec is None:
        return {"status": "no_record"}
    # nessun tetto: la via sale all'infinito (i regni oltre l'8 si generano da soli)
    if not (stage_of(conn, ctype, cid) >= STAGES_PER_REALM and rec["progress"] >= 1.0):
        return {"status": "not_ready"}

    dao = rec["dao_understanding"]
    fails = rec["bt_failures"] or 0
    from engine.systems import character
    aff_bonus = (character.affinity_factor(conn, ctype, cid, "cultivation") - 1.0) * 0.15
    # corruzione dell'Abisso: il Cielo percepisce la minaccia e OSTACOLA l'ascesa
    # (abbassa la riuscita; NON aumenta più la letalità — quello era il vecchio trabocchetto)
    residue_penalty = 0.0
    if ctype == "player":
        prof = character.get_profile(conn, "player", cid)
        if prof and prof["soul_residue"]:
            residue_penalty = min(0.35, prof["soul_residue"] * 0.0007)
    # ogni fallimento tempra il corpo e ti rende più PRONTO al tentativo seguente
    fail_bonus = fails * 0.13
    fate_succ, fate_death = 0.0, 1.0
    if ctype == "player":
        from engine.systems import dao_powers
        fate_succ, fate_death = dao_powers.fate_breakthrough(conn, cid)   # Dao del Destino
    p_success = max(0.05, min(0.97,
                              0.5 + (rec["progress"] - 1.0) + dao * 0.003 - tier * 0.04
                              + aff_bonus - residue_penalty + fail_bonus + fate_succ))
    name = _char_name(conn, ctype, cid)
    loc = _char_location(conn, ctype, cid)

    # garanzia anti-stallo: dopo molti fallimenti il corpo SFONDA comunque
    if fails >= BT_GUARANTEE:
        return _breakthrough_success(conn, ctype, cid, tier, tick, name, loc, observer, observations)

    if rng.random() < p_success:
        return _breakthrough_success(conn, ctype, cid, tier, tick, name, loc, observer, observations)

    # fallimento: contraccolpo o morte (le origini "hard_tribulation" rischiano di più)
    p_death = 0.03 + tier * 0.02
    if character.has_flag(conn, ctype, cid, "hard_tribulation"):
        p_death *= 1.5
    # i fallimenti accumulati temprano il corpo contro la deviazione del qi: meno morte
    p_death *= (1.0 - min(0.7, fails * 0.18))
    # il karma negativo rende la tribolazione più letale (vale anche per gli NPC)
    from engine.systems import karma
    p_death *= karma.breakthrough_factor(karma.get_karma(conn, ctype, cid))
    p_death *= fate_death                     # il Destino allontana la catastrofe
    if rng.random() < p_death:
        return _breakthrough_death(conn, ctype, cid, tier, tick, rng, name, loc, observer, observations)
    return _breakthrough_setback(conn, ctype, cid, rec, tier, tick, name, loc, observer, observations)


def _breakthrough_success(conn, ctype, cid, tier, tick, name, loc, observer, observations):
    new_tier = tier + 1
    new_realm_id = ensure_realm(conn, new_tier)        # crea il regno se non esiste (infinito)
    new_realm = conn.execute(
        "SELECT id, name FROM cultivation_realms WHERE id=?;", (new_realm_id,)).fetchone()
    table = "players" if ctype == "player" else "npcs"
    conn.execute(f"UPDATE {table} SET realm_id=? WHERE id=?;", (new_realm["id"], cid))
    conn.execute(
        "UPDATE cultivation_records SET realm_id=?, progress=0, stage=1, breakthrough_tick=?, "
        "bt_failures=0, "
        "qi_level=qi_level+10, body_level=body_level+8, soul_level=soul_level+8, "
        "dao_understanding=dao_understanding+5 WHERE character_type=? AND character_id=?;",
        (new_realm["id"], tick, ctype, cid),
    )
    ev.log_event(
        conn, event_type="breakthrough", tick=tick, location_id=loc,
        title=f"{name} ascende a {new_realm['name']}",
        summary=f"{name} sfonda fino al regno {new_realm['name']}.",
        participants=[ev.Participant(ctype, cid, "initiator")],
        consequences=[ev.Consequence(ctype, cid, "realm_change",
                                     f"nuovo regno: tier {new_tier}",
                                     visibility="public" if loc == observer else "hidden",
                                     resolve_tick=tick)],
    )
    if observations is not None and loc == observer:
        observations.append(f"{name} sfonda fino a {new_realm['name']}.")
    return {"status": "success", "new_tier": new_tier, "realm": new_realm["name"]}


def _breakthrough_setback(conn, ctype, cid, rec, tier, tick, name, loc, observer, observations):
    # contraccolpo: retrocedi di uno strato (o perdi progresso se sei già in basso)
    stage = max(1, min(STAGES_PER_REALM, rec["stage"] if rec["stage"] else 1))
    new_stage = max(1, stage - 1)
    fails = (rec["bt_failures"] or 0) + 1
    # il fallimento TEMPRA il corpo: la coltivazione cala ma la carne si rinforza
    body_gain = 3 + tier
    conn.execute(
        "UPDATE cultivation_records SET progress=0.5, stage=?, bt_failures=?, "
        "body_level=body_level+? WHERE id=?;",
        (new_stage, fails, body_gain, rec["id"]))
    # per il giocatore la forgiatura si SENTE in combattimento (forza/vitalità/resistenza)
    if ctype == "player":
        conn.execute(
            "UPDATE character_profiles SET grow_strength=grow_strength+?, "
            "grow_vitality=grow_vitality+?, grow_resistance=grow_resistance+? "
            "WHERE character_type='player' AND character_id=?;",
            (2 + tier, 2 + tier, 1 + tier, cid))
    ev.log_event(
        conn, event_type="breakthrough_failure", tick=tick, location_id=loc,
        title=f"{name} fallisce il breakthrough",
        summary=f"{name} non riesce a sfondare e subisce un contraccolpo.",
        participants=[ev.Participant(ctype, cid, "initiator")],
        consequences=[ev.Consequence(ctype, cid, "cultivation_setback",
                                     "progresso perduto nel contraccolpo",
                                     visibility="public" if loc == observer else "hidden",
                                     resolve_tick=tick)],
    )
    if observations is not None and loc == observer:
        observations.append(f"{name} fallisce il proprio breakthrough.")
    return {"status": "failure", "bt_failures": fails}


def _breakthrough_death(conn, ctype, cid, tier, tick, rng, name, loc, observer, observations):
    from engine.simulation import combat
    consequences = combat._kill(conn, tick, rng, (ctype, cid, name), "hidden")
    ev.log_event(
        conn, event_type="death", tick=tick, location_id=loc,
        title=f"Deviazione del qi: {name}",
        summary=f"{name} perisce in una deviazione del qi durante il breakthrough.",
        participants=[ev.Participant(ctype, cid, "victim")],
        consequences=consequences,
    )
    if observations is not None and loc == observer:
        observations.append(f"{name} muore in una deviazione del qi.")
    return {"status": "death"}


def npc_cultivation_pass(conn, tick, scope: set[int], rng: random.Random,
                         observer: int | None, observations: list) -> int:
    """Coltivazione passiva degli NPC attivi; raramente tentano un breakthrough."""
    if not scope:
        return 0
    placeholders = ",".join("?" * len(scope))
    npcs = conn.execute(
        f"SELECT id FROM npcs WHERE status='alive' AND location_id IN ({placeholders});",
        tuple(scope),
    ).fetchall()
    events = 0
    for n in npcs:
        res = cultivate(conn, "npc", n["id"], tick, rng, amount=0.004)
        if res["ready"] and rng.random() < 0.03:
            r = attempt_breakthrough(conn, "npc", n["id"], tick, rng, observer, observations)
            if r["status"] in ("success", "failure", "death"):
                events += 1
    return events


# ---------- helper ----------

def _char_name(conn, ctype, cid) -> str:
    if ctype == "player":
        row = conn.execute("SELECT name FROM players WHERE id=?;", (cid,)).fetchone()
        return row["name"] if row else "Tu"
    row = conn.execute("SELECT name FROM npcs WHERE id=?;", (cid,)).fetchone()
    return row["name"] if row else "?"


def _char_location(conn, ctype, cid) -> int | None:
    table = "players" if ctype == "player" else "npcs"
    row = conn.execute(f"SELECT location_id FROM {table} WHERE id=?;", (cid,)).fetchone()
    return row["location_id"] if row else None
