"""
LIGNAGGI DI SANGUE (血脉) — il sangue delle bestie leggendarie che scorre in te.

COME SI OTTENGONO
  - Le bestie d'alto livello e le bestie rare, quando muoiono, lasciano un'ESSENZA DI SANGUE
    (nello zaino: 'use essenza' per raffinarla e assorbirla). Le rare a volte lasciano anche
    un nucleo antico o altri tesori.
  - Il DIVORATORE assorbe il sangue direttamente quando divora una bestia (e di più).
  - Per eredità: il destino «Sangue di Drago» o «Corpo della Fenice», l'origine di clan
    (un sangue di famiglia), e alla reincarnazione una parte del tuo lignaggio più forte.

CONCENTRAZIONE (senza tetto)
  Tracce · Risvegliato (10) · Concentrato (30) · Puro (80) · Ancestrale (200) · Sacro (500)
  · Primordiale (1200) · poi «Sangue del Caos» I, II, III… (ogni ×2,5).

MANIFESTAZIONI IBRIDE (a ogni grado se ne risveglia una, con un potere in battaglia)
  1 occhi (critici) · 2 artigli/zanne (attacco) · 3 squame/piume/guscio (danni subiti ridotti)
  · 4 ali (schivata) · 5 corna/coda (perforazione; dal Primordiale un colpo in più).
  Dal grado Puro: TECNICA INNATA del sangue (lo stato del suo elemento, frequente e forte).
  Doni di famiglia: la Fenice ti rialza dalla morte, il Drago schiaccia con la sua pressione,
  la Tartaruga indurisce, il Qilin acceca… E le stirpi longeve allungano la vita.

TRASFORMAZIONE COMPLETA
  Dal grado Sacro: 'trasformati [n]' — nello scontro successivo DIVENTI la bestia sacra
  (attacco moltiplicato, stati più frequenti, pelle durissima). Costa spirito; poi il sangue
  deve riposare qualche giorno.

FUSIONE DEI LIGNAGGI
  'fondi_sangue <n> <m> [...]' — due o più lignaggi almeno Puri si fondono in un sangue
  ibrido (senza perdere quasi nulla della concentrazione): Drago di Fuoco + Fenice di
  Ghiaccio → «Drago-Fenice di Fuoco e Ghiaccio», con
  gli elementi uniti, le manifestazioni di entrambi e la trasformazione combinata. I fusi si
  possono fondere ancora.

SANGUE IN RIVOLTA
  Lignaggi non fusi con elementi in conflitto (il Fuoco contro l'Acqua…) possono ribellarsi
  quando ne assorbi altro: ferite e una crepa nel cuore. Fonderli, o l'arte del Domatore,
  li tiene a bada.

  sangue            i tuoi lignaggi, i gradi, le manifestazioni
"""

from __future__ import annotations

import math
import random
import sqlite3

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "bloodlines"
GRADES = [(0, "Tracce"), (10, "Risvegliato"), (30, "Concentrato"), (80, "Puro"),
          (200, "Ancestrale"), (500, "Sacro"), (1200, "Primordiale")]
PURE, SACRED = 3, 5
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

EL_ADJ = {"fuoco": "Fuoco", "acqua": "Ghiaccio", "fulmine": "Tuono", "vento": "Vento",
          "terra": "Terra", "metallo": "Metallo", "legno": "Legno", "luce": "Luce",
          "oscurita": "Tenebra", "corpo": "Carne Ferrea", "anima": "Spirito"}

