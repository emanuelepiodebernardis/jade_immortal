"""
ALTRI VASI D'ANIMA (Aggiornamento 61) — oggetti con un'anima dentro, oltre all'anello.

Si trovano una volta per vita, esplorando i luoghi giusti. Ognuno cresce in un modo suo, dà doni
suoi, e ha la sua storia in tre capitoli (soul_arcs.py, trame in intrigue_data3.py).

  PAGODA DELLE NOVE PRIGIONI   uno spirito d'artefatto (器灵) che ha dimenticato tutto
      cresce: nutri i piani con pietre spirituali ('pagoda nutri')
      dona:   coltivazione (la stanza del tempo) e, in battaglia, i nemici sono più deboli
      storia: il prigioniero del terzo piano · i padroni di un tempo · il nome della pagoda

  STENDARDO DELLE DIECIMILA ANIME   la via demoniaca: beve l'anima di chi uccidi
      cresce: da solo, a ogni coltivatore che abbatti (e il karma scende)
      dona:   forza in battaglia; 'stendardo scatena' libera le anime nel prossimo scontro
      storia: la bambina tra le anime · i giusti ti cercano · la rivolta delle anime

  CALDERONE DELLA FIAMMA DORMIENTE   una fiamma viva e affamata
      cresce: mangia erbe spirituali ('calderone nutri')
      dona:   arti più riuscite, tossine bruciate ogni giorno
      storia: la fiamma strana · l'alchimista che lo forgiò · la fiamma celeste

  PERLA DEI NOVE SIGILLI   un demone sigillato, gentile finché gli servi
      cresce: a ogni PATTO ('perla patto forza|vita|segreto'): un sigillo si scioglie
      dona:   ciò che chiedi, a un prezzo (anni di vita, karma, cuore)
      storia: la voce gentile · il prezzo dei patti · la notte in cui la perla si aprì

  vasi                       tutti i tuoi vasi d'anima
  pagoda | stendardo | calderone | perla [azione]
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

ORDER = ("pagoda", "stendardo", "calderone", "perla")
V = {
    "pagoda": {"name": "Pagoda delle Nove Prigioni", "icon": "🏯", "max": 9,
               "spirits": ["Xiao Ling", "Yue'er", "Lan Lan", "A-Qing"],
               "where": ("ruin", "mountain"), "tier_min": 1,
               "find": ("Tra le macerie, una pagoda di bronzo alta un palmo. Nove piani, nove porte chiuse. "
                        "Quando la sollevi, una vocina dice: «Finalmente. Avevo tanta paura del buio.»")},
    "stendardo": {"name": "Stendardo delle Diecimila Anime", "icon": "🏴", "max": 12,
                  "spirits": ["le anime dello stendardo"],
                  "where": ("forbidden_zone", "ruin"), "tier_min": 2,
                  "find": ("Infilzato in un cumulo di ossa, uno stendardo nero che si muove senza vento. Dalla "
                           "stoffa escono voci: «Prendici. Ti daremo la forza di tutti quelli che uccidi.»")},
    "calderone": {"name": "Calderone della Fiamma Dormiente", "icon": "🔥", "max": 9,
                  "spirits": ["Huo'er", "la Piccola Fiamma", "Zhu Yan"],
                  "where": ("mountain", "ruin", "city"), "tier_min": 1,
                  "find": ("Un calderone a tre piedi, coperto di cenere, in un angolo dimenticato. Quando lo tocchi "
                           "una fiammella si accende sul fondo e ti annusa le dita: «Hai erbe? Ho tanta fame.»")},
    "perla": {"name": "Perla dei Nove Sigilli", "icon": "🔮", "max": 9,
              "spirits": ["il Signore della Perla", "Mo Yan della Città Divorata", "la Dama della Marea Nera"],
              "where": ("forbidden_zone",), "tier_min": 2,
              "find": ("Una perla nera grande come un occhio, avvolta in nove giri di talismani sbiaditi. Una voce "
                       "gentilissima: «Che mani calde. Portami con te, e ti racconterò tutti i segreti del mondo.»")},
}
STONES_PER_LEVEL = 200          # pagoda: pietre × livello × regno
HERBS_BASE, HERBS_STEP = 5, 4   # calderone: erbe per livello
BANNER_STEPS = (3, 8, 15, 25, 40, 60, 85, 115, 150, 190, 240, 300)
PACT_GAP = 3                    # giorni tra un patto e l'altro
FIND_CHANCE = 0.02              # a ogni arrivo in un luogo adatto
FIND_GAP = 30                   # giorni minimi tra il ritrovamento di un vaso e il successivo


def _key(k: str) -> str:
    return "vaso_" + k


def get(conn, k: str) -> dict | None:
    return state.get_json(conn, _key(k), None)


def _save(conn, k: str, d: dict) -> None:
    state.set_json(conn, _key(k), d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _tier(conn, pid: int) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def owned(conn) -> list[str]:
    return [k for k in ORDER if (get(conn, k) or {}).get("active")]


def level(conn, k: str) -> int:
    d = get(conn, k)
    return int(d.get("level", 0)) if d and d.get("active") else 0


# ---------------------------------------------------------------- trovarli

def offer_scene(conn, rng, player) -> str | None:
    """Arrivando in un luogo adatto, a volte: uno dei vasi (ognuno una volta per vita)."""
    from engine.systems import encounters
    if encounters.pending(conn) or _day(conn) < 3:
        return None
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    lt = lt["location_type"] if lt else ""
    tier = _tier(conn, player.id)
    if _day(conn) - state.get_int(conn, "vaso_ultimo", -999) < FIND_GAP:
        return None                                     # un vaso nuovo è un evento: non più di uno al mese
    for k in ORDER:
        v = V[k]
        if get(conn, k) or state.flag(conn, "vaso_visto_" + k, False) or lt not in v["where"] or tier < v["tier_min"]:
            continue
        if rng.random() > FIND_CHANCE:
            continue
        state.set(conn, "vaso_visto_" + k, "1")
        state.set(conn, "vaso_ultimo", str(_day(conn)))
        sc = {"key": "vaso_" + k, "title": v["name"], "event_type": "fortune", "text": v["find"],
              "choices": [{"label": "Lo prendi con te", "effects": {"vaso": {"take": k}}},
                          {"label": "Lo lasci dov'è", "effects": {"text": "Te ne vai. Qualcosa, dietro di te, sospira."}}]}
        return encounters.start_scene(conn, player, sc)
    return None


def acquire(conn, player, k: str, rng: random.Random | None = None) -> list[str]:
    if k not in V or (get(conn, k) or {}).get("active"):
        return []
    rng = rng or random.Random(tick_mod.get_tick(conn) + len(k))
    sp = rng.choice(V[k]["spirits"])
    _save(conn, k, {"active": True, "level": 1, "fed": 0, "spirit": sp, "souls": 0, "flags": [], "atk": 0.0,
                    "since": _day(conn)})
    state.grant_title(conn, f"Portatore di {V[k]['name'].split(' ')[0]}")
    hint = {"pagoda": "'pagoda nutri' con pietre spirituali", "stendardo": "cresce da solo con chi abbatti",
            "calderone": "'calderone nutri' con erbe spirituali", "perla": "'perla patto forza|vita|segreto'"}[k]
    return [f"{V[k]['icon']} Ora porti con te: {V[k]['name']}. Dentro vive {sp}. ({hint}; 'vasi' per vederli tutti)"]


def on_effect(conn, t: int, rng, player, data: dict) -> list[str]:
    if data.get("take"):
        return acquire(conn, player, data["take"], rng)
    return []


# ---------------------------------------------------------------- farli crescere

def feed_need(conn, k: str, lv: int, pid: int = 1) -> int:
    if k == "pagoda":
        return STONES_PER_LEVEL * lv * _tier(conn, pid)
    if k == "calderone":
        return HERBS_BASE + HERBS_STEP * lv
    return 0


def _level_up(conn, k: str, d: dict, out: list[str]) -> None:
    while d["level"] < V[k]["max"] and d["fed"] >= feed_need(conn, k, d["level"]):
        d["fed"] -= feed_need(conn, k, d["level"])
        d["level"] += 1
        out.append(f"✦ {V[k]['name']}: livello {d['level']}." + (f" Si apre il {d['level']}° piano." if k == "pagoda" else ""))


def feed(conn, player, k: str, arg: str) -> str:
    from engine.systems import sects, professions
    d = get(conn, k)
    if not d or not d.get("active"):
        return f"Non porti {V[k]['name']}."
    if d["level"] >= V[k]["max"]:
        return f"{V[k]['name']} è al massimo ({d['level']})."
    need = feed_need(conn, k, d["level"], player.id) - d["fed"]
    if k == "pagoda":
        have = sects.get_resource(conn, "pietre_spirituali", player.id)
        n = min(int(arg) if arg.strip().isdigit() else need, have)
        if n <= 0:
            return f"La pagoda vuole pietre spirituali: {need} per il prossimo piano."
        sects.grant_resource(conn, "pietre_spirituali", -n, player.id)
        out = [f"{d['spirit']} beve il Qi di {n} pietre spirituali."]
    elif k == "calderone":
        have = professions.material(conn, player.id, "erbe")
        n = min(int(arg) if arg.strip().isdigit() else need, have)
        if n <= 0:
            return f"«Erbe! Erbe spirituali!» ({need} per crescere; 'gather' in montagna o nelle zone proibite)"
        professions.spend(conn, player.id, {"erbe": n})
        out = [f"{d['spirit']} divora {n} erbe spirituali e scoppietta di gioia."]
    else:
        return {"stendardo": "Lo stendardo non si nutre a mano: beve le anime di chi abbatti.",
                "perla": "La perla non vuole cibo. Vuole patti. ('perla patto forza|vita|segreto')"}[k]
    d["fed"] += n
    _level_up(conn, k, d, out)
    _save(conn, k, d)
    return "\n".join(out)


def care(conn, player) -> list[str]:
    """La cura quotidiana ('tesori cura'): la pagoda solo se le pietre avanzano, il calderone con le erbe."""
    from engine.systems import sects, professions
    out = []
    d = get(conn, "pagoda")
    if d and d.get("active") and d["level"] < V["pagoda"]["max"]:
        need = feed_need(conn, "pagoda", d["level"], player.id) - d["fed"]
        if sects.get_resource(conn, "pietre_spirituali", player.id) >= 3 * need:
            out.append(feed(conn, player, "pagoda", str(need)))
    d = get(conn, "calderone")
    if d and d.get("active") and d["level"] < V["calderone"]["max"]:
        need = feed_need(conn, "calderone", d["level"], player.id) - d["fed"]
        if professions.material(conn, player.id, "erbe") > 0:
            out.append(feed(conn, player, "calderone", str(need)))
    return out


def on_kill(conn, t: int, rng, player, npc_id: int) -> list[str]:
    """Lo stendardo beve l'anima di chi cade (solo coltivatori: le bestie non hanno anime da tenere)."""
    d = get(conn, "stendardo")
    if not d or not d.get("active"):
        return []
    r = conn.execute("SELECT name, kind, archetype FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not r or r["kind"] not in (None, "human"):
        return []
    from engine.simulation import cultivation
    nt = cultivation.realm_tier(conn, "npc", npc_id) or 1
    gain = 3 if nt >= _tier(conn, player.id) or r["archetype"] == "anziano" else 1
    d["souls"] = d.get("souls", 0) + gain
    old = d["level"]
    d["level"] = min(V["stendardo"]["max"], 1 + sum(1 for s in BANNER_STEPS if d["souls"] >= s))
    _save(conn, "stendardo", d)
    from engine.systems import karma
    karma.adjust_karma(conn, "player", player.id, -gain, "lo stendardo beve un'anima", t)
    out = [f"🏴 Lo stendardo beve l'anima di {r['name']} ({d['souls']} anime)."]
    if d["level"] > old:
        out.append(f"✦ Lo Stendardo delle Diecimila Anime cresce: livello {d['level']}.")
    return out


def pact(conn, player, arg: str) -> str:
    """La perla: un patto, un sigillo che si scioglie, un dono e un prezzo."""
    from engine.systems import encounters, items, dao_training
    d = get(conn, "perla")
    if not d or not d.get("active"):
        return "Non porti la Perla dei Nove Sigilli."
    if "sigillata" in d["flags"]:
        return "La perla è sigillata per sempre: nessun patto."
    if d["level"] >= 9:
        return "Non restano sigilli da sciogliere."
    if _day(conn) - d.get("pact_day", -99) < PACT_GAP:
        return f"{d['spirit']}: «Così presto? Non essere avido, caro.» (un patto ogni {PACT_GAP} giorni)"
    what = (arg or "").strip().lower()
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 5 + player.id)
    if what.startswith("forz"):
        d["atk"] = round(min(0.6, d.get("atk", 0.0) + 0.06), 3)
        lines = [f"Ti scorre nelle braccia una forza che non è tua: attacco +{d['atk'] * 100:.0f}% per sempre."]
        lines += encounters.apply_effects(conn, t, rng, player, {"lifespan_years": -15}, {})
    elif what.startswith("vit"):
        lines = ["Le ferite si chiudono, il Qi torna pieno."]
        conn.execute("UPDATE injuries SET healed=1, heal_tick=? WHERE character_type='player' AND character_id=? "
                     "AND healed=0;", (t, player.id))
        lines += encounters.apply_effects(conn, t, rng, player, {"qi_full": True, "karma": -8}, {})
    elif what.startswith("seg"):
        rows = dao_training.trainable_daos(conn, player.id)
        dk = min(rows, key=lambda r: r["comprehension"])["dao_key"] if rows else "anima"
        lines = [f"{d['spirit']} ti sussurra un segreto del Dao."]
        lines += items.apply_effects(conn, t, rng, player.id, {"dao_key": dk, "dao_gain": 6 + 2 * d["level"]})
        lines += encounters.apply_effects(conn, t, rng, player, {"heart": -6}, {})
    else:
        return (f"{d['spirit']}: «Cosa desideri, caro?»\n  perla patto forza    attacco per sempre (costa 15 anni di vita)\n"
                "  perla patto vita     guarigione e Qi pieno (costa karma)\n"
                "  perla patto segreto  un passo nel tuo Dao più debole (costa serenità del cuore)")
    d["pact_day"] = _day(conn)
    d["level"] += 1
    _save(conn, "perla", d)
    lines.append(f"🔮 Un sigillo si scioglie: ne restano {9 - d['level']}. La voce è un po' meno gentile.")
    return "\n".join(lines)


