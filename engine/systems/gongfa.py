"""
METODI DI COLTIVAZIONE (功法) — come fai circolare il Qi.

Ogni metodo ha un GRADO (senza tetto) e spesso un ELEMENTO:
  - il grado moltiplica la velocità di coltivazione (+15% a grado);
  - se l'elemento coincide con una tua radice spirituale forte, rende ancora di più
    (fino a raddoppiare il bonus) — un metodo del Fuoco su una radice di Ghiaccio è uno spreco.
  - puoi praticarne uno alla volta; un metodo troppo alto per il tuo regno (grado > regno+2)
    non riesci ancora a sostenerlo.

Dove trovarli: la tua setta te ne consegna uno del suo livello ('gongfa setta' nella sede),
i reami segreti e i maestri ne custodiscono, la casa d'aste li vende, alcuni rotoli si
trovano sui cadaveri dei coltivatori.

  gongfa                    i metodi che conosci e quello che pratichi
  gongfa pratica <n>        cambi metodo
  gongfa setta              ricevi il metodo della tua setta
"""

from __future__ import annotations

import random

from engine.systems import state

GRADE_NAMES = ["Mortale", "della Terra", "del Cielo", "Mistico", "Immortale", "Divino", "Sovrano",
               "Primordiale"]
_PREFIX = ["Sutra", "Canone", "Arte", "Scrittura", "Metodo", "Classico", "Rotolo", "Codice"]
_SUFFIX = ["delle Nove Rivoluzioni", "dell'Ascesa", "del Cuore Immobile", "dei Diecimila Fiumi",
           "della Montagna Celeste", "del Drago Nascosto", "del Loto Eterno", "delle Tre Purezze",
           "del Respiro Primordiale", "della Fenice Rinascente"]
_EL_ADJ = {"legno": "del Legno Verde", "fuoco": "della Fiamma", "terra": "della Terra Profonda",
           "metallo": "del Metallo Puro", "acqua": "dell'Acqua Celeste", "fulmine": "del Tuono",
           "vento": "del Vento", "luce": "della Luce", "oscurita": "dell'Ombra"}


def grade_name(g: int) -> str:
    if g <= len(GRADE_NAMES):
        return GRADE_NAMES[g - 1]
    return f"Oltre il Cielo ({g - len(GRADE_NAMES)}°)"


def generate(rng: random.Random, grade: int, element: str | None = None) -> dict:
    from engine.systems import spirit_roots
    if element is None and rng.random() < 0.75:
        element = rng.choice(spirit_roots.ELEMENTS)
    name = f"{rng.choice(_PREFIX)} {_EL_ADJ[element] if element else rng.choice(_SUFFIX)}"
    if element and rng.random() < 0.5:
        name += " " + rng.choice(_SUFFIX)
    return {"name": name, "grade": max(1, int(grade)), "element": element}


def known(conn, pid: int = 1) -> list[dict]:
    return state.get_json(conn, "gongfa_known", []) or []


def active(conn, pid: int = 1) -> dict | None:
    i = state.get_int(conn, "gongfa_active", -1)
    k = known(conn, pid)
    return k[i] if 0 <= i < len(k) else None


def learn(conn, pid: int, method: dict) -> str:
    k = known(conn, pid)
    if any(m["name"] == method["name"] and m["grade"] == method["grade"] for m in k):
        return f"Conosci già il «{method['name']}»."
    k.append(method)
    state.set_json(conn, "gongfa_known", k)
    msg = f"Impari il metodo «{method['name']}» (grado {grade_name(method['grade'])})."
    cur = active(conn, pid)
    if cur is None or (method["grade"] > cur["grade"] and _usable(conn, pid, method)):
        state.set(conn, "gongfa_active", str(len(k) - 1))
        msg += " Lo pratichi da subito."
    else:
        msg += " ('gongfa pratica' per adottarlo)"
    return msg


def _usable(conn, pid: int, m: dict) -> bool:
    from engine.simulation import cultivation
    return m["grade"] <= (cultivation.realm_tier(conn, "player", pid) or 1) + 2


def mult_of(conn, pid: int, m: dict) -> float:
    from engine.systems import spirit_roots
    base = 0.15 * m["grade"]
    if m.get("element"):
        roots = spirit_roots.get(conn, "player", pid)
        sc = roots.get(m["element"], 0)
        top = max(roots.values()) if roots else 1
        base *= 1.0 + min(1.0, sc / max(1.0, top))          # radice affine: fino a ×2
    return 1.0 + base


def cultivation_mult(conn, pid: int) -> tuple[float, str]:
    m = active(conn, pid)
    if not m or not _usable(conn, pid, m):
        return 1.0, ""
    return mult_of(conn, pid, m), f"il metodo «{m['name']}»"


def from_sect(conn, player) -> str:
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni a nessuna setta."
    hq = conn.execute("SELECT home_location_id, element FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if hq["home_location_id"] != player.location_id:
        return "I metodi della setta si ricevono nella Sala dei Sutra, alla sede."
    rank_lv = (m["rank_level"] or 0)
    grade = max(1, (m["sect_tier"] or 1) + rank_lv // 3)
    key = f"gongfa_sect_{m['faction_id']}_{grade}"
    if state.flag(conn, key, False):
        return "Hai già ricevuto il metodo che il tuo rango ti consente. Sali di rango per accedere a quelli superiori."
    state.set(conn, key, "1")
    el = hq["element"] if hq["element"] in _EL_ADJ else None
    method = generate(random.Random(m["faction_id"] * 911 + grade), grade, el)
    return f"L'anziano della Sala dei Sutra ti consegna un rotolo.\n{learn(conn, player.id, method)}"


def describe(conn, player) -> str:
    k = known(conn, player.id)
    if not k:
        return ("Non conosci alcun metodo di coltivazione: respiri il Qi come un mortale. "
                "La tua setta ('gongfa setta'), i reami segreti e la casa d'aste ne custodiscono.")
    cur = state.get_int(conn, "gongfa_active", -1)
    lines = ["Metodi di coltivazione:"]
    for i, m in enumerate(k):
        el = f", {m['element']}" if m.get("element") else ""
        mark = " ◀ pratichi" if i == cur else ""
        warn = "" if _usable(conn, player.id, m) else " (troppo alto per il tuo regno)"
        lines.append(f"  [{i + 1}] {m['name']} — grado {grade_name(m['grade'])}{el} — "
                     f"×{mult_of(conn, player.id, m):.2f}{mark}{warn}")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    if parts and parts[0].lower() in ("setta", "sect"):
        return from_sect(conn, player)
    if parts and parts[0].lower() in ("pratica", "practice", "usa") and len(parts) > 1 and parts[1].isdigit():
        i = int(parts[1]) - 1
        k = known(conn, player.id)
        if not (0 <= i < len(k)):
            return describe(conn, player)
        if not _usable(conn, player.id, k[i]):
            return "Il tuo regno non regge ancora quel metodo."
        state.set(conn, "gongfa_active", str(i))
        return f"Ora pratichi il «{k[i]['name']}»."
    return describe(conn, player)
