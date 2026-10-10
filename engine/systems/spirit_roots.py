"""
RADICI SPIRITUALI (灵根) — punteggi per elemento, talenti, e combinazioni.

Ogni coltivatore nasce con alcune radici: Legno, Fuoco, Terra, Metallo, Acqua, Fulmine,
Vento, Luce, Oscurità. Ogni radice ha un PUNTEGGIO senza tetto.

1) PUNTEGGIO → GRADO (infinito)
     <20 Grezza · 20 Comune · 40 Buona · 70 Eccellente · 100 Celeste · 200 Divina ·
     400 Primordiale · poi ogni raddoppio sale di un "Grado del Caos" (all'infinito).

2) PUNTEGGIO → TALENTO
     Ogni radice dal grado Eccellente in su genera un TALENTO del suo elemento
     (es. Fuoco → "Sangue della Fenice"), che si potenzia a ogni grado:
       - coltivazione più rapida (la radice più forte pesa di più)
       - comprensione più rapida dei Dao affini (Fuoco → Dao del Fuoco, Metallo → Spada…)
       - in combattimento, lo stato del suo elemento scatta più spesso e più forte

3) PIÙ RADICI → COMBINAZIONI (tutte le 511 combinazioni possibili hanno un effetto)
     Gli effetti si calcolano da regole, così OGNI sottoinsieme di radici attive (≥ 20)
     produce qualcosa — con un nome, se esiste:
       - GENERAZIONE (Legno→Fuoco→Terra→Metallo→Acqua→Legno): ogni coppia che si genera
         dà coltivazione e attacco; le catene di 3, 4, 5 hanno nomi propri e bonus crescenti.
       - DISTRUZIONE: due radici in conflitto rallentano la coltivazione… a meno che tu non
         possieda l'elemento-PONTE che le concilia: allora il conflitto diventa potenza.
       - COPPIE SPECIALI: Fulmine+Vento (Tempesta), Fulmine+Acqua (Tuono Marino),
         Luce+Oscurità (Yin e Yang: fortissimo se equilibrate), Vento+Fuoco, ecc.
       - NUMERO: più radici armonizzate hai, più l'insieme vale (Armonia di N Radici);
         i 5 elementi completi formano il CORPO DEI CINQUE ELEMENTI; tutte e 9 la
         RADICE DEL CAOS PRIMORDIALE.
     L'intensità di ogni combinazione cresce con il punteggio della radice più debole
     coinvolta: migliorare le radici migliora le combinazioni, senza limite.

4) CRESCITA
     - Il DIVORATORE si nutre delle radici delle vittime: ogni assorbimento ne travasa una
       parte nelle tue (anche radici che non avevi). Cresce all'infinito.
     - Ogni nuovo regno affina tutte le radici (+10%).
     - Illuminazioni, pillole e tesori rari possono farle crescere.
"""

from __future__ import annotations

import math
import random
import sqlite3
from itertools import combinations

ELEMENTS = ["legno", "fuoco", "terra", "metallo", "acqua", "fulmine", "vento", "luce", "oscurita"]
LABEL = {"legno": "Legno", "fuoco": "Fuoco", "terra": "Terra", "metallo": "Metallo", "acqua": "Acqua",
         "fulmine": "Fulmine", "vento": "Vento", "luce": "Luce", "oscurita": "Oscurità"}
CYCLE = ["legno", "fuoco", "terra", "metallo", "acqua"]
DAL = {"legno": "dal Legno", "fuoco": "dal Fuoco", "terra": "dalla Terra", "metallo": "dal Metallo",
       "acqua": "dall'Acqua", "fulmine": "dal Fulmine", "vento": "dal Vento", "luce": "dalla Luce",
       "oscurita": "dall'Oscurità"}
ACTIVE = 20                      # una radice "conta" nelle combinazioni da 20 in su

# quale radice nutre quale Dao
ROOT_OF_DAO = {e: e for e in ELEMENTS}
ROOT_OF_DAO.update({"spada": "metallo", "sciabola": "metallo", "lancia": "metallo", "arco": "vento",
                    "pugno": "terra", "bastone": "legno", "corpo": "terra", "anima": "luce",
                    "spazio": "vento", "tempo": "acqua", "destino": "luce", "sangue": "fuoco",
                    "massacro": "metallo", "vita_morte": "legno", "samsara": "acqua",
                    "yinyang": "luce", "caos": "oscurita", "illusione": "oscurita",
                    "stelle": "luce", "vuoto": "oscurita", "creazione": "terra", "karma": "luce"})

