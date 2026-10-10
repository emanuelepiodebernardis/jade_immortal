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
    return state.get(conn, "profession")


def xp(conn, pid: int = 1) -> int:
    return state.get_int(conn, "profession_xp", 0)


def level(conn, pid: int = 1) -> int:
    if not profession(conn, pid):
        return 0
    from engine.systems import destinies
    return level_for_xp(xp(conn, pid)) + int(destinies.flag_value(conn, "crafter", pid, 0))


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
    key = _ALIASES.get(raw.strip().lower(), raw.strip().lower())
    cur = profession(conn, pid)
    if not key:
        if cur:
            from engine.systems import classes
            return (f"La tua arte: {PROFESSIONS[cur]} (livello {level(conn, pid)}) — classe: "
                    f"{classes.class_name(conn, pid)}. {materials_line(conn, pid)}\n"
                    "'recipes' per le ricette, 'sintonia <elemento>' per la classe, 'vocazione' per i dettagli.")
        return ("Non pratichi ancora un'arte. Scegline una: 'profession alchimia' (pillole e veleni), "
                "'profession talismani' (buff di battaglia), 'profession forgia' (armi), "
                "'profession formazioni' (formazioni elementali) o 'profession domatore' (bestie).\n"
                "Con 'sintonia <elemento>' l'arte diventa una classe: es. Maestro delle Formazioni della Fiamma.")
    if key not in PROFESSIONS:
        return "Arti disponibili: alchimia, talismani, forgia, formazioni, domatore."
    if cur == key:
        return f"Pratichi già l'arte: {PROFESSIONS[key]}."
    if cur and xp(conn, pid) > 0:
        state.set(conn, "profession_xp", str(xp(conn, pid) // 3))
        msg = f"Abbandoni la {PROFESSIONS[cur]} per la {PROFESSIONS[key]}: perdi buona parte dell'esperienza."
    else:
        msg = f"Scegli l'arte: {PROFESSIONS[key]}."
    state.set(conn, "profession", key)
    return msg + " 'recipes' per vedere cosa puoi creare; 'sintonia <elemento>' per la tua classe."


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
    for k, (lo, hi) in table.items():
        n = rng.randint(lo, hi) + (bonus if rng.random() < 0.5 else 0)
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


def recipes_for(conn, pid: int = 1) -> list[tuple]:
    prof = profession(conn, pid)
    return [r for r in RECIPES if r[0] == prof]


def describe_recipes(conn, pid: int = 1) -> str:
    prof = profession(conn, pid)
    if not prof:
        return choose(conn, pid, "")
    lv = level(conn, pid)
    lines = [f"Ricette di {PROFESSIONS[prof]} — livello {lv} (esperienza {xp(conn, pid)}):"]
    for i, r in enumerate(recipes_for(conn, pid), 1):
        cost = ", ".join(f"{v} {MATERIALS[k]}" for k, v in r[3].items())
        lock = "" if lv >= r[1] else f"  [serve livello {r[1]}]"
        lines.append(f"  {i}. {r[2]} — {cost}{lock}")
    lines.append(materials_line(conn, pid))
    lines.append("'craft <n>' per creare; 'gather' nelle zone selvagge per i materiali.")
    return "\n".join(lines)


def craft(conn, t: int, rng: random.Random, player, raw: str) -> str:
    from engine.systems import items
    prof = profession(conn, player.id)
    if not prof:
        return choose(conn, player.id, "")
    rs = recipes_for(conn, player.id)
    if not raw.strip().isdigit() or not (1 <= int(raw) <= len(rs)):
        return describe_recipes(conn, player.id)
    _p, need, name, cost, make = rs[int(raw) - 1]
    lv = level(conn, player.id)
    if lv < need:
        return f"Non sei ancora abbastanza esperto per «{name}» (serve livello {need})."
    if not spend(conn, player.id, cost):
        return f"Ti mancano i materiali per «{name}». {materials_line(conn, player.id)}"
    before = lv
    from engine.systems import cave_abode
    home_lv = cave_abode.craft_level(conn, player.id, player.location_id)
    state.set(conn, "profession_xp", str(xp(conn, player.id) + (1 + need // 3) * (2 if home_lv else 1)))
    from engine.simulation import world_tick
    from engine.core import tick as tick_mod
    world_tick.advance(conn, tick_mod.cost_of("short_rest"))
    p_ok = min(0.97, 0.6 + 0.07 * (lv - need) + 0.05 * home_lv)
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
    after = level(conn, player.id)
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
