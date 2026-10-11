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
  coltivazione (fino a dimezzarla e oltre). Si smaltiscono da sole piano piano, molto più
  in fretta in ritiro, o con una Pillola di Purificazione (alchimia). Gli alchimisti esperti
  ne assorbono di meno; il Corpo dei Cento Veleni ne è immune.

  corpo       costituzione, cuore del Dao e tossine
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

HEART_KEY = "dao_heart"
TOXIN_KEY = "pill_toxin"


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
    if day - last < 20:
        return adjust(conn, -6, "sfondamenti troppo ravvicinati") + \
            ["Sei salito troppo in fretta: il cuore fatica a stare dietro al corpo."]
    return adjust(conn, 2)


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
        return float(state.get(conn, TOXIN_KEY, "0") or 0)
    except ValueError:
        return 0.0


def _set_toxin(conn, v: float) -> None:
    state.set(conn, TOXIN_KEY, f"{max(0.0, v):.1f}")


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
    return 1.0 / (1.0 + (v - 10) / 60.0), f"tossine delle pillole ({toxin_label(v)})"


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
        _set_toxin(conn, v - 1.5)
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
        _set_toxin(conn, v - 5.0 * days)
        out.append(f"Nel ritiro smaltisci le tossine: {toxin_label(v)} → {toxin_label(toxin(conn))}.")
    out += adjust(conn, min(10, days // 3))
    return out


# ============================================================
# Pannello
# ============================================================

def describe(conn, player) -> str:
    from engine.systems import constitutions
    lines = ["☯ IL TUO CORPO E IL TUO CUORE"]
    cl = constitutions.describe_line(conn)
    lines.append("  " + (cl or "Costituzione: comune (nessun corpo divino)."))
    h = heart(conn)
    lines.append(f"  Cuore del Dao: {h}/100 — {heart_label(h)}"
                 + (" (rischio di deviazione del Qi!)" if h < 30 else "")
                 + (" (illuminazioni più frequenti)" if h >= 80 else ""))
    v = toxin(conn)
    m, _ = cultivation_mult(conn)
    lines.append(f"  Tossine delle pillole: {v:.0f} — {toxin_label(v)}"
                 + (f" (coltivazione ×{m:.2f})" if m < 1 else ""))
    return "\n".join(lines)
