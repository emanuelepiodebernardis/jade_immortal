"""
LE TRAME — intrighi a più atti, scritti a mano, che il regista delle trame sceglie giorno per giorno.

Ogni trama ha un CAST preso dal mondo vivo (i tuoi legami, i rivali delle altre sette, i caduti che
ti cercano) o creato apposta, ATTI distanziati di qualche giorno, INDIZI che raccogli e RAMI che le tue
scelte aprono. L'atto finale cambia con quello che sai: con abbastanza indizi smascheri il mandante;
senza, la verità resta nell'ombra e paghi tu il prezzo.

Ispirazione: le grandi saghe di coltivazione (gli intrighi tra clan e sette, i tornei dove i geni
nascondono la loro forza, i debiti con l'Oltretomba, le eredità degli antichi Dèi-Demoni, le
maledizioni che attraversano le vite, l'isola che appare ogni sessant'anni).

SEGNAPOSTO nei testi: {mandante} {pedina} {vittima} {genio} {luogo} {npc} (chi è
in scena in quell'atto).

PER AGGIUNGERE UNA TRAMA basta un dizionario in TEMPLATES:
  key, title, kind, weight, tier_min, (req_sect), cast {ruolo: tipo}, acts [ {title, focus, gap, text,
  (text_dead {ruolo: testo}), choices [...]} ], outcomes {chiave: testo}
  Le scelte sono quelle degli incontri (check/success/failure/effects/command) più:
    "need_clues": n        la scelta compare solo con almeno n indizi
    "need_branch": "x"     … solo se hai preso il ramo x
    nei dizionari di effetto, "intrigue": {"clue": n, "branch": "x", "end": "esito"}
  Tipi di cast: rivale (un potente di un'altra setta), alleato (un tuo legame o compagno di setta),
  sgherro, genio, spettro, anziano.
"""

from __future__ import annotations

_P = {"rank": 2, "kinds": ["pillola", "tesoro"]}
_P3 = {"rank": 3, "kinds": ["tesoro", "manuale", "pillola"]}
_P4 = {"rank": 4, "kinds": ["tesoro", "manuale"]}

