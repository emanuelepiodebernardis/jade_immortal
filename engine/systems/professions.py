"""
PROFESSIONI — Alchimia, Talismani, Forgia.

Come in Yi Xian (dove la professione pesa quanto la setta) e Tale of Immortal:
scegli UN'arte ('profession <nome>') e trasforma i materiali raccolti nel mondo in
pillole, talismani o armi migliori.

  Materiali (player_resources): erbe (erbe spirituali), minerali, nuclei (di bestia),
  nuclei_rari (dalle bestie rare). Si ottengono con 'gather' nelle zone selvagge e
  cacciando creature.
  Ogni creazione dà esperienza: il livello (senza tetto) sblocca ricette migliori e alza
  la riuscita e la potenza di ciò che crei.
  'recipes' mostra le ricette, 'craft <n>' crea.
"""

from __future__ import annotations

import random

from engine.systems import state

MATERIALS = {"erbe": "erbe spirituali", "minerali": "minerali", "nuclei": "nuclei di bestia",
             "nuclei_rari": "nuclei rari"}
PROFESSIONS = {"alchimia": "Alchimia", "talismani": "Talismani", "forgia": "Forgia",
               "formazioni": "Formazioni", "domatore": "Addomesticamento delle Bestie"}
_ALIASES = {"alchemy": "alchimia", "alchimista": "alchimia", "talisman": "talismani",
            "talismano": "talismani", "fulu": "talismani", "forge": "forgia", "fabbro": "forgia",
            "formazione": "formazioni", "array": "formazioni", "arrays": "formazioni", "formation": "formazioni",
            "formations": "formazioni", "domatore": "domatore", "domatori": "domatore", "tamer": "domatore",
            "bestie": "domatore", "addomesticatore": "domatore"}
XP_LEVELS = [0, 3, 8, 15, 25, 40, 60, 85, 115, 150]     # xp minima per i livelli 1..10 (poi cresce)


# ============================================================
# Stato
# ============================================================

def profession(conn, pid: int = 1) -> str | None:
    """L'arte PRINCIPALE (quella della classe, delle ricette senza nome e dei capolavori)."""
    return state.get(conn, "profession")


# Più arti insieme: 'arts_xp' = {arte: esperienza} di tutte quelle che conosci,
# 'arts_on' = quelle che stai PRATICANDO (crescono con 'train', il pilota le usa).
def _xpmap(conn) -> dict:
    m = state.get_json(conn, "arts_xp")
    if m is None:                                  # salvataggi precedenti: una sola arte
        main = state.get(conn, "profession")
        m = {main: state.get_int(conn, "profession_xp", 0)} if main else {}
        state.set_json(conn, "arts_xp", m)
        state.set_json(conn, "arts_on", [main] if main else [])
    main = state.get(conn, "profession")
    if main:                                       # chi scrive ancora 'profession_xp' (vecchi salvataggi)
        legacy = state.get_int(conn, "profession_xp", 0)
        if main not in m or legacy > int(m.get(main, 0)):
            m[main] = max(legacy, int(m.get(main, 0)))
            state.set_json(conn, "arts_xp", m)
    return m


def _set_main(conn, key: str) -> None:
    m = _xpmap(conn)
    m.setdefault(key, 0)
    state.set_json(conn, "arts_xp", m)
    state.set(conn, "profession_xp", str(int(m[key])))
    state.set(conn, "profession", key)


def known(conn, pid: int = 1) -> list[str]:
    return [k for k in PROFESSIONS if k in _xpmap(conn)]


def has(conn, key: str, pid: int = 1) -> bool:
    return key in _xpmap(conn)


def practiced(conn, pid: int = 1) -> list[str]:
    _xpmap(conn)
    on = state.get_json(conn, "arts_on", []) or []
    return [k for k in PROFESSIONS if k in on]


def set_practiced(conn, keys: list[str], pid: int = 1) -> None:
    m = _xpmap(conn)
    for k in keys:
        m.setdefault(k, 0)
    state.set_json(conn, "arts_xp", m)
    state.set_json(conn, "arts_on", [k for k in PROFESSIONS if k in keys])
    if keys and not profession(conn, pid):
        _set_main(conn, keys[0])