# famiglia: (nome, [occhi, artigli, pelle, ali, corno], dono, longeva)
FAMILIES = {
    "drago": ("Drago", ["Occhi del Drago", "Artigli del Drago", "Squame del Drago",
                        "Ali del Drago", "Corna del Drago"], "pressione", True),
    "fenice": ("Fenice", ["Occhi della Fenice", "Artigli della Fenice", "Piume di Fiamma",
                          "Ali della Fenice", "Coda della Fenice"], "rinascita", True),
    "qilin": ("Qilin", ["Occhi del Qilin", "Zoccoli del Qilin", "Scaglie del Qilin",
                        "Nubi sotto i Piedi", "Corno del Qilin"], "accecamento", True),
    "tigre": ("Tigre", ["Occhi della Tigre", "Artigli della Tigre", "Pelle della Tigre",
                        "Balzo della Tigre", "Zanne della Tigre"], "emorragia", False),
    "tartaruga": ("Tartaruga", ["Occhi della Tartaruga", "Morso della Tartaruga",
                                "Guscio della Tartaruga Nera", "Nuoto degli Abissi",
                                "Coda di Serpente"], "guscio", True),
    "serpente": ("Serpente", ["Occhi del Serpente", "Zanne Velenose", "Squame del Serpente",
                              "Ali del Serpente Volante", "Coda del Serpente"], "veleno", False),
    "peng": ("Peng", ["Occhi del Peng", "Artigli del Peng", "Piume del Peng",
                      "Ali del Grande Peng", "Becco del Peng"], "velocita", False),
    "lupo": ("Lupo", ["Occhi del Lupo", "Zanne del Lupo", "Pelliccia del Lupo",
                      "Corsa del Lupo", "Ululato del Lupo"], "terrore", False),
    "orso": ("Orso", ["Occhi dell'Orso", "Artigli dell'Orso", "Pelle di Ferro",
                      "Passo dell'Orso", "Ruggito dell'Orso"], "scudo", False),
    "aquila": ("Aquila", ["Occhi dell'Aquila", "Artigli dell'Aquila", "Piume del Tuono",
                          "Ali dell'Aquila", "Becco dell'Aquila"], "stordimento", False),
    "cinghiale": ("Cinghiale", ["Occhi del Cinghiale", "Zanne del Cinghiale", "Corazza del Cinghiale",
                                "Carica del Cinghiale", "Zanne Ricurve"], "stordimento", False),
}
_GENERIC = ("Bestia", ["Occhi Bestiali", "Artigli Bestiali", "Pelle Bestiale", "Ali Bestiali",
                       "Corna Bestiali"], None, False)
_KINDS = ["occhi", "artigli", "pelle", "ali", "corno"]

RARITY_GAIN = {"comune": 2.0, "rara": 8.0, "leggendaria": 20.0, "ibrida": 30.0}


# ============================================================
# Gradi e calcoli
# ============================================================

def grade_index(conc: float) -> int:
    idx = 0
    for i, (th, _n) in enumerate(GRADES):
        if conc >= th:
            idx = i
    if conc >= GRADES[-1][0]:
        extra = int(math.log(conc / GRADES[-1][0], 2.5)) if conc > 0 else 0
        idx = len(GRADES) - 1 + extra
    return idx


def grade_name(conc: float) -> str:
    i = grade_index(conc)
    if i < len(GRADES):
        return GRADES[i][1]
    k = i - len(GRADES) + 1
    return f"Sangue del Caos {_ROMAN[k - 1] if k <= len(_ROMAN) else k}"


def next_threshold(conc: float) -> float:
    for th, _n in GRADES:
        if conc < th:
            return th
    i = grade_index(conc) - len(GRADES) + 1
    return GRADES[-1][0] * (2.5 ** (i + 1))


def _strength(conc: float) -> float:
    return math.log2(1 + conc / 10.0)


def families_of(species: str) -> list[str]:
    s = species.lower()
    return [k for k in FAMILIES if k in s]


def _fam(key: str):
    return FAMILIES.get(key, _GENERIC)


# ============================================================
# Stato
# ============================================================

def all_lines(conn) -> dict:
    return state.get_json(conn, KEY, {}) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def ordered(conn) -> list[tuple[str, dict]]:
    return sorted(all_lines(conn).items(), key=lambda kv: -kv[1]["conc"])


def _new_line(species: str, elements: list[str], families: list[str] | None = None,
              fused_from: list[str] | None = None) -> dict:
    fams = families if families is not None else families_of(species)
    return {"name": f"Sangue di {species}", "species": species, "elements": list(elements),
            "families": fams, "conc": 0.0, "fused_from": fused_from or []}


def manifestations(line: dict) -> list[tuple[str, str]]:
    """[(tipo, nome)] risvegliate per questo lignaggio."""
    n = min(len(_KINDS), grade_index(line["conc"]))
    fams = line["families"] or ["_"]
    out = []
    for i in range(n):
        fam = _fam(fams[i % len(fams)])
        out.append((_KINDS[i], fam[1][i]))
    return out


