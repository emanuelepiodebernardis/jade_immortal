"""
GLI OBIETTIVI GUIDATI (Aggiornamento 79) — dici dove vuoi arrivare, il gioco ti mostra la strada.

  obiettivo tempesta        una fusione: i componenti, il cuore del Dao, le pietre, poi «fusione tempesta»
  obiettivo ghiaccio        una via nuova: il Dao da cui deriva, le pietre (o la condizione di risveglio)
  obiettivo yinyang         un Dao alto: se una fusione portata in fondo lo apre, il piano passa da lì
  obiettivo spada 250       un Dao fino a una comprensione
  obiettivo alchimia 10     un'arte fino a un livello
  obiettivo                 il piano attuale, passo per passo, con le barre · obiettivo via: lo togli

Il pilota automatico, se c'è un obiettivo, dedica parte delle giornate al passo che manca.
Aggiungere un tipo di obiettivo = un ramo in `_plan`.
"""

from __future__ import annotations

from engine.systems import state

KEY = "goal"


def get(conn) -> dict | None:
    return state.get_json(conn, KEY, None)


def _dao_name(k: str) -> str:
    from engine.systems.dao_techniques import _dao_label
    return _dao_label(k)


def _comp(conn, k: str, pid: int = 1) -> int:
    from engine.systems import dao_laws
    return dao_laws._comp(conn, k, pid)


def _step(text: str, have: float, need: float, cmd: str | None = None) -> dict:
    return {"text": text, "have": int(have), "need": int(need), "done": have >= need, "cmd": cmd}


def _fusion_steps(conn, key: str, pid: int) -> list[dict]:
    from engine.systems import dao_laws, dao_heart, sects
    from engine.simulation import cultivation
    st = dao_laws.recipe_status(conn, key, pid)
    out = []
    for c, v in dao_laws.requirement_of(conn, key).items():
        out += _dao_reach(conn, c, v, pid)
    light = dao_laws.is_light(key)
    out.append(_step("Cuore del Dao saldo (riposa, mantieni le promesse, non deviare)", dao_heart.heart(conn),
                     dao_laws.LIGHT_HEART if light else dao_laws.FUSE_HEART, None))
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    out.append(_step("Pietre spirituali per il ritiro", sects.get_resource(conn, "pietre_spirituali", pid),
                     (300 if light else 1500) * tier, None))
    if st["risk"]:
        out.append(_step("Un ponte tra le vie in conflitto (o un'intuizione da reperti e nemici)", 0, 1, "reperti"))
    out.append(_step(f"Fondi: {dao_laws.FUSED[key][1]}", 1 if dao_laws._has(conn, key, pid) else 0, 1, f"fusione {key}"))
    return out


def _dao_reach(conn, key: str, n: int, pid: int) -> list[dict]:
    """Arrivare a `key` ≥ n: prima averlo (aprirlo, fonderlo o risvegliarlo), poi allenarlo."""
    from engine.systems import dao_laws
    if dao_laws._has(conn, key, pid):
        return [_step(f"{_dao_name(key)} a {n}", _comp(conn, key, pid), n, f"comprehend {key}")]
    if key in dao_laws.FUSED:
        return _fusion_steps(conn, key, pid) + [_step(f"{_dao_name(key)} a {n}", 0, n, f"comprehend {key}")]
    return _open_steps(conn, key, pid) + [_step(f"{_dao_name(key)} a {n}", 0, n, f"comprehend {key}")]


