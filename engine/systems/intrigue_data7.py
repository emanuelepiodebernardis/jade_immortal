"""
TRE NUOVE SAGHE (Aggiornamento 74) — amore, orrore, potere.

Stesso formato di intrigue_data6 (capitoli legati da un segno, stessi personaggi, finali diversi), più i
due campi delle saghe (vedi sagas.py): «teaser» (il presagio a metà dell'attesa) e «memory» (come ti
ricorda il protagonista della saga, per esito).

  IL FILO ROSSO (dal 2° regno) — una spadaccina su un lago che non si scioglie mai, promessa a un altro.
    I   Il lago ghiacciato → Il nome del promesso → Il filo rosso: fuggite / lo smascheri / la lasci sposare
    II  Inseguiti (la taglia, la casa sul fiume) · La sposa avvelenata (la vendetta del promesso) ·
        La sposa del vecchio (troppo tardi?)
    III Le nozze (il patriarca del suo clan: forza, cuore o pietre — o il rifiuto)

  LA CITTÀ CHE DORME (dal 3° regno) — al tramonto tutti si addormentano dove sono, e sognano lo stesso sogno.
    I   Sonno al tramonto → Il tè del buon sonno → La Luna Rossa: bruci il loto / lo combatti in sogno / patto
    II  Quelli che non sognano più · Il Signore del Sogno · Il prezzo del loto

  IL TRONO DI GIADA (dal 2° regno, solo in una setta) — il patriarca muore avvelenato senza un erede.
    I   L'ultima tosse → La tazza → Il conclave: l'erede onesto / il gran anziano / il trono a te
    II  L'assedio (l'usurpatore torna con un esercito) · La lama dell'usurpatore · Il peso della corona
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}

TEMPLATES: list[dict] = [
    # ================================================================ IL FILO ROSSO — I
    {
        "key": "filo_rosso", "title": "Il Filo Rosso", "kind": "legame", "weight": 6, "tier_min": 2,
        "cast": {"amata": "genio@f", "promesso": "anziano@m"},
        "indagine": "istinto", "need": 1, "reveal_act": 1,
        "indizi": ["{promesso} ha già avuto tre spose. Tutte giovani, tutte dotate. Tutte morte entro un anno dalle nozze.",
                   "Le spose di {promesso} avevano radici Yin purissime: lui pratica un'arte che beve il Yin altrui."],
        "memory": {"fuga": "amato", "smascherato": "amato", "perduta": "abbandonato"},
        "acts": [
            {"title": "Il lago che non si scioglie", "focus": "amata", "gap": (1, 2),
             "text": ("Sopra {luogo} c'è un lago che non si scioglie mai, nemmeno d'estate. Ci sali per meditare "
                      "e trovi qualcuno che danza sul ghiaccio con una spada sottile come un filo d'acqua: una "
                      "giovane spadaccina dai capelli legati con un nastro rosso. Ogni passo lascia un fiore di "
                      "brina. All'ultimo giro il ghiaccio si spacca sotto i suoi piedi."),
             "choices": [
                 {"label": "Ti lanci e la afferri prima che cada",
                  "effects": {"relation": 20, "text": ("La tiri fuori dall'acqua nera per un polso. Lei tossisce, ride, e "
                                                       "ti punta la spada alla gola: «Ce l'avrei fatta da sola. Grazie lo "
                                                       "stesso. Mi chiamo {amata}.»"), "intrigue": {"branch": "salvata"}}},
                 {"label": "La sfidi: «Bella danza. Ma sa anche combattere?»",
                  "check": {"stat": "potenza", "dc": 50},
                  "success": {"relation": 15, "text": ("Incrociate le lame sul ghiaccio che geme. Quando la disarmi, invece "
                                                       "di arrabbiarsi ride forte. «Domani alla stessa ora. Voglio la "
                                                       "rivincita.» Si chiama {amata}."), "intrigue": {"branch": "duellato"}},
                  "failure": {"relation": 12, "text": ("Ti ritrovi seduto sul ghiaccio con la sua lama sotto il mento. "
                                                       "«Non male», dice {amata}. «Per uno che guarda le ragazze danzare.»"),
                              "intrigue": {"branch": "duellato"}}},
                 {"label": "Raccogli un fiore di brina e glielo lasci sulla riva",
                  "effects": {"relation": 10, "heart": 3,
                              "text": ("Te ne vai senza dire niente. Il giorno dopo il fiore è sparito, e al suo posto c'è "
                                       "un nastro rosso legato a un ramo. Ci sono ricamate due parole: «{amata}. Domani?»"),
                              "intrigue": {"branch": "fiore"}}},
             ]},
            {"title": "Il nome del promesso", "focus": "amata", "gap": (3, 5),
             "text": ("Vi vedete ogni giorno, per settimane. Una sera {amata} non danza: siede sul ghiaccio con le "
                      "ginocchia strette al petto. «Il mio clan mi ha promessa a {promesso». È un alleato di mio "
                      "padre. Ha il triplo dei miei anni.» Si sforza di sorridere. «Fra trenta giorni mi sposo.»"),
             "text_branch": {"salvata": ("Una sera {amata} non danza. Ti mostra il polso dove l'hai afferrata il primo "
                                         "giorno: c'è ancora il segno. «Mi hai tirata fuori dall'acqua una volta. Non "
                                         "puoi farlo di nuovo.» Il suo clan l'ha promessa a {promesso}, che ha il triplo "
                                         "dei suoi anni. Fra trenta giorni si sposa."),
                             "duellato": ("Una sera {amata} arriva senza spada. «Niente rivincita, oggi.» Il suo clan l'ha "
                                          "promessa a {promesso}, un vecchio alleato di suo padre. «Il giorno delle nozze "
                                          "dovrò posare la spada per sempre. Così vuole lui.»")},
             "choices": [
                 {"label": "«Troverò un modo. Te lo prometto»",
                  "effects": {"relation": 20, "heart": 3, "text": "Ti guarda a lungo. «Non promettere cose che non puoi mantenere.» Ma ti stringe la mano.",
                              "intrigue": {"branch": "promessa"}}},
                 {"label": "Indaghi su {promesso}",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": ("Tre spose prima di lei. Tre tombe nel giardino di {promesso}, tutte giovani, tutte "
                                       "dotate. Un vecchio servo trema quando glielo chiedi."), "intrigue": {"clue": 1, "branch": "segreto"}},
                  "failure": {"text": "Le porte della casa di {promesso} restano chiuse. Nessuno parla.", "intrigue": {}}},
                 {"label": "«Il dovere verso il clan viene prima»",
                  "effects": {"relation": -20, "text": "«Lo so», dice piano. «Volevo solo sentirlo dire da qualcun altro.»",
                              "intrigue": {"branch": "dovere"}}},
             ]},
            {"title": "Il filo rosso", "focus": "amata", "gap": (2, 3),
             "text": ("La notte prima delle nozze qualcuno bussa alla tua finestra. È {amata}, col vestito da sposa "
                      "sotto il mantello e un filo rosso tra le dita. «Dicono che il Vecchio della Luna leghi con un "
                      "filo rosso chi è destinato a incontrarsi. Io il mio l'ho comprato al mercato.» Ti tende un capo. "
                      "«Se lo leghi, partiamo stanotte. Se no, domani mi sposo e non mi vedrai più.»"),
             "choices": [
                 {"label": "Leghi il filo al tuo polso: partite stanotte",
                  "effects": {"bond": "dao_partner", "relation": 40, "heart": 10, "infamy": 4,
                              "text": ("Il filo è corto: per tenerlo dovete camminare vicini. All'alba siete già due "
                                       "valli lontano, e dietro di voi le campane del clan suonano a martello."),
                              "intrigue": {"flag": "filo_fuga", "end": "fuga"}}},
                 {"label": "Porti le prove al clan, davanti a tutti", "need_clues": 1,
                  "effects": {"bond": "dao_partner", "relation": 40, "fame": 12, "karma": 15,
                              "text": ("Il giorno delle nozze, davanti a tutto il clan, metti sul tavolo i nomi delle tre "
                                       "spose morte. Il padre di {amata} impallidisce. {promesso} se ne va senza una parola, "
                                       "ma prima di uscire ti guarda: è uno sguardo che non si dimentica."),
                              "intrigue": {"flag": "filo_clan", "end": "smascherato"}}},
                 {"label": "Lasci il filo sul davanzale",
                  "effects": {"relation": -50, "heart": -5,
                              "text": ("Lei aspetta. Poi raccoglie il filo e se lo avvolge al dito, giro dopo giro, finché "
                                       "non diventa bianco. «Va bene», dice. Il giorno dopo senti le campane delle nozze."),
                              "intrigue": {"flag": "filo_perduto", "end": "perduta"}}},
             ]},
        ],
        "auto_end": [{"outcome": "sposata", "text": "{amata} si è sposata con {promesso}. Il lago, quest'anno, non è gelato."}],
        "outcomes": {"fuga": "Sei fuggito con {amata}, legati da un filo rosso.",
                     "smascherato": "Hai smascherato {promesso}: {amata} è libera, e ha scelto te.",
                     "perduta": "Hai lasciato che {amata} sposasse {promesso}.",
                     "sposata": "{amata} si è sposata senza di te."},
    },
    # ---------------------------------------------------------------- II · fuggiaschi
    {
        "key": "filo_inseguiti", "title": "Il Filo Rosso — Inseguiti", "kind": "legame", "weight": 6, "tier_min": 2,
        "req_flag": "filo_fuga", "delay": 18, "cast": {"amata": "legame:filo_fuga", "cacciatore": "anziano"},
        "teaser": ("Ai crocevia compaiono avvisi col volto di {amata}: il suo clan offre una taglia. Lei ci ride sopra, ma "
                   "dorme con la spada sotto il cuscino."),
        "memory": {"ritorno": "amato", "rifugio": "amato"},
        "acts": [
            {"title": "La taglia", "focus": "cacciatore", "gap": (1, 2),
             "text": ("Alla locanda di {luogo} l'oste vi guarda troppo a lungo. Prima di sera arriva {cacciatore}, un "
                      "cacciatore di taglie del clan di {amata}, con una catena d'argento. «La ragazza viene con me. "
                      "Tu puoi andartene vivo, se ti sbrighi.»"),
             "choices": [
                 {"label": "Ti metti tra lui e lei", "effects": {"intrigue": {"branch": "difesa"}},
                  "command": "duello {cacciatore}"},
                 {"label": "Fuggite dalla finestra e fate perdere le tracce",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Camminate nel fiume per mezza notte. All'alba lui cerca ancora sulla riva sbagliata.",
                              "intrigue": {"clue": 1, "branch": "nascosti"}},
                  "failure": {"injury": 1, "text": "La catena ti prende alla caviglia. Ve la cavate, ma lui ora sa dove andate.",
                              "intrigue": {}}},
                 {"label": "Lo paghi per tornare a mani vuote (1500 pietre)",
                  "effects": {"stones": -1500, "text": "Conta le pietre due volte. «Non vi ho mai visti.» Ma tornerà a contarne altre.",
                              "intrigue": {"branch": "pagato"}}},
             ]},
            {"title": "La casa sul fiume", "focus": "amata", "gap": (3, 5),
             "text": ("Trovate una casa abbandonata su un'ansa del fiume, dove nessuno passa. {amata} la sistema in tre "
                      "giorni: tende di bambù, un fornello, un ramo di pruno nel vaso. La sera, sul pontile, ti chiede: "
                      "«Potremmo restare qui per sempre. Oppure tornare e guardare in faccia mio padre. Scappare stanca, "
                      "lo sai?»"),
             "choices": [
                 {"label": "«Torniamo. Gli chiederò la tua mano come si deve»",
                  "effects": {"relation": 20, "heart": 6, "text": "Ti bacia la fronte. «Sei più matto di me.» Partite all'alba.",
                              "intrigue": {"flag": "filo_ritorno", "end": "ritorno"}}},
                 {"label": "«Restiamo. Il mondo può fare a meno di noi»",
                  "effects": {"relation": 30, "heart": 12, "lifespan_years": 10, "prize": _ARGENTO,
                              "title": "Eremita del Filo Rosso",
                              "text": ("Gli anni passano lenti come il fiume. Coltivate insieme, all'alba, sul pontile. "
                                       "Nessuno vi cerca più. Qualche volta te ne vai per un'avventura; torni sempre."),
                              "intrigue": {"end": "rifugio"}}},
             ]},
        ],
        "auto_end": [{"outcome": "presi", "text": "Il clan ha ritrovato {amata} e l'ha riportata a casa."}],
        "outcomes": {"ritorno": "Tu e {amata} tornate dal suo clan, a testa alta.",
                     "rifugio": "Tu e {amata} vivete nella casa sul fiume.",
                     "presi": "Il clan ha ripreso {amata}."},
    },
    # ---------------------------------------------------------------- II · la vendetta del promesso
    {
        "key": "filo_veleno", "title": "Il Filo Rosso — La sposa avvelenata", "kind": "vendetta", "weight": 6,
        "tier_min": 2, "req_flag": "filo_clan", "delay": 25,
        "cast": {"amata": "legame:filo_clan", "promesso": "legame:filo_clan"},
        "teaser": ("Dicono che {promesso} sia sparito dalla sua casa il giorno dopo lo scandalo. Qualcuno l'ha visto al "
                   "mercato nero, a comprare veleni freddi."),
        "memory": {"guarita": "amato", "cara": "amato", "cicatrice": "amato"},
        "acts": [
            {"title": "Il gelo nelle vene", "focus": "amata", "gap": (1, 2),
             "text": ("Una mattina {amata} non si sveglia. Ha le labbra blu e la pelle fredda come il suo lago, e sul "
                      "cuscino c'è un fiore di brina che non ha fatto lei. È un veleno Yin, lento: chi l'ha preparato "
                      "voleva che tu la guardassi morire."),
             "choices": [
                 {"label": "Cerchi l'antidoto nella Valle delle Mille Erbe",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": ("Tra mille erbe trovi l'unica che cresce sulla neve: il Loto di Fuoco Rovesciato. "
                                       "Il mercante che te la vende ha visto passare {promesso}, due giorni fa."),
                              "intrigue": {"clue": 1, "branch": "erba"}},
                  "failure": {"injury": 1, "text": "La valle è piena di erbe che uccidono. Torni a mani vuote e avvelenato a tua volta.",
                              "intrigue": {}}},
                 {"label": "Le dai il tuo qi, ogni notte, per tenerla in vita",
                  "effects": {"lifespan_years": -5, "heart": 8, "relation": 25,
                              "text": ("Ogni notte le passi un filo del tuo qi. Ogni mattina sei un po' più vecchio. "
                                       "Lei, nel sonno, ti stringe la mano."),
                              "intrigue": {"branch": "qi"}}},
             ]},
            {"title": "Il covo del veleno", "focus": "promesso", "gap": (2, 3),
             "text": ("Trovi {promesso} in una villa di montagna, tra alambicchi e vasi di neve. Non scappa. «Tre spose mi "
                      "hanno dato trent'anni di vita. Lei me ne avrebbe dati dieci. Tu me li hai rubati.» Indica una "
                      "fiala sul tavolo. «L'antidoto. Prendilo, se ci riesci.»"),
             "choices": [
                 {"label": "Lo affronti", "effects": {"intrigue": {"clue": 1}}, "command": "duello {promesso}"},
                 {"label": "Gli fai bere il suo stesso veleno", "need_branch": "erba",
                  "effects": {"karma": -5, "text": ("Il Loto Rovesciato brucia il veleno freddo: glielo sciogli nel vino. "
                                                    "Beve per sfida, e capisce troppo tardi. Muore com'è vissuto: gelido."),
                              "intrigue": {"clue": 1, "branch": "giustizia"}}},
                 {"label": "Prendi la fiala e corri",
                  "check": {"stat": "istinto", "dc": 56},
                  "success": {"text": "Afferri la fiala e salti dalla finestra. Lui non ti insegue: ride.", "intrigue": {"branch": "fiala"}},
                  "failure": {"injury": 2, "text": "La fiala era falsa. Quella vera l'ha bevuta lui, ridendo.", "intrigue": {}}},
             ]},
            {"title": "Il risveglio", "auto": True,
             "text": "Torni da lei di corsa. La stanza è fredda. Poi, piano, il ghiaccio sul davanzale comincia a sciogliersi.",
             "endings": [
                 {"need_clues": 2, "outcome": "guarita",
                  "effects": {"heart": 15, "karma": 15, "prize": _ORO, "title": "Compagno del Filo Rosso"},
                  "text": ("{amata} apre gli occhi e la prima cosa che dice è: «Hai una faccia orribile.» Poi piange. Il "
                           "veleno se n'è andato, e con lui {promesso}. Quell'inverno il suo lago gela di nuovo.")},
                 {"need_branch": "qi", "outcome": "cara",
                  "effects": {"heart": 10, "lifespan_years": 5},
                  "text": ("Il tuo qi l'ha tenuta in vita abbastanza a lungo. Si sveglia debole, ma si sveglia. «Ti ho "
                           "sentito, ogni notte», dice. «Ti devo cinque anni. Te li restituirò, uno alla volta.»")},
                 {"outcome": "cicatrice", "effects": {"heart": -5},
                  "text": ("Sopravvive, ma il veleno le ha bruciato metà delle radici. Non danzerà più sul ghiaccio. "
                           "«Non importa», mente. Lo sapete tutti e due.")},
             ]},
        ],
        "auto_end": [{"outcome": "spenta", "text": "Il veleno ha fatto il suo corso."}],
        "outcomes": {"duello_vinto": "Hai battuto {promesso} nel suo covo.", "duello_perso": "{promesso} ti ha battuto nel suo covo.",
                     "duello_fuga": "Sei fuggito dal covo di {promesso}.", "spenta": "{amata} non si è più svegliata."},
    },
    # ---------------------------------------------------------------- II · troppo tardi?
    {
        "key": "filo_sposa", "title": "Il Filo Rosso — La sposa del vecchio", "kind": "legame", "weight": 6,
        "tier_min": 2, "req_flag": "filo_perduto", "delay": 30,
        "cast": {"amata": "legame:filo_perduto", "promesso": "legame:filo_perduto"},
        "teaser": ("Al mercato vendono ventagli dipinti con una sposa triste su un lago gelato. La pittrice non firma, ma "
                   "sul manico c'è sempre un filo rosso."),
        "memory": {"riscatto_vinto": "amato", "addio": "amato", "rimpianto": "abbandonato"},
        "acts": [
            {"title": "La sposa del vecchio", "focus": "amata", "gap": (1, 2),
             "text": ("La rivedi al tempio, accanto a {promesso}. È pallida, sottile, con le mani fredde: l'arte del marito "
                      "le sta bevendo il Yin, un sorso al giorno. Quando lui si allontana, {amata} non ti chiede niente. "
                      "«È stata una mia scelta», dice. «E anche tua.» Al dito ha ancora il filo rosso, bianco di nodi."),
             "choices": [
                 {"label": "«Questa volta resto.» Sfidi {promesso}", "effects": {"intrigue": {"end": "riscatto"}},
                  "command": "duello {promesso}"},
                 {"label": "Le lasci un passaggio sicuro e cento pietre, senza chiedere nulla",
                  "effects": {"stones": -100, "relation": 30, "heart": 6,
                              "text": ("Una settimana dopo il tempio dice che la sposa di {promesso} è fuggita da sola, "
                                       "di notte, a piedi nudi sul ghiaccio. Non ha lasciato biglietti. Solo un nastro rosso "
                                       "sul tuo cancello."),
                              "intrigue": {"end": "addio"}}},
                 {"label": "Ti volti e te ne vai",
                  "effects": {"karma": -5, "heart": -8, "text": "Non ti chiama. Non si chiama chi se n'è già andato due volte.",
                              "intrigue": {"end": "rimpianto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "svanita", "text": "La sposa di {promesso} si è spenta in silenzio."}],
        "outcomes": {"riscatto_vinto": "Hai battuto {promesso} e hai riportato via {amata}. In ritardo, ma l'hai fatto.",
                     "riscatto_perso": "{promesso} ti ha battuto davanti a lei.",
                     "riscatto_fuga": "Sei fuggito dal duello con {promesso}.",
                     "addio": "{amata} è fuggita da sola. Ti ha lasciato un nastro rosso.",
                     "rimpianto": "Te ne sei andato.", "svanita": "{amata} si è spenta."},
    },
    # ---------------------------------------------------------------- III · le nozze
    {
        "key": "filo_nozze", "title": "Il Filo Rosso — Le nozze", "kind": "legame", "weight": 7, "tier_min": 3,
        "req_flag": "filo_ritorno", "delay": 20, "cast": {"amata": "legame:filo_ritorno", "padre": "anziano@m"},
        "teaser": "Una colomba porta un biglietto con la grafia di {amata}: «Mio padre ha accettato di vederti. Non dire niente di stupido.»",
        "memory": {"nozze": "amato", "nozze_forza": "amato", "nozze_dono": "amato", "rifiuto": "amato"},
        "acts": [
            {"title": "Il patriarca del clan", "focus": "padre", "gap": (1, 2),
             "text": ("Il padre di {amata}, {padre}, ti riceve nella sala degli antenati, seduto sotto cento tavolette "
                      "col nome dei morti. Non ti offre il tè. «Mi hai rubato una figlia e un'alleanza. Dimmi perché "
                      "non dovrei scriverti su una di queste tavolette.» {amata}, dietro di te, trattiene il fiato."),
             "choices": [
                 {"label": "Gli offri una prova di forza", "check": {"stat": "potenza", "dc": 60},
                  "success": {"text": "Lo scambio dura un respiro. Lui abbassa la spada per primo: «Almeno sai proteggerla.»",
                              "intrigue": {"branch": "forza"}},
                  "failure": {"injury": 1, "text": "Ti mette in ginocchio in tre mosse. «Forte non basta.»", "intrigue": {}}},
                 {"label": "Gli parli col cuore, senza abbassare gli occhi", "check": {"stat": "anima", "dc": 56},
                  "success": {"text": ("Gli racconti del lago, della brina, del filo comprato al mercato. Quando finisci, "
                                       "il vecchio guarda la figlia come non la guardava da anni."),
                              "intrigue": {"branch": "cuore"}},
                  "failure": {"text": "Le parole ti si incastrano. Lui aspetta, gelido, che tu finisca.", "intrigue": {}}},
                 {"label": "Gli offri un dono di nozze degno del clan (3000 pietre)",
                  "effects": {"stones": -3000, "text": "Fa portare via le pietre senza guardarle. «Le alleanze si comprano. Le figlie no.»",
                              "intrigue": {"branch": "dono"}}},
             ]},
            {"title": "Le nozze", "auto": True,
             "text": "Il patriarca resta in silenzio a lungo. Poi si alza, e tutte le tavolette degli antenati sembrano guardarti.",
             "endings": [
                 {"need_branch": "cuore", "outcome": "nozze",
                  "effects": {"prize": _ORO, "heart": 15, "lifespan_years": 20, "fame": 10, "title": "Legato dal Filo Rosso"},
                  "text": ("«Mia figlia ha scelto bene», dice, e a {amata} tremano le spalle. Le nozze durano tre giorni. "
                           "Il quarto, all'alba, il lago sopra il clan gela per la prima volta dopo anni.")},
                 {"need_branch": "forza", "outcome": "nozze_forza",
                  "effects": {"prize": _ARGENTO, "heart": 10, "fame": 8, "title": "Legato dal Filo Rosso"},
                  "text": "«Proteggila meglio di come hai protetto il mio orgoglio.» È un sì. Il più burbero della storia."},
                 {"need_branch": "dono", "outcome": "nozze_dono",
                  "effects": {"heart": 5, "fame": 4},
                  "text": ("Il patriarca accetta. {amata} sorride, ma per tutta la cerimonia non ti guarda: le figlie non "
                           "si comprano, ha detto suo padre. Ci vorrà tempo.")},
                 {"outcome": "rifiuto", "effects": {"heart": 6, "infamy": 3},
                  "text": ("«No.» {amata} si alza, si toglie il sigillo del clan dalla cintura e lo posa davanti al padre. "
                           "«Allora non ho più un clan.» Uscite insieme. Nessuno vi ferma.")},
             ]},
        ],
        "auto_end": [{"outcome": "rimandate", "text": "Non sei andato all'incontro. {amata} è tornata dal clan da sola."}],
        "outcomes": {"rimandate": "Le nozze sono rimandate."},
    },

    # ================================================================ LA CITTÀ CHE DORME — I
    {
        "key": "citta_dorme", "title": "La Città che Dorme", "kind": "mistero", "weight": 6, "tier_min": 3,
        "cast": {"sognatrice": "spettro@f", "medico": "anziano"},
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["Tutti in città sognano la stessa strada sotto una luna rossa. E ogni notte, in sogno, la strada è più lunga.",
                   "Il «tè del buon sonno» di {medico} contiene polline di Loto Divoratore di Sogni.",
                   "Sotto la piazza c'è un loto grande come una casa: si nutre dei sogni, e chi ci sogna dentro invecchia."],
        "memory": {"bruciato": "salvato", "dentro": "salvato"},
        "acts": [
            {"title": "Sonno al tramonto", "focus": "sognatrice", "gap": (1, 2),
             "text": ("Arrivi a una città vicina a {luogo} quando il sole tocca i tetti. In un attimo, tutti si "
                      "addormentano dove sono: il fornaio sulla pagnotta, la guardia in piedi contro il muro, i bambini "
                      "sui gradini. Il silenzio è totale. Solo una vecchia cieca, seduta sulla soglia del tempio, è "
                      "sveglia. «Benvenuto», dice {sognatrice}. «Io non dormo da quarant'anni. Tu, stanotte, starai attento.»"),
             "choices": [
                 {"label": "Resti sveglio tutta la notte a guardare",
                  "check": {"stat": "anima", "dc": 56},
                  "success": {"text": ("Verso mezzanotte, dalle bocche dei dormienti sale un filo di nebbia. Tutti i fili "
                                       "vanno nella stessa direzione: la piazza."), "intrigue": {"clue": 1}},
                  "failure": {"text": "Ti svegli all'alba sul selciato. Non ricordi di esserti addormentato.", "intrigue": {}}},
                 {"label": "Ti lasci addormentare per vedere il sogno",
                  "effects": {"lifespan_years": -1,
                              "text": ("Sogni una strada sotto una luna rossa. Tutta la città cammina in fila verso un "
                                       "punto che non vedi. Qualcuno ti prende la mano: è {sognatrice}, che in sogno ha "
                                       "vent'anni e ci vede benissimo."), "intrigue": {"clue": 1, "branch": "sognato"}}},
                 {"label": "Cerchi il medico della città (100 pietre per un consulto)",
                  "effects": {"stones": -100, "text": ("{medico} ti sorride troppo. «È il clima. Bevete il mio tè del buon "
                                                       "sonno e non ci penserete più.» Te ne dà una scatola, gratis.")}},
             ]},
            {"title": "Il tè del buon sonno", "focus": "medico", "gap": (2, 3),
             "text": ("Tutta la città beve il tè di {medico}. Le persone sono più pallide ogni giorno, e più felici: dicono "
                      "di fare sogni bellissimi. {medico}, invece, sembra ringiovanire."),
             "choices": [
                 {"label": "Analizzi il tè col tuo qi", "check": {"stat": "qi", "dc": 58},
                  "success": {"text": "Polline. Un polline che brilla al buio e che non viene da nessun fiore di questo mondo.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Sa di camomilla e di qualcosa che non riconosci.", "intrigue": {}}},
                 {"label": "Bevi il tè anche tu, per scendere più a fondo nel sogno",
                  "effects": {"lifespan_years": -2, "text": ("Stavolta il sogno è più profondo: arrivi in fondo alla strada. C'è un "
                                                             "fiore enorme, rosa, che respira. Sotto i petali, mille volti addormentati."),
                              "intrigue": {"clue": 1, "branch": "bevuto"}}},
                 {"label": "Affronti {medico}", "effects": {"intrigue": {"clue": 1}}, "command": "duello {medico}"},
             ]},
            {"title": "La Luna Rossa", "focus": "sognatrice", "gap": (2, 3),
             "text": ("Sotto la piazza, nelle vecchie cisterne, c'è il Loto Divoratore di Sogni: grande come una casa, rosa "
                      "come una ferita, e respira al ritmo della città che dorme. {sognatrice} ti ha guidato fin qui. «Io "
                      "sono stata la prima», dice. «Quarant'anni fa il loto mi ha preso tutti i sogni, e da allora non ho "
                      "più dormito. Fermalo. Come vuoi. Ma fermalo.»"),
             "text_low": ("Nelle cisterne sotto la piazza qualcosa respira. {sognatrice} ti tira per una manica: «È qui sotto. "
                          "Non sai ancora abbastanza, ma è qui sotto.»"),
             "choices": [
                 {"label": "Bruci il loto con il fuoco del tuo qi", "need_clues": 2,
                  "effects": {"fame": 15, "karma": 20, "prize": _ARGENTO,
                              "text": ("Il loto urla con mille voci. Quando si spegne, la città si sveglia tutta insieme, "
                                       "a mezzanotte, come da un incubo. Ma la mattina dopo, a colazione, nessuno racconta "
                                       "i propri sogni. Nessuno ne ha fatti."),
                              "intrigue": {"flag": "citta_vuoti", "end": "bruciato"}}},
                 {"label": "Entri nel sogno e lo combatti da dentro", "need_branch": "sognato",
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"karma": 15, "fame": 10,
                              "text": ("Nel sogno il loto è un gigante di petali. Lo abbatti con una spada fatta di veglia. "
                                       "Ti svegli, e la città è salva. Ma il cuore del loto, nel sogno, ti è entrato in petto."),
                              "intrigue": {"flag": "citta_sognatore", "end": "dentro"}},
                  "failure": {"lifespan_years": -5,
                              "text": ("Il loto ti stringe nel sogno per tre giorni. Ti sveglia {sognatrice}, a schiaffi. Il "
                                       "loto è ferito. E un suo seme ti è rimasto dentro."),
                              "intrigue": {"flag": "citta_sognatore", "end": "intrappolato"}}},
                 {"label": "Ascolti cosa ti offre il loto",
                  "effects": {"bt_bonus": 0.05, "karma": -20,
                              "text": ("Il loto ti mostra un sogno: il tuo prossimo sfondamento, perfetto. «Lascia la città "
                                       "a me, e questo sogno è tuo.» Ti svegli con il sapore del potere in bocca."),
                              "intrigue": {"flag": "citta_patto", "end": "patto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "dormiente", "text": "La città dorme ancora. Ogni notte un po' di più."}],
        "outcomes": {"bruciato": "Hai bruciato il Loto Divoratore di Sogni.",
                     "dentro": "Hai sconfitto il loto dentro il sogno.", "intrappolato": "Il loto ti ha tenuto prigioniero nel sogno.",
                     "patto": "Hai fatto un patto col Loto Divoratore di Sogni.",
                     "duello_vinto": "Hai battuto il medico.", "duello_perso": "Il medico ti ha respinto.",
                     "dormiente": "La città continua a dormire."},
    },
    {
        "key": "citta_vuoti", "title": "La Città che Dorme — Quelli che non sognano più", "kind": "mistero", "weight": 6,
        "tier_min": 3, "req_flag": "citta_vuoti", "delay": 20, "cast": {"sognatrice": "legame:citta_vuoti"},
        "teaser": "Un mercante racconta di una città dove nessuno ride più. «Non sono tristi», dice. «Sono vuoti.»",
        "memory": {"dono": "salvato", "seme": "salvato"},
        "acts": [
            {"title": "La città vuota", "focus": "sognatrice", "gap": (1, 2),
             "text": ("Torni in città. Nessuno dorme più al tramonto, ma nessuno fa più niente: il fornaio fissa il "
                      "forno spento, i bambini non giocano. Senza sogni non c'è desiderio, e senza desiderio non c'è "
                      "domani. {sognatrice} ti aspetta sulla soglia del tempio. «Un sogno si può solo regalare. Da chi ne "
                      "ha uno da parte.»"),
             "choices": [
                 {"label": "Regali i tuoi sogni alla città",
                  "effects": {"karma": 30, "heart": -6, "lifespan_years": -3, "fame": 15,
                              "title": "Colui che Diede i Suoi Sogni",
                              "text": ("Ti siedi in piazza e apri il tuo sonno a tutti. Quella notte la città sogna i tuoi "
                                       "sogni: il fiume dell'infanzia, la prima spada, chi hai amato. Tu, da allora, "
                                       "dormi senza sognare. La città ride di nuovo."),
                              "intrigue": {"end": "dono"}}},
                 {"label": "Cerchi un seme del loto e lo ripianti, addomesticato",
                  "check": {"stat": "istinto", "dc": 60},
                  "success": {"karma": 10, "prize": _ARGENTO,
                              "text": ("Nella cenere della cisterna trovi un seme ancora caldo. Lo pianti nel giardino del "
                                       "tempio, e {sognatrice} giura di vegliarlo. Un loto piccolo, che prende un sogno "
                                       "per notte e ne restituisce due."), "intrigue": {"end": "seme"}},
                  "failure": {"text": "La cenere è fredda. Del loto non è rimasto niente.", "intrigue": {}}},
                 {"label": "Te ne vai: hai già fatto abbastanza",
                  "effects": {"karma": -10, "text": "La città vuota ti guarda andare senza chiederti niente.",
                              "intrigue": {"end": "abbandonata"}}},
             ]},
        ],
        "auto_end": [{"outcome": "spenta", "text": "La città vuota si è spenta, una casa alla volta."}],
        "outcomes": {"dono": "Hai regalato i tuoi sogni a una città.", "seme": "Hai piantato un loto buono.",
                     "abbandonata": "Hai lasciato la città vuota.", "spenta": "La città vuota si è spenta."},
    },
    {
        "key": "citta_signore", "title": "La Città che Dorme — Il Signore del Sogno", "kind": "mistero", "weight": 6,
        "tier_min": 3, "req_flag": "citta_sognatore", "delay": 25, "cast": {"sognatrice": "legame:citta_sognatore"},
        "teaser": "Stanotte hai sognato il sogno di un altro: una donna che cercava un figlio in un mercato. Ti sei svegliato col suo nome in bocca.",
        "memory": {"risveglio": "salvato", "signore": "maestro"},
        "acts": [
            {"title": "I sogni degli altri", "focus": "sognatrice", "gap": (1, 2),
             "text": ("Il cuore del loto ti è rimasto dentro. Di notte cammini nei sogni degli altri: vedi le loro paure, "
                      "i loro segreti, i loro desideri. Potresti cambiarli. Potresti comandarli. {sognatrice} lo capisce "
                      "subito: «Ce l'hai negli occhi. Puoi diventare il nuovo loto, oppure lasciarmi spegnerlo. Con me "
                      "dentro, se serve.»"),
             "choices": [
                 {"label": "Diventi il Signore del Sogno",
                  "effects": {"bt_bonus": 0.08, "karma": -15, "title": "Signore del Sogno",
                              "text": ("Da quella notte nessun sogno ti è chiuso. Sai ciò che i tuoi nemici temono prima "
                                       "che lo sappiano loro. {sognatrice} non ti saluta più."),
                              "intrigue": {"end": "signore"}}},
                 {"label": "Lasci che {sognatrice} lo spenga", "check": {"stat": "anima", "dc": 64},
                  "success": {"heart": 15, "karma": 20, "prize": _ORO,
                              "text": ("Lei ti posa le mani sugli occhi e canta una ninnananna di quarant'anni fa. Il cuore "
                                       "del loto si spegne. Quella notte dormi come un bambino; e anche lei, per la prima volta, dorme."),
                              "intrigue": {"end": "risveglio"}},
                  "failure": {"lifespan_years": -5,
                              "text": "Il cuore del loto resiste. Lo spegne lo stesso, ma ti porta via qualcosa: non dormi più.",
                              "intrigue": {"end": "insonne"}}},
             ]},
        ],
        "auto_end": [{"outcome": "cresciuto", "text": "Il cuore del loto è cresciuto dentro di te."}],
        "outcomes": {"signore": "Sei il Signore del Sogno.", "risveglio": "Il cuore del loto si è spento.",
                     "insonne": "Non dormi più.", "cresciuto": "Il loto cresce in te."},
    },
    {
        "key": "citta_prezzo", "title": "La Città che Dorme — Il prezzo del loto", "kind": "mistero", "weight": 6,
        "tier_min": 3, "req_flag": "citta_patto", "delay": 20, "cast": {"sognatrice": "legame:citta_patto"},
        "teaser": "Il tuo sfondamento sognato è ancora lì, ogni notte, perfetto. Ma da qualche giorno, alla fine del sogno, c'è un conto da pagare.",
        "acts": [
            {"title": "Il conto", "focus": "sognatrice", "gap": (1, 2),
             "text": ("Il loto torna a trovarti in sogno. «Ho bisogno di un'altra città. Più grande. {luogo}, per esempio. "
                      "Tu porta il tè, al resto penso io.» Ti svegli e trovi {sognatrice} seduta sul tuo letto. Non vede, "
                      "ma sa. «Puoi ancora tradirlo», dice. «I patti col loto si rompono solo da dentro.»"),
             "choices": [
                 {"label": "Porti il tè a {luogo}",
                  "effects": {"stones": 3000, "infamy": 10, "karma": -40, "bt_bonus": 0.06, "title": "Pastore di Sogni",
                              "text": "Una città intera dorme per te. I suoi sogni ti fanno più forte. Non pensarci.",
                              "intrigue": {"end": "pagato"}}},
                 {"label": "Torni nel sogno e tradisci il loto", "check": {"stat": "anima", "dc": 64},
                  "success": {"karma": 30, "heart": 10, "fame": 10, "prize": _ORO,
                              "text": ("Entri nel sogno come suo alleato, e lo colpisci al cuore dall'interno. Il loto muore "
                                       "senza capire. Il tuo sogno di potere svanisce con lui. Non ti manca."),
                              "intrigue": {"end": "tradito_loto"}},
                  "failure": {"inner_demon": True,
                              "text": "Il loto ti scopre. Muore, ma il suo ultimo sogno ti resta dentro: un demone del cuore.",
                              "intrigue": {"end": "incubo"}}},
             ]},
        ],
        "auto_end": [{"outcome": "riscosso", "effects": {"lifespan_years": -5}, "text": "Il loto si è preso il suo pagamento da te."}],
        "outcomes": {"pagato": "Hai pagato il loto con una città.", "tradito_loto": "Hai tradito il loto, e l'hai ucciso.",
                     "incubo": "Il loto è morto, ma il suo incubo vive in te.", "riscosso": "Il loto ha riscosso."},
    },

    # ================================================================ IL TRONO DI GIADA — I
    {
        "key": "trono_giada", "title": "Il Trono di Giada", "kind": "corte", "weight": 6, "tier_min": 2, "req_sect": True,
        "cast": {"usurpatore": "anziano", "erede": "genio", "patriarca": "anziano"},
        "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["Il patriarca beve ogni sera dalla stessa tazza di giada: ha l'orlo annerito.",
                   "Il servo che lava la tazza è stato assunto da {usurpatore} tre mesi fa.",
                   "{usurpatore} ha già fatto scolpire il proprio nome su una tavoletta da patriarca. La tiene sotto il letto."],
        "memory": {"erede_patriarca": "erede:salvato", "tuo": "erede:abbandonato", "usurpatore_patriarca": "erede:abbandonato"},
        "acts": [
            {"title": "L'ultima tosse", "focus": "patriarca", "gap": (1, 2),
             "text": ("Il patriarca {della_mia_setta}, {patriarca}, tossisce sangue da una settimana e non ha nominato un "
                      "erede. Nei corridoi tutti parlano a bassa voce di due nomi: {erede}, il discepolo più dotato della "
                      "generazione, onesto fino all'ingenuità; e {usurpatore}, il gran anziano, che controlla il tesoro "
                      "e metà degli anziani. Il patriarca ti fa chiamare. Ma quando arrivi, dorme."),
             "choices": [
                 {"label": "Vegli il patriarca fino all'alba", "check": {"stat": "anima", "dc": 54},
                  "success": {"text": "Nel delirio ti afferra il polso: «La tazza… non lasciare… la tazza…»", "intrigue": {"clue": 1}},
                  "failure": {"text": "Dorme tutta la notte. Al mattino non ti riconosce.", "intrigue": {}}},
                 {"label": "Prometti il tuo appoggio a {erede}",
                  "effects": {"relation": 20, "text": "{erede} arrossisce: «Non voglio il trono. Voglio solo che il maestro guarisca.»",
                              "intrigue": {"branch": "erede"}}},
                 {"label": "Accetti l'invito a cena di {usurpatore} (e un regalo di 1000 pietre)",
                  "effects": {"stones": 1000, "text": "«Un uomo pratico», dice {usurpatore}, versandoti il vino. «Ci capiremo.»",
                              "intrigue": {"branch": "usurpatore"}}},
             ]},
            {"title": "La tazza di giada", "focus": "usurpatore", "gap": (2, 3),
             "text": ("Il patriarca peggiora. {usurpatore} convoca il conclave degli anziani fra tre giorni: «La setta non "
                      "può restare senza guida.» Hai tre giorni."),
             "choices": [
                 {"label": "Esamini la tazza del patriarca", "check": {"stat": "istinto", "dc": 56},
                  "success": {"text": "L'orlo è annerito: veleno di scorpione di giada, una goccia al giorno.", "intrigue": {"clue": 1}},
                  "failure": {"text": "La tazza è stata lavata. Troppo bene.", "intrigue": {}}},
                 {"label": "Fai parlare il servo che la lava (300 pietre)",
                  "effects": {"stones": -300, "text": "Il servo trema: «È stato il gran anziano ad assumermi. Io lavo solo le tazze.»",
                              "intrigue": {"clue": 1}}},
                 {"label": "Ti alleni: al conclave servirà la spada più delle parole",
                  "effects": {"heart": 3, "text": "Tre giorni di spada. Le tue mani sono calme.", "intrigue": {"branch": "pronto"}}},
             ]},
            {"title": "Il conclave", "focus": "erede", "gap": (2, 3),
             "text": ("Il patriarca è morto all'alba. Nella sala del trono di giada ci sono tutti gli anziani. {usurpatore} "
                      "si alza: «Propongo me stesso, per continuità.» Metà della sala annuisce. {erede} è pallido, e ti "
                      "cerca con gli occhi."),
             "text_low": ("Il patriarca è morto all'alba. Nella sala del trono {usurpatore} propone se stesso. Hai sospetti, "
                          "ma non prove. {erede} ti guarda."),
             "choices": [
                 {"label": "Metti la tazza sul tavolo e accusi {usurpatore}", "need_clues": 2,
                  "effects": {"fame": 15, "karma": 15, "relation": 30,
                              "text": ("La sala ammutolisce. {usurpatore} fugge prima che le guardie lo prendano. Gli anziani "
                                       "scelgono {erede}, che sale sul trono di giada con le mani che tremano e ti nomina "
                                       "sua mano destra."), "intrigue": {"flag": "trono_erede", "end": "erede_patriarca"}}},
                 {"label": "Voti per {usurpatore}", "need_branch": "usurpatore",
                  "effects": {"stones": 3000, "karma": -20,
                              "text": "{usurpatore} sale sul trono. {erede} lascia la setta quella notte stessa, senza salutare nessuno.",
                              "intrigue": {"flag": "trono_usurpatore", "end": "usurpatore_patriarca"}}},
                 {"label": "Ti alzi: «Il trono lo prendo io»", "check": {"stat": "potenza", "dc": 62},
                  "success": {"fame": 25, "infamy": 5,
                              "text": ("Nessuno osa sfidarti. Sali sul trono di giada nel silenzio. {usurpatore} si inchina "
                                       "per ultimo, sorridendo. {erede} non si inchina affatto."),
                              "intrigue": {"flag": "trono_tuo", "end": "tuo"}},
                  "failure": {"infamy": 8, "injury": 2,
                              "text": "Gli anziani si alzano tutti insieme contro di te. Esci dalla sala sanguinando, e dalla setta in disgrazia.",
                              "intrigue": {"end": "cacciato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "deciso", "text": "Il conclave si è tenuto senza di te: {usurpatore} è il nuovo patriarca."}],
        "outcomes": {"erede_patriarca": "{erede} è il nuovo patriarca, e tu la sua mano destra.",
                     "usurpatore_patriarca": "Hai messo {usurpatore} sul trono di giada.",
                     "tuo": "Siedi sul trono di giada.", "cacciato": "Il conclave ti ha cacciato.",
                     "deciso": "{usurpatore} siede sul trono di giada."},
    },
    {
        "key": "trono_assedio", "title": "Il Trono di Giada — L'assedio", "kind": "corte", "weight": 7, "tier_min": 2,
        "req_flag": "trono_erede", "delay": 25,
        "cast": {"usurpatore": "legame:trono_erede", "erede": "legame:trono_erede"},
        "teaser": "Le sentinelle dicono di aver visto fuochi sulle colline: {usurpatore} non è fuggito lontano. Sta radunando qualcuno.",
        "memory": {"vittoria": "erede:fratello", "resistito": "erede:salvato"},
        "acts": [
            {"title": "I fuochi sulle colline", "focus": "usurpatore", "gap": (1, 2),
             "text": ("{usurpatore} torna con un esercito di mercenari e due sette rivali. «Il trono era mio per diritto "
                      "d'anzianità», grida sotto le mura. {erede}, sul trono da pochi mesi, ti stringe il braccio: "
                      "«Non so fare la guerra. Tu sì.»"),
             "choices": [
                 {"label": "Organizzi la difesa delle mura", "check": {"stat": "potenza", "dc": 60},
                  "success": {"text": "Le mura tengono la prima notte, e la seconda. I mercenari cominciano a contare i morti.",
                              "intrigue": {"clue": 1, "branch": "mura"}},
                  "failure": {"injury": 2, "text": "La porta est cede. Ricacci indietro il nemico, ma a caro prezzo.", "intrigue": {}}},
                 {"label": "Esci da solo e sfidi {usurpatore}", "effects": {"intrigue": {"branch": "sfida"}},
                  "command": "duello {usurpatore}"},
                 {"label": "Compri i mercenari (2500 pietre)",
                  "effects": {"stones": -2500, "text": "A mezzanotte metà dell'esercito leva le tende. I mercenari non muoiono per gli altri.",
                              "intrigue": {"branch": "comprati", "clue": 1}}},
             ]},
            {"title": "Dopo l'assedio", "auto": True,
             "text": "All'alba del settimo giorno il fumo si dirada.",
             "endings": [
                 {"need_branch": "duello_vinto", "outcome": "vittoria",
                  "effects": {"prize": _ORO, "fame": 20, "karma": 10, "title": "Mano Destra del Trono di Giada"},
                  "text": ("{usurpatore} è caduto davanti a tutti, e il suo esercito si è sciolto. {erede} ti aspetta sulle "
                           "mura e ti mette in mano il sigillo della setta: «Metà del trono è tua. Lo è sempre stata.»")},
                 {"need_clues": 1, "outcome": "resistito",
                  "effects": {"prize": _ARGENTO, "fame": 10},
                  "text": "Le mura hanno tenuto. {usurpatore} si ritira tra le colline, più vecchio e senza esercito."},
                 {"outcome": "caduta", "effects": {"fame": -8},
                  "text": ("La setta resiste, ma perde metà dei suoi discepoli e tutto il tesoro. {erede} invecchia di dieci "
                           "anni in sette giorni.")},
             ]},
        ],
        "auto_end": [{"outcome": "presa", "text": "{usurpatore} ha preso la setta mentre eri lontano."}],
        "outcomes": {"presa": "La setta è caduta."},
    },
    {
        "key": "trono_lama", "title": "Il Trono di Giada — La lama dell'usurpatore", "kind": "corte", "weight": 7,
        "tier_min": 2, "req_flag": "trono_usurpatore", "delay": 25,
        "cast": {"usurpatore": "legame:trono_usurpatore", "erede": "legame:trono_usurpatore"},
        "teaser": "Si dice che {erede} abbia radunato i discepoli scontenti in una valle a nord. Il nuovo patriarca non dorme più.",
        "memory": {"lama": "erede:tradito", "cambio": "erede:salvato"},
        "acts": [
            {"title": "Un lavoro per te", "focus": "usurpatore", "gap": (1, 2),
             "text": ("{usurpatore}, sul trono di giada, ti riceve da solo. «{erede} sta radunando i discepoli contro di "
                      "me. Tu sei l'unico di cui si fida ancora.» Ti spinge davanti un pugnale. «Uno degno. Ti farò gran "
                      "anziano.»"),
             "choices": [
                 {"label": "Prendi il pugnale e vai nella valle",
                  "effects": {"stones": 4000, "karma": -35, "infamy": 8, "title": "Lama dell'Usurpatore",
                              "text": ("{erede} ti accoglie a braccia aperte. Poi vede il pugnale. Non si difende. «Lo sapevo», "
                                       "dice soltanto."), "intrigue": {"end": "lama"}}},
                 {"label": "Vai nella valle e racconti tutto a {erede}",
                  "effects": {"relation": 30, "karma": 15,
                              "text": ("{erede} ascolta, poi ti abbraccia. «Allora torniamo insieme. Alla luce del sole.» "
                                       "Quella notte la valle si riempie di fuochi."),
                              "intrigue": {"flag": "trono_erede", "end": "cambio"}}},
                 {"label": "Pianti il pugnale nel tavolo di {usurpatore}", "effects": {"intrigue": {"end": "duello"}},
                  "command": "duello {usurpatore}"},
             ]},
        ],
        "auto_end": [{"outcome": "scoperto", "text": "{usurpatore} ha trovato un'altra lama."}],
        "outcomes": {"lama": "Hai ucciso la speranza di una setta per {usurpatore}.", "cambio": "Hai cambiato parte: torni con {erede}.",
                     "duello_vinto": "Hai abbattuto {usurpatore} sul suo trono rubato.", "duello_perso": "{usurpatore} ti ha battuto.",
                     "duello_fuga": "Sei fuggito dalla sala del trono.", "scoperto": "Qualcun altro ha fatto il lavoro."},
    },
    {
        "key": "trono_corona", "title": "Il Trono di Giada — Il peso della corona", "kind": "corte", "weight": 7,
        "tier_min": 3, "req_flag": "trono_tuo", "delay": 30,
        "cast": {"usurpatore": "legame:trono_tuo", "erede": "legame:trono_tuo"},
        "teaser": "Gli anziani si inchinano quando passi. Poi, quando credono che tu non senta, sussurrano. {usurpatore} sussurra più di tutti.",
        "acts": [
            {"title": "L'inverno della setta", "focus": "usurpatore", "gap": (1, 2),
             "text": ("Regnare non è come combattere. Il tesoro è vuoto, i raccolti di erbe sono andati a male, e i "
                      "discepoli esterni hanno fame. {usurpatore}, tuo gran anziano, propone di raddoppiare i tributi. "
                      "{erede}, in fondo alla sala, ti guarda come si guarda un estraneo."),
             "choices": [
                 {"label": "Paghi di tasca tua (3000 pietre)",
                  "effects": {"stones": -3000, "karma": 10,
                              "text": "I discepoli mangiano. Qualcuno, nei corridoi, comincia a chiamarti «il patriarca buono».",
                              "intrigue": {"branch": "generoso"}}},
                 {"label": "Raddoppi i tributi", "effects": {"stones": 2000, "karma": -10,
                                                            "text": "Il tesoro si riempie. I corridoi si svuotano.",
                                                            "intrigue": {"branch": "duro"}}},
                 {"label": "Fai sorvegliare {usurpatore}", "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "Di notte {usurpatore} incontra emissari di una setta rivale. Ora lo sai.", "intrigue": {"clue": 1}},
                  "failure": {"text": "{usurpatore} si accorge della spia e sorride.", "intrigue": {}}},
             ]},
            {"title": "La corona", "auto": True,
             "text": "Passano le stagioni. Una sera, nella sala del trono, ti accorgi che la giada del trono è calda.",
             "endings": [
                 {"need_branch": "generoso", "need_clues": 1, "outcome": "amato",
                  "effects": {"prize": _ORO, "fame": 25, "karma": 15, "title": "Patriarca del Trono di Giada"},
                  "text": ("Sventi la congiura di {usurpatore} prima che cominci, e lo esili con misericordia. {erede} torna "
                           "a inchinarsi davanti a te, stavolta di sua scelta. Il trono di giada ti riconosce.")},
                 {"need_clues": 1, "outcome": "temuto",
                  "effects": {"prize": _ARGENTO, "fame": 15, "infamy": 5, "title": "Patriarca di Ferro"},
                  "text": "La congiura finisce prima di cominciare: {usurpatore} sparisce una notte. La setta ti teme. Ti basta?"},
                 {"outcome": "rovesciato", "effects": {"fame": -15, "infamy": 5},
                  "text": ("Una notte la sala del trono si riempie di lame. {usurpatore} ha comprato metà degli anziani. "
                           "Ti salvi, ma il trono non è più tuo.")},
             ]},
        ],
        "auto_end": [{"outcome": "abdicato", "text": "Hai lasciato il trono vuoto troppo a lungo."}],
        "outcomes": {"abdicato": "Il trono di giada ha un nuovo padrone."},
    },
]
