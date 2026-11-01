"""
COSA PUOI FARE QUI — le azioni del luogo come tessere (per la dashboard).

Nel terminale bisognava ricordare i comandi; nella dashboard il luogo stesso ti mostra cosa
offre: allenarti, raccogliere, il mercato, l'asta, la sede di una setta, le creature da cacciare,
i ricercati, i reami segreti, la tua dimora, gli eventi in corso qui, lo sfondamento quando sei
pronto. Ogni tessera è un'azione a un tocco; quelle non ancora possibili dicono cosa manca.
"""

from __future__ import annotations


def _t(icon: str, label: str, cmd: str, hint: str = "", ok: bool = True, why: str = "", tone: str = "") -> dict:
    return {"icon": icon, "label": label, "cmd": cmd, "hint": hint, "ok": bool(ok), "why": why if not ok else "",
            "tone": tone}


def tiles(conn, player) -> list[dict]:
    from engine.core import entities
    from engine.systems import (market, auction, sects, cave_abode, travel, system_daily,
                                pursuers)
    loc = entities.get_location(conn, player.location_id)
    if loc is None:
        return []
    out: list[dict] = []
    # (allenarsi, tempra, sonno, sfondamento: stanno solo in alto a sinistra — vedi quick_flags)
    for d in travel.destinations(conn, player):
        if d["loc"] == player.location_id and d.get("join"):
            out.append(_t("✦", d["title"], d["join"], "qui, ora", tone="rare"))
    q = system_daily.data(conn, player.id)
    # luogo
    if market.is_market_here(conn, player.location_id):
        out.append(_t("🏪", "Mercato", "mercato", "compra con un tocco"))
    a = auction.current(conn)
    if a and a["loc"] == player.location_id:
        out.append(_t("⚖", "Casa d'aste", "asta", "lotti rari", tone="warn"))
    fac = conn.execute("SELECT name FROM factions WHERE home_location_id=?;", (player.location_id,)).fetchone()
    m = sects.get_membership(conn, player.id)
    if fac:
        if m and m["sect_name"] == fac["name"]:
            out.append(_t("⛩", "La tua setta", "setta", fac["name"]))
        elif not m:
            out.append(_t("⛩", f"Entra in {fac['name']}", "join", "test d'ingresso", tone="info"))
    if cave_abode.is_home(conn, player.id, player.location_id):
        out.append(_t("⌂", "La tua dimora", "dimora", "produzione e ritiro"))
        out.append(_t("🧘", "Ritiro (3 giorni)", "ritiro 3", "coltivazione intensa"))
    if loc.location_type != "city":
        out.append(_t("✿", "Raccogli materiali", "gather", "erbe, minerali"))
    # chi c'è
    rows = conn.execute("SELECT id, name, kind FROM npcs WHERE location_id=? AND status='alive';",
                        (player.location_id,)).fetchall()
    beasts = [r for r in rows if (r["kind"] or "human") != "human"]
    if beasts:
        out.append(_t("🐾", f"Caccia ({len(beasts)} creature)", "attack creatures", "bottino ed essenze", tone="warn"))
    chase = dict(pursuers.tracked(conn))
    for r in rows:
        if r["id"] in chase:
            out.append(_t("⚔", f"Affronta {r['name']}", f"duello {r['name'].split()[0]}", "ti dà la caccia", tone="bad"))
    from engine.systems import bounties
    for b in bounties.active_bounties(conn):
        if any(r["id"] == b["npc_id"] for r in rows):
            out.append(_t("🎯", f"Taglia: {b['name']}", f"duello {b['name'].split()[0]}", f"{b['reward']} pietre", tone="warn"))
    if q and loc.location_type == "city":
        out.append(_t("🤝", "Chi ha bisogno di te", "bacheca", "incarichi, taglie, missioni"))
    out += _more(conn, player, loc, rows)
    return out