def _open_steps(conn, key: str, pid: int) -> list[dict]:
    from engine.systems import dao_laws, sects
    if dao_laws._has(conn, key, pid):
        return []
    row = dao_laws.BY_KEY.get(key)
    if row:
        kind = row[4][0]
        if kind == "derivato":
            base, v = min(row[4][1].items(), key=lambda kv: max(0, kv[1] - _comp(conn, kv[0], pid)))
            out = _dao_reach(conn, base, v, pid)
            return out + [_step(f"Apri il {row[1]}", 0, 1, f"comprehend {key}"),
                          _step("Pietre per lo studio", sects.get_resource(conn, "pietre_spirituali", pid),
                                dao_laws.learn_cost(conn))]
        if kind == "scelta":
            return [_step("Pietre per lo studio", sects.get_resource(conn, "pietre_spirituali", pid),
                          dao_laws.learn_cost(conn)), _step(f"Apri il {row[1]}", 0, 1, f"comprehend {key}")]
        return [_step(f"Il {row[1]} si risveglia da solo: {_awake_hint(key)}", 0, 1, None)]
    # un Dao alto che una fusione portata in fondo può mostrarti
    for fk, steps in dao_laws.INSIGHT.items():
        for th, d in steps:
            if d == key:
                return _dao_reach(conn, fk, th, pid)
    if key in dao_laws.BASE_STUDY:
        return [_step("Pietre per studiarlo", sects.get_resource(conn, "pietre_spirituali", pid), 2 * dao_laws.learn_cost(conn)),
                _step(f"Studia il {_dao_name(key)} (o: scorci, reperti, assorbimento)", 0, 1, f"comprehend {key}")]
    from engine.systems import dao_insight
    sc = dao_insight._data(conn)["scorci"].get(key, 0)
    need = dao_insight.GLIMPSES_HIGH if dao_insight._is_high(key) else dao_insight.GLIMPSES
    return [_step(f"Apri il {_dao_name(key)}: scorci da chi lo usa meglio di te e dai reperti (o assorbi chi lo "
                  f"conosce)", sc, need, "reperti")]


_AWAKE = {"volonta": "cuore del Dao ≥ 80 e almeno il terzo regno", "annientamento": "Massacro ≥ 100 e Vuoto ≥ 25",
          "ordine": "cuore del Dao ≥ 90 e una setta", "ciclo": "Stagioni ≥ 50, o tutti e cinque gli elementi ≥ 25",
          "origine": "cuore del Dao ≥ 90 e due Dao a 1000", "divoramento": "aver divorato otto persone",
          "maledizione": "karma ≤ −150", "morti": "Vita e Morte ≥ 25 e Oscurità ≥ 25",
          "follia": "Massacro ≥ 50, karma ≤ −100, trenta uccisioni"}


def _awake_hint(key: str) -> str:
    return _AWAKE.get(key, "una condizione del mondo")


def _plan(conn, g: dict, pid: int = 1) -> tuple[str, list[dict]]:
    from engine.systems import dao_laws, professions
    k, n = g["key"], g.get("n")
    if g["kind"] == "arte":
        lv = professions.level(conn, pid, k)
        title = f"{professions.PROFESSIONS[k]} al livello {n}"
        first = [] if professions.has(conn, k, pid) else [_step(f"Impara l'arte {professions.PROFESSIONS[k]}", 0, 1,
                                                                f"arti {k}")]
        return title, first + [_step(f"{professions.PROFESSIONS[k]} livello {n}", lv, n, "train")]
    if k in dao_laws.FUSED and not n:
        return dao_laws.FUSED[k][1], _fusion_steps(conn, k, pid)
    if n:
        return f"{_dao_name(k)} a {n}", _dao_reach(conn, k, n, pid)
    return _dao_name(k), _open_steps(conn, k, pid) or [_step(f"Hai il {_dao_name(k)}", 1, 1, None)]


def plan(conn, pid: int = 1) -> dict | None:
    g = get(conn)
    if not g:
        return None
    title, steps = _plan(conn, g, pid)
    # passi duplicati (lo stesso Dao chiesto due volte): resta il più alto
    seen: dict[str, dict] = {}
    for s in steps:
        if s["text"] in seen:
            continue
        seen[s["text"]] = s
    steps = list(seen.values())
    done = sum(1 for s in steps if s["done"])
    nxt = next((s for s in steps if not s["done"]), None)
    return {"title": title, "steps": steps, "done": done, "total": len(steps), "complete": nxt is None,
            "next": nxt}


