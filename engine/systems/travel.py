"""
METE — comandi diretti per raggiungere ciò che conta, senza perdersi sulla mappa.

Quando nel mondo compare qualcosa (un reame segreto, la Grande Assemblea, un'asta, una gara
della tua arte, un'invasione, un elemento celeste, la tua famiglia minacciata…) non devi
cercare la strada a mano:

  mete                    tutto ciò che sta accadendo, numerato, con la distanza
  vai <n | nome>          raggiungi quella meta (o un luogo qualsiasi che conosci per nome)
  iscriviti <n | nome>    raggiungi la meta E ti iscrivi / entri / intervieni subito
                          (Assemblea, gara, reame segreto, difesa dall'invasione…)

Il viaggio costa tempo in proporzione alla distanza (il mondo continua a vivere), Qi se
voli; dal 2° regno voli e arrivi prima, dal 6° il Passo nel Vuoto è quasi istantaneo.
Se all'arrivo succede qualcosa di importante, 'iscriviti' si ferma e te lo lascia risolvere.
"""

from __future__ import annotations

from engine.core import entities, tick as tick_mod


def _loc_name(conn, lid: int) -> str:
    r = conn.execute("SELECT name FROM locations WHERE id=?;", (lid,)).fetchone()
    return r["name"] if r else "?"


def destinations(conn, player) -> list[dict]:
    """[{key, title, loc, join}] di ciò che sta accadendo nel mondo e ti riguarda."""
    from engine.systems import (secret_realms, assembly, auction, contests, world_events, celestial_elements,
                                family, sects, professions, eras)
    out = []
    rr = secret_realms.current(conn)
    if rr and not secret_realms.run(conn):
        out.append({"key": "reame", "title": f"Reame segreto «{rr['name']}»", "loc": rr["loc"], "join": "enter"})
    asm = assembly.current(conn)
    if asm and not asm.get("done"):
        out.append({"key": "assemblea", "title": "Grande Assemblea", "loc": asm["loc"],
                    "join": None if asm.get("joined") else "assemblea iscriviti"})
    gc = contests.current(conn)
    if gc and not gc["done"]:
        mine = professions.profession(conn, player.id) == gc["art"]
        out.append({"key": "gara", "title": contests.NAMES[gc["art"]] + ("" if mine else " (non è la tua arte)"),
                    "loc": gc["loc"], "join": ("gara prova" if gc["joined"] else "gara iscriviti") if mine else None})
    au = auction.current(conn)
    if au:
        out.append({"key": "asta", "title": "Casa d'aste", "loc": au["loc"], "join": "asta"})
    wev = world_events.active_event(conn)
    if wev and wev["location_id"]:
        out.append({"key": "invasione", "title": f"Invasione: {world_events.KIND_LABEL.get(wev['kind'], wev['kind'])}",
                    "loc": wev["location_id"], "join": "defend"})
    ce = celestial_elements.current_event(conn)
    if ce and not ce.get("taken"):
        out.append({"key": "elemento", "title": f"Elemento celeste: {ce['name']}", "loc": ce["loc"],
                    "join": "elementi"})
    fam = family.get(conn)
    if fam and fam.get("threat"):
        out.append({"key": "famiglia", "title": "La tua famiglia è minacciata!", "loc": fam["home"],
                    "join": "famiglia difendi"})
    elif fam:
        out.append({"key": "casa", "title": f"Casa ({fam['clan']})", "loc": fam["home"], "join": "famiglia visita"})
    m = sects.get_membership(conn, player.id)
    if m:
        h = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
        if h and h["home_location_id"]:
            out.append({"key": "setta", "title": f"Sede della setta ({m['sect_name']})", "loc": h["home_location_id"],
                        "join": None})
    return out


def _distance(conn, a: int, b: int) -> int | None:
    from engine.systems import svolte
    return svolte._distance(conn, a, b)


