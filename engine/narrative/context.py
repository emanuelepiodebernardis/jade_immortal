"""
NarrativeContext builder (Fase 9).

Raccoglie SOLO FATTI OSSERVABILI dalla simulazione per una scena. Niente framing
emotivo, niente interpretazioni: è il "Factual Lock". L'LLM riceve questi fatti e
li rende in prosa, ma non può inferire cause o emozioni non presenti qui.

Il contesto è limitato (contro il context drift): poche memorie attive, pochi NPC,
pochi eventi locali recenti.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from engine.core import entities
from engine.systems import relations, memory
from engine.simulation import cultivation, combat

MEMORY_IN_CONTEXT = 4
LOCAL_EVENTS_IN_CONTEXT = 5
LOCAL_EVENT_WINDOW = 40


@dataclass
class NpcFact:
    name: str
    archetype: str | None
    realm: str
    disposition: str


@dataclass
class NarrativeContext:
    tick: int
    location_name: str
    location_type: str | None
    danger: int
    location_desc: str | None
    owner_faction: str | None
    player_name: str
    player_realm: str
    player_wounds: int
    present_npcs: list[NpcFact] = field(default_factory=list)
    recent_local_events: list[str] = field(default_factory=list)
    active_memories: list[str] = field(default_factory=list)

    def allowed_names(self) -> set[str]:
        names = {self.location_name, self.player_name, "Tu", "te"}
        if self.owner_faction:
            names.add(self.owner_faction)
        for n in self.present_npcs:
            names.add(n.name)
        return names


def build_scene_context(conn: sqlite3.Connection, player: entities.Player,
                        tick: int) -> NarrativeContext:
    loc = entities.get_location(conn, player.location_id)
    owner = entities.location_owner_name(conn, player.location_id)

    npcs = []
    for n in entities.npcs_in_location(conn, player.location_id):
        npcs.append(NpcFact(
            name=n.name,
            archetype=n.archetype,
            realm=cultivation.realm_name(conn, "npc", n.id),
            disposition=relations.get_disposition(conn, n.id).relationship_type,
        ))

    # eventi pubblici recenti in questa location (fatti, non interpretazioni)
    rows = conn.execute(
        "SELECT DISTINCT e.summary FROM events e "
        "JOIN consequences c ON c.event_id=e.id AND c.visibility='public' "
        "WHERE e.location_id=? AND e.tick>=? AND e.event_type<>'npc_move' "
        "ORDER BY e.tick DESC LIMIT ?;",
        (player.location_id, max(0, tick - LOCAL_EVENT_WINDOW), LOCAL_EVENTS_IN_CONTEXT),
    ).fetchall()
    recent_local = [r["summary"] for r in rows]

    mems = [m.summary for m in
            memory.active_memory(conn, "player", player.id, tick, budget=MEMORY_IN_CONTEXT)]

    return NarrativeContext(
        tick=tick,
        location_name=loc.name if loc else "ignoto",
        location_type=loc.location_type if loc else None,
        danger=loc.danger_level if loc else 1,
        location_desc=loc.description if loc else None,
        owner_faction=owner,
        player_name=player.name,
        player_realm=cultivation.realm_name(conn, "player", player.id),
        player_wounds=len(combat.active_injuries(conn, "player", player.id)),
        present_npcs=npcs,
        recent_local_events=recent_local,
        active_memories=mems,
    )
