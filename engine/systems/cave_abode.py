"""
GROTTA-DIMORA (洞府) — la tua casa tra le montagne.

  dimora                     stato della dimora (o come ottenerne una)
  dimora reclama             reclami il luogo in cui ti trovi (montagna, rovine o zona
                             proibita) pagando in pietre spirituali
  dimora potenzia <ala>      potenzi una struttura (livelli infiniti, costo crescente)
  dimora raccogli            raccogli ciò che la dimora ha prodotto (devi esserci)
  dimora torna               torni a casa (il viaggio richiede tempo)
  dimora potenzia max [ala]  porta la dimora (o un'ala) al livello più alto che puoi
                             permetterti ora con le tue pietre, in un colpo solo

Strutture:
  erbe      Campo di Erbe Spirituali — produce erbe ogni giorno
  qi        Formazione di Raccolta del Qi — coltivi più in fretta a casa
  ritiro    Stanza del Ritiro — il ritiro a porte chiuse rende di più a casa
  alchimia  Stanza dell'Alchimia — creare a casa riesce più spesso e insegna di più
  difesa    Formazione Difensiva — meno disturbi durante il ritiro; tiene lontani gli intrusi
  stalla    Stalla delle Bestie — la tua bestia cresce ogni giorno; produce nuclei
"""

from __future__ import annotations

import sqlite3

from engine.systems import state

KEY = "abode"
_SPOTS = ("mountain", "ruin", "forbidden_zone")
WINGS = {
    "erbe": ("Campo di Erbe Spirituali", 120),
    "qi": ("Formazione di Raccolta del Qi", 200),
    "ritiro": ("Stanza del Ritiro", 180),
    "alchimia": ("Stanza dell'Alchimia", 150),
    "difesa": ("Formazione Difensiva", 160),
    "stalla": ("Stalla delle Bestie", 140),
}
_ALIASES = {"campo": "erbe", "herbs": "erbe", "raccolta": "qi", "formazione": "qi",
            "seclusion": "ritiro", "alchemy": "alchimia", "forno": "alchimia",
            "defense": "difesa", "scudo": "difesa", "stable": "stalla", "bestie": "stalla"}


def get(conn: sqlite3.Connection, pid: int = 1) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, ab: dict) -> None:
    state.set_json(conn, KEY, ab)


def level(conn, pid: int, wing: str) -> int:
    ab = get(conn, pid)
    return int(ab["wings"].get(wing, 0)) if ab else 0


def is_home(conn, pid: int, location_id: int | None) -> bool:
    ab = get(conn, pid)
    return bool(ab and location_id is not None and ab["loc"] == location_id)


def claim_cost(tier: int) -> int:
    return 150 * tier


def upgrade_cost(wing: str, lv: int) -> int:
    """Costo per passare da lv a lv+1: cresce del 60% a livello (senza tetto)."""
    return int(WINGS[wing][1] * (1.6 ** lv))


# ---------- effetti sugli altri sistemi ----------

def cultivation_mult(conn, pid: int, location_id: int | None, seclusion: bool = False) -> tuple[float, str]:
    if not is_home(conn, pid, location_id):
        return 1.0, ""
    m = 1.0 + 0.15 * level(conn, pid, "qi")
    if seclusion:
        m *= 1.0 + 0.2 * level(conn, pid, "ritiro")
    m *= 1.10                               # la propria casa: niente distrazioni
    return m, "la tua grotta-dimora"


def disturb_factor(conn, pid: int, location_id: int | None) -> float:
    if not is_home(conn, pid, location_id):
        return 1.0
    return 1.0 / (1 + level(conn, pid, "difesa"))


def craft_level(conn, pid: int, location_id: int | None) -> int:
    return level(conn, pid, "alchimia") if is_home(conn, pid, location_id) else 0


# ---------- comandi ----------

def claim(conn, player) -> str:
    from engine.systems import sects
    from engine.simulation import cultivation
    from engine.core import tick as tick_mod
    if get(conn, player.id):
        return "Hai già una dimora. ('dimora' per vederla)"
    lt = conn.execute("SELECT name, location_type FROM locations WHERE id=?;",
                      (player.location_id,)).fetchone()
    if not lt or lt["location_type"] not in _SPOTS:
        return "Una grotta-dimora va scavata tra montagne, rovine o zone proibite, lontano dalle città."
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    cost = claim_cost(tier)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Servono {cost} pietre spirituali per sigillare e arredare la grotta."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    _save(conn, {"loc": player.location_id, "name": f"Dimora di {lt['name']}",
                 "wings": {}, "stock": {}, "since": tick_mod.get_tick(conn)})
    return (f"Scavi una grotta nella roccia di {lt['name']}, tracci i primi sigilli e ne fai la tua casa. "
            f"(-{cost} pietre)\nOra puoi potenziarla: 'dimora potenzia <erbe|qi|ritiro|alchimia|difesa|stalla>'.")


