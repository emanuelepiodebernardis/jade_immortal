"""
LA SQUADRA DI BESTIE (Aggiornamento 71) — alla Pokémon, nel mondo dei coltivatori.

  · Fino a TRE bestie (una, due dal 3° regno, tre dal 5°; un Domatore esperto ne guida di più).
  · Ogni bestia ha un LIVELLO che sale combattendo (duelli, lotte tra bestie) e mangiando nuclei.
    A livello 10 e 25 si EVOLVE: prende un nome nuovo e diventa molto più forte.
  · Ogni bestia ha due MOSSE del suo elemento. Nel duello compaiono come carte: «Ordina a Lupo: Morso di Vento».
    Valgono i tipi (superefficace / poco efficace) e gli stati, come le tue tecniche.
  · LOTTA TRA BESTIE: 'squadra lotta <nome>' — la tua bestia capofila contro una creatura del luogo, a turni,
    con i tipi. Se vinci, la tua bestia sale di livello e la creatura sconfitta si lascia domare più facilmente.

Tutto vive in uno stato JSON {npc_id: {lv, xp}} sopra le bestie che già esistono (beasts.py, bonds 'beast').
Per aggiungere mosse o evoluzioni: MOVES / EVO.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import duel_types, state

KEY = "beast_team"
EVO_LV = (10, 25)
# elemento -> due mosse (nome, moltiplicatore)
MOVES = {"fuoco": [("Soffio di Fiamma", 1.5), ("Artiglio Ardente", 1.2)],
         "acqua": [("Getto di Marea", 1.45), ("Morso Gelido", 1.2)],
         "fulmine": [("Scarica del Tuono", 1.55), ("Carica Elettrica", 1.15)],
         "vento": [("Lame di Vento", 1.45), ("Morso di Vento", 1.2)],
         "terra": [("Frana", 1.5), ("Corno di Roccia", 1.2)],
         "metallo": [("Artigli d'Acciaio", 1.5), ("Zanna di Ferro", 1.2)],
         "legno": [("Frusta di Rovi", 1.4), ("Spore Velenose", 1.2)],
         "luce": [("Raggio Sacro", 1.5), ("Bagliore", 1.15)],
         "oscurita": [("Morso d'Ombra", 1.5), ("Nebbia Nera", 1.15)],
         "anima": [("Urlo dell'Anima", 1.45), ("Tocco Spettrale", 1.2)],
         "corpo": [("Carica Possente", 1.5), ("Zampata", 1.2)]}
DEFAULT_MOVES = [("Zampata Feroce", 1.4), ("Morso", 1.2)]
EVO = {1: ("", 1.0), 2: ("Maggiore", 1.6), 3: ("Re", 2.5)}           # stadio -> (titolo, moltiplicatore)


def _all(conn) -> dict:
    return state.get_json(conn, KEY) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def info(conn, npc_id: int) -> dict:
    d = _all(conn)
    return d.get(str(npc_id)) or {"lv": 1, "xp": 0}


def stage(lv: int) -> int:
    return 3 if lv >= EVO_LV[1] else 2 if lv >= EVO_LV[0] else 1


def element(conn, npc_id: int) -> str:
    from engine.systems import beasts
    els = (beasts.traits(conn, npc_id)["elements"] or "corpo").split(",")
    return els[0].strip() or "corpo"


def moves(conn, npc_id: int) -> list[tuple[str, float]]:
    return MOVES.get(element(conn, npc_id), DEFAULT_MOVES)


def display_name(conn, npc_id: int) -> str:
    n = entities.get_npc(conn, npc_id)
    nm = n.name if n else "?"
    t = EVO[stage(info(conn, npc_id)["lv"])][0]
    return f"{nm} {t}".strip()


def gain(conn, npc_id: int, xp: int) -> list[str]:
    """Esperienza alla bestia; livelli ed evoluzioni."""
    d = _all(conn)
    b = d.get(str(npc_id)) or {"lv": 1, "xp": 0}
    before = stage(b["lv"])
    b["xp"] += xp
    out = []
    while b["xp"] >= need(b["lv"]):
        b["xp"] -= need(b["lv"])
        b["lv"] += 1
        out.append(f"🐾 {entities.get_npc(conn, npc_id).name} sale al livello {b['lv']}!")
    d[str(npc_id)] = b
    _save(conn, d)
    if stage(b["lv"]) > before:
        from engine.systems import npc_factory
        npc_factory.raise_npc(conn, npc_id, 6 if stage(b["lv"]) == 2 else 10)
        out.append(f"✨ EVOLUZIONE! La tua bestia diventa {display_name(conn, npc_id)}: più grande, più forte, "
                   f"il suo elemento brucia più intenso.")
    return out


def need(lv: int) -> int:
    return 20 + 10 * lv


def team(conn, pid: int) -> list:
    from engine.systems import beasts
    return beasts.pets(conn, pid)


def lead(conn, pid: int):
    t = team(conn, pid)
    if not t:
        return None
    lid = state.get_int(conn, KEY + "_lead", 0)
    return next((x for x in t if x["npc_id"] == lid), t[0])


def power(conn, npc_id: int) -> float:
    from engine.simulation import combat
    from engine.systems import beasts
    tr = beasts.traits(conn, npc_id)
    lv = info(conn, npc_id)["lv"]
    return (combat.combat_power(conn, "npc", npc_id)["attack"] * beasts.TALENT_MULT.get(tr["talent"], 1.0)
            * EVO[stage(lv)][1] * (1 + 0.04 * lv))


# ---------------- nel duello: le carte delle bestie ----------------
def duel_cards(conn, player, d: dict) -> list[dict]:
    out = []
    for pt in team(conn, player.id)[:3]:
        if pt["location_id"] != player.location_id:
            continue
        el = element(conn, pt["npc_id"])
        cd = d.get("bcd", {}).get(str(pt["npc_id"]), 0) - d["round"]
        mv, m = moves(conn, pt["npc_id"])[0]
        info_ = duel_types.card_info(mv, d.get("el_e"), None)
        eff = duel_types.effectiveness(el, d.get("el_e"))[1]
        out.append({"key": f"bestia_{pt['npc_id']}", "name": f"{display_name(conn, pt['npc_id']).split()[0]}: {mv}",
                    "icon": duel_types.EL_ICON.get(el, "🐾"), "desc": f"la tua bestia attacca (×{m:.1f})", "cost": "",
                    "ok": cd <= 0, "why": f"riprende fiato tra {cd} turni" if cd > 0 else "",
                    "cmd": f"duello_azione bestia {pt['npc_id']}", "kind": "bestia", "cd": max(0, cd),
                    "el": el, "el_icon": duel_types.EL_ICON.get(el, ""), "el_nome": duel_types.EL_IT.get(el, el),
                    "eff": eff, "stato": info_.get("stato", "")})
    return out


def duel_strike(conn, player, d: dict, npc_id: int, pd: dict, rng: random.Random) -> tuple[float, list[str]]:
    """La bestia colpisce su tuo ordine. Ritorna (danno, righe)."""
    from engine.simulation import combat
    pt = next((x for x in team(conn, player.id) if x["npc_id"] == npc_id), None)
    if not pt:
        return 0.0, ["Non hai quella bestia qui."]
    el = element(conn, npc_id)
    mv, m = moves(conn, npc_id)[0]
    eff, tag = duel_types.effectiveness(el, d.get("el_e"))
    dmg, crit = combat._strike(power(conn, npc_id) * m * eff, pd["defense"], rng)
    d.setdefault("bcd", {})[str(npc_id)] = d["round"] + 2
    lines = [f"🐾 {display_name(conn, npc_id)} usa {mv}!" + (" Colpo critico!" if crit else "")]
    if duel_types.eff_line(tag):
        lines.append(duel_types.eff_line(tag))
    s = duel_types.maybe_on_hit(d, el, tag, rng)
    if s:
        lines.append(s)
    return dmg, lines


def after_duel(conn, player, won: bool) -> list[str]:
    out = []
    for pt in team(conn, player.id)[:3]:
        if pt["location_id"] == player.location_id:
            out += gain(conn, pt["npc_id"], 12 if won else 4)
    return out


# ---------------- lotta tra bestie ----------------
def battle(conn, player, target: str) -> str:
    """La tua bestia capofila contro una creatura del luogo: a turni, con i tipi. Niente morti: chi cade, sviene."""
    me = lead(conn, player.id)
    if not me:
        return "Non hai bestie. Domane una con 'tame <nome>'."
    foes = [n for n in entities.npcs_in_location(conn, player.location_id)
            if (conn.execute("SELECT kind FROM npcs WHERE id=?;", (n.id,)).fetchone()["kind"] or "") in ("beast", "spirit")
            and n.id not in {x["npc_id"] for x in team(conn, player.id)}]
    t = (target or "").lower().strip()
    foe = next((n for n in foes if t and t in n.name.lower()), foes[0] if foes and not t else None)
    if not foe:
        return "Qui non c'è nessuna creatura con cui lottare." if not foes else f"Nessuna creatura chiamata '{target}'."
    day = tick_mod.get_tick(conn) // 120
    k = f"{KEY}_fought_{foe.id}"
    if state.get_int(conn, k, -1) == day:
        return f"{foe.name} è ancora stremato dall'ultima lotta."
    state.set(conn, k, str(day))
    rng = random.Random(tick_mod.get_tick(conn) * 13 + foe.id)
    a_el, b_el = element(conn, me["npc_id"]), element(conn, foe.id)
    a_hp = b_hp = 100.0
    a_pow, b_pow = power(conn, me["npc_id"]), power(conn, foe.id) * 0.9
    a_name = display_name(conn, me["npc_id"])
    lines = [f"🐾 LOTTA TRA BESTIE: {a_name} ({duel_types.EL_ICON.get(a_el, '')}) contro {foe.name} "
             f"({duel_types.EL_ICON.get(b_el, '')})"]
    ratio = a_pow / max(1.0, a_pow + b_pow)
    for rnd in range(1, 9):
        mv, m = rng.choice(moves(conn, me["npc_id"]))
        e1, t1 = duel_types.effectiveness(a_el, b_el)
        hit = 30 * m * e1 * (0.6 + 0.8 * rng.random()) * (0.5 + ratio)
        b_hp -= hit
        lines.append(f"  {rnd}. {a_name} usa {mv}: −{round(hit)}" + (" — superefficace!" if t1 == "super" else
                                                                   " — poco efficace" if t1 == "poco" else ""))
        if b_hp <= 0:
            break
        mv2, m2 = rng.choice(MOVES.get(b_el, DEFAULT_MOVES))
        e2, t2 = duel_types.effectiveness(b_el, a_el)
        hit2 = 30 * m2 * e2 * (0.6 + 0.8 * rng.random()) * (1.5 - ratio)
        a_hp -= hit2
        lines.append(f"     {foe.name} risponde con {mv2}: −{round(hit2)}" + (" — superefficace!" if t2 == "super" else ""))
        if a_hp <= 0:
            break
    won = b_hp <= 0 or (a_hp > 0 and a_hp >= b_hp)
    if won:
        lines.append(f"🏆 {foe.name} crolla esausto! {a_name} ha vinto. (Ora domarlo è più facile: 'tame {foe.name.split()[0]}')")
        try:
            conn.execute("INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
                         "healed, heal_tick) VALUES ('npc', ?, 2, 'sfinito dalla lotta', ?, 0, ?);",
                         (foe.id, tick_mod.get_tick(conn), tick_mod.get_tick(conn) + 240))
        except Exception:                              # noqa: BLE001
            pass
        lines += gain(conn, me["npc_id"], 25)
    else:
        lines.append(f"{a_name} sviene. {foe.name} ruggisce e si allontana.")
        lines += gain(conn, me["npc_id"], 8)
    return "\n".join(lines)


# ---------------- la scheda ----------------
def describe(conn, player) -> str:
    from engine.systems import beasts, classes
    t = team(conn, player.id)
    mx = classes.max_beasts(conn, player.id)
    if not t:
        return f"🐾 SQUADRA (0/{mx}) — domane una con 'tame <nome>' (ferirla prima aiuta)."
    ld = lead(conn, player.id)
    lines = [f"🐾 SQUADRA ({len(t)}/{mx})"]
    for i, pt in enumerate(t, 1):
        b = info(conn, pt["npc_id"])
        tr = beasts.traits(conn, pt["npc_id"])
        el = element(conn, pt["npc_id"])
        mv = " · ".join(m for m, _x in moves(conn, pt["npc_id"]))
        lines.append(f"  {i}. {'★ ' if ld and pt['npc_id'] == ld['npc_id'] else ''}{display_name(conn, pt['npc_id'])} — "
                     f"liv. {b['lv']} ({b['xp']}/{need(b['lv'])} xp) · {duel_types.EL_ICON.get(el, '')} "
                     f"{duel_types.EL_IT.get(el, el)} · talento {tr['talent']} · mosse: {mv}"
                     + (f" · evolve al liv. {EVO_LV[0] if b['lv'] < EVO_LV[0] else EVO_LV[1]}" if b["lv"] < EVO_LV[1] else ""))
    lines.append("'squadra capo <n>' sceglie la capofila · 'squadra lotta <creatura>' · 'feed' nutre la capofila")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    p = (arg or "").split(maxsplit=1)
    sub = p[0].lower() if p else ""
    if sub in ("capo", "capofila", "guida") and len(p) > 1 and p[1].strip().isdigit():
        t = team(conn, player.id)
        i = int(p[1]) - 1
        if 0 <= i < len(t):
            state.set(conn, KEY + "_lead", str(t[i]["npc_id"]))
            return f"{display_name(conn, t[i]['npc_id'])} guida la squadra."
        return "Nessuna bestia con quel numero."
    if sub in ("lotta", "sfida"):
        return battle(conn, player, p[1] if len(p) > 1 else "")
    return describe(conn, player)
