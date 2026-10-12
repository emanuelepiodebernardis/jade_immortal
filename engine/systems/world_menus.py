"""
I menu del mondo: ARTI, REGNI, EVENTI e l'indice di tutti i menu (vedi menus.py).
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state
from engine.systems.menus import act, bar, menu, section


def _stones(conn, pid) -> int:
    from engine.systems import sects
    return sects.get_resource(conn, "pietre_spirituali", pid)


def _where(conn, player, loc) -> str:
    from engine.systems.travel import _distance, _loc_name
    d = _distance(conn, player.location_id, loc)
    return f"{_loc_name(conn, loc)} — " + ("QUI" if d == 0 else f"{d} tappe" if d is not None else "un altro mondo")


# ================================================================ ARTI

def arts(conn, player) -> dict:
    from engine.systems import professions as P
    d = P.menu_data(conn, player.id)
    on = d["pratichi"]
    choose = [act("Praticale tutte", "arti tutte", ok=len(on) < len(P.PROFESSIONS), why="le pratichi già tutte"),
              act("Non praticarne nessuna (Qi e Dao al centro)", "arti nessuna", ok=bool(on), why="non ne pratichi")]
    secs = [section("Quali arti praticare", [
        "Le arti IN PRATICA crescono insieme a ogni 'train' (più sono, più piano cresce ciascuna) "
        "e il pilota automatico crea con le loro ricette. Le altre restano tue, a riposo."], choose, icon="⚒")]
    for a in d["arti"]:
        acts = []
        if a["conosciuta"]:
            acts.append(act("Smetti di praticarla" if a["pratica"] else "Riprendi a praticarla",
                            f"arti {'smetti' if a['pratica'] else 'pratica'} {a['key']}"))
            if not a["principale"]:
                acts.append(act("Rendila l'arte principale (classe e capolavori)", f"arti principale {a['key']}"))
            for r in a["ricette"]:
                if r["ok"]:
                    acts.append(act(f"Crea: {r['nome']} — {r['costo']}", f"craft {a['key']} {r['n']}",
                                    ok=r["pronta"], why="mancano i materiali"))
            locked = [r for r in a["ricette"] if not r["ok"]]
            lines = [a["desc"].capitalize()]
            if locked:
                lines.append(f"Prossima ricetta: {locked[0]['nome']} (livello {locked[0]['livello']}).")
            title = (f"{a['nome']}{' ★' if a['principale'] else ''} — livello {a['livello']}"
                     f" · {'IN PRATICA' if a['pratica'] else 'a riposo'}")
            secs.append(section(title, lines, acts, [bar("Esperienza", a["pct"], f"{a['xp']}/{a['prossimo']}")]))
        else:
            secs.append(section(f"{a['nome']} — mai praticata", [a["desc"].capitalize()],
                                [act("Inizia a praticarla", f"arti pratica {a['key']}")]))
    mats = ", ".join(f"{k} {v}" for k, v in d["materiali"].items())
    here = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    wild = here and here["location_type"] in ("mountain", "forbidden_zone", "ruin")
    secs.append(section("Materiali", [mats], [act("Raccogli materiali qui", "gather", ok=bool(wild),
                                                  why="servono montagne, rovine o zone proibite")], icon="✿"))
    return menu("arti", "⚒ LE TUE ARTI", [("Pratichi: " + ", ".join(P.PROFESSIONS[k] for k in on)) if on
                                          else "Non pratichi nessuna arte."], secs)


# ================================================================ REGNI

def realms(conn, player) -> dict:
    from engine.systems import kingdoms as K, races as R, perception
    from engine.simulation import cultivation
    d = K.all_k(conn) or K.ensure(conn)
    stones = _stones(conn, player.id)
    secs = []
    kk = K.kingdom_of(conn, player.location_id)
    if kk:
        rk, k = kk
        nxt = next(((th, nm) for th, nm in K.RANKS if th > k["favor"]), None)
        lines = [f"Sovrano: {'TU' if k['ruler_player'] else K._name(conn, k['king'])}",
                 f"Il tuo rango: {K.rank_of(k['favor'])} (favore {k['favor']})",
                 "Il favore cresce con i tributi e abbattendo banditi, ricercati e mostri nelle sue terre."]
        bars = [bar(f"Verso «{nxt[1]}»", 100 * k["favor"] / nxt[0], f"{k['favor']}/{nxt[0]}")] if nxt else []
        acts = []
        for n in (100, 500, 2000):
            acts.append(act(f"Offri un tributo di {n} pietre (+{n // 10} favore)", f"tributo {n}", ok=stones >= n,
                            why=f"hai {stones} pietre"))
        for p in k["princes"]:
            nm = K._name(conn, p)
            if "✝" not in nm:
                acts.append(act(f"Sostieni il principe {nm} nella successione" + (" ✓" if p == k["backed"] else ""),
                                f"sostieni {nm.split()[0]}", ok=p != k["backed"], why="lo sostieni già"))
        if k.get("war"):
            lines.append(f"⚔ In guerra contro il {k['war']['enemy']}!")
            acts.append(act("Scendi in campo per il regno", "guerra_regni", ok=not k["war"].get("fought"),
                            why="hai già combattuto in questa guerra", main=True))
        if not k["ruler_player"]:
            strong = perception.strength_ratio(conn, player.id, k["king"]) >= 1.2
            acts.append(act("Prendi il trono con la forza", "trono", ok=k["favor"] >= 1500 and strong,
                            why="serve il rango di Duca" if k["favor"] < 1500 else "il sovrano è ancora più forte di te"))
        secs.append(section(f"{k['name']} (sei qui)", lines, acts, bars, icon="👑"))
    else:
        secs.append(section("Fuori dai regni", ["Qui non governa nessun regno: raggiungi una capitale."]))
    allk = []
    for rk, k in d.items():
        if kk and rk == kk[0]:
            continue
        war = f" ⚔ in guerra col {k['war']['enemy']}" if k.get("war") else ""
        allk.append(act(f"{k['name']} — rango {K.rank_of(k['favor'])}{war} — vai a {_where(conn, player, k['capital'])}",
                        f"vai #{k['capital']}"))
    secs.append(section("Tutti i regni", [], allk, icon="🗺"))
    racts, rlines = [], []
    for key, r in R.all_r(conn).items():
        nm = R.RACES[key][0]
        st = "ALLEATI" if r["rel"] >= 60 else ("IN GUERRA" if r["rel"] <= -60 else f"rapporto {r['rel']:+d}")
        rlines.append(f"{nm}: {st} · onore {r['honor']} ({R.honor_rank(r['honor'])})")
        here = key == "maree" or (r["land"] and r["land"] == player.location_id)
        if here:
            racts.append(act(f"{nm}: dona 100 pietre", f"ambasciata {key} dona 100", ok=stones >= 100,
                             why=f"hai {stones} pietre"))
            racts.append(act(f"{nm}: affronta il loro campione", f"razza {key} sfida"))
        elif r["land"]:
            racts.append(act(f"{nm}: vai nelle loro terre ({_where(conn, player, r['land'])})", f"vai #{r['land']}"))
    racts.insert(0, act("I regni delle razze: campioni, sangue, reliquie, la scala fino al trono", "razze", main=True))
    secs.append(section("Le razze antiche", rlines, racts, icon="🐉"))
    return menu("regni", "👑 REGNI, CORTI E RAZZE", [], secs)


# ================================================================ EVENTI

def events(conn, player) -> dict:
    from engine.systems import (travel, assembly, auction, contests, secret_realms, eras, world_events,
                                sect_war, sects, sect_life, celestial_elements, family)
    from engine.systems.travel import _distance
    secs = []
    stones = _stones(conn, player.id)
    # in corso adesso, con i comandi diretti
    for d in travel.destinations(conn, player):
        if d["key"] in ("casa", "setta"):
            continue
        here = _distance(conn, player.location_id, d["loc"]) == 0
        acts, lines = [], [_where(conn, player, d["loc"])]
        if d["key"] == "assemblea":
            a = assembly.current(conn)
            if a and a.get("joined") and not a.get("done") and here:
                dl = assembly.describe(conn, player).splitlines()
                lines.append(dl[-2] if len(dl) >= 2 else dl[-1])
                acts += [act("Combatti: assalto frontale", "assemblea 1", main=True),
                         act("Combatti: difesa e contrattacco", "assemblea 2"),
                         act("Combatti: tecnica segreta (consuma spirito)", "assemblea 3")]
        if d["key"] == "asta" and here:
            a = auction.current(conn)
            for i, l in enumerate((a or {}).get("lots", []), 1):
                if not l["sold"]:
                    offer = int(l["current"] * 1.25) + 10
                    acts.append(act(f"Offri {offer} pietre per {l['name']} (ora {l['current']})",
                                    f"asta offri {i} {offer}", ok=stones >= offer, why=f"hai {stones} pietre"))
        if d["join"] and here:
            acts.insert(0, act("Partecipa ora", d["join"], main=True))
        elif d["join"]:
            acts.insert(0, act("Raggiungilo e partecipa", f"iscriviti {d['key']}", main=True))
        if not here:
            acts.append(act("Raggiungilo soltanto", f"vai {d['key']}"))
        if d["key"] == "gara" and not d["join"]:
            art = (contests.current(conn) or {}).get("art")
            if art:
                acts.append(act(f"Impara l'arte per partecipare ({art})", f"arti pratica {art}"))
        secs.append(section(d["title"], lines, acts, icon="✦"))
    rr = secret_realms.run(conn)
    if rr:
        secs.insert(0, section("Sei dentro un reame segreto", [],
                               [act("Scendi al piano successivo", "delve", main=True),
                                act("Esci tenendo ciò che hai preso", "realm esci")], icon="🌀"))
    e = eras.get(conn)
    if e["key"] == "calamita":
        secs.insert(0, section(f"Calamità: {e['calamity']}", [f"{e['waves']} ondate da respingere."],
                               [act("Affronta la prossima ondata", "calamita", main=True)], icon="☠"))
    m = sects.get_membership(conn, player.id)
    war = sect_war.active_war(conn)
    if m and war and m["faction_id"] in (war["player_faction_id"], war["enemy_faction_id"]):
        at = war["battle_location_id"] == player.location_id
        secs.insert(0, section("Guerra tra sette", [_where(conn, player, war["battle_location_id"])],
                               [act("Combatti al fronte" if at else "Raggiungi il fronte", "war" if at else "fronte",
                                    main=True)], icon="🔥"))
    # calendario: ciò che verrà
    cal = []
    if m:
        ag = sect_life.agenda_line(conn, tick_mod.get_tick(conn), player.id)
        if ag:
            cal.append(f"Setta — {ag}")
    if not assembly.current(conn):
        cal.append(assembly.describe(conn, player))
    if not auction.current(conn):
        cal.append(auction.describe(conn, player))
    cal += [ln.strip() for ln in eras.describe(conn, player).splitlines()[:3]]
    wev = world_events.active_event(conn)
    if not wev:
        cal.append("Nessuna invasione in corso.")
    secs.append(section("Il calendario del mondo", cal,
                        [act("Tutte le mete", "mete"), act("Classifiche del Cielo", "classifica")], icon="📅"))
    return menu("eventi", "✦ EVENTI DEL MONDO", ["Tutto ciò a cui puoi partecipare, con i comandi pronti."], secs)


# ================================================================ INDICE

def hub(conn, player) -> dict:
    from engine.systems import sects, professions, own_sect
    m = sects.get_membership(conn, player.id)
    acts = [act("Setta — " + (m["sect_name"] if m else "dove iscriverti"), "setta", main=True),
            act("Arti — " + (", ".join(professions.PROFESSIONS[k] for k in professions.practiced(conn))
                             or "scegli quali praticare"), "arti"),
            act("Regni, corti e razze antiche", "regni"),
            act("Eventi del mondo", "eventi"),
            act("Coltivazione: allenamento, sfondamento, Dao, dimora", "coltivazione"),
            act("Grotta-dimora", "dimora"),
            act("Famiglia, legami e discepoli", "famiglia"),
            act("Il Libro dei Rancori e dei Debiti (faide e alleanze)", "faide"),
            act("Dominio: servi sigillati, salme, sette vassalle", "dominio")]
    if own_sect.get(conn):
        acts.append(act("La setta che hai fondato", "setta mia"))
    more = [act("Mete (vai / iscriviti)", "mete"), act("La trama", "trama"), act("La tua storia", "goals"),
            act("Tesori", "tesori"), act("Legami", "bonds"), act("Favori", "favori"), act("Cronaca", "cronaca"),
            act("Svolte", "svolte"), act("Classifiche", "classifica"), act("Il ritmo della storia", "ritmo")]
    return menu("menu", "☰ MENU", ["Ogni parte del gioco, con le azioni pronte."],
                [section("Menu", [], acts), section("Pannelli", [], more)])


# ================================================================ COLTIVAZIONE

def growth(conn, player) -> dict:
    from engine.simulation import cultivation
    from engine.systems import dao_training, dao_powers, gongfa, cave_abode, training, qi as qimod, train_all
    t = tick_mod.get_tick(conn)
    rec = cultivation.get_record(conn, "player", player.id)
    stage = (rec["stage"] or 1) if rec else 1
    prog = float(rec["progress"] or 0) if rec else 0.0
    ready = stage >= 10 and prog >= 1.0
    sess = training.sessions_today(conn, t, "player", player.id)
    secs = []
    secs.append(section("Allenamento", [f"Sessioni di oggi: {sess} (le prime rendono di più)."], [
        act("Allenati: Qi, Dao, spirito e arti insieme", "train", main=True),
        act("Medita solo sul Qi", "cultivate"),
        act("Ritiro a porte chiuse per 5 giorni", "ritiro 5"),
        act("Ritiro di 20 giorni", "ritiro 20"),
        act("Dormi fino all'alba", "sleep")],
        [bar("Strato " + str(stage) + "/10", prog * 100)], icon="☯"))
    from engine.systems import soul_temper as ST, perception as _perc
    sg, sxp, slo, shi = ST.progress(conn)
    secs.append(section("Spirito (tempra dell'anima)", [
        f"{ST.grade_name(sg)} (grado {sg}) · punteggio di spirito {_perc.spirit_score(conn, 'player', player.id):.0f}",
        "Lo spirito decide chi puoi sigillare, allarga la riserva per le tecniche Dao e il senso divino."], [
        act("Tempra lo spirito (seduta dedicata)", "tempra", main=True),
        act("Il tuo dominio: servi, salme, sette vassalle", "dominio")],
        [bar("Verso il grado " + str(sg + 1), 100 * (sxp - slo) / max(1, shi - slo), tone="info")], icon="🌀"))
    trib = dao_powers.tribulation_due(conn, player.id) > 0
    secs.append(section("Sfondamento", [cultivation.realm_label(conn, "player", player.id)], [
        act("Tenta lo sfondamento al regno successivo", "breakthrough", ok=ready,
            why="prima arriva al colmo dello strato 10"),
        act("Affronta la tribolazione celeste", "tribulation", ok=trib, why="nessuna tribolazione in attesa"),
        act("Le tue tribolazioni", "tribolazioni")], icon="⇑"))
    d_acts = []
    for d in dao_training.trainable_daos(conn, player.id)[:8]:
        d_acts.append(act(f"Medita sul {d['name']} (comprensione {d['comprehension']})",
                          f"comprehend {d['dao_key']}"))
    d_acts += [act("Tutti i tuoi Dao", "dao"), act("Svolte e Dao tutto tuo", "svolte")]
    secs.append(section("Dao", [], d_acts, icon="☸"))
    g = gongfa.active(conn, player.id)
    g_acts = [act(f"Pratica: {m['name']}", f"gongfa pratica {i}", ok=m is not g, why="lo pratichi già")
              for i, m in enumerate(gongfa.known(conn, player.id), 1)]
    secs.append(section("Metodo di coltivazione", [f"Pratichi: {g['name']}" if g else "Non pratichi alcun metodo."],
                        g_acts + [act("Radici spirituali", "radici"), act("Corpo e cuore del Dao", "corpo")],
                        icon="📜"))
    ab = cave_abode.get(conn, player.id)
    if ab:
        steps, cost = cave_abode.plan_max(ab, _stones(conn, player.id))
        n = sum(b - a for _k, a, b in steps)
        home = player.location_id == ab["loc"]
        secs.append(section(f"Grotta-dimora: {ab['name']}", [], [
            act("Apri il menu della dimora", "dimora", main=True),
            act(f"Potenzia al massimo ({n} livell{'o' if n == 1 else 'i'}, {cost} pietre)", "dimora potenzia max",
                ok=bool(n) and home, why="devi essere alla dimora" if n else "non hai abbastanza pietre")], icon="⌂"))
    else:
        secs.append(section("Grotta-dimora", ["Una casa tra le montagne: coltivi e crei meglio, produce erbe e nuclei."],
                            [act("Apri il menu della dimora", "dimora")], icon="⌂"))
    return menu("coltivazione", "☯ COLTIVAZIONE", [cultivation.realm_label(conn, "player", player.id)], secs)


# ================================================================ FAMIGLIA E LEGAMI

_BOND = {"companion": "compagno di viaggio", "master": "maestro", "sworn": "fratello giurato",
         "dao_partner": "compagna del Dao", "fiancee": "fidanzata", "lover": "amata", "rival": "rivale",
         "nemesis": "nemesi", "disciple": "discepolo"}


def family_menu(conn, player) -> dict:
    from engine.systems import family, dialogues, bonds
    from engine.simulation import cultivation
    secs = []
    d = family.get(conn)
    if d:
        home = player.location_id == d["home"]
        lines = [f"{m['role']}: {family._name(conn, m['id'])}" for m in d["members"]]
        acts = []
        if d.get("threat"):
            acts.append(act(f"Difendili da {d['threat']['enemy']}!", "famiglia difendi" if home else "iscriviti famiglia",
                            main=True))
        acts += [act("Vai a trovarli (calma il cuore del Dao)", "famiglia visita" if home else f"vai #{d['home']}"),
                 act("Dona 100 pietre al clan", "famiglia dona 100", ok=_stones(conn, player.id) >= 100,
                     why="ti mancano le pietre")]
        secs.append(section(f"{d['clan']} — livello {d['level']}", lines, acts,
                            [bar("Prossimo livello", 100 * d["gifts"] / max(1, family.level_need(d["level"])))],
                            icon="🏠"))
    bonds.ensure_table(conn)
    rows = conn.execute("SELECT b.npc_id, b.kind, n.name, n.location_id, n.status FROM bonds b JOIN npcs n "
                        "ON n.id=b.npc_id WHERE b.player_id=? AND b.status='active' ORDER BY b.kind;",
                        (player.id,)).fetchall()
    reqs = dialogues.requests(conn)
    acts, lines = [], []
    for r in rows:
        if r["status"] != "alive" or r["kind"] == "family":
            continue
        first = r["name"].split()[0]
        here = r["location_id"] == player.location_id
        role = _BOND.get(r["kind"], r["kind"])
        if r["kind"] in ("nemesis", "rival"):
            acts.append(act(f"{r['name']} ({role}) — " + ("sfidalo a duello" if here else "raggiungilo"),
                            f"duello {first}" if here else f"vai #{r['location_id']}"))
            continue
        if here:
            acts.append(act(f"Parla con {r['name']} ({role})", f"parla {first}"))
        else:
            acts.append(act(f"Raggiungi {r['name']} ({role})", f"vai #{r['location_id']}"))
        if str(r["npc_id"]) in reqs:
            acts.append(act(f"Esaudisci il favore di {r['name']}", f"favore {first}", ok=here, why="non è qui"))
    if not acts:
        lines.append("Nessun legame per ora: compagni, maestri, fratelli giurati e amori nascono viaggiando.")
    secs.append(section("Legami", lines, acts + [act("Tutti i legami", "bonds"), act("Favori", "favori")], icon="♥"))
    from engine.systems import own_sect
    dis = own_sect.disciples(conn, player.id)
    if dis or own_sect.max_disciples(conn, player.id):
        dacts = [act(f"Insegna a {r['name']}", f"insegna {r['name'].split()[0]}",
                     ok=r["location_id"] == player.location_id, why="non è qui") for r in dis]
        secs.append(section(f"Discepoli ({len(dis)}/{own_sect.max_disciples(conn, player.id)})",
                            [] if dis else ["Accogli chi ti stima ed è più debole di te: 'accogli <nome>'."],
                            dacts + [act("I tuoi discepoli", "discepoli")], icon="🎓"))
    return menu("famiglia", "🏠 FAMIGLIA E LEGAMI", [], secs)


# ================================================================ DIMORA

def abode(conn, player) -> dict:
    from engine.systems import cave_abode as A, professions
    from engine.simulation import cultivation
    from engine.systems.travel import _loc_name
    ab = A.get(conn, player.id)
    stones = _stones(conn, player.id)
    if not ab:
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        here = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
        ok = here and here["location_type"] in A._SPOTS
        cost = A.claim_cost(tier)
        return menu("dimora", "⌂ GROTTA-DIMORA", ["Non hai ancora una dimora."], [section("Reclamarne una", [
            "Si scava tra montagne, rovine o zone proibite. Poi la potenzi senza limiti: erbe, Qi, ritiro, "
            "alchimia, difesa, stalla."],
            [act(f"Reclama questo luogo ({cost} pietre)", "dimora reclama", ok=bool(ok) and stones >= cost,
                 why="serve una montagna, delle rovine o una zona proibita" if not ok else f"hai {stones} pietre",
                 main=True)], icon="⌂")])
    home = player.location_id == ab["loc"]
    steps, cost = A.plan_max(ab, stones)
    n = sum(b - a for _k, a, b in steps)
    top = [act(f"Potenzia tutto al massimo possibile ora: {n} livell{'o' if n == 1 else 'i'}, {cost} pietre",
               "dimora potenzia max", ok=bool(n) and home,
               why=("devi essere alla dimora" if n else
                    f"il prossimo potenziamento costa {min(A.upgrade_cost(k, int(ab['wings'].get(k, 0))) for k in A.WINGS)} pietre, ne hai {stones}"),
               main=True)]
    if not home:
        top.append(act("Torna alla dimora", "dimora torna", main=True))
    lines = [("Sei a casa." if home else f"La dimora è a {_loc_name(conn, ab['loc'])}.") + f" Pietre: {stones}."]
    if steps:
        lines.append("Il potenziamento massimo farebbe: " + ", ".join(f"{A.WINGS[k][0]} {a}→{b}" for k, a, b in steps) + ".")
    secs = [section("Potenzia", lines, top, icon="⇑")]
    st = {k: v for k, v in ab.get("stock", {}).items() if v}
    secs.append(section("Produzione", ["Da raccogliere: " + ", ".join(f"{v} {professions.MATERIALS.get(k, k)}"
                                                                    for k, v in st.items()) if st else
                                       "Nulla da raccogliere, per ora."],
                        [act("Raccogli", "dimora raccogli", ok=bool(st) and home,
                             why="devi essere alla dimora" if st else "non c'è nulla")], icon="✿"))
    for k, (nm, _c) in A.WINGS.items():
        lv = int(ab["wings"].get(k, 0))
        c1 = A.upgrade_cost(k, lv)
        wsteps, wcost = A.plan_max(ab, stones, k)
        to = wsteps[0][2] if wsteps else lv
        acts = [act(f"Potenzia di un livello ({c1} pietre)", f"dimora potenzia {k}", ok=home and stones >= c1,
                    why="devi essere alla dimora" if not home else f"servono {c1} pietre")]
        if to > lv + 1:
            acts.append(act(f"Al massimo possibile: livello {to} ({wcost} pietre)", f"dimora potenzia {k} max",
                            ok=home, why="devi essere alla dimora"))
        secs.append(section(f"{nm} — livello {lv}", [f"Ora: {A.EFFECT[k](lv)} · al prossimo: {A.EFFECT[k](lv + 1)}"],
                            acts))
    return menu("dimora", f"⌂ {ab['name'].upper()}", [], secs)


# ================================================================ RANCORI E DEBITI

_ST = {"giurata": "si prepara", "in caccia": "ti ha trovato", "ignoto": "cerca ancora l'assassino",
       "debito": "ti deve la vita", "alleato": "accorrerà al tuo fianco", "chiusa": "chiusa col risarcimento",
       "riconciliata": "riconciliata", "vendicata": "caduto", "saldato": "debito saldato"}


def grudges(conn, player) -> dict:
    from engine.systems import feuds as F, perception
    from engine.systems.travel import _loc_name
    F.ensure_table(conn)
    day = tick_mod.get_tick(conn) // 120
    secs = []
    fs = F.feuds(conn)
    if not fs:
        secs.append(section("Faide", ["Nessuno ti cerca per vendetta. Ogni vita che togli, però, lascia qualcuno."],
                            icon="🩸"))
    for f in fs:
        here = f["location_id"] == player.location_id
        first = f["name"].split()[0]
        try:
            cmp_ = perception.relative_strength(conn, player.id, f["npc_id"])
        except Exception:
            cmp_ = ""
        lines = [f"{F.REL_LABEL.get(f['relation'], f['relation']).capitalize()} di {f['victim_name']} "
                 f"(ucciso a {f['place']}) — {_ST.get(f['status'], f['status'])}"
                 + (f" · {f['gen']}ª generazione" if f["gen"] > 1 else ""),
                 (f"Si trova a {_loc_name(conn, f['location_id'])}" if f["knows"] else "Non sa chi sei")
                 + (f" · {cmp_}" if cmp_ else "")
                 + (f" · arriverà tra circa {max(0, f['ready_day'] - day)} giorni" if f["status"] == "giurata" else "")]
        cost = F._cost(conn, f)
        lei = f["relation"] in F.FEMALE
        acts = [act(f"Duello con {f['name']}", f"duello {first}" if here else f"faide duello {f['id']}", ok=here or f["knows"],
                    why="non sa ancora chi sei"),
                act(f"Risarcisci la famiglia ({cost} pietre)", f"faide risarcisci {f['id']}",
                    ok=_stones(conn, player.id) >= cost and f["knows"], why=f"servono {cost} pietre"),
                act("Racconta la verità", f"faide verita {f['id']}", ok=bool(f["knows"]), why="non sa chi sei")]
        if not here and f["location_id"]:
            acts.append(act("Vai da lei" if lei else "Vai da lui", f"vai #{f['location_id']}"))
        secs.append(section(f"🩸 {f['name']}", lines, acts, [bar("Rancore", f["intensity"], tone="bad")]))
    ds = F.debts(conn)
    d_lines = [f"🤝 {d['name']} — risparmiato a {d['place']}: {_ST.get(d['status'], d['status'])}" for d in ds]
    secs.append(section("Debiti di vita", d_lines or ["Nessuno ti deve la vita. Risparmiare chi hai battuto crea alleati."],
                        [act(f"Vai da {d['name']}", f"vai #{d['location_id']}") for d in ds
                         if d["location_id"] and d["location_id"] != player.location_id][:4], icon="🤝"))
    old = [r for r in F._rows(conn, "faida", active=False) if r["status"] in ("chiusa", "riconciliata", "vendicata")]
    old += [r for r in F._rows(conn, "debito", active=False) if r["status"] == "saldato"]
    if old:
        secs.append(section("Conti chiusi", [f"{r['name']} ({r['victim_name']}): {_ST.get(r['status'], r['status'])}"
                                              + (f" — {r['note']}" if r["note"] else "") for r in old[-8:]], icon="📜"))
    return menu("faide", "🩸 IL LIBRO DEI RANCORI E DEI DEBITI",
                [f"Faide aperte: {len(fs)} · debiti di vita: {len(ds)}"], secs)
