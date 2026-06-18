"""
Cacciatori dell'Eretico.

Quando il tuo SOSPETTO o la tua INFAMIA salgono troppo, il mondo reagisce: anziani di
setta e cacciatori di taglie si mettono sulle tue tracce. Compaiono a poca distanza,
ti INSEGUONO di luogo in luogo e, quando ti raggiungono, ti AFFRONTANO.

La maschera è la tua via di fuga: in incognito ('mask on') perdono le tue tracce e,
col tempo, rinunciano.

Più sei famigerato, più cacciatori (e più forti) ti danno la caccia.
"""

from __future__ import annotations

import random
import sqlite3
from collections import deque

# soglie di pericolo (sospetto OPPURE infamia)
TIER1 = 500      # un cacciatore inizia a darti la caccia
TIER2 = 1000     # sei l'Eretico conclamato: più cacciatori, più forti
SPAWN_INTERVAL = 30
SPAWN_CHANCE = 0.6
GIVE_UP_DISGUISED = 0.4   # prob. che un cacciatore perda le tracce mentre sei in incognito


def _threat_tier(conn: sqlite3.Connection, player_id: int = 1) -> int:
    from engine.systems import reputation, character
    rep = reputation.get(conn, player_id)
    worst = max(rep["suspicion"], rep["infamy"])
    prof = character.get_profile(conn, "player", player_id)
    res = (prof["soul_residue"] or 0) if (prof and prof["anomaly"] == "abisso_divoratore") else 0
    if worst >= TIER2 or res >= 1000:        # Eretico conclamato / Anomalia Celeste
        return 2
    if worst >= TIER1 or res >= 250:         # indagini / gli anziani percepiscono l'Abisso
        return 1
    return 0


def active_hunters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name, location_id FROM npcs WHERE hunting=1 AND status='alive';").fetchall()


def _next_step_toward(conn: sqlite3.Connection, start: int, goal: int) -> int | None:
    """BFS sul grafo delle location: ritorna l'id della PROSSIMA location verso il goal."""
    if start == goal or start is None or goal is None:
        return None
    from engine.core import entities
    prev: dict[int, int] = {start: start}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for to in entities.get_exits(conn, cur).values():
            if to not in prev:
                prev[to] = cur
                q.append(to)
    if goal not in prev:
        return None
    node = goal
    while prev[node] != start:
        node = prev[node]
    return node


def _spawn_hunter(conn: sqlite3.Connection, tick: int, rng: random.Random,
                  player, tier: int) -> int | None:
    from engine.generators import npc_gen, dao_gen
    from engine.simulation import cultivation
    ploc = player.location_id
    if ploc is None:
        return None
    # comparsa a 2-3 passi dal giocatore (così c'è un inseguimento)
    far = conn.execute(
        "SELECT id FROM locations WHERE id<>? ORDER BY danger_level DESC, id LIMIT 8;",
        (ploc,)).fetchall()
    if not far:
        return None
    loc = rng.choice(far)["id"]
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    htier = max(2, min(8, ptier + (1 if tier >= 2 else 0)))   # pari o superiore al giocatore
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    realm_id = by_tier.get(htier, by_tier.get(1))
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    name = npc_gen._unique_name(rng, used)
    is_elder = rng.random() < 0.5
    archetype = "anziano" if is_elder else "cacciatore"
    desc = ("Un anziano di setta che dà la caccia all'eretico."
            if is_elder else "Un cacciatore di taglie spietato.")
    cur = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, kind, "
        "realm_id, hunting, last_active_tick) VALUES (?, ?, 'alive', ?, ?, 'human', ?, 1, ?);",
        (name, loc, desc, archetype, realm_id, tick))
    nid = cur.lastrowid
    stage = min(10, 5 + tier * 2)
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, 0.3, ?, ?, ?, ?, ?);",
        (nid, realm_id, stage, htier * 10 + stage * 2, htier * 8 + stage,
         htier * 8 + stage, htier * 6))
    # un cacciatore temibile: Dao da combattimento + Dao dell'Anima (ti percepisce)
    dao_gen._set_dao(conn, "npc", nid, "spada", 60, htier * 9 + stage, 1)
    dao_gen._set_dao(conn, "npc", nid, "anima", 55, htier * 7, 1)
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="hunter_dispatched", tick=tick, location_id=loc,
        title=f"{name} dà la caccia all'eretico",
        summary=f"{archetype.title()} {name} si mette sulle tracce del giocatore.",
        participants=[ev.Participant("npc", nid, "hunter"),
                      ev.Participant("player", player.id, "target")],
        consequences=[ev.Consequence("player", player.id, "hunted",
                                     "Sei dato per cacciato", visibility="public",
                                     resolve_tick=tick)])
    role = "Un anziano di setta" if is_elder else "Un cacciatore di taglie"
    return (nid, f"{role}, {name}, si è messo sulle tue tracce (avvistato a {lname}).")


def maybe_spawn(conn, tick, rng, player, observations) -> int:
    tier = _threat_tier(conn, player.id)
    if tier == 0:
        return 0
    cap = 1 if tier == 1 else 3
    if len(active_hunters(conn)) >= cap:
        return 0
    res = _spawn_hunter(conn, tick, rng, player, tier)
    if not res:
        return 0
    _nid, msg = res
    if observations is not None:
        observations.append("⚔ " + msg + " La maschera ('mask on') può farti perdere di vista.")
    return 1


