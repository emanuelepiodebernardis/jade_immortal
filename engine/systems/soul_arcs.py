"""
GLI ARCHI DEI VASI D'ANIMA (Aggiornamento 61) — le storie che vivono dentro gli oggetti.

Un «vaso» è un oggetto con un'anima dentro: l'anello del vecchio maestro, la pagoda col suo spirito,
lo stendardo delle anime, il calderone con la fiamma viva, la perla col demone sigillato. Ogni vaso
cresce (lo nutri, combatti, stringi patti) e, a certi livelli, apre un CAPITOLO: una trama vera, con
scelte, prove, duelli e indizi (intrigue_data3.py). L'esito del capitolo cambia il vaso: l'anima si
risveglia, viene rapita, rinasce in un corpo, si ribella, ti tradisce.

  ARCS[vaso] = [capitolo, …]   capitolo = livello minimo, trama, esiti che lo chiudono, giorni per
                               ritentare se va male

Ogni vaso (un modulo) risponde a cinque domande:
  arc_level(conn)                     a che livello è (None = non lo porti, o è muto)
  names(conn)                         i segnaposto delle sue trame ({maestro}, {spirito}…)
  prepare(conn, player, trama)        prepara il capitolo (il traditore…); False = capitolo già vissuto
  branches(conn, trama)               rami con cui comincia (ciò che hai imparato prima)
  on_chapter(conn, player, trama, esito, chiuso)   le conseguenze sul vaso

Aggiungere un capitolo è una riga qui e una trama in intrigue_data3.py.
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "soul_arcs"
CHAPTER_GAP = 4          # giorni di respiro tra un capitolo chiuso e il successivo

ARCS = {
    "anello": [
        {"level": 3, "plot": "anello_legno", "ok": ("legno_vinto", "comprato", "rubato"), "retry": 8},
        {"level": 6, "plot": "anello_traditore", "ok": ("vendetta_vinto", "perdono"), "retry": 10},
        {"level": 8, "plot": "anello_palazzo", "ok": ("assalto_vinto", "furtivo", "riscatto", "abbandonato"), "retry": 6},
        {"level": 10, "plot": "anello_corpo", "ok": ("rinato", "tradimento"), "retry": 12},
    ],
    "pagoda": [
        {"level": 3, "plot": "pagoda_ricordo", "ok": ("porta_vinto", "liberato"), "retry": 6},
        {"level": 6, "plot": "pagoda_padroni", "ok": ("rifiuto_vinto", "rifiuto_perso", "rifiuto_fuga", "scelta",
                                                      "restituita"), "retry": 8},
        {"level": 9, "plot": "pagoda_nome", "ok": ("legata", "libera"), "retry": 5},
    ],
    "stendardo": [
        {"level": 2, "plot": "stendardo_voci", "ok": ("liberata", "innocenti", "tenuta"), "retry": 5},
        {"level": 4, "plot": "stendardo_giusti", "ok": ("scontro_vinto", "scontro_perso", "scontro_fuga", "tregua",
                                                        "nascosto"), "retry": 8},
        {"level": 6, "plot": "stendardo_rivolta", "ok": ("dominate", "battaglia_vinto", "liberate"), "retry": 10},
    ],
    "calderone": [
        {"level": 3, "plot": "calderone_fame", "ok": ("fiamma_vinto", "richiamo"), "retry": 7},
        {"level": 6, "plot": "calderone_maestro", "ok": ("superato", "allievo"), "retry": 6},
        {"level": 9, "plot": "calderone_fiamma", "ok": ("celeste_vinto", "ingoiata"), "retry": 12},
    ],
    "perla": [
        {"level": 2, "plot": "perla_voce", "ok": ("sigillo", "verita", "rifiuto"), "retry": 5},
        {"level": 4, "plot": "perla_prezzo", "ok": ("consegnata", "sutra", "tenuta", "cacciato_vinto",
                                                    "cacciato_perso", "cacciato_fuga"), "retry": 8},
        {"level": 6, "plot": "perla_possessione", "ok": ("divorato", "risigillato", "simbiosi"), "retry": 15},
    ],
}
# (Agg. 67) la saga dei compagni perduti: stessi capitoli, ma il «livello» è il tuo regno
ARCS["compagni"] = [
    {"level": 1, "plot": "compagni_varco", "ok": ("traccia",), "retry": 5},
    {"level": 2, "plot": "compagni_amico", "ok": ("liberato_vinto", "riscattato", "fuga_insieme"), "retry": 7},
    {"level": 4, "plot": "compagni_santa", "ok": ("giuramento_vinto", "protetta", "svelata"), "retry": 8},
    {"level": 5, "plot": "compagni_prigioniera", "ok": ("assalto_vinto", "furtivo", "risvegliata"), "retry": 8},
    {"level": 7, "plot": "compagni_caduto", "ok": ("fermato_vinto", "redento", "patto"), "retry": 10},
    {"level": 8, "plot": "compagni_cacciatore", "ok": ("voce_vinto", "verita"), "retry": 8},
    {"level": 10, "plot": "compagni_finale", "ok": ("custode_vinto", "sigillato", "preso"), "retry": 12},
]
NAMES = {"compagni": "I compagni perduti", "anello": "L'anello del maestro", "pagoda": "La Pagoda delle Nove Prigioni",
         "stendardo": "Lo Stendardo delle Diecimila Anime", "calderone": "Il Calderone della Fiamma Dormiente",
         "perla": "La Perla dei Nove Sigilli"}


def _mod(vessel: str):
    if vessel == "compagni":
        from engine.systems import lost_companions
        return lost_companions
    if vessel == "anello":
        from engine.systems import mentor_ring
        return mentor_ring
    from engine.systems import soul_artifacts
    return soul_artifacts.adapter(vessel)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _vs(d: dict, vessel: str) -> dict:
    return d.setdefault(vessel, {"ch": 0, "running": None, "since": 0, "retry_day": 0})


def reset(conn, vessel: str) -> None:
    """Un'anima nuova nel vaso: la sua storia ricomincia dal primo capitolo."""
    d = get(conn)
    d[vessel] = {"ch": 0, "running": None, "since": 0, "retry_day": _day(conn) + 3}
    _save(conn, d)


