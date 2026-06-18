"""
INVASIONI GUIDATE (end-game).

Raggiunta una CATEGORIA ALTA di discepolo (Erede della Setta o Giovane Patriarca) non
ti limiti più a razziare da solo: GUIDI la tua setta all'assalto della sede di una setta
rivale. Porti con te dei compagni d'arme (alleati della tua setta), affronti i difensori a
ondate — incluso il loro campione/patriarca — e, se vinci, CONQUISTI la loro sede:
  • la loro influenza crolla (se va a zero, la setta è soggiogata);
  • la sede passa sotto il controllo della TUA setta (owner_faction_id);
  • razzii pietre, manuali e tesori;
  • la tua setta si ESPANDE — e con l'espansione arrivano più nemici (vedi world_events).

Distinta dalla razzia in solitaria (`raid`): l'invasione richiede rango alto, porta alleati,
si combatte a ondate e CONQUISTA territorio.
"""

from __future__ import annotations

import random
import sqlite3

from engine.systems import sects
from engine.simulation import combat

# rango minimo per guidare un'invasione (indice nella RANK_LADDER)
MIN_RANK_INDEX = 6      # "Erede della Setta" o "Giovane Patriarca"

CONQUEST_KEY = "player_sect_conquests"


def rank_index(rank: str | None) -> int:
    try:
        return sects.RANK_LADDER.index(rank) if rank else 0
    except ValueError:
        return 0


def can_lead(conn: sqlite3.Connection, player_id: int = 1) -> tuple[bool, str]:
    m = sects.get_membership(conn, player_id)
    if not m:
        return False, "Non appartieni a nessuna setta: non puoi guidare un'invasione."
    if rank_index(m["rank"]) < MIN_RANK_INDEX:
        need = sects.RANK_LADDER[MIN_RANK_INDEX]
        return False, (f"Solo i discepoli di alto rango guidano un'invasione. "
                       f"Devi raggiungere almeno «{need}» (vinci i tornei per salire). "
                       f"Rango attuale: «{m['rank']}».")
    return True, ""


def conquests(conn: sqlite3.Connection) -> int:
    r = conn.execute("SELECT value FROM game_state WHERE key=?;", (CONQUEST_KEY,)).fetchone()
    return int(r["value"]) if r else 0


def _bump_conquests(conn: sqlite3.Connection) -> int:
    n = conquests(conn) + 1
    conn.execute("INSERT INTO game_state (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (CONQUEST_KEY, str(n)))
    return n


def _power(conn, ctype, cid) -> float:
    cp = combat.combat_power(conn, ctype, cid)
    return cp["attack"] + cp["defense"] * 0.6 + cp["vitality"] * 0.4


def lead_invasion(conn: sqlite3.Connection, tick: int, rng: random.Random, player) -> dict:
    """Guida la tua setta contro la setta rivale che ha sede dove ti trovi."""
    ok, why = can_lead(conn, player.id)
    if not ok:
        return {"status": "blocked", "lines": [why]}
    target = sects.sect_at_location(conn, player.location_id)
    if not target:
        return {"status": "no_target",
                "lines": ["Qui non ha sede nessuna setta da invadere. Usa 'raidtarget' "
                          "per raggiungere la sede di una setta rivale, poi 'invade'."]}
    m = sects.get_membership(conn, player.id)
    if target["id"] == m["faction_id"]:
        return {"status": "own", "lines": ["Questa è la TUA setta: non puoi invaderla."]}

    my_fac = m["faction_id"]
    my_name = m["sect_name"]
    loc = player.location_id

    # alleati: alcuni membri della tua setta accorrono con te (più rango = più seguito)
    n_allies = 2 + rank_index(m["rank"]) // 2
    allies = conn.execute(
        "SELECT id, name FROM npcs WHERE faction_id=? AND status='alive' AND kind='human' "
        "AND id<>? ORDER BY RANDOM() LIMIT ?;", (my_fac, player.id, n_allies)).fetchall()
    # difensori della setta rivale presenti alla sede
    defenders = conn.execute(
        "SELECT id, name, archetype FROM npcs WHERE faction_id=? AND status='alive' "
        "AND kind='human' AND location_id=? ORDER BY id;", (target["id"], loc)).fetchall()

    lines = ["═" * 44, f"⚔  INVASIONE — {my_name} assalta {target['name']}!", "═" * 44]
    if allies:
        lines.append("Combattono al tuo fianco: " + ", ".join(a["name"] for a in allies) + ".")
    if not defenders:
        lines.append(f"La sede di {target['name']} è sguarnita: la prendi senza opporre resistenza.")

    # il GIOCATORE affronta i difensori più forti; gli alleati si occupano del resto
    from engine.cli import loop as _loop          # riuso del motore di combattimento
    ally_power = sum(_power(conn, "npc", a["id"]) for a in allies)
    routed = 0
    for d in defenders:
        dp = _power(conn, "npc", d["id"])
        # i pezzi grossi (patriarca/anziano) li affronti TU; gli altri li travolgono gli alleati
        if d["archetype"] in ("patriarca", "anziano") or ally_power < dp:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (loc, d["id"]))
            npc = _entity_npc(conn, d["id"])
            if npc is None:
                continue
            res = _loop._attack_auto(conn, _entity_player(conn, player.id), npc, None)
            last = [ln for ln in res.split("\n") if ln.strip()]
            lines.append(f"  • Tu contro {d['name']}: {last[-1].strip() if last else '...'}")
            if _is_dead(conn, d["id"]):
                routed += 1
        else:
            ally_power -= dp * 0.7
            conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (tick, d["id"]))
            routed += 1
            lines.append(f"  • I tuoi compagni travolgono {d['name']}.")

    still = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE faction_id=? AND status='alive' AND kind='human' "
        "AND location_id=?;", (target["id"], loc)).fetchone()["c"]
    if still > 0:
        lines.append(f"L'assalto è respinto: {still} difensori tengono ancora la sede. Ritirati e riprova.")
        return {"status": "repelled", "lines": lines}

    # VITTORIA → conquista
    return _conquer(conn, tick, rng, player, target, my_fac, my_name, loc, lines)


