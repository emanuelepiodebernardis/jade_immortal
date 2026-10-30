"""
LE SAGHE (Aggiornamento 74) — le trame a capitoli diventano storie che si seguono come un romanzo.

Le trame legate da un segno (req_flag / legame:) formano già delle catene. Questo modulo le riconosce da
sole (nessun elenco da tenere aggiornato: basta scrivere i capitoli) e aggiunge quattro cose:

  · NEL CAPITOLO PRECEDENTE — quando un capitolo comincia, la scena si apre col riassunto di com'era
    finito il capitolo prima e di cosa avevi scelto;
  · IL PRESAGIO — a metà dell'attesa tra un capitolo e l'altro, una voce, una lettera, un sogno: il
    personaggio che tornerà si fa sentire (campo «teaser» del capitolo, o TEASERS qui sotto);
  · LA MEMORIA — chi ha vissuto la saga con te se la ricorda e te lo dice quando ti incontra (campo
    «memory» del capitolo: {esito: tipo di ricordo}, vedi npc_memory.KINDS);
  · IL LIBRO DELLE SAGHE — Storia → 📚 Saghe: ogni saga che hai toccato, capitolo per capitolo, con il
    prossimo in arrivo e i finali scoperti sul totale (si conservano per sempre, anche oltre le 40 trame
    del diario).
"""

from __future__ import annotations

from engine.systems import state

KEY = "sagas"

# presagi per i capitoli scritti prima dell'Agg. 74 (i nuovi lo portano nel campo «teaser»)
TEASERS = {
    "duello_tre_anni": "Un viandante ti porta un nastro rosso: «{vittima} si allena ogni notte. Dice che conta i giorni.»",
    "nemici_maestro": "Da qualche giorno, quando usi l'arte del maestro della grotta, ti senti osservato.",
    "corte_del_re": "Cavalieri col sigillo reale chiedono di te nelle locande. Portano un ritratto di {vittima}.",
    "ragazzo_esame": "Ti arriva una lettera piena di errori: «Maestro, mi alleno ogni giorno. Presto vi farò onore. — {vittima}»",
    "sangue_reale": "{vittima} ha smesso di firmarsi con il nome da schiavo. Da qualche giorno porta al collo un sigillo d'oro.",
    "seconda_prova": "Nelle notti serene un lampo cade sempre nello stesso punto, poco lontano. Il Cielo prende la mira.",
}
# nomi delle saghe quando il titolo del primo capitolo non basta
TITLES = {"spada_spezzata": "La Spada Spezzata", "mercante_destini": "Il Mercante di Destini",
          "maestro_eterno": "Il Maestro che non muore"}


# ---------------------------------------------------------------- il grafo dei capitoli

def _flags_set(tpl: dict) -> set[str]:
    out = set()
    for act in tpl.get("acts", []):
        for ch in act.get("choices", []):
            for part in (ch.get("effects"), ch.get("success"), ch.get("failure")):
                fl = ((part or {}).get("intrigue") or {}).get("flag")
                if fl:
                    out.add(fl)
        for e in act.get("endings", []):
            if e.get("flag"):
                out.add(e["flag"])
    return out


_CACHE: dict = {}


def graph() -> dict:
    """{"saga_of": {chiave capitolo: chiave saga}, "sagas": {saga: {"title", "chapters", "finals"}}}."""
    if _CACHE:
        return _CACHE
    from engine.systems import intrigues
    tpls = intrigues._templates()
    sets = {k: _flags_set(t) for k, t in tpls.items() if not t.get("arc")}
    needs: dict[str, list[str]] = {}
    for k, t in tpls.items():
        if t.get("req_flag") and not t.get("arc"):
            needs.setdefault(t["req_flag"], []).append(k)
    saga_of, sagas = {}, {}
    roots = [k for k in sets if not tpls[k].get("req_flag") and any(f in needs for f in sets[k])]
    for r in roots:
        seen, todo = [], [r]
        while todo:
            k = todo.pop(0)
            if k in seen:
                continue
            seen.append(k)
            for fl in sets.get(k, ()):
                todo += [n for n in needs.get(fl, []) if n not in seen]
        if len(seen) < 2:
            continue
        for k in seen:
            saga_of.setdefault(k, r)
        finals = [k for k in seen if not any(f in needs for f in sets.get(k, ()))]
        title = TITLES.get(r) or tpls[r]["title"].split(" — ")[0]
        sagas[r] = {"title": title, "chapters": seen, "finals": finals}
    _CACHE.update({"saga_of": saga_of, "sagas": sagas})
    return _CACHE


def _continuing(tpl: dict) -> set[str]:
    """Gli esiti che portano a un altro capitolo (la scelta che chiude il capitolo accende un segno)."""
    out = set()
    for act in tpl.get("acts", []):
        for ch in act.get("choices", []):
            for part in (ch.get("effects"), ch.get("success"), ch.get("failure")):
                d = (part or {}).get("intrigue") or {}
                if d.get("flag") and d.get("end"):
                    out |= {d["end"], d["end"] + "_vinto", d["end"] + "_perso", d["end"] + "_fuga"}
        for e in act.get("endings", []):
            if e.get("flag") and e.get("flag") != tpl.get("req_flag"):
                out.add(e.get("outcome"))
    return out


