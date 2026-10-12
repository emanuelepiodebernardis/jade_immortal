"""
REGNI E IMPERI — la politica dei mortali (e degli immortali che li governano).

Ogni territorio del mondo è un REGNO con un sovrano, una capitale e dei principi che si
contendono la successione. Dai tempi della tua ascesa al quarto regno, le corti si
accorgono di te.

  regni                     i regni del mondo: sovrani, principi, guerre, il tuo favore
  corte                     (nella capitale) il tuo rango a corte, il principe che sostieni
  sostieni <principe>       ti schieri con un principe nella successione
  tributo <pietre>          doni alla corte del regno in cui sei: il favore cresce
  guerra_regni              (durante una guerra) scendi in campo per il tuo regno

Il FAVORE cresce anche abbattendo banditi, ricercati e mostri nelle terre del regno.
Ranghi (senza fine): Cavaliere · Generale · Consigliere · Duca · Principe Reggente · Re… e
oltre ancora, Re dei Re di N regni. Ogni rango porta uno stipendio.
Quando un sovrano muore si apre la SUCCESSIONE: vince il principe più sostenuto — e chi è
abbastanza forte può prendersi il trono da solo, fondando la propria DINASTIA.
Di tanto in tanto due regni si fanno la GUERRA.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "kingdoms"
RANKS = [(0, "Suddito"), (50, "Cavaliere"), (200, "Generale"), (500, "Consigliere"), (1500, "Duca"),
         (4000, "Principe Reggente")]
_PREFIX = ["Regno di", "Impero di", "Principato di", "Dominio di"]


def all_k(conn) -> dict:
    return state.get_json(conn, KEY, {}) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def ensure(conn, rng: random.Random | None = None) -> dict:
    """Crea i regni mancanti (uno per territorio)."""
    from engine.systems import npc_factory
    d = all_k(conn)
    rng = rng or random.Random(4242)
    changed = False
    for r in conn.execute("SELECT id, name FROM regions WHERE region_type='territory' OR parent_region_id IS NOT NULL;"):
        if str(r["id"]) in d:
            continue
        cities = [x["id"] for x in conn.execute("SELECT id FROM locations WHERE region_id=? AND location_type='city';",
                                                 (r["id"],))]
        locs = cities or [x["id"] for x in conn.execute("SELECT id FROM locations WHERE region_id=?;", (r["id"],))]
        if not locs:
            continue
        cap = locs[0]
        base = r["name"].replace("Territorio ", "")
        tier = max(2, conn.execute("SELECT MAX(r2.tier) t FROM npcs n JOIN cultivation_realms r2 ON r2.id=n.realm_id "
                                   "WHERE n.location_id IN (SELECT id FROM locations WHERE region_id=?);",
                                   (r["id"],)).fetchone()["t"] or 2)
        king = npc_factory.spawn(conn, rng, archetype="anziano", location_id=cap, tier=tier + 1, stage=5,
                                 traits={"pride": 80, "ambition": 70})
        princes = [npc_factory.spawn(conn, rng, archetype="discepolo", location_id=cap, tier=max(1, tier - 1),
                                     stage=rng.randint(3, 9), traits={"ambition": 90}) for _ in range(2)]
        d[str(r["id"])] = {"name": f"{rng.choice(_PREFIX)} {base}", "capital": cap, "king": king,
                           "princes": princes, "favor": 0, "backed": None, "ruler_player": False,
                           "war": None, "kings_lost": 0}
        changed = True
    if changed:
        _save(conn, d)
    return d


def kingdom_of(conn, location_id) -> tuple[str, dict] | None:
    r = conn.execute("SELECT region_id FROM locations WHERE id=?;", (location_id,)).fetchone()
    if not r:
        return None
    d = all_k(conn)
    k = d.get(str(r["region_id"]))
    return (str(r["region_id"]), k) if k else None


def rank_of(favor: int) -> str:
    name = "Suddito"
    for th, nm in RANKS:
        if favor >= th:
            name = nm
    if favor >= 10000:
        name = f"Re dei Re ({favor // 10000}°)"
    return name


def _name(conn, nid) -> str:
    r = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (nid,)).fetchone()
    return (r["name"] + ("" if r["status"] == "alive" else " ✝")) if r else "?"


def add_favor(conn, region_key: str, n: int) -> list[str]:
    d = all_k(conn)
    k = d.get(region_key)
    if not k:
        return []
    before = rank_of(k["favor"])
    k["favor"] = max(0, k["favor"] + n)
    _save(conn, d)
    after = rank_of(k["favor"])
    if after != before and n > 0:
        state.grant_title(conn, f"{after} del {k['name']}")
        return [f"✦ Il {k['name']} ti nomina {after}!"]
    return []


def on_kill(conn, player, npc_id: int) -> list[str]:
    kk = kingdom_of(conn, player.location_id)
    if not kk:
        return []
    r = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    outlaw = conn.execute("SELECT 1 FROM outlaws WHERE npc_id=?;", (npc_id,)).fetchone()
    if outlaw or (r and r["kind"] in ("beast", "demon")):
        return add_favor(conn, kk[0], 3 if outlaw else 1)
    return []


def tribute(conn, player, arg: str) -> str:
    from engine.systems import sects
    kk = kingdom_of(conn, player.location_id)
    if not kk:
        return "Qui non governa nessun regno."
    n = int(arg) if arg.strip().isdigit() else 0
    if n <= 0 or sects.get_resource(conn, "pietre_spirituali", player.id) < n:
        return "Usa: tributo <pietre>."
    sects.grant_resource(conn, "pietre_spirituali", -n, player.id)
    return "\n".join([f"Offri {n} pietre alla corte del {kk[1]['name']}."] + add_favor(conn, kk[0], n // 10))


def back(conn, player, arg: str) -> str:
    kk = kingdom_of(conn, player.location_id)
    if not kk:
        return "Qui non governa nessun regno."
    rk, k = kk
    pick = next((p for p in k["princes"] if arg.strip().lower() in _name(conn, p).lower()), None)
    if not pick:
        return "Quale principe? " + ", ".join(_name(conn, p) for p in k["princes"])
    d = all_k(conn)
    d[rk]["backed"] = pick
    _save(conn, d)
    from engine.systems import master_plot
    master_plot.record_choice(conn, f"principe_{rk}", pick)
    return f"Ti schieri con {_name(conn, pick)}. Se salirà al trono, si ricorderà di te — e così i suoi nemici."


def court(conn, player) -> str:
    kk = kingdom_of(conn, player.location_id)
    if not kk:
        return "Qui non governa nessun regno."
    rk, k = kk
    lines = [f"👑 {k['name']} — sovrano: {'TU' if k['ruler_player'] else _name(conn, k['king'])}",
             f"  Il tuo rango: {rank_of(k['favor'])} (favore {k['favor']})",
             "  Principi: " + ", ".join(_name(conn, p) + (" ← sostenuto da te" if p == k["backed"] else "")
                                       for p in k["princes"])]
    if k.get("war"):
        lines.append(f"  ⚔ In guerra contro il {k['war']['enemy']}! ('guerra_regni')")
    return "\n".join(lines)


def describe(conn, player) -> str:
    d = ensure(conn)
    if not d:
        return "Il mondo non conosce ancora regni."
    lines = ["👑 I REGNI DEL MONDO"]
    for rk, k in d.items():
        cap = conn.execute("SELECT name FROM locations WHERE id=?;", (k["capital"],)).fetchone()["name"]
        lines.append(f"  · {k['name']} — capitale {cap} — sovrano {'TU' if k['ruler_player'] else _name(conn, k['king'])}"
                     f" — il tuo rango: {rank_of(k['favor'])}" + (f" — ⚔ guerra col {k['war']['enemy']}" if k.get("war") else ""))
    return "\n".join(lines)


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import sects, npc_factory
    from engine.simulation import cultivation
    if (cultivation.realm_tier(conn, "player", player.id) or 1) < 2:
        return []
    d = ensure(conn, rng)
    out = []
    day = t // 120
    for rk, k in d.items():
        # stipendio
        idx = sum(1 for th, _n in RANKS if k["favor"] >= th) - 1
        if idx > 0 and day % 5 == 0:
            sects.grant_resource(conn, "pietre_spirituali", 20 * idx * idx, player.id)
        if k["ruler_player"] and day % 5 == 0:
            sects.grant_resource(conn, "pietre_spirituali", 300, player.id)
        # successione
        if not k["ruler_player"] and rng.random() < 0.006:
            out += _succession(conn, rng, player, rk, d)
        # guerre
        if k.get("war") and day > k["war"]["until"]:
            k["war"] = None
        elif not k.get("war") and len(d) > 1 and rng.random() < 0.004:
            other = rng.choice([x for x in d if x != rk])
            k["war"] = {"enemy": d[other]["name"], "until": day + 6, "fought": False}
            if k["favor"] >= 50:
                out.append(f"⚔ Il {k['name']} entra in guerra contro il {d[other]['name']}: il tuo regno ti chiama "
                           "('guerra_regni' nella sua terra).")
    _save(conn, d)
    return out


def _succession(conn, rng, player, rk, d) -> list[str]:
    from engine.systems import npc_factory
    k = d[rk]
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (k["king"],))
    alive = [p for p in k["princes"] if conn.execute("SELECT status FROM npcs WHERE id=?;", (p,)).fetchone()["status"] == "alive"]
    if not alive:
        alive = [npc_factory.spawn(conn, rng, archetype="discepolo", location_id=k["capital"], tier=3)]
    win = k["backed"] if k["backed"] in alive and rng.random() < 0.5 + min(0.4, k["favor"] / 2000) else rng.choice(alive)
    k["king"] = win
    k["princes"] = [p for p in alive if p != win] + [npc_factory.spawn(conn, rng, archetype="discepolo",
                                                                       location_id=k["capital"], tier=2)]
    out = [f"👑 Il sovrano del {k['name']} è morto. Dopo la lotta per la successione, sale al trono {_name(conn, win)}."]
    if win == k["backed"]:
        out += [f"Il principe che sostenevi è re: si ricorda di te."] + add_favor(conn, rk, 200)
    elif k["backed"]:
        k["favor"] = k["favor"] // 2
        out.append("Hai sostenuto il principe sbagliato: a corte il tuo nome ora pesa la metà.")
    k["backed"] = None
    return out


def seize(conn, player) -> str:
    """Prendere il trono con la forza (serve essere Duca e più forti del sovrano)."""
    from engine.systems import perception
    kk = kingdom_of(conn, player.location_id)
    if not kk:
        return "Qui non governa nessun regno."
    rk, k = kk
    if k["ruler_player"]:
        return "Il trono è già tuo."
    if k["favor"] < 1500:
        return "Nessuno ti seguirebbe: serve almeno il rango di Duca."
    if perception.strength_ratio(conn, player.id, k["king"]) < 1.2:
        return "Il sovrano è ancora troppo forte per te."
    d = all_k(conn)
    d[rk]["ruler_player"] = True
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (k["king"],))
    _save(conn, d)
    state.grant_title(conn, "Fondatore di Dinastia")
    from engine.systems import master_plot
    master_plot.record_choice(conn, f"trono_{rk}", "preso")
    return (f"Entri nella sala del trono e nessuno osa fermarti. Il {k['name']} ha un nuovo sovrano: TU. "
            "✧ Nuovo titolo: «Fondatore di Dinastia» ✧ (il regno ti versa tributi)")


def war(conn, player) -> str:
    from engine.systems import encounters, npc_factory
    from engine.simulation import cultivation
    kk = kingdom_of(conn, player.location_id)
    if not kk or not kk[1].get("war"):
        return "Il regno in cui ti trovi non è in guerra."
    rk, k = kk
    if k["war"].get("fought"):
        return "Hai già combattuto in questa guerra."
    d = all_k(conn)
    d[rk]["war"]["fought"] = True
    _save(conn, d)
    rng = random.Random(tick_mod.get_tick(conn))
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    sc = {"key": "guerra_regni", "title": f"Guerra: {k['name']} contro {k['war']['enemy']}", "event_type": "combat",
          "text": "Sul campo di battaglia, il generale nemico {npc} guida la carica.",
          "spawn": {"archetype": "guardia", "tier_offset": 0, "stage": 7},
          "choices": [{"label": "Lo affronti in duello davanti ai due eserciti",
                       "effects": {"kingdom_favor": [rk, 80], "fame": 5}, "command": "attack {npc}"},
                      {"label": "Guidi la cavalleria sul fianco", "check": {"stat": "istinto", "dc": 60 + 2 * tier},
                       "success": {"kingdom_favor": [rk, 60], "stones": 50 * tier, "npc_leaves": True,
                                   "text": "Il fianco nemico crolla: la battaglia è vinta."},
                       "failure": {"injury": 4, "kingdom_favor": [rk, 10], "text": "La carica si infrange."}}]}
    from engine.systems import dominion
    v_bonus, v_names = dominion.war_support(conn)
    if v_names:
        sc["choices"].append({"label": f"Mandi in prima linea le tue sette vassalle ({', '.join(v_names[:3])})",
                              "effects": {"kingdom_favor": [rk, 40 + v_bonus], "fame": 4, "npc_leaves": True,
                                          "text": "Le bandiere delle tue vassalle travolgono il fronte nemico."}})
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    return encounters.start_scene(conn, player, sc, force=True) or ""