def unleash(conn, player) -> str:
    d = get(conn, "stendardo")
    if not d or not d.get("active"):
        return "Non porti lo stendardo."
    if d.get("souls", 0) < 5:
        return "Lo stendardo ha troppe poche anime da scatenare."
    state.set(conn, "stendardo_scatena", "1")
    return "Pianti lo stendardo: nel prossimo scontro le anime si scaglieranno sul nemico (ne perderai un decimo)."


# ---------------------------------------------------------------- doni

def cultivation_mult(conn) -> tuple[float, str]:
    m, parts = 1.0, []
    pl = level(conn, "pagoda")
    if pl:
        m *= 1.0 + 0.03 * pl * (1.5 if "legata" in get(conn, "pagoda")["flags"] else 1.0)
        parts.append("la stanza del tempo della pagoda")
    cl = level(conn, "calderone")
    if cl:
        m *= 1.0 + 0.01 * cl
        parts.append("il calderone")
    return m, ", ".join(parts)


def craft_bonus(conn) -> float:
    cl = level(conn, "calderone")
    if not cl:
        return 0.0
    d = get(conn, "calderone")
    return 0.03 * cl * (2.0 if "celeste" in d["flags"] else 1.0)


def combat(conn, fx) -> list[str]:
    out = []
    pl = level(conn, "pagoda")
    if pl:
        cut = min(0.3, 0.025 * pl * (1.5 if "legata" in get(conn, "pagoda")["flags"] else 1.0))
        fx.e.atk_mult *= 1.0 - cut
    sd = get(conn, "stendardo")
    if sd and sd.get("active"):
        lv = sd["level"]
        fx.p.atk_mult *= 1.0 + min(0.6, 0.04 * lv) * (1.5 if "re" in sd["flags"] else 1.0)
        if state.get(conn, "stendardo_scatena"):
            state.delete(conn, "stendardo_scatena")
            fx.p.atk_mult *= 1.0 + 0.05 * lv
            fx.e.atk_mult *= 0.9
            lost = max(1, sd["souls"] // 10)
            sd["souls"] -= lost
            _save(conn, "stendardo", sd)
            out.append(f"🏴 Le anime dello stendardo urlano e si scagliano sul nemico ({lost} si disperdono).")
    pd = get(conn, "perla")
    if pd and pd.get("active") and pd.get("atk"):
        fx.p.atk_mult *= 1.0 + pd["atk"] * (1.5 if "simbiosi" in pd["flags"] else 1.0)
    return out


def daily(conn, t: int, rng, player) -> list[str]:
    cl = level(conn, "calderone")
    if cl and player is not None:
        from engine.systems import dao_heart
        v = dao_heart.toxin(conn)
        if v > 0:
            burn = cl * (4.0 if "strana" in get(conn, "calderone")["flags"] else 2.0)
            dao_heart._set_toxin(conn, v - burn)
    return []


# ---------------------------------------------------------------- l'arco (soul_arcs)

class _Adapter:
    def __init__(self, k: str):
        self.k = k

    def arc_level(self, conn):
        d = get(conn, self.k)
        return d["level"] if d and d.get("active") else None

    def names(self, conn) -> dict:
        d = get(conn, self.k) or {}
        sp = d.get("spirit", "lo spirito")
        from engine.systems.mentor_ring import _di
        return {"spirito": sp, "Spirito": sp[:1].upper() + sp[1:], "di_spirito": _di(sp), "vaso": V[self.k]["name"]}

    def prepare(self, conn, player, plot):
        return True

    def branches(self, conn, plot) -> list:
        d = get(conn, self.k) or {}
        return [f for f in d.get("flags", []) if f in ("sutra", "verita")]

    def on_chapter(self, conn, player, plot, outcome, closed) -> list[str]:
        return _chapter(conn, player, self.k, plot, outcome, closed)


def adapter(k: str) -> _Adapter:
    return _Adapter(k)


def _gift(conn, player, eff: dict) -> list[str]:
    from engine.systems import encounters
    t = tick_mod.get_tick(conn)
    return encounters.apply_effects(conn, t, random.Random(t + 313), player, eff, {})


def _lose(conn, k: str, d: dict, why: str) -> list[str]:
    d["active"] = False
    d["gone"] = why
    return []


def _chapter(conn, player, k: str, plot: str, outcome: str, closed: bool) -> list[str]:
    d = get(conn, k)
    if not d:
        return []
    out: list[str] = []
    nm = V[k]["name"]
    if k == "pagoda":
        if plot == "pagoda_ricordo" and closed:
            d["level"] = min(V[k]["max"], d["level"] + 1)
            out.append(f"✦ {d['spirit']} ricorda chi l'ha forgiata: ti insegna il Sigillo della Pagoda.")
            out += _gift(conn, player, {"prize": {"rank": 2, "kinds": ["manuale"], "n": 1, "stones": False}})
        elif plot == "pagoda_padroni":
            if outcome == "restituita":
                _lose(conn, k, d, "restituita")
                out += _gift(conn, player, {"prize": {"rank": 1, "kinds": ["tesoro", "manuale"]}})
                out.append("La setta della pagoda ti ripaga con il suo tesoro. Lo spirito, partendo, ti saluta con la mano.")
            elif closed:
                d["flags"].append("scelta")
                out.append(f"✦ {d['spirit']} ha scelto te: la pagoda ora ti obbedisce del tutto.")
        elif plot == "pagoda_nome":
            if outcome == "libera":
                _lose(conn, k, d, "libera")
                out += _gift(conn, player, {"prize": {"rank": 1, "kinds": ["reliquia", "tesoro"]}, "lifespan_years": 50})
                state.grant_title(conn, "Colui che Restituì un Nome")
            else:
                d["flags"].append("legata")
                out.append(f"✦ {d['spirit']} è legata a te per sempre: tutti i doni della pagoda crescono della metà.")
                state.grant_title(conn, "Signore della Pagoda")
    elif k == "stendardo":
        if plot == "stendardo_voci":
            if outcome == "liberata":
                d["souls"] = max(0, d["souls"] - 1)
            elif outcome == "innocenti":
                d["souls"] = int(d["souls"] * 0.8)
                d["flags"].append("misericordia")
            else:
                d["souls"] += 5
        elif plot == "stendardo_giusti" and outcome in ("scontro_perso", "tregua"):
            d["souls"] //= 2
            out.append("Metà delle anime è fuggita dallo stendardo.")
        elif plot == "stendardo_rivolta":
            if outcome == "liberate":
                _lose(conn, k, d, "liberate")
                out += _gift(conn, player, {"karma": 30, "heart": 10, "merit": 50, "lifespan_years": 30})
                state.grant_title(conn, "Liberatore delle Diecimila Anime")
            elif closed:
                d["flags"].append("re")
                state.grant_title(conn, "Re delle Anime")
                out.append("✦ Lo stendardo diventa lo Stendardo del Re delle Anime: la sua forza in battaglia cresce della metà.")
            else:
                d["souls"] //= 2
        d["level"] = min(V[k]["max"], 1 + sum(1 for s in BANNER_STEPS if d["souls"] >= s)) if d.get("active") else d["level"]
    elif k == "calderone":
        if plot == "calderone_fame" and closed:
            d["flags"].append("strana")
            d["level"] = min(V[k]["max"], d["level"] + 1)
            out.append("✦ Il calderone ha mangiato una Fiamma Strana: brucia il doppio delle tossine, ogni giorno.")
        elif plot == "calderone_maestro" and closed:
            out += _gift(conn, player, {"prize": {"rank": 1, "kinds": ["pillola", "manuale"]}})
            out.append("Il vecchio alchimista ti lascia le sue ricette migliori.")
        elif plot == "calderone_fiamma" and closed:
            d["flags"].append("celeste")
            state.grant_title(conn, "Padrone della Fiamma Celeste")
            out.append("✦ La Fiamma Celeste arde nel calderone: le tue arti riescono il doppio più spesso.")
    elif k == "perla":
        if plot == "perla_voce":
            if outcome == "sigillo":
                d["level"] += 1
                out += _gift(conn, player, {"prize": {"rank": 2, "kinds": ["tesoro"], "n": 1, "stones": False}})
            elif outcome == "verita":
                d["flags"].append("verita")
        elif plot == "perla_prezzo":
            if outcome == "consegnata":
                _lose(conn, k, d, "consegnata")
                out += _gift(conn, player, {"prize": {"rank": 1, "kinds": ["tesoro", "manuale"]}, "heart": 8})
                out.append("Il monaco porta via la perla. Per la prima volta da settimane dormi senza sogni.")
            elif outcome == "sutra":
                d["flags"].append("sutra")
        elif plot == "perla_possessione":
            if outcome == "divorato":
                _lose(conn, k, d, "divorato")
                from engine.systems import items
                t = tick_mod.get_tick(conn)
                out += items.apply_effects(conn, t, random.Random(t + 9), player.id, {
                    "learn_technique": {"name": f"Diecimila Anni {__import__('engine.systems.mentor_ring', fromlist=['x'])._di(d['spirit'])}", "magnitude": 0.3,
                                        "tech_key": "perla:divorato"}, "dao_key": "anima", "dao_gain": 30})
                state.grant_title(conn, "Divoratore di Demoni")
            elif outcome == "risigillato":
                d["flags"].append("sigillata")
                out.append("La perla è sigillata per sempre. La forza dei patti, però, resta tua.")
            elif outcome == "simbiosi":
                d["flags"].append("simbiosi")
                state.grant_title(conn, "Due Anime in un Corpo")
                out.append("✦ Il demone vive con te: la forza dei patti cresce della metà, ma il karma ne porta il segno.")
            else:
                d["level"] = 3                                  # respinto: tre sigilli tornano al loro posto
                out.append("I sigilli si richiudono a fatica: ne tornano sei.")
    _save(conn, k, d)
    return out


# ---------------------------------------------------------------- comandi e pannello

def describe(conn, k: str) -> list[str]:
    from engine.systems import soul_arcs
    d = get(conn, k)
    if not d:
        return []
    if not d.get("active"):
        return [f"{V[k]['icon']} {V[k]['name']} — non è più con te ({d.get('gone', '')})."]
    lines = [f"{V[k]['icon']} {V[k]['name']} — {d['spirit']}, livello {d['level']}/{V[k]['max']}"]
    if k == "pagoda":
        lines.append(f"  Nutrimento: {d['fed']}/{feed_need(conn, k, d['level'])} pietre spirituali. "
                     f"Coltivazione +{3 * d['level']}%, nemici −{min(30, 2.5 * d['level']):.0f}% di attacco.")
    elif k == "stendardo":
        nxt = next((s for s in BANNER_STEPS if s > d["souls"]), None)
        lines.append(f"  Anime: {d['souls']}" + (f" (prossimo livello a {nxt})" if nxt else "")
                     + f". Attacco +{min(60, 4 * d['level'])}%" + (" ×1,5 (Re delle Anime)" if "re" in d["flags"] else "") + ".")
    elif k == "calderone":
        lines.append(f"  Nutrimento: {d['fed']}/{feed_need(conn, k, d['level'])} erbe. Arti +{craft_bonus(conn) * 100:.0f}%, "
                     f"tossine −{d['level'] * (4 if 'strana' in d['flags'] else 2)} al giorno.")
    elif k == "perla":
        lines.append(f"  Sigilli sciolti: {d['level']}/9. Forza dei patti: attacco +{d.get('atk', 0) * 100:.0f}%.")
    lines.append("  " + soul_arcs.status_line(conn, k))
    return lines


def command(conn, player, k: str, arg: str) -> str:
    parts = (arg or "").split()
    sub = parts[0].lower() if parts else ""
    rest = " ".join(parts[1:])
    if sub in ("nutri", "feed"):
        return feed(conn, player, k, rest)
    if k == "perla" and sub in ("patto", "patti", "pact"):
        return pact(conn, player, rest)
    if k == "stendardo" and sub in ("scatena", "libera_anime", "usa"):
        return unleash(conn, player)
    return "\n".join(describe(conn, k)) or f"Non porti {V[k]['name']}."


def overview(conn, player) -> str:
    from engine.systems import mentor_ring
    lines = ["✧ I TUOI VASI D'ANIMA"]
    if mentor_ring.get(conn):
        lines.append(mentor_ring.advise(conn, player).split("\n")[0])
    for k in ORDER:
        lines += describe(conn, k)
    if len(lines) == 1:
        lines.append("Non porti oggetti con un'anima. Si trovano esplorando rovine, montagne e zone proibite.")
    return "\n".join(lines)


def menu_sections(conn, player) -> list[dict]:
    from engine.systems.menus import act, bar, section
    from engine.systems import mentor_ring, soul_arcs, professions, sects
    secs = []
    r = mentor_ring.get(conn)
    if r:
        acts, lines, bars = [], [], []
        if r.get("gone"):
            c = mentor_ring.soul_candidate(conn)
            lines.append("L'anello è vuoto.")
            acts.append(act("Accogli un'anima nell'anello", "anello accogli", bool(c),
                            "abbatti un coltivatore forte: per un giorno la sua anima vaga"))
        elif r.get("captive"):
            lines.append(f"{r['name']} è prigioniero del Palazzo delle Anime.")
            lines.append(soul_arcs.status_line(conn, "anello"))
        else:
            need = mentor_ring.feed_need(r["level"])
            bars.append(bar("Nutrimento", 100 * r.get("fed", 0) / max(1, need), f"{r.get('fed', 0)}/{need} nuclei", tone="rare"))
            lines.append(f"{r['name']}, livello {r['level']}" + (" · Legno Nutrianime" if r.get("wood") else ""))
            lines.append(soul_arcs.status_line(conn, "anello"))
            have = professions.material(conn, player.id, "nuclei")
            acts += [act("Nutri il maestro", f"anello nutri {max(1, need - r.get('fed', 0))}", have > 0, "nessun nucleo"),
                     act("Il maestro combatte con te (prossimo scontro)", "anello forza"),
                     act("Chiedi consiglio", "anello")]
        secs.append(section("L'anello del maestro", lines, acts, bars, icon="💍"))
    for k in ORDER:
        d = get(conn, k)
        if not d:
            continue
        lines = describe(conn, k)[1:]
        acts = []
        if d.get("active"):
            if k == "pagoda":
                need = feed_need(conn, k, d["level"], player.id) - d["fed"]
                ok = sects.get_resource(conn, "pietre_spirituali", player.id) > 0 and d["level"] < V[k]["max"]
                acts.append(act(f"Nutri il piano ({need} pietre)", "pagoda nutri", ok, "niente pietre o pagoda completa"))
            elif k == "calderone":
                ok = professions.material(conn, player.id, "erbe") > 0 and d["level"] < V[k]["max"]
                acts.append(act("Nutri la fiamma con erbe", "calderone nutri", ok, "niente erbe o calderone completo"))
            elif k == "stendardo":
                acts.append(act("Scatena le anime nel prossimo scontro", "stendardo scatena", d["souls"] >= 5,
                                "servono almeno 5 anime"))
            elif k == "perla":
                ok = "sigillata" not in d["flags"] and d["level"] < 9
                acts += [act("Patto: forza (−15 anni di vita)", "perla patto forza", ok, "nessun patto possibile"),
                         act("Patto: vita (−karma)", "perla patto vita", ok, "nessun patto possibile"),
                         act("Patto: segreto (−cuore)", "perla patto segreto", ok, "nessun patto possibile")]
        secs.append(section(V[k]["name"] + (f" — {d.get('spirit')}" if d.get("active") else ""), lines, acts,
                            icon=V[k]["icon"]))
    if not secs:
        secs.append(section("Nessun vaso d'anima", [
            "Esplorando rovine, montagne e zone proibite puoi trovare oggetti con un'anima dentro: un anello, una "
            "pagoda, uno stendardo, un calderone, una perla. Ognuno ha la sua storia."], icon="✧"))
    return secs
