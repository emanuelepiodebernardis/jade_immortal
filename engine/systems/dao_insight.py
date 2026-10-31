"""
LE INTUIZIONI DEL DAO (Aggiornamento 77) — si impara anche guardando e cercando.

  · SCONTRARSI CON CHI È PIÙ FORTE: se il nemico ha un regno più alto o un Dao più profondo del tuo, a volte
    vedi COME lo usa. Se pratichi quel Dao, la tua comprensione fa un salto; se non lo pratichi, ne ricavi uno
    SCORCIO (tre scorci aprono il Dao, sei per i Dao superiori). Se lui usa due Dao che insieme formano una
    fusione, ne ricavi l'INTUIZIONE (soglie −20%, nessun rischio di conflitto).
  · I REPERTI: tra rovine, grotte, montagne e zone proibite i maestri del passato hanno lasciato stele,
    rotoli, spade conficcate nella roccia. 'reperti' li cerca (una volta per luogo ogni trenta giorni):
    approfondiscono un Dao che pratichi, danno scorci di vie nuove o intuizioni sulle fusioni.

Tutto data-driven: aggiungere un reperto = una riga in RELICS; un Dao vicino = una voce in NEAR.
"""

from __future__ import annotations

import random

STRONG_CHANCE = 0.4            # probabilità di «vedere» qualcosa in uno scontro con chi è più forte
GLIMPSES = 3                   # scorci per aprire un Dao
GLIMPSES_HIGH = 6              # … superiore, profondo o proibito
RELIC_DAYS = 30
RELIC_PLACES = ("ruin", "cave", "mountain", "forbidden_zone")

# un Dao base che vedi usare bene ti fa intravedere anche le vie vicine
NEAR = {"acqua": ["ghiaccio", "nebbia"], "terra": ["gravita", "formazioni"], "metallo": ["magnetismo", "forgia"],
        "fulmine": ["magnetismo", "suono"], "vento": ["suono", "nebbia"], "legno": ["veleno", "stagioni"],
        "fuoco": ["alchimia", "forgia"], "spada": ["pugnale", "volonta"], "sciabola": ["falce"], "lancia": ["catena"],
        "bastone": ["scudo"], "pugno": ["martello"], "arco": ["sguardo"], "corpo": ["scudo", "longevita"],
        "anima": ["memoria", "sguardo", "volonta"], "destino": ["numeri"], "spazio": ["confine", "mondo"],
        "tempo": ["ciclo", "memoria"], "massacro": ["falce"], "vita_morte": ["longevita"], "luce": ["specchio"],
        "illusione": ["specchio", "nebbia"], "karma": ["ordine"]}

# (dove, che cosa, testo) — «what»: deep = approfondisce un tuo Dao, glimpse = scorcio di una via nuova,
#                                  hint = intuizione su una fusione, scroll = pagina di tecnica (comprensione a un Dao fuso)
RELICS = [
    (("ruin",), "deep", "Una stele spaccata in due: le incisioni sono la spiegazione di un maestro morto da diecimila anni."),
    (("ruin", "cave"), "glimpse", "Un rotolo di seta chiuso in un tubo di giada: parla di una via che non conosci."),
    (("ruin", "forbidden_zone"), "hint", "Due statue che si tengono per mano, ognuna con il simbolo di un Dao diverso."),
    (("mountain",), "deep", "Una spada conficcata nella roccia: l'intento che vi ha lasciato il padrone è ancora vivo."),
    (("cave",), "deep", "Sulla parete, mille segni di unghie: qualcuno ha meditato qui fino a capire."),
    (("forbidden_zone",), "glimpse", "Un altare annerito: il Dao che vi si praticava ha lasciato un'impronta nel qi."),
    (("mountain", "cave"), "hint", "Un'iscrizione a due mani, due scritture intrecciate: un maestro che fondeva due vie."),
    (("ruin",), "scroll", "Un manuale sfogliato da troppi discepoli: le pagine più consumate sono quelle sulle fusioni."),
]


