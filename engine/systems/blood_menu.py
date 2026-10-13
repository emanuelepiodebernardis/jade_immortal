"""
IL MENU DEL SANGUE — gestire i lignaggi in un posto solo ('sangue', pulsante 🩸 Sangue).

  · le ESSENZE nello zaino: assorbile tutte con un clic;
  · ogni LIGNAGGIO: grado, barra verso il grado successivo, elementi, manifestazioni, doni, razza affine;
  · la TRASFORMAZIONE: scegli in quale bestia sacra trasformarti nel prossimo scontro;
  · le FUSIONI proposte: due o più lignaggi Puri fusi in uno (risolvono anche i conflitti);
  · la RAFFINAZIONE: un lignaggio debole versato in uno forte ('sangue raffina <n> in <m>'), per
    togliere i doppioni e i conflitti senza perdere tutto (il 70%, o il 50% se non hanno nulla in comune).

  sangue                          il menu
  sangue info                     l'elenco testuale (come prima)
  sangue raffina <n> in <m>       versi il lignaggio n nel lignaggio m
  fondi_sangue <n> <m> [...]      fusione (anche dai pulsanti)
  trasformati [n]                 la trasformazione (anche dai pulsanti)
  sangue evolvi <n> [forma]       l'EVOLUZIONE del lignaggio (vedi blood_evolution)
"""

from __future__ import annotations

import itertools

from engine.core import tick as tick_mod
from engine.systems import state

LIST_MAX = 12


def _essences(conn, pid) -> int:
    r = conn.execute("SELECT COALESCE(SUM(v.quantity),0) n FROM inventories v JOIN items i ON i.id=v.item_id "
                     "WHERE v.owner_type='player' AND v.owner_id=? AND i.item_type='essenza' AND v.quantity>0 "
                     "AND i.effects LIKE '%bloodline%';", (pid,)).fetchone()
    return int(r["n"] or 0)


def _relics(conn, pid) -> int:
    r = conn.execute("SELECT COALESCE(SUM(v.quantity),0) n FROM inventories v JOIN items i ON i.id=v.item_id "
                     "WHERE v.owner_type='player' AND v.owner_id=? AND i.item_type='reliquia' AND v.quantity>0;",
                     (pid,)).fetchone()
    return int(r["n"] or 0)


def _race_of(ln: dict) -> str | None:
    from engine.systems import race_realms
    fams = set(ln.get("families") or []) | set(ln.get("minor") or [])
    for k, b in race_realms.BLOOD.items():
        if fams & set(b[2]):
            return k
    return None


def _conflicting_pairs(o) -> set[tuple[int, int]]:
    from engine.systems import elements
    out = set()
    for (i, (_a, la)), (j, (_b, lb)) in itertools.combinations(enumerate(o, 1), 2):
        if la.get("fused_from") or lb.get("fused_from"):
            continue
        if any(elements.OVERCOMES.get(x) in lb["elements"] or elements.OVERCOMES.get(y) in la["elements"]
               for x in la["elements"] for y in lb["elements"]):
            out.add((i, j))
    return out


def fusion_suggestions(conn, limit: int = 4) -> list[tuple[list[int], str]]:
    from engine.systems import bloodlines as B
    o = B.ordered(conn)
    pure = [i for i, (_k, ln) in enumerate(o, 1) if B.grade_index(ln["conc"]) >= B.PURE]
    if len(pure) < 2:
        return []
    out = []
    conf = _conflicting_pairs(o)
    for i, j in sorted(conf):                              # prima chi risolve un conflitto
        if i in pure and j in pure:
            out.append(([i, j], "risolve un conflitto"))
    top = sorted(pure[:8], key=lambda i: (-B.line_rank(o[i - 1][1]), i))[:6]  # noqa: F841
    for i, j in itertools.combinations(top, 2):
        if ([i, j], "risolve un conflitto") not in out:
            out.append(([i, j], ""))
    if len(pure) >= 3:
        out.insert(min(1, len(out)), (pure[:3], "i tre più forti"))
    return out[:limit]