# talento generato da una radice forte, per elemento (nome, stato in combattimento)
TALENTS = {
    "legno": ("Cuore dell'Albero Eterno", "rigenerazione"),
    "fuoco": ("Sangue della Fenice", "ustione"),
    "terra": ("Ossa della Montagna", "scudo"),
    "metallo": ("Meridiani di Spada", "emorragia"),
    "acqua": ("Vene dell'Abisso Marino", "gelo"),
    "fulmine": ("Corpo del Tuono", "stordimento"),
    "vento": ("Passo del Vento Errante", "velocita"),
    "luce": ("Occhio del Sole", "accecamento"),
    "oscurita": ("Ombra che Divora", "drenaggio"),
}
GRADES = [(0, "Grezza"), (20, "Comune"), (40, "Buona"), (70, "Eccellente"), (100, "Celeste"),
          (200, "Divina"), (400, "Primordiale")]

SPECIAL_PAIRS = {
    frozenset({"fulmine", "vento"}): ("Tempesta Errante", {"attack": 0.06, "strike": 0.05}),
    frozenset({"fulmine", "acqua"}): ("Tuono Marino", {"attack": 0.05, "state": 0.06}),
    frozenset({"fuoco", "vento"}): ("Incendio nel Vento", {"attack": 0.07}),
    frozenset({"acqua", "vento"}): ("Bufera di Gelo", {"state": 0.07}),
    frozenset({"luce", "fuoco"}): ("Sole Ardente", {"attack": 0.05, "state": 0.04}),
    frozenset({"oscurita", "acqua"}): ("Abisso Silente", {"taken": 0.05, "state": 0.04}),
    frozenset({"luce", "oscurita"}): ("Yin e Yang", {}),          # speciale: dipende dall'equilibrio
    frozenset({"fulmine", "metallo"}): ("Lama Folgorante", {"attack": 0.06}),
    frozenset({"legno", "luce"}): ("Germoglio Celeste", {"cult": 0.06}),
    frozenset({"terra", "oscurita"}): ("Tomba Nera", {"taken": 0.06}),
}


# ============================================================
# Tabella e lettura
# ============================================================

def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS spirit_roots ("
                 "character_type TEXT NOT NULL, character_id INTEGER NOT NULL, "
                 "element TEXT NOT NULL, score REAL NOT NULL DEFAULT 0, "
                 "PRIMARY KEY (character_type, character_id, element));")


def grade_index(score: float) -> int:
    if score < 400:
        idx = 0
        for i, (th, _n) in enumerate(GRADES):
            if score >= th:
                idx = i
        return idx
    return 6 + int(math.log2(score / 400.0))


def grade_name(score: float) -> str:
    i = grade_index(score)
    if i < len(GRADES):
        return GRADES[i][1]
    return f"del Caos di {i - 6}° Grado"


def _generate_player(conn, cid: int) -> dict[str, float]:
    """Radici di nascita, dal talento di coltivazione e dai Dao già posseduti."""
    from engine.systems import character
    p = character.get_profile(conn, "player", cid)
    aff = (p["aff_cultivation"] if p and p["aff_cultivation"] is not None else 50)
    seed = (aff * 7919 + cid * 31 + (p["age"] if p and p["age"] else 16))
    rng = random.Random(seed)
    roots: dict[str, float] = {}
    for d in conn.execute("SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' "
                          "AND character_id=? AND (practiced=1 OR comprehension>0);", (cid,)):
        el = ROOT_OF_DAO.get(d["dao_key"])
        if el:
            roots[el] = max(roots.get(el, 0), 15 + aff * 0.25)
    n = 1 + (1 if aff >= 40 else 0) + (1 if rng.random() < 0.5 else 0) + (1 if rng.random() < 0.25 else 0)
    budget = aff * 1.3
    for el in rng.sample(ELEMENTS, n):
        roots[el] = roots.get(el, 0) + budget / n * rng.uniform(0.6, 1.4)
    return {k: round(v, 1) for k, v in roots.items()}


