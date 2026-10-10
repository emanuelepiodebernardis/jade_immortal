"""
PILOTA AUTOMATICO — lo «stato etereo»: il personaggio vive da solo le parti monotone.

Prima di partire imposti come deve comportarsi; poi i giorni scorrono da soli, con i
comandi veri del gioco (le stesse regole, gli stessi rischi). Il pilota si FERMA da solo
quando succede qualcosa che vale la pena giocare.

  auto                                  la configurazione attuale
  auto <giorni>                         parte (massimo 60 giorni per volta; Ctrl+C lo interrompe)
  auto imposta attivita coltiva=3 dao=2 caccia=2 raccolta=1 lavoro=1 insegna=1
                                        quanto spazio dare a ogni attività (0 = mai)
  auto imposta bersagli <nessuno|bestie|ricercati|deboli|tutti>
                                        chi attaccare quando lo incontri (mai chi è più forte)
  auto imposta assorbi <si|no>          (Divoratore) divora i caduti
  auto imposta loot <si|no>             raccogli tutto il bottino
  auto imposta oggetti <si|no>          usa pillole ed essenze raccolte
  auto imposta sfonda <si|no>           tenta da solo lo sfondamento quando sei al colmo (rischioso!)
  auto imposta condotta <virtuosa|prudente|opportunista|spietata>
                                        come comportarti negli incontri casuali minori
  auto imposta fermati <reame|assemblea|asta|invasione|elemento> <si|no>
                                        quali occasioni meritano una sosta (le altre restano nel resoconto)

Si ferma per: capitoli della storia, maestri segreti, scene importanti (nemesi, demone
interiore, emissari, fratelli in pericolo…), reami segreti, Grande Assemblea, aste,
tornei e sfide di setta imminenti, invasioni di mostri, guerre tra sette, assalti alla tua
setta, sfondamento pronto, ferite gravi, vecchiaia vicina, morte.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "auto_cfg"
MAX_DAYS = 60
ACTIVITIES = ["coltiva", "dao", "caccia", "raccolta", "lavoro", "insegna"]
TARGETS = ["nessuno", "bestie", "ricercati", "deboli", "tutti"]
CONDUCTS = ["virtuosa", "prudente", "opportunista", "spietata"]
_WILD = ("mountain", "ruin", "forbidden_zone")
DEFAULT = {"attivita": {"coltiva": 3, "dao": 2, "caccia": 2, "raccolta": 1, "lavoro": 1, "insegna": 1},
           "bersagli": "bestie", "assorbi": False, "loot": True, "oggetti": True, "sfonda": False,
           "condotta": "prudente",
           "fermate": {"reame": True, "assemblea": True, "asta": False, "invasione": True, "elemento": True}}
_STOP_KEY = {"realm": "reame", "assembly": "assemblea", "auction": "asta", "event": "invasione",
             "celestial": "elemento"}


# ============================================================
# Configurazione
# ============================================================

def config(conn) -> dict:
    c = dict(DEFAULT)
    c.update(state.get_json(conn, KEY, {}) or {})
    c["attivita"] = {**DEFAULT["attivita"], **(c.get("attivita") or {})}
    c["fermate"] = {**DEFAULT["fermate"], **(c.get("fermate") or {})}
    return c


def _yes(v: str) -> bool | None:
    v = v.lower()
    if v in ("si", "sì", "yes", "on", "1", "true"):
        return True
    if v in ("no", "off", "0", "false"):
        return False
    return None


def configure(conn, arg: str) -> str:
    c = config(conn)
    parts = arg.split()
    if not parts:
        return describe(conn)
    what, rest = parts[0].lower(), parts[1:]
    if what in ("attivita", "attività", "attivitá"):
        for tok in rest:
            k, _, v = tok.partition("=")
            k = k.lower()
            if k in ACTIVITIES and v.isdigit():
                c["attivita"][k] = max(0, min(9, int(v)))
            else:
                return f"Formato: auto imposta attivita coltiva=3 dao=2 ... (attività: {', '.join(ACTIVITIES)})"
    elif what == "bersagli" and rest and rest[0].lower() in TARGETS:
        c["bersagli"] = rest[0].lower()
    elif what == "condotta" and rest and rest[0].lower() in CONDUCTS:
        c["condotta"] = rest[0].lower()
    elif what in ("assorbi", "loot", "oggetti", "sfonda") and rest and _yes(rest[0]) is not None:
        c[what] = _yes(rest[0])
    elif what in ("fermati", "fermata", "stop") and len(rest) >= 2 and rest[0].lower() in DEFAULT["fermate"] \
            and _yes(rest[1]) is not None:
        c["fermate"][rest[0].lower()] = _yes(rest[1])
    else:
        return ("Non ho capito. Esempi: 'auto imposta bersagli bestie', 'auto imposta condotta virtuosa', "
                "'auto imposta assorbi si', 'auto imposta attivita coltiva=4 caccia=0'.")
    state.set_json(conn, KEY, c)
    return "Impostato.\n" + describe(conn)


def describe(conn) -> str:
    c = config(conn)
    act = ", ".join(f"{k} {v}" for k, v in c["attivita"].items())
    return ("✧ PILOTA AUTOMATICO (stato etereo) ✧\n"
            f"  Attività (peso): {act}\n"
            f"  Bersagli: {c['bersagli']}   Assorbi: {'sì' if c['assorbi'] else 'no'}   "
            f"Bottino: {'sì' if c['loot'] else 'no'}   Usa oggetti: {'sì' if c['oggetti'] else 'no'}   "
            f"Sfonda da solo: {'sì' if c['sfonda'] else 'no'}\n"
            f"  Condotta negli incontri: {c['condotta']}\n"
            "  Si ferma anche per: " + ", ".join(f"{k} {'sì' if v else 'no'}" for k, v in c["fermate"].items())
            + " ('auto imposta fermati asta si')\n"
            "Avvia con 'auto <giorni>' (max 60). Si ferma da solo davanti agli eventi importanti; "
            "Ctrl+C per interromperlo. 'auto imposta ...' per cambiare (vedi 'help auto').")


# ============================================================
# Incontri casuali: scelta secondo la condotta
# ============================================================

def _score(ch: dict, conduct: str) -> float:
    eff = ch.get("effects") or ch.get("success") or {}
    fail = ch.get("failure") or {}
    karma = eff.get("karma", 0)
    infamy = eff.get("infamy", 0)
    fame = eff.get("fame", 0)
    gains = max(0, eff.get("stones", 0)) + 60 * float(eff.get("cultivation_progress", 0) or 0) \
        + (25 if (eff.get("item") or eff.get("learn_technique") or eff.get("dao_gain")) else 0) \
        + 4 * sum(eff.get(k, 0) for k in ("grow_strength", "grow_vitality", "grow_soul"))
    cost = max(0, -eff.get("stones", 0))
    attack = bool(ch.get("command") or eff.get("command") or fail.get("command"))
    risky = "check" in ch
    injury = eff.get("injury", 0) + fail.get("injury", 0)
    if conduct == "virtuosa":
        return karma * 1.0 + fame * 2 - infamy * 3 + gains * 0.1 - cost * 0.02
    if conduct == "prudente":
        return gains * 0.3 + karma * 0.1 - 25 * risky - 40 * attack - 6 * injury - cost * 0.05
    if conduct == "opportunista":
        return gains * 1.0 + karma * 0.05 - infamy * 0.5 - 15 * attack - 3 * injury - cost * 0.2
    return gains * 1.0 - karma * 0.4 + infamy * 0.5 + 15 * attack - cost * 0.2   # spietata


def pick_choice(scene: dict, conduct: str) -> int:
    chs = scene.get("choices", [])
    if not chs:
        return 1
    best = max(range(len(chs)), key=lambda i: _score(chs[i], conduct))
    return best + 1


def _random_keys() -> set[str]:
    from engine.systems.encounter_data import ENCOUNTERS
    return {e["key"] for e in ENCOUNTERS}


# ============================================================
# Azioni
# ============================================================

def _loc_type(conn, loc_id) -> str:
    r = conn.execute("SELECT location_type FROM locations WHERE id=?;", (loc_id,)).fetchone()
    return r["location_type"] if r else ""


def _step_to_wild(conn, player) -> str | None:
    from collections import deque
    start = player.location_id
    seen = {start}
    q = deque([(start, None)])
    while q:
        cur, first = q.popleft()
        for r in conn.execute("SELECT direction, to_location_id FROM location_connections "
                              "WHERE from_location_id=?;", (cur,)).fetchall():
            nxt = r["to_location_id"]
            if nxt in seen:
                continue
            fd = first or r["direction"]
            if _loc_type(conn, nxt) in _WILD:
                return fd
            seen.add(nxt)
            q.append((nxt, fd))
    return None


def _wander(conn, player, rng) -> str | None:
    ex = entities.get_exits(conn, player.location_id)
    if not ex:
        return None
    wild = [d for d, lid in ex.items() if _loc_type(conn, lid) in _WILD]
    return f"move {rng.choice(sorted(wild or ex))}"


def _targets(conn, player, mode: str) -> list[str]:
    from engine.systems import perception, bonds
    if mode == "nessuno":
        return []
    prot = bonds.protected_ids(conn, player.id)
    out = []
    rows = conn.execute("SELECT id, name, COALESCE(kind,'human') AS kind FROM npcs WHERE location_id=? "
                        "AND status='alive';", (player.location_id,)).fetchall()
    outlaws = {r["npc_id"] for r in conn.execute("SELECT npc_id FROM outlaws WHERE resolved=0;")}
    for r in rows:
        if r["id"] in prot:
            continue
        rel = perception.relative_strength(conn, player.id, r["id"])
        if "più forte" in rel:
            continue                                   # mai chi è più forte
        if mode != "tutti" and "più debole" not in rel:
            continue                                   # alla pari solo se hai scelto "tutti"
        human = r["kind"] == "human"
        if mode == "bestie" and human:
            continue
        if mode == "ricercati" and (human and r["id"] not in outlaws):
            continue
        out.append(r["name"])
    return out


def _best_recipe(conn, pid: int) -> int | None:
    from engine.systems import professions
    if not professions.profession(conn, pid):
        return None
    lv = professions.level(conn, pid)
    best = None
    for i, r in enumerate(professions.recipes_for(conn, pid), 1):
        _p, need, _name, cost, _make = r
        if lv >= need and all(professions.material(conn, pid, k) >= v for k, v in cost.items()):
            best = i
    return best


def _meditations_today(conn) -> int:
    from engine.systems import training
    try:
        return training.sessions_today(conn, tick_mod.get_tick(conn), "player", 1)
    except AttributeError:
        return 0


def _choose_action(conn, player, cfg: dict, rng: random.Random) -> str | None:
    from engine.systems import dao_training, loot, absorption, own_sect
    from engine.core import entities as ents
    # prima ciò che è a terra
    if cfg["loot"] and loot.drops_in_location(conn, player.location_id):
        return "loot"
    if cfg["assorbi"] and ents.dead_npcs_in_location(conn, player.location_id) \
            and absorption.can_absorb(conn, player.id):
        return "absorb all"
    inj = conn.execute("SELECT COALESCE(SUM(severity),0) s FROM injuries WHERE character_type='player' "
                       "AND character_id=? AND healed=0;", (player.id,)).fetchone()["s"]
    from engine.simulation import cultivation
    rec = cultivation.get_record(conn, "player", player.id)
    if cfg.get("sfonda") and rec and (rec["stage"] or 1) >= 10 and rec["progress"] >= 1.0 and inj == 0:
        return "breakthrough"
    tg = _targets(conn, player, cfg["bersagli"]) if inj < 4 else []
    weights = dict(cfg["attivita"])
    if _meditations_today(conn) >= 4:              # sfinito: niente più meditazione oggi
        weights["coltiva"] = weights["dao"] = 0
    if tg and weights.get("caccia", 0) > 0 and rng.random() < 0.7:
        return f"attack {tg[0]}"
    acts = [a for a in ACTIVITIES if weights.get(a, 0) > 0]
    if not acts:
        return None                                 # giornata finita: si dorme
    act = rng.choices(acts, weights=[weights[a] for a in acts])[0]
    wild_here = _loc_type(conn, player.location_id) in _WILD
    if act == "coltiva":
        return "cultivate"
    if act == "dao":
        rows = dao_training.trainable_daos(conn, player.id)
        return f"comprehend {rows[0]['dao_key']}" if rows else "cultivate"
    if act == "caccia":
        if cfg["bersagli"] == "nessuno":
            return "cultivate"
        if not wild_here:
            st = _step_to_wild(conn, player)
            return f"move {st}" if st else "cultivate"
        return _wander(conn, player, rng) or "cultivate"
    if act == "raccolta":
        if wild_here:
            return "gather"
        st = _step_to_wild(conn, player)
        return f"move {st}" if st else "cultivate"
    if act == "lavoro":
        r = _best_recipe(conn, player.id)
        if r:
            return f"craft {r}"
        return "gather" if wild_here else "cultivate"
    if act == "insegna":
        for d in own_sect.disciples(conn, player.id):
            if d["location_id"] == player.location_id and \
                    state.get_int(conn, f"taught_{d['npc_id']}", -1) != tick_mod.get_tick(conn) // 120:
                return f"insegna {d['name'].split()[0]}"
        return "cultivate"
    return "cultivate"


# ============================================================
# Interruzioni
# ============================================================

def _snapshot(conn, pid: int) -> dict:
    from engine.systems import secret_realms, assembly, auction, own_sect, world_events, sect_war
    from engine.systems import sects
    m = sects.get_membership(conn, pid)
    war = sect_war.active_war(conn)
    return {"realm": bool(secret_realms.current(conn)),
            "assembly": bool(assembly.current(conn)),
            "auction": bool(_auction_open(conn)),
            "threat": bool((own_sect.get(conn) or {}).get("threat")),
            "sworn": bool(state.get_json(conn, "sworn_request")),
            "event": _near_event(conn, pid),
            "war": bool(war and m and m["faction_id"] in (war["player_faction_id"], war["enemy_faction_id"]))
            if war and "player_faction_id" in war.keys() else bool(war),
            "life": state.get_int(conn, "life_warned", 0),
            "celestial": bool(_celestial(conn)),
            "family": bool((_family(conn) or {}).get("threat")),
            "legacy": bool((_legacy(conn) or {}).get("holder"))}


def _celestial(conn):
    from engine.systems import celestial_elements
    return celestial_elements.current_event(conn)


def _family(conn):
    from engine.systems import family
    return family.get(conn)


def _legacy(conn):
    from engine.systems import lost_legacy
    return lost_legacy.get(conn)


def _near_event(conn, pid: int):
    """Id dell'invasione in corso se è qui o accanto, o colpisce casa tua; altrimenti None."""
    from engine.systems import world_events, cave_abode, own_sect
    ev = world_events.active_event(conn)
    if not ev:
        return None
    p = entities.get_player(conn, pid)
    homes = {x for x in ((cave_abode.get(conn, pid) or {}).get("loc"),
                         (own_sect.get(conn) or {}).get("loc")) if x}
    if ev["location_id"] in homes:
        return ev["id"]
    d = cave_abode._distance(conn, p.location_id, ev["location_id"]) if p.location_id else None
    return ev["id"] if d is not None and d <= 1 else None


