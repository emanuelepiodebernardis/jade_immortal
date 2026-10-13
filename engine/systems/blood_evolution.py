"""
L'EVOLUZIONE DEL SANGUE — ogni lignaggio può salire di rarità mutando nella bestia che ne è l'erede.

Come nei romanzi di coltivazione: il serpente che vive cinquecento anni diventa un Jiao, il Jiao che
supera la tribolazione diventa Drago; il pesce Kun si trasforma nell'uccello Peng; la volpe mette nove
code. Il sangue non cambia solo nome: sale di RANGO (Mortale → Spirituale → Reale → Imperiale → Divino →
Quattro Simboli → Ancestrale → Caos), cambiano manifestazioni, dono e trasformazione, e LA FORMA DI
PRIMA NON SI PERDE: resta nelle vene come tratto minore (il suo dono si manifesta ancora, a tratti).

  · ogni famiglia ha una o più EVOLUZIONI (a volte un ramo per elemento: il Drago con la terra diventa
    Drago Giallo, il Jiao con l'acqua diventa Leviatano);
  · per evolvere servono un GRADO del lignaggio e un REGNO di coltivazione che crescono col rango
    d'arrivo; poi la PROVA: tre giorni nel bozzolo di sangue, con una probabilità di riuscita
    (sale col grado in più, con la purezza e con un'ESSENZA della bestia d'arrivo, che fa da guida
    e viene consumata). Se fallisce, il sangue si ritira (−20%) e ferisce; si potrà ritentare
    dopo 7 giorni;
  · in cima alla catena c'è l'Hundun, il Caos; oltre il Caos il sangue ASCENDE, un cielo dopo
    l'altro, senza fine.

  sangue evolvi <n> [forma]     tenta l'evoluzione del lignaggio n (anche dai pulsanti del menu)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

# famiglia -> [(famiglia d'arrivo, elementi richiesti o None)]  — l'arrivo è SEMPRE di rango più alto
EVOLUTIONS: dict[str, list[tuple[str, set | None]]] = {
    # sangue selvatico e mortale
    "serpente": [("jiao", None)],
    "lupo": [("tiangou", None)],
    "orso": [("gigante", None)],
    "cinghiale": [("pixiu", None)],
    "aquila": [("peng", None)],
    # spirituale
    "tigre": [("tigre bianca", None)],
    "volpe": [("nove code", None)],
    "gru": [("fenice", None)],
    # reale
    "peng": [("kunpeng", None)],
    "tartaruga": [("tartaruga nera", None)],
    "pixiu": [("taotie", None), ("drago", {"terra", "metallo"})],
    "suanni": [("drago", None)],                                  # uno dei nove figli del Drago
    # imperiale
    "jiao": [("drago", None), ("leviatano", {"acqua"})],
    "tiangou": [("taotie", None)],
    "nove code": [("demone", None)],
    "kun": [("kunpeng", None)],                                  # il pesce Kun diventa l'uccello Peng
    "qilin": [("drago giallo", None)],
    "bai ze": [("drago giallo", None)],
    # divino
    "drago": [("drago azzurro", None), ("drago giallo", {"terra"}), ("drago della torcia", {"fuoco", "tempo"})],
    "fenice": [("uccello vermiglio", None)],
    "demone": [("taotie", None), ("qiongqi", {"vento"})],
    "silvano": [("drago azzurro", None)],
    "gigante": [("taowu", None)],
    "leviatano": [("xiangliu", None), ("tartaruga nera", {"acqua"})],
    # i Quattro Simboli (e il Drago Giallo del Centro)
    "drago azzurro": [("drago della torcia", None)],
    "drago giallo": [("drago della torcia", None), ("taowu", {"terra"})],
    "tigre bianca": [("qiongqi", None)],
    "uccello vermiglio": [("drago della torcia", None)],
    "tartaruga nera": [("xiangliu", None)],
    # le Bestie Ancestrali tornano al Caos
    "taotie": [("hundun", None)], "qiongqi": [("hundun", None)], "taowu": [("hundun", None)],
    "kunpeng": [("hundun", None)], "drago della torcia": [("hundun", None)], "xiangliu": [("hundun", None)],
}

# il racconto di ogni arrivo
TALES = {
    "jiao": "Le squame si induriscono come ferro, sulla fronte spuntano due bozzi di corno: il serpente è diventato Jiao.",
    "tiangou": "Il lupo ulula alla luna finché la luna non risponde: il tuo sangue diventa quello del Cane Celeste, che divora il sole.",
    "gigante": "Le ossa si allungano e si fanno pietra: il sangue dell'orso ricorda di essere nato dalle montagne.",
    "pixiu": "Le zanne del cinghiale si piegano in corna: il tuo sangue impara a divorare e a non restituire nulla.",
    "peng": "L'aquila vola più in alto di ogni nube e il vento la riconosce: ora sei sangue di Peng.",
    "tigre bianca": "Il manto della tigre sbianca, l'aria d'Occidente sa di metallo: la Tigre Bianca dei Quattro Simboli ti chiama figlio.",
    "nove code": "Una coda, poi tre, poi nove: mille anni di astuzia scorrono in una notte.",
    "fenice": "La gru brucia nel bozzolo e dalle ceneri si leva una fenice.",
    "kunpeng": "Nel Mare del Nord c'è un pesce che si chiama Kun; si trasforma in un uccello, e il suo nome è Peng: le sue ali coprono il cielo.",
    "tartaruga nera": "Il guscio si fa nero come le acque del Nord e attorno ti si avvolge un serpente: sei sangue della Tartaruga Nera.",
    "taotie": "Una fame senza fondo ti spalanca il petto: il Taotie divora anche se stesso, e ora vive in te.",
    "drago": "Il fulmine della tribolazione ti attraversa le vene: corna, artigli, nuvole. Sei sangue di Drago.",
    "leviatano": "Le acque profonde ti chiamano: il sangue si fa abissale, freddo, immenso.",
    "demone": "Le code si tingono di tenebra: il sangue della volpe si fa demone.",
    "drago giallo": "La terra del Centro ti riconosce: il Drago Giallo, signore delle quattro direzioni, ti scorre nelle vene.",
    "drago azzurro": "L'Oriente si colora d'alba: il Drago Azzurro dei Quattro Simboli ti apre gli occhi.",
    "drago della torcia": "Apri gli occhi ed è giorno, li chiudi ed è notte: il Drago della Torcia regge il tempo nelle tue vene.",
    "uccello vermiglio": "Il fuoco del Sud non si spegne più: l'Uccello Vermiglio arde in te.",
    "qiongqi": "Sulle spalle della tigre si aprono ali d'ombra: il Qiongqi, che premia il male e divora il giusto.",
    "xiangliu": "Nove teste, nove fauci, un diluvio di veleno: il sangue di Xiangliu si sveglia.",
    "taowu": "Indomabile, ostinato, senza paura: il Taowu non si piega a nulla, nemmeno al Cielo.",
    "hundun": "Il sangue perde forma, volto, nome: è tornato all'Hundun, il Caos prima del principio.",
}

ATTEMPT_DAYS = 3
RETRY_DAYS = 7


# ============================================================
# Requisiti
# ============================================================

def req_grade(target_rank: int) -> int:
    """Il grado del lignaggio richiesto: Puro fino al rango Imperiale, poi uno in più per rango
    (Ancestrale, Sacro, Primordiale, Caos I… senza fine)."""
    return max(3, target_rank - 1)


def req_tier(target_rank: int) -> int:
    """Il regno di coltivazione richiesto (tier)."""
    return max(1, target_rank - 2)


def _rank_of_families(fams: list[str]) -> int:
    from engine.systems import bloodlines as B
    return B.line_rank({"families": fams})


def preview(ln: dict, fam: str, target: str) -> dict:
    """Il lignaggio come sarebbe dopo l'evoluzione (famiglie, minori, nome, rango)."""
    from engine.systems import bloodlines as B
    fams = [target if f == fam else f for f in ln.get("families") or []]
    minor = [m for m in (ln.get("minor") or []) if m != target]
    if fam not in minor:
        minor.append(fam)
    if ln.get("fused_from"):
        main, extra = B._split_families(list(dict.fromkeys(fams + minor)))
        species = B.fused_species(main, ln.get("elements", []))
        fams, minor = main, extra
    else:
        fams = list(dict.fromkeys(fams))
        els = ln.get("elements", [])[:2]
        species = f"{B._fam(target)[0]} di " + " e ".join(B.EL_ADJ.get(e, e.title()) for e in els) if els \
            else B._fam(target)[0]
    new = dict(ln, families=fams, minor=minor, species=species, name=f"Sangue di {species}")
    return {"families": fams, "minor": minor, "species": species, "name": new["name"],
            "rank": B.line_rank(new), "line": new}