def next_cmd(conn, pid: int = 1) -> str | None:
    p = plan(conn, pid)
    if not p or p["complete"]:
        return None
    for s in p["steps"]:
        if not s["done"] and s["cmd"]:
            return s["cmd"]
    return None


def _parse(arg: str) -> tuple[dict | None, str]:
    from engine.systems import dao_laws, professions
    words = [w for w in (arg or "").lower().split() if w not in ("il", "la", "lo", "dao", "del", "della", "arte",
                                                                    "livello", "a", "al", "fino")]
    n = next((int(w) for w in words if w.isdigit()), None)
    words = [w for w in words if not w.isdigit()]
    if not words:
        return None, ""
    text = " ".join(words)
    pk = professions._key(text) if hasattr(professions, "_key") else None
    if pk:
        return {"kind": "arte", "key": pk, "n": n or 10}, ""
    k = dao_laws.find(text) or dao_laws._key_of(text) or next((dao_laws._key_of(w) for w in words
                                                                if dao_laws._key_of(w)), None)
    if not k:
        return None, f"Non riconosco «{text}» come Dao, fusione o arte. Prova 'vie', 'fusione' o 'arti'."
    return {"kind": "dao", "key": k, "n": n}, ""


def _bar(done: int, total: int, w: int = 12) -> str:
    f = round(w * done / max(1, total))
    return "█" * f + "·" * (w - f)


def describe(conn, pid: int = 1) -> str:
    p = plan(conn, pid)
    if not p:
        return ("🎯 Nessun obiettivo. Scrivi 'obiettivo <meta>': una fusione (tempesta), una via (ghiaccio), un Dao alto "
                "(yinyang), un Dao a una soglia (spada 250) o un'arte a un livello (alchimia 10).")
    lines = [f"🎯 OBIETTIVO — {p['title']}  [{_bar(p['done'], p['total'])}] {p['done']}/{p['total']}"]
    for s in p["steps"]:
        mark = "✔" if s["done"] else ("▶" if s is p["next"] else "·")
        num = f" ({s['have']}/{s['need']})" if s["need"] > 1 else ""
        cmd = f"  → '{s['cmd']}'" if s is p["next"] and s["cmd"] else ""
        lines.append(f"  {mark} {s['text']}{num}{cmd}")
    if p["complete"]:
        lines.append("✦ Obiettivo raggiunto! Scegline un altro.")
    else:
        lines.append("Il pilota automatico dedica parte delle giornate al passo che manca. ('obiettivo via' per toglierlo)")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    if not a:
        return describe(conn, player.id)
    if a in ("via", "togli", "nessuno", "annulla", "cancella"):
        state.delete(conn, KEY)
        return "🎯 Obiettivo tolto."
    g, err = _parse(a)
    if not g:
        return err
    state.set_json(conn, KEY, g)
    return describe(conn, player.id)


def hud_line(conn, pid: int = 1) -> str:
    p = plan(conn, pid)
    if not p:
        return ""
    if p["complete"]:
        return f"🎯 {p['title']}: raggiunto!"
    return f"🎯 {p['title']} {p['done']}/{p['total']} — ora: {p['next']['text']}"


def menu_section(conn, player):
    from engine.systems.menus import act, bar, section
    p = plan(conn, player.id)
    if not p:
        return section("Obiettivo", ["Nessun obiettivo: scrivi 'obiettivo <meta>' (tempesta, ghiaccio, spada 250, "
                                     "alchimia 10…)."], [], icon="🎯")
    lines = [("✔ " if s["done"] else "· ") + s["text"] + (f" ({s['have']}/{s['need']})" if s["need"] > 1 else "")
             for s in p["steps"]]
    acts = []
    if p["next"] and p["next"]["cmd"]:
        acts.append(act(f"Prossimo passo: {p['next']['text']}", p["next"]["cmd"], main=True))
    acts.append(act("Togli l'obiettivo", "obiettivo via"))
    return section(f"Obiettivo: {p['title']}", lines, acts, icon="🎯",
                   bars=[bar("Avanzamento", 100 * p["done"] / max(1, p["total"]), f"{p['done']}/{p['total']}")])