def gain(conn, t: int, rng: random.Random, player, species: str, elements: list[str],
         amount: float) -> list[str]:
    """Aggiunge concentrazione al lignaggio di una specie (lo crea se nuovo)."""
    d = all_lines(conn)
    key = species.lower()
    # se il sangue di questa specie è già confluito in un lignaggio fuso, va lì
    for k, ln in d.items():
        if key in ln.get("fused_from", []):
            key = k
            break
    lines = []
    new = key not in d
    if new:
        d[key] = _new_line(species, elements)
    ln = d[key]
    before = grade_index(ln["conc"])
    ln["conc"] = round(ln["conc"] + amount, 2)
    after = grade_index(ln["conc"])
    _save(conn, d)
    if new:
        lines.append(f"🩸 Un nuovo sangue scorre in te: {ln['name']} ({grade_name(ln['conc'])}).")
    else:
        lines.append(f"🩸 {ln['name']}: concentrazione {ln['conc']:.0f} ({grade_name(ln['conc'])}).")
    if after > before:
        lines += _on_grade_up(conn, ln, before, after)
    lines += _rebellion(conn, t, rng, player, key, amount)
    return lines


def _on_grade_up(conn, ln: dict, before: int, after: int) -> list[str]:
    from engine.systems import lifespan
    out = [f"✦ Il {ln['name']} sale al grado {grade_name(ln['conc'])}!"]
    mf = manifestations(ln)
    for i in range(before, min(after, len(_KINDS))):
        out.append(f"  Il tuo corpo muta — si manifestano: {mf[i][1]}.")
    if before < PURE <= after:
        out.append("  Il sangue ti rivela la sua TECNICA INNATA.")
    if before < SACRED <= after:
        out.append(f"  Ora puoi ASSUMERE LA FORMA della bestia sacra: 'trasformati'.")
    if any(_fam(f)[3] for f in ln["families"]):
        yrs = 15 * (after - before)
        lifespan.add_bonus_years(conn, yrs)
        out.append(f"  Il sangue longevo ti allunga la vita di {yrs} anni.")
    return out


def _conflicts(d: dict) -> int:
    from engine.systems import elements
    els = [set(ln["elements"]) for ln in d.values() if not ln.get("fused_from")]
    n = 0
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            if any(elements.OVERCOMES.get(a) in els[j] or elements.OVERCOMES.get(b) in els[i]
                   for a in els[i] for b in els[j]):
                n += 1
    return n


def _rebellion(conn, t, rng, player, key, amount) -> list[str]:
    from engine.systems import professions, heart_demon
    d = all_lines(conn)
    c = _conflicts(d)
    if c == 0:
        return []
    tamer = professions.level(conn, player.id, "domatore")
    p = max(0.0, 0.12 * c * min(1.0, amount / 10.0) - 0.015 * tamer)
    if rng.random() >= p:
        return []
    conn.execute(
        "INSERT INTO injuries (character_type, character_id, severity, description, "
        "inflicted_tick, healed, heal_tick) VALUES ('player', ?, 3, 'sangue in rivolta', ?, 0, ?);",
        (player.id, t, t + 45))
    heart_demon.add_bonus(conn, -0.05)
    return ["⚠ SANGUE IN RIVOLTA: i tuoi lignaggi si combattono dentro le vene. Ne esci ferito, e il "
            "cuore vacilla (fonderli li placherebbe)."]


# ============================================================
# Fonti
# ============================================================

