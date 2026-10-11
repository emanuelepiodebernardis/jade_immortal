"""
COSTITUZIONI SPECIALI (体质) — i corpi divini con cui pochi nascono.

Alla nascita, raramente, il Cielo ti dà un corpo fuori dal comune (il destino «Corpo
Divino» lo garantisce; i geni ne hanno uno più spesso). Nasce SIGILLATO: i suoi poteri
sono solo un'eco. Si RISVEGLIA a stadi, senza fine: a ogni nuovo regno, vincendo
sull'orlo della morte, nelle illuminazioni. Ogni stadio rafforza i doni del 25%.

Ogni corpo ha DONI e spesso una MALEDIZIONE:
  Corpo del Caos Primordiale   coltivazione e stati di ogni tipo · il Cielo lo odia (sfondamenti più duri)
  Vene Yin Estreme             coltivazione rapidissima, gelo · senza cura MUORI A 20 ANNI:
                               serve un Fuoco Yang (radice o lignaggio di fuoco, Dao del Fuoco,
                               o una compagna del Dao) per guarirle
  Ossa di Spada Innate         Dao della Spada ×1,5, colpi perforanti · gli altri Dao d'arma rallentano
  Corpo del Tuono Celeste      stordimento, resistenza · le tribolazioni ti cercano
  Corpo dell'Ombra Celeste     schivata e drenaggio · la luce ti brucia (i nemici di luce colpiscono di più)
  Corpo di Giada Puro          resiste al demone interiore, rigenera · l'assorbimento lo avvelena
  Cuore del Vuoto              comprende ogni Dao in fretta · corpo fragile
  Corpo del Drago Vero         corpo possente, il sangue di drago si concentra il doppio
  Occhi del Cielo              critici, vedi la forza vera degli altri
  Corpo dei Cento Veleni       immune alle tossine delle pillole, avvelena chi colpisce · la gente ti teme
  Meridiani Spezzati           lo «spazzatura» delle storie: coltivi a metà… finché non si
                               risvegliano: allora raddoppi, e ogni stadio vale di più

  corpo        la tua costituzione, il tuo cuore del Dao e le tossine (tutto in un pannello)
"""

from __future__ import annotations

import random

from engine.systems import state

KEY = "constitution"

# chiave: nome, doni (dict), maledizione (testo o None), peso estrazione
BODIES = {
    "caos": ("Corpo del Caos Primordiale", {"cult": 0.30, "chance_all": 0.06, "bt": -0.06},
             "Il Cielo odia il Caos: ogni sfondamento è più difficile.", 2),
    "vene_yin": ("Vene Yin Estreme", {"cult": 0.50, "state": ("gelo", 0.18, 1.6)},
                 "Senza un Fuoco Yang che le guarisca, non vivrai oltre i vent'anni.", 4),
    "ossa_spada": ("Ossa di Spada Innate", {"dao": {"spada": 1.5}, "pierce": 0.10, "dao_other_weapon": 0.85},
                   "Le altre armi ti sono estranee: i loro Dao crescono più piano.", 5),
    "tuono": ("Corpo del Tuono Celeste", {"state": ("stordimento", 0.14, 1.4), "taken": 0.05, "dao": {"fulmine": 1.3},
                                          "bt": -0.03},
              "Il Cielo ti riconosce da lontano: ogni sfondamento è una prova più dura.", 4),
    "ombra": ("Corpo dell'Ombra Celeste", {"evade": 0.08, "state": ("drenaggio", 0.15, 1.3), "dao": {"oscurita": 1.3}},
              "La luce ti brucia: i coltivatori della Luce ti feriscono di più.", 4),
    "giada": ("Corpo di Giada Puro", {"state": ("rigenerazione", 0.15, 1.3), "heart": 10},
              "L'assorbimento lo avvelena: divorare i caduti incrina il tuo cuore.", 5),
    "vuoto": ("Cuore del Vuoto", {"dao_all": 1.25},
              "Il corpo è fragile: subisci più danni.", 5),
    "drago": ("Corpo del Drago Vero", {"taken": 0.08, "atk": 0.06, "blood": "drago"}, None, 3),
    "occhi": ("Occhi del Cielo", {"crit": 0.08}, None, 5),
    "veleno": ("Corpo dei Cento Veleni", {"state": ("veleno", 0.16, 1.4), "toxin_immune": True},
               "La gente ti teme: è più difficile farsi amici.", 4),
    "spezzati": ("Meridiani Spezzati", {"cult": -0.5}, "Coltivi a metà della velocità… per ora.", 5),
}


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def stage(conn) -> int:
    c = get(conn)
    return int(c.get("stage", 0)) if c else 0


