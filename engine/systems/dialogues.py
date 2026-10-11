"""
DIALOGHI E FAVORI — parlare davvero con chi ti è vicino.

Con la famiglia, la compagna del Dao, il maestro, i fratelli giurati, i compagni di viaggio
e i discepoli, `parla <nome>` apre un DIALOGO a scelta (una volta al giorno per persona):
  · ricordare insieme ciò che avete vissuto (la cronaca e i legami ricordano per te);
  · chiedere come sta davvero — e a volte ti confida un FAVORE che le sta a cuore;
  · chiedere un consiglio (il maestro ti corregge il Dao, la famiglia ti calma il cuore…).

FAVORI (uno per persona, alla volta)
  · un dono      portarle dei materiali (erbe, minerali, nuclei);
  · un luogo     accompagnarla / raggiungere un luogo che le è caro;
  · un torto     abbattere chi le ha fatto del male (compare nel mondo, con un nome).
  favori              l'elenco, con cosa manca
  favore <nome>       consegni / completi il favore, se le condizioni ci sono

INTIMITÀ: ogni favore compiuto approfondisce il legame (livelli senza fine). Da intimità 2
chi ti è vicino può ARRIVARE QUANDO SERVE: negli scontri difficili, anche se non era con te,
compare al tuo fianco (più spesso quanto più è profondo il legame).
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

CLOSE = ("family", "dao_partner", "master", "sworn", "companion", "disciple")
REQ_KEY = "personal_requests"
INT_KEY = "intimacy"
_MATS = {"erbe": "erbe spirituali", "minerali": "minerali", "nuclei": "nuclei di bestia"}


def close_kind(conn, pid: int, npc_id: int) -> str | None:
    from engine.systems import bonds
    kinds = bonds.bond_kinds(conn, npc_id, pid)
    for k in CLOSE:
        if k in kinds:
            return k
    return None


def intimacy(conn, npc_id: int) -> int:
    return int((state.get_json(conn, INT_KEY, {}) or {}).get(str(npc_id), 0))


def _add_intimacy(conn, npc_id: int, n: int = 1) -> int:
    d = state.get_json(conn, INT_KEY, {}) or {}
    d[str(npc_id)] = int(d.get(str(npc_id), 0)) + n
    state.set_json(conn, INT_KEY, d)
    return d[str(npc_id)]


def requests(conn) -> dict:
    return state.get_json(conn, REQ_KEY, {}) or {}


def _save_requests(conn, r: dict) -> None:
    state.set_json(conn, REQ_KEY, r)


# ------------------------------------------------------------
# Il dialogo
# ------------------------------------------------------------

_KIND_WORD = {"family": "di famiglia", "dao_partner": "compagna del Dao", "master": "maestro",
              "sworn": "fratello giurato", "companion": "compagno di viaggio", "disciple": "discepolo"}


def _memory(conn, npc_name: str, bond_row) -> str:
    from engine.systems import chronicle
    first = npc_name.split()[0]
    try:
        chronicle.ensure_table(conn)
        r = conn.execute("SELECT text FROM chronicle_entries WHERE text LIKE ? ORDER BY RANDOM() LIMIT 1;",
                         (f"%{first}%",)).fetchone()
    except Exception:
        r = None
    if r:
        return f"Ricordate insieme: «{r['text']}»"
    days = max(1, (tick_mod.get_tick(conn) - (bond_row["since_tick"] or 0)) // 120) if bond_row else 1
    why = (bond_row["reason"] if bond_row and bond_row["reason"] else "il giorno in cui vi siete incontrati")
    return f"Ricordate insieme {why}: sono passati {days} giorni, e sembra ieri."


def scene(conn, player, npc) -> dict | None:
    kind = close_kind(conn, player.id, npc.id)
    if not kind:
        return None
    bond = conn.execute("SELECT * FROM bonds WHERE player_id=? AND npc_id=? AND kind=? AND status='active';",
                        (player.id, npc.id, kind)).fetchone()
    lv = intimacy(conn, npc.id)
    req = requests(conn).get(str(npc.id))
    ask_label = ("«Come stai, davvero?»" if not req else "«Il favore che mi avevi chiesto…»")
    advice = {"master": ("Chiedi un consiglio sulla tua via", {"dao_gain": 4, "relation": 3}),
              "dao_partner": ("Coltivate insieme in silenzio", {"heart": 5, "relation": 4}),
              "family": ("Ti lasci consolare", {"heart": 6, "relation": 3}),
              "sworn": ("Bevete insieme e parlate di battaglie", {"heart": 3, "relation": 5}),
              }.get(kind, ("Chiedi un consiglio", {"relation": 3, "heart": 2}))
    eff_adv = dict(advice[1])
    if "dao_gain" in eff_adv:
        from engine.systems import dao_training
        rows = dao_training.trainable_daos(conn, player.id)
        if rows:
            eff_adv["dao_key"] = rows[0]["dao_key"]
        else:
            eff_adv.pop("dao_gain")
    return {"key": f"dialogo_{npc.id}", "title": f"Con {npc.name} ({_KIND_WORD[kind]})", "event_type": "bond",
            "ctx": {"npc_id": npc.id, "npc_name": npc.name},
            "text": f"{npc.name} si siede accanto a te." + (f" Tra voi c'è un'intimità profonda (livello {lv})."
                                                           if lv else ""),
            "choices": [
                {"label": "Ricordate insieme ciò che avete vissuto",
                 "effects": {"relation": 4, "heart": 2, "text": _memory(conn, npc.name, bond)}},
                {"label": ask_label, "effects": {"dlg_request": npc.id}},
                {"label": advice[0], "effects": eff_adv}]}


def talk(conn, t: int, rng, player, npc) -> str | None:
    """Per chi ti è vicino: apre il dialogo (una volta al giorno). None = parlata normale."""
    from engine.systems import encounters
    if not close_kind(conn, player.id, npc.id) or encounters.pending(conn):
        return None
    day = t // 120
    k = f"dlg_day_{npc.id}"
    if state.get_int(conn, k, -1) == day:
        return None
    state.set(conn, k, str(day))
    sc = scene(conn, player, npc)
    return encounters.start_scene(conn, player, sc, force=True) if sc else None


# ------------------------------------------------------------
# Favori
# ------------------------------------------------------------

def make_request(conn, player, npc_id: int) -> str:
    from engine.systems import npc_factory
    reqs = requests(conn)
    if str(npc_id) in reqs:
        return describe_one(conn, player, npc_id, reqs[str(npc_id)])
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 7 + npc_id)
    lv = intimacy(conn, npc_id)
    kind = rng.choice(["dono", "luogo", "torto"])
    if kind == "dono":
        mat = rng.choice(list(_MATS))
        req = {"type": "dono", "mat": mat, "n": 3 + 2 * lv}
        pr = "le" if npc_factory.is_female(conn, npc_id) else "gli"
        text = (f"{nm} esita, poi confessa: {pr} servirebbero {req['n']} {_MATS[mat]}. "
                "Non te lo chiederebbe, se non fosse importante.")
    elif kind == "luogo":
        loc = conn.execute("SELECT id, name FROM locations WHERE location_type IN ('mountain','ruin') "
                           "ORDER BY RANDOM() LIMIT 1;").fetchone()
        req = {"type": "luogo", "loc": loc["id"], "where": loc["name"]}
        text = (f"{nm} guarda lontano: «C'è un posto, {loc['name']}, dove vorrei tornare. Ci verresti con me?» "
                "(raggiungilo e usa 'favore')")
    else:
        from engine.simulation import cultivation
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        enemy_loc = conn.execute("SELECT id, name FROM locations ORDER BY RANDOM() LIMIT 1;").fetchone()
        eid = npc_factory.spawn(conn, rng, archetype="vagabondo", location_id=enemy_loc["id"], tier=tier,
                                stage=rng.randint(3, 8), traits={"honor": 10, "compassion": 5})
        ename = conn.execute("SELECT name FROM npcs WHERE id=?;", (eid,)).fetchone()["name"]
        req = {"type": "torto", "enemy": eid, "ename": ename, "where": enemy_loc["name"]}
        text = (f"{nm} stringe i pugni: «{ename} mi ha fatto un torto che non posso dimenticare. Si nasconde "
                f"a {enemy_loc['name']}.» (abbattilo, poi 'favore')")
    reqs[str(npc_id)] = req
    _save_requests(conn, reqs)
    return text


def _status(conn, player, req: dict) -> tuple[bool, str]:
    from engine.systems import professions
    if req["type"] == "dono":
        have = professions.material(conn, player.id, req["mat"])
        return have >= req["n"], f"portale {req['n']} {_MATS[req['mat']]} (ne hai {have})"
    if req["type"] == "luogo":
        here = player.location_id == req["loc"]
        return here, f"raggiungi {req['where']}" + (" — sei qui!" if here else " ('vai " + req["where"] + "')")
    st = conn.execute("SELECT status FROM npcs WHERE id=?;", (req["enemy"],)).fetchone()
    done = not st or st["status"] != "alive"
    return done, f"abbatti {req['ename']} ({req['where']})" + (" — fatto!" if done else "")


def describe_one(conn, player, npc_id: int, req: dict) -> str:
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    ok, what = _status(conn, player, req)
    return f"{nm['name'] if nm else '?'}: {what}" + (" → 'favore " + nm["name"].split()[0] + "'" if ok and nm else "")


def describe(conn, player) -> str:
    reqs = requests(conn)
    lines = ["♥ FAVORI DI CHI TI È VICINO"]
    if not reqs:
        lines.append("  Nessuno ti ha chiesto nulla. Parla con chi ti è vicino ('parla <nome>').")
    for nid, req in reqs.items():
        lines.append("  · " + describe_one(conn, player, int(nid), req))
    close = conn.execute("SELECT DISTINCT b.npc_id, n.name FROM bonds b JOIN npcs n ON n.id=b.npc_id WHERE "
                         "b.player_id=? AND b.status='active' AND n.status='alive' AND b.kind IN (%s);"
                         % ",".join("?" * len(CLOSE)), (player.id, *CLOSE)).fetchall()
    ints = [(r["name"], intimacy(conn, r["npc_id"])) for r in close]
    if ints:
        lines.append("Intimità: " + ", ".join(f"{n} {v}" for n, v in ints) +
                     "  (da 2 in su possono arrivare in tuo aiuto negli scontri difficili)")
    return "\n".join(lines)


def fulfil(conn, player, arg: str) -> str:
    from engine.systems import professions, relations, chronicle, dao_heart
    a = arg.strip().lower()
    reqs = requests(conn)
    for nid, req in list(reqs.items()):
        r = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (int(nid),)).fetchone()
        if not r or (a and a not in r["name"].lower()):
            continue
        if r["status"] != "alive":
            reqs.pop(nid)
            _save_requests(conn, reqs)
            return f"{r['name']} non c'è più. Il favore resterà per sempre incompiuto."
        ok, what = _status(conn, player, req)
        if not ok:
            return f"Non ancora: {what}."
        if req["type"] == "dono":
            professions.spend(conn, player.id, {req["mat"]: req["n"]})
        reqs.pop(nid)
        _save_requests(conn, reqs)
        lv = _add_intimacy(conn, int(nid))
        relations.adjust(conn, int(nid), 20, tick_mod.get_tick(conn), player.id)
        out = [f"♥ Hai fatto ciò che {r['name']} ti aveva chiesto. Qualcosa, tra voi, si fa più profondo "
               f"(intimità {lv})."]
        out += dao_heart.adjust(conn, 3)
        chronicle.add(conn, "legame", f"Esaudisci il favore di {r['name']} (intimità {lv}).")
        if lv == 2:
            out.append(f"Da ora {r['name']} potrà accorrere al tuo fianco quando sarai in pericolo.")
        if lv in (3, 7, 15):
            t = f"Legato a {r['name']}" if lv == 3 else f"Anima Gemella di {r['name']}" if lv == 7 \
                else f"Una Vita sola con {r['name']}"
            if state.grant_title(conn, t):
                out.append(f"✧ Nuovo titolo: «{t}» ✧")
        return "\n".join(out)
    return "Nessun favore corrisponde. ('favori' per l'elenco)"


# ------------------------------------------------------------
# Chi ti è vicino arriva quando serve
# ------------------------------------------------------------

def rescuers(conn, player_id: int, npc_id: int, ratio: float) -> list[dict]:
    """Negli scontri difficili (sei più debole), chi ha intimità ≥2 può accorrere."""
    from engine.simulation import combat
    if ratio >= 1.0:
        return []
    p = entities.get_player(conn, player_id)
    out = []
    rng = random.Random(tick_mod.get_tick(conn) * 13 + npc_id)
    for nid, lv in (state.get_json(conn, INT_KEY, {}) or {}).items():
        nid = int(nid)
        if lv < 2 or nid == npc_id:
            continue
        r = conn.execute("SELECT name, status, location_id FROM npcs WHERE id=?;", (nid,)).fetchone()
        if not r or r["status"] != "alive" or r["location_id"] == p.location_id:
            continue
        if rng.random() > min(0.75, 0.2 + 0.08 * lv):
            continue
        atk = combat.combat_power(conn, "npc", nid)["attack"] * 0.5
        out.append({"intro": f"♥ Nel momento peggiore, {r['name']} arriva di corsa: «Non ti lascio solo!»",
                    "attack": atk,
                    "line": f"{r['name']} " + rng.choice(["ti copre le spalle e colpisce.",
                                                         "si getta nella mischia accanto a te.",
                                                         "devia un colpo che era per te."])})
        if len(out) >= 2:
            break
    return out
