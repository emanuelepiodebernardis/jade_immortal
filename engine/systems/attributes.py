"""
FINESTRA DI STATO — gli attributi del coltivatore (ispirata a «The Gamer»).

In «The Gamer» il protagonista vede la sua vita come un gioco: una finestra di stato con
livello, PV, PM, sei attributi e punti da distribuire a ogni livello; osserva gli altri e ne
legge il livello. Qui:

LIVELLO = (regno − 1) × 10 + strato. Ogni strato guadagnato dà 1 PUNTO ATTRIBUTO, ogni regno
superato 5 in più, e ogni 5 titoli uno di bonus. I punti si distribuiscono fra:

  FOR  Forza       attacco
  VIT  Vitalità    vita
  AGI  Agilità     difesa e schivata
  INT  Intelletto  Qi massimo
  SAG  Saggezza    spirito massimo e velocità di comprensione dei Dao
  FRT  Fortuna     sfondamenti più probabili

L'effetto è logaritmico e senza tetto: i primi punti si sentono molto, poi sempre meno, ma
non smettono mai di contare. La forza resta nel regno; gli attributi danno la «forma» al tuo
personaggio.

  stato_finestra (o «finestra»)    la finestra di stato
  attributi                        menu dei punti
  attributi <FOR|VIT|AGI|INT|SAG|FRT> [n]   distribuisci
  attributi bilancia               distribuisci tutto in modo bilanciato
  attributi auto on|off            il pilota automatico li distribuisce da solo
  osserva <nome>                   la finestra di stato di un altro
"""

from __future__ import annotations

import math

from engine.systems import state

KEY = "attributes"
AUTO_KEY = "attributes_auto"
ATTRS = ["FOR", "VIT", "AGI", "INT", "SAG", "FRT"]
NAMES = {"FOR": "Forza", "VIT": "Vitalità", "AGI": "Agilità", "INT": "Intelletto", "SAG": "Saggezza", "FRT": "Fortuna"}
EFFECT = {"FOR": "attacco", "VIT": "vita", "AGI": "difesa e schivata", "INT": "Qi massimo",
          "SAG": "spirito e comprensione dei Dao", "FRT": "sfondamenti"}
ALIAS = {"forza": "FOR", "str": "FOR", "vitalita": "VIT", "vitalità": "VIT", "vit": "VIT", "agilita": "AGI",
         "agilità": "AGI", "dex": "AGI", "agi": "AGI", "intelletto": "INT", "int": "INT", "saggezza": "SAG",
         "wis": "SAG", "sag": "SAG", "fortuna": "FRT", "luk": "FRT", "frt": "FRT", "for": "FOR"}


def level(conn, pid: int = 1) -> int:
    from engine.simulation import cultivation
    t = cultivation.realm_tier(conn, "player", pid) or 1
    st = cultivation.stage_of(conn, "player", pid) or 1
    return (t - 1) * 10 + st


def earned(conn, pid: int = 1) -> int:
    from engine.simulation import cultivation
    t = cultivation.realm_tier(conn, "player", pid) or 1
    from engine.systems import system_daily           # le missioni quotidiane del Sistema
    return level(conn, pid) + 5 * (t - 1) + len(state.titles(conn)) // 5 + 3 + system_daily.bonus_points(conn)