def _mult(conn) -> float:
    return 1.0 + 0.25 * stage(conn)


def grant(conn, key: str) -> str:
    state.set_json(conn, KEY, {"key": key, "stage": 0, "cured": False})
    nm = BODIES[key][0]
    curse = BODIES[key][2]
    msg = f"✦ Nasci con una costituzione rara: {nm} (sigillata)."
    if curse:
        msg += f" {curse}"
    return msg


def roll_at_birth(conn, rng: random.Random, origin_key: str, forced: bool = False) -> list[str]:
    from engine.systems import character
    p = character.get_profile(conn, "player", 1)
    flags = {}
    try:
        import json
        flags = json.loads(p["flags"]) if p and p["flags"] else {}
    except Exception:
        pass
    chance = 0.10 + (0.25 if origin_key == "genio" else 0.0)
    if not (forced or flags.get("divine_body") or rng.random() < chance):
        state.delete(conn, KEY)
        return []
    keys = list(BODIES)
    return [grant(conn, rng.choices(keys, weights=[BODIES[k][3] for k in keys])[0])]


def awaken(conn, reason: str) -> list[str]:
    c = get(conn)
    if not c:
        return []
    c["stage"] = int(c.get("stage", 0)) + 1
    state.set_json(conn, KEY, c)
    nm = BODIES[c["key"]][0]
    out = [f"✦ RISVEGLIO ({reason}): il tuo {nm} si apre ancora — stadio {c['stage']}. ✦"]
    if c["key"] == "spezzati" and c["stage"] == 1:
        out.append("  I meridiani spezzati si saldano in vie larghe come fiumi: chi rideva di te smetterà.")
    if c["stage"] in (1, 5, 10):
        state.grant_title(conn, {1: "Corpo Risvegliato", 5: "Corpo Divino", 10: "Corpo del Cielo e della Terra"}[c["stage"]])
    return out


def on_realm_up(conn, rng: random.Random) -> list[str]:
    if get(conn) and rng.random() < 0.45:
        return awaken(conn, "nuovo regno")
    return []


def on_near_death_win(conn, rng: random.Random) -> list[str]:
    if get(conn) and rng.random() < 0.25:
        return awaken(conn, "sull'orlo della morte")
    return []


def on_illumination(conn, rng: random.Random) -> list[str]:
    if get(conn) and rng.random() < 0.15:
        return awaken(conn, "illuminazione")
    return []


# ---------- effetti ----------

def _gifts(conn) -> dict:
    c = get(conn)
    return BODIES[c["key"]][1] if c else {}


def cultivation_mult(conn) -> tuple[float, str]:
    c = get(conn)
    if not c:
        return 1.0, ""
    g = _gifts(conn)
    st = int(c.get("stage", 0))
    if c["key"] == "spezzati":
        return (0.5, "meridiani spezzati") if st == 0 else (1.0 + 1.0 * (1 + 0.25 * (st - 1)), "meridiani rinati")
    cult = g.get("cult", 0.0)
    if not cult:
        return 1.0, ""
    m = 1.0 + cult * (0.3 if st == 0 else 1.0) * _mult(conn)
    return m, BODIES[c["key"]][0]


def dao_mult(conn, dao_key: str) -> float:
    from engine.systems import weapons
    c = get(conn)
    if not c:
        return 1.0
    g = _gifts(conn)
    eff = 0.3 if int(c.get("stage", 0)) == 0 else 1.0
    m = 1.0
    if dao_key in g.get("dao", {}):
        m *= 1.0 + (g["dao"][dao_key] - 1.0) * eff * _mult(conn)
    if g.get("dao_all"):
        m *= 1.0 + (g["dao_all"] - 1.0) * eff * _mult(conn)
    if g.get("dao_other_weapon") and dao_key in {v[0] for v in weapons.WEAPONS.values()} and dao_key != "spada":
        m *= g["dao_other_weapon"]
    return m


