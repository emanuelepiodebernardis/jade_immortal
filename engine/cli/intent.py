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

# verbi-comando riconosciuti dal motore (prima parola)
KNOWN_COMMANDS = {
    "move", "look", "map", "wait", "rest", "examine", "greet", "attack",
    "cultivate", "meditate", "breakthrough", "factions", "faction", "log",
    "news", "memories", "recall", "narrate", "scene", "story", "chronicle",
    "tale", "status", "where", "help", "quit", "exit",
}

SYSTEM_PROMPT = """Sei un interprete di comandi per un gioco testuale xianxia.
Converti la frase del giocatore in UN SOLO comando tra quelli permessi.

Comandi permessi (e loro argomento):
- move <north|south|east|west>   (spostarsi; usa SEMPRE le direzioni in inglese)
- look | map | where             (osservare il luogo)
- wait                           (far passare il tempo)
- examine <nome>                 (esaminare un personaggio presente)
- greet <nome>                   (salutare un personaggio)
- attack <nome>                  (attaccare un personaggio)
- cultivate                      (meditare/coltivare)
- breakthrough                   (tentare di salire di regno)
- factions | faction <nome>      (informazioni sulle fazioni)
- log | memories                 (cronache e ricordi)
- narrate | chronicle            (rendere la scena/cronaca come prosa)
- status | help                  (stato del personaggio / aiuto)

REGOLE:
- Scegli il nome del personaggio dalla lista dei presenti, se la frase si riferisce a qualcuno.
- Le direzioni vanno sempre in inglese: north, south, east, west.
- Se la frase non corrisponde a nessun comando, usa "command": "help".
- Rispondi SOLO con un oggetto JSON, senza testo aggiuntivo:
  {"command": "<comando>", "arg": "<argomento o stringa vuota>"}
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
