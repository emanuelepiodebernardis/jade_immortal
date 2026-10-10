"""
MARIONETTE (傀儡) e TESORI MAGICI LEGATI AL SANGUE (本命法宝).

MARIONETTE — con l'arte della Forgia o delle Formazioni (livello 3+) costruisci marionette
da combattimento con minerali e nuclei. Combattono al tuo fianco. Si POTENZIANO senza fine
('marionetta potenzia <n>'); puoi guidarne una in più ogni 5 livelli della tua arte.

TESORI LEGATI AL SANGUE — una Spada Volante, uno Scudo di Giada, una Campana del Tuono…
Si trovano nei reami segreti e sulle bestie sacre, o si forgiano (livello 5). Li lega
il tuo sangue: li NUTRI col tuo sangue ('tesoro nutri <n>' — ogni livello costa un anno di
vita e pietre) e crescono senza fine. Al massimo tre legati insieme.

  marionette                        le tue marionette
  marionetta crea                   costruisci una marionetta (10 minerali, 2 nuclei)
  marionetta potenzia <n>           la potenzi (minerali e nuclei, costo crescente)
  tesori                            i tuoi tesori legati
  tesoro forgia <spada|scudo|campana>   (Forgia 5) forgi un tesoro
  tesoro nutri <n>                  lo nutri col tuo sangue
"""

from __future__ import annotations

import random

from engine.systems import state

P_KEY = "puppets"
T_KEY = "bound_treasures"
TREASURES = {
    "spada": ("Spada Volante", "colpisce da sola, a distanza: un colpo in più e attacco"),
    "scudo": ("Scudo di Giada", "si interpone ai colpi: danni subiti ridotti"),
    "campana": ("Campana del Tuono", "il suo rintocco stordisce i nemici"),
    "specchio": ("Specchio dei Cieli", "riflette e acceca"),
    "gourd": ("Zucca del Fuoco Celeste", "sputa fiamme che bruciano a lungo"),
}
_TR_STATE = {"campana": "stordimento", "specchio": "accecamento", "gourd": "ustione"}


def puppets(conn) -> list[dict]:
    return state.get_json(conn, P_KEY, []) or []


def treasures(conn) -> list[dict]:
    return state.get_json(conn, T_KEY, []) or []


def _art_level(conn, pid) -> int:
    from engine.systems import professions
    if professions.profession(conn, pid) in ("forgia", "formazioni"):
        return professions.level(conn, pid)
    return 0


def max_puppets(conn, pid) -> int:
    lv = _art_level(conn, pid)
    return 0 if lv < 3 else 1 + lv // 5


def create_puppet(conn, player) -> str:
    from engine.systems import professions
    if len(puppets(conn)) >= max_puppets(conn, player.id):
        return ("Serve l'arte della Forgia o delle Formazioni (livello 3) per costruire marionette; "
                f"ora ne puoi guidare {max_puppets(conn, player.id)}.")
    if not professions.spend(conn, player.id, {"minerali": 10, "nuclei": 2}):
        return "Servono 10 minerali e 2 nuclei di bestia."
    ps = puppets(conn)
    n = len(ps) + 1
    ps.append({"n": n, "level": 1})
    state.set_json(conn, P_KEY, ps)
    state.grant_title(conn, "Maestro delle Marionette") if n == 3 else None
    return f"Incastri ingranaggi, incidi rune, infondi Qi: la Marionetta n.{n} apre gli occhi di cristallo."


