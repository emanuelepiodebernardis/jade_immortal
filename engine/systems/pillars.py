"""
I SEI PILASTRI (Aggiornamento 73) — quindici fonti di forza raccolte in sei, ognuna con un ruolo chiaro.

Prima il giocatore vedeva una quindicina di sistemi separati (meridiani, sangue, corpo, Dao profondi,
spiriti, tecniche, dantian, tempra dell'anima, vasi, Dharma, sigilli, equipaggiamento, arma,
cavalcatura, bestie, compagni, cloni…). Ora stanno in sei PILASTRI, ognuno con un modo diverso di
crescere:

  ☯ Regno          la scala di tutto: sfondamenti, doni della tribolazione, destini, cuore del Dao
  🩸 Corpo          ciò che sei di carne: corpo leggendario, sangue, meridiani
  🌌 Dao            ciò che capisci: amplificatore dei Dao, spiriti del Dao, tecniche
  ✧ Anima          ciò che sei dentro: tempra dell'anima, vasi d'anima, Dharma, sigilli ancestrali
  ⚔ Ciò che porti  equipaggiamento, arma, cavalcatura
  ♥ Legami         compagni e fratelli, bestie, servi e schiavi, discepoli e cloni

Ogni pilastro ha un punteggio 0-100 RISPETTO AL TUO REGNO (quanto di ciò che il regno permette hai
già costruito). Nessun sistema cambia: i pilastri li leggono e basta. In più:

  ARMONIA DEI PILASTRI — quando il pilastro più debole si avvicina alla media degli altri, il cultivatore è
  «intero»: fino a +12% di potenza e +10% di coltivazione. Non toglie mai niente a nessuno: premia
  chi cresce in modo completo, e indica sempre il pilastro da alzare (con il comando da cliccare).

Il calcolo costa qualche query: si rifà una volta al giorno (e quando apri la scheda), e il
combattimento legge solo il valore salvato. Aggiungere una fonte = una riga in _metrics().
"""

from __future__ import annotations

from engine.systems import state

KEY = "pillars"
ORDER = ["regno", "corpo", "dao", "anima", "porti", "legami"]
LABEL = {"regno": "☯ Regno", "corpo": "🩸 Corpo", "dao": "🌌 Dao", "anima": "✧ Anima",
         "porti": "⚔ Ciò che porti", "legami": "♥ Legami"}
ROLE = {"regno": "la scala di tutto: ogni sfondamento moltiplica il resto",
        "corpo": "resistere e colpire con la carne: vitalità, difesa, sangue che si risveglia",
        "dao": "capire: i Dao amplificano ogni colpo, le tecniche li mettono in pratica",
        "anima": "ciò che sei dentro: crescita più rapida, vasi e sigilli che combattono con te",
        "porti": "ciò che indossi e impugni: la via più rapida, ma la prima a restare indietro",
        "legami": "chi cammina con te o ti obbedisce: compagni, bestie, servi, schiavi e discepoli"}
CMD = {"regno": "via coltivazione", "corpo": "via corpo", "dao": "via profondi", "anima": "via anime",
       "porti": "equip", "legami": "legami"}
HARMONY_ATK = 0.12
HARMONY_CULT = 0.10
LOW_START = 0.3                      # sotto questo rapporto (il più debole / la media) l'armonia non c'è
MIN_TOP = 15                         # serve almeno un pilastro a 15 perché l'armonia abbia senso


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


def _day(conn) -> int:
    from engine.core import tick
    return tick.get_tick(conn) // 120


def _safe(fn, default=0.0):
    try:
        return fn()
    except Exception:                                   # noqa: BLE001 — un sistema assente vale zero, non rompe
        return default


# ---------------------------------------------------------------- le fonti, pilastro per pilastro

