"""
IL REGISTA DELLE TRAME — sceglie, giorno per giorno, il momento di storia più adatto.

Non scrive testo nuovo: SCEGLIE. Ogni giorno raccoglie i candidati (l'atto successivo di ogni trama
in corso, o l'inizio di una trama nuova tra quelle scritte in intrigue_data) e dà a ognuno un
punteggio di RILEVANZA, in una passata sola:

  · urgenza       un atto già maturo pesa di più, e ancora di più se aspetta da giorni;
  · legami        le trame che toccano chi conosci (i tuoi legami, la tua setta) pesano di più;
  · presenza      se chi è in scena è vicino a te, l'atto è più naturale adesso;
  · varietà       un tipo di trama appena vissuto (torneo, intrigo, maledizione…) pesa di meno;
  · misura        il regno giusto per la trama; mai più di due trame aperte insieme.

Vince il punteggio più alto: un solo momento di trama al giorno, e solo se non c'è già una scena
aperta. Le trame ricordano INDIZI e RAMI: l'atto finale cambia con quello che sai. Se lasci una
trama a metà troppo a lungo (30 giorni), il mondo la chiude senza di te.

  trame            le trame aperte, gli indizi, chi c'è dentro (anche nel menu Eventi)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "intrigues"
from engine.systems.calibration import (PLOT_MAX_ACTIVE as MAX_ACTIVE, PLOT_NEW_GAP_DAYS as NEW_GAP,   # noqa: E402
                                       PLOT_EXPIRE_DAYS as EXPIRE, PLOT_REPEAT_GAP_DAYS as REPEAT_GAP)


def _templates() -> dict:
    from engine.systems import intrigue_data
    return {t["key"]: t for t in intrigue_data.TEMPLATES}


def get(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {}
    d.setdefault("active", [])
    d.setdefault("done", [])
    d.setdefault("seq", 0)
    d.setdefault("last_start", -999)
    return d


def _save(conn, d: dict) -> None:
    d["done"] = d["done"][-40:]
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


# ============================================================
# Il cast, preso dal mondo vivo
# ============================================================

def _ptier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _alive(conn, nid) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()
    return bool(r and r["status"] == "alive")


def _spawn(conn, rng, player, archetype: str, tier: int, traits: dict | None = None) -> int:
    from engine.systems import npc_factory
    return npc_factory.spawn(conn, rng, archetype=archetype, location_id=player.location_id, tier=max(1, tier),
                             traits=traits, tick=tick_mod.get_tick(conn))


def _cast_one(conn, rng, player, kind: str, taken: set) -> int:
    from engine.systems import sects
    pt = _ptier(conn, player.id)
    mem = sects.get_membership(conn, player.id)
    my_f = mem["faction_id"] if mem else None
    if kind == "alleato":
        rows = conn.execute(
            "SELECT b.npc_id FROM bonds b JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=? AND b.status='active' "
            "AND b.kind IN ('companion','master','disciple','lover','friend') AND n.status='alive' ORDER BY b.id;",
            (player.id,)).fetchall()
        ids = [r["npc_id"] for r in rows if r["npc_id"] not in taken]
        if not ids and my_f:
            ids = [r["id"] for r in conn.execute(
                "SELECT id FROM npcs WHERE faction_id=? AND status='alive' AND (kind IS NULL OR kind='human') "
                "ORDER BY id LIMIT 30;", (my_f,)) if r["id"] not in taken]
        if ids:
            return rng.choice(ids)
        return _spawn(conn, rng, player, "discepolo", pt, {"honor": 70, "loyalty": 60})
    if kind == "rivale":
        rows = conn.execute(
            "SELECT n.id FROM npcs n JOIN cultivation_realms r ON r.id=n.realm_id WHERE n.status='alive' "
            "AND (n.kind IS NULL OR n.kind='human') AND n.faction_id IS NOT NULL AND (? IS NULL OR n.faction_id<>?) "
            "AND r.tier BETWEEN ? AND ? ORDER BY n.id;", (my_f, my_f, pt, pt + 2)).fetchall()
        ids = [r["id"] for r in rows if r["id"] not in taken]
        if ids:
            return rng.choice(ids)
        return _spawn(conn, rng, player, "anziano", pt + 1, {"ambition": 90, "honor": 25, "pride": 80})
    if kind == "genio":
        return _spawn(conn, rng, player, "discepolo", pt + 1, {"pride": 85, "ambition": 85, "courage": 80})
    if kind == "anziano":
        return _spawn(conn, rng, player, "anziano", pt + 1, {"ambition": 60, "honor": 40})
    if kind == "spettro":
        return _spawn(conn, rng, player, "eremita", pt, {"compassion": 10, "honor": 50})
    return _spawn(conn, rng, player, "vagabondo", pt, {"greed": 85, "honor": 20, "courage": 60})


def _cast(conn, rng, player, tpl: dict, d: dict | None = None) -> dict:
    taken: set = set()
    cast = {}
    for role, kind in tpl.get("cast", {}).items():
        if kind.startswith("legame:"):                   # chi è legato a una tua scelta passata
            links = [i for i in ((d or {}).get("links", {}).get(kind.split(":", 1)[1]) or [])
                     if _alive(conn, i) and i not in taken]
            if links:
                cast[role] = links[0]
                taken.add(links[0])
                continue
            kind = "rivale"
        nid = _cast_one(conn, rng, player, kind, taken)
        taken.add(nid)
        cast[role] = nid
    return cast


def _names(conn, it: dict, player) -> dict:
    from engine.systems import sects
    f = {}
    for role, nid in it["cast"].items():
        r = conn.execute("SELECT name, faction_id FROM npcs WHERE id=?;", (nid,)).fetchone()
        f[role] = r["name"] if r else "uno sconosciuto"
    fac = None
    mid = it["cast"].get("mandante")
    if mid:
        r = conn.execute("SELECT f.name FROM npcs n JOIN factions f ON f.id=n.faction_id WHERE n.id=?;", (mid,)).fetchone()
        fac = r["name"] if r else None
    if not fac:
        mem = sects.get_membership(conn, player.id)
        r = conn.execute("SELECT name FROM factions WHERE (? IS NULL OR id<>?) ORDER BY id LIMIT 1;",
                         (mem["faction_id"] if mem else None, mem["faction_id"] if mem else None)).fetchone()
        fac = r["name"] if r else "Setta dell'Ombra"
    mem = sects.get_membership(conn, player.id)
    f.update(_articled("setta", fac))
    f.update(_articled("mia_setta", mem["sect_name"] if mem else "Setta senza nome"))
    loc = conn.execute("SELECT name FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    f["luogo"] = loc["name"] if loc else "qui"
    return f


_MASC = ("Palazzo", "Clan", "Tempio", "Monte", "Padiglione", "Regno", "Santuario", "Culto", "Ordine", "Picco",
         "Monastero", "Sentiero", "Dominio", "Feudo")


def _articled(key: str, name: str) -> dict:
    """«Palazzo della Spada» → il Palazzo…, del Palazzo…, al Palazzo…; «Setta…» → la Setta…, della…, alla…"""
    first = (name or "").split(" ")[0]
    if first[:1].lower() in "aeiou":
        art = {"la": "l'", "della": "dell'", "alla": "all'"}
        sp = ""
    elif first in _MASC:
        art = {"la": "il ", "della": "del ", "alla": "al "}
        sp = None
    else:
        art = {"la": "la ", "della": "della ", "alla": "alla "}
        sp = None
    out = {key: name}
    for k, a in art.items():
        v = f"{a}{name}" if sp is None else f"{a}{name}"
        out[f"{k}_{key}"] = v
        out[f"{k[0].upper() + k[1:]}_{key}"] = v[0].upper() + v[1:]
    return out


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def _fmt(s: str, f: dict) -> str:
    return (s or "").format_map(_Safe(f))


# ============================================================
# Il punteggio (una passata sola: scegliere, non generare)
# ============================================================

def _near(conn, player, nid) -> bool:
    r = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (nid,)).fetchone()
    if not r:
        return False
    if r["location_id"] == player.location_id:
        return True
    return bool(conn.execute("SELECT 1 FROM location_connections WHERE from_location_id=? AND to_location_id=?;",
                             (player.location_id, r["location_id"])).fetchone())


def _bonded(conn, player) -> bool:
    return bool(conn.execute("SELECT 1 FROM bonds WHERE player_id=? AND status='active' AND kind IN "
                             "('companion','master','disciple','lover','friend') LIMIT 1;", (player.id,)).fetchone())


def candidates(conn, player, rng: random.Random) -> list[tuple[float, str, dict]]:
    """[(punteggio, tipo, dati)]: gli atti maturi e le trame che potrebbero cominciare."""
    from engine.systems import sects
    d = get(conn)
    day = _day(conn)
    tpls = _templates()
    out = []
    recent_kinds = {x.get("kind") for x in d["done"] if day - x.get("day", -999) < 20}
    for it in d["active"]:
        if day < it["next_day"]:
            continue
        tpl = tpls.get(it["key"])
        if not tpl:
            continue
        act = tpl["acts"][it["act"]]
        s = 5.0 + 0.3 * (day - it["next_day"])
        foc = act.get("focus")
        if foc and it["cast"].get(foc) and _near(conn, player, it["cast"][foc]):
            s += 1.5
        out.append((s, "atto", it))
    from engine.systems.calibration import PLOT_FIRST_DAY
    if len(d["active"]) < MAX_ACTIVE and day - d["last_start"] >= NEW_GAP and day >= PLOT_FIRST_DAY:
        pt = _ptier(conn, player.id)
        active_keys = {it["key"] for it in d["active"]}
        last_done = {x["key"]: x["day"] for x in d["done"]}
        member = bool(sects.get_membership(conn, player.id))
        bonded = _bonded(conn, player)
        for k, tpl in tpls.items():
            if k in active_keys or pt < tpl.get("tier_min", 1) or (tpl.get("req_sect") and not member):
                continue
            if tpl.get("req_flag") and tpl["req_flag"] not in d.get("flags", []):
                continue                                   # nasce solo da una scelta passata
            if day - last_done.get(k, -999) < REPEAT_GAP:
                continue
            s = 1.0 + 0.4 * tpl.get("weight", 3)
            if "alleato" in tpl.get("cast", {}).values() and bonded:
                s += 1.5                                   # c'è di mezzo qualcuno che conosci
            if tpl.get("req_sect"):
                s += 1.0
            if tpl.get("req_flag"):
                s += 3.0                                   # le conseguenze delle tue scelte arrivano prima
            if tpl.get("kind") in recent_kinds:
                s -= 2.0                                   # varietà
            s -= 0.5 * max(0, pt - tpl.get("tier_min", 1) - 4)   # le trame troppo «basse» stancano
            s += rng.random()                              # un filo di caso
            out.append((s, "nuova", {"key": k}))
    out.sort(key=lambda x: -x[0])
    return out


# ============================================================
# Gli atti
# ============================================================

def _act_scene(conn, player, it: dict, tpl: dict) -> dict:
    act = tpl["acts"][it["act"]]
    f = _names(conn, it, player)
    text = act["text"]
    if act.get("text_low") and it.get("clues", 0) < 2:
        text = act["text_low"]
    for br in it.get("branches", []):
        if br in (act.get("text_branch") or {}):
            text = act["text_branch"][br]
    choices = []
    for ch in act["choices"]:
        if ch.get("need_clues") and it.get("clues", 0) < ch["need_clues"]:
            continue
        if ch.get("need_branch") and ch["need_branch"] not in it.get("branches", []):
            continue
        c = dict(ch, label=_fmt(ch["label"], f))
        for part in ("effects", "success", "failure"):
            if isinstance(c.get(part), dict):
                c[part] = dict(c[part])
                if c[part].get("text"):
                    c[part]["text"] = _fmt(c[part]["text"], f)
        choices.append(c)
    foc = act.get("focus")
    ctx = dict(f)
    ctx["intrigue_id"] = it["id"]
    ctx["title"] = act["title"]
    if foc and it["cast"].get(foc) and _alive(conn, it["cast"][foc]):
        ctx["npc_id"] = it["cast"][foc]
        ctx["npc_name"] = f[foc]
        ctx["npc"] = f[foc]
    # chi deve combattere viene da te: il focus e chi è nominato nei duelli
    movers = {it["cast"][foc]} if foc and it["cast"].get(foc) else set()
    for ch in choices:
        cmd = ch.get("command") or ""
        for role, nid in it["cast"].items():
            if "{" + role + "}" in cmd:
                movers.add(nid)
    for nid in movers:
        if _alive(conn, nid):
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
    title = _fmt(tpl["title"], f)
    n = len(tpl["acts"])
    clues = it.get("clues", 0)
    head = f"{title} — atto {it['act'] + 1}/{n}: {act['title']}" + (f"  (indizi: {clues})" if clues else "")
    return {"key": f"intrigo_{tpl['key']}", "title": head, "event_type": "story", "sticky": True,
            "text": _fmt(text, f), "choices": choices, "ctx": ctx}


def _dead_focus(conn, it: dict, tpl: dict) -> bool:
    foc = tpl["acts"][it["act"]].get("focus")
    return bool(foc and it["cast"].get(foc) and not _alive(conn, it["cast"][foc]))


def _match(it: dict, cond: dict) -> bool:
    if cond.get("need_clues") and it.get("clues", 0) < cond["need_clues"]:
        return False
    if cond.get("max_clues") is not None and it.get("clues", 0) > cond["max_clues"]:
        return False
    if cond.get("need_branch") and cond["need_branch"] not in it.get("branches", []):
        return False
    return True


def _apply(conn, player, it: dict, eff: dict, f: dict) -> list[str]:
    """Effetti di un atto che si risolve da solo (premi, ferite, fama…), senza scelte."""
    from engine.systems import encounters
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 7907 + it["id"])
    eff = dict(eff or {})
    if eff.get("text"):
        eff["text"] = _fmt(eff["text"], f)
    ctx = dict(f)
    ctx.pop("intrigue_id", None)
    return encounters.apply_effects(conn, t, rng, player, eff, ctx)


def _auto_act(conn, player, it: dict, tpl: dict, act: dict) -> str:
    """Un atto che si racconta e si risolve da solo. Se ha dei finali, la trama si conclude col primo
    finale che corrisponde a ciò che sai (indizi) e alle strade prese (rami)."""
    f = _names(conn, it, player)
    title = _fmt(tpl["title"], f)
    lines = [f"✦ {title} — {act['title']} ✦", _fmt(act.get("text", ""), f)]
    if act.get("endings"):
        end = next((e for e in act["endings"] if _match(it, e)), act["endings"][-1])
        lines += _apply(conn, player, it, end.get("effects", {}), f)
        lines.append("✦ " + _finish(conn, it, end.get("outcome", "compiuta"), _fmt(end.get("text", ""), f) or None))
        return "\n".join(x for x in lines if x)
    lines += _apply(conn, player, it, act.get("effects", {}), f)
    d = get(conn)
    cur = next(x for x in d["active"] if x["id"] == it["id"])
    cur["act"] += 1
    if cur["act"] >= len(tpl["acts"]):
        _save(conn, d)
        lines.append("✦ " + _finish(conn, cur, "compiuta"))
    else:
        lo, hi = tpl["acts"][cur["act"]].get("gap", (2, 3))
        cur["next_day"] = _day(conn) + random.Random(cur["id"] * 31 + cur["act"]).randint(lo, hi)
        _save(conn, d)
    return "\n".join(x for x in lines if x)


def play(conn, player, it: dict) -> str | None:
    """Mette in scena l'atto corrente di una trama."""
    from engine.systems import encounters
    tpl = _templates().get(it["key"])
    if not tpl:
        return None
    if tpl["acts"][it["act"]].get("auto"):
        return _auto_act(conn, player, it, tpl, tpl["acts"][it["act"]])
    if _dead_focus(conn, it, tpl):                     # chi doveva esserci è morto: la trama si chiude
        f = _names(conn, it, player)
        _finish(conn, it, "spezzata", f"La trama si spezza: {f.get(tpl['acts'][it['act']]['focus'], 'qualcuno')} è morto prima del tempo.")
        return f"✦ {_fmt(tpl['title'], f)}: la trama si spezza — chi ne teneva i fili è morto."
    return encounters.start_scene(conn, player, _act_scene(conn, player, it, tpl), force=True)


