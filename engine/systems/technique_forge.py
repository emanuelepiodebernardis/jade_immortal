"""
LA FUCINA DELLE TECNICHE (功法融合) — fondere due o più tecniche in una tecnica nuova, tutta tua.

Un pannello solo ('tecniche', o il pulsante ⚒ Tecniche) mostra TUTTE le tue tecniche — la mossa
dell'arma, le tecniche segrete delle sette, delle razze e dei manuali, le tecniche dei Dao, i colpi
speciali — con i loro effetti, e propone già le FUSIONI migliori: un clic e provi a crearla.

COME FUNZIONA UNA FUSIONE
  Ogni tecnica porta con sé i suoi Dao/elementi. Quando ne fondi due:
    · RISONANZA      (stesso Dao)                       il nucleo si raddoppia: più potenza
    · GENERAZIONE    (Legno→Fuoco→Terra→Metallo→Acqua→Legno, nel ciclo che si nutre)  +potenza, +riuscita
    · INTENTO        (arma + elemento)                  l'elemento scorre nella lama
    · CONFLITTO      (il Fuoco contro l'Acqua, la Luce contro l'Ombra…)  molto più difficile,
                     ma se riesci nasce un'«Armonia degli Opposti», la più potente
  La riuscita cresce con la tempra dello spirito e con la comprensione dei Dao coinvolti; ogni
  fallimento lascia un'INTUIZIONE che rende più facile il tentativo successivo. Fallire costa
  spirito e a volte una ferita (il contraccolpo del Qi).
  Le tecniche create si possono fondere ANCORA (seconda, terza generazione… senza fine: quelle
  create che usi come ingredienti confluiscono nella nuova; ogni generazione aggiunge un po' meno), si
  ALLENANO (e crescono anche usandole in battaglia: livelli senza tetto) e si possono rinominare.

  tecniche                               il pannello: tecniche, fusioni proposte, tecniche create
  tecniche fondi <n> <m> [<k>…]         fondi le tecniche n, m (…) dell'elenco
  tecniche fondi migliore                la fusione più promettente, in un colpo
  tecniche allena <n>                    alleni una tecnica creata (spirito)
  tecniche rinomina <n> <nome>           le dai un nome tuo
  tecniche dimentica <n>                 la dimentichi (libera un posto)
"""

from __future__ import annotations

