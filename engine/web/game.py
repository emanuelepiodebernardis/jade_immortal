"""
Il ponte tra la dashboard e il motore.

La dashboard non ha regole sue: ogni azione passa da `loop.dispatch`, esattamente come nel
terminale, e dopo ogni comando si fa lo stesso giro del loop testuale (alba del nuovo giorno,
report differiti, morte, capitolo della storia, azioni suggerite). In più questo modulo
fornisce i DATI strutturati per i pannelli: stato, luogo, scena in sospeso, mete, mappa.

Tutte le funzioni pubbliche aprono una transazione propria e sono protette da un lucchetto:
il server può essere multi-thread, il gioco no.
"""

from __future__ import annotations

import random
import re
import threading
from collections import deque

from engine.core import entities, tick as tick_mod
from engine.db import transaction

LOCK = threading.RLock()
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(text: str | None) -> str:
    return _ANSI.sub("", text or "")


# ============================================================
# Nuova partita, morte e rinascita
# ============================================================

def phase() -> str:
    """'nuovo' (nessun personaggio), 'morto' (attende la rinascita) o 'gioco'."""
    from engine.systems import character
    with LOCK, transaction() as conn:
        if not character.has_profile(conn):
            return "nuovo"
        p = entities.get_player(conn)
        if p is None or p.status != "alive":
            return "morto"
        return "gioco"


def creation_options(life_no: int = 1) -> dict:
    from engine.systems import character, destinies
    hand = destinies.draw_hand(random.Random(), life_no)
    return {"origini": [{"key": k, "name": o["name"], "desc": o["desc"]} for k, o in character.list_origins()],
            "destini": [{"key": k, "label": destinies.label(k)} for k in hand],
            "rivali": [{"key": k, "label": f"{k.capitalize()} — {v[1]}"} for k, v in destinies.RIVAL_LEVELS.items()]}


def create(origin: str, destiny: str, name: str, rivals: str, hardcore: bool = False) -> str:
    from engine.systems import character, destinies, constitutions, rebirth
    name = " ".join((name or "Viandante").split())[:32] or "Viandante"
    with LOCK, transaction() as conn:
        if character.has_profile(conn):
            return "Il personaggio esiste già."
        applied = character.apply_origin(conn, origin, random.Random())
        d = destinies.apply(conn, destiny) if destiny in destinies.DESTINIES else None
        if rivals in destinies.RIVAL_LEVELS:
            destinies.set_rival_level(conn, rivals)
        conn.execute("UPDATE players SET name=? WHERE id=1;", (name,))
        if hardcore:
            rebirth.set_hardcore(conn, True)
        lines = [f"Sei {name}. Hai scelto: {applied['name']}" + (f", destino «{d['name']}»." if d else ".")]
        lines += constitutions.roll_at_birth(conn, random.Random(), origin)
        lines.append(character.describe_profile(conn))
    return _clean("\n".join(lines)) + "\n\n" + intro()


def death_info() -> dict:
    """Epilogo della vita appena finita (registrato una volta sola) e frammenti ereditabili."""
    from engine.systems import rebirth, state
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        saved = rebirth.try_phoenix(conn, p)
        if saved:
            return {"salvato": _clean(saved)}
        key = "web_death_row"
        row_id = state.get_int(conn, key, -1)
        row = conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (rebirth.life_no(conn),)).fetchone() \
            if row_id == rebirth.life_no(conn) else None
        if row is None:
            row = rebirth.record_death(conn, p)
            state.set(conn, key, str(rebirth.life_no(conn)))
        opts = rebirth.inheritance_options(row)
        return {"epilogo": _clean(rebirth.epilogue_text(row)), "eredita": [o["label"] for o in opts],
                "vita": rebirth.life_no(conn) + 1, "senza_ritorno": rebirth.hardcore(conn),
                "frammenti": rebirth.fragments_allowed(conn, len(opts) - 1),
                "volontaria": bool(rebirth.voluntary_pending(conn))}


def new_world() -> str:
    """Senza Ritorno: archivia il mondo finito e ne genera uno nuovo (poi si crea il personaggio)."""
    from engine.systems import rebirth
    from engine import db as _db
    from engine.generators.world_gen import generate
    with LOCK:
        name = rebirth.archive_world(_db.DB_PATH)
        _db.init_db(_db.DB_PATH)
        with transaction() as conn:
            if not conn.execute("SELECT 1 FROM worlds LIMIT 1;").fetchone():
                generate(conn)
    return f"Il vecchio mondo è conservato in database/saves/{name}. Un nuovo mondo ti attende."


def reincarnate(origin: str, destiny: str, name: str, inherit_idx) -> str:
    from engine.systems import rebirth, character, state
    with LOCK, transaction() as conn:
        row = conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (rebirth.life_no(conn),)).fetchone()
        opts = rebirth.inheritance_options(row) if row else [{"key": "none"}]
        idxs = inherit_idx if isinstance(inherit_idx, list) else [inherit_idx]
        inherit = [opts[max(0, min(len(opts) - 1, int(i)))] for i in idxs][:rebirth.fragments_allowed(conn, len(opts) - 1)]
        lines = rebirth.reincarnate(conn, random.Random(), origin, name or None, inherit, destiny=destiny or None)
        state.delete(conn, "web_death_row")
        lines.append(character.describe_profile(conn))
    return _clean("\n".join(lines)) + "\n\n" + intro()


