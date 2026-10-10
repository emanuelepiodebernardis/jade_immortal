"""
FORMAZIONI PIAZZATE (阵法) — l'arte del Maestro delle Formazioni.

Le formazioni si creano con l'arte 'formazioni' ('recipes', 'craft') e si piazzano usando
il disco ('use') nel luogo in cui ti trovi. Una per luogo; piazzarne una nuova la sostituisce.

  raccolta      Formazione di Raccolta del Qi: coltivi più in fretta in quel luogo
  difesa        Formazione Difensiva: lì subisci meno danni
  uccisione     Formazione d'Uccisione: lì i tuoi elementi colpiscono con furia
  teletrasporto Formazione di Teletrasporto: viaggi all'istante tra le tue formazioni di
                teletrasporto ('teletrasporto' per l'elenco, 'teletrasporto <n>' per partire)

  formazioni    l'elenco delle tue formazioni nel mondo
"""

from __future__ import annotations

from engine.systems import state

KINDS = {"raccolta": "Formazione di Raccolta del Qi", "difesa": "Formazione Difensiva",
         "uccisione": "Formazione d'Uccisione", "teletrasporto": "Formazione di Teletrasporto"}


def _all(conn) -> dict:
    return state.get_json(conn, "formations", {}) or {}


def at(conn, location_id) -> dict | None:
    if location_id is None:
        return None
    return _all(conn).get(str(location_id))


def place(conn, pid: int, kind: str, level: int) -> str:
    from engine.core import entities
    from engine.systems import classes
    loc = entities.get_player(conn, pid).location_id
    d = _all(conn)
    els = classes.attunement(conn, pid)
    d[str(loc)] = {"kind": kind, "level": int(level), "elements": els}
    state.set_json(conn, "formations", d)
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    el = f" ({classes.fusion_name(els)})" if els else ""
    return f"Pianti le bandiere e tracci le rune: {KINDS[kind]}{el} di livello {level} attiva a {lname}."


def cultivation_mult(conn, location_id) -> tuple[float, str]:
    f = at(conn, location_id)
    if f and f["kind"] == "raccolta":
        return 1.0 + 0.12 * f["level"] + 0.05 * len(f.get("elements", [])), "la tua Formazione di Raccolta del Qi"
    return 1.0, ""


def describe(conn, player) -> str:
    d = _all(conn)
    if not d:
        return "Non hai formazioni nel mondo. (Arte 'formazioni': 'recipes' e 'craft', poi 'use' il disco.)"
    lines = ["Le tue formazioni:"]
    for i, (lid, f) in enumerate(sorted(d.items()), 1):
        r = conn.execute("SELECT name FROM locations WHERE id=?;", (int(lid),)).fetchone()
        lines.append(f"  · {KINDS[f['kind']]} liv. {f['level']} — {r['name'] if r else '?'}"
                     + (" (sei qui)" if int(lid) == player.location_id else ""))
    return "\n".join(lines)


def teleport(conn, player, arg: str) -> str:
    from engine.core import entities
    from engine.simulation import world_tick
    d = _all(conn)
    tps = [(int(k), v) for k, v in sorted(d.items()) if v["kind"] == "teletrasporto"]
    here = at(conn, player.location_id)
    if not here or here["kind"] != "teletrasporto":
        return "Per teletrasportarti devi trovarti su una tua Formazione di Teletrasporto."
    dests = [(lid, f) for lid, f in tps if lid != player.location_id]
    if not dests:
        return "Non hai altre Formazioni di Teletrasporto verso cui viaggiare."
    if not arg.strip().isdigit():
        lines = ["Destinazioni:"]
        for i, (lid, f) in enumerate(dests, 1):
            nm = conn.execute("SELECT name FROM locations WHERE id=?;", (lid,)).fetchone()["name"]
            lines.append(f"  [{i}] {nm}")
        lines.append("'teletrasporto <n>' per partire.")
        return "\n".join(lines)
    i = int(arg) - 1
    if not (0 <= i < len(dests)):
        return "Destinazione non valida."
    entities.move_player(conn, player.id, dests[i][0])
    world_tick.advance(conn, 2)
    nm = conn.execute("SELECT name FROM locations WHERE id=?;", (dests[i][0],)).fetchone()["name"]
    return f"Le rune si accendono, lo spazio si piega: in un battito di ciglia sei a {nm}."
