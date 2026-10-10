"""
IL SISTEMA (系统) — solo per l'origine «Trasmigratore col Sistema».

Una voce fredda nella tua testa: [Ding!] Ogni giorno il Sistema assegna tre MISSIONI
(coltivare, comprendere il Dao, uccidere, raccogliere, creare…). Completarle dà PUNTI
SISTEMA da spendere nel NEGOZIO: pillole, metodi di coltivazione, anni di vita, frammenti
di Dao, sfondamenti assistiti. Le missioni crescono con te, senza fine.

  sistema                 pannello: missioni del giorno, avanzamento, punti
  sistema riscuoti        incassa le missioni completate
  sistema negozio         il negozio del Sistema
  sistema compra <n>      compra l'articolo n

L'avanzamento si misura da contatori reali del gioco: non serve fare nulla di speciale,
basta vivere da coltivatore.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

# chiave -> (descrizione con {n}, funzione contatore, base, crescita per regno)
def _c_cult(conn, pid):
    r = conn.execute("SELECT cult_sessions FROM character_profiles WHERE character_type='player' "
                     "AND character_id=?;", (pid,)).fetchone()
    return (r["cult_sessions"] or 0) if r else 0


def _c_dao(conn, pid):
    r = conn.execute("SELECT dao_sessions FROM character_profiles WHERE character_type='player' "
                     "AND character_id=?;", (pid,)).fetchone()
    return (r["dao_sessions"] or 0) if r else 0


def _c_kills(conn, pid):
    return state.get_int(conn, "kills_total", 0)


def _c_mats(conn, pid):
    return state.get_int(conn, "sys_gathered", 0)


def _c_prof(conn, pid):
    return state.get_int(conn, "profession_xp", 0)


def _c_fame(conn, pid):
    from engine.systems import reputation
    return reputation.get(conn, pid)["fame"]


QUESTS = {
    "coltiva": ("Coltiva {n} volte", _c_cult, 3, 1),
    "dao": ("Medita il Dao {n} volte", _c_dao, 2, 1),
    "uccidi": ("Abbatti {n} nemici", _c_kills, 2, 1),
    "raccogli": ("Raccogli {n} materiali", _c_mats, 4, 2),
    "arte": ("Guadagna {n} esperienza nella tua arte", _c_prof, 2, 1),
    "fama": ("Accresci la tua fama di {n}", _c_fame, 2, 1),
}

SHOP = [
    ("Pillola del Sistema (esperienza di coltivazione)", 30, "pill"),
    ("Frammento di Dao (comprensione del tuo Dao migliore)", 45, "dao"),
    ("Anni di vita (+10)", 60, "life"),
    ("Sfondamento assistito (bonus al prossimo breakthrough)", 80, "bt"),
    ("Metodo di coltivazione del Sistema (grado pari al tuo regno +1)", 150, "gongfa"),
    ("Pozione di talento (affinità di coltivazione +2)", 200, "talent"),
]


def active(conn) -> bool:
    from engine.systems import character
    p = character.get_profile(conn, "player", 1)
    return bool(p and p["origin"] == "trasmigratore")


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _new_day(conn, pid: int, day: int) -> dict:
    rng = random.Random(day * 7919 + pid)
    keys = rng.sample(list(QUESTS), 3)
    tier = _tier(conn, pid)
    qs = []
    for k in keys:
        _d, fn, base, grow = QUESTS[k]
        need = base + grow * (tier - 1)
        qs.append({"key": k, "need": need, "start": fn(conn, pid), "done": False,
                   "reward": 8 + 4 * tier + 2 * need})
    d = {"day": day, "quests": qs}
    state.set_json(conn, "sys_day", d)
    return d


def today(conn, pid: int = 1) -> dict:
    day = tick_mod.get_tick(conn) // 120
    d = state.get_json(conn, "sys_day")
    if not d or d["day"] != day:
        d = _new_day(conn, pid, day)
    return d


def points(conn) -> int:
    return state.get_int(conn, "sys_points", 0)


def _progress(conn, pid, q) -> int:
    return max(0, QUESTS[q["key"]][1](conn, pid) - q["start"])


def describe(conn, player) -> str:
    if not active(conn):
        return "Nessuna voce ti risponde. (Il Sistema accompagna solo i Trasmigratori.)"
    d = today(conn, player.id)
    lines = ["[Ding!] ═══ PANNELLO DEL SISTEMA ═══", f"Punti Sistema: {points(conn)}",
             "Missioni di oggi:"]
    for i, q in enumerate(d["quests"], 1):
        pr = min(q["need"], _progress(conn, player.id, q))
        mark = "✔ riscossa" if q["done"] else ("✔ completa! ('sistema riscuoti')" if pr >= q["need"] else f"{pr}/{q['need']}")
        lines.append(f"  {i}. {QUESTS[q['key']][0].format(n=q['need'])} — {mark} (+{q['reward']} punti)")
    lines.append("'sistema negozio' per spendere i punti.")
    return "\n".join(lines)


def claim(conn, player) -> str:
    if not active(conn):
        return describe(conn, player)
    d = today(conn, player.id)
    got = 0
    for q in d["quests"]:
        if not q["done"] and _progress(conn, player.id, q) >= q["need"]:
            q["done"] = True
            got += q["reward"]
    if not got:
        return "[Ding!] Nessuna missione completata da riscuotere."
    bonus = ""
    if all(q["done"] for q in d["quests"]):
        got += 10 * _tier(conn, player.id)
        bonus = " Tutte le missioni del giorno completate: bonus!"
        n = state.get_int(conn, "sys_full_days", 0) + 1
        state.set(conn, "sys_full_days", str(n))
        if n in (7, 30, 100) and state.grant_title(conn, {7: "Ospite del Sistema", 30: "Prediletto del Sistema",
                                                           100: "Padrone del Sistema"}[n]):
            bonus += " ✧ Nuovo titolo! ✧"
    state.set_json(conn, "sys_day", d)
    state.set(conn, "sys_points", str(points(conn) + got))
    return f"[Ding!] Ricompensa: +{got} punti Sistema (totale {points(conn)}).{bonus}"


def shop(conn) -> str:
    lines = [f"[Ding!] NEGOZIO DEL SISTEMA — hai {points(conn)} punti"]
    for i, (name, cost, _k) in enumerate(SHOP, 1):
        lines.append(f"  {i}. {name} — {cost} punti")
    lines.append("'sistema compra <n>'")
    return "\n".join(lines)


def buy(conn, player, n: int) -> str:
    from engine.systems import items, heart_demon, gongfa, dao_training, lifespan
    if not (1 <= n <= len(SHOP)):
        return shop(conn)
    name, cost, kind = SHOP[n - 1]
    if points(conn) < cost:
        return f"[Ding!] Punti insufficienti ({points(conn)}/{cost})."
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 3 + n)
    tier = _tier(conn, player.id)
    state.set(conn, "sys_points", str(points(conn) - cost))
    out = [f"[Ding!] Acquisto: {name}."]
    if kind == "pill":
        out += items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": 0.4})
    elif kind == "dao":
        rows = dao_training.trainable_daos(conn, player.id)
        if rows:
            out += items.apply_effects(conn, t, rng, player.id,
                                       {"dao_key": rows[0]["dao_key"], "dao_gain": 6 + 3 * tier})
    elif kind == "life":
        lifespan.add_bonus_years(conn, 10)
        out.append("La tua vita si allunga di 10 anni.")
    elif kind == "bt":
        heart_demon.add_bonus(conn, 0.15)
        out.append("Il prossimo sfondamento sarà più sicuro.")
    elif kind == "gongfa":
        out.append(gongfa.learn(conn, player.id, gongfa.generate(rng, tier + 1)))
    elif kind == "talent":
        out += items.apply_effects(conn, t, rng, player.id, {"aff_cultivation": 2})
    return "\n".join(out)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    if not active(conn):
        return describe(conn, player)
    if sub in ("riscuoti", "claim", "incassa"):
        return claim(conn, player)
    if sub in ("negozio", "shop"):
        return shop(conn)
    if sub in ("compra", "buy") and len(parts) > 1 and parts[1].isdigit():
        return buy(conn, player, int(parts[1]))
    return describe(conn, player)


def daily(conn, t: int, rng, player) -> list[str]:
    if not active(conn):
        return []
    d = today(conn, player.id)
    return ["[Ding!] Nuove missioni del Sistema: " +
            "; ".join(QUESTS[q["key"]][0].format(n=q["need"]) for q in d["quests"]) + " ('sistema')"]