def intro() -> str:
    from engine.cli import loop, story_cmds
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        out = []
        banner = loop._day_banner(conn, p)
        if banner:
            out.append(banner)
        out.append(loop.render_location(conn, p))
        _after(conn, p)
    return _clean("\n".join(out))


# ============================================================
# Un turno: lo stesso giro del loop testuale
# ============================================================

def _after(conn, player) -> list[str]:
    """Capitolo della storia, risvegli, azioni suggerite (salvate per i pulsanti)."""
    from engine.systems import encounters, suggestions, dao_superiori
    from engine.cli import story_cmds
    from engine.systems import menus
    menus.consume_open(conn)                  # nella dashboard i menu hanno i loro pulsanti
    out = list(dao_superiori.check_awakenings(conn, player.id))
    ch = story_cmds.story_tick(conn, player)
    if ch:
        out.append(ch)
    if encounters.pending(conn):
        suggestions.store(conn, [])
    else:
        sugg = suggestions.compute(conn, player)
        suggestions.store(conn, sugg)
        from engine.systems import state
        state.set_json(conn, "web_sugg", [[lab, cmd] for lab, cmd in sugg])
    return out


def turn(raw: str) -> dict:
    from engine.cli import loop
    from engine.systems import reports
    raw = (raw or "").strip()
    if not raw:
        return {"log": ""}
    with LOCK:
        with transaction() as conn:
            out = loop.dispatch(conn, raw)
        if out is None:
            return {"log": "(Per uscire chiudi la finestra: la partita è già salvata.)"}
        parts = [out] if out else []
        with transaction() as conn:
            p = entities.get_player(conn)
            if p is not None:
                banner = loop._day_banner(conn, p)
                if banner:
                    parts.append(banner)
                parts += reports.drain(conn, p.id)
        with transaction() as conn:
            p = entities.get_player(conn)
            if p is None or p.status != "alive":
                parts.append("Le tue ferite hanno avuto la meglio.")
                return {"log": _clean("\n".join(parts)), "morto": True}
            parts += _after(conn, p)
    return {"log": _clean("\n".join(x for x in parts if x))}


# ============================================================
# Stato per i pannelli
# ============================================================

def _scene(conn, player) -> dict | None:
    from engine.systems import encounters, destinies, perception
    sc = encounters.pending(conn)
    if not sc:
        return None
    choices = []
    for i, ch in enumerate(sc.get("choices", []), 1):
        hint = ""
        chk = ch.get("check")
        if chk:
            p = encounters.chance(encounters.stat_value(conn, player.id, chk.get("stat", "fortuna")),
                                  int(chk.get("dc", 60)))
            word = (f"{int(round(p * 100))}%" if destinies.flag_value(conn, "heaven_eyes", player.id, False)
                    else encounters.chance_word(p))
            hint = f"{encounters.STAT_LABEL.get(chk.get('stat'), chk.get('stat'))}: {word}"
        cmd = ch.get("command") or ""
        if cmd.startswith("attack") and sc.get("ctx", {}).get("npc_id"):
            hint = (hint + " · " if hint else "") + "scontro: ti sembra " + \
                perception.relative_strength(conn, player.id, sc["ctx"]["npc_id"])
        choices.append({"n": i, "label": ch["label"], "hint": hint})
    return {"title": sc.get("title", "Incontro"), "text": sc.get("text", ""), "choices": choices}


def _duel(conn) -> dict | None:
    from engine.systems import duel
    d = duel.get(conn)
    if not d:
        return None
    return {"nome": d["name"], "turno": d["round"], "tu": _bar(max(0, d["hp_p"]), d["pmax"]),
            "lui": _bar(max(0, d["hp_e"]), d["emax"]), "carica": d.get("charge_e", False),
            "concentrato": d.get("focus", False)}


def _bar(cur: float, mx: float) -> dict:
    return {"cur": round(cur), "max": round(mx), "pct": max(0, min(100, round(100 * cur / mx))) if mx else 0}


