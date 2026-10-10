"""
Interprete di intenti in linguaggio naturale (Fase 9.1 — layer ibrido).

L'LLM NON decide nulla della simulazione: traduce soltanto la frase del giocatore
in UNO dei comandi permessi (intent classification). Il motore deterministico
esegue e decide l'esito. Coerente con i principi: la verità resta nel DB.

Graceful: se Ollama non è attivo, `translate` ritorna None e restano i comandi fissi.
"""

from __future__ import annotations

import json
import re
import sqlite3

from engine.core import entities
from engine.narrative import llm

from engine.cli import help_text

# verbi-comando riconosciuti dal motore (prima parola): derivati dall'aiuto, così il
# traduttore conosce SEMPRE tutti i comandi (prima ne conosceva solo una parte).
KNOWN_COMMANDS = help_text.command_words() | {
    "meditate", "rest", "news", "recall", "scene", "story", "tale", "exit",
}

_COMMAND_LIST = "\n".join("- " + ln for ln in help_text.command_lines()
                          if not ln.startswith("<"))

SYSTEM_PROMPT = f"""Sei un interprete di comandi per un gioco testuale xianxia.
Converti la frase del giocatore in UN SOLO comando tra quelli permessi.

Comandi permessi (comando, argomento — significato):
{_COMMAND_LIST}

REGOLE:
- Scegli il nome del personaggio dalla lista dei presenti, se la frase si riferisce a qualcuno.
- Le direzioni vanno sempre in inglese: north, south, east, west.
- Se la frase non corrisponde a nessun comando, usa "command": "help".
- Rispondi SOLO con un oggetto JSON, senza testo aggiuntivo:
  {{"command": "<comando>", "arg": "<argomento o stringa vuota>"}}
"""


def _scene_hint(conn: sqlite3.Connection, player: entities.Player) -> tuple[list[str], list[str]]:
    npcs = [n.name for n in entities.npcs_in_location(conn, player.location_id)]
    exits = sorted(entities.get_exits(conn, player.location_id).keys())
    return npcs, exits


def build_command_from_llm_text(text: str) -> str | None:
    """Estrae e valida il comando dal JSON prodotto dall'LLM. Pura, testabile."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    cmd = str(data.get("command", "")).strip().lower()
    arg = str(data.get("arg", "")).strip()
    if cmd not in KNOWN_COMMANDS:
        return None
    return f"{cmd} {arg}".strip()


def translate(conn: sqlite3.Connection, player: entities.Player, raw: str) -> str | None:
    """Traduce una frase libera in un comando del motore. None se LLM non disponibile."""
    if not llm.is_enabled():
        return None
    npcs, exits = _scene_hint(conn, player)
    prompt = (
        f'Frase del giocatore: "{raw}"\n'
        f"Personaggi presenti: {', '.join(npcs) if npcs else 'nessuno'}\n"
        f"Uscite disponibili: {', '.join(exits) if exits else 'nessuna'}\n"
        "Converti in un comando JSON."
    )
    out = llm.generate(SYSTEM_PROMPT, prompt)
    if not out:
        return None
    return build_command_from_llm_text(out)
