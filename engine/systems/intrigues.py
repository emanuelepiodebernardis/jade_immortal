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
MAX_ACTIVE = 2
NEW_GAP = 6                # giorni minimi tra l'inizio di due trame
EXPIRE = 30                # giorni dopo cui un atto non giocato chiude la trama
REPEAT_GAP = 60            # giorni prima che la stessa trama possa tornare


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


def _cast(conn, rng, player, tpl: dict) -> dict:
    taken: set = set()
    cast = {}
    for role, kind in tpl.get("cast", {}).items():
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
    if len(d["active"]) < MAX_ACTIVE and day - d["last_start"] >= NEW_GAP:
        pt = _ptier(conn, player.id)
        active_keys = {it["key"] for it in d["active"]}
        last_done = {x["key"]: x["day"] for x in d["done"]}
        member = bool(sects.get_membership(conn, player.id))
        bonded = _bonded(conn, player)
        for k, tpl in tpls.items():
            if k in active_keys or pt < tpl.get("tier_min", 1) or (tpl.get("req_sect") and not member):
                continue
            if day - last_done.get(k, -999) < REPEAT_GAP:
                continue
            s = 1.0 + 0.4 * tpl.get("weight", 3)
            if "alleato" in tpl.get("cast", {}).values() and bonded:
                s += 1.5                                   # c'è di mezzo qualcuno che conosci
            if tpl.get("req_sect"):
                s += 1.0
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


def play(conn, player, it: dict) -> str | None:
    """Mette in scena l'atto corrente di una trama."""
    from engine.systems import encounters
    tpl = _templates().get(it["key"])
    if not tpl:
        return None
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
    it = {"id": d["seq"], "key": key, "cast": _cast(conn, rng, player, tpl), "act": 0, "clues": 0,
          "branches": [], "next_day": _day(conn), "start_day": _day(conn)}
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


def on_effect(conn, t: int, rng, player, data: dict, ctx: dict) -> list[str]:
    """Dagli effetti di una scelta: indizi, rami, atto successivo o fine."""
    iid = ctx.get("intrigue_id")
    d = get(conn)
    it = next((x for x in d["active"] if x["id"] == iid), None)
    if not it:
        return []
    tpl = _templates().get(it["key"])
    out = []
    if data.get("clue"):
        it["clues"] = it.get("clues", 0) + int(data["clue"])
        out.append(f"🔎 Indizio raccolto (ora {it['clues']}).")
    if data.get("branch") and data["branch"] not in it["branches"]:
        it["branches"].append(data["branch"])
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
            _finish(conn, it, "sfumata", "Hai lasciato la trama a metà: il mondo è andato avanti senza di te.")
            out.append(f"✦ Una trama si è chiusa senza di te ({_templates().get(it['key'], {}).get('title', '')}).")
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
        lines.append(f"  • {_fmt(tpl.get('title', ''), f)} — atto {it['act'] + 1}/{len(acts)} «{nxt}» "
                     + (f"tra {wait} giorni" if wait > 0 else "pronto") + f" · indizi {it.get('clues', 0)}")
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
    for it in d["active"]:
        tpl = tpls.get(it["key"], {})
        f = _names(conn, it, player)
        wait = it["next_day"] - day
        lines.append(f"{_fmt(tpl.get('title', ''), f)} — atto {it['act'] + 1}/{len(tpl.get('acts', []))}, "
                     f"indizi {it.get('clues', 0)}, " + (f"continua tra {wait} giorni" if wait > 0 else "pronta a continuare"))
    for x in d["done"][-2:]:
        lines.append(f"Conclusa: {x['title']} — {x['text']}")
    return section("Trame e intrighi", lines, [act("Le trame in dettaglio", "trame")], icon="🕸")