def state_snapshot() -> dict:
    from engine.simulation import cultivation, combat
    from engine.systems import (qi as qimod, spirit as spmod, lifespan, sects, dao_heart, eras, reputation,
                                state, travel, autopilot, captivity)
    from engine.narrative import varia
    from engine.cli import hud
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        if p is None:
            return {"fase": "nuovo"}
        t = tick_mod.get_tick(conn)
        day, hour = hud.day_and_hour(t)
        rec = cultivation.get_record(conn, "player", p.id)
        loc = entities.get_location(conn, p.location_id)
        wounds = combat.active_injuries(conn, "player", p.id)
        exits = []
        for d, lid in sorted(entities.get_exits(conn, p.location_id).items()):
            r = conn.execute("SELECT name, danger_level FROM locations WHERE id=?;", (lid,)).fetchone()
            exits.append({"dir": d, "name": r["name"] if r else "?", "danger": r["danger_level"] if r else 0})
        npcs = []
        from engine.cli import loop
        from engine.systems import bonds as _bonds
        for n in entities.npcs_in_location(conn, p.location_id)[:40]:
            tag = _clean(loop._npc_tag(conn, n) or "")
            kinds = _bonds.bond_kinds(conn, n.id, p.id) - {"family"}
            # chi conta per te in cima: legami e nemici, ricercati, figure di rango; poi gli altri
            pri = (0 if kinds & {"nemesis", "rival"} else 1 if kinds else
                   2 if "RICERCATO" in tag else 3 if (n.archetype or "") in ("patriarca", "anziano") else
                   5 if (conn.execute("SELECT kind FROM npcs WHERE id=?;", (n.id,)).fetchone()["kind"]
                         or "human") != "human" else 4)
            npcs.append({"name": n.name, "tag": tag, "pri": pri,
                         "rel": "nemico" if kinds & {"nemesis", "rival"} else ("legame" if kinds else "")})
        npcs.sort(key=lambda x: x["pri"])
        dests = []
        for i, d in enumerate(travel.destinations(conn, p), 1):
            dist = travel._distance(conn, p.location_id, d["loc"])
            dests.append({"n": i, "key": d["key"], "title": d["title"], "where": travel._loc_name(conn, d["loc"]),
                          "dist": dist, "join": d["join"]})
        era = eras.get(conn)
        heart = dao_heart.heart(conn)
        snap = {
            "fase": "gioco" if p.status == "alive" else "morto",
            "nome": p.name,
            "regno": cultivation.realm_label(conn, "player", p.id),
            "esperienza": round((rec["progress"] if rec else 0) * 100),
            "qi": _bar(qimod.get_qi(conn, p.id), qimod.max_qi(conn, p.id)),
            "spirito": _bar(spmod.get_spirit(conn, p.id), spmod.max_spirit(conn, p.id)),
            "cuore": {"val": heart, "label": dao_heart.heart_label(heart)},
            "ferite": {"n": len(wounds), "max": max((w["severity"] for w in wounds), default=0)},
            "eta": lifespan.label(conn, p.id),
            "pietre": sects.get_resource(conn, "pietre_spirituali", p.id),
            "fama": reputation.get(conn, p.id)["fame"],
            "giorno": day, "ora": hour,
            "era": eras.ERAS[era["key"]][0],
            "stagione": varia.season(t), "meteo": varia.weather(t), "momento": varia.time_of_day(t),
            "luogo": {"name": loc.name if loc else "?", "type": loc.location_type if loc else "",
                      "danger": loc.danger_level if loc else 0, "desc": loc.description if loc else ""},
            "uscite": exits, "presenti": npcs,
            "scena": _scene(conn, p),
            "suggerimenti": [{"label": a, "cmd": b} for a, b in (state.get_json(conn, "web_sugg", []) or [])],
            "mete": dests,
            "prigioniero": captivity.active(conn),
            "duello": _duel(conn),
            "auto": autopilot.config(conn),
        }
    return snap


# ============================================================
# Pannelli (testo dei comandi di sola lettura)
# ============================================================

PANELS = {
    "personaggio": ["status", "rating", "dao", "corpo", "radici", "sangue"],
    "tesori": ["tesori", "arma"],
    "storia": ["trama", "goals", "arcinemico", "retaggio", "svolte"],
    "legami": ["favori"],
    "mondo": ["era", "ritmo"],
    "aiuto": ["help tutto"],
}


def menu_data(key: str) -> dict:
    """Un menu a sezioni (setta, arti, coltivazione, eventi, regni, famiglia, menu): guardarlo non cambia nulla."""
    from engine.systems import menus
    if key not in menus.NAMES:
        return {"errore": f"menu sconosciuto: {key}"}
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        m = menus.build(conn, p, key)
        conn.rollback()
    return m


def panel(name: str) -> list[dict]:
    from engine.cli import loop
    cmds = PANELS.get(name, [])
    out = []
    with LOCK, transaction() as conn:
        for c in cmds:
            try:
                txt = loop.dispatch(conn, c, allow_nl=False) or ""
            except Exception as e:                     # un pannello rotto non deve rompere gli altri
                txt = f"(non disponibile: {e})"
            out.append({"cmd": c, "text": _clean(txt)})
        conn.rollback()                                # i pannelli guardano, non toccano: nulla cambia
    return out


# ============================================================
# Mappa
# ============================================================

