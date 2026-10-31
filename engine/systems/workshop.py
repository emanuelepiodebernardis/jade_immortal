"""
LA BOTTEGA (Aggiornamento 79) — i mestieri senza divorare nessuno.

Ogni persona del mondo conosce un'arte (vedi npc_crafts). Oltre a divorarla, puoi IMPARARLA:

  bottega <nome>            vai a bottega da un maestro: una giornata di lavoro al suo fianco ti dà esperienza nella
                            sua arte, fino al suo livello (mai oltre). Se non la conosci, ti insegna le basi. Si paga
                            con pietre, o gratis se siete amici. Una volta al giorno per maestro.
  commissiona <nome> [n]    gli fai creare una cosa della sua arte, al suo livello: senza le ricette 'n' elenca cosa sa
                            fare. Paghi pietre, non materiali.
  laboratorio [apri|riscuoti]  apri un laboratorio tuo in città: rende pietre ogni giorno, secondo il tuo livello
                            migliore e i discepoli della tua setta che ci lavorano.

È la via «pulita»: più lenta dell'Abisso, ma non costa corruzione né karma.
"""

from __future__ import annotations

import random

from engine.systems import state

LAB_COST = 1500
LAB_KEY = "laboratorio"


def _master(conn, player, arg: str):
    from engine.core import entities
    from engine.systems import npc_crafts
    if not (arg or "").strip():
        return None, None, "Da chi? Scrivi 'bottega <nome>' (con 'examine <nome>' vedi il mestiere di qualcuno)."
    npc = entities.find_npc_in_location(conn, player.location_id, arg.split()[0])
    if npc is None:
        return None, None, f"Non vedi nessuno di nome '{arg.split()[0]}' qui."
    cr = npc_crafts.of_npc(conn, npc.id)
    if not cr:
        return npc, None, f"{npc.name} non conosce nessuna arte da insegnarti."
    return npc, cr, ""


def _friendly(conn, npc_id: int) -> bool:
    from engine.systems import relations
    return relations.get_disposition(conn, npc_id).score >= 30


def apprentice(conn, player, arg: str) -> str:
    from engine.core import tick
    from engine.systems import professions, relations, sects
    from engine.simulation import world_tick
    npc, cr, err = _master(conn, player, arg)
    if err:
        return err
    key, lv = cr[0]
    name = professions.PROFESSIONS[key]
    t = tick.get_tick(conn)
    day = t // 120
    done = state.get_json(conn, "bottega_giorni", {}) or {}
    if done.get(str(npc.id)) == day:
        return f"Oggi hai già lavorato con {npc.name}. Torna domani."
    fee = 0 if _friendly(conn, npc.id) else 25 * lv
    if fee and sects.get_resource(conn, "pietre_spirituali", player.id) < fee:
        return f"{npc.name} chiede {fee} pietre per una giornata alla sua bottega (gratis per gli amici)."
    have = professions.xp(conn, player.id, key) if professions.has(conn, key, player.id) else 0
    ceiling = professions.xp_for_level(lv)
    if professions.has(conn, key, player.id) and have >= ceiling:
        return f"{npc.name} è {name.lower()} di livello {lv}: ne sai già quanto lui. Cercati un maestro più grande."
    if fee:
        sects.grant_resource(conn, "pietre_spirituali", -fee, player.id)
    done[str(npc.id)] = day
    state.set_json(conn, "bottega_giorni", done)
    world_tick.advance(conn, tick.cost_of("cultivate"))
    conn.execute("UPDATE npcs SET location_id=? WHERE id=? AND status='alive';",      # il maestro resta a bottega
                 (player.location_id, npc.id))
    relations.adjust(conn, npc.id, 2, t)
    first = npc.name.split()[0]
    if not professions.has(conn, key, player.id):
        lv_now = professions.add_xp(conn, player.id, 3, key)
        return (f"⚒ {first} ti mostra le basi dell'arte {name}: come si tiene il fuoco, come si legge un materiale. "
                f"Ora la conosci (liv. {lv_now}). Praticala con 'arti {key}'." + (f" (−{fee} pietre)" if fee else ""))
    gain = max(2, min(ceiling - have, int(ceiling * 0.08) + 2))
    before = professions.level(conn, player.id, key)
    after = professions.add_xp(conn, player.id, gain, key)
    up = f" Sali al livello {after}!" if after > before else ""
    return (f"⚒ Una giornata alla bottega di {first} ({name}, liv. {lv}): lo guardi, sbagli, lui ti corregge. "
            f"Esperienza +{gain}.{up}" + (f" (−{fee} pietre)" if fee else " (gratis: siete amici)"))


