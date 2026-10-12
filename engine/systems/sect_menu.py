"""
IL MENU DELLA SETTA e l'ASCESA alle sette superiori.

  setta                    il menu: ascesa, classe e tornei, tecniche, metodo, tesoro del merito,
                           rango e stipendio, missioni, anziani, guerre, razzie e invasioni
  setta ascesa             a che punto sei per salire a una setta superiore
  setta ascendi <n>        accetti l'offerta n e ti trasferisci alla nuova setta
  setta rimanda            ci penserai: le offerte restano nel menu
  setta rifiuta            resti per lealtà: la tua setta ti premia (e le prossime offerte saranno più alte)
  setta impara <n>         impari una tecnica segreta col merito
  setta compra <n>         tesoro del merito: pillole, pietre, materiali, essenze, stanza di coltivazione
  setta promozione         sali di rango spendendo merito (oppure 'challenge': una sfida di rango)
  setta stipendio          ritiri lo stipendio del mese
  setta mia                la setta che hai FONDATO tu (riscuoti, recluta, difendi)

L'ASCESA — ogni setta ha una soglia. La superi in uno di tre modi:
  · sei troppo forte per lei: il tuo regno raggiunge quello del suo Patriarca;
  · hai guadagnato abbastanza merito da quando ci sei entrato;
  · vinci il torneo mensile.
Allora le sette superiori ti mandano i loro emissari: una scena, e la scelta è tua.
Il merito riparte da zero nella nuova setta; le tecniche imparate restano tue.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state
from engine.systems.menus import act, bar, menu, section

OFFER_KEY = "sect_ascension"          # {"reason": ..., "day": ...} offerta d'ascesa aperta
REFUSE_KEY = "sect_refusals"          # rifiuti per lealtà in questa setta
EARNED_KEY = "sect_merit_earned"      # merito guadagnato da quando sei in questa setta
CHAMBER_KEY = "sect_chamber_until"    # giorno fino a cui puoi usare la stanza di coltivazione
STIPEND_KEY = "sect_stipend_day"
SCENE_KEY = "ascesa_setta"

MERIT_PER_TIER = 150
CHAMBER_MULT = 1.5
STIPEND_EVERY = 30


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _m(conn, pid):
    from engine.systems import sects
    return sects.get_membership(conn, pid)


def _tier(m) -> int:
    return max(1, (m["sect_tier"] or 1)) if m else 1


def level(conn, pid: int) -> int:
    """Il livello EFFETTIVO della setta per te: il suo livello, ma mai più alto del regno con cui
    sei entrato (chi entra da mortale in una grande setta parte comunque dal basso)."""
    from engine.simulation import cultivation
    m = _m(conn, pid)
    if not m:
        return 1
    j = state.get_json(conn, "sect_join_realm") or {}
    if j.get("fid") != m["faction_id"]:                 # setta nuova: si riparte da capo
        if j:
            for k in (EARNED_KEY, REFUSE_KEY, CHAMBER_KEY, STIPEND_KEY, OFFER_KEY):
                state.delete(conn, k)
        j = {"fid": m["faction_id"], "realm": cultivation.realm_tier(conn, "player", pid) or 1}
        state.set_json(conn, "sect_join_realm", j)
    return max(1, min(_tier(m), j["realm"]))


def _rank_idx(m) -> int:
    from engine.systems import sects
    return sects.RANK_LADDER.index(m["rank"]) if m and m["rank"] in sects.RANK_LADDER else 0


def _hq(conn, m) -> int | None:
    r = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    return r["home_location_id"] if r else None


# ================================================================ ascesa

def requirements(conn, pid: int) -> dict:
    from engine.simulation import cultivation
    t = level(conn, pid)
    ref = state.get_int(conn, REFUSE_KEY, 0)
    realm = cultivation.realm_tier(conn, "player", pid) or 1
    need_r = t + 2 + ref
    earned = state.get_int(conn, EARNED_KEY, 0)
    need_m = int(MERIT_PER_TIER * t * (1.5 ** ref))
    from engine.systems import sects
    top = sects.current_sect_tier(conn, pid) >= sects.max_sect_tier(conn, pid)
    return {"top": top, "realm": realm, "need_realm": need_r, "earned": earned, "need_merit": need_m,
            "pct": max(realm / need_r, earned / need_m) * 100,
            "by_strength": realm >= need_r, "by_merit": earned >= need_m, "refusals": ref}


def offers(conn, pid: int) -> list:
    from engine.systems import sects
    return list(sects.pending_invitations(conn, pid))


_TEXT = {
    "forza": ("Il Patriarca ti convoca nella Sala degli Antenati. Ti guarda a lungo, poi sospira: «Il tuo regno "
              "ha raggiunto il mio. Questa montagna è diventata troppo piccola per te.» Quella notte, sulla "
              "piazza della setta, si posano nubi che non portano pioggia: sono navi. Gli emissari delle sette "
              "superiori sono venuti per te."),
    "merito": ("Il tuo nome è ormai inciso in cima alla Stele del Merito, e la voce ha viaggiato oltre le "
               "montagne. All'alba tre emissari attraversano il portale della setta, ciascuno con un sigillo "
               "diverso e la stessa domanda: verrai con noi?"),
    "torneo": ("La tua vittoria al torneo non è passata inosservata: tra il pubblico sedevano, in silenzio, "
               "gli osservatori delle sette superiori. Ora si fanno avanti, uno alla volta, e ti offrono un posto."),
}


def _scene(conn, player, reason: str) -> dict:
    from engine.systems import sects
    invs = offers(conn, player.id)[:3]
    choices = [{"label": f"Accetti: {r['name']} — {r['hint']}", "effects": {}, "command": f"setta ascendi {r['slot']}"}
               for r in invs]
    choices.append({"label": "Ci penserai (le offerte restano nel menu della setta)", "effects": {},
                    "command": "setta rimanda"})
    m = _m(conn, player.id)
    choices.append({"label": f"Resti per lealtà a {m['sect_name'] if m else 'la tua setta'}", "effects": {},
                    "command": "setta rifiuta"})
    return {"key": SCENE_KEY, "title": "Gli emissari delle sette superiori", "event_type": "social",
            "sticky": True, "text": _TEXT.get(reason, _TEXT["merito"]), "choices": choices,
            "ctx": {"sect_tier": sects.current_sect_tier(conn, player.id)}}


def open_offer(conn, t: int, rng: random.Random, player, reason: str) -> str | None:
    """Le sette superiori si fanno avanti: crea le offerte e, se si può, apre la scena."""
    from engine.systems import sects, encounters
    if not _m(conn, player.id):
        return None
    sects.generate_invitations(conn, t, rng, player.id, count=3, bonus=state.get_int(conn, REFUSE_KEY, 0))
    state.set_json(conn, OFFER_KEY, {"reason": reason, "day": _day(conn), "shown": False})
    return show_scene(conn, player)


def show_scene(conn, player) -> str | None:
    from engine.systems import encounters
    o = state.get_json(conn, OFFER_KEY)
    if not o or o.get("shown") or not offers(conn, player.id) or encounters.pending(conn):
        return None
    txt = encounters.start_scene(conn, player, _scene(conn, player, o.get("reason", "merito")))
    if txt:
        o["shown"] = True
        state.set_json(conn, OFFER_KEY, o)
    return txt


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    """Ogni giorno: se hai superato la soglia, gli emissari arrivano."""
    if not _m(conn, player.id):
        return []
    if offers(conn, player.id):
        txt = show_scene(conn, player)
        return [txt] if txt else []
    r = requirements(conn, player.id)
    if r["top"]:
        return []                         # la setta più alta di questo mondo: oltre c'è solo l'ascensione
    if r["by_strength"] or r["by_merit"]:
        txt = open_offer(conn, t, rng, player, "forza" if r["by_strength"] else "merito")
        return [txt or "Gli emissari delle sette superiori ti cercano: 'setta ascesa'."]
    return []


def _clear_scene(conn) -> None:
    from engine.systems import encounters
    sc = encounters.pending(conn)
    if sc and sc.get("key") == SCENE_KEY:
        encounters.clear(conn)


def ascend(conn, player, arg: str) -> str:
    from engine.cli import loop
    from engine.systems import chronicle
    invs = offers(conn, player.id)
    if not invs:
        return "Nessuna setta superiore ti ha ancora fatto un'offerta. ('setta ascesa' per sapere quanto manca)"
    a = arg.strip()
    if not a.isdigit():
        return describe_ascent(conn, player)
    old = _m(conn, player.id)
    old_name = old["sect_name"] if old else "la tua setta"
    _clear_scene(conn)
    res = loop.cmd_accept(conn, player, a)
    if not res.startswith("Ascendi"):
        return res
    for k in (OFFER_KEY, EARNED_KEY, REFUSE_KEY, CHAMBER_KEY, STIPEND_KEY, "sect_join_realm"):
        state.delete(conn, k)
    new = _m(conn, player.id)
    chronicle.add(conn, "setta", f"Lascia {old_name} e ascende a {new['sect_name']}.")
    return (f"Saluti i compagni di {old_name} sulla piazza: qualcuno ti invidia, qualcuno piange. "
            f"La nave di nubi ti porta via.\n" + res +
            "\n('setta' per il menu della nuova setta: il merito riparte da zero, le tue tecniche restano tue.)")


def postpone(conn, player) -> str:
    _clear_scene(conn)
    if not offers(conn, player.id):
        return "Non c'è nessuna offerta da rimandare."
    return "Chiedi tempo per pensarci. Gli emissari annuiscono: le offerte restano aperte ('setta ascesa')."


def refuse(conn, player) -> str:
    from engine.systems import sects, guild, chronicle, sect_politics
    _clear_scene(conn)
    m = _m(conn, player.id)
    if not m or not offers(conn, player.id):
        return "Non c'è nessuna offerta da rifiutare."
    t = level(conn, player.id)
    conn.execute("UPDATE sect_invitations SET resolved=1 WHERE player_id=?;", (player.id,))
    state.delete(conn, OFFER_KEY)
    ref = state.get_int(conn, REFUSE_KEY, 0) + 1
    state.set(conn, REFUSE_KEY, str(ref))
    merit = 40 * t
    conn.execute("UPDATE sect_memberships SET merit=COALESCE(merit,0)+? WHERE player_id=?;", (merit, player.id))
    stones = 100 * t
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    es = sect_politics.elders(conn, player.id)
    for e in es:
        e["favor"] += 8
    sect_politics._save(conn, player.id, es)
    promo = sects.promote_rank(conn, player.id)
    chronicle.add(conn, "setta", f"Rifiuta le sette superiori per restare fedele a {m['sect_name']}.")
    lines = [f"Rimandi indietro gli emissari. Quando la notizia si sparge, la sala di {m['sect_name']} esplode "
             f"in un boato: il Patriarca in persona ti versa il vino.",
             f"Merito +{merit}, +{stones} pietre, gli anziani ti guardano con favore."]
    if promo and promo["promoted"]:
        lines.append(f"Vieni elevato a {promo['rank']}.")
    lines.append("Le sette superiori torneranno — e la prossima volta saranno ancora più grandi.")
    return "\n".join(lines)


def describe_ascent(conn, player) -> str:
    from engine.systems import sects
    m = _m(conn, player.id)
    if not m:
        return "Non sei in una setta. ('setta' per vedere dove iscriverti)"
    r = requirements(conn, player.id)
    lines = [f"ASCESA da {m['sect_name']} ({sects.tier_name(_tier(m))}):",
             f"  · Forza: regno {r['realm']}/{r['need_realm']}" + (" ✓" if r["by_strength"] else ""),
             f"  · Merito guadagnato qui: {r['earned']}/{r['need_merit']}" + (" ✓" if r["by_merit"] else ""),
             "  · oppure vinci il torneo mensile."]
    invs = offers(conn, player.id)
    if invs:
        lines.append("Offerte aperte ('setta ascendi <n>', 'setta rifiuta'):")
        lines += [f"  {i['slot']}. {i['name']} — {i['hint']}" for i in invs]
    return "\n".join(lines)


# ================================================================ tesoro, rango, stipendio

def shop(conn, player) -> list[dict]:
    from engine.simulation import cultivation
    t = level(conn, player.id)
    realm = cultivation.realm_tier(conn, "player", player.id) or 1
    lv = max(t, realm)
    return [
        {"name": "Pillola del Progresso", "cost": 25 * t, "kind": "pill", "n": round(0.18 + 0.05 * lv, 2),
         "desc": "fa avanzare la coltivazione"},
        {"name": f"{60 * t} pietre spirituali", "cost": 15 * t, "kind": "stones", "n": 60 * t, "desc": ""},
        {"name": f"{4 + 2 * t} erbe spirituali e {2 + t} minerali", "cost": 10 * t, "kind": "mats",
         "n": {"erbe": 4 + 2 * t, "minerali": 2 + t}, "desc": "per le arti"},
        {"name": f"{2 + t} nuclei di bestia", "cost": 15 * t, "kind": "mats", "n": {"nuclei": 2 + t}, "desc": ""},
        {"name": "Essenza del Dao", "cost": 30 * t, "kind": "essence", "n": 4 + 2 * lv,
         "desc": "il tuo Dao più alto"},
        {"name": "Stanza di Coltivazione (3 giorni)", "cost": 40 * t, "kind": "chamber", "n": 3,
         "desc": f"×{CHAMBER_MULT} alla coltivazione nella sede"},
    ]


def buy(conn, player, arg: str) -> str:
    from engine.systems import guild, sects, items, professions
    if not _m(conn, player.id):
        return "Non sei in una setta."
    sh = shop(conn, player)
    if not arg.strip().isdigit() or not (1 <= int(arg) <= len(sh)):
        return "Cosa vuoi comprare? ('setta' per il tesoro del merito)"
    it = sh[int(arg) - 1]
    have = guild.get_merit(conn, player.id)
    if have < it["cost"]:
        return f"Ti serve più merito: {it['cost']} (ne hai {have})."
    conn.execute("UPDATE sect_memberships SET merit=merit-? WHERE player_id=?;", (it["cost"], player.id))
    if it["kind"] == "pill":
        iid = items.create_item(conn, "Pillola del Progresso della Setta", "pillola", "non_comune",
                                "Dal tesoro della setta: fa avanzare la coltivazione.",
                                {"cultivation_progress": it["n"]})
        items.grant(conn, "player", player.id, iid)
        got = "una Pillola del Progresso (nello zaino: 'use pillola')"
    elif it["kind"] == "stones":
        sects.grant_resource(conn, "pietre_spirituali", it["n"], player.id)
        got = it["name"]
    elif it["kind"] == "mats":
        for k, v in it["n"].items():
            professions.give(conn, player.id, k, v)
        got = it["name"]
    elif it["kind"] == "essence":
        best = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
                            "ORDER BY comprehension DESC LIMIT 1;", (player.id,)).fetchone()
        dk = best["dao_key"] if best else "spada"
        iid = items.create_item(conn, f"Essenza del Dao «{dk}»", "essenza", "raro",
                                "Dal tesoro della setta.", {"dao_key": dk, "dao_gain": it["n"]})
        items.grant(conn, "player", player.id, iid)
        got = f"un'Essenza del Dao «{dk}» (nello zaino)"
    else:
        until = max(_day(conn), state.get_int(conn, CHAMBER_KEY, -1)) + it["n"]
        state.set(conn, CHAMBER_KEY, str(until))
        got = f"la Stanza di Coltivazione fino al giorno {until + 1} (coltiva nella sede)"
    return f"Spendi {it['cost']} merito: ricevi {got}. Merito rimasto: {guild.get_merit(conn, player.id)}."


def chamber_mult(conn, location_id) -> tuple[float, str]:
    if state.get_int(conn, CHAMBER_KEY, -1) < _day(conn):
        return 1.0, ""
    m = _m(conn, 1)
    if not m or location_id != _hq(conn, m):
        return 1.0, ""
    return CHAMBER_MULT, f"stanza di coltivazione della setta ×{CHAMBER_MULT}"


def promotion_info(conn, player) -> dict:
    from engine.systems import sects, guild
    from engine.simulation import cultivation
    m = _m(conn, player.id)
    i = _rank_idx(m)
    if i >= len(sects.RANK_LADDER) - 1:
        return {"next": None, "ok": False, "why": "sei già al rango più alto"}
    t = level(conn, player.id)
    nxt = sects.RANK_LADDER[i + 1]
    cost = 40 * (i + 1) * t
    need_realm = t + (i + 1) // 3
    realm = cultivation.realm_tier(conn, "player", player.id) or 1
    merit = guild.get_merit(conn, player.id)
    why = ""
    if realm < need_realm:
        why = f"serve il regno {need_realm}"
    elif merit < cost:
        why = f"servono {cost} merito (ne hai {merit})"
    return {"next": nxt, "cost": cost, "need_realm": need_realm, "ok": not why, "why": why}


def promote(conn, player) -> str:
    from engine.systems import sects, chronicle
    if not _m(conn, player.id):
        return "Non sei in una setta."
    p = promotion_info(conn, player)
    if not p["ok"]:
        return f"Non puoi ancora salire di rango: {p['why']}."
    conn.execute("UPDATE sect_memberships SET merit=merit-? WHERE player_id=?;", (p["cost"], player.id))
    res = sects.promote_rank(conn, player.id)
    chronicle.add(conn, "setta", f"Diventa {res['rank']} della setta.")
    return (f"Il Consiglio degli Anziani esamina il tuo merito e annuisce: sei ora {res['rank']}. "
            f"(−{p['cost']} merito)" + ("\nPuoi guidare la setta in un'invasione ('invadi' alla sede rivale)."
                                        if res["rank"] in sects.RANK_LADDER[6:] else ""))


def stipend_info(conn, player) -> tuple[bool, int, int]:
    m = _m(conn, player.id)
    amount = 15 * (_rank_idx(m) + 1) * _tier(m)
    last = state.get_int(conn, STIPEND_KEY, -999)
    left = last + STIPEND_EVERY - _day(conn)
    return left <= 0, amount, max(0, left)


def stipend(conn, player) -> str:
    from engine.systems import sects
    if not _m(conn, player.id):
        return "Non sei in una setta."
    ok, amount, left = stipend_info(conn, player)
    if not ok:
        return f"Lo stipendio del mese l'hai già ritirato: torna tra {left} giorni."
    state.set(conn, STIPEND_KEY, str(_day(conn)))
    sects.grant_resource(conn, "pietre_spirituali", amount, player.id)
    return f"Il tesoriere della setta ti consegna lo stipendio del mese: {amount} pietre spirituali."


# ================================================================ il menu

def _not_member(conn, player) -> dict:
    from engine.systems import sects, own_sect
    from engine.systems.travel import _distance, _loc_name
    from engine.systems import ascension
    rows = sects.joinable_sects(conn, ascension.player_layer(conn, player.id))
    here = sects.sect_at_location(conn, player.location_id)
    acts, lines = [], []
    if here:
        acts.append(act(f"Sostieni il test d'ingresso di {here['name']}", "join", main=True))
    rs = sorted(rows, key=lambda r: (_distance(conn, player.location_id, r["home_location_id"]) or 99))[:6]
    for r in rs:
        if here and r["id"] == here["id"]:
            continue
        d = _distance(conn, player.location_id, r["home_location_id"])
        acts.append(act(f"Vai a {r['name']} — {sects.tier_name(r['tier'])}, sede {r['hq_name']}"
                        + (f" ({d} tappe)" if d else ""), f"vai #{r['home_location_id']}"))
    secs = [section("Le sette vicine", ["Una setta ti dà maestri, risorse, tecniche segrete e una via per salire."],
                    acts, icon="⛩")]
    if own_sect.get(conn):
        secs.append(_own_section(conn, player))
    return menu("setta", "✦ SETTA — non appartieni a nessuna setta", [], secs)


def _own_section(conn, player) -> dict:
    from engine.systems import own_sect
    s = own_sect.get(conn)
    if not s:
        return {}
    return section(f"La tua setta: {s['name']}", ["La setta che hai fondato tu."],
                   [act("Pannello della tua setta", "setta mia"), act("Riscuoti i tributi", "setta riscuoti"),
                    act("Recluta discepoli esterni", "setta recluta"), act("Difendi la sede", "setta difendi"),
                    act("I tuoi discepoli", "discepoli")], icon="🏯")


def build(conn, player) -> dict:
    from engine.systems import sects, guild, sect_life, sect_politics, sect_war, sect_invasion, gongfa
    from engine.systems.travel import _loc_name
    m = _m(conn, player.id)
    if not m:
        return _not_member(conn, player)
    t = _tier(m)
    t_now = tick_mod.get_tick(conn)
    hq = _hq(conn, m)
    at_hq = hq == player.location_id
    merit = guild.get_merit(conn, player.id)
    el = sects._dao_display(conn, m["sect_element"]) if m["sect_element"] else ""
    sub = [f"{sects.tier_name(t)} (livello {t})" + (f" · affine al {el}" if el else ""),
           f"Rango: {m['rank']} ({_rank_idx(m) + 1}/{len(sects.RANK_LADDER)}) · {m['grade'] or ''} · Merito: {merit}",
           "Sei alla sede." if at_hq else f"La sede è a {_loc_name(conn, hq)}." if hq else ""]
    secs = []

    # --- ascesa
    r = requirements(conn, player.id)
    invs = offers(conn, player.id)
    a_acts = []
    if invs:
        a_acts += [act(f"Sali a {i['name']} — {i['hint']}", f"setta ascendi {i['slot']}", main=True) for i in invs]
        a_acts.append(act("Resta per lealtà (premi e offerte più alte la prossima volta)", "setta rifiuta"))
    elif r["top"]:
        a_acts.append(act("Ascendi al mondo superiore (lì ci sono sette più grandi)", "ascendi_mondo",
                          ok=__import__("engine.systems.ascension", fromlist=["x"]).at_world_peak(conn, player.id),
                          why="prima raggiungi il regno più alto di questo mondo"))
    else:
        a_acts.append(act("Sali alla setta superiore", "setta ascesa", ok=False,
                          why="gli emissari arriveranno quando supererai la soglia"))
    secs.append(section("Ascesa alle sette superiori", [
        "Sei nella setta più alta che questo mondo possa reggere." if r["top"] else "",
        f"Forza: regno {r['realm']}/{r['need_realm']}" + (" ✓" if r["by_strength"] else ""),
        f"Merito guadagnato qui: {r['earned']}/{r['need_merit']}" + (" ✓" if r["by_merit"] else ""),
        "Oppure: vinci il torneo mensile."], a_acts,
        [bar("Verso l'ascesa", r["pct"])], icon="☁"))

    # --- classe e tornei
    lines = [sect_life.agenda_line(conn, t_now, player.id) or "Nessuna sfida in calendario."]
    mates = sect_life.classmates(conn, player.id)
    if mates:
        lines.append("Compagni di classe: " + ", ".join(x["name"] for x in mates))
    if m["class_rank"]:
        lines.append(f"Il tuo posto in classifica: {m['class_rank']}°")
    c_acts = [act("Classifica e potenza della classe", "classe")]
    if _rank_idx(m) < len(sects.RANK_LADDER) - 1:
        nxt = sects.RANK_LADDER[_rank_idx(m) + 1]
        done = state.get_int(conn, "challenge_day", -1) == _day(conn)
        c_acts.append(act(f"Sfida di rango: conquista il posto di «{nxt}»", "challenge", ok=not done,
                          why="hai già sfidato oggi"))
    if not at_hq and hq:
        c_acts.append(act("Torna alla sede", "home"))
    secs.append(section("Classe, tornei e sfide", lines, c_acts, icon="⚔"))

    # --- tecniche
    t_acts = []
    for tech in guild.sect_techniques(conn, m["faction_id"]):
        learned = guild.is_learned(conn, tech["key"], player.id)
        lbl = f"{tech['name']} (+{int(tech['magnitude'] * 100)}% in combattimento) — {tech['cost']} merito"
        if learned:
            t_acts.append(act(lbl + " ✓", "", ok=False, why="già tua"))
        else:
            t_acts.append(act("Impara: " + lbl, f"setta impara {tech['rank']}", ok=merit >= tech["cost"],
                              why=f"servono {tech['cost']} merito"))
    rank_lv = m["rank_level"] or 0
    grade = max(1, t + rank_lv // 3)
    got = state.flag(conn, f"gongfa_sect_{m['faction_id']}_{grade}", False)
    t_acts.append(act(f"Ricevi il metodo di coltivazione della setta (grado {gongfa.grade_name(grade)})",
                      "gongfa setta", ok=at_hq and not got,
                      why="già ricevuto: sali di rango per il prossimo" if got else "si riceve alla sede"))
    secs.append(section("Tecniche segrete e metodo", [], t_acts, icon="📜"))

    # --- tesoro del merito
    s_acts = [act(f"{it['name']}" + (f" ({it['desc']})" if it["desc"] else "") + f" — {it['cost']} merito",
                  f"setta compra {i}", ok=merit >= it["cost"], why=f"servono {it['cost']} merito")
              for i, it in enumerate(shop(conn, player), 1)]
    ch = state.get_int(conn, CHAMBER_KEY, -1)
    secs.append(section("Tesoro del merito", [f"Stanza di coltivazione attiva fino al giorno {ch + 1}."
                                              if ch >= _day(conn) else ""], s_acts, icon="💰"))

    # --- rango e stipendio
    p = promotion_info(conn, player)
    ok_s, amount, left = stipend_info(conn, player)
    g_acts = []
    if p["next"]:
        g_acts.append(act(f"Chiedi la promozione a «{p['next']}» — {p['cost']} merito, regno {p['need_realm']}",
                          "setta promozione", ok=p["ok"], why=p["why"]))
    g_acts.append(act(f"Ritira lo stipendio del mese ({amount} pietre)", "setta stipendio", ok=ok_s,
                      why=f"tra {left} giorni"))
    secs.append(section("Rango e stipendio", [], g_acts, icon="🎖"))

    # --- missioni
    cur = state.get_json(conn, "sect_mission")
    if cur:
        m_lines = [f"In corso: {cur['text']} (per l'Anziano {cur['elder_name']})"]
        m_acts = [act("Consegna la missione", "missioni completa", main=True)]
    else:
        m_lines = []
        m_acts = [act(f"{b['text']} — merito {b['merit']}, {b['stones']} pietre", f"missioni accetta {i}")
                  for i, b in enumerate(sect_politics._board(conn, player), 1)]
    secs.append(section("Bacheca delle missioni", m_lines, m_acts, icon="📋"))

    # --- anziani
    served = state.get_int(conn, "served_day", -1) == _day(conn)
    pr = sect_politics.protector(conn, player.id)
    e_acts = [act(f"Servi l'Anziano {e['name']} (favore {e['favor']})", f"servi {e['name'].split()[0]}",
                  ok=not served, why="hai già servito oggi")
              for e in sect_politics.elders(conn, player.id)]
    secs.append(section("Gli anziani", [f"Il tuo protettore: l'Anziano {pr['name']}." if pr else
                                        "Con 60 di favore un anziano diventa tuo protettore."], e_acts, icon="🧓"))

    # --- guerre, razzie, invasioni
    w_lines, w_acts = [], []
    war = sect_war.active_war(conn)
    if war and m["faction_id"] in (war["player_faction_id"], war["enemy_faction_id"]):
        ef = conn.execute("SELECT name FROM factions WHERE id=?;", (war["enemy_faction_id"],)).fetchone()["name"]
        w_lines.append(f"GUERRA contro {ef}: fronte a {_loc_name(conn, war['battle_location_id'])}, "
                       f"il tuo punteggio {war['score_player']}.")
        if war["battle_location_id"] == player.location_id:
            w_acts.append(act("Combatti al fronte (lo stato della guerra)", "war", main=True))
        else:
            w_acts.append(act("Raggiungi il fronte", "fronte", main=True))
    rival = sects.sect_at_location(conn, player.location_id)
    at_rival = bool(rival and rival["id"] != m["faction_id"])
    w_acts.append(act("Raggiungi la sede rivale più vicina", "vairaid"))
    w_acts.append(act("Razzia questa sede, da solo", "raid", ok=at_rival, why="devi essere alla sede di una setta rivale"))
    can, why = sect_invasion.can_lead(conn, player.id)
    w_acts.append(act("Guida la tua setta all'invasione di questa sede", "invadi", ok=can and at_rival,
                      why=("devi essere alla sede di una setta rivale" if can else
                           f"serve il rango «{sects.RANK_LADDER[sect_invasion.MIN_RANK_INDEX]}»")))
    zone = conn.execute("SELECT hunt_zone_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if zone and zone["hunt_zone_id"]:
        here = zone["hunt_zone_id"] == player.location_id
        w_acts.append(act(f"Zona di caccia della setta: {_loc_name(conn, zone['hunt_zone_id'])} (merito ×1,5)",
                          "huntzone" if here else f"vai #{zone['hunt_zone_id']}"))
    secs.append(section("Guerre, razzie, invasioni e caccia", w_lines, w_acts, icon="🔥"))
    secs.append(_own_section(conn, player))
    return menu("setta", f"✦ {m['sect_name']}", sub, secs)


# ================================================================ comando

def command(conn, player, arg: str) -> str:
    from engine.systems import own_sect, sect_politics, guild, menus
    from engine.cli import loop
    p = arg.strip().split()
    sub = p[0].lower() if p else ""
    rest = " ".join(p[1:])
    t = tick_mod.get_tick(conn)
    if sub in ("mia", "fondata", "mine"):
        return own_sect.describe(conn, player)
    if sub in ("riscuoti", "collect", "tributi"):
        return own_sect.collect(conn, player)
    if sub in ("recluta", "recruit"):
        return own_sect.recruit(conn, t, random.Random(t * 53 + player.id), player)
    if sub in ("difendi", "defend", "difesa"):
        return own_sect.defend(conn, t, random.Random(t * 59 + player.id), player)
    if not sub:
        if not _m(conn, player.id) and own_sect.get(conn):
            return own_sect.describe(conn, player) + "\n\n" + menus.show(conn, player, "setta")
        return menus.show(conn, player, "setta")
    if sub in ("ascesa", "ascend"):
        return describe_ascent(conn, player)
    if sub in ("ascendi", "accetta", "sali"):
        return ascend(conn, player, rest)
    if sub in ("rimanda", "pensaci"):
        return postpone(conn, player)
    if sub in ("rifiuta", "resta", "lealta", "lealtà"):
        return refuse(conn, player)
    if sub in ("impara", "learn", "tecnica"):
        return loop.cmd_learn(conn, player, rest)
    if sub in ("compra", "buy", "tesoro"):
        return buy(conn, player, rest) if rest else menus.show(conn, player, "setta")
    if sub in ("promozione", "promuovi", "rango"):
        return promote(conn, player)
    if sub in ("stipendio", "paga"):
        return stipend(conn, player)
    if sub in ("missioni", "missione", "bacheca"):
        return sect_politics.missions(conn, player, rest)
    if sub in ("anziani",):
        return sect_politics.describe_elders(conn, player)
    if sub in ("servi",):
        return sect_politics.serve(conn, player, rest)
    if sub in ("metodo", "gongfa"):
        from engine.systems import gongfa
        return gongfa.from_sect(conn, player)
    return menus.show(conn, player, "setta")
