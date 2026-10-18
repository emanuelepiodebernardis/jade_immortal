"""
IL DANTIAN (Aggiornamento 65) — le tecniche come pezzi da incastrare in uno spazio limitato.

Lo spunto viene da Destiny of Immortal (造化仙缘), dove il dantian è una griglia e le tecniche sono
pezzi di forme diverse, come a Tetris: lo spazio è poco, e gli incastri giusti danno bonus.

Qui il dantian è una RISONANZA che si aggiunge alle tecniche (che restano tutte usabili in battaglia):
  · la griglia cresce col regno: 3×3, poi 4×4 dal 3° regno, 5×5 dal 6°, 6×6 dal 9°, 7×7 dal 12°…
  · ogni tecnica occupa un pezzo: le più forti sono più grandi (1, 2, 3 o 4 caselle);
  · ogni casella occupata dà risonanza; due pezzi che si toccano e condividono un Dao danno di più;
    due pezzi nel ciclo che si nutre (Legno→Fuoco→Terra→Metallo→Acqua) ancora un po';
  · la risonanza diventa attacco e coltivazione (con un tetto: passa dal bilancio della potenza).

  dantian                       la griglia, i pezzi, la risonanza
  dantian auto                  sistema da solo il dantian nel modo migliore che trova
  dantian metti <n> <r> <c> [ruota]   metti la tecnica n (dell'elenco) con l'angolo in riga r, colonna c
  dantian togli <n>             togli il pezzo n
  dantian svuota                svuoti il dantian
"""

from __future__ import annotations

from engine.systems import state

KEY = "dantian"
CYCLE = ["legno", "fuoco", "terra", "metallo", "acqua"]
SHAPES = {1: [(0, 0)], 2: [(0, 0), (0, 1)], 3: [(0, 0), (1, 0), (1, 1)], 4: [(0, 0), (0, 1), (1, 0), (1, 1)]}
CELL_ATK, TOUCH_SAME, TOUCH_CYCLE = 0.012, 0.02, 0.012
ATK_CAP, CULT_PER_CELL, CULT_CAP = 0.45, 0.004, 0.15
EMO = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬜", "🔶", "🔷", "🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]


def size(conn, pid: int = 1) -> int:
    from engine.simulation import cultivation
    t = cultivation.realm_tier(conn, "player", pid) or 1
    return 3 if t < 3 else 4 + (t - 3) // 3


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"pieces": []}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _techs(conn, pid: int) -> list[dict]:
    from engine.systems import technique_forge as tf
    ts = tf.techniques(conn, pid)
    out = []
    for m in ts:
        p = tf._power(m)
        n = 1 if p < 1.8 else 2 if p < 2.8 else 3 if p < 4.5 else 4
        out.append({"key": m.get("key") or m["name"], "name": m["name"], "tags": list(m.get("tags") or []), "n": n,
                    "power": p})
    return out


def _rotate(cells: list, k: int) -> list:
    for _ in range(k % 4):
        cells = [(c, -r) for r, c in cells]
    mr, mc = min(r for r, _c in cells), min(c for _r, c in cells)
    return sorted((r - mr, c - mc) for r, c in cells)


def _occupied(pieces: list[dict]) -> dict:
    occ = {}
    for i, p in enumerate(pieces):
        for r, c in p["cells"]:
            occ[(r, c)] = i
    return occ


def _fits(cells, occ, n) -> bool:
    return all(0 <= r < n and 0 <= c < n and (r, c) not in occ for r, c in cells)


def _cycle_pair(a: list, b: list) -> bool:
    for x in a:
        for y in b:
            if x in CYCLE and y in CYCLE and (CYCLE.index(x) + 1) % 5 == CYCLE.index(y):
                return True
    return False


def score(pieces: list[dict]) -> dict:
    occ = _occupied(pieces)
    cells = len(occ)
    same = cyc = 0
    seen = set()
    for (r, c), i in occ.items():
        for dr, dc in ((1, 0), (0, 1)):
            j = occ.get((r + dr, c + dc))
            if j is None or j == i or (min(i, j), max(i, j)) in seen:
                continue
            seen.add((min(i, j), max(i, j)))
            a, b = pieces[i]["tags"], pieces[j]["tags"]
            if set(a) & set(b):
                same += 1
            elif _cycle_pair(a, b) or _cycle_pair(b, a):
                cyc += 1
    atk = min(ATK_CAP, CELL_ATK * cells + TOUCH_SAME * same + TOUCH_CYCLE * cyc)
    cult = min(CULT_CAP, CULT_PER_CELL * cells + 0.005 * same)
    return {"cells": cells, "same": same, "cycle": cyc, "atk": round(atk, 4), "cult": round(cult, 4)}


def place(conn, pid: int, idx: int, r: int, c: int, rot: int = 0) -> str:
    ts = _techs(conn, pid)
    if not (1 <= idx <= len(ts)):
        return "Nessuna tecnica con quel numero. ('dantian' per l'elenco)"
    t = ts[idx - 1]
    d = get(conn)
    d["pieces"] = [p for p in d["pieces"] if p["key"] != t["key"]]
    n = size(conn, pid)
    cells = [(r - 1 + dr, c - 1 + dc) for dr, dc in _rotate(SHAPES[t["n"]], rot)]
    if not _fits(cells, _occupied(d["pieces"]), n):
        return f"«{t['name']}» non ci sta lì (dantian {n}×{n})."
    d["pieces"].append({"key": t["key"], "name": t["name"], "tags": t["tags"], "cells": [list(x) for x in cells]})
    _save(conn, d)
    return f"Fai scendere «{t['name']}» nel dantian. " + line(conn, pid)