import itertools
import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "forged_techs"
INSIGHT = "forge_insight"
CYCLE = ["legno", "fuoco", "terra", "metallo", "acqua"]
WEAPON_DAOS = {"spada", "lancia", "sciabola", "arco", "pugno", "bastone"}
_ICON = {"arma": "⚔", "tecnica": "📜", "dao": "☸", "abisso": "🕳", "tribolazione": "⚡", "creata": "✦"}
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def forged(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def _save(conn, lst: list[dict]) -> None:
    state.set_json(conn, KEY, lst)


def slots(conn, pid: int = 1) -> int:
    from engine.systems import soul_temper
    return 3 + soul_temper.grade(conn, pid) // 2 + _tier(conn, pid) // 3


# ============================================================ le tue tecniche, con i loro Dao

def _learned_tags(conn, pid) -> dict[str, list[str]]:
    from engine.systems import race_realms
    out = {}
    for r in conn.execute("SELECT tech_key, faction_id FROM learned_techniques WHERE player_id=?;", (pid,)).fetchall():
        tags: list[str] = []
        k = r["tech_key"] or ""
        if r["faction_id"]:
            f = conn.execute("SELECT element FROM factions WHERE id=?;", (r["faction_id"],)).fetchone()
            if f and f["element"]:
                tags.append(f["element"])
        if k.startswith("race:"):
            rk = k.split(":")[1]
            tags += race_realms.BLOOD.get(rk, (None, []))[1][:1]
        out[f"tec{k.replace(':', '_')}"] = tags
    return out


def techniques(conn, pid: int = 1) -> list[dict]:
    """Tutte le tecniche (le stesse mosse del combattimento), ognuna con i suoi Dao ('tags')."""
    from engine.systems import moves, weapons
    lt = _learned_tags(conn, pid)
    out = []
    for m in moves.available_moves(conn, pid):
        src = m.get("source", "")
        if src == "arma":
            tags = [weapons.get_weapon(conn, pid) or "corpo"]
        elif src == "tecnica":
            tags = lt.get(m["key"], [])
        elif src == "dao":
            tags = list(m.get("fused") or [m.get("main")])
        elif src == "abisso":
            tags = ["oscurita", "sangue"]
        elif src == "tribolazione":
            tags = ["fulmine"]
        elif src == "creata":
            tags = list(m.get("tags", []))
        else:
            tags = []
        out.append({**m, "tags": [t for t in tags if t], "gen": m.get("gen", 0)})
    return out


def _cost(m: dict) -> float:
    return m.get("spirit_cost", 0) if m.get("fuel") == "spirit" else m.get("qi_cost", 0) * 0.5


def summary(m: dict) -> str:
    md = m.get("mods", {})
    bits = [f"×{md.get('attack_mult', 1.0):.2f}"]
    if md.get("pierce"):
        bits.append(f"perfora {int(md['pierce'] * 100)}%")
    if md.get("extra_strikes"):
        bits.append(f"+{md['extra_strikes']} colpi")
    if md.get("death_bonus"):
        bits.append(f"letale +{int(md['death_bonus'] * 100)}%")
    if md.get("taken_mult", 1.0) < 1.0:
        bits.append(f"danni subiti −{int((1 - md['taken_mult']) * 100)}%")
    cost = f"{m.get('spirit_cost', 0)} spirito" if m.get("fuel") == "spirit" else f"{m.get('qi_cost', 0)} Qi"
    return " · ".join(bits) + f" · {cost}"


# ============================================================ la fusione

def _bond(ta: set, tb: set) -> tuple[str, float, float]:
    """(tipo di legame, sinergia di potenza, modifica alla riuscita)."""
    from engine.systems import elements
    if ta & tb:
        return "risonanza", 0.15, 0.10
    for a in ta:
        for b in tb:
            if a in CYCLE and b in CYCLE and (CYCLE[(CYCLE.index(a) + 1) % 5] == b or CYCLE[(CYCLE.index(b) + 1) % 5] == a):
                return "generazione", 0.20, 0.10
    for a in ta:
        for b in tb:
            if elements.OVERCOMES.get(a) == b or elements.OVERCOMES.get(b) == a:
                return "conflitto", 0.35, -0.25
    if (ta & WEAPON_DAOS) or (tb & WEAPON_DAOS):
        return "intento", 0.10, 0.05
    return "neutro", 0.05, 0.0


_BOND_IT = {"risonanza": "Risonanza", "generazione": "Generazione", "conflitto": "Conflitto (Armonia degli Opposti)",
            "intento": "Intento", "neutro": "Accostamento"}


def _modifier(tags: list[str], name: str) -> str:
    from engine.systems import dao_techniques
    for t in tags:
        w = dao_techniques._MODIFIERS.get(t)
        if w and w.lower() not in name.lower():
            return w
    return ""


def _core(name: str) -> str:
    name = name.split(" — ")[0]
    for pre in ("Arte Suprema: ", "Armonia degli Opposti: "):
        name = name.replace(pre, "")
    w = name.replace("…", "").split()
    return " ".join(w[:4])


def plan(parts: list[dict], conn=None, pid: int = 1) -> dict:
    """Il risultato previsto di una fusione (nome, effetti, costo, probabilità)."""
    a = parts[0]
    tags = list(dict.fromkeys(t for p in parts for t in p["tags"]))
    synergy, chance_mod, kinds = 0.0, 0.0, []
    acc = {"attack_mult": a["mods"].get("attack_mult", 1.0), "pierce": a["mods"].get("pierce", 0.0),
           "extra_strikes": int(a["mods"].get("extra_strikes", 0)), "death_bonus": a["mods"].get("death_bonus", 0.0),
           "taken_mult": a["mods"].get("taken_mult", 1.0)}
    seen = set(a["tags"])
    gen0 = max(p.get("gen", 0) for p in parts)
    damp = 1.0 / (1 + 0.5 * gen0)                         # ogni generazione aggiunge un po' meno: senza tetto, ma lenta
    for b in parts[1:]:
        kind, syn, ch = _bond(seen, set(b["tags"]))
        kinds.append(kind)
        synergy += syn
        chance_mod += ch
        bm = b["mods"]
        hi, lo = max(acc["attack_mult"], bm.get("attack_mult", 1.0)), min(acc["attack_mult"], bm.get("attack_mult", 1.0))
        acc["attack_mult"] = hi + (0.5 * max(0.0, lo - 1.0) + syn) * damp
        acc["pierce"] = min(0.9, acc["pierce"] + 0.7 * bm.get("pierce", 0.0))
        acc["extra_strikes"] = min(4, acc["extra_strikes"] + int(bm.get("extra_strikes", 0)))
        acc["death_bonus"] = min(0.7, acc["death_bonus"] + 0.7 * bm.get("death_bonus", 0.0))
        acc["taken_mult"] = max(0.3, min(acc["taken_mult"], bm.get("taken_mult", 1.0)))
        seen |= set(b["tags"])
    mods = {k: round(v, 3) for k, v in acc.items() if (k == "attack_mult" or (v and (k != "taken_mult" or v < 1.0)))}
    spirit = any(p.get("fuel") == "spirit" for p in parts)
    costs = sorted((_cost(p) for p in parts), reverse=True)
    total = costs[0] * 1.15 + 0.25 * sum(costs[1:])
    gen = gen0 + 1
    # nome
    core = _core(a["name"])
    mod = ""
    for b in parts[1:]:
        mod = _modifier(b["tags"], core) or mod
    if not mod:
        mod = "di " + _core(parts[1]["name"]).split()[-1]
    name = f"{core} {mod}".strip()
    if "conflitto" in kinds:
        name = f"Armonia degli Opposti: {name}"
    elif "risonanza" in kinds and len(parts) == 2:
        name = f"{name} Risonante" if "Risonante" not in name else name
    if gen >= 3 or len(parts) >= 3:
        name = f"Arte Suprema: {name}"
    # riuscita
    chance = 0.55 + chance_mod - 0.1 * (len(parts) - 2) - 0.04 * (gen - 1)
    if conn is not None:
        from engine.systems import soul_temper
        chance += 0.02 * soul_temper.grade(conn, pid) + 0.08 * state.get_int(conn, INSIGHT, 0)
        comp = 0
        for t in tags:
            r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                             "AND dao_key=?;", (pid, t)).fetchone()
            comp += (r["comprehension"] or 0) if r else 0
        chance += 0.0015 * min(200, comp)
    return {"name": name, "mods": mods, "tags": tags, "fuel": "spirit" if spirit else "qi",
            "spirit_cost": int(total) if spirit else 0, "qi_cost": 0 if spirit else int(total * 2),
            "cooldown": max(p.get("cooldown", 2) for p in parts), "gen": gen, "kinds": kinds,
            "chance": max(0.15, min(0.95, chance)), "parts": [p["name"] for p in parts]}