def upgrade(conn, player, wing_raw: str) -> str:
    from engine.systems import sects
    ab = get(conn, player.id)
    if not ab:
        return "Non hai una dimora. ('dimora reclama' in una montagna, rovine o zona proibita)"
    w = wing_raw.strip().lower()
    w = _ALIASES.get(w, w)
    if w not in WINGS:
        return "Cosa vuoi potenziare? " + ", ".join(f"{k} ({v[0]})" for k, v in WINGS.items())
    if player.location_id != ab["loc"]:
        return "Devi essere nella tua dimora per lavorarci. ('dimora torna')"
    lv = int(ab["wings"].get(w, 0))
    cost = upgrade_cost(w, lv)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"{WINGS[w][0]} livello {lv + 1}: servono {cost} pietre spirituali."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    ab["wings"][w] = lv + 1
    _save(conn, ab)
    from engine.simulation import world_tick
    world_tick.advance(conn, 24)
    return f"{WINGS[w][0]} portata al livello {lv + 1}. (-{cost} pietre)"


EFFECT = {"erbe": lambda lv: f"{2 * lv} erbe al giorno",
          "qi": lambda lv: f"coltivazione a casa ×{1.1 * (1 + 0.15 * lv):.2f}",
          "ritiro": lambda lv: f"ritiro a casa ×{1 + 0.2 * lv:.1f}",
          "alchimia": lambda lv: f"creare a casa: +{5 * lv}% riuscita, esperienza doppia" if lv else "nessun bonus",
          "difesa": lambda lv: f"disturbi ÷{1 + lv}",
          "stalla": lambda lv: f"nuclei e crescita della bestia ({lv})" if lv else "nessuna produzione"}


def plan_max(ab: dict, stones: int, wing: str | None = None) -> tuple[list[tuple[str, int, int]], int]:
    """I potenziamenti che puoi permetterti ora: [(ala, dal livello, al livello)], costo totale.
    Per tutta la dimora sceglie ogni volta il potenziamento più economico (le ali crescono in equilibrio)."""
    lv = {k: int(ab["wings"].get(k, 0)) for k in WINGS}
    start = dict(lv)
    spent = 0
    keys = [wing] if wing else list(WINGS)
    while True:
        k = min(keys, key=lambda x: upgrade_cost(x, lv[x]))
        c = upgrade_cost(k, lv[k])
        if spent + c > stones:
            break
        spent += c
        lv[k] += 1
    return [(k, start[k], lv[k]) for k in WINGS if lv[k] > start[k]], spent


def upgrade_max(conn, player, wing_raw: str = "") -> str:
    """'dimora potenzia max [ala]': tutto ciò che puoi permetterti, in una sola sessione di lavoro."""
    from engine.systems import sects
    from engine.simulation import world_tick
    ab = get(conn, player.id)
    if not ab:
        return "Non hai una dimora. ('dimora reclama' in una montagna, rovine o zona proibita)"
    w = _ALIASES.get(wing_raw.strip().lower(), wing_raw.strip().lower()) or None
    if w and w not in WINGS:
        return "Quale ala? " + ", ".join(WINGS)
    if player.location_id != ab["loc"]:
        return "Devi essere nella tua dimora per lavorarci. ('dimora torna')"
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    steps, cost = plan_max(ab, stones, w)
    if not steps:
        k = w or min(WINGS, key=lambda x: upgrade_cost(x, int(ab["wings"].get(x, 0))))
        return (f"Non hai abbastanza pietre: il prossimo potenziamento ({WINGS[k][0]}) costa "
                f"{upgrade_cost(k, int(ab['wings'].get(k, 0)))} pietre, ne hai {stones}.")
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    n = 0
    for k, a, b in steps:
        ab["wings"][k] = b
        n += b - a
    _save(conn, ab)
    world_tick.advance(conn, min(120, 24 + 8 * (n - 1)))
    lines = [f"Lavori alla dimora senza sosta: {n} potenziament{'o' if n == 1 else 'i'} (-{cost} pietre)."]
    lines += [f"  · {WINGS[k][0]}: livello {a} → {b} ({EFFECT[k](b)})" for k, a, b in steps]
    return "\n".join(lines)