def xp(conn, pid: int = 1, key: str | None = None) -> int:
    key = key or profession(conn, pid)
    return int(_xpmap(conn).get(key, 0)) if key else 0


def add_xp(conn, pid: int, n: int, key: str | None = None) -> int:
    """Esperienza a un'arte (di default la principale). Ritorna il nuovo livello."""
    key = key or profession(conn, pid)
    if not key:
        return 0
    m = _xpmap(conn)
    m[key] = int(m.get(key, 0)) + int(n)
    state.set_json(conn, "arts_xp", m)
    if key == profession(conn, pid):
        state.set(conn, "profession_xp", str(m[key]))     # compatibilità
    return level(conn, pid, key)


def level(conn, pid: int = 1, key: str | None = None) -> int:
    key = key or profession(conn, pid)
    if not key or key not in _xpmap(conn):
        return 0
    from engine.systems import destinies
    return level_for_xp(xp(conn, pid, key)) + int(destinies.flag_value(conn, "crafter", pid, 0))


def best_level(conn, pid: int = 1) -> int:
    return max([level(conn, pid, k) for k in known(conn, pid)] or [0])


def total_xp(conn, pid: int = 1) -> int:
    return sum(int(v) for v in _xpmap(conn).values())


def xp_for_level(lv: int) -> int:
    """Esperienza minima per il livello lv (SENZA tetto: oltre il 10 cresce del 35% a livello)."""
    if lv <= len(XP_LEVELS):
        return XP_LEVELS[max(0, lv - 1)]
    return int(XP_LEVELS[-1] * (1.35 ** (lv - len(XP_LEVELS))))


def level_for_xp(x: int) -> int:
    lv = 1
    while xp_for_level(lv + 1) <= x:
        lv += 1
    return lv


def material(conn, pid: int, key: str) -> int:
    from engine.systems import sects
    return sects.get_resource(conn, key, pid)


def give(conn, pid: int, key: str, n: int) -> int:
    from engine.systems import sects
    return sects.grant_resource(conn, key, n, pid)


def spend(conn, pid: int, cost: dict[str, int]) -> bool:
    if any(material(conn, pid, k) < v for k, v in cost.items()):
        return False
    for k, v in cost.items():
        give(conn, pid, k, -v)
    return True


def materials_line(conn, pid: int = 1) -> str:
    return "Materiali: " + ", ".join(f"{MATERIALS[k]} {material(conn, pid, k)}" for k in MATERIALS)


def choose(conn, pid: int, raw: str) -> str:
    """'profession <arte>': impari l'arte (se nuova), la pratichi e la rendi PRINCIPALE.
    Le altre arti restano tue: niente esperienza perduta. Il menu completo è 'arti'."""
    key = _ALIASES.get(raw.strip().lower(), raw.strip().lower())
    cur = profession(conn, pid)
    if not key:
        if cur:
            return describe_menu(conn, pid)
        return ("Non pratichi ancora un'arte. Scegline una, o più d'una: 'arti alchimia' (pillole e veleni), "
                "'arti talismani' (buff di battaglia), 'arti forgia' (armi), 'arti formazioni' "
                "(formazioni elementali), 'arti domatore' (bestie) — oppure 'arti tutte'.\n"
                "Con 'sintonia <elemento>' l'arte principale diventa una classe: es. Maestro delle Formazioni della Fiamma.")
    if key not in PROFESSIONS:
        return "Arti disponibili: alchimia, talismani, forgia, formazioni, domatore."
    if cur == key and key in practiced(conn, pid):
        return f"{Art(key)} è già la tua arte principale. ('arti' per il menu)"
    new = key not in _xpmap(conn)
    set_practiced(conn, list(dict.fromkeys(practiced(conn, pid) + [key])), pid)
    _set_main(conn, key)
    msg = (f"Inizi a praticare {art(key)}" if new else f"{Art(key)} torna la tua arte principale") \
        + " (le altre arti restano tue)."
    return msg + " 'recipes' per vedere cosa puoi creare; 'arti' per il menu delle arti."


# ============================================================
# Menu delle arti
# ============================================================