def fusion_cost(conn, pid: int, n_parts: int, gen: int) -> tuple[int, int]:
    from engine.systems import spirit as spmod
    return (max(15, int(spmod.max_spirit(conn, pid) * 0.35)), 40 * _tier(conn, pid) * gen * (n_parts - 1))


def suggestions(conn, pid: int = 1, limit: int = 6) -> list[tuple[list[int], dict]]:
    techs = techniques(conn, pid)
    out = []
    for i, j in itertools.combinations(range(len(techs)), 2):
        if set(techs[i]["tags"]) == set(techs[j]["tags"]) and techs[i]["source"] == techs[j]["source"] == "dao":
            continue                                           # la tecnica fusa dei Dao li contiene già
        p = plan([techs[i], techs[j]], conn, pid)
        out.append(([i + 1, j + 1], p))
    if len(techs) >= 3:
        best3 = None
        for c in itertools.combinations(range(len(techs)), 3):
            p = plan([techs[k] for k in c], conn, pid)
            v = p["mods"]["attack_mult"] * p["chance"]
            if best3 is None or v > best3[0]:
                best3 = (v, [k + 1 for k in c], p)
        if best3:
            out.append((best3[1], best3[2]))
    out.sort(key=lambda x: -(x[1]["mods"]["attack_mult"] + 0.2 * x[1]["mods"].get("extra_strikes", 0)) * x[1]["chance"])
    return out[:limit]


