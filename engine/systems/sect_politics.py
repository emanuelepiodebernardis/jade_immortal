"""
POLITICA INTERNA DELLA SETTA: anziani, bacheca delle missioni, intrighi.

  anziani               gli anziani della tua setta e il loro favore verso di te
  servi <anziano>       passi la giornata al servizio di un anziano: favore e merito
                        (ma gli anziani sono in competizione: chi ne serve uno, ne irrita un altro)
  missioni              la bacheca delle missioni (cambia ogni giorno)
  missioni accetta <n>  ne prendi una (una alla volta)
  missioni completa     consegni la missione compiuta

Un anziano che ti stima molto (favore ≥ 60) diventa il tuo PROTETTORE: ogni tanto ti
manda doni, e ti difende quando qualcuno trama contro di te.
Più sali, più crescono le invidie: un rivale può INCASTRARTI con false accuse.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state


def _fid(conn, pid):
    from engine.systems import sects
    m = sects.get_membership(conn, pid)
    return m["faction_id"] if m else None


def elders(conn, pid: int) -> list[dict]:
    """Tre anziani della setta (creati se mancano). [{id, name, favor}]"""
    from engine.systems import npc_factory
    from engine.simulation import cultivation
    fid = _fid(conn, pid)
    if not fid:
        return []
    key = f"sect_elders_{fid}"
    data = state.get_json(conn, key, []) or []
    data = [d for d in data if (conn.execute("SELECT status FROM npcs WHERE id=?;", (d["id"],)).fetchone() or
                                {"status": "dead"})["status"] == "alive"]
    if len(data) < 3:
        home = conn.execute("SELECT home_location_id, tier FROM factions WHERE id=?;", (fid,)).fetchone()
        have = {d["id"] for d in data}
        cands = [r["id"] for r in conn.execute(
            "SELECT id FROM npcs WHERE faction_id=? AND archetype='anziano' AND status='alive';", (fid,))
            if r["id"] not in have]
        rng = random.Random(fid * 7 + len(data))
        ptier = cultivation.realm_tier(conn, "player", pid) or 1
        while len(data) < 3:
            nid = cands.pop() if cands else npc_factory.spawn(
                conn, rng, archetype="anziano", location_id=home["home_location_id"],
                tier=max(ptier + 1, (home["tier"] or 1) + 2), faction_id=fid, tick=tick_mod.get_tick(conn))
            nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
            data.append({"id": nid, "name": nm, "favor": 0})
        state.set_json(conn, key, data)
    return data


def _save(conn, pid, data):
    state.set_json(conn, f"sect_elders_{_fid(conn, pid)}", data)


def protector(conn, pid: int) -> dict | None:
    best = max(elders(conn, pid), key=lambda d: d["favor"], default=None)
    return best if best and best["favor"] >= 60 else None


def describe_elders(conn, player) -> str:
    es = elders(conn, player.id)
    if not es:
        return "Non appartieni a nessuna setta."
    lines = ["Gli anziani della setta:"]
    pr = protector(conn, player.id)
    for d in es:
        mark = " — il tuo PROTETTORE" if pr and pr["id"] == d["id"] else ""
        lines.append(f"  · Anziano {d['name']} — favore {d['favor']:+d}{mark}")
    lines.append("'servi <nome>' per guadagnarne il favore (gli altri anziani se ne accorgono).")
    return "\n".join(lines)


def serve(conn, player, name: str) -> str:
    from engine.systems import guild
    from engine.simulation import world_tick
    es = elders(conn, player.id)
    if not es:
        return "Non appartieni a nessuna setta."
    d = next((e for e in es if name.strip().lower() in e["name"].lower()), None) if name.strip() else None
    if d is None:
        return describe_elders(conn, player)
    t = tick_mod.get_tick(conn)
    if state.get_int(conn, "served_day", -1) == t // 120:
        return "Hai già servito un anziano oggi."
    state.set(conn, "served_day", str(t // 120))
    rng = random.Random(t + d["id"])
    gain = rng.randint(6, 12)
    d["favor"] += gain
    others = [e for e in es if e is not d]
    rival = rng.choice(others)
    rival["favor"] -= 3
    _save(conn, player.id, es)
    guild.add_merit(conn, 4, player.id)
    world_tick.advance(conn, 60)
    lines = [f"Passi la giornata a servire l'Anziano {d['name']}: favore +{gain}, merito +4.",
             f"L'Anziano {rival['name']} ti guarda storto (favore -3)."]
    if d["favor"] >= 60 and not state.flag(conn, f"protector_{d['id']}", False):
        state.set(conn, f"protector_{d['id']}", "1")
        lines.append(f"✧ L'Anziano {d['name']} ti prende sotto la sua ala: ora è il tuo PROTETTORE. ✧")
    return "\n".join(lines)


# ---------- bacheca delle missioni ----------

def _board(conn, player) -> list[dict]:
    from engine.simulation import cultivation
    fid = _fid(conn, player.id)
    day = tick_mod.get_tick(conn) // 120
    rng = random.Random(fid * 1009 + day)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    locs = [r["id"] for r in conn.execute("SELECT id FROM locations WHERE location_type!='city';")]
    es = elders(conn, player.id)
    board = []
    for i in range(3):
        kind = rng.choice(["caccia", "raccolta", "pattuglia"])
        el = rng.choice(es)
        if kind == "caccia":
            n = rng.randint(2, 4)
            m = {"kind": kind, "n": n, "text": f"Abbatti {n} nemici o creature."}
        elif kind == "raccolta":
            n = rng.randint(3, 6) * tier
            m = {"kind": kind, "n": n, "text": f"Consegna {n} erbe spirituali alla Sala dell'Alchimia."}
        else:
            loc = rng.choice(locs)
            nm = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
            m = {"kind": kind, "loc": loc, "text": f"Pattuglia {nm} e torna a riferire."}
        m.update({"elder": el["id"], "elder_name": el["name"], "merit": 10 + 5 * tier,
                  "stones": 40 * tier, "id": f"{day}:{i}"})
        board.append(m)
    return board


def missions(conn, player, arg: str) -> str:
    from engine.systems import dao_superiori, professions, guild, sects
    if not _fid(conn, player.id):
        return "La bacheca delle missioni è solo per i membri di una setta."
    p = arg.split()
    cur = state.get_json(conn, "sect_mission")
    if p and p[0] in ("accetta", "accept") and len(p) > 1 and p[1].isdigit():
        if cur:
            return f"Hai già una missione: {cur['text']}"
        b = _board(conn, player)
        i = int(p[1]) - 1
        if not (0 <= i < len(b)):
            return missions(conn, player, "")
        m = b[i]
        if m["kind"] == "caccia":
            m["base"] = state.get_int(conn, "kills_total", 0)
        state.set_json(conn, "sect_mission", m)
        return f"Accetti la missione dell'Anziano {m['elder_name']}: {m['text']}"
    if p and p[0] in ("completa", "consegna", "complete"):
        if not cur:
            return "Non hai missioni in corso."
        ok = False
        if cur["kind"] == "caccia":
            ok = state.get_int(conn, "kills_total", 0) - cur["base"] >= cur["n"]
        elif cur["kind"] == "raccolta":
            ok = professions.spend(conn, player.id, {"erbe": cur["n"]})
        else:
            ok = bool(cur.get("visited"))
        if not ok:
            return f"Non hai ancora finito: {cur['text']}"
        state.delete(conn, "sect_mission")
        guild.add_merit(conn, cur["merit"], player.id)
        sects.grant_resource(conn, "pietre_spirituali", cur["stones"], player.id)
        es = elders(conn, player.id)
        for e in es:
            if e["id"] == cur["elder"]:
                e["favor"] += 5
        _save(conn, player.id, es)
        n = state.get_int(conn, "missions_done", 0) + 1
        state.set(conn, "missions_done", str(n))
        return (f"Missione compiuta! Merito +{cur['merit']}, +{cur['stones']} pietre; "
                f"l'Anziano {cur['elder_name']} annuisce (favore +5).")
    lines = ["BACHECA DELLE MISSIONI (cambia ogni giorno):"]
    for i, m in enumerate(_board(conn, player), 1):
        lines.append(f"  [{i}] {m['text']} — per l'Anziano {m['elder_name']} "
                     f"(merito {m['merit']}, {m['stones']} pietre)")
    if cur:
        lines.append(f"In corso: {cur['text']} ('missioni completa' quando hai finito)")
    else:
        lines.append("'missioni accetta <n>' per prenderne una.")
    return "\n".join(lines)


def on_arrival(conn, player) -> None:
    cur = state.get_json(conn, "sect_mission")
    if cur and cur["kind"] == "pattuglia" and cur["loc"] == player.location_id and not cur.get("visited"):
        cur["visited"] = True
        state.set_json(conn, "sect_mission", cur)


# ---------- intrighi ----------

def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import sects, encounters, items, npc_factory
    m = sects.get_membership(conn, player.id)
    if not m:
        return []
    out = []
    pr = protector(conn, player.id)
    if pr and rng.random() < 0.08:
        lines = items.apply_effects(conn, t, rng, player.id, {"stones": 50 * max(1, m["sect_tier"] or 1)})
        out.append(f"L'Anziano {pr['name']}, tuo protettore, ti fa recapitare un dono. " + " ".join(lines))
    day = t // 120
    if ((m["rank_level"] or 0) >= 2 and not encounters.pending(conn)
            and day - state.get_int(conn, "framed_day", -999) >= 25 and rng.random() < 0.06):
        state.set(conn, "framed_day", str(day))
        hq = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
        prot = f" L'Anziano {pr['name']} ti lancia uno sguardo: «Parla, ragazzo.»" if pr else ""
        sc = {"key": "incastrato", "title": "Falsa accusa", "event_type": "social", "sticky": True,
              "text": (f"Alla Sala della Disciplina, {{npc}}, un discepolo invidioso, ti accusa di aver rubato "
                       f"pillole dal tesoro della setta. Testimoni comprati annuiscono.{prot}"),
              "spawn": {"archetype": "discepolo", "tier_offset": 0, "traits": {"honor": 5, "pride": 90}},
              "choices": [
                  {"label": "Indaghi e smascheri l'inganno", "check": {"stat": "anima", "dc": 55 if pr else 68},
                   "success": {"merit": 15, "fame": 3, "outlaw": 80, "crime": "falsa accusa e furto",
                               "npc_leaves": False, "text": "Le prove si ritorcono contro di lui: viene cacciato."},
                   "failure": {"merit": -20, "text": "Non riesci a provarlo. Paghi tu."}},
                  {"label": "Lo sfidi sulla Piattaforma della Vita e della Morte", "effects": {"fame": 2},
                   "command": "attack {npc}"},
                  {"label": "Chini il capo e accetti la punizione", "effects": {"merit": -10, "karma": 5}},
              ]}
        sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
        if hq and player.location_id == hq["home_location_id"]:
            txt = encounters.start_scene(conn, player, sc)
            if txt:
                out.append(txt)
        else:
            state.set_json(conn, "framed_pending", sc)
            out.append("Ti giunge voce che qualcuno, nella tua setta, sta spargendo calunnie su di te…")
    return out


def on_arrival_scene(conn, player) -> str | None:
    from engine.systems import encounters, sects
    sc = state.get_json(conn, "framed_pending")
    m = sects.get_membership(conn, player.id)
    if not sc or not m or encounters.pending(conn):
        return None
    hq = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if hq["home_location_id"] != player.location_id:
        return None
    state.delete(conn, "framed_pending")
    return encounters.start_scene(conn, player, sc)
