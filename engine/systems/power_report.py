"""
IL RAPPORTO SULLA FORZA (Aggiornamento 70) — la scheda «⚖ Forza» della Via, più chiara.

  · fattori(): ogni moltiplicatore della crescita personale, uno per uno (tecniche, doni, Dao…),
    letto da combat.combat_power con trace=…: quello che vedi è quello che usa il combattimento.
  · peers(): tu e il tuo regno — quanto vale la persona media del tuo regno, quanto un élite, quanto il più forte.
  · advice(): cosa potenziare adesso, con il comando da cliccare. Solo consigli che si possono fare subito.
"""

from __future__ import annotations


def fattori(conn, player) -> list[tuple[str, float]]:
    from engine.simulation import combat
    t: dict = {}
    combat.combat_power(conn, "player", player.id, t)
    out = []
    if t.get("arma", 1.0) != 1.0:
        out.append(("arma", t["arma"]))
    for name, m in t.get("fattori", []):
        v = m.get("attack", 1.0)
        if abs(v - 1.0) > 0.005:
            out.append((name, v))
    return sorted(out, key=lambda x: -x[1])


def peers(conn, player) -> dict:
    from engine.simulation import combat, cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    me = combat.combat_power(conn, "player", player.id)["attack"]
    rows = conn.execute("SELECT id FROM npcs WHERE status='alive' AND kind='human';").fetchall()
    vals = []
    for r in rows:
        if (cultivation.realm_tier(conn, "npc", r["id"]) or 0) == tier:
            vals.append(combat.combat_power(conn, "npc", r["id"])["attack"])
        if len(vals) >= 60:
            break
    if not vals:
        return {"regno": tier, "tu": me, "n": 0}
    vals.sort()
    return {"regno": tier, "tu": me, "n": len(vals), "mediana": vals[len(vals) // 2], "max": vals[-1],
            "rapporto": me / max(1.0, vals[len(vals) // 2])}


def advice(conn, player) -> list[tuple[str, str]]:
    """(testo, comando) — al massimo 5, i più utili per primi."""
    out: list[tuple[str, str]] = []
    try:
        from engine.systems import attributes
        pts = attributes.free(conn, player.id)
        if pts:
            out.append((f"Hai {pts} punt{'o' if pts == 1 else 'i'} attributo da assegnare.", "attributi"))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.systems import gear
        d = gear.get(conn)
        empty = [s for s in gear.ORDER if s not in d["eq"]]
        better = [x for x in d["bag"] if gear.score(x) > gear.score(d["eq"].get(x["slot"]))]
        if better:
            out.append((f"Nello zaino hai {len(better)} pezzi migliori di ciò che indossi.", "equip auto"))
        if empty:
            out.append((f"{len(empty)} posti dell'equipaggiamento vuoti: forgia {gear.SLOTS[empty[0]][0].lower()} "
                        f"({gear.forge_cost(gear._tier(conn))} pietre).", f"equip forgia {empty[0]}"))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.systems import meridians
        if meridians.openable(conn):
            out.append(("Un meridiano si può aprire.", "meridiani"))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.systems import dharma_body
        if not dharma_body.get(conn).get("awake") and dharma_body._tier(conn) >= dharma_body.AWAKEN_TIER:
            out.append(("Il Corpo del Dharma può risvegliarsi.", "dharma risveglia"))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.simulation import combat
        t: dict = {}
        combat.combat_power(conn, "player", player.id, t)
        if t.get("ferite", 1.0) < 0.95:
            out.append((f"Le ferite ti tolgono il {round(100 * (1 - t['ferite']))}% della forza: riposa o cura.", "sleep"))
        if t.get("dao", {}).get("attack", 1.0) < 1.3:
            out.append(("I tuoi Dao sono poveri per il tuo regno: allenali, l'amplificatore arriva oltre ×2.", "via profondi"))
    except Exception:                                  # noqa: BLE001
        pass
    out.append(("Il regno resta la scala principale: ogni sfondamento moltiplica tutto ×1,6.", "via coltivazione"))
    return out[:5]


def sections(conn, player) -> list:
    """Le sezioni in più per la scheda «⚖ Forza»."""
    from engine.systems.menus import act, bar, section
    import math
    secs = []
    f = fattori(conn, player)
    if f:
        top = max(math.log(max(1.0001, v)) for _n, v in f)
        bars = [bar(f"{n} ×{v:.2f}", 100 * math.log(max(1.0, v)) / top if top > 0 else 0, "") for n, v in f]
        secs.append(section("La crescita personale, fonte per fonte", [
            "Prima della compressione: questi moltiplicatori si sommano in un rapporto enorme, che poi il gioco "
            "comprime (×1000 grezzi diventano circa ×3). Il primo della lista è quello che pesa di più."], [], bars,
            icon="✦"))
    p = peers(conn, player)
    if p.get("n"):
        from engine.systems import elites
        lo, hi = elites.BANDS["elite"]
        lines = [f"Tu: attacco {_n(p['tu'])} · persona media del {p['regno']}° regno: {_n(p['mediana'])} "
                 f"(sei ×{p['rapporto']:.1f}) · la più forte: {_n(p['max'])}."]
        if p["rapporto"] > 1 / elites.DOMINANT:
            lines.append(f"Sei molto avanti: il mondo risponde. Gli ★ élite valgono tra {int(lo * 100)}% e "
                         f"{int(hi * 100)}% di te, i ♛ boss (patriarchi) tra il 90% e il 130%. Gli altri restano come sono.")
        secs.append(section("Tu e il tuo regno", lines, icon="⚖"))
    adv = advice(conn, player)
    if adv:
        secs.append(section("Cosa potenziare adesso", [a for a, _c in adv],
                            [act(a[:48] + ("…" if len(a) > 48 else ""), c) for a, c in adv], icon="➤"))
    return secs


def _n(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")
