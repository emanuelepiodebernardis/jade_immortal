"""
LE STAGIONI E I GRANDI TRAGUARDI (Aggiornamento 70) — un obiettivo anche quando hai già tutto.

STAGIONE — ogni 30 giorni di gioco il Cielo cambia legge:
  · un ELEMENTO della stagione: le tecniche di quell'elemento colpiscono ×1,15 nel duello;
  · tre PROVE scelte a rotazione (sconfiggi élite, colpi superefficaci, forgia, risparmia i vinti…);
    ogni prova completata dà pietre; tutte e tre danno un pezzo d'equipaggiamento DIVINO del set della
    stagione e un titolo unico. Le stagioni passate restano nell'albo.

GRANDI TRAGUARDI — la scheda «🏆 Traguardi» raccoglie le grandi vie del finale: ascendere al mondo superiore,
fondare e far crescere la tua setta, salire la Torre della Deificazione, la stagione in corso.

Contatori: count(conn, chiave) dagli agganci (duello, forgia…). Aggiungere una prova è una riga in TRIALS.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "seasons"
DAYS = 30
ELEMENTS = ["fuoco", "acqua", "fulmine", "legno", "metallo", "terra", "luce", "oscurita"]
SET_OF = {"fuoco": "fenice", "acqua": "tartaruga", "fulmine": "drago", "legno": "qilin", "metallo": "tigre",
          "terra": "tartaruga", "luce": "qilin", "oscurita": "drago"}
EL_BONUS = 1.15
# chiave -> (descrizione, obiettivo)
TRIALS = {
    "elite": ("Sconfiggi élite o boss", 4),
    "duelli": ("Vinci duelli", 8),
    "super": ("Colpi superefficaci", 15),
    "stati": ("Stati lasciati sui nemici", 12),
    "forgia": ("Pezzi forgiati", 3),
    "risparmia": ("Avversari risparmiati", 3),
    "elemento": ("Colpi con l'elemento della stagione", 10),
}


def season_no(conn) -> int:
    return tick_mod.get_tick(conn) // 120 // DAYS


def element(conn) -> str:
    return ELEMENTS[season_no(conn) % len(ELEMENTS)]


def trials_of(n: int) -> list[str]:
    keys = list(TRIALS)
    return random.Random(n * 7907 + 3).sample(keys, 3)


def get(conn) -> dict:
    d = state.get_json(conn, KEY) or {}
    n = season_no(conn)
    if d.get("n") != n:
        if d.get("n") is not None:
            albo = d.get("albo", [])
            albo.append({"n": d["n"], "el": ELEMENTS[d["n"] % len(ELEMENTS)],
                         "fatte": sum(1 for k in d.get("trials", []) if k in d.get("done", [])), "campione": d.get("champion", False)})
            d = {"albo": albo[-12:]}
        d.update({"n": n, "trials": trials_of(n), "count": {}, "done": [], "champion": False})
        state.set_json(conn, KEY, d)
    d.setdefault("albo", [])
    return d


def count(conn, key: str, n: int = 1) -> list[str]:
    """Un passo verso una prova della stagione. Ritorna le righe dei premi, se ne arrivano."""
    d = get(conn)
    if key not in d["trials"] or key in d["done"]:
        return []
    d["count"][key] = d["count"].get(key, 0) + n
    out = []
    if d["count"][key] >= TRIALS[key][1]:
        d["done"].append(key)
        out += _reward_trial(conn, key)
        if len(d["done"]) == len(d["trials"]) and not d["champion"]:
            d["champion"] = True
            out += _reward_champion(conn)
    state.set_json(conn, KEY, d)
    return out


def _player(conn):
    from engine.core import entities
    return entities.get_player(conn)


def _tier(conn) -> int:
    from engine.simulation import cultivation
    p = _player(conn)
    return max(1, cultivation.realm_tier(conn, "player", p.id) or 1) if p else 1


def _reward_trial(conn, key: str) -> list[str]:
    from engine.systems import sects
    p = _player(conn)
    v = 300 * _tier(conn)
    if p:
        sects.grant_resource(conn, "pietre_spirituali", v, p.id)
    return [f"🏆 Prova della stagione superata: {TRIALS[key][0]}! (+{v} pietre)"]


def _reward_champion(conn) -> list[str]:
    from engine.systems import gear
    el = element(conn)
    it = gear.make(random.Random(season_no(conn) * 13), _tier(conn), rar="divina")
    it["set"] = SET_OF.get(el, "drago")
    it["nome"] = it["nome"].split(" del")[0].split(" dei")[0] + f" {gear.SETS[it['set']][0]}"
    out = ["🏆 Hai superato tutte le prove della stagione!"]
    out.append(gear.add(conn, it))
    title = f"Campione della Stagione {_el_it(el)} ({season_no(conn) + 1}ª)"
    if state.grant_title(conn, title):
        out.append(f"✧ Nuovo titolo: «{title}» ✧")
    return out


def _el_it(el: str) -> str:
    from engine.systems import duel_types
    return "del " + duel_types.EL_IT.get(el, el) if el != "acqua" else "dell'Acqua"


def duel_bonus(conn, move_el: str | None) -> float:
    return EL_BONUS if move_el and move_el == element(conn) else 1.0


def days_left(conn) -> int:
    return DAYS - (tick_mod.get_tick(conn) // 120) % DAYS


# ---------------- la scheda ----------------
def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import duel_types
    d = get(conn)
    el = element(conn)
    secs = []
    bars = []
    for k in d["trials"]:
        desc, goal = TRIALS[k]
        c = min(goal, d["count"].get(k, 0))
        bars.append(bar(f"{'✔ ' if k in d['done'] else ''}{desc} {c}/{goal}", 100 * c / goal, "", tone="rare" if k in d["done"] else ""))
    secs.append(section(f"Stagione {d['n'] + 1} — {duel_types.EL_ICON.get(el, '')} {_el_it(el).split(' ', 1)[-1]}", [
        f"Legge del Cielo: le tecniche di {duel_types.EL_IT.get(el, el)} colpiscono ×{EL_BONUS:.2f}. "
        f"Mancano {days_left(conn)} giorni.",
        f"Ogni prova: {300 * _tier(conn)} pietre. Tutte e tre: un pezzo DIVINO del set "
        f"{gear_set_name(el)} e il titolo di Campione."], [], bars, icon="🏆"))
    # le grandi vie del finale
    lines, acts = [], []
    try:
        from engine.systems import ascension
        lay = ascension.reached(conn)
        cap = ascension.world_cap(lay)
        from engine.simulation import cultivation
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        peak = ascension.at_world_peak(conn, player.id)
        lines.append(f"🌌 Ascensione: sei nel {ascension.layer_name(lay)} (tetto: {cap}° regno, tu sei al {tier}°)."
                     + (" Sei al vertice: puoi ascendere." if peak else ""))
        acts.append(act("Ascendi al mondo superiore", "ascendi_mondo", peak, f"serve il {cap}° regno al massimo"))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.systems import own_sect
        s = own_sect.get(conn)
        lines.append(f"⛩ La tua setta: {s.get('name', 'fondata')}." if s else
                     "⛩ La tua setta: non ancora fondata (dal 4° regno, con dimora, 3 discepoli e 2000 pietre).")
        acts.append(act("La tua setta" if s else "Fonda la tua setta", "setta" if s else "fonda", True))
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from engine.systems import deification_tower
        t = deification_tower.get(conn)
        lines.append(f"🗼 Torre della Deificazione: piano migliore {t.get('best', 0)}, questa settimana {t.get('floor', 0)}.")
        acts.append(act("Sali la Torre", "torre"))
    except Exception:                                  # noqa: BLE001
        pass
    secs.append(section("Le grandi vie del finale", lines, acts, icon="🌌"))
    if d["albo"]:
        secs.append(section("Albo delle stagioni", [
            f"Stagione {x['n'] + 1} ({duel_types.EL_IT.get(x['el'], x['el'])}): {x['fatte']}/3 prove"
            + (" · 🏆 Campione" if x["campione"] else "") for x in reversed(d["albo"])], icon="📜"))
    return menu("stagione", "🏆 TRAGUARDI", ["Quando hai già tutto, il Cielo cambia le regole."], secs)


def gear_set_name(el: str) -> str:
    from engine.systems import gear
    return gear.SETS[SET_OF.get(el, "drago")][0].split(" ", 1)[-1]


def command(conn, player, arg: str) -> str:
    from engine.systems import duel_types
    d = get(conn)
    el = element(conn)
    lines = [f"🏆 STAGIONE {d['n'] + 1} — elemento {duel_types.EL_IT.get(el, el)} (×{EL_BONUS}), {days_left(conn)} giorni"]
    for k in d["trials"]:
        desc, goal = TRIALS[k]
        lines.append(f"  {'✔' if k in d['done'] else '·'} {desc}: {min(goal, d['count'].get(k, 0))}/{goal}")
    return "\n".join(lines)
