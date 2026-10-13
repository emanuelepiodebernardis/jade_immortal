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
  …e i corpi dei grandi racconti: Corpo Santo dell'Era Desolata, Osso Supremo, Doppie Pupille,
  Embrione del Dao Innato, Corpo dei Nove Yang, Corpi Santi della Luna e del Sole, Corpo di Asura,
  Corpo Immortale, Nirvana della Fenice, Anima Innata Celeste. Ognuno ha la sua STORIA e i suoi DONI
  (vedi LORE). Alla nascita e alla rinascita puoi chiedere al Cielo un corpo leggendario a caso.
  Stadi: Sigillato · Primo e Secondo Risveglio · Piccola e Grande Perfezione · Corpo Compiuto · oltre.

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
    # --- i corpi leggendari dei grandi racconti ---
    "santo_antico": ("Corpo Santo dell'Era Desolata", {"atk": 0.12, "taken": 0.12, "state": ("stordimento", 0.12, 1.5),
                                                       "bt": -0.05, "life": 80},
                     "Il Cielo lo teme e lo ha maledetto: finché è sigillato coltivi più piano, e ogni sfondamento è "
                     "una guerra.", 2),
    "osso_supremo": ("Osso Supremo", {"chance_all": 0.08, "crit": 0.06, "cult": 0.15},
                     "Chi scopre l'Osso Supremo vorrà strappartelo dal petto.", 3),
    "doppie_pupille": ("Doppie Pupille", {"crit": 0.10, "evade": 0.06, "spirit_pool": 40, "dao": {"illusione": 1.3}},
                       None, 3),
    "dao_innato": ("Embrione del Dao Innato", {"dao_all": 1.35, "cult": 0.15, "bt": -0.04},
                   "Il Dao ti ama e il Cielo è geloso: le tribolazioni ti colpiscono più forte.", 2),
    "nove_yang": ("Corpo dei Nove Yang", {"cult": 0.25, "state": ("ustione", 0.16, 1.5), "life": 60,
                                          "dao": {"fuoco": 1.3}, "heart": -10},
                  "Il fuoco interiore brucia la calma: il cuore del Dao vacilla più facilmente.", 4),
    "luna": ("Corpo Santo della Luna Grande", {"state": ("gelo", 0.15, 1.4), "spirit_pool": 60,
                                               "dao": {"acqua": 1.25, "oscurita": 1.2}}, None, 3),
    "sole": ("Corpo Santo del Sole Grande", {"state": ("ustione", 0.15, 1.4), "atk": 0.08,
                                             "dao": {"fuoco": 1.25, "luce": 1.2}}, None, 3),
    "asura": ("Corpo di Asura", {"atk": 0.14, "state": ("emorragia", 0.16, 1.5), "dao": {"massacro": 1.4}},
              "Il sangue chiama sangue: la quiete ti è nemica, il cuore del Dao si incrina nella pace.", 4),
    "immortale": ("Corpo Immortale", {"state": ("rigenerazione", 0.20, 1.5), "saves": 1, "life": 200},
                  "Non muori facilmente, ma senti tutto: il dolore non ti risparmia nulla.", 2),
    "fenice_nirvana": ("Corpo del Nirvana della Fenice", {"cult": 0.15, "saves": 1, "state": ("ustione", 0.12, 1.3),
                                                          "life": 100, "blood": "fenice"}, None, 2),
    "anima_celeste": ("Anima Innata Celeste", {"spirit_pool": 80, "soul": 1.4, "dao": {"anima": 1.3}},
                      "Il corpo è debole: l'anima è tutto.", 4),
}

