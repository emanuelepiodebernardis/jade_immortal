"""
World Tick System (Fase 3).

Il mondo si muove anche senza il giocatore. A ogni tick, gli NPC nello SCOPE
ATTIVO (principio P1) eseguono una routine minima: restano fermi o si spostano
in una location adiacente. Ogni spostamento è un evento tracciabile (vincolo 26).

Active Simulation Scope (P1):
  scope = location dell'osservatore (player) + location adiacenti.
  Solo gli NPC dentro lo scope vengono simulati. Gli altri restano dormienti;
  il loro `last_active_tick` non avanza, abilitando la batch simulation futura.

Determinismo: l'rng di default è seedato dal tick iniziale, così l'evoluzione
è riproducibile (coerente con la filosofia di tracciabilità). I test passano
un rng proprio o forzano `move_probability`.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.simulation import event_system as ev
from engine.simulation import faction_engine
from engine.simulation import event_generator
from engine.simulation import combat
from engine.simulation import cultivation

_DIR_IT = {"north": "nord", "south": "sud", "east": "est", "west": "ovest"}

# Le fazioni evolvono lentamente: drift ogni N tick (non a ogni tick).
FACTION_DRIFT_INTERVAL = 24

# La fauna selvaggia si ripopola con cadenza (≈ un giorno di gioco).
WILD_REPLENISH_INTERVAL = 24


def compute_active_scope(conn: sqlite3.Connection, location_id: int) -> set[int]:
    """Location osservatore + adiacenti."""
    scope = {location_id}
    scope.update(entities.get_exits(conn, location_id).values())
    return scope


def _active_npcs(conn: sqlite3.Connection, scope: set[int]) -> list[entities.NPC]:
    if not scope:
        return []
    placeholders = ",".join("?" * len(scope))
    rows = conn.execute(
        f"SELECT id, name, location_id, status, description, archetype FROM npcs "
        f"WHERE status='alive' AND location_id IN ({placeholders}) ORDER BY id;",
        tuple(scope),
    ).fetchall()
    return [entities._npc_from_row(r) for r in rows]


def _move_probability(traits: dict[str, int]) -> float:
    base = 0.30
    if traits.get("ambition", 50) > 60 or traits.get("courage", 50) > 60:
        base += 0.20
    if traits.get("ambition", 50) < 35 and traits.get("courage", 50) < 45:
        base -= 0.15
    return max(0.0, min(1.0, base))


def simulate_tick(conn: sqlite3.Connection, tick_no: int, scope: set[int],
                  observer_location_id: int | None, rng: random.Random,
                  observations: list[str],
                  move_probability: float | None = None) -> tuple[int, int]:
    """Simula un singolo tick per gli NPC attivi. Ritorna (events, npcs_acted)."""
    npcs = _active_npcs(conn, scope)
    events = 0
    # gli invasori legati a un evento mondiale presidiano il luogo: non vagano
    pinned = {r["id"] for r in conn.execute(
        "SELECT id FROM npcs WHERE event_id IS NOT NULL AND status='alive';")}

    for npc in npcs:
        # tutti gli NPC attivi sono "simulati" a questo tick
        conn.execute(
            "UPDATE npcs SET last_active_tick=? WHERE id=?;", (tick_no, npc.id)
        )
        if npc.id in pinned:
            continue  # invasore: resta a presidiare il luogo dell'evento

        traits = entities.get_npc_traits(conn, npc.id)
        p_move = move_probability if move_probability is not None else _move_probability(traits)
        if rng.random() >= p_move:
            continue  # resta fermo

        exits = entities.get_exits_detailed(conn, npc.location_id)
        if not exits:
            continue
        choice = rng.choice(exits)
        from_loc, to_loc, direction = npc.location_id, choice["dest_id"], choice["direction"]

        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (to_loc, npc.id))

        visible = observer_location_id in (from_loc, to_loc)
        ev.log_event(
            conn,
            event_type="npc_move",
            tick=tick_no,
            location_id=from_loc,
            title=f"{npc.name} si sposta",
            summary=f"{npc.name} si è spostato verso {_DIR_IT.get(direction, direction)}.",
            participants=[ev.Participant("npc", npc.id, "initiator")],
            consequences=[ev.Consequence(
                target_type="npc", target_id=npc.id,
                consequence_type="location_change",
                description=f"location {from_loc} -> {to_loc}",
                visibility="public" if visible else "hidden",
                resolve_tick=tick_no,
            )],
        )
        events += 1

        # osservazioni per il giocatore
        if observer_location_id is not None:
            if to_loc == observer_location_id:
                observations.append(f"{npc.name} arriva da {_dir_from(conn, to_loc, from_loc)}.")
            elif from_loc == observer_location_id:
                observations.append(f"{npc.name} si allontana verso {_DIR_IT.get(direction, direction)}.")

    return events, len(npcs)


def _dir_from(conn: sqlite3.Connection, here: int, origin: int) -> str:
    """Direzione da cui si arriva a `here` provenendo da `origin` (per le osservazioni)."""
    for ex in entities.get_exits_detailed(conn, here):
        if ex["dest_id"] == origin:
            return _DIR_IT.get(ex["direction"], ex["direction"])
    return "lontano"


def advance(conn: sqlite3.Connection, n: int, player_id: int = 1,
            rng: random.Random | None = None,
            move_probability: float | None = None) -> list[str]:
    """
    Avanza il mondo di n tick eseguendo la simulazione nello scope attivo.
    Ritorna le osservazioni visibili al giocatore durante la finestra.
    """
    observations: list[str] = []
    if n <= 0:
        return observations

    player = entities.get_player(conn, player_id)
    observer_loc = player.location_id if player else None
    scope = compute_active_scope(conn, observer_loc) if observer_loc else set()

    if rng is None:
        rng = random.Random(tick_mod.get_tick(conn))

    def on_tick(c: sqlite3.Connection, tick_no: int) -> tuple[int, int]:
        events, acted = simulate_tick(c, tick_no, scope, observer_loc, rng,
                                      observations, move_probability)
        # vita sociale: incontri / scontri tra NPC co-locati nello scope
        events += event_generator.resolve_encounters(
            c, tick_no, scope, rng, observer_loc, observations)
        # minaccia autonoma verso il giocatore (se si è fatto nemici)
        events += event_generator.resolve_player_threats(
            c, tick_no, scope, rng, player, observer_loc, observations)
        # pressione karmica: un karma molto negativo attira ostilità
        from engine.systems import karma
        events += karma.karmic_pressure(
            c, tick_no, rng, player, scope, observer_loc, observations)
        # eventi di setta programmati (sfide di classifica, tornei mensili)
        from engine.systems import sect_life
        events += sect_life.resolve_sect_events(
            c, tick_no, rng, player, observer_loc, observations)
        # criminali: ogni tanto seminano il terrore (li tiene salienti)
        from engine.systems import bounties
        events += bounties.outlaw_crime_tick(
            c, tick_no, rng, player, scope, observer_loc, observations)
        # eventi mondiali: invasioni (comparsa a cadenza + risoluzione scadute)
        from engine.systems import world_events
        events += world_events.tick(c, tick_no, rng, player, observations)
        # fazioni (cadenza)
        if tick_no % FACTION_DRIFT_INTERVAL == 0:
            events += faction_engine.faction_drift(
                c, tick_no, rng, observer_loc, observations)
        # fauna selvaggia: ripopola le zone pericolose (cadenza), così
        # l'assorbitore ha sempre prede da cacciare fuori dalla setta.
        if tick_no % WILD_REPLENISH_INTERVAL == 0:
            from engine.generators import creature_gen
            creature_gen.replenish_wild(c, rng)
        # coltivazione passiva degli NPC attivi
        events += cultivation.npc_cultivation_pass(
            c, tick_no, scope, rng, observer_loc, observations)
        # conseguenze differite mature + guarigione ferite
        events += event_generator.resolve_due_consequences(
            c, tick_no, rng, observer_loc, observations)
        combat.heal_due_injuries(c, tick_no)
        return events, acted

    tick_mod.advance_tick(conn, n, on_tick=on_tick)
    return observations