def _rng(conn, salt: int = 0) -> random.Random:
    from engine.core import tick
    return random.Random(tick.get_tick(conn) * 131 + salt)


def _data(conn) -> dict:
    from engine.systems import state
    d = state.get_json(conn, "dao_insight", None) or {}
    d.setdefault("scorci", {})
    d.setdefault("relics", {})       # id luogo → giorno dell'ultima ricerca
    d.setdefault("log", [])
    return d


def _save(conn, d: dict) -> None:
    from engine.systems import state
    d["log"] = d["log"][-12:]
    state.set_json(conn, "dao_insight", d)


def _is_high(key: str) -> bool:
    from engine.systems import dao_laws
    from engine.generators import dao_gen
    lvl = next((r[2] for r in dao_gen.DAOS if r[0] == key), "")
    return lvl in ("superior", "deep", "forbidden") or (key in dao_laws.BY_KEY and dao_laws.BY_KEY[key][2] in ("deep", "forbidden"))


def glimpse(conn, key: str, d: dict, pid: int = 1) -> str:
    """Uno scorcio di un Dao che non pratichi; al terzo (o sesto) si apre."""
    from engine.systems import dao_laws
    from engine.systems.dao_techniques import _dao_label
    if dao_laws._has(conn, key, pid):
        return ""
    need = GLIMPSES_HIGH if _is_high(key) else GLIMPSES
    n = d["scorci"].get(key, 0) + 1
    d["scorci"][key] = n
    name = _dao_label(key)
    if n >= need:
        d["scorci"].pop(key, None)
        dao_laws.grant(conn, key, 10, pid)
        d["log"].append(f"aperto il {name}")
        return (f"✺ Gli scorci si uniscono: capisci il {name}. Si apre una via nuova. "
                f"(Allenalo con 'comprehend {key}'.)")
    return f"✧ Uno scorcio del {name} ({n}/{need}): ancora qualche visione e la via si aprirà."


def deepen(conn, key: str, gain: int, pid: int = 1) -> str:
    from engine.systems.dao_techniques import _dao_label
    conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='player' "
                 "AND character_id=? AND dao_key=?;", (gain, pid, key))
    return f"✧ Il tuo {_dao_label(key)} va più a fondo: comprensione +{gain}."