# STORIA e VANTAGGI di ogni corpo (come nei grandi racconti di coltivazione: il Corpo Santo dell'Era
# Desolata, l'Osso Supremo, le Doppie Pupille, l'Embrione del Dao, le Vene Yin, i corpi del Sole e della Luna…)
LORE = {
    "caos": ("Prima del Cielo e della Terra c'era il Caos. Chi nasce con questo corpo porta in sé un frammento di quel "
             "tempo: ogni Qi gli è affine, ogni legge gli scivola dentro. Il Cielo, che è ordine, lo guarda con sospetto.",
             ["coltivazione +30% (risvegliato)", "ogni stato in battaglia più probabile", "nessun Dao gli è estraneo"]),
    "vene_yin": ("Le Nove Vene Yin Assolute: un gelo che nasce dal midollo. Chi le ha coltiva come un vento di "
                 "tempesta, ma il freddo sale al cuore anno dopo anno. Nelle storie solo un Fuoco Yang le scioglie.",
                 ["coltivazione +50%", "colpi di gelo", "guarite, diventano una forza per sempre"]),
    "ossa_spada": ("Nasci con lo scheletro di una spada: le ossa vibrano quando una lama si sguaina vicino a te. "
                   "Il Dao della Spada ti riconosce come un figlio.", ["Dao della Spada ×1,5", "colpi perforanti"]),
    "tuono": ("Una notte di tempesta un fulmine ha cercato la tua culla, e non ti ha ucciso: ti ha scelto. "
              "Il tuono ti scorre nelle vene.", ["stordimento", "pelle temprata dal fulmine", "Dao del Fulmine ×1,3"]),
    "ombra": ("Nato nell'ora senza luna. Le ombre ti obbediscono come cani fedeli, e il tuo colpo beve la vita.",
              ["schivata", "drenaggio", "Dao dell'Oscurità ×1,3"]),
    "giada": ("Un corpo puro come la giada di montagna: nessuna impurità vi attecchisce, e il cuore resta limpido "
              "anche davanti ai demoni interiori.", ["rigenerazione", "cuore del Dao +10", "resiste ai demoni del cuore"]),
    "vuoto": ("Il tuo cuore è vuoto come il cielo d'inverno: ogni Dao vi entra senza attrito. Ma il corpo, "
              "trascurato dal destino, è fragile.", ["ogni Dao ×1,25"]),
    "drago": ("Il sangue di un Drago Vero, diluito in mille generazioni, si è risvegliato in te. Le tue ossa sono "
              "ferro, le tue vene un fiume.", ["corpo possente", "attacco +6%", "il sangue di drago si concentra"]),
    "occhi": ("Occhi che vedono il filo dei colpi prima che partano, e la forza vera di chi ti sta davanti.",
              ["critici +8%", "leggi la forza degli altri"]),
    "veleno": ("Sopravvissuto da bambino a cento veleni: ora il veleno ti scorre dentro, docile, e colpisce chi ti tocca.",
               ["immune alle tossine delle pillole", "veleno nei colpi"]),
    "spezzati": ("«Spazzatura», dicevano. Meridiani spezzati, Qi che si disperde. Ma le storie amano proprio questi: "
                 "quando si saldano, diventano fiumi.", ["al risveglio: coltivazione raddoppiata", "ogni stadio vale di più"]),
    "santo_antico": ("Il Corpo Santo dell'Era Desolata: il corpo che nelle ere antiche sfidò il Cielo. Il Cielo lo "
                     "maledisse e da allora chi lo porta coltiva a fatica — ma ogni regno conquistato vale dieci regni "
                     "degli altri, e a mani nude spacca le montagne.",
                     ["attacco +12%, danni subiti −12%", "colpi che stordiscono", "vita +80 anni",
                      "sigillato coltivi più piano: risvegliato, il freno sparisce"]),
    "osso_supremo": ("Un osso che brilla di rune nel petto, dono dell'Antenato: tutto ciò che fai ti riesce un poco "
                     "meglio. È anche il tesoro che i potenti sognano di strappare.",
                     ["ogni stato più probabile", "critici +6%", "coltivazione +15%"]),
    "doppie_pupille": ("Due pupille in ogni occhio: vedi attraverso le illusioni, leggi i movimenti prima che "
                       "nascano. Nelle leggende chi le ha non perde mai di vista il proprio nemico.",
                       ["critici +10%", "schivata +6%", "riserva di spirito +40", "Dao dell'Illusione ×1,3"]),
    "dao_innato": ("Un embrione del Dao concepito con te: comprendi le leggi come gli altri respirano. Il Cielo, "
                   "geloso, raddoppia la severità delle tue tribolazioni.",
                   ["ogni Dao ×1,35", "coltivazione +15%"]),
    "nove_yang": ("Il sole ti è nato dentro: nove fiamme Yang ardono nei tuoi meridiani. Vivi più a lungo, coltivi "
                  "più in fretta, bruci chi ti tocca — ma la calma ti sfugge.",
                  ["coltivazione +25%", "ustioni", "vita +60 anni", "Dao del Fuoco ×1,3"]),
    "luna": ("Il Corpo Santo della Luna Grande (Taiyin): freddo, silenzioso, profondo. Lo spirito vi si raccoglie "
             "come la marea sotto la luna.", ["gelo", "riserva di spirito +60", "Acqua ×1,25, Oscurità ×1,2"]),
    "sole": ("Il Corpo Santo del Sole Grande (Taiyang): il fratello di fuoco della Luna. Ogni colpo è un'alba che "
             "brucia.", ["ustioni", "attacco +8%", "Fuoco ×1,25, Luce ×1,2"]),
    "asura": ("Nato su un campo di battaglia, tra i morti. Il corpo di Asura si nutre di lotta: più combatti, più "
              "diventi forte; nella pace, invece, ti consumi.", ["attacco +14%", "emorragie", "Dao del Massacro ×1,4"]),
    "immortale": ("Un corpo che si rifiuta di morire: le ferite si chiudono, le ossa si saldano, e una volta — una "
                  "sola, per ogni risveglio — torni in piedi dalla morte.",
                  ["rigenerazione", "si rialza una volta dalla morte (risvegliato)", "vita +200 anni"]),
    "fenice_nirvana": ("Il Nirvana della Fenice: muori nel fuoco e rinasci più forte. Il sangue della fenice ti "
                       "chiama dalle ceneri.", ["si rialza una volta dalla morte (risvegliato)", "coltivazione +15%",
                                                 "ustioni", "vita +100 anni", "sangue di fenice"]),
    "anima_celeste": ("Un'anima discesa dal cielo in un corpo mortale: lo spirito è vasto come un mare, il corpo "
                      "esile come un giunco.", ["riserva di spirito +80", "tempra dello spirito ×1,4",
                                               "Dao dell'Anima ×1,3"]),
}

