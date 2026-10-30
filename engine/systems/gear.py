"""
L'EQUIPAGGIAMENTO (Aggiornamento 69) — sei posti sul corpo, pezzi veri con regno, rarità, statistiche e set.

  veste      → vitalità          corona   → velocità di coltivazione
  amuleto    → difesa            anello   → attacco
  stivali    → schivata          talismano → critici

Ogni pezzo è forgiato per un REGNO (più alto = più forte) e ha una RARITÀ (comune, raffinata, pregiata,
divina): la rarità moltiplica la statistica principale e aggiunge statistiche secondarie. Dai pregiati in su
un pezzo appartiene a un SET: 2, 4 e 6 pezzi dello stesso set danno bonus in più.

Si trova tra i tesori (premi, tombe, torre, torneo) e si forgia con le pietre ('equip forgia <posto>').
I pezzi superati si scompongono in pietre ('equip scomponi').

Tutto vive in uno stato JSON: aggiungere un posto, un set o una statistica è una riga in SLOTS / SETS / BASE.
"""

from __future__ import annotations

import random

from engine.systems import state

KEY = "gear"
BAG_MAX = 40
SLOTS = {"veste": ("Veste", "vit", ["Veste", "Tunica", "Manto", "Armatura leggera"]),
         "corona": ("Corona", "cult", ["Corona", "Diadema", "Fermacapelli", "Copricapo"]),
         "amuleto": ("Amuleto", "def", ["Amuleto", "Ciondolo", "Pendente", "Medaglione"]),
         "anello": ("Anello", "atk", ["Anello", "Sigillo", "Anello di giada", "Fascia di giada"]),
         "stivali": ("Stivali", "evade", ["Stivali", "Calzari", "Sandali", "Gambali"]),
         "talismano": ("Talismano", "crit", ["Talismano", "Amuleto di carta", "Tessera", "Specchio"])}
ORDER = list(SLOTS)
BASE = {"atk": 0.04, "def": 0.03, "vit": 0.05, "cult": 0.03, "crit": 0.015, "evade": 0.012}
LABEL = {"atk": "attacco", "def": "difesa", "vit": "vitalità", "cult": "coltivazione", "crit": "critici",
         "evade": "schivata"}
CAPS = {"crit": 0.3, "evade": 0.15, "cult": 0.6}
RARITY = ["comune", "raffinata", "pregiata", "divina"]
R_MULT = [1.0, 1.45, 2.0, 2.8]
R_WEIGHTS_FORGE = [55, 30, 12, 3]
ADJ = {"comune": ["del viandante", "dell'apprendista", "di bottega"],
       "raffinata": ["delle rune minori", "del maestro artigiano", "della setta"],
       "pregiata": ["delle nuvole", "del cristallo di qi", "delle ossa di bestia"],
       "divina": ["celeste", "dell'Immortale", "dei Nove Cieli"]}
SETS = {"fenice": ("della Fenice Cremisi", {2: {"atk": 0.06}, 4: {"crit": 0.05}, 6: {"vit": 0.15}}),
        "tartaruga": ("della Tartaruga Nera", {2: {"def": 0.06}, 4: {"vit": 0.12}, 6: {"def": 0.10}}),
        "drago": ("del Drago Azzurro", {2: {"atk": 0.05}, 4: {"atk": 0.08}, 6: {"cult": 0.08}}),
        "tigre": ("della Tigre Bianca", {2: {"crit": 0.03}, 4: {"atk": 0.07}, 6: {"evade": 0.05}}),
        "qilin": ("del Qilin d'Oro", {2: {"cult": 0.05}, 4: {"vit": 0.10}, 6: {"cult": 0.10}})}
WEIGHT = {"atk": 1.0, "def": 1.0, "vit": 0.8, "cult": 0.9, "crit": 2.5, "evade": 3.0}    # per confrontare i pezzi


def get(conn) -> dict:
    d = state.get_json(conn, KEY) or {}
    d.setdefault("eq", {})
    d.setdefault("bag", [])
    d.setdefault("n", 1)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _tier(conn) -> int:
    from engine.simulation import cultivation
    from engine.core import entities
    p = entities.get_player(conn)
    return max(1, cultivation.realm_tier(conn, "player", p.id) or 1) if p else 1


