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
    fams = set(ln.get("families") or [])
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
    top = pure[:6]
    for i, j in itertools.combinations(top, 2):
        if ([i, j], "risolve un conflitto") not in out:
            out.append(([i, j], ""))
    if len(pure) >= 3:
        out.insert(min(1, len(out)), (pure[:3], "i tre più forti"))
    return out[:limit]


def _preview(conn, idx: list[int]) -> tuple[str, float, str]:
    from engine.systems import bloodlines as B
    o = B.ordered(conn)
    picks = [o[i - 1][1] for i in idx]
    fams, els = [], []
    for ln in picks:
        for f in ln["families"] or ["bestia"]:
            if f not in fams:
                fams.append(f)
        for e in ln["elements"]:
            if e not in els:
                els.append(e)
    noun = "-".join(B._fam(f)[0] for f in fams if f in B.FAMILIES) or "Chimera"
    species = f"{noun} di " + " e ".join(B.EL_ADJ.get(e, e.title()) for e in els)
    conc = 0.9 * sum(ln["conc"] for ln in picks)
    return species, conc, B.grade_name(conc)


def refine(conn, player, arg: str) -> str:
    """Versa il lignaggio n nel lignaggio m (70% se hanno famiglia o elemento in comune, altrimenti 50%)."""
    from engine.systems import bloodlines as B
    p = [x for x in arg.replace("in", " ").split() if x.isdigit()]
    o = B.ordered(conn)
    if len(p) != 2 or p[0] == p[1] or not all(1 <= int(x) <= len(o) for x in p):
        return "Usa: sangue raffina <n> in <m> (i numeri del menu del sangue)."
    (ka, la), (kb, lb) = o[int(p[0]) - 1], o[int(p[1]) - 1]
    share = set(la.get("families") or []) & set(lb.get("families") or []) or set(la["elements"]) & set(lb["elements"])
    rate = 0.7 if share else 0.5
    d = B.all_lines(conn)
    before = B.grade_index(lb["conc"])
    d[kb]["conc"] = round(lb["conc"] + rate * la["conc"], 1)
    d.pop(ka, None)
    B._save(conn, d)
    from engine.simulation import world_tick
    world_tick.advance(conn, tick_mod.cost_of("cultivate"))
    out = [f"Lasci che il {la['name']} si sciolga nel {lb['name']}: ne assorbe il {int(rate * 100)}%.",
           f"🩸 {lb['name']}: concentrazione {d[kb]['conc']:.0f} ({B.grade_name(d[kb]['conc'])})."]
    after = B.grade_index(d[kb]["conc"])
    if after > before:
        out += B._on_grade_up(conn, d[kb], before, after)
    return "\n".join(out)


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import bloodlines as B, race_realms
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
        tacts = [act(f"Diventa {'-'.join(B._fam(f)[0] for f in ln['families'] if f in B.FAMILIES) or ln['species']}",
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
        gifts = [B._fam(f)[2] for f in ln.get("families", []) if B._fam(f)[2]]
        rk = _race_of(ln)
        lines = [f"Elementi: {', '.join(B.EL_ADJ.get(e, e) for e in ln['elements'])}"
                 + (f" · dono: {', '.join(gifts)}" if gifts and g >= B.PURE else "")
                 + (" · lignaggio fuso" if ln.get("fused_from") else ""),
                 ("Manifestazioni: " + ", ".join(n for _k, n in mf)) if mf else "Nessuna manifestazione ancora.",
                 ("Tecnica innata attiva" if g >= B.PURE else f"Tecnica innata dal grado Puro")
                 + (" · TRASFORMAZIONE" if g >= B.SACRED else "")
                 + (f" · razza affine: {race_realms._name(rk)}" if rk else "")]
        acts = []
        if g >= B.SACRED:
            acts.append(act("Trasformati in questa forma", f"trasformati {i}"))
        if i != 1:
            acts.append(act(f"Versalo nel #1 ({o[0][1]['name']})", f"sangue raffina {i} in 1"))
        if rk:
            acts.append(act(f"Razza affine: {race_realms._name(rk)}", "razze"))
        secs.append(section(f"#{i} {ln['name']} — {B.grade_name(ln['conc'])}", lines, acts,
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
    if a.startswith(("raffina", "versa")):
        return refine(conn, player, a.split(maxsplit=1)[1] if " " in a else "")
    return menus.show(conn, player, "sangue")
