"""
LA TUA FAMIGLIA — genitori, fratelli, il clan da proteggere (o da vendicare).

All'inizio di ogni vita hai una famiglia nella città da cui parti. Non combattono per te,
ma ti vogliono bene: andarli a trovare ('famiglia visita', una volta ogni 10 giorni) calma il
cuore del Dao, e da giovane i genitori ti danno quel poco che hanno.

Ma chi ha qualcosa da perdere, ha nemici: di tanto in tanto un clan rivale minaccia i tuoi.
Hai pochi giorni per tornare e difenderli ('famiglia difendi'). Se non ci sei, qualcuno
può non sopravvivere — e chi l'ha ucciso diventa la tua nemesi.

Il clan cresce con te, senza fine: ogni tuo regno e ogni dono ('famiglia dona <pietre>')
ne alza il LIVELLO: più prestigio, rendite che ti arrivano, parenti più forti.
Dal settimo regno puoi riportare in vita un familiare caduto ('famiglia resuscita <nome>'),
pagando con anni della tua vita.

  famiglia                       la tua famiglia e il clan
  famiglia visita | difendi | dona <pietre> | resuscita <nome>
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "family"
_SURNAMES = ["Lin", "Xiao", "Ye", "Han", "Mo", "Shi", "Bai", "Su", "Gu", "Tang"]
_ROLES = [("padre", "anziano"), ("madre", "eremita"), ("sorella minore", "discepolo"), ("fratello maggiore", "guardia")]


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def create(conn, rng: random.Random, player) -> list[str]:
    from engine.systems import npc_factory, bonds
    if get(conn):
        return []
    sur = rng.choice(_SURNAMES)
    loc = player.location_id
    members = []
    for role, arch in rng.sample(_ROLES, 3):
        given = npc_factory.unique_name(rng, conn=conn).split()[-1]
        nid = npc_factory.spawn(conn, rng, archetype=arch, location_id=loc, tier=1, stage=rng.randint(1, 4),
                                name=f"{sur} {given}", traits={"loyalty": 95, "compassion": 80})
        bonds.add_bond(conn, player.id, nid, "family", tick_mod.get_tick(conn), reason=role)
        members.append({"id": nid, "role": role})
    _save(conn, {"clan": f"Famiglia {sur}", "home": loc, "members": members, "level": 1, "gifts": 0,
                 "threat": None, "last_visit": -99})
    return [f"Hai una famiglia: la Famiglia {sur}, a casa tua. ('famiglia')"]


def _alive(conn, nid) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()
    return bool(r) and r["status"] == "alive"


def _name(conn, nid) -> str:
    return conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]


def level_need(lv: int) -> int:
    return int(200 * (1.6 ** (lv - 1)))


def donate(conn, player, arg: str) -> str:
    from engine.systems import sects
    d = get(conn)
    if not d:
        return "Non hai una famiglia in questa vita."
    n = int(arg) if arg.strip().isdigit() else 0
    if n <= 0 or sects.get_resource(conn, "pietre_spirituali", player.id) < n:
        return "Usa: famiglia dona <pietre> (quante ne hai)."
    sects.grant_resource(conn, "pietre_spirituali", -n, player.id)
    d["gifts"] += n
    out = [f"Mandi {n} pietre alla {d['clan']}: costruiscono, assumono maestri, crescono."]
    while d["gifts"] >= level_need(d["level"]):
        d["gifts"] -= level_need(d["level"])
        d["level"] += 1
        out.append(f"✦ La {d['clan']} sale al livello {d['level']}: il suo nome pesa sempre di più.")
        _raise_members(conn, d)
    _save(conn, d)
    return "\n".join(out)


def _raise_members(conn, d: dict) -> None:
    from engine.systems import npc_factory
    for m in d["members"]:
        if _alive(conn, m["id"]):
            npc_factory.raise_npc(conn, m["id"], 2)


def visit(conn, player) -> str:
    from engine.systems import dao_heart, sects
    from engine.simulation import cultivation
    d = get(conn)
    if not d:
        return "Non hai una famiglia in questa vita."
    if player.location_id != d["home"]:
        return "La tua famiglia vive altrove: torna a casa per visitarla."
    day = tick_mod.get_tick(conn) // 120
    if day - d.get("last_visit", -99) < 10:
        return "Li hai visti da poco: la tua famiglia sta bene."
    d["last_visit"] = day
    _save(conn, d)
    alive = [m for m in d["members"] if _alive(conn, m["id"])]
    if not alive:
        return "La casa è vuota. Solo ricordi."
    lines = ["Ceni con la tua famiglia. Per una sera non sei un coltivatore: sei solo a casa."]
    lines += dao_heart.adjust(conn, 6)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    gift = 20 * d["level"] if tier <= 2 else 10 * d["level"] * tier
    sects.grant_resource(conn, "pietre_spirituali", gift, player.id)
    lines.append(f"Al momento di partire ti mettono in mano un sacchetto: {gift} pietre spirituali.")
    return "\n".join(lines)


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import sects, bonds, npc_factory
    from engine.simulation import cultivation
    d = get(conn)
    if not d:
        return []
    out = []
    day = t // 120
    # rendita del clan
    if d["level"] >= 3 and day % 5 == 0:
        sects.grant_resource(conn, "pietre_spirituali", 5 * d["level"], player.id)
    th = d.get("threat")
    if th and day > th["deadline"]:
        d["threat"] = None
        alive = [m for m in d["members"] if _alive(conn, m["id"])]
        if alive and rng.random() < 0.6:
            v = rng.choice(alive)
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (t, v["id"]))
            out.append(f"✝ Non sei tornato in tempo. {th['enemy']} ha colpito la tua famiglia: tuo {v['role']} "
                       f"{_name(conn, v['id'])} è caduto.")
            if th.get("npc") and _alive(conn, th["npc"]):
                bonds.add_bond(conn, player.id, th["npc"], "nemesis", t, rng=rng, reason="ha ucciso la tua famiglia")
        else:
            out.append(f"{th['enemy']} ha devastato la casa della tua famiglia. Sono vivi, ma terrorizzati.")
        from engine.systems import dao_heart
        out += dao_heart.adjust(conn, -8)
    elif not th and day >= 6 and rng.random() < 0.025 and any(_alive(conn, m["id"]) for m in d["members"]):
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        nid = npc_factory.spawn(conn, rng, archetype="guardia", location_id=None, tier=tier, stage=rng.randint(3, 8),
                                traits={"compassion": 5, "pride": 90})
        enemy = f"{_name(conn, nid)} del Clan {rng.choice(_SURNAMES)}"
        d["threat"] = {"enemy": enemy, "npc": nid, "deadline": day + 4}
        hname = conn.execute("SELECT name FROM locations WHERE id=?;", (d["home"],)).fetchone()["name"]
        out.append(f"⚠ {enemy} minaccia la tua famiglia a {hname}! Hai 4 giorni per tornare ('famiglia difendi').")
    _save(conn, d)
    return out


def defend(conn, player) -> str:
    from engine.systems import encounters
    d = get(conn)
    if not d or not d.get("threat"):
        return "Nessuno minaccia la tua famiglia, ora."
    if player.location_id != d["home"]:
        return "Devi essere a casa per difenderli."
    th = d["threat"]
    nid = th.get("npc")
    if nid and _alive(conn, nid):
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
    d["threat"] = None
    _save(conn, d)
    sc = {"key": "famiglia_minacciata", "title": "La tua famiglia", "event_type": "bond",
          "text": f"{th['enemy']} è sulla soglia di casa tua, e ride. Dietro di te, i tuoi ti guardano.",
          "ctx": {"npc_id": nid, "npc_name": _name(conn, nid)} if nid else {},
          "choices": [{"label": "Lo affronti", "effects": {"heart": 4, "fame": 2},
                       "command": f"attack {_name(conn, nid)}" if nid else None},
                      {"label": "Paghi perché se ne vada", "effects": {"stones": -100 * d["level"], "npc_leaves": True}}]}
    return encounters.start_scene(conn, player, sc, force=True) or ""


def resurrect(conn, player, name: str) -> str:
    from engine.systems import lifespan, dao_heart
    from engine.simulation import cultivation
    d = get(conn)
    if not d:
        return "Non hai una famiglia in questa vita."
    if (cultivation.realm_tier(conn, "player", player.id) or 1) < 7:
        return "Strappare un'anima alla morte richiede almeno il settimo regno."
    m = next((m for m in d["members"] if name.strip().lower() in _name(conn, m["id"]).lower()
              and not _alive(conn, m["id"])), None)
    if not m:
        return "Non c'è nessun familiare caduto con quel nome."
    years = 50
    if lifespan.max_years(conn, player.id) - lifespan.age_years(conn, player.id) < years + 5:
        return f"Ti servono almeno {years} anni di vita da offrire."
    lifespan.add_bonus_years(conn, -years)
    conn.execute("UPDATE npcs SET status='alive', location_id=? WHERE id=?;", (d["home"], m["id"]))
    dao_heart.adjust(conn, 15)
    state.grant_title(conn, "Colui che Sfidò la Morte")
    return (f"Bruci {years} anni della tua vita in un rito proibito. {_name(conn, m['id'])} apre gli occhi: "
            "è tornato. ✧ Nuovo titolo: «Colui che Sfidò la Morte» ✧")


def on_realm_up(conn) -> list[str]:
    d = get(conn)
    if not d:
        return []
    d["level"] += 1
    _raise_members(conn, d)
    _save(conn, d)
    return [f"La notizia del tuo nuovo regno raggiunge casa: la {d['clan']} sale al livello {d['level']}."]


def describe(conn, player) -> str:
    d = get(conn)
    if not d:
        return "Non hai una famiglia in questa vita."
    from engine.simulation import cultivation
    hname = conn.execute("SELECT name FROM locations WHERE id=?;", (d["home"],)).fetchone()["name"]
    lines = [f"🏠 {d['clan']} — a {hname} — livello {d['level']} (doni {d['gifts']}/{level_need(d['level'])})"]
    for m in d["members"]:
        st = cultivation.realm_label(conn, "npc", m["id"]) if _alive(conn, m["id"]) else "✝ caduto"
        lines.append(f"  · {m['role']}: {_name(conn, m['id'])} — {st}")
    if d.get("threat"):
        lines.append(f"  ⚠ {d['threat']['enemy']} li minaccia! ('famiglia difendi' a casa)")
    lines.append("  'famiglia visita' (ogni 10 giorni), 'famiglia dona <pietre>', 'famiglia resuscita <nome>' (regno 7+)")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    if sub in ("visita", "visit"):
        return visit(conn, player)
    if sub in ("difendi", "defend"):
        return defend(conn, player)
    if sub in ("dona", "donate"):
        return donate(conn, player, rest)
    if sub in ("resuscita", "revive"):
        return resurrect(conn, player, rest)
    return describe(conn, player)