ART_DESC = {"alchimia": "pillole, elisir e veleni", "talismani": "talismani di battaglia",
            "forgia": "armi e affinamenti", "formazioni": "formazioni elementali",
            "domatore": "bestie spirituali: domarle, allevarle, combatterci"}


_ART = {"alchimia": "l'Alchimia", "talismani": "i Talismani", "forgia": "la Forgia",
        "formazioni": "le Formazioni", "domatore": "l'Addomesticamento delle Bestie"}


def art(key: str) -> str:
    """Il nome dell'arte con l'articolo giusto."""
    return _ART.get(key, PROFESSIONS.get(key, key))


def Art(key: str) -> str:
    a = art(key)
    return a[0].upper() + a[1:]


def _key(raw: str) -> str | None:
    k = _ALIASES.get(raw.strip().lower(), raw.strip().lower())
    return k if k in PROFESSIONS else None


def ready_recipes(conn, pid: int, key: str) -> list[tuple[int, tuple]]:
    lv = level(conn, pid, key)
    return [(i, r) for i, r in enumerate(recipes_for(conn, pid, key), 1)
            if lv >= r[1] and all(material(conn, pid, k) >= v for k, v in r[3].items())]


def menu_data(conn, pid: int = 1) -> dict:
    main, on = profession(conn, pid), practiced(conn, pid)
    arts = []
    for k, name in PROFESSIONS.items():
        kn = has(conn, k, pid)
        lv = level(conn, pid, k)
        x = xp(conn, pid, k)
        lo, hi = (xp_for_level(lv), xp_for_level(lv + 1)) if kn else (0, 1)
        arts.append({"key": k, "nome": name, "desc": ART_DESC.get(k, ""), "conosciuta": kn,
                     "pratica": k in on, "principale": k == main, "livello": lv, "xp": x,
                     "pct": int(100 * (x - lo) / max(1, hi - lo)) if kn else 0,
                     "prossimo": hi, "pronte": len(ready_recipes(conn, pid, k)) if kn else 0,
                     "ricette": [{"n": i, "nome": r[2], "livello": r[1], "ok": lv >= r[1],
                                  "costo": ", ".join(f"{v} {MATERIALS[m]}" for m, v in r[3].items()),
                                  "pronta": lv >= r[1] and all(material(conn, pid, m) >= v for m, v in r[3].items())}
                                 for i, r in enumerate(recipes_for(conn, pid, k), 1)] if kn else []})
    return {"arti": arts, "principale": main, "pratichi": on,
            "materiali": {MATERIALS[k]: material(conn, pid, k) for k in MATERIALS}}


