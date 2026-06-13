"""
Prompt per il narrative engine (Fase 9).

Il system prompt impone il Factual Lock: l'LLM è un RENDERIZZATORE, non un
interprete. Può abbellire lo stile, mai inventare fatti, cause o emozioni.
"""

from __future__ import annotations

from engine.narrative.context import NarrativeContext

SYSTEM_PROMPT = """Sei il narratore di un romanzo xianxia/wuxia. Il tuo unico compito è
trasformare in PROSA evocativa i FATTI che ti vengono forniti.

REGOLE FERREE (non violarle mai):
- Usa SOLO i fatti elencati. Non inventare eventi, personaggi, luoghi, oggetti.
- NON attribuire emozioni, intenzioni, motivazioni o pensieri che non siano nei fatti.
- NON collegare tra loro eventi separati con rapporti di causa che non sono dati.
- Descrivi solo ciò che è osservabile nella scena.
- Non aggiungere dialoghi o nomi non presenti.

STILE:
- Terza persona (o seconda persona "tu" se ci si rivolge al protagonista).
- Tono sobrio e immaginifico, atmosfera da mondo di coltivatori.
- Da 2 a 4 frasi. Nessun elenco, nessun titolo.
"""


def build_scene_prompt(ctx: NarrativeContext) -> str:
    lines = ["FATTI DELLA SCENA (rendi in prosa, senza aggiungere nulla):"]
    lines.append(f"- Luogo: {ctx.location_name}"
                 + (f" ({ctx.location_type})" if ctx.location_type else "")
                 + f", livello di pericolo {ctx.danger}.")
    if ctx.location_desc:
        lines.append(f"- Descrizione del luogo: {ctx.location_desc}")
    if ctx.owner_faction:
        lines.append(f"- Il luogo è controllato dalla fazione: {ctx.owner_faction}.")
    lines.append(f"- Protagonista: {ctx.player_name}, regno di coltivazione {ctx.player_realm}"
                 + (f", con {ctx.player_wounds} ferite." if ctx.player_wounds else "."))
    if ctx.present_npcs:
        lines.append("- Presenti nel luogo:")
        for n in ctx.present_npcs:
            lines.append(f"    · {n.name}, {n.archetype or 'figura'}, regno {n.realm}, "
                         f"rapporto col protagonista: {n.disposition}.")
    if ctx.recent_local_events:
        lines.append("- Fatti accaduti di recente qui:")
        for e in ctx.recent_local_events:
            lines.append(f"    · {e}")
    if ctx.active_memories:
        lines.append("- Ricordi che il protagonista porta con sé:")
        for m in ctx.active_memories:
            lines.append(f"    · {m}")
    return "\n".join(lines)