def _conquer(conn, tick, rng, player, target, my_fac, my_name, loc, lines) -> dict:
    from engine.systems import items, reputation
    # 1) influenza rivale schiantata; se va a zero, la setta è soggiogata
    conn.execute("UPDATE factions SET influence=MAX(0, influence-40), wealth=MAX(0, wealth-30) "
                 "WHERE id=?;", (target["id"],))
    subdued = conn.execute("SELECT influence FROM factions WHERE id=?;",
                           (target["id"],)).fetchone()["influence"] <= 0
    # 2) la sede passa sotto il controllo della TUA setta; la tua influenza cresce
    conn.execute("UPDATE locations SET owner_faction_id=? WHERE id=?;", (my_fac, loc))
    conn.execute("UPDATE factions SET influence=influence+30, wealth=wealth+25 WHERE id=?;", (my_fac,))
    if subdued:
        conn.execute("UPDATE factions SET status='subdued' WHERE id=?;", (target["id"],))
    # 3) bottino: pietre, manuale segreto, tesoro
    stones = rng.randint(150, 350) + (target["tier"] or 1) * 60 if "tier" in target.keys() else rng.randint(150, 350)
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    from engine.systems import guild
    manual = None
    techs = guild.sect_techniques(conn, target["id"])
    if techs:
        t0 = techs[0]
        manual = t0["name"]
        miid = items.create_item(
            conn, f"Manuale: {t0['name']}", "manuale", "prezioso",
            f"Tecnica segreta trafugata a {target['name']}.",
            {"learn_technique": {"name": t0["name"], "magnitude": t0.get("magnitude", 0.1),
                                 "tech_key": f"conquest:{target['id']}"}})
        items.grant(conn, "player", player.id, miid, 1)
    iid = items.create_item(conn, f"Tesoro di {target['name']}", "tesoro", "prezioso",
                            "Bottino di guerra della setta conquistata.",
                            {"stones": stones // 2, "grow_strength": 20, "grow_vitality": 20})
    items.grant(conn, "player", player.id, iid, 1)
    reputation.adjust(conn, player.id, fame=60)
    n = _bump_conquests(conn)

    lines.append(f"★ CONQUISTA! {my_name} prende la sede di {target['name']}.")
    if subdued:
        lines.append(f"  {target['name']} è SOGGIOGATA: la sua influenza è annientata.")
    lines.append(f"  Bottino: +{stones} pietre, un Tesoro di guerra"
                 + (f", e il manuale «{manual}»" if manual else "") + ".")
    lines.append(f"  La tua setta si ESPANDE (conquiste totali: {n}). +60 fama.")
    lines.append("  ⚠ Ma più ti espandi, più nemici vorranno colpirti: aspettati ritorsioni.")
    lines.append("═" * 44)
    return {"status": "conquered", "subdued": subdued, "stones": stones,
            "manual": manual, "conquests": n, "lines": lines}


# --- piccoli helper per evitare import circolari pesanti ---

def _entity_npc(conn, nid):
    from engine.core import entities
    return entities.get_npc(conn, nid)


def _entity_player(conn, pid):
    from engine.core import entities
    return entities.get_player(conn, pid)


def _is_dead(conn, nid) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()
    return (not r) or r["status"] != "alive"