def endings(saga: str) -> list[str]:
    """Tutti i finali possibili di una saga: «capitolo:esito» degli esiti che non portano oltre."""
    from engine.systems import intrigues
    tpls = intrigues._templates()
    out = []
    for k in graph()["sagas"][saga]["chapters"]:
        t = tpls[k]
        miss = {a.get("outcome") for a in t.get("auto_end", [])}
        outs = set(t.get("outcomes", {}))
        for act in t["acts"]:
            outs |= {e.get("outcome") for e in act.get("endings", [])}
        cont = _continuing(t)
        out += [f"{k}:{o}" for o in sorted(o for o in outs if o) if o not in miss and o not in cont
                and not o.endswith("_fuga") and not o.endswith("_perso") and o != "duello"]
    return out


def endings_total(saga: str) -> int:
    return len(endings(saga))


# ---------------------------------------------------------------- lo stato

def get(conn) -> dict:
    d = state.get_json(conn, KEY, None)
    if d is None:                                        # partite di prima: si ricostruisce dal diario delle trame
        d = {}
        from engine.systems import intrigues
        g = graph()
        for x in intrigues.get(conn).get("done", []):
            saga = g["saga_of"].get(x.get("key"))
            if saga and x.get("outcome") not in ("spezzata", "sfumata"):
                e = _entry(d, saga)
                e["chapters"].append({"key": x["key"], "title": x.get("title", ""), "outcome": x.get("outcome", ""),
                                      "text": x.get("text", ""), "day": x.get("day", 0), "log": []})
                tag = f"{x['key']}:{x.get('outcome')}"
                if tag in endings(saga) and tag not in e["endings"]:
                    e["endings"].append(tag)
                    e["closed"] = True
        state.set_json(conn, KEY, d)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _entry(d: dict, saga: str) -> dict:
    return d.setdefault(saga, {"chapters": [], "endings": [], "teased": []})


# ---------------------------------------------------------------- gli agganci (da intrigues)

def recap(conn, key: str) -> str:
    """Il riassunto del capitolo precedente, per aprire la scena del capitolo che comincia."""
    g = graph()
    saga = g["saga_of"].get(key)
    if not saga or key == saga:
        return ""
    e = get(conn).get(saga)
    if not e or not e["chapters"]:
        return ""
    last = e["chapters"][-1]
    picks = [x.split(": ", 1)[1] for x in last.get("log", []) if ": " in x and not x.startswith(("Comincia", "Duello"))]
    out = f"📖 Nel capitolo precedente: {last['text']}"
    if picks:
        pk = picks[-1]
        out += f" Avevi scelto: {pk}." if "«" in pk else f" Avevi scelto: «{pk}»."
    return out


def on_finish(conn, it: dict, tpl: dict, outcome: str, text: str, title: str, day: int) -> list[str]:
    """Un capitolo è finito: lo scrive nel libro della saga, segna il finale se è l'ultimo, e fa ricordare
    l'esito a chi l'ha vissuto (campo «memory»)."""
    g = graph()
    saga = g["saga_of"].get(it["key"])
    out: list[str] = []
    mem = (tpl.get("memory") or {}).get(outcome) or (tpl.get("memory") or {}).get(outcome.rsplit("_", 1)[0])
    if mem:                                              # «ruolo:ricordo», o solo il ricordo (il protagonista)
        from engine.systems import npc_memory
        role, _, kind = mem.rpartition(":")
        who = it.get("cast", {}).get(role) if role else next(iter(it.get("cast", {}).values()), None)
        if who:
            npc_memory.remember(conn, who, kind, "")
    if not saga or outcome in ("spezzata", "sfumata"):
        return out
    d = get(conn)
    e = _entry(d, saga)
    rec = {"key": it["key"], "title": title, "outcome": outcome, "text": text, "day": day,
           "log": [x for x in it.get("log", []) if not x.startswith("🔎")][-4:]}
    if e["chapters"] and (e["chapters"][-1]["key"], e["chapters"][-1]["outcome"], e["chapters"][-1]["day"]) == \
            (it["key"], outcome, day):
        e["chapters"][-1] = rec                          # già ricostruito dal diario: lo completa
    else:
        e["chapters"].append(rec)
    e["chapters"] = e["chapters"][-30:]
    open_next = bool(set(it.get("flags_set", [])) & {t.get("req_flag") for t in _tpls_of(saga)})
    if not open_next:
        tag = f"{it['key']}:{outcome}"
        is_final = tag in endings(saga)
        if is_final and tag not in e["endings"]:
            e["endings"].append(tag)
            tot = endings_total(saga)
            out.append(f"📚 Finale scoperto: {g['sagas'][saga]['title']} ({len(e['endings'])}/{tot}).")
        e["closed"] = True
    else:
        e["closed"] = False
    _save(conn, d)
    return out