def _auction_open(conn) -> bool:
    try:
        from engine.systems import auction
        return bool(auction.current(conn))
    except Exception:
        return False


def _stop_reason(conn, player, before: dict, rng_keys: set[str], cfg: dict | None = None) -> str | None:
    from engine.systems import encounters, sects, sect_life, training
    from engine.simulation import cultivation
    p = entities.get_player(conn, player.id)
    if p.status != "alive":
        return "la tua vita si è interrotta"
    sc = encounters.pending(conn)
    if sc and sc.get("key") not in rng_keys:
        return f"un evento importante: «{sc.get('title', 'incontro')}»"
    now = _snapshot(conn, player.id)
    labels = {"realm": "si è aperto un reame segreto", "assembly": "è convocata la Grande Assemblea",
              "auction": "ha aperto la casa d'aste", "threat": "la tua setta è sotto assalto",
              "sworn": "un fratello giurato chiede aiuto", "event": "un'invasione di mostri minaccia questa regione",
              "war": "è scoppiata una guerra tra sette", "life": "la vecchiaia si avvicina",
              "celestial": "è nato un Elemento Celeste", "family": "la tua famiglia è minacciata",
              "legacy": "un frammento del tuo retaggio si è mostrato"}
    stops = (cfg or DEFAULT)["fermate"]
    for k, lab in labels.items():
        if k in _STOP_KEY and not stops.get(_STOP_KEY[k], True):
            continue
        if now[k] and (not before[k] or (k in ("life", "event") and now[k] != before[k])):
            return lab
    m = sects.get_membership(conn, p.id)
    if m:
        t = tick_mod.get_tick(conn)
        nxt = sect_life.next_event(conn, t, p.id)
        if nxt and nxt["fire_tick"] - t <= training.DAY_TICKS:
            return "un torneo o una sfida di setta è imminente"
    rec = cultivation.get_record(conn, "player", p.id)
    if rec and (rec["stage"] or 1) >= 10 and rec["progress"] >= 1.0 and not (cfg or DEFAULT).get("sfonda"):
        return "sei pronto allo sfondamento ('breakthrough')"
    inj = conn.execute("SELECT COALESCE(SUM(severity),0) s FROM injuries WHERE character_type='player' "
                       "AND character_id=? AND healed=0;", (p.id,)).fetchone()["s"]
    if inj >= 9:
        return "le tue ferite sono gravi"
    return None