def _generate_npc(conn, cid: int) -> dict[str, float]:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "npc", cid) or 1
    rng = random.Random(cid * 104729)
    roots: dict[str, float] = {}
    for d in conn.execute("SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' "
                          "AND character_id=?;", (cid,)):
        el = ROOT_OF_DAO.get(d["dao_key"])
        if el:
            roots[el] = roots.get(el, 0) + 10 + (d["comprehension"] or 0) * 0.3 + tier * 4
    try:
        bt = conn.execute("SELECT elements FROM beast_traits WHERE npc_id=?;", (cid,)).fetchone()
    except sqlite3.OperationalError:
        bt = None
    if bt and bt["elements"]:
        for el in bt["elements"].split(","):
            if el in ELEMENTS:
                roots[el] = roots.get(el, 0) + 15 + tier * 8
    for el in rng.sample(ELEMENTS, 1 + rng.randint(0, 2)):
        roots[el] = roots.get(el, 0) + rng.uniform(10, 30) + tier * 6
    return {k: round(v, 1) for k, v in roots.items()}


def get(conn, ctype: str, cid: int) -> dict[str, float]:
    ensure_table(conn)
    rows = conn.execute("SELECT element, score FROM spirit_roots WHERE character_type=? AND character_id=?;",
                        (ctype, cid)).fetchall()
    if rows:
        return {r["element"]: r["score"] for r in rows}
    roots = _generate_player(conn, cid) if ctype == "player" else _generate_npc(conn, cid)
    if ctype == "player":                    # gli NPC si calcolano al volo, senza riempire il DB
        for el, sc in roots.items():
            conn.execute("INSERT OR REPLACE INTO spirit_roots VALUES ('player', ?, ?, ?);", (cid, el, sc))
    return roots


def add(conn, ctype: str, cid: int, element: str, amount: float) -> float:
    ensure_table(conn)
    get(conn, ctype, cid)
    conn.execute("INSERT INTO spirit_roots VALUES (?, ?, ?, ?) ON CONFLICT(character_type, character_id, "
                 "element) DO UPDATE SET score=score+excluded.score;", (ctype, cid, element, amount))
    return conn.execute("SELECT score FROM spirit_roots WHERE character_type=? AND character_id=? "
                        "AND element=?;", (ctype, cid, element)).fetchone()["score"]


def refine_all(conn, cid: int, frac: float) -> None:
    get(conn, "player", cid)
    conn.execute("UPDATE spirit_roots SET score=score*? WHERE character_type='player' AND character_id=?;",
                 (1.0 + frac, cid))


# ============================================================
# Combinazioni (tutte, generate da regole)
# ============================================================

def _intensity(scores: list[float]) -> float:
    """Quanto 'vale' una combinazione: cresce col punteggio della radice più debole (senza tetto)."""
    m = min(scores)
    return 1.0 + math.log2(1.0 + m / 50.0)


def _gen_pair(a: str, b: str) -> bool:
    if a in CYCLE and b in CYCLE:
        ia, ib = CYCLE.index(a), CYCLE.index(b)
        return (ia + 1) % 5 == ib or (ib + 1) % 5 == ia
    return False


def _overcome_pair(a: str, b: str) -> tuple[str, str] | None:
    from engine.systems.elements import OVERCOMES
    if OVERCOMES.get(a) == b and a in CYCLE:
        return a, b
    if OVERCOMES.get(b) == a and b in CYCLE:
        return b, a
    return None


def _bridge(winner: str, loser: str) -> str:
    """L'elemento che concilia: generato da chi vince, genera chi perde (Legno ⊣ Terra: Fuoco)."""
    return CYCLE[(CYCLE.index(winner) + 1) % 5]


def _chains(active: set[str]) -> list[frozenset]:
    """Le catene di generazione massimali (elementi consecutivi del ciclo) presenti."""
    from engine.systems.elements import CHAIN_NAMES
    cyc = [e for e in CYCLE if e in active]
    if len(cyc) == 5:
        return [frozenset(CYCLE)]
    out = []
    for start in range(5):
        if CYCLE[start] not in active or CYCLE[(start - 1) % 5] in active:
            continue
        run = []
        i = start
        while CYCLE[i % 5] in active and len(run) < 5:
            run.append(CYCLE[i % 5])
            i += 1
        if len(run) >= 2 and frozenset(run) in CHAIN_NAMES:
            out.append(frozenset(run))
    return out