def describe_menu(conn, pid: int = 1) -> str:
    d = menu_data(conn, pid)
    on = [PROFESSIONS[k] for k in d["pratichi"]]
    lines = ["✦ LE TUE ARTI — " + (f"pratichi: {', '.join(on)}" if on else "non ne pratichi nessuna")
             + (f" · principale: {PROFESSIONS[d['principale']]} ★" if d["principale"] else "")]
    for i, a in enumerate(d["arti"], 1):
        if a["conosciuta"]:
            bar = "█" * (a["pct"] // 10) + "·" * (10 - a["pct"] // 10)
            st = "IN PRATICA" if a["pratica"] else "a riposo"
            lines.append(f"  {i}. {a['nome']}{' ★' if a['principale'] else ''} — livello {a['livello']} [{bar}] "
                         f"{st}" + (f" · {a['pronte']} ricette pronte" if a["pronte"] else ""))
        else:
            lines.append(f"  {i}. {a['nome']} — mai praticata ({a['desc']})")
    lines.append(materials_line(conn, pid))
    n = len(d["pratichi"])
    if n > 1:
        lines.append(f"Con {n} arti in pratica, 'train' le fa crescere tutte (ognuna un po' più piano).")
    lines.append("Comandi: arti <nome> (pratica/smetti) · arti tutte · arti nessuna · arti principale <nome> · "
                 "ricette <arte> · craft <arte> <n>")
    return "\n".join(lines)


def menu_command(conn, pid: int, arg: str) -> str:
    """'arti' — il menu delle arti: scegli quali praticare (una, alcune, tutte o nessuna)."""
    p = arg.strip().lower().split()
    if not p:
        return describe_menu(conn, pid)
    if p[0] in ("tutte", "tutti", "all"):
        set_practiced(conn, list(PROFESSIONS), pid)
        return "Pratichi tutte le arti: 'train' le farà crescere insieme (ognuna un po' più piano)."
    if p[0] in ("nessuna", "nessuno", "none", "stop"):
        set_practiced(conn, [], pid)
        return ("Metti da parte le arti: l'allenamento si concentra su Qi e Dao. Ciò che hai imparato resta tuo "
                "e puoi ancora creare ('craft <arte> <n>').")
    if p[0] in ("principale", "main", "prima") and len(p) > 1:
        k = _key(p[1])
        if not k:
            return "Arti: alchimia, talismani, forgia, formazioni, domatore."
        return choose(conn, pid, k)
    if p[0] in ("ricette", "recipes") and len(p) > 1:
        return describe_recipes(conn, pid, _key(p[1]))
    k = _key(p[0]) if p[0] not in ("pratica", "smetti") else (_key(p[1]) if len(p) > 1 else None)
    if not k:
        return describe_menu(conn, pid)
    on = practiced(conn, pid)
    stop = (p[0] == "smetti") or (p[0] != "pratica" and k in on)
    if stop:
        set_practiced(conn, [x for x in on if x != k], pid)
        return f"Smetti di praticare {art(k)} (resta tua: livello {level(conn, pid, k)})."
    new = not has(conn, k, pid)
    set_practiced(conn, on + [k], pid)
    return (f"{'Inizi a praticare' if new else 'Riprendi'} {art(k)}"
            f"{' — è la tua arte principale' if profession(conn, pid) == k else ''}.")


# ============================================================
# Raccolta
# ============================================================

_GATHER = {"mountain": {"erbe": (1, 3), "minerali": (0, 2)},
           "forbidden_zone": {"erbe": (1, 3), "nuclei": (0, 1)},
           "ruin": {"minerali": (1, 3), "erbe": (0, 1)}}


def gather(conn, t: int, rng: random.Random, player) -> str:
    from engine.core import entities
    loc = entities.get_location(conn, player.location_id)
    table = _GATHER.get(loc.location_type if loc else "")
    if not table:
        return "Qui non c'è nulla da raccogliere: cerca montagne, rovine o zone proibite."
    got = []
    bonus = (loc.danger_level or 1) // 3
    from engine.systems import frontier
    fm = frontier.gather_mult(conn, player.location_id)          # le terre di frontiera sono più ricche
    for k, (lo, hi) in table.items():
        n = int(round((rng.randint(lo, hi) + (bonus if rng.random() < 0.5 else 0)) * fm))
        if n > 0:
            give(conn, player.id, k, n)
            state.set(conn, "sys_gathered", str(state.get_int(conn, "sys_gathered", 0) + n))
            got.append(f"{n} {MATERIALS[k]}")
    from engine.simulation import world_tick
    from engine.core import tick as tick_mod
    world_tick.advance(conn, tick_mod.cost_of("short_rest"))
    if not got:
        return "Cerchi a lungo, ma torni a mani vuote."
    return "Raccogli: " + ", ".join(got) + ".\n" + materials_line(conn, player.id)


def on_creature_kill(conn, pid: int, npc_id: int, kind: str | None) -> str | None:
    """Le creature lasciano nuclei (le rare un nucleo raro)."""
    if kind not in ("beast", "demon", "spirit"):
        return None
    rare = conn.execute("SELECT rarity FROM beast_traits WHERE npc_id=?;", (npc_id,)).fetchone() \
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='beast_traits';").fetchone() else None
    if rare and rare["rarity"] != "comune":
        give(conn, pid, "nuclei_rari", 1)
        give(conn, pid, "nuclei", 2)
        return "Raccogli un NUCLEO RARO e due nuclei dalla creatura."
    give(conn, pid, "nuclei", 1)
    return None


# ============================================================
# Ricette
# ============================================================

def _best_dao(conn, pid) -> str:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND "
                     "character_id=? AND practiced=1 ORDER BY comprehension DESC LIMIT 1;",
                     (pid,)).fetchone()
    return r["dao_key"] if r else "corpo"