def _metrics(conn, t: int) -> dict[str, list[tuple[str, float, float, str]]]:
    """{pilastro: [(fonte, peso, frazione 0..1 rispetto al regno, comando)]}. Peso 0 = non ancora sbloccata."""
    from engine.systems import (tribulation, breakthrough_fates, dao_heart, constitutions, bloodlines, meridians,
                                dao_training, dao_spirits, guild, soul_temper, soul_artifacts, dharma_body,
                                ancestral_sigils, gear, weapons, mounts, beasts, clones)
    from engine.simulation import combat

    def merid():
        d = meridians.get(conn)
        cap = max(1, meridians.openable(conn))
        o = min(d.get("open", 0), cap)
        lv = d.get("lv", [])[:o]
        temper = (sum(lv) / len(lv)) / max(1, t) if lv else 0.0
        return 0.7 * o / cap + 0.3 * min(1.0, temper)

    def blood():
        lines = bloodlines.ordered(conn)
        if not lines:
            return 0.0
        return bloodlines.grade_index(max(v.get("conc", 0) for _k, v in lines)) / min(6, t + 1)

    def amp():
        a = combat.dao_amplifier(dao_training.dao_power(conn, "player", 1), t)
        return (a - 1.0) / 1.2

    def gear_f():
        eq = gear.get(conn).get("eq", {})
        tot = 0.0
        for s in gear.ORDER:
            it = eq.get(s)
            if it:
                r = gear.RARITY.index(it["rar"]) if it.get("rar") in gear.RARITY else 0
                tot += (0.4 + 0.2 * r) * min(1.0, (it.get("tier") or 1) / t)
        return tot / len(gear.ORDER)

    def vasi():
        own = soul_artifacts.owned(conn)
        if not own:
            return 0.0
        lv = sum(soul_artifacts.level(conn, k) for k in own) / len(own)
        return 0.6 * len(own) / min(4, max(1, t // 2)) + 0.4 * min(1.0, lv / max(1, t))

    def sigils():
        d = ancestral_sigils.get(conn)
        return len(d.get("eq", [])) / max(1, ancestral_sigils.slots(conn))

    def friends():
        n = conn.execute("SELECT COUNT(*) n FROM bonds b JOIN npcs x ON x.id=b.npc_id WHERE b.player_id=1 "
                         "AND b.status='active' AND x.status='alive' AND b.kind IN "
                         "('companion','sworn','dao_partner','master','friend','lover');").fetchone()["n"]
        return n / min(4, 1 + t // 2)

    def followers():
        from engine.systems import own_sect
        n = len(_safe(lambda: own_sect.disciples(conn, 1), [])) + len(_safe(lambda: clones.clones(conn), []))
        n += conn.execute("SELECT COUNT(*) n FROM bonds b JOIN npcs x ON x.id=b.npc_id WHERE b.player_id=1 AND "
                          "b.status='active' AND x.status='alive' AND b.kind='disciple';").fetchone()["n"]
        return n / max(1, t // 2)

    def servants():
        from engine.systems import dominion                # servi col sigillo dell'anima, scorta, salme: gente che comandi
        ids = {r["npc_id"] for r in dominion.servants(conn)}
        ids |= {r["npc_id"] for r in conn.execute(
            "SELECT b.npc_id FROM bonds b JOIN npcs x ON x.id=b.npc_id WHERE b.player_id=1 AND b.status='active' "
            "AND x.status='alive' AND b.kind IN ('servo','scorta');")}
        return len(ids) / max(2, t)

    def beasts_f():
        n = conn.execute("SELECT COUNT(*) n FROM bonds b JOIN npcs x ON x.id=b.npc_id WHERE b.player_id=1 AND "
                         "b.status='active' AND x.status='alive' AND b.kind='beast';").fetchone()["n"]
        return max(n, len(beasts.pets(conn, 1))) / min(3, 1 + t // 3)

    awake_w = 1.0 if t >= dharma_body.AWAKEN_TIER else 0.0
    return {
        "regno": [("Doni della tribolazione", 1.0, _safe(lambda: len(tribulation.boon_list(conn)) / max(1, t - 1)), "via coltivazione"),
                  ("Destini dello sfondamento", 1.0 if t >= 2 else 0.0,
                   _safe(lambda: len(breakthrough_fates.chosen(conn)) / max(1, t - 1)), "via coltivazione"),
                  ("Cuore del Dao", 1.0, _safe(lambda: dao_heart.heart(conn) / 80), "via corpo")],
        "corpo": [("Corpo leggendario", 1.0, _safe(lambda: constitutions.stage(conn) / min(7, t)), "via corpo"),
                  ("Sangue", 1.0, _safe(blood), "via sangue"),
                  ("Meridiani", 1.0, _safe(merid), "via meridiani")],
        "dao": [("Amplificatore dei Dao", 1.5, _safe(amp), "via profondi"),
                ("Spiriti del Dao", 1.0, _safe(lambda: len(dao_spirits.spirits(conn)) / max(1, t // 3)), "via spiriti"),
                ("Tecniche", 1.0, _safe(lambda: len(guild.learned(conn)) / (3 * t)), "via tecniche")],
        "anima": [("Tempra dell'anima", 1.5, _safe(lambda: soul_temper.grade(conn) / (2 * t + 1)), "via anime"),
                  ("Vasi d'anima", 1.0 if t >= 2 else 0.0, _safe(vasi), "via anime"),
                  ("Corpo del Dharma", awake_w, _safe(lambda: 1.0 if dharma_body.get(conn).get("awake") else 0.0), "via dharma"),
                  ("Sigilli ancestrali", 1.0 if t >= 2 else 0.0, _safe(sigils), "via dharma")],
        "porti": [("Equipaggiamento", 2.0, _safe(gear_f), "equip"),
                  ("Arma", 1.0, _safe(lambda: weapons.equipped_bonus(conn, 1) / (0.05 + 0.035 * t)), "equip"),
                  ("Cavalcatura", 0.5 if t >= 2 else 0.0, _safe(lambda: 1.0 if mounts.mounted(conn) else 0.0), "cavalca")],
        "legami": [("Compagni e fratelli", 1.5, _safe(friends), "legami"),
                   ("Bestie", 1.0, _safe(beasts_f), "bestie"),
                   ("Servi e schiavi", 1.0 if t >= 2 else 0.0, _safe(servants), "dominio"),
                   ("Discepoli e cloni", 1.0 if t >= 3 else 0.0, _safe(followers), "discepoli")],
    }


def compute(conn) -> dict:
    """I punteggi: {"scores": {pilastro: 0..100}, "parts": {pilastro: [(fonte, %, comando)]}, …}."""
    t = _tier(conn)
    m = _metrics(conn, t)
    scores, parts = {}, {}
    for k in ORDER:
        rows = [(n, w, max(0.0, min(1.0, f)), c) for n, w, f, c in m[k]]
        tw = sum(w for _n, w, _f, _c in rows) or 1.0
        scores[k] = round(100 * sum(w * f for _n, w, f, _c in rows) / tw)
        parts[k] = [(n, round(100 * f), c) for n, w, f, c in rows if w > 0]
    return {"tier": t, "scores": scores, "parts": parts, **_harmony(scores)}


def _harmony(scores: dict) -> dict:
    lo_k = min(ORDER, key=lambda k: scores[k])
    hi_k = max(ORDER, key=lambda k: scores[k])
    hi = scores[hi_k]
    mean = sum(scores.values()) / len(scores)
    ratio = scores[lo_k] / mean if mean else 0.0         # il più debole rispetto alla media dei sei
    h = 0.0 if hi < MIN_TOP else max(0.0, min(1.0, (ratio - LOW_START) / (1.0 - LOW_START)))
    return {"weakest": lo_k, "strongest": hi_k, "ratio": round(ratio, 3), "harmony": round(h, 3)}


def refresh(conn) -> dict:
    d = compute(conn)
    d["day"] = _day(conn)
    state.set_json(conn, KEY, d)
    return d


def cached(conn) -> dict:
    d = state.get_json(conn, KEY, None)
    if not d or "scores" not in d:
        d = refresh(conn)
    return d


def harmony(conn) -> float:
    return float(cached(conn).get("harmony", 0.0))


def combat_mult(conn) -> float:
    """Moltiplicatore della potenza: lo legge combat.combat_power (dal valore salvato, costa una query)."""
    return 1.0 + HARMONY_ATK * harmony(conn)


def cultivation_mult(conn) -> tuple[float, str]:
    h = harmony(conn)
    return (1.0 + HARMONY_CULT * h, "Armonia dei pilastri") if h > 0 else (1.0, "")


def daily(conn, t, rng, player) -> list[str]:
    """Una volta al giorno: ricalcola. Avvisa solo quando l'armonia sale di un gradino."""
    old = state.get_json(conn, KEY, None) or {}
    new = refresh(conn)
    step = lambda h: int(h * 4)                          # noqa: E731 — quattro gradini: 25%, 50%, 75%, 100%
    if old.get("scores") and step(new["harmony"]) > step(old.get("harmony", 0.0)):
        return [f"☯ I tuoi pilastri si accordano: armonia {int(100 * new['harmony'])}% "
                f"(+{100 * HARMONY_ATK * new['harmony']:.0f}% potenza, +{100 * HARMONY_CULT * new['harmony']:.0f}% coltivazione)."]
    return []


def word(v: int) -> str:
    return ("fragile" if v < 20 else "in crescita" if v < 45 else "saldo" if v < 70
            else "forte" if v < 90 else "compiuto")


# ---------------------------------------------------------------- consigli e menu

def advice(conn) -> tuple[str, str] | None:
    """(testo, comando): la fonte più bassa del pilastro più debole."""
    d = cached(conn)
    k = d["weakest"]
    parts = [p for p in d["parts"].get(k, []) if p[1] < 100]
    if not parts:
        return None
    n, v, c = min(parts, key=lambda p: p[1])
    return (f"Il pilastro più debole è {LABEL[k]} ({d['scores'][k]}/100): alza «{n}» ({v}%).", c)


def summary(conn) -> str:
    d = cached(conn)
    s = " · ".join(f"{LABEL[k]} {d['scores'][k]}" for k in ORDER)
    return f"Pilastri: {s} · armonia {int(100 * d['harmony'])}%"


def sections(conn, player) -> list:
    from engine.systems.menus import act, bar, section
    d = refresh(conn)
    secs = []
    bars = [bar(LABEL[k], d["scores"][k], f"{d['scores'][k]}/100 · {word(d['scores'][k])}",
                tone="warn" if k == d["weakest"] and d["scores"][k] < 70 else ("rare" if k == d["strongest"] else ""))
            for k in ORDER]
    h = d["harmony"]
    lines = [f"Sei pilastri, misurati rispetto a ciò che il tuo {d['tier']}° regno permette. "
             f"Armonia {int(100 * h)}%: +{100 * HARMONY_ATK * h:.0f}% potenza, +{100 * HARMONY_CULT * h:.0f}% coltivazione.",
             ("L'armonia cresce quando il pilastro più debole raggiunge la media dei sei "
              f"(ora {LABEL[d['weakest']]} {d['scores'][d['weakest']]}, media "
              f"{round(sum(d['scores'].values()) / len(ORDER))}).")]
    acts = [act(f"Alza {LABEL[k]}", CMD[k], main=(k == d["weakest"])) for k in ORDER]
    secs.append(section("I sei pilastri", lines, acts, bars, icon="☯"))
    k = d["weakest"]
    detail = [bar(n, v, "") for n, v, _c in d["parts"][k]]
    adv = advice(conn)
    secs.append(section(f"Il pilastro da alzare: {LABEL[k]}", [adv[0]] if adv else ["Questo pilastro è già al massimo per il tuo regno."],
                        [act(n[:40], c) for n, v, c in d["parts"][k] if v < 100][:3], detail, icon="➤"))
    return secs
