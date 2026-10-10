"""
CICLO DEI CINQUE ELEMENTI (五行), FUSIONI ELEMENTALI e FUSIONI LEGGENDARIE.

Ispirato al Wu Xing dei giochi di coltivazione (Amazing Cultivation Simulator, Yi Xian)
e ai "duo boon" dei roguelike: i Dao non sono più solo numeri che si sommano, ma
INTERAGISCONO.

  - GENERAZIONE: Legno → Fuoco → Terra → Metallo → Acqua → Legno.
    Possedere elementi CONSECUTIVI forma una CATENA: 2, 3, 4 o tutti e 5 gli elementi.
    Ogni catena ha un nome e potenzia la tua tecnica (fusioni a 3+ elementi).
  - DISTRUZIONE: Legno ⊣ Terra, Terra ⊣ Acqua, Acqua ⊣ Fuoco, Fuoco ⊣ Metallo, Metallo ⊣ Legno
    (e Luce ⊣ Oscurità ⊣ Luce). Contro un nemico il cui Dao dominante è "distrutto" dal
    tuo, colpisci più forte; viceversa soffri. Dentro di te, due elementi in conflitto
    senza l'elemento-ponte che li concilia ti indeboliscono un poco.
  - FUSIONI LEGGENDARIE: combinazioni con nome di 2, 3 o più Dao precisi (anche non
    elementali e superiori), ciascuna con un effetto unico.
  - DOMINIO: un Dao al grado "dominatore" apre un campo che applica il suo stato a ogni
    scambio.

Il modulo è puro calcolo: legge i Dao dal DB e restituisce un profilo di bonus che il
combattimento (combat_states.py) applica.
"""

from __future__ import annotations

import sqlite3

CYCLE = ["legno", "fuoco", "terra", "metallo", "acqua"]
OVERCOMES = {"legno": "terra", "terra": "acqua", "acqua": "fuoco", "fuoco": "metallo",
             "metallo": "legno", "luce": "oscurita", "oscurita": "luce"}
ELEMENT_LABEL = {"legno": "Legno", "fuoco": "Fuoco", "terra": "Terra", "metallo": "Metallo",
                 "acqua": "Acqua", "luce": "Luce", "oscurita": "Oscurità", "vento": "Vento",
                 "fulmine": "Fulmine"}

ELEMENT_MIN = 10          # comprensione minima perché un elemento "conti" nella fusione
LEGEND_MIN = 25           # comprensione minima per le fusioni leggendarie (salvo indicato)
DOMAIN_IDX = 6            # indice di soglia "dominatore" (comprensione 500)

# catene di GENERAZIONE: nome per insieme di elementi consecutivi
CHAIN_NAMES = {
    frozenset({"legno", "fuoco"}): "Legna che Arde",
    frozenset({"fuoco", "terra"}): "Cenere Fertile",
    frozenset({"terra", "metallo"}): "Vena d'Acciaio",
    frozenset({"metallo", "acqua"}): "Rugiada di Ferro",
    frozenset({"acqua", "legno"}): "Pioggia di Primavera",
    frozenset({"legno", "fuoco", "terra"}): "Vulcano Vivente",
    frozenset({"fuoco", "terra", "metallo"}): "Forgia del Cielo",
    frozenset({"terra", "metallo", "acqua"}): "Sorgente Minerale",
    frozenset({"metallo", "acqua", "legno"}): "Foresta di Lame Gelide",
    frozenset({"acqua", "legno", "fuoco"}): "Ciclo della Vita",
    frozenset({"legno", "fuoco", "terra", "metallo"}): "Arsenale della Terra Ardente",
    frozenset({"fuoco", "terra", "metallo", "acqua"}): "Marea d'Acciaio Fuso",
    frozenset({"terra", "metallo", "acqua", "legno"}): "Giardino di Giada",
    frozenset({"metallo", "acqua", "legno", "fuoco"}): "Tempesta di Fiori di Fuoco",
    frozenset({"acqua", "legno", "fuoco", "terra"}): "Montagna che Respira",
    frozenset(CYCLE): "Ciclo Perfetto dei Cinque Elementi",
}
# bonus per lunghezza della catena: (attacco aggiuntivo, moltiplicatore probabilità degli stati)
CHAIN_BONUS = {1: (0.0, 1.0), 2: (0.08, 1.10), 3: (0.20, 1.25), 4: (0.35, 1.40), 5: (0.60, 1.70)}

