"""
I SIGILLI ANCESTRALI (Aggiornamento 67) — le rune degli antichi, incastonate nel petto.

Lo spunto viene da Immortal Celestial Fate (gli «Ancestral Sigils»). Sei casate di antichi hanno lasciato
ognuna quattro rune: ventiquattro sigilli in tutto. Si trovano tra i tesori (tombe, reami segreti, torre,
torneo, trame, premi): più alto il premio, più facile che ci sia un sigillo.

  · ogni sigillo si INCASTONA in una costellazione nel petto: 2 posti, +1 ogni due regni (fino a 12);
  · un sigillo che hai già si FONDE con il tuo: sale di una STELLA, senza fine (ogni stella vale meno
    della precedente, ma vale sempre);
  · due sigilli della stessa casata danno il loro SET minore, quattro il SET maggiore.

  Drago (attacco) · Fenice (vitalità) · Tigre (critici) · Tartaruga (danni subiti) · Qilin (coltivazione)
  · Serpente Celeste (schivata e comprensione)

  sigilli                  il pannello
  sigilli auto             incastona i migliori (cercando i set)
  sigilli metti <n>        incastoni il sigillo n · sigilli togli <n>
"""

from __future__ import annotations

import math
import random

from engine.systems import state

KEY = "ancestral_sigils"
HOUSES = [
    ("drago", "del Drago", "atk", ["Artiglio", "Scaglia", "Corno", "Perla"]),
    ("fenice", "della Fenice", "vit", ["Piuma", "Cenere", "Fiamma", "Uovo"]),
    ("tigre", "della Tigre", "crit", ["Zanna", "Ruggito", "Striscia", "Occhio"]),
    ("tartaruga", "della Tartaruga Nera", "def", ["Guscio", "Montagna", "Abisso", "Serpe"]),
    ("qilin", "del Qilin", "cult", ["Zoccolo", "Criniera", "Nuvola", "Benedizione"]),
    ("serpente", "del Serpente Celeste", "evade", ["Spira", "Veleno", "Muta", "Stella"]),
]
BASE = {"atk": 0.03, "vit": 0.035, "crit": 0.012, "def": 0.012, "cult": 0.025, "evade": 0.008}
SET2 = {"atk": 0.06, "vit": 0.08, "crit": 0.03, "def": 0.03, "cult": 0.05, "evade": 0.02}
SET4 = {"atk": 0.15, "vit": 0.18, "crit": 0.06, "def": 0.06, "cult": 0.12, "evade": 0.04}
LABEL = {"atk": "attacco", "vit": "vitalità", "crit": "critici", "def": "danni subiti", "cult": "coltivazione",
         "evade": "schivata"}
CAPS = {"crit": 0.3, "def": 0.3, "evade": 0.15}