def start(conn, player, key: str, rng: random.Random | None = None) -> str | None:
    """Comincia una trama (il regista la sceglie; i test e i comandi possono forzarla)."""
    tpl = _templates().get(key)
    if not tpl:
        return None
    rng = rng or random.Random(tick_mod.get_tick(conn) * 6151 + player.id)
    d = get(conn)
    d["seq"] += 1
    cast = _cast(conn, rng, player, tpl, d)
    if tpl.get("req_flag") and tpl["req_flag"] in d.get("flags", []):
        d["flags"].remove(tpl["req_flag"])               # la conseguenza si consuma
    it = {"id": d["seq"], "key": key, "cast": cast, "act": 0, "clues": 0,
          "branches": [], "next_day": _day(conn), "start_day": _day(conn)}
    _log(it, f"Comincia: {tpl['acts'][0]['title']}")
    d["active"].append(it)
    d["last_start"] = _day(conn)
    _save(conn, d)
    return play(conn, player, it)


def _finish(conn, it: dict, outcome: str, text: str | None = None) -> str:
    from engine.systems import chronicle
    from engine.core import entities
    tpl = _templates().get(it["key"], {})
    d = get(conn)
    d["active"] = [x for x in d["active"] if x["id"] != it["id"]]
    p = entities.get_player(conn)
    f = _names(conn, it, p) if p else {}
    msg = text or _fmt((tpl.get("outcomes") or {}).get(outcome, "La trama si chiude."), f)
    d["done"].append({"key": it["key"], "kind": tpl.get("kind"), "day": _day(conn), "outcome": outcome,
                      "title": _fmt(tpl.get("title", ""), f), "text": msg, "clues": it.get("clues", 0)})
    _save(conn, d)
    try:
        chronicle.add(conn, "storia", f"{_fmt(tpl.get('title', ''), f)}: {msg}")
    except Exception:  # noqa: BLE001
        pass
    if len([x for x in d["done"] if x.get("outcome") not in ("sfumata", "spezzata")]) == 5:
        state.grant_title(conn, "Tessitore di Trame")
    return msg


