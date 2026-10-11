"""
LA TRAMA MAESTRA — una storia sola, dal primo giorno a tutti i mondi, senza un nemico finale.

È costruita a "storylet" (come Fallen London): piccole scene che si sbloccano quando le
condizioni del mondo e del personaggio lo permettono, e che ricordano le tue scelte.

ATTO I — L'umiliazione (regni 1-3)
  · Il fidanzamento annullato davanti a tutti — e il giuramento dei tre anni.
  · L'arcinemico che ti soffia la prima fortuna (tornerà, sempre).
  · Il primo frammento del tuo retaggio rivela che il furto non fu un caso: esiste la MIETITURA.
ATTO II — Il mondo è più grande (regni 4-6)
  · Le corti dei regni ti chiamano.  · Il segreto dei tuoi genitori.  · Le razze antiche.
  · Il tradimento di chi ti era vicino — e la prigionia.
ATTO III — La mietitura (regni 7-9)
  · I Mietitori danno la caccia ai geni.  · La calamità dell'era.  · La Porta Celeste.
ATTO IV, V, … — I mondi superiori (per ogni nuovo strato di mondo, senza fine)
  · Il clan dominante che disprezza i nuovi venuti.  · Un nuovo pezzo della verità (tua madre,
    tuo padre, e poi sempre più su).  · Il SIGNORE di quel mondo da superare.  · Fondare il tuo
    Dao come legge di quel mondo (Imperatore del Dao).
  La Mietitura non ha un vertice raggiungibile: ogni mondo ne rivela un gradino più alto.

  trama        a che punto sei della storia, e cosa ti aspetta
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "master_plot"
YEAR_DAYS = 17                       # ~ un anno di gioco
_ORDER = ["Mietitori", "Falciatori", "Custodi del Granaio", "Signori del Raccolto", "Vecchi del Campo Celeste",
          "Seminatori delle Ere"]


def get(conn) -> dict:
    d = state.get_json(conn, KEY)
    if not d:
        d = {"done": [], "flags": [], "choices": {}, "fiancee": None, "duel_day": None, "betrayer": None,
             "lords": {}, "laws": []}
        state.set_json(conn, KEY, d)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def flag(conn, f: str) -> bool:
    return f in get(conn)["flags"]


def set_flag(conn, f: str) -> None:
    d = get(conn)
    if f not in d["flags"]:
        d["flags"].append(f)
        _save(conn, d)


def record_choice(conn, k: str, v) -> None:
    d = get(conn)
    d["choices"][k] = v
    _save(conn, d)


def order_rank(n: int) -> str:
    return _ORDER[n] if n < len(_ORDER) else f"{_ORDER[-1]} del {n - len(_ORDER) + 2}° Cerchio"


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _day(conn) -> int:
    from engine.systems import storyline
    return (tick_mod.get_tick(conn) - storyline.life_start(conn)) // 120


def _name(conn, nid) -> str:
    r = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone() if nid else None
    return r["name"] if r else "qualcuno"


def _alive(conn, nid) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone() if nid else None
    return bool(r) and r["status"] == "alive"


# ============================================================
# Storylet
# ============================================================

def _beats(conn, player) -> list[tuple[str, bool, callable]]:
    from engine.systems import lost_legacy, ascension
    d = get(conn)
    t = _tier(conn, player.id)
    day = _day(conn)
    lg = lost_legacy.get(conn)
    beats = [
        ("fidanzamento", day >= 2, _b_engagement),
        ("arcinemico", day >= 5, _b_archrival),
        ("duello", "giuramento" in d["flags"] and d.get("duel_day") is not None
         and tick_mod.get_tick(conn) // 120 >= d["duel_day"], _b_duel),
        ("verita_1", bool(lg) and lost_legacy.total(lg) >= 1, _b_truth1),
        ("corte", t >= 4, _b_court),
        ("genitori", t >= 4, _b_parents),
        ("razze", t >= 4, _b_races),
        ("tradimento", t >= 5, _b_betrayal),
        ("prigionia", t >= 5 and "tradimento" in d["flags"], _b_prison),
        ("mietitori", t >= 7, _b_reapers),
        ("calamita", t >= 8, _b_calamity),
    ]
    for L in range(1, ascension.reached(conn) + 1):
        b = 6 + 3 * L
        beats += [
            (f"disprezzo_{L}", t >= b, lambda c, p, L=L: _b_scorn(c, p, L)),
            (f"verita_{L + 1}", t >= b + 1, lambda c, p, L=L: _b_truth(c, p, L)),
            (f"signore_{L}", t >= b + 1, lambda c, p, L=L: _b_lord(c, p, L)),
            (f"imperatore_{L}", t >= b + 2 and _lord_beaten(c=conn, L=L), lambda c, p, L=L: _b_emperor(c, p, L)),
        ]
    return beats


def maybe_advance(conn, player) -> str | None:
    from engine.systems import encounters, captivity
    if encounters.pending(conn) or captivity.active(conn):
        return None
    d = get(conn)
    for key, ok, fn in _beats(conn, player):
        if key in d["done"] or not ok:
            continue
        sc = fn(conn, player)
        d = get(conn)
        if key != "duello" and key not in d["done"]:
            d["done"].append(key)
        _save(conn, d)
        if sc:
            sc.setdefault("sticky", True)
            sc.setdefault("event_type", "story")
            return encounters.start_scene(conn, player, sc)
    return None


def _scene(title: str, text: str, choices: list[dict], ctx: dict | None = None) -> dict:
    s = {"key": "trama", "title": f"☯ {title}", "text": text, "choices": choices}
    if ctx:
        s["ctx"] = ctx
    return s


# ---------- ATTO I ----------

def _b_engagement(conn, player) -> dict:
    from engine.systems import npc_factory, prodigies
    rng = random.Random(tick_mod.get_tick(conn) + 11)
    f = conn.execute("SELECT id, name, home_location_id FROM factions WHERE status='active' ORDER BY influence DESC LIMIT 1;").fetchone()
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=f["home_location_id"] if f else player.location_id,
                            tier=_tier(conn, player.id), stage=rng.randint(6, 9), faction_id=f["id"] if f else None,
                            traits={"pride": 90, "ambition": 85, "honor": 55}, gender="f")
    d = get(conn)
    d["fiancee"] = nid
    _save(conn, d)
    ids = state.get_json(conn, prodigies.KEY, []) or []
    ids.insert(0, nid)
    state.set_json(conn, prodigies.KEY, ids)
    nm = _name(conn, nid)
    sect = f["name"] if f else "una grande setta"
    return _scene("L'annullamento del fidanzamento",
                  f"Davanti a tutta la città, {nm} — la tua promessa sposa fin dall'infanzia, ora discepola prediletta della "
                  f"{sect} — getta a terra il contratto di fidanzamento. «Un futuro immortale non sposa una nullità.» "
                  "La folla ride.",
                  [{"label": "Subisci in silenzio, a pugni chiusi", "effects": {"heart": -5, "plot_flag": "silenzio",
                                                                               "plot_choice": {"fidanzamento": "silenzio"}}},
                   {"label": "«Tra tre anni ti sconfiggerò davanti a tutti.»",
                    "effects": {"plot_flag": "giuramento", "plot_vow": 3, "fame": 3,
                                "plot_choice": {"fidanzamento": "giuramento"},
                                "text": "Il silenzio cala sulla piazza. Qualcuno smette di ridere."}},
                   {"label": "Sei tu a stracciare il contratto: «Non ti ho mai voluto.»",
                    "effects": {"fame": 5, "heart": 3, "plot_flag": "orgoglio",
                                "plot_choice": {"fidanzamento": "orgoglio"}}}])


def _b_archrival(conn, player) -> dict:
    from engine.systems import archrival
    rng = random.Random(tick_mod.get_tick(conn) + 13)
    if not archrival.get(conn):
        archrival.create(conn, rng, player)
    d = archrival.get(conn)
    nm = archrival.npc_name(conn, d)
    return _scene("L'arcinemico",
                  f"Avevi trovato per primo un'erba spirituale millenaria. {nm} «{d['epithet']}» te la strappa di mano "
                  "con un sorriso: «Le fortune del Cielo appartengono a chi è nato per riceverle.»",
                  [{"label": "Lo sfidi subito", "effects": {}, "command": f"attack {nm}"},
                   {"label": "Lo lasci andare, e te lo segni", "effects": {"heart": -1, "plot_flag": "segnato",
                                                                          "text": "Te lo segni. Ti incontrerà di nuovo."}}],
                  ctx={"npc_id": d["npc"], "npc_name": nm})


def _b_duel(conn, player) -> dict:
    d = get(conn)
    nm = _name(conn, d["fiancee"])
    if not _alive(conn, d["fiancee"]):
        d["flags"].append("duello_senza_avversario")
        d["done"].append("duello")
        _save(conn, d)
        return _scene("Il giorno del patto", f"È il giorno del patto, ma {nm} non c'è più. Il giuramento resta "
                      "senza risposta: la città, però, ricorda che ti eri presentato.",
                      [{"label": "Prosegui", "effects": {"fame": 5}}])
    return _scene("Il giorno del patto",
                  f"Sono passati tre anni. La piazza è gremita: {nm} ti aspetta sull'arena, più forte che mai, la "
                  "spada in pugno e il mento alto. "
                  "«Sei venuto davvero. Bene: oggi ti rimetto al tuo posto.»",
                  [{"label": "Combatti il duello giurato", "effects": {"plot_duel": "fidanzamento"}},
                   {"label": "Chiedi altri tre anni (perdi la faccia)", "effects": {"plot_vow": 3, "fame": -5, "heart": -4}}])


def _b_truth1(conn, player) -> dict:
    return _scene("La prima verità",
                  "Il frammento del tuo retaggio, appena ripreso, porta un'impronta: un sigillo a forma di falce. "
                  "Non sei stato derubato per caso. Qualcuno, da qualche parte, «miete» i talenti del mondo come "
                  "spighe. Li chiamano i Mietitori.",
                  [{"label": "Giuri di scoprire chi sono", "effects": {"plot_flag": "mietitura_nota", "heart": 3}},
                   {"label": "Tieni il segreto per te", "effects": {"plot_flag": "mietitura_nota", "dao_key": "anima",
                                                                     "dao_gain": 3}}])


# ---------- ATTO II ----------

def _b_court(conn, player) -> dict:
    from engine.systems import kingdoms
    d = kingdoms.ensure(conn)
    kk = kingdoms.kingdom_of(conn, player.location_id)
    name = kk[1]["name"] if kk else (list(d.values())[0]["name"] if d else "un regno lontano")
    return _scene("Le corti dei regni",
                  f"Un messaggero con le insegne del {name} si inchina davanti a te: «Sua Maestà ha sentito parlare "
                  "di voi. La corte ha bisogno di uomini come voi — e i principi, già, si contendono la successione.»",
                  [{"label": "Accetti di presentarti a corte", "effects": {"plot_flag": "corte", "fame": 3,
                                                                          "text": "('regni', 'corte', 'sostieni <principe>')"}},
                   {"label": "La politica dei mortali non ti riguarda", "effects": {"plot_flag": "corte", "heart": 2}}])


def _b_parents(conn, player) -> dict:
    from engine.systems import ascension
    return _scene("Il segreto dei tuoi genitori",
                  "Una lettera, sigillata con il sangue, che ti aspettava da anni presso un vecchio amico di famiglia: "
                  f"«Se leggi questo, sei diventato forte. Tua madre non è morta: è prigioniera di un clan del "
                  f"{ascension.layer_name(1)}. Tuo padre è andato a cercarla, e non è tornato. Non fidarti dei Mietitori.»",
                  [{"label": "Giuri di salire ai mondi superiori per liberarla",
                    "effects": {"plot_flag": "genitori", "heart": 6, "plot_choice": {"genitori": "giuro"}}},
                   {"label": "Bruci la lettera: la tua strada è tua",
                    "effects": {"plot_flag": "genitori", "aff_soul": 2, "plot_choice": {"genitori": "bruciata"}}}])


def _b_races(conn, player) -> dict:
    from engine.systems import races
    lines = races.intro(conn, player)
    return _scene("Le razze antiche",
                  "Al confine delle terre umane ti attende un consiglio insolito: un vecchio dagli occhi di drago, una "
                  "donna di linfa e corteccia, un gigante, un demone dalle corna d'ossidiana. «Il tuo nome è arrivato "
                  "fino a noi. Vedremo se meriti la nostra amicizia.» " + " ".join(lines[1:]),
                  [{"label": "Ti inchini a ognuno di loro", "effects": {"plot_flag": "razze", "race_all": 10}},
                   {"label": "Li guardi dritto negli occhi, da pari", "effects": {"plot_flag": "razze", "fame": 3}}])


def _b_betrayal(conn, player) -> dict | None:
    from engine.systems import bonds, npc_factory
    pid = player.id
    cand = None
    for kind in ("sworn", "companion", "disciple"):
        rows = [r for r in bonds._active(conn, pid, kind) if r["npc_status"] == "alive"]
        if rows:
            cand = rows[0]["npc_id"]
            bonds.end_bond(conn, pid, cand, kind, "tradito")
            break
    if not cand:
        r = conn.execute("SELECT npc_id FROM npc_player_relations WHERE player_id=? ORDER BY score DESC LIMIT 1;",
                         (pid,)).fetchone()
        cand = r["npc_id"] if r and _alive(conn, r["npc_id"]) else npc_factory.spawn(
            conn, random.Random(7), archetype="vagabondo", location_id=None, tier=_tier(conn, pid))
    d = get(conn)
    d["betrayer"] = cand
    _save(conn, d)
    nm = _name(conn, cand)
    return _scene("Il tradimento",
                  f"Lo scopri troppo tardi: {nm}, di cui ti fidavi, ha venduto ai tuoi nemici i tuoi segreti — il tuo "
                  "rifugio, i tuoi poteri, le tue debolezze. Ti guarda negli occhi un'ultima volta: «Non è niente di "
                  "personale. Mi hanno offerto un futuro.»",
                  [{"label": "Giuri vendetta", "effects": {"plot_flag": "tradimento", "bond": "nemesis",
                                                           "bond_reason": "ti ha tradito", "heart": -4,
                                                           "plot_choice": {"traditore": "vendetta"}}},
                   {"label": "Lo lasci andare: un giorno capirà", "effects": {"plot_flag": "tradimento", "heart": 4,
                                                                              "karma": 20, "npc_leaves": True,
                                                                              "plot_choice": {"traditore": "perdono"}}}],
                  ctx={"npc_id": cand, "npc_name": nm})


def _b_prison(conn, player) -> dict:
    d = get(conn)
    who = _name(conn, d.get("betrayer"))
    return _scene("L'imboscata",
                  f"Grazie a ciò che ha rivelato {who}, ti tendono un'imboscata perfetta: sigilli che bloccano il Qi, "
                  "dieci coltivatori al tuo livello. Combatti, ma alla fine il buio ti inghiotte.",
                  [{"label": "…", "effects": {"imprison": "chi ha comprato il tradimento"}}])


# ---------- ATTO III ----------

def _b_reapers(conn, player) -> dict:
    from engine.systems import prodigies
    ids = [i for i in prodigies.roster(conn) if _alive(conn, i)]
    victim = _name(conn, ids[0]) if ids else "un giovane genio"
    return _scene("I Mietitori",
                  f"Una figura senza volto, con una falce d'argento sul petto, afferra {victim} per la gola. «Il raccolto "
                  "è maturo.» È un Mietitore — il primo che vedi con i tuoi occhi.",
                  [{"label": "Lo affronti per salvare il genio",
                    "effects": {"plot_flag": "mietitori", "spawn": {"archetype": "anziano", "tier_offset": 1, "stage": 5},
                                "plot_choice": {"mietitori": "combatti"}, "heart": 3}, "command": "attack {npc}"},
                   {"label": "Lo segui di nascosto per scoprire dove porta i talenti",
                    "check": {"stat": "istinto", "dc": 70},
                    "success": {"plot_flag": "mietitori", "plot_flag2": "granaio_noto",
                                "text": "Lo vedi sparire in una crepa del cielo: il «granaio» non è in questo mondo.",
                                "plot_choice": {"mietitori": "segui"}},
                    "failure": {"plot_flag": "mietitori", "injury": 4, "text": "Ti scopre, e ti lascia un segno."}},
                   {"label": "Ti offri di servire la Mietitura", "effects": {"plot_flag": "mietitori", "karma": -80,
                                                                            "infamy": 15, "cultivation_progress": 0.8,
                                                                            "plot_choice": {"mietitori": "servo"},
                                                                            "text": "Ti consegnano un segno a falce. "
                                                                                    "Il potere arriva. Il cuore no."}}])


def _b_calamity(conn, player) -> dict:
    from engine.systems import eras
    al = eras.allies(conn, player.id)
    e = eras.get(conn)
    e["start"] = min(e["start"], tick_mod.get_tick(conn) // 120 - eras.ERA_DAYS + 5)
    e["n"] = e["n"] + (3 - e["n"] % 4) % 4
    eras._save(conn, e)
    return _scene("Il presagio della calamità",
                  "Gli astri si oscurano. Gli anziani di ogni setta, i re, perfino le razze antiche dicono la stessa cosa: "
                  "fra pochi giorni tornerà la calamità dell'era. Chi resterà al tuo fianco?\n"
                  + ("Si schierano con te: " + ", ".join(al) + "." if al else "Per ora, nessuno: cerca alleati."),
                  [{"label": "Chiami a raccolta tutti i tuoi alleati", "effects": {"plot_flag": "calamita", "fame": 5}},
                   {"label": "Ti prepari da solo", "effects": {"plot_flag": "calamita", "dao_key": "random", "dao_gain": 5}}])


# ---------- I MONDI SUPERIORI (senza fine) ----------

def _b_scorn(conn, player, L: int) -> dict:
    from engine.systems import ascension
    clan = random.Random(L * 31).choice(["Clan Celeste Long", "Casata Imperiale Xuan", "Clan delle Nove Stelle",
                                         "Palazzo del Sole Eterno", "Clan del Loto Dorato"])
    return _scene(f"{ascension.layer_name(L)} — Il disprezzo",
                  f"Nel {ascension.layer_name(L)} i nuovi venuti dal basso sono meno che servi. Un giovane maestro del "
                  f"{clan} ti blocca la strada: «Inginocchiati, ascensore. Qui il tuo regno non vale niente.»",
                  [{"label": "Ti inginocchi (per ora)", "effects": {"heart": -6, "plot_choice": {f"disprezzo_{L}": "chino"}}},
                   {"label": "Lo umili davanti a tutti", "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 0,
                                                                              "stage": 9, "traits": {"pride": 99}},
                                                                    "plot_choice": {f"disprezzo_{L}": "sfida"}, "fame": 6},
                    "command": "attack {npc}"}])


def _b_truth(conn, player, L: int) -> dict:
    from engine.systems import ascension
    if L == 1:
        txt = ("La trovi: tua madre, in una prigione di cristallo nel cuore del clan che la teneva. Ti riconosce prima "
               "che tu dica una parola. «Sei cresciuto.» Per liberarla dovrai spezzare il sigillo — e chi lo custodisce.")
        ch = [{"label": "Spezzi il sigillo e affronti il custode",
               "effects": {"spawn": {"archetype": "anziano", "tier_offset": 1, "stage": 6}, "plot_flag": "madre_libera",
                           "heart": 15, "lifespan_years": 50, "title": "Figlio che Spezzò il Sigillo"},
               "command": "attack {npc}"}]
    elif L == 2:
        txt = ("Tua madre ti porta dove tuo padre era scomparso: una crepa nel cielo, la stessa in cui spariscono i "
               "talenti mietuti. Dall'altra parte, una voce che conosci: «Ancora più su, figlio mio. Il granaio ha altri piani.»")
        ch = [{"label": "Prometti di raggiungerlo", "effects": {"plot_flag": "padre_vivo", "heart": 10, "dao_key": "destino",
                                                                "dao_gain": 10}}]
    else:
        rank = order_rank(L - 1)
        txt = (f"Nel {ascension.layer_name(L)} scopri che i {order_rank(L - 2)} che conoscevi obbedivano ai {rank}: "
               "un gradino più su, un raccolto più grande. La verità sale come i mondi — e così te.")
        ch = [{"label": "Continui a salire", "effects": {"dao_key": "random", "dao_gain": 5 + L, "heart": 3,
                                                         "plot_flag": f"verita_{L + 1}"}}]
    return _scene(f"{ascension.layer_name(L)} — Un'altra verità", txt, ch)


def _lord_beaten(c, L: int) -> bool:
    d = get(c)
    nid = d["lords"].get(str(L))
    return bool(nid) and not _alive(c, nid)


def _b_lord(conn, player, L: int) -> dict:
    from engine.systems import npc_factory, ascension
    rng = random.Random(L * 97)
    t = _tier(conn, player.id)
    nid = npc_factory.spawn(conn, rng, archetype="patriarca", location_id=player.location_id,
                            tier=t + 1, stage=8, traits={"pride": 95})
    d = get(conn)
    d["lords"][str(L)] = nid
    _save(conn, d)
    nm = _name(conn, nid)
    return _scene(f"{ascension.layer_name(L)} — Il Signore di questo mondo",
                  f"{nm}, che regna sul {ascension.layer_name(L)} da diecimila anni, viene di persona a vedere chi osa "
                  "salire così in fretta. «Superami, e questo mondo sarà tuo. Fallisci, e sarai polvere tra le stelle.»",
                  [{"label": "Lo sfidi ora", "effects": {}, "command": f"attack {nm}"},
                   {"label": "«Tornerò quando sarò pronto.»", "effects": {"text": "Sorride. «Ti aspetterò.»"}}],
                  ctx={"npc_id": nid, "npc_name": nm})


def _b_emperor(conn, player, L: int) -> dict:
    from engine.systems import ascension
    return _scene(f"{ascension.layer_name(L)} — Imperatore del Dao",
                  f"Il Signore del {ascension.layer_name(L)} è caduto. Ora puoi incidere il tuo Dao nelle leggi di questo "
                  "mondo: d'ora in poi, ovunque, il tuo Dao sarà un po' più forte.",
                  [{"label": "Incidi la tua legge", "effects": {"dao_law": L,
                                                               "title": f"Imperatore del Dao del {ascension.layer_name(L)}"}}])


# ============================================================
# Effetti speciali
# ============================================================

def apply_effect(conn, t: int, rng, player, eff: dict, ctx: dict) -> list[str]:
    out = []
    d = get(conn)
    if eff.get("plot_flag"):
        set_flag(conn, eff["plot_flag"])
    if eff.get("plot_flag2"):
        set_flag(conn, eff["plot_flag2"])
    for k, v in (eff.get("plot_choice") or {}).items():
        record_choice(conn, k, v)
    if eff.get("plot_vow"):
        d = get(conn)
        d["duel_day"] = t // 120 + YEAR_DAYS * int(eff["plot_vow"])
        if "giuramento" not in d["flags"]:
            d["flags"].append("giuramento")
        _save(conn, d)
        out.append(f"Il patto è fissato: tra {eff['plot_vow']} anni, il duello.")
    if eff.get("plot_duel"):
        out += _resolve_duel(conn, rng, player)
    if eff.get("imprison"):
        from engine.systems import captivity
        out.append(captivity.imprison(conn, player, eff["imprison"]))
    if eff.get("dao_law"):
        d = get(conn)
        d["laws"].append(int(eff["dao_law"]))
        _save(conn, d)
        out.append("✦ Il tuo Dao è ora una legge di questo mondo: tutti i tuoi Dao crescono più in fretta, ovunque.")
    if eff.get("race_all"):
        from engine.systems import races
        for k in races.RACES:
            out += races.adjust(conn, k, rel=int(eff["race_all"]))
    return out


def _resolve_duel(conn, rng, player) -> list[str]:
    from engine.systems import perception, reputation, relations
    d = get(conn)
    fid = d["fiancee"]
    nm = _name(conn, fid)
    ratio = perception.strength_ratio(conn, player.id, fid)
    won = ratio * rng.uniform(0.8, 1.2) >= 1.0
    d["done"].append("duello")
    _save(conn, d)
    if won:
        reputation.adjust(conn, player.id, fame=30)
        state.grant_title(conn, "Colui che Mantenne il Patto")
        relations.adjust(conn, fid, 40, tick_mod.get_tick(conn), player.id)
        set_flag(conn, "duello_vinto")
        return [f"✦ Dopo un duello che la città racconterà per generazioni, {nm} è a terra. Ti guarda, e per la prima "
                "volta non c'è disprezzo nei suoi occhi. ✧ Nuovo titolo: «Colui che Mantenne il Patto» ✧",
                f"(Il vostro rapporto è cambiato: un giorno, chissà, potrebbe perfino diventare la tua compagna del Dao.)"]
    from engine.systems import dao_heart
    d = get(conn)
    d["done"].remove("duello")
    d["duel_day"] = tick_mod.get_tick(conn) // 120 + YEAR_DAYS
    _save(conn, d)
    return [f"{nm} ti batte, ancora una volta. «Torna fra un anno, se hai ancora la faccia.»"] + dao_heart.adjust(conn, -8)


def dao_mult(conn) -> float:
    return 1.0 + 0.08 * len(get(conn).get("laws", []))


# ============================================================
# Diario
# ============================================================

def goals(conn, player) -> list[str]:
    d = get(conn)
    out = []
    if "giuramento" in d["flags"] and "duello" not in d["done"] and d.get("duel_day") is not None:
        left = d["duel_day"] - tick_mod.get_tick(conn) // 120
        out.append(f"☯ Il patto dei tre anni con {_name(conn, d['fiancee'])}: il duello tra {max(0, left)} giorni.")
    if "genitori" in d["flags"] and "madre_libera" not in d["flags"]:
        out.append("☯ Tua madre è prigioniera nel mondo superiore: ascendi per liberarla.")
    from engine.systems import captivity
    if captivity.active(conn):
        out.append("⛓ Sei prigioniero: 'evadi'.")
    for L, nid in d["lords"].items():
        if _alive(conn, nid):
            out.append(f"☯ Il Signore del mondo {L}: {_name(conn, nid)} ti aspetta.")
    return out


def describe(conn, player) -> str:
    from engine.systems import ascension
    d = get(conn)
    t = _tier(conn, player.id)
    act = "I — L'umiliazione" if t <= 3 else ("II — Il mondo è più grande" if t <= 6 else
                                              ("III — La mietitura" if t <= 9 else
                                               f"{ascension.reached(conn) + 3} — {ascension.layer_name(ascension.reached(conn))}"))
    lines = [f"📜 LA TUA STORIA — Atto {act}", f"  Capitoli vissuti: {len(d['done'])}"]
    lines += ["  " + g for g in goals(conn, player)]
    if d["choices"]:
        lines.append("  Scelte che il mondo ricorda: " + ", ".join(f"{k}: {v}" for k, v in list(d["choices"].items())[-6:]))
    if d.get("laws"):
        lines.append(f"  Leggi del tuo Dao incise nei mondi: {len(d['laws'])}")
    lines.append(f"  La Mietitura: finora conosci i {order_rank(max(0, ascension.reached(conn)))}. Più sali, più in alto vedi.")
    return "\n".join(lines)