# FUSIONI LEGGENDARIE: (chiave, nome, requisiti {dao: comprensione}, effetti, descrizione)
# effetti: attack (+% attacco), pierce, extra_strikes, taken (riduzione danno subito),
#   state_chance {stato: +prob}, state_power {stato: ×}, special [..]
LEGENDARY = [
    ("tempesta_tuono", "Tempesta del Tuono", {"fulmine": 25, "acqua": 25},
     {"state_chance": {"stordimento": 0.20}}, "l'acqua conduce il fulmine: stordisci molto più spesso"),
    ("incendio", "Incendio Danzante", {"fuoco": 25, "vento": 25},
     {"state_power": {"ustione": 2.0}, "state_chance": {"ustione": 0.10}}, "il vento alimenta le fiamme: ustioni doppie"),
    ("taglio_vuoto", "Taglio del Vuoto", {"spada": 25, "spazio": 25},
     {"pierce": 0.35}, "la lama taglia lo spazio stesso: le difese contano poco"),
    ("ritorno_fato", "Ritorno del Fato", {"tempo": 25, "destino": 25},
     {"special": ["survive_lethal"]}, "una volta per scontro, il colpo mortale non è mai accaduto"),
    ("adamante", "Corpo d'Adamante", {"corpo": 25, "terra": 25},
     {"taken": 0.20, "state_power": {"scudo": 1.5}}, "corpo e montagna: subisci molto meno"),
    ("lama_fulmine", "Lama del Fulmine", {"spada": 25, "fulmine": 25},
     {"extra_strikes": 1, "state_chance": {"stordimento": 0.08}}, "fendenti rapidi come saette"),
    ("luna_nera", "Luna Nera", {"oscurita": 25, "anima": 25},
     {"state_chance": {"pressione": 0.15, "drenaggio": 0.10}}, "l'ombra schiaccia lo spirito e ne beve la forza"),
    ("sole_nascente", "Sole Nascente", {"luce": 25, "fuoco": 25},
     {"state_chance": {"accecamento": 0.15, "ustione": 0.10}}, "acceca e incendia"),
    ("albero_eterno", "Albero Eterno", {"legno": 25, "corpo": 25},
     {"state_power": {"rigenerazione": 2.0}}, "il corpo rinasce come un albero potato"),
    ("marea_gelo", "Marea del Gelo", {"acqua": 25, "vento": 25},
     {"state_chance": {"gelo": 0.15}}, "il vento gela l'acqua: il nemico si irrigidisce"),
    # --- tre o più ---
    ("tifone", "Tifone Celeste", {"acqua": 25, "vento": 25, "fulmine": 25},
     {"extra_strikes": 1, "state_chance": {"stordimento": 0.15, "gelo": 0.10}}, "acqua, vento e tuono in un'unica tempesta"),
    ("inferno_tuono", "Inferno del Tuono", {"fuoco": 25, "fulmine": 25, "vento": 25},
     {"attack": 0.25, "state_power": {"ustione": 1.5}}, "un uragano di fiamme e folgori"),
    ("trinita", "Trinità Profonda", {"spazio": 25, "tempo": 25, "destino": 25},
     {"pierce": 0.30, "attack": 0.25, "special": ["survive_lethal"]}, "Spazio, Tempo e Destino piegati insieme"),
    ("caos_primordiale", "Caos Primordiale", {"luce": 50, "oscurita": 50, "anima": 50},
     {"attack": 0.50, "state_chance": {"*": 0.10}}, "gli opposti uniti: ogni stato diventa più probabile"),
    ("sette_spade", "Formazione delle Sette Lame", {"spada": 50, "metallo": 25, "vento": 25},
     {"extra_strikes": 2, "pierce": 0.15}, "sette lame d'intento ruotano attorno a te"),
    # --- con i Dao superiori ---
    ("giudizio", "Giudizio del Cielo", {"karma": 25, "fulmine": 25},
     {"state_power": {"retribuzione": 2.0}, "state_chance": {"stordimento": 0.10}}, "il fulmine colpisce chi ha peccato"),
    ("samsara_eterno", "Samsara Eterno", {"samsara": 25, "vita_morte": 25},
     {"special": ["survive_lethal", "survive_lethal_2"]}, "la ruota non si ferma: due volte risorgi nello scontro"),
    ("taiji_caos", "Taiji del Caos", {"yinyang": 25, "caos": 25},
     {"attack": 0.60, "state_chance": {"*": 0.12}}, "dal Wuji al Taiji: la fusione di ogni cosa"),
    ("fiume_sangue", "Fiume di Sangue", {"sangue": 25, "massacro": 25},
     {"state_power": {"drenaggio": 2.0, "emorragia": 1.5}}, "ogni ferita nutre la successiva"),
    ("sogno_stelle", "Sogno delle Stelle", {"illusione": 25, "stelle": 25},
     {"state_chance": {"confusione": 0.15}, "crit": 0.15}, "il nemico colpisce costellazioni che non esistono"),
    ("genesi", "Genesi", {"creazione": 25, "legno": 25, "terra": 25},
     {"state_power": {"rigenerazione": 2.0, "scudo": 2.0}}, "plasmi carne e pietra mentre combatti"),
    ("cancellazione", "Cancellazione", {"vuoto": 25, "spazio": 50},
     {"pierce": 0.50, "special": ["nullify"]}, "annulli difese, scudi e doni del nemico"),
]