def daily(conn, t: int, rng, player) -> list[str]:
    """Produzione quotidiana (accumulata finché non la raccogli)."""
    ab = get(conn, player.id)
    if not ab:
        return []
    st = ab.setdefault("stock", {})
    erbe = 2 * int(ab["wings"].get("erbe", 0))
    stalla = int(ab["wings"].get("stalla", 0))
    if erbe:
        st["erbe"] = min(erbe * 30, st.get("erbe", 0) + erbe)
    if stalla:
        st["nuclei"] = min(stalla * 15, st.get("nuclei", 0) + (1 if rng.random() < 0.3 * stalla else 0))
    out = []
    if stalla:
        from engine.systems import beasts, npc_factory
        pt = beasts.pet(conn, player.id)
        if pt and rng.random() < 0.15 * stalla:
            npc_factory.raise_npc(conn, pt["npc_id"], 1)
    _save(conn, ab)
    return out


def collect(conn, player) -> str:
    from engine.systems import professions
    ab = get(conn, player.id)
    if not ab:
        return "Non hai una dimora."
    if player.location_id != ab["loc"]:
        return "Devi essere nella tua dimora per raccogliere."
    st = ab.get("stock", {})
    got = []
    for k, n in list(st.items()):
        if n > 0:
            professions.give(conn, player.id, k, n)
            got.append(f"{n} {professions.MATERIALS.get(k, k)}")
    ab["stock"] = {}
    _save(conn, ab)
    return ("Raccogli: " + ", ".join(got) + ".") if got else "Non c'è ancora nulla da raccogliere."


def go_home(conn, player) -> str:
    from engine.core import entities
    from engine.simulation import world_tick
    ab = get(conn, player.id)
    if not ab:
        return "Non hai una dimora."
    if player.location_id == ab["loc"]:
        return "Sei già a casa."
    hops = _distance(conn, player.location_id, ab["loc"])
    if hops is None:
        return "Non trovi la strada di casa da qui."
    entities.move_player(conn, player.id, ab["loc"])
    world_tick.advance(conn, 6 * hops)
    return f"Torni alla tua dimora ({hops} tappe di viaggio)."


def _distance(conn, a: int, b: int) -> int | None:
    from collections import deque
    seen, q = {a}, deque([(a, 0)])
    while q:
        cur, d = q.popleft()
        if cur == b:
            return d
        for r in conn.execute("SELECT to_location_id FROM location_connections WHERE from_location_id=?;",
                              (cur,)):
            if r[0] not in seen:
                seen.add(r[0])
                q.append((r[0], d + 1))
    return None


def describe(conn, player) -> str:
    from engine.simulation import cultivation
    ab = get(conn, player.id)
    if not ab:
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        return ("Non hai ancora una grotta-dimora. Trova una montagna, delle rovine o una zona "
                f"proibita e usa 'dimora reclama' ({claim_cost(tier)} pietre).")
    loc = conn.execute("SELECT name FROM locations WHERE id=?;", (ab["loc"],)).fetchone()["name"]
    lines = [f"⌂ {ab['name']} — a {loc}" + (" (sei qui)" if player.location_id == ab["loc"] else "")]
    for k, (nm, _c) in WINGS.items():
        lv = int(ab["wings"].get(k, 0))
        lines.append(f"  {nm:<32} liv. {lv:<3} (prossimo: {upgrade_cost(k, lv)} pietre — 'dimora potenzia {k}')")
    st = {k: v for k, v in ab.get("stock", {}).items() if v}
    if st:
        lines.append("In attesa di raccolta: " + ", ".join(f"{v} {k}" for k, v in st.items()) +
                     " ('dimora raccogli')")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    if sub in ("reclama", "claim", "scava"):
        return claim(conn, player)
    if sub in ("max", "massimo") or (sub in ("potenzia", "upgrade", "costruisci", "build")
                                     and rest.split()[:1] and rest.split()[0] in ("max", "massimo", "tutto", "tutta")):
        r = rest.split()
        wing = r[1] if sub not in ("max", "massimo") and len(r) > 1 else (r[0] if sub in ("max", "massimo") and r else "")
        return upgrade_max(conn, player, wing)
    if sub in ("potenzia", "upgrade", "costruisci", "build") and rest.split()[-1:] in (["max"], ["massimo"]):
        return upgrade_max(conn, player, rest.split()[0])
    if sub in ("potenzia", "upgrade", "costruisci", "build"):
        return upgrade(conn, player, rest)
    if sub in ("raccogli", "collect"):
        return collect(conn, player)
    if sub in ("torna", "home", "casa"):
        return go_home(conn, player)
    return describe(conn, player)