def combinations_of(roots: dict[str, float]) -> list[dict]:
    """Elenco degli effetti di combinazione attivi: [{name, kind, cult, attack, taken, state, strike, bt}]."""
    from engine.systems.elements import CHAIN_NAMES
    active = {e for e, s in roots.items() if s >= ACTIVE}
    out: list[dict] = []
    if len(active) < 2:
        return out
    # catene di generazione con nome (2..5)
    chained_pairs = set()
    for ch in _chains(active):
        n = len(ch)
        k = _intensity([roots[e] for e in ch])
        bonus = {2: 0.06, 3: 0.15, 4: 0.28, 5: 0.5}[n]
        out.append({"name": CHAIN_NAMES[ch], "kind": f"catena di {n}",
                    "cult": bonus * k, "attack": bonus * 0.6 * k, "state": 0.02 * n * k,
                    "elements": sorted(ch, key=CYCLE.index)})
        for a, b in combinations(ch, 2):
            if _gen_pair(a, b):
                chained_pairs.add(frozenset({a, b}))
    if active >= set(CYCLE):
        k = _intensity([roots[e] for e in CYCLE])
        out.append({"name": "Corpo dei Cinque Elementi", "kind": "ciclo completo",
                    "cult": 0.25 * k, "taken": 0.06 * k, "bt": 0.05 * k, "elements": list(CYCLE)})
    # coppie: conflitti, conflitti conciliati, coppie speciali
    for a, b in combinations(sorted(active), 2):
        pair = frozenset({a, b})
        k = _intensity([roots[a], roots[b]])
        ov = _overcome_pair(a, b)
        if ov:
            w, l = ov
            br = _bridge(w, l)
            if br in active:
                out.append({"name": f"{LABEL[w]} e {LABEL[l]} conciliati {DAL[br]}",
                            "kind": "conflitto domato", "attack": 0.05 * k, "state": 0.03 * k,
                            "elements": [w, l, br]})
            else:
                out.append({"name": f"{LABEL[w]} contro {LABEL[l]}", "kind": "conflitto",
                            "cult": -0.04, "attack": 0.02 * k, "elements": [w, l]})
        if pair in SPECIAL_PAIRS:
            nm, eff = SPECIAL_PAIRS[pair]
            d = {"name": nm, "kind": "coppia speciale", "elements": sorted(pair)}
            if pair == frozenset({"luce", "oscurita"}):
                bal = min(roots[a], roots[b]) / max(roots[a], roots[b])
                d.update({"cult": 0.10 * bal * k, "attack": 0.10 * bal * k, "taken": 0.05 * bal * k})
                d["kind"] = f"equilibrio {int(bal * 100)}%"
            else:
                for key, v in eff.items():
                    d[key] = v * k
            out.append(d)
    # numero di radici armonizzate (vale per qualunque insieme)
    n = len(active)
    k = _intensity([roots[e] for e in active])
    name = {2: "Radice Doppia", 3: "Radice Tripla", 4: "Radice Quadrupla", 5: "Radice Quintupla",
            6: "Radice dei Sei Venti", 7: "Radice delle Sette Stelle", 8: "Radice degli Otto Trigrammi",
            9: "Radice del Caos Primordiale"}[n]
    harm = {"name": name, "kind": f"{n} radici", "cult": 0.03 * (n - 1) * k, "state": 0.01 * n * k,
            "elements": sorted(active, key=ELEMENTS.index)}
    if n == 9:
        harm.update({"attack": 0.3 * k, "taken": 0.1 * k, "bt": 0.1 * k})
    out.append(harm)
    return out


# ============================================================
# Effetti sugli altri sistemi
# ============================================================

def _totals(roots: dict[str, float]) -> dict:
    t = {"cult": 0.0, "attack": 0.0, "taken": 0.0, "state": 0.0, "strike": 0.0, "bt": 0.0}
    for c in combinations_of(roots):
        for key in t:
            t[key] += c.get(key, 0.0)
    return t


def cultivation_mult(conn, ctype: str, cid: int) -> tuple[float, str]:
    roots = get(conn, ctype, cid)
    if not roots:
        return 1.0, ""
    sc = sorted(roots.values(), reverse=True)
    base = 0.65 + sc[0] / 200.0 + sum(sc[1:]) / 800.0
    c = _totals(roots)["cult"]
    m = max(0.5, base * (1.0 + (math.log1p(c) if c > 0 else c)))
    if abs(m - 1.0) < 0.02:
        return 1.0, ""
    return m, "le tue radici spirituali"


def dao_mult(conn, ctype: str, cid: int, dao_key: str) -> float:
    roots = get(conn, ctype, cid)
    el = ROOT_OF_DAO.get(dao_key)
    if el and el in roots:
        return 1.0 + roots[el] / 150.0
    return 1.0 + (max(roots.values()) / 1000.0 if roots else 0.0)


