"""
IL TESTO ESSENZIALE — alleggerisce il diario prima di mostrarlo (dashboard e pilota automatico).

Non inventa e non riscrive nulla: SCEGLIE cosa tenere, in una passata sola.
  · righe identiche ripetute → una sola;
  · elenchi lunghi («Dao: Spada +1, Corpo +1, … ») → i primi 5 e «e altri N»;
  · cinque o più righe consecutive dello stesso tipo (stessa icona e stesse prime parole) → le prime
    tre e «… e altre N simili»;
  · i suggerimenti da terminale («scrivi il numero…») spariscono: nella dashboard ci sono i pulsanti.
"""

from __future__ import annotations

import re

LIST_MAX = 5
RUN_KEEP = 3
_DROP = re.compile(r"^\s*\((scrivi il numero|digita il numero)[^)]*\)\s*$", re.I)
_CHOICE = re.compile(r"^\s*\[\d+\]")
_DECOR = re.compile(r"^[\s=\-–—_*·•~]*$")
_LIST = re.compile(r"^(\s*[^:]{2,40}:\s)(.+?)(\.?)$")


def _shorten_list(line: str) -> str:
    m = _LIST.match(line)
    if not m:
        return line
    items = [x for x in m.group(2).split(", ")]
    if len(items) <= LIST_MAX + 1 or any(len(x) > 40 for x in items):
        return line
    return f"{m.group(1)}{', '.join(items[:LIST_MAX])} e altri {len(items) - LIST_MAX}{m.group(3)}"


def _kind(line: str) -> str:
    s = line.strip()
    if not s or _CHOICE.match(s) or _DECOR.match(s):
        return ""
    words = s.split()
    return " ".join(words[:3]) if len(words) >= 4 else ""


def compact(text: str) -> str:
    if not text:
        return text
    out: list[str] = []
    seen: set[str] = set()
    for ln in text.split("\n"):
        if _DROP.match(ln):
            continue
        key = ln.strip()
        if key and not _DECOR.match(key) and not _CHOICE.match(key):
            if key in seen:
                continue
            seen.add(key)
        out.append(_shorten_list(ln))
    res: list[str] = []
    i = 0
    while i < len(out):
        k = _kind(out[i])
        j = i
        while k and j + 1 < len(out) and _kind(out[j + 1]) == k:
            j += 1
        run = j - i + 1
        if run >= RUN_KEEP + 2:
            res += out[i:i + RUN_KEEP]
            indent = out[i][:len(out[i]) - len(out[i].lstrip())]
            res.append(f"{indent}… e altre {run - RUN_KEEP} simili.")
        else:
            res += out[i:j + 1]
        i = j + 1
    return "\n".join(res)