def options(conn, ln: dict) -> list[dict]:
    """Le evoluzioni possibili di un lignaggio (anche quelle non ancora pronte, col perché)."""
    from engine.systems import bloodlines as B
    out = []
    els = set(ln.get("elements") or [])
    cur = B.line_rank(ln)
    for fam in ln.get("families") or []:
        for target, need in EVOLUTIONS.get(fam, []):
            if need and not (need & els):
                continue
            if target in (ln.get("families") or []):
                continue
            pv = preview(ln, fam, target)
            if pv["rank"] <= cur:          # (nei fusi a più sangui) un'evoluzione che non alza il rango non conviene
                continue
            out.append({"from": fam, "to": target, "need": need, "preview": pv, "rank_before": cur,
                        "rank_after": pv["rank"], "target_rank": B.FAMILY_RANK.get(target, 0)})
    if not out and cur >= max(B.FAMILY_RANK.values()):                 # oltre il Caos: l'ascesa
        out.append({"from": None, "to": "ascesa", "need": None, "preview": None, "rank_before": cur,
                    "rank_after": cur + 1, "target_rank": cur + 1})
    return out


def _catalyst(conn, pid: int, target: str):
    """Un'essenza di sangue della bestia d'arrivo nello zaino (id inventario, nome) o None."""
    import json
    from engine.systems import bloodlines as B
    if target == "ascesa":
        target = "hundun"
    rows = conn.execute(
        "SELECT v.id vid, i.name, i.effects FROM inventories v JOIN items i ON i.id=v.item_id "
        "WHERE v.owner_type='player' AND v.owner_id=? AND i.item_type='essenza' AND v.quantity>0;", (pid,)).fetchall()
    for r in rows:
        try:
            spec = (json.loads(r["effects"] or "{}") or {}).get("bloodline") or {}
        except (ValueError, TypeError):
            continue
        if target in B.families_of(spec.get("species", "")):
            return r["vid"], r["name"]
    return None