def breakthrough_bonus(conn, cid: int) -> float:
    return min(0.25, _totals(get(conn, "player", cid))["bt"])


def combat_profile(conn, ctype: str, cid: int) -> dict:
    roots = get(conn, ctype, cid)
    tot = _totals(roots)
    procs = []
    for el, s in roots.items():
        if grade_index(s) >= 3:                       # talento attivo
            st = TALENTS[el][1]
            gi = grade_index(s)
            procs.append((st, min(0.45, 0.06 + 0.03 * gi + tot["state"]), 1.0 + 0.15 * gi,
                          f"radice:{el}"))
    return {"attack": math.log1p(tot["attack"]), "taken": min(0.35, tot["taken"]),
            "strike": min(0.4, tot["strike"]),
            "procs": procs}


def talents_of(roots: dict[str, float]) -> list[str]:
    out = []
    for el, s in sorted(roots.items(), key=lambda x: -x[1]):
        gi = grade_index(s)
        if gi >= 3:
            nm = TALENTS[el][0]
            out.append(f"{nm}" + (f" ({gi - 2}° livello)" if gi > 3 else ""))
    return out


# ============================================================
# Divoratore: nutrirsi delle radici delle vittime
# ============================================================

def devour(conn, player_id: int, victim_id: int, freshness: float = 1.0, clean: bool = True) -> str | None:
    from engine.systems import character
    prof = character.get_profile(conn, "player", player_id)
    if prof is None or prof["anomaly"] != "abisso_divoratore":
        return None
    victim = _generate_npc(conn, victim_id)
    if not victim:
        return None
    frac = (0.25 if clean else 0.12) * max(0.3, freshness)
    mine = get(conn, "player", player_id)
    gains = []
    for el, sc in victim.items():
        g = round(sc * frac, 1)
        if g <= 0:
            continue
        before = mine.get(el, 0.0)
        after = add(conn, "player", player_id, el, g)
        gi0, gi1 = grade_index(before), grade_index(after)
        tag = f" → {grade_name(after)}!" if gi1 > gi0 else ""
        gains.append(f"{LABEL[el]} +{g:g}{tag}" if before > 0 else f"nuova radice di {LABEL[el]} ({g:g}){tag}")
    if not gains:
        return None
    return "L'Abisso succhia le radici spirituali della vittima: " + ", ".join(gains) + "."


# ============================================================
# Descrizione
# ============================================================

def describe(conn, player) -> str:
    roots = get(conn, "player", player.id)
    lines = ["☯ RADICI SPIRITUALI"]
    if not roots:
        return "Non senti alcuna radice spirituale in te."
    for el, s in sorted(roots.items(), key=lambda x: -x[1]):
        bar = "█" * min(20, int(s / 10)) or "▏"
        act = "" if s >= ACTIVE else "  (troppo debole per combinarsi)"
        lines.append(f"  {LABEL[el]:<9} {s:>8.1f}  {grade_name(s):<22} {bar}{act}")
    tal = talents_of(roots)
    if tal:
        lines.append("Talenti generati: " + ", ".join(tal))
    combos = combinations_of(roots)
    if combos:
        lines.append("Combinazioni:")
        for c in combos:
            fx = []
            if c.get("cult"):
                fx.append(f"coltivazione {c['cult'] * 100:+.0f}%")
            if c.get("attack"):
                fx.append(f"attacco {c['attack'] * 100:+.0f}%")
            if c.get("taken"):
                fx.append(f"danni subiti -{c['taken'] * 100:.0f}%")
            if c.get("state"):
                fx.append(f"stati elementali {c['state'] * 100:+.0f}%")
            if c.get("strike"):
                fx.append(f"colpi extra {c['strike'] * 100:+.0f}%")
            if c.get("bt"):
                fx.append(f"sfondamento {c['bt'] * 100:+.0f}%")
            lines.append(f"  ◇ {c['name']} [{c['kind']}]: " + ", ".join(fx))
    m, _ = cultivation_mult(conn, "player", player.id)
    lines.append(f"Velocità di coltivazione dalle radici: ×{m:.2f}")
    from engine.systems import character
    prof = character.get_profile(conn, "player", player.id)
    if prof and prof["anomaly"] == "abisso_divoratore":
        lines.append("L'Abisso in te si nutre delle radici di chi divori: crescono senza limite.")
    return "\n".join(lines)
