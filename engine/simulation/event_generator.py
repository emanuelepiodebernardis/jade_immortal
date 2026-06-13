"""
Event generator (Fase 5).

Genera la "vita sociale" del mondo tra gli NPC nello scope attivo:
  - incontri (encounter): NPC co-locati interagiscono; la relazione migliora o
    peggiora in base a tratti e relazione pregressa;
  - combattimenti (fight): un incontro molto ostile può degenerare in scontro
    (risoluzione semplice, precursore del sistema di combattimento della Fase 6);
  - morte (rara): uno scontro programma un `death_check` DIFFERITO; il resolver
    lo applica tick dopo, e solo con bassa probabilità l'NPC muore.

Conseguenze differite: un evento ora può registrare una conseguenza con
`resolve_tick` futuro e `resolved=0`. `resolve_due_consequences` le applica quando
maturano. Questo è il meccanismo delle "conseguenze a manifestazione differita".

Tutto passa per event_system.log_event -> vincolo 26 garantito.
"""

from __future__ import annotations

import itertools
import random
import sqlite3

from engine.core import entities
from engine.simulation import event_system as ev
from engine.simulation import faction_engine
from engine.systems import relations

ENCOUNTER_PROB = 0.15        # prob. che una coppia selezionata interagisca, per tick
MAX_PAIRS_PER_LOC = 2        # coppie valutate per location per tick (bound volume)
FIGHT_REL_THRESHOLD = -40    # relazione sotto cui un incontro può degenerare
FIGHT_ESCALATION_PROB = 0.4  # prob. che l'ostilità diventi scontro
DEATH_FROM_WOUND_PROB = 0.25 # prob. che un death_check porti alla morte


# ---------- incontri ----------

def resolve_encounters(conn: sqlite3.Connection, tick: int, scope: set[int],
                       rng: random.Random, observer: int | None,
                       observations: list[str]) -> int:
    events = 0
    for loc in scope:
        npcs = entities.npcs_in_location(conn, loc)
        if len(npcs) < 2:
            continue
        pairs = list(itertools.combinations(npcs, 2))
        rng.shuffle(pairs)
        for a, b in pairs[:MAX_PAIRS_PER_LOC]:
            if rng.random() < ENCOUNTER_PROB:
                events += _encounter(conn, tick, rng, a, b, loc, observer, observations)
    return events


def _compat(ta: dict, tb: dict) -> int:
    c = 0
    c += (ta.get("honor", 50) - 50 + tb.get("honor", 50) - 50) // 10
    c -= (ta.get("greed", 50) - 50 + tb.get("greed", 50) - 50) // 10
    c -= max(0, (ta.get("pride", 50) - 60) + (tb.get("pride", 50) - 60)) // 10
    return c


def _faction_enmity(conn, a, b) -> int:
    """Relazione tra le fazioni dei due NPC (0 se senza fazione o stessa fazione)."""
    fa = conn.execute("SELECT faction_id FROM npcs WHERE id=?;", (a.id,)).fetchone()["faction_id"]
    fb = conn.execute("SELECT faction_id FROM npcs WHERE id=?;", (b.id,)).fetchone()["faction_id"]
    if fa is None or fb is None or fa == fb:
        return 0
    return faction_engine.get_relation(conn, fa, fb)


