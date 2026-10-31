"""
LA COMPRESSIONE DEL QI (Aggiornamento 75) — non sfondare subito: comprimi.

Allo Strato 10 colmo puoi tentare lo sfondamento, OPPURE continuare ad allenarti: il qi in più non si
perde, si COMPRIME nel dantian, oltre il 100%. Più ne comprimi prima di salire, più solide sono le
FONDAMENTA del nuovo regno, e i loro doni restano per sempre:

    +10%  Qi Denso                 riserva di qi +6%
    +20%  Qi Condensato            vitalità +3%
    +50%  Qi Liquido               attacco +4%, spirito +6%
   +100%  Qi Cristallino           coltivazione +5%, difesa +4%
   +300%  Qi Stellare              attacco +8%, vitalità +8%, critici +2%
   +500%  Qi del Caos Primordiale  attacco +12%, vitalità +10%, coltivazione +8%, riserva di qi +15%

LA SOGLIA DEL TALENTO. Il corpo regge fino a un certo punto, poi il qi ERROMPE e lo sfondamento parte
da solo. La soglia dipende dal talento di coltivazione (un mostro arriva al 500% senza fatica, un
mortale si ferma verso il 70%) e cresce con la PRATICA: ogni regno compresso a fondo la alza (fino a
+400%). Così anche un corpo comune, comprimendo a ogni regno, recupera chi è nato col talento.
Sotto la soglia l'eruzione è rara; sopra, quasi certa. Più comprimi, più lento è comprimere ancora.

IL PREZZO. Il qi compresso rende lo sfondamento più facile, ma è un'offesa all'ordine del Cielo: dal
100% in su, appena sali di regno, arriva una TRIBOLAZIONE DELLA COMPRESSIONE, tarata sulla tua stessa
resistenza (più comprimi, più è dura). Se la domi, le fondamenta di quel regno valgono +20%; se ti
travolge, ustioni e fondamenta −20%. Un fallimento dello sfondamento disperde metà del qi compresso.

Solo il giocatore. Stato JSON; i doni si leggono da combat_power, cult_mods, qi.max_qi, spirit.max_spirit.
"""

from __future__ import annotations

import math
import random

from engine.systems import state

KEY = "qi_compression"
GRADES = [  # (soglia in «barre»: 1.0 = +100%, nome, doni)
    (0.1, "Qi Denso", {"qi": 0.06}),
    (0.2, "Qi Condensato", {"vit": 0.03}),
    (0.5, "Qi Liquido", {"atk": 0.04, "spirit": 0.06}),
    (1.0, "Qi Cristallino", {"cult": 0.05, "def": 0.04}),
    (3.0, "Qi Stellare", {"atk": 0.08, "vit": 0.08, "crit": 0.02}),
    (5.0, "Qi del Caos Primordiale", {"atk": 0.12, "vit": 0.10, "cult": 0.08, "qi": 0.15}),
]
LABEL = {"qi": "riserva di qi", "vit": "vitalità", "atk": "attacco", "spirit": "spirito", "cult": "coltivazione",
         "def": "difesa", "crit": "critici"}
MASTERY_PER_BAR = 0.15          # ogni barra compressa (fino all'eruzione o allo sfondamento) alza la soglia
MASTERY_CAP = 4.0
TRIB_FROM = 1.0                 # dal +100% il Cielo se ne accorge