_D = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def map_data(radius: int = 5) -> dict:
    from engine.systems import state, travel, cave_abode
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        start = p.location_id
        pos = {start: (0, 0)}
        q = deque([start])
        while q:
            cur = q.popleft()
            x, y = pos[cur]
            for d, nxt in entities.get_exits(conn, cur).items():
                if d not in _D or nxt in pos:
                    continue
                nx, ny = x + _D[d][0], y + _D[d][1]
                if abs(nx) > radius or abs(ny) > radius or (nx, ny) in pos.values():
                    continue
                pos[nxt] = (nx, ny)
                q.append(nxt)
        visited = set(state.get_json(conn, "world_codex_luoghi", []) or [])
        marks: dict[int, list[str]] = {}
        for d in travel.destinations(conn, p):
            marks.setdefault(d["loc"], []).append(d["title"])
        home = (cave_abode.get(conn, p.id) or {}).get("loc")
        nodes, edges = [], []
        for lid, (x, y) in pos.items():
            r = conn.execute("SELECT name, location_type, danger_level FROM locations WHERE id=?;", (lid,)).fetchone()
            nodes.append({"id": lid, "x": x, "y": y, "name": r["name"], "type": r["location_type"],
                          "danger": r["danger_level"], "here": lid == start, "visited": r["name"] in visited,
                          "marks": marks.get(lid, []), "home": lid == home})
            for d, nxt in entities.get_exits(conn, lid).items():
                if nxt in pos and d in ("east", "south"):
                    edges.append([lid, nxt])
    return {"nodes": nodes, "edges": edges}


# ============================================================
# Pilota automatico, un giorno alla volta (per seguirlo dal vivo)
# ============================================================

STOP = threading.Event()


def auto_day() -> dict:
    """Un giorno di pilota automatico. Ritorna il resoconto e se il pilota si è fermato."""
    from engine.systems import autopilot, encounters, captivity
    from engine.cli import loop
    with LOCK:
        with transaction() as conn:
            p = entities.get_player(conn)
            if p is None or p.status != "alive":
                return {"log": "", "stop": "morto"}
            if encounters.pending(conn):
                return {"log": "", "stop": "c'è una scena in sospeso"}
            if captivity.active(conn):
                return {"log": "", "stop": "sei prigioniero"}
            rep = _clean(autopilot.run(conn, p, 1))
        with transaction() as conn:
            p = entities.get_player(conn)
            dead = p is None or p.status != "alive"
            if not dead:
                _after(conn, p)
    m = re.search(r"si ferma: (.+)", rep)
    stop = "morto" if dead else (m.group(1).strip() if m else None)
    return {"log": rep, "stop": stop}


def summary_snapshot() -> dict:
    """Istantanea per il riepilogo del pilota automatico."""
    from engine.systems import history, feuds, items, state
    from engine.simulation import cultivation
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        if p is None:
            return {}
        s = history.snapshot(conn, p.id)
        s.update({"regno": cultivation.realm_label(conn, "player", p.id),
                  "kills": state.get_int(conn, "kills_total", 0), "titoli": list(state.titles(conn)),
                  "faide": len(feuds.feuds(conn)), "debiti": len(feuds.debts(conn)),
                  "oggetti": sum(r["quantity"] for r in items.player_inventory(conn, p.id))})
        return s


def summary_diff(a: dict, b: dict) -> dict:
    if not a or not b:
        return {}
    pw = (b["power"] / a["power"]) if a.get("power") else 1
    return {"giorni": b["d"] - a["d"], "regno_da": a["regno"], "regno_a": b["regno"],
            "potenza": round(pw, 2), "dao": b["dao"] - a["dao"], "pietre": b["stones"] - a["stones"],
            "fama": b["fame"] - a["fame"], "karma": b["karma"] - a["karma"], "uccisioni": b["kills"] - a["kills"],
            "titoli": [t for t in b["titoli"] if t not in a["titoli"]], "faide": b["faide"] - a["faide"],
            "debiti": b["debiti"] - a["debiti"], "oggetti": b["oggetti"] - a["oggetti"]}


def dao_data() -> list[dict]:
    """I Dao del personaggio con la soglia successiva (per le barre del pannello)."""
    from engine.systems import dao_training as dt, train_all
    with LOCK, transaction() as conn:
        out = []
        for r in dt.trainable_daos(conn, 1):
            c = r["comprehension"] or 0
            nxt = dt.next_threshold(c)
            prev = max([t[0] for t in dt.DAO_THRESHOLDS if t[0] <= c] or [0])
            if nxt:
                goal, label = nxt[0], nxt[1]
            else:                                   # oltre la Legge: le incarnazioni, a ogni raddoppio
                goal, label = max(2000, 1 << (c.bit_length())), "incarnazione"
                prev = goal // 2 if goal > 2000 else 1000
            pct = round(100 * (c - prev) / max(1, goal - prev))
            out.append({"name": r["name"], "short": train_all.short(r["name"]), "comp": c,
                        "label": dt.comprehension_label(c), "next": label, "goal": goal,
                        "pct": max(0, min(100, pct)), "rarity": r["level"]})
    return out


