"""
SAGHE LUNGHE SCRITTE A MANO (Aggiornamento 73) — personaggi che tornano per anni, finali diversi.

Stesso formato di intrigue_data.py. Ogni saga è fatta di più trame legate da un «segno» (flag): la
scelta che fai alla fine di un capitolo accende il capitolo successivo, con gli stessi personaggi
(cast «legame:<segno>»), dopo il tempo giusto («delay», in giorni). Così la stessa persona ti segue:

  LA SPADA SPEZZATA (dal primo regno in poi)
    I   Una sola copia ............ condividi il manuale → fratelli · lo tieni → rivali · lo vendi → traditore
    II  fratelli: Il fratello accusato  ·  rivali: La sfida in piazza  ·  traditore: L'uomo con la cicatrice
    III La spada ricomposta (fratelli giurati, o lui muore per te) · Il picco senza nome (il duello dei
        rivali: rispetto o umiliazione) · Il demone con la tua spada (nemesi: lo uccidi o lo riporti indietro)

  IL MERCANTE DI DESTINI (seguito delle trame dell'Agg. 71)
    da socio: Il conto del socio (tradire lui o il tuo amico) · se l'hai battuto: La lastra spezzata

  IL MAESTRO CHE NON MUORE (regni 2 → 4 → 6)
    I   La voce nella giada ....... porti con te il frammento d'anima, o lo lasci all'eremita, o lo distruggi
    II  Il corpo in prestito / Gli occhi dell'eremita ... sigillarlo, dargli un corpo, un fantoccio di giada
    III Il Maestro Senza Tomba (rinato: diventi il suo erede, gli dai la morte o lo abbatti)
        Il Maestro di giada (il fantoccio: maestro per sempre, o lo lasci andare)
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}
_MANUALE = {"rank": 2, "kinds": ["manuale"]}

TEMPLATES: list[dict] = [
    # ================================================================ LA SPADA SPEZZATA — I
    {
        "key": "spada_spezzata", "title": "La Spada Spezzata", "kind": "legame", "weight": 6, "tier_min": 1,
        "cast": {"fratello": "genio", "anziano": "anziano"},
        "acts": [
            {"title": "La lama rotta", "focus": "fratello", "gap": (1, 2),
             "text": ("All'alba, sulla riva del fiume vicino a {luogo}, un ragazzo si allena da solo con mezza spada. "
                      "La lama finisce un palmo dopo l'elsa, spezzata di netto. Si chiama {fratello}. «Era di mio "
                      "padre», dice senza smettere di colpire l'aria. «L'hanno spezzata i discepoli di {anziano}, "
                      "il giorno in cui l'hanno ucciso. Un giorno la rifarò intera. E poi andrò a restituirgliela.»"),
             "choices": [
                 {"label": "Ti alleni con lui fino a sera",
                  "effects": {"relation": 15, "heart": 3,
                              "text": ("Due spade, una intera e una rotta. Al tramonto ridete come vecchi amici: "
                                       "la sua mezza lama ti ha toccato due volte."),
                              "intrigue": {"branch": "allenati"}}},
                 {"label": "Gli paghi un fabbro per rifarla (200 pietre)",
                  "effects": {"stones": -200, "relation": 25,
                              "text": ("Il fabbro scuote la testa: «L'acciaio è vivo, non si salda. Ma la conservo "
                                       "finché non porterete un metallo degno.» {fratello} ti guarda a lungo."),
                              "intrigue": {"branch": "forgiata"}}},
                 {"label": "«Con mezza spada, al massimo tagli il pane»",
                  "effects": {"relation": -15,
                              "text": "{fratello} non risponde. Continua a colpire l'aria, più forte.",
                              "intrigue": {"branch": "deriso"}}},
             ]},
            {"title": "Il manuale della Spada che Torna", "focus": "anziano", "gap": (3, 5),
             "text": ("Si sparge una voce: nelle rovine del vecchio clan di {fratello} è stato sepolto un manuale, "
                      "la «Spada che Torna», l'arte che fece del padre un maestro. {anziano} ha mandato i suoi "
                      "uomini a cercarlo. {fratello} ti viene a bussare di notte: «Non posso farcela da solo.»"),
             "choices": [
                 {"label": "Cercate la stanza segreta sotto le rovine",
                  "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": ("Sotto l'altare spaccato, una lastra suona vuota. Il manuale è lì, avvolto "
                                       "nella seta di un clan che non esiste più."), "intrigue": {"clue": 1, "branch": "trovato"}},
                  "failure": {"text": "Scavate fino all'alba: solo ossa e cenere. Gli uomini di {anziano} arrivano prima.",
                              "intrigue": {}}},
                 {"label": "Affronti gli uomini di {anziano} all'ingresso", "effects": {"intrigue": {"clue": 1}},
                  "command": "duello {anziano}"},
             ]},
            {"title": "Una sola copia", "focus": "fratello", "gap": (2, 3),
             "text": ("Il manuale è tra voi due, sul tavolo di una locanda. Lo avete letto insieme tutta la notte, e "
                      "avete capito la stessa cosa: l'arte si imprime nel meridiano di chi la studia per primo, e la "
                      "carta poi si sbriciola. Una sola copia. Una sola spada che torna. {fratello} tiene gli occhi "
                      "bassi. «Era di mio padre», dice piano. «Ma senza di te non l'avrei mai trovata.»"),
             "choices": [
                 {"label": "Lo strappi in due: «Metà a te, metà a me. Come fratelli»",
                  "effects": {"bond": "sworn", "heart": 10, "karma": 10, "relation": 30,
                              "text": ("Ognuno impara metà dell'arte. Nessuno dei due sarà mai completo da solo. "
                                       "{fratello} si incide il palmo e ti tende la mano insanguinata: «Fratelli.»"),
                              "intrigue": {"flag": "spada_fratelli", "end": "giurati"}}},
                 {"label": "Lo impari tu: «Ti insegnerò io, un giorno»",
                  "effects": {"prize": _MANUALE, "relation": -35,
                              "text": ("La carta si sbriciola tra le tue dita. {fratello} si alza senza una parola. "
                                       "Sulla porta si ferma: «Un giorno.» Non suona come una promessa."),
                              "intrigue": {"flag": "spada_rivali", "end": "rivali"}}},
                 {"label": "Lo vendi a {anziano}, e con lui {fratello} (1500 pietre)",
                  "effects": {"stones": 1500, "karma": -30, "infamy": 6, "relation": -80,
                              "text": ("All'alba gli uomini di {anziano} sfondano la porta. {fratello} ti guarda "
                                       "mentre lo trascinano via: non urla. È questo che ti resta in testa."),
                              "intrigue": {"flag": "spada_tradito", "end": "tradito"}}},
             ]},
        ],
        "auto_end": [{"outcome": "separati", "text": "{fratello} è partito da solo con la sua mezza spada."}],
        "outcomes": {"giurati": "Tu e {fratello} siete fratelli giurati: ognuno porta metà della Spada che Torna.",
                     "rivali": "Hai preso la Spada che Torna. {fratello} non l'ha dimenticato.",
                     "tradito": "Hai venduto {fratello} a {anziano}. Le pietre pesano più del previsto.",
                     "separati": "Le vostre strade si sono divise."},
    },
    # ---------------------------------------------------------------- II · fratelli
    {
        "key": "spada_fratello_accusato", "title": "La Spada Spezzata — Il fratello accusato", "kind": "legame",
        "weight": 6, "tier_min": 1, "req_flag": "spada_fratelli", "delay": 20,
        "cast": {"fratello": "legame:spada_fratelli", "mandante": "anziano"},
        "acts": [
            {"title": "La lettera senza firma", "focus": "fratello", "gap": (1, 2),
             "text": ("Ti arriva una lettera senza firma, ma conosci quella calligrafia storta: «Non venire.» Basta "
                      "chiedere in giro per sapere il resto. {fratello} è accusato di aver rubato il sigillo del "
                      "tesoro de {setta}; {mandante}, l'anziano che conduce il processo, chiede la sua testa. "
                      "Tuo fratello non ha chiesto aiuto a nessuno. Neanche a te."),
             "choices": [
                 {"label": "Indaghi sul furto prima del processo",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": ("Il sigillo è stato visto, la notte del furto, nelle mani del nipote di "
                                       "{mandante}. Un servo lo giura, se lo proteggerai."),
                              "intrigue": {"clue": 1, "branch": "prove"}},
                  "failure": {"text": "Nessuno parla. Tutti hanno paura di {mandante}.", "intrigue": {}}},
                 {"label": "Vai da lui in prigione",
                  "effects": {"relation": 20, "heart": 4,
                              "text": ("Ti guarda attraverso le sbarre e ride, stanco. «Ti avevo scritto di non "
                                       "venire.» «E io non so leggere», rispondi. Ride più forte."),
                              "intrigue": {"branch": "visitato"}}},
                 {"label": "Fai finta di non aver ricevuto la lettera",
                  "effects": {"relation": -60, "karma": -10,
                              "text": ("Il processo si fa senza di te. Lui sopravvive, chissà come. Ma da quel giorno "
                                       "qualcuno, in una cella buia, ripete il tuo nome come una preghiera al contrario."),
                              "intrigue": {"flag": "spada_ombra", "end": "abbandonato"}}},
             ]},
            {"title": "Il processo", "focus": "mandante", "gap": (2, 3),
             "text": ("La sala del giudizio è piena. {mandante} legge l'accusa con la voce di chi ha già deciso. "
                      "{fratello}, in catene, cerca i tuoi occhi tra la folla e li trova."),
             "choices": [
                 {"label": "Porti il servo e la verità davanti a tutti", "need_clues": 1,
                  "effects": {"fame": 12, "karma": 12, "prize": _ARGENTO,
                              "text": ("Il servo parla. Il nipote di {mandante} sbianca. L'anziano chiude il libro "
                                       "delle accuse con troppa calma: oggi ha perso, e non lo dimenticherà."),
                              "intrigue": {"flag": "spada_vincolo", "end": "assolto"}}},
                 {"label": "Sfidi {mandante}: «Il giudizio della spada»",
                  "effects": {"intrigue": {"flag": "spada_vincolo", "end": "duello"}}, "command": "duello {mandante}"},
                 {"label": "Ti prendi la colpa al posto suo",
                  "effects": {"infamy": 8, "heart": 15, "stones": -800,
                              "text": ("«Il ladro sono io.» Paghi la multa, ti prendi il marchio. {fratello} ti "
                                       "abbraccia fuori dalla sala così forte da toglierti il fiato."),
                              "intrigue": {"flag": "spada_vincolo", "end": "colpa"}}},
             ]},
        ],
        "auto_end": [{"outcome": "condannato", "text": "Il processo si è chiuso senza di te. {fratello} è stato esiliato."}],
        "outcomes": {"assolto": "Hai salvato {fratello} con la verità.",
                     "duello_vinto": "Hai vinto il giudizio della spada: {fratello} è libero.",
                     "duello_perso": "Hai perso il giudizio della spada, ma {fratello} ha visto che sei venuto.",
                     "duello_fuga": "Sei fuggito dal giudizio. {fratello} è stato esiliato, ma ti ha visto venire.",
                     "colpa": "Ti sei preso la colpa di {fratello}.",
                     "abbandonato": "Hai abbandonato {fratello} al suo processo.",
                     "condannato": "{fratello} è stato esiliato."},
    },
    # ---------------------------------------------------------------- II · rivali
    {
        "key": "spada_sfida_piazza", "title": "La Spada Spezzata — La sfida in piazza", "kind": "duello",
        "weight": 6, "tier_min": 1, "req_flag": "spada_rivali", "delay": 20,
        "cast": {"fratello": "legame:spada_rivali"},
        "acts": [
            {"title": "La mezza spada è intera", "focus": "fratello", "gap": (1, 2),
             "text": ("In piazza a {luogo} c'è folla attorno a un giovane che ha appena battuto tre discepoli di "
                      "fila. È {fratello}. La sua spada adesso è intera: una lama nuova, nera, saldata sulla vecchia "
                      "elsa. Ti vede. La folla si apre da sola. «Hai imparato la Spada che Torna?» chiede. «Io ho "
                      "imparato senza. Fammi vedere chi dei due aveva ragione.»"),
             "choices": [
                 {"label": "Accetti la sfida, qui, davanti a tutti",
                  "effects": {"fame": 6, "intrigue": {"flag": "spada_sfida", "end": "sfida"}},
                  "command": "duello {fratello}"},
                 {"label": "«Avevi ragione tu. Ti insegno ciò che ho imparato»",
                  "check": {"stat": "anima", "dc": 52},
                  "success": {"relation": 40, "heart": 8, "karma": 8,
                              "text": ("Ti fissa a lungo, cercando lo scherno. Non lo trova. Abbassa la spada. "
                                       "«Una lezione al giorno. E la prima la paghi tu, da bere.»"),
                              "intrigue": {"flag": "spada_vincolo", "end": "riconciliati"}},
                  "failure": {"relation": -10,
                              "text": "«Non voglio la tua elemosina.» Se ne va, ma ti ha dato un appuntamento.",
                              "intrigue": {"flag": "spada_sfida", "end": "rifiutata"}}},
                 {"label": "Te ne vai senza rispondere",
                  "effects": {"fame": -6,
                              "text": "Alle tue spalle, la folla ride. Lui no: lui ti scrive una data, su un muro.",
                              "intrigue": {"flag": "spada_sfida", "end": "evitata"}}},
             ]},
        ],
        "auto_end": [{"outcome": "partito", "text": "{fratello} ha lasciato la città, cercandoti altrove."}],
        "outcomes": {"sfida_vinto": "Hai battuto {fratello} in piazza. Lui ha sorriso: «Non è finita.»",
                     "sfida_perso": "{fratello} ti ha battuto in piazza, con la sua spada nera.",
                     "sfida_fuga": "Sei fuggito dalla sfida di {fratello}.",
                     "riconciliati": "Hai fatto pace con {fratello}: ora impara da te.",
                     "rifiutata": "{fratello} ha rifiutato il tuo aiuto e ti ha dato appuntamento.",
                     "evitata": "Hai evitato la sfida: {fratello} ti ha dato appuntamento.",
                     "partito": "{fratello} se n'è andato."},
    },
    # ---------------------------------------------------------------- II · traditore
    {
        "key": "spada_cicatrice", "title": "La Spada Spezzata — L'uomo con la cicatrice", "kind": "vendetta",
        "weight": 6, "tier_min": 1, "req_flag": "spada_tradito", "delay": 15,
        "cast": {"fratello": "legame:spada_tradito", "anziano": "anziano"},
        "acts": [
            {"title": "Ciò che esce dalle segrete", "focus": "fratello", "gap": (1, 2),
             "text": ("Una notte la porta della tua stanza si apre senza rumore. L'uomo sulla soglia ha una cicatrice "
                      "che gli attraversa il viso come una crepa in un vaso, e un'aura nera, sporca, che fa gemere "
                      "le travi. Ti ci vuole un momento per riconoscerlo. {fratello}. «Sono uscito dalle segrete di "
                      "{anziano} mangiando quello che c'era da mangiare», dice. «Non chiedermi cosa.»"),
             "choices": [
                 {"label": "Ti inginocchi e gli chiedi perdono",
                  "check": {"stat": "anima", "dc": 58},
                  "success": {"relation": 30, "heart": 10, "karma": 15,
                              "text": ("Resta in silenzio un tempo lunghissimo. Poi si siede per terra, davanti a te, "
                                       "e piange senza lacrime. «Mi resta solo una cosa da fare con te: un duello "
                                       "vero. Dopo, vedremo chi siamo.»"),
                              "intrigue": {"flag": "spada_sfida", "end": "perdono"}},
                  "failure": {"relation": -20,
                              "text": "«Il perdono si chiede in piedi.» Ti sputa ai piedi e sparisce dalla finestra.",
                              "intrigue": {"flag": "spada_ombra", "end": "odio"}}},
                 {"label": "Lo affronti prima che sia lui a farlo",
                  "effects": {"intrigue": {"flag": "spada_ombra", "end": "duello"}}, "command": "duello {fratello}"},
                 {"label": "Gli dai il nascondiglio di {anziano}",
                  "effects": {"karma": -5,
                              "text": ("Prende il foglio e sorride per la prima volta. «Prima lui.» Non dice chi viene "
                                       "dopo. Non serve."),
                              "intrigue": {"flag": "spada_ombra", "end": "vendetta"}}},
             ]},
        ],
        "auto_end": [{"outcome": "svanito", "text": "L'uomo con la cicatrice è svanito nella notte."}],
        "outcomes": {"perdono": "{fratello} ti ha quasi perdonato. Manca un duello.",
                     "odio": "{fratello} ti odia: lo rivedrai.",
                     "duello_vinto": "Hai respinto {fratello}. Si è ritirato nell'ombra, a crescere.",
                     "duello_perso": "{fratello} ti ha lasciato a terra, vivo: «Morire sarebbe troppo poco.»",
                     "duello_fuga": "Sei fuggito da {fratello}.",
                     "vendetta": "Hai indicato a {fratello} la strada per la sua vendetta. La prima.",
                     "svanito": "{fratello} è svanito."},
    },
    # ---------------------------------------------------------------- III · fratelli giurati
    {
        "key": "spada_ricomposta", "title": "La Spada Spezzata — La spada ricomposta", "kind": "legame",
        "weight": 7, "tier_min": 2, "req_flag": "spada_vincolo", "delay": 25,
        "cast": {"fratello": "legame:spada_vincolo", "nemico": "rivale"},
        "acts": [
            {"title": "La Gola delle Mille Lame", "focus": "nemico", "gap": (1, 2),
             "text": ("Le due metà della Spada che Torna si cercano: l'hai sentito per mesi, un formicolio nel "
                      "meridiano. Stanotte è diventato un grido. {fratello} è ferito nella Gola delle Mille Lame, e "
                      "chi lo bracca è {nemico}, che vuole entrambe le metà dell'arte — la sua e la tua."),
             "choices": [
                 {"label": "Corri da lui senza fermarti",
                  "check": {"stat": "potenza", "dc": 58},
                  "success": {"text": ("Arrivi mentre {nemico} alza la lama sul suo collo. La tua metà dell'arte "
                                       "risponde da sola: la spada torna, e devia il colpo."),
                              "intrigue": {"clue": 1, "branch": "arrivato"}},
                  "failure": {"injury": 1,
                              "text": "La gola è un labirinto di lame. Arrivi tardi, sanguinando, ma arrivi.",
                              "intrigue": {"branch": "tardi"}}},
                 {"label": "Gli mandi pillole e un messaggio: «Resisti» (500 pietre)",
                  "effects": {"stones": -500, "text": "Il messaggero corre. Tu lo segui, più lento.",
                              "intrigue": {"branch": "pillole"}}},
             ]},
            {"title": "Schiena contro schiena", "focus": "fratello", "gap": (1, 1),
             "text": ("{fratello} si rialza e ti mette la schiena contro la schiena. Due metà di un'arte, due metà "
                      "di una spada. Gli uomini di {nemico} vi circondano. «Come la prima volta, al fiume», ride lui, "
                      "con la bocca piena di sangue. «Tu a destra.»"),
             "choices": [
                 {"label": "Combattete insieme: la Spada che Torna, intera per la prima volta",
                  "check": {"stat": "potenza", "dc": 60},
                  "success": {"bond": "sworn", "relation": 30, "karma": 15, "fame": 15, "prize": _ORO,
                              "title": "Fratello della Spada Ricomposta",
                              "text": ("Le due metà si chiudono. La spada torna, e torna, e torna: quando finisce "
                                       "non c'è più nessuno in piedi tranne voi due. {fratello} raccoglie i pezzi "
                                       "della lama di suo padre e te li mette in mano. «Tienili tu. Sei la mia famiglia.»"),
                              "intrigue": {"end": "fratelli"}},
                  "failure": {"npc_falls": True, "heart": 20, "karma": 10,
                              "text": ("Una lama destinata alla tua schiena la prende lui. Muore sorridendo, con la "
                                       "mano sulla tua spalla: «Tu a destra, ti avevo detto.» La sua metà dell'arte "
                                       "passa nel tuo meridiano, calda come un'ultima stretta."),
                              "intrigue": {"end": "caduto"}}},
                 {"label": "Affronti {nemico} da solo, perché lui possa fuggire",
                  "effects": {"intrigue": {"end": "duello"}}, "command": "duello {nemico}"},
             ]},
        ],
        "auto_end": [{"outcome": "mancato", "text": "Non sei arrivato alla Gola. Nessuno sa cosa sia successo a {fratello}."}],
        "outcomes": {"fratelli": "La Spada che Torna è di nuovo intera: tu e {fratello} siete fratelli per sempre.",
                     "caduto": "{fratello} è morto per te nella Gola delle Mille Lame.",
                     "duello_vinto": "Hai abbattuto {nemico} da solo: {fratello} ti deve la vita, e lo sa.",
                     "duello_perso": "{nemico} ti ha battuto, ma {fratello} è fuggito: vivrà per vendicarti.",
                     "duello_fuga": "Siete fuggiti entrambi dalla Gola.",
                     "mancato": "Non sei arrivato in tempo."},
    },
    # ---------------------------------------------------------------- III · rivali
    {
        "key": "spada_picco", "title": "La Spada Spezzata — Il picco senza nome", "kind": "duello",
        "weight": 7, "tier_min": 2, "req_flag": "spada_sfida", "delay": 30,
        "cast": {"fratello": "legame:spada_sfida"},
        "acts": [
            {"title": "L'appuntamento", "focus": "fratello", "gap": (2, 3),
             "text": ("Arriva una spada piantata nella porta, e attorno all'elsa un nastro con scritto: «Picco senza "
                      "nome, alla prossima luna.» È di {fratello}. Hai il tempo di prepararti. Anche lui lo avrà."),
             "choices": [
                 {"label": "Ti alleni ogni notte, solo con la spada",
                  "check": {"stat": "potenza", "dc": 55},
                  "success": {"text": "Alla fine del mese la tua lama taglia la pioggia a metà.",
                              "intrigue": {"clue": 1, "branch": "pronto"}},
                  "failure": {"injury": 1, "text": "Ti alleni troppo e male. Arriverai stanco.", "intrigue": {}}},
                 {"label": "Mediti: un duello si vince prima nel cuore",
                  "effects": {"heart": 6, "text": "Pensi a lui, a quel primo giorno al fiume. Non lo odi. Forse non l'hai mai odiato.",
                              "intrigue": {"branch": "calmo"}}},
             ]},
            {"title": "Il picco senza nome", "focus": "fratello", "gap": (1, 2),
             "text": ("Sulla vetta tira un vento che taglia. {fratello} è già lì, seduto sulla roccia, con la spada "
                      "nera sulle ginocchia. Si alza. «Finalmente.» Non c'è nessun altro: nessun pubblico, nessun "
                      "maestro, nessuno a cui dimostrare niente. Solo voi due e tutti gli anni che vi siete rubati."),
             "choices": [
                 {"label": "Combatti fino alla fine", "effects": {"intrigue": {"end": "duello"}},
                  "command": "duello {fratello}"},
                 {"label": "Abbassi la spada al primo sangue: «Basta così»",
                  "check": {"stat": "potenza", "dc": 58},
                  "success": {"bond": "sworn", "relation": 50, "fame": 12, "heart": 12, "prize": _ARGENTO,
                              "title": "Rivale Rispettato",
                              "text": ("Il tuo colpo gli apre la guancia, il suo ti sfiora la gola. Vi fermate "
                                       "insieme. Lui ride, poi si siede nella neve. «Dieci anni per arrivare qui, "
                                       "e ora non so cosa fare domani.» «Domani scendiamo», dici. «Insieme.»"),
                              "intrigue": {"end": "rispetto"}},
                  "failure": {"fame": -8, "injury": 1,
                              "text": ("Abbassi la spada un attimo troppo presto. Lui non ferma la sua. Ti risparmia "
                                       "all'ultimo, con disprezzo: «Neanche questo sai fare per bene.»"),
                              "intrigue": {"end": "umiliato"}}},
                 {"label": "Getti la spada giù dal picco", "need_branch": "calmo",
                  "effects": {"relation": 60, "heart": 20, "karma": 15, "bond": "sworn",
                              "title": "Colui che Gettò la Spada",
                              "text": ("Lui la guarda cadere. Poi, piano, getta anche la sua. Scendete senza armi, "
                                       "parlando di vostro padre — il suo, il tuo, non fa più differenza."),
                              "intrigue": {"end": "pace"}}},
             ]},
        ],
        "auto_end": [{"outcome": "assente", "effects": {"fame": -10},
                      "text": "Non sei salito sul picco. {fratello} ha aspettato tre giorni, poi ha spezzato la sua spada."}],
        "outcomes": {"duello_vinto": "Hai vinto il duello sul picco senza nome. {fratello} non ti sfiderà più.",
                     "duello_perso": "{fratello} ti ha battuto sul picco senza nome. Aveva ragione lui.",
                     "duello_fuga": "Sei fuggito dal picco senza nome.",
                     "rispetto": "Tu e {fratello} vi siete fermati al primo sangue: rivali, e fratelli.",
                     "umiliato": "{fratello} ti ha umiliato sul picco.",
                     "pace": "Avete gettato le spade: la rivalità è finita.",
                     "assente": "Non ti sei presentato al picco."},
    },
    # ---------------------------------------------------------------- III · nemesi
    {
        "key": "spada_demone", "title": "La Spada Spezzata — Il demone con la tua spada", "kind": "vendetta",
        "weight": 7, "tier_min": 2, "req_flag": "spada_ombra", "delay": 25,
        "cast": {"fratello": "legame:spada_ombra"},
        "acts": [
            {"title": "Il tuo nome nel sangue", "focus": "fratello", "gap": (1, 2),
             "text": ("Un villaggio a due giorni da {luogo} è stato raso al suolo in una notte. Sui muri, scritto col "
                      "sangue, c'è il tuo nome. Chi è sopravvissuto parla di un uomo con la cicatrice e una spada "
                      "nera che «torna sempre indietro». Lo chiamano già la Spada Spezzata. Lo conosci."),
             "choices": [
                 {"label": "Segui le sue tracce",
                  "effects": {"bond": "nemesis", "intrigue": {"clue": 1},
                              "text": ("Le tracce sono facili da seguire: lui vuole essere trovato. A ogni villaggio, "
                                       "un messaggio. A ogni messaggio, un ricordo vostro.")}},
                 {"label": "Proteggi i villaggi vicini",
                  "effects": {"bond": "nemesis", "karma": 12, "fame": 6,
                              "text": "Resti tre notti di guardia. La quarta notte, una spada nera si pianta accanto a te.",
                              "intrigue": {"branch": "protetti"}}},
             ]},
            {"title": "Il ponte di ferro", "focus": "fratello", "gap": (2, 3),
             "text": ("Ti aspetta al centro del ponte di ferro sopra la gola, come nelle storie. L'aura nera ora è "
                      "così densa che la pioggia evapora prima di toccarlo. «Mi hai venduto per millecinquecento "
                      "pietre», dice. «Ho fatto i conti: ne ho uccisi uno per ogni pietra. Mancano gli ultimi.»"),
             "choices": [
                 {"label": "Lo affronti: deve finire qui", "effects": {"intrigue": {"end": "duello"}},
                  "command": "duello {fratello}"},
                 {"label": "Gli offri il tuo sangue per spezzare il demone", "need_clues": 1,
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"end_bond": "nemesis", "relation": 60, "heart": 25, "karma": 30, "fame": 10,
                              "title": "Colui che Riportò Indietro un Demone",
                              "text": ("Ti tagli il palmo come un giorno avevate quasi fatto, al tavolo della locanda. "
                                       "Il demone urla quando il tuo sangue lo tocca. Quando si zittisce, sul ponte "
                                       "c'è solo un ragazzo stanco con mezza spada. «Perché?» «Perché era mia la colpa.»"),
                              "intrigue": {"end": "redento"}},
                  "failure": {"injury": 3,
                              "text": ("Il demone beve il tuo sangue e ride con la sua bocca. «Non basta.» Ti lascia "
                                       "vivo sul ponte: «Ti voglio vedere invecchiare con questo.»"),
                              "intrigue": {"end": "respinto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "strage", "effects": {"infamy": 4},
                      "text": "La Spada Spezzata ha raso al suolo un altro villaggio, col tuo nome sui muri."}],
        "outcomes": {"duello_vinto": "Hai abbattuto la Spada Spezzata sul ponte di ferro. Era tuo fratello, un tempo.",
                     "duello_perso": "La Spada Spezzata ti ha battuto. La sua conta non è finita.",
                     "duello_fuga": "Sei fuggito dal ponte di ferro.",
                     "redento": "Hai riportato indietro {fratello} dal suo demone.",
                     "respinto": "Il demone di {fratello} ha rifiutato il tuo sangue.",
                     "strage": "La Spada Spezzata continua la sua strage."},
    },

    # ================================================================ IL MERCANTE DI DESTINI — seguiti
    {
        "key": "mercante_conto", "title": "Il Mercante di Destini — Il conto del socio", "kind": "intrigo",
        "weight": 6, "tier_min": 2, "req_flag": "mercante_socio", "delay": 25,
        "cast": {"mandante": "legame:mercante_socio", "vittima": "alleato"},
        "acts": [
            {"title": "Il destino che vuole", "focus": "vittima", "gap": (1, 2),
             "text": ("Da mesi le fiale di luce rubata ti rendono ricco. Stanotte il Mercante ti versa da bere e posa "
                      "sul tavolo una lastra d'osso nuova, bianchissima. Sopra c'è inciso un nome: {vittima}. «Il suo "
                      "destino è il più dolce che abbia mai annusato. Me lo porti tu. Di te si fida.»"),
             "choices": [
                 {"label": "Glielo porti", "effects": {"stones": 2500, "karma": -30, "relation": -60, "infamy": 6,
                                                      "text": ("{vittima} ti abbraccia quando arrivi. La mattina dopo non "
                                                               "ricorda più il tuo nome."),
                                                      "intrigue": {"branch": "consegnato"}}},
                 {"label": "Fingi di accettare e prepari una trappola",
                  "check": {"stat": "istinto", "dc": 58},
                  "success": {"relation": 15,
                              "text": ("Avverti {vittima}, scambi la lastra con una falsa, e scopri dove il "
                                       "Mercante tiene la coppa d'osso in cui beve."),
                              "intrigue": {"clue": 1, "branch": "trappola"}},
                  "failure": {"text": "Il Mercante annusa la menzogna come annusa i destini. Sorride: «Peccato.»",
                              "intrigue": {"branch": "scoperto"}}},
                 {"label": "Rifiuti: «Lui no»",
                  "effects": {"relation": 10, "lifespan_years": -3,
                              "text": ("Il Mercante non si arrabbia. Ti posa un dito sulla fronte, e senti un anno — "
                                       "tre anni — scivolarti via. «Allora pagherai tu. Un sorso alla volta.»"),
                              "intrigue": {"branch": "rifiuto"}}},
             ]},
            {"title": "La coppa d'osso", "focus": "mandante", "gap": (2, 3),
             "text": ("La tenda viola, a notte fonda. Il Mercante beve dalla coppa d'osso e la sua pelle si fa liscia "
                      "come quella di un ragazzo. «Sei un buon socio. Ancora cent'anni insieme, che ne dici?»"),
             "choices": [
                 {"label": "Spezzi la coppa e restituisci i destini rubati", "need_clues": 1,
                  "effects": {"karma": 30, "fame": 12, "lifespan_years": 15, "prize": _ORO,
                              "text": ("La coppa si spezza con un suono di campana. Mille luci escono dalla tenda e "
                                       "tornano a casa; una, la più piccola, torna dentro di te. Il Mercante "
                                       "invecchia di un secolo in un respiro."),
                              "intrigue": {"end": "rotto"}}},
                 {"label": "Rompi il patto: «Il socio sei tu, e io mi ritiro»",
                  "effects": {"intrigue": {"end": "duello"}}, "command": "duello {mandante}"},
                 {"label": "Brindi: cent'anni insieme",
                  "effects": {"stones": 5000, "karma": -40, "lifespan_years": 10, "infamy": 8,
                              "title": "Socio del Mercante di Destini",
                              "text": "Bevi anche tu dalla coppa. È dolce. Non pensare a chi l'ha riempita.",
                              "intrigue": {"end": "eterno"}}},
             ]},
        ],
        "auto_end": [{"outcome": "riscosso", "effects": {"lifespan_years": -5},
                      "text": "Il Mercante ha riscosso il suo conto da te, un sorso alla volta."}],
        "outcomes": {"rotto": "Hai spezzato la coppa del Mercante: i destini rubati sono tornati a casa.",
                     "duello_vinto": "Hai rotto il patto col Mercante a colpi di spada.",
                     "duello_perso": "Il Mercante ti ha battuto: il vostro patto resta, alle sue condizioni.",
                     "duello_fuga": "Sei fuggito dalla tenda viola.",
                     "eterno": "Sei socio del Mercante di Destini, per cent'anni.",
                     "riscosso": "Il Mercante ha riscosso il conto."},
    },
    {
        "key": "mercante_lastra", "title": "Il Mercante di Destini — La lastra spezzata", "kind": "intrigo",
        "weight": 6, "tier_min": 3, "req_flag": "mercante_ritorno", "delay": 30,
        "cast": {"mandante": "legame:mercante_ritorno", "pedina": "sgherro"},
        "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["La lastra all'asta porta inciso il tuo nome e la data del tuo prossimo sfondamento.",
                   "Chi possiede la lastra di un uomo può spezzargli il destino nel momento in cui lo tocca il cielo.",
                   "{pedina} è il nuovo servo del Mercante: porta l'ago d'osso e il tuo odore addosso."],
        "acts": [
            {"title": "All'asta, il tuo destino", "focus": "mandante", "gap": (1, 2),
             "text": ("La tenda viola è tornata, e stavolta non vende letture: vende lastre. All'asta di {luogo} c'è "
                      "un pezzo d'osso inciso fitto, spezzato a metà. I compratori sussurrano un nome. È il tuo. "
                      "Il Mercante, dal fondo della sala, ti fa un inchino. Non si è dimenticato di te."),
             "choices": [
                 {"label": "Partecipi all'asta (2000 pietre)",
                  "effects": {"stones": -2000, "text": "Batti tutti. La metà della lastra è tua: è calda, come viva.",
                              "intrigue": {"clue": 1, "branch": "comprata"}}},
                 {"label": "La rubi durante la notte",
                  "check": {"stat": "istinto", "dc": 60},
                  "success": {"text": "Entri dal tetto, esci dal tetto. Mezza lastra, e la mappa per l'altra metà.",
                              "intrigue": {"clue": 1, "branch": "rubata"}},
                  "failure": {"infamy": 4, "injury": 1, "text": "Le guardie dell'asta ti scoprono. Fuggi a mani vuote.",
                              "intrigue": {}}},
                 {"label": "Lasci perdere: un destino non si compra",
                  "effects": {"heart": 4, "text": "Esci dalla sala. Alle tue spalle il martelletto batte tre volte.",
                              "intrigue": {"branch": "lasciata"}}},
             ]},
            {"title": "L'ago d'osso", "focus": "pedina", "gap": (2, 3),
             "text": ("{pedina} ti segue da giorni. Stanotte entra nella tua stanza con l'ago d'osso, deciso a "
                      "incidere sulla tua carne ciò che manca alla lastra."),
             "choices": [
                 {"label": "Lo affronti", "effects": {"intrigue": {"clue": 1}}, "command": "duello {pedina}"},
                 {"label": "Lo lasci fare, fingendo di dormire, per capire",
                  "check": {"stat": "anima", "dc": 58},
                  "success": {"text": "L'ago traccia una runa: la stessa che chiude la lastra. Ora sai come aprirla.",
                              "intrigue": {"clue": 1}},
                  "failure": {"lifespan_years": -2, "text": "Ti svegli più vecchio, con una runa nuova sul polso.",
                              "intrigue": {}}},
             ]},
            {"title": "Riscrivere il destino", "auto": True,
             "text": "Le due metà della lastra si cercano. Quando si toccano, tu senti il cielo trattenere il fiato.",
             "endings": [
                 {"need_clues": 3, "outcome": "riscritto",
                  "effects": {"lifespan_years": 20, "heart": 12, "bt_bonus": 0.08, "karma": 10,
                              "title": "Colui che Spezzò la Propria Lastra"},
                  "text": ("Apri la runa e incidi tu, sopra la sua grafia. La lastra si sbriciola in polvere bianca: "
                           "nessuno, mai più, potrà leggere il tuo destino. Neanche tu. È la cosa più bella che ti "
                           "sia capitata. Il Mercante, lontano, sente la sua lastra migliore andare in pezzi.")},
                 {"need_clues": 2, "outcome": "spezzato", "effects": {"prize": _ARGENTO, "heart": 6},
                  "text": "Spezzi la lastra prima che altri la usino. Non hai riscritto niente, ma nessuno ti possiede."},
                 {"outcome": "posseduto", "effects": {"lifespan_years": -5}, "flag": "mercante_ritorno",
                  "text": ("La metà che ti manca resta al Mercante. Ogni tanto, la notte, senti qualcuno sfogliarti "
                           "come un libro. Tornerà a chiederti il resto.")},
             ]},
        ],
        "auto_end": [{"outcome": "venduta", "effects": {"lifespan_years": -3},
                      "text": "La lastra col tuo nome è stata venduta a qualcuno che non conosci."}],
        "outcomes": {"duello_vinto": "Hai respinto il servo del Mercante.", "duello_perso": "Il servo del Mercante ti ha inciso.",
                     "venduta": "La tua lastra è stata venduta."},
    },

    # ================================================================ IL MAESTRO CHE NON MUORE — I
    {
        "key": "maestro_eterno", "title": "Il Maestro che non muore — La voce nella giada", "kind": "mistero",
        "weight": 6, "tier_min": 2, "cast": {"maestro": "spettro"},
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["Il Maestro Senza Tomba ha già vissuto in sette corpi: tutti di discepoli che lo amavano.",
                   "Ogni volta che ti insegna qualcosa, la giada diventa un po' più calda e tu un po' più freddo.",
                   "{maestro} non porta il frammento per devozione: lo porta perché, se lo lascia, il Maestro sceglie lui."],
        "acts": [
            {"title": "La voce nella giada", "focus": "maestro", "gap": (1, 2),
             "text": ("Nella grotta di un eremita, sopra {luogo}, un pendente di giada verde ti parla prima ancora "
                      "dell'uomo che lo porta. «Finalmente un meridiano decente», dice la giada. L'eremita, {maestro}, "
                      "sospira come chi ha sentito quella voce per trecento anni. «È il mio maestro. Il Maestro Senza "
                      "Tomba. È morto prima che nascesse il nonno di tuo nonno, e non ha mai smesso di parlare.»"),
             "choices": [
                 {"label": "Chiedi alla giada di insegnarti",
                  "effects": {"prize": _MANUALE,
                              "text": ("La voce ti insegna per una notte intera. All'alba sai cose che nessun vivo sa. "
                                       "Hai anche le mani fredde, ma sarà la grotta."),
                              "intrigue": {"clue": 1, "branch": "allievo"}}},
                 {"label": "Chiedi all'eremita cosa vuole davvero quella voce",
                  "check": {"stat": "anima", "dc": 52},
                  "success": {"relation": 15,
                              "text": "{maestro} abbassa la voce, anche se la giada sente tutto: «Un corpo. Vuole sempre un corpo.»",
                              "intrigue": {"clue": 1}},
                  "failure": {"text": "{maestro} scuote la testa e cambia discorso.", "intrigue": {}}},
             ]},
            {"title": "Chi porta il frammento", "focus": "maestro", "gap": (3, 5),
             "text": ("Torni alla grotta. {maestro} è più magro, più vecchio. «Sono stanco», dice. «Trecento anni. "
                      "Prendilo tu, il frammento. O lascialo a me, e lascia che mi consumi. O distruggilo — ma allora "
                      "con lui muore la più grande arte del Dao che sia mai esistita.» La giada, per una volta, tace."),
             "choices": [
                 {"label": "Prendi il pendente: «Lo porto io»",
                  "effects": {"heart": 4, "relation": 25, "bt_bonus": 0.04,
                              "text": ("La giada si scalda contro il tuo petto. «Bravo ragazzo», dice. Hai la "
                                       "sensazione di aver firmato qualcosa che non hai letto."),
                              "intrigue": {"flag": "maestro_patto", "end": "patto"}}},
                 {"label": "Lo lasci a {maestro}: «È il tuo maestro, non il mio»",
                  "effects": {"relation": -10,
                              "text": "{maestro} chiude gli occhi. «Hai ragione.» Non sembra sollevato.",
                              "intrigue": {"flag": "maestro_eremita", "end": "custode"}}},
                 {"label": "Spezzi la giada", "need_clues": 1,
                  "effects": {"karma": 10, "heart": 8, "prize": _BRONZO, "relation": 40,
                              "text": ("La giada urla con trecento anni di voce. Poi niente. {maestro} piange come "
                                       "un bambino, e per la prima volta da secoli dorme una notte intera."),
                              "intrigue": {"end": "distrutto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "silenzio", "text": "Non sei tornato alla grotta. La giada aspetterà un altro."}],
        "outcomes": {"patto": "Porti al collo il Maestro Senza Tomba.",
                     "custode": "Hai lasciato il Maestro Senza Tomba al suo eremita.",
                     "distrutto": "Hai spezzato la giada: il Maestro Senza Tomba ha avuto, finalmente, una tomba.",
                     "silenzio": "La voce nella giada aspetta un altro allievo."},
    },
    # ---------------------------------------------------------------- II · l'hai portato tu
    {
        "key": "maestro_corpo", "title": "Il Maestro che non muore — Il corpo in prestito", "kind": "mistero",
        "weight": 7, "tier_min": 4, "req_flag": "maestro_patto", "delay": 30,
        "cast": {"maestro": "legame:maestro_patto"},
        "acts": [
            {"title": "Ti svegli altrove", "focus": "maestro", "gap": (1, 2),
             "text": ("Da settimane ti svegli in posti dove non ricordi di essere andato: sul tetto, nella foresta, "
                      "una volta in ginocchio davanti a una tomba senza nome. La giada al collo è calda come una "
                      "mano. «Il tuo corpo è comodo», dice. «Ma è tuo, lo so, lo so. Facciamo un patto. Il corpo di "
                      "{maestro} è vecchio, ma andrebbe bene. Lui è stanco, e me lo deve.»"),
             "choices": [
                 {"label": "Resisti alla voce con tutta la tua anima",
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"heart": 6,
                              "text": ("Per una notte intera tieni la porta chiusa. All'alba la voce è più debole, "
                                       "e tu sai dove sta il suo punto più fragile."),
                              "intrigue": {"clue": 1, "branch": "resistito"}},
                  "failure": {"lifespan_years": -3,
                              "text": "Ti svegli sul bordo di un precipizio, con un piede nel vuoto. La voce ride.",
                              "intrigue": {}}},
                 {"label": "Ascolti fino in fondo la sua proposta",
                  "effects": {"text": ("Parla per ore: del Dao che ti lascerà, dei regni che salirai, della tomba che "
                                       "non ha mai avuto. Ti accorgi che ti sta pregando."),
                              "intrigue": {"branch": "ascoltato"}}},
             ]},
            {"title": "Tre strade per un'anima vecchia", "focus": "maestro", "gap": (2, 3),
             "text": ("Davanti alla grotta di {maestro}. L'eremita ti aspetta: sa già tutto. «Decidi tu», dice. "
                      "«Sono pronto a qualsiasi cosa, tranne a portarlo un altro secolo.»"),
             "choices": [
                 {"label": "Gli dai il corpo di {maestro}",
                  "effects": {"karma": -25, "prize": _ORO, "bt_bonus": 0.06,
                              "text": ("{maestro} si siede, chiude gli occhi. Quando li riapre, sono di un altro "
                                       "colore. «Grazie, ragazzo», dice il Maestro con la sua bocca. «Non lo dimenticherò.»"),
                              "intrigue": {"flag": "maestro_rinato", "end": "rinato"}}},
                 {"label": "Gli costruisci un corpo di giada col tuo sangue (3000 pietre)", "need_branch": "ascoltato",
                  "effects": {"stones": -3000, "lifespan_years": -5, "relation": 30,
                              "text": ("Tre notti di forgia e di sangue. Il fantoccio apre gli occhi di giada e si "
                                       "guarda le mani. «È… stretto», dice il Maestro. «Ma è mio.» {maestro} ride, libero."),
                              "intrigue": {"flag": "maestro_fantoccio", "end": "fantoccio"}}},
                 {"label": "Lo sigilli per sempre", "need_clues": 1,
                  "check": {"stat": "anima", "dc": 64},
                  "success": {"heart": 15, "karma": 12, "prize": _ARGENTO, "relation": 30,
                              "title": "Sigillatore del Maestro Senza Tomba",
                              "text": ("Colpisci il punto fragile. La voce si spegne come una candela. La giada è "
                                       "solo giada, adesso. Dentro, qualcosa dorme. Per sempre, si spera."),
                              "intrigue": {"end": "sigillato"}},
                  "failure": {"injury": 2, "lifespan_years": -5,
                              "text": ("Il sigillo si spezza. La voce schizza fuori dalla giada come fumo e si infila "
                                       "nella bocca aperta di {maestro}. L'eremita si rialza con gli occhi di un altro."),
                              "intrigue": {"flag": "maestro_rinato", "end": "sfuggito"}}},
             ]},
        ],
        "auto_end": [{"outcome": "consumato", "effects": {"lifespan_years": -5},
                      "text": "La giada ti ha consumato un po' di vita. Il Maestro aspetta ancora."}],
        "outcomes": {"rinato": "Il Maestro Senza Tomba è rinato nel corpo di {maestro}.",
                     "fantoccio": "Il Maestro Senza Tomba vive in un corpo di giada che hai forgiato tu.",
                     "sigillato": "Hai sigillato il Maestro Senza Tomba per sempre.",
                     "sfuggito": "Il Maestro Senza Tomba ti è sfuggito in un corpo nuovo.",
                     "consumato": "La giada ti consuma."},
    },
    # ---------------------------------------------------------------- II · l'hai lasciato all'eremita
    {
        "key": "maestro_occhi", "title": "Il Maestro che non muore — Gli occhi dell'eremita", "kind": "mistero",
        "weight": 7, "tier_min": 4, "req_flag": "maestro_eremita", "delay": 30,
        "cast": {"maestro": "legame:maestro_eremita"},
        "acts": [
            {"title": "Gli occhi di un altro colore", "focus": "maestro", "gap": (1, 2),
             "text": ("{maestro} scende in città, per la prima volta in trecento anni. Cammina dritto, ride forte, "
                      "beve vino. Ha gli occhi di un altro colore. Quando ti vede ti saluta con un inchino da vecchio "
                      "maestro: «Avevi ragione tu, ragazzo. Non era il tuo maestro. Adesso è il mio corpo.»"),
             "choices": [
                 {"label": "Lo affronti: «Ridagli il suo corpo»",
                  "effects": {"intrigue": {"flag": "maestro_rinato", "end": "duello"}}, "command": "duello {maestro}"},
                 {"label": "Cerchi l'eremita dentro di lui",
                  "check": {"stat": "anima", "dc": 62},
                  "success": {"bond": "master", "relation": 50, "heart": 15, "karma": 20, "prize": _ARGENTO,
                              "text": ("Lo chiami col suo nome, quello vero, e ripeti le cose che ti ha detto in grotta. "
                                       "Qualcosa, dentro, si aggrappa alla tua voce. Il Maestro urla e si dissolve. "
                                       "L'eremita cade in ginocchio: «Sono io. Sono io.» Da quel giorno, ti insegna lui."),
                              "intrigue": {"end": "liberato"}},
                  "failure": {"text": "Lo chiami. Risponde il Maestro, con la sua voce: «Non c'è più.»",
                              "intrigue": {"flag": "maestro_rinato", "end": "perduto"}}},
                 {"label": "Lo lasci andare: in fondo, l'eremita era stanco",
                  "effects": {"karma": -8, "text": "Il Maestro ti fa l'occhiolino e se ne va per la sua strada.",
                              "intrigue": {"flag": "maestro_rinato", "end": "lasciato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "partito", "text": "Il Maestro, nel corpo dell'eremita, ha lasciato la regione."}],
        "outcomes": {"duello_vinto": "Hai battuto il Maestro nel corpo dell'eremita: è fuggito a cercarsene un altro.",
                     "duello_perso": "Il Maestro ti ha battuto con le mani dell'eremita.",
                     "duello_fuga": "Sei fuggito dal Maestro.",
                     "liberato": "Hai liberato {maestro} dal Maestro Senza Tomba: ora è il tuo maestro.",
                     "perduto": "L'eremita {maestro} non c'è più: c'è solo il Maestro.",
                     "lasciato": "Hai lasciato al Maestro il corpo dell'eremita.",
                     "partito": "Il Maestro se n'è andato."},
    },
    # ---------------------------------------------------------------- III · il Maestro rinato
    {
        "key": "maestro_senza_tomba", "title": "Il Maestro che non muore — Il Maestro Senza Tomba", "kind": "mistero",
        "weight": 8, "tier_min": 6, "req_flag": "maestro_rinato", "delay": 40,
        "cast": {"maestro": "legame:maestro_rinato", "erede": "genio"},
        "indagine": "anima", "need": 2, "reveal_act": 1,
        "indizi": ["Il Maestro cambia corpo ogni cinquant'anni: il prossimo è già scelto.",
                   "Ciò che il Maestro teme davvero non è la spada: è una tomba con il suo nome scritto sopra.",
                   "Il suo vero nome, quello di quando era vivo, è inciso sotto la sua prima lastra, nella grotta."],
        "acts": [
            {"title": "Una setta nata in un anno", "focus": "maestro", "gap": (1, 2),
             "text": ("In un anno è nata una setta che fa tremare le altre. Il suo patriarca insegna arti perdute da "
                      "millenni, e i suoi discepoli lo adorano. Lo chiamano il Maestro Senza Tomba. Ti riceve nel "
                      "suo padiglione con un sorriso che conosci. «Il mio primo allievo di questo secolo! Siediti. "
                      "Ho un'offerta per te.»"),
             "choices": [
                 {"label": "Ascolti l'offerta in ginocchio, come un allievo",
                  "effects": {"relation": 20, "text": ("«Sarai il mio erede. Tutto ciò che so, tutto ciò che sono stato.» "
                                                      "Non dice cosa vuole in cambio. Non lo dice mai."),
                              "intrigue": {"branch": "erede"}}},
                 {"label": "Torni nella grotta dove tutto è cominciato",
                  "check": {"stat": "istinto", "dc": 62},
                  "success": {"text": ("Sotto la prima lastra della grotta, inciso nella roccia, c'è un nome. Il suo "
                                       "nome vero, di quando era un uomo e aveva paura di morire."),
                              "intrigue": {"clue": 1, "branch": "nome"}},
                  "failure": {"text": "La grotta è stata svuotata. Ci è già passato lui.", "intrigue": {}}},
                 {"label": "Avverti le sette vicine",
                  "effects": {"fame": 8, "text": "Ti ascoltano a metà. Ma qualcuno, tra gli anziani, ti crede.",
                              "intrigue": {"branch": "allarme"}}},
             ]},
            {"title": "Il discepolo scelto", "focus": "erede", "gap": (2, 3),
             "text": ("Il discepolo prediletto del Maestro si chiama {erede}: il più dotato, il più devoto. Sta "
                      "preparando la cerimonia per «ricevere l'eredità». Non sa che l'eredità è lui, il suo corpo."),
             "choices": [
                 {"label": "Gli racconti la verità sui sette corpi",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"relation": 35, "bond": "companion",
                              "text": "{erede} ti ascolta, pallido. Poi ti porta i registri segreti della setta.",
                              "intrigue": {"clue": 1, "branch": "salvato"}},
                  "failure": {"relation": -20, "text": "«Menti. Il Maestro mi ama.» Ti caccia dal padiglione.",
                              "intrigue": {}}},
                 {"label": "Lasci che la cerimonia si faccia",
                  "effects": {"karma": -10, "text": "Non è affar tuo. Non ancora.", "intrigue": {"branch": "lasciato"}}},
             ]},
            {"title": "La tomba che non ha mai avuto", "focus": "maestro", "gap": (2, 3),
             "text": ("La notte della cerimonia. Il Maestro ti vede entrare e sospira, quasi affettuoso. «Speravo "
                      "venissi come erede. Sei venuto come becchino, vero?»"),
             "text_low": "La notte della cerimonia. Il Maestro ti vede entrare e ti tende la mano: «Il mio erede.»",
             "choices": [
                 {"label": "Pronunci il suo vero nome e gli offri la morte", "need_clues": 2,
                  "check": {"stat": "anima", "dc": 66},
                  "success": {"karma": 35, "heart": 25, "fame": 25, "lifespan_years": 30, "prize": _ORO,
                              "title": "Colui che Diede la Tomba al Maestro",
                              "text": ("Dici il suo nome. Il Maestro si ferma come un bambino chiamato dalla madre. "
                                       "«Nessuno lo diceva da diecimila anni», sussurra. Poi, piano, smette di "
                                       "trattenersi. Lo seppellisci tu, in una tomba con il suo nome sopra."),
                              "intrigue": {"end": "pace"}},
                  "failure": {"injury": 3,
                              "text": "Il nome ti si spezza in gola. Il Maestro ride, e ti scaraventa fuori dal padiglione.",
                              "intrigue": {"end": "respinto"}}},
                 {"label": "Lo affronti", "effects": {"intrigue": {"end": "duello"}}, "command": "duello {maestro}"},
                 {"label": "Accetti l'eredità", "need_branch": "erede",
                  "effects": {"karma": -25, "lifespan_years": 60, "prize": _ORO, "bt_bonus": 0.1,
                              "title": "Erede del Maestro Senza Tomba",
                              "text": ("Ti inginocchi. Lui ti posa le mani sulla testa, e diecimila anni di Dao ti "
                                       "attraversano come un fiume. «Tra cinquant'anni», sussurra, «verrò a "
                                       "riprendermelo. Tienilo bene.»"),
                              "intrigue": {"end": "erede"}}},
             ]},
        ],
        "auto_end": [{"outcome": "nuovo_corpo", "text": "Il Maestro Senza Tomba ha preso un nuovo corpo. Ne prenderà altri."}],
        "outcomes": {"pace": "Hai dato al Maestro Senza Tomba la tomba che non ha mai avuto.",
                     "duello_vinto": "Hai abbattuto il Maestro Senza Tomba. Il suo frammento, però, si è disperso nel vento.",
                     "duello_perso": "Il Maestro Senza Tomba ti ha battuto. «Torna quando sarai degno.»",
                     "duello_fuga": "Sei fuggito dal padiglione del Maestro.",
                     "respinto": "Il Maestro ti ha respinto.",
                     "erede": "Sei l'erede del Maestro Senza Tomba. Per cinquant'anni.",
                     "nuovo_corpo": "Il Maestro ha preso un nuovo corpo."},
    },
    # ---------------------------------------------------------------- III · il fantoccio di giada
    {
        "key": "maestro_giada", "title": "Il Maestro che non muore — Il Maestro di giada", "kind": "legame",
        "weight": 7, "tier_min": 5, "req_flag": "maestro_fantoccio", "delay": 40,
        "cast": {"maestro": "legame:maestro_fantoccio"},
        "acts": [
            {"title": "Il fantoccio che invecchia", "focus": "maestro", "gap": (1, 2),
             "text": ("Il fantoccio di giada vive nella grotta con {maestro}, e i due litigano come vecchi sposi. "
                      "Ma la giada si sta crepando: un'anima così grande non entra in un corpo così piccolo. «Ho "
                      "ancora un anno», ti dice il Maestro. «Forse due. Poi dovrò scegliere: un corpo vero, o la fine.»"),
             "choices": [
                 {"label": "Passi l'anno con lui, a imparare",
                  "effects": {"prize": _MANUALE, "bt_bonus": 0.05, "heart": 6,
                              "text": "Ogni sera una lezione. Ogni mattina una crepa in più.",
                              "intrigue": {"clue": 1, "branch": "lezioni"}}},
                 {"label": "Cerchi giada più antica per rinforzarlo (2000 pietre)",
                  "effects": {"stones": -2000, "text": "La giada nuova tiene. Per ora. Il Maestro tace, commosso.",
                              "intrigue": {"branch": "rinforzato"}}},
             ]},
            {"title": "L'ultima lezione", "auto": True,
             "text": "Una mattina il Maestro di giada ti chiama, e la sua voce è più piccola del solito.",
             "endings": [
                 {"need_branch": "lezioni", "outcome": "ultima_lezione",
                  "effects": {"lifespan_years": 25, "heart": 15, "karma": 20, "prize": _ORO,
                              "title": "Ultimo Allievo del Maestro Senza Tomba"},
                  "text": ("«Ho avuto diecimila anni e sette corpi», dice, «e l'anno migliore è stato questo, in un "
                           "fantoccio, con un ragazzo testardo.» Sceglie la fine. Si spegne mentre ti spiega l'ultima "
                           "cosa, a metà frase. La finisci tu, da solo, ad alta voce.")},
                 {"need_branch": "rinforzato", "outcome": "maestro_di_giada",
                  "effects": {"bt_bonus": 0.06, "heart": 8, "title": "Allievo del Maestro di Giada"},
                  "text": ("La giada nuova tiene. «Credo che resterò così», dice il Maestro, guardandosi le mani "
                           "verdi. «Un vecchio fantoccio in una grotta, con un eremita e un allievo. Non si sta male.»")},
                 {"outcome": "crepato", "effects": {"heart": 4},
                  "text": "La giada si spezza in silenzio. Nella grotta resta solo {maestro}, che finalmente dorme."},
             ]},
        ],
        "auto_end": [{"outcome": "crepato", "text": "Il fantoccio di giada si è spezzato mentre non c'eri."}],
        "outcomes": {"crepato": "Il Maestro di giada si è spezzato."},
    },
]