def make(rng: random.Random, tier: int, slot: str | None = None, rar: str | None = None) -> dict:
    slot = slot if slot in SLOTS else rng.choice(ORDER)
    rar = rar if rar in RARITY else rng.choices(RARITY, weights=[50, 32, 14, 4])[0]
    ri = RARITY.index(rar)
    title, main, nouns = SLOTS[slot]
    scale = (1.0 + 0.12 * (tier - 1)) * R_MULT[ri]
    stats = {main: round(BASE[main] * scale, 4)}
    others = [k for k in BASE if k != main]
    for k in rng.sample(others, ri):
        stats[k] = round(BASE[k] * scale * rng.uniform(0.25, 0.45), 4)
    st = rng.choice(list(SETS)) if ri >= 2 else ""
    name = f"{rng.choice(nouns)} {rng.choice(ADJ[rar])}" + (f" {SETS[st][0]}" if st else "")
    return {"slot": slot, "nome": name, "tier": tier, "rar": rar, "set": st, "stats": stats}


def score(it: dict | None) -> float:
    if not it:
        return 0.0
    return sum(v * WEIGHT.get(k, 1.0) for k, v in it["stats"].items())


def add(conn, it: dict) -> str:
    d = get(conn)
    it = dict(it, id=d["n"])
    d["n"] += 1
    cur = d["eq"].get(it["slot"])
    if cur is None:                                    # posto vuoto: lo indossi subito
        d["eq"][it["slot"]] = it
        _save(conn, d)
        return f"🧥 Indossi {fmt(it)}."
    d["bag"].append(it)
    note = " — migliore di ciò che porti!" if score(it) > score(cur) else ""
    if len(d["bag"]) > BAG_MAX:                         # lo zaino trabocca: si scompone il pezzo peggiore
        worst = min(d["bag"], key=score)
        d["bag"].remove(worst)
        _gain(conn, worst)
    _save(conn, d)
    return f"🧥 Trovi {fmt(it)}{note} ('equip')"


def maybe_drop(conn, rng: random.Random, rank: int) -> list[str]:
    chance = {1: 0.45, 2: 0.3, 3: 0.2}.get(rank, 0.1)
    if rng.random() >= chance:
        return []
    rar = RARITY[min(3, max(0, rng.choices([0, 1, 2, 3], weights=[40, 34, 20, 6])[0] + (1 if rank == 1 and rng.random() < 0.3 else 0)))]
    return [add(conn, make(rng, _tier(conn), rar=rar))]


def fmt(it: dict) -> str:
    st = ", ".join(f"{LABEL[k]} +{v * 100:.1f}%" for k, v in it["stats"].items())
    return f"{it['nome']} [{it['rar']}, regno {it['tier']}] ({st})"


def bonus(conn) -> dict:
    d = get(conn)
    out = {k: 0.0 for k in BASE}
    count: dict[str, int] = {}
    for it in d["eq"].values():
        for k, v in it["stats"].items():
            out[k] = out.get(k, 0.0) + v
        if it.get("set"):
            count[it["set"]] = count.get(it["set"], 0) + 1
    for s, c in count.items():
        for need, fx in SETS[s][1].items():
            if c >= need:
                for k, v in fx.items():
                    out[k] += v
    for k, cap in CAPS.items():
        out[k] = min(cap, out[k])
    return out


def sets_active(conn) -> list[str]:
    d = get(conn)
    count: dict[str, int] = {}
    for it in d["eq"].values():
        if it.get("set"):
            count[it["set"]] = count.get(it["set"], 0) + 1
    return [f"{SETS[s][0][4:] if SETS[s][0].startswith('del') else SETS[s][0]} {c}/6" for s, c in count.items() if c >= 2]


def summary(conn) -> str:
    b = bonus(conn)
    parts = [f"{LABEL[k]} +{v * 100:.1f}%" for k, v in b.items() if v]
    s = sets_active(conn)
    return (" · ".join(parts) + (f" · set: {', '.join(s)}" if s else "")) if parts else "nulla di speciale addosso"


# ---------- effetti ----------
def combat_mults(conn) -> dict:
    """Moltiplicatori per combat.combat_power (attacco, difesa, vitalità)."""
    b = bonus(conn)
    return {"attack": 1.0 + b["atk"], "defense": 1.0 + b["def"], "vitality": 1.0 + b["vit"]}


def combat(conn, fx) -> list[str]:
    b = bonus(conn)
    pr = fx.p.prof
    for k, f in (("crit", "crit"), ("evade", "evade")):
        if b[k]:
            pr[f] = pr.get(f, 0.0) + b[k]
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    c = bonus(conn)["cult"]
    return (1.0 + c, "l'equipaggiamento") if c else (1.0, "")