def sigil_name(k: int) -> str:
    h = HOUSES[k // 4]
    return f"Sigillo {h[3][k % 4]} {h[1]}"


def get(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {}
    d.setdefault("owned", {})
    d.setdefault("eq", [])
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def slots(conn) -> int:
    from engine.simulation import cultivation
    t = cultivation.realm_tier(conn, "player", 1) or 1
    return min(12, 2 + t // 2)


def give(conn, k: int | None = None, rng: random.Random | None = None) -> str:
    """Un sigillo trovato: nuovo, o fuso con quello che hai (+1 stella)."""
    d = get(conn)
    rng = rng or random.Random()
    if k is None:
        k = rng.randrange(len(HOUSES) * 4)
    key = str(k)
    if key in d["owned"]:
        d["owned"][key] += 1
        _save(conn, d)
        return f"✴ {sigil_name(k)}: si fonde con il tuo e sale a {d['owned'][key]} stelle."
    d["owned"][key] = 1
    if len(d["eq"]) < slots(conn):
        d["eq"].append(k)
        _save(conn, d)
        return f"✴ Un sigillo ancestrale: {sigil_name(k)}. Si incastona da solo nel tuo petto."
    _save(conn, d)
    return f"✴ Un sigillo ancestrale: {sigil_name(k)} ('sigilli' per incastonarlo)."


def maybe_drop(conn, rng, rank: int) -> list[str]:
    chance = {1: 0.25, 2: 0.15, 3: 0.08}.get(rank, 0.03)
    return [give(conn, None, rng)] if rng.random() < chance else []


def _value(star: int) -> float:
    return 1.0 + 0.6 * math.log2(max(1, star))


def bonus(conn) -> dict:
    d = get(conn)
    out = {k: 0.0 for k in LABEL}
    count: dict[int, int] = {}
    for k in d["eq"][: slots(conn)]:
        eff = HOUSES[k // 4][2]
        out[eff] += BASE[eff] * _value(d["owned"].get(str(k), 1))
        count[k // 4] = count.get(k // 4, 0) + 1
    for h, c in count.items():
        eff = HOUSES[h][2]
        if c >= 2:
            out[eff] += SET2[eff]
        if c >= 4:
            out[eff] += SET4[eff]
    for k, cap in CAPS.items():
        out[k] = min(cap, out[k])
    return out


def sets_active(conn) -> list[str]:
    d = get(conn)
    count: dict[int, int] = {}
    for k in d["eq"][: slots(conn)]:
        count[k // 4] = count.get(k // 4, 0) + 1
    return [f"{'maggiore' if c >= 4 else 'minore'} {HOUSES[h][1]}" for h, c in count.items() if c >= 2]


def auto(conn) -> str:
    """Incastona i sigilli migliori: prima le casate di cui hai più pezzi (per i set), poi le stelle."""
    d = get(conn)
    owned = [int(k) for k in d["owned"]]
    if not owned:
        return "Non hai ancora sigilli ancestrali: si trovano tra i tesori."
    per_house: dict[int, list[int]] = {}
    for k in owned:
        per_house.setdefault(k // 4, []).append(k)
    order = sorted(owned, key=lambda k: (-min(4, len(per_house[k // 4])), -d["owned"][str(k)], k))
    d["eq"] = order[: slots(conn)]
    _save(conn, d)
    return f"Incastoni {len(d['eq'])} sigilli. " + summary(conn)


def summary(conn) -> str:
    b = bonus(conn)
    parts = [f"{LABEL[k]} {'−' if k == 'def' else '+'}{v * 100:.1f}%" for k, v in b.items() if v]
    s = sets_active(conn)
    return " · ".join(parts) + (f" · set: {', '.join(s)}" if s else "") if parts else "nessun effetto"


def combat(conn, fx) -> list[str]:
    b = bonus(conn)
    if b["atk"]:
        fx.p.atk_mult *= 1.0 + b["atk"]
    if b["vit"]:
        from engine.systems import power_budget
        m = power_budget.soft(1.0 + b["vit"], 2.5)        # la vitalità non passa dal bilancio dei doni: tetto suo
        fx.p.hp *= m
        fx.p.max *= m
    pr = fx.p.prof
    for k, f in (("crit", "crit"), ("def", "taken"), ("evade", "evade")):
        if b[k]:
            pr[f] = pr.get(f, 0.0) + b[k]
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    c = bonus(conn)["cult"]
    return (1.0 + c, "i sigilli ancestrali") if c else (1.0, "")


def menu_sections(conn, player) -> list:
    from engine.systems.menus import act, section
    d = get(conn)
    n = slots(conn)
    eq = d["eq"][:n]
    lines = [f"Costellazione: {len(eq)}/{n} posti · sigilli trovati {len(d['owned'])}/24", "Effetti: " + summary(conn)]
    lines += [f"✦ {sigil_name(k)} ★{d['owned'].get(str(k), 1)} — {LABEL[HOUSES[k // 4][2]]}" for k in eq]
    spare = [int(k) for k in d["owned"] if int(k) not in eq]
    acts = [act("Incastona i migliori (cerca i set)", "sigilli auto", bool(d["owned"]), "nessun sigillo", main=bool(spare))]
    acts += [act(f"Togli {sigil_name(k)}", f"sigilli togli {i + 1}") for i, k in enumerate(eq)][:4]
    out = [section("I Sigilli ancestrali", lines + (["Si trovano tra i tesori: tombe, reami segreti, torre, torneo, "
                                                    "premi delle trame. Un doppione si fonde e sale di stella."]
                                                   if not d["owned"] else []), acts, icon="✴")]
    if spare:
        out.append(section("Sigilli non incastonati",
                           [f"{i + 1}. {sigil_name(k)} ★{d['owned'][str(k)]}" for i, k in enumerate(spare)][:12],
                           [act(f"Metti {sigil_name(k)}", f"sigilli metti {i + 1}", len(eq) < n, "costellazione piena")
                            for i, k in enumerate(spare)][:4], icon="✴"))
    return out


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    d = get(conn)
    if sub == "auto":
        return auto(conn)
    if sub in ("togli", "rimuovi") and len(p) > 1 and p[1].isdigit():
        i = int(p[1]) - 1
        if 0 <= i < len(d["eq"]):
            k = d["eq"].pop(i)
            _save(conn, d)
            return f"Togli {sigil_name(k)} dalla costellazione."
        return "Nessun sigillo incastonato con quel numero."
    if sub in ("metti", "incastona") and len(p) > 1 and p[1].isdigit():
        spare = [int(k) for k in d["owned"] if int(k) not in d["eq"]]
        i = int(p[1]) - 1
        if not (0 <= i < len(spare)):
            return "Nessun sigillo libero con quel numero."
        if len(d["eq"]) >= slots(conn):
            return "La costellazione è piena: togli prima un sigillo."
        d["eq"].append(spare[i])
        _save(conn, d)
        return f"Incastoni {sigil_name(spare[i])}. " + summary(conn)
    from engine.systems import menus, dharma_body
    return menus.render(conn, dharma_body.menu_build(conn, player))