def _preview(conn, idx: list[int]) -> tuple[str, float, str]:
    from engine.systems import bloodlines as B
    o = B.ordered(conn)
    res = B.fusion_result([o[i - 1][1] for i in idx])
    rank = B.line_rank({"families": res["families"]})
    return res["species"], res["conc"], f"{B.grade_name(res['conc'])}, {B.RANK_NAME[rank]}"


def _els_main_first(ln: dict) -> list[str]:
    from engine.systems import bloodlines as B
    pref = [B.FAMILY_ELEMENT[f] for f in ln.get("families", []) if f in B.FAMILY_ELEMENT]
    return list(dict.fromkeys([e for e in pref if e in ln["elements"]] + ln["elements"]))


def noblest(conn) -> int | None:
    """Il numero (#) del lignaggio più nobile: rarità più alta, poi concentrazione."""
    from engine.systems import bloodlines as B
    o = B.ordered(conn)
    if not o:
        return None
    return 1 + max(range(len(o)), key=lambda i: (B.line_rank(o[i][1]), o[i][1]["conc"]))


def sacrifice_preview(la: dict, lb: dict) -> tuple[float, float, str]:
    """(concentrazione ceduta, purezza guadagnata, tipo) versando la in lb."""
    from engine.systems import bloodlines as B
    ra, rb = B.line_rank(la), B.line_rank(lb)
    if ra < rb:                                   # sacrificio: il sangue nobile divora il meno nobile
        gain = 0.6 * la["conc"]
        purity = 0.05 + 0.15 * (rb - ra) * min(1.0, la["conc"] / max(1.0, lb["conc"]))
        return gain, round(purity, 3), "sacrificio"
    share = set(la.get("families") or []) & set(lb.get("families") or []) or set(la["elements"]) & set(lb["elements"])
    return (0.7 if share else 0.5) * la["conc"], 0.0, "raffinazione"


def _pour(conn, player, src: int, dst: int) -> list[str]:
    from engine.systems import bloodlines as B
    o = B.ordered(conn)
    (ka, la), (kb, lb) = o[src - 1], o[dst - 1]
    if B.line_rank(la) > B.line_rank(lb):
        return [f"Il {la['name']} è più nobile del {lb['name']}: non si piega a un sangue inferiore. "
                f"Fai il contrario, o fondili."]
    gain, purity, kind = sacrifice_preview(la, lb)
    d = B.all_lines(conn)
    before = B.grade_index(lb["conc"])
    d[kb]["conc"] = round(lb["conc"] + gain, 1)
    if purity:
        d[kb]["purity"] = round(lb.get("purity", 0.0) + purity, 3)
    d.pop(ka, None)
    B._save(conn, d)
    if kind == "sacrificio":
        out = [f"🩸 Offri il {la['name']} al {lb['name']}: il sangue più nobile lo divora e si fa più puro "
               f"(+{gain:.0f} concentrazione, purezza +{int(purity * 100)}%)."]
    else:
        out = [f"Lasci che il {la['name']} si sciolga nel {lb['name']} (+{gain:.0f} concentrazione)."]
    after = B.grade_index(d[kb]["conc"])
    if after > before:
        out += B._on_grade_up(conn, d[kb], before, after)
    return out


