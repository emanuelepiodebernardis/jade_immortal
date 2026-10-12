"""
BESTIE SPIRITUALI — domare, crescere, combattere insieme.

Oltre a uccidere o divorare una creatura, puoi DOMARLA ('tame <nome>'). Ogni bestia
ha un TALENTO (comune, dotata, rara, prodigio, divina) che decide quanto cresce e
quanto pesa in battaglia, e un ELEMENTO che porta il suo stato nello scontro.

Con il progredire della tua storia (il tuo regno) il mondo rivela bestie RARE
(Qilin, Tigre Bianca, Tartaruga Nera…), poi LEGGENDARIE (Fenice, Drago) e infine
IBRIDI di bestie leggendarie (Drago-Fenice, Qilin del Tuono…): giungono voci di
avvistamenti in luoghi selvaggi, e vanno cercate. Più sono rare, più è difficile
domarle (ferirle prima aiuta; il destino "Amico delle Bestie" e il "Sangue di Drago"
anche).

Una sola bestia alla volta ('release' per liberarla). Si nutre con i nuclei
('feed'), che si ottengono cacciando.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities
from engine.systems import state

# grado di talento: (nome, moltiplicatore crescita/potenza, peso estrazione)
TALENTS = [("comune", 0.8, 55), ("dotata", 1.0, 25), ("rara", 1.25, 12),
           ("prodigio", 1.6, 6), ("divina", 2.0, 2)]
TALENT_MULT = {n: m for n, m, _w in TALENTS}

# creature comuni -> elemento
COMMON_ELEMENT = {"Cinghiale Corazzato": "corpo", "Orso di Ferro": "corpo",
                  "Lupo Spirituale": "vento", "Tigre di Giada": "metallo",
                  "Serpente di Roccia": "terra", "Aquila del Tuono": "fulmine",
                  "Spirito Errante": "anima", "Anima Nebbiosa": "acqua",
                  "Eco Ancestrale": "anima", "Fiamma Fatua": "fuoco"}

# specie rare/leggendarie/ibride: (nome, rarità, elementi, regno minimo del giocatore, abilità)
# La scala delle bestie (dal Classico dei Monti e dei Mari e dai romanzi di coltivazione): spirituali e
# reali, poi imperiali e divine, poi i QUATTRO SIMBOLI, le BESTIE ANCESTRALI e infine il CAOS.
RARE_SPECIES = [
    # spirituali e reali
    ("Volpe Spirituale", "rara", ["illusione"], 3, None),
    ("Gru delle Nubi", "rara", ["vento"], 3, None),
    ("Serpente Volante", "rara", ["vento"], 3, None),
    ("Pixiu", "rara", ["terra", "metallo"], 4, None),
    ("Suanni", "rara", ["fuoco"], 4, None),
    ("Grande Peng", "rara", ["vento", "acqua"], 4, None),
    ("Tartaruga di Giada", "rara", ["acqua", "terra"], 4, None),
    # imperiali e divine
    ("Qilin", "leggendaria", ["luce"], 5, None),
    ("Bai Ze", "leggendaria", ["luce", "anima"], 5, None),
    ("Volpe a Nove Code", "leggendaria", ["illusione", "fuoco"], 6, None),
    ("Kun degli Abissi", "leggendaria", ["acqua"], 6, None),
    ("Fenice", "leggendaria", ["fuoco"], 6, "rinascita"),
    ("Drago delle Nubi", "leggendaria", ["fulmine", "acqua"], 6, "drago"),
    ("Drago-Fenice", "ibrida", ["fuoco", "fulmine"], 7, "rinascita"),
    ("Qilin del Tuono", "ibrida", ["luce", "fulmine"], 7, None),
    ("Fenice di Ghiaccio", "ibrida", ["fuoco", "acqua"], 7, "rinascita"),
    ("Drago Nero dell'Abisso", "ibrida", ["oscurita", "acqua"], 7, "drago"),
    ("Tigre Alata del Vento", "ibrida", ["metallo", "vento"], 7, None),
    # i Quattro Simboli
    ("Drago Azzurro", "simbolo", ["legno", "fulmine"], 8, "drago"),
    ("Tigre Bianca", "simbolo", ["metallo"], 8, None),
    ("Uccello Vermiglio", "simbolo", ["fuoco"], 8, "rinascita"),
    ("Tartaruga Nera", "simbolo", ["acqua", "terra"], 8, None),
    # le Bestie Ancestrali (nei mondi superiori)
    ("Taotie", "ancestrale", ["oscurita", "sangue"], 11, None),
    ("Qiongqi", "ancestrale", ["vento", "oscurita"], 11, None),
    ("Taowu", "ancestrale", ["terra", "massacro"], 11, None),
    ("Kunpeng", "ancestrale", ["acqua", "vento"], 12, None),
    ("Drago della Torcia", "ancestrale", ["fuoco", "tempo"], 13, "drago"),
    ("Xiangliu", "ancestrale", ["acqua", "oscurita"], 12, None),
    # il Caos
    ("Hundun", "caos", ["caos"], 14, None),
]
RARITY_ORDER = ["comune", "rara", "leggendaria", "ibrida", "simbolo", "ancestrale", "caos"]
RARITY_TAME_PENALTY = {"comune": 0.0, "rara": 0.15, "leggendaria": 0.30, "ibrida": 0.40, "simbolo": 0.50,
                       "ancestrale": 0.60, "caos": 0.70}
RARITY_TALENT_FLOOR = {"comune": 0, "rara": 2, "leggendaria": 3, "ibrida": 3, "simbolo": 3, "ancestrale": 4, "caos": 4}
RARITY_IT = {"comune": "comune", "rara": "rara", "leggendaria": "leggendaria", "ibrida": "ibrida",
             "simbolo": "dei Quattro Simboli", "ancestrale": "ancestrale", "caos": "del Caos"}
# quali classi di bestie abitano ogni mondo: salendo, le bestie minori scompaiono e ne compaiono di più alte
_PLANE_CLASSES = [("rara", "leggendaria", "ibrida", "simbolo"), ("leggendaria", "ibrida", "simbolo", "ancestrale"),
                  ("simbolo", "ancestrale", "caos")]


def plane_pool(layer: int, ptier: int) -> list[tuple]:
    classes = _PLANE_CLASSES[min(layer, len(_PLANE_CLASSES) - 1)]
    pool = [s for s in RARE_SPECIES if s[1] in classes and s[3] <= ptier]
    if not pool:
        lo = min(s[3] for s in RARE_SPECIES if s[1] in classes)
        pool = [s for s in RARE_SPECIES if s[1] in classes and s[3] == lo]
    if layer >= len(_PLANE_CLASSES):               # oltre: le stesse bestie, ma «del N° Cielo»
        from engine.systems import ascension
        pool = [(f"{s[0]} del {ascension.layer_name(layer)}", s[1], s[2], s[3], s[4]) for s in pool]
    return pool


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS beast_traits (npc_id INTEGER PRIMARY KEY, species TEXT, "
        "rarity TEXT DEFAULT 'comune', talent TEXT DEFAULT 'comune', elements TEXT, "
        "ability TEXT);")


def _roll_talent(rng: random.Random, floor: int = 0) -> str:
    pool = TALENTS[floor:]
    return rng.choices([t[0] for t in pool], weights=[t[2] for t in pool])[0]


def traits(conn, npc_id: int, rng: random.Random | None = None) -> sqlite3.Row:
    """Tratti della bestia (creati alla prima lettura per le creature comuni)."""
    ensure_table(conn)
    row = conn.execute("SELECT * FROM beast_traits WHERE npc_id=?;", (npc_id,)).fetchone()
    if row:
        return row
    rng = rng or random.Random(npc_id * 977)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    base = name.rstrip("0123456789 ").strip()
    el = COMMON_ELEMENT.get(base, "corpo")
    conn.execute("INSERT INTO beast_traits (npc_id, species, rarity, talent, elements) "
                 "VALUES (?, ?, 'comune', ?, ?);", (npc_id, base, _roll_talent(rng), el))
    return conn.execute("SELECT * FROM beast_traits WHERE npc_id=?;", (npc_id,)).fetchone()


def pets(conn, player_id: int = 1) -> list:
    from engine.systems import bonds
    bonds.ensure_table(conn)
    return [r for r in bonds._active(conn, player_id, "beast") if r["npc_status"] == "alive"]


def pet(conn, player_id: int = 1) -> sqlite3.Row | None:
    try:
        return conn.execute(
            "SELECT b.npc_id, n.name, n.location_id, n.status FROM bonds b JOIN npcs n ON n.id=b.npc_id "
            "WHERE b.player_id=? AND b.kind='beast' AND b.status='active' AND n.status='alive' "
            "ORDER BY b.id LIMIT 1;", (player_id,)).fetchone()
    except sqlite3.OperationalError:
        return None


# ============================================================
# Avvistamenti di bestie rare
# ============================================================

def _wild_spot(conn, start: int, rng: random.Random, hops: int) -> int:
    loc = start
    for _ in range(hops):
        ex = entities.get_exits(conn, loc)
        if not ex:
            break
        loc = rng.choice(sorted(ex.values()))
    return loc


def spawn_rare(conn, rng: random.Random, player, species: tuple | None = None) -> tuple[int, str]:
    from engine.simulation import cultivation
    from engine.systems import npc_factory
    ensure_table(conn)
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    if species is None:
        from engine.systems import ascension
        pool = plane_pool(ascension.player_layer(conn, player.id), ptier)
        wmap = {"rara": 6, "leggendaria": 3, "ibrida": 1.5, "simbolo": 1, "ancestrale": 1, "caos": 0.4}
        species = rng.choices(pool, weights=[wmap.get(s[1], 1) for s in pool])[0]
    name, rarity, els, _min, ability = species
    loc = _wild_spot(conn, player.location_id, rng, rng.randint(2, 4))
    nid = npc_factory.spawn(conn, rng, archetype="vagabondo", location_id=loc,
                            tier=ptier + (0 if rarity == "rara" else 1 if rarity in ("leggendaria", "ibrida") else 2),
                            stage=rng.randint(3, 8),
                            name=name if not conn.execute("SELECT 1 FROM npcs WHERE name=?;", (name,)).fetchone()
                            else f"{name} {rng.randint(2, 99)}",
                            dao=els[0], dao_comp=30 + ptier * 10,
                            traits={"courage": 90, "pride": 80})
    conn.execute("UPDATE npcs SET kind='beast', archetype='bestia', description=? WHERE id=?;",
                 (f"Una creatura {RARITY_IT.get(rarity, rarity)}: {name}. Gli elementi danzano attorno a lei.", nid))
    for extra in els[1:]:
        conn.execute("INSERT OR IGNORE INTO character_daos (character_type, character_id, dao_key, "
                     "affinity, comprehension, practiced) VALUES ('npc', ?, ?, 70, ?, 1);",
                     (nid, extra, 20 + ptier * 8))
    conn.execute("INSERT OR REPLACE INTO beast_traits (npc_id, species, rarity, talent, elements, ability) "
                 "VALUES (?, ?, ?, ?, ?, ?);",
                 (nid, name, rarity, _roll_talent(rng, RARITY_TALENT_FLOOR[rarity]), ",".join(els), ability))
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"]
    return nid, lname


def active_rare(conn) -> list[sqlite3.Row]:
    ensure_table(conn)
    return conn.execute(
        "SELECT n.id, n.name, n.location_id, bt.rarity, l.name AS loc FROM beast_traits bt "
        "JOIN npcs n ON n.id=bt.npc_id LEFT JOIN locations l ON l.id=n.location_id "
        "WHERE bt.rarity<>'comune' AND n.status='alive' AND n.id NOT IN "
        "(SELECT npc_id FROM bonds WHERE kind='beast' AND status='active');").fetchall()


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    """Crescita della tua bestia + avvistamenti di bestie rare col progredire."""
    from engine.simulation import cultivation
    from engine.systems import npc_factory
    out = []
    pt = pet(conn, player.id)
    if pt:
        tr = traits(conn, pt["npc_id"])
        mult = TALENT_MULT.get(tr["talent"], 1.0)
        ptier = cultivation.realm_tier(conn, "player", player.id) or 1
        if rng.random() < 0.35 * mult and npc_factory.npc_tier(conn, pt["npc_id"]) <= ptier + 1:
            npc_factory.raise_npc(conn, pt["npc_id"], max(1, round(mult)))
            out.append(f"{pt['name']} cresce: la sua forza aumenta.")
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    if ptier >= 3 and not active_rare(conn) and rng.random() < 0.12 + 0.03 * ptier:
        nid, lname = spawn_rare(conn, rng, player)
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        out.append(f"🐉 Voci dai viandanti: un esemplare di {nm} è stato avvistato a {lname}!")
    return out


# ============================================================
# Domare, liberare, nutrire
# ============================================================

def tame(conn, t: int, rng: random.Random, player, npc) -> tuple[str, str | None]:
    """Ritorna (testo, comando_da_eseguire). Se fallisce, la bestia attacca."""
    from engine.systems import bonds, perception, destinies, character
    k = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()["kind"]
    if k not in ("beast", "spirit"):
        return ("Solo bestie e spiriti possono essere domati." if k == "demon"
                else f"{npc.name} non è una creatura da domare."), None
    from engine.systems import classes
    if len(pets(conn, player.id)) >= classes.max_beasts(conn, player.id):
        return ("Hai già tutte le bestie che sai guidare ('release' per liberarne una; "
                "un Domatore di Bestie esperto può tenerne di più)."), None
    tr = traits(conn, npc.id, rng)
    rel = perception.relative_strength(conn, player.id, npc.id)
    base = {"molto più debole di te": 0.75, "più debole di te": 0.55, "circa alla tua pari": 0.35,
            "più forte di te": 0.15, "molto più forte di te": 0.03}.get(rel, 0.3)
    prof = character.get_profile(conn, "player", player.id)
    soul = (prof["aff_soul"] or 50) if prof else 50
    p = base + (soul - 50) / 250 + int(destinies.flag_value(conn, "tamer", player.id, 0)) / 100
    p -= RARITY_TAME_PENALTY.get(tr["rarity"], 0.0)
    p += classes.tame_bonus(conn, player.id)
    from engine.systems import beast_eggs
    p += beast_eggs.tame_bonus(conn, npc.id)
    wounded = conn.execute("SELECT 1 FROM injuries WHERE character_type='npc' AND character_id=? "
                           "AND healed=0;", (npc.id,)).fetchone()
    if wounded:
        p += 0.20
    if tr["ability"] == "drago" and destinies.flag_value(conn, "dragon_blood", player.id, False):
        p += 0.30
    p = max(0.02, min(0.95, p))
    if rng.random() < p:
        bonds.add_bond(conn, player.id, npc.id, "beast", t, reason="l'hai domata")
        conn.execute("UPDATE npcs SET faction_id=NULL, hunting=0 WHERE id=?;", (npc.id,))
        state.grant_title(conn, f"Domatore di {tr['species']}") if tr["rarity"] != "comune" else None
        return (f"Tendi la mano. {npc.name} ti fissa a lungo… poi abbassa il capo. È tua.\n"
                f"Talento: {tr['talent']}; elemento: {tr['elements']}"
                + (f"; rarità: {tr['rarity']}" if tr["rarity"] != "comune" else "")
                + ". Ti seguirà e combatterà con te."), None
    return (f"{npc.name} si ribella al tuo tentativo e ti attacca!"
            + (" (Ferirla prima rende più facile domarla.)" if not wounded else "")), f"attack {npc.name}"


def release(conn, t: int, player) -> str:
    from engine.systems import bonds
    pt = pet(conn, player.id)
    if not pt:
        return "Non hai bestie con te."
    bonds.end_bond(conn, player.id, pt["npc_id"], "beast", "liberata")
    return f"Liberi {pt['name']}: torna alla natura selvaggia."


def feed(conn, player) -> str:
    from engine.systems import npc_factory, professions
    pt = pet(conn, player.id)
    if not pt:
        return "Non hai bestie da nutrire."
    if not professions.spend(conn, player.id, {"nuclei": 1}):
        return "Non hai nuclei di bestia ('raccogli' nelle zone selvagge, o caccia creature)."
    tr = traits(conn, pt["npc_id"])
    stages = max(1, round(2 * TALENT_MULT.get(tr["talent"], 1.0)))
    npc_factory.raise_npc(conn, pt["npc_id"], stages)
    return f"{pt['name']} divora il nucleo con avidità e si fa più forte (+{stages} strati)."


def describe(conn, player) -> str:
    from engine.simulation import cultivation
    pt = pet(conn, player.id)
    lines = []
    if pt:
        tr = traits(conn, pt["npc_id"])
        lines.append(f"La tua bestia: {pt['name']} — {cultivation.realm_label(conn, 'npc', pt['npc_id'])}")
        lines.append(f"  Talento {tr['talent']}, elemento {tr['elements']}"
                     + (f", rarità {tr['rarity']}" if tr["rarity"] != "comune" else "")
                     + (", RINASCITA (ti salva da un colpo mortale per scontro)" if tr["ability"] == "rinascita" else "")
                     + ". 'feed' per nutrirla con un nucleo, 'release' per liberarla.")
    else:
        lines.append("Non hai una bestia. Domane una con 'tame <nome>' (ferirla prima aiuta).")
    rares = active_rare(conn)
    if rares:
        lines.append("Avvistamenti di bestie rare:")
        lines += [f"  · {r['name']} ({r['rarity']}) — a {r['loc'] or 'luogo ignoto'}" for r in rares]
    return "\n".join(lines)


# ============================================================
# In combattimento
# ============================================================

def combat_allies(conn, player_id: int, npc_id: int, fx) -> list[dict]:
    out = []
    for pt in pets(conn, player_id):
        a = combat_ally(conn, player_id, npc_id, fx, pt)
        if a:
            out.append(a)
    return out


def combat_ally(conn, player_id: int, npc_id: int, fx, pt=None) -> dict | None:
    from engine.simulation import combat
    from engine.systems import combat_states, classes
    pt = pt or pet(conn, player_id)
    if not pt or pt["npc_id"] == npc_id:
        return None
    p = entities.get_player(conn, player_id)
    if pt["location_id"] != p.location_id:
        return None
    tr = traits(conn, pt["npc_id"])
    mult = TALENT_MULT.get(tr["talent"], 1.0)
    atk = (combat.combat_power(conn, "npc", pt["npc_id"])["attack"] * 0.55 * mult
           * classes.tamer_mult(conn, player_id, tr["elements"]))
    for el in (tr["elements"] or "").split(","):
        st = combat_states.STATE_OF_DAO.get(el)
        if st:
            fx.add_proc("p", st, 0.15 + 0.05 * mult, 1.0 + 0.2 * mult, f"bestia:{el}")
    if tr["ability"] == "rinascita":
        fx.p.lethal_saves += 1
    return {"intro": f"{pt['name']} ruggisce al tuo fianco.", "attack": atk,
            "line": f"{pt['name']} " + random.choice(
                ["azzanna il nemico.", "si avventa con furia.", "colpisce con gli artigli.",
                 "scatena la forza del suo elemento."])}