def _player_daos(conn, pid: int = 1) -> dict[str, int]:
    return {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND (practiced=1 OR comprehension>0);", (pid,))}


def _fusion_of(keys: set[str]) -> str | None:
    from engine.systems import dao_laws
    for fk, row in dao_laws.FUSED.items():
        comps = set(row[2])
        if len(comps) >= 2 and len(comps & keys) >= 2:
            return fk
    return None


# ---------------------------------------------------------------- scontrarsi con chi è più forte

def observe(conn, npc_id: int, pid: int = 1, rng: random.Random | None = None, force: bool = False,
            intro: str | None = None) -> list[str]:
    """All'inizio di uno scontro: se il nemico ti supera, a volte vedi come usa il suo Dao.
    force=True (dopo una sconfitta, o guardando un duello altrui): accade sempre, anche con chi non ti supera."""
    from engine.simulation import cultivation
    from engine.systems.dao_techniques import _dao_label
    rng = rng or _rng(conn, npc_id)
    foe = {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' AND character_id=? "
        "AND comprehension>=10 ORDER BY comprehension DESC;", (npc_id,))}
    if not foe:
        return []
    mine = _player_daos(conn, pid)
    t_me = cultivation.realm_tier(conn, "player", pid) or 1
    t_foe = cultivation.realm_tier(conn, "npc", npc_id) or 1
    top, top_c = next(iter(foe.items()))
    stronger = t_foe > t_me or top_c > mine.get(top, 0) * 1.5 + 10
    if not force and (not stronger or rng.random() >= STRONG_CHANCE):
        return []
    if force and not stronger and top_c <= mine.get(top, 0):
        return []                                 # non ha niente da insegnarti
    d = _data(conn)
    out = [intro or f"👁 Mentre vi studiate, vedi come usa il {_dao_label(top)}: non è un'arte, è un modo di essere."]
    if top in mine:
        gain = max(1, min(60, (top_c - mine[top]) // 8 + 2 * max(0, t_foe - t_me)))
        out.append("  " + deepen(conn, top, gain, pid))
    else:
        out.append("  " + glimpse(conn, top, d, pid))
    for k in NEAR.get(top, []):
        if rng.random() < 0.35 and k not in mine:
            out.append("  " + glimpse(conn, k, d, pid))
            break
    fk = _fusion_of(set(foe))
    from engine.systems import dao_laws
    if fk and dao_laws.add_hint(conn, fk):
        out.append(f"  ✧ Intreccia due vie in una: hai un'intuizione sul {dao_laws.FUSED[fk][1]} "
                   f"(soglie −20%, nessun rischio di conflitto — 'fusione').")
    d["log"].append(f"osservato un nemico più forte ({_dao_label(top)})")
    _save(conn, d)
    return [x for x in out if x.strip()]


# ---------------------------------------------------------------- i reperti dei maestri

def search(conn, player) -> str:
    from engine.core import entities, tick
    from engine.systems import dao_laws, training
    from engine.systems.dao_techniques import _dao_label
    loc = entities.get_location(conn, player.location_id)
    if not loc or loc.location_type not in RELIC_PLACES:
        return ("Qui non ci sono reperti di maestri del passato: cercali tra rovine, grotte, montagne e "
                "zone proibite.")
    d = _data(conn)
    day = training.current_day(tick.get_tick(conn))
    last = d["relics"].get(str(loc.id))
    if last is not None and day - int(last) < RELIC_DAYS:
        return f"Hai già frugato {loc.name}: tra {RELIC_DAYS - (day - int(last))} giorni il luogo avrà altro da mostrare."
    d["relics"][str(loc.id)] = day
    rng = _rng(conn, loc.id * 7 + 3)
    from engine.simulation import world_tick
    world_tick.advance(conn, tick.cost_of("cultivate"))
    if rng.random() < 0.3:
        _save(conn, d)
        return f"Cerchi a lungo tra le pietre di {loc.name}. Solo polvere, oggi: altri sono passati prima di te."
    pool = [r for r in RELICS if loc.location_type in r[0]]
    _w, what, text = rng.choice(pool)
    mine = _player_daos(conn, player.id)
    out = [f"🏺 {text}"]
    if what == "scroll":
        fused = [k for k in mine if k in dao_laws.FUSED]
        if fused:
            k = rng.choice(fused)
            out.append(deepen(conn, k, rng.randint(15, 40), player.id) + f" (profondità {dao_laws.grade(mine[k])} → "
                       f"{dao_laws.grade(mine[k] + 15)})")
        else:
            what = "hint"
    if what == "hint":
        cand = [k for k in dao_laws.FUSED if k not in dao_laws.hints(conn) and not dao_laws._has(conn, k, player.id)
                and any(c in mine for c in dao_laws.FUSED[k][2])]
        if cand:
            k = rng.choice(cand)
            dao_laws.add_hint(conn, k)
            comps = " e ".join(_dao_label(c) for c in dao_laws.FUSED[k][2])
            out.append(f"✧ Intuizione: {comps} possono diventare il {dao_laws.FUSED[k][1]} "
                       f"(soglie −20%, nessun rischio — 'fusione').")
        else:
            what = "deep"
    if what == "glimpse":
        cand = [k for k in set(sum((NEAR.get(m, []) for m in mine), [])) if k not in mine] or \
               [k for k in dao_laws.BY_KEY if k not in mine and dao_laws.BY_KEY[k][4][0] != "risveglio"]
        if cand:
            out.append(glimpse(conn, rng.choice(sorted(cand)), d, player.id))
        else:
            what = "deep"
    if what == "deep":
        if mine:
            k = max(mine, key=lambda x: (mine[x], x)) if rng.random() < 0.5 else rng.choice(sorted(mine))
            out.append(deepen(conn, k, rng.randint(8, 25) + mine[k] // 40, player.id))
        else:
            out.append("Non pratichi ancora nessun Dao: le parole del maestro ti restano oscure.")
    d["log"].append(f"reperto a {loc.name}")
    _save(conn, d)
    return "\n".join(out)


def after_defeat(conn, npc_id: int, pid: int = 1) -> list[str]:
    """La sconfitta insegna: ripensi a ogni colpo che hai preso."""
    from engine.systems.dao_techniques import _dao_label
    top = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='npc' AND character_id=? "
                       "ORDER BY comprehension DESC LIMIT 1;", (npc_id,)).fetchone()
    if not top:
        return []
    return observe(conn, npc_id, pid, force=True, intro=(
        f"👁 La sconfitta brucia, ma ripensi a ogni colpo che hai preso: ora capisci come usava il "
        f"{_dao_label(top['dao_key'])}."))


def watch(conn, player) -> str:
    """'assisti': ti fermi a guardare chi qui combatte o si allena, e impari dal più bravo."""
    from engine.core import entities, tick
    from engine.systems import training
    from engine.simulation import world_tick
    day = training.current_day(tick.get_tick(conn))
    d = _data(conn)
    seen = d.setdefault("watched", {})
    if seen.get(str(player.location_id)) == day:
        return "Hai già passato ore a guardare, oggi. Torna domani: ci saranno altri da osservare."
    best = None
    for n in entities.npcs_in_location(conn, player.location_id):
        r = conn.execute("SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' "
                         "AND character_id=? ORDER BY comprehension DESC LIMIT 1;", (n.id,)).fetchone()
        if r and (r["comprehension"] or 0) >= 10 and (not best or r["comprehension"] > best[1]):
            best = (n, r["comprehension"], r["dao_key"])
    if not best:
        return "Qui nessuno combatte né si allena: non c'è niente da guardare."
    seen[str(player.location_id)] = day
    _save(conn, d)
    world_tick.advance(conn, tick.cost_of("short_rest"))
    from engine.systems.dao_techniques import _dao_label
    n = best[0]
    out = observe(conn, n.id, player.id, force=True, intro=(
        f"👁 Ti fermi a guardare {n.name} che si allena. Ogni gesto del suo {_dao_label(best[2])} è una lezione."))
    return "\n".join(out) if out else (f"Guardi {n.name} allenarsi per ore, ma il suo {_dao_label(best[2])} non ha "
                                        f"niente che tu non sappia già.")


def can_search(conn, loc_id: int) -> bool:
    from engine.core import tick
    from engine.systems import training
    last = _data(conn)["relics"].get(str(loc_id))
    return last is None or training.current_day(tick.get_tick(conn)) - int(last) >= RELIC_DAYS


def describe(conn) -> str:
    from engine.systems.dao_techniques import _dao_label
    d = _data(conn)
    lines = ["👁 LE INTUIZIONI DEL DAO — scontrarsi con chi è più forte ti mostra come usa il suo Dao; i reperti "
             "('reperti', tra rovine, grotte, montagne, zone proibite) custodiscono gli insegnamenti dei maestri."]
    if d["scorci"]:
        lines.append("Scorci: " + ", ".join(
            f"{_dao_label(k)} {n}/{GLIMPSES_HIGH if _is_high(k) else GLIMPSES}" for k, n in sorted(d["scorci"].items())))
    from engine.systems import dao_laws
    h = dao_laws.hints(conn)
    if h:
        lines.append("Intuizioni di fusione: " + ", ".join(dao_laws.FUSED[k][1] for k in sorted(h) if k in dao_laws.FUSED))
    if d["log"]:
        lines.append("Ultime: " + "; ".join(d["log"][-5:]))
    return "\n".join(lines)