# ---------- azioni ----------
def forge_cost(tier: int) -> int:
    return int(150 * tier ** 1.4)


def scrap_value(it: dict) -> int:
    return int(forge_cost(it["tier"]) * 0.3 * R_MULT[RARITY.index(it["rar"])])


def _gain(conn, it: dict) -> int:
    from engine.systems import sects
    from engine.core import entities
    v = scrap_value(it)
    p = entities.get_player(conn)
    if p:
        sects.grant_resource(conn, "pietre_spirituali", v, p.id)
    return v


def _find(d: dict, ident: str) -> dict | None:
    if ident.isdigit():
        n = int(ident)
        return next((x for x in d["bag"] if x["id"] == n), None)
    return None


def equip(conn, ident: str) -> str:
    d = get(conn)
    it = _find(d, ident)
    if not it:
        return "Nello zaino non c'è un pezzo con quel numero. ('equip')"
    d["bag"].remove(it)
    old = d["eq"].get(it["slot"])
    d["eq"][it["slot"]] = it
    if old:
        d["bag"].append(old)
    _save(conn, d)
    return f"Indossi {it['nome']}." + (f" Riponi {old['nome']}." if old else "") + " " + summary(conn)


def unequip(conn, slot: str) -> str:
    d = get(conn)
    it = d["eq"].pop(slot, None)
    if not it:
        return f"Non porti nulla come {slot}."
    d["bag"].append(it)
    _save(conn, d)
    return f"Togli {it['nome']}."


def auto(conn) -> str:
    """Per ogni posto il pezzo migliore; poi completa i set se conviene (4 pezzi uguali battono un pezzo isolato)."""
    d = get(conn)
    pool = d["bag"] + list(d["eq"].values())
    best: dict[str, dict] = {}
    for it in pool:
        if score(it) > score(best.get(it["slot"])):
            best[it["slot"]] = it
    # prova a completare il set più presente
    sets: dict[str, dict[str, dict]] = {}
    for it in pool:
        if it.get("set"):
            cur = sets.setdefault(it["set"], {}).get(it["slot"])
            if score(it) > score(cur):
                sets[it["set"]][it["slot"]] = it
    for s, pieces in sorted(sets.items(), key=lambda x: -len(x[1])):
        if len(pieces) >= 2:
            trial = dict(best)
            trial.update(pieces)
            if _value_of(trial) > _value_of(best):
                best = trial
            break
    chosen = {id(x) for x in best.values()}
    d["eq"] = {s: it for s, it in best.items()}
    d["bag"] = [x for x in pool if id(x) not in chosen]
    _save(conn, d)
    return f"Indossi il meglio che hai ({len(d['eq'])}/6 posti). " + summary(conn)


def _value_of(eq: dict) -> float:
    b = {k: 0.0 for k in BASE}
    count: dict[str, int] = {}
    for it in eq.values():
        for k, v in it["stats"].items():
            b[k] += v
        if it.get("set"):
            count[it["set"]] = count.get(it["set"], 0) + 1
    for s, c in count.items():
        for need, fx in SETS[s][1].items():
            if c >= need:
                for k, v in fx.items():
                    b[k] += v
    return sum(v * WEIGHT[k] for k, v in b.items())


def scrap(conn, ident: str) -> str:
    d = get(conn)
    if ident in ("tutto", "peggiori", "superati"):
        keep, gone, tot = [], 0, 0
        for it in d["bag"]:
            cur = d["eq"].get(it["slot"])
            if cur and score(it) <= score(cur) and not (it.get("set") and it["set"] == cur.get("set")):
                tot += _gain(conn, it)
                gone += 1
            else:
                keep.append(it)
        d["bag"] = keep
        _save(conn, d)
        return f"Scomponi {gone} pezzi superati: +{tot} pietre." if gone else "Nessun pezzo superato da scomporre."
    it = _find(d, ident)
    if not it:
        return "Nello zaino non c'è un pezzo con quel numero."
    d["bag"].remove(it)
    v = _gain(conn, it)
    _save(conn, d)
    return f"Scomponi {it['nome']}: +{v} pietre spirituali."


