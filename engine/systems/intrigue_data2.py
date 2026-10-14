"""
ALTRE TRAME (Aggiornamento 58) — intrighi, tornei, corti, misteri e le loro conseguenze.

Lo stesso formato di intrigue_data.py. Molte sono INCATENATE: una scelta accende un segno ("flag") e
una trama successiva nasce solo da quel segno, con gli stessi personaggi (cast "legame:<segno>").

  il fidanzamento annullato  → il duello dei tre anni
  la lista dell'assassino    → il Padiglione della Notte
  la principessa in fuga     → la corte del re
  l'esame d'ingresso         → il ragazzo dell'esame
  l'asta degli schiavi       → il sangue reale
  la grotta del maestro      → i nemici del maestro
  il figlio del Cielo        → la seconda prova del Cielo
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}
_RELIQUIA = {"rank": 1, "kinds": ["reliquia", "tesoro"]}
_SANGUE = {"rank": 2, "kinds": ["sangue", "nucleo"]}

MORE: list[dict] = [
    # ================================================================== IL FIDANZAMENTO ANNULLATO
    {
        "key": "fidanzamento_annullato", "title": "Il fidanzamento annullato", "kind": "umiliazione", "weight": 5,
        "tier_min": 1, "cast": {"vittima": "genio", "mandante": "anziano"},
        "acts": [
            {"title": "Davanti a tutta la città", "focus": "vittima", "gap": (1, 2),
             "text": ("Nella sala del clan, davanti a tutti, {vittima} posa sul tavolo il contratto di fidanzamento che le "
                      "vostre famiglie firmarono anni fa. Accanto a lei {mandante}, anziano della sua setta, sorride: "
                      "«Il Cielo e la terra sono troppo distanti. Mia allieva non sposerà uno come te.» La sala ride."),
             "choices": [
                 {"label": "Strappi tu il contratto: «Tra tre anni, nella vostra setta, decideremo chi è la terra»",
                  "effects": {"fame": 8, "heart": 5, "text": "La sala ammutolisce. Hai giurato: tra tre anni, un duello.",
                              "intrigue": {"flag": "tre_anni", "end": "giuramento"}}},
                 {"label": "Accetti in silenzio e te ne vai",
                  "effects": {"fame": -4, "heart": -3, "text": "Esci senza voltarti. Qualcosa, dentro, brucia.",
                              "intrigue": {"end": "silenzio"}}},
                 {"label": "Sfidi l'anziano qui, subito",
                  "effects": {"intrigue": {"end": "sfida"}}, "command": "duello {mandante}"},
             ]},
        ],
        "outcomes": {"giuramento": "Hai giurato il duello dei tre anni.", "silenzio": "Hai accettato l'umiliazione in silenzio.",
                     "sfida": "Hai sfidato l'anziano davanti a tutti.",
                     "sfida_vinto": "Hai umiliato l'anziano davanti a tutti: la sala ora ride di lui.",
                     "sfida_perso": "L'anziano ti ha messo in ginocchio davanti a tutti."},
    },
    {
        "key": "duello_tre_anni", "delay": 30, "title": "Il duello dei tre anni", "kind": "duello", "weight": 7, "tier_min": 1,
        "req_flag": "tre_anni", "cast": {"vittima": "legame:tre_anni", "mandante": "rivale"},
        "acts": [
            {"title": "Il giorno promesso", "focus": "vittima", "gap": (30, 40),
             "text": ("Il giorno promesso è arrivato. Sulla piazza della setta di {vittima} c'è tutta la città, e i "
                      "vecchi che tre anni fa ridevano adesso non ridono. {vittima} ti aspetta con la spada in mano: "
                      "«Non pensavo saresti venuto.»"),
             "choices": [
                 {"label": "Combatti il duello promesso",
                  "effects": {"fame": 10, "intrigue": {"end": "duello"}}, "command": "duello {npc}"},
                 {"label": "Le restituisci il giuramento: «Non ho più bisogno di dimostrarti niente»",
                  "effects": {"heart": 10, "karma": 10, "fame": 6,
                              "text": "Te ne vai. È la vittoria più pulita: non ti serve la sua sconfitta.",
                              "intrigue": {"end": "liberato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "mancato", "effects": {"fame": -10}, "text": "Non ti sei presentato al giorno promesso."}],
        "outcomes": {"duello_vinto": "Hai vinto il duello dei tre anni: chi ti derideva ora abbassa gli occhi.",
                     "duello_perso": "Hai perso il duello dei tre anni.", "liberato": "Hai sciolto il giuramento senza combattere."},
    },
    # ================================================================== L'ASSASSINO
    {
        "key": "lista_assassino", "title": "Un nome sulla lista nera", "kind": "intrigo", "weight": 5, "tier_min": 2,
        "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["L'arma dell'assassino ha il fiore nero del Padiglione della Notte inciso sull'elsa.",
                   "Il Padiglione accetta contratti solo da chi paga in giada imperiale.",
                   "Solo tre famiglie a {luogo} hanno giada imperiale; una è quella di {mandante}.",
                   "{mandante} ha pagato il Padiglione per la tua testa: non ti ha mai perdonato."],
        "cast": {"pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "La lama nel buio", "focus": "pedina", "gap": (2, 3),
             "text": ("Ti svegli con una lama alla gola. {pedina} sorride nel buio: «Niente di personale. Il tuo nome è "
                      "sulla lista del Padiglione della Notte.» Ti divincoli appena in tempo."),
             "choices": [
                 {"label": "Lo affronti", "effects": {"intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Lo lasci fuggire e lo segui",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "Lo vedi entrare in un magazzino col fiore nero sulla porta.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Lo perdi sui tetti.", "intrigue": {}}},
             ]},
            {"title": "Chi ha pagato", "focus": "mandante", "gap": (2, 4),
             "text": "Chi paga il Padiglione per la tua testa è {mandante}. Ora sai dove trovarlo.",
             "text_low": "Un altro assassino, un'altra notte. Prima o poi uno ce la farà, se non scopri chi paga.",
             "choices": [
                 {"label": "Vai da lui e lo costringi a ritirare il contratto",
                  "need_clues": 2,
                  "effects": {"fame": 8, "prize": _ARGENTO,
                              "text": "{mandante} ritira il contratto tremando. Ma il Padiglione ricorda chi gli toglie un lavoro.",
                              "intrigue": {"flag": "padiglione_notte", "end": "ritirato"}}},
                 {"label": "Lo affronti", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {npc}"},
                 {"label": "Compri il tuo nome dalla lista (3000 pietre)",
                  "effects": {"stones": -3000, "text": "Il tuo nome viene cancellato. Per ora.", "intrigue": {"end": "comprato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "ferito", "effects": {"injury": 3}, "text": "Un assassino ti ha raggiunto nel sonno."}],
        "outcomes": {"duello_vinto": "Hai battuto chi ti voleva morto.", "duello_perso": "Chi ti voleva morto ha avuto la meglio.",
                     "ritirato": "Hai costretto {mandante} a ritirare il contratto.", "comprato": "Hai comprato il tuo nome."},
    },
    {
        "key": "padiglione_notte", "delay": 4, "title": "Il Padiglione della Notte", "kind": "vendetta", "weight": 6, "tier_min": 2,
        "req_flag": "padiglione_notte", "cast": {"pedina": "sgherro", "mandante": "anziano"},
        "acts": [
            {"title": "Il fiore nero", "focus": "pedina", "gap": (3, 5),
             "text": ("Sulla tua porta qualcuno ha inciso un fiore nero. {pedina} ti aspetta in strada: «Il Signore del "
                      "Padiglione vuole parlarti. Hai tolto un lavoro ai suoi figli.»"),
             "choices": [
                 {"label": "Vai all'appuntamento", "effects": {"intrigue": {"branch": "incontro"}}},
                 {"label": "Rifiuti e ti prepari", "effects": {"intrigue": {"branch": "guerra"}}},
             ]},
            {"title": "Il Signore del Padiglione", "focus": "mandante", "gap": (1, 2),
             "text": ("In una sala senza finestre ti riceve {mandante}, il Signore del Padiglione della Notte: «Puoi "
                      "lavorare per me, o morire per me. Scegli.»"),
             "text_branch": {"guerra": "Di notte {mandante}, il Signore del Padiglione, ti viene a cercare di persona."},
             "choices": [
                 {"label": "Lo sfidi", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {npc}"},
                 {"label": "Accetti un solo incarico, poi siete pari",
                  "effects": {"infamy": 8, "karma": -15, "prize": _ARGENTO, "relation": 30,
                              "text": "Uccidi un uomo che non conosci. Il Padiglione ti chiama amico. Non è un complimento.",
                              "intrigue": {"end": "patto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "taglia", "effects": {"injury": 2}, "text": "Il Padiglione ti ha messo una taglia sulla testa."}],
        "outcomes": {"duello_vinto": "Hai battuto il Signore del Padiglione della Notte.",
                     "duello_perso": "Il Signore del Padiglione ti ha lasciato vivere: per ora.", "patto": "Hai lavorato per il Padiglione."},
    },
    # ================================================================== LA PILLOLA CONTRAFFATTA
    {
        "key": "pillola_contraffatta", "title": "La pillola contraffatta", "kind": "intrigo", "weight": 5, "tier_min": 2,
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["Le pillole che avvelenano i discepoli hanno il sigillo della Gilda degli Alchimisti, ma è inciso male.",
                   "Dentro c'è polvere d'ossa di bestia, non l'erba che dovrebbe esserci.",
                   "Solo un forno della città cuoce polvere d'ossa: quello di {pedina}.",
                   "{pedina} cuoce per {mandante}, che compra le botteghe dei rivali ridotte in rovina."],
        "cast": {"pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "I discepoli avvelenati", "focus": None, "gap": (2, 3),
             "text": ("A {luogo} tre discepoli sono morti dopo aver preso una Pillola della Fondazione comprata al mercato. "
                      "La Gilda degli Alchimisti giura che non è sua."),
             "choices": [
                 {"label": "Esamini una pillola", "check": {"stat": "anima", "dc": 56},
                  "success": {"text": "Il sigillo è falso, inciso da una mano inesperta.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Sembra vera. Troppo vera.", "intrigue": {}}},
                 {"label": "Ti fingi compratore al mercato nero",
                  "effects": {"stones": -200, "text": "Il venditore ti allunga una pillola uguale: viene da un forno di periferia.",
                              "intrigue": {"clue": 1}}},
             ]},
            {"title": "Il forno di periferia", "focus": "mandante", "gap": (2, 3),
             "text": "Il forno è di {pedina}, ma chi paga è {mandante}.",
             "text_low": "Altri due discepoli muoiono. La città chiede un colpevole, e lo chiede a te che indagavi.",
             "choices": [
                 {"label": "Porti le prove alla Gilda", "need_clues": 2,
                  "effects": {"fame": 10, "karma": 20, "prize": _ARGENTO,
                              "text": "La Gilda chiude le botteghe di {mandante} e ti nomina amico degli alchimisti.",
                              "intrigue": {"end": "smascherato"}}},
                 {"label": "Affronti {mandante}", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {mandante}"},
             ]},
        ],
        "auto_end": [{"outcome": "insabbiato", "effects": {"karma": -5}, "text": "La faccenda è stata insabbiata."}],
        "outcomes": {"smascherato": "Hai smascherato il commercio di pillole avvelenate.",
                     "duello_vinto": "Hai battuto chi vendeva pillole avvelenate.", "duello_perso": "Chi vendeva veleno ti ha battuto."},
    },
    # ================================================================== LA GARA DEL GRAN MAESTRO ALCHIMISTA
    {
        "key": "gara_alchimia", "title": "La gara del Gran Maestro Alchimista", "kind": "torneo", "weight": 4, "tier_min": 2,
        "cast": {"genio": "genio", "mandante": "anziano"},
        "acts": [
            {"title": "Il forno incrinato", "focus": "genio", "gap": (1, 2),
             "text": ("Alla gara degli alchimisti di {luogo} ti assegnano un forno: ha una crepa sottile, quasi invisibile. "
                      "Accanto a te {genio}, il favorito, ha un forno nuovo di zecca."),
             "choices": [
                 {"label": "Ripari la crepa con il tuo Qi", "check": {"stat": "qi", "dc": 58},
                  "success": {"text": "La crepa si chiude. Nessuno se ne accorge.", "intrigue": {"branch": "riparato"}},
                  "failure": {"injury": 1, "text": "Il forno scoppietta. Perderai tempo.", "intrigue": {}}},
                 {"label": "Denunci il forno ai giudici", "effects": {"text": "Ti danno un forno nuovo, guardandoti storto.",
                                                                     "intrigue": {"clue": 1}}},
             ]},
            {"title": "La pillola finale", "auto": True,
             "text": "Il fumo sale dai forni. Alla fine, i giudici annusano, assaggiano, pesano.",
             "endings": [
                 {"need_branch": "riparato", "outcome": "vittoria", "effects": {"prize": _ORO, "fame": 12},
                  "text": "Con un forno rotto hai fatto una pillola perfetta: il Gran Maestro in persona ti stringe la mano."},
                 {"need_clues": 1, "outcome": "secondo", "effects": {"prize": _ARGENTO, "fame": 6},
                  "text": "Arrivi secondo dietro {genio}. Ma ora sai che qualcuno voleva farti perdere."},
                 {"outcome": "terzo", "effects": {"prize": _BRONZO}, "text": "La tua pillola è buona, non perfetta."},
             ]},
        ],
        "auto_end": [{"outcome": "assente", "text": "La gara si è svolta senza di te."}], "outcomes": {},
    },
    # ================================================================== LA PRINCIPESSA IN FUGA
    {
        "key": "principessa_fuga", "title": "La principessa in fuga", "kind": "corte", "weight": 5, "tier_min": 2,
        "cast": {"vittima": "genio", "pedina": "sgherro", "mandante": "anziano"},
        "acts": [
            {"title": "Una ragazza col mantello da servitrice", "focus": "vittima", "gap": (1, 2),
             "text": ("Una ragazza col mantello da servitrice ma le mani di chi non ha mai lavorato ti afferra il braccio: "
                      "«Mi chiamo {vittima}. Mi vogliono dare in sposa al figlio di {mandante} per un'alleanza. Aiutami a "
                      "passare il confine.» Dietro di lei, cavalieri con lo stendardo reale."),
             "choices": [
                 {"label": "La nascondi e la scorti al confine",
                  "effects": {"relation": 25, "intrigue": {"branch": "scorta"}}},
                 {"label": "La consegni ai cavalieri", "effects": {"stones": 800, "relation": -50, "karma": -10,
                                                                    "intrigue": {"end": "consegnata"}}},
             ]},
            {"title": "I cavalieri al passo", "focus": "pedina", "gap": (1, 2),
             "text": "Al passo, {pedina}, capitano delle guardie reali, vi sbarra la strada.",
             "choices": [
                 {"label": "Lo affronti", "effects": {"intrigue": {}}, "command": "duello {npc}"},
                 {"label": "Lo convinci a lasciarvi passare", "check": {"stat": "karma", "dc": 58},
                  "success": {"text": "«Non ho visto nessuno», dice, e si volta.", "intrigue": {"clue": 1}},
                  "failure": {"text": "«Ordini del re.» Sguaina.", "intrigue": {}}, "command": ""},
             ]},
            {"title": "Oltre il confine", "auto": True,
             "text": "Oltre il confine, {vittima} si toglie il mantello. Sotto, un sigillo reale.",
             "endings": [
                 {"need_branch": "duello_vinto", "outcome": "salvata", "flag": "principessa",
                  "effects": {"prize": _ARGENTO, "relation": 30, "bond": "companion"},
                  "text": "«Non dimenticherò.» Ti lascia il sigillo: un giorno potrebbe aprirti le porte di una corte."},
                 {"need_clues": 1, "outcome": "salvata", "flag": "principessa", "effects": {"prize": _ARGENTO, "relation": 30},
                  "text": "Passate il confine senza versare sangue. «Non dimenticherò.»"},
                 {"outcome": "ripresa", "effects": {"fame": -3}, "text": "Al confine i cavalieri la riprendono."},
             ]},
        ],
        "auto_end": [{"outcome": "ripresa", "text": "La principessa è stata ripresa senza di te."}],
        "outcomes": {"consegnata": "Hai consegnato la principessa ai cavalieri."},
    },
    {
        "key": "corte_del_re", "delay": 10, "title": "La corte del re", "kind": "corte", "weight": 6, "tier_min": 2,
        "req_flag": "principessa", "cast": {"vittima": "legame:principessa", "mandante": "anziano"},
        "acts": [
            {"title": "La convocazione", "focus": "mandante", "gap": (8, 14),
             "text": ("Un messaggero col sigillo reale: il re ti convoca. A corte {mandante}, gran consigliere, ti accusa "
                      "di aver rapito la principessa {vittima}. Lei, in fondo alla sala, ti guarda."),
             "choices": [
                 {"label": "Racconti la verità davanti al re", "check": {"stat": "karma", "dc": 56},
                  "success": {"fame": 15, "prize": _ORO,
                              "text": "{vittima} conferma ogni parola. Il re ti nomina Ospite del Regno; il consigliere impallidisce.",
                              "intrigue": {"end": "ospite"}},
                  "failure": {"text": "Il re non ti crede. La principessa tace, per paura.", "intrigue": {"end": "bandito"}}},
                 {"label": "Sfidi il consigliere al giudizio delle armi",
                  "effects": {"fame": 6, "intrigue": {"end": "giudizio"}}, "command": "duello {mandante}"},
             ]},
        ],
        "auto_end": [{"outcome": "bandito", "effects": {"infamy": 4}, "text": "Non ti sei presentato: il re ti ha bandito."}],
        "outcomes": {"ospite": "Il re ti ha nominato Ospite del Regno.", "bandito": "Il re ti ha bandito dal regno.",
                     "giudizio_vinto": "Hai vinto il giudizio delle armi davanti al re.",
                     "giudizio_perso": "Hai perso il giudizio delle armi: il re ti bandisce."},
    },
    # ================================================================== L'ESAME D'INGRESSO
    {
        "key": "esame_ingresso", "title": "L'esame d'ingresso", "kind": "setta", "weight": 4, "tier_min": 3,
        "req_sect": True, "cast": {"vittima": "genio", "pedina": "sgherro"},
        "acts": [
            {"title": "Il ragazzo con le scarpe di paglia", "focus": "vittima", "gap": (1, 2),
             "text": ("La {mia_setta} ti nomina esaminatore. Tra cento ragazzi ce n'è uno con le scarpe di paglia, {vittima}: "
                      "la pietra del talento si accende appena, ma lui non si arrende alla terza prova. Intanto il figlio "
                      "di un anziano, {pedina}, supera tutto con troppa facilità."),
             "choices": [
                 {"label": "Prendi {vittima} come tuo allievo, contro il parere di tutti",
                  "effects": {"relation": 40, "bond": "companion", "text": "«Non ti deluderò, maestro.»",
                              "intrigue": {"flag": "allievo_esame", "end": "allievo"}}},
                 {"label": "Smascheri l'imbroglio di {pedina} (pietra truccata)", "check": {"stat": "istinto", "dc": 56},
                  "success": {"fame": 6, "merit": 150, "text": "La pietra era truccata. L'anziano suo padre non te lo perdonerà.",
                              "intrigue": {"end": "imbroglio"}},
                  "failure": {"text": "Non trovi nulla. {pedina} ti sorride.", "intrigue": {"end": "niente"}}},
                 {"label": "Segui le regole: passa chi passa", "effects": {"intrigue": {"end": "regole"}}},
             ]},
        ],
        "outcomes": {"allievo": "Hai preso un allievo senza talento.", "imbroglio": "Hai smascherato un esame truccato.",
                     "niente": "Non hai trovato l'imbroglio.", "regole": "Hai seguito le regole."},
    },
    {
        "key": "ragazzo_esame", "delay": 25, "title": "Il ragazzo dell'esame", "kind": "setta", "weight": 6, "tier_min": 3,
        "req_flag": "allievo_esame", "cast": {"vittima": "legame:allievo_esame", "mandante": "rivale"},
        "acts": [
            {"title": "L'allievo è cresciuto", "focus": "vittima", "gap": (20, 30),
             "text": ("Il tuo allievo {vittima}, quello delle scarpe di paglia, ha sfondato un regno da solo. Ora {mandante} "
                      "gli offre un posto da discepolo interno nella sua setta, con pillole e maestri che tu non puoi dargli."),
             "choices": [
                 {"label": "Lo lasci andare: è il suo cammino", "effects": {"karma": 15, "relation": 20, "prize": _BRONZO,
                                                                         "text": "Ti si inchina tre volte prima di partire.",
                                                                         "intrigue": {"end": "partito"}}},
                 {"label": "Gli chiedi di restare", "check": {"stat": "karma", "dc": 55},
                  "success": {"relation": 30, "text": "«Il mio maestro sei tu.» Resta.", "intrigue": {"end": "rimasto"}},
                  "failure": {"relation": -20, "text": "Se ne va senza voltarsi.", "intrigue": {"end": "partito"}}},
             ]},
        ],
        "outcomes": {"partito": "Il tuo allievo ha preso la sua strada.", "rimasto": "Il tuo allievo è rimasto con te."},
    },
    # ================================================================== IL DEMONE NEL POZZO
    {
        "key": "demone_pozzo", "title": "Il demone nel pozzo sigillato", "kind": "demoniaco", "weight": 4, "tier_min": 3,
        "cast": {"mandante": "anziano"},
        "acts": [
            {"title": "Il villaggio che sacrifica", "focus": "mandante", "gap": (1, 2),
             "text": ("Nel villaggio vicino a {luogo} ogni dieci anni si getta una fanciulla nel pozzo sigillato, perché il "
                      "demone dentro non esca. Quest'anno tocca alla nipote di {mandante}, il capo villaggio."),
             "choices": [
                 {"label": "Scendi nel pozzo al posto suo",
                  "effects": {"karma": 15, "intrigue": {"branch": "scendi"}}},
                 {"label": "Rafforzi il sigillo dall'esterno", "check": {"stat": "anima", "dc": 62},
                  "success": {"karma": 20, "prize": _BRONZO, "text": "Il sigillo regge per altri cent'anni. Nessuna fanciulla.",
                              "intrigue": {"end": "sigillo"}},
                  "failure": {"injury": 2, "text": "Il sigillo ti respinge. Devi scendere.", "intrigue": {"branch": "scendi"}}},
             ]},
            {"title": "In fondo al pozzo", "auto": True,
             "text": "In fondo al pozzo non c'è un demone: c'è un vecchio coltivatore incatenato da secoli, che ride.",
             "endings": [
                 {"need_branch": "scendi", "outcome": "liberato", "effects": {"prize": _ORO, "karma": -5},
                  "text": "Lo liberi. In cambio ti lascia la sua arte, e sparisce nella notte. Forse era davvero un demone."},
                 {"outcome": "sigillo", "text": "Il pozzo resta chiuso."},
             ]},
        ],
        "outcomes": {"sigillo": "Hai rafforzato il sigillo del pozzo."},
    },
    # ================================================================== L'ASTA DEGLI SCHIAVI
    {
        "key": "asta_schiavi", "title": "L'asta degli schiavi", "kind": "asta", "weight": 4, "tier_min": 2,
        "cast": {"vittima": "genio", "mandante": "rivale"},
        "acts": [
            {"title": "Il lotto numero nove", "focus": "vittima", "gap": (1, 2),
             "text": ("Nel sotterraneo di un'asta proibita vendono coltivatori in catene. Il lotto nove, {vittima}, ha gli "
                      "occhi d'oro dei clan reali. {mandante} alza la mano per primo."),
             "choices": [
                 {"label": "Lo compri (2500 pietre) e lo liberi",
                  "effects": {"stones": -2500, "karma": 20, "relation": 40,
                              "intrigue": {"flag": "sangue_reale", "end": "liberato"}}},
                 {"label": "Liberi tutti i lotti con la forza", "check": {"stat": "potenza", "dc": 62},
                  "success": {"karma": 35, "fame": 10, "infamy": 3, "relation": 40,
                              "text": "Le catene cadono. L'asta brucia.", "intrigue": {"flag": "sangue_reale", "end": "rivolta"}},
                  "failure": {"injury": 3, "text": "Le guardie ti respingono.", "intrigue": {"end": "fallito"}}},
                 {"label": "Te ne vai", "effects": {"karma": -5, "intrigue": {"end": "indifferenza"}}},
             ]},
        ],
        "outcomes": {"liberato": "Hai comprato la libertà del lotto nove.", "rivolta": "Hai liberato tutti gli schiavi dell'asta.",
                     "fallito": "Non sei riuscito a liberarli.", "indifferenza": "Te ne sei andato."},
    },
    {
        "key": "sangue_reale", "delay": 12, "title": "Il sangue reale", "kind": "eredita", "weight": 6, "tier_min": 2,
        "req_flag": "sangue_reale", "cast": {"vittima": "legame:sangue_reale", "mandante": "rivale"},
        "acts": [
            {"title": "Il principe perduto", "focus": "vittima", "gap": (10, 16),
             "text": ("{vittima}, lo schiavo che hai liberato, torna da te con un sigillo d'oro: è l'ultimo erede di un regno "
                      "caduto, e {mandante} che lo vendette vuole finire il lavoro."),
             "choices": [
                 {"label": "Lo aiuti a riprendersi il trono", "effects": {"intrigue": {"end": "trono"}},
                  "command": "duello {mandante}"},
                 {"label": "Gli consigli di vivere in pace, lontano", "effects": {"karma": 5, "prize": _SANGUE,
                                                                                  "text": "Ti lascia una goccia del suo sangue reale, in segno di gratitudine.",
                                                                                  "intrigue": {"end": "pace"}}},
             ]},
        ],
        "outcomes": {"trono_vinto": "Hai rimesso un principe sul suo trono: un regno ti deve tutto.",
                     "trono_perso": "Non sei riuscito a difendere il principe perduto.", "pace": "Il principe è partito in pace."},
    },
    # ================================================================== IL MAESTRO CHE VENDE I DISCEPOLI
    {
        "key": "maestro_venduto", "title": "I discepoli che non tornano", "kind": "intrigo", "weight": 4, "tier_min": 3,
        "req_sect": True, "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["I discepoli scomparsi erano tutti di talento, e tutti in missione con lo stesso anziano.",
                   "Le missioni partivano sempre verso la Palude Nera, dove non c'è nulla da cacciare.",
                   "Nella palude, un accampamento demoniaco paga in pillole di sangue.",
                   "L'anziano che vende i discepoli ai demoni è {mandante}."],
        "cast": {"vittima": "alleato", "mandante": "anziano"},
        "acts": [
            {"title": "Un'altra missione", "focus": "vittima", "gap": (2, 3),
             "text": ("Nella {mia_setta} tre discepoli di talento non sono tornati dalle missioni. Ora {vittima} è stato "
                      "scelto per la prossima. Ti chiede di accompagnarlo, in segreto."),
             "choices": [
                 {"label": "Lo segui in segreto", "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "La missione va verso la Palude Nera. Perché?", "intrigue": {"clue": 2}},
                  "failure": {"text": "Lo perdi nella nebbia.", "intrigue": {"clue": 1}}},
                 {"label": "Controlli i registri delle missioni", "effects": {"intrigue": {"clue": 1}}},
             ]},
            {"title": "La Palude Nera", "focus": "mandante", "gap": (1, 2),
             "text": "Nella palude {mandante} consegna {vittima} a un emissario demoniaco.",
             "text_low": "{vittima} non è tornato. La setta dice che è caduto da eroe.",
             "choices": [
                 {"label": "Intervieni e smascheri l'anziano", "need_clues": 2,
                  "effects": {"intrigue": {"end": "smascherato"}}, "command": "duello {mandante}"},
                 {"label": "Torni alla setta e denunci quello che hai visto", "need_clues": 2,
                  "effects": {"merit": 300, "fame": 8, "intrigue": {"end": "denuncia"}}},
             ]},
        ],
        "auto_end": [{"outcome": "perduto", "effects": {"karma": -5}, "text": "Altri discepoli non sono tornati."}],
        "outcomes": {"smascherato_vinto": "Hai smascherato e battuto l'anziano che vendeva i discepoli.",
                     "smascherato_perso": "L'anziano ti ha battuto e messo a tacere.",
                     "denuncia": "Hai denunciato l'anziano traditore alla setta."},
    },
    # ================================================================== IL GENIO CADUTO
    {
        "key": "genio_caduto", "title": "Il genio caduto", "kind": "riscatto", "weight": 4, "tier_min": 2,
        "cast": {"vittima": "genio"},
        "acts": [
            {"title": "Lo spazzatura del clan", "focus": "vittima", "gap": (1, 2),
             "text": ("Tre anni fa {vittima} era il genio del suo clan. Poi qualcuno gli ha spezzato i meridiani, e ora lo "
                      "chiamano «spazzatura». Ti guarda allenarti per ore, in silenzio."),
             "choices": [
                 {"label": "Gli insegni una tecnica per riaprire i meridiani", "check": {"stat": "anima", "dc": 56},
                  "success": {"relation": 40, "bond": "companion", "text": "Dopo un mese il suo Qi torna a scorrere.",
                              "intrigue": {"branch": "salvato"}},
                  "failure": {"relation": 10, "text": "Ci provate. Non basta. Ma lui non si arrende.", "intrigue": {}}},
                 {"label": "Gli dai una pillola rara", "effects": {"stones": -800, "relation": 30, "intrigue": {"branch": "salvato"}}},
             ]},
            {"title": "Il giorno della rivincita", "auto": True,
             "text": "Al torneo del clan, «la spazzatura» sale sulla pedana.",
             "endings": [
                 {"need_branch": "salvato", "outcome": "rivincita", "effects": {"prize": _ARGENTO, "fame": 6},
                  "text": "{vittima} vince il torneo del clan, e davanti a tutti si inchina a te: «Il mio maestro.»"},
                 {"outcome": "caduto", "text": "{vittima} perde, e lascia il clan. Non lo rivedrai più."},
             ]},
        ],
        "outcomes": {},
    },
    # ================================================================== IL TESORO CADUTO DAL CIELO
    {
        "key": "tesoro_cielo", "title": "La stella caduta", "kind": "reame", "weight": 5, "tier_min": 2,
        "cast": {"genio": "genio", "pedina": "sgherro"},
        "acts": [
            {"title": "Una stella nella notte", "focus": None, "gap": (1, 1),
             "text": ("Di notte una stella cade oltre le colline di {luogo}. All'alba, mezza regione corre verso il cratere: "
                      "si dice che dentro ci sia un tesoro dei Cieli Superiori."),
             "choices": [
                 {"label": "Corri al cratere", "effects": {"intrigue": {"branch": "veloce"}}},
                 {"label": "Aspetti che si scannino, poi vai", "effects": {"karma": -5, "intrigue": {"branch": "furbo"}}},
             ]},
            {"title": "Il cratere", "focus": "genio", "gap": (1, 1),
             "text": "Nel cratere {genio} e {pedina} sono già alle mani per una sfera che pulsa di luce.",
             "choices": [
                 {"label": "Prendi la sfera mentre combattono", "check": {"stat": "istinto", "dc": 60},
                  "success": {"text": "La sfera è tua. Corri.", "intrigue": {"branch": "sfera"}},
                  "failure": {"injury": 2, "text": "Ti vedono entrambi.", "intrigue": {}}, "command": ""},
                 {"label": "Sfidi il più forte dei due", "effects": {"intrigue": {}}, "command": "duello {genio}"},
             ]},
            {"title": "Dopo la stella", "auto": True, "text": "Quando la polvere si posa, il cratere è vuoto.",
             "endings": [
                 {"need_branch": "sfera", "outcome": "sfera", "effects": {"prize": _RELIQUIA, "infamy": 2},
                  "text": "La sfera era il cuore di una stella: un tesoro dei Cieli Superiori."},
                 {"need_branch": "duello_vinto", "outcome": "vinto", "effects": {"prize": _ORO},
                  "text": "Battuto il più forte, gli altri ti lasciano il tesoro."},
                 {"outcome": "perso", "effects": {"prize": _BRONZO}, "text": "Ti restano solo frammenti di stella."},
             ]},
        ],
        "auto_end": [{"outcome": "perso", "text": "Altri hanno preso il tesoro della stella."}], "outcomes": {},
    },
    # ================================================================== LA CITTÀ DEI FANTASMI
    {
        "key": "citta_fantasmi", "title": "La città che appare di notte", "kind": "mistero", "weight": 4, "tier_min": 3,
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["La città fantasma è identica a {luogo}, ma com'era trecento anni fa.",
                   "Tutti i fantasmi ripetono la stessa notte: quella dell'incendio.",
                   "L'incendio non fu un incidente: le porte furono sbarrate dall'esterno.",
                   "Chi sbarrò le porte era il fondatore della famiglia di {mandante}, che ancora oggi governa la città."],
        "cast": {"spettro": "spettro", "mandante": "anziano"},
        "acts": [
            {"title": "Le lanterne di mezzanotte", "focus": "spettro", "gap": (2, 3),
             "text": ("A mezzanotte, accanto a {luogo}, si accendono lanterne dove non c'è niente: una città intera, di "
                      "nebbia e voci. {spettro} ti chiede: «Hai visto chi ha chiuso le porte?»"),
             "choices": [
                 {"label": "Cammini tra i fantasmi e ascolti", "check": {"stat": "anima", "dc": 58},
                  "success": {"text": "Tutti raccontano la stessa notte, quella del fuoco.", "intrigue": {"clue": 2}},
                  "failure": {"text": "Le voci si confondono.", "intrigue": {"clue": 1}}},
             ]},
            {"title": "Le porte sbarrate", "focus": "mandante", "gap": (2, 3),
             "text": "La famiglia di {mandante} governa la città da trecento anni, costruita sulle ceneri di quella notte.",
             "choices": [
                 {"label": "Costringi {mandante} a chiedere perdono ai morti", "need_clues": 2,
                  "effects": {"karma": 30, "prize": _ARGENTO,
                              "text": "{mandante} si inginocchia nella nebbia. Le lanterne si spengono, una dopo l'altra: i morti riposano.",
                              "intrigue": {"end": "pace"}}},
                 {"label": "Bruci un incenso per i morti e te ne vai", "effects": {"karma": 5, "intrigue": {"end": "incenso"}}},
             ]},
        ],
        "auto_end": [{"outcome": "nebbia", "text": "La città fantasma continua ad apparire ogni notte."}],
        "outcomes": {"pace": "Hai dato pace ai morti della città fantasma.", "incenso": "Hai acceso un incenso per i morti."},
    },
    # ================================================================== IL BANCHETTO DELLE DUE FAMIGLIE
    {
        "key": "banchetto", "title": "Il banchetto della riconciliazione", "kind": "intrigo", "weight": 4, "tier_min": 2,
        "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["Il vino avvelenato era solo nella coppa del capo famiglia, non nell'anfora.",
                   "La coppa l'ha versata un servo nuovo, assunto tre giorni fa.",
                   "Il servo è sparito, ma ha lasciato una ricevuta di un banco di pegni.",
                   "Il pegno è stato riscattato da {mandante}, che voleva la guerra tra le due famiglie."],
        "cast": {"vittima": "alleato", "mandante": "rivale"},
        "acts": [
            {"title": "La coppa che cade", "focus": "vittima", "gap": (2, 3),
             "text": ("Al banchetto che doveva riconciliare due famiglie in faida da tre generazioni, il capo famiglia beve e "
                      "cade riverso. Le spade escono dai foderi. {vittima} ti guarda: «Fermali, prima che sia tardi.»"),
             "choices": [
                 {"label": "Ti metti in mezzo: «Nessuno si muove finché non so chi è stato»",
                  "effects": {"fame": 6, "intrigue": {"clue": 1}}},
                 {"label": "Salvi il capo famiglia con il tuo Qi", "check": {"stat": "qi", "dc": 60},
                  "success": {"karma": 15, "text": "Il veleno esce col sangue nero. Vivrà.", "intrigue": {"clue": 1, "branch": "salvato"}},
                  "failure": {"text": "Troppo tardi.", "intrigue": {}}},
             ]},
            {"title": "Chi voleva la guerra", "focus": "mandante", "gap": (2, 3),
             "text": "Chi voleva la guerra è {mandante}.", "text_low": "Le due famiglie si armano. La guerra è vicina.",
             "choices": [
                 {"label": "Lo smascheri davanti alle due famiglie", "need_clues": 2,
                  "effects": {"fame": 12, "karma": 20, "prize": _ARGENTO, "intrigue": {"end": "pace"}}},
                 {"label": "Lo affronti", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {mandante}"},
             ]},
        ],
        "auto_end": [{"outcome": "guerra", "text": "Le due famiglie sono tornate in guerra."}],
        "outcomes": {"pace": "Hai salvato la pace tra le due famiglie.", "duello_vinto": "Hai battuto chi voleva la guerra.",
                     "duello_perso": "Chi voleva la guerra ti ha battuto: le famiglie si armano."},
    },
    # ================================================================== LA PRIGIONE SOTTO IL LAGO
    {
        "key": "prigione_lago", "title": "La prigione sotto il lago", "kind": "salvataggio", "weight": 4, "tier_min": 3,
        "cast": {"vittima": "anziano", "pedina": "sgherro"},
        "acts": [
            {"title": "Un messaggio nella bottiglia", "focus": None, "gap": (1, 2),
             "text": ("Un pescatore ti porta una bottiglia trovata nel lago: dentro, un messaggio scritto col sangue. «Sono "
                      "{vittima}, anziano accusato ingiustamente. Mi tengono sotto il lago da dieci anni.»"),
             "choices": [
                 {"label": "Scendi a cercare la prigione", "check": {"stat": "corpo", "dc": 58},
                  "success": {"text": "Trovi l'ingresso, tra le alghe.", "intrigue": {"branch": "trovata"}},
                  "failure": {"injury": 1, "text": "Le correnti ti respingono. Riproverai.", "intrigue": {"branch": "trovata"}}},
                 {"label": "Ignori il messaggio", "effects": {"intrigue": {"end": "ignorato"}}},
             ]},
            {"title": "Il carceriere", "focus": "pedina", "gap": (1, 2),
             "text": "Davanti alla cella, {pedina}, il carceriere, mangia da solo da dieci anni.",
             "choices": [
                 {"label": "Lo affronti", "effects": {"intrigue": {}}, "command": "duello {npc}"},
                 {"label": "Lo convinci che anche lui è un prigioniero", "check": {"stat": "karma", "dc": 56},
                  "success": {"text": "Piange. Ti dà le chiavi.", "intrigue": {"branch": "chiavi"}},
                  "failure": {"text": "«Il mio dovere è qui.» Sguaina.", "intrigue": {}}, "command": ""},
             ]},
            {"title": "La luce dopo dieci anni", "auto": True, "text": "La cella si apre.",
             "endings": [
                 {"need_branch": "chiavi", "outcome": "liberato", "effects": {"prize": _ORO, "relation": 50, "karma": 20},
                  "text": "{vittima} esce alla luce dopo dieci anni, e ti insegna l'arte che lo fece temere."},
                 {"need_branch": "duello_vinto", "outcome": "liberato", "effects": {"prize": _ORO, "relation": 50},
                  "text": "{vittima} esce alla luce dopo dieci anni, e ti insegna l'arte che lo fece temere."},
                 {"outcome": "troppo_tardi", "effects": {"karma": 5}, "text": "Arrivi tardi: {vittima} è morto da qualche giorno."},
             ]},
        ],
        "outcomes": {"ignorato": "Hai ignorato il messaggio nella bottiglia."},
    },
    # ================================================================== L'UOVO DELLA FENICE
    {
        "key": "uovo_fenice", "title": "L'uovo rubato", "kind": "bestie", "weight": 4, "tier_min": 3,
        "cast": {"pedina": "sgherro"},
        "acts": [
            {"title": "La madre impazzita", "focus": "pedina", "gap": (1, 2),
             "text": ("Da tre giorni una fenice adulta brucia i campi attorno a {luogo}. Qualcuno le ha rubato l'uovo: "
                      "{pedina}, che ora cerca un compratore e ti mostra l'uovo, caldo, sotto un telo."),
             "choices": [
                 {"label": "Prendi l'uovo e lo riporti alla madre",
                  "effects": {"karma": 25, "intrigue": {"branch": "riportato"}}, "command": "duello {npc}"},
                 {"label": "Compri l'uovo (2000 pietre)", "effects": {"stones": -2000, "intrigue": {"branch": "comprato"}}},
             ]},
            {"title": "La fenice", "auto": True, "text": "La fenice scende dal cielo, ali di fuoco aperte.",
             "endings": [
                 {"need_branch": "riportato", "outcome": "benedizione", "effects": {"prize": _SANGUE, "karma": 10},
                  "text": "La fenice riprende l'uovo e ti lascia una piuma che brucia senza consumarsi: il suo sangue ti benedice."},
                 {"need_branch": "comprato", "outcome": "ira", "effects": {"injury": 3, "prize": _SANGUE},
                  "text": "La fenice ti trova. Fuggi col corpo ustionato e l'uovo che si schiude tra le tue mani."},
                 {"outcome": "cenere", "text": "I campi bruciano ancora per giorni."},
             ]},
        ],
        "outcomes": {},
    },
    # ================================================================== LA PESTE DELLE ANIME
    {
        "key": "peste_anime", "title": "La peste delle anime", "kind": "mistero", "weight": 4, "tier_min": 4,
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["I malati perdono la memoria a pezzi, come se qualcuno la mangiasse.",
                   "Tutti hanno bevuto al pozzo vicino al tempio abbandonato.",
                   "Nel pozzo c'è un verme d'anima, allevato: qualcuno lo nutre.",
                   "Chi lo nutre è {mandante}: raccoglie le memorie per un rituale."],
        "cast": {"mandante": "rivale"},
        "acts": [
            {"title": "Chi dimentica il proprio nome", "focus": None, "gap": (2, 3),
             "text": "A {luogo} la gente dimentica: prima i nomi, poi i volti, poi se stessa.",
             "choices": [
                 {"label": "Esamini un malato con il senso divino", "check": {"stat": "anima", "dc": 60},
                  "success": {"text": "Qualcosa ha morso la sua anima.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Non vedi nulla.", "intrigue": {}}},
                 {"label": "Prepari un rimedio che rallenti il male", "effects": {"karma": 10, "intrigue": {"clue": 1}}},
             ]},
            {"title": "Il verme nel pozzo", "focus": "mandante", "gap": (2, 3),
             "text": "Al pozzo, {mandante} nutre il verme d'anima.", "text_low": "Il male si allarga a tutta la regione.",
             "choices": [
                 {"label": "Uccidi il verme e restituisci le memorie", "need_clues": 2,
                  "effects": {"karma": 35, "fame": 10, "prize": _ARGENTO, "intrigue": {"end": "guariti"}}},
                 {"label": "Affronti {mandante}", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {mandante}"},
             ]},
        ],
        "auto_end": [{"outcome": "epidemia", "effects": {"karma": -5}, "text": "La peste delle anime si è allargata."}],
        "outcomes": {"guariti": "Hai fermato la peste delle anime.", "duello_vinto": "Hai battuto chi nutriva la peste.",
                     "duello_perso": "Chi nutriva la peste ti ha battuto."},
    },
    # ================================================================== IL FIGLIO DEL CIELO
    {
        "key": "figlio_cielo", "title": "Il figlio del Cielo", "kind": "destino", "weight": 4, "tier_min": 4,
        "cast": {"genio": "genio"},
        "acts": [
            {"title": "Il ragazzo che il fulmine evita", "focus": "genio", "gap": (1, 2),
             "text": ("Dicono che {genio} sia protetto dal Cielo: i fulmini lo evitano, le fortune lo cercano. Ti fissa "
                      "come si fissa un ostacolo: «Il Cielo dice che uno di noi due è di troppo.»"),
             "choices": [
                 {"label": "Lo sfidi: il Cielo non sceglie per te", "effects": {"intrigue": {"flag": "seconda_prova", "end": "sfida"}},
                  "command": "duello {npc}"},
                 {"label": "Gli offri un'alleanza contro il Cielo stesso", "check": {"stat": "karma", "dc": 60},
                  "success": {"relation": 40, "text": "Ride. «Contro il Cielo? Mi piaci.»", "intrigue": {"end": "alleanza"}},
                  "failure": {"text": "«Il Cielo non si tradisce.»", "intrigue": {"flag": "seconda_prova", "end": "rifiuto"}}},
             ]},
        ],
        "outcomes": {"sfida_vinto": "Hai battuto il figlio del Cielo: ora il Cielo ti guarda.",
                     "sfida_perso": "Il figlio del Cielo ti ha battuto.", "alleanza": "Ti sei alleato col figlio del Cielo.",
                     "rifiuto": "Il figlio del Cielo ha rifiutato la tua mano."},
    },
    {
        "key": "seconda_prova", "delay": 20, "title": "La seconda prova del Cielo", "kind": "destino", "weight": 6, "tier_min": 4,
        "req_flag": "seconda_prova", "cast": {"genio": "legame:seconda_prova"},
        "acts": [
            {"title": "Il fulmine che ti cerca", "focus": "genio", "gap": (15, 25),
             "text": ("Il Cielo non dimentica. Un giorno di sole un fulmine cade a un passo da te, e {genio} esce dal fumo: "
                      "più forte, più vicino al Cielo. «Seconda prova.»"),
             "choices": [
                 {"label": "Accetti", "effects": {"fame": 8, "intrigue": {"end": "prova"}}, "command": "duello {npc}"},
                 {"label": "Spezzi il legame col Cielo (sfida le leggi)", "check": {"stat": "anima", "dc": 64},
                  "success": {"heart": 10, "prize": _ORO, "text": "Il fulmine si spegne a mezz'aria. Il Cielo, per un istante, esita.",
                              "intrigue": {"end": "legame_spezzato"}},
                  "failure": {"injury": 3, "text": "Il Cielo non si spezza così.", "intrigue": {"end": "prova"},
                              "command": "duello {npc}"}},
             ]},
        ],
        "outcomes": {"prova_vinto": "Hai superato la seconda prova del Cielo.", "prova_perso": "Il Cielo ti ha sconfitto ancora.",
                     "legame_spezzato": "Hai spezzato il legame tra il Cielo e il suo figlio."},
    },
    # ================================================================== I NEMICI DEL MAESTRO (dalla grotta)
    {
        "key": "nemici_maestro", "delay": 12, "title": "I nemici del maestro senza nome", "kind": "eredita", "weight": 6, "tier_min": 1,
        "req_flag": "erede_grotta", "cast": {"mandante": "rivale", "pedina": "sgherro"},
        "acts": [
            {"title": "Chi riconosce la tua tecnica", "focus": "pedina", "gap": (10, 16),
             "text": ("Usi l'arte del maestro della grotta, e {pedina} impallidisce: «Quella tecnica… il mio signore la "
                      "cerca da trecento anni.» Il suo signore è {mandante}, che uccise il maestro."),
             "choices": [
                 {"label": "Fai sapere che l'erede è vivo, e aspetti", "effects": {"fame": 8, "intrigue": {"branch": "attesa"}}},
                 {"label": "Fai sparire {pedina} prima che parli", "effects": {"karma": -10, "intrigue": {}},
                  "command": "duello {npc}"},
             ]},
            {"title": "Il debito del maestro", "focus": "mandante", "gap": (3, 6),
             "text": "{mandante} viene a riprendersi l'arte del maestro che uccise trecento anni fa.",
             "choices": [
                 {"label": "Paghi il debito del tuo maestro", "effects": {"intrigue": {"end": "vendetta"}},
                  "command": "duello {npc}"},
             ]},
        ],
        "outcomes": {"vendetta_vinto": "Hai vendicato il maestro della grotta.",
                     "vendetta_perso": "Il nemico del tuo maestro ti ha battuto."},
    },
]
