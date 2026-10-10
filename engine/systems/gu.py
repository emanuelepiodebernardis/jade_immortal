"""
GU (蛊) — la via degli insetti spirituali, come Fang Yuan.

I Gu sono creature-tesoro che vivono nella tua APERTURA. Si trovano sulle bestie uccise in
rovine e zone proibite, o si comprano. Ogni Gu ha un GRADO (senza fine) e un effetto.
Vanno NUTRITI: ogni giorno consumano un po' di pietre spirituali; se non mangi, muoiono.
Due Gu dello stesso tipo si possono RAFFINARE in uno di grado superiore ('gu raffina <tipo>').
L'apertura regge 2 Gu più uno per regno.

  Gu della Luna d'Argento    attacco          Gu della Pelle di Rame   difesa
  Gu della Primavera Verde   rigenerazione    Gu del Veleno Nero       veleno
  Gu della Fortuna           incontri e bottini migliori
  Gu della Primavera e dell'Autunno (rarissimo)  alla morte riavvolge il tempo: rinasci
                             poco prima, e il Gu si consuma

  gu                         i tuoi Gu, il loro grado, quanto mangiano
  gu raffina <tipo>          fondi due Gu dello stesso tipo in uno di grado superiore
"""

from __future__ import annotations

import random

from engine.systems import state

KEY = "gu"
TYPES = {
    "luna": ("Gu della Luna d'Argento", "attacco"),
    "rame": ("Gu della Pelle di Rame", "difesa"),
    "primavera": ("Gu della Primavera Verde", "rigenerazione"),
    "veleno": ("Gu del Veleno Nero", "veleno"),
    "fortuna": ("Gu della Fortuna", "fortuna"),
    "cicala": ("Gu della Primavera e dell'Autunno", "riavvolge il tempo alla morte"),
}


def gus(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def _save(conn, g: list[dict]) -> None:
    state.set_json(conn, KEY, g)


def slots(conn, pid: int) -> int:
    from engine.simulation import cultivation
    return 2 + (cultivation.realm_tier(conn, "player", pid) or 1)


def add(conn, pid: int, kind: str, grade: int = 1) -> str:
    g = gus(conn)
    if len(g) >= slots(conn, pid):
        return f"La tua apertura è piena ({slots(conn, pid)} Gu): il {TYPES[kind][0]} fugge via."
    g.append({"kind": kind, "grade": grade, "hunger": 0})
    _save(conn, g)
    return f"🐛 Un {TYPES[kind][0]} (grado {grade}) entra nella tua apertura."


def maybe_drop(conn, rng: random.Random, player) -> str | None:
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    if not lt or lt["location_type"] not in ("ruin", "forbidden_zone") or rng.random() > 0.15:
        return None
    kind = "cicala" if rng.random() < 0.04 else rng.choice(["luna", "rame", "primavera", "veleno", "fortuna"])
    return add(conn, player.id, kind)


def refine(conn, player, arg: str) -> str:
    kind = arg.strip().lower()
    g = gus(conn)
    same = sorted([x for x in g if x["kind"] == kind], key=lambda x: -x["grade"])
    if len(same) < 2:
        return "Servono due Gu dello stesso tipo ('gu' per vederli; tipi: " + ", ".join(TYPES) + ")."
    a, b = same[0], same[1]
    rng = random.Random(sum(x["grade"] for x in g) * 31 + len(g))
    g.remove(a)
    g.remove(b)
    if rng.random() < max(0.3, 0.85 - 0.05 * a["grade"]):
        new = {"kind": kind, "grade": max(a["grade"], b["grade"]) + 1, "hunger": 0}
        g.append(new)
        _save(conn, g)
        return f"I due Gu si divorano a vicenda… ne esce un {TYPES[kind][0]} di grado {new['grade']}!"
    g.append(a)
    _save(conn, g)
    return f"La raffinazione fallisce: il Gu più debole muore, l'altro resta di grado {a['grade']}."


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import sects
    g = gus(conn)
    if not g:
        return []
    cost = sum(3 * x["grade"] for x in g)
    out = []
    if sects.get_resource(conn, "pietre_spirituali", player.id) >= cost:
        sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
        for x in g:
            x["hunger"] = 0
    else:
        for x in list(g):
            x["hunger"] += 1
            if x["hunger"] >= 3:
                g.remove(x)
                out.append(f"Il tuo {TYPES[x['kind']][0]} è morto di fame.")
        if any(x["hunger"] == 1 for x in g):
            out.append(f"⚠ I tuoi Gu hanno fame: servono {cost} pietre al giorno.")
    _save(conn, g)
    return out


def combat(conn, fx) -> list[str]:
    pr = fx.p.prof
    for x in gus(conn):
        gr = x["grade"]
        if x["kind"] == "luna":
            fx.p.atk_mult *= 1.0 + 0.05 * gr
        elif x["kind"] == "rame":
            pr["taken"] = pr.get("taken", 0.0) + min(0.25, 0.04 * gr)
        elif x["kind"] == "primavera":
            fx.add_proc("p", "rigenerazione", min(0.45, 0.12 + 0.03 * gr), 1.0 + 0.15 * gr, "gu")
        elif x["kind"] == "veleno":
            fx.add_proc("p", "veleno", min(0.45, 0.12 + 0.03 * gr), 1.0 + 0.2 * gr, "gu")
    return []


def fortune_bonus(conn) -> int:
    return sum(5 * x["grade"] for x in gus(conn) if x["kind"] == "fortuna")


def try_rewind(conn, player) -> str | None:
    g = gus(conn)
    c = next((x for x in g if x["kind"] == "cicala"), None)
    if not c:
        return None
    g.remove(c)
    _save(conn, g)
    conn.execute("UPDATE players SET status='alive' WHERE id=?;", (player.id,))
    conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' AND character_id=?;", (player.id,))
    return ("🐛 Il Gu della Primavera e dell'Autunno si spezza: il tempo si riavvolge come un filo. "
            "Riapri gli occhi un attimo prima della fine — vivo. Il Gu non c'è più.")


def describe(conn, player) -> str:
    g = gus(conn)
    lines = [f"🐛 APERTURA DEI GU ({len(g)}/{slots(conn, player.id)}) — consumano {sum(3 * x['grade'] for x in g)} "
             "pietre al giorno"]
    for x in sorted(g, key=lambda x: (x["kind"], -x["grade"])):
        nm, eff = TYPES[x["kind"]]
        lines.append(f"  · {nm} — grado {x['grade']} — {eff}" + (" (affamato!)" if x["hunger"] else ""))
    if not g:
        lines.append("  Vuota. I Gu si trovano sulle bestie di rovine e zone proibite.")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    if parts and parts[0].lower() in ("raffina", "refine") and len(parts) > 1:
        return refine(conn, player, parts[1])
    return describe(conn, player)
