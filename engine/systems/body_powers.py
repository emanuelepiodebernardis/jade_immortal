"""
I POTERI DEI CORPI LEGGENDARI — il corpo che si risveglia non diventa solo più forte: IMPARA.

Ogni corpo ha una sua via di poteri, come nei grandi racconti (il Corpo Santo che apre il Mare
dell'Amaro e la Ruota della Vita, l'Osso Supremo con le sue Arti Preziose, le Doppie Pupille che
vedono il vuoto, l'Asura con Tre Teste e Sei Braccia, il Nirvana della Fenice che rinasce
dalla cenere…). A ogni soglia di risveglio si sblocca un potere:

  stadio 1   (Primo Risveglio)      la TECNICA del corpo (I), che entra tra le tue tecniche
  stadio 2   (Secondo Risveglio)    un primo dono passivo
  stadio 3   (Piccola Perfezione)   un secondo dono
  stadio 4   (Grande Perfezione)    il potere maggiore e la seconda tecnica
  stadio 5   (Corpo Compiuto)       il potere supremo del corpo
  oltre      ogni 3 stadi la tecnica del corpo sale di grado (II, III, IV… senza fine)

Gli effetti passivi entrano in ogni scontro; le tecniche si sommano alle altre (come quelle delle
sette e delle razze). Il pannello del corpo mostra i poteri presi e il prossimo.
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

MILESTONES = (1, 2, 3, 4, 4, 5)
COMPLETE = 5
EVERY = 3
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# corpo -> [(nome, effetti, racconto)] per le soglie 1, 2, 3, 4, 4, 5.
# effetti: tech (potenza della tecnica), atk, taken, crit, evade, pierce, chance, strikes, saves,
#          proc (stato, probabilità, forza), cult (coltivazione), life (anni)
POWERS: dict[str, list[tuple[str, dict, str]]] = {
    "caos": [
        ("Pugno del Caos Primordiale", {"tech": 0.10}, "Un pugno che non ha forma: ogni legge vi si scioglie."),
        ("Qi Senza Nome", {"chance": 0.06}, "Ogni stato che provochi attecchisce più facilmente."),
        ("Mare del Caos", {"cult": 0.10}, "Il dantian diventa un mare senza rive."),
        ("Le Tre Mila Leggi in Uno", {"atk": 0.10, "pierce": 0.08}, "Ogni Dao è un dito della stessa mano."),
        ("Spada che Separa il Cielo e la Terra", {"tech": 0.18}, "Il primo gesto della creazione, ripetuto."),
        ("Corpo del Caos Compiuto", {"strikes": 1, "saves": 1}, "Prima del principio c'eri tu, e ci sarai dopo la fine."),
    ],
    "vene_yin": [
        ("Palmo delle Nove Vene Yin", {"tech": 0.10}, "Il gelo del midollo diventa un palmo."),
        ("Brina nel Sangue", {"proc": ("gelo", 0.08, 1.2)}, "Chi ti colpisce sente il freddo salire."),
        ("Respiro Yin", {"cult": 0.10}, "Il Qi Yin scorre come un fiume sotto il ghiaccio."),
        ("Dominio del Gelo Assoluto", {"taken": 0.08, "proc": ("gelo", 0.12, 1.4)}, "Attorno a te l'aria si ferma."),
        ("Luna nel Pozzo Ghiacciato", {"tech": 0.18}, "Un colpo che congela persino il riflesso."),
        ("Vene Yin Compiute", {"saves": 1, "evade": 0.06}, "Yin e Yang si guardano, ora, alla pari."),
    ],
    "ossa_spada": [
        ("Spada dell'Osso", {"tech": 0.10}, "Estrai la spada dal tuo stesso braccio."),
        ("Ossa che Vibrano", {"pierce": 0.06}, "Ogni lama vicina ti obbedisce un poco."),
        ("Intento di Spada Innato", {"crit": 0.05}, "Lo sguardo taglia prima della spada."),
        ("Diecimila Spade Tornano alla Fonte", {"atk": 0.10, "strikes": 1}, "Ogni osso è una spada, e colpiscono insieme."),
        ("Spada Nascosta", {"tech": 0.18}, "Un colpo che nessuno vede partire."),
        ("Corpo di Spada Compiuto", {"pierce": 0.12, "crit": 0.06}, "Tu sei la spada, la spada è il Dao."),
    ],
    "tuono": [
        ("Pugno del Tuono Celeste", {"tech": 0.10}, "Il fulmine che ti ha scelto ora esce dalle tue nocche."),
        ("Pelle di Folgore", {"taken": 0.05}, "Le tribolazioni ti hanno temprato."),
        ("Passo del Lampo", {"evade": 0.05}, "Ti muovi tra un tuono e l'altro."),
        ("Lago del Tuono", {"proc": ("stordimento", 0.12, 1.4), "atk": 0.08}, "Dove ti fermi cadono i fulmini."),
        ("Tribolazione Rovesciata", {"tech": 0.18}, "Rimandi al nemico il fulmine del Cielo."),
        ("Corpo del Tuono Compiuto", {"strikes": 1, "pierce": 0.08}, "Il Cielo non ti punisce più: ti obbedisce."),
    ],
    "ombra": [
        ("Artiglio d'Ombra", {"tech": 0.10}, "La tua ombra colpisce un attimo prima di te."),
        ("Passo senza Luna", {"evade": 0.05}, "Scompari tra due respiri."),
        ("Bere la Vita", {"proc": ("drenaggio", 0.08, 1.2)}, "Ogni colpo restituisce un poco."),
        ("Mille Ombre", {"evade": 0.06, "crit": 0.06}, "Il nemico non sa quale sei tu."),
        ("Ombra che Divora il Sole", {"tech": 0.18}, "Per un istante, la luce si spegne."),
        ("Corpo d'Ombra Compiuto", {"saves": 1, "strikes": 1}, "L'ombra non muore: si sposta."),
    ],
    "giada": [
        ("Palmo di Giada Pura", {"tech": 0.10}, "Un palmo che non lascia impurità."),
        ("Pelle di Giada", {"taken": 0.05}, "Le ferite si chiudono come acqua."),
        ("Cuore Limpido", {"cult": 0.08}, "Nessun demone trova appiglio."),
        ("Sorgente di Giada", {"proc": ("rigenerazione", 0.15, 1.5)}, "Nel petto, una sorgente che non si secca."),
        ("Luce della Montagna di Giada", {"tech": 0.18}, "Un colpo puro che purifica anche il nemico."),
        ("Corpo di Giada Compiuto", {"saves": 1, "taken": 0.08}, "Incorruttibile come la giada di diecimila anni."),
    ],
    "vuoto": [
        ("Dito del Vuoto", {"tech": 0.10}, "Indichi, e lì non c'è più niente."),
        ("Cuore Senza Attrito", {"cult": 0.08}, "Ogni Dao vi entra come vento in una stanza vuota."),
        ("Passo fra i Vuoti", {"evade": 0.06}, "Lo spazio ti lascia passare."),
        ("Vuoto che Accoglie", {"chance": 0.08, "atk": 0.08}, "Prendi la forza del nemico e la lasci cadere."),
        ("Spada del Nulla", {"tech": 0.18}, "Taglia ciò che non esiste ancora."),
        ("Cuore del Vuoto Compiuto", {"taken": 0.12, "strikes": 1}, "Il corpo fragile è diventato il cielo stesso."),
    ],
    "drago": [
        ("Artiglio del Drago Vero", {"tech": 0.10}, "Il braccio si copre di squame per un istante."),
        ("Ossa di Ferro", {"taken": 0.05}, "Le ossa del drago non si spezzano."),
        ("Ruggito del Drago", {"proc": ("terrore", 0.10, 1.3)}, "I deboli cadono in ginocchio."),
        ("Forma del Drago", {"atk": 0.12, "taken": 0.06}, "Per un respiro, sei il drago."),
        ("Drago che Sale ai Nove Cieli", {"tech": 0.18}, "Un colpo che si attorciglia fino al cielo."),
        ("Corpo del Drago Compiuto", {"strikes": 1, "saves": 1}, "Il Drago Vero non è più nel tuo sangue: sei tu."),
    ],
    "occhi": [
        ("Sguardo che Trafigge", {"tech": 0.10}, "Vedi il punto, e il colpo ci arriva."),
        ("Occhi del Cielo Aperti", {"crit": 0.05}, "Il filo dei colpi è visibile."),
        ("Vista Vera", {"evade": 0.05}, "Le illusioni non ti toccano."),
        ("Occhio che Vede la Morte", {"crit": 0.08, "pierce": 0.08}, "Ogni cosa ha un punto in cui finisce."),
        ("Pupilla del Giudizio", {"tech": 0.18}, "Lo sguardo condanna."),
        ("Occhi del Cielo Compiuti", {"crit": 0.10, "strikes": 1}, "Il Cielo guarda con i tuoi occhi."),
    ],
    "veleno": [
        ("Palmo dei Cento Veleni", {"tech": 0.10}, "Un tocco, cento veleni."),
        ("Sangue Avvelenato", {"proc": ("veleno", 0.08, 1.2)}, "Chi ti ferisce beve il tuo sangue."),
        ("Nebbia Velenosa", {"chance": 0.05}, "Il veleno trova sempre una strada."),
        ("Re dei Veleni", {"proc": ("veleno", 0.14, 1.5), "taken": 0.05}, "Ogni veleno del mondo ti riconosce re."),
        ("Fiore che Scioglie le Ossa", {"tech": 0.18}, "Fiorisce una volta, e basta."),
        ("Corpo dei Cento Veleni Compiuto", {"saves": 1, "pierce": 0.08}, "Il veleno è diventato una medicina: la tua."),
    ],
    "spezzati": [
        ("Pugno dello Scarto", {"tech": 0.12}, "Il pugno di chi è stato deriso per anni."),
        ("Meridiani come Fiumi", {"cult": 0.12}, "Le vie spezzate si sono saldate più larghe."),
        ("Volontà Indomita", {"taken": 0.06}, "Chi è caduto mille volte non teme di cadere."),
        ("Rinascita dalle Rovine", {"atk": 0.12, "saves": 1}, "Ciò che era spezzato non si spezza più."),
        ("Colpo che Ribalta il Destino", {"tech": 0.20}, "Il colpo di chi non doveva arrivare fin qui."),
        ("Meridiani Rinati Compiuti", {"strikes": 1, "cult": 0.10}, "Chi rideva di te ora ti chiama Venerabile."),
    ],
    "santo_antico": [
        ("Pugno del Santo dell'Era Desolata", {"tech": 0.12}, "A mani nude, spacca le montagne."),
        ("Mare dell'Amaro", {"cult": 0.08}, "Apri il mare nel ventre: il sangue d'oro vi bolle."),
        ("Ruota della Vita", {"taken": 0.06, "life": 50}, "La sorgente della vita gira e non si ferma."),
        ("Sangue d'Oro Santo", {"atk": 0.12, "proc": ("stordimento", 0.10, 1.4)}, "Il sangue dorato schiaccia chi lo guarda."),
        ("Le Sei Vie del Segreto", {"tech": 0.20}, "Le arti segrete delle ere antiche, una dopo l'altra."),
        ("Corpo Santo Compiuto", {"strikes": 1, "saves": 1}, "Il Cielo ti ha maledetto. Ora ha paura."),
    ],
    "osso_supremo": [
        ("Arte Preziosa dell'Osso", {"tech": 0.12}, "Il simbolo inciso nell'osso si accende."),
        ("Simboli che Scorrono", {"chance": 0.05}, "Le rune dell'osso guidano ogni colpo."),
        ("Arte Preziosa del Suanni", {"atk": 0.08}, "Il ruggito che spezza la volontà."),
        ("Arte Preziosa del Kunpeng", {"evade": 0.08, "strikes": 1}, "Ali che coprono il cielo, velocità senza pari."),
        ("Arte Preziosa del Leone Dorato", {"tech": 0.20}, "Un ruggito d'oro che fende il mare."),
        ("Osso Supremo Compiuto", {"crit": 0.08, "saves": 1}, "Nessuno potrà strapparti l'osso: ora è il mondo intero."),
    ],
    "doppie_pupille": [
        ("Sguardo delle Doppie Pupille", {"tech": 0.12}, "Due pupille, due mondi."),
        ("Vedere il Vuoto", {"evade": 0.05}, "Le tecniche del nemico si vedono prima di nascere."),
        ("Illusione Rovesciata", {"proc": ("confusione", 0.10, 1.3)}, "Lo specchio restituisce l'inganno."),
        ("Mondo nella Pupilla", {"crit": 0.08, "chance": 0.06}, "Nella pupilla si apre un piccolo mondo."),
        ("Pupilla che Disfa le Leggi", {"tech": 0.20}, "Guardi una legge, e si sfalda."),
        ("Doppie Pupille Compiute", {"strikes": 1, "evade": 0.06}, "Vedi il passato e il futuro del colpo."),
    ],
    "dao_innato": [
        ("Sigillo dell'Embrione del Dao", {"tech": 0.12}, "Il Dao nato con te prende forma."),
        ("Dao che Respira", {"cult": 0.08}, "Il Dao ti cresce dentro anche quando dormi."),
        ("Mille Comprensioni", {"chance": 0.05}, "Ogni scontro è una lezione."),
        ("Embrione che si Schiude", {"atk": 0.10, "pierce": 0.08}, "Il Dao innato esce dal guscio."),
        ("Parola del Dao", {"tech": 0.20}, "Una parola sola, e il mondo obbedisce."),
        ("Embrione del Dao Compiuto", {"saves": 1, "strikes": 1}, "Tu sei il Dao che cammina."),
    ],
    "nove_yang": [
        ("Palmo dei Nove Yang", {"tech": 0.10}, "Nove soli in un palmo."),
        ("Sangue che Brucia", {"proc": ("ustione", 0.08, 1.2)}, "Il tuo sangue scotta chi lo versa."),
        ("Fornace Interiore", {"cult": 0.10}, "Il fuoco interiore raffina il Qi."),
        ("Nove Soli nel Cielo", {"atk": 0.10, "proc": ("ustione", 0.12, 1.4)}, "Nove soli sorgono alle tue spalle."),
        ("Fiamma che Brucia il Cielo", {"tech": 0.18}, "Una fiamma che arde anche il vuoto."),
        ("Corpo dei Nove Yang Compiuto", {"saves": 1, "taken": 0.08}, "Il fuoco non brucia più la tua calma."),
    ],
    "luna": [
        ("Palmo della Luna Grande", {"tech": 0.10}, "Una luce fredda, piena."),
        ("Luce Lunare", {"evade": 0.05}, "Ti muovi come un riflesso sull'acqua."),
        ("Marea", {"proc": ("gelo", 0.10, 1.3)}, "La luna muove le acque del nemico."),
        ("Luna Piena Eterna", {"taken": 0.08, "chance": 0.05}, "Sopra di te la luna non cala."),
        ("Luna che Taglia il Mare", {"tech": 0.18}, "Un arco d'argento che divide le onde."),
        ("Corpo della Luna Compiuto", {"saves": 1, "evade": 0.06}, "La luna e il sole, ora, si cercano."),
    ],
    "sole": [
        ("Palmo del Sole Grande", {"tech": 0.10}, "Il sole di mezzogiorno in una mano."),
        ("Luce che Acceca", {"proc": ("accecamento", 0.08, 1.2)}, "Guardarti fa male."),
        ("Calore Instancabile", {"atk": 0.06}, "Il sole non si stanca."),
        ("Sole a Mezzogiorno", {"atk": 0.10, "proc": ("ustione", 0.12, 1.4)}, "Nessuna ombra dove sei tu."),
        ("Sole che Cade", {"tech": 0.18}, "Un sole intero precipita sul nemico."),
        ("Corpo del Sole Compiuto", {"strikes": 1, "pierce": 0.08}, "Il sole sorge quando lo dici tu."),
    ],
    "asura": [
        ("Lama dell'Asura", {"tech": 0.12}, "Il sangue chiama sangue."),
        ("Furia Crescente", {"atk": 0.06}, "Ogni ferita ti rende più feroce."),
        ("Occhi Rossi", {"proc": ("terrore", 0.10, 1.3)}, "Chi ti guarda vede la propria morte."),
        ("Tre Teste e Sei Braccia", {"strikes": 1, "atk": 0.10}, "Spuntano due teste e quattro braccia: sei mani, sei armi."),
        ("Campo di Massacro", {"tech": 0.20}, "Dove passi, crescono solo spade."),
        ("Corpo di Asura Compiuto", {"saves": 1, "pierce": 0.10}, "Il re degli Asura non conosce la pace, né la sconfitta."),
    ],
    "immortale": [
        ("Pugno che Non Muore", {"tech": 0.10}, "Colpisci, e non smetti di colpire."),
        ("Carne che Ricresce", {"proc": ("rigenerazione", 0.10, 1.3)}, "Le ferite si chiudono mentre combatti."),
        ("Mille Anni in Più", {"life": 120}, "Il tempo ti passa accanto."),
        ("Goccia di Sangue Immortale", {"saves": 1, "taken": 0.06}, "Basta una goccia per tornare."),
        ("Corpo che Sfida il Tempo", {"tech": 0.18}, "Un colpo che il tempo non sa fermare."),
        ("Corpo Immortale Compiuto", {"saves": 1, "proc": ("rigenerazione", 0.15, 1.6)}, "Neanche il Cielo sa come ucciderti."),
    ],
    "fenice_nirvana": [
        ("Ali di Fiamma della Fenice", {"tech": 0.10}, "Ali di fuoco si aprono alle tue spalle."),
        ("Cenere Viva", {"proc": ("ustione", 0.08, 1.2)}, "Dove passi resta brace."),
        ("Canto della Fenice", {"cult": 0.08}, "Ogni alba ti rinnova."),
        ("Nirvana", {"saves": 1, "atk": 0.08}, "Muori nel fuoco, rinasci più forte."),
        ("Fenice che Brucia i Nove Cieli", {"tech": 0.18}, "Un volo di fiamme che attraversa il cielo."),
        ("Nirvana Compiuto", {"saves": 1, "strikes": 1}, "Ogni morte è solo un'altra alba."),
    ],
    "anima_celeste": [
        ("Spada dell'Anima", {"tech": 0.12}, "Una spada che ferisce l'anima, non il corpo."),
        ("Anima Vasta", {"chance": 0.05}, "Il senso divino copre la valle."),
        ("Pressione dell'Anima", {"proc": ("pressione", 0.10, 1.3)}, "Il nemico sente il peso del cielo."),
        ("Anima che Lascia il Corpo", {"evade": 0.08, "crit": 0.06}, "Combatti da due luoghi insieme."),
        ("Mille Spade dell'Anima", {"tech": 0.20}, "Mille spade invisibili, e nessuna manca."),
        ("Anima Celeste Compiuta", {"saves": 1, "taken": 0.06}, "Il corpo è un abito: l'anima non muore."),
    ],
}


def _key_stage(conn) -> tuple[str | None, int]:
    from engine.systems import constitutions
    c = constitutions.get(conn)
    return (c["key"], int(c.get("stage", 0))) if c else (None, 0)


def unlocked(key: str | None, stage: int) -> list[tuple[int, str, dict, str]]:
    """[(soglia, nome, effetti, racconto)] dei poteri già sbloccati, più le tecniche oltre il Corpo Compiuto."""
    if not key or key not in POWERS:
        return []
    out = [(m, *POWERS[key][i]) for i, m in enumerate(MILESTONES) if stage >= m]
    k = 1
    while stage >= COMPLETE + EVERY * k:                       # oltre il corpo compiuto: senza fine
        name, eff, _t = POWERS[key][0]
        out.append((COMPLETE + EVERY * k, f"{name} ({_ROMAN[k] if k < len(_ROMAN) else k + 1})",
                    {"tech": eff["tech"] * (1 + 0.5 * k)}, "La tecnica del corpo sale di grado."))
        k += 1
    return out


def next_power(key: str | None, stage: int) -> tuple[int, str] | None:
    if not key or key not in POWERS:
        return None
    for i, m in enumerate(MILESTONES):
        if stage < m:
            return m, POWERS[key][i][0]
    k = (stage - COMPLETE) // EVERY + 1
    return COMPLETE + EVERY * k, f"{POWERS[key][0][0]} ({_ROMAN[k] if k < len(_ROMAN) else k + 1})"


def on_stage(conn, key: str, before: int, after: int) -> list[str]:
    """Chiamato al risveglio: annuncia e concede i poteri delle soglie superate."""
    from engine.core import entities
    from engine.systems import lifespan
    new = []
    p = entities.get_player(conn)
    t = tick_mod.get_tick(conn)
    for i, (m, name, eff, tale) in enumerate(unlocked(key, after)):
        if m <= before:
            continue
        new.append((name, eff, tale))
        if eff.get("tech") and p is not None:
            conn.execute("INSERT OR IGNORE INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, "
                         "learned_tick) VALUES (?, NULL, ?, ?, ?, ?);",
                         (p.id, f"body:{key}:{i}", name, round(eff["tech"], 3), t))
        if eff.get("life"):
            lifespan.add_bonus_years(conn, int(eff["life"]))
        if m == COMPLETE and i == len(MILESTONES) - 1:
            state.grant_title(conn, f"{POWERS[key][-1][0]}")
    if len(new) == 1:
        name, eff, tale = new[0]
        return [f"  ✧ Nuovo potere del corpo: «{name}» — {tale}"
                + (f" (tecnica: +{int(100 * eff['tech'])}% potenza)" if eff.get("tech") else "")]
    if new:
        return ["  ✧ Nuovi poteri del corpo: " + ", ".join(f"«{n}»" for n, _e, _t in new)
                + ". ('corpo' per vederli)"]
    return []


def sync(conn) -> list[str]:
    """Concede (una volta sola) i poteri delle soglie raggiunte; anche per i salvataggi vecchi."""
    key, st = _key_stage(conn)
    mark = state.get(conn, "body_powers_mark") or ""
    mk, _, ms = mark.partition(":")
    last = int(ms) if (mk == key and ms.isdigit()) else 0
    if not key or st <= last:
        if mark != f"{key}:{st}" and key and st < last:
            state.set(conn, "body_powers_mark", f"{key}:{st}")
        return []
    state.set(conn, "body_powers_mark", f"{key}:{st}")
    return on_stage(conn, key, last, st)


def combat(conn, fx) -> list[str]:
    """Gli effetti passivi dei poteri sbloccati."""
    key, st = _key_stage(conn)
    pw = unlocked(key, st)
    if not pw:
        return []
    pr = fx.p.prof
    for _m, name, eff, _t in pw:
        for k in ("crit", "evade", "pierce", "taken"):
            if eff.get(k):
                pr[k] = pr.get(k, 0.0) + eff[k]
        if eff.get("atk"):
            fx.p.atk_mult *= 1.0 + eff["atk"]
        if eff.get("chance"):
            pr["chance_mult"] = pr.get("chance_mult", 1.0) * (1.0 + eff["chance"])
        if eff.get("strikes"):
            pr["extra_strikes"] = pr.get("extra_strikes", 0) + int(eff["strikes"])
        if eff.get("saves"):
            fx.p.lethal_saves += int(eff["saves"])
        if eff.get("proc"):
            s, ch, power = eff["proc"]
            fx.add_proc("p", s, ch, power, f"potere:{name}")
    return []


def cult_bonus(conn) -> float:
    key, st = _key_stage(conn)
    return sum(eff.get("cult", 0.0) for _m, _n, eff, _t in unlocked(key, st))


def describe(conn) -> list[str]:
    key, st = _key_stage(conn)
    if not key:
        return []
    pw = unlocked(key, st)
    out = []
    if pw:
        out.append("Poteri del corpo: " + ", ".join(n for _m, n, _e, _t in pw[-4:])
                   + (f" (e altri {len(pw) - 4})" if len(pw) > 4 else ""))
    nx = next_power(key, st)
    if nx:
        out.append(f"Prossimo potere allo stadio {nx[0]}: «{nx[1]}».")
    return out


def summary(conn) -> dict:
    key, st = _key_stage(conn)
    nx = next_power(key, st)
    return {"poteri": [{"nome": n, "stadio": m, "testo": t} for m, n, _e, t in unlocked(key, st)][-6:],
            "prossimo": {"stadio": nx[0], "nome": nx[1]} if nx else None}