def _encounter(conn, tick, rng, a, b, loc, observer, observations) -> int:
    ta = entities.get_npc_traits(conn, a.id)
    tb = entities.get_npc_traits(conn, b.id)
    rel = relations.get_npc_relation(conn, a.id, b.id)
    fac_rel = _faction_enmity(conn, a, b)        # tensione ereditata dalle fazioni
    compat = _compat(ta, tb) + rng.randint(-10, 10)
    # l'ostilità effettiva considera relazione personale + relazione tra fazioni
    # (membri di sette in guerra possono scontrarsi anche al primo incontro)
    effective_rel = rel + fac_rel

    # incontro ostile -> possibile scontro
    if effective_rel <= FIGHT_REL_THRESHOLD and min(ta.get("courage", 50), tb.get("courage", 50)) > 40:
        if rng.random() < FIGHT_ESCALATION_PROB:
            return _fight(conn, tick, rng, a, b, loc, observer, observations)

    # interazione sociale (immediata); la tensione tra fazioni spinge verso il negativo
    delta = max(-8, min(8, compat * 2 + fac_rel // 15))
    relations.adjust_npc(conn, a.id, b.id, delta, tick)
    relations.adjust_npc(conn, b.id, a.id, delta, tick)
    verb = "stringono un'intesa" if delta > 0 else ("si scontrano a parole" if delta < 0 else "si incrociano")
    ev.log_event(
        conn, event_type="encounter", tick=tick, location_id=loc,
        title=f"{a.name} e {b.name} {verb}",
        summary=f"{a.name} e {b.name} {verb}.",
        participants=[ev.Participant("npc", a.id, "initiator"),
                      ev.Participant("npc", b.id, "target")],
        consequences=[ev.Consequence(
            "npc", a.id, "relation_change", f"relazione con {b.id} {delta:+d}",
            visibility="public" if loc == observer else "hidden", resolve_tick=tick)],
    )
    return 1


def _fight(conn, tick, rng, a, b, loc, observer, observations) -> int:
    """Uno scontro tra NPC ora usa il vero sistema di combattimento (Fase 6)."""
    from engine.simulation import combat
    relations.adjust_npc(conn, a.id, b.id, -20, tick)
    relations.adjust_npc(conn, b.id, a.id, -20, tick)
    combat.resolve_combat(
        conn, tick, rng,
        ("npc", a.id, a.name), ("npc", b.id, b.name),
        loc, observer, observations,
    )
    return 1


def resolve_player_threats(conn, tick, scope, rng, player, observer, observations) -> int:
    """NPC molto ostili al giocatore e co-locati possono attaccarlo da soli.
    All'inizio nessuno lo è (disposizione neutra): la minaccia emerge se il
    giocatore si fa dei nemici."""
    if player is None or player.location_id is None:
        return 0
    events = 0
    npcs = entities.npcs_in_location(conn, player.location_id)
    for npc in npcs:
        disp = relations.get_disposition(conn, npc.id).score
        traits = entities.get_npc_traits(conn, npc.id)
        if disp <= -40 and traits.get("courage", 50) > 50 and rng.random() < 0.3:
            from engine.simulation import combat
            combat.resolve_combat(
                conn, tick, rng,
                ("npc", npc.id, npc.name), ("player", player.id, "te"),
                player.location_id, observer, observations,
            )
            events += 1
            # se il giocatore muore, basta un attacco
            st = conn.execute("SELECT status FROM players WHERE id=?;", (player.id,)).fetchone()["status"]
            if st != "alive":
                break
    return events


# ---------- resolver conseguenze differite ----------

def resolve_due_consequences(conn: sqlite3.Connection, tick: int, rng: random.Random,
                             observer: int | None, observations: list[str],
                             death_prob: float = DEATH_FROM_WOUND_PROB) -> int:
    events = 0
    due = conn.execute(
        "SELECT id, target_id FROM consequences "
        "WHERE resolved=0 AND consequence_type='death_check' AND resolve_tick<=?;",
        (tick,),
    ).fetchall()

    for row in due:
        npc_id = row["target_id"]
        npc = conn.execute(
            "SELECT id, name, location_id, status, faction_id FROM npcs WHERE id=?;",
            (npc_id,),
        ).fetchone()
        if npc and npc["status"] == "alive" and rng.random() < death_prob:
            events += _kill_npc(conn, tick, rng, npc, observer, observations)
        conn.execute("UPDATE consequences SET resolved=1 WHERE id=?;", (row["id"],))
    return events


def _kill_npc(conn, tick, rng, npc, observer, observations) -> int:
    conn.execute(
        "UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (tick, npc["id"]),
    )
    consequences = [ev.Consequence(
        "npc", npc["id"], "death", "morto per le ferite riportate",
        visibility="public" if npc["location_id"] == observer else "hidden",
        resolve_tick=tick)]

    # successione se era un leader di fazione
    if npc["faction_id"] is not None:
        leads = conn.execute(
            "SELECT id FROM factions WHERE leader_id=?;", (npc["id"],)
        ).fetchone()
        if leads:
            successor = conn.execute(
                "SELECT n.id FROM npcs n JOIN npc_traits t ON t.npc_id=n.id "
                "WHERE n.faction_id=? AND n.status='alive' AND n.id<>? "
                "ORDER BY (t.ambition + t.pride) DESC LIMIT 1;",
                (npc["faction_id"], npc["id"]),
            ).fetchone()
            new_leader = successor["id"] if successor else None
            conn.execute("UPDATE factions SET leader_id=? WHERE id=?;",
                         (new_leader, leads["id"]))
            consequences.append(ev.Consequence(
                "faction", leads["id"], "succession",
                f"nuovo leader: {new_leader}" if new_leader else "fazione senza leader",
                visibility="hidden", resolve_tick=tick))

    ev.log_event(
        conn, event_type="death", tick=tick, location_id=npc["location_id"],
        title=f"Morte di {npc['name']}",
        summary=f"{npc['name']} è morto.",
        participants=[ev.Participant("npc", npc["id"], "victim")],
        consequences=consequences,
    )
    if npc["location_id"] == observer:
        observations.append(f"{npc['name']} è morto.")
    return 1