def upgrade_cost(lv: int) -> dict:
    return {"minerali": 5 + 3 * lv, "nuclei": 1 + lv // 2}


def upgrade_puppet(conn, player, arg: str) -> str:
    from engine.systems import professions
    ps = puppets(conn)
    p = next((x for x in ps if str(x["n"]) == arg.strip()), ps[0] if ps and not arg.strip() else None)
    if not p:
        return "Quale marionetta? ('marionette')"
    cost = upgrade_cost(p["level"])
    if not professions.spend(conn, player.id, cost):
        return f"Servono {cost['minerali']} minerali e {cost['nuclei']} nuclei."
    p["level"] += 1
    state.set_json(conn, P_KEY, ps)
    return f"La Marionetta n.{p['n']} sale al livello {p['level']}."


def forge_treasure(conn, player, kind: str) -> str:
    from engine.systems import professions
    from engine.systems import professions as pr
    kind = kind.strip().lower()
    if kind not in TREASURES:
        return "Quale tesoro? " + ", ".join(TREASURES)
    if pr.profession(conn, player.id) != "forgia" or pr.level(conn, player.id) < 5:
        return "Solo un fabbro di livello 5 sa forgiare un tesoro da legare al sangue."
    if not professions.spend(conn, player.id, {"minerali": 15, "nuclei_rari": 1}):
        return "Servono 15 minerali e un nucleo raro."
    return bind(conn, kind)


def bind(conn, kind: str) -> str:
    ts = treasures(conn)
    if len(ts) >= 3:
        return f"Hai già tre tesori legati: il tuo sangue non ne regge un quarto. (Il {TREASURES[kind][0]} resta inerte.)"
    ts.append({"kind": kind, "level": 1})
    state.set_json(conn, T_KEY, ts)
    return f"Versi una goccia di sangue sul {TREASURES[kind][0]}: ora è legato a te, e crescerà con te."


def feed(conn, player, arg: str) -> str:
    from engine.systems import lifespan, sects
    ts = treasures(conn)
    t = next((x for i, x in enumerate(ts, 1) if str(i) == arg.strip()), ts[0] if ts and not arg.strip() else None)
    if not t:
        return "Quale tesoro? ('tesori')"
    cost = 100 * t["level"]
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Servono {cost} pietre spirituali (e un anno della tua vita)."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    lifespan.add_bonus_years(conn, -1)
    t["level"] += 1
    state.set_json(conn, T_KEY, ts)
    return f"Il {TREASURES[t['kind']][0]} beve il tuo sangue (un anno di vita, {cost} pietre): livello {t['level']}."


def combat_allies(conn, player_id: int, fx) -> list[dict]:
    from engine.simulation import combat
    out = []
    base = combat.combat_power(conn, "player", player_id)["attack"]
    for p in puppets(conn):
        out.append({"intro": f"La Marionetta n.{p['n']} avanza con un clangore.",
                    "attack": base * min(1.0, 0.2 + 0.04 * p["level"]),
                    "line": f"La Marionetta n.{p['n']} colpisce senza esitazione."})
    pr = fx.p.prof
    for t in treasures(conn):
        lv = t["level"]
        if t["kind"] == "spada":
            fx.p.atk_mult *= 1.0 + 0.04 * lv
            pr["extra_strikes"] = pr.get("extra_strikes", 0) + (1 if lv >= 5 else 0)
        elif t["kind"] == "scudo":
            pr["taken"] = pr.get("taken", 0.0) + min(0.3, 0.03 * lv)
        st = _TR_STATE.get(t["kind"])
        if st:
            fx.add_proc("p", st, min(0.45, 0.1 + 0.02 * lv), 1.0 + 0.15 * lv, f"tesoro:{t['kind']}")
    return out


def maybe_drop_treasure(conn, rng: random.Random, player) -> str | None:
    if rng.random() > 0.08:
        return None
    kind = rng.choice(list(TREASURES))
    return f"Tra i resti trovi un tesoro antico: {TREASURES[kind][0]}! " + bind(conn, kind)


def describe(conn, player, what: str = "") -> str:
    lines = []
    ps = puppets(conn)
    lines.append(f"⚙ MARIONETTE ({len(ps)}/{max_puppets(conn, player.id)})")
    for p in ps:
        c = upgrade_cost(p["level"])
        lines.append(f"  · Marionetta n.{p['n']} — livello {p['level']} (potenziarla: {c['minerali']} minerali, "
                     f"{c['nuclei']} nuclei)")
    ts = treasures(conn)
    lines.append(f"✧ TESORI LEGATI AL SANGUE ({len(ts)}/3)")
    for i, t in enumerate(ts, 1):
        nm, desc = TREASURES[t["kind"]]
        lines.append(f"  {i}. {nm} — livello {t['level']} — {desc} (nutrirlo: {100 * t['level']} pietre e un anno di vita)")
    if not ts:
        lines.append("  Nessuno: si trovano nei reami segreti e sulle bestie sacre, o si forgiano (Forgia 5).")
    return "\n".join(lines)
