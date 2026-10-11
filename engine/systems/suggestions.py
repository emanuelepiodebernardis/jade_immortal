"""
AZIONI SUGGERITE — dopo ogni comando, 2–4 opzioni numerate e sensate per la situazione.

Ispirate alle "tre carte scelta" delle storie interattive: con ~70 comandi il problema
non è la mancanza di cose da fare, ma sapere cosa fare ADESSO. Le genera il motore
leggendo lo stato (niente LLM), quindi funzionano sempre e non mentono mai.
Scrivi il numero per eseguire l'azione; i comandi restano tutti disponibili.
"""

from __future__ import annotations

import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "suggestions"
MAX = 4


_SKIP: set[str] = set()


def _add(out: list, label: str, cmd: str) -> None:
    if cmd in _SKIP:
        return
    if len(out) < MAX and all(c != cmd for _l, c in out):
        out.append((label, cmd))


def compute(conn: sqlite3.Connection, player: entities.Player) -> list[tuple[str, str]]:
    from engine.systems import (absorption, loot, world_events, sects, training, market,
                                bonds, bounties, weapons, items, dao_powers, perception)
    from engine.simulation import cultivation
    out: list[tuple[str, str]] = []
    if player.status != "alive":
        return out
    loc = player.location_id
    t = tick_mod.get_tick(conn)
    _SKIP.clear()
    last = state.get_json(conn, "sugg_last", {}) or {}
    if last.get("tick") == t and last.get("cmd"):
        _SKIP.add(last["cmd"])            # appena fatta e senza effetti sul tempo

    # 0) prigionia e calamità: vengono prima di tutto
    from engine.systems import captivity, eras, contests
    if captivity.active(conn):
        _add(out, "Pianifica la fuga", "evadi")
        return out
    era = eras.get(conn)
    if era["key"] == "calamita" and era["waves"] > 0:
        _add(out, f"Respingi un'ondata di {era['calamity']}", "calamita")
    gc = contests.current(conn)
    if gc and gc["loc"] == loc and not gc["done"]:
        _add(out, "Affronta la prossima prova della gara" if gc["joined"] else "Iscriviti alla gara d'arte",
             "gara prova" if gc["joined"] else "gara iscriviti")

    # 1) minacce immediate
    for nm in bonds.nemeses(conn, player.id):
        if nm["location_id"] == loc:
            _add(out, f"Affronta la tua nemesi {nm['name']}", f"attack {nm['name']}")
    hunters_here = conn.execute(
        "SELECT name FROM npcs WHERE location_id=? AND hunting=1 AND status='alive' LIMIT 1;",
        (loc,)).fetchone()
    if hunters_here:
        _add(out, f"Affronta il cacciatore {hunters_here['name']}", f"attack {hunters_here['name']}")
        _add(out, "Indossa la maschera per seminarlo", "mask on")
    wev = world_events.active_event(conn)
    if wev and wev["location_id"] == loc:
        _add(out, "Respingi l'invasione che minaccia questo luogo", "defend")

    # 1b) occasioni a tempo: reame segreto, Assemblea, setta assaltata, Sistema
    from engine.systems import secret_realms, assembly, own_sect, system_quest, cave_abode
    rr = secret_realms.current(conn)
    if rr:
        if secret_realms.run(conn):
            _add(out, "Scendi al piano successivo del reame segreto", "delve")
        elif rr["loc"] == loc:
            _add(out, f"Entra nel reame segreto «{rr['name']}»", "enter")
    asm = assembly.current(conn)
    if asm and asm["loc"] == loc:
        if not asm["joined"]:
            _add(out, "Iscriviti alla Grande Assemblea", "assemblea iscriviti")
        elif not asm["done"]:
            _add(out, "Combatti il tuo incontro all'Assemblea (assalto)", "assemblea 1")
    osct = own_sect.get(conn)
    if osct and osct.get("threat") and osct["loc"] == loc:
        _add(out, "Difendi la tua setta dall'assalto", "setta difendi")
    if system_quest.active(conn):
        d = system_quest.today(conn, player.id)
        if any(not q["done"] and system_quest._progress(conn, player.id, q) >= q["need"]
               for q in d["quests"]):
            _add(out, "[Ding!] Riscuoti le missioni del Sistema", "sistema riscuoti")
    ab = cave_abode.get(conn, player.id)
    if ab and ab["loc"] == loc and any(v > 0 for v in (ab.get("stock") or {}).values()):
        _add(out, "Raccogli la produzione della tua dimora", "dimora raccogli")

    if conn.execute("SELECT 1 FROM inventories v JOIN items i ON i.id=v.item_id WHERE v.owner_type='player' "
                    "AND v.owner_id=? AND v.quantity>0 AND i.item_type='essenza' LIMIT 1;",
                    (player.id,)).fetchone():
        _add(out, "Assorbi l'essenza di sangue che hai raccolto", "use essenza")

    from engine.systems import celestial_elements, family, lost_legacy
    cev = celestial_elements.current_event(conn)
    if cev and cev["loc"] == loc and not cev.get("taken") and cev.get("guard") is not None:
        _add(out, f"Assorbi il {cev['name']}", "elementi assorbi")
    fam = family.get(conn)
    if fam and fam.get("threat") and fam["home"] == loc:
        _add(out, "Difendi la tua famiglia", "famiglia difendi")
    lg = lost_legacy.get(conn)
    if lg and lg.get("holder"):
        hr = conn.execute("SELECT name, location_id FROM npcs WHERE id=? AND status='alive';", (lg["holder"],)).fetchone()
        if hr and hr["location_id"] == loc:
            _add(out, f"Riprenditi il frammento da {hr['name']}", f"attack {hr['name']}")
    from engine.systems import npc_quests
    if len(npc_quests.active(conn)) < npc_quests.MAX_ACTIVE and npc_quests._offers_here(conn, player):
        _add(out, "Ascolta chi, qui, ha un incarico per te", "richieste")

    # 2) ciò che è a terra
    if loot.drops_in_location(conn, loc):
        _add(out, "Raccogli il bottino", "loot")
    from engine.systems import rebirth
    if any(not r["tomb_claimed"] and r["life_no"] < rebirth.life_no(conn)
           for r in rebirth.tombs_here(conn, loc)):
        _add(out, "Apri la tomba della tua vita passata", "loot")
    if entities.dead_npcs_in_location(conn, loc) and absorption.can_absorb(conn, player.id):
        from engine.systems import reputation
        if reputation.witnesses(conn, loc) and not reputation.is_disguised(conn, player.id):
            _add(out, "Indossa la maschera: qui ci sono testimoni per ciò che vuoi fare", "mask on")
        else:
            _add(out, "Divora i resti dei caduti (Abisso)", "absorb all")

    # 3) svolte della coltivazione
    rec = cultivation.get_record(conn, "player", player.id)
    if rec and (rec["stage"] or 1) >= 10 and rec["progress"] >= 1.0:
        _add(out, "Tenta il breakthrough al regno successivo (rischioso!)", "breakthrough")
    if dao_powers.tribulation_due(conn, player.id) > 0:
        _add(out, "Affronta la tribolazione celeste", "tribulation")

    # 4) bersagli interessanti qui (con la tua stima di forza)
    protected = bonds.protected_ids(conn, player.id)
    # (si suggerisce di combattere solo ciò che puoi ragionevolmente reggere)
    for r in conn.execute(
            "SELECT o.npc_id, n.name, o.reward FROM outlaws o JOIN npcs n ON n.id=o.npc_id "
            "WHERE o.resolved=0 AND n.status='alive' AND n.location_id=? LIMIT 1;", (loc,)):
        if r["npc_id"] not in protected:
            rel = perception.relative_strength(conn, player.id, r["npc_id"])
            if "più forte" not in rel:
                _add(out, f"Riscuoti la taglia su {r['name']} ({r['reward']} pietre; è {rel})",
                     f"attack {r['name']}")
    creatures = conn.execute(
        "SELECT id, name FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human' "
        "AND kind IS NOT NULL ORDER BY id;", (loc,)).fetchall()
    if creatures:
        rels = [perception.relative_strength(conn, player.id, cr["id"]) for cr in creatures]
        if not any("più forte" in r for r in rels):
            _add(out, f"Caccia le creature qui ({len(creatures)}; alla tua portata)",
                 "attack creatures")

    # 5) setta e città
    m = sects.get_membership(conn, player.id)
    hq = sects.sect_at_location(conn, loc)
    if not m and hq:
        _add(out, f"Sostieni il test d'ingresso di {hq['name']}", "join")
    if m and not weapons.get_weapon(conn, player.id):
        _add(out, "Prendi la spada come arma principale ('weapon' per le altre vie)",
             "weapon spada")
    if m:
        from engine.systems import sect_life
        nxt = sect_life.next_event(conn, t, player.id)
        if nxt and nxt["fire_tick"] - t <= training.DAY_TICKS:
            _add(out, "Controlla la classifica: la sfida è vicina", "class")
    # bestie rare qui: prova a domarle
    from engine.systems import beasts, professions
    for r in beasts.active_rare(conn):
        if r["location_id"] == loc and not beasts.pet(conn, player.id):
            _add(out, f"Prova a domare {r['name']} ({r['rarity']})", f"tame {r['name']}")
    prof = professions.profession(conn, player.id)
    if prof:
        lvl = professions.level(conn, player.id)
        for i, rcp in enumerate(professions.recipes_for(conn, player.id), 1):
            if lvl >= rcp[1] and all(professions.material(conn, player.id, k) >= v for k, v in rcp[3].items()):
                _add(out, f"Crea: {rcp[2]}", f"craft {i}")
                break
        here = entities.get_location(conn, loc)
        if here and here.location_type in ("mountain", "forbidden_zone", "ruin"):
            _add(out, "Raccogli materiali per la tua arte", "gather")
    if items.player_inventory(conn, player.id):
        _add(out, "Usa ciò che hai nello zaino", "use all")
    if market.is_market_here(conn, loc):
        stones = sects.get_resource(conn, "pietre_spirituali", player.id)
        market.ensure_stock(conn, player.id, loc)
        prices = [o["price"] for o in market.offers(conn, player.id, loc)]
        if prices and stones >= min(prices):
            _add(out, "Al mercato c'è qualcosa che puoi permetterti", "market")

    # 6) persone
    comp = bonds.companion(conn, player.id)
    for n in entities.npcs_in_location(conn, loc):
        if n.id in protected or (comp and n.id == comp["npc_id"]):
            continue
        kinds = bonds.bond_kinds(conn, n.id, player.id)
        if kinds or bounties.is_outlaw(conn, n.id):
            continue
        row = conn.execute("SELECT kind FROM npcs WHERE id=?;", (n.id,)).fetchone()
        if row and row["kind"] not in (None, "human"):
            continue
        from engine.systems import relations
        d = relations.get_disposition(conn, n.id, player.id)
        if (d.score >= bonds.recruit_need(conn, n.id) and comp is None
                and bonds.npc_is_recruitable(conn, n.id)):
            _add(out, f"Chiedi a {n.name} di viaggiare con te", f"recruit {n.name}")
        elif -10 < d.score < bonds.RECRUIT_MIN:
            _add(out, f"Parla con {n.name} ({n.archetype or 'sconosciuto'})", f"talk {n.name}")
        break

    # 7) ritmo della giornata
    sessions = training.sessions_today(conn, t, "player", player.id)
    from engine.systems import qi as qimod
    if sessions < 3:
        _add(out, "Allenati: Qi, Dao e arte insieme (sessioni piene oggi)", "train")
    elif qimod.get_qi(conn, player.id) < qimod.max_qi(conn, player.id) * 0.3:
        _add(out, "Riposa e recupera il Qi", "wait")
    else:
        _add(out, "Dormi fino al giorno dopo", "sleep")
    # 8) esplorazione: la zona vicina più promettente
    # la zona più stimolante ALLA TUA PORTATA (non la più letale)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    comfort = tier * 2 + 1
    exits = entities.get_exits_detailed(conn, loc)
    ok = [e for e in exits if e["danger"] <= comfort]
    pick = (max(ok, key=lambda e: e["danger"]) if ok
            else min(exits, key=lambda e: e["danger"]) if exits else None)
    if pick:
        ex = pick
        _add(out, f"Esplora verso {ex['direction']}: {ex['dest_name']} (pericolo {ex['danger']})",
             f"move {ex['direction']}")
    return out


def store(conn: sqlite3.Connection, sugg: list[tuple[str, str]]) -> None:
    state.set_json(conn, KEY, [c for _l, c in sugg])


def stored(conn: sqlite3.Connection) -> list[str]:
    return list(state.get_json(conn, KEY, []) or [])


def render(sugg: list[tuple[str, str]]) -> str:
    if not sugg:
        return ""
    return "Azioni suggerite:  " + "   ".join(f"[{i}] {lab}" for i, (lab, _c) in enumerate(sugg, 1))


def render_block(sugg: list[tuple[str, str]]) -> str:
    if not sugg:
        return ""
    return "Azioni suggerite:\n" + "\n".join(f"  [{i}] {lab}" for i, (lab, _c) in enumerate(sugg, 1))


def enabled(conn: sqlite3.Connection) -> bool:
    return state.flag(conn, "ui_suggest", True)
