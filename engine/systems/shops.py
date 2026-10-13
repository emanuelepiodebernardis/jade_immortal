"""
TUTTO A UN CLIC — mercato, casa d'aste, ricette e bacheca come menu con pulsanti.

Nella dashboard ogni oggetto in vendita, ogni lotto, ogni ricetta, ogni missione e ogni invito
è un pulsante: lo tocchi e succede. Nel terminale gli stessi menu sono numerati.

  mercato     gli oggetti in vendita qui (compra con un clic)
  asta        i lotti della casa d'aste (rilancia con un clic)
  ricette     le ricette di tutte le arti che conosci (crea con un clic)
  bacheca     missioni della setta, inviti delle sette superiori, tecniche segrete
"""

from __future__ import annotations

from engine.systems.menus import act, bar, menu, section


def _stones(conn, pid: int) -> int:
    from engine.systems import sects
    return sects.get_resource(conn, "pietre_spirituali", pid)


def _nearest_city(conn, player) -> str | None:
    from engine.systems import travel
    best = None
    for r in conn.execute("SELECT id, name FROM locations WHERE location_type='city';"):
        d = travel._distance(conn, player.location_id, r["id"])
        if d is not None and (best is None or d < best[0]):
            best = (d, r["name"])
    return best[1] if best else None


# ---------------------------------------------------------------- mercato

def market_menu(conn, player) -> dict:
    from engine.systems import market, items
    st = _stones(conn, player.id)
    if not market.is_market_here(conn, player.location_id):
        city = _nearest_city(conn, player)
        return menu("mercato", "🏪 MERCATO", [f"Pietre spirituali: {st}"], [section(
            "Qui non c'è un mercato", ["I mercati sono nelle città."],
            [act(f"Vai a {city}", f"vai {city}", main=True)] if city else [], icon="🏪")])
    market.ensure_stock(conn, player.id, player.location_id)
    rows = market.offers(conn, player.id, player.location_id)
    by_type: dict[str, list] = {}
    for i, r in enumerate(rows, 1):
        by_type.setdefault(r["item_type"], []).append((i, r))
    icons = {"pillola": "💊", "essenza": "🧪", "nucleo": "◆", "manuale": "📜", "tesoro": "🏺", "arma": "⚔"}
    secs = []
    for typ, lst in by_type.items():
        acts = [act(f"{r['name']} · {items.rarity_word(r['rarity'])} — {r['price']} pietre", f"buy {i}",
                    st >= r["price"], f"servono {r['price']} pietre (ne hai {st})", main=st >= r["price"])
                for i, r in lst]
        secs.append(section(typ.capitalize() + ("i" if typ.endswith("o") else ""), actions=acts, icon=icons.get(typ, "✧")))
    if not secs:
        secs.append(section("Esaurito", ["Il mercato è esaurito per oggi: torna domani."], icon="🏪"))
    return menu("mercato", "🏪 MERCATO", [f"Pietre spirituali: {st} · tocca un oggetto per comprarlo",
                                          "L'assortimento cresce col livello della tua setta e si rinnova ogni giorno."], secs)


# ---------------------------------------------------------------- asta

