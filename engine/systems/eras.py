"""
LE ERE DEL MONDO e la CALAMITÀ che ritorna.

Il mondo vive per ERE (ognuna dura circa 90 giorni). Ogni era cambia le regole:
  Era della Rinascita del Qi   si coltiva più in fretta; gli elementi celesti nascono più spesso
  Era del Declino              il Qi si fa raro (coltivazione più lenta)… ma i maestri nascosti escono
  Era delle Mille Scuole       le sette fioriscono: tornei e gare più ricchi
  Era della Pace               nessun cambiamento: il respiro tra due tempeste
  Era della Calamità           ogni quarta era torna la CALAMITÀ (la Marea Oscura, la Notte senza Qi,
                               la Pioggia di Sangue…): ondate che vanno respinte. Ogni calamità è più
                               forte della precedente — senza fine.

Durante la calamità, gli ALLEATI che hai conquistato (razze alleate, il regno che servi, la
tua setta, la tua famiglia, i fratelli giurati, i discepoli) combattono con te: ognuno rende
le ondate più facili e lo racconta il resoconto. Le scelte fatte nella storia contano qui.

  era          l'era attuale, quanto manca alla prossima, la prossima calamità
  calamita     (durante la calamità) affronti la prossima ondata
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "world_era"            # sopravvive alla reincarnazione: il mondo resta
ERA_DAYS = 90
ERAS = {
    "rinascita": ("Era della Rinascita del Qi", 1.25),
    "declino": ("Era del Declino", 0.85),
    "scuole": ("Era delle Mille Scuole", 1.0),
    "pace": ("Era della Pace", 1.0),
    "calamita": ("Era della Calamità", 1.0),
}
_CALAMITIES = ["la Marea Oscura", "la Notte senza Qi", "la Pioggia di Sangue", "lo Sciame del Vuoto",
               "il Risveglio delle Ossa", "la Fiamma che Divora i Cieli"]


def get(conn) -> dict:
    d = state.get_json(conn, KEY)
    if not d:
        d = {"key": "pace", "start": 0, "n": 1, "calamities": 0, "waves": 0, "wave_day": 0, "calamity": None}
        state.set_json(conn, KEY, d)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def name(conn) -> str:
    return ERAS[get(conn)["key"]][0]


def cultivation_mult(conn) -> tuple[float, str]:
    k = get(conn)["key"]
    m = ERAS[k][1]
    return (m, ERAS[k][0]) if m != 1.0 else (1.0, "")


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    d = get(conn)
    day = t // 120
    out = []
    if day - d["start"] >= ERA_DAYS:
        d["n"] += 1
        d["start"] = day
        if d["n"] % 4 == 0:
            d["key"] = "calamita"
            d["calamities"] += 1
            d["calamity"] = rng.choice(_CALAMITIES)
            d["waves"] = 3 + d["calamities"]
            d["wave_day"] = day
            out.append(f"☠ Comincia l'ERA DELLA CALAMITÀ: {d['calamity']} si abbatte sul mondo "
                       f"({d['calamities']}ª calamità, {d['waves']} ondate). ('calamita' per affrontarla)")
        else:
            d["key"] = rng.choice(["rinascita", "declino", "scuole", "pace"])
            d["calamity"] = None
            out.append(f"✦ Il mondo entra in una nuova era: {ERAS[d['key']][0]}. ('era')")
        _save(conn, d)
    elif d["key"] == "calamita" and d["waves"] > 0 and day - d.get("wave_day", day) >= 15:
        # un'ondata non respinta colpisce il mondo
        d["wave_day"] = day
        d["waves"] -= 1
        _save(conn, d)
        _wave_damage(conn, rng)
        out.append(f"⚠ Un'ondata di {d['calamity']} si abbatte senza che nessuno la fermi: città ferite, vite perdute.")
    return out


def _wave_damage(conn, rng) -> None:
    rows = conn.execute("SELECT id FROM npcs WHERE status='alive' AND COALESCE(kind,'human')='human' "
                        "ORDER BY RANDOM() LIMIT 2;").fetchall()
    for r in rows:
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (r["id"],))
    conn.execute("UPDATE factions SET influence=MAX(0, influence-5) WHERE status='active';")


def allies(conn, pid: int) -> list[str]:
    from engine.systems import races, kingdoms, sects, family, oaths, own_sect
    out = [races.RACES[k][0] for k in races.allies(conn)]
    out += [k["name"] for k in kingdoms.all_k(conn).values() if k["favor"] >= 200 or k["ruler_player"]]
    m = sects.get_membership(conn, pid)
    if m:
        out.append(m["sect_name"])
    s = own_sect.get(conn)
    if s:
        out.append(s["name"])
    if family.get(conn):
        out.append(family.get(conn)["clan"])
    out += [r["name"] for r in oaths.sworn(conn, pid)]
    if own_sect.disciples(conn, pid):
        out.append("i tuoi discepoli")
    return out


def fight_wave(conn, player) -> str:
    from engine.systems import encounters, npc_factory
    from engine.simulation import cultivation
    d = get(conn)
    if d["key"] != "calamita" or d["waves"] <= 0:
        return "Nessuna calamità in corso. ('era')"
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    al = allies(conn, player.id)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    stage = max(1, 4 + d["calamities"] * 2 - len(al))
    rng = random.Random(tick_mod.get_tick(conn) + d["waves"])
    help_line = ("Al tuo fianco combattono: " + ", ".join(al) + ".") if al else "Combatti da solo: nessuno ti ha seguito."
    sc = {"key": "calamita", "title": f"La calamità: {d['calamity']} (ondate rimaste {d['waves']})",
          "event_type": "combat", "sticky": True,
          "text": f"L'ondata avanza, guidata da {{npc}}. {help_line}",
          "spawn": {"archetype": "guardia", "tier_offset": 1 if d["calamities"] > 2 else 0, "stage": min(10, stage)},
          "choices": [{"label": "Affronti il condottiero dell'ondata", "effects": {"calamity_wave": True, "fame": 4},
                       "command": "attack {npc}"},
                      {"label": "Organizzi la difesa con i tuoi alleati",
                       "check": {"stat": "potenza", "dc": max(30, 70 + 3 * d["calamities"] - 6 * len(al))},
                       "success": {"calamity_wave": True, "npc_leaves": True, "fame": 6,
                                   "text": "La linea regge: l'ondata si infrange contro i tuoi alleati."},
                       "failure": {"injury": 3, "text": "La linea cede in un punto: l'ondata passa, ma la ricacciate."}}]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    return encounters.start_scene(conn, player, sc, force=True) or ""


def wave_won(conn) -> list[str]:
    d = get(conn)
    if d["key"] != "calamita" or d["waves"] <= 0:
        return []
    d["waves"] -= 1
    d["wave_day"] = tick_mod.get_tick(conn) // 120
    out = [f"L'ondata è respinta. Ne restano {d['waves']}."]
    if d["waves"] == 0:
        out.append(f"✦ {d['calamity'].capitalize()} è finita, e il mondo ricorda chi l'ha fermata.")
        n = state.get_int(conn, "world_calamities_stopped", 0) + 1
        state.set(conn, "world_calamities_stopped", str(n))
        t = {1: "Argine contro la Calamità", 3: "Pilastro delle Ere", 10: "Custode delle Diecimila Ere"}.get(n)
        if t and state.grant_title(conn, t):
            out.append(f"✧ Nuovo titolo: «{t}» ✧")
    _save(conn, d)
    return out


def describe(conn, player) -> str:
    d = get(conn)
    day = tick_mod.get_tick(conn) // 120
    left = max(0, ERA_DAYS - (day - d["start"]))
    lines = [f"🌗 {ERAS[d['key']][0]} (l'era n.{d['n']}) — la prossima tra {left} giorni"]
    m = ERAS[d["key"]][1]
    if m != 1.0:
        lines.append(f"  Coltivazione ×{m:.2f}")
    if d["key"] == "calamita":
        lines.append(f"  ☠ {d['calamity']}: {d['waves']} ondate da respingere ('calamita').")
    else:
        nxt = 4 - d["n"] % 4
        lines.append(f"  La prossima calamità tra {nxt} ere. Calamità superate: "
                     f"{state.get_int(conn, 'world_calamities_stopped', 0)}.")
    al = allies(conn, player.id)
    lines.append("  I tuoi alleati per la calamità: " + (", ".join(al) if al else "nessuno, per ora."))
    return "\n".join(lines)