# ============================================================
# Il diario e le indagini
# ============================================================

GENERIC_CLUES = ["Qualcosa non torna: c'è una mano che muove i fili.",
                 "Le tracce portano verso {la_setta}.",
                 "Dietro tutto c'è {mandante}."]


def _log(it: dict, text: str) -> None:
    it.setdefault("log", []).append(text)
    it["log"] = it["log"][-12:]


def _clue_list(tpl: dict) -> list[str]:
    return tpl.get("indizi") or (GENERIC_CLUES if tpl.get("need") else [])


def need(tpl: dict) -> int:
    return int(tpl.get("need", 2))


def _reveal(conn, player, it: dict, tpl: dict, n: int, fallback: str = "") -> list[str]:
    """Svela i prossimi n indizi della trama, uno alla volta, nel loro ordine."""
    f = _names(conn, it, player)
    out = []
    lst = _clue_list(tpl)
    before = it.get("clues", 0)
    for _ in range(max(0, n)):
        it["clues"] = it.get("clues", 0) + 1
        idx = len(it.setdefault("found", []))
        txt = (_fmt(lst[idx], f) if idx < len(lst)
               else (fallback or "Un altro tassello conferma ciò che sospettavi."))
        it["found"].append(txt)
        _log(it, "🔎 " + txt)
        out.append(f"🔎 Indizio {it['clues']}: {txt}")
    if (lst and before < need(tpl) <= it["clues"] and tpl.get("reveal_act") is not None
            and it["act"] < tpl["reveal_act"]):
        out.append("⚖ Sai abbastanza: puoi affrontare il colpevole ('trame accusa').")
    return out


