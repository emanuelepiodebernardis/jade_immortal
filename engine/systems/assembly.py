"""
GRANDE ASSEMBLEA DELL'ALLEANZA MARZIALE (武林大会).

Ogni ~45 giorni le sette convocano in una città la Grande Assemblea: otto coltivatori
tra i più forti del momento si sfidano a eliminazione diretta (quarti, semifinale, finale).
Gli incontri NON sono all'ultimo sangue: chi perde esce dal torneo, ferito nell'orgoglio.

  assemblea                 notizie sull'Assemblea (dove, quando, il tabellone)
  assemblea iscriviti       ti iscrivi (devi essere nella città che la ospita)
  assemblea <1|2|3>         combatti il tuo prossimo incontro con uno stile:
                              1 = assalto frontale (premia chi è più forte)
                              2 = difesa e contrattacco (riduce il caso)
                              3 = tecnica segreta (consuma spirito, grande potenza, rischiosa)

Il vincitore diventa CAPO DELL'ALLEANZA MARZIALE: fama enorme, pietre e un titolo.
Ogni vittoria rende, e battere chi è più forte può portare un'illuminazione.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

INTERVAL_DAYS = 45
OPEN_DAYS = 3
ROUNDS = ["Quarti di finale", "Semifinale", "Finale"]


def current(conn) -> dict | None:
    a = state.get_json(conn, "assembly")
    if not a:
        return None
    if tick_mod.get_tick(conn) // 120 > a["end_day"]:
        return None
    return a


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    day = t // 120
    a = state.get_json(conn, "assembly")
    out = []
    if a and day > a["end_day"]:
        state.delete(conn, "assembly")
        if a.get("joined") and not a.get("done"):
            out.append("La Grande Assemblea si è chiusa senza di te: il tuo posto nel tabellone è perduto.")
        a = None
    last = state.get_int(conn, "assembly_day", 10)        # la prima dopo qualche settimana
    if a is None and day - last >= INTERVAL_DAYS:
        city = conn.execute("SELECT id, name FROM locations WHERE location_type='city' "
                            "ORDER BY RANDOM() LIMIT 1;").fetchone()
        if not city:
            return out
        state.set_json(conn, "assembly", {"loc": city["id"], "city": city["name"],
                                          "start_day": day, "end_day": day + OPEN_DAYS,
                                          "joined": False, "round": 0, "done": False, "bracket": []})
        state.set(conn, "assembly_day", str(day))
        out.append(f"⚔ Le sette convocano la GRANDE ASSEMBLEA DELL'ALLEANZA MARZIALE a {city['name']}! "
                   f"Iscrizioni aperte per {OPEN_DAYS} giorni ('assemblea').")
    return out


def _pick_field(conn, player, rng) -> list[int]:
    from engine.systems import power
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    me = power.combat_rating(conn, "player", player.id)
    rows = conn.execute("SELECT id FROM npcs WHERE status='alive' AND COALESCE(kind,'human')='human' "
                        "AND location_id IS NOT NULL;").fetchall()
    cands = []
    for r in rows:
        tier = cultivation.realm_tier(conn, "npc", r["id"]) or 1
        if tier > ptier + 1:
            continue
        cands.append((power.combat_rating(conn, "npc", r["id"]), r["id"]))
    cands.sort(key=lambda x: abs(x[0] - me * 1.1))      # avversari intorno al tuo livello, un po' sopra
    field = [c[1] for c in cands[:7]]
    from engine.systems import npc_factory
    while len(field) < 7:                               # mondo troppo piccolo: arrivano campioni da lontano
        nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=None,
                                tier=ptier, stage=rng.randint(3, 9), tick=tick_mod.get_tick(conn))
        field.append(nid)
    rng.shuffle(field)
    return field


def register(conn, player) -> str:
    a = current(conn)
    if not a:
        return "Nessuna Grande Assemblea in corso. ('assemblea' per sapere quando)"
    if a["joined"]:
        return "Sei già iscritto. 'assemblea' per il tabellone."
    if player.location_id != a["loc"]:
        return f"L'Assemblea si tiene a {a['city']}: devi essere lì per iscriverti."
    rng = random.Random(tick_mod.get_tick(conn) * 3 + player.id)
    field = _pick_field(conn, player, rng)
    a.update({"joined": True, "bracket": field, "round": 0})
    state.set_json(conn, "assembly", a)
    return ("Scrivi il tuo nome sul grande registro di giada. Otto nomi, una sola vetta.\n"
            + describe(conn, player))


def _opponent(a: dict) -> int | None:
    # il giocatore è sempre "slot 0" del suo ramo: affronta bracket[round]
    if a["round"] >= len(ROUNDS):
        return None
    return a["bracket"][a["round"]]


def describe(conn, player) -> str:
    a = current(conn)
    if not a:
        last = state.get_int(conn, "assembly_day", 10)
        nxt = max(1, INTERVAL_DAYS - (tick_mod.get_tick(conn) // 120 - last))
        champ = state.get(conn, "assembly_champion")
        return (f"Nessuna Grande Assemblea in corso: la prossima tra circa {nxt} giorn{'o' if nxt == 1 else 'i'}."
                + (f" Ultimo Capo dell'Alleanza: {champ}." if champ else ""))
    left = max(0, a["end_day"] - tick_mod.get_tick(conn) // 120)
    lines = [f"⚔ GRANDE ASSEMBLEA DELL'ALLEANZA MARZIALE — a {a['city']} (chiude tra {left} giorn{'o' if left == 1 else 'i'})"]
    if not a["joined"]:
        lines.append("Non sei iscritto: vai in città e 'assemblea iscriviti'.")
        return "\n".join(lines)
    if a["done"]:
        lines.append(a.get("result", "Il tuo torneo è concluso."))
        return "\n".join(lines)
    opp = _opponent(a)
    from engine.systems import perception
    from engine.simulation import cultivation
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (opp,)).fetchone()["name"]
    lines.append(f"{ROUNDS[a['round']]}: affronti {name} ({cultivation.realm_label(conn, 'npc', opp)}) — "
                 f"{perception.relative_strength(conn, player.id, opp)}.")
    lines.append("Scegli lo stile: 'assemblea 1' assalto · 'assemblea 2' difesa e contrattacco · "
                 "'assemblea 3' tecnica segreta (consuma spirito)")
    return "\n".join(lines)


def fight(conn, player, style: int) -> str:
    from engine.systems import perception, reputation, sects, seclusion
    from engine.systems import spirit as spmod
    from engine.simulation import world_tick
    a = current(conn)
    if not a or not a["joined"] or a["done"]:
        return describe(conn, player)
    if player.location_id != a["loc"]:
        return f"Gli incontri si tengono a {a['city']}."
    opp = _opponent(a)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (opp,)).fetchone()["name"]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 13 + a["round"] * 101 + player.id)
    ratio = perception.strength_ratio(conn, player.id, opp)
    from engine.simulation import cultivation as _cult
    _crowd = ["Diecimila spettatori trattengono il fiato.", "Sugli spalti le sette scommettono a voce alta.",
              "I tamburi di guerra battono il tempo dello scontro.", "Il vento solleva i vessilli di cento sette."]
    lines = [f"⚔ {ROUNDS[a['round']]} contro {name} — {_cult.realm_label(conn, 'npc', opp)} "
             f"({perception.relative_strength(conn, player.id, opp)}).", rng.choice(_crowd)]
    if style == 1:
        score = ratio * rng.uniform(0.75, 1.25) * (1.08 if ratio >= 1 else 0.95)
        lines.append("Ti lanci all'attacco senza risparmiarti.")
    elif style == 2:
        score = ratio * rng.uniform(0.9, 1.1)
        lines.append("Paziente, aspetti l'errore e colpisci di rimessa.")
    else:
        cost_ok = spmod.spend(conn, 10, player.id)
        score = ratio * rng.uniform(0.6, 1.6) * (1.15 if cost_ok else 0.9)
        lines.append("Bruci lo spirito in una tecnica segreta: tutto o niente!")
    won = score >= 1.0
    world_tick.advance(conn, 24)
    if not won:
        a["done"] = True
        a["result"] = f"Sei uscito ai {ROUNDS[a['round']].lower()} per mano di {name}."
        state.set_json(conn, "assembly", a)
        reputation.adjust(conn, player.id, fame=1 + a["round"] * 2)
        lines.append(f"{name} ti supera. Esci dal torneo — ma il tuo nome è stato visto ({a['result']})")
        return "\n".join(lines)
    reward = (100 + 100 * a["round"]) * max(1, _ptier(conn, player.id))
    sects.grant_resource(conn, "pietre_spirituali", reward, player.id)
    reputation.adjust(conn, player.id, fame=4 + 4 * a["round"])
    lines.append(rng.choice([f"Il tuo ultimo colpo fa arretrare {name} fuori dall'arena.",
                             f"{name} alza la mano: si arrende, con un inchino che vale più di una vittoria.",
                             f"Un fendente di luce: l'arma di {name} vola via e si pianta tra la folla."]))
    lines.append(f"Vinci! {name} cede il campo. (+{reward} pietre)")
    from engine.systems import rewards
    pr = rewards.grant(conn, rng, player, rank=3 - min(2, a["round"]), scale=1.0 + 0.5 * a["round"], stones=False)
    lines.append("I giudici ti consegnano: " + ", ".join(pr) + ".")
    if ratio < 0.87:
        lines += seclusion.on_upset_win(conn, t, rng, player, name, ratio)
    a["round"] += 1
    if a["round"] >= len(ROUNDS):
        a["done"] = True
        a["result"] = "Hai vinto la Grande Assemblea: sei il CAPO DELL'ALLEANZA MARZIALE!"
        state.set(conn, "assembly_champion", player.name)
        wins = state.get_int(conn, "assembly_wins", 0) + 1
        state.set(conn, "assembly_wins", str(wins))
        reputation.adjust(conn, player.id, fame=30)
        lines.append("✦ Diecimila voci gridano il tuo nome: sei il CAPO DELL'ALLEANZA MARZIALE! ✦")
        lines.append("Il Sigillo dell'Alleanza ti viene posto tra le mani: " + ", ".join(
            rewards.grant(conn, rng, player, rank=1, scale=2.0, kinds=["tesoro", "manuale"])) + ".")
        for tt in ("Capo dell'Alleanza Marziale",) + (("Sovrano delle Assemblee",) if wins >= 3 else ()):
            if state.grant_title(conn, tt):
                lines.append(f"✧ Nuovo titolo: «{tt}» ✧")
    else:
        nxt = conn.execute("SELECT name FROM npcs WHERE id=?;", (_opponent(a),)).fetchone()["name"]
        lines.append(f"Prossimo turno ({ROUNDS[a['round']]}): {nxt}. 'assemblea 1/2/3' quando sei pronto.")
    state.set_json(conn, "assembly", a)
    return "\n".join(lines)


def _ptier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def command(conn, player, arg: str) -> str:
    a = arg.strip().lower()
    if a in ("iscriviti", "join", "register", "iscrizione"):
        return register(conn, player)
    if a in ("1", "2", "3"):
        return fight(conn, player, int(a))
    return describe(conn, player)
