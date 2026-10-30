"""Rigenera docs/MAPPA_DEL_CODICE.md: per ogni modulo di engine/ la prima riga della sua documentazione.

    python strumenti/mappa_codice.py
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
INTRO = """# Mappa del codice

Generata da `strumenti/mappa_codice.py`: per ogni modulo la prima riga della sua documentazione.
Rigenerala dopo un aggiornamento grande (`python strumenti/mappa_codice.py`).

Come è organizzato il gioco:
- `engine/core` — le entità e il tempo (tick, giocatore, personaggi, luoghi).
- `engine/simulation` — il mondo che vive da solo: coltivazione, combattimento, eventi.
- `engine/systems` — un modulo per sistema di gioco (setta, Dao, sangue, duello, grotte…). Ogni sistema
  tiene il suo stato in `state` (JSON) o in tabelle sue, ed espone `command`, `menu_build`, `daily` quando serve.
- `engine/cli` — i comandi testuali (`loop.dispatch` e `story_cmds.handle`).
- `engine/web` — la dashboard: `game.py` (dati), `server.py` (API), `static/` (pagina).
- `engine/narrative` — i testi variati e il modello linguistico opzionale.
"""


def main() -> None:
    groups: dict[str, list] = {}
    for f in sorted((ROOT / "engine").rglob("*.py")):
        if "__pycache__" in f.parts or f.name == "__init__.py":
            continue
        src = f.read_text(encoding="utf-8")
        try:
            doc = ast.get_docstring(ast.parse(src)) or ""
        except SyntaxError:
            doc = ""
        first = next((ln.strip() for ln in doc.splitlines() if ln.strip()), "").replace("|", "/")
        groups.setdefault(f.parent.relative_to(ROOT).as_posix(), []).append((f.name, len(src.splitlines()), first[:150]))
    out = [INTRO]
    for g in sorted(groups):
        out += [f"## {g}", "", "| file | righe | cosa fa |", "|---|---:|---|"]
        out += [f"| `{n}` | {k} | {d} |" for n, k, d in groups[g]]
        out.append("")
    (ROOT / "docs" / "MAPPA_DEL_CODICE.md").write_text("\n".join(out), encoding="utf-8")
    print("docs/MAPPA_DEL_CODICE.md aggiornata")


if __name__ == "__main__":
    main()
