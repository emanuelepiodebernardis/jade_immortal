"""
DISCEPOLI e la TUA SETTA.

Discepoli (dal Regno 3 — Fondazione in su):
  accogli <nome>        prendi come discepolo qualcuno più debole di te che ti stima
  discepoli             i tuoi discepoli: regno, lealtà, dove sono
  insegna <nome> [dao]  una lezione al giorno: lui cresce, e insegnando capisci meglio anche tu
  congeda_discepolo <nome>

I discepoli vivono nella tua grotta-dimora (o nella sede della tua setta) e lì crescono
anche da soli. Più sali di regno, più discepoli puoi seguire.

La tua setta (dal Regno 4, con dimora, 3 discepoli e 2000 pietre):
  fonda <nome>          fondi la tua setta, con sede nella tua dimora
  setta                 il pannello della setta: membri, tesoro, potenza, minacce
  setta riscuoti        ritiri i tributi accumulati
  setta recluta         spendi pietre per accogliere nuovi discepoli esterni
  setta difendi         quando un nemico assalta la sede, sei tu a doverla difendere

Una setta giovane attira ammiratori… e invidie: le altre sette di tanto in tanto mettono
alla prova la tua sede. Se non la difendi, perdi influenza e tesoro.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

DISCIPLE_MIN_TIER = 3
FOUND_MIN_TIER = 4
FOUND_COST = 2000
FOUND_MIN_DISCIPLES = 3
KEY = "own_sect"


def max_disciples(conn, pid: int) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    extra = 0
    s = get(conn)
    if s:
        extra = 2 + s.get("halls", 0)
    return (tier - 1 + extra) if tier >= DISCIPLE_MIN_TIER else 0


def disciples(conn, pid: int = 1) -> list[sqlite3.Row]:
    from engine.systems import bonds
    bonds.ensure_table(conn)
    return [r for r in bonds._active(conn, pid, "disciple") if r["npc_status"] == "alive"]


def _home(conn, pid: int) -> int | None:
    s = get(conn)
    if s:
        return s["loc"]
    from engine.systems import cave_abode
    ab = cave_abode.get(conn, pid)
    return ab["loc"] if ab else None


# ============================================================
# Discepoli
# ============================================================

def accept(conn, t: int, player, npc) -> str:
    from engine.systems import bonds, relations
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    if ptier < DISCIPLE_MIN_TIER:
        return "Sei troppo giovane nella Via per avere discepoli: serve almeno il terzo regno."
    kind = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()["kind"]
    if kind not in (None, "human"):
        return f"{npc.name} non può diventare tuo discepolo."
    if "disciple" in bonds.bond_kinds(conn, npc.id, player.id):
        return f"{npc.name} è già tuo discepolo."
    if {"nemesis", "master"} & bonds.bond_kinds(conn, npc.id, player.id):
        return f"{npc.name} non si inchinerebbe mai davanti a te come allievo."
    ntier = cultivation.realm_tier(conn, "npc", npc.id) or 1
    if ntier >= ptier:
        return f"{npc.name} non è più debole di te: non ha nulla da imparare da un suo pari."
    if conn.execute("SELECT 1 FROM factions WHERE leader_id=?;", (npc.id,)).fetchone():
        return f"{npc.name} guida già una setta."
    if len(disciples(conn, player.id)) >= max_disciples(conn, player.id):
        return (f"Non puoi seguire altri discepoli (massimo {max_disciples(conn, player.id)} al tuo regno"
                + ("; una setta te ne concede di più" if not get(conn) else "") + ").")
    score = relations.get_disposition(conn, npc.id, player.id).score
    from engine.systems import reputation
    fame = reputation.get(conn, player.id)["fame"]
    if score < 20 and fame < 30:
        return (f"{npc.name} non ti conosce abbastanza da affidarti la sua Via. "
                "Parlagli, aiutalo, o fatti un nome.")
    bonds.add_bond(conn, player.id, npc.id, "disciple", t, reason="accolto come discepolo")
    s = get(conn)
    if s:
        conn.execute("UPDATE npcs SET faction_id=? WHERE id=?;", (s["fid"], npc.id))
    home = _home(conn, player.id)
    where = ""
    if home:
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (home, npc.id))
        where = " Si trasferisce nella tua dimora."
    return (f"{npc.name} si inginocchia e batte la fronte a terra tre volte: «Maestro!» "
            f"Ora è tuo DISCEPOLO.{where} ('insegna {npc.name.split()[0]}' per guidarlo)")


def teach(conn, t: int, rng, player, npc, dao_frag: str = "") -> str:
    from engine.systems import bonds, dao_training, items, npc_factory
    from engine.simulation import cultivation, world_tick
    if "disciple" not in bonds.bond_kinds(conn, npc.id, player.id):
        return f"{npc.name} non è tuo discepolo."
    key = f"taught_{npc.id}"
    day = t // 120
    if state.get_int(conn, key, -1) == day:
        return f"Hai già dato una lezione a {npc.name} oggi."
    state.set(conn, key, str(day))
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    stages = 1 + rng.randint(0, max(1, ptier // 2))
    ntier = cultivation.realm_tier(conn, "npc", npc.id) or 1
    if ntier >= ptier - 1:
        stages = 1                                 # oltre una certa soglia deve trovare la sua via
    npc_factory.raise_npc(conn, npc.id, stages)
    lines = [f"Insegni a {npc.name} per un'intera giornata. Cresce di {stages} strati."]
    rows = dao_training.trainable_daos(conn, player.id)
    if dao_frag:
        r = dao_training.find_dao(conn, dao_frag, player.id)
        dk = r["dao_key"] if r else None
    else:
        dk = rows[0]["dao_key"] if rows else None
    if dk:
        conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, "
                     "comprehension, practiced) VALUES ('npc', ?, ?, 50, 3, 1) "
                     "ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
                     "comprehension=comprehension+3, practiced=1;", (npc.id, dk))
        lines.append("Spiegando il tuo Dao, lo vedi con occhi nuovi:")
        lines += items.apply_effects(conn, t, rng, player.id, {"dao_key": dk, "dao_gain": 1 + ptier // 2})
    n = state.get_int(conn, "lessons", 0) + 1
    state.set(conn, "lessons", str(n))
    if n in (10, 100, 1000):
        title = {10: "Maestro Paziente", 100: "Grande Maestro", 1000: "Maestro di Diecimila Allievi"}[n]
        if state.grant_title(conn, title):
            lines.append(f"✧ Nuovo titolo: «{title}» ✧")
    world_tick.advance(conn, 60)
    return "\n".join(lines)


def dismiss_disciple(conn, player, npc) -> str:
    from engine.systems import bonds
    if "disciple" not in bonds.bond_kinds(conn, npc.id, player.id):
        return f"{npc.name} non è tuo discepolo."
    bonds.end_bond(conn, player.id, npc.id, "disciple", "congedato")
    return f"Congedi {npc.name}: «Va', e trova la tua strada.»"


def describe_disciples(conn, player) -> str:
    from engine.simulation import cultivation
    rows = disciples(conn, player.id)
    mx = max_disciples(conn, player.id)
    if not rows:
        if mx == 0:
            return "Dal terzo regno potrai accogliere discepoli ('accogli <nome>')."
        return f"Nessun discepolo (puoi seguirne {mx}). 'accogli <nome>' con chi ti stima ed è più debole di te."
    lines = [f"I tuoi discepoli ({len(rows)}/{mx}):"]
    for r in rows:
        loc = conn.execute("SELECT name FROM locations WHERE id=?;", (r["location_id"],)).fetchone() \
            if r["location_id"] else None
        lines.append(f"  · {r['name']} — {cultivation.realm_label(conn, 'npc', r['npc_id'])}"
                     + (f" — a {loc['name']}" if loc else ""))
    return "\n".join(lines)


def daily_disciples(conn, t: int, rng, player) -> list[str]:
    """I discepoli crescono da soli; ogni tanto uno fa un balzo e te lo racconta."""
    from engine.systems import npc_factory, cave_abode
    from engine.simulation import cultivation
    out = []
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    for r in disciples(conn, player.id):
        p = 0.25 + 0.05 * cave_abode.level(conn, player.id, "qi")
        if rng.random() < p and (cultivation.realm_tier(conn, "npc", r["npc_id"]) or 1) < ptier:
            npc_factory.raise_npc(conn, r["npc_id"], 1)
        if rng.random() < 0.02:
            out.append(f"Il tuo discepolo {r['name']} ti manda un messaggio: ha fatto un passo avanti "
                       "nella Via e ti ringrazia.")
    return out


# ============================================================
# La tua setta
# ============================================================

def get(conn) -> dict | None:
    s = state.get_json(conn, KEY)
    if not s:
        return None
    row = conn.execute("SELECT status FROM factions WHERE id=?;", (s["fid"],)).fetchone()
    return s if row else None


def _save(conn, s: dict) -> None:
    state.set_json(conn, KEY, s)


def found(conn, t: int, player, name: str) -> str:
    from engine.systems import sects, cave_abode
    from engine.simulation import cultivation
    if get(conn):
        return "Hai già fondato una setta. ('setta')"
    name = name.strip().strip('"«»')
    if len(name) < 3:
        return "Usa: fonda <nome della setta>  (es. 'fonda Setta della Giada Celeste')"
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    missing = []
    if tier < FOUND_MIN_TIER:
        missing.append(f"almeno il regno {FOUND_MIN_TIER}")
    ab = cave_abode.get(conn, player.id)
    if not ab:
        missing.append("una grotta-dimora come sede ('dimora reclama')")
    elif player.location_id != ab["loc"]:
        missing.append("essere nella tua dimora")
    if len(disciples(conn, player.id)) < FOUND_MIN_DISCIPLES:
        missing.append(f"{FOUND_MIN_DISCIPLES} discepoli")
    if sects.get_membership(conn, player.id):
        missing.append("lasciare la setta a cui appartieni ('leave')")
    if sects.get_resource(conn, "pietre_spirituali", player.id) < FOUND_COST:
        missing.append(f"{FOUND_COST} pietre spirituali")
    if missing:
        return "Per fondare una setta ti servono: " + "; ".join(missing) + "."
    sects.grant_resource(conn, "pietre_spirituali", -FOUND_COST, player.id)
    if not name.lower().startswith(("setta", "palazzo", "valle", "monte", "tempio", "clan", "sala")):
        name = "Setta " + name
    cur = conn.execute(
        "INSERT INTO factions (name, leader_id, home_location_id, influence, wealth, description, "
        "goals, tier, status) VALUES (?, NULL, ?, 10, 20, ?, ?, ?, 'player_sect');",
        (name, ab["loc"], f"Setta fondata da {player.name}.", "crescere", max(1, min(6, tier - 2))))
    fid = cur.lastrowid
    for r in disciples(conn, player.id):
        conn.execute("UPDATE npcs SET faction_id=?, location_id=? WHERE id=?;", (fid, ab["loc"], r["npc_id"]))
    _save(conn, {"fid": fid, "loc": ab["loc"], "name": name, "treasury": 0, "founded": t,
                 "halls": 0, "threat": None, "next_raid_day": t // 120 + 20})
    from engine.systems import reputation
    reputation.adjust(conn, player.id, fame=15)
    state.grant_title(conn, "Fondatore di Setta")
    from engine.simulation import event_system as ev
    try:
        ev.log_event(conn, event_type="sect_founded", tick=t, location_id=ab["loc"],
                     title=f"Nasce la {name}", summary=f"{player.name} fonda la {name}.",
                     participants=[ev.Participant("player", player.id, "initiator")],
                     consequences=[])
    except Exception:
        pass
    return (f"✧ Sulla roccia della tua dimora incidi un nome: {name}. Oggi nasce una setta! ✧\n"
            f"I tuoi discepoli ne sono i primi membri. ✧ Nuovo titolo: «Fondatore di Setta» ✧\n"
            "'setta' per il pannello; i tributi si accumulano ogni giorno.")


def members(conn, fid: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, name FROM npcs WHERE faction_id=? AND status='alive';", (fid,)).fetchall()


def power_score(conn, fid: int) -> int:
    from engine.systems import power
    return sum(power.combat_rating(conn, "npc", r["id"]) for r in members(conn, fid))


def describe(conn, player) -> str:
    s = get(conn)
    if not s:
        return ("Non hai una setta. Requisiti per fondarla: regno 4, una grotta-dimora, "
                f"{FOUND_MIN_DISCIPLES} discepoli, {FOUND_COST} pietre — poi 'fonda <nome>'.")
    f = conn.execute("SELECT influence, wealth FROM factions WHERE id=?;", (s["fid"],)).fetchone()
    mem = members(conn, s["fid"])
    lines = [f"✦ {s['name']} — fondatore: {player.name}",
             f"  Membri: {len(mem)}   Influenza: {f['influence']}   Potenza: {power_score(conn, s['fid'])}",
             f"  Tesoro (tributi da riscuotere): {s['treasury']} pietre ('setta riscuoti')",
             f"  Recluta un discepolo esterno: {recruit_cost(conn, s)} pietre ('setta recluta')"]
    if s.get("threat"):
        th = s["threat"]
        lines.append(f"  ⚠ {th['enemy']} assalta la sede! Torna e difendila ('setta difendi') "
                     f"entro {max(0, th['deadline'] - tick_mod.get_tick(conn) // 120)} giorni.")
    return "\n".join(lines)


def recruit_cost(conn, s: dict) -> int:
    return 150 + 40 * len(members(conn, s["fid"]))


def collect(conn, player) -> str:
    from engine.systems import sects
    s = get(conn)
    if not s:
        return "Non hai una setta."
    n = s["treasury"]
    if n <= 0:
        return "Il tesoro della setta è vuoto: i tributi arrivano ogni giorno."
    sects.grant_resource(conn, "pietre_spirituali", n, player.id)
    s["treasury"] = 0
    _save(conn, s)
    return f"Ritiri {n} pietre spirituali dal tesoro della setta."


def recruit(conn, t: int, rng, player) -> str:
    from engine.systems import sects, npc_factory
    from engine.simulation import cultivation
    s = get(conn)
    if not s:
        return "Non hai una setta."
    cost = recruit_cost(conn, s)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Reclutare costa {cost} pietre (vitto, alloggio, pillole di base)."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=s["loc"],
                            tier=max(1, ptier - 2), faction_id=s["fid"], tick=t)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    conn.execute("UPDATE factions SET influence=influence+1 WHERE id=?;", (s["fid"],))
    return f"{name} supera la prova d'ingresso ed entra nella {s['name']}. (-{cost} pietre)"


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import reputation
    from engine.simulation import cultivation
    out = daily_disciples(conn, t, rng, player)
    s = get(conn)
    if not s:
        return out
    day = t // 120
    mem = members(conn, s["fid"])
    trib = sum(5 * (cultivation.realm_tier(conn, "npc", r["id"]) or 1) for r in mem)
    inf = conn.execute("SELECT influence FROM factions WHERE id=?;", (s["fid"],)).fetchone()["influence"]
    trib += inf
    s["treasury"] = min(trib * 60, s["treasury"] + trib)
    # la fama attira aspiranti discepoli
    fame = reputation.get(conn, player.id)["fame"]
    if rng.random() < min(0.25, 0.02 + fame / 4000):
        from engine.systems import npc_factory
        ptier = cultivation.realm_tier(conn, "player", player.id) or 1
        nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=s["loc"],
                                tier=max(1, ptier - 3), faction_id=s["fid"], tick=t)
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        out.append(f"Attratto dalla tua fama, {nm} bussa alla porta della {s['name']} e viene accolto.")
    # minacce: un assalto alla sede
    th = s.get("threat")
    if th and day > th["deadline"]:
        loss = s["treasury"] // 2
        s["treasury"] -= loss
        conn.execute("UPDATE factions SET influence=MAX(0, influence-10) WHERE id=?;", (s["fid"],))
        if mem and rng.random() < 0.5:
            victim = rng.choice(mem)
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (t, victim["id"]))
            out.append(f"⚠ Nessuno ha difeso la sede: {th['enemy']} la saccheggia. {victim['name']} cade. "
                       f"Perdi {loss} pietre e influenza.")
        else:
            out.append(f"⚠ Nessuno ha difeso la sede: {th['enemy']} la saccheggia. Perdi {loss} pietre e influenza.")
        s["threat"] = None
        s["next_raid_day"] = day + rng.randint(15, 30)
    elif not th and day >= s.get("next_raid_day", day + 1):
        rival = conn.execute("SELECT name FROM factions WHERE status='active' ORDER BY RANDOM() LIMIT 1;").fetchone()
        enemy = rival["name"] if rival else "Una banda di coltivatori demoniaci"
        s["threat"] = {"enemy": enemy, "deadline": day + 3}
        out.append(f"⚠ {enemy} manda i suoi a mettere alla prova la {s['name']}! Hai 3 giorni per "
                   "tornare e difenderla ('setta difendi').")
    _save(conn, s)
    return out


def defend(conn, t: int, rng, player) -> str:
    from engine.systems import encounters
    s = get(conn)
    if not s or not s.get("threat"):
        return "Nessuno minaccia la tua setta, per ora."
    if player.location_id != s["loc"]:
        return "Devi essere nella sede per difenderla. ('dimora torna')"
    th = s["threat"]
    s["threat"] = None
    s["next_raid_day"] = t // 120 + rng.randint(18, 35)
    _save(conn, s)
    from engine.systems import npc_factory
    sc = {
        "key": "difesa_setta", "title": f"Assalto alla {s['name']}", "event_type": "combat",
        "text": f"Gli inviati di {th['enemy']} sono al cancello. Il loro capo, {{npc}}, ride: "
                "«Una setta nata ieri? Inginocchiatevi.»",
        "spawn": {"archetype": "discepolo", "tier_offset": 0, "stage": 7, "traits": {"pride": 90}},
        "sticky": True,
        "choices": [
            {"label": "Lo affronti davanti a tutti i tuoi discepoli",
             "effects": {"fame": 5, "sect_influence": 8}, "command": "attack {npc}"},
            {"label": "Lo umili con la sola pressione della tua aura", "check": {"stat": "potenza", "dc": 65},
             "success": {"fame": 8, "sect_influence": 12, "npc_leaves": True,
                         "text": "Le ginocchia gli cedono. Se ne va senza una parola."},
             "failure": {"text": "Ride più forte e sguaina l'arma.", "command": "attack {npc}"}},
            {"label": "Paghi un tributo perché se ne vadano",
             "effects": {"stones": -200, "sect_influence": -5, "npc_leaves": True}},
        ]}
    ctx = {"npc_name": npc_factory.unique_name(rng, conn=conn)}
    return encounters.start_scene(conn, player, encounters.format_scene(sc, ctx), force=True) or ""


def add_influence(conn, n: int) -> None:
    s = get(conn)
    if s:
        conn.execute("UPDATE factions SET influence=MAX(0, influence+?) WHERE id=?;", (n, s["fid"]))
