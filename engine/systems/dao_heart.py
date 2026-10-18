"""
CUORE DEL DAO (道心), DEVIAZIONE DEL QI (走火入魔) e TOSSINE DELLE PILLOLE (丹毒).

CUORE DEL DAO (0-100, parte da 60)
  Sale con: vittorie contro chi è più forte, illuminazioni, giuramenti mantenuti, ritiri,
            fratelli salvati.
  Scende con: sconfitte, tradimenti, demoni interiori non vinti, sfondamenti troppo ravvicinati
            (crescere troppo in fretta), e per chi ha il Corpo di Giada, l'assorbimento.
  Effetti:  sotto 30 la meditazione rischia la DEVIAZIONE DEL QI (ferite, esperienza persa,
            a volte uno strato perduto); sopra 80 la mente è limpida: illuminazioni più
            frequenti mentre mediti e sfondamenti più sicuri.

TOSSINE DELLE PILLOLE
  Ogni pillola di coltivazione lascia scorie nei meridiani. Le tossine rallentano la
  coltivazione (fino a dimezzarla e oltre). Si smaltiscono da sole (di più quando sono
  tante), molto più in fretta in ritiro, con una Pillola di Purificazione (alchimia), con
  il comando PURIFICA (un bagno di Qi al giorno, a pagamento in pietre) e a ogni nuovo
  regno (lo sfondamento lava i meridiani a metà). Con i meridiani intasati, 'use all' e
  il pilota automatico non ingoiano più pillole di coltivazione. Gli alchimisti esperti
  ne assorbono di meno; il Corpo dei Cento Veleni ne è immune.

  corpo       costituzione, cuore del Dao e tossine
  purifica    pillole di purificazione dallo zaino, poi un bagno di Qi (una volta al giorno)
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

HEART_KEY = "dao_heart"
TOXIN_KEY = "pill_toxin"
TOXIN_MAX = 300.0          # (Agg. 66) oltre, i meridiani non trattengono altro: le scorie si disperdono
TOXIN_FLOOR = 0.3          # anche avvelenato, il Qi scorre almeno a un terzo
PILL_STOP = 60.0           # da qui in su 'use all' e il pilota lasciano le pillole di coltivazione nello zaino
DAILY_BASE, DAILY_FRAC = 1.5, 0.03       # smaltimento quotidiano: fisso + una quota di ciò che c'è
RETREAT_BASE, RETREAT_FRAC = 5.0, 0.06   # in ritiro, per giorno
BATH_FRAC, BATH_MIN = 0.35, 25.0         # il bagno di Qi del comando 'purifica'
BATH_COST_PER_TIER = 30                  # pietre spirituali per regno


# ============================================================
# Cuore del Dao
# ============================================================

def heart(conn) -> int:
    from engine.systems import constitutions
    v = state.get(conn, HEART_KEY)
    base = 60 + constitutions.heart_bonus(conn)
    return max(0, min(100, int(v) if v is not None else base))


def heart_label(v: int) -> str:
    if v >= 90:
        return "limpido come il cielo"
    if v >= 75:
        return "saldo"
    if v >= 50:
        return "stabile"
    if v >= 30:
        return "incrinato"
    if v >= 15:
        return "tormentato"
    return "sull'orlo della follia"


def adjust(conn, delta: int, reason: str = "") -> list[str]:
    before = heart(conn)
    after = max(0, min(100, before + int(delta)))
    state.set(conn, HEART_KEY, str(after))
    out = []
    for th, up, down in ((30, "Il tuo cuore del Dao ritrova la calma.",
                          "⚠ Il tuo cuore del Dao si incrina: meditare ora è pericoloso (deviazione del Qi)."),
                         (80, "✦ Il tuo cuore del Dao si fa limpido: le illuminazioni verranno più facilmente.",
                          "Il tuo cuore del Dao perde un poco della sua limpidezza.")):
        if before < th <= after:
            out.append(up)
        elif after < th <= before:
            out.append(down)
    return out


def breakthrough_bonus(conn) -> float:
    return (heart(conn) - 50) / 500.0


def on_breakthrough(conn) -> list[str]:
    """Crescere troppo in fretta incrina il cuore."""
    day = tick_mod.get_tick(conn) // 120
    last = state.get_int(conn, "last_bt_day", -999)
    state.set(conn, "last_bt_day", str(day))
    tox = []
    v = toxin(conn)
    if v >= 10:
        _set_toxin(conn, v * 0.5)
        tox = [f"Il nuovo regno lava i meridiani: tossine {v:.0f} → {v * 0.5:.0f}."]
    if day - last < 20:
        return tox + adjust(conn, -6, "sfondamenti troppo ravvicinati") + \
            ["Sei salito troppo in fretta: il cuore fatica a stare dietro al corpo."]
    return tox + adjust(conn, 2)


def on_cultivate(conn, t: int, rng: random.Random, player) -> list[str]:
    """Chiamato a ogni sessione di meditazione: deviazione del Qi o illuminazione."""
    from engine.simulation import cultivation
    h = heart(conn)
    if h < 30 and rng.random() < 0.05 + (30 - h) * 0.005:
        rec = cultivation.get_record(conn, "player", player.id)
        lines = ["⚠ DEVIAZIONE DEL QI: il Qi ti si rivolta contro nei meridiani!"]
        conn.execute(
            "INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
            "healed, heal_tick) VALUES ('player', ?, 3, 'deviazione del Qi', ?, 0, ?);", (player.id, t, t + 60))
        if rec:
            if rec["progress"] >= 0.3 or (rec["stage"] or 1) <= 1:
                conn.execute("UPDATE cultivation_records SET progress=MAX(0, progress-0.3) WHERE id=?;", (rec["id"],))
                lines.append("Perdi parte dell'esperienza accumulata, e ne esci ferito.")
            else:
                conn.execute("UPDATE cultivation_records SET stage=stage-1, progress=0.7 WHERE id=?;", (rec["id"],))
                lines.append("Precipiti di uno STRATO, e ne esci ferito.")
        n = state.get_int(conn, "qi_deviations", 0) + 1
        state.set(conn, "qi_deviations", str(n))
        return lines
    if h >= 80 and rng.random() < 0.02 + (h - 80) * 0.001:
        from engine.systems import seclusion
        return seclusion.illumination(conn, t, rng, player, "nella quiete del cuore")
    return []


# ============================================================
# Tossine
# ============================================================

def toxin(conn) -> float:
    try:
        return min(TOXIN_MAX, float(state.get(conn, TOXIN_KEY, "0") or 0))
    except ValueError:
        return 0.0


def _set_toxin(conn, v: float) -> None:
    state.set(conn, TOXIN_KEY, f"{min(TOXIN_MAX, max(0.0, v)):.1f}")


def toxin_label(v: float) -> str:
    if v < 10:
        return "meridiani puliti"
    if v < 30:
        return "lievi scorie"
    if v < 60:
        return "scorie evidenti"
    if v < 100:
        return "meridiani intasati"
    return "meridiani avvelenati"


def cultivation_mult(conn) -> tuple[float, str]:
    v = toxin(conn)
    if v < 10:
        return 1.0, ""
    # (Agg. 66) un pavimento: prima a 1.200 tossine la coltivazione scendeva a ×0,05, una trappola senza uscita
    return max(TOXIN_FLOOR, 1.0 / (1.0 + (v - 10) / 60.0)), f"tossine delle pillole ({toxin_label(v)})"


def on_pill(conn, pid: int, potency: float) -> list[str]:
    """Una pillola di coltivazione consumata: aggiunge tossine."""
    from engine.systems import constitutions, professions
    if potency <= 0 or constitutions.toxin_immune(conn):
        return []
    red = 1.0
    if professions.has(conn, "alchimia"):
        red = max(0.3, 1.0 - 0.04 * professions.level(conn, pid, "alchimia"))
    before = toxin(conn)
    after = before + 25.0 * potency * red
    _set_toxin(conn, after)
    out = []
    for th in (30, 60, 100):
        if before < th <= after:
            out.append(f"⚠ Le tossine delle pillole si accumulano ({toxin_label(after)}): la coltivazione rallenta. "
                       "Un ritiro o una Pillola di Purificazione le smaltiscono.")
            break
    return out


def purify(conn, amount: float) -> str:
    before = toxin(conn)
    _set_toxin(conn, before - amount)
    return f"Le scorie si sciolgono: {toxin_label(before)} → {toxin_label(toxin(conn))}."


def daily(conn, t: int, rng, player) -> list[str]:
    v = toxin(conn)
    if v > 0:
        _set_toxin(conn, v - DAILY_BASE - DAILY_FRAC * v)
    # il tempo guarisce: un cuore ferito torna piano verso la calma (più in fretta quando è
    # in pericolo). Senza questo un cuore a zero era una spirale senza uscita.
    from engine.systems import constitutions
    h, base = heart(conn), 60 + constitutions.heart_bonus(conn)
    if h < base:
        return adjust(conn, 3 if h < 30 else 1)
    return []


def on_retreat_days(conn, days: int) -> list[str]:
    out = []
    v = toxin(conn)
    if v > 0:
        w = v
        for _ in range(max(0, days)):
            w = w - RETREAT_BASE - RETREAT_FRAC * w
        _set_toxin(conn, w)
        out.append(f"Nel ritiro smaltisci le tossine: {toxin_label(v)} → {toxin_label(toxin(conn))}.")
    out += adjust(conn, min(10, days // 3))
    return out


def pills_blocked(conn) -> bool:
    """Meridiani intasati: le pillole di coltivazione farebbero più male che bene."""
    from engine.systems import constitutions
    return toxin(conn) >= PILL_STOP and not constitutions.toxin_immune(conn)


def purify_command(conn, player) -> str:
    """PURIFICA: prima le Pillole di Purificazione dello zaino, poi un bagno di Qi (una volta al giorno)."""
    from engine.systems import items, sects
    from engine.simulation import cultivation
    v0 = toxin(conn)
    if v0 < 1:
        return "I tuoi meridiani sono puliti: non c'è nulla da purificare."
    out = [f"Purifichi i meridiani (tossine {v0:.0f} — {toxin_label(v0)})."]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 41 + player.id)
    for r in items.player_inventory(conn, player.id):
        if toxin(conn) < 1:
            break
        if "purificazione" not in r["name"].lower():
            continue
        for _ in range(r["quantity"]):
            if toxin(conn) < 1:
                break
            res = items.use_item(conn, t, rng, player.id, r["name"])
            if res["status"] == "used":
                out.append(f"  · {res['name']}: " + "; ".join(res["lines"]))
    day = t // 120
    v = toxin(conn)
    if v >= 1:
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        cost = BATH_COST_PER_TIER * tier
        if state.get_int(conn, "purify_day", -1) == day:
            out.append("  Il bagno di Qi l'hai già fatto oggi: domani potrai ripeterlo (o ritirati: 'ritiro 5').")
        elif sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
            out.append(f"  Per un bagno di Qi servono {cost} pietre spirituali.")
        else:
            sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
            state.set(conn, "purify_day", str(day))
            cut = max(BATH_MIN, BATH_FRAC * v)
            _set_toxin(conn, v - cut)
            out.append(f"  Bagno di Qi ({cost} pietre): sciogli le scorie col fuoco del tuo Qi, "
                       f"{v:.0f} → {toxin(conn):.0f}.")
    v1 = toxin(conn)
    m, _ = cultivation_mult(conn)
    out.append(f"Tossine ora: {v1:.0f} — {toxin_label(v1)}" + (f" (coltivazione ×{m:.2f})" if m < 1 else "") + ".")
    if v1 >= 10:
        out.append("Le tossine calano anche da sole ogni giorno, molto di più in ritiro, e si dimezzano a ogni nuovo regno.")
    return "\n".join(out)


# ============================================================
# Pannello
# ============================================================

def describe(conn, player) -> str:
    from engine.systems import constitutions
    lines = ["☯ IL TUO CORPO E IL TUO CUORE"]
    lines += ["  " + ln for ln in constitutions.describe_full(conn).splitlines()]
    h = heart(conn)
    lines.append(f"  Cuore del Dao: {h}/100 — {heart_label(h)}"
                 + (" (rischio di deviazione del Qi!)" if h < 30 else "")
                 + (" (illuminazioni più frequenti)" if h >= 80 else ""))
    v = toxin(conn)
    m, _ = cultivation_mult(conn)
    lines.append(f"  Tossine delle pillole: {v:.0f} — {toxin_label(v)}"
                 + (f" (coltivazione ×{m:.2f})" if m < 1 else ""))
    return "\n".join(lines)