def _tpls_of(saga: str) -> list[dict]:
    from engine.systems import intrigues
    tpls = intrigues._templates()
    return [tpls[k] for k in graph()["sagas"][saga]["chapters"] if k in tpls]


# ---------------------------------------------------------------- il presagio

def _waiting(conn) -> list[tuple[str, dict, int, int]]:
    """[(flag, capitolo, giorni passati, attesa)] per i capitoli che aspettano il loro momento."""
    from engine.systems import intrigues
    d = intrigues.get(conn)
    day = intrigues._day(conn)
    out = []
    for fl in d.get("flags", []):
        for k, t in intrigues._templates().items():
            if t.get("req_flag") == fl:
                out.append((fl, t, day - d.get("flag_days", {}).get(fl, day), t.get("delay", 0)))
    return out


def teaser_text(conn, tpl: dict, flag: str) -> str:
    from engine.systems import intrigues
    txt = tpl.get("teaser") or TEASERS.get(tpl["key"])
    if not txt:
        return ""
    d = intrigues.get(conn)
    links = [i for i in d.get("links", {}).get(flag, []) if intrigues._alive(conn, i)]
    names = {}
    roles = list(tpl.get("cast", {}))
    for role, kind in tpl.get("cast", {}).items():
        if kind == "legame:" + flag and links:
            r = conn.execute("SELECT name FROM npcs WHERE id=?;", (links[0],)).fetchone()
            names[role] = r["name"] if r else "qualcuno"
    for role in roles:
        names.setdefault(role, "qualcuno")
    try:
        return txt.format(**names)
    except (KeyError, IndexError):
        return ""


def daily(conn, t, rng, player) -> list[str]:
    """A metà dell'attesa, il personaggio che tornerà si fa sentire (una volta per capitolo)."""
    g = graph()
    d = get(conn)
    out = []
    changed = False
    for fl, tpl, passed, delay in _waiting(conn):
        saga = g["saga_of"].get(tpl["key"])
        if not saga or delay < 4 or passed < delay // 2:
            continue
        e = _entry(d, saga)
        tag = f"{tpl['key']}:{fl}"
        if tag in e["teased"]:
            continue
        txt = teaser_text(conn, tpl, fl)
        e["teased"].append(tag)
        changed = True
        if txt:
            out.append(f"🕯 {g['sagas'][saga]['title']} — {txt}")
    if changed:
        _save(conn, d)
    return out


# ---------------------------------------------------------------- il libro delle saghe

def book(conn) -> list[dict]:
    """Per la dashboard: le saghe che hai toccato, con i capitoli, il prossimo in arrivo e i finali."""
    from engine.systems import intrigues
    g = graph()
    d = get(conn)
    it_d = intrigues.get(conn)
    active = {x["key"]: x for x in it_d["active"]}
    waiting = {g["saga_of"].get(t["key"]): (t, passed, delay, fl) for fl, t, passed, delay in _waiting(conn)}
    out = []
    for saga, info in g["sagas"].items():
        e = d.get(saga)
        now = next((k for k in info["chapters"] if k in active), None)
        if not e and not now:
            continue
        e = e or {"chapters": [], "endings": [], "teased": []}
        if now:
            stato = "in corso: " + intrigues._templates()[now]["title"].split(" — ")[-1]
        elif saga in waiting:
            t, passed, delay, fl = waiting[saga]
            left = max(0, delay - passed)
            hint = teaser_text(conn, t, fl) if f"{t['key']}:{fl}" in e.get("teased", []) else ""
            stato = ("il prossimo capitolo è vicino" if left == 0 else f"il prossimo capitolo tra circa {left} giorni")
            stato += (f" — {hint}" if hint else "")
        else:
            stato = "conclusa" if e.get("closed") else "in attesa"
        out.append({"saga": saga, "titolo": info["title"], "stato": stato,
                    "capitoli": [{"titolo": c["title"].split(" — ")[-1], "testo": c["text"], "giorno": c["day"]}
                                 for c in e["chapters"]],
                    "finali": len(e.get("endings", [])), "finali_tot": endings_total(saga),
                    "capitoli_tot": len(info["chapters"])})
    return out


def describe(conn) -> str:
    rows = book(conn)
    if not rows:
        return "Nessuna saga ancora: le storie a capitoli cominciano da sole, giorno dopo giorno."
    lines = ["📚 LE TUE SAGHE"]
    for r in rows:
        lines.append(f"  ✦ {r['titolo']} — {r['stato']} · finali scoperti {r['finali']}/{r['finali_tot']}")
        for c in r["capitoli"][-4:]:
            lines.append(f"     · g.{c['giorno']} {c['titolo']}: {c['testo']}")
    return "\n".join(lines)