def _free_after(conn, pid, parts) -> bool:
    used = sum(1 for x in parts if x.get("source") == "creata")
    return len(forged(conn)) - used < slots(conn, pid)


def fuse(conn, player, idxs: list[int]) -> str:
    from engine.systems import spirit as spmod, sects, chronicle
    techs = techniques(conn, player.id)
    if len(idxs) < 2 or len(set(idxs)) != len(idxs) or any(not (1 <= i <= len(techs)) for i in idxs):
        return "Indica almeno due tecniche diverse dell'elenco: 'tecniche fondi <n> <m>' (vedi 'tecniche')."
    parts = [techs[i - 1] for i in idxs]
    if not _free_after(conn, player.id, parts):
        return (f"Puoi custodire {slots(conn, player.id)} tecniche create: dimenticane una ('tecniche dimentica <n>') "
                "o tempra lo spirito per fare spazio.")
    p = plan(parts, conn, player.id)
    sp_cost, stones = fusion_cost(conn, player.id, len(parts), p["gen"])
    if sects.get_resource(conn, "pietre_spirituali", player.id) < stones:
        return f"La fusione consuma {stones} pietre spirituali (per sostenere il Qi): non ne hai abbastanza."
    if not spmod.spend(conn, sp_cost, player.id):
        return f"Ti serve più spirito ({sp_cost}) per tenere insieme due intenti diversi: riposa o medita."
    sects.grant_resource(conn, "pietre_spirituali", -stones, player.id)
    consumed = [x.get("forge_id") for x in parts if x.get("source") == "creata"]
    from engine.simulation import world_tick
    t = tick_mod.get_tick(conn)
    world_tick.advance(conn, tick_mod.cost_of("cultivate"))
    rng = random.Random(t * 19 + sum(idxs))
    lines = [f"⚒ Chiudi gli occhi e lasci scorrere insieme {' e '.join('«' + x + '»' for x in p['parts'])}.",
             f"Legame: {', '.join(_BOND_IT[k] for k in p['kinds'])} — riuscita stimata {int(p['chance'] * 100)}%."]
    if rng.random() >= p["chance"]:
        n = state.get_int(conn, INSIGHT, 0) + 1
        state.set(conn, INSIGHT, str(n))
        lines.append("✖ Gli intenti si respingono: il Qi ti esplode nei meridiani e la tecnica si dissolve.")
        if rng.random() < 0.3:
            conn.execute("INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
                         "healed, heal_tick) VALUES ('player', ?, 2, 'contraccolpo di una fusione', ?, 0, ?);",
                         (player.id, t, t + 30))
            lines.append("Ne esci ferito.")
        lines.append(f"Ma qualcosa resta: un'INTUIZIONE (+{8 * n}% alla prossima fusione).")
        return "\n".join(lines)
    state.set(conn, INSIGHT, "0")
    lst = forged(conn)
    if consumed:                                          # le tecniche create confluiscono nella nuova
        lst = [x for x in lst if x["id"] not in consumed]
        lines.append("Le tecniche create che hai usato confluiscono nella nuova e smettono di esistere da sole.")
    tech = {"id": max([x["id"] for x in forged(conn)], default=0) + 1, "name": p["name"], "mods": p["mods"],
            "tags": p["tags"], "fuel": p["fuel"], "spirit_cost": p["spirit_cost"], "qi_cost": p["qi_cost"],
            "cooldown": p["cooldown"], "gen": p["gen"], "parts": p["parts"], "lv": 1, "xp": 0, "day": t // 120}
    lst.append(tech)
    _save(conn, lst)
    lines.append(f"✦ Nasce una tecnica nuova: «{tech['name']}» — {summary(tech)}.")
    if tech["fuel"] == "spirit" and tech["spirit_cost"] > spmod.max_spirit(conn, player.id):
        lines.append("⚠ Costa più spirito di quanto la tua anima ne contenga: potrai usarla quando la riserva crescerà "
                     "('tempra').")
    if p["gen"] >= 3:
        state.grant_title(conn, "Fondatore di Arti")
    if not state.flag(conn, "forge_first", False):
        state.set(conn, "forge_first", "1")
        state.grant_title(conn, "Creatore di Tecniche")
    chronicle.add(conn, "crescita", f"Crea la tecnica «{tech['name']}».")
    lines.append("Combatte con te da subito (si sceglie da sola quando conviene). Allenala per farla crescere.")
    return "\n".join(lines)


# ============================================================ crescita, nomi, oblio

def _need(lv: int) -> int:
    return 5 * lv


def _gain_xp(conn, tech_id: int, n: int) -> list[str]:
    lst = forged(conn)
    out = []
    for x in lst:
        if x["id"] == tech_id:
            x["xp"] += n
            while x["xp"] >= _need(x["lv"]):
                x["xp"] -= _need(x["lv"])
                x["lv"] += 1
                out.append(f"✦ «{x['name']}» sale al livello {x['lv']}.")
    _save(conn, lst)
    return out


def on_use(conn, move: dict) -> None:
    if move.get("source") == "creata":
        _gain_xp(conn, move.get("forge_id", -1), 1)


def train(conn, player, n: int) -> str:
    from engine.systems import spirit as spmod, soul_temper
    lst = forged(conn)
    if not (1 <= n <= len(lst)):
        return "Quale tecnica creata? 'tecniche allena <n>' (il numero tra le tue tecniche create)."
    x = lst[n - 1]
    cost = max(10, int(spmod.max_spirit(conn, player.id) * 0.2))
    if not spmod.spend(conn, cost, player.id):
        return f"Ti serve più spirito ({cost})."
    from engine.simulation import world_tick
    world_tick.advance(conn, tick_mod.cost_of("cultivate"))
    gain = 2 + soul_temper.grade(conn, player.id) // 3
    ups = _gain_xp(conn, x["id"], gain)
    return "\n".join([f"Ripeti «{x['name']}» finché il corpo la ricorda da solo (+{gain} maestria)."] + ups)


def rename(conn, n: int, name: str) -> str:
    lst = forged(conn)
    name = " ".join(name.split())[:60]
    if not (1 <= n <= len(lst)) or not name:
        return "Usa: tecniche rinomina <n> <nuovo nome>."
    old = lst[n - 1]["name"]
    lst[n - 1]["name"] = name
    _save(conn, lst)
    return f"«{old}» ora si chiama «{name}»."


def forget(conn, n: int) -> str:
    lst = forged(conn)
    if not (1 <= n <= len(lst)):
        return "Quale tecnica creata? 'tecniche dimentica <n>'."
    x = lst.pop(n - 1)
    _save(conn, lst)
    return f"Lasci che «{x['name']}» si dissolva nella memoria."


def custom_moves(conn, pid: int = 1) -> list[dict]:
    """Le tecniche create, come mosse di combattimento (crescono col livello)."""
    out = []
    for x in forged(conn):
        lv = x.get("lv", 1)
        k = 1 + 0.06 * (lv - 1)
        mods = dict(x["mods"])
        mods["attack_mult"] = round(mods.get("attack_mult", 1.0) * k, 3)
        if mods.get("death_bonus"):
            mods["death_bonus"] = min(0.8, mods["death_bonus"] * (1 + 0.02 * (lv - 1)))
        out.append({"key": f"forgia{x['id']}", "name": x["name"] + (f" ({_ROMAN[lv - 1] if lv <= 10 else lv})" if lv > 1 else ""),
                    "cooldown": x.get("cooldown", 2), "spirit_cost": x.get("spirit_cost", 0),
                    "qi_cost": x.get("qi_cost", 0), "fuel": x.get("fuel", "qi"), "mods": mods,
                    "desc": "tecnica creata da te: " + " + ".join(x.get("parts", [])), "source": "creata",
                    "tags": x.get("tags", []), "gen": x.get("gen", 1), "forge_id": x["id"]})
    return out


# ============================================================ menu e comandi

def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import sects, spirit as spmod
    techs = techniques(conn, player.id)
    lst = forged(conn)
    secs = []
    if len(techs) < 2:
        secs.append(section("La fucina è fredda", [
            "Per fondere servono almeno due tecniche. Le ottieni: scegliendo un'arma ('weapon'), comprendendo un Dao "
            "fino a 10, imparando le tecniche segrete della setta ('techniques'), dai manuali e dalle razze antiche."],
            icon="⚒"))
    else:
        stones = sects.get_resource(conn, "pietre_spirituali", player.id)
        cur_sp = spmod.get_spirit(conn, player.id)
        sug = suggestions(conn, player.id)
        acts = []
        lines = [f"Tecniche create: {len(lst)}/{slots(conn, player.id)} · spirito {cur_sp}"
                 f"/{spmod.max_spirit(conn, player.id)} · intuizioni {state.get_int(conn, INSIGHT, 0)}"]
        for k, (idx, p) in enumerate(sug):
            sp, st = fusion_cost(conn, player.id, len(idx), p["gen"])
            free = _free_after(conn, player.id, [techs[i - 1] for i in idx])
            ok = free and stones >= st and cur_sp >= sp
            why = ("nessun posto libero" if not free else
                   f"servono {st} pietre" if stones < st else f"servono {sp} di spirito")
            acts.append(act(f"«{p['name']}» ← " + " + ".join(p["parts"]) +
                            f" · ×{p['mods']['attack_mult']:.2f} · {int(p['chance'] * 100)}% · {_BOND_IT[p['kinds'][0]]}",
                            "tecniche fondi " + " ".join(map(str, idx)), ok=ok, why=why, main=k == 0))
        secs.append(section("Fucina: fusioni proposte (un clic per tentare)", lines, acts, icon="⚒"))
    lines = [f"#{i} {_ICON.get(m['source'], '•')} {m['name']} — {summary(m)}"
             + (f" · Dao: {', '.join(m['tags'])}" if m["tags"] else "") for i, m in enumerate(techs, 1)]
    secs.append(section("Tutte le tue tecniche (i numeri # servono per 'tecniche fondi <n> <m>')", lines,
                        [act("Tecniche della setta", "techniques"), act("Tecniche delle vassalle", "dominio tecniche")],
                        icon="📜"))
    cm = {m["forge_id"]: m for m in custom_moves(conn, player.id)}
    for i, x in enumerate(lst, 1):
        mv = cm.get(x["id"])
        secs.append(section(f"✦ {x['name']}", [
            f"Generazione {x['gen']} · nata da " + " + ".join(x.get("parts", [])),
            summary(mv) if mv else ""],
            [act("Allenala", f"tecniche allena {i}", main=True), act("Dimenticala", f"tecniche dimentica {i}")],
            [bar(f"Livello {x['lv']}", 100 * x["xp"] / _need(x["lv"]), tone="rare")]))
    return menu("tecniche", "⚒ LE TUE TECNICHE E LA FUCINA",
                ["Fondi due o più tecniche in una nuova: la fucina propone le combinazioni migliori."], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus
    p = arg.strip().split()
    sub = p[0].lower() if p else ""
    if sub in ("fondi", "fondere", "unisci", "fusione"):
        if len(p) > 1 and p[1].lower() in ("migliore", "best", "auto"):
            sug = suggestions(conn, player.id, 1)
            if not sug:
                return "Non hai abbastanza tecniche da fondere."
            return fuse(conn, player, sug[0][0])
        idxs = [int(x) for x in p[1:] if x.isdigit()]
        return fuse(conn, player, idxs)
    if sub in ("allena", "esercita") and len(p) > 1 and p[1].isdigit():
        return train(conn, player, int(p[1]))
    if sub in ("rinomina", "nome") and len(p) > 2 and p[1].isdigit():
        return rename(conn, int(p[1]), " ".join(p[2:]))
    if sub in ("dimentica", "elimina") and len(p) > 1 and p[1].isdigit():
        return forget(conn, int(p[1]))
    return menus.show(conn, player, "tecniche")
