"""
FENG SHUI DELLA DIMORA e GIARDINO SPIRITUALE (Aggiornamento 65).

FENG SHUI — lo spunto viene da Amazing Cultivation Simulator, dove le stanze della setta vanno
bilanciate secondo i cinque elementi. Qui ogni ala della grotta-dimora ha il suo elemento:
  Legno = Campo di Erbe · Fuoco = Stanza dell'Alchimia · Terra = Formazione Difensiva
  Metallo = Formazione di Raccolta del Qi · Acqua = Stanza del Ritiro
Se le cinque ali sono in ARMONIA (livelli vicini tra loro), la casa respira: coltivazione a casa fino
a +20% e un raccolto più ricco. Se un elemento domina troppo, il Qi ristagna (−5%), ma la sua ala
rende di più.

GIARDINO SPIRITUALE — lo spunto viene da Ascend From Nine Mountains e Cultivation Core Incremental:
un orto a riquadri, uno per livello del Campo di Erbe (fino a 12). Ogni riquadro cresce da solo
(🌱 → 🌿 → 🌸) e, se vuoi, si ripianta da solo dopo il raccolto.
  Erba del Qi      2 giorni   erbe spirituali
  Loto di Giada    5 giorni   una pillola
  Radice di Drago  9 giorni   un'essenza
  Fiore del Vuoto 14 giorni   un tesoro

  fengshui                    l'armonia della dimora
  orto                        il giardino
  orto pianta <tipo> [n]      semini n riquadri liberi (erba, loto, radice, vuoto)
  orto raccogli               raccogli ciò che è maturo (devi essere a casa)
  orto auto                   ripianta da solo: sì / no
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

ELEMENT = {"erbe": "legno", "alchimia": "fuoco", "difesa": "terra", "qi": "metallo", "ritiro": "acqua"}
ICON = {"legno": "🌳", "fuoco": "🔥", "terra": "⛰", "metallo": "⚙", "acqua": "💧"}
PLANTS = {"erba": ("Erba del Qi", 2), "loto": ("Loto di Giada", 5), "radice": ("Radice di Drago", 9),
          "vuoto": ("Fiore del Vuoto", 14)}
GKEY = "spirit_garden"
MAX_PLOTS = 12


def _levels(conn, pid: int) -> dict:
    from engine.systems import cave_abode
    return {w: cave_abode.level(conn, pid, w) for w in ELEMENT}


def harmony(conn, pid: int = 1) -> dict:
    lv = _levels(conn, pid)
    if not any(lv.values()):
        return {"score": 0.0, "label": "nessuna dimora", "dominant": None, "mult": 1.0}
    hi, lo = max(lv.values()), min(lv.values())
    if lo == 0:
        sc = 0.0
    else:
        sc = max(0.0, 1.0 - (hi - lo) / (hi + 1))
    dom = max(lv, key=lambda w: lv[w]) if hi - lo >= 4 else None
    mult = 1.0 + 0.2 * sc - (0.05 if dom else 0.0)
    label = ("armonia perfetta" if sc >= 0.9 else "armonia" if sc >= 0.6 else "squilibrio lieve" if sc >= 0.3
             else "Qi stagnante" if dom else "elementi incompleti")
    return {"score": round(sc, 2), "label": label, "dominant": ELEMENT[dom] if dom else None, "mult": round(mult, 3),
            "levels": lv}


def cultivation_mult(conn, pid: int, location_id) -> tuple[float, str]:
    from engine.systems import cave_abode
    if not cave_abode.is_home(conn, pid, location_id):
        return 1.0, ""
    h = harmony(conn, pid)
    return (h["mult"], f"il feng shui della dimora ({h['label']})") if h["mult"] != 1.0 else (1.0, "")


def describe(conn, player) -> str:
    h = harmony(conn, player.id)
    if h["label"] == "nessuna dimora":
        return "Non hai una dimora: il feng shui riguarda le ali della tua grotta-dimora."
    lv = h["levels"]
    lines = ["☯ FENG SHUI DELLA DIMORA — " + h["label"],
             "  " + " · ".join(f"{ICON[ELEMENT[w]]} {ELEMENT[w]} {lv[w]}" for w in ELEMENT),
             f"  Coltivazione a casa ×{h['mult']:.2f}." + (f" Domina il {h['dominant']}: il Qi ristagna." if h["dominant"] else ""),
             "  Tieni le cinque ali a livelli vicini tra loro per l'armonia."]
    return "\n".join(lines)


# ---------------------------------------------------------------- giardino

def garden(conn) -> dict:
    return state.get_json(conn, GKEY, None) or {"plots": [], "auto": True}


def _gsave(conn, g: dict) -> None:
    state.set_json(conn, GKEY, g)


def plots_max(conn, pid: int) -> int:
    from engine.systems import cave_abode
    return min(MAX_PLOTS, cave_abode.level(conn, pid, "erbe"))


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def plant(conn, player, arg: str) -> str:
    p = (arg or "").split()
    kind = p[0].lower() if p else "erba"
    kind = next((k for k in PLANTS if kind.startswith(k[:3])), None)
    if not kind:
        return "Cosa vuoi piantare? " + ", ".join(f"{k} ({v[0]}, {v[1]} giorni)" for k, v in PLANTS.items())
    mx = plots_max(conn, player.id)
    if not mx:
        return "Serve il Campo di Erbe Spirituali della dimora (almeno livello 1)."
    g = garden(conn)
    free = mx - len(g["plots"])
    n = min(free, int(p[1]) if len(p) > 1 and p[1].isdigit() else free)
    if n <= 0:
        return "Non ci sono riquadri liberi."
    for _ in range(n):
        g["plots"].append({"kind": kind, "day": _day(conn)})
    _gsave(conn, g)
    return f"Semini {n} riquadri di {PLANTS[kind][0]}: matureranno in {PLANTS[kind][1]} giorni."


def _stage(conn, pl: dict) -> str:
    d = _day(conn) - pl["day"]
    need = PLANTS[pl["kind"]][1]
    return "🌸" if d >= need else "🌿" if d >= need / 2 else "🌱"


def harvest(conn, player, rng=None) -> str:
    from engine.systems import cave_abode, professions, rewards
    if not cave_abode.is_home(conn, player.id, player.location_id):
        return "Devi essere nella tua dimora per raccogliere dall'orto."
    g = garden(conn)
    rng = rng or random.Random(tick_mod.get_tick(conn) + 77)
    h = harmony(conn, player.id)
    bonus = 1.0 + 0.5 * h["score"] + (0.3 if h["dominant"] == "legno" else 0.0)
    out, keep, got = [], [], 0
    for pl in g["plots"]:
        if _stage(conn, pl) != "🌸":
            keep.append(pl)
            continue
        got += 1
        if pl["kind"] == "erba":
            professions.give(conn, player.id, "erbe", max(1, int(3 * bonus)))
        else:
            kind = {"loto": "pillola", "radice": "essenza", "vuoto": "tesoro"}[pl["kind"]]
            out += rewards.grant(conn, rng, player, rank=3 if pl["kind"] != "vuoto" else 2, kinds=[kind], n=1, stones=False)
        if g.get("auto", True):
            keep.append({"kind": pl["kind"], "day": _day(conn)})
    g["plots"] = keep
    _gsave(conn, g)
    if not got:
        return "Nell'orto non c'è ancora nulla di maturo."
    return f"Raccogli {got} riquadri maturi" + (" e li ripianti" if g.get("auto", True) else "") + ".\n" + "\n".join(out)


def ready_count(conn) -> int:
    return sum(1 for pl in garden(conn)["plots"] if _stage(conn, pl) == "🌸")


def garden_lines(conn, pid: int) -> list[str]:
    mx = plots_max(conn, pid)
    g = garden(conn)
    row = [_stage(conn, pl) for pl in g["plots"]] + ["▫"] * max(0, mx - len(g["plots"]))
    return [" ".join(row[i:i + 6]) for i in range(0, len(row), 6)] or ["(nessun riquadro: potenzia il Campo di Erbe)"]


def menu_sections(conn, player) -> list:
    from engine.systems.menus import act, section
    h = harmony(conn, player.id)
    secs = []
    if h["label"] != "nessuna dimora":
        lv = h["levels"]
        secs.append(section("Feng shui — " + h["label"], [
            " · ".join(f"{ICON[ELEMENT[w]]} {lv[w]}" for w in ELEMENT),
            f"Coltivazione a casa ×{h['mult']:.2f}." + (f" Domina il {h['dominant']}." if h["dominant"] else "")
            + " Tieni le cinque ali a livelli vicini."], icon="☯"))
    mx = plots_max(conn, player.id)
    if mx:
        g = garden(conn)
        free = mx - len(g["plots"])
        secs.append(section(f"Giardino spirituale ({len(g['plots'])}/{mx})", garden_lines(conn, player.id) + [
            "🌱 germoglio · 🌿 cresce · 🌸 maturo · ▫ libero" + (" · si ripianta da solo" if g.get("auto", True) else "")],
            [act(f"Raccogli ({ready_count(conn)})", "orto raccogli", ready_count(conn) > 0, "niente di maturo", main=True),
             act("Semina Erba del Qi", "orto pianta erba", free > 0, "nessun riquadro libero"),
             act("Semina Loto di Giada", "orto pianta loto", free > 0, "nessun riquadro libero"),
             act("Semina Radice di Drago", "orto pianta radice", free > 0, "nessun riquadro libero"),
             act("Semina Fiore del Vuoto", "orto pianta vuoto", free > 0, "nessun riquadro libero"),
             act("Ripianta da solo: " + ("sì" if g.get("auto", True) else "no"), "orto auto")], icon="🌸"))
    return secs


def command(conn, player, cmd: str, arg: str) -> str:
    if cmd == "fengshui":
        return describe(conn, player)
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub in ("pianta", "semina"):
        return plant(conn, player, " ".join(p[1:]))
    if sub in ("raccogli", "raccolta"):
        return harvest(conn, player)
    if sub == "auto":
        g = garden(conn)
        g["auto"] = not g.get("auto", True)
        _gsave(conn, g)
        return "Il giardino si ripianta da solo." if g["auto"] else "Il giardino non si ripianta più da solo."
    from engine.systems import menus
    m = menus.menu("orto", "🌸 IL GIARDINO E IL FENG SHUI", [], menu_sections(conn, player))
    return menus.render(conn, m)