def _find(conn, arg: str) -> tuple[dict | None, dict | None, dict]:
    d = get(conn)
    nums = [int(x) for x in arg.split() if x.isdigit()]
    i = nums[0] if nums else 1
    if not (1 <= i <= len(d["active"])):
        return None, None, d
    it = d["active"][i - 1]
    return it, _templates().get(it["key"]), d


def investigate(conn, player, arg: str) -> str:
    """Indaga su una trama aperta: mezza giornata di ricerche e una prova; se riesce, un indizio in più.
    Una sola indagine al giorno per trama."""
    from engine.systems import encounters
    from engine.simulation import world_tick
    it, tpl, d = _find(conn, arg)
    if not it:
        return "Nessuna trama aperta con quel numero ('trame' per l'elenco)."
    lst = _clue_list(tpl)
    if not lst:
        return f"«{_fmt(tpl['title'], _names(conn, it, player))}» non è un mistero da indagare: si vive, atto dopo atto."
    if len(it.get("found", [])) >= len(lst):
        return "Hai già trovato tutto quello che c'era da trovare: ora agisci ('trame accusa')."
    day = _day(conn)
    if it.get("inv_day") == day:
        return "Per oggi hai già indagato su questa trama: le tracce si rinnovano domani."
    it["inv_day"] = day
    rng = random.Random(tick_mod.get_tick(conn) * 9173 + it["id"])
    found = len(it.get("found", []))
    ok, _v, _r = encounters.roll(conn, rng, player.id, {"stat": tpl.get("indagine", "istinto"), "dc": 48 + 6 * found})
    world_tick.advance(conn, 60)                    # mezza giornata di domande, appostamenti, tracce
    f = _names(conn, it, player)
    title = _fmt(tpl["title"], f)
    if ok:
        lines = [f"Indaghi su «{title}»: domande, appostamenti, tracce."] + _reveal(conn, player, it, tpl, 1)
    else:
        _log(it, "Un giorno di ricerche senza frutto.")
        lines = [f"Indaghi su «{title}», ma oggi le tracce non portano da nessuna parte. Domani riprova."]
    _save(conn, d)
    return "\n".join(lines)