def beast_blood(conn, npc_id: int) -> dict | None:
    """Specie/elementi/quantità di sangue di una bestia (None se troppo debole)."""
    from engine.systems import beasts
    from engine.simulation import cultivation
    k = conn.execute("SELECT kind, name FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not k or k["kind"] != "beast":
        return None
    tr = beasts.traits(conn, npc_id)
    tier = cultivation.realm_tier(conn, "npc", npc_id) or 1
    rarity = tr["rarity"] or "comune"
    if rarity == "comune" and tier < 2:
        return None
    els = [e for e in (tr["elements"] or "").split(",") if e] or ["corpo"]
    amt = RARITY_GAIN.get(rarity, 2.0) * beasts.TALENT_MULT.get(tr["talent"], 1.0) * (1 + 0.3 * tier)
    return {"species": tr["species"] or k["name"], "elements": els, "gain": round(amt, 1),
            "rarity": rarity, "tier": tier}


def on_beast_kill(conn, t: int, rng, player, npc_id: int) -> list[str]:
    """Le bestie d'alto livello lasciano essenze di sangue (e le rare altri tesori)."""
    from engine.systems import items
    b = beast_blood(conn, npc_id)
    if not b:
        return []
    if b["rarity"] == "comune" and rng.random() >= 0.35:
        return []
    rar = {"comune": "non_comune", "rara": "raro", "leggendaria": "prezioso", "ibrida": "prezioso"}[b["rarity"]]
    nm = f"Essenza di Sangue di {b['species']}"
    iid = items.create_item(conn, nm, "essenza", rar, "Sangue raffinato di una bestia: assorbilo con 'use'.",
                            {"bloodline": {"species": b["species"], "elements": b["elements"],
                                           "gain": b["gain"]}})
    items.grant(conn, "player", player.id, iid)
    out = [f"Dalla bestia raccogli un'{nm}! ('use essenza' per assorbirla)"]
    if b["rarity"] in ("leggendaria", "ibrida") and rng.random() < 0.6:
        tn = f"Nucleo Antico di {b['species']}"
        iid = items.create_item(conn, tn, "pillola", "prezioso", "Il cuore cristallizzato di una bestia sacra.",
                                {"cultivation_progress": round(0.5 + 0.1 * b["tier"], 2),
                                 "grow_strength": 2, "grow_vitality": 2})
        items.grant(conn, "player", player.id, iid)
        out.append(f"E un {tn}, che pulsa ancora di potere.")
    return out


def on_devour_beast(conn, t: int, rng, player, npc_id: int) -> list[str]:
    """Il Divoratore beve il sangue direttamente (e ne prende di più)."""
    b = beast_blood(conn, npc_id)
    if not b:
        return []
    return gain(conn, t, rng, player, b["species"], b["elements"], b["gain"] * 1.5)


def use_essence(conn, t: int, rng, player_id: int, spec: dict) -> list[str]:
    from engine.core import entities
    p = entities.get_player(conn, player_id)
    return gain(conn, t, rng, p, spec["species"], spec.get("elements", []), float(spec.get("gain", 5)))


def grant_heritage(conn, species: str, elements: list[str], conc: float) -> str:
    d = all_lines(conn)
    key = species.lower()
    if key not in d:
        d[key] = _new_line(species, elements)
    d[key]["conc"] = max(d[key]["conc"], conc)
    _save(conn, d)
    return f"Nelle tue vene scorre il {d[key]['name']} ({grade_name(d[key]['conc'])})."


def on_new_life(conn, origin_key: str, rng: random.Random) -> list[str]:
    """Sangue ereditario dall'origine (clan) — chiamato alla creazione del personaggio."""
    if origin_key != "clan":
        return []
    sp = rng.choice([("Tigre Bianca", ["metallo"]), ("Tartaruga Nera", ["acqua", "terra"]),
                     ("Serpente Volante", ["vento"]), ("Qilin", ["luce"])])
    return [grant_heritage(conn, sp[0], sp[1], 12)]


def on_destiny(conn, key: str) -> list[str]:
    if key == "sangue_drago":
        return [grant_heritage(conn, "Drago Azzurro", ["fulmine", "acqua"], 15)]
    if key == "fenice":
        return [grant_heritage(conn, "Fenice", ["fuoco"], 15)]
    return []


def legacy(conn) -> dict | None:
    o = ordered(conn)
    if not o:
        return None
    k, ln = o[0]
    return {"species": ln["species"], "elements": ln["elements"], "families": ln["families"],
            "fused_from": ln.get("fused_from", []), "name": ln["name"], "conc": ln["conc"] * 0.25}


def inherit(conn, leg: dict | None) -> list[str]:
    if not leg or leg["conc"] < 3:
        return []
    d = all_lines(conn)
    key = leg["species"].lower()
    ln = _new_line(leg["species"], leg["elements"], leg["families"], leg["fused_from"])
    ln["name"] = leg["name"]
    ln["conc"] = max(d.get(key, {}).get("conc", 0), round(leg["conc"], 1))
    d[key] = ln
    _save(conn, d)
    return [f"Il sangue non dimentica: il {ln['name']} della vita passata scorre ancora in te "
            f"({grade_name(ln['conc'])})."]


# ============================================================
# Fusione e trasformazione
# ============================================================

def fuse(conn, player, arg: str) -> str:
    o = ordered(conn)
    idx = [int(x) for x in arg.split() if x.isdigit()]
    if len(set(idx)) < 2 or any(not (1 <= i <= len(o)) for i in idx):
        return ("Usa: fondi_sangue <n> <m> [...] — i numeri dei lignaggi in 'sangue' "
                "(ognuno almeno di grado Puro).")
    picks = [o[i - 1] for i in sorted(set(idx))]
    weak = [ln["name"] for _k, ln in picks if grade_index(ln["conc"]) < PURE]
    if weak:
        return "Sono ancora troppo diluiti per fondersi (serve il grado Puro): " + ", ".join(weak) + "."
    fams, els, srcs = [], [], []
    for k, ln in picks:
        for f in ln["families"] or ["bestia"]:
            if f not in fams:
                fams.append(f)
        for e in ln["elements"]:
            if e not in els:
                els.append(e)
        srcs += [k] + ln.get("fused_from", [])
    noun = "-".join(_fam(f)[0] for f in fams if f in FAMILIES) or "Chimera"
    species = f"{noun} di " + " e ".join(EL_ADJ.get(e, e.title()) for e in els)
    conc = 0.9 * sum(ln["conc"] for _k, ln in picks)
    d = all_lines(conn)
    for k, _ln in picks:
        d.pop(k, None)
    key = species.lower()
    new = _new_line(species, els, fams, srcs)
    new["conc"] = round(conc, 1)
    d[key] = new
    _save(conn, d)
    from engine.simulation import world_tick
    world_tick.advance(conn, 120)
    msg = (f"Per un giorno intero il tuo sangue ribolle: i lignaggi si divorano e rinascono come uno solo.\n"
           f"✦ Nasce il {new['name']} — {grade_name(new['conc'])} (concentrazione {new['conc']:.0f}). ✦")
    if len(picks) >= 3 and state.grant_title(conn, "Crogiolo dei Lignaggi"):
        msg += "\n✧ Nuovo titolo: «Crogiolo dei Lignaggi» ✧"
    elif state.grant_title(conn, "Sangue Fuso"):
        msg += "\n✧ Nuovo titolo: «Sangue Fuso» ✧"
    return msg


def transform(conn, player, arg: str) -> str:
    from engine.systems import spirit as spmod
    o = ordered(conn)
    able = [(k, ln) for k, ln in o if grade_index(ln["conc"]) >= SACRED]
    if not able:
        return "Nessun tuo lignaggio è abbastanza concentrato (serve il grado Sacro) per assumerne la forma."
    pick = able[0]
    if arg.strip().isdigit():
        i = int(arg.strip())
        if 1 <= i <= len(o) and grade_index(o[i - 1][1]["conc"]) >= SACRED:
            pick = o[i - 1]
    day = tick_mod.get_tick(conn) // 120
    if day < state.get_int(conn, "blood_transform_ready", -1):
        return "Il tuo sangue riposa dopo l'ultima trasformazione: aspetta ancora qualche giorno."
    if state.get(conn, "blood_transform"):
        return "Sei già pronto alla trasformazione: si scatenerà nel prossimo scontro."
    if not spmod.spend(conn, 20, player.id):
        return "Ti manca lo spirito per sostenere la trasformazione (servono 20)."
    state.set(conn, "blood_transform", pick[0])
    noun = "-".join(_fam(f)[0] for f in pick[1]["families"] if f in FAMILIES) or pick[1]["species"]
    return (f"Il {pick[1]['name']} ruggisce nelle tue vene: sei pronto a diventare {noun}. "
            "La forma si scatenerà nel prossimo scontro.")


# ============================================================
# Combattimento e altri effetti
# ============================================================

def combat(conn, player_id: int, fx) -> list[str]:
    from engine.systems import combat_states
    d = all_lines(conn)
    if not d:
        return []
    intro = []
    pr = fx.p.prof
    for k, ln in d.items():
        s = _strength(ln["conc"])
        g = grade_index(ln["conc"])
        kinds = {kd for kd, _n in manifestations(ln)}
        if "occhi" in kinds:
            pr["crit"] = pr.get("crit", 0.0) + 0.03 * s
        if "artigli" in kinds:
            fx.p.atk_mult *= 1.0 + 0.04 * s
        if "pelle" in kinds:
            pr["taken"] = pr.get("taken", 0.0) + min(0.25, 0.025 * s)
        if "ali" in kinds:
            pr["evade"] = min(0.35, pr.get("evade", 0.0) + 0.02 * s)
        if "corno" in kinds:
            pr["pierce"] = pr.get("pierce", 0.0) + 0.03 * s
        if g >= len(GRADES) - 1:
            pr["extra_strikes"] = pr.get("extra_strikes", 0) + 1
        if g >= PURE:
            for e in ln["elements"]:
                st = combat_states.STATE_OF_DAO.get(e)
                if st:
                    fx.add_proc("p", st, min(0.45, 0.12 + 0.02 * s), 1.2 + 0.1 * s, f"sangue:{k}")
            for f in ln["families"]:
                gift = _fam(f)[2]
                if gift == "rinascita" and g >= 4:
                    fx.p.lethal_saves += 1
                elif gift == "guscio":
                    pr["taken"] = pr.get("taken", 0.0) + 0.05
                elif gift and gift in combat_states.STATES:
                    fx.add_proc("p", gift, min(0.35, 0.08 + 0.015 * s), 1.0 + 0.1 * s, f"dono:{f}")
    tk = state.get(conn, "blood_transform")
    if tk and tk in d:
        ln = d[tk]
        s = _strength(ln["conc"])
        state.delete(conn, "blood_transform")
        state.set(conn, "blood_transform_ready", str(tick_mod.get_tick(conn) // 120 + 3))
        fx.p.atk_mult *= 1.5 + 0.1 * s
        pr["taken"] = pr.get("taken", 0.0) + 0.2
        pr["chance_mult"] = pr.get("chance_mult", 1.0) * 1.3
        noun = "-".join(_fam(f)[0] for f in ln["families"] if f in FAMILIES) or ln["species"]
        intro.append(f"✦ TRASFORMAZIONE: il tuo corpo esplode di luce e sangue — diventi {noun} "
                     f"({', '.join(EL_ADJ.get(e, e) for e in ln['elements'])})! ✦")
        n = state.get_int(conn, "transforms", 0) + 1
        state.set(conn, "transforms", str(n))
        if n == 1:
            state.grant_title(conn, "Bestia Sacra Incarnata")
    else:
        best = ordered(conn)[0][1]
        mf = manifestations(best)
        if mf:
            intro.append(f"Il {best['name']} si agita: " + ", ".join(n for _k, n in mf[-2:]) + ".")
    return intro


def dao_mult(conn, dao_key: str) -> float:
    m = 1.0
    for ln in all_lines(conn).values():
        if dao_key in ln["elements"]:
            m += 0.05 * grade_index(ln["conc"])
    return m


def describe(conn, player) -> str:
    o = ordered(conn)
    if not o:
        return ("Nel tuo sangue non scorre nulla di speciale. Le bestie d'alto livello e quelle rare, "
                "quando cadono, lasciano ESSENZE DI SANGUE ('use essenza'); il Divoratore beve il sangue "
                "direttamente.")
    lines = ["🩸 LIGNAGGI DI SANGUE"]
    for i, (k, ln) in enumerate(o, 1):
        g = grade_index(ln["conc"])
        lines.append(f"  {i}. {ln['name']} — {grade_name(ln['conc'])} (concentrazione {ln['conc']:.0f}, "
                     f"prossimo grado a {next_threshold(ln['conc']):.0f}) — "
                     f"{', '.join(EL_ADJ.get(e, e) for e in ln['elements'])}")
        mf = manifestations(ln)
        if mf:
            lines.append("     Manifestazioni: " + ", ".join(n for _k, n in mf))
        extra = []
        if g >= PURE:
            extra.append("tecnica innata")
        if g >= SACRED:
            extra.append("TRASFORMAZIONE ('trasformati')")
        if ln.get("fused_from"):
            extra.append("lignaggio fuso")
        if extra:
            lines.append("     " + " · ".join(extra))
    c = _conflicts(all_lines(conn))
    if c:
        lines.append(f"⚠ {c} conflitt{'o' if c == 1 else 'i'} tra lignaggi non fusi: rischio di SANGUE IN RIVOLTA.")
    if sum(1 for _k, ln in o if grade_index(ln["conc"]) >= PURE) >= 2:
        lines.append("Due o più lignaggi Puri: puoi fonderli ('fondi_sangue <n> <m>').")
    return "\n".join(lines)