# ============================================================
# Lettura dei Dao
# ============================================================

def _daos(conn: sqlite3.Connection, ctype: str, cid: int) -> dict[str, int]:
    return {r["dao_key"]: (r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type=? AND character_id=?;", (ctype, cid))}


def longest_chain(owned: set[str]) -> list[str]:
    """La catena di generazione più lunga tra gli elementi posseduti (ciclica)."""
    if set(CYCLE) <= owned:
        return list(CYCLE)
    best: list[str] = []
    for i in range(5):
        chain = []
        for j in range(5):
            e = CYCLE[(i + j) % 5]
            if e in owned:
                chain.append(e)
            else:
                break
        if len(chain) > len(best):
            best = chain
    return best


def conflicts(owned: set[str]) -> list[tuple[str, str, str]]:
    """Coppie in conflitto (a distrugge b) senza l'elemento-ponte che le concilia.
    Nel ciclo, a → ponte → b: il ponte è generato da a e genera b."""
    out = []
    for a in CYCLE:
        b = OVERCOMES[a]
        if a in owned and b in owned:
            bridge = CYCLE[(CYCLE.index(a) + 1) % 5]
            if bridge not in owned:
                out.append((a, b, bridge))
    return out


def dominant_element(conn, ctype: str, cid: int) -> str | None:
    d = _daos(conn, ctype, cid)
    cands = [(c, k) for k, c in d.items() if k in OVERCOMES and c >= ELEMENT_MIN]
    if not cands:
        # gli NPC deboli: conta comunque il loro Dao primario
        cands = [(c, k) for k, c in d.items() if k in OVERCOMES and c > 0]
    return max(cands)[1] if cands else None


_FEM = {"terra", "acqua", "luce", "oscurita"}


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _poss(el: str, who: str) -> str:
    """'il tuo Fuoco', 'la sua Acqua'."""
    if el in _FEM:
        return f"la {'tua' if who == 'tuo' else 'sua'} {ELEMENT_LABEL[el]}"
    return f"il {who} {ELEMENT_LABEL[el]}"


def matchup(conn, player_id: int, npc_id: int) -> tuple[float, float, str | None]:
    """(moltiplicatore tuo, moltiplicatore suo, frase) dal ciclo di distruzione."""
    mine = dominant_element(conn, "player", player_id)
    theirs = dominant_element(conn, "npc", npc_id)
    if not mine or not theirs:
        return 1.0, 1.0, None
    if OVERCOMES.get(mine) == theirs:
        return 1.25, 1.0, (f"{_cap(_poss(mine, 'tuo'))} sovrasta {_poss(theirs, 'suo')}: "
                           f"colpisci più a fondo.")
    if OVERCOMES.get(theirs) == mine:
        return 1.0, 1.25, (f"{_cap(_poss(theirs, 'suo'))} sovrasta {_poss(mine, 'tuo')}: "
                           f"attento.")
    return 1.0, 1.0, None


# ============================================================
# Profilo di fusione
# ============================================================

def profile(conn: sqlite3.Connection, ctype: str, cid: int) -> dict:
    """Bonus elementali e leggendari di un personaggio."""
    from engine.systems import dao_training as dt
    d = _daos(conn, ctype, cid)
    owned = {k for k in CYCLE if d.get(k, 0) >= ELEMENT_MIN}
    chain = longest_chain(owned)
    n = len(chain)
    atk, chance_mult = CHAIN_BONUS.get(n, (0.0, 1.0))
    prof = {"attack": atk, "pierce": 0.0, "extra_strikes": 0, "taken": 0.0, "crit": 0.0,
            "chance_mult": chance_mult, "state_chance": {}, "state_power": {}, "special": set(),
            "chain": chain, "chain_name": CHAIN_NAMES.get(frozenset(chain)) if n >= 2 else None,
            "conflicts": conflicts(owned), "legendary": [], "domains": []}
    prof["attack"] -= 0.06 * len(prof["conflicts"])
    if n == 5:
        prof["special"].add("cycle_states")          # ogni scambio: uno stato del ciclo
    for key, name, req, eff, _desc in LEGENDARY:
        if all(d.get(k, 0) >= v for k, v in req.items()):
            prof["legendary"].append(name)
            prof["attack"] += eff.get("attack", 0.0)
            prof["pierce"] += eff.get("pierce", 0.0)
            prof["extra_strikes"] += eff.get("extra_strikes", 0)
            prof["taken"] += eff.get("taken", 0.0)
            prof["crit"] += eff.get("crit", 0.0)
            for st, v in eff.get("state_chance", {}).items():
                prof["state_chance"][st] = prof["state_chance"].get(st, 0.0) + v
            for st, v in eff.get("state_power", {}).items():
                prof["state_power"][st] = prof["state_power"].get(st, 1.0) * v
            prof["special"].update(eff.get("special", []))
    for k, c in d.items():
        if dt._tier_index(c) >= DOMAIN_IDX:
            prof["domains"].append(k)
    return prof


def describe(conn: sqlite3.Connection, player_id: int = 1) -> list[str]:
    """Righe per i comandi 'dao'/'techniques': fusioni attive e quelle a portata."""
    d = _daos(conn, "player", player_id)
    pr = profile(conn, "player", player_id)
    lines = []
    owned = [ELEMENT_LABEL[e] for e in CYCLE if d.get(e, 0) >= ELEMENT_MIN]
    lines.append("Ciclo dei Cinque Elementi (Legno→Fuoco→Terra→Metallo→Acqua→Legno): "
                 + (", ".join(owned) if owned else "nessun elemento ancora (serve comprensione ≥10)"))
    if pr["chain_name"]:
        lines.append(f"  ☯ Catena di {len(pr['chain'])} elementi: «{pr['chain_name']}» "
                     f"(+{int(CHAIN_BONUS[len(pr['chain'])][0]*100)}% attacco, stati più frequenti)")
    for a, b, bridge in pr["conflicts"]:
        lines.append(f"  ⚠ {ELEMENT_LABEL[a]} e {ELEMENT_LABEL[b]} si combattono dentro di te "
                     f"(-6%): il {ELEMENT_LABEL[bridge]} li concilierebbe.")
    if pr["legendary"]:
        lines.append("  ✦ Fusioni leggendarie attive: " + ", ".join(pr["legendary"]))
    near = []
    for key, name, req, _eff, desc in LEGENDARY:
        if name in pr["legendary"]:
            continue
        have = sum(1 for k, v in req.items() if d.get(k, 0) >= v)
        started = sum(1 for k in req if d.get(k, 0) > 0)
        if have >= len(req) - 1 and started == len(req):
            missing = [f"{k} {d.get(k, 0)}/{v}" for k, v in req.items() if d.get(k, 0) < v]
            near.append(f"{name} — {desc} (manca: {', '.join(missing)})")
    if near:
        lines.append("  Fusioni a portata di mano:")
        lines += [f"    · {x}" for x in near[:5]]
    if pr["domains"]:
        lines.append("  ◎ Domini aperti: " + ", ".join(pr["domains"]))
    return lines