def _more(conn, player, loc, rows) -> list[dict]:
    """(Agg. 81) Le azioni che prima stavano solo nel testo: ora sono tessere a un tocco."""
    out: list[dict] = []
    try:
        from engine.core import entities
        from engine.systems import absorption, dao_insight, heaven_trials, dao_laws, workshop, goals, npc_crafts
        dead = entities.dead_npcs_in_location(conn, player.location_id)
        if dead:
            if absorption.can_absorb(conn, player.id):
                out.append(_t("🩸", f"Divora i resti ({len(dead)})", "absorb all", "corpo, anima, Dao e mestieri",
                              tone="bad"))
        if loc.location_type in dao_insight.RELIC_PLACES:
            ok = dao_insight.can_search(conn, player.location_id)
            out.append(_t("🏺", "Cerca reperti", "reperti", "insegnamenti dei maestri", ok,
                          "già frugato di recente", tone="rare"))
        if any((r["kind"] or "human") == "human" for r in rows) and loc.location_type in ("sect", "city", "village"):
            out.append(_t("👁", "Assisti agli allenamenti", "assisti", "impara dal più bravo"))
        masters = [(r, npc_crafts.of_npc(conn, r["id"])) for r in rows if (r["kind"] or "human") == "human"]
        masters = [(r, c[0]) for r, c in masters if c and c[0][1] >= 3]
        if masters:
            r, (k, lv) = max(masters, key=lambda x: x[1][1])
            from engine.systems import professions
            out.append(_t("⚒", f"Bottega da {r['name'].split()[0]}", f"bottega {r['name'].split()[0]}",
                          f"{professions.PROFESSIONS[k]} liv. {lv}"))
        ready = [k for k in dao_laws.FUSED if not dao_laws._has(conn, k, player.id)
                 and not dao_laws.recipe_status(conn, k, player.id)["missing"]]
        if ready:
            out.append(_t("☯", f"Fondi: {dao_laws.FUSED[ready[0]][1].split(' ', 2)[-1]}", f"fusione {ready[0]}",
                          "una fusione è pronta", tone="rare"))
        d = heaven_trials._get(conn)
        day = heaven_trials._day(conn)
        free = [g for g in (1, 2, 3) if d["last"].get(str(g)) is None or day - int(d["last"][str(g)]) >= heaven_trials.COOLDOWN]
        if free and day >= 10:
            out.append(_t("⛩", "Prove del Cielo", "prova_cielo", f"{len(free)} pronte"))
        lab = workshop.lab(conn)
        if lab and lab.get("cassa", 0) > 0:
            out.append(_t("⚒", f"Incassa il laboratorio ({lab['cassa']})", "laboratorio riscuoti", lab["dove"], tone="info"))
        g = goals.plan(conn, player.id)
        if g and g["next"] and g["next"]["cmd"]:
            out.append(_t("🎯", g["next"]["text"][:28], g["next"]["cmd"], g["title"], tone="info"))
    except Exception:                                    # noqa: BLE001 — una tessera in meno, mai un errore
        pass
    return out


def quick_flags(conn, player) -> dict:
    """Lo stato dei pulsanti fissi in alto a sinistra (allenati, tempra, sfonda, raccogli…)."""
    from engine.simulation import cultivation
    from engine.systems import dao_powers, loot, spirit, qi, dao_spirits
    rec = cultivation.get_record(conn, "player", player.id)
    return {
        "breakthrough": bool(rec and (rec["stage"] or 1) >= 10 and (rec["progress"] or 0) >= 1.0),
        "tribulation": dao_powers.tribulation_due(conn, player.id) > 0,
        "raccogli": len(loot.drops_in_location(conn, player.location_id)),
        "tempra": spirit.get_spirit(conn, player.id) > 0,
        "spiriti": bool(dao_spirits.spirits(conn, player.id)),
        "sonno": qi.get_qi(conn, player.id) < qi.max_qi(conn, player.id) * 0.5,
    }