def accuse(conn, player, arg: str) -> str:
    """Con abbastanza indizi, vai dritto al colpevole: l'atto della resa dei conti comincia adesso."""
    from engine.systems import encounters
    it, tpl, d = _find(conn, arg)
    if not it:
        return "Nessuna trama aperta con quel numero ('trame' per l'elenco)."
    if encounters.pending(conn):
        return "Prima chiudi la scena in corso."
    if not _clue_list(tpl) or tpl.get("reveal_act") is None:
        return continue_now(conn, player, arg)
    if it.get("clues", 0) < need(tpl):
        return (f"Non sai ancora abbastanza: hai {it.get('clues', 0)} indizi, te ne servono {need(tpl)}. "
                "Indaga ('trame indaga') o segui la trama.")
    if it["act"] < tpl["reveal_act"]:
        it["act"] = tpl["reveal_act"]
        _log(it, "Vai dritto al colpevole.")
    it["next_day"] = _day(conn)
    _save(conn, d)
    return play(conn, player, it) or ""


def continue_now(conn, player, arg: str) -> str:
    from engine.systems import encounters
    it, tpl, d = _find(conn, arg)
    if not it:
        return "Nessuna trama aperta con quel numero ('trame' per l'elenco)."
    if encounters.pending(conn):
        return "Prima chiudi la scena in corso."
    wait = it["next_day"] - _day(conn)
    if wait > 0:
        return f"Il prossimo atto non è ancora maturo: tra {wait} giorni."
    return play(conn, player, it) or ""