def get(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {}
    d.setdefault("over", 0.0)          # barre compresse nel regno attuale
    d.setdefault("peak", 0.0)          # il massimo raggiunto nel regno attuale
    d.setdefault("mastery", 0.0)       # pratica: alza la soglia
    d.setdefault("bonus", {})          # doni permanenti accumulati
    d.setdefault("log", [])            # [regno, barre, grado, esito della tribolazione]
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


# ---------------------------------------------------------------- il talento

def talent(conn) -> float:
    """Affinità di coltivazione 0-100 (50 = comune)."""
    from engine.systems import character
    return 50.0 * character.affinity_factor(conn, "player", 1, "cultivation")


def cap(conn, d: dict | None = None) -> float:
    """La soglia oltre cui il qi erompe (in barre). Talento + pratica."""
    d = d or get(conn)
    a = max(0.0, min(100.0, talent(conn)))
    base = 0.3 + 4.7 * (a / 90.0) ** 2           # 20 → 0,53 · 50 → 1,75 · 70 → 3,14 · 90 → 5,0
    return round(min(6.5, base) + min(MASTERY_CAP, d["mastery"]), 2)


def grade_of(over: float) -> int:
    return sum(1 for g in GRADES if over + 1e-9 >= g[0])


def grade_name(i: int) -> str:
    return GRADES[i - 1][1] if i > 0 else "Qi comune"


def gifts_of(i: int) -> dict:
    out: dict = {}
    for _t, _n, gift in GRADES[:i]:
        for k, v in gift.items():
            out[k] = out.get(k, 0.0) + v
    return out


def _fmt_gifts(g: dict) -> str:
    return ", ".join(f"{LABEL[k]} +{round(100 * v)}%" for k, v in g.items()) or "nessuno"


# ---------------------------------------------------------------- l'accumulo (da cultivation.cultivate)

def feed(conn, excess: float) -> None:
    """Il qi in più allo Strato 10 colmo. Più sei compresso, meno entra; oltre la soglia il qi erompe."""
    if excess <= 0:
        return
    d = get(conn)
    c = cap(conn, d)
    over = d["over"]
    slow = 1.0 + over / (1.5 + d["mastery"])              # più comprimi, più è lento (la pratica aiuta)
    if over > c:
        slow *= 3.0
    before = grade_of(over)
    over += excess / slow
    d["over"] = round(over, 4)
    d["peak"] = max(d.get("peak", 0.0), d["over"])
    after = grade_of(over)
    if after > before:
        d.setdefault("news", []).append(f"🌀 Il qi si comprime ancora: {grade_name(after)} (+{round(100 * GRADES[after - 1][0])}%).")
    # l'eruzione: rara sotto la soglia, quasi certa sopra
    ratio = over / max(0.1, c)
    p = 0.02 * ratio ** 6 if ratio < 1 else min(0.9, 0.2 + (ratio - 1) * 1.2)
    rng = random.Random(int(over * 10007) + int(d["mastery"] * 97))
    from engine.systems import ascension
    if rng.random() < p and not ascension.at_world_peak(conn, 1):   # al tetto del mondo il qi aspetta l'ascensione
        d["erupt"] = True
    _save(conn, d)


def take_news(conn) -> list[str]:
    d = get(conn)
    out = d.pop("news", [])
    if out:
        _save(conn, d)
    return out


def eruption_pending(conn) -> bool:
    return bool(get(conn).get("erupt"))


def clear_eruption(conn) -> None:
    d = get(conn)
    if d.pop("erupt", None):
        _save(conn, d)


def bt_bonus(conn) -> float:
    """Il qi compresso spinge: lo sfondamento è più facile (fino a +25%)."""
    return min(0.25, get(conn)["over"] * 0.06)


# ---------------------------------------------------------------- lo sfondamento

def on_breakthrough(conn, tick: int, player, success: bool) -> list[str]:
    """Riuscito: le fondamenta si consolidano (doni permanenti), poi la tribolazione della compressione.
    Fallito: metà del qi compresso si disperde."""
    d = get(conn)
    d.pop("erupt", None)
    over = d["over"]
    if not success:
        if over > 0:
            d["over"] = round(over / 2, 4)
            _save(conn, d)
            return [f"🌀 Metà del qi compresso si disperde nel contraccolpo (resta +{round(100 * d['over'])}%)."]
        _save(conn, d)
        return []
    g = grade_of(over)
    d["over"], d["peak"] = 0.0, 0.0
    d["mastery"] = round(min(MASTERY_CAP, d["mastery"] + MASTERY_PER_BAR * over), 3)
    if g == 0:
        _save(conn, d)
        return []
    lines = [f"🌀 Le fondamenta del nuovo regno si posano sul qi compresso: {grade_name(g)} (+{round(100 * over)}%)."]
    factor, trib = 1.0, ""
    if over >= TRIB_FROM:
        res = _tribulation(conn, tick, player, over)
        lines += res["lines"]
        factor = 1.2 if res["status"] == "survived" else 0.8
        trib = res["status"]
    gift = {k: v * factor for k, v in gifts_of(g).items()}
    for k, v in gift.items():
        d["bonus"][k] = round(d["bonus"].get(k, 0.0) + v, 4)
    lines.append(f"Doni permanenti: {_fmt_gifts(gift)}.")
    d["log"] = (d["log"] + [[_tier(conn), round(over, 2), g, trib]])[-40:]
    if g >= 6:
        state.grant_title(conn, "Fondamenta Contro il Cielo")
        lines.append("✧ Nuovo titolo: «Fondamenta Contro il Cielo» ✧")
    _save(conn, d)
    return lines


def _tribulation(conn, tick: int, player, over: float) -> dict:
    """La tribolazione della compressione: tarata sulla tua resistenza, più dura quanto più hai compresso."""
    from engine.simulation import combat
    from engine.systems import tribulation
    cp = combat.combat_power(conn, "player", player.id)
    resist = tribulation.fulmine_resistance(conn, player.id) + cp["defense"] * 0.5 + cp["vitality"] * 0.3
    hard = 0.55 + 0.22 * math.log2(1 + over)            # +100% → 0,77 · +300% → 0,99 · +500% → 1,12
    bolts = max(1, min(120, int(3 + 6 * math.log2(1 + 1))))
    power = int(resist * hard * bolts)
    res = tribulation.resolve_tribulation(conn, tick, random.Random(tick * 313 + int(over * 100)), power, player.id)
    res["lines"] = ["⚡ Il Cielo sente il qi che hai stretto contro le sue leggi: TRIBOLAZIONE DELLA COMPRESSIONE."] \
        + res["lines"]
    return res


# ---------------------------------------------------------------- i doni

def bonus(conn) -> dict:
    return dict(get(conn)["bonus"])


def combat_mults(conn) -> dict:
    b = bonus(conn)
    return {"attack": 1.0 + b.get("atk", 0.0), "defense": 1.0 + b.get("def", 0.0), "vitality": 1.0 + b.get("vit", 0.0)}


def combat(conn, fx) -> list[str]:
    c = bonus(conn).get("crit", 0.0)
    if c:
        fx.p.prof["crit"] = fx.p.prof.get("crit", 0.0) + c
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    v = bonus(conn).get("cult", 0.0)
    return (1.0 + v, "Fondamenta compresse") if v else (1.0, "")


def qi_mult(conn) -> float:
    return 1.0 + bonus(conn).get("qi", 0.0)


def spirit_mult(conn) -> float:
    return 1.0 + bonus(conn).get("spirit", 0.0)


# ---------------------------------------------------------------- per il giocatore

def status(conn) -> dict:
    from engine.simulation import cultivation
    d = get(conn)
    rec = cultivation.get_record(conn, "player", 1)
    ready = bool(rec and (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM and rec["progress"] >= 1.0)
    c = cap(conn, d)
    g = grade_of(d["over"])
    nxt = GRADES[g] if g < len(GRADES) else None
    ratio = d["over"] / max(0.1, c)
    risk = ("nessuno" if ratio < 0.5 else "basso" if ratio < 0.8 else "alto" if ratio < 1 else "imminente")
    return {"ready": ready, "over": d["over"], "cap": c, "grade": g, "grade_name": grade_name(g), "next": nxt,
            "risk": risk, "talent": round(talent(conn)), "mastery": d["mastery"], "bonus": d["bonus"],
            "pending": gifts_of(g), "trib": d["over"] >= TRIB_FROM}


def line_after_training(conn) -> str:
    s = status(conn)
    if not s["ready"]:
        return ""
    from engine.systems import ascension
    if ascension.at_world_peak(conn, 1):
        return (f"🌀 Qi compresso +{round(100 * s['over'])}% ({s['grade_name']}): al tetto di questo mondo non puoi "
                "sfondare. Il qi compresso ti aspetta: diventerà le fondamenta del primo regno dopo l'ascensione.")
    if s["over"] <= 0:
        return ("🌀 Sei al colmo: puoi sfondare ('breakthrough'), oppure continuare ad allenarti e COMPRIMERE il qi "
                f"oltre il 100% per fondamenta più solide (la tua soglia: ~+{round(100 * s['cap'])}%).")
    nx = f" · prossimo: {s['next'][1]} a +{round(100 * s['next'][0])}%" if s["next"] else ""
    return (f"🌀 Qi compresso +{round(100 * s['over'])}% ({s['grade_name']}){nx} · soglia ~+{round(100 * s['cap'])}% · "
            f"rischio di eruzione: {s['risk']}.")


def menu_section(conn, player):
    from engine.systems.menus import act, bar, section
    s = status(conn)
    lines = []
    if s["ready"]:
        lines.append(f"Qi compresso: +{round(100 * s['over'])}% — {s['grade_name']}. Soglia del talento: ~+{round(100 * s['cap'])}% "
                     f"(talento {s['talent']}, pratica +{round(100 * s['mastery'])}%). Rischio di eruzione: {s['risk']}.")
        if s["pending"]:
            lines.append(f"Se sfondi adesso, doni permanenti: {_fmt_gifts(s['pending'])}"
                         + (" — e arriverà la tribolazione della compressione." if s["trib"] else "."))
    else:
        lines.append("Allo Strato 10 colmo potrai continuare ad allenarti e comprimere il qi oltre il 100%: più ne "
                     f"comprimi prima di sfondare, più forti le fondamenta. La tua soglia: ~+{round(100 * s['cap'])}%.")
    lines.append("Gradi: " + " · ".join(f"+{round(100 * t)}% {n}" for t, n, _g in GRADES) + ".")
    if s["bonus"]:
        lines.append(f"Fondamenta già posate (per sempre): {_fmt_gifts(s['bonus'])}.")
    top = max(5.0, s["cap"])
    bars = [bar(f"Qi compresso: +{round(100 * s['over'])}%", 100 * s["over"] / top,
                f"soglia +{round(100 * s['cap'])}%", tone="warn" if s["risk"] in ("alto", "imminente") else "rare")]
    acts = [act("Comprimi (allenati)", "train", s["ready"], "prima riempi lo Strato 10"),
            act("Sfonda adesso", "breakthrough", s["ready"], "non sei al colmo", main=s["ready"] and s["over"] > 0)]
    return section("🌀 Compressione del Qi", lines, acts, bars, icon="🌀")


def describe(conn) -> str:
    sec = menu_section(conn, None)
    return "🌀 COMPRESSIONE DEL QI\n" + "\n".join("  " + ln for ln in sec["lines"])
