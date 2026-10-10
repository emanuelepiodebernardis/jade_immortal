"""
CLASSI DI PERSONAGGIO: ARTE + ELEMENTI.

La tua arte (professione) unita agli elementi a cui ti SINTONIZZI forma una classe:

  Maestro delle Formazioni + Fuoco      → Maestro delle Formazioni della Fiamma
  Maestro delle Formazioni + Acqua+Legno→ Maestro delle Formazioni «Pioggia di Primavera»
  Domatore di Bestie + Fulmine          → Domatore di Bestie del Tuono
  … e così per ogni arte e ogni combinazione di elementi.

  sintonia <elemento> [elemento…]   scegli gli elementi della tua arte (servono radici
                                    spirituali di quell'elemento ≥ 20). Puoi fonderne
                                    1 + 1 ogni 5 livelli dell'arte: 2 al livello 5, 3 al 10…
  classe                            la tua classe e cosa fa

Effetti per arte:
  - FORMAZIONI: porti con te una formazione mobile. In ogni scontro gli elementi a cui sei
    sintonizzato scatenano i loro stati (ustione, gelo, stordimento…), più forti a ogni
    livello; nelle formazioni che hai piazzato (d'uccisione, difensive) l'effetto è molto
    maggiore. Le fusioni di elementi danno nomi e bonus delle combinazioni.
  - DOMATORE: puoi tenere più bestie (1 + 1 ogni 4 livelli), le domi più facilmente, e le
    tue bestie combattono più forte; se sono del tuo elemento, ancora di più.
  - ALCHIMIA / TALISMANI / FORGIA: l'elemento sintonizzato dà un'aura del suo stato in
    battaglia (più leggera) e un nome alla tua classe.
"""

from __future__ import annotations

from engine.systems import state

_ADJ = {"legno": "del Legno", "fuoco": "della Fiamma", "terra": "della Terra", "metallo": "del Metallo",
        "acqua": "dell'Acqua", "fulmine": "del Tuono", "vento": "del Vento", "luce": "della Luce",
        "oscurita": "dell'Ombra"}
CLASS_BASE = {"formazioni": "Maestro delle Formazioni", "domatore": "Domatore di Bestie",
              "alchimia": "Alchimista", "talismani": "Maestro dei Talismani", "forgia": "Forgiatore",
              "veleni": "Maestro dei Veleni"}


def attunement(conn, pid: int = 1) -> list[str]:
    return list(state.get_json(conn, "attunement", []) or [])


def max_attune(conn, pid: int = 1) -> int:
    from engine.systems import professions
    return 1 + professions.level(conn, pid) // 5


def fusion_name(els: list[str]) -> str:
    from engine.systems import spirit_roots
    from engine.systems.elements import CHAIN_NAMES
    if not els:
        return ""
    if len(els) == 1:
        return _ADJ[els[0]]
    fs = frozenset(els)
    if fs in CHAIN_NAMES:
        return f"«{CHAIN_NAMES[fs]}»"
    if fs in spirit_roots.SPECIAL_PAIRS:
        return f"«{spirit_roots.SPECIAL_PAIRS[fs][0]}»"
    if len(els) == len(spirit_roots.ELEMENTS):
        return "del Caos Primordiale"
    return "dei " + {2: "Due", 3: "Tre", 4: "Quattro", 5: "Cinque", 6: "Sei", 7: "Sette",
                     8: "Otto"}.get(len(els), str(len(els))) + " Elementi"


def class_name(conn, pid: int = 1) -> str | None:
    from engine.systems import professions
    prof = professions.profession(conn, pid)
    if not prof:
        return None
    base = CLASS_BASE.get(prof, professions.PROFESSIONS.get(prof, prof))
    els = attunement(conn, pid)
    return f"{base} {fusion_name(els)}".strip()


def attune(conn, player, arg: str) -> str:
    from engine.systems import spirit_roots, professions
    if not professions.profession(conn, player.id):
        return "Prima scegli un'arte ('profession')."
    want = []
    for w in arg.lower().replace(",", " ").split():
        w = {"oscurità": "oscurita", "tuono": "fulmine", "fiamma": "fuoco", "ombra": "oscurita"}.get(w, w)
        if w in spirit_roots.ELEMENTS and w not in want:
            want.append(w)
    if not want:
        return ("Sintonizzati su uno o più elementi: 'sintonia fuoco' o 'sintonia acqua legno'. "
                f"Al tuo livello puoi fonderne {max_attune(conn, player.id)}.")
    mx = max_attune(conn, player.id)
    if len(want) > mx:
        return f"La tua arte regge al massimo {mx} elementi fusi (1 in più ogni 5 livelli)."
    roots = spirit_roots.get(conn, "player", player.id)
    weak = [spirit_roots.LABEL[e] for e in want if roots.get(e, 0) < spirit_roots.ACTIVE]
    if weak:
        return (f"Le tue radici di {', '.join(weak)} sono troppo deboli (servono almeno "
                f"{spirit_roots.ACTIVE}). 'radici' per vederle.")
    state.set_json(conn, "attunement", want)
    return f"Ti sintonizzi. La tua classe ora è: {class_name(conn, player.id)}."