def chapter(conn, vessel: str) -> tuple[int, dict | None]:
    s = get(conn).get(vessel) or {}
    i = int(s.get("ch", 0))
    arc = ARCS.get(vessel, [])
    return i, (arc[i] if i < len(arc) else None)


def placeholders(conn, vessel: str) -> dict:
    try:
        return dict(_mod(vessel).names(conn))
    except Exception:                                   # noqa: BLE001 — una trama non deve mai cadere per un nome
        return {"maestro": "il maestro", "Maestro": "Il maestro", "di_maestro": "del maestro",
                "spirito": "lo spirito", "Spirito": "Lo spirito", "di_spirito": "dello spirito"}


def on_finish(conn, vessel: str, plot: str, outcome: str) -> list[str]:
    """Chiamato da intrigues._finish quando un capitolo si chiude: le conseguenze sul vaso."""
    from engine.core import entities
    d = get(conn)
    s = _vs(d, vessel)
    arc = ARCS.get(vessel, [])
    i = int(s.get("ch", 0))
    ch = arc[i] if i < len(arc) else None
    if not ch or ch["plot"] != plot:
        ch = next((c for c in arc if c["plot"] == plot), None)
        if not ch:
            return []
        i = arc.index(ch)
    closed = outcome in ch["ok"]
    s["running"] = None
    if closed:
        s["ch"] = i + 1
        s["retry_day"] = _day(conn) + CHAPTER_GAP          # un respiro tra un capitolo e l'altro
    else:
        s["retry_day"] = _day(conn) + ch.get("retry", 7)
    _save(conn, d)
    p = entities.get_player(conn)
    try:
        lines = _mod(vessel).on_chapter(conn, p, plot, outcome, closed) or []
    except Exception:                                   # noqa: BLE001
        lines = []
    if not closed:
        lines.append(f"(La storia non è finita: tra {ch.get('retry', 7)} giorni potrai ritentare.)")
    return lines


def daily(conn, t: int, rng, player) -> list[str]:
    """Ogni giorno: se un vaso è cresciuto abbastanza, il suo capitolo comincia (uno al giorno)."""
    if player is None:
        return []
    from engine.systems import encounters, intrigues
    d = get(conn)
    day = t // 120
    active = {x["key"] for x in intrigues.get(conn)["active"]}
    changed = False
    for vessel, arc in ARCS.items():
        s = _vs(d, vessel)
        if s.get("running") and s["running"] not in active:
            s["running"] = None                         # la trama è sparita (scaduta senza esito): si ritenta
            s["retry_day"] = day + 3
            changed = True
    if changed:
        _save(conn, d)
    if any(s.get("running") for s in d.values() if isinstance(s, dict)) or encounters.pending(conn):
        return []                                       # un capitolo alla volta
    for vessel, arc in ARCS.items():
        mod = _mod(vessel)
        lv = mod.arc_level(conn)
        if lv is None:
            continue
        s = _vs(d, vessel)
        i = int(s.get("ch", 0))
        if i >= len(arc) or lv < arc[i]["level"] or day < s.get("retry_day", 0):
            continue
        ch = arc[i]
        if mod.prepare(conn, player, ch["plot"]) is False:      # già vissuto (vecchi salvataggi)
            s["ch"] = i + 1
            _save(conn, d)
            continue
        s["running"] = ch["plot"]
        s["since"] = day
        _save(conn, d)
        txt = intrigues.start(conn, player, ch["plot"], branches=mod.branches(conn, ch["plot"]))
        return [f"✧ {NAMES.get(vessel, vessel)}: si apre un nuovo capitolo.", txt or ""]
    return []


def status_line(conn, vessel: str) -> str:
    i, ch = chapter(conn, vessel)
    arc = ARCS.get(vessel, [])
    s = get(conn).get(vessel) or {}
    if s.get("running"):
        return f"Capitolo {i + 1}/{len(arc)} in corso (Mete → trame)."
    if ch is None:
        return f"Tutti i {len(arc)} capitoli vissuti."
    wait = s.get("retry_day", 0) - _day(conn) if s.get("retry_day") else 0
    try:
        lv = _mod(vessel).arc_level(conn) or 0
    except Exception:                                   # noqa: BLE001
        lv = 0
    if lv >= ch["level"]:
        return (f"Capitolo {i + 1}/{len(arc)}: "
                + (f"si apre fra {wait} giorni." if wait > 0 else "si apre alla prossima alba (se non hai altro davanti)."))
    return f"Capitolo {i + 1}/{len(arc)}: si apre al livello {ch['level']}."
