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

# premi (rewards.grant: rank 1 = oro, 2 = argento, 3 = bronzo)
_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}

TEMPLATES: list[dict] = [
    # ------------------------------------------------------------------ 1. LA MANO NELL'OMBRA
    {
        "key": "mano_ombra",
        "indagine": "istinto", "need": 2, "reveal_act": 2, "indizi": ["La ferita è un colpo dall'alto, di qualcuno molto più forte del morto: non può essere stato {vittima}.", "Sotto le unghie del morto c'è terra rossa, che a {luogo} non esiste: viene dalle colline a nord.", '{pedina}, un vagabondo con gli stivali rossi di quella terra, spende pietre che non può avere.', "{pedina} consegna i suoi guadagni a un emissario col sigillo di {mandante}: è lui la mano nell'ombra."],
         "title": "La mano nell'ombra", "kind": "intrigo", "weight": 6, "tier_min": 2,
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
                  "effects": {"fame": 15, "karma": 25, "prize": _ARGENTO,
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
        "key": "torneo_truccato",
        "indagine": "istinto", "need": 2, "reveal_act": None, "indizi": ['Il sacchetto offerto per perdere porta il sigillo {della_setta}.', 'Le lame di {pedina} sono unte di veleno dei Cento Serpenti, vietato dal regolamento.', 'Tre giudici su cinque hanno ricevuto doni dalla stessa mano.', 'Chi paga giudici e sicari è {mandante}: vuole il posto dei Venerabili per un suo protetto.'],
         "title": "Il Torneo delle Cento Sette", "kind": "torneo", "weight": 7, "tier_min": 1,
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
                  "effects": {"fame": 10, "prize": _ARGENTO,
                              "text": "Il gong suona. Cento sette guardano la pedana.",
                              "intrigue": {"end": "finale"}}, "command": "duello {npc}"},
                 {"label": "Denunci il torneo truccato davanti ai Venerabili",
                  "need_clues": 2,
                  "effects": {"fame": 18, "karma": 20, "prize": _ORO,
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
        "key": "debito_oltretomba",
        "indagine": "anima", "need": 2, "reveal_act": 1, "indizi": ["Il rotolo del debito ha l'inchiostro fresco: non può venire dall'Oltretomba.", 'La firma accanto al tuo nome è di un uomo vivo, non del Re dei Mille Inferi.', "Al mercato nero si vendono «debiti dell'Oltretomba»: un nome sul rotolo, e uno spettro va a riscuotere.", 'Il falsario è {mandante}, un vecchio che lavora per chi ha nemici da far sparire.'],
         "title": "Il debito dell'Oltretomba", "kind": "mistero", "weight": 4, "tier_min": 3,
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
                  "effects": {"karma": 20, "lifespan_years": 20, "prize": _BRONZO,
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
                  "success": {"prize": _ORO, "lifespan_years": 30,
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
        "key": "maledizione",
        "indagine": "anima", "need": 2, "reveal_act": 2, "indizi": ["Il filo nero ti esce dal petto e si perde a nord: qualcuno tiene l'altro capo.", "A nord c'è un altare d'ossa con la tua vecchia faccia scolpita: lo custodisce {pedina}.", "Sotto l'altare, una tavoletta col sigillo {della_setta}.", 'Chi tiene il filo è {mandante}: in una vita passata gli hai tolto tutto.'],
         "title": "La maledizione della vita passata", "kind": "maledizione", "weight": 4,
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
                  "effects": {"karma": 15, "heart": 8, "prize": _ARGENTO,
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
        "key": "traditore_setta",
        "indagine": "istinto", "need": 2, "reveal_act": 2, "indizi": ['Le firme dei prelievi dal tesoro sono di {pedina}, un discepolo esterno senza diritto di firma.', 'Di notte {pedina} lascia biglietti in un nido di gru sul tetto.', 'Le gru volano verso le terre {della_setta}.', 'I biglietti portano il sigillo di {mandante}, anziano {della_setta}: è lui che compra il traditore.'],
         "title": "Il traditore {della_mia_setta}", "kind": "intrigo", "weight": 5,
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
                  "effects": {"merit": 300, "fame": 10, "sect_influence": 5, "prize": _ARGENTO,
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
                  "effects": {"fame": 12, "prize": _ORO, "intrigue": {"end": "spada"}}, "command": "duello {npc}"},
                 {"label": "Comprendi la spada senza lama, senza toccarla",
                  "need_clues": 2,
                  "effects": {"prize": _ORO, "heart": 6, "fame": 10,
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


# ======================================================================================================
# TRAME CHE SI CONCLUDONO DA SOLE — l'ultimo atto non chiede una scelta: racconta come finisce, con il
# premio che ti sei guadagnato (indizi e rami decidono quale finale). "auto_end" decide anche come
# finiscono se le lasci a metà.
# ======================================================================================================

_RELIQUIA = {"rank": 1, "kinds": ["reliquia", "tesoro"]}
_SANGUE = {"rank": 2, "kinds": ["sangue", "nucleo"]}
_CORPO = {"rank": 1, "kinds": ["corpo", "manuale"]}

TEMPLATES += [
    # ------------------------------------------------------------------ 8. IL REAME SEGRETO
    {
        "key": "reame_mille_tesori", "title": "Il Reame dei Mille Tesori", "kind": "reame", "weight": 6, "tier_min": 2,
        "cast": {"genio": "genio", "vittima": "alleato"},
        "acts": [
            {"title": "La porta nella cascata", "focus": "vittima", "gap": (2, 3),
             "text": ("Dietro la cascata vicino a {luogo} si è aperta una porta di luce: un reame segreto, sigillato "
                      "da mille anni, che resterà aperto sette giorni. Le sette mandano i loro discepoli migliori. "
                      "{vittima} ti chiede di entrare insieme."),
             "choices": [
                 {"label": "Entri con {vittima}",
                  "effects": {"relation": 10, "text": "Varcate insieme la luce.", "intrigue": {"branch": "insieme"}}},
                 {"label": "Entri da solo: nel reame non ci si fida di nessuno",
                  "effects": {"text": "Varchi la luce da solo.", "intrigue": {"branch": "solo"}}},
                 {"label": "Studi la porta prima di entrare",
                  "check": {"stat": "anima", "dc": 56},
                  "success": {"text": "Le rune dicono dove batte il cuore del reame: al centro, sotto il lago.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Le rune non ti dicono niente. Entri alla cieca.", "intrigue": {}}},
             ]},
            {"title": "L'erba dei mille anni", "focus": "genio", "gap": (1, 2),
             "text": ("Su una rupe cresce un'Erba dei Mille Anni, custodita da un serpente di giada. {genio} è già lì, "
                      "e sta per attaccare il serpente da solo."),
             "choices": [
                 {"label": "Aspetti che si sfianchino e prendi l'erba",
                  "check": {"stat": "istinto", "dc": 60},
                  "success": {"prize": {"rank": 2, "kinds": ["pillola"]}, "infamy": 2,
                              "text": "Mentre il serpente stritola {genio}, l'erba è tua.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "Il serpente ti vede. Fuggi con le mani vuote.", "intrigue": {}}},
                 {"label": "Aiuti {genio} contro il serpente",
                  "check": {"stat": "potenza", "dc": 58},
                  "success": {"relation": 25, "text": "Insieme lo abbattete. {genio} ti lascia metà dell'erba.",
                              "prize": {"rank": 3, "kinds": ["pillola"]}, "intrigue": {"branch": "alleanza"}},
                  "failure": {"injury": 2, "text": "Il serpente vi respinge entrambi. {genio} però non lo dimentica.",
                              "intrigue": {"branch": "alleanza"}}},
                 {"label": "Sfidi {genio} per il diritto all'erba",
                  "effects": {"fame": 4, "intrigue": {}}, "command": "duello {npc}"},
             ]},
            {"title": "La sala dei mille tesori", "focus": "genio", "gap": (1, 2),
             "text": ("Al settimo giorno, mentre il reame comincia a tremare, trovi la sala che tutti cercavano: sui "
                      "piedistalli brillano una reliquia antica, un rotolo d'oro, una fiala di sangue di Kun, una "
                      "pillola che profuma di mille anni. Le porte si chiudono tra pochi respiri. Alle tue spalle "
                      "arrivano {genio} e altri due discepoli di sette diverse: ansimano, feriti, e guardano i "
                      "piedistalli come guardi tu. La regola non scritta dei reami è una sola: ognuno prende un "
                      "tesoro."),
             "choices": [
                 {"label": "Prendi solo la reliquia antica",
                  "effects": {"prize": {"rank": 1, "kinds": ["reliquia"], "n": 1, "stones": False}, "fame": 3,
                              "text": "Prendi la reliquia e lasci il resto. {genio} annuisce: è la regola.",
                              "intrigue": {"end": "un_tesoro"}}},
                 {"label": "Prendi solo il rotolo d'oro (una tecnica)",
                  "effects": {"prize": {"rank": 1, "kinds": ["manuale"], "n": 1, "stones": False}, "fame": 3,
                              "intrigue": {"end": "un_tesoro"}}},
                 {"label": "Prendi solo il sangue di Kun",
                  "effects": {"prize": {"rank": 1, "kinds": ["sangue"], "n": 1, "stones": False}, "fame": 3,
                              "intrigue": {"end": "un_tesoro"}}},
                 {"label": "Dividi con {genio}: un tesoro a testa, insieme",
                  "need_branch": "alleanza",
                  "effects": {"prize": {"rank": 1, "kinds": ["tesoro", "pillola"], "n": 2}, "relation": 20,
                              "bond": "companion",
                              "text": "Uscite insieme dalla sala, ognuno col suo tesoro. Un'amicizia nata nel reame.",
                              "intrigue": {"end": "alleanza"}}},
                 {"label": "Prendi il cuore del reame, sotto il lago (il reame crollerà con gli altri dentro)",
                  "need_clues": 2,
                  "effects": {"prize": {"rank": 1, "kinds": ["reliquia", "corpo"], "n": 2}, "karma": -25, "infamy": 8,
                              "text": ("Strappi il cuore del reame. La sala crolla: tu esci dalla cascata; gli altri, "
                                       "forse, no. Chi sopravvive non lo dimenticherà."),
                              "intrigue": {"enemies": 1, "flag": "reame_avido", "end": "cuore"}}},
                 {"label": "Prendi TUTTO, prima che gli altri si muovano",
                  "effects": {"prize": {"rank": 1, "kinds": ["reliquia", "manuale", "sangue", "pillola"], "n": 4},
                              "infamy": 10, "karma": -15, "fame": 5,
                              "text": ("Una manica che spazza i piedistalli, un passo nel varco che si chiude. Dietro "
                                       "di te, tre voci giurano vendetta sui loro maestri."),
                              "intrigue": {"enemies": 2, "flag": "reame_avido", "end": "avido",
                                           "reason": "hai preso tutti i tesori del reame"}}},
             ]},
        ],
        "auto_end": [{"outcome": "chiuso", "text": "Il reame si è richiuso senza di te."}],
        "outcomes": {"un_tesoro": "Sei uscito dal reame con un tesoro, secondo la regola.",
                     "alleanza": "Hai diviso i tesori del reame con {genio}.",
                     "cuore": "Hai strappato il cuore del reame: chi era dentro ti cerca.",
                     "avido": "Hai preso tutti i tesori del reame, e ti sei fatto nemici tutti quelli che erano entrati."},
    },
    # ------------------------------------------------------------------ 9. LA MAREA DI BESTIE
    {
        "key": "marea_bestie",
        "indagine": "istinto", "need": 2, "reveal_act": None, "indizi": ['Gli uccelli fuggono verso sud e i pozzi tremano: qualcosa spinge le bestie giù dalle montagne.', "Il Re delle Bestie è un vecchio orso d'argento, ferito: la marea fugge, non attacca.", "C'è una gola a est dove la marea potrebbe passare oltre la città."],
         "title": "La marea di bestie", "kind": "assedio", "weight": 5, "tier_min": 2,
        "cast": {"mandante": "anziano"},
        "acts": [
            {"title": "Gli uccelli fuggono verso sud", "focus": "mandante", "gap": (1, 2),
             "text": ("Da tre giorni gli uccelli fuggono verso sud e i pozzi di {luogo} tremano. {mandante}, che "
                      "governa la città, ti ferma per strada: «Una marea di bestie scende dalle montagne. Tra pochi "
                      "giorni sarà alle mura. Ci aiuterai?»"),
             "choices": [
                 {"label": "Ti unisci alla difesa delle mura",
                  "effects": {"fame": 4, "text": "{mandante} ti affida la porta nord.", "intrigue": {"branch": "difesa"}}},
                 {"label": "Vai in esplorazione a cercare il Re delle Bestie",
                  "check": {"stat": "istinto", "dc": 60},
                  "success": {"text": "Lo trovi: un vecchio orso d'argento, ferito. La marea fugge da qualcosa, non attacca.",
                              "intrigue": {"clue": 2}},
                  "failure": {"injury": 2, "text": "Le bestie ti fiutano. Torni in città di corsa.", "intrigue": {}}},
                 {"label": "Te ne vai prima che arrivino",
                  "effects": {"fame": -6, "text": "Da lontano, vedi il fumo salire dalle mura.",
                              "intrigue": {"end": "fuggito"}}},
             ]},
            {"title": "La notte dell'assalto", "focus": "mandante", "gap": (1, 2),
             "text": ("A mezzanotte la marea arriva: lupi, cinghiali, serpenti grandi come alberi. Le mura gemono."),
             "choices": [
                 {"label": "Tieni la porta nord",
                  "check": {"stat": "potenza", "dc": 58},
                  "success": {"fame": 8, "text": "Per tutta la notte la porta non cede.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 3, "text": "La porta cede per un attimo; ricacci le bestie a caro prezzo.",
                              "intrigue": {}}},
                 {"label": "Guidi le bestie lontano dalla città, verso la gola",
                  "need_clues": 2,
                  "effects": {"karma": 20, "text": ("Sapendo cosa le spinge, apri loro la strada verso la gola. La "
                                                   "marea passa oltre, e la città quasi non viene toccata."),
                              "intrigue": {"clue": 1, "branch": "saggio"}}},
             ]},
            {"title": "L'alba dopo la marea", "auto": True,
             "text": "All'alba la marea si ritira. La città conta i morti e cerca chi l'ha salvata.",
             "endings": [
                 {"need_branch": "saggio", "outcome": "salvata",
                  "effects": {"fame": 15, "karma": 15, "prize": _SANGUE},
                  "text": "La città ti chiama il Pastore delle Bestie: dal Re delle Bestie ricevi un dono di sangue."},
                 {"need_clues": 1, "outcome": "difesa",
                  "effects": {"fame": 10, "prize": _ARGENTO},
                  "text": "{mandante} ti consegna il tesoro della città come ricompensa."},
                 {"outcome": "superstite", "effects": {"prize": _BRONZO},
                  "text": "La città resiste a fatica. Ti ringraziano con quello che possono."},
             ]},
        ],
        "auto_end": [{"outcome": "caduta", "effects": {"fame": -4}, "text": "Senza di te le mura hanno ceduto."}],
        "outcomes": {"fuggito": "Hai lasciato la città alla marea."},
    },
    # ------------------------------------------------------------------ 10. IL SIGILLO MALEDETTO DELL'ASTA
    {
        "key": "sigillo_asta",
        "indagine": "anima", "need": 1, "reveal_act": None, "indizi": ['Il sigillo di bronzo nero non è un tesoro: è una prigione, e dentro dorme qualcosa.', '{mandante} conosce il contenuto del sigillo: ci ha inciso una runa di sangue.', 'Lo spirito si sveglierà alla luna piena.'],
         "title": "Il sigillo dell'asta", "kind": "asta", "weight": 4, "tier_min": 2,
        "cast": {"mandante": "rivale", "pedina": "sgherro"},
        "acts": [
            {"title": "Il lotto senza nome", "focus": "mandante", "gap": (1, 2),
             "text": ("Alla casa d'aste di {luogo} l'ultimo lotto è un sigillo di bronzo nero, senza nome. Il banditore "
                      "lo vende «così com'è». In prima fila, {mandante} alza la mano con troppa fretta."),
             "choices": [
                 {"label": "Rilanci e lo compri (1500 pietre)",
                  "effects": {"stones": -1500, "text": "Il martelletto cade. {mandante} ti guarda come si guarda un ladro.",
                              "intrigue": {"branch": "comprato"}}},
                 {"label": "Lasci che lo compri lui e lo segui",
                  "check": {"stat": "istinto", "dc": 56},
                  "success": {"text": "Lo vedi incidere una runa di sangue sul sigillo: sa cosa contiene.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Lo perdi nella folla.", "intrigue": {}}},
                 {"label": "Esamini il sigillo prima dell'asta",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"text": "Dentro dorme qualcosa: il sigillo è una prigione, non un tesoro.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Il sigillo ti morde il dito. Brucia per ore.", "intrigue": {}}},
             ]},
            {"title": "Gli assassini nella notte", "focus": "pedina", "gap": (1, 2),
             "text": "Di notte {pedina} scavalca la finestra con un pugnale avvelenato. Vuole il sigillo, o la tua vita.",
             "text_branch": {"comprato": "Di notte {pedina} scavalca la tua finestra: {mandante} rivuole il sigillo."},
             "choices": [
                 {"label": "Lo affronti",
                  "effects": {"intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Gli lasci trovare un sigillo falso",
                  "need_branch": "comprato",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Scappa col falso. {mandante} avrà una brutta sorpresa.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "Non ci casca. Ti ferisce e fugge.", "intrigue": {}}},
             ]},
            {"title": "Ciò che dormiva nel sigillo", "auto": True,
             "text": "Il sigillo si incrina da solo, alla luna piena. Quello che ne esce ha atteso diecimila anni.",
             "endings": [
                 {"need_branch": "comprato", "need_clues": 1, "outcome": "reliquia",
                  "effects": {"prize": _RELIQUIA},
                  "text": "Preparato, sottometti lo spirito del sigillo: diventa una reliquia che ti obbedisce."},
                 {"need_branch": "comprato", "outcome": "maledizione",
                  "effects": {"injury": 3, "prize": _BRONZO},
                  "text": "Lo spirito ti ferisce prima di dissolversi: resta solo un guscio prezioso."},
                 {"need_clues": 1, "outcome": "rivale_maledetto",
                  "effects": {"prize": _ARGENTO, "karma": 5},
                  "text": "Lo spirito divora la casa di {mandante}. Tra le macerie raccogli ciò che resta."},
                 {"outcome": "perduto", "text": "Il sigillo si apre lontano da te. Qualcun altro ne avrà i frutti."},
             ]},
        ],
        "auto_end": [{"outcome": "perduto", "text": "Il sigillo si è aperto lontano da te."}],
        "outcomes": {},
    },
    # ------------------------------------------------------------------ 11. LA GROTTA DEL MAESTRO
    {
        "key": "grotta_maestro", "title": "La grotta del maestro senza nome", "kind": "eredita", "weight": 5,
        "tier_min": 1, "cast": {"spettro": "spettro"},
        "acts": [
            {"title": "Lo scheletro seduto", "focus": None, "gap": (1, 2),
             "text": ("Inseguendo una volpe bianca cadi in un crepaccio, e il crepaccio finisce in una grotta. Seduto "
                      "nella posizione del loto c'è uno scheletro con un anello al dito. Sulla parete, una frase: "
                      "«Chi si inchina nove volte avrà ciò che cerca.»"),
             "choices": [
                 {"label": "Ti inchini nove volte",
                  "effects": {"karma": 10, "text": "Al nono inchino la pietra sotto le tue ginocchia si apre: un rotolo.",
                              "intrigue": {"clue": 2, "branch": "rispetto"}}},
                 {"label": "Prendi l'anello e basta",
                  "effects": {"text": "L'anello è freddo. Lo scheletro, per un attimo, sembra guardarti.",
                              "intrigue": {"branch": "avido"}}},
             ]},
            {"title": "La prova del maestro", "focus": "spettro", "gap": (1, 2),
             "text": ("Di notte l'anima residua del maestro, {spettro}, si siede davanti a te: «Mi resta poco. Mostrami "
                      "che meriti la mia eredità.»"),
             "choices": [
                 {"label": "Gli mostri la tua comprensione del Dao",
                  "check": {"stat": "anima", "dc": 58},
                  "success": {"text": "Annuisce piano. «Sì… sì.»", "intrigue": {"clue": 1}},
                  "failure": {"text": "Sospira. «Ancora acerbo.»", "intrigue": {}}},
                 {"label": "Gli mostri la tua forza",
                  "check": {"stat": "corpo", "dc": 58},
                  "success": {"text": "Ride. «Un bue. Ma un bue onesto.»", "intrigue": {"clue": 1}},
                  "failure": {"injury": 1, "text": "Un dito, e sei a terra.", "intrigue": {}}},
             ]},
            {"title": "L'ultimo dono", "auto": True,
             "text": "All'alba l'anima del maestro si dissolve, e lascia dietro di sé ciò che ha deciso di lasciare.",
             "endings": [
                 {"need_branch": "rispetto", "need_clues": 3, "outcome": "erede",
                  "effects": {"prize": _CORPO, "heart": 5},
                  "text": "Ti chiama discepolo prima di svanire: la sua arte e il suo corpo sono tuoi."},
                 {"need_branch": "rispetto", "outcome": "discepolo", "effects": {"prize": _ARGENTO},
                  "text": "Ti lascia il suo rotolo e una benedizione."},
                 {"outcome": "anello", "effects": {"prize": _BRONZO, "injury": 1},
                  "text": "Ti lascia solo l'anello, e una trappola che scatta quando esci."},
             ]},
        ],
        "auto_end": [{"outcome": "anello", "effects": {"prize": _BRONZO}, "text": "Esci dalla grotta con il solo anello."}],
        "outcomes": {},
    },
    # ------------------------------------------------------------------ 12. LA TRIBOLAZIONE DI UN ALTRO
    {
        "key": "tribolazione_altrui", "title": "Il fulmine sul Picco Solitario", "kind": "tribolazione", "weight": 4,
        "tier_min": 3, "cast": {"mandante": "anziano", "pedina": "sgherro"},
        "acts": [
            {"title": "Nubi a forma di drago", "focus": "mandante", "gap": (1, 1),
             "text": ("Sopra il Picco Solitario le nubi si avvolgono come un drago: un vecchio, {mandante}, affronta la "
                      "tribolazione celeste. Se sopravvive salirà di regno; se muore, il suo anello sarà di chiunque."),
             "choices": [
                 {"label": "Fai la guardia ai piedi del picco",
                  "effects": {"karma": 10, "intrigue": {"branch": "protettore"}}},
                 {"label": "Aspetti, nascosto, che il fulmine finisca il suo lavoro",
                  "effects": {"karma": -5, "intrigue": {"branch": "avvoltoio"}}},
                 {"label": "Raccogli l'essenza del fulmine che cade intorno",
                  "check": {"stat": "corpo", "dc": 62},
                  "success": {"prize": {"rank": 2, "kinds": ["essenza", "nucleo"]}, "text": "Il fulmine ti brucia le mani e ti tempra.",
                              "intrigue": {"clue": 1}},
                  "failure": {"injury": 3, "text": "Il fulmine non perdona i ladri.", "intrigue": {}}},
             ]},
            {"title": "Chi sale a uccidere", "focus": "pedina", "gap": (0, 1),
             "text": "Al terzo fulmine, {pedina} sale il sentiero con una lama: vuole uccidere il vecchio ora che è indifeso.",
             "choices": [
                 {"label": "Gli sbarri la strada",
                  "effects": {"intrigue": {"branch": "protettore"}}, "command": "duello {npc}"},
                 {"label": "Lo lasci passare",
                  "effects": {"karma": -10, "intrigue": {"branch": "avvoltoio"}}},
             ]},
            {"title": "Dopo l'ultimo fulmine", "auto": True,
             "text": "Il nono fulmine cade. Poi il silenzio.",
             "endings": [
                 {"need_branch": "protettore", "outcome": "patrono",
                  "effects": {"relation": 40, "lifespan_years": 20, "prize": _ARGENTO},
                  "text": "{mandante} scende dal picco rinato. «Ti devo la vita», dice, e ti dona ciò che ha di più caro."},
                 {"need_branch": "avvoltoio", "outcome": "anello",
                  "effects": {"karma": -15, "infamy": 4, "prize": _ORO},
                  "text": "{mandante} non scende. Sul picco, tra le ceneri, il suo anello è ancora caldo."},
                 {"outcome": "testimone", "effects": {"prize": _BRONZO},
                  "text": "Hai visto un uomo sfidare il Cielo. Qualcosa ti resta dentro."},
             ]},
        ],
        "auto_end": [{"outcome": "testimone", "text": "La tribolazione è finita senza di te."}],
        "outcomes": {},
    },
    # ------------------------------------------------------------------ 13. IL SACRIFICIO DI SANGUE
    {
        "key": "sacrificio_sangue",
        "indagine": "istinto", "need": 2, "reveal_act": 2, "indizi": ["I segni di sangue a forma d'occhio formano un cerchio attorno a {luogo}: è una formazione.", 'Le persone scomparse vengono trascinate nelle fogne, di notte.', "Nelle fogne c'è uno dei nove nodi: una colonna d'ossa incisa da {pedina}.", 'Il cuore della formazione è sulla torre, e chi la guida è {mandante}.'],
         "title": "La formazione dei diecimila spiriti", "kind": "demoniaco", "weight": 5,
        "tier_min": 3, "cast": {"pedina": "sgherro", "mandante": "rivale"},
        "acts": [
            {"title": "Le case vuote", "focus": None, "gap": (2, 3),
             "text": ("A {luogo} spariscono persone: prima i mendicanti, poi i bambini. Sulle soglie delle case vuote, "
                      "un segno di sangue a forma di occhio."),
             "choices": [
                 {"label": "Segui i segni di sangue",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "I segni formano un cerchio attorno alla città: una formazione.", "intrigue": {"clue": 1}},
                  "failure": {"text": "I segni ti confondono. Ne perdi il filo.", "intrigue": {}}},
                 {"label": "Fai la ronda di notte",
                  "effects": {"text": "Vedi un'ombra trascinare un sacco verso le fogne.", "intrigue": {"clue": 1}}},
             ]},
            {"title": "Il nodo nelle fogne", "focus": "pedina", "gap": (1, 2),
             "text": "Nelle fogne {pedina} incide rune su una colonna di ossa. Uno dei nove nodi della formazione.",
             "choices": [
                 {"label": "Lo affronti",
                  "effects": {"intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Spezzi il nodo senza farti vedere",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"text": "Il nodo si spegne. Gli altri otto tremano.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "La formazione ti morde l'anima.", "intrigue": {}}},
             ]},
            {"title": "La luna di sangue", "focus": "mandante", "gap": (1, 2),
             "text": ("Alla luna di sangue {mandante} sale sulla torre: la formazione si accende. Diecimila anime "
                      "urlano. Ancora un'ora e la città sarà un deserto."),
             "choices": [
                 {"label": "Spezzi la formazione dal suo cuore",
                  "need_clues": 2,
                  "effects": {"karma": 40, "fame": 15, "prize": _ORO,
                              "text": "Sai dove colpire: la formazione crolla, e {mandante} ne viene travolto.",
                              "intrigue": {"end": "salvata"}}},
                 {"label": "Sali sulla torre e lo affronti",
                  "effects": {"fame": 10, "karma": 15, "intrigue": {"end": "duello"}}, "command": "duello {npc}"},
                 {"label": "Fuggi dalla città",
                  "effects": {"karma": -25, "text": "Alle tue spalle, diecimila voci si spengono.",
                              "intrigue": {"end": "caduta"}}},
             ]},
        ],
        "auto_end": [{"outcome": "caduta", "effects": {"karma": -5},
                      "text": "Alla luna di sangue la città si è spenta. Nessuno l'ha fermato."}],
        "outcomes": {"salvata": "Hai salvato la città dalla formazione dei diecimila spiriti.",
                     "duello": "Hai affrontato {mandante} sulla torre.", "caduta": "La città è caduta."},
    },
    # ------------------------------------------------------------------ 14. IL VECCHIO MOSTRO NEL CORPO GIOVANE
    {
        "key": "possessione",
        "indagine": "anima", "need": 2, "reveal_act": 1, "indizi": ["{vittima} usa tecniche di un'era morta da secoli.", 'Di notte parla con una voce che non è la sua, e ride.', "Dietro i suoi occhi c'è un'anima vecchia: un mostro che si è preso il suo corpo."],
         "title": "Il vecchio mostro negli occhi di {vittima}", "kind": "possessione", "weight": 4,
        "tier_min": 3, "cast": {"vittima": "alleato"},
        "acts": [
            {"title": "Una tecnica che non poteva conoscere", "focus": "vittima", "gap": (2, 3),
             "text": ("{vittima} è cambiato. Usa tecniche che nessuno gli ha insegnato, parla di imperatori morti da "
                      "secoli, e di notte lo senti ridere con una voce che non è la sua."),
             "choices": [
                 {"label": "Guardi nei suoi occhi con il senso divino",
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"text": "Dietro i suoi occhi c'è un vecchio: un mostro che si è preso il suo corpo.",
                              "intrigue": {"clue": 2}},
                  "failure": {"text": "Ti respinge con una forza che non dovrebbe avere.", "intrigue": {}}},
                 {"label": "Ne parli con lui apertamente",
                  "effects": {"text": "Sorride. «Sei perspicace. Parliamone, da vecchi amici.»",
                              "intrigue": {"branch": "patto"}}},
             ]},
            {"title": "Il prezzo del vecchio mostro", "focus": "vittima", "gap": (1, 2),
             "text": ("Il vecchio mostro parla con la bocca di {vittima}: «Il ragazzo dorme. Posso insegnarti cose che "
                      "nessuna setta conosce. In cambio, lascia stare.»"),
             "choices": [
                 {"label": "Lo scacci dal corpo del tuo amico",
                  "need_clues": 2,
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"relation": 50, "karma": 25, "prize": _CORPO,
                              "text": "L'anima vecchia urla e si disperde. {vittima} apre gli occhi: i suoi.",
                              "intrigue": {"end": "salvato"}},
                  "failure": {"injury": 3, "text": "Il mostro ti respinge e fugge col corpo del tuo amico.",
                              "intrigue": {"end": "perduto"}}},
                 {"label": "Accetti il patto e impari da lui",
                  "effects": {"infamy": 6, "karma": -20, "prize": {"rank": 1, "kinds": ["manuale"]},
                              "text": "Impari tre tecniche dimenticate. Del tuo amico non resta niente.",
                              "intrigue": {"end": "patto"}}},
                 {"label": "Lo affronti: il corpo è già perduto",
                  "effects": {"karma": -5, "intrigue": {"end": "duello"}}, "command": "duello {npc}"},
             ]},
        ],
        "auto_end": [{"outcome": "perduto", "text": "Il vecchio mostro se n'è andato, col corpo del tuo amico."}],
        "outcomes": {"salvato": "Hai salvato {vittima} dal vecchio mostro.", "patto": "Hai fatto un patto col vecchio mostro.",
                     "duello": "Hai affrontato il vecchio mostro nel corpo di {vittima}.",
                     "perduto": "{vittima} è perduto."},
    },
    # ------------------------------------------------------------------ 15. LA CAROVANA
    {
        "key": "carovana", "title": "La carovana del Mercante Dorato", "kind": "scorta", "weight": 5, "tier_min": 1,
        "cast": {"mandante": "anziano", "pedina": "sgherro"},
        "acts": [
            {"title": "Un ingaggio troppo generoso", "focus": "mandante", "gap": (1, 2),
             "text": ("{mandante}, mercante della Lega Dorata, cerca una scorta fino al passo: «Pago il triplo. Non fare "
                      "domande sul carico.» Uno dei carri è coperto da un telo nero, e respira."),
             "choices": [
                 {"label": "Accetti l'ingaggio",
                  "effects": {"stones": 300, "intrigue": {"branch": "scorta"}}},
                 {"label": "Sbirci sotto il telo nero",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Un uovo grande come un uomo, caldo, con scaglie dorate.", "intrigue": {"clue": 1, "branch": "scorta"}},
                  "failure": {"text": "Il mercante ti afferra il polso: «Ti avevo detto niente domande.»",
                              "intrigue": {"branch": "scorta"}}},
             ]},
            {"title": "L'agguato al passo", "focus": "pedina", "gap": (1, 2),
             "text": "Al passo, {pedina} e i suoi sbarrano la strada: sanno cosa c'è nel carro nero.",
             "choices": [
                 {"label": "Difendi la carovana",
                  "effects": {"fame": 4, "intrigue": {"clue": 1}}, "command": "duello {npc}"},
                 {"label": "Li aggiri per un sentiero di capre",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"text": "La carovana scivola via mentre i banditi aspettano.", "intrigue": {"clue": 1}},
                  "failure": {"injury": 2, "text": "Vi scoprono: si combatte tra le rocce.", "intrigue": {}}},
             ]},
            {"title": "Oltre il passo", "auto": True,
             "text": "Oltre il passo il mercante conta il carico, e il carro nero si muove da solo.",
             "endings": [
                 {"need_clues": 2, "outcome": "uovo",
                  "effects": {"prize": _SANGUE, "stones": 600},
                  "text": "L'uovo si schiude ai tuoi piedi: il mercante, tremando, ti lascia il sangue del piccolo e la paga doppia."},
                 {"outcome": "paga", "effects": {"stones": 500, "prize": _BRONZO},
                  "text": "Il mercante paga quanto promesso, e qualcosa di più."},
             ]},
        ],
        "auto_end": [{"outcome": "partita", "text": "La carovana è partita senza di te."}],
        "outcomes": {},
    },
    # ------------------------------------------------------------------ 16. LA VENDETTA DEL REAME
    {
        "key": "vendetta_reame", "title": "I tesori del reame", "kind": "vendetta", "weight": 6, "tier_min": 1,
        "req_flag": "reame_avido", "cast": {"pedina": "legame:reame_avido", "mandante": "rivale"},
        "acts": [
            {"title": "I maestri chiedono conto", "focus": "pedina", "gap": (2, 4),
             "text": ("{pedina}, uno dei discepoli rimasti a mani vuote nel reame, è tornato dalla sua setta. Ora "
                      "cammina verso di te alla testa di sei compagni, e dietro di loro, a cavallo di una gru, "
                      "{mandante}: «I tesori del reame appartengono a chi è entrato. Restituisci la nostra parte.»"),
             "choices": [
                 {"label": "Restituisci una parte (2000 pietre) e chiudi la questione",
                  "effects": {"stones": -2000, "infamy": -4, "relation": 30,
                              "text": "{mandante} conta le pietre e annuisce. Per ora basta.",
                              "intrigue": {"end": "restituito"}}},
                 {"label": "Rifiuti: chi vuole i tesori venga a prenderli",
                  "effects": {"fame": 6, "intrigue": {"branch": "sfida"}}, "command": "duello {npc}"},
                 {"label": "Metti i discepoli l'uno contro l'altro: a uno prometti tutto",
                  "check": {"stat": "karma", "dc": 58},
                  "success": {"text": "La notte stessa litigano tra loro. {pedina} se ne va da solo, furioso.",
                              "intrigue": {"clue": 1, "branch": "divisi"}},
                  "failure": {"text": "Ti ridono in faccia. «Pensi che siamo sciocchi?»", "intrigue": {"branch": "sfida"}}},
             ]},
            {"title": "L'agguato della setta", "focus": "mandante", "gap": (2, 4),
             "text": "Al passo, {mandante} ti aspetta da solo: «Ho mandato via i ragazzi. Questo è tra noi due.»",
             "text_branch": {"divisi": ("Divisi e litigiosi, i discepoli non si sono fatti più vedere. Solo {mandante} "
                                        "ti aspetta al passo, stanco: «Hai seminato zizzania. Abile. Parliamo.»")},
             "choices": [
                 {"label": "Lo affronti",
                  "effects": {"fame": 10, "intrigue": {"end": "battaglia"}}, "command": "duello {npc}"},
                 {"label": "Trattate: un tesoro in cambio di pace",
                  "need_branch": "divisi",
                  "effects": {"karma": 10, "relation": 40, "prize": {"rank": 2, "kinds": ["manuale"], "n": 1},
                              "text": "Vi scambiate un tesoro e una tecnica della sua setta. Nemici, ma non più in guerra.",
                              "intrigue": {"end": "pace"}}},
                 {"label": "Fuggi con i tesori",
                  "effects": {"infamy": 4, "text": "Sparisci nella nebbia. La caccia continuerà.",
                              "intrigue": {"end": "fuga"}}},
             ]},
        ],
        "auto_end": [{"outcome": "caccia", "effects": {"infamy": 3},
                      "text": "Le sette del reame ti hanno messo una taglia sulla testa."}],
        "outcomes": {"restituito": "Hai restituito parte dei tesori del reame.",
                     "battaglia": "Hai difeso i tesori del reame contro {mandante}.",
                     "pace": "Hai fatto pace con chi ti cercava per i tesori del reame.",
                     "fuga": "Sei fuggito con i tesori del reame: la caccia continua."},
    },
]