def bt_bonus(conn) -> float:
    return _gifts(conn).get("bt", 0.0)


def toxin_immune(conn) -> bool:
    return bool(_gifts(conn).get("toxin_immune"))


def heart_bonus(conn) -> int:
    return int(_gifts(conn).get("heart", 0))


def lifespan_cap(conn) -> int | None:
    c = get(conn)
    if c and c["key"] == "vene_yin" and not c.get("cured"):
        return 20
    return None


def combat(conn, fx) -> list[str]:
    c = get(conn)
    if not c:
        return []
    g = _gifts(conn)
    eff = (0.3 if int(c.get("stage", 0)) == 0 else 1.0) * _mult(conn)
    pr = fx.p.prof
    if g.get("state"):
        st, ch, pw = g["state"]
        fx.add_proc("p", st, min(0.5, ch * eff), pw * (0.8 + 0.2 * eff), f"corpo:{c['key']}")
    if g.get("chance_all"):
        pr["chance_mult"] = pr.get("chance_mult", 1.0) * (1.0 + g["chance_all"] * eff)
    for k in ("pierce", "crit", "evade"):
        if g.get(k):
            pr[k] = pr.get(k, 0.0) + g[k] * eff
    if g.get("taken"):
        pr["taken"] = pr.get("taken", 0.0) + g["taken"] * eff
    if g.get("atk"):
        fx.p.atk_mult *= 1.0 + g["atk"] * eff
    if c["key"] == "vuoto":
        pr["taken"] = pr.get("taken", 0.0) - 0.08          # fragile
    return [f"Il tuo {BODIES[c['key']][0]} si desta."] if int(c.get("stage", 0)) > 0 else []


def daily(conn, t: int, rng, player) -> list[str]:
    """Le Vene Yin si curano con un Fuoco Yang; i corpi crescono con i giorni (raramente)."""
    c = get(conn)
    if not c:
        return []
    out = []
    if c["key"] == "vene_yin" and not c.get("cured"):
        if _has_yang(conn, player.id):
            c["cured"] = True
            state.set_json(conn, KEY, c)
            out.append("✦ Un Fuoco Yang incontra le tue Vene Yin: il gelo mortale si scioglie. Sei GUARITO, "
                       "e il loro potere è tuo per sempre.")
            out += awaken(conn, "cura delle Vene Yin")
        else:
            from engine.systems import lifespan
            left = 20 - lifespan.age_years(conn, player.id)
            if 0 < left < 2 and not state.flag(conn, "yin_warned", False):
                state.set(conn, "yin_warned", "1")
                out.append("⚠ Il gelo delle Vene Yin ti sale al cuore: ti resta meno di due anni. Cerca un Fuoco "
                           "Yang (radice o lignaggio di fuoco, Dao del Fuoco a 50, una compagna del Dao).")
    return out


def _has_yang(conn, pid: int) -> bool:
    from engine.systems import bloodlines, bonds
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key='fuoco';", (pid,)).fetchone()
    if r and (r["comprehension"] or 0) >= 50:
        return True
    if any("fuoco" in ln["elements"] and ln["conc"] >= 30 for ln in bloodlines.all_lines(conn).values()):
        return True
    try:
        from engine.systems import spirit_roots
        if spirit_roots.get(conn, "player", pid).get("fuoco", 0) >= 60:
            return True
    except Exception:
        pass
    return bonds.dao_partner(conn, pid) is not None


def describe_line(conn) -> str | None:
    c = get(conn)
    if not c:
        return None
    nm, _g, curse, _w = BODIES[c["key"]]
    st = int(c.get("stage", 0))
    s = f"Costituzione: {nm} — " + ("sigillata (un'eco dei suoi poteri)" if st == 0 else f"risvegliata, stadio {st}")
    if curse and not c.get("cured"):
        s += f". Maledizione: {curse}"
    elif c.get("cured"):
        s += ". La maledizione è spezzata."
    return s
