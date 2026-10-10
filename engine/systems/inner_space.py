"""
LO SPAZIO INTERIORE — dalla bottiglietta di giada al MONDO INTERIORE.

Un piccolo tesoro spaziale (la Bottiglietta di Giada Verde) si trova nei reami segreti,
all'asta o si risveglia da solo quando raggiungi il quinto regno. Dentro c'è un campo dove
il tempo scorre più in fretta.

  spazio                 lo stato del tuo spazio interiore
  spazio semina <n>      pianti n erbe spirituali: dopo un giorno ne raccogli molte di più
  spazio raccogli        raccogli il raccolto maturo
  spazio espandi         lo allarghi (pietre spirituali, costo crescente, livelli infiniti)

Più è grande, più cresce il raccolto (×3, ×4, ×5…). Dal livello 3 le tue bestie vi
riposano e ne nasce qualche nucleo; dal livello 5 diventa un MONDO INTERIORE: il suo Qi
ti fa coltivare più in fretta, ovunque tu sia, e cresce con ogni livello.
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "inner_space"


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def grant(conn, how: str = "") -> str:
    if get(conn):
        return ""
    _save(conn, {"level": 1, "planted": 0, "ready_day": 0})
    state.grant_title(conn, "Custode dello Spazio Interiore")
    return ("✦ Una bottiglietta di giada verde si lega alla tua anima: dentro c'è un piccolo campo dove il tempo "
            "corre più veloce. ('spazio')" + (f" ({how})" if how else ""))


def level(conn) -> int:
    d = get(conn)
    return int(d["level"]) if d else 0


def name_of(lv: int) -> str:
    if lv >= 5:
        return f"Mondo Interiore (livello {lv})"
    return f"Bottiglietta di Giada Verde (livello {lv})"


def expand_cost(lv: int) -> int:
    return int(300 * (1.7 ** lv))


def sow(conn, player, arg: str) -> str:
    from engine.systems import professions
    d = get(conn)
    if not d:
        return "Non possiedi uno spazio interiore."
    if d.get("planted"):
        return "Il campo è già seminato: 'spazio raccogli' quando è maturo."
    n = int(arg) if arg.strip().isdigit() else professions.material(conn, player.id, "erbe")
    n = min(n, professions.material(conn, player.id, "erbe"), 10 * d["level"])
    if n <= 0:
        return "Ti servono erbe spirituali da piantare ('gather' nelle zone selvagge)."
    professions.spend(conn, player.id, {"erbe": n})
    d["planted"] = n
    d["ready_day"] = tick_mod.get_tick(conn) // 120 + 1
    _save(conn, d)
    return f"Pianti {n} erbe nel campo interiore. Domani saranno mature (resa ×{2 + d['level']})."


def harvest(conn, player) -> str:
    from engine.systems import professions
    d = get(conn)
    if not d or not d.get("planted"):
        return "Non c'è nulla da raccogliere nel tuo spazio interiore."
    if tick_mod.get_tick(conn) // 120 < d["ready_day"]:
        return "Le erbe non sono ancora mature: torna domani."
    got = d["planted"] * (2 + d["level"])
    professions.give(conn, player.id, "erbe", got)
    d["planted"] = 0
    _save(conn, d)
    return f"Raccogli {got} erbe spirituali dal campo interiore, gonfie di Qi."


def expand(conn, player) -> str:
    from engine.systems import sects
    d = get(conn)
    if not d:
        return "Non possiedi uno spazio interiore."
    cost = expand_cost(d["level"])
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Per allargarlo al livello {d['level'] + 1} servono {cost} pietre spirituali."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    d["level"] += 1
    _save(conn, d)
    msg = f"Lo spazio interiore si allarga: {name_of(d['level'])}. (-{cost} pietre)"
    if d["level"] == 5:
        msg += "\n✦ È diventato un MONDO INTERIORE: il suo Qi ti accompagna ovunque."
        state.grant_title(conn, "Signore di un Mondo Interiore")
    return msg


def cultivation_mult(conn) -> tuple[float, str]:
    lv = level(conn)
    if lv < 5:
        return 1.0, ""
    return 1.0 + 0.05 * (lv - 4), "il Qi del tuo mondo interiore"


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import professions, beasts, npc_factory
    from engine.simulation import cultivation
    d = get(conn)
    out = []
    if not d:
        if (cultivation.realm_tier(conn, "player", player.id) or 1) >= 5:
            out.append(grant(conn, "il tuo dantian si apre in uno spazio"))
        return out
    if d["level"] >= 3:
        if rng.random() < 0.1 * d["level"]:
            professions.give(conn, player.id, "nuclei", 1)
        pt = beasts.pet(conn, player.id)
        if pt and rng.random() < 0.03 * d["level"]:
            npc_factory.raise_npc(conn, pt["npc_id"], 1)
    return out


def describe(conn, player) -> str:
    d = get(conn)
    if not d:
        return ("Non possiedi uno spazio interiore. Si trova nei reami segreti o all'asta, e si risveglia da solo "
                "al quinto regno.")
    day = tick_mod.get_tick(conn) // 120
    crop = ("vuoto ('spazio semina <n>')" if not d.get("planted") else
            ("maturo! ('spazio raccogli')" if day >= d["ready_day"] else f"{d['planted']} erbe in crescita"))
    lines = [f"✧ {name_of(d['level'])}", f"  Campo: {crop} — resa ×{2 + d['level']}, fino a {10 * d['level']} erbe",
             f"  Allargarlo: {expand_cost(d['level'])} pietre ('spazio espandi')"]
    if d["level"] >= 3:
        lines.append("  Le tue bestie vi riposano; a volte vi nasce un nucleo.")
    if d["level"] >= 5:
        m, _ = cultivation_mult(conn)
        lines.append(f"  Mondo Interiore: coltivazione ×{m:.2f} ovunque tu sia.")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    if sub in ("semina", "pianta", "sow"):
        return sow(conn, player, parts[1] if len(parts) > 1 else "")
    if sub in ("raccogli", "harvest"):
        return harvest(conn, player)
    if sub in ("espandi", "allarga", "expand"):
        return expand(conn, player)
    return describe(conn, player)
