"""
RENDITE — come si guadagna, in un pannello solo ('rendite', pulsante 💰 Rendite).

Le cose costano sempre di più (la dimora cresce del 60% a livello, le fusioni col regno…): le rendite
crescono con te. Ogni giorno, all'alba, arrivano da sole; ogni 7 giorni un riepilogo.

  BOTTEGA        ogni arte dal livello 3 vende ciò che produci (pillole, talismani, armi, formazioni,
                 bestie addestrate): più alto il livello e il regno, più rende. Le arti che pratichi
                 rendono intere, le altre a metà.
  SETTA          lo stipendio del rango (ogni 30 giorni, molto più alto di prima) e, da Erede della Setta
                 in su, una QUOTA DEL TESORO della setta ogni giorno.
  LA TUA SETTA   i tributi della setta che hai fondato (si riscuotono qui).
  VASSALLE       i tributi delle sette vassalle (si riscuotono qui).
  SERVI          i servi al lavoro portano pietre.
  RAZZE          da Anziano in su le razze ti versano una rendita; da Sovrano/Eletto il tesoro della razza.
  REGNI          lo stipendio del tuo rango a corte (ogni 5 giorni) e la rendita del trono.

  rendite               il pannello: quanto rende ogni fonte, al giorno e al mese
  rendite riscuoti      riscuoti tutto ciò che si accumula (stipendio, tesoro della tua setta, vassalle)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

WEEK_KEY = "income_week"


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _tm(conn, pid) -> float:
    """Le rendite seguono il tuo regno: chi è più in alto guadagna (e spende) di più."""
    return 1 + 0.5 * _tier(conn, pid)


def workshop(conn, pid: int = 1) -> list[tuple[str, int]]:
    from engine.systems import professions as P
    out = []
    on = set(P.practiced(conn, pid))
    for k in P.known(conn, pid):
        lv = P.level(conn, pid, k)
        if lv < 3:
            continue
        v = 4 * lv ** 1.5 * _tm(conn, pid) * (1.0 if k in on else 0.5)
        out.append((P.PROFESSIONS[k], int(v)))
    return out


def sect_treasury_share(conn, pid: int = 1) -> int:
    """Da Erede della Setta in su attingi ogni giorno al tesoro della setta."""
    from engine.systems import sects
    m = sects.get_membership(conn, pid)
    if not m or m["rank"] not in sects.RANK_LADDER:
        return 0
    idx = sects.RANK_LADDER.index(m["rank"])
    if idx < 6:
        return 0
    f = conn.execute("SELECT wealth, tier FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    return int((f["wealth"] or 50) * (f["tier"] or 1) * (0.4 if idx == 6 else 0.8))


def race_rent(conn, pid: int = 1) -> list[tuple[str, int]]:
    from engine.systems import race_realms
    out = []
    for k, r in race_realms.get(conn).items():
        st = r.get("standing", 0)
        if st >= 3:
            v = (15 * st if st < 5 else 120) * _tier(conn, pid)
            out.append((f"{race_realms.standing_name(k, st, r.get('path', ''))} dei {race_realms._name(k)}", int(v)))
    return out


def sources(conn, player) -> list[tuple[str, str, int, str]]:
    """(icona, fonte, pietre al giorno, nota)."""
    from engine.systems import sect_menu, dominion, own_sect, kingdoms
    pid = player.id
    out = []
    for nm, v in workshop(conn, pid):
        out.append(("⚒", f"Bottega: {nm}", v, "ogni giorno"))
    if sect_menu._m(conn, pid):
        ok, amount, left = sect_menu.stipend_info(conn, player)
        out.append(("⛩", "Stipendio della setta", amount // 30, "pronto da riscuotere" if ok else f"tra {left} giorni"))
    share = sect_treasury_share(conn, pid)
    if share:
        out.append(("⛩", "Quota del tesoro della setta", share, "ogni giorno (rango di vertice)"))
    s = own_sect.get(conn)
    if s:
        out.append(("🏯", f"Tributi di {s['name']}", 0, f"{s.get('treasury', 0)} nel tesoro"))
    v = dominion.vassals(conn)
    if v:
        out.append(("🏯", "Tributi delle vassalle", sum(dominion.tribute_per_day(conn, int(k), e) for k, e in v.items()),
                    f"{sum(int(e.get('acc', 0)) for e in v.values())} accumulati"))
    workers = [s for s in dominion.servants(conn) if s["role"] == "lavoro"]
    if workers:
        out.append(("⛓", f"Servi al lavoro ({len(workers)})", sum(5 + 3 * dominion._tier(conn, "npc", s["npc_id"])
                                                                   for s in workers), "ogni giorno"))
    for nm, val in race_rent(conn, pid):
        out.append(("🐉", nm, val, "ogni giorno"))
    try:
        d = kingdoms.all_k(conn)
        for _rk, k in (d or {}).items():
            idx = sum(1 for th, _n in kingdoms.RANKS if k["favor"] >= th) - 1
            if idx > 0 or k.get("ruler_player"):
                val = (20 * idx * idx * _tier(conn, pid) // 2 + (300 * _tier(conn, pid) if k.get("ruler_player") else 0)) // 5
                out.append(("👑", f"Corte di {k['name']} ({kingdoms.rank_of(k['favor'])})", val, "ogni 5 giorni"))
    except Exception:
        pass
    return out


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    """All'alba: la bottega vende, il tesoro della setta paga, le razze versano. Riepilogo ogni 7 giorni."""
    from engine.systems import sects
    pid = player.id
    got = sum(v for _n, v in workshop(conn, pid)) + sect_treasury_share(conn, pid) + sum(v for _n, v in race_rent(conn, pid))
    if got:
        sects.grant_resource(conn, "pietre_spirituali", got, pid)
    wk = state.get_int(conn, WEEK_KEY, 0) + got
    out = []
    if (t // 120) % 7 == 0 and wk:
        out.append(f"💰 Rendite della settimana: {wk} pietre spirituali (bottega, setta, razze). ('rendite')")
        wk = 0
    state.set(conn, WEEK_KEY, str(wk))
    return out


def collect_all(conn, player) -> str:
    """Riscuote in un colpo tutto ciò che si accumula: stipendio, tesoro della tua setta, vassalle."""
    from engine.systems import sect_menu, dominion, own_sect
    out = []
    if sect_menu._m(conn, player.id) and sect_menu.stipend_info(conn, player)[0]:
        out.append(sect_menu.stipend(conn, player))
    s = own_sect.get(conn)
    if s and s.get("treasury", 0) > 0:
        out.append(own_sect.collect(conn, player))
    if any(int(e.get("acc", 0)) for e in dominion.vassals(conn).values()):
        out.append(dominion.collect(conn, player))
    return "\n".join(out) if out else "Non c'è nulla da riscuotere adesso: le altre rendite arrivano da sole ogni giorno."


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import sects
    src = sources(conn, player)
    per_day = sum(v for _i, _n, v, _note in src)
    lines = [f"{i} {n}: {v} al giorno ({note})" for i, n, v, note in src] or [
        "Nessuna rendita, per ora. Porta un'arte al livello 3, sali di rango nella setta, sottometti sette o "
        "razze, conquista un rango a corte."]
    secs = [section("Le tue rendite", [f"Pietre spirituali: {sects.get_resource(conn, 'pietre_spirituali', player.id)}"
                                       f" · rendita stimata: ~{per_day} al giorno, ~{per_day * 30} al mese"] + lines,
                    [act("Riscuoti tutto ciò che si accumula", "rendite riscuoti", main=True),
                     act("Arti e bottega", "arti"), act("Setta", "setta"), act("Dominio", "dominio"),
                     act("Regni delle razze", "razze")], icon="💰")]
    wk = state.get_int(conn, WEEK_KEY, 0)
    secs.append(section("Questa settimana", [f"Già arrivate da sole: {wk} pietre."],
                        bars=[bar("Settimana", 100 * ((tick_mod.get_tick(conn) // 120) % 7) / 7, tone="info")], icon="📅"))
    secs.append(section("Come guadagnare di più", [
        "⚒ Ogni livello d'arte rende di più (e le arti che pratichi rendono il doppio).",
        "⛩ Da Erede della Setta in su attingi ogni giorno al tesoro della setta.",
        "🏯 Fonda una setta, o sottometti un patriarca: tributi ogni giorno.",
        "🐉 Da Anziano di una razza in su ricevi una rendita; da Sovrano il loro tesoro.",
        "👑 Il favore a corte porta uno stipendio; il trono una rendita."], icon="📜"))
    return menu("rendite", "💰 RENDITE", ["Le cose costano sempre di più: le rendite crescono con te."], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus
    if arg.strip().lower() in ("riscuoti", "ritira", "tutto"):
        return collect_all(conn, player)
    return menus.show(conn, player, "rendite")