def saves() -> list[dict]:
    import datetime
    from engine.systems import qol
    files = sorted(qol._saves_dir().glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    return [{"name": f.stem, "when": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")}
            for f in files]


# ============================================================
# Schede strutturate: legami, regni, classifiche, zaino, cronaca
# ============================================================

def bonds_data() -> list[dict]:
    from engine.systems import bonds, relations, dialogues, npc_factory
    from engine.simulation import cultivation
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        rows = conn.execute("SELECT b.kind, b.npc_id, b.reason, n.name, n.status, n.location_id FROM bonds b "
                            "JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=? AND b.status='active' "
                            "ORDER BY b.kind, n.name;", (p.id,)).fetchall()
        reqs = dialogues.requests(conn)
        out = []
        for r in rows:
            loc = conn.execute("SELECT name FROM locations WHERE id=?;", (r["location_id"],)).fetchone()
            req = reqs.get(str(r["npc_id"]))
            out.append({"nome": r["name"], "tipo": bonds.KINDS_IT.get(r["kind"], r["kind"]), "kind": r["kind"],
                        "vivo": r["status"] == "alive", "qui": r["location_id"] == p.location_id,
                        "dove": loc["name"] if loc else "?", "rapporto": relations.get_disposition(conn, r["npc_id"]).score,
                        "intimita": dialogues.intimacy(conn, r["npc_id"]),
                        "regno": cultivation.realm_name(conn, "npc", r["npc_id"]),
                        "donna": npc_factory.is_female(conn, r["npc_id"]),
                        "favore": dialogues.describe_one(conn, p, r["npc_id"], req) if req else None,
                        "perche": r["reason"] or ""})
    return out


def world_data() -> dict:
    from engine.systems import kingdoms, rankings, races
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        ks = []
        for _rid, k in kingdoms.all_k(conn).items():
            king = conn.execute("SELECT name FROM npcs WHERE id=?;", (k.get("king"),)).fetchone()
            ks.append({"nome": k["name"], "re": "TU" if k.get("ruler_player") else (king["name"] if king else "—"),
                       "favore": k.get("favor", 0), "rango": kingdoms.rank_of(k.get("favor", 0)),
                       "guerra": bool(k.get("war"))})
        top = []
        for i, (rt, kind, name, _loc, ref) in enumerate(rankings._entries(conn, False), 1):
            if i <= 15 or kind == "player":
                from engine.simulation import cultivation
                top.append({"pos": i, "nome": name, "tu": kind == "player", "potenza": rt,
                            "regno": cultivation.realm_name(conn, kind, ref)})
        allr = races.all_r(conn)
        rc = [{"nome": nm, "rel": allr.get(key, {}).get("rel", 0), "onore": allr.get(key, {}).get("honor", 0),
               "incontrata": allr.get(key, {}).get("met", False)} for key, (nm, *_r) in races.RACES.items()]
    return {"regni": ks, "classifica": top, "razze": rc}


def items_data() -> list[dict]:
    with LOCK, transaction() as conn:
        rows = conn.execute("SELECT i.name, i.item_type, i.rarity, i.description, inv.quantity FROM inventories inv "
                            "JOIN items i ON i.id=inv.item_id WHERE inv.owner_type='player' AND inv.owner_id=1 "
                            "AND inv.quantity>0 ORDER BY CASE i.rarity WHEN 'leggendario' THEN 0 WHEN 'prezioso' THEN 1 "
                            "WHEN 'raro' THEN 2 WHEN 'non_comune' THEN 3 ELSE 4 END, i.name;").fetchall()
        return [{"nome": r["name"], "tipo": r["item_type"], "rarita": r["rarity"] or "comune",
                 "desc": r["description"] or "", "n": r["quantity"]} for r in rows]


def chronicle_data(all_lives: bool = False) -> list[dict]:
    from engine.systems import chronicle
    with LOCK, transaction() as conn:
        return [{"giorno": r["tick"] // 120 + 1, "vita": r["life_no"], "tipo": r["kind"],
                 "icona": chronicle.ICON.get(r["kind"], "·"), "testo": r["text"]}
                for r in chronicle.entries(conn, all_lives)[-300:]]


def merit_preview() -> dict:
    from engine.systems import rebirth
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        if rebirth.hardcore(conn):
            return {"senza_ritorno": True}
        m = rebirth.merit(conn, p.id)
        m["senza_ritorno"] = False
        return m


def voluntary() -> dict:
    from engine.systems import rebirth
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        return {"log": _clean(rebirth.voluntary(conn, p)), "morto": True}


# ============================================================
# Obiettivi (primari, secondari, missioni) e Persone (alleati e nemici, con la potenza)
# ============================================================

def objectives_data() -> dict:
    from engine.systems import (storyline, master_plot, world_arcs, lost_legacy, npc_quests, dialogues, bonds,
                                bounties, secret_masters, sects, sect_politics, system_quest, svolte, beasts)
    from engine.simulation import cultivation
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        prim, sec, mis = [], [], []
        arc = storyline.arc_for(conn, p.id)
        if arc:
            idx = storyline.chapter(conn)
            if idx < len(arc["chapters"]):
                prim.append({"t": f"«{arc['title']}» — capitolo {idx + 1}/{len(arc['chapters'])}: "
                                  + storyline._fill(arc["chapters"][idx]["goal"], conn), "cmd": "goals"})
        prim += [{"t": _clean(g), "cmd": "trama"} for g in master_plot.goals(conn, p)]
        prim += [{"t": _clean(g), "cmd": "goals"} for g in world_arcs.goals(conn)]
        lg = lost_legacy.get(conn)
        if lg:
            nm = lost_legacy.LEGACIES[lg["key"]][0]
            if lg.get("holder"):
                h = conn.execute("SELECT name FROM npcs WHERE id=?;", (lg["holder"],)).fetchone()
                prim.append({"t": f"Retaggio spezzato ({nm}): riprendi il frammento da {h['name'] if h else '?'}",
                             "cmd": "retaggio"})
            else:
                prim.append({"t": f"Retaggio spezzato ({nm}): {lg['found']}/{lost_legacy.FRAGMENTS} frammenti — "
                                  f"il prossimo al regno {lost_legacy._next_tier(lg)}", "cmd": "retaggio"})
        rec = cultivation.get_record(conn, "player", p.id)
        if rec and (rec["stage"] or 1) >= 10 and rec["progress"] >= 1.0:
            prim.append({"t": "Sei al colmo del regno: tenta lo sfondamento", "cmd": "breakthrough"})
        nxt = [m for m in svolte.milestones(conn, p) if not m[2]][:2]
        prim += [{"t": f"Prossima svolta: {nm} — {how}", "cmd": "svolte"} for _i, nm, _d, how in nxt]
        # secondari
        for q in npc_quests.active(conn):
            dest = npc_quests._loc_name(conn, q["dest"]) if q.get("dest") else None
            sec.append({"t": f"Incarico per {npc_quests._name(conn, q['giver'])}: {q['kind']} "
                             f"(passo {q['step']}/{q['chain']})" + (f" → {dest}" if dest else ""),
                        "cmd": f"vai {dest}" if dest and q["dest"] != p.location_id else "incarichi"})
        for nid, req in dialogues.requests(conn).items():
            sec.append({"t": "Favore — " + _clean(dialogues.describe_one(conn, p, int(nid), req)), "cmd": "favori"})
        for nm in bonds.nemeses(conn, p.id):
            sec.append({"t": f"Nemesi: {nm['name']} ti cerca ({nm['reason']})", "cmd": "bonds"})
        ab = bounties.active_bounties(conn)
        if ab:
            sec.append({"t": f"{len(ab)} ricercati con una taglia", "cmd": "bounties"})
        for m in secret_masters.available(conn, p.id):
            sec.append({"t": f"Un maestro segreto è pronto a riceverti: {m['name']}", "cmd": "masters"})
        for r in beasts.active_rare(conn):
            sec.append({"t": f"Bestia {r['rarity']} avvistata: {r['name']} a {r['loc'] or '?'}",
                        "cmd": f"vai {r['loc']}" if r["loc"] else "beast"})
        # missioni
        if sects.get_membership(conn, p.id):
            try:
                for m in sect_politics._board(conn, p):
                    mis.append({"t": f"Setta — {m['text']} (per {m['elder_name']}: {m['merit']} merito, "
                                     f"{m['stones']} pietre)", "cmd": "missioni"})
            except Exception:
                pass
        if system_quest.active(conn):
            d = system_quest.today(conn, p.id)
            for q in d["quests"]:
                pr = min(q["need"], system_quest._progress(conn, p.id, q))
                mis.append({"t": "Sistema — " + system_quest.QUESTS[q["key"]][0].format(n=q["need"])
                                 + (" ✔" if q["done"] else f" ({pr}/{q['need']})"),
                            "cmd": "sistema riscuoti" if pr >= q["need"] and not q["done"] else "sistema"})
    return {"primari": prim, "secondari": sec, "missioni": mis}


def people_data() -> dict:
    from engine.systems import bonds, perception, power, archrival, hunters, dialogues, relations, npc_factory
    from engine.simulation import cultivation
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)

        def card(nid: int, role: str, extra: dict | None = None) -> dict | None:
            r = conn.execute("SELECT name, status, location_id FROM npcs WHERE id=?;", (nid,)).fetchone()
            if not r:
                return None
            alive = r["status"] == "alive"
            loc = conn.execute("SELECT name FROM locations WHERE id=?;", (r["location_id"],)).fetchone()
            c = {"id": nid, "nome": r["name"], "ruolo": role, "vivo": alive, "qui": r["location_id"] == p.location_id,
                 "dove": loc["name"] if loc else "?", "regno": cultivation.realm_name(conn, "npc", nid),
                 "potenza": power.combat_rating(conn, "npc", nid) if alive else 0,
                 "confronto": perception.relative_strength(conn, p.id, nid) if alive else "caduto",
                 "rapporto": relations.get_disposition(conn, nid, p.id).score,
                 "donna": npc_factory.is_female(conn, nid)}
            c.update(extra or {})
            return c

        allies, enemies, seen = [], [], set()
        rows = conn.execute("SELECT kind, npc_id, reason FROM bonds WHERE player_id=? AND status='active' "
                            "ORDER BY kind;", (p.id,)).fetchall()
        reqs = dialogues.requests(conn)
        for r in rows:
            if r["npc_id"] in seen:
                continue
            seen.add(r["npc_id"])
            role = bonds.KINDS_IT.get(r["kind"], r["kind"])
            if r["kind"] == "dao_partner":
                role = "compagna del Dao"
            if r["kind"] == "family" and r["reason"]:
                role = r["reason"]
            if r["kind"] == "nemesis":
                c = card(r["npc_id"], "nemesi", {"perche": r["reason"] or ""})
                if c:
                    enemies.append(c)
                continue
            req = reqs.get(str(r["npc_id"]))
            c = card(r["npc_id"], role, {"intimita": dialogues.intimacy(conn, r["npc_id"]),
                                          "favore": _clean(dialogues.describe_one(conn, p, r["npc_id"], req)) if req else None})
            if c:
                allies.append(c)
        ar = archrival.get(conn)
        if ar and ar["npc"] not in seen:
            seen.add(ar["npc"])
            c = card(ar["npc"], f"arcinemico «{ar['epithet']}» ({ar['gen']}ª generazione)")
            if c:
                enemies.append(c)
        for h in hunters.active_hunters(conn):
            if h["id"] not in seen:
                seen.add(h["id"])
                c = card(h["id"], "cacciatore sulle tue tracce")
                if c:
                    enemies.append(c)
        for r in conn.execute("SELECT r.npc_id FROM npc_player_relations r JOIN npcs n ON n.id=r.npc_id "
                              "WHERE r.player_id=? AND r.score<=-40 AND n.status='alive' ORDER BY r.score LIMIT 12;",
                              (p.id,)).fetchall():
            if r["npc_id"] not in seen:
                seen.add(r["npc_id"])
                c = card(r["npc_id"], "ostile")
                if c:
                    enemies.append(c)
        from engine.systems import feuds
        for f in feuds.feuds(conn):
            if f["npc_id"] not in seen:
                seen.add(f["npc_id"])
                c = card(f["npc_id"], f"{feuds.REL_LABEL.get(f['relation'], '')} di {f['victim_name']} (faida)",
                         {"perche": f"rancore {f['intensity']}/100" + ("" if f["knows"] else " · non sa chi sei")})
                if c:
                    enemies.append(c)
        for d in feuds.debts(conn):
            if d["npc_id"] not in seen:
                seen.add(d["npc_id"])
                c = card(d["npc_id"], "ti deve la vita" if d["status"] == "debito" else "alleato (debito di vita)")
                if c:
                    allies.append(c)
        me = {"potenza": power.combat_rating(conn, "player", p.id), "regno": cultivation.realm_name(conn, "player", p.id)}
    return {"io": me, "alleati": allies, "nemici": enemies}


# ============================================================
# Grafici, rete delle relazioni, Libro
# ============================================================

def charts_data() -> dict:
    """Serie storiche (un punto al giorno) e radar degli attributi."""
    from engine.systems import history
    from engine.simulation import combat
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        cp = combat.combat_power(conn, "player", p.id)
        from engine.systems import qi as qimod, spirit as spmod
        dao = conn.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos WHERE character_type='player' "
                           "AND character_id=?;", (p.id,)).fetchone()["s"]
        radar = {"Attacco": cp["attack"], "Difesa": cp["defense"], "Vitalità": cp["vitality"],
                 "Spirito": spmod.max_spirit(conn, p.id), "Qi": qimod.max_qi(conn, p.id), "Dao": dao}
        hist = history.series(conn)
        if not hist or hist[-1]["d"] != tick_mod.get_tick(conn) // 120 + 1:
            hist = hist + [history.snapshot(conn, p.id)]
    return {"storia": hist, "radar": {k: round(float(v), 1) for k, v in radar.items()}}


