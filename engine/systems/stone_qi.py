"""
COLTIVARE CON LE PIETRE SPIRITUALI (Aggiornamento 66) — dove finiscono le pietre di troppo.

Nel genere le pietre spirituali sono prima di tutto Qi solido: si stringono nel palmo e se ne beve
l'energia. Nelle simulazioni di 1000 giorni un personaggio ne accumulava fino a 860.000 senza nulla
in cui spenderle. Ora puoi ASSORBIRLE per coltivare, ovunque tu sia:

  · una sessione costa 25 pietre per regno, e ogni sessione dello stesso giorno costa di più
    (+50% ciascuna): le prime rendono molto, le altre sempre meno, e non c'è fondo;
  · una sessione vale circa due terzi di una coltivazione normale (con tutti i tuoi moltiplicatori);
  · niente tossine: è Qi puro, non una pillola. Ma i meridiani avvelenati ne trattengono meno;
  · al massimo 10 sessioni al giorno; ognuna richiede un'ora;
  · allo strato più alto del regno (in attesa dello sfondamento o dell'ascensione) il Qi non entra
    più: CONSOLIDA il tuo Dao migliore (comprensione +1 ogni tre regni, per sessione).

Le pietre restano tue: si assorbe solo quando lo decidi. Se vuoi, il pilota automatico può farlo da sé
('auto imposta pietre si', spento di base) con le pietre che superano una riserva (500 per regno),
fino a 4 sessioni al giorno.

  pietre                   il pannello
  pietre assorbi [n]       assorbi n sessioni (1 se non dici quante)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "stone_qi"
BASE_COST = 25          # pietre per regno, per la prima sessione del giorno
STEP = 0.5              # ogni sessione in più nello stesso giorno: +50%
MAX_PER_DAY = 10
YIELD = 0.65            # rispetto a una coltivazione normale
RESERVE_PER_TIER = 500  # il pilota non scende sotto questa riserva
AUTO_SESSIONS = 4


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _tier(conn, pid: int) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def done_today(conn) -> int:
    d = state.get_json(conn, KEY, None) or {}
    return int(d.get("n", 0)) if d.get("day") == _day(conn) else 0


def cost(conn, pid: int, k: int | None = None) -> int:
    k = done_today(conn) if k is None else k
    return int(BASE_COST * _tier(conn, pid) * (1.0 + STEP * k))


def absorb(conn, player, n: int = 1) -> str:
    from engine.systems import sects, cult_mods, dao_heart
    from engine.simulation import cultivation, world_tick
    n = max(1, min(MAX_PER_DAY, n))
    k0 = done_today(conn)
    if k0 >= MAX_PER_DAY:
        return f"Oggi hai già assorbito {MAX_PER_DAY} volte: i meridiani sono saturi. Domani di nuovo."
    rec = cultivation.get_record(conn, "player", player.id)
    if rec and (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM and rec["progress"] >= 1.0:
        return _consolidate(conn, player, n, k0)
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 13 + player.id)
    mult, _labels = cult_mods.cultivation_mult(conn, player.id, player.location_id)
    spent, sessions, stage_up = 0, 0, False
    for i in range(n):
        if k0 + i >= MAX_PER_DAY:
            break
        c = cost(conn, player.id, k0 + i)
        if sects.get_resource(conn, "pietre_spirituali", player.id) < c:
            break
        sects.grant_resource(conn, "pietre_spirituali", -c, player.id)
        spent += c
        sessions += 1
        res = cultivation.cultivate(conn, "player", player.id, t, rng, multiplier=mult * YIELD)
        stage_up = stage_up or res.get("stage_up", False)
        if res.get("ready"):
            break
    if not sessions:
        return f"Ti servono {cost(conn, player.id, k0)} pietre spirituali per una sessione."
    state.set_json(conn, KEY, {"day": _day(conn), "n": k0 + sessions})
    world_tick.advance(conn, 5 * sessions)
    rec = cultivation.get_record(conn, "player", player.id)
    tox = " I meridiani avvelenati ne trattengono meno." if dao_heart.toxin(conn) >= 10 else ""
    return (f"💎 Stringi le pietre nei palmi e ne bevi il Qi: {sessions} {'sessione' if sessions == 1 else 'sessioni'}, "
            f"−{spent} pietre. Strato {rec['stage']}, {int(rec['progress'] * 100)}%."
            + (" Sali di strato!" if stage_up else "") + tox
            + (f" (la prossima oggi costa {cost(conn, player.id)})" if k0 + sessions < MAX_PER_DAY else ""))


def _consolidate(conn, player, n: int, k0: int) -> str:
    """Allo strato più alto (in attesa dello sfondamento o dell'ascensione) il Qi non entra più nel
    regno: si deposita nel Dao. Ogni sessione dà comprensione al tuo Dao migliore."""
    from engine.systems import sects, dao_training, items
    from engine.simulation import world_tick
    rows = dao_training.trainable_daos(conn, player.id)
    if not rows:
        return "Sei allo strato più alto del regno e non hai un Dao in cui depositare il Qi: serve lo sfondamento."
    best = max(rows, key=lambda r: r["comprehension"])
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 29 + player.id)
    spent = sessions = 0
    gain = 1 + _tier(conn, player.id) // 3
    lines: list[str] = []
    for i in range(n):
        if k0 + i >= MAX_PER_DAY:
            break
        c = cost(conn, player.id, k0 + i)
        if sects.get_resource(conn, "pietre_spirituali", player.id) < c:
            break
        sects.grant_resource(conn, "pietre_spirituali", -c, player.id)
        spent += c
        sessions += 1
        lines = items.apply_effects(conn, t, rng, player.id, {"dao_key": best["dao_key"], "dao_gain": gain}) or lines
    if not sessions:
        return f"Ti servono {cost(conn, player.id, k0)} pietre spirituali per una sessione."
    state.set_json(conn, KEY, {"day": _day(conn), "n": k0 + sessions})
    world_tick.advance(conn, 5 * sessions)
    return (f"💎 Il regno è colmo: il Qi delle pietre scende nel Dao. {sessions} "
            f"{'sessione' if sessions == 1 else 'sessioni'}, −{spent} pietre, +{gain * sessions} di comprensione. "
            + (lines[-1] if lines else ""))


def auto_spend(conn, player) -> list[str]:
    """Per il pilota: assorbe ciò che supera la riserva, al massimo AUTO_SESSIONS sessioni al giorno."""
    from engine.systems import sects
    reserve = RESERVE_PER_TIER * _tier(conn, player.id)
    n = 0
    k = done_today(conn)
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    while n < AUTO_SESSIONS and k + n < MAX_PER_DAY and have - cost(conn, player.id, k + n) >= reserve:
        have -= cost(conn, player.id, k + n)
        n += 1
    if not n:
        return []
    txt = absorb(conn, player, n)
    return [txt.splitlines()[0][:140]] if txt.startswith("💎") else []


def menu_section(conn, player):
    from engine.systems.menus import act, section
    from engine.systems import sects
    k = done_today(conn)
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    c = cost(conn, player.id)
    ok = k < MAX_PER_DAY and have >= c
    why = "meridiani saturi per oggi" if k >= MAX_PER_DAY else f"servono {c} pietre"
    return section("Assorbire le pietre spirituali", [
        f"Pietre: {have} · sessioni oggi {k}/{MAX_PER_DAY} · la prossima costa {c}.",
        "Ogni sessione vale circa due terzi di una coltivazione, senza tossine; ogni sessione dello stesso "
        "giorno costa di più. Le pietre restano tue: assorbi solo quando vuoi."],
        [act(f"Assorbi ({c} pietre)", "pietre assorbi", ok, why, main=ok),
         act("Assorbi 3 volte", "pietre assorbi 3", ok, why)], icon="💎")


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    if p and p[0].lower() in ("assorbi", "brucia", "usa", "coltiva"):
        n = int(p[1]) if len(p) > 1 and p[1].isdigit() else 1
        return absorb(conn, player, n)
    from engine.systems import menus
    return menus.render(conn, menus.menu("pietre", "💎 LE PIETRE SPIRITUALI", [], [menu_section(conn, player)]))