def sacrifice_to_top(conn, player, keys: list[str]) -> list[str]:
    """Sacrifica i lignaggi `keys` ai lignaggi del RANGO PIÙ ALTO, divisi in parti uguali tra loro."""
    from engine.systems import bloodlines as B
    d = B.all_lines(conn)
    before = {k: B.grade_index(ln["conc"]) for k, ln in d.items()}
    gained: dict[str, list[float]] = {}
    for k in keys:
        src = d.get(k)
        if not src or k in B.top_lines(d):
            continue
        d.pop(k)
        for kk, g, p in B.pour_into_top(d, src, src["conc"]):
            gained.setdefault(kk, [0.0, 0.0])
            gained[kk][0] += g
            gained[kk][1] += p
    B._save(conn, d)
    out = []
    for kk, (g, p) in gained.items():
        ln = d[kk]
        out.append(f"🩸 {ln['name']}: +{g:.0f} concentrazione, purezza +{int(p * 100)}% "
                   f"(ora {B.grade_name(ln['conc'])}, purezza {int(100 * ln.get('purity', 0))}%).")
        if B.grade_index(ln["conc"]) > before.get(kk, 0):
            out += B._on_grade_up(conn, ln, before[kk], B.grade_index(ln["conc"]))
    return out


def refine(conn, player, arg: str) -> str:
    """'sangue sacrifica <n>' (ai più nobili, in parti uguali) / 'sangue sacrifica <n> a <m>' /
    'sangue raffina <n> in <m>' / 'sangue sacrifica tutti'."""
    from engine.systems import bloodlines as B
    from engine.simulation import world_tick
    o = B.ordered(conn)
    d = B.all_lines(conn)
    tops = B.top_lines(d)
    if arg.strip().lower() in ("tutti", "tutto", "meno nobili"):
        victims = [k for k, ln in o if k not in tops and not _race_of(ln)]   # i sangui delle razze restano (servono ai loro regni)
        if not o or not victims:
            return "Nessun lignaggio è meno nobile dei tuoi lignaggi più alti."
        names = " e ".join(d[k]["name"] for k in tops)
        out = [f"Nel silenzio della meditazione offri tutti i sangui meno nobili al {names}."]
        out += sacrifice_to_top(conn, player, victims)
        world_tick.advance(conn, 120)
        return "\n".join(out)
    nums = [x for x in arg.replace(" in ", " ").replace(" a ", " ").split() if x.isdigit()]
    if len(nums) == 1 and 1 <= int(nums[0]) <= len(o):
        k, ln = o[int(nums[0]) - 1]
        if k in tops:
            return f"Il {ln['name']} è già tra i tuoi lignaggi più nobili: non ha a chi essere sacrificato."
        out = [f"Offri il {ln['name']} ai tuoi lignaggi più nobili."] + sacrifice_to_top(conn, player, [k])
        world_tick.advance(conn, tick_mod.cost_of("cultivate"))
        return "\n".join(out)
    p = [x for x in arg.replace(" in ", " ").replace(" a ", " ").split() if x.isdigit()]
    if len(p) != 2 or p[0] == p[1] or not all(1 <= int(x) <= len(o) for x in p):
        return ("Usa: sangue sacrifica <n> (ai lignaggi più nobili, in parti uguali), sangue sacrifica <n> a <m>, "
                "o 'sangue sacrifica tutti'.")
    out = _pour(conn, player, int(p[0]), int(p[1]))
    world_tick.advance(conn, tick_mod.cost_of("cultivate"))
    return "\n".join(out)


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import bloodlines as B, race_realms, blood_evolution, body_blood
    o = B.ordered(conn)
    secs = []
    ess, rel = _essences(conn, player.id), _relics(conn, player.id)
    conf = _conflicting_pairs(o)
    head = [f"Lignaggi: {len(o)} · essenze di sangue nello zaino: {ess} · reliquie: {rel}"]
    if conf:
        head.append(f"⚠ {len(conf)} conflitt{'o' if len(conf) == 1 else 'i'} tra lignaggi (elementi opposti): rischio di "
                    "SANGUE IN RIVOLTA quando ne assorbi altro. Fondili o raffinali per placarli.")
    acts = [act(f"Assorbi tutte le essenze ({ess})", "use essenze", ok=ess > 0, why="nessuna essenza", main=ess > 0),
            act("I regni delle razze (sangue d'alto lignaggio)", "razze")]
    top = noblest(conn)
    tops = B.top_lines(B.all_lines(conn))
    if top:
        low = [ln for k, ln in o if k not in tops and not _race_of(ln)]
        if low:
            g = 0.6 * sum(ln["conc"] for ln in low)
            who = (f"al {o[top - 1][1]['name']}" if len(tops) == 1 else f"ai {len(tops)} lignaggi più nobili, in parti uguali")
            acts.insert(1, act(f"Sacrifica i {len(low)} sangui meno nobili {who} (+{g:.0f}, più puri; i sangui delle "
                               "razze restano)", "sangue sacrifica tutti"))
    pur_on = state.flag(conn, B.PURIFY_KEY, False)
    acts.append(act(f"Purificazione automatica: {'ACCESA' if pur_on else 'SPENTA'} (il sangue meno nobile che "
                    "assorbi va subito ai più nobili)", "sangue purifica"))
    if not o:
        head.append("Nel tuo sangue non scorre ancora nulla. Le bestie d'alto livello e rare lasciano essenze; i "
                    "campioni delle razze antiche lasciano il sangue più alto.")
    secs.append(section("Il tuo sangue", head, acts, icon="🩸"))
    if not o:
        return menu("sangue", "🩸 IL SANGUE E I LIGNAGGI", [], secs)
    # trasformazione
    sacred = [(i, ln) for i, (_k, ln) in enumerate(o, 1) if B.grade_index(ln["conc"]) >= B.SACRED]
    if sacred:
        day = tick_mod.get_tick(conn) // 120
        wait = state.get_int(conn, "blood_transform_ready", -1) - day
        ready_now = bool(state.get(conn, "blood_transform"))
        why = "pronto: si scatenerà nel prossimo scontro" if ready_now else f"il sangue riposa ancora {wait} giorni"
        tacts = [act(f"Diventa {B.form_name(ln)}",
                     f"trasformati {i}", ok=not ready_now and wait <= 0, why=why) for i, ln in sacred[:6]]
        secs.append(section("Trasformazione (grado Sacro)", [
            "Nel prossimo scontro assumi la forma della bestia sacra: attacco moltiplicato, stati più frequenti, pelle "
            "durissima. Costa 20 di spirito, poi il sangue riposa 3 giorni."], tacts, icon="🐉"))
    # fusioni
    fs = fusion_suggestions(conn)
    if fs:
        facts = []
        for idx, why in fs:
            sp, conc, gname = _preview(conn, idx)
            facts.append(act(f"Fondi {' + '.join('#' + str(i) for i in idx)} → {sp} ({gname}, {conc:.0f})"
                             + (f" · {why}" if why else ""), "fondi_sangue " + " ".join(map(str, idx))))
        secs.append(section("Fusioni proposte (lignaggi Puri)", [
            "I lignaggi fusi tengono quasi tutta la concentrazione (90%), uniscono elementi e manifestazioni e non "
            "entrano più in conflitto. Costa un giorno."], facts, icon="⚗"))
    # lignaggi
    for i, (k, ln) in enumerate(o[:LIST_MAX], 1):
        g = B.grade_index(ln["conc"])
        prev = B.GRADES[g][0] if g < len(B.GRADES) else B.GRADES[-1][0] * (2.5 ** (g - len(B.GRADES) + 1))
        nxt = B.next_threshold(ln["conc"])
        pct = 100 * (ln["conc"] - prev) / max(1.0, nxt - prev)
        mf = B.manifestations(ln)
        gifts = list(dict.fromkeys(B._fam(f)[2] for f in ln.get("families", []) if B._fam(f)[2]))
        rk = _race_of(ln)
        lines = [(f"Purezza ×{1 + 0.1 * ln['purity']:.2f} · " if ln.get("purity") else "")
                 + f"Elementi: {', '.join(B.EL_ADJ.get(e, e) for e in _els_main_first(ln)[:4])}"
                 + (f" +{len(ln['elements']) - 4}" if len(ln['elements']) > 4 else "")
                 + (f" · dono: {', '.join(gifts)}" if gifts and g >= B.PURE else "")
                 + (" · lignaggio fuso" if ln.get("fused_from") else ""),
                 ("Manifestazioni: " + ", ".join(n for _k, n in mf)) if mf else "Nessuna manifestazione ancora.",
                 ("Tecnica innata attiva" if g >= B.PURE else f"Tecnica innata dal grado Puro")
                 + (" · TRASFORMAZIONE" if g >= B.SACRED else "")
                 + (f" · razza affine: {race_realms._name(rk)}" if rk else "")]
        acts = []
        if g >= B.SACRED:
            acts.append(act("Trasformati in questa forma", f"trasformati {i}"))
        if top and k not in tops:
            share = 0.6 * ln["conc"] / max(1, len(tops))
            acts.append(act(f"Sacrificalo ai più nobili (+{share:.0f} a ciascuno dei {len(tops)})" if len(tops) > 1
                            else f"Sacrificalo al #{top} {o[top - 1][1]['name']} (+{share:.0f}, più puro)",
                            f"sangue sacrifica {i}"))
        elif top and i != top and B.line_rank(ln) == B.line_rank(o[top - 1][1]):
            acts.append(act(f"Versalo nel #{top} {o[top - 1][1]['name']} (+{sacrifice_preview(ln, o[top - 1][1])[0]:.0f})",
                            f"sangue raffina {i} in {top}"))
        if rk:
            acts.append(act(f"Razza affine: {race_realms._name(rk)}", "razze"))
        ev_lines, ev_acts = blood_evolution.menu_lines(conn, player, i, ln)
        res = body_blood.label(conn, ln)
        if res:
            ev_lines.insert(0, res)
        lines[1:1] = ev_lines                     # l'evoluzione e la risonanza subito sotto il nome
        acts = ev_acts + acts
        rk_ = B.line_rank(ln)
        if ln.get("minor"):
            lines.append("Tratti minori assorbiti: " + ", ".join(B._fam(f)[0] for f in ln["minor"] if f in B.FAMILIES))
        secs.append(section(f"#{i} {B.RANK_ICON[rk_]} {ln['name']} — {B.grade_name(ln['conc'])} · {B.RANK_NAME[rk_]}",
                            lines, acts,
                            [bar(f"verso {B.grade_name(nxt)}", pct, f"{ln['conc']:.0f}/{nxt:.0f}", tone="bad")]))
    if len(o) > LIST_MAX:
        secs.append(section("Altri lignaggi", [f"… e altri {len(o) - LIST_MAX} lignaggi più deboli: 'sangue info' "
                                               "per vederli tutti, o versali in quelli forti ('sangue raffina <n> in <m>')."],
                            icon="🩸"))
    return menu("sangue", "🩸 IL SANGUE E I LIGNAGGI",
                ["Assorbi, fondi, raffina e trasformati: tutto il sangue che scorre in te, in un posto solo."], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus, bloodlines
    a = arg.strip().lower()
    if a in ("info", "elenco", "lista", "tutti"):
        return bloodlines.describe(conn, player)
    if a.startswith("purifica"):
        val = not state.flag(conn, bloodlines.PURIFY_KEY, False)
        state.set(conn, bloodlines.PURIFY_KEY, "1" if val else "0")
        return (f"Purificazione automatica {'ACCESA' if val else 'SPENTA'}: "
                + ("il sangue meno nobile che assorbirai andrà subito ai tuoi lignaggi più nobili, in parti uguali."
                   if val else "ogni sangue che assorbi resta un lignaggio a sé."))
    if a.startswith(("evolvi", "evolvere", "evoluzione", "evolve")):
        from engine.systems import blood_evolution
        return blood_evolution.evolve(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    if a.startswith(("raffina", "versa", "sacrifica", "offri")):
        return refine(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    return menus.show(conn, player, "sangue")