def allocated(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {}
    return {a: int(d.get(a, 0)) for a in ATTRS}


def free(conn, pid: int = 1) -> int:
    return max(0, earned(conn, pid) - sum(allocated(conn).values()))


def mult(conn, attr: str) -> float:
    p = allocated(conn).get(attr, 0)
    return 1.0 + 0.22 * math.log2(1 + p / 4) if p > 0 else 1.0


def combat_mults(conn) -> dict:
    return {"attack": mult(conn, "FOR"), "vitality": mult(conn, "VIT"), "defense": mult(conn, "AGI")}


def qi_mult(conn) -> float:
    return mult(conn, "INT")


def spirit_mult(conn) -> float:
    return 1.0 + (mult(conn, "SAG") - 1.0) * 0.6


def dao_mult(conn) -> float:
    return 1.0 + (mult(conn, "SAG") - 1.0) * 0.5


def bt_bonus(conn) -> float:
    p = allocated(conn).get("FRT", 0)
    return min(0.2, 0.025 * math.log2(1 + p / 2)) if p > 0 else 0.0


def assign(conn, attr: str, n: int, pid: int = 1) -> str:
    attr = ALIAS.get(attr.lower(), attr.upper())
    if attr not in ATTRS:
        return "Attributo sconosciuto: FOR, VIT, AGI, INT, SAG, FRT."
    f = free(conn, pid)
    if f <= 0:
        return "Non hai punti attributo liberi. Ne guadagni uno a ogni strato, cinque in più a ogni regno."
    n = max(1, min(f, n))
    d = allocated(conn)
    d[attr] += n
    state.set_json(conn, KEY, d)
    return f"[Sistema] {NAMES[attr]} +{n} → {d[attr]} ({EFFECT[attr]} ×{mult(conn, attr):.2f}). Punti liberi: {free(conn, pid)}."


def balance(conn, pid: int = 1) -> str:
    f = free(conn, pid)
    if f <= 0:
        return "Nessun punto da distribuire."
    d = allocated(conn)
    for _ in range(f):
        a = min(ATTRS, key=lambda k: (d[k], ATTRS.index(k)))
        d[a] += 1
    state.set_json(conn, KEY, d)
    return f"[Sistema] Distribuiti {f} punti in modo bilanciato: " + ", ".join(f"{a} {d[a]}" for a in ATTRS) + "."


def auto_spend(conn, pid: int = 1) -> list[str]:
    if not state.flag(conn, AUTO_KEY, False) or free(conn, pid) <= 0:
        return []
    return [balance(conn, pid)]


def window(conn, pid: int = 1) -> dict:
    """I dati della finestra di stato (per la dashboard e per il terminale)."""
    from engine.core import entities
    from engine.simulation import combat, cultivation
    from engine.systems import qi, spirit, sects, reputation, karma
    p = entities.get_player(conn)
    cp = combat.combat_power(conn, "player", pid)
    rec = cultivation.get_record(conn, "player", pid)
    al = allocated(conn)
    titles = state.titles(conn)
    try:
        rep = reputation.get(conn, pid)
        fame = rep["fame"] if rep else 0
    except Exception:
        fame = 0
    return {
        "nome": p.name if p else "?", "livello": level(conn, pid),
        "regno": cultivation.realm_name(conn, "player", pid) if hasattr(cultivation, "realm_name") else "",
        "titolo": titles[-1] if titles else "—", "titoli": len(titles),
        "pv": int(cp["vitality"]), "attacco": int(cp["attack"]), "difesa": int(cp["defense"]),
        "qi": [qi.get_qi(conn, pid), qi.max_qi(conn, pid)],
        "spirito": [spirit.get_spirit(conn, pid) if hasattr(spirit, "get_spirit") else 0, spirit.max_spirit(conn, pid)],
        "attributi": [{"k": a, "nome": NAMES[a], "punti": al[a], "mult": round(mult(conn, a), 2), "effetto": EFFECT[a]}
                      for a in ATTRS],
        "liberi": free(conn, pid),
        "corpo": int(rec["body_level"] or 0) if rec else 0, "anima": int(rec["soul_level"] or 0) if rec else 0,
        "pietre": sects.get_resource(conn, "pietre_spirituali", pid), "fama": fame,
        "karma": karma.get_karma(conn, "player", pid),
        "auto": state.flag(conn, AUTO_KEY, False),
        "rango": __import__("engine.systems.system_daily", fromlist=["x"]).hunter_rank(conn, pid),
    }


def window_text(conn, pid: int = 1) -> str:
    w = window(conn, pid)
    lines = ["╔══════════ FINESTRA DI STATO ══════════╗",
             f"  {w['nome']} · Livello {w['livello']} · Rango {w['rango']} · {w['regno']}",
             f"  Titolo: {w['titolo']}  ({w['titoli']} titoli)",
             f"  PV {w['pv']} · ATT {w['attacco']} · DIF {w['difesa']}",
             f"  Qi {w['qi'][0]}/{w['qi'][1]} · Spirito {w['spirito'][0]}/{w['spirito'][1]}",
             f"  Corpo {w['corpo']} · Anima {w['anima']} · Karma {w['karma']}",
             f"  Pietre {w['pietre']} · Fama {w['fama']}",
             "  ─────────────── attributi ───────────────"]
    for a in w["attributi"]:
        lines.append(f"  {a['k']} {a['nome']:<10} {a['punti']:>4}   {a['effetto']} ×{a['mult']:.2f}")
    lines.append(f"  Punti liberi: {w['liberi']}" + ("  (distribuzione automatica attiva)" if w["auto"] else ""))
    lines.append("╚════════════════════════════════════════╝")
    if w["liberi"]:
        lines.append("Distribuisci: «attributi FOR 3», oppure «attributi bilancia».")
    return "\n".join(lines)


def observe(conn, player, arg: str) -> str:
    """«Osserva»: la finestra di stato di qualcuno che hai davanti."""
    from engine.simulation import cultivation
    from engine.systems import perception, pursuers
    a = (arg or "").strip().lower()
    rows = conn.execute("SELECT id, name, kind, archetype FROM npcs WHERE location_id=? AND status='alive';",
                        (player.location_id,)).fetchall()
    rows = [r for r in rows if a and a in r["name"].lower()] if a else rows[:1]
    if not rows:
        return "Non vedi nessuno con quel nome qui."
    r = rows[0]
    t = cultivation.realm_tier(conn, "npc", r["id"]) or 1
    st = cultivation.stage_of(conn, "npc", r["id"]) or 1
    lvl = (t - 1) * 10 + st
    dao = conn.execute("SELECT d.name, cd.comprehension FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
                       "WHERE cd.character_type='npc' AND cd.character_id=? ORDER BY cd.comprehension DESC LIMIT 1;",
                       (r["id"],)).fetchone()
    kind = dict(pursuers.tracked(conn)).get(r["id"])
    lines = [f"[Osserva] {r['name']} — Livello {lvl}",
             f"  {r['archetype'] or r['kind'] or ''} · {perception.relative_strength(conn, player.id, r['id'])}"]
    if dao:
        lines.append(f"  Dao principale: {dao['name']} ({dao['comprehension']})")
    if kind:
        lines.append(f"  ⚠ Ti dà la caccia ({kind}).")
    return "\n".join(lines)


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    w = window(conn, player.id)
    secs = [section("Finestra di stato", [
        f"{w['nome']} · Livello {w['livello']} · Titolo: {w['titolo']}",
        f"PV {w['pv']} · ATT {w['attacco']} · DIF {w['difesa']} · Qi {w['qi'][1]} · Spirito {w['spirito'][1]}",
        f"Punti liberi: {w['liberi']}"], [
        act("Distribuisci in modo bilanciato", "attributi bilancia", w["liberi"] > 0, "nessun punto libero", main=True),
        act("Distribuzione automatica: " + ("ON" if w["auto"] else "OFF"), "attributi auto " + ("off" if w["auto"] else "on"))],
        icon="🪟")]
    mx = max([a["punti"] for a in w["attributi"]] + [1])
    for a in w["attributi"]:
        secs.append(section(f"{a['k']} — {a['nome']}", [f"{a['effetto']} ×{a['mult']:.2f}"],
                            [act("+1", f"attributi {a['k']} 1", w["liberi"] > 0, "nessun punto libero"),
                             act("+5", f"attributi {a['k']} 5", w["liberi"] >= 5, "servono 5 punti")],
                            [bar(a["nome"], 100 * a["punti"] / mx, str(a["punti"]))], icon="◆"))
    return menu("attributi", "🪟 ATTRIBUTI",
                ["Un punto a ogni strato, cinque a ogni regno, uno ogni cinque titoli."], secs)


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().split()
    if not a:
        from engine.systems import menus
        return menus.show(conn, player, "attributi")
    if a[0].lower() in ("bilancia", "bilanciato", "auto_distribuisci"):
        return balance(conn, player.id)
    if a[0].lower() == "auto":
        on = not (len(a) > 1 and a[1].lower() in ("off", "no", "0"))
        state.set(conn, AUTO_KEY, "1" if on else "0")
        return f"Distribuzione automatica dei punti: {'attiva' if on else 'spenta'}."
    n = int(a[1]) if len(a) > 1 and a[1].isdigit() else 1
    return assign(conn, a[0], n, player.id)