def _price(need: int, lv: int) -> int:
    return 60 * need + 10 * lv


def commission(conn, player, arg: str) -> str:
    from engine.systems import professions, sects, items, relations
    from engine.core import tick
    words = (arg or "").split()
    npc, cr, err = _master(conn, player, words[0] if words else "")
    if err:
        return err
    key, lv = cr[0]
    rs = [r for r in professions.RECIPES if r[0] == key and r[1] <= lv]
    first = npc.name.split()[0]
    if not rs:
        return f"{first} non sa ancora fare nulla che valga la pena comprare."
    pick = words[1] if len(words) > 1 else ""
    if not pick.isdigit() or not (1 <= int(pick) <= len(rs)):
        lines = [f"⚒ {npc.name} — {professions.PROFESSIONS[key]}, liv. {lv}. Può farti:"]
        for i, r in enumerate(rs, 1):
            lines.append(f"  {i}. {r[2]} — {_price(r[1], lv)} pietre")
        lines.append(f"Scrivi 'commissiona {first} <n>'.")
        return "\n".join(lines)
    _p, need, name, _cost, make = rs[int(pick) - 1]
    price = _price(need, lv)
    if _friendly(conn, npc.id):
        price = int(price * 0.8)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < price:
        return f"«{name}» costa {price} pietre: non ti bastano."
    res = make(conn, player.id, lv)
    if "item" not in res:
        return f"{first} non forgia armi su commissione: per quelle serve la tua mano ('craft forgia')."
    sects.grant_resource(conn, "pietre_spirituali", -price, player.id)
    it = res["item"]
    iid = items.create_item(conn, it["name"], it["item_type"], it["rarity"], it["desc"], it["effects"])
    items.grant(conn, "player", player.id, iid)
    relations.adjust(conn, npc.id, 1, tick.get_tick(conn))
    return f"⚒ {first} lavora per te: «{it['name']}» è nello zaino. (−{price} pietre)"


# ---------------------------------------------------------------- il laboratorio

def lab(conn) -> dict | None:
    return state.get_json(conn, LAB_KEY, None)


def _income(conn, pid: int) -> int:
    from engine.systems import professions, own_sect
    best = professions.best_level(conn, pid)
    if not best:
        return 0
    try:
        hands = len(own_sect.disciples(conn, pid))
    except Exception:                                     # noqa: BLE001
        hands = 0
    return int(15 * best * (1 + 0.25 * min(8, hands)))


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    d = lab(conn)
    if not d or player is None:
        return []
    d["cassa"] = int(d.get("cassa", 0)) + _income(conn, player.id)
    state.set_json(conn, LAB_KEY, d)
    return []


def lab_command(conn, player, arg: str) -> str:
    from engine.core import entities
    from engine.systems import sects
    a = (arg or "").strip().lower()
    d = lab(conn)
    if a in ("apri", "fonda", "compra"):
        if d:
            return f"Hai già un laboratorio a {d['dove']}."
        loc = entities.get_location(conn, player.location_id)
        if not loc or loc.location_type != "city":
            return "Un laboratorio si apre in città, dove ci sono clienti."
        if sects.get_resource(conn, "pietre_spirituali", player.id) < LAB_COST:
            return f"Aprire un laboratorio costa {LAB_COST} pietre (bottega, attrezzi, licenza)."
        sects.grant_resource(conn, "pietre_spirituali", -LAB_COST, player.id)
        state.set_json(conn, LAB_KEY, {"dove": loc.name, "cassa": 0})
        return (f"⚒ Apri il tuo laboratorio a {loc.name}. Renderà ogni giorno secondo la tua arte migliore e i "
                f"discepoli della tua setta che ci lavorano. ('laboratorio riscuoti' per incassare)")
    if not d:
        return (f"Non hai un laboratorio. In città: 'laboratorio apri' ({LAB_COST} pietre). Rende ogni giorno "
                "secondo la tua arte migliore e i tuoi discepoli.")
    if a in ("riscuoti", "incassa", "ritira"):
        n = int(d.get("cassa", 0))
        if not n:
            return "La cassa del laboratorio è vuota."
        sects.grant_resource(conn, "pietre_spirituali", n, player.id)
        d["cassa"] = 0
        state.set_json(conn, LAB_KEY, d)
        return f"⚒ Incassi {n} pietre dal laboratorio di {d['dove']}."
    return (f"⚒ Il tuo laboratorio a {d['dove']}: in cassa {d.get('cassa', 0)} pietre, rende circa "
            f"{_income(conn, player.id)} al giorno. ('laboratorio riscuoti')")