# ============================================================
# Esecuzione
# ============================================================

def _stats(conn, pid: int) -> dict:
    from engine.systems import sects, professions, lifespan, reputation
    from engine.simulation import cultivation
    rec = cultivation.get_record(conn, "player", pid)
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    return {"lvl": tier * 100 + (rec["stage"] or 1) if rec else 0,
            "label": cultivation.realm_label(conn, "player", pid),
            "kills": state.get_int(conn, "kills_total", 0),
            "stones": sects.get_resource(conn, "pietre_spirituali", pid),
            "prof": professions.level(conn, pid) if professions.profession(conn, pid) else 0,
            "dao": conn.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos "
                                "WHERE character_type='player' AND character_id=?;", (pid,)).fetchone()["s"],
            "age": lifespan.age_years(conn, pid),
            "fame": reputation.get(conn, pid)["fame"],
            "titles": len(state.titles(conn)),
            "items": conn.execute("SELECT COALESCE(SUM(quantity),0) s FROM inventories "
                                  "WHERE owner_type='player' AND owner_id=?;", (pid,)).fetchone()["s"]}


_NOTABLE = ("✦", "✧", "⚠", "☠", "✝", "🩸", "★", "Avanzi", "Nuovo titolo", "ILLUMINAZIONE")


def run(conn, player, days: int) -> str:
    from engine.cli import loop
    from engine.systems import encounters, reports
    if encounters.pending(conn):
        return "C'è una scena in sospeso: risolvila prima di entrare nello stato etereo."
    days = max(1, min(MAX_DAYS, days))
    cfg = config(conn)
    rng_keys = _random_keys()
    s0 = _stats(conn, player.id)
    before = _snapshot(conn, player.id)
    t0 = tick_mod.get_tick(conn)
    notes: list[str] = []
    reason = None
    done_days = 0
    rng = random.Random(t0 * 131 + player.id)
    try:
        for _d in range(days):
            day = tick_mod.get_tick(conn) // 120
            steps = 0
            while tick_mod.get_tick(conn) // 120 == day and steps < 14:
                p = entities.get_player(conn, player.id)
                sc = encounters.pending(conn)
                if sc:
                    if sc.get("key") in rng_keys:
                        n = pick_choice(sc, cfg["condotta"])
                        out = loop.dispatch(conn, str(n), allow_nl=False) or ""
                        notes += [ln for ln in out.splitlines() if ln.startswith("»")]
                        continue
                    reason = f"un evento importante: «{sc.get('title', 'incontro')}»"
                    break
                cmd = _choose_action(conn, p, cfg, rng)
                if cmd is None:
                    break
                out = loop.dispatch(conn, cmd, allow_nl=False) or ""
                notes += [ln.strip() for ln in out.splitlines() if any(k in ln for k in _NOTABLE)]
                steps += 1
                reason = _stop_reason(conn, player, before, rng_keys, cfg)
                if reason:
                    break
            if reason:
                break
            p = entities.get_player(conn, player.id)
            if tick_mod.get_tick(conn) // 120 == day:
                loop.dispatch(conn, "sleep", allow_nl=False)
            banner = loop._day_banner(conn, p) or ""
            notes += [ln.strip() for ln in banner.splitlines() if any(k in ln for k in _NOTABLE)]
            for rep in reports.drain(conn, player.id):
                notes += [ln.strip() for ln in rep.splitlines()[:3]]
            if cfg["oggetti"] and _usable_items(conn, player.id):
                out = loop.dispatch(conn, "use all", allow_nl=False) or ""
                notes += [ln.strip() for ln in out.splitlines() if any(k in ln for k in _NOTABLE)]
            done_days += 1
            conn.commit()
            reason = _stop_reason(conn, player, before, rng_keys, cfg)
            if reason:
                break
    except KeyboardInterrupt:
        reason = "interrotto da te"
    return _report(conn, player.id, s0, done_days, reason, notes)


