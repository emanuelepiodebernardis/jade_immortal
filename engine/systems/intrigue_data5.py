"""
NUOVE TRAME SCRITTE A MANO (Aggiornamento 71) — cattivi da ricordare, personaggi che ritornano.

Stesso formato di intrigue_data.py (le sceglie il regista delle trame, giorno per giorno). Il genere:
  · il vecchio indovino che vende destini e ne ruba altrettanti;
  · la pagoda della prova da cui i discepoli non tornano;
  · il traghettatore del Fiume Nero che riscuote i debiti delle vite passate;
  · il genio travestito da sguattero, ultimo erede di un clan sterminato;
  · il torneo delle lanterne, dove chi perde dimentica il proprio nome.

Ogni trama ha un esito che cambia il mondo (chi resta tuo alleato, chi diventa nemico, che cosa ti porti via).
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}

TEMPLATES: list[dict] = [
    # ============================================================ IL MERCANTE DI DESTINI
    {
        "key": "mercante_destini", "title": "Il Mercante di Destini", "kind": "intrigo", "weight": 5, "tier_min": 2,
        "indagine": "istinto", "need": 2, "reveal_act": 2,
        "indizi": ["Le «letture del destino» di {mandante} si avverano sempre il giorno dopo che lui ha incontrato qualcuno.",
                   "{pedina} ha in tasca un ago d'osso con incise le stesse rune che ha il «destino» venduto ai clienti.",
                   "Chi compra un destino da {mandante} perde, piano piano, la propria fortuna: lui la beve."],
        "cast": {"mandante": "anziano", "pedina": "sgherro", "vittima": "alleato"},
        "acts": [
            {"title": "La tenda viola", "focus": "mandante", "gap": (1, 2),
             "text": ("In fondo al mercato di {luogo} c'è una tenda viola che nessuno ricorda di aver visto montare. "
                      "Dentro, {mandante} — un vecchio con le dita sottili come zampe di ragno — legge i destini su "
                      "lastre d'osso. «Il tuo è torbido, giovane. Posso schiarirlo. Per un prezzo.» Fuori, la fila è "
                      "lunga; tra i clienti c'è anche {vittima}, pallido come chi non dorme da giorni."),
             "choices": [
                 {"label": "Ti fai leggere il destino (100 pietre)",
                  "effects": {"stones": -100, "text": ("Le lastre si scaldano tra le sue dita. «Vedo un grande sfondamento… "
                                                       "e un grande nemico.» Mentre esci, ti senti più leggero. Troppo."), "intrigue": {"clue": 1, "branch": "cliente"}}},
                 {"label": "Osservi chi entra e chi esce",
                  "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": "Chi esce sorride; chi torna, il giorno dopo, ha gli occhi spenti. Sempre.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Una folla, una tenda, niente di strano. Forse.", "intrigue": {}}},
                 {"label": "Porti via {vittima} dalla fila",
                  "effects": {"relation": 10, "text": "«Mi aveva promesso che la mia sfortuna sarebbe finita…»",
                              "intrigue": {"branch": "salvato"}}},
             ]},
            {"title": "L'ago d'osso", "focus": "pedina", "gap": (2, 3),
             "text": ("Di notte, {pedina} si muove tra le case dei clienti del vecchio. Entra dalle finestre, si china "
                      "sui dormienti con un ago d'osso, e ne esce con una goccia di luce in una fiala."),
             "choices": [
                 {"label": "Lo blocchi e gli strappi la fiala", "effects": {"intrigue": {"clue": 1, "branch": "fiala"}},
                  "command": "duello {pedina}"},
                 {"label": "Lo segui fino alla tenda",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "{pedina} versa la luce in una coppa. {mandante} la beve, e ringiovanisce di un anno.",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "Lo perdi nei vicoli.", "intrigue": {}}},
             ]},
            {"title": "La tenda brucia", "focus": "mandante", "gap": (2, 3),
             "text": ("La tenda viola è più grande, ora; il vecchio ha la pelle di un uomo di quarant'anni. Ti aspettava. "
                      "«Hai ficcato il naso nel mio destino. Ti propongo un affare: metà di quello che bevo, per sempre.»"),
             "text_low": "La tenda viola è più grande, ora. Il vecchio ti sorride come a un cliente affezionato.",
             "choices": [
                 {"label": "Lo smascheri davanti al mercato: le fiale, l'ago, i clienti", "need_clues": 2,
                  "effects": {"fame": 15, "karma": 20, "prize": _ARGENTO, "intrigue": {"end": "smascherato"},
                              "text": ("Uno a uno, i clienti capiscono. La folla rovescia la tenda: dentro, mille fiale di "
                                       "luce rubata tornano ai loro padroni.")}},
                 {"label": "Lo sfidi: «Ridammi ciò che hai preso»", "effects": {"intrigue": {"end": "duello"}},
                  "command": "duello {mandante}"},
                 {"label": "Accetti l'affare", "effects": {"stones": 1200, "karma": -25, "infamy": 6,
                                                         "intrigue": {"end": "socio"},
                                                         "text": "Ogni notte, una fiala in più. Ogni mattina, un viso spento in più."}},
             ]},
        ],
        "auto_end": [{"outcome": "fuggito", "text": "Una mattina la tenda viola non c'è più. Il vecchio è andato altrove."}],
        "outcomes": {"smascherato": "Hai smascherato il Mercante di Destini: la fortuna rubata è tornata a {luogo}.",
                     "duello_vinto": "Hai spezzato le lastre di {mandante}: la sua giovinezza rubata si dissolve.",
                     "duello_perso": "{mandante} ti ha battuto e ha bevuto un sorso del tuo destino. Lo rivedrai.",
                     "duello_fuga": "Sei fuggito dalla tenda viola.",
                     "socio": "Sei diventato socio del Mercante di Destini.",
                     "fuggito": "Il Mercante di Destini è fuggito."},
    },
    # ============================================================ LA PAGODA CHE MANGIA I DISCEPOLI
    {
        "key": "settimo_piano", "title": "La Pagoda che mangia i discepoli", "kind": "mistero", "weight": 5,
        "tier_min": 2, "indagine": "istinto", "need": 2, "reveal_act": 2,
        "indizi": ["Tutti i discepoli scomparsi avevano radici spirituali eccellenti: la pagoda sceglie i migliori.",
                   "Al settimo piano le pareti sono calde, come la pancia di una bestia che digerisce.",
                   "{mandante} entra nella pagoda ogni luna nuova e ne esce con un regno in più."],
        "cast": {"mandante": "anziano", "vittima": "genio"},
        "acts": [
            {"title": "Il settimo piano", "focus": "vittima", "gap": (1, 2),
             "text": ("Nella setta vicina a {luogo} la Pagoda della Prova è un onore: chi arriva al settimo piano "
                      "diventa discepolo interno. Quest'anno, però, tre geni ci sono saliti e nessuno è sceso. "
                      "{vittima}, il più dotato dell'anno, sta per entrare. Ti guarda: «Se non esco entro sera… "
                      "vieni a cercarmi.»"),
             "choices": [
                 {"label": "Entri con lui, di nascosto",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Al settimo piano le pareti pulsano. {vittima} viene risucchiato in una crepa; "
                                      "lo afferri per un braccio e lo tiri fuori.", "intrigue": {"clue": 1, "branch": "salvato"}},
                  "failure": {"text": "Le guardie ti respingono all'ingresso.", "intrigue": {}}},
                 {"label": "Interroghi i servi della pagoda (50 pietre)",
                  "effects": {"stones": -50, "text": "«Prendono sempre i migliori, signore. Sempre.»", "intrigue": {"clue": 1}}},
             ]},
            {"title": "La luna nuova", "focus": "mandante", "gap": (2, 4),
             "text": ("È luna nuova. {mandante}, l'anziano custode della pagoda, sale le scale da solo con una lanterna "
                      "rossa. Quando ne esce, all'alba, la sua aura è più spessa — e la pagoda, per un attimo, sospira."),
             "choices": [
                 {"label": "Lo segui fin dentro",
                  "check": {"stat": "potenza", "dc": 58},
                  "success": {"text": "Lo vedi posare la mano sulla parete calda e bere qi come da una fonte.",
                              "intrigue": {"clue": 1}},
                  "failure": {"injury": 1, "text": "La pagoda si accorge di te: una scala crolla sotto i tuoi piedi.",
                              "intrigue": {}}},
                 {"label": "Avverti il patriarca della setta", "effects": {"fame": 3,
                  "text": "Il patriarca ascolta, impassibile. «Senza prove, è la tua parola contro la sua.»",
                  "intrigue": {"branch": "avvertito"}}},
             ]},
            {"title": "Il cuore della pagoda", "focus": "mandante", "gap": (2, 3),
             "text": ("Il settimo piano non è un piano: è uno stomaco. Ossa di geni, ancora avvolte nelle vesti della "
                      "setta, galleggiano nel qi denso. {mandante} ti aspetta al centro. «Avresti dovuto restare un "
                      "talento mediocre. Ora sarai il mio prossimo regno.»"),
             "text_low": "Al settimo piano {mandante} ti aspetta. Non sai ancora cosa ci sia nelle pareti.",
             "choices": [
                 {"label": "Spezzi il cuore della pagoda e liberi le anime", "need_clues": 2,
                  "check": {"stat": "potenza", "dc": 60},
                  "success": {"karma": 30, "fame": 15, "prize": _ORO, "intrigue": {"end": "liberati"},
                              "text": "Il cuore si incrina; cento luci salgono al cielo. {mandante} invecchia di un secolo in un istante."},
                  "failure": {"injury": 2, "text": "Il cuore è troppo duro. {mandante} ride.", "intrigue": {"end": "taciuto"}}},
                 {"label": "Affronti {mandante}", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {mandante}"},
                 {"label": "Fuggi e racconti tutto alla setta", "effects": {"fame": 5, "intrigue": {"end": "denunciato"},
                  "text": "La setta sigilla la pagoda. {mandante} sparisce prima del processo."}},
             ]},
        ],
        "auto_end": [{"outcome": "taciuto", "text": "La pagoda continua a scegliere i migliori."}],
        "outcomes": {"liberati": "Hai spezzato il cuore della Pagoda: le anime dei geni sono libere.",
                     "duello_vinto": "Hai abbattuto {mandante} nel cuore della pagoda: nessuno sparirà più.",
                     "duello_perso": "{mandante} ti ha respinto: la pagoda ha un nuovo nome da desiderare.",
                     "duello_fuga": "Sei fuggito dal settimo piano.",
                     "denunciato": "Hai denunciato il custode della pagoda: è fuggito.",
                     "taciuto": "La Pagoda continua a mangiare."},
    },
    # ============================================================ IL DEBITO DEL FIUME NERO
    {
        "key": "fiume_nero", "title": "Il debito del Fiume Nero", "kind": "maledizione", "weight": 4, "tier_min": 3,
        "cast": {"traghettatore": "spettro", "vittima": "alleato"},
        "acts": [
            {"title": "La barca senza remi", "focus": "traghettatore", "gap": (1, 2),
             "text": ("Una nebbia nera sale dal fiume di {luogo}. Una barca senza remi attracca da sola, e il "
                      "{traghettatore} — un uomo senza ombra — ti porge un registro di carta d'osso. «Nella vita "
                      "passata hai attraversato il mio fiume senza pagare. Il debito è cresciuto. Ora vale cento anni "
                      "della tua vita… o una vita intera, di qualcuno che ami.»"),
             "choices": [
                 {"label": "Paghi con la tua vita (−30 anni di vita)", "effects": {"lifespan_years": -30, "karma": 10,
                  "text": "Il registro si chiude. Senti gli anni andarsene come acqua da un secchio bucato.",
                  "intrigue": {"end": "pagato"}}},
                 {"label": "Contratti: «Un debito si può lavorare»",
                  "check": {"stat": "anima", "dc": 55},
                  "success": {"text": "Il {traghettatore} ride senza suono. «Portami tre anime perdute dal fiume, e siamo pari.»",
                              "intrigue": {"branch": "lavoro"}},
                  "failure": {"text": "«I morti non contrattano.» La nebbia si infittisce attorno a {vittima}.",
                              "intrigue": {"branch": "minaccia"}}},
                 {"label": "Lo sfidi: «Nessun debito di un'altra vita mi lega»", "effects": {"intrigue": {"end": "duello"}},
                  "command": "duello {traghettatore}"},
             ]},
            {"title": "Le anime nel fiume", "focus": "vittima", "gap": (2, 3),
             "text": ("Di notte, sulle rive, le anime perdute cantano. Una ha la voce di {vittima}: il fiume l'ha "
                      "chiamata nel sonno, e il suo corpo dorme di un sonno da cui non si sveglia."),
             "choices": [
                 {"label": "Scendi nel fiume e riporti indietro l'anima", "need_branch": "minaccia",
                  "check": {"stat": "potenza", "dc": 60},
                  "success": {"relation": 40, "karma": 15, "text": "Riporti l'anima nel corpo. {vittima} si sveglia piangendo.",
                              "intrigue": {"end": "salvato"}},
                  "failure": {"injury": 2, "text": "Il fiume ti respinge. L'anima di {vittima} si allontana.",
                              "intrigue": {"end": "perduto"}}},
                 {"label": "Raccogli tre anime perdute per il {traghettatore}", "need_branch": "lavoro",
                  "effects": {"karma": 20, "prize": _ARGENTO, "intrigue": {"end": "lavorato"},
                              "text": "Tre anime, tre storie, tre addii. Il registro si chiude. Il {traghettatore} si inchina."}},
                 {"label": "Bruci il registro di carta d'osso",
                  "check": {"stat": "istinto", "dc": 62},
                  "success": {"karma": -10, "prize": _ORO, "intrigue": {"end": "bruciato"},
                              "text": "Il registro brucia con una fiamma verde. Mille debiti si cancellano, il tuo e quello di altri."},
                  "failure": {"injury": 1, "text": "Il fuoco non attecchisce sulla carta dei morti.", "intrigue": {"end": "perduto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "perduto", "text": "La nebbia nera si ritira. Il debito resta scritto."}],
        "outcomes": {"pagato": "Hai pagato il debito del Fiume Nero con anni della tua vita.",
                     "duello_vinto": "Hai battuto il traghettatore: il Fiume Nero non ha più diritti su di te.",
                     "duello_perso": "Il traghettatore ti ha battuto: il debito raddoppia.",
                     "duello_fuga": "Sei fuggito dalla nebbia nera.",
                     "salvato": "Hai riportato l'anima di {vittima} dal Fiume Nero.",
                     "lavorato": "Hai saldato il debito guidando tre anime perdute.",
                     "bruciato": "Hai bruciato il registro del Fiume Nero.",
                     "perduto": "Il Fiume Nero ha preso ciò che gli spettava."},
    },
    # ============================================================ L'EREDE NELLA CUCINA
    {
        "key": "erede_cucina", "title": "L'erede nella cucina", "kind": "salvataggio", "weight": 5, "tier_min": 1,
        "cast": {"genio": "genio", "mandante": "rivale"},
        "acts": [
            {"title": "Lo sguattero che taglia il vento", "focus": "genio", "gap": (1, 2),
             "text": ("Nella locanda di {luogo} uno sguattero, {genio}, taglia le verdure così in fretta che il coltello "
                      "lascia scie d'aria. Quando si accorge che lo guardi, sbaglia apposta un taglio. Sul polso ha un "
                      "tatuaggio sbiadito: il simbolo di un clan sterminato dieci anni fa."),
             "choices": [
                 {"label": "Gli parli a bassa voce del suo clan", "effects": {"relation": 15,
                  "text": "Impallidisce. «Non dire quel nome qui. Chi l'ha distrutto mi cerca ancora.»",
                  "intrigue": {"branch": "fiducia"}}},
                 {"label": "Lo metti alla prova con un colpo improvviso",
                  "check": {"stat": "potenza", "dc": 50},
                  "success": {"text": "Para senza pensarci, con un mestolo. Poi ti guarda con odio e paura.",
                              "intrigue": {"branch": "scoperto"}},
                  "failure": {"text": "Lo colpisci per davvero: cade, come un vero sguattero. Forse ti sbagli.", "intrigue": {}}},
             ]},
            {"title": "Gli uomini col mantello grigio", "focus": "mandante", "gap": (2, 3),
             "text": ("Tre uomini col mantello grigio entrano nella locanda. Li guida {mandante}, la cui setta salì al "
                      "potere sulle ceneri del clan di {genio}. «Cerchiamo un ragazzo. Ha un tatuaggio. Chi lo nasconde "
                      "muore con lui.»"),
             "choices": [
                 {"label": "Ti metti tra loro e la cucina", "need_branch": "fiducia",
                  "effects": {"intrigue": {"end": "difeso"}}, "command": "duello {mandante}"},
                 {"label": "Fai fuggire {genio} dal retro",
                  "check": {"stat": "istinto", "dc": 52},
                  "success": {"relation": 30, "text": "Mentre i mantelli grigi rovesciano i tavoli, {genio} è già lontano. "
                                                    "Ti lascia un biglietto: «Ti devo la vita.»",
                              "intrigue": {"end": "fuggito"}},
                  "failure": {"text": "Lo prendono sulla porta.", "intrigue": {"end": "catturato"}}},
                 {"label": "Lo consegni: non è la tua guerra", "effects": {"stones": 800, "karma": -20, "infamy": 5,
                  "text": "{mandante} ti getta un sacchetto. {genio} non urla. Ti guarda soltanto.",
                  "intrigue": {"end": "venduto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "catturato", "text": "I mantelli grigi hanno trovato il ragazzo."}],
        "outcomes": {"difeso_vinto": "Hai difeso l'ultimo erede del clan: {genio} ti seguirà ovunque.",
                     "difeso_perso": "{mandante} ti ha battuto e si è preso il ragazzo.",
                     "difeso_fuga": "Sei fuggito; {genio} è rimasto solo.",
                     "fuggito": "Hai fatto fuggire l'ultimo erede del clan. Un giorno tornerà.",
                     "catturato": "L'ultimo erede del clan è stato preso.",
                     "venduto": "Hai venduto l'ultimo erede del clan."},
    },
    # ============================================================ IL TORNEO DELLE LANTERNE
    {
        "key": "torneo_lanterne", "title": "Il Torneo delle Lanterne", "kind": "torneo", "weight": 4, "tier_min": 2,
        "cast": {"genio": "genio", "mandante": "anziano"},
        "acts": [
            {"title": "La lanterna col tuo nome", "focus": "mandante", "gap": (1, 2),
             "text": ("A {luogo}, una notte all'anno, si accendono mille lanterne: ognuna porta il nome di un "
                      "coltivatore. Chi vince il Torneo delle Lanterne ottiene un desiderio. Chi perde… la sua lanterna "
                      "si spegne, e con lei il suo nome: nessuno lo ricorderà più. {mandante}, il maestro del torneo, "
                      "ti porge una lanterna già accesa. C'è scritto il tuo nome."),
             "choices": [
                 {"label": "Accetti la sfida", "effects": {"fame": 5, "intrigue": {"branch": "iscritto"},
                  "text": "La lanterna brucia con un fuoco freddo, come un cuore che aspetta."}},
                 {"label": "Spegni la lanterna con le dita", "check": {"stat": "potenza", "dc": 55},
                  "success": {"text": "La fiamma si spegne; il tuo nome resta tuo. {mandante} ti guarda con interesse.",
                              "intrigue": {"end": "rifiutato"}},
                  "failure": {"injury": 1, "text": "La fiamma ti morde le dita e non si spegne. Sei dentro, che tu lo voglia o no.",
                              "intrigue": {"branch": "iscritto"}}},
             ]},
            {"title": "La finale", "focus": "genio", "gap": (2, 3),
             "text": ("Hai superato i primi turni. In finale ti aspetta {genio}, che non ha perso un solo scontro e non "
                      "ha mai detto il suo nome. Prima del duello ti sussurra: «Ho già perso una volta, qui. Mi chiamavo "
                      "in un altro modo. Non ricordo come.»"),
             "choices": [
                 {"label": "Combatti per vincere", "need_branch": "iscritto", "effects": {"intrigue": {"end": "finale"}},
                  "command": "duello {genio}"},
                 {"label": "Ti arrendi perché lui ritrovi il suo nome", "effects": {"karma": 25, "heart": 6,
                  "relation": 40, "text": ("La tua lanterna si spegne. Per un istante il mondo vacilla, poi {genio} grida "
                                          "un nome — il suo — e piange. Il tuo nome, però, resta: chi si sacrifica non "
                                          "si dimentica."), "intrigue": {"end": "sacrificio"}}},
                 {"label": "Distruggi le mille lanterne", "check": {"stat": "potenza", "dc": 65},
                  "success": {"karma": 20, "fame": 15, "prize": _ORO, "intrigue": {"end": "liberati"},
                              "text": "Le lanterne si rompono una dopo l'altra: mille nomi tornano ai loro padroni."},
                  "failure": {"injury": 2, "text": "{mandante} ti ferma con un gesto.", "intrigue": {"end": "fermato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "rifiutato", "text": "Il torneo si è concluso senza di te."}],
        "outcomes": {"rifiutato": "Hai rifiutato il Torneo delle Lanterne.",
                     "finale_vinto": "Hai vinto il Torneo delle Lanterne: un desiderio ti aspetta (+fama).",
                     "finale_perso": "Hai perso la finale: qualcuno, da qualche parte, ha dimenticato il tuo nome.",
                     "finale_fuga": "Sei fuggito dalla finale.",
                     "sacrificio": "Hai restituito il nome a {genio}.",
                     "liberati": "Hai liberato i mille nomi delle lanterne.",
                     "fermato": "Il maestro del torneo ti ha fermato."},
    },
]
