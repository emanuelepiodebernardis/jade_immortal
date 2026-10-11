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


def create(origin: str, destiny: str, name: str, rivals: str) -> str:
    from engine.systems import character, destinies, constitutions
    name = " ".join((name or "Viandante").split())[:32] or "Viandante"
    with LOCK, transaction() as conn:
        if character.has_profile(conn):
            return "Il personaggio esiste già."
        applied = character.apply_origin(conn, origin, random.Random())
        d = destinies.apply(conn, destiny) if destiny in destinies.DESTINIES else None
        if rivals in destinies.RIVAL_LEVELS:
            destinies.set_rival_level(conn, rivals)
        conn.execute("UPDATE players SET name=? WHERE id=1;", (name,))
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
                "vita": rebirth.life_no(conn) + 1}


def reincarnate(origin: str, destiny: str, name: str, inherit_idx: int) -> str:
    from engine.systems import rebirth, character, state
    with LOCK, transaction() as conn:
        row = conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (rebirth.life_no(conn),)).fetchone()
        opts = rebirth.inheritance_options(row) if row else [{"key": "none"}]
        inherit = opts[max(0, min(len(opts) - 1, inherit_idx))]
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
        for n in entities.npcs_in_location(conn, p.location_id)[:30]:
            npcs.append({"name": n.name, "tag": _clean(loop._npc_tag(conn, n) or "")})
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
            "auto": autopilot.config(conn),
        }
    return snap


# ============================================================
# Pannelli (testo dei comandi di sola lettura)
# ============================================================

PANELS = {
    "personaggio": ["status", "rating", "dao", "corpo", "radici", "sangue"],
    "tesori": ["tesori", "arma", "inventory"],
    "storia": ["trama", "goals", "arcinemico", "retaggio", "svolte", "bonds"],
    "mondo": ["era", "regni", "razze", "classifica", "setta", "ritmo"],
    "aiuto": ["help tutto"],
}


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