def check(conn, player, ln: dict, opt: dict) -> dict:
    """Pronto? Probabilità di riuscita e cosa manca."""
    from engine.systems import bloodlines as B, professions
    from engine.simulation import cultivation
    tr = opt["target_rank"]
    g = B.grade_index(ln["conc"])
    rg, rt = req_grade(tr), req_tier(tr)
    tier = cultivation.realm_tier(conn, "player", player.id)
    day = tick_mod.get_tick(conn) // 120
    wait = int(ln.get("evo_ready", 0)) - day
    missing = []
    if g < rg:
        missing.append(f"grado {B.GRADES[rg][1] if rg < len(B.GRADES) else B.grade_name(B.GRADES[-1][0] * 2.5 ** (rg - len(B.GRADES) + 1))}")
    if tier < rt:
        r = conn.execute("SELECT name FROM cultivation_realms WHERE tier=? ORDER BY id LIMIT 1;", (rt,)).fetchone()
        missing.append(f"il regno {r['name']}" if r else f"il {rt}° regno")
    if wait > 0:
        missing.append(f"il sangue si riprende ancora {wait} giorni")
    cat = _catalyst(conn, player.id, opt["to"])
    jump = max(0, tr - B.FAMILY_RANK.get(opt["from"], tr - 1) - 1) if opt["from"] else 0
    p = (0.55 + 0.12 * max(0, g - rg) + min(0.3, 0.15 * ln.get("purity", 0.0)) + (0.25 if cat else 0.0)
         + 0.01 * professions.level(conn, player.id, "domatore") - 0.06 * jump)
    from engine.systems import body_blood
    if body_blood.strength(conn, ln) or body_blood.level((body_blood._body(conn) or {}).get("key"),
                                                         {"families": [opt["to"]]}):
        p += 0.15                                              # il corpo leggendario affine guida il sangue
    p = max(0.1, min(0.95, p))
    return {"ok": not missing, "missing": missing, "p": p, "catalyst": cat, "grade_need": rg, "tier_need": rt}


def ready_lines(conn, player) -> list[tuple[int, dict, dict]]:
    """[(numero nel menu, lignaggio, opzione)] delle evoluzioni pronte adesso."""
    from engine.systems import bloodlines as B
    out = []
    for i, (_k, ln) in enumerate(B.ordered(conn), 1):
        for o in options(conn, ln):
            if check(conn, player, ln, o)["ok"]:
                out.append((i, ln, o))
    return out


