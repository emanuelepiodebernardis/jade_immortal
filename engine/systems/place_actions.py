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
    from engine.simulation import cultivation
    from engine.systems import (market, auction, sects, cave_abode, dao_powers, travel, qi, spirit, system_daily,
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