# (professione, livello minimo, nome, costo, funzione(conn, pid, lv) -> dict risultato)
def _pill(name, eff, desc, rarity="non_comune"):
    return {"item": {"name": name, "item_type": "pillola", "rarity": rarity, "desc": desc, "effects": eff}}


def _formation(kind, lv):
    from engine.systems import formations
    nm = "Disco della " + formations.KINDS[kind]
    return {"item": {"name": nm, "item_type": "formazione", "rarity": "raro",
                     "desc": "Si piazza nel luogo in cui ti trovi ('use').",
                     "effects": {"place_formation": {"kind": kind, "level": lv}}}}


def _talisman(name, buff, desc):
    return {"item": {"name": name, "item_type": "talismano", "rarity": "non_comune", "desc": desc,
                     "effects": {"combat_buff": buff}}}


RECIPES = [
    ("alchimia", 1, "Pillola di Raccolta del Qi", {"erbe": 3},
     lambda c, p, lv: _pill("Pillola di Raccolta del Qi",
                            {"cultivation_progress": round(0.15 + 0.04 * lv, 2)}, "Fa avanzare la coltivazione.")),
    ("alchimia", 2, "Pillola Curativa", {"erbe": 2},
     lambda c, p, lv: _pill("Pillola Curativa", {"heal_injuries": True}, "Richiude le ferite.", "comune")),
    ("alchimia", 2, "Pillola di Purificazione", {"erbe": 3},
     lambda c, p, lv: _pill("Pillola di Purificazione", {"purify": 30 + 5 * lv},
                            "Scioglie le tossine lasciate dalle altre pillole.")),
    ("alchimia", 3, "Pillola di Fondazione", {"erbe": 4, "nuclei": 1},
     lambda c, p, lv: _pill("Pillola di Fondazione", {"bt_bonus": round(0.10 + 0.02 * lv, 2)},
                            "Rende più sicuro il prossimo breakthrough.", "raro")),
    ("alchimia", 5, "Elisir dello Spirito", {"erbe": 4, "nuclei": 2},
     lambda c, p, lv: _pill("Elisir dello Spirito", {"dao_key": _best_dao(c, p), "dao_gain": 4 + lv},
                            "Approfondisce il tuo Dao più forte.", "raro")),
    ("alchimia", 7, "Elisir di Longevità", {"erbe": 6, "nuclei_rari": 1},
     lambda c, p, lv: _pill("Elisir di Longevità", {"lifespan_years": 10 + 3 * lv},
                            "Allunga la vita.", "prezioso")),
    ("talismani", 1, "Talismano del Fuoco", {"erbe": 1, "minerali": 1},
     lambda c, p, lv: _talisman("Talismano del Fuoco", {"name": "Talismano del Fuoco", "state": "ustione",
                                                        "power": 1.0 + 0.2 * lv}, "Incendia il nemico a inizio scontro.")),
    ("talismani", 2, "Talismano dello Scudo d'Oro", {"minerali": 2},
     lambda c, p, lv: _talisman("Talismano dello Scudo d'Oro", {"name": "Scudo d'Oro", "state": "scudo",
                                                                "power": 1.5 + 0.3 * lv}, "Uno scudo all'inizio dello scontro.")),
    ("talismani", 3, "Talismano del Tuono", {"minerali": 2, "nuclei": 1},
     lambda c, p, lv: _talisman("Talismano del Tuono", {"name": "Talismano del Tuono", "state": "stordimento"},
                                "Stordisce il nemico al primo scambio.")),
    ("talismani", 5, "Talismano del Gelo", {"erbe": 2, "minerali": 2},
     lambda c, p, lv: _talisman("Talismano del Gelo", {"name": "Talismano del Gelo", "state": "gelo"},
                                "Gela il nemico al primo scambio.")),
    ("talismani", 7, "Talismano della Fenice", {"erbe": 3, "nuclei_rari": 1},
     lambda c, p, lv: _talisman("Talismano della Fenice", {"name": "Talismano della Fenice",
                                                           "state": "rigenerazione", "power": 3.0,
                                                           "lethal_save": True},
                                "Rigenera e salva da un colpo mortale.")),
    ("alchimia", 2, "Veleno del Serpente di Giada", {"erbe": 2, "nuclei": 1},
     lambda c, p, lv: _talisman("Veleno del Serpente di Giada", {"name": "Veleno del Serpente di Giada",
                                                               "state": "veleno", "power": 1.0 + 0.2 * lv},
                                "Unta sulla lama: avvelena il nemico a inizio scontro.")),
    ("alchimia", 6, "Polvere dei Sette Passi", {"erbe": 4, "nuclei_rari": 1},
     lambda c, p, lv: _talisman("Polvere dei Sette Passi", {"name": "Polvere dei Sette Passi",
                                                           "state": "veleno", "power": 2.5 + 0.3 * lv},
                                "Un veleno leggendario: sette passi e si cade.")),
    # ---- FORMAZIONI (si piazzano con 'use' nel luogo in cui ti trovi) ----
    ("formazioni", 1, "Disco della Formazione di Raccolta del Qi", {"minerali": 3},
     lambda c, p, lv: _formation("raccolta", lv)),
    ("formazioni", 2, "Disco della Formazione Difensiva", {"minerali": 3, "erbe": 1},
     lambda c, p, lv: _formation("difesa", lv)),
    ("formazioni", 4, "Disco della Formazione d'Uccisione", {"minerali": 4, "nuclei": 1},
     lambda c, p, lv: _formation("uccisione", lv)),
    ("formazioni", 6, "Disco della Formazione di Teletrasporto", {"minerali": 6, "nuclei_rari": 1},
     lambda c, p, lv: _formation("teletrasporto", lv)),
    # ---- ADDOMESTICAMENTO ----
    ("domatore", 1, "Esca Spirituale", {"erbe": 2, "nuclei": 1},
     lambda c, p, lv: _pill("Esca Spirituale", {"beast_lure": True},
                            "Attira una bestia rara nei dintorni.", "raro")),
    ("domatore", 2, "Pillola del Sangue Bestiale", {"erbe": 2, "nuclei": 2},
     lambda c, p, lv: _pill("Pillola del Sangue Bestiale", {"beast_stages": 1 + lv // 2},
                            "Fa crescere le tue bestie.")),
    ("domatore", 5, "Rito del Risveglio della Stirpe", {"nuclei": 3, "nuclei_rari": 1},
     lambda c, p, lv: _pill("Rito del Risveglio della Stirpe", {"beast_talent": 1},
                            "Risveglia il talento della tua bestia.", "prezioso")),
    ("domatore", 8, "Rito della Fusione delle Stirpi", {"nuclei_rari": 2},
     lambda c, p, lv: _pill("Rito della Fusione delle Stirpi", {"beast_element": True},
                            "Infonde nella tua bestia gli elementi della tua sintonia.", "prezioso")),
    ("forgia", 1, "Forgia un'arma del tuo regno", {"minerali": 4},
     lambda c, p, lv: {"forge": "tier"}),
    ("forgia", 3, "Raffina l'arma (rarità +1)", {"minerali": 5, "nuclei": 1},
     lambda c, p, lv: {"forge": "rarity"}),
    ("forgia", 6, "Risveglia lo spirito dell'arma", {"minerali": 6, "nuclei_rari": 1},
     lambda c, p, lv: {"forge": "spirit"}),
]


def recipes_for(conn, pid: int = 1, key: str | None = None) -> list[tuple]:
    prof = key or profession(conn, pid)
    return [r for r in RECIPES if r[0] == prof]


def describe_recipes(conn, pid: int = 1, key: str | None = None) -> str:
    prof = key or profession(conn, pid)
    if not prof:
        return choose(conn, pid, "")
    if not has(conn, prof, pid):
        return f"Non conosci {art(prof)}: 'arti {prof}' per iniziare a praticarla."
    lv = level(conn, pid, prof)
    lines = [f"Ricette di {PROFESSIONS[prof]} — livello {lv} (esperienza {xp(conn, pid, prof)}):"]
    for i, r in enumerate(recipes_for(conn, pid, prof), 1):
        cost = ", ".join(f"{v} {MATERIALS[k]}" for k, v in r[3].items())
        lock = "" if lv >= r[1] else f"  [serve livello {r[1]}]"
        lines.append(f"  {i}. {r[2]} — {cost}{lock}")
    lines.append(materials_line(conn, pid))
    lines.append(("'craft <n>'" if prof == profession(conn, pid) else f"'craft {prof} <n>'")
                 + " per creare; 'gather' nelle zone selvagge per i materiali.")
    return "\n".join(lines)


def craft(conn, t: int, rng: random.Random, player, raw: str) -> str:
    from engine.systems import items
    parts = raw.strip().split()
    prof = _key(parts[0]) if parts else None
    if prof:
        raw = " ".join(parts[1:])
    else:
        prof = profession(conn, player.id)
    if not prof:
        return choose(conn, player.id, "")
    if not has(conn, prof, player.id):
        return f"Non conosci {art(prof)}: 'arti {prof}' per iniziare a praticarla."
    rs = recipes_for(conn, player.id, prof)
    if not raw.strip().isdigit() or not (1 <= int(raw) <= len(rs)):
        return describe_recipes(conn, player.id, prof)
    _p, need, name, cost, make = rs[int(raw) - 1]
    lv = level(conn, player.id, prof)
    if lv < need:
        return f"Non sei ancora abbastanza esperto per «{name}» (serve livello {need})."
    if not spend(conn, player.id, cost):
        return f"Ti mancano i materiali per «{name}». {materials_line(conn, player.id)}"
    before = lv
    from engine.systems import cave_abode
    home_lv = cave_abode.craft_level(conn, player.id, player.location_id)
    add_xp(conn, player.id, (1 + need // 3) * (2 if home_lv else 1), prof)
    from engine.simulation import world_tick
    from engine.core import tick as tick_mod
    world_tick.advance(conn, tick_mod.cost_of("short_rest"))
    from engine.systems import mentor_ring, celestial_elements
    p_ok = min(0.97, 0.6 + 0.07 * (lv - need) + 0.05 * home_lv + mentor_ring.craft_bonus(conn)
               + celestial_elements.craft_bonus(conn))
    if rng.random() >= p_ok:
        out = "Il tentativo fallisce: i materiali vanno perduti. (Esperienza +1)"
    else:
        res = make(conn, player.id, lv)
        if "item" in res:
            it = res["item"]
            iid = items.create_item(conn, it["name"], it["item_type"], it["rarity"], it["desc"], it["effects"])
            items.grant(conn, "player", player.id, iid)
            out = f"Crei: {it['name']}! (nello zaino — 'use {it['name'].split()[0].lower()}')"
        else:
            out = _forge(conn, rng, player, res["forge"], lv)
    after = level(conn, player.id, prof)
    if after > before:
        out += f"\n✧ La tua arte cresce: {PROFESSIONS[prof]} livello {after}!"
    return out


def _forge(conn, rng, player, what: str, lv: int) -> str:
    from engine.systems import weapons
    from engine.simulation import cultivation
    eq = weapons.get_equipped(conn, player.id)
    if not weapons.get_weapon(conn, player.id):
        return "Non hai ancora una via marziale ('weapon <arma>'): non sai cosa forgiare."
    tier = (eq or {}).get("tier", 1)
    rarity = (eq or {}).get("rarity", 1)
    if what == "tier":
        ptier = cultivation.realm_tier(conn, "player", player.id) or 1
        if ptier <= tier:
            return "La tua arma è già all'altezza del tuo regno: i minerali tornano utili altrove."
        weapons._set_equipped(conn, player.id, ptier, rarity)
        return f"Riforgi la tua arma al livello del tuo regno ({ptier})."
    if what == "rarity":
        if rarity >= 4:
            return "La tua arma ha già la qualità più alta."
        weapons._set_equipped(conn, player.id, tier, rarity + 1)
        return f"Raffini l'arma: ora è {weapons.rarity_name(rarity + 1)}."
    from engine.systems import weapon_spirit
    return weapon_spirit.awaken(conn, rng, player, forced=True)