def graph_data() -> dict:
    """La rete: famiglia, legami, nemici, faide (con le vittime da cui nascono), debiti di vita."""
    from engine.systems import bonds, feuds, archrival, family, power
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        me = power.combat_rating(conn, "player", p.id) or 1
        nodes, edges, seen = [{"id": "io", "label": p.name, "group": "io", "vivo": True, "qui": True}], [], set()

        def node(nid, group, label=None):
            if nid in seen:
                return
            r = conn.execute("SELECT name, status, location_id FROM npcs WHERE id=?;", (nid,)).fetchone()
            if not r:
                return
            seen.add(nid)
            alive = r["status"] == "alive"
            nodes.append({"id": nid, "label": label or r["name"], "nome": r["name"], "group": group, "vivo": alive,
                          "qui": r["location_id"] == p.location_id, "loc": r["location_id"],
                          "forza": round(power.combat_rating(conn, "npc", nid) / me, 2) if alive else 0})

        fam = family.get(conn)
        for m in (fam or {}).get("members", []):
            node(m["id"], "famiglia")
            edges.append({"a": "io", "b": m["id"], "label": m["role"], "kind": "famiglia"})
        for r in conn.execute("SELECT kind, npc_id, reason FROM bonds WHERE player_id=? AND status='active';",
                              (p.id,)).fetchall():
            if r["kind"] == "family":
                continue
            g = "nemico" if r["kind"] in ("nemesis", "rival") else "legame"
            node(r["npc_id"], g)
            edges.append({"a": "io", "b": r["npc_id"], "label": bonds.KINDS_IT.get(r["kind"], r["kind"]), "kind": g})
        ar = archrival.get(conn)
        if ar:
            node(ar["npc"], "nemico")
            edges.append({"a": "io", "b": ar["npc"], "label": "arcinemico", "kind": "nemico"})
        for f in feuds.feuds(conn):
            node(f["npc_id"], "faida")
            if f["victim_id"]:
                node(f["victim_id"], "vittima")
                edges.append({"a": f["npc_id"], "b": f["victim_id"],
                              "label": feuds.REL_LABEL.get(f["relation"], f["relation"]), "kind": "parentela"})
                edges.append({"a": "io", "b": f["victim_id"], "label": "ucciso da te", "kind": "sangue"})
            edges.append({"a": f["npc_id"], "b": "io", "label": f"vendetta {f['intensity']}", "kind": "faida"})
        for d in feuds.debts(conn):
            node(d["npc_id"], "debito")
            edges.append({"a": d["npc_id"], "b": "io", "label": "ti deve la vita", "kind": "debito"})
    return {"nodi": nodes, "archi": edges}