TEMPLATES: list[dict] = [
    # ------------------------------------------------------------------ 1. LA MANO NELL'OMBRA
    {
        "key": "mano_ombra", "title": "La mano nell'ombra", "kind": "intrigo", "weight": 6, "tier_min": 2,
        "cast": {"vittima": "alleato", "pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "Il cadavere al pozzo", "focus": "vittima", "gap": (2, 3),
             "text": ("All'alba trovano un discepolo {della_setta} riverso accanto al pozzo di {luogo}, la gola "
                      "aperta da una lama di Qi. Accanto al corpo, un ciondolo di giada: quello di {vittima}. "
                      "{La_setta} esige il colpevole entro tre giorni, o sarà guerra. {vittima} ti guarda: "
                      "«Non sono stato io. Lo giuro sul mio Dao.»"),
             "choices": [
                 {"label": "Esamini il corpo prima che lo portino via",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": ("La ferita è troppo pulita: un colpo dall'alto, da qualcuno molto più forte. "
                                       "E sotto le unghie, terra rossa che qui non esiste."),
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Le guardie della setta ti allontanano prima che tu capisca qualcosa.",
                              "intrigue": {}}},
                 {"label": "Difendi {vittima} davanti a tutti: «Rispondo io per lui»",
                  "effects": {"fame": 4, "relation": 15, "text": "Un mormorio attraversa la folla. Ora ci sei dentro anche tu.",
                              "intrigue": {"branch": "garante"}}},
                 {"label": "Consegni {vittima} {alla_setta}: non è affar tuo",
                  "effects": {"relation": -40, "karma": -10, "infamy": 3,
                              "text": "{vittima} non dice nulla. Ti guarda soltanto, mentre lo legano.",
                              "intrigue": {"branch": "tradito"}}},
             ]},
            {"title": "L'uomo con la terra rossa", "focus": "pedina", "gap": (2, 4),
             "text": ("Un vagabondo, {pedina}, spende pietre spirituali come un principe nelle bettole di {luogo}. "
                      "Ha gli stivali sporchi di terra rossa e la mano destra fasciata. Quando ti vede, posa la "
                      "coppa troppo in fretta."),
             "choices": [
                 {"label": "Lo segui da lontano fino al suo nascondiglio",
                  "check": {"stat": "istinto", "dc": 62},
                  "success": {"text": ("Lo vedi consegnare un sacchetto a un emissario con il sigillo {della_setta}: "
                                       "è la stessa setta del morto. Qualcuno dentro di loro vuole questa guerra."),
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Svolta in un vicolo e sparisce. Ma ora sa che lo cerchi.",
                              "intrigue": {"branch": "allarmato"}}},
                 {"label": "Lo affronti e lo costringi a parlare",
                  "effects": {"text": "«Parlerò solo se mi batti!» Sguaina una spada troppo buona per un vagabondo.",
                              "intrigue": {"clue": 1}},
                  "command": "duello {npc}"},
                 {"label": "Paghi un informatore del mercato nero (300 pietre)",
                  "effects": {"stones": -300, "text": ("«Quello? Lavora per un anziano. Non so quale. So solo che lo "
                                                       "pagano in pillole di prima qualità.»"),
                              "intrigue": {"clue": 1}}},
             ]},
            {"title": "Il terzo giorno", "focus": "mandante", "gap": (2, 3),
             "text": ("Il terzo giorno {la_setta} si raduna nella piazza di {luogo}. A guidarla c'è {mandante}, "
                      "che con voce grave chiede vendetta per il discepolo ucciso. È lo stesso uomo che, "
                      "tu lo sai, ha pagato {pedina}."),
             "text_low": ("Il terzo giorno {la_setta} si raduna nella piazza di {luogo}. A guidarla c'è "
                          "{mandante}: chiede la testa di {vittima}, e nessuno ha prove per fermarlo."),
             "choices": [
                 {"label": "Smascheri {mandante} davanti a tutti, prove alla mano",
                  "need_clues": 2,
                  "effects": {"fame": 15, "karma": 25, "prize": _P3,
                              "text": ("Il ciondolo, la terra rossa, l'emissario, le pietre: pezzo dopo pezzo la "
                                       "piazza capisce. {mandante} impallidisce, poi fugge. La guerra non ci sarà."),
                              "intrigue": {"end": "smascherato"}}},
                 {"label": "Lo sfidi a duello: che decida il Cielo",
                  "effects": {"fame": 6, "text": "«Insolente.» Il potere di {mandante} schiaccia la piazza.",
                              "intrigue": {"end": "duello"}},
                  "command": "duello {npc}"},
                 {"label": "Vai da lui di notte e gli offri il tuo silenzio, a caro prezzo",
                  "need_clues": 1,
                  "effects": {"stones": 1500, "infamy": 8, "karma": -20,
                              "text": ("{mandante} sorride senza allegria e ti allunga un sacchetto pesante. «Saggio. "
                                       "Siamo uguali, noi due.» Il giorno dopo la colpa ricade su {pedina}."),
                              "intrigue": {"end": "ricatto"}}},
                 {"label": "Liberi {vittima} con la forza e fuggite insieme",
                  "need_branch": "garante",
                  "check": {"stat": "potenza", "dc": 60},
                  "success": {"relation": 40, "infamy": 6, "text": "Fuggite tra le frecce. {vittima} non lo dimenticherà mai.",
                              "intrigue": {"end": "fuga"}},
                  "failure": {"injury": 3, "text": "Vi circondano. Ne esci vivo per miracolo, solo.",
                              "intrigue": {"end": "perduto"}}},
                 {"label": "Lasci che la giustizia della setta faccia il suo corso",
                  "effects": {"karma": -15, "text": "La testa di {vittima} rotola sulla pietra. {mandante} ti guarda e annuisce.",
                              "intrigue": {"end": "perduto"}}},
             ]},
        ],
        "outcomes": {"smascherato": "Hai smascherato {mandante}: la guerra tra le sette è evitata.",
                     "duello": "Hai sfidato {mandante} davanti alla sua setta.",
                     "ricatto": "Hai venduto il tuo silenzio a {mandante}.",
                     "fuga": "Hai strappato {vittima} alla morte.",
                     "perduto": "{vittima} è caduto per un delitto che non aveva commesso."},
    },
    # ------------------------------------------------------------------ 2. IL TORNEO TRUCCATO
    {
        "key": "torneo_truccato", "title": "Il Torneo delle Cento Sette", "kind": "torneo", "weight": 7, "tier_min": 1,
        "cast": {"pedina": "sgherro", "genio": "genio", "mandante": "rivale"},
        "acts": [
            {"title": "L'invito e il patto", "focus": "pedina", "gap": (1, 2),
             "text": ("A {luogo} si apre il Torneo delle Cento Sette: cento giovani, un solo vincitore, e per lui "
                      "un posto ai piedi dei Venerabili. La sera prima, {pedina} ti trova in locanda e posa sul "
                      "tavolo un sacchetto gonfio: «Perdi al terzo turno. Il mio padrone paga bene, e ricorda chi "
                      "gli fa un favore.»"),
             "choices": [
                 {"label": "Accetti il denaro (800 pietre): perderai al terzo turno",
                  "effects": {"stones": 800, "infamy": 3, "text": "«Bravo. Il mio padrone ti terrà d'occhio.»",
                              "intrigue": {"branch": "venduto"}}},
                 {"label": "Rifiuti: combatterai per vincere",
                  "effects": {"text": "{pedina} si alza senza una parola. Sulla porta si volta: «Peccato.»",
                              "intrigue": {"branch": "onesto"}}},
                 {"label": "Fingi di accettare e porti il sacchetto ai giudici",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"fame": 4, "text": ("I giudici riconoscono il sigillo sul sacchetto: è {della_setta}. "
                                                  "Non dicono nulla, ma ora sanno."),
                              "intrigue": {"clue": 1, "branch": "onesto"}},
                  "failure": {"text": "I giudici fanno sparire il sacchetto. Forse sono comprati anche loro.",
                              "intrigue": {"branch": "onesto"}}},
             ]},
            {"title": "Il veleno nella lama", "focus": "pedina", "gap": (1, 2),
             "text": ("Secondo turno. Il tuo avversario è {pedina} in persona, iscritto all'ultimo momento. Quando "
                      "sguaina, la lama manda un riflesso verdastro: veleno dei Cento Serpenti, vietato dal regolamento."),
             "choices": [
                 {"label": "Combatti lo stesso: il veleno non ti fermerà",
                  "effects": {"fame": 4, "intrigue": {}}, "command": "duello {npc}"},
                 {"label": "Fermi l'incontro e mostri il veleno ai giudici",
                  "check": {"stat": "anima", "dc": 58},
                  "success": {"fame": 6, "text": ("Il giudice annusa la lama e la spezza sul ginocchio. {pedina} viene "
                                                  "squalificato, e prima di andarsene ti sibila un nome: {mandante}."),
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "«Nessun veleno», sentenzia il giudice senza guardare. Il duello comincia.",
                              "intrigue": {}}, "command": ""},
             ]},
            {"title": "Il genio che nasconde la sua forza", "focus": "genio", "gap": (1, 2),
             "text": ("Semifinale. {genio} ha vinto ogni incontro con un solo colpo, sempre lo stesso, senza mai "
                      "usare la mano sinistra. Gli spettatori lo chiamano «il Muto». Prima di salire sulla pedana "
                      "ti dice, a bassa voce: «Il tuo prossimo avversario non sono io. È chi ha comprato i giudici.»"),
             "text_branch": {"venduto": ("Semifinale: è il terzo turno, quello che hai promesso di perdere. Davanti "
                                         "a te {genio}, che non sa nulla del patto, ti saluta con rispetto.")},
             "choices": [
                 {"label": "Combatti al massimo",
                  "effects": {"fame": 6, "intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Perdi apposta, come promesso",
                  "need_branch": "venduto",
                  "effects": {"stones": 400, "infamy": 6, "fame": -8, "karma": -15,
                              "text": "Cadi al primo scambio. Il pubblico fischia. {pedina}, in tribuna, applaude da solo.",
                              "intrigue": {"end": "venduto"}}},
                 {"label": "Ti allei con {genio}: insieme scoprirete chi trucca il torneo",
                  "check": {"stat": "karma", "dc": 55},
                  "success": {"relation": 30, "bond": "companion",
                              "text": "Vi stringete il polso. «Dopo il torneo», dice. «Prima la verità.»",
                              "intrigue": {"clue": 1, "branch": "alleanza"}},
                  "failure": {"text": "Ti guarda a lungo, poi scuote la testa: «Non mi fido di nessuno, qui.»",
                              "intrigue": {}}},
             ]},
            {"title": "La finale", "focus": "mandante", "gap": (1, 2),
             "text": ("Finale. Contro ogni regola, a sfidarti scende {mandante} in persona, «per onorare il "
                      "torneo». I giudici non fiatano: sono suoi. Tutta la città trattiene il fiato."),
             "choices": [
                 {"label": "Accetti la finale",
                  "effects": {"fame": 10, "prize": _P3,
                              "text": "Il gong suona. Cento sette guardano la pedana.",
                              "intrigue": {"end": "finale"}}, "command": "duello {npc}"},
                 {"label": "Denunci il torneo truccato davanti ai Venerabili",
                  "need_clues": 2,
                  "effects": {"fame": 18, "karma": 20, "prize": _P4,
                              "text": ("Il sigillo, il veleno, il nome sussurrato: i Venerabili ascoltano. {mandante} "
                                       "è cacciato con disonore, e la vittoria è assegnata a te."),
                              "intrigue": {"end": "denuncia"}}},
                 {"label": "Ti ritiri: questo torneo non vale la tua vita",
                  "effects": {"fame": -5, "text": "Scendi dalla pedana tra i fischi. Ma sei vivo.",
                              "intrigue": {"end": "ritiro"}}},
             ]},
        ],
        "outcomes": {"finale": "Hai combattuto la finale contro {mandante}.",
                     "denuncia": "Hai svelato il torneo truccato: la vittoria è tua.",
                     "venduto": "Hai venduto il torneo.", "ritiro": "Ti sei ritirato dalla finale."},
    },
    # ------------------------------------------------------------------ 3. IL DEBITO DELL'OLTRETOMBA
    {
        "key": "debito_oltretomba", "title": "Il debito dell'Oltretomba", "kind": "mistero", "weight": 4, "tier_min": 3,
        "cast": {"pedina": "spettro", "mandante": "anziano"},
        "acts": [
            {"title": "Il messaggero dalla lanterna verde", "focus": "pedina", "gap": (2, 4),
             "text": ("A mezzanotte la tua candela si fa verde. Sulla soglia c'è {pedina}, con una lanterna che non "
                      "fa ombra e un rotolo di pelle nera: «In una vita passata hai preso in prestito trent'anni dal "
                      "Registro della Vita e della Morte. Il Re dei Mille Inferi chiede che siano restituiti.»"),
             "choices": [
                 {"label": "Paghi: trent'anni della tua vita",
                  "effects": {"lifespan_years": -30, "karma": 15,
                              "text": "Senti qualcosa scivolare via dalle ossa. Il messaggero si inchina e svanisce.",
                              "intrigue": {"end": "pagato"}}},
                 {"label": "Chiedi di vedere il Registro con i tuoi occhi",
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"text": ("Sul rotolo il tuo nome c'è. Ma l'inchiostro è fresco, e la firma accanto non "
                                       "è del Re dei Mille Inferi: è di un uomo vivo."),
                              "intrigue": {"clue": 2}},
                  "failure": {"text": "Il rotolo ti brucia gli occhi. «Hai tre giorni», dice la voce.",
                              "intrigue": {"clue": 0}}},
                 {"label": "Lo cacci con la forza",
                  "effects": {"text": "La lanterna si spegne. Ma il freddo non se ne va.", "intrigue": {}},
                  "command": "duello {npc}"},
             ]},
            {"title": "Il falsario dei registri", "focus": "mandante", "gap": (2, 4),
             "text": ("Segui la traccia dell'inchiostro fresco fino a {mandante}, un vecchio che vende «debiti "
                      "dell'Oltretomba» a chi ha nemici: un nome sul rotolo, e uno spettro va a riscuotere. Qualcuno "
                      "ha comprato il tuo nome."),
             "text_low": ("Il freddo non ti lascia. Al terzo giorno un vecchio, {mandante}, si presenta alla tua "
                          "porta: «Posso cancellare il tuo debito. Per un prezzo.»"),
             "choices": [
                 {"label": "Lo costringi a dirti chi ha comprato il tuo nome",
                  "need_clues": 2,
                  "effects": {"karma": 20, "lifespan_years": 20, "prize": _P,
                              "text": ("Il vecchio trema e confessa: il nome lo ha comprato un tuo vecchio nemico. "
                                       "Bruci il rotolo: dal fuoco escono vent'anni che non sapevi di avere."),
                              "intrigue": {"end": "smascherato"}}},
                 {"label": "Paghi il vecchio perché cancelli il debito (2000 pietre)",
                  "effects": {"stones": -2000, "text": "Il vecchio cancella il tuo nome con un colpo di pennello.",
                              "intrigue": {"end": "comprato"}}},
                 {"label": "Lo sfidi: il suo commercio finisce qui",
                  "effects": {"karma": 10, "intrigue": {"end": "duello"}}, "command": "duello {npc}"},
             ]},
        ],
        "outcomes": {"pagato": "Hai pagato all'Oltretomba un debito che forse non era tuo.",
                     "smascherato": "Hai scoperto il falsario dei registri dell'Oltretomba.",
                     "comprato": "Hai comprato la cancellazione del tuo debito.",
                     "duello": "Hai sfidato il falsario dei registri."},
    },
    # ------------------------------------------------------------------ 4. L'EREDITÀ DEL DIO-DEMONE
    {
        "key": "eredita_dio_demone", "title": "L'eredità del Dio-Demone", "kind": "eredita", "weight": 5, "tier_min": 3,
        "cast": {"vittima": "alleato", "genio": "genio", "mandante": "rivale"},
        "acts": [
            {"title": "La mappa nell'osso", "focus": "vittima", "gap": (2, 3),
             "text": ("{vittima} ti porta un osso lungo come un braccio, inciso di rune che si muovono: «L'ho comprato "
                      "per niente da un mercante di Monte. È una mappa. Porta alla tomba di un Dio-Demone delle ere "
                      "antiche, uno di quelli che avevano tre teste e sei braccia.» Ma la notizia corre: anche "
                      "{genio} e {la_setta} la cercano."),
             "choices": [
                 {"label": "Decifri le rune",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"text": "Le rune indicano un passaggio laterale che nessun altro conosce.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Le rune ti girano davanti agli occhi. Andrete per la via principale.",
                              "intrigue": {}}},
                 {"label": "Partite subito, prima degli altri",
                  "effects": {"text": "Partite all'alba, leggeri.", "intrigue": {"branch": "rapidi"}}},
             ]},
            {"title": "L'imboscata del genio", "focus": "genio", "gap": (2, 3),
             "text": ("All'ingresso della valle, {genio} vi aspetta seduto su una roccia. «La tomba è mia. Andatevene, "
                      "e vivrete.» Dietro di lui, lontano, i vessilli {della_setta}."),
             "choices": [
                 {"label": "Lo affronti",
                  "effects": {"fame": 5, "intrigue": {}}, "command": "duello {npc}"},
                 {"label": "Gli proponi di dividere l'eredità contro {la_setta}",
                  "check": {"stat": "karma", "dc": 55},
                  "success": {"relation": 25, "text": "Ci pensa. Poi sorride: «Prima loro. Poi vedremo.»",
                              "intrigue": {"branch": "patto"}},
                  "failure": {"text": "«Non divido nulla.» Si alza. Il duello è inevitabile.", "intrigue": {}},
                  "command": ""},
                 {"label": "Prendete il passaggio laterale delle rune",
                  "need_clues": 1,
                  "effects": {"text": "Scivolate nella roccia mentre lui aspetta ancora sulla strada.",
                              "intrigue": {"clue": 1}}},
             ]},
            {"title": "Le tre prove del Dio-Demone", "focus": "vittima", "gap": (2, 3),
             "text": ("Nella tomba, una statua con tre teste e sei braccia apre gli occhi: «Carne, anima, volontà. "
                      "Supera le tre prove e avrai il mio retaggio.» Alle tue spalle {vittima} ha lo sguardo strano: "
                      "fissa la statua come un affamato."),
             "choices": [
                 {"label": "Affronti la prova della carne",
                  "check": {"stat": "corpo", "dc": 64},
                  "success": {"prize": _P4, "lifespan_years": 30,
                              "text": ("Le sei braccia ti colpiscono insieme e tu resti in piedi. La statua si "
                                       "inchina: un frammento della sua arte scorre in te."),
                              "intrigue": {"clue": 1, "branch": "erede"}},
                  "failure": {"injury": 3, "text": "Le braccia di pietra ti spezzano le costole. Ma sei vivo.",
                              "intrigue": {}}},
                 {"label": "Lasci la prova a {vittima}, che l'ha trovata",
                  "effects": {"relation": 30, "karma": 15,
                              "text": "{vittima} entra nel cerchio di luce. Quando ne esce, non ti guarda più allo stesso modo.",
                              "intrigue": {"branch": "generoso"}}},
             ]},
            {"title": "Il tradimento nella tomba", "focus": "vittima", "gap": (1, 2),
             "text": ("Mentre uscite, {vittima} si ferma sulla soglia. «Mi dispiace», dice. Dalla valle salgono i "
                      "vessilli {della_setta}: guidati da {mandante}, e qualcuno li ha chiamati."),
             "text_branch": {"generoso": ("Mentre uscite, {vittima} ti posa una mano sulla spalla: «Mi avevano "
                                          "pagato per tradirti. Non lo farò.» Dalla valle sale {mandante} con "
                                          "{la_setta}. Siete in due, ora.")},
             "choices": [
                 {"label": "Affronti {mandante} all'uscita della tomba",
                  "effects": {"fame": 10, "intrigue": {"end": "battaglia"}}, "command": "duello {mandante}"},
                 {"label": "Perdoni {vittima} e fuggite insieme",
                  "need_branch": "generoso",
                  "effects": {"relation": 40, "bond": "companion",
                              "text": "Correte nella notte, con il retaggio del Dio-Demone e un amico vero.",
                              "intrigue": {"end": "amicizia"}}},
                 {"label": "Colpisci {vittima} prima che ti colpisca",
                  "effects": {"karma": -10, "relation": -60, "intrigue": {"end": "tradimento"}},
                  "command": "duello {npc}"},
             ]},
        ],
        "outcomes": {"battaglia": "Hai difeso l'eredità del Dio-Demone da {mandante}.",
                     "amicizia": "Hai conquistato l'eredità e un amico vero.",
                     "tradimento": "{vittima} ti ha tradito nella tomba del Dio-Demone."},
    },
    # ------------------------------------------------------------------ 5. LA MALEDIZIONE DELLA VITA PASSATA
    {
        "key": "maledizione", "title": "La maledizione della vita passata", "kind": "maledizione", "weight": 4,
        "tier_min": 2, "cast": {"pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "Il filo nero", "focus": None, "gap": (2, 4),
             "text": ("Da tre notti sogni la stessa cosa: un filo nero che ti esce dal petto e si perde a nord. Al "
                      "risveglio il Qi scorre più lento, e sul polso è comparso un segno che non avevi. Qualcuno ti "
                      "sta maledicendo attraverso le vite."),
             "choices": [
                 {"label": "Segui il filo in meditazione",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"text": "Il filo porta a un altare d'ossa, e su di esso la tua vecchia faccia, scolpita.",
                              "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "Il filo ti strattona e ti sveglia col sangue in bocca.",
                              "intrigue": {}}},
                 {"label": "Bruci incenso purificatore e aspetti",
                  "effects": {"heart": 3, "text": "Il segno sul polso impallidisce. Per ora.", "intrigue": {}}},
             ]},
            {"title": "Il custode dell'altare", "focus": "pedina", "gap": (2, 4),
             "text": ("A nord trovi l'altare d'ossa, e a custodirlo {pedina}, che ogni notte vi versa sangue. «Non "
                      "è niente di personale», ti dice. «Mi pagano per tenere acceso il fuoco.»"),
             "choices": [
                 {"label": "Lo costringi a parlare",
                  "effects": {"intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Spezzi l'altare senza combattere",
                  "check": {"stat": "potenza", "dc": 60},
                  "success": {"text": "L'altare si incrina. Dentro, una tavoletta con un sigillo: {della_setta}.",
                              "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "L'altare ti respinge. {pedina} scappa a dare l'allarme.",
                              "intrigue": {}}},
             ]},
            {"title": "Chi tiene il filo", "focus": "mandante", "gap": (2, 4),
             "text": ("Il filo nero finisce nelle mani di {mandante}, {della_setta}. In una vita passata tu gli hai "
                      "tolto tutto; in questa lui ha aspettato cent'anni per riprendersi la rivincita."),
             "text_low": ("La maledizione si stringe. Un giorno, sulla strada, ti si para davanti {mandante}: «Mi "
                          "riconosci? No, certo. Ma io riconosco te.»"),
             "choices": [
                 {"label": "Tagli il filo davanti ai suoi occhi",
                  "need_clues": 2,
                  "effects": {"karma": 15, "heart": 8, "prize": _P3,
                              "text": ("Con gli indizi trovi il nodo del filo e lo recidi. {mandante} vomita sangue: "
                                       "la maledizione torna a chi l'ha lanciata."),
                              "intrigue": {"end": "spezzata"}}},
                 {"label": "Lo sfidi: una vita per una vita",
                  "effects": {"fame": 8, "intrigue": {"end": "duello"}}, "command": "duello {npc}"},
                 {"label": "Gli chiedi perdono per ciò che fu",
                  "check": {"stat": "karma", "dc": 62},
                  "success": {"karma": 30, "heart": 10,
                              "text": "Lo vedi esitare. Poi lascia cadere il filo. «Cent'anni… per niente.»",
                              "intrigue": {"end": "perdono"}},
                  "failure": {"injury": 3, "text": "Ride. Il filo si stringe ancora.", "intrigue": {"end": "duello"}},
                  "command": ""},
             ]},
        ],
        "outcomes": {"spezzata": "Hai spezzato la maledizione della vita passata.",
                     "duello": "Hai affrontato chi ti maledisse attraverso le vite.",
                     "perdono": "Hai chiuso con il perdono un odio di due vite."},
    },
    # ------------------------------------------------------------------ 6. IL TRADITORE NELLA SETTA
    {
        "key": "traditore_setta", "title": "Il traditore {della_mia_setta}", "kind": "intrigo", "weight": 5,
        "tier_min": 2, "req_sect": True, "cast": {"vittima": "alleato", "pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "Le pillole che spariscono", "focus": "vittima", "gap": (2, 3),
             "text": ("Nel tesoro {della_mia_setta} mancano pillole da tre mesi, e due discepoli sono morti in missioni "
                      "che il nemico sembrava conoscere in anticipo. Il vecchio custode ti chiama in disparte: «C'è "
                      "un traditore. Tu sei nuovo: di te posso fidarmi.» {vittima} è tra i sospettati."),
             "choices": [
                 {"label": "Controlli i registri del tesoro",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "Le firme dei prelievi sono di {pedina}: un discepolo esterno senza alcun diritto.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "I registri sono stati riscritti. Chiunque sia, è prudente.", "intrigue": {}}},
                 {"label": "Parli con {vittima}",
                  "effects": {"relation": 10, "text": "«Mi accusano perché sono povero», dice. «Aiutami.»",
                              "intrigue": {"branch": "fiducia"}}},
             ]},
            {"title": "Il messaggio nel nido di gru", "focus": "pedina", "gap": (2, 3),
             "text": ("Di notte vedi {pedina} arrampicarsi sul tetto e infilare un biglietto in un nido di gru. "
                      "All'alba una gru vola verso le terre {della_setta}."),
             "choices": [
                 {"label": "Intercetti la gru",
                  "check": {"stat": "istinto", "dc": 60},
                  "success": {"text": "Il biglietto porta il sigillo di {mandante}, anziano {della_setta}.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "La gru è troppo veloce.", "intrigue": {}}},
                 {"label": "Affronti {pedina} sul tetto",
                  "effects": {"intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Lo lasci fare e gli fai arrivare informazioni false",
                  "effects": {"text": "Il prossimo biglietto lo scrivi tu.",
                              "intrigue": {"branch": "doppio_gioco", "clue": 1}}},
             ]},
            {"title": "La resa dei conti", "focus": "mandante", "gap": (2, 3),
             "text": ("{La_setta} attacca un convoglio {della_mia_setta}, come previsto. A guidarli c'è {mandante}."),
             "text_branch": {"doppio_gioco": ("Grazie ai tuoi biglietti falsi, {mandante} {della_setta} cade "
                                              "dritto nella trappola {della_mia_setta}: lo aspettate in una gola.")},
             "choices": [
                 {"label": "Smascheri il traditore davanti al consiglio della setta",
                  "need_clues": 2,
                  "effects": {"merit": 300, "fame": 10, "sect_influence": 5, "prize": _P3,
                              "text": "{pedina} viene giudicato. {vittima} è libero. Il consiglio ti guarda con occhi nuovi.",
                              "intrigue": {"end": "smascherato"}}},
                 {"label": "Affronti {mandante} nella gola",
                  "effects": {"fame": 10, "merit": 150, "intrigue": {"end": "battaglia"}}, "command": "duello {npc}"},
                 {"label": "Lasci che accusino {vittima}: è più semplice",
                  "effects": {"karma": -20, "relation": -50, "text": "Il traditore vero resta. E ora sa che tu sai.",
                              "intrigue": {"end": "perduto"}}},
             ]},
        ],
        "outcomes": {"smascherato": "Hai smascherato il traditore della setta.",
                     "battaglia": "Hai affrontato {mandante} che manovrava il traditore.",
                     "perduto": "Hai lasciato che un innocente pagasse al posto del traditore."},
    },
    # ------------------------------------------------------------------ 7. L'ISOLA DELLA SPADA NASCOSTA
    {
        "key": "isola_spada", "title": "L'Isola della Spada Nascosta", "kind": "torneo", "weight": 4, "tier_min": 4,
        "cast": {"genio": "genio", "pedina": "genio", "mandante": "anziano"},
        "acts": [
            {"title": "L'isola che appare ogni sessant'anni", "focus": "genio", "gap": (2, 3),
             "text": ("Dal mare si alza la nebbia, e nella nebbia un'isola: la Spada Nascosta, che appare una volta "
                      "ogni sessant'anni. Sulla spiaggia, cento spade piantate nella sabbia. Solo chi ne estrae una "
                      "può salire. Accanto a te, {genio} ne afferra già l'elsa."),
             "choices": [
                 {"label": "Estrai la spada che ti chiama",
                  "check": {"stat": "coltivazione", "dc": 58},
                  "success": {"text": "La spada esce come da un fodero d'acqua. Ti senti osservato da qualcosa di antico.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "La spada non si muove. Ne prendi un'altra, più umile.", "intrigue": {}}},
                 {"label": "Osservi gli altri prima di scegliere",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Noti che le spade migliori sono quelle che nessuno guarda.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Mentre guardi, le spade migliori se ne vanno.", "intrigue": {}}},
             ]},
            {"title": "La scala delle novantanove spade", "focus": "pedina", "gap": (1, 2),
             "text": ("Una scala di novantanove gradini: su ognuno l'eco di un maestro morto ti attacca. A metà "
                      "salita, {pedina} ti sbarra la strada: «Solo uno arriva in cima. Meglio scoprire subito chi.»"),
             "choices": [
                 {"label": "Combatti sulla scala",
                  "effects": {"fame": 6, "intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Lo superi senza combattere, gradino dopo gradino",
                  "check": {"stat": "corpo", "dc": 62},
                  "success": {"text": "Lui si consuma contro gli echi; tu sali come la marea.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "Gli echi ti feriscono. Arrivi in cima per ultimo.", "intrigue": {}}},
             ]},
            {"title": "Il custode della spada", "focus": "mandante", "gap": (1, 2),
             "text": ("In cima, una spada senza lama infissa in un trono di pietra. La custodisce {mandante}, che vive "
                      "sull'isola da sessant'anni e non vuole andarsene: «Se la prendi, l'isola affonda. Con me "
                      "dentro.»"),
             "choices": [
                 {"label": "Lo sfidi per la spada",
                  "effects": {"fame": 12, "prize": _P4, "intrigue": {"end": "spada"}}, "command": "duello {npc}"},
                 {"label": "Comprendi la spada senza lama, senza toccarla",
                  "need_clues": 2,
                  "effects": {"prize": _P4, "heart": 6, "fame": 10,
                              "text": ("Capisci: la lama è l'intento. Lo porti via dentro di te, e l'isola resta. Il "
                                       "custode ti saluta da lontano, mentre la nebbia si richiude."),
                              "intrigue": {"end": "intento"}}},
                 {"label": "Lasci la spada al custode",
                  "effects": {"karma": 20, "text": "Scendi la scala. Dietro di te, il custode piange.",
                              "intrigue": {"end": "rinuncia"}}},
             ]},
        ],
        "outcomes": {"spada": "Hai conquistato la Spada Nascosta.",
                     "intento": "Hai compreso l'intento della Spada Nascosta senza toccarla.",
                     "rinuncia": "Hai lasciato la Spada Nascosta al suo custode."},
    },
]