def chain(fam: str, limit: int = 8) -> list[str]:
    """La via principale di una famiglia fino al Caos (il primo ramo di ogni passo)."""
    out, seen = [fam], {fam}
    while len(out) < limit and EVOLUTIONS.get(out[-1]):
        nxt = EVOLUTIONS[out[-1]][0][0]
        if nxt in seen:
            break
        out.append(nxt)
        seen.add(nxt)
    return out


def _target_name(to: str) -> str:
    from engine.systems import bloodlines as B
    return "Oltre il Caos" if to == "ascesa" else B._fam(to)[0]


# ============================================================
# L'evoluzione
# ============================================================

def evolve(conn, player, arg: str, rng: random.Random | None = None) -> str:
    from engine.systems import bloodlines as B, items, lifespan, heart_demon
    from engine.simulation import world_tick
    rng = rng or random.Random(tick_mod.get_tick(conn) * 7919 + player.id)
    o = B.ordered(conn)
    parts = arg.split()
    if not parts or not parts[0].isdigit() or not (1 <= int(parts[0]) <= len(o)):
        rl = ready_lines(conn, player)
        if not rl:
            return ("Usa: sangue evolvi <n> [forma] — nessun lignaggio è pronto a evolversi ora (guarda il menu "
                    "'sangue': ogni lignaggio mostra la sua catena e cosa manca).")
        i, _ln, opt = rl[0]
        parts = [str(i), opt["to"]]
    i = int(parts[0])
    key, ln = o[i - 1]
    opts = options(conn, ln)
    if not opts:
        return f"Il {ln['name']} non ha evoluzioni (non c'è una bestia più nobile di cui sia l'erede)."
    want = " ".join(parts[1:]).lower().strip()
    opt = next((x for x in opts if x["to"] == want or _target_name(x["to"]).lower() == want), None) if want else opts[0]
    if opt is None:
        return (f"Il {ln['name']} non può diventare «{want}». Può evolversi in: "
                + ", ".join(_target_name(x["to"]) for x in opts) + ".")
    ck = check(conn, player, ln, opt)
    if not ck["ok"]:
        goal = "ad ascendere oltre il Caos" if opt["to"] == "ascesa" else f"a diventare {_target_name(opt['to'])}"
        return f"Il {ln['name']} non è ancora pronto {goal}: manca " + ", ".join(ck["missing"]) + "."
    out = [f"Ti chiudi in un bozzolo di sangue per {ATTEMPT_DAYS} giorni: il {ln['name']} cerca la forma di "
           f"{_target_name(opt['to'])}."]
    if ck["catalyst"]:
        vid, nm = ck["catalyst"]
        conn.execute("UPDATE inventories SET quantity=quantity-1 WHERE id=?;", (vid,))
        conn.execute("DELETE FROM inventories WHERE id=? AND quantity<=0;", (vid,))
        out.append(f"L'{nm} si scioglie nel bozzolo e indica la strada.")
    world_tick.advance(conn, 120 * ATTEMPT_DAYS)
    d = B.all_lines(conn)
    ln = d[key]
    day = tick_mod.get_tick(conn) // 120
    if rng.random() >= ck["p"]:
        ln["conc"] = round(ln["conc"] * 0.8, 2)
        ln["evo_ready"] = day + RETRY_DAYS
        B._save(conn, d)
        conn.execute(
            "INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, healed, "
            "heal_tick) VALUES ('player', ?, 2, 'bozzolo di sangue spezzato', ?, 0, ?);",
            (player.id, tick_mod.get_tick(conn), tick_mod.get_tick(conn) + 60))
        heart_demon.add_bonus(conn, -0.03)
        out.append(f"✖ Il bozzolo si spezza: il sangue non regge la nuova forma e si ritira (concentrazione "
                   f"{ln['conc']:.0f}). Potrai ritentare tra {RETRY_DAYS} giorni.")
        return "\n".join(out)
    before = B.line_rank(ln)
    if opt["to"] == "ascesa":
        ln["ascent"] = int(ln.get("ascent", 0)) + 1
        tale = (f"Il sangue del Caos si spezza e si ricompone più in alto: ascende al "
                f"{B.RANK_NAME[B.line_rank(ln)]}.")
    else:
        pv = preview(ln, opt["from"], opt["to"])
        ln["families"], ln["minor"] = pv["families"], pv["minor"]
        ln["species"], ln["name"] = pv["species"], pv["name"]
        ln.setdefault("lineage", []).append(opt["from"])
        tale = TALES.get(opt["to"], f"Il sangue muta: ora sei sangue di {_target_name(opt['to'])}.")
        if B._fam(opt["to"])[3] and not B._fam(opt["from"])[3]:
            lifespan.add_bonus_years(conn, 40)
            tale += " Il nuovo sangue è longevo: +40 anni di vita."
    ln["evo"] = int(ln.get("evo", 0)) + 1
    ln["evo_ready"] = day + 1
    B._save(conn, d)
    after = B.line_rank(ln)
    out.append("✦ EVOLUZIONE! " + tale + " ✦")
    out.append(f"Ora: {ln['name']} — {B.RANK_ICON[after]} {B.RANK_NAME[after]}"
               + (f" (prima: {B.RANK_NAME[before]})" if after != before else "") + ".")
    if opt["from"]:
        out.append(f"La forma di prima non si perde: il sangue di {B._fam(opt['from'])[0]} resta come tratto minore.")
    if opt["from"]:
        from engine.systems import body_blood
        out += body_blood.on_evolved(conn, ln, opt["to"])
    nxt = options(conn, ln)
    if nxt:
        out.append("La via continua: " + " o ".join(_target_name(x["to"]) for x in nxt[:3]) + ".")
    n = state.get_int(conn, "blood_evolutions", 0) + 1
    state.set(conn, "blood_evolutions", str(n))
    for title, cond in (("Sangue che Muta", n == 1), ("Erede delle Bestie Antiche", after >= 7),
                        ("Ritorno al Caos", after >= 8), ("Oltre il Caos", opt["to"] == "ascesa")):
        if cond and state.grant_title(conn, title):
            out.append(f"✧ Nuovo titolo: «{title}» ✧")
    return "\n".join(out)


