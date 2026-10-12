"""
Comandi di SETTA del terminale (spostati da loop.py per tenerlo leggibile): elenco delle sette,
iscrizione, inviti e ascesa, tecniche e merito, sfide di rango, razzie, invasioni, guerre, ritorno
alla sede. I nomi restano disponibili anche come loop.cmd_* (loop li reimporta).
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick
from engine.simulation import world_tick, combat, cultivation
from engine.cli.loop import (_after_arrival, _attack_auto, _danger_tag, _first_step_toward, _format_observations, _hop_distance, _travel_to, render_location)  # noqa: F401


def _rank_duel(conn, rng, player, opp_name, idx) -> tuple[bool, list[str]]:
    """Duello di rango (NON letale): il tuo potere REALE contro la soglia attesa per il rango
    superiore. Se sei sovra-allenato per il tuo rango, lo travolgi; se sei acerbo, perdi."""
    from engine.simulation import cultivation
    pcp = combat.combat_power(conn, "player", player.id)
    power = pcp["attack"] + pcp["defense"] * 0.5 + pcp["vitality"] * 0.4
    realm = cultivation.realm_tier(conn, "player", player.id) or 1
    # soglia del rango successivo: cresce col regno e (di più) col rango da scalare
    baseline = (realm * 70 + (idx + 1) * 60) * (1.0 + 0.06 * idx)
    score = power * rng.uniform(0.8, 1.2)
    win = score >= baseline
    margin = score / max(1.0, baseline)
    lines = [f"⚔ SFIDA DI RANGO — affronti {opp_name}, un anziano un gradino sopra di te!"]
    if win:
        lines.append("Lo travolgi scambio dopo scambio." if margin > 1.4
                     else "Lotta serrata, ma alla fine lo pieghi.")
    else:
        lines.append("La sua esperienza superiore ti respinge." if margin < 0.75
                     else "Per un soffio non basta: ti manca ancora qualcosa.")
    return win, lines


def cmd_challenge(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Sfida un discepolo di rango superiore: se vinci, ne prendi il posto (sali di categoria)."""
    from engine.systems import sects, reputation, training
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni a nessuna setta: non c'è nessun rango da scalare."
    ladder = sects.RANK_LADDER
    cur = m["rank"] if m["rank"] in ladder else ladder[0]
    idx = ladder.index(cur)
    if idx >= len(ladder) - 1:
        return f"Sei già al rango massimo della tua setta («{cur}»): non c'è nessuno sopra di te."
    nxt = ladder[idx + 1]
    # cooldown: una sfida al giorno
    day = training.current_day(tick.get_tick(conn))
    cd = conn.execute("SELECT value FROM game_state WHERE key='challenge_day';").fetchone()
    if cd and int(cd["value"]) == day:
        return "Hai già lanciato una sfida di rango oggi. Riprova domani (riposa o allenati)."
    conn.execute("INSERT INTO game_state (key, value) VALUES ('challenge_day', ?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (str(day),))

    opp_name = f"Anziano «{nxt}»"
    win, lines = _rank_duel(conn, random.Random(tick.get_tick(conn) * 7 + player.id),
                            player, opp_name, idx)
    world_tick.advance(conn, tick.cost_of("move"))
    if win:
        promo = sects.promote_rank(conn, player.id)
        reputation.adjust(conn, player.id, fame=15)
        lines.append(f"★ Hai SCONFITTO {opp_name}! Ne prendi il posto: ora sei «{promo['rank']}». (+15 fama)")
        if promo.get("top"):
            lines.append("Sei in cima alla tua setta: ora puoi guidare un'invasione ('invade').")
    else:
        lines.append(f"Vieni respinto da {opp_name}: non sei ancora pronto. Allenati e riprova domani.")
    return "\n".join(lines)


def cmd_invade(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Guida la tua setta all'invasione della setta rivale con sede qui (richiede rango alto)."""
    from engine.systems import sect_invasion
    t = tick.get_tick(conn)
    res = sect_invasion.lead_invasion(conn, t, random.Random(t * 53 + player.id), player)
    if res["status"] in ("conquered", "repelled"):
        world_tick.advance(conn, 2)        # un'invasione è un evento, il mondo gira
    return "\n".join(res["lines"])


def cmd_raid(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Assalta da solo la sede di una setta rivale: abbatti i membri presenti e, se
    li sconfiggi tutti, saccheggia manuali e tesori e ne spezzi l'influenza."""
    from engine.systems import sects, guild, items
    hq = sects.sect_at_location(conn, player.location_id)
    if not hq:
        return "Qui non ha sede nessuna setta da razziare. Raggiungi la sede di una setta rivale."
    m = sects.get_membership(conn, player.id)
    if m and m["faction_id"] == hq["id"]:
        return "Questa è la TUA setta: non puoi razziarla. ('leave' prima, se proprio vuoi.)"
    from engine.systems import dominion
    if hq["id"] in dominion.vassal_ids(conn):
        return f"{hq['name']} è tua vassalla: ciò che ha è già tuo ('dominio')."
    members = conn.execute(
        "SELECT id, name FROM npcs WHERE faction_id=? AND status='alive' AND kind='human' "
        "AND location_id=? ORDER BY id;", (hq["id"], player.location_id)).fetchall()
    if not members:
        return f"Non c'è nessun membro di {hq['name']} da affrontare qui ora."
    out = [f"⚔ RAZZIA — assalti da solo la sede di {hq['name']} ({len(members)} presenti)!"]
    killed = 0
    for r in members:
        p = entities.get_player(conn, player.id)
        if p.status != "alive":
            out.append("Cadi nell'assalto: la razzia fallisce.")
            break
        npc = entities.get_npc(conn, r["id"])
        if npc is None:
            continue
        res = _attack_auto(conn, p, npc, None)
        if ("hai ucciso" in res) or ("★" in res):
            killed += 1
        rl = [ln for ln in res.split("\n") if ln.strip()]
        out.append(f"  • {r['name']}: {rl[-1].strip() if rl else '...'}")
    out.append(f"Membri abbattuti: {killed}/{len(members)}.")

    p = entities.get_player(conn, player.id)
    remaining = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE faction_id=? AND status='alive' AND kind='human' "
        "AND location_id=?;", (hq["id"], player.location_id)).fetchone()["c"]
    drops = loot_drops = entities.dead_npcs_in_location(conn, player.location_id)
    if drops:
        out.append("⚑ Resti e bottino a terra: usa 'loot' e 'absorb all'.")
    if p.status == "alive" and remaining == 0:
        frow = conn.execute("SELECT wealth, influence FROM factions WHERE id=?;",
                            (hq["id"],)).fetchone()
        booty = max(50, (frow["wealth"] or 0) // 2 + 80)
        sects.grant_resource(conn, "pietre_spirituali", booty, player.id)
        conn.execute("UPDATE factions SET wealth=MAX(0, wealth-?), "
                     "influence=MAX(0, influence-40) WHERE id=?;", (booty, hq["id"]))
        # ruba un manuale di tecnica segreta della setta
        techs = guild.sect_techniques(conn, hq["id"])
        steal = ""
        if techs:
            tname = f"Manuale Rubato: {techs[0]['name']}"
            iid = items.create_item(
                conn, tname, "manuale", "prezioso",
                f"Tecnica segreta sottratta a {hq['name']}.",
                {"learn_technique": {"name": techs[0]["name"],
                                     "magnitude": float(techs[0]["magnitude"]),
                                     "tech_key": f"stolen:{hq['id']}:{techs[0]['key']}"}})
            items.grant(conn, "player", player.id, iid, 1)
            steal = f" Trafughi un manuale segreto: «{techs[0]['name']}» (nello zaino, 'use')."
        from engine.systems import reputation
        reputation.apply_deed(conn, player.id, infamy=20, fame=8)
        out.append(f"SACCHEGGIO RIUSCITO: spezzi l'influenza di {hq['name']} e razzii "
                   f"{booty} pietre spirituali.{steal}")
        out.append("La notizia si spande: temuto e infame in egual misura.")
    elif p.status == "alive":
        out.append(f"Restano difensori di {hq['name']}: la sede non è ancora caduta. "
                   f"Riprenditi e torna a finire l'opera.")
    from engine.simulation import world_tick
    world_tick.advance(conn, 1)
    return "\n".join(out)


def cmd_sects(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    rows = sects.joinable_sects(conn)
    if not rows:
        return "Non si conoscono sette in questo mondo."
    m = sects.get_membership(conn, player.id)
    lines = ["Sette conosciute (vai alla sede e usa 'join'):"]
    for r in rows:
        here = " ← sei qui" if r["home_location_id"] == player.location_id else ""
        mine = " [la tua setta]" if m and m["faction_id"] == r["id"] else ""
        el = f", affine al {sects._dao_display(conn, r['element'])}" if r["element"] else ""
        from engine.systems import alignment
        al = alignment.label(conn, r["id"])
        al = f" [{al}]" if al else ""
        lines.append(f"  · {r['name']}{al} — {sects.tier_name(r['tier'])}{el} — sede: {r['hq_name']}{here}{mine}")
    if m:
        tn = sects.tier_name(m["sect_tier"])
        lines.append(f"\nSei {m['rank']} di {m['sect_name']} ({m['grade']}) — {tn}.")
        if sects.pending_invitations(conn, player.id):
            lines.append("Hai inviti pendenti da sette superiori: usa 'invitations'.")
    return "\n".join(lines)


def cmd_join(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    t = tick.get_tick(conn)
    here = sects.sect_at_location(conn, player.location_id)
    if here and not sects.get_membership(conn, player.id):
        from engine.systems import alignment
        ok, why = alignment.can_join(conn, player.id, here["id"])
        if not ok:
            return why
    res = sects.join_sect(conn, t, player.id)
    s = res["status"]
    if s == "no_sect_here":
        return "Qui non c'è la sede di alcuna setta. Usa 'sects' per sapere dove andare."
    if s == "already_member":
        return f"Sei già membro di {res['sect']}. Usa 'leave' per andartene."
    if s == "joined":
        from engine.systems import sect_life, weapons
        rng = random.Random(t * 17 + player.id)
        setup = sect_life.setup_class(conn, t, rng, player.id)
        agenda = sect_life.agenda_line(conn, t, player.id)
        mates = sect_life.classmates(conn, player.id)
        mate_names = ", ".join(m["name"] for m in mates)
        msg = (f"Ti presenti alla sede di {res['sect']}. Misurano le tue radici spirituali: "
               f"{res['grade']}.\nSei ammesso come {res['rank']}. "
               f"Ricevi {res['stones']} pietre spirituali.\n"
               f"I tuoi compagni di classe: {mate_names}.\n"
               f"Annuncio: {agenda} Allenati: la classifica deciderà chi conta.")
        if weapons.get_weapon(conn, player.id) is None:
            msg += ("\nÈ ora di scegliere la tua ARMA principale (scelta permanente): "
                    "usa 'weapon <spada|lancia|sciabola|arco|pugni|bastone>'.")
        return msg
    return "Nulla accade."


def cmd_leave(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    res = sects.leave_sect(conn, player.id)
    if res["status"] == "not_member":
        return "Non appartieni ad alcuna setta."
    return f"Lasci {res['sect']}. Sei di nuovo un coltivatore errante."


def cmd_invitations(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    invs = sects.pending_invitations(conn, player.id)
    if not invs:
        return ("Nessun rappresentante ti corteggia. Vinci un torneo di setta "
                "(arriva 1°) per attirare le sette superiori.")
    lines = ["I RAPPRESENTANTI delle sette superiori ti offrono un posto",
             "(usa 'accept <numero>' per ascendere — lascerai la setta attuale):"]
    for r in invs:
        lines.append(f"  {r['slot']}. {r['name']} — {r['hint']}")
    return "\n".join(lines)


def cmd_accept(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import sects
    if not arg or not arg.strip().isdigit():
        return "Accettare quale invito? Usa: accept <numero> (vedi 'invitations')."
    slot = int(arg.strip())
    t = tick.get_tick(conn)
    rng = random.Random(t * 131 + player.id + slot)
    res = sects.accept_invitation(conn, t, rng, slot, player.id)
    if res["status"] == "no_invitation":
        return f"Non c'è un invito numero {slot}. Usa 'invitations' per la lista."
    el = sects._dao_display(conn, res["element"])
    return (f"Ascendi a {res['sect']} ({sects.tier_name(res['tier'])}) come {res['rank']} "
            f"({res['grade']}). Ricevi {res['stones']} pietre spirituali. "
            f"La setta è affine al {el}: comprenderlo sarà più rapido. "
            f"Ti trasferisci alla nuova sede; una nuova classe di rivali ti attende.")


def cmd_huntzone(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni a una setta: nessuna zona di caccia. Usa 'sects'."
    f = conn.execute("SELECT hunt_zone_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if not f or not f["hunt_zone_id"]:
        return "La tua setta non ha una zona di caccia designata."
    zid = f["hunt_zone_id"]
    zone = entities.get_location(conn, zid)
    alive = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind<>'human' AND status='alive';",
        (zid,)).fetchone()["c"]
    if zid == player.location_id:
        return (f"Sei nella zona di caccia di {m['sect_name']}: {zone.name} "
                f"{_danger_tag(zone.danger_level)}. Mostri presenti: {alive}. "
                f"Attaccali ('attack <nome>') per guadagnare merito; puoi anche assorbirli.")
    step = _first_step_toward(conn, player.location_id, zid)
    where = f"{zone.name} {_danger_tag(zone.danger_level)}"
    if step:
        return (f"La zona di caccia di {m['sect_name']} è {where} (mostri: {alive}). "
                f"Muoviti verso '{step}' per raggiungerla.")
    return f"La zona di caccia di {m['sect_name']} è {where}, ma non trovo una via da qui."


def cmd_techniques(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects, guild, dao_techniques, spirit as spmod
    out: list[str] = []
    dao_list = dao_techniques.technique_list(conn, player.id)
    if dao_list:
        out.append(f"Tecniche del Dao (Guerriero Dao) — Spirito: {spmod.spirit_label(conn, player.id)}:")
        out += [f"  ◈ {ln}" for ln in dao_list]
        out.append("  Nascono dai tuoi Dao (≥10) ed evolvono a soglie; affaticano lo Spirito, non il Qi.")
        from engine.systems import elements
        out += ["  " + ln for ln in elements.describe(conn, player.id)]
    m = sects.get_membership(conn, player.id)
    if not m:
        if not dao_list:
            return ("Non hai tecniche. Le tecniche Dao nascono coltivando un Dao fino a "
                    "comprensione ≥10 ('comprehend <dao>'); le tecniche segrete richiedono una setta.")
        return "\n".join(out)
    techs = guild.sect_techniques(conn, m["faction_id"])
    merit = guild.get_merit(conn, player.id)
    if out:
        out.append("")
    out.append(f"Tecniche segrete di {m['sect_name']} (merito disponibile: {merit}):")
    for t in techs:
        if guild.is_learned(conn, t["key"], player.id):
            mark = "✔ appresa"
        else:
            mark = f"costo {t['cost']} merito"
        out.append(f"  {t['rank']}. {t['name']} — +{int(t['magnitude']*100)}% potenza — {mark}")
    out.append("Guadagna merito cacciando i mostri ('huntzone'); 'learn <n>' per apprendere.")
    return "\n".join(out)


def cmd_learn(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import guild
    if not arg.strip().isdigit():
        return "Imparare quale tecnica? Usa: learn <numero> (vedi 'techniques')."
    t = tick.get_tick(conn)
    res = guild.learn(conn, t, int(arg.strip()), player.id)
    s = res["status"]
    if s == "no_sect":
        return "Non appartieni a una setta."
    if s == "no_such":
        return "Quella tecnica non esiste. Usa 'techniques'."
    if s == "already":
        return f"Conosci già {res['name']}."
    if s == "poor":
        return (f"Merito insufficiente per {res['name']}: servono {res['need']}, "
                f"ne hai {res['have']}. Caccia altri mostri ('huntzone').")
    return (f"Apprendi {res['name']}! La tua potenza cresce (+{int(res['magnitude']*100)}%). "
            f"Merito residuo: {res['merit']}.")


def cmd_class(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects, sect_life
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni ad alcuna setta. Usa 'sects' per trovarne una."
    t = tick.get_tick(conn)
    lines = [f"Setta: {m['sect_name']} — {m['rank']} ({sects.tier_name(m['sect_tier'])})"]
    from engine.systems import guild
    lines.append(f"Merito: {guild.get_merit(conn, player.id)} (caccia i mostri con 'huntzone'; 'techniques' per spenderlo)")
    if m["class_rank"]:
        lines.append(f"Posizione attuale in classifica: {m['class_rank']}°")
    mates = sect_life.classmates(conn, player.id)
    if mates:
        lines.append("Compagni di classe (rivali) e loro coltivazione:")
        for m2 in mates:
            realm = cultivation.realm_label(conn, "npc", m2["id"])
            tr = conn.execute("SELECT talent FROM sect_cohort WHERE player_id=? AND npc_id=?;",
                              (player.id, m2["id"])).fetchone()
            tal = tr["talent"] if tr else 50
            tlab = ("talento eccelso" if tal >= 80 else "molto dotato" if tal >= 60
                    else "dotato" if tal >= 45 else "nella media")
            lines.append(f"  · {m2['name']} — {realm} ({tlab})")
        lines.append("Ogni giorno coltivano: i più dotati ti incalzano in fretta.")
    ag = sect_life.agenda_line(conn, t, player.id)
    if ag:
        lines.append("Prossimo evento — " + ag)
    return "\n".join(lines)


def cmd_war(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sect_war
    war = sect_war.active_war(conn)
    if not war:
        return "Nessuna guerra tra sette in corso. (Se appartieni a una setta, può scoppiare.)"
    return sect_war.describe(conn, war, player.location_id, _first_step_toward)


def cmd_spare(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Sottometti e risparmia un discepolo nemico al fronte (richiede di essere abbastanza forte)."""
    from engine.systems import sect_war
    if not arg:
        return "Risparmiare chi? Usa: spare <nome> (su un discepolo nemico al fronte)."
    war = sect_war.active_war(conn)
    if not war or war["battle_location_id"] != player.location_id:
        return "Non sei a un fronte di guerra: non c'è nessun nemico da risparmiare qui."
    enemies = sect_war.enemy_disciples(conn, war)
    low = arg.strip().lower()
    target = next((e for e in enemies if low in e["name"].lower()), None)
    if target is None:
        return f"Nessun discepolo nemico di nome '{arg}' al fronte."
    pr = combat.combat_power(conn, "player", player.id)
    er = combat.combat_power(conn, "npc", target["id"])
    p_rating = pr["attack"] * 0.5 + pr["defense"] * 0.3 + pr["vitality"] * 0.2
    e_rating = er["attack"] * 0.5 + er["defense"] * 0.3 + er["vitality"] * 0.2
    if p_rating < e_rating:
        return (f"{target['name']} è troppo forte per essere sottomesso a mani basse: "
                f"se vuoi affrontarlo devi combatterlo ('attack {arg}').")
    t = tick.get_tick(conn)
    msg = sect_war.on_enemy_defeated(conn, t, player, target["id"], "spare")
    obs = world_tick.advance(conn, tick.cost_of("short_rest"))
    out = f"Sopraffai {target['name']} e gli concedi la vita. " + (msg or "")
    from engine.systems import feuds
    _sp = feuds.on_spare(conn, t, random.Random(t + target["id"]), player, entities.get_npc(conn, target["id"]), True)
    if _sp:
        out += "\n" + "\n".join(_sp)
    if obs:
        out += "\n" + _format_observations(obs)
    return out


def cmd_to_war(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Ti porta direttamente al fronte di guerra attivo più vicino."""
    rows = conn.execute(
        "SELECT location_id, COUNT(*) c FROM npcs WHERE war_id IS NOT NULL AND status='alive' "
        "AND location_id IS NOT NULL GROUP BY location_id;").fetchall()
    if not rows:
        return ("Nessuna guerra di setta in corso al momento. "
                "(Le guerre nascono tra sette rivali: controlla 'events'.)")
    best, bestd = None, 1e9
    for r in rows:
        d = _hop_distance(conn, player.location_id, r["location_id"])
        if d is not None and d < bestd:
            bestd, best = d, r["location_id"]
    if best is None:
        best = rows[0]["location_id"]
    return _travel_to(conn, player, best, "raggiungi il fronte di guerra. Usa 'attack all' o 'attack <nome>'.")


def cmd_to_raid(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Ti porta direttamente alla sede di una setta rivale, pronta per il 'raid'."""
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    my_fac = m["faction_id"] if m else -1
    rows = conn.execute(
        "SELECT id, name, home_location_id FROM factions WHERE status='active' "
        "AND home_location_id IS NOT NULL AND id<>?;", (my_fac,)).fetchall()
    if not rows:
        return "Non ci sono sette rivali con una sede raggiungibile."
    best, bestd = None, 1e9
    for r in rows:
        d = _hop_distance(conn, player.location_id, r["home_location_id"])
        if d is not None and d < bestd:
            bestd, best = d, r
    if best is None:
        best = rows[0]
    return _travel_to(conn, player, best["home_location_id"],
                      f"raggiungi la sede di {best['name']}. Usa 'raid' per attaccarla.")


def cmd_home(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Torna direttamente alla sede della tua setta (evita di perderti)."""
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if m is None:
        return "Non appartieni a nessuna setta. ('join' per iscriverti dove possibile.)"
    home = conn.execute("SELECT home_location_id FROM factions WHERE id=?;",
                        (m["faction_id"],)).fetchone()
    if not home or home["home_location_id"] is None:
        return "La tua setta non ha una sede raggiungibile."
    dest = home["home_location_id"]
    if dest == player.location_id:
        return "Sei già alla sede della tua setta.\n" + render_location(conn, player)
    entities.move_player(conn, player.id, dest)
    obs = world_tick.advance(conn, tick.cost_of("move"))
    moved = entities.get_player(conn, player.id)
    out = (f"Tick {tick.get_tick(conn)} — torni alla sede della tua setta.\n"
           + render_location(conn, moved))
    if obs:
        out += "\nNel frattempo:\n" + _format_observations(obs)
    return out + _after_arrival(conn, moved)