def book_data() -> dict:
    """Il Libro: tesori, bestie, sangue, reliquie, nemici e maestri — tutto ciò che hai incontrato."""
    import os
    from engine.systems import (items, bloodlines, beasts, celestial_elements, archrival, bonds, feuds,
                                secret_masters, state as st)
    with LOCK, transaction() as conn:
        p = entities.get_player(conn)
        pages = []

        def add(cat, name, sub="", rar="", desc="", facts=None):
            pages.append({"cat": cat, "nome": name, "sub": sub, "rarita": rar or "", "desc": desc or "",
                          "fatti": facts or []})
        inv = {r["name"]: r for r in items.player_inventory(conn, p.id)}
        for nm, r in inv.items():
            add("tesori", nm, r["item_type"], r["rarity"], r["description"], [f"Nello zaino: {r['quantity']}"])
        for nm, e in (st.get_json(conn, "world_book_items", {}) or {}).items():
            if nm not in inv:
                add("tesori", nm, e.get("kind", ""), e.get("rarity", ""), e.get("desc", ""), [f"Ottenuto {e.get('n', 1)} volt{'a' if e.get('n', 1) == 1 else 'e'}"])
        for k, ln in bloodlines.ordered(conn):
            add("sangue", ln.get("name", k), f"sangue di {ln.get('species', '?')}", "leggendario", "",
                [f"Concentrazione: {round(float(ln.get('conc', 0)), 1)}%",
                 "Elementi: " + (", ".join(ln.get("elements") or []) or "—")]
                + ([f"Fuso da: {', '.join(ln['fused_from'])}"] if ln.get("fused_from") else []))
        pet = beasts.pet(conn, p.id)
        if pet:
            tr = beasts.traits(conn, pet["npc_id"])
            add("bestie", pet["name"], f"la tua bestia — {tr['species']}", tr["rarity"], "",
                [f"Talento: {tr['talent']}", f"Elementi: {tr['elements']}"])
        for r in beasts.active_rare(conn):
            add("bestie", r["name"], "bestia rara nel mondo", r["rarity"], "",
                [f"Avvistata a {r['loc']}"] if r["loc"] else [])
        for nm in st.get_json(conn, "world_codex_bestie", []) or []:
            if not any(x["nome"] == nm for x in pages if x["cat"] == "bestie"):
                add("bestie", nm, "incontrata in battaglia", "comune")
        for el, v in (celestial_elements.owned(conn) or {}).items():
            names = v.get("names") or [el]
            pw = float(v.get("power", 0))
            add("reliquie", names[-1], f"elemento celeste ({el})", "leggendario", "",
                [f"Potenza: {round(pw, 1)}", f"Grado: {celestial_elements.grade(pw)}"]
                + ([f"Assorbiti: {', '.join(names)}"] if len(names) > 1 else []))
        ar = archrival.get(conn)
        if ar:
            r = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (ar["npc"],)).fetchone()
            if r:
                add("nemici", r["name"], f"arcinemico «{ar['epithet']}»", "prezioso", "",
                    [f"Generazione: {ar['gen']}", f"Vittorie tue: {ar.get('wins', 0)}", f"Sconfitte: {ar.get('losses', 0)}",
                     "Vivo" if r["status"] == "alive" else "Caduto"])
        for r in bonds.nemeses(conn, p.id):
            add("nemici", r["name"], "nemesi", "raro", "")
        for f in feuds.feuds(conn):
            add("nemici", f["name"], f"{feuds.REL_LABEL.get(f['relation'], '')} di {f['victim_name']}", "raro",
                "Ha giurato vendetta.", [f"Rancore: {f['intensity']}/100", f"Generazione: {f['gen']}"])
        for k in secret_masters.learned(conn):
            add("maestri", str(k), "maestro segreto", "prezioso")
        imgs = []
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "immagini")
        if os.path.isdir(folder):
            imgs = sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")))
        conn.rollback()
    return {"pagine": pages, "immagini": imgs}