def remove(conn, pid: int, idx: int) -> str:
    d = get(conn)
    if not (1 <= idx <= len(d["pieces"])):
        return "Nessun pezzo con quel numero."
    p = d["pieces"].pop(idx - 1)
    _save(conn, d)
    return f"Togli «{p['name']}» dal dantian."


def auto(conn, pid: int) -> str:
    """Un incastro goloso: dalla tecnica più forte, ogni pezzo nel posto (e verso) che fa crescere di più."""
    n = size(conn, pid)
    ts = sorted(_techs(conn, pid), key=lambda t: (-t["n"], -t["power"]))
    pieces: list[dict] = []
    for t in ts:
        occ = _occupied(pieces)
        best, best_s = None, None
        for rot in range(4):
            shape = _rotate(SHAPES[t["n"]], rot)
            for r in range(n):
                for c in range(n):
                    cells = [(r + dr, c + dc) for dr, dc in shape]
                    if not _fits(cells, occ, n):
                        continue
                    cand = pieces + [{"key": t["key"], "name": t["name"], "tags": t["tags"], "cells": cells}]
                    s = score(cand)
                    v = s["atk"] + s["cult"] + 0.001 * t["power"]
                    if best_s is None or v > best_s:
                        best, best_s = cand[-1], v
        if best:
            pieces.append(best)
    _save(conn, {"pieces": [{**p, "cells": [list(x) for x in p["cells"]]} for p in pieces]})
    return f"Il Qi trova da solo la sua strada: {len(pieces)} tecniche nel dantian. " + line(conn, pid)


def _pieces(conn) -> list[dict]:
    return [{**p, "cells": [tuple(x) for x in p["cells"]]} for p in get(conn)["pieces"]]


def current(conn) -> dict:
    return score(_pieces(conn))


def line(conn, pid: int = 1) -> str:
    s = current(conn)
    return (f"Risonanza: {s['cells']} caselle, {s['same']} incastri dello stesso Dao, {s['cycle']} nel ciclo — "
            f"attacco +{s['atk'] * 100:.1f}%, coltivazione +{s['cult'] * 100:.1f}%.")


def grid_lines(conn, pid: int = 1) -> list[str]:
    n = size(conn, pid)
    occ = _occupied(_pieces(conn))
    rows = []
    for r in range(n):
        rows.append("".join(EMO[occ[(r, c)] % len(EMO)] if (r, c) in occ else "⬛" for c in range(n)))
    return rows


def describe(conn, player) -> str:
    n = size(conn, player.id)
    lines = [f"☯ IL DANTIAN ({n}×{n})"] + ["  " + x for x in grid_lines(conn, player.id)]
    for i, p in enumerate(get(conn)["pieces"], 1):
        lines.append(f"  {EMO[(i - 1) % len(EMO)]} {i}. {p['name']}" + (f" ({', '.join(p['tags'])})" if p["tags"] else ""))
    lines.append("  " + line(conn, player.id))
    lines.append("  Le tue tecniche (dimensione del pezzo):")
    for i, t in enumerate(_techs(conn, player.id), 1):
        lines.append(f"   {i}. {t['name']} — {t['n']} caselle" + (f" · {', '.join(t['tags'])}" if t["tags"] else ""))
    lines.append("  ('dantian auto' per incastrarle da solo; 'dantian metti <n> <riga> <colonna> [ruota]')")
    return "\n".join(lines)


def combat(conn, fx) -> list[str]:
    s = current(conn)
    if s["atk"]:
        fx.p.atk_mult *= 1.0 + s["atk"]
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    s = current(conn)
    return (1.0 + s["cult"], "la risonanza del dantian") if s["cult"] else (1.0, "")


def menu_section(conn, player):
    from engine.systems.menus import act, section
    n = size(conn, player.id)
    s = current(conn)
    lines = grid_lines(conn, player.id) + [
        f"Risonanza: attacco +{s['atk'] * 100:.1f}%, coltivazione +{s['cult'] * 100:.1f}% "
        f"({s['cells']}/{n * n} caselle, {s['same']} incastri dello stesso Dao, {s['cycle']} nel ciclo)."]
    lines += [f"{EMO[(i - 1) % len(EMO)]} {p['name']}" for i, p in enumerate(get(conn)["pieces"], 1)][:8]
    return section(f"Il dantian ({n}×{n})", lines, [act("Incastra da solo nel modo migliore", "dantian auto", main=True),
                                                  act("Svuota", "dantian svuota", bool(get(conn)["pieces"]), "è vuoto"),
                                                  act("Dettagli e posizioni", "dantian")], icon="☯")


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub == "auto":
        return auto(conn, player.id)
    if sub in ("svuota", "reset"):
        _save(conn, {"pieces": []})
        return "Svuoti il dantian: il Qi torna a scorrere libero."
    if sub in ("togli", "rimuovi") and len(p) > 1 and p[1].isdigit():
        return remove(conn, player.id, int(p[1]))
    if sub in ("metti", "posa") and len(p) >= 4 and all(x.isdigit() for x in p[1:4]):
        rot = 1 if len(p) > 4 and p[4].startswith("ruot") else 0
        return place(conn, player.id, int(p[1]), int(p[2]), int(p[3]), rot)
    return describe(conn, player)