def notes_on_grade_up(conn, ln: dict) -> list[str]:
    """Quando un lignaggio sale di grado: annuncia se ora può evolversi."""
    from engine.core import entities
    try:
        p = entities.get_player(conn)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for o in options(conn, ln):
        ck = check(conn, p, ln, o)
        if ck["ok"]:
            out.append(f"  🧬 Il sangue è pronto a EVOLVERSI in {_target_name(o['to'])} ('sangue evolvi', "
                       f"riuscita {int(100 * ck['p'])}%).")
            break
    return out


# ============================================================
# Menu
# ============================================================

def menu_lines(conn, player, i: int, ln: dict) -> tuple[list[str], list]:
    """Righe e pulsanti dell'evoluzione per il lignaggio #i nel menu del sangue."""
    from engine.systems import bloodlines as B
    from engine.systems.menus import act
    lines, acts = [], []
    hist = ln.get("lineage") or []
    fams = ln.get("families") or []
    if hist:
        lines.append("Evoluto da: " + " ▸ ".join(B._fam(f)[0] for f in hist) + f" ▸ {', '.join(B._fam(f)[0] for f in fams)}"
                     + (f" · ascese oltre il Caos: {ln['ascent']}" if ln.get("ascent") else ""))
    elif fams and EVOLUTIONS.get(fams[0]):
        lines.append("Catena: " + " ▸ ".join(B._fam(f)[0] for f in chain(fams[0])))
    for opt in options(conn, ln)[:3]:
        ck = check(conn, player, ln, opt)
        rk = f"{B.RANK_NAME[opt['rank_before']]} → {B.RANK_NAME[opt['rank_after']]}"
        guide = " · essenza guida ✓" if ck["catalyst"] else ""
        need = f" (con {'/'.join(B.EL_ADJ.get(e, e) for e in sorted(opt['need']))})" if opt["need"] else ""
        label = (f"🧬 Evolvi in {_target_name(opt['to'])}{need} · {rk} · riuscita {int(100 * ck['p'])}%{guide}"
                 if opt["to"] != "ascesa" else f"🧬 Ascendi oltre il Caos · {rk} · riuscita {int(100 * ck['p'])}%{guide}")
        acts.append(act(label, f"sangue evolvi {i} {opt['to']}", ok=ck["ok"],
                        why="manca " + ", ".join(ck["missing"]), main=ck["ok"]))
    return lines, acts