def auction_menu(conn, player) -> dict:
    from engine.systems import auction
    a = auction.current(conn)
    st = _stones(conn, player.id)
    if not a:
        return menu("asta", "⚖ CASA D'ASTE", [f"Pietre spirituali: {st}"], [section(
            "Nessuna asta in corso", ["Il Padiglione di Giada apre a turno nelle città, ogni dieci giorni circa."], icon="⚖")])
    here = player.location_id == a["loc"]
    secs = []
    if not here:
        secs.append(section(f"L'asta è a {a['city']}", ["Per offrire devi essere lì."],
                            [act(f"Vai a {a['city']}", f"vai {a['city']}", main=True)], icon="🧭"))
    for i, l in enumerate(a["lots"], 1):
        if l["sold"]:
            secs.append(section(l["name"], [f"Aggiudicato a {l['sold']}."], icon="✔"))
            continue
        step = max(10, l["value"] // 20)
        mins = l["current"] + step
        offers = sorted({mins, mins + step * 3, int(l["current"] * 1.5)})
        acts = []
        for o in offers:
            ok = here and st >= o
            why = f"sei lontano da {a['city']}" if not here else f"ne hai {st}"
            acts.append(act(f"Offri {o} pietre" + (" (rilancio minimo)" if o == mins else ""), f"asta offri {i} {o}",
                            ok, why, main=ok and o == mins))
        secs.append(section(l["name"], [f"Offerta corrente: {l['current']} pietre ({l['rival']})"], acts, icon="⚖"))
    return menu("asta", f"⚖ CASA D'ASTE — {a['city']}", [f"Pietre spirituali: {st} · tocca un'offerta per rilanciare",
                                                          "Chi perde un lotto prezioso può aspettarti fuori città…"], secs)


# ---------------------------------------------------------------- ricette

def recipes_menu(conn, player) -> dict:
    from engine.systems import professions as P
    known = P.known(conn, player.id)
    if not known:
        return menu("ricette", "⚗ RICETTE", [], [section("Nessuna arte", ["Scegli un'arte per cominciare."],
                                                           [act("Apri le arti", "arti", main=True)], icon="⚗")])
    secs = [section("Materiali", [P.materials_line(conn, player.id)], [act("Raccogli materiali", "gather")], icon="✿")]
    for prof in known:
        lv = P.level(conn, player.id, prof)
        acts = []
        for i, r in enumerate(P.recipes_for(conn, player.id, prof), 1):
            _p, need, name, cost, _make = r
            have_all = all(P.material(conn, player.id, k) >= v for k, v in cost.items())
            c = ", ".join(f"{v} {P.MATERIALS[k]}" for k, v in cost.items())
            why = f"serve livello {need}" if lv < need else f"mancano materiali ({c})"
            acts.append(act(f"{name} — {c}", f"craft {prof} {i}", lv >= need and have_all, why,
                            main=lv >= need and have_all))
        nxt = P.xp_for_level(lv + 1)
        cur = P.xp(conn, player.id, prof)
        secs.append(section(f"{P.PROFESSIONS[prof]} — livello {lv}", actions=acts,
                            bars=[bar("Esperienza", 100 * cur / max(1, nxt), f"{cur}/{nxt}")], icon="⚗"))
    return menu("ricette", "⚗ RICETTE", ["Tocca una ricetta per crearla. Le ricette grigie dicono cosa manca."], secs)


# ---------------------------------------------------------------- bacheca

def board_menu(conn, player) -> dict:
    from engine.systems import sects, sect_politics, guild, state
    secs = []
    m = sects.get_membership(conn, player.id)
    if m:
        cur = state.get_json(conn, "sect_mission")
        if cur:
            secs.append(section("Missione in corso", [cur["text"]],
                                [act("Consegna la missione", "missioni completa", main=True)], icon="✎"))
        b = sect_politics._board(conn, player)
        secs.append(section("Bacheca delle missioni", ["Cambia ogni giorno."], [
            act(f"{x['text']} — {x['merit']} merito, {x['stones']} pietre (Anziano {x['elder_name']})",
                f"missioni accetta {i}", not cur, "hai già una missione") for i, x in enumerate(b, 1)], icon="✎"))
    else:
        secs.append(section("Nessuna setta", ["Le missioni e le tecniche segrete sono per i membri di una setta."],
                            [act("Cerca una setta", "sects", main=True)], icon="⛩"))
    from engine.systems import npc_quests, bounties
    offers = npc_quests._offers_here(conn, player)
    if offers:
        secs.append(section("Chi qui ha bisogno di te", actions=[
            act(f"Ascolta {npc_quests._name(conn, nid)} e accetta l'incarico", f"incarico {i}")
            for i, nid in enumerate(offers, 1)], icon="🤝"))
    qs = npc_quests.active(conn)
    if qs:
        secs.append(section("Incarichi in corso", [f"{npc_quests._name(conn, q['giver'])}: {q['kind']} (passo {q['step']}/{q['chain']})"
                                                   for q in qs], [act("Consegna ciò che puoi", "consegna"), act("Rivedi gli incarichi", "incarichi")], icon="🤝"))
    ab = bounties.active_bounties(conn)[:6]
    if ab:
        secs.append(section("Taglie", actions=[
            act(f"{b['name']} — {b['reward']} pietre ({b['crime']}) a {b['loc_name'] or '?'}", f"vai {b['loc_name']}",
                bool(b["loc_name"]), "luogo sconosciuto") for b in ab], icon="🎯"))
    invs = sects.pending_invitations(conn, player.id)
    if invs:
        secs.append(section("Inviti delle sette superiori", ["Accettare significa lasciare la setta attuale."], [
            act(f"{r['name']} — {r['hint']}", f"accept {r['slot']}", main=True) for r in invs], icon="✉"))
    return menu("bacheca", "📋 BACHECA", ["Missioni, inviti e tecniche: tutto a un clic."], secs)
