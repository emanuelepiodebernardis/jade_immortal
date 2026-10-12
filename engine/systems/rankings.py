"""
CLASSIFICHE DEL CIELO (天榜) — chi è il più forte sotto il Cielo?

  classifica            Classifica del Cielo: i coltivatori più forti del mondo
  classifica giovani    Lista del Drago Nascente: la nuova generazione (discepoli e giramondo)
  classifica sette      le sette per influenza e potenza dei loro membri

La forza è quella reale di combattimento (la stessa che decide i duelli). Il tuo nome
compare in classifica accanto agli altri: quando sali di posizione per la prima volta
entro le soglie (100, 50, 20, 10, 3, 1) il mondo se ne accorge — fama, pietre, titoli.
Accanto a ogni nome c'è dove è stato visto l'ultima volta: chi vuole salire, sa chi sfidare.
"""

from __future__ import annotations

import sqlite3

from engine.systems import state

_YOUNG = ("discepolo", "vagabondo", "giovane_maestro", "erede")
THRESHOLDS = (100, 50, 20, 10, 3, 1)
_TITLES = {
    "cielo": {10: "Tra i Dieci sotto il Cielo", 3: "Uno dei Tre Sovrani", 1: "Primo sotto il Cielo"},
    "giovani": {10: "Drago Nascente", 1: "Primo della Nuova Generazione"},
}


def _entries(conn, young: bool) -> list[tuple[int, str, str, int]]:
    """[(rating, kind, name, location_id|None, ref)] dei vivi, giocatore compreso."""
    from engine.systems import power
    from engine.core import entities
    q = ("SELECT id, name, archetype, location_id FROM npcs WHERE status='alive' "
         "AND COALESCE(kind,'human')='human'")
    if young:
        q += " AND archetype IN (%s)" % ",".join("?" * len(_YOUNG))
        rows = conn.execute(q, _YOUNG).fetchall()
    else:
        rows = conn.execute(q).fetchall()
    out = [(power.combat_rating(conn, "npc", r["id"]), "npc", r["name"], r["location_id"], r["id"])
           for r in rows]
    p = entities.get_player(conn)
    if p and p.status == "alive":
        out.append((power.combat_rating(conn, "player", p.id), "player", p.name, p.location_id, p.id))
    out.sort(key=lambda x: -x[0])
    return out


def player_rank(conn, young: bool = False) -> tuple[int, int]:
    es = _entries(conn, young)
    for i, e in enumerate(es, 1):
        if e[1] == "player":
            return i, len(es)
    return 0, len(es)


def describe(conn, player, arg: str = "") -> str:
    a = arg.strip().lower()
    if a in ("sette", "sects", "fazioni"):
        return _sects(conn, player)
    young = a in ("giovani", "young", "generazione", "drago")
    title = "LISTA DEL DRAGO NASCENTE" if young else "CLASSIFICA DEL CIELO"
    es = _entries(conn, young)
    lines = [f"✦ {title} ✦"]
    me = None
    for i, (rt, kind, name, loc, ref) in enumerate(es, 1):
        if kind == "player":
            me = i
        if i <= 15 or kind == "player":
            lname = ""
            if loc:
                r = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()
                lname = f" — {r['name']}" if r else ""
            mark = "  ◀ TU" if kind == "player" else ""
            from engine.simulation import cultivation
            realm = cultivation.realm_name(conn, kind, ref)
            lines.append(f"  {i:>3}. {name:<24} {realm:<24} potenza {rt:>6}{lname}{mark}")
    if me:
        lines.append(f"Sei {me}° su {len(es)}." + (" Sfida chi ti sta sopra per salire." if me > 1 else
                                                    " Nessuno sotto il Cielo ti eguaglia."))
    return "\n".join(lines)


def _sects(conn, player) -> str:
    from engine.systems import power
    rows = conn.execute("SELECT id, name, influence, tier, status FROM factions "
                        "WHERE COALESCE(status,'active')!='destroyed';").fetchall()
    from engine.systems import ascension                  # la classifica del mondo in cui ti trovi
    plane = ascension.plane_faction_ids(conn, ascension.player_layer(conn, player.id))
    rows = [f for f in rows if f["id"] in plane] or rows
    scored = []
    for f in rows:
        mem = [r["id"] for r in conn.execute(
            "SELECT id FROM npcs WHERE faction_id=? AND status='alive';", (f["id"],))]
        top = sorted((power.combat_rating(conn, "npc", i) for i in mem), reverse=True)[:5]
        scored.append((sum(top) + (f["influence"] or 0) * 3, f, len(mem)))
    scored.sort(key=lambda x: -x[0])
    lines = ["✦ CLASSIFICA DELLE SETTE ✦"]
    for i, (sc, f, n) in enumerate(scored, 1):
        lines.append(f"  {i:>2}. {f['name']:<34} membri {n:<4} punteggio {int(sc)}")
    return "\n".join(lines)


def daily(conn, t: int, rng, player) -> list[str]:
    """Controlla se sei salito oltre una soglia per la prima volta: ricompense e titoli."""
    from engine.systems import reputation, sects
    out = []
    for board, young in (("cielo", False), ("giovani", True)):
        rank, total = player_rank(conn, young)
        if not rank or total < 5:
            continue
        best = state.get_int(conn, f"rank_best_{board}", 10 ** 9)
        if rank >= best:
            continue
        state.set(conn, f"rank_best_{board}", str(rank))
        # un posto conta solo se la classifica è abbastanza affollata da renderlo un'impresa
        crossed = [th for th in THRESHOLDS if rank <= th < best and total >= max(12, th * 3)]
        if not crossed:
            continue
        th = min(crossed)
        label = "Classifica del Cielo" if board == "cielo" else "Lista del Drago Nascente"
        fame = {100: 2, 50: 4, 20: 6, 10: 10, 3: 20, 1: 40}[th]
        stones = fame * 25
        reputation.adjust(conn, player.id, fame=fame)
        sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
        out.append(f"✦ Il tuo nome sale nella {label}: sei {rank}°! (+{stones} pietre in doni e omaggi)")
        tt = _TITLES[board].get(th)
        if tt and state.grant_title(conn, tt):
            out.append(f"✧ Nuovo titolo: «{tt}» ✧")
    return out
