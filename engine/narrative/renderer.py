"""
Renderer narrativo (Fase 9).

render_scene: prova a usare l'LLM (Ollama); se non disponibile, usa un fallback
deterministico che intesse i fatti in prosa leggibile. In entrambi i casi il
risultato è SOLO testo a schermo: il narrative layer è un SINK PURO (principio P2),
non scrive nulla nella simulazione.

validate_no_foreign_entities: controllo deterministico (Factual Lock leggero) che
l'output non nomini NPC inesistenti nella scena. Essendo un sink puro, un'eventuale
allucinazione è solo cosmetica — ma la segnaliamo.
"""

from __future__ import annotations

import re
import sqlite3

from engine.core import entities
from engine.narrative import context as ctx_mod
from engine.narrative import prompts, llm

_ARTICLE = {"city": "l'insediamento di", "mountain": "le alture di",
            "ruin": "le rovine di", "forbidden_zone": "la landa di"}


def render_scene(conn: sqlite3.Connection, player: entities.Player,
                 tick: int) -> str:
    ctx = ctx_mod.build_scene_context(conn, player, tick)
    cfg = llm.load_llm_config()

    if cfg.get("enabled"):
        system = prompts.SYSTEM_PROMPT
        prompt = prompts.build_scene_prompt(ctx)
        text = llm.generate(system, prompt, cfg)
        if text:
            foreign = validate_no_foreign_entities(conn, text, ctx.allowed_names())
            if foreign:
                text += "\n[nota: riferimenti non verificati: " + ", ".join(foreign) + "]"
            return text
    # fallback deterministico
    return _fallback_render(ctx)


def _fallback_render(ctx: ctx_mod.NarrativeContext) -> str:
    parts = []
    where = f"Ti trovi presso {ctx.location_name}"
    if ctx.location_desc:
        where += f": {ctx.location_desc.rstrip('.').lower()}"
    if ctx.owner_faction:
        where += f". Su queste terre regna {ctx.owner_faction}"
    parts.append(where + ".")

    if ctx.present_npcs:
        who = []
        for n in ctx.present_npcs:
            tag = f"{n.name}, {n.archetype or 'una figura'} del regno {n.realm}"
            who.append(tag)
        if len(who) == 1:
            parts.append(f"Accanto a te indugia {who[0]}.")
        else:
            parts.append("Attorno a te si trovano " + "; ".join(who) + ".")

    if ctx.recent_local_events:
        parts.append("Da poco, in questo luogo: " +
                     "; ".join(e.rstrip('.') for e in ctx.recent_local_events) + ".")

    if ctx.active_memories:
        parts.append("Nella mente ti pesa il ricordo di: " +
                     "; ".join(m.rstrip('.') for m in ctx.active_memories[:2]) + ".")

    if ctx.player_wounds:
        parts.append(f"Le tue {ctx.player_wounds} ferite ti rammentano la fragilità del corpo mortale.")

    return " ".join(parts)


def validate_no_foreign_entities(conn: sqlite3.Connection, text: str,
                                 allowed: set[str]) -> list[str]:
    """Ritorna i nomi di NPC esistenti nel mondo citati nel testo ma NON presenti
    nella scena (potenziali invenzioni dell'LLM). Controllo a parola intera."""
    all_names = [r["name"] for r in conn.execute("SELECT name FROM npcs;")]
    foreign = []
    for name in all_names:
        if name in allowed:
            continue
        if re.search(r"\b" + re.escape(name) + r"\b", text):
            foreign.append(name)
    return foreign


def render_chronicle(conn: sqlite3.Connection, tick: int, limit: int = 6) -> str:
    """Breve passo di cronaca dai fatti significativi del mondo (fallback testuale)."""
    from engine.systems import memory
    events = memory.world_historical(conn, tick, limit=limit)
    if not events:
        return "Nelle cronache non si registra ancora nulla di memorabile."
    seen, uniq = set(), []
    for e in events:
        s = e.summary.rstrip('.')
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    body = "; ".join(uniq)
    return f"Si tramanda che, in tempi recenti: {body}."