def pursue(conn, tick, rng, player, observations) -> int:
    """Ogni cacciatore avanza verso il giocatore; se lo raggiunge, lo affronta.
    In incognito il giocatore può seminarli."""
    from engine.systems import reputation
    events = 0
    disguised = reputation.is_disguised(conn, player.id)
    for h in active_hunters(conn):
        if disguised and rng.random() < GIVE_UP_DISGUISED:
            # perde le tracce: rinuncia e si allontana
            conn.execute("UPDATE npcs SET hunting=0 WHERE id=?;", (h["id"],))
            if observations is not None:
                observations.append(f"In incognito, semini {h['name']}: ha perso le tue tracce.")
            events += 1
            continue
        if h["location_id"] == player.location_id:
            _confront(conn, tick, rng, player, h, observations)
            events += 1
            st = conn.execute("SELECT status FROM players WHERE id=?;",
                              (player.id,)).fetchone()["status"]
            if st != "alive":
                break
            continue
        if disguised:
            continue   # non sa dove sei: non avanza
        step = _next_step_toward(conn, h["location_id"], player.location_id)
        if step is not None:
            conn.execute("UPDATE npcs SET location_id=?, last_active_tick=? WHERE id=?;",
                         (step, tick, h["id"]))
            if step == player.location_id and observations is not None:
                observations.append(f"{h['name']} ti ha raggiunto: è qui, pronto ad affrontarti!")
    return events


def _confront(conn, tick, rng, player, hunter, observations) -> None:
    from engine.simulation import combat
    if observations is not None:
        observations.append(f"{hunter['name']} ti affronta in nome della giustizia!")
    combat.resolve_combat(
        conn, tick, rng, ("npc", hunter["id"], hunter["name"]),
        ("player", player.id, "te"), player.location_id, player.location_id, observations)


def on_hunter_defeated(conn, npc_id, player) -> str | None:
    """Sconfiggere un inseguitore placa l'indagine. Se era un CAMPIONE di una specie
    (bestia/demone/spirito) che ti dava la caccia, abbatterlo ti copre di gloria."""
    row = conn.execute("SELECT hunting, kind, name FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not row or not row["hunting"]:
        return None
    from engine.systems import reputation
    if row["kind"] and row["kind"] != "human":
        reputation.adjust(conn, player.id, fame=25, suspicion=-40, infamy=-10)
        return (f"Hai abbattuto {row['name']}: la tua fama di flagello delle creature "
                f"si diffonde, e le ombre sul tuo nome si diradano!")
    reputation.adjust(conn, player.id, suspicion=-120)
    return "Hai messo a tacere un cacciatore dell'Eretico: il sospetto su di te si attenua."


# ============================================================
# CACCIA TERRITORIALE — se stermini troppe creature di una specie, un loro CAMPIONE
# si mette sulle tue tracce. Abbatterlo dà gloria; oppure rientra in zona sicura.
# ============================================================

SPECIES_KILL_THRESHOLD = 6
_CHAMPION_NAME = {"beast": "Re Bestiale", "demon": "Signore Demoniaco", "spirit": "Antico Spirito"}
_SPECIES_LABEL = {"beast": "delle Bestie", "demon": "dei Demoni", "spirit": "degli Spiriti"}


def _nearby_spawn_loc(conn, start, rng, hops=2):
    """Una location a qualche passo dal giocatore (il campione poi lo raggiunge)."""
    cur = start
    for _ in range(hops):
        nbrs = [r["to_location_id"] for r in conn.execute(
            "SELECT to_location_id FROM location_connections WHERE from_location_id=?;",
            (cur,)).fetchall()]
        if not nbrs:
            break
        cur = rng.choice(nbrs)
    return cur if cur != start else None


def record_creature_kill(conn, tick, rng, player, kind) -> str | None:
    """Conta le uccisioni per specie; superata la soglia, evoca un campione che ti caccia."""
    if kind not in ("beast", "demon", "spirit"):
        return None
    key = f"species_kills:{kind}"
    row = conn.execute("SELECT value FROM game_state WHERE key=?;", (key,)).fetchone()
    n = (int(row["value"]) if row else 0) + 1
    if n < SPECIES_KILL_THRESHOLD:
        conn.execute("INSERT INTO game_state (key, value) VALUES (?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (key, str(n)))
        return None
    conn.execute("INSERT INTO game_state (key, value) VALUES (?, '0') "
                 "ON CONFLICT(key) DO UPDATE SET value='0';", (key,))
    return _spawn_champion(conn, tick, rng, player, kind)


def _spawn_champion(conn, tick, rng, player, kind) -> str:
    from engine.generators import creature_gen
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    tier = max(2, ptier + 1)
    loc = _nearby_spawn_loc(conn, player.location_id, rng) or player.location_id
    nid = creature_gen._spawn_one(conn, rng, kind, loc, tier, tier + 1)
    cname = _CHAMPION_NAME.get(kind, "Campione")
    conn.execute("UPDATE npcs SET hunting=1, name=? WHERE id=?;", (cname, nid))
    return (f"⚠ Hai sterminato troppe creature: il {cname} {_SPECIES_LABEL.get(kind, '')} "
            f"si mette sulle tue tracce! Affrontalo quando ti raggiunge, o rifugiati "
            f"('home') finché non si placa.")


def tick(conn, tick_no, rng, player, observations) -> int:
    if player is None or player.location_id is None:
        return 0
    events = pursue(conn, tick_no, rng, player, observations)
    if tick_no % SPAWN_INTERVAL == 0 and rng.random() < SPAWN_CHANCE:
        events += maybe_spawn(conn, tick_no, rng, player, observations)
    return events