def command(conn, player, arg: str) -> str:
    a = arg.strip().lower()
    if a.startswith(("indaga", "investiga")):
        return investigate(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    if a.startswith(("accusa", "smaschera", "colpevole")):
        return accuse(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    if a.startswith(("continua", "avanti", "gioca")):
        return continue_now(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    return describe(conn, player)


def journal(conn, player) -> list[dict]:
    """Per la dashboard: ogni trama aperta col suo diario, gli indizi, e cosa puoi fare adesso."""
    d = get(conn)
    day = _day(conn)
    out = []
    for i, it in enumerate(d["active"], 1):
        tpl = _templates().get(it["key"], {})
        f = _names(conn, it, player)
        acts = tpl.get("acts", [])
        lst = _clue_list(tpl)
        wait = it["next_day"] - day
        nxt = acts[it["act"]]["title"] if it["act"] < len(acts) else ""
        out.append({
            "n": i, "titolo": _fmt(tpl.get("title", ""), f), "tipo": tpl.get("kind", ""),
            "atto": it["act"] + 1, "atti": len(acts), "prossimo": nxt, "attesa": max(0, wait),
            "indizi": it.get("found", []), "servono": need(tpl) if lst else 0, "totale": len(lst),
            "diario": [x for x in it.get("log", []) if not x.startswith("🔎")][-5:],
            "indaga": bool(lst) and len(it.get("found", [])) < len(lst) and it.get("inv_day") != day,
            "indagato_oggi": it.get("inv_day") == day,
            "accusa": bool(lst) and tpl.get("reveal_act") is not None and it.get("clues", 0) >= need(tpl),
            "continua": wait <= 0,
        })
    return out


def _make_enemies(conn, rng, player, it: dict, extra: int, reason: str) -> list[int]:
    """Il cast della trama più `extra` nuovi personaggi (di altre sette) diventano tuoi nemici: il primo
    una nemesi che tornerà a cercarti, gli altri rivali ostili (ti tenderanno agguati se vi incrociate)."""
    from engine.systems import bonds, relations, sects
    t = tick_mod.get_tick(conn)
    ids = [nid for role, nid in it["cast"].items() if role in ("genio", "pedina", "rivale") and _alive(conn, nid)]
    mem = sects.get_membership(conn, player.id)
    facs = [r["id"] for r in conn.execute("SELECT id FROM factions WHERE (? IS NULL OR id<>?) ORDER BY id;",
                                          (mem["faction_id"] if mem else None, mem["faction_id"] if mem else None))]
    for _ in range(extra):
        nid = _spawn(conn, rng, player, "discepolo", _ptier(conn, player.id), {"pride": 80, "ambition": 75})
        if facs:
            conn.execute("UPDATE npcs SET faction_id=? WHERE id=?;", (rng.choice(facs), nid))
        ids.append(nid)
    for i, nid in enumerate(ids):
        relations.adjust(conn, nid, -80, t, player.id)
        kind = "nemesis" if i == 0 else "rival"
        if bonds.add_bond(conn, player.id, nid, kind, t, rng=rng, reason=reason) is None and kind == "nemesis":
            bonds.add_bond(conn, player.id, nid, "rival", t, rng=rng, reason=reason)
    return ids


def on_effect(conn, t: int, rng, player, data: dict, ctx: dict) -> list[str]:
    """Dagli effetti di una scelta: indizi, rami, atto successivo o fine."""
    iid = ctx.get("intrigue_id")
    d = get(conn)
    it = next((x for x in d["active"] if x["id"] == iid), None)
    if not it:
        return []
    tpl = _templates().get(it["key"])
    out = []
    if ctx.get("_choice"):
        _log(it, f"{ctx.get('title', '')}: {ctx['_choice']}")
    if data.get("clue"):
        out += _reveal(conn, player, it, tpl, int(data["clue"]), ctx.get("_text") or "")
    if data.get("branch") and data["branch"] not in it["branches"]:
        it["branches"].append(data["branch"])
    if data.get("enemies") is not None:                 # ti fai nemici tutti quelli che erano lì
        ids = _make_enemies(conn, rng, player, it, int(data["enemies"]), data.get("reason", tpl["title"]))
        f = _names(conn, it, player)
        names = [conn.execute("SELECT name FROM npcs WHERE id=?;", (i,)).fetchone()["name"] for i in ids]
        if names:
            out.append("⚔ Ora ti odiano: " + ", ".join(names) + ". Torneranno a cercarti.")
        if data.get("flag"):
            d.setdefault("links", {})[data["flag"]] = ids
    if data.get("flag"):
        d.setdefault("flags", [])
        if data["flag"] not in d["flags"]:
            d["flags"].append(data["flag"])
    if data.get("end"):
        _save(conn, d)
        return out + ["✦ " + _finish(conn, it, data["end"])]
    it["act"] += 1
    if it["act"] >= len(tpl["acts"]):
        _save(conn, d)
        return out + ["✦ " + _finish(conn, it, "compiuta")]
    lo, hi = tpl["acts"][it["act"]].get("gap", (2, 3))
    it["next_day"] = _day(conn) + rng.randint(lo, hi)
    _save(conn, d)
    out.append(f"(La trama continua tra qualche giorno: «{tpl['acts'][it['act']]['title']}».)")
    return out


# ============================================================
# Ogni giorno
# ============================================================

def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import encounters
    d = get(conn)
    day = _day(conn)
    out = []
    for it in list(d["active"]):                        # le trame dimenticate si chiudono da sole
        if day - it["next_day"] > EXPIRE:
            tpl = _templates().get(it["key"], {})
            ae = tpl.get("auto_end")
            if ae:                                      # alcune si concludono da sole, con quel che sai
                f = _names(conn, it, player)
                end = next((e for e in ae if _match(it, e)), ae[-1])
                lines = _apply(conn, player, it, end.get("effects", {}), f)
                msg = _finish(conn, it, end.get("outcome", "compiuta"), _fmt(end.get("text", ""), f) or None)
                out.append(f"✦ {_fmt(tpl.get('title', ''), f)} si conclude senza di te: {msg}")
                out += lines
                continue
            _finish(conn, it, "sfumata", "Hai lasciato la trama a metà: il mondo è andato avanti senza di te.")
            out.append(f"✦ Una trama si è chiusa senza di te ({tpl.get('title', '')}).")
    if encounters.pending(conn):
        return out
    cands = candidates(conn, player, rng)
    if not cands:
        return out
    score, kind, data = cands[0]
    if kind == "atto":
        txt = play(conn, player, data)
    else:
        if score < 3.0 or rng.random() > 0.45:          # le trame nuove arrivano con misura
            return out
        txt = start(conn, player, data["key"], rng)
    if txt:
        out.append(txt)
    return out


def describe(conn, player) -> str:
    d = get(conn)
    tpls = _templates()
    day = _day(conn)
    lines = ["✦ LE TRAME"]
    if not d["active"]:
        lines.append("  Nessuna trama aperta. Il mondo ne tesse di nuove: tornei, intrighi, eredità, maledizioni.")
    for it in d["active"]:
        tpl = tpls.get(it["key"], {})
        f = _names(conn, it, player)
        acts = tpl.get("acts", [])
        nxt = acts[it["act"]]["title"] if it["act"] < len(acts) else "?"
        wait = it["next_day"] - day
        lines.append(f"  {d['active'].index(it) + 1}. {_fmt(tpl.get('title', ''), f)} — atto {it['act'] + 1}/{len(acts)} «{nxt}» "
                     + (f"tra {wait} giorni" if wait > 0 else "pronto") + f" · indizi {it.get('clues', 0)}"
                     + (f"/{need(tpl)}" if _clue_list(tpl) else ""))
        for x in it.get("found", []):
            lines.append(f"     🔎 {x}")
        if _clue_list(tpl):
            lines.append(f"     'trame indaga {d['active'].index(it) + 1}' per cercare il prossimo indizio"
                         + (f", 'trame accusa {d['active'].index(it) + 1}' per affrontare il colpevole"
                            if it.get("clues", 0) >= need(tpl) and tpl.get("reveal_act") is not None else ""))
    if d["done"]:
        lines.append("  Concluse di recente:")
        for x in d["done"][-4:]:
            lines.append(f"   – {x['title']}: {x['text']}")
    return "\n".join(lines)


def menu_section(conn, player):
    """La sezione «Trame» per il menu Eventi."""
    from engine.systems.menus import act, section
    d = get(conn)
    if not d["active"] and not d["done"]:
        return None
    tpls = _templates()
    day = _day(conn)
    lines = []
    acts = []
    for j in journal(conn, player):
        lines.append(f"{j['titolo']} — atto {j['atto']}/{j['atti']}"
                     + (f", indizi {len(j['indizi'])}/{j['servono']}" if j["servono"] else "")
                     + (f", continua tra {j['attesa']} giorni" if j["attesa"] else ", pronta a continuare"))
        if j["indaga"]:
            acts.append(act(f"🔎 Indaga: {j['titolo']}", f"trame indaga {j['n']}", main=True))
        if j["accusa"]:
            acts.append(act(f"⚖ Affronta il colpevole: {j['titolo']}", f"trame accusa {j['n']}", main=True))
        elif j["continua"]:
            acts.append(act(f"▶ Continua: {j['titolo']}", f"trame continua {j['n']}"))
    for x in d["done"][-2:]:
        lines.append(f"Conclusa: {x['title']} — {x['text']}")
    return section("Trame e intrighi", lines, acts + [act("Le trame in dettaglio", "trame")], icon="🕸")
