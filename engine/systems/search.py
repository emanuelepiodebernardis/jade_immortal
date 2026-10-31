"""
LA RICERCA GLOBALE e L'ELENCO DEI COMANDI (Aggiornamento 79).

  cerca <parola>      trova tutto ciò che la riguarda: Dao, vie nuove, fusioni, arti e ricette, pagine della guida,
                      comandi, persone qui intorno, oggetti nello zaino
  commands()          l'elenco dei comandi (dalle righe dell'aiuto) per i suggerimenti della barra
  argomenti(conn)     i valori possibili dopo un comando (Dao per 'comprehend', ricette per 'fusione'…)
  did_you_mean(w)     il comando più vicino a una parola sbagliata («fusinoe» → fusione)
"""

from __future__ import annotations

import re
import unicodedata


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


# ---------------------------------------------------------------- i comandi

_CAT = None


def commands() -> list[dict]:
    """[{cmd, args, desc, cat, alias}] da tutte le righe dell'aiuto (più gli alias dei verbi)."""
    global _CAT
    if _CAT is not None:
        return _CAT
    from engine.cli import help_text
    from engine.cli.loop import VERB_ALIAS
    out: dict[str, dict] = {}
    for _k, title, lines in help_text.CATEGORIES:
        for ln in lines:
            if "—" not in ln:
                continue
            head, desc = ln.split("—", 1)
            head = head.strip()
            first = head.split()[0] if head else ""
            if not first or first.startswith("<"):
                continue
            for w in [x.strip() for x in first.split("|")]:
                if not re.fullmatch(r"[a-zà-ù_]+", w):
                    continue
                args = head[len(first):].strip()
                if w in out:
                    continue
                out[w] = {"cmd": w, "args": args, "desc": desc.strip(), "cat": title, "alias": []}
    for a, c in VERB_ALIAS.items():
        if c in out and a not in out:
            out[c]["alias"].append(a)
    _CAT = sorted(out.values(), key=lambda d: d["cmd"])
    return _CAT


def _lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def did_you_mean(word: str) -> str | None:
    w = _plain(word)
    if len(w) < 3:
        return None
    best, bd = None, 3
    for c in commands():
        for name in [c["cmd"]] + c["alias"]:
            d = _lev(w, _plain(name))
            if d < bd:
                best, bd = c["cmd"], d
    return best


def argomenti(conn, pid: int = 1) -> dict[str, list[dict]]:
    from engine.generators import dao_gen
    from engine.systems import dao_laws, professions
    from engine.core import entities
    daos = [{"v": k, "d": n} for k, n, *_r in dao_gen.DAOS]
    fus = [{"v": k, "d": r[1]} for k, r in dao_laws.FUSED.items()]
    arts = [{"v": k, "d": n} for k, n in professions.PROFESSIONS.items()]
    base = [d for d in daos if d["v"] not in dao_laws.FUSED]
    out = {"comprehend": daos, "fusione": fus + base, "obiettivo": fus + base + arts, "arti": arts,
           "ricette": arts, "craft": arts}
    try:
        p = entities.get_player(conn, pid)
        ppl = [{"v": n.name.split()[0], "d": n.name} for n in entities.npcs_in_location(conn, p.location_id)]
        for c in ("attack", "duello", "examine", "greet", "osserva", "bottega", "commissiona", "assisti", "talk"):
            out[c] = ppl
    except Exception:                                    # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- la ricerca

def search(conn, q: str, pid: int = 1, limit: int = 30) -> list[dict]:
    """[{tipo, titolo, testo, cmd}] — prima le corrispondenze nel titolo, poi nel testo."""
    from engine.generators import dao_gen
    from engine.systems import dao_laws, professions, guide
    from engine.core import entities
    t = _plain(q).strip()
    if len(t) < 2:
        return []
    hits: list[tuple[int, dict]] = []

    def add(tipo: str, titolo: str, testo: str, cmd: str | None):
        a, b = _plain(titolo), _plain(testo)
        if t in a:
            hits.append((0 if a.startswith(t) or (" " + t) in a else 1, {"tipo": tipo, "titolo": titolo, "testo": testo,
                                                                          "cmd": cmd}))
        elif t in b:
            hits.append((2, {"tipo": tipo, "titolo": titolo, "testo": testo, "cmd": cmd}))

    for k, n, lvl, d in dao_gen.DAOS:
        row = dao_laws.BY_KEY.get(k)
        if row:
            add("Via nuova", n, f"{d} ✔ {row[10]} · ✘ {row[11]}", f"comprehend {k}")
        elif k in dao_laws.FUSED:
            comps = " + ".join(dao_gen_name(c) for c in dao_laws.FUSED[k][2])
            add("Fusione", n, f"{d} ({comps})", f"obiettivo {k}")
        else:
            add("Dao", n, d, f"comprehend {k}")
    for k, n in professions.PROFESSIONS.items():
        add("Arte", n, professions.ART_DESC.get(k, ""), f"arti {k}")
    for r in professions.RECIPES:
        add("Ricetta", r[2], f"{professions.PROFESSIONS[r[0]]}, livello {r[1]}", f"ricette {r[0]}")
    for key, (title, text) in guide.CODEX.items():
        add("Guida", title, text[:220] + ("…" if len(text) > 220 else ""), f"codex {key}")
    for c in commands():
        add("Comando", c["cmd"] + (" " + c["args"] if c["args"] else ""), c["desc"], c["cmd"])
    try:
        p = entities.get_player(conn, pid)
        for n in entities.npcs_in_location(conn, p.location_id):
            add("Persona qui", n.name, n.description or (n.archetype or ""), f"examine {n.name.split()[0]}")
        from engine.systems import items
        for r in items.player_inventory(conn, pid):
            add("Nello zaino", r["name"], r["description"] or "", f"use {r['name']}")
    except Exception:                                    # noqa: BLE001
        pass
    hits.sort(key=lambda x: x[0])
    seen, out = set(), []
    for _s, h in hits:
        k = (h["tipo"], h["titolo"])
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def dao_gen_name(k: str) -> str:
    from engine.systems.dao_techniques import _dao_label
    return _dao_label(k)


def describe(conn, q: str, pid: int = 1) -> str:
    if not (q or "").strip():
        return "Cerca cosa? 'cerca <parola>' — per esempio 'cerca veleno', 'cerca pillola', 'cerca fusione'."
    res = search(conn, q, pid)
    if not res:
        dm = did_you_mean(q.split()[0])
        return f"Niente su «{q}»." + (f" Forse intendevi '{dm}'?" if dm else "")
    lines = [f"🔎 «{q}» — {len(res)} risultati"]
    for r in res:
        lines.append(f"  [{r['tipo']}] {r['titolo']} — {r['testo'][:140]}" + (f"  → '{r['cmd']}'" if r["cmd"] else ""))
    return "\n".join(lines)