def forge(conn, player, slot: str, rng: random.Random | None = None) -> str:
    from engine.systems import sects
    from engine.core import tick as tick_mod
    if slot not in SLOTS:
        return "Quale posto? " + ", ".join(ORDER) + ". ('equip forgia anello')"
    tier = _tier(conn)
    cost = forge_cost(tier)
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    if have < cost:
        return f"Forgiare {SLOTS[slot][0].lower()} del regno {tier} costa {cost} pietre: ne hai {have}."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    rng = rng or random.Random(tick_mod.get_tick(conn) * 7919 + get(conn)["n"])
    rar = rng.choices(RARITY, weights=R_WEIGHTS_FORGE)[0]
    return f"🔥 Alla forgia, {cost} pietre: " + add(conn, make(rng, tier, slot, rar))


# ---------- dashboard e menu ----------
def view(conn) -> dict:
    d = get(conn)
    tier = _tier(conn)

    def row(it):
        cur = d["eq"].get(it["slot"])
        return {"id": it.get("id"), "slot": it["slot"], "posto": SLOTS[it["slot"]][0], "nome": it["nome"],
                "rar": it["rar"], "tier": it["tier"], "set": SETS[it["set"]][0] if it.get("set") else "",
                "stats": [f"{LABEL[k]} +{v * 100:.1f}%" for k, v in it["stats"].items()],
                "meglio": (cur is None or cur.get("id") != it.get("id")) and score(it) > score(cur),
                "valore": scrap_value(it), "img": [f"oggetti/eq_{it['slot']}", "oggetti/tesoro"]}
    return {"posti": [{"slot": s, "posto": SLOTS[s][0], "pezzo": row(d["eq"][s]) if s in d["eq"] else None,
                       "img": [f"oggetti/eq_{s}"]} for s in ORDER],
            "zaino": [row(x) for x in sorted(d["bag"], key=lambda x: (ORDER.index(x["slot"]), -score(x)))],
            "riepilogo": summary(conn), "costo_forgia": forge_cost(tier), "regno": tier}


def menu_sections(conn, player) -> list:
    from engine.systems.menus import act, section
    d = get(conn)
    lines = [f"{SLOTS[s][0]}: " + (fmt(d["eq"][s]) if s in d["eq"] else "—") for s in ORDER]
    lines.append("Effetti: " + summary(conn))
    acts = [act("Indossa il meglio (cerca i set)", "equip auto", bool(d["bag"]), "zaino vuoto", main=True),
            act("Scomponi i pezzi superati", "equip scomponi tutto", bool(d["bag"]), "zaino vuoto")]
    acts += [act(f"Forgia {SLOTS[s][0].lower()} ({forge_cost(_tier(conn))} pietre)", f"equip forgia {s}")
             for s in ORDER if s not in d["eq"]][:3]
    out = [section("Equipaggiamento", lines, acts, icon="🧥", img=["oggetti/eq_veste"])]
    if d["bag"]:
        out.append(section(f"Nello zaino ({len(d['bag'])}/{BAG_MAX})",
                           [f"{x['id']}. {fmt(x)}" for x in d["bag"]][:15],
                           [act(f"Indossa {x['nome']}", f"equip metti {x['id']}") for x in d["bag"]
                            if score(x) > score(d["eq"].get(x["slot"]))][:4], icon="🎒"))
    return out


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub in ("", "mostra", "lista"):
        return _text(conn)
    if sub == "auto":
        return auto(conn)
    if sub in ("metti", "indossa") and len(p) > 1:
        return equip(conn, p[1])
    if sub in ("togli", "rimuovi") and len(p) > 1:
        return unequip(conn, p[1].lower())
    if sub in ("scomponi", "vendi") and len(p) > 1:
        return scrap(conn, p[1].lower())
    if sub == "forgia":
        return forge(conn, player, p[1].lower() if len(p) > 1 else "")
    return ("equip — mostra · equip auto · equip metti <n> · equip togli <posto> · "
            "equip forgia <posto> · equip scomponi <n|tutto>")


def _text(conn) -> str:
    d = get(conn)
    out = ["🧥 EQUIPAGGIAMENTO"] + [f"  {SLOTS[s][0]}: " + (fmt(d["eq"][s]) if s in d["eq"] else "—") for s in ORDER]
    out.append("  Effetti: " + summary(conn))
    if d["bag"]:
        out.append(f"Zaino ({len(d['bag'])}/{BAG_MAX}):")
        out += [f"  {x['id']}. {fmt(x)}" for x in d["bag"][:20]]
    out.append("equip auto · equip metti <n> · equip forgia <posto> · equip scomponi tutto")
    return "\n".join(out)