def describe(conn, player) -> str:
    ds = destinations(conn, player)
    if not ds:
        return "Nulla di importante sta accadendo, per ora. ('vai <luogo>' per un luogo che conosci)"
    lines = ["🧭 METE — 'vai <n>' per andarci, 'iscriviti <n>' per andarci e partecipare subito"]
    for i, d in enumerate(ds, 1):
        dist = _distance(conn, player.location_id, d["loc"])
        where = "QUI" if dist == 0 else (f"{dist} tappe" if dist is not None else "in un altro mondo")
        join = f" → '{d['join']}'" if d["join"] else ""
        lines.append(f"  {i}. {d['title']} — {_loc_name(conn, d['loc'])} ({where}){join}")
    return "\n".join(lines)


def _resolve(conn, player, arg: str) -> tuple[dict | None, int | None, str]:
    """(meta, location_id, nome) da un numero, un nome di meta o un nome di luogo."""
    a = arg.strip().lower()
    ds = destinations(conn, player)
    if a.isdigit() and 1 <= int(a) <= len(ds):
        d = ds[int(a) - 1]
        return d, d["loc"], _loc_name(conn, d["loc"])
    for d in ds:
        if a and (a == d["key"] or a in d["title"].lower()):
            return d, d["loc"], _loc_name(conn, d["loc"])
    if a:
        r = conn.execute("SELECT id, name FROM locations WHERE LOWER(name) LIKE ? ORDER BY LENGTH(name) LIMIT 1;",
                         (f"%{a}%",)).fetchone()
        if r:
            return None, r["id"], r["name"]
    return None, None, ""


def go(conn, player, arg: str) -> str:
    from engine.systems import captivity, encounters, qi as qimod, svolte
    from engine.simulation import world_tick, cultivation
    from engine.cli import loop
    if not arg.strip():
        return describe(conn, player)
    words = [w for w in arg.lower().split() if w not in ("a", "al", "alla", "verso", "di", "il", "la", "per", "favore")]
    if len(words) == 1 and words[0] in loop.DIRECTIONS:
        return loop.dispatch(conn, f"move {words[0]}", allow_nl=False)       # 'vai a nord' = un passo
    if captivity.active(conn):
        return captivity.blocked_msg()
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    d, loc, name = _resolve(conn, player, arg)
    if loc is None:
        return f"Non trovo una meta o un luogo chiamato '{arg}'. ('mete' per l'elenco)"
    if loc == player.location_id:
        return f"Sei già a {name}."
    dist = _distance(conn, player.location_id, loc)
    if dist is None:
        return f"{name} è in un altro mondo: serve ben altro che un viaggio ('mondi')."
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    if tier >= svolte.VOID_TIER:
        ticks, how = 1, "Un passo nel vuoto"
    elif tier >= svolte.FLY_TIER and qimod.can_afford(conn, 3 * dist, player.id):
        qimod.spend(conn, 3 * dist, player.id)
        ticks, how = max(1, dist // 2), "Voli sulla tua spada"
    else:
        ticks, how = dist * tick_mod.cost_of("move"), "Cammini"
    entities.move_player(conn, player.id, loc)
    obs = world_tick.advance(conn, ticks)
    from engine.systems import qol
    qol.note(conn, "luoghi", name)
    moved = entities.get_player(conn, player.id)
    out = f"{how} per {dist} tappe ({ticks} tick) e arrivi a {name}.\n" + loop.render_location(conn, moved)
    if obs:
        out += "\nNel frattempo:\n" + loop._format_observations(obs)
    return out + loop._after_arrival(conn, moved)


def join(conn, player, arg: str) -> str | None:
    """'iscriviti <meta>': ci vai e partecipi. None se l'argomento non è una meta (→ altri comandi)."""
    from engine.systems import encounters
    from engine.cli import loop
    d, loc, _name = _resolve(conn, player, arg)
    if d is None:
        return None
    out = ""
    if loc != player.location_id:
        out = go(conn, player, arg) + "\n\n"
        if encounters.pending(conn) or entities.get_player(conn, player.id).location_id != loc:
            return out + "(Il viaggio si è interrotto: prima risolvi ciò che è successo.)"
    if not d["join"]:
        return out + "Sei arrivato. Qui non c'è nulla a cui iscriversi: guardati intorno ('look')."
    return out + (loop.dispatch(conn, d["join"], allow_nl=False) or "")