STAGE_NAMES = ["Sigillato", "Primo Risveglio", "Secondo Risveglio", "Piccola Perfezione", "Grande Perfezione",
               "Corpo Compiuto"]


def stage_name(st: int) -> str:
    if st < len(STAGE_NAMES):
        return STAGE_NAMES[st]
    return f"Oltre il Compimento ({st - len(STAGE_NAMES) + 1}°)"


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def stage(conn) -> int:
    c = get(conn)
    return int(c.get("stage", 0)) if c else 0


def _mult(conn) -> float:
    return 1.0 + 0.25 * stage(conn)


def grant(conn, key: str) -> str:
    state.set_json(conn, KEY, {"key": key, "stage": 0, "cured": False})
    nm, g, curse, _w = BODIES[key]
    msg = f"✦ Nasci con un corpo leggendario: {nm} (sigillato)."
    if key in LORE:
        msg += "\n  " + LORE[key][0]
        msg += "\n  Doni: " + "; ".join(LORE[key][1]) + "."
    if curse:
        msg += f"\n  Maledizione: {curse}"
    msg += "\n  Si risveglia a stadi: a ogni nuovo regno, vincendo sull'orlo della morte, nelle illuminazioni. ('corpo')"
    if g.get("life"):
        from engine.systems import lifespan
        lifespan.add_bonus_years(conn, int(g["life"]))
    if g.get("blood"):
        try:
            from engine.systems import bloodlines
            sp = {"drago": ("Drago delle Nubi", ["fulmine", "acqua"]), "fenice": ("Fenice", ["fuoco"])}.get(g["blood"])
            if sp:
                bloodlines.grant_heritage(conn, sp[0], sp[1], 12)
        except Exception:
            pass
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
    nm, g, _cu, _w = BODIES[c["key"]]
    out = [f"✦ RISVEGLIO ({reason}): il tuo {nm} si apre ancora — {stage_name(c['stage'])} (stadio {c['stage']}). ✦"]
    if g.get("life"):
        from engine.systems import lifespan
        lifespan.add_bonus_years(conn, int(g["life"]) // 4)
    if g.get("saves") and c["stage"] == 1:
        out.append("  Ora il tuo corpo può tornare dalla morte una volta per ogni scontro mortale.")
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
    if c["key"] == "santo_antico" and st == 0:
        return 0.8, "Corpo Santo maledetto dal Cielo"
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
    if c["key"] == "anima_celeste":
        pr["taken"] = pr.get("taken", 0.0) - 0.06          # il corpo è un giunco
    if g.get("saves") and int(c.get("stage", 0)) >= 1:
        fx.p.lethal_saves += int(g["saves"])
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


def spirit_pool(conn) -> int:
    c = get(conn)
    if not c:
        return 0
    return int(_gifts(conn).get("spirit_pool", 0) * (0.3 if int(c.get("stage", 0)) == 0 else _mult(conn)))


def soul_mult(conn) -> float:
    return float(_gifts(conn).get("soul", 1.0)) if get(conn) else 1.0


def describe_full(conn) -> str:
    c = get(conn)
    if not c:
        return ("Non porti un corpo leggendario. Si nasce con uno raramente (i geni più spesso, il destino «Corpo "
                "Divino» lo garantisce), oppure scegliendo, alla nascita o alla rinascita, di affidarti al Cielo.")
    nm, _g, curse, _w = BODIES[c["key"]]
    st = int(c.get("stage", 0))
    lines = [f"✦ {nm} — {stage_name(st)}" + (f" (stadio {st}, doni ×{_mult(conn):.2f})" if st else
                                             " (un'eco dei suoi poteri: si risveglia a stadi)")]
    if c["key"] in LORE:
        lines.append("  " + LORE[c["key"]][0])
        lines.append("  Doni: " + "; ".join(LORE[c["key"]][1]) + ".")
    if curse and not c.get("cured"):
        lines.append(f"  Maledizione: {curse}")
    elif c.get("cured"):
        lines.append("  La maledizione è spezzata.")
    lines.append("  Risvegli: a ogni nuovo regno (45%), vincendo sull'orlo della morte (25%), nelle illuminazioni (15%). "
                 "Ogni stadio rafforza i doni del 25%, senza fine.")
    return "\n".join(lines)


def describe_line(conn) -> str | None:
    c = get(conn)
    if not c:
        return None
    nm, _g, curse, _w = BODIES[c["key"]]
    st = int(c.get("stage", 0))
    s = f"Corpo leggendario: {nm} — " + ("sigillato (un'eco dei suoi poteri)" if st == 0 else f"{stage_name(st)}, stadio {st}")
    if curse and not c.get("cured"):
        s += f". Maledizione: {curse}"
    elif c.get("cured"):
        s += ". La maledizione è spezzata."
    return s