def _power(conn, pid: int) -> tuple[int, float]:
    from engine.systems import professions
    lv = professions.level(conn, pid)
    return lv, 1.0 + 0.1 * lv


def combat(conn, pid: int, npc_id: int, fx) -> list[str]:
    """Effetti della classe in combattimento (chiamato all'inizio di ogni scontro)."""
    from engine.systems import professions, formations
    from engine.systems.combat_states import STATE_OF_DAO
    prof = professions.profession(conn, pid)
    els = attunement(conn, pid)
    if not prof or not els:
        return []
    lv, pw = _power(conn, pid)
    from engine.core import entities
    loc = entities.get_player(conn, pid).location_id
    out = []
    if prof == "formazioni":
        placed = formations.at(conn, loc)
        boost = 1.0
        if placed and placed["kind"] == "uccisione":
            boost = 1.8 + 0.05 * placed["level"]
            fx.p.atk_mult *= 1.0 + 0.04 * placed["level"]
            out.append(f"✦ Combatti dentro la tua Formazione d'Uccisione: il terreno stesso ti obbedisce.")
        else:
            out.append(f"◎ Spieghi la tua formazione mobile ({class_name(conn, pid)}).")
        if placed and placed["kind"] == "difesa":
            fx.p.prof["taken"] = fx.p.prof.get("taken", 0.0) + min(0.3, 0.05 + 0.02 * placed["level"])
        n = len(els)
        for el in els:
            st = STATE_OF_DAO.get(el)
            if st:
                fx.add_proc("p", st, min(0.5, (0.08 + 0.012 * lv) * boost), pw * (1 + 0.15 * (n - 1)),
                            f"formazione:{el}")
        if n >= 2:
            fx.p.atk_mult *= 1.0 + 0.05 * n
    elif prof == "domatore":
        pass                                  # vedi tamer_mult (bestie più forti)
    else:
        for el in els:
            st = STATE_OF_DAO.get(el)
            if st:
                fx.add_proc("p", st, min(0.3, 0.04 + 0.006 * lv), 1.0 + 0.05 * lv, f"aura:{el}")
    return out


def tamer_mult(conn, pid: int, beast_elements: str | None) -> float:
    from engine.systems import professions
    if professions.profession(conn, pid) != "domatore":
        return 1.0
    lv = professions.level(conn, pid)
    m = 1.0 + 0.08 * lv
    els = attunement(conn, pid)
    if beast_elements and any(e in (beast_elements or "").split(",") for e in els):
        m *= 1.0 + 0.05 * lv
    return m


def max_beasts(conn, pid: int) -> int:
    from engine.systems import professions
    if professions.profession(conn, pid) != "domatore":
        return 1
    return 1 + professions.level(conn, pid) // 4


def tame_bonus(conn, pid: int) -> float:
    from engine.systems import professions
    if professions.profession(conn, pid) != "domatore":
        return 0.0
    return min(0.4, 0.04 * professions.level(conn, pid))


def describe(conn, player) -> str:
    from engine.systems import professions
    nm = class_name(conn, player.id)
    if not nm:
        return ("Non hai ancora una classe: scegli un'arte ('profession formazioni', 'profession domatore', "
                "'profession alchimia'…) e sintonizzala su un elemento ('sintonia fuoco').")
    lv = professions.level(conn, player.id)
    els = attunement(conn, player.id)
    lines = [f"Classe: {nm} — livello {lv}"]
    if not els:
        lines.append("Non sei sintonizzato su alcun elemento: 'sintonia <elemento>' per dare forza alla tua arte.")
    lines.append(f"Elementi fondibili: {len(els)}/{max_attune(conn, player.id)} (uno in più ogni 5 livelli).")
    prof = professions.profession(conn, player.id)
    if prof == "formazioni":
        lines.append("In ogni scontro la tua formazione mobile scatena gli stati dei tuoi elementi; "
                     "nelle tue formazioni piazzate ('formazioni') l'effetto è molto maggiore.")
    elif prof == "domatore":
        lines.append(f"Puoi tenere {max_beasts(conn, player.id)} bestie; combattono ×{tamer_mult(conn, player.id, None):.2f}"
                     " (di più se condividono il tuo elemento); domare ti riesce più facile.")
    else:
        lines.append("Il tuo elemento dà un'aura leggera di stati in battaglia.")
    return "\n".join(lines)