def _usable_items(conn, pid: int) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM inventories v JOIN items i ON i.id=v.item_id WHERE v.owner_type='player' "
        "AND v.owner_id=? AND v.quantity>0 AND i.item_type IN ('pillola','essenza') LIMIT 1;",
        (pid,)).fetchone())


def _report(conn, pid: int, s0: dict, days: int, reason: str | None, notes: list[str]) -> str:
    s1 = _stats(conn, pid)
    lines = [f"✧ STATO ETEREO — {days} giorn{'o' if days == 1 else 'i'} trascors{'o' if days == 1 else 'i'} ✧"]
    lines.append(f"  Coltivazione: {s0['label']} → {s1['label']}")
    d = {"Vite tolte": s1["kills"] - s0["kills"], "Pietre spirituali": s1["stones"] - s0["stones"],
         "Comprensione dei Dao": s1["dao"] - s0["dao"], "Livelli dell'arte": s1["prof"] - s0["prof"],
         "Fama": s1["fame"] - s0["fame"], "Oggetti nello zaino": s1["items"] - s0["items"],
         "Nuovi titoli": s1["titles"] - s0["titles"]}
    for k, v in d.items():
        if v:
            lines.append(f"  {k}: {v:+d}")
    lines.append(f"  Età: {s0['age']:.1f} → {s1['age']:.1f} anni")
    seen = []
    for n in notes:
        if n and n not in seen:
            seen.append(n)
    if seen:
        lines.append("Momenti salienti:")
        lines += ["  " + n for n in seen[-15:]]
    if reason:
        lines.append(f"⏸ Il pilota si ferma: {reason}.")
    else:
        lines.append("Il periodo stabilito è trascorso. 'auto <giorni>' per riprendere.")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    a = arg.strip()
    if not a:
        return describe(conn)
    parts = a.split(maxsplit=1)
    if parts[0].lower() in ("imposta", "set", "config"):
        return configure(conn, parts[1] if len(parts) > 1 else "")
    if parts[0].isdigit():
        return run(conn, player, int(parts[0]))
    return describe(conn)
